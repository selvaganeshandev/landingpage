from typing import Dict, Any, List
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Avg, Count
from shared_models.models import (
    Domain, Prompt, PromptAnalytics, PromptGroup, SentimentAnalytics,
    PromptMetricSnapshot, PromptGroupMetricSnapshot, DomainMetricSnapshot
)
from decimal import Decimal
from datetime import date
import logging
from .metric_snapshot_logger import (
    log_snapshot_creation_start, log_table_check, log_analytics_filtering,
    log_prompts_processing, log_platform_processing, log_snapshot_creation,
    log_snapshot_error, log_snapshot_creation_complete, log_method_call,
    log_database_query
)


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
                avg_sentiment=Avg('sentiment_score'),
            )

            # Calculate visibility score and sentiment score
            avg_pos = float(group_totals['avg_position'] or 0)
            group_visibility_score = self._calculate_visibility_score(avg_pos)
            group_sentiment_score = float(group_totals['avg_sentiment'] or 0)

            # Update group record
            group.total_citations = group_totals['total_citations'] or 0
            group.total_mentions = group_totals['total_mentions'] or 0
            group.average_position = avg_pos
            group.visibility_score = group_visibility_score
            group.sentiment_score = group_sentiment_score
            group.track_status = 'COMP'
            group.tracked_at = timezone.now()
            group.is_published = True  # Mark as published when completed
            group.save(update_fields=[
                'total_citations', 'total_mentions', 'average_position',
                'visibility_score', 'sentiment_score',
                'track_status', 'tracked_at', 'is_published', 'modified_at'
            ])
            
            # Create metric snapshots for group (daily by default)
            today = date.today()
            self._create_group_metric_snapshots(group, analytics, today, period_type='daily')
            
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
                    prompt__group__domain=domain,
                    prompt__track_status='COMP'
                )
                domain_totals = domain_analytics.aggregate(
                    total_citations=Sum('total_citations'),
                    total_mentions=Sum('total_mentions'),
                    avg_position=Avg('position'),
                    avg_sentiment=Avg('sentiment_score'),
                )
                
                # Calculate visibility score and sentiment score for domain
                domain_avg_pos = float(domain_totals['avg_position'] or 0)
                domain_visibility_score = self._calculate_visibility_score(domain_avg_pos)
                domain_sentiment_score = float(domain_totals['avg_sentiment'] or 0)
                
                domain.total_citations = domain_totals['total_citations'] or 0
                domain.total_mentions = domain_totals['total_mentions'] or 0
                domain.average_position = domain_avg_pos
                domain.visibility_score = domain_visibility_score
                domain.sentiment_score = domain_sentiment_score
                domain.tracked_at = timezone.now()
                domain.save(update_fields=[
                    'total_citations', 'total_mentions', 'average_position',
                    'visibility_score', 'sentiment_score',
                    'tracked_at', 'modified_at'
                ])
                
                # Create metric snapshots for domain (daily by default)
                try:
                    self._create_domain_metric_snapshots(domain, domain_analytics, today, period_type='daily')
                except Exception as domain_snapshot_error:
                    logger.error(f"Error creating domain metric snapshots: {str(domain_snapshot_error)}", exc_info=True)
                
                # Create metric snapshots for individual prompts (daily by default)
                # Use domain_analytics to get all prompts in the domain, not just the current group
                try:
                    logger.info(f"About to call _create_prompt_metric_snapshots with {domain_analytics.count()} analytics")
                    self._create_prompt_metric_snapshots(domain_analytics, today, period_type='daily')
                    logger.info(f"Completed _create_prompt_metric_snapshots call")
                except Exception as prompt_snapshot_error:
                    logger.error(f"Error creating prompt metric snapshots: {str(prompt_snapshot_error)}", exc_info=True)

            logger.info(f"Successfully aggregated group {group.id} and domain {domain.id}")
            
        except Exception as e:
            logger.error(f"Error aggregating group {group.id}: {str(e)}")

    def _update_sentiment_analytics_for_theme(self, group: PromptGroup, analytics) -> None:
        """
        Update or create SentimentAnalytics record for this group's theme
        Aggregates sentiment data from ALL groups with the same theme in the domain
        """
        try:
            theme = group.theme
            domain = group.domain
            today = date.today()
            
            if not theme:
                return
            
            # Query ALL PromptAnalytics for ALL groups with this theme in the domain
            # This ensures we aggregate across all groups, not just one group
            from shared_models.models import PromptAnalytics as PA
            analytics_qs = PA.objects.filter(
                prompt__group__domain=domain,
                prompt__group__theme=theme,
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
            
            # Calculate 5 core metrics
            totals = analytics_qs.filter(is_mention=True, is_published=True).aggregate(
                total_mentions=Sum('total_mentions'),
                total_citations=Sum('total_citations'),
                avg_position=Avg('position'),
                avg_sentiment=Avg('sentiment_score'),
            )
            
            avg_pos = float(totals['avg_position'] or 0)
            visibility_score = self._calculate_visibility_score(avg_pos)
            
            # Update or create SentimentAnalytics for this theme (overall, not platform-specific)
            sentiment_analytics, created = SentimentAnalytics.objects.update_or_create(
                domain=domain,
                theme=theme,
                platform=None,  # Overall aggregation
                snapshot_date=today,
                period_type='daily',
                defaults={
                    'positive_percentage': round(positive_pct, 2),
                    'neutral_percentage': round(neutral_pct, 2),
                    'negative_percentage': round(negative_pct, 2),
                    'mention_count': total,
                    'mentions': totals['total_mentions'] or 0,
                    'citations': totals['total_citations'] or 0,
                    'visibility_score': visibility_score,
                    'sentiment_score': float(totals['avg_sentiment'] or 0),
                    'average_position': avg_pos,
                }
            )
            
            # Create platform-wise sentiment analytics
            platforms = analytics_qs.values_list('platform', flat=True).distinct()
            for platform in platforms:
                platform_analytics = analytics_qs.filter(
                    platform=platform,
                    is_mention=True,
                    is_published=True
                )
                platform_total = platform_analytics.count()
                
                if platform_total == 0:
                    continue
                
                platform_positive = platform_analytics.filter(sentiment_category='positive').count()
                platform_neutral = platform_analytics.filter(sentiment_category='neutral').count()
                platform_negative = platform_analytics.filter(sentiment_category='negative').count()
                
                platform_positive_pct = (platform_positive / platform_total) * 100
                platform_neutral_pct = (platform_neutral / platform_total) * 100
                platform_negative_pct = (platform_negative / platform_total) * 100
                
                platform_totals = platform_analytics.aggregate(
                    total_mentions=Sum('total_mentions'),
                    total_citations=Sum('total_citations'),
                    avg_position=Avg('position'),
                    avg_sentiment=Avg('sentiment_score'),
                )
                
                platform_avg_pos = float(platform_totals['avg_position'] or 0)
                platform_visibility_score = self._calculate_visibility_score(platform_avg_pos)
                
                SentimentAnalytics.objects.update_or_create(
                    domain=domain,
                    theme=theme,
                    platform=platform,
                    snapshot_date=today,
                    period_type='daily',
                    defaults={
                        'positive_percentage': round(platform_positive_pct, 2),
                        'neutral_percentage': round(platform_neutral_pct, 2),
                        'negative_percentage': round(platform_negative_pct, 2),
                        'mention_count': platform_total,
                        'mentions': platform_totals['total_mentions'] or 0,
                        'citations': platform_totals['total_citations'] or 0,
                        'visibility_score': platform_visibility_score,
                        'sentiment_score': float(platform_totals['avg_sentiment'] or 0),
                        'average_position': platform_avg_pos,
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
    
    def _calculate_visibility_score(self, average_position: float) -> Decimal:
        """
        Calculate visibility score from average position.
        Formula: max(0, min(100, 100 - (average_position * 20)))
        """
        if average_position <= 0:
            return Decimal('100.0')
        score = max(0, min(100, 100 - (average_position * 20)))
        return Decimal(str(round(score, 2)))
    
    def _create_prompt_metric_snapshots(self, analytics, snapshot_date: date, period_type: str = 'daily') -> None:
        """Create metric snapshots for individual prompts (per platform only)"""
        try:
            analytics_count = analytics.count()
            log_snapshot_creation_start(analytics_count, snapshot_date, period_type)
            log_method_call("_create_prompt_metric_snapshots", 
                          analytics_count=analytics_count,
                          snapshot_date=str(snapshot_date),
                          period_type=period_type)
            
            # First, verify the table exists and can be queried
            try:
                existing_count = PromptMetricSnapshot.objects.count()
                log_table_check(True, existing_count)
                logger.info(f"PromptMetricSnapshot table exists, current count: {existing_count}")
            except Exception as table_check_error:
                log_table_check(False, error=table_check_error)
                logger.error(f"Error checking PromptMetricSnapshot table: {str(table_check_error)}", exc_info=True)
                return
            
            logger.info(f"Starting _create_prompt_metric_snapshots with {analytics_count} analytics records")
            
            # Filter out analytics with no platform
            analytics_with_platform = analytics.exclude(platform__isnull=True).exclude(platform='')
            
            total_with_platform = analytics_with_platform.count()
            total_count = analytics.count()
            
            # Get sample platforms for logging
            sample_platforms = list(analytics.values_list('platform', flat=True).distinct()[:10])
            log_analytics_filtering(total_count, total_with_platform, sample_platforms)
            logger.info(f"Analytics with platform: {total_with_platform} (total: {total_count})")
            
            if not analytics_with_platform.exists():
                logger.warning(f"No analytics with platform found for prompt metric snapshots")
                logger.warning(f"Sample platforms in analytics: {sample_platforms}")
                log_snapshot_creation_complete(0, 0, 0)
                return
            
            # Group analytics by prompt
            prompts = list(analytics_with_platform.values_list('prompt', flat=True).distinct())
            # Get actual prompt objects for logging
            prompt_objects = Prompt.objects.filter(id__in=prompts) if prompts else []
            prompt_ids = [p.id for p in prompt_objects] if prompt_objects else prompts
            
            log_prompts_processing(len(prompts), prompt_ids)
            logger.info(f"Creating prompt metric snapshots for {len(prompts)} prompts on {snapshot_date}")
            
            created_count = 0
            updated_count = 0
            
            # Get actual prompt objects for processing
            prompt_objects = Prompt.objects.filter(id__in=prompts) if prompts else []
            
            for prompt in prompt_objects:
                prompt_analytics = analytics_with_platform.filter(prompt=prompt)
                
                # Create snapshots per platform for this prompt only (no aggregated snapshot)
                platforms = list(prompt_analytics.values_list('platform', flat=True).distinct())
                
                logger.debug(f"Prompt {prompt.id} has {len(platforms)} platforms: {platforms}")
                
                for platform in platforms:
                    if not platform:  # Skip None or empty platforms
                        logger.debug(f"Skipping empty platform for prompt {prompt.id}")
                        continue
                        
                    platform_analytics = prompt_analytics.filter(platform=platform)
                    platform_analytics_count = platform_analytics.count()
                    
                    log_platform_processing(prompt.id, platform, platform_analytics_count)
                    
                    if not platform_analytics.exists():
                        logger.debug(f"No analytics found for prompt {prompt.id}, platform {platform}")
                        continue
                    
                    platform_totals = platform_analytics.aggregate(
                        total_mentions=Sum('total_mentions'),
                        total_citations=Sum('total_citations'),
                        avg_position=Avg('position'),
                        avg_sentiment=Avg('sentiment_score'),
                    )
                    
                    platform_avg_pos = float(platform_totals['avg_position'] or 0)
                    platform_visibility_score = self._calculate_visibility_score(platform_avg_pos)
                    
                    metrics = {
                        'mentions': platform_totals['total_mentions'] or 0,
                        'citations': platform_totals['total_citations'] or 0,
                        'visibility_score': platform_visibility_score,
                        'sentiment_score': float(platform_totals['avg_sentiment'] or 0),
                        'average_position': platform_avg_pos,
                    }
                    
                    try:
                        log_database_query(
                            f"update_or_create for prompt {prompt.id}, platform {platform}, date {snapshot_date}"
                        )
                        
                        snapshot, created = PromptMetricSnapshot.objects.update_or_create(
                            prompt=prompt,
                            platform=platform,
                            snapshot_date=snapshot_date,
                            period_type=period_type,
                            defaults=metrics
                        )
                        
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                            
                        log_snapshot_creation(prompt.id, platform, snapshot_date, created, metrics)
                        
                        action = "Created" if created else "Updated"
                        logger.info(
                            f"{action} PromptMetricSnapshot for prompt {prompt.id}, "
                            f"platform {platform}, date {snapshot_date}: "
                            f"mentions={metrics['mentions']}, "
                            f"citations={metrics['citations']}, "
                            f"visibility={metrics['visibility_score']}, "
                            f"position={metrics['average_position']}"
                        )
                    except Exception as create_error:
                        log_snapshot_error(prompt.id, platform, create_error)
                        logger.error(
                            f"Error creating snapshot for prompt {prompt.id}, platform {platform}: {str(create_error)}",
                            exc_info=True
                        )
            
            log_snapshot_creation_complete(created_count, updated_count, len(prompts))
            logger.info(
                f"Completed _create_prompt_metric_snapshots: "
                f"{created_count} created, {updated_count} updated, "
                f"{len(prompts)} prompts processed"
            )
        except Exception as e:
            logger.error(f"Error creating prompt metric snapshots: {str(e)}", exc_info=True)
            log_snapshot_error(None, None, e)
    
    def _create_group_metric_snapshots(
        self, 
        group: PromptGroup, 
        analytics, 
        snapshot_date: date, 
        period_type: str = 'daily'
    ) -> None:
        """Create metric snapshots for prompt group (per platform only)"""
        try:
            # Filter out analytics with no platform
            analytics_with_platform = analytics.exclude(platform__isnull=True).exclude(platform='')
            
            if not analytics_with_platform.exists():
                logger.warning(f"No analytics with platform found for group {group.id} metric snapshots")
                return
            
            # Create snapshots per platform only (no aggregated snapshot)
            platforms = list(analytics_with_platform.values_list('platform', flat=True).distinct())
            
            logger.info(f"Creating group metric snapshots for group {group.id}, {len(platforms)} platforms")
            
            for platform in platforms:
                if not platform:  # Skip None or empty platforms
                    continue
                    
                platform_analytics = analytics_with_platform.filter(platform=platform)
                
                if not platform_analytics.exists():
                    continue
                
                platform_totals = platform_analytics.aggregate(
                    total_mentions=Sum('total_mentions'),
                    total_citations=Sum('total_citations'),
                    avg_position=Avg('position'),
                    avg_sentiment=Avg('sentiment_score'),
                )
                
                platform_avg_pos = float(platform_totals['avg_position'] or 0)
                platform_visibility_score = self._calculate_visibility_score(platform_avg_pos)
                
                snapshot, created = PromptGroupMetricSnapshot.objects.update_or_create(
                    prompt_group=group,
                    platform=platform,
                    snapshot_date=snapshot_date,
                    period_type=period_type,
                    defaults={
                        'mentions': platform_totals['total_mentions'] or 0,
                        'citations': platform_totals['total_citations'] or 0,
                        'visibility_score': platform_visibility_score,
                        'sentiment_score': float(platform_totals['avg_sentiment'] or 0),
                        'average_position': platform_avg_pos,
                    }
                )
                
                action = "Created" if created else "Updated"
                logger.debug(
                    f"{action} PromptGroupMetricSnapshot for group {group.id}, "
                    f"platform {platform}, date {snapshot_date}: "
                    f"mentions={platform_totals['total_mentions'] or 0}, "
                    f"citations={platform_totals['total_citations'] or 0}"
                )
        except Exception as e:
            logger.error(f"Error creating group metric snapshots: {str(e)}", exc_info=True)
    
    def _create_domain_metric_snapshots(
        self, 
        domain: Domain, 
        analytics, 
        snapshot_date: date, 
        period_type: str = 'daily'
    ) -> None:
        """Create metric snapshots for domain (per platform only)"""
        try:
            # Filter out analytics with no platform
            analytics_with_platform = analytics.exclude(platform__isnull=True).exclude(platform='')
            
            if not analytics_with_platform.exists():
                logger.warning(f"No analytics with platform found for domain {domain.id} metric snapshots")
                return
            
            # Create snapshots per platform only (no aggregated snapshot)
            platforms = list(analytics_with_platform.values_list('platform', flat=True).distinct())
            
            logger.info(f"Creating domain metric snapshots for domain {domain.id}, {len(platforms)} platforms")
            
            for platform in platforms:
                if not platform:  # Skip None or empty platforms
                    continue
                    
                platform_analytics = analytics_with_platform.filter(platform=platform)
                
                if not platform_analytics.exists():
                    continue
                
                platform_totals = platform_analytics.aggregate(
                    total_mentions=Sum('total_mentions'),
                    total_citations=Sum('total_citations'),
                    avg_position=Avg('position'),
                    avg_sentiment=Avg('sentiment_score'),
                )
                
                platform_avg_pos = float(platform_totals['avg_position'] or 0)
                platform_visibility_score = self._calculate_visibility_score(platform_avg_pos)
                
                snapshot, created = DomainMetricSnapshot.objects.update_or_create(
                    domain=domain,
                    platform=platform,
                    snapshot_date=snapshot_date,
                    period_type=period_type,
                    defaults={
                        'mentions': platform_totals['total_mentions'] or 0,
                        'citations': platform_totals['total_citations'] or 0,
                        'visibility_score': platform_visibility_score,
                        'sentiment_score': float(platform_totals['avg_sentiment'] or 0),
                        'average_position': platform_avg_pos,
                    }
                )
                
                action = "Created" if created else "Updated"
                logger.debug(
                    f"{action} DomainMetricSnapshot for domain {domain.id}, "
                    f"platform {platform}, date {snapshot_date}: "
                    f"mentions={platform_totals['total_mentions'] or 0}, "
                    f"citations={platform_totals['total_citations'] or 0}"
                )
        except Exception as e:
            logger.error(f"Error creating domain metric snapshots: {str(e)}", exc_info=True)
    
    def _get_fallback_analytics(self, prompt_text: str, user_domain: str, platform: str) -> Dict[str, Any]:
        """Generate fallback analytics when AI platforms are unavailable"""
        return {
            'citations': 0,
            'mention_count': 0,
            'sentiment_score': 0.0,
            'context_summary': f"Fallback processing for {platform} - AI service unavailable"
        }