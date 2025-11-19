from typing import Dict, Any, List
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Avg, Count, Max, Q
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

            # Select one INIT group - process when domain has finished prompt generation
            # Domain must be in PROC (prompts ready) or COMP status
            group = (
                PromptGroup.objects.filter(
                    track_status='INIT',
                    domain__processing_status__in=['PROC', 'COMP']  # PROC = prompts ready, waiting for analytics
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

            # Process with each platform - get enabled platforms from settings (lowercase keys)
            platforms = getattr(settings, 'ENABLED_PLATFORMS', ['chatgpt'])
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

            # Create prompt metric snapshots and sentiment analytics immediately
            # This ensures records are created even if the group is not complete
            today = date.today()
            try:
                # Get analytics for this prompt (analytics are created with track_status='COMP')
                prompt_analytics = PromptAnalytics.objects.filter(
                    prompt=prompt
                )
                
                # Create prompt metric snapshots for this prompt
                if prompt_analytics.exists():
                    logger.info(f"Creating prompt metric snapshots for prompt {prompt_id}")
                    self._create_prompt_metric_snapshots(prompt_analytics, today, period_type='daily')
                    
                    # Update sentiment analytics for the theme if applicable
                    if group.theme:
                        logger.info(f"Updating sentiment analytics for theme '{group.theme}' after processing prompt {prompt_id}")
                        try:
                            self._update_sentiment_analytics_for_theme(group, prompt_analytics)
                        except Exception as sentiment_error:
                            logger.error(f"Error updating sentiment analytics for theme '{group.theme}': {str(sentiment_error)}", exc_info=True)
            except Exception as snapshot_error:
                logger.error(f"Error creating snapshots for prompt {prompt_id}: {str(snapshot_error)}", exc_info=True)
                # Don't fail the entire process if snapshots fail

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
                        # citation_count is now consistent: only domain URLs (same as citations list)
                        'total_citations': int(result.get('citation_count', 0) or 0),
                        'position': float(extracted_position or 0),
                        'sentiment_category': str(result.get('sentiment') or 'neutral'),
                        'sentiment_score': float(result.get('sentiment_score', 0.0) or 0.0),
                        'context_summary': result.get('context_summary') or result.get('response_text') or '',
                        'citation_list': result.get('citations') or [],
                        'competitor_mention_list': result.get('competitor_mention_list') or [],  # Save extracted competitors
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
            total_mentions = group_totals['total_mentions'] or 0
            total_citations = group_totals['total_citations'] or 0
            avg_sentiment = float(group_totals['avg_sentiment'] or 0)
            group_visibility_score = self._calculate_visibility_score(
                mentions=total_mentions,
                citations=total_citations,
                sentiment_score=avg_sentiment,
                average_position=avg_pos,
                scope='group'
            )
            group_sentiment_score = avg_sentiment

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
                # Filter for mentions and published analytics only
                domain_analytics = PromptAnalytics.objects.filter(
                    prompt__group__domain=domain,
                    prompt__track_status='COMP',
                    is_mention=True,
                    is_published=True
                )
                domain_totals = domain_analytics.aggregate(
                    total_citations=Sum('total_citations'),
                    total_mentions=Sum('total_mentions'),
                    avg_position=Avg('position'),
                    avg_sentiment=Avg('sentiment_score'),
                )
                
                # Calculate visibility score and sentiment score for domain
                domain_avg_pos = float(domain_totals['avg_position'] or 0)
                domain_total_mentions = domain_totals['total_mentions'] or 0
                domain_total_citations = domain_totals['total_citations'] or 0
                domain_avg_sentiment = float(domain_totals['avg_sentiment'] or 0)
                domain_visibility_score = self._calculate_visibility_score(
                    mentions=domain_total_mentions,
                    citations=domain_total_citations,
                    sentiment_score=domain_avg_sentiment,
                    average_position=domain_avg_pos,
                    scope='domain'
                )
                domain_sentiment_score = domain_avg_sentiment
                
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
                    logger.info(f"About to create domain metric snapshots for domain {domain.id}, date {today}")
                    logger.info(f"Domain analytics count: {domain_analytics.count()}")
                    self._create_domain_metric_snapshots(domain, domain_analytics, today, period_type='daily')
                    logger.info(f"Successfully completed domain metric snapshots for domain {domain.id}")
                except Exception as domain_snapshot_error:
                    logger.error(f"Error creating domain metric snapshots for domain {domain.id}: {str(domain_snapshot_error)}", exc_info=True)
                    # Don't re-raise here - let the process continue even if snapshots fail
                
                # Create metric snapshots for individual prompts (daily by default)
                # Use domain_analytics to get all prompts in the domain, not just the current group
                try:
                    logger.info(f"About to call _create_prompt_metric_snapshots with {domain_analytics.count()} analytics")
                    self._create_prompt_metric_snapshots(domain_analytics, today, period_type='daily')
                    logger.info(f"Completed _create_prompt_metric_snapshots call")
                except Exception as prompt_snapshot_error:
                    logger.error(f"Error creating prompt metric snapshots: {str(prompt_snapshot_error)}", exc_info=True)

            logger.info(f"Successfully aggregated group {group.id} and domain {domain.id}")

            # DISABLED: Competitor extraction is now manual via "Start Analysing" button
            # Extract top competitors after domain analytics are complete
            # try:
            #     from .competitor_extractor import extract_competitors_for_domain
            #     created_count, competitor_names = extract_competitors_for_domain(domain.id)
            #     if created_count > 0:
            #         logger.info(f"Auto-extracted {created_count} competitors for domain {domain.id}: {', '.join(competitor_names)}")
            #     else:
            #         logger.info(f"No new competitors extracted for domain {domain.id} (insufficient data or already exists)")
            # except Exception as comp_error:
            #     logger.error(f"Error extracting competitors for domain {domain.id}: {str(comp_error)}")
            #     # Don't fail the entire aggregation if competitor extraction fails

            # Check if ALL groups for this domain are now complete
            # If so, mark the domain as COMP
            self._check_and_complete_domain(domain)

        except Exception as e:
            logger.error(f"Error aggregating group {group.id}: {str(e)}")

    def _check_and_complete_domain(self, domain: Domain) -> None:
        """
        Check if all prompt groups for this domain are complete.
        If so, mark the domain as COMP (completed).
        """
        try:
            # Count total groups and completed groups
            total_groups = PromptGroup.objects.filter(domain=domain).count()
            completed_groups = PromptGroup.objects.filter(domain=domain, track_status='COMP').count()

            logger.info(f"Domain {domain.id} ({domain.name}): {completed_groups}/{total_groups} groups completed")

            # If all groups are completed, mark domain as COMP
            if total_groups > 0 and completed_groups == total_groups:
                with transaction.atomic():
                    domain_fresh = Domain.objects.select_for_update().get(id=domain.id)

                    # Only update if still in PROC status
                    if domain_fresh.processing_status == 'PROC':
                        domain_fresh.processing_status = 'COMP'
                        domain_fresh.track_message = f'Successfully completed all analytics for {total_groups} prompt groups'
                        domain_fresh.tracked_at = timezone.now()
                        domain_fresh.save(update_fields=['processing_status', 'track_message', 'tracked_at', 'modified_at'])

                        logger.info(f"✅ Domain {domain.id} ({domain.name}) marked as COMP - all {total_groups} groups completed")
                    else:
                        logger.info(f"Domain {domain.id} already in status {domain_fresh.processing_status}, skipping")
            else:
                # Still have pending groups
                pending_groups = total_groups - completed_groups
                logger.info(f"Domain {domain.id} still processing: {pending_groups} groups remaining")

        except Exception as e:
            logger.error(f"Error checking domain completion for domain {domain.id}: {str(e)}")

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
            total_mentions = totals['total_mentions'] or 0
            total_citations = totals['total_citations'] or 0
            avg_sentiment = float(totals['avg_sentiment'] or 0)
            visibility_score = self._calculate_visibility_score(
                mentions=total_mentions,
                citations=total_citations,
                sentiment_score=avg_sentiment,
                average_position=avg_pos,
                scope='domain'
            )
            
            # NOTE: We no longer create overall aggregation records with platform=None
            # Only platform-specific records with valid platform names are created
            
            # Create platform-wise sentiment analytics
            # Get all distinct platforms from analytics (including those with whitespace)
            platforms_raw = analytics_qs.exclude(
                platform__isnull=True
            ).exclude(
                platform=''
            ).values_list('platform', flat=True).distinct()
            
            # Normalize platforms: strip whitespace and filter out empty/whitespace-only
            # Create a mapping of normalized -> original for filtering
            platform_map = {}  # normalized -> list of original values
            for platform_raw in platforms_raw:
                # Skip None, empty strings, and non-string values
                if not platform_raw or not isinstance(platform_raw, str):
                    logger.warning(f"Skipping invalid platform_raw for theme '{theme}': {repr(platform_raw)}")
                    continue
                
                # Normalize: strip whitespace
                platform_normalized = platform_raw.strip()
                
                # Only add non-empty normalized platforms
                if platform_normalized and len(platform_normalized) > 0:
                    if platform_normalized not in platform_map:
                        platform_map[platform_normalized] = []
                    # Only add original if it's also non-empty
                    if platform_raw and platform_raw.strip() and platform_raw not in platform_map[platform_normalized]:
                        platform_map[platform_normalized].append(platform_raw)
            
            # CRITICAL: If no valid platforms found, do not create any records
            if not platform_map:
                logger.warning(f"No valid platforms found for theme '{theme}'. Skipping SentimentAnalytics creation.")
                return
            
            # Process each normalized platform
            for platform_normalized, original_platforms in platform_map.items():
                # Skip if platform is empty after normalization
                if not platform_normalized or not platform_normalized.strip():
                    continue
                
                # Filter analytics using original platform values (to match database records)
                # Use Q objects to match any of the original platform values
                # Only include non-empty original platforms in the filter
                platform_filter = Q()
                valid_original_platforms = []
                for orig_platform in original_platforms:
                    # Validate original platform is non-empty
                    if orig_platform and isinstance(orig_platform, str) and orig_platform.strip():
                        platform_filter |= Q(platform=orig_platform)
                        valid_original_platforms.append(orig_platform)
                
                # Skip if no valid original platforms found
                if not valid_original_platforms:
                    logger.warning(f"Skipping SentimentAnalytics creation for theme '{theme}': no valid original platforms for normalized '{platform_normalized}'")
                    continue
                
                platform_analytics = analytics_qs.filter(
                    platform_filter,
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
                platform_total_mentions = platform_totals['total_mentions'] or 0
                platform_total_citations = platform_totals['total_citations'] or 0
                platform_avg_sentiment = float(platform_totals['avg_sentiment'] or 0)
                platform_visibility_score = self._calculate_visibility_score(
                    mentions=platform_total_mentions,
                    citations=platform_total_citations,
                    sentiment_score=platform_avg_sentiment,
                    average_position=platform_avg_pos,
                    scope='domain'
                )
                
                # Validate platform: must be a non-empty string (not None, not empty, not whitespace-only)
                # This is a final safety check to ensure we never store empty platforms
                if not platform_normalized or not isinstance(platform_normalized, str):
                    logger.warning(f"Skipping SentimentAnalytics creation for theme '{theme}': platform is None or not a string")
                    continue
                
                platform_value = platform_normalized.strip()
                
                # Final validation: platform must be a non-empty string after stripping
                # CRITICAL: Do not create records with empty platforms - only create if platform is valid
                if not platform_value or len(platform_value) == 0 or not platform_value.strip():
                    logger.warning(f"Skipping SentimentAnalytics creation for theme '{theme}': platform is empty after normalization")
                    continue
                
                # ABSOLUTE FINAL CHECK: Ensure platform_value is a valid, non-empty string before saving
                # This prevents any edge case where an empty string might slip through
                if platform_value is None or (isinstance(platform_value, str) and (not platform_value or not platform_value.strip())):
                    logger.error(f"CRITICAL: Attempted to create SentimentAnalytics with invalid platform for theme '{theme}'. Skipping.")
                    continue
                
                # FINAL SAFETY CHECK: Double-check platform_value is not None or empty before database operation
                # This is the last line of defense before creating the record
                if not platform_value or platform_value is None or (isinstance(platform_value, str) and len(platform_value.strip()) == 0):
                    logger.error(f"CRITICAL: platform_value is None or empty for theme '{theme}'. Aborting record creation.")
                    continue
                
                # ABSOLUTE FINAL CHECK: Ensure platform_value is a valid string before database operation
                # Convert to string and strip to ensure it's not None or empty
                platform_final = str(platform_value).strip() if platform_value else None
                if not platform_final or len(platform_final) == 0:
                    logger.error(f"CRITICAL: platform_final is None or empty after conversion for theme '{theme}'. Aborting record creation.")
                    continue
                
                # Only create records with valid, non-empty platform values
                # Platform must be a real platform name (e.g., 'ChatGPT', 'Google Gemini', 'Perplexity')
                # Never create records with None, empty string, or whitespace-only platforms
                # CRITICAL: platform_final is guaranteed to be a non-empty string at this point
                try:
                    SentimentAnalytics.objects.update_or_create(
                        domain=domain,
                        theme=theme,
                        platform=platform_final,  # Use final validated platform value (guaranteed non-empty string, never None)
                        snapshot_date=today,
                        period_type='daily',
                        defaults={
                            'positive_percentage': round(platform_positive_pct, 2),
                            'neutral_percentage': round(platform_neutral_pct, 2),
                            'negative_percentage': round(platform_negative_pct, 2),
                            'mention_count': platform_total,
                            'mentions': platform_total_mentions,
                            'citations': platform_total_citations,
                            'visibility_score': platform_visibility_score,
                            'sentiment_score': platform_avg_sentiment,
                            'average_position': platform_avg_pos,
                        }
                    )
                except ValueError as e:
                    # Catch ValueError from model's save() method if platform is None or empty
                    logger.error(f"CRITICAL: ValueError caught when creating SentimentAnalytics for theme '{theme}': {str(e)}")
                    logger.error(f"  platform_final value: {repr(platform_final)}")
                    continue
            
            # Log platform-specific records created
            logger.info(
                f"Created platform-specific SentimentAnalytics for theme '{theme}': "
                f"Pos={positive_pct:.1f}%, Neu={neutral_pct:.1f}%, Neg={negative_pct:.1f}%, "
                f"Mentions={total}"
            )
            
        except Exception as e:
            logger.error(f"Error updating sentiment analytics for theme '{group.theme}': {str(e)}")
    
    def _calculate_visibility_score(
        self, 
        mentions: int = 0,
        citations: int = 0,
        sentiment_score: float = 0.0,
        average_position: float = 0.0,
        scope: str = 'domain'
    ) -> Decimal:
        """
        Calculate visibility score using weighted formula.
        
        Formula: weighted_score = (
            0.4 * norm_mentions +
            0.3 * norm_citations +
            0.2 * norm_sentiment +
            0.1 * norm_position
        ) * 100
        
        Weights:
        - Mentions: 40% (biggest driver - frequency)
        - Citations: 30% (authority/trust)
        - Sentiment: 20% (perception quality)
        - Position: 10% (ranking adjustment)
        
        Args:
            mentions: Total mentions count
            citations: Total citations count
            sentiment_score: Average sentiment score (-1.0 to 1.0)
            average_position: Average position in results
            scope: Normalization scope ('domain', 'group', 'snapshot')
        
        Returns:
            Decimal: Visibility score (0-100)
        """
        # Fetch normalization limits based on scope
        # Convert to float to avoid Decimal/float division issues
        if scope == 'domain':
            # Normalize across all domains
            max_mentions = float(Domain.objects.aggregate(Max('total_mentions'))['total_mentions__max'] or 1)
            max_citations = float(Domain.objects.aggregate(Max('total_citations'))['total_citations__max'] or 1)
            max_position = float(Domain.objects.aggregate(Max('average_position'))['average_position__max'] or 1)
        elif scope == 'group':
            # Normalize across all groups in the same domain (will need domain_id passed)
            # For now, use domain normalization
            max_mentions = float(Domain.objects.aggregate(Max('total_mentions'))['total_mentions__max'] or 1)
            max_citations = float(Domain.objects.aggregate(Max('total_citations'))['total_citations__max'] or 1)
            max_position = float(Domain.objects.aggregate(Max('average_position'))['average_position__max'] or 1)
        else:  # snapshot
            # For snapshots, use domain normalization
            max_mentions = float(Domain.objects.aggregate(Max('total_mentions'))['total_mentions__max'] or 1)
            max_citations = float(Domain.objects.aggregate(Max('total_citations'))['total_citations__max'] or 1)
            max_position = float(Domain.objects.aggregate(Max('average_position'))['average_position__max'] or 1)
        
        # Ensure all values are float for division operations
        mentions_float = float(mentions) if mentions else 0.0
        citations_float = float(citations) if citations else 0.0
        sentiment_float = float(sentiment_score) if sentiment_score else 0.0
        position_float = float(average_position) if average_position else 0.0
        
        # Normalize components (0-1 range)
        norm_mentions = mentions_float / max_mentions if max_mentions > 0 else 0.0
        norm_citations = citations_float / max_citations if max_citations > 0 else 0.0
        norm_sentiment = (sentiment_float + 1.0) / 2.0  # Convert -1 to 1 range to 0-1 range
        norm_position = 1.0 - (position_float / max_position) if max_position > 0 and position_float > 0 else 1.0
        
        # Clamp normalized values to 0-1
        norm_mentions = max(0, min(1, norm_mentions))
        norm_citations = max(0, min(1, norm_citations))
        norm_sentiment = max(0, min(1, norm_sentiment))
        norm_position = max(0, min(1, norm_position))
        
        # Weighted score
        weighted_score = (
            0.4 * norm_mentions +
            0.3 * norm_citations +
            0.2 * norm_sentiment +
            0.1 * norm_position
        )
        
        # Scale to 0-100
        visibility_score = round(weighted_score * 100, 2)
        return Decimal(str(visibility_score))
    
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
                    platform_total_mentions = platform_totals['total_mentions'] or 0
                    platform_total_citations = platform_totals['total_citations'] or 0
                    platform_avg_sentiment = float(platform_totals['avg_sentiment'] or 0)
                    platform_visibility_score = self._calculate_visibility_score(
                        mentions=platform_total_mentions,
                        citations=platform_total_citations,
                        sentiment_score=platform_avg_sentiment,
                        average_position=platform_avg_pos,
                        scope='snapshot'
                    )
                    
                    metrics = {
                        'mentions': platform_total_mentions,
                        'citations': platform_total_citations,
                        'visibility_score': platform_visibility_score,
                        'sentiment_score': platform_avg_sentiment,
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
                platform_total_mentions = platform_totals['total_mentions'] or 0
                platform_total_citations = platform_totals['total_citations'] or 0
                platform_avg_sentiment = float(platform_totals['avg_sentiment'] or 0)
                platform_visibility_score = self._calculate_visibility_score(
                    mentions=platform_total_mentions,
                    citations=platform_total_citations,
                    sentiment_score=platform_avg_sentiment,
                    average_position=platform_avg_pos,
                    scope='snapshot'
                )
                
                snapshot, created = PromptGroupMetricSnapshot.objects.update_or_create(
                    prompt_group=group,
                    platform=platform,
                    snapshot_date=snapshot_date,
                    period_type=period_type,
                    defaults={
                        'mentions': platform_total_mentions,
                        'citations': platform_total_citations,
                        'visibility_score': platform_visibility_score,
                        'sentiment_score': platform_avg_sentiment,
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
            # Log initial state
            total_analytics = analytics.count()
            logger.info(f"Creating domain metric snapshots for domain {domain.id}, date {snapshot_date}, period_type {period_type}")
            logger.info(f"Total analytics passed: {total_analytics}")
            
            # Filter out analytics with no platform
            analytics_with_platform = analytics.exclude(platform__isnull=True).exclude(platform='')
            analytics_with_platform_count = analytics_with_platform.count()
            
            logger.info(f"Analytics with platform: {analytics_with_platform_count} (out of {total_analytics})")
            
            if not analytics_with_platform.exists():
                logger.warning(f"No analytics with platform found for domain {domain.id} metric snapshots")
                # Log sample platforms to help debug
                sample_platforms = list(analytics.values_list('platform', flat=True).distinct()[:10])
                logger.warning(f"Sample platforms in analytics (may include None/empty): {sample_platforms}")
                return
            
            # Create snapshots per platform only (no aggregated snapshot)
            platforms = list(analytics_with_platform.values_list('platform', flat=True).distinct())
            
            logger.info(f"Creating domain metric snapshots for domain {domain.id}, {len(platforms)} platforms: {platforms}")
            
            created_count = 0
            updated_count = 0
            
            for platform in platforms:
                if not platform:  # Skip None or empty platforms
                    logger.warning(f"Skipping empty platform for domain {domain.id}")
                    continue
                    
                platform_analytics = analytics_with_platform.filter(platform=platform)
                platform_analytics_count = platform_analytics.count()
                
                if not platform_analytics.exists():
                    logger.warning(f"No analytics found for platform {platform} in domain {domain.id}")
                    continue
                
                logger.debug(f"Processing platform {platform} with {platform_analytics_count} analytics")
                
                platform_totals = platform_analytics.aggregate(
                    total_mentions=Sum('total_mentions'),
                    total_citations=Sum('total_citations'),
                    avg_position=Avg('position'),
                    avg_sentiment=Avg('sentiment_score'),
                )
                
                platform_avg_pos = float(platform_totals['avg_position'] or 0)
                platform_total_mentions = platform_totals['total_mentions'] or 0
                platform_total_citations = platform_totals['total_citations'] or 0
                platform_avg_sentiment = float(platform_totals['avg_sentiment'] or 0)
                
                logger.debug(
                    f"Platform {platform} totals: mentions={platform_total_mentions}, "
                    f"citations={platform_total_citations}, avg_position={platform_avg_pos}, "
                    f"avg_sentiment={platform_avg_sentiment}"
                )
                
                platform_visibility_score = self._calculate_visibility_score(
                    mentions=platform_total_mentions,
                    citations=platform_total_citations,
                    sentiment_score=platform_avg_sentiment,
                    average_position=platform_avg_pos,
                    scope='snapshot'
                )
                
                try:
                    snapshot, created = DomainMetricSnapshot.objects.update_or_create(
                        domain=domain,
                        platform=platform,
                        snapshot_date=snapshot_date,
                        period_type=period_type,
                        defaults={
                            'mentions': platform_total_mentions,
                            'citations': platform_total_citations,
                            'visibility_score': platform_visibility_score,
                            'sentiment_score': platform_avg_sentiment,
                            'average_position': platform_avg_pos,
                        }
                    )
                    
                    if created:
                        created_count += 1
                        action = "Created"
                    else:
                        updated_count += 1
                        action = "Updated"
                    
                    logger.info(
                        f"{action} DomainMetricSnapshot for domain {domain.id}, "
                        f"platform {platform}, date {snapshot_date}, period_type {period_type}: "
                        f"mentions={platform_total_mentions}, "
                        f"citations={platform_total_citations}, "
                        f"visibility_score={platform_visibility_score}"
                    )
                except Exception as db_error:
                    logger.error(
                        f"Database error creating DomainMetricSnapshot for domain {domain.id}, "
                        f"platform {platform}, date {snapshot_date}: {str(db_error)}",
                        exc_info=True
                    )
                    raise
            
            logger.info(
                f"Completed domain metric snapshots for domain {domain.id}, date {snapshot_date}: "
                f"{created_count} created, {updated_count} updated"
            )
            
        except Exception as e:
            logger.error(f"Error creating domain metric snapshots for domain {domain.id}: {str(e)}", exc_info=True)
            raise  # Re-raise to ensure the error is visible
    
    def _get_fallback_analytics(self, prompt_text: str, user_domain: str, platform: str) -> Dict[str, Any]:
        """Generate fallback analytics when AI platforms are unavailable"""
        return {
            'citations': [],
            'mention_count': 0,
            'sentiment': 'neutral',
            'sentiment_score': 0.0,
            'context_summary': f"Fallback processing for {platform} - AI service unavailable",
            'citation_count': 0,
            'has_citation': False,
            'all_urls': [],
            'competitor_mention_list': [],  # Include empty list for consistency
            'is_mention': False
        }