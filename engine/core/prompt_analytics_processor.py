from typing import Dict, Any, List
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Avg, Count
from shared_models.models import Domain, Prompt, PromptAnalytics, PromptGroup, SentimentAnalytics
from datetime import date
import logging


logger = logging.getLogger(__name__)


class PromptAnalyticsProcessor:
    def __init__(self, max_concurrent_prompts: int):
        self.max_concurrent_prompts = max_concurrent_prompts

        # Initialize clients once
        self.openai_client = None
        self.gemini_client = None
        self.perplexity_client = None
        # Lazy import helpers from views.py
        self._helpers_loaded = False
        self._load_helpers()

    def _load_helpers(self) -> None:
        """Load analytics helper functions from views.py"""
        if self._helpers_loaded:
            return
        try:
            # Import self-contained helpers (no dependency on engine/views.py)
            from .analytics_helpers import (
                process_prompt_with_chatgpt,
                process_prompt_with_gemini,
                process_prompt_with_perplexity,
                extract_position_from_response,
                get_openai_client,
                get_gemini_client,
                get_perplexity_client,
            )
            self._process_prompt_with_chatgpt = process_prompt_with_chatgpt
            self._process_prompt_with_gemini = process_prompt_with_gemini
            self._process_prompt_with_perplexity = process_prompt_with_perplexity
            self._extract_position = extract_position_from_response
            self._get_openai_client = get_openai_client
            self._get_gemini_client = get_gemini_client
            self._get_perplexity_client = get_perplexity_client
            
            # Initialize clients
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
            logger.warning(f"Analytics helpers not available; using fallback processing: {str(e)}")
            self._helpers_loaded = True

    def schedule_tick(self) -> Dict[str, Any]:
        """
        Group-wise scheduler:
        - If any prompt group is SCHD, exit (let it finish).
        - Else pick one INIT prompt group, mark SCHD.
        - Enforce per-group scheduled prompt limit.
        - Process all INIT prompts in that group.
        """
        try:
            # If a group is in progress, skip scheduling
            if PromptGroup.objects.filter(track_status='SCHD').exists():
                return {'scheduled': False, 'reason': 'group_in_progress'}

            # Select one INIT group - only process if domain is fully complete
            # This prevents processing incomplete groups while domain is still creating prompts
            group = (
                PromptGroup.objects.filter(
                    track_status='INIT',
                    domain__processing_status='COMP'  # Wait until domain finishes
                )
                .select_related('domain')
                .order_by('modified_at')
                .first()
            )
            if group is None:
                return {'scheduled': False, 'reason': 'no_init_group'}

            max_per_group = int(getattr(settings, 'MAX_CONCURRENT_PROMPT_ANALYTICS', 10))

            # Mark group as scheduled
            with transaction.atomic():
                fresh = PromptGroup.objects.select_for_update().get(id=group.id)
                if fresh.track_status != 'INIT':
                    return {'scheduled': False, 'reason': 'race_condition'}
                fresh.track_status = 'SCHD'
                fresh.tracked_at = timezone.now()
                fresh.save(update_fields=['track_status', 'tracked_at', 'modified_at'])
                group = fresh

            # Enforce per-group scheduled limit
            scheduled_prompts_count = group.prompts.filter(track_status='SCHD').count()
            if scheduled_prompts_count >= max_per_group:
                return {
                    'scheduled': False,
                    'reason': 'group_limit_reached',
                    'group_id': group.id,
                    'scheduled_prompts_count': scheduled_prompts_count,
                    'limit': max_per_group,
                }

            # Fetch INIT prompts of this group
            init_prompts = list(
                group.prompts.filter(track_status='INIT').select_related('group__domain')
            )

            processed = 0
            failed = 0
            
            try:
                for prompt in init_prompts:
                    try:
                        # Mark prompt as scheduled then process
                        with transaction.atomic():
                            p = Prompt.objects.select_for_update().get(id=prompt.id)
                            if p.track_status != 'INIT':
                                continue
                            p.track_status = 'SCHD'
                            p.tracked_at = timezone.now()
                            p.save(update_fields=['track_status', 'tracked_at', 'modified_at'])
                        
                        self.process_single_prompt(prompt.id)
                        processed += 1
                    except Exception as prompt_error:
                        logger.error(f"Error processing prompt {prompt.id}: {str(prompt_error)}")
                        failed += 1
                        # Mark prompt as failed so it doesn't block the group
                        try:
                            prompt.track_status = 'FAIL'
                            prompt.track_message = f'Processing error: {str(prompt_error)[:200]}'
                            prompt.tracked_at = timezone.now()
                            prompt.save(update_fields=['track_status', 'track_message', 'tracked_at', 'modified_at'])
                        except:
                            pass
            finally:
                # ALWAYS check and aggregate, even if there were errors
                # This ensures the group doesn't stay stuck in SCHD
                self._check_and_aggregate_group(group)

            return {
                'scheduled': True,
                'group_id': group.id,
                'processed_prompts': processed,
                'failed_prompts': failed
            }
        except Exception as e:
            logger.error(f"Error in schedule_tick: {str(e)}")
            # Critical: If we fail here, reset the group to INIT so it can be retried
            try:
                group.track_status = 'INIT'
                group.track_message = f'Scheduler error, resetting: {str(e)[:200]}'
                group.tracked_at = timezone.now()
                group.save(update_fields=['track_status', 'track_message', 'tracked_at', 'modified_at'])
            except:
                pass
            return {'error': str(e)}

    def process_single_prompt(self, prompt_id: int) -> Dict[str, Any]:
        """
        Process analytics for a single prompt across all platforms.
        """
        try:
            prompt = (
                Prompt.objects.select_related('group__domain')
                .get(id=prompt_id)
            )
            logger.info(f"Processing analytics for prompt {prompt_id}: {prompt.prompt[:50]}...")

            # Update prompt status to processing
            prompt.track_status = 'PROC'
            prompt.tracked_at = timezone.now()
            prompt.save(update_fields=['track_status', 'tracked_at', 'modified_at'])

            # Get domain and group info
            user_domain = prompt.group.domain.name
            group = prompt.group

            # Process with each platform
            platforms = ['chatgpt']
            results = {}
            
            for platform in platforms:
                try:
                    logger.info(f"Processing {platform} for prompt {prompt_id}")
                    
                    if platform == 'chatgpt' and self.openai_client is not None:
                        result = self._process_prompt_with_chatgpt(
                            prompt.prompt, user_domain, self.openai_client, group
                        )
                    elif platform == 'gemini' and self.gemini_client is not None:
                        result = self._process_prompt_with_gemini(
                            prompt.prompt, user_domain, self.gemini_client, group
                        )
                    elif platform == 'perplexity' and self.perplexity_client is not None:
                        result = self._process_prompt_with_perplexity(
                            prompt.prompt, user_domain, self.perplexity_client, group
                        )
                    else:
                        # Fallback processing
                        result = self._get_fallback_analytics(prompt.prompt, user_domain, platform)
                    
                    results[platform] = result
                    logger.info(f"Completed {platform} processing for prompt {prompt_id}")
                    
                except Exception as e:
                    logger.error(f"Error processing {platform} for prompt {prompt_id}: {str(e)}")
                    results[platform] = self._get_fallback_analytics(prompt.prompt, user_domain, platform)

            # Create analytics record
            analytics = self._create_analytics_record(prompt, results)
            
            # Update prompt status to completed
            prompt.track_status = 'COMP'
            prompt.tracked_at = timezone.now()
            prompt.save(update_fields=['track_status', 'tracked_at', 'modified_at'])

            # Check if all prompts in group are done, then aggregate
            self._check_and_aggregate_group(group)

            return {
                'prompt_id': prompt_id,
                'analytics_id': analytics.id if analytics else None,
                'status': 'completed',
                'platforms_processed': list(results.keys())
            }
            
        except Exception as e:
            logger.error(f"Error processing prompt {prompt_id}: {str(e)}")
            # Mark prompt as failed
            try:
                prompt = Prompt.objects.get(id=prompt_id)
                prompt.track_status = 'FAIL'
                prompt.tracked_at = timezone.now()
                prompt.save(update_fields=['track_status', 'tracked_at', 'modified_at'])
            except:
                pass
            return {'error': str(e)}

    def _create_analytics_record(self, prompt: Prompt, results: Dict[str, Any]) -> PromptAnalytics:
        """Create one PromptAnalytics entry per platform result."""
        last_created: PromptAnalytics | None = None
        try:
            for platform_key, result in results.items():
                # Determine platform label stored in DB
                if platform_key == 'chatgpt':
                    platform_label = 'ChatGPT'
                elif platform_key == 'gemini':
                    platform_label = 'Google Gemini'
                elif platform_key == 'perplexity':
                    platform_label = 'Perplexity'
                else:
                    platform_label = platform_key

                # Extract position from context
                extracted_position = None
                if self._extract_position and result.get('context_summary'):
                    try:
                        extracted_position = self._extract_position(
                            result.get('context_summary') or '',
                            prompt.group.domain.name,
                            result.get('citations') or [],
                            result.get('is_mention') or False,
                        )
                    except Exception:
                        extracted_position = None

                # Create or update analytics row per platform
                analytics_obj, _ = PromptAnalytics.objects.update_or_create(
                    prompt=prompt,
                    platform=platform_label,
                    defaults={
                        'is_mention': bool(result.get('is_mention') or (result.get('mention_count', 0) or 0) > 0),
                        'total_mentions': int(result.get('mention_count', 0) or 0),
                        'total_citations': int(result.get('citation_count', 0) or len(result.get('citations') or [])),
                        'position': float(extracted_position or 0),
                        'sentiment_category': str(result.get('sentiment') or 'neutral'),
                        'sentiment_score': float(result.get('sentiment_score', 0.0) or 0.0),
                        'context_summary': result.get('context_summary') or result.get('response_text') or '',
                        'citation_list': result.get('citations') or [],
                        'track_status': 'COMP',  # Mark as completed
                        'tracked_at': timezone.now(),
                        'is_published': True,  # Mark as published when completed
                    }
                )
                last_created = analytics_obj

            return last_created

        except Exception as e:
            logger.error(f"Error creating analytics records: {str(e)}")
            return None

    def _check_and_aggregate_group(self, group: PromptGroup) -> None:
        """If no prompts remain in non-complete states, aggregate group and domain, mark group COMP."""
        try:
            # Validation: Check if group has at least one prompt
            total_prompts = group.prompts.count()
            if total_prompts == 0:
                logger.warning(f"Group {group.id} has no prompts, skipping aggregation")
                return
            
            # Count prompts that are still pending (INIT, SCHD, PROC)
            # COMP and FAIL are considered "done"
            remaining_prompts = group.prompts.filter(track_status__in=['INIT', 'SCHD', 'PROC']).count()
            if remaining_prompts > 0:
                logger.info(f"Group {group.id} not ready for aggregation: {remaining_prompts}/{total_prompts} prompts remaining")
                return

            logger.info(f"Aggregating results for group {group.id}")
            
            # Aggregate analytics for this group
            # Use prompt__track_status because PromptAnalytics.track_status is never updated
            analytics = PromptAnalytics.objects.filter(
                prompt__group=group,
                prompt__track_status='COMP'
            )
            
            if not analytics.exists():
                logger.warning(f"No completed analytics found for group {group.id}")
                return

            # Calculate group totals
            group_totals = analytics.aggregate(
                total_citations=Sum('total_citations'),
                total_mentions=Sum('total_mentions'),
                avg_position=Avg('position'),
            )

            # Update group record
            group.total_citations = group_totals['total_citations'] or 0
            group.total_mentions = group_totals['total_mentions'] or 0
            group.average_position = group_totals['avg_position'] or 0.0
            group.track_status = 'COMP'
            group.tracked_at = timezone.now()
            group.is_published = True  # Mark as published when completed
            group.save(update_fields=[
                'total_citations', 'total_mentions', 'average_position', 
                'track_status', 'tracked_at', 'is_published', 'modified_at'
            ])
            
            # Update SentimentAnalytics for this group's theme
            if group.theme:
                try:
                    self._update_sentiment_analytics_for_theme(group, analytics)
                except Exception as sentiment_error:
                    logger.error(f"Error updating sentiment analytics for group {group.id}: {str(sentiment_error)}")
                    # Don't fail the entire aggregation if sentiment update fails

            # Update domain aggregating across all completed analytics
            # Use select_for_update to prevent concurrent updates from overwriting each other
            with transaction.atomic():
                domain = Domain.objects.select_for_update().get(id=group.domain_id)
                
                # Use prompt__track_status because PromptAnalytics.track_status is never updated
                domain_analytics = PromptAnalytics.objects.filter(
                    prompt__domain=domain,
                    prompt__track_status='COMP'
                )
                domain_totals = domain_analytics.aggregate(
                    total_citations=Sum('total_citations'),
                    total_mentions=Sum('total_mentions'),
                    avg_position=Avg('position')
                )
                domain.total_citations = domain_totals['total_citations'] or 0
                domain.total_mentions = domain_totals['total_mentions'] or 0
                domain.average_position = domain_totals['avg_position'] or 0.0
                domain.tracked_at = timezone.now()
                domain.save(update_fields=['total_citations', 'total_mentions', 'average_position', 'tracked_at', 'modified_at'])

            logger.info(f"Successfully aggregated group {group.id} and domain {domain.id}")
            
        except Exception as e:
            logger.error(f"Error aggregating group {group.id}: {str(e)}")

    def _update_sentiment_analytics_for_theme(self, group: PromptGroup, analytics) -> None:
        """
        Update or create SentimentAnalytics record for this group's theme
        Aggregates sentiment data from all PromptAnalytics in the group
        """
        try:
            theme = group.theme
            domain = group.domain
            today = date.today()
            
            # Ensure analytics is a PromptAnalytics QuerySet, not a list or other type
            if not hasattr(analytics, 'filter'):
                logger.error(f"Invalid analytics type for group {group.id}: {type(analytics)}")
                return
            
            # Debug: Log the analytics queryset info
            logger.debug(f"Analytics queryset for group {group.id}: model={analytics.model.__name__}, count={analytics.count()}")
            
            # Count sentiment categories - make sure we're working with a clean queryset
            # Re-query from database to avoid any stale queryset issues
            from shared_models.models import PromptAnalytics as PA
            analytics_qs = PA.objects.filter(
                prompt__group=group,
                prompt__track_status='COMP'
            )
            
            total = analytics_qs.filter(is_mention=True, is_published=True).count()
            
            if total == 0:
                logger.info(f"No mentions found for theme '{theme}', skipping sentiment update")
                return
            
            positive_count = analytics_qs.filter(
                sentiment_category='positive',
                is_mention=True,
                is_published=True
            ).count()
            
            neutral_count = analytics_qs.filter(
                sentiment_category='neutral',
                is_mention=True,
                is_published=True
            ).count()
            
            negative_count = analytics_qs.filter(
                sentiment_category='negative',
                is_mention=True,
                is_published=True
            ).count()
            
            # Calculate percentages
            positive_pct = (positive_count / total) * 100 if total > 0 else 0.0
            neutral_pct = (neutral_count / total) * 100 if total > 0 else 0.0
            negative_pct = (negative_count / total) * 100 if total > 0 else 0.0
            
            # Update or create SentimentAnalytics for this theme (overall, not platform-specific)
            sentiment_analytics, created = SentimentAnalytics.objects.update_or_create(
                domain=domain,
                theme=theme,
                platform=None,  # Overall aggregation
                timestamp=today,
                defaults={
                    'positive_percentage': round(positive_pct, 2),
                    'neutral_percentage': round(neutral_pct, 2),
                    'negative_percentage': round(negative_pct, 2),
                    'mention_count': total
                }
            )
            
            action = "Created" if created else "Updated"
            logger.info(
                f"{action} SentimentAnalytics for theme '{theme}': "
                f"Pos={positive_pct:.1f}%, Neu={neutral_pct:.1f}%, Neg={negative_pct:.1f}%, "
                f"Mentions={total}"
            )
            
        except Exception as e:
            logger.error(f"Error updating sentiment analytics for theme '{group.theme}': {str(e)}")
    
    def _get_fallback_analytics(self, prompt_text: str, user_domain: str, platform: str) -> Dict[str, Any]:
        """Generate fallback analytics when AI platforms are unavailable"""
        return {
            'citations': 0,
            'mention_count': 0,
            'sentiment_score': 0.0,
            'context_summary': f"Fallback processing for {platform} - AI service unavailable"
        }