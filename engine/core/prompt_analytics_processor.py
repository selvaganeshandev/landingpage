from typing import Dict, Any
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Avg
from shared_models.models import Domain, Prompt, PromptAnalytics
import logging


logger = logging.getLogger(__name__)


class PromptAnalyticsProcessor:
    def __init__(self, max_concurrent_prompts: int):
        self.max_concurrent_prompts = max_concurrent_prompts

        # Initialize clients once
        self.openai_client = None
        self.gemini_client = None
        self.perplexity_client = None
        # Lazy import helpers from core.analytics_helpers to avoid external dependencies
        self._helpers_loaded = False
        self._load_helpers()

    def _load_helpers(self) -> None:
        if self._helpers_loaded:
            return
        try:
            from .analytics_helpers import (
                get_openai_client,
                get_gemini_client,
                get_perplexity_client,
                process_prompt_with_chatgpt,
                process_prompt_with_gemini_wrapper,
                process_prompt_with_perplexity_wrapper,
                extract_position_from_response,
            )
            self._get_openai_client = get_openai_client
            self._get_gemini_client = get_gemini_client
            self._get_perplexity_client = get_perplexity_client
            self._process_prompt_with_chatgpt = process_prompt_with_chatgpt
            self._process_prompt_with_gemini = process_prompt_with_gemini_wrapper
            self._process_prompt_with_perplexity = process_prompt_with_perplexity_wrapper
            self._extract_position = extract_position_from_response
            try:
                self.openai_client = self._get_openai_client()
            except Exception as e:
                logger.warning(f"ChatGPT client unavailable: {str(e)}")
            try:
                self.gemini_client = self._get_gemini_client()
            except Exception as e:
                logger.warning(f"Gemini client unavailable: {str(e)}")
            try:
                self.perplexity_client = self._get_perplexity_client()
            except Exception as e:
                logger.warning(f"Perplexity client unavailable: {str(e)}")
            self._helpers_loaded = True
        except Exception as e:
            # Helpers not available; fall back to no-op processing
            logger.warning(f"Analytics helpers not available; using fallback processing: {e}")
            self._get_openai_client = None
            self._get_gemini_client = None
            self._get_perplexity_client = None
            self._process_prompt_with_chatgpt = None
            self._process_prompt_with_gemini = None
            self._process_prompt_with_perplexity = None
            self._extract_position = None

    def schedule_tick(self) -> Dict[str, Any]:
        # Concurrency window based on prompts currently scheduled (SCHD) or processing
        current_proc_prompts = Prompt.objects.filter(track_status='SCHD').count()
        available_slots = max(0, self.max_concurrent_prompts - current_proc_prompts)
        if available_slots <= 0:
            return {
                'success': True,
                'processed_domains': 0,
                'message': 'No available slots for prompt analytics processing'
            }

        # Find prompts ready to process ordered by modified time
        ready_prompt_ids = list(
            Prompt.objects.filter(track_status__in=['INIT'])
            .order_by('modified_at')
            .values_list('id', flat=True)[:available_slots]
        )

        # Group by domain and enqueue domain-level processing (the Celery task wraps this class)
        prompts_qs = Prompt.objects.filter(id__in=ready_prompt_ids).select_related('domain')
        domain_ids = sorted({p.domain_id for p in prompts_qs})
        from .processing_tasks import process_prompt_analytics_task  # local import to avoid circular

        processed_domains = 0
        for domain_id in domain_ids:
            try:
                process_prompt_analytics_task.delay(domain_id)
                processed_domains += 1
            except Exception as e:
                logger.error(f"Error scheduling analytics for domain {domain_id}: {str(e)}")

        return {
            'success': True,
            'processed_domains': processed_domains,
            'message': f'Scheduled analytics processing for {processed_domains} domains'
        }

    def process_domain(self, domain_id: int) -> Dict[str, Any]:
        try:
            domain = Domain.objects.get(id=domain_id)

            prompts = Prompt.objects.filter(domain=domain)
            if not prompts.exists():
                return {
                    'success': True,
                    'domain_id': domain_id,
                    'message': 'No prompts found for domain'
                }

            processed_count = 0

            for prompt in prompts:
                try:
                    # Mark prompt as scheduled
                    prompt.track_status = 'SCHD'
                    prompt.tracked_at = timezone.now()
                    prompt.save(update_fields=['track_status', 'tracked_at', 'modified_at'])

                    analytics = PromptAnalytics.objects.filter(prompt=prompt)

                    # Set analytics to scheduled/processing per platform
                    for analytic in analytics:
                        platform = analytic.platform.lower()
                        if platform == 'chatgpt':
                            analytic.chatgpt_status = 'processing'
                        elif platform == 'google gemini':
                            analytic.gemini_status = 'processing'
                        elif platform == 'perplexity':
                            analytic.perplexity_status = 'processing'
                        analytic.track_status = 'SCHD'
                        analytic.tracked_at = timezone.now()
                        analytic.save(update_fields=['chatgpt_status', 'gemini_status', 'perplexity_status', 'track_status', 'tracked_at', 'modified_at'])

                    # Perform real processing
                    user_domain = prompt.domain.url or prompt.domain.name
                    group = prompt.group

                    for analytic in analytics:
                        platform = analytic.platform.lower()
                        try:
                            if platform == 'chatgpt' and self.openai_client is not None and self._process_prompt_with_chatgpt is not None:
                                result = self._process_prompt_with_chatgpt(prompt.prompt, user_domain, self.openai_client, group)
                                analytic.chatgpt_status = 'completed'
                            elif platform == 'google gemini' and self.gemini_client is not None and self._process_prompt_with_gemini is not None:
                                result = self._process_prompt_with_gemini(prompt.prompt, user_domain, self.gemini_client, group)
                                analytic.gemini_status = 'completed'
                            elif platform == 'perplexity' and self.perplexity_client is not None and self._process_prompt_with_perplexity is not None:
                                result = self._process_prompt_with_perplexity(prompt.prompt, user_domain, self.perplexity_client, group)
                                analytic.perplexity_status = 'completed'
                            else:
                                # Client not available; mark zeros
                                result = {
                                    'response_text': '',
                                    'is_mention': False,
                                    'mention_count': 0,
                                    'citations': [],
                                    'sentiment': 'neutral',
                                    'sentiment_score': 0.0,
                                    'context_summary': '',
                                    'citation_count': 0,
                                    'has_citation': False,
                                    'all_urls': []
                                }

                            if self._extract_position is not None:
                                position = self._extract_position(
                                    result.get('context_summary') or result.get('response_text') or '',
                                    user_domain,
                                    result.get('citations') or [],
                                    result.get('is_mention') or False,
                                )
                            else:
                                position = 0

                            analytic.is_mention = result.get('is_mention', False)
                            analytic.total_mentions = int(result.get('mention_count', 0) or 0)
                            analytic.total_citations = int(result.get('citation_count', 0) or len(result.get('all_urls') or []))
                            analytic.position = float(position or 0)
                            analytic.sentiment = result.get('sentiment', 'neutral')
                            analytic.sentiment_score = float(result.get('sentiment_score', 0.0) or 0.0)
                            analytic.citations = result.get('citations') or []
                            analytic.context_summary = result.get('context_summary') or result.get('response_text') or ''

                            analytic.track_status = 'COMP'
                            analytic.tracked_at = timezone.now()
                            analytic.save(update_fields=[
                                'chatgpt_status', 'gemini_status', 'perplexity_status',
                                'is_mention', 'total_mentions', 'total_citations', 'position',
                                'sentiment', 'sentiment_score', 'citations', 'context_summary',
                                'track_status', 'tracked_at', 'modified_at'
                            ])
                        except Exception as perr:
                            logger.error(f"Platform processing failed for {platform}: {str(perr)}")
                            analytic.track_status = 'FAIL'
                            analytic.tracked_at = timezone.now()
                            analytic.save(update_fields=['track_status', 'tracked_at', 'modified_at'])

                    # Check completion and aggregate group/domain
                    all_completed = all(
                        a.chatgpt_status == 'completed' and
                        a.gemini_status == 'completed' and
                        a.perplexity_status == 'completed'
                        for a in analytics
                    )
                    if all_completed:
                        prompt.track_status = 'COMP'
                        prompt.tracked_at = timezone.now()

                        if prompt.group:
                            group_prompts = prompt.group.prompts.all()
                            if all(p.track_status == 'COMP' for p in group_prompts):
                                group_analytics = PromptAnalytics.objects.filter(prompt__group=prompt.group)
                                aggregated_metrics = group_analytics.aggregate(
                                    total_citations=Sum('total_citations'),
                                    total_mentions=Sum('total_mentions'),
                                    avg_position=Avg('position'),
                                    avg_sentiment_score=Avg('sentiment_score')
                                )
                                prompt.group.total_citations = aggregated_metrics.get('total_citations') or 0
                                prompt.group.total_mentions = aggregated_metrics.get('total_mentions') or 0
                                prompt.group.track_status = 'COMP'
                                prompt.group.tracked_at = timezone.now()
                                prompt.group.save(update_fields=['total_citations', 'total_mentions', 'track_status', 'tracked_at', 'modified_at'])

                        # Domain-level aggregation
                        domain_prompts = domain.prompts.all()
                        if all(p.track_status == 'COMP' for p in domain_prompts):
                            domain_analytics = PromptAnalytics.objects.filter(prompt__domain=domain)
                            domain_aggregated = domain_analytics.aggregate(
                                total_citations=Sum('total_citations'),
                                total_mentions=Sum('total_mentions'),
                                avg_position=Avg('position'),
                                avg_sentiment_score=Avg('sentiment_score')
                            )
                            domain.total_citations = domain_aggregated.get('total_citations') or 0
                            domain.total_mentions = domain_aggregated.get('total_mentions') or 0
                            domain.track_status = 'COMP'
                            domain.tracked_at = timezone.now()
                            domain.save(update_fields=['total_citations', 'total_mentions', 'track_status', 'tracked_at', 'modified_at'])

                    prompt.save(update_fields=['track_status', 'tracked_at', 'modified_at'])
                    processed_count += 1

                except Exception as e:
                    logger.error(f"Error processing prompt {prompt.id}: {str(e)}")
                    prompt.track_status = 'FAIL'
                    prompt.tracked_at = timezone.now()
                    prompt.save(update_fields=['track_status', 'tracked_at', 'modified_at'])

            return {
                'success': True,
                'domain_id': domain_id,
                'processed_count': processed_count,
                'message': f'Processed {processed_count} prompts for domain: {domain.name}'
            }

        except Domain.DoesNotExist:
            logger.error(f"Domain with id {domain_id} does not exist")
            return {
                'success': False,
                'domain_id': domain_id,
                'error': 'Domain not found'
            }
        except Exception as e:
            logger.error(f"Error processing prompt analytics for domain {domain_id}: {str(e)}")
            return {
                'success': False,
                'domain_id': domain_id,
                'error': str(e)
            }


