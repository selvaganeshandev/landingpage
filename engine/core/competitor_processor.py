"""
Competitor Processing Module
Handles end-to-end competitor tracking and analytics

Flow:
1. Competitor created with track_status='INIT'
2. Schedule_tick picks up INIT competitors
3. Links all prompts with completed PromptAnalytics to competitor (creates CompetitorPromptAnalytics records)
4. Extracts competitor mentions from existing PromptAnalytics.context_summary (no new API calls)
5. Aggregates results into Competitor and ShareOfVoiceAnalytics

Note: Uses existing PromptAnalytics data instead of making new API calls to save costs and ensure consistency.
"""

import logging
from typing import Dict, Any, List
from datetime import date, datetime
from decimal import Decimal

from django.db import transaction
from django.db.models import Avg, Sum, Count, Q
from django.utils import timezone
from django.conf import settings

from shared_models.models import (
    Competitor,
    CompetitorPromptAnalytics,
    CompetitorAnalytics,
    CompetitorMetricSnapshot,
    ShareOfVoiceAnalytics,
    Domain,
    Prompt,
    PromptAnalytics
)


logger = logging.getLogger(__name__)


class CompetitorProcessor:
    """
    Processes competitors and generates analytics by testing how competitors appear
    in AI responses to prompts.
    
    Similar to PromptAnalyticsProcessor but focused on competitor visibility.
    """
    
    def __init__(self, max_concurrent_prompts: int = 10):
        """
        Initialize the competitor processor
        
        Args:
            max_concurrent_prompts: Max number of prompts to process per competitor at once
        """
        self.max_concurrent_prompts = max_concurrent_prompts
        logger.info(f"CompetitorProcessor initialized with max_concurrent_prompts={max_concurrent_prompts}")
    
    def process_competitor(self, competitor: Competitor) -> Dict[str, Any]:
        """
        Process a specific competitor. This is the main entry point for processing a single competitor.
        
        Args:
            competitor: Competitor instance to process
        
        Returns:
            dict: Status information about the processing result
        """
        try:
            # Check if competitor can be processed
            if competitor.track_status not in ['INIT', 'FAIL', 'COMP']:
                return {
                    'scheduled': False,
                    'reason': 'invalid_status',
                    'error': f'Competitor is in status {competitor.track_status}. Cannot process.',
                    'current_status': competitor.track_status
                }
            
            # Reset if COMP (allow reprocessing)
            if competitor.track_status == 'COMP':
                with transaction.atomic():
                    competitor = Competitor.objects.select_for_update().get(id=competitor.id)
                    competitor.track_status = 'INIT'
                    competitor.track_message = 'Resetting for reprocessing'
                    competitor.save(update_fields=['track_status', 'track_message', 'modified_at'])
            
            # Link prompts and schedule processing
            with transaction.atomic():
                competitor = Competitor.objects.select_for_update().get(id=competitor.id)
                competitor.track_status = 'SCHD'
                competitor.track_message = f"Scheduled for processing at {timezone.now()}"
                competitor.save(update_fields=['track_status', 'track_message', 'modified_at'])
            
            logger.info(f"Scheduled competitor {competitor.id} ({competitor.name}) for processing")
            
            # Link prompts to competitor
            self._link_prompts_to_competitor(competitor)
            
            # Mark as processing and start actual work
            with transaction.atomic():
                competitor = Competitor.objects.select_for_update().get(id=competitor.id)
                competitor.track_status = 'PROC'
                competitor.track_message = "Processing competitor analytics"
                competitor.save(update_fields=['track_status', 'track_message', 'modified_at'])
            
            # Process prompts
            try:
                self._process_competitor_prompts(competitor)
                
                # Check if we have any completed analytics before marking as COMP
                completed_count = CompetitorPromptAnalytics.objects.filter(
                    competitor=competitor,
                    track_status='COMP'
                ).count()
                
                failed_count = CompetitorPromptAnalytics.objects.filter(
                    competitor=competitor,
                    track_status='FAIL'
                ).count()
                
                total_count = CompetitorPromptAnalytics.objects.filter(
                    competitor=competitor
                ).count()
                
                # Mark as complete even if some failed (partial success is still success)
                with transaction.atomic():
                    competitor = Competitor.objects.select_for_update().get(id=competitor.id)
                    competitor.track_status = 'COMP'
                    competitor.track_message = f"Completed at {timezone.now()}. Processed {completed_count}/{total_count} prompts successfully."
                    competitor.tracked_at = timezone.now()
                    competitor.save(update_fields=['track_status', 'track_message', 'tracked_at', 'modified_at'])
                
                logger.info(f"Successfully completed competitor {competitor.id}: {completed_count} succeeded, {failed_count} failed out of {total_count} total")
                return {
                    'scheduled': True,
                    'competitor_id': competitor.id,
                    'competitor_name': competitor.name,
                    'status': 'completed',
                    'processed': completed_count,
                    'failed': failed_count,
                    'total': total_count
                }
                
            except Exception as processing_error:
                logger.error(f"Error processing competitor {competitor.id}: {str(processing_error)}", exc_info=True)
                with transaction.atomic():
                    competitor = Competitor.objects.select_for_update().get(id=competitor.id)
                    competitor.track_status = 'FAIL'
                    competitor.track_message = f"Processing failed: {str(processing_error)}"
                    competitor.save(update_fields=['track_status', 'track_message', 'modified_at'])
                
                return {
                    'scheduled': True,
                    'competitor_id': competitor.id,
                    'status': 'failed',
                    'error': str(processing_error)
                }
        
        except Exception as e:
            logger.error(f"Error in process_competitor: {str(e)}", exc_info=True)
            return {'scheduled': False, 'reason': 'error', 'error': str(e)}
    
    def schedule_tick(self) -> Dict[str, Any]:
        """
        Main scheduling method - picks one INIT competitor and processes it.
        
        Returns:
            dict: Status information about what was scheduled
        """
        try:
            # If a competitor is in progress, skip scheduling
            if Competitor.objects.filter(track_status='SCHD').exists():
                return {'scheduled': False, 'reason': 'competitor_in_progress'}
            
            # Select one INIT competitor
            competitor = (
                Competitor.objects.filter(track_status='INIT')
                .select_related('domain')
                .order_by('modified_at')
                .first()
            )
            if competitor is None:
                return {'scheduled': False, 'reason': 'no_init_competitor'}
            
            # Use the process_competitor method
            return self.process_competitor(competitor)
        
        except Exception as e:
            logger.error(f"Error in schedule_tick: {str(e)}", exc_info=True)
            return {'scheduled': False, 'reason': 'error', 'error': str(e)}
    
    def _link_prompts_to_competitor(self, competitor: Competitor) -> int:
        """
        Link all prompts with completed analytics from competitor's domain to this competitor.
        Only links prompts that have completed PromptAnalytics (track_status='COMP').
        Creates CompetitorPromptAnalytics records with status='INIT'.
        
        Args:
            competitor: Competitor instance
        
        Returns:
            int: Number of prompts linked
        """
        try:
            # Ensure competitor.domain is loaded (not lazy)
            domain = competitor.domain
            if domain is None:
                raise ValueError(f"Competitor {competitor.id} has no domain assigned")
            
            # Get domain ID to ensure we're using the correct reference
            domain_id = domain.id if hasattr(domain, 'id') else domain
            
            # Get all prompts for this domain that have completed analytics
            # Note: Prompt doesn't have domain field directly, it's through group.domain
            # First, get all prompts for the domain
            domain_prompts = Prompt.objects.filter(
                group__domain_id=domain_id
            ).select_related('group').distinct()
            
            logger.info(f"Found {domain_prompts.count()} prompts for domain {domain_id}")
            
            # Then filter to only those with completed analytics
            prompts_with_analytics = []
            for prompt in domain_prompts:
                # Check if this prompt has any completed PromptAnalytics
                has_completed_analytics = PromptAnalytics.objects.filter(
                    prompt=prompt,
                    track_status='COMP'
                ).exists()
                
                if has_completed_analytics:
                    prompts_with_analytics.append(prompt)
            
            logger.info(f"Found {len(prompts_with_analytics)} prompts with completed analytics for domain {domain_id}")
            
            created_count = 0
            skipped_count = 0
            with transaction.atomic():
                for prompt in prompts_with_analytics:
                    # Ensure prompt is a Prompt instance
                    if not isinstance(prompt, Prompt):
                        logger.error(f"Invalid prompt object: {type(prompt)}, skipping")
                        skipped_count += 1
                        continue
                    
                    # Create CompetitorPromptAnalytics if not exists
                    try:
                        _, created = CompetitorPromptAnalytics.objects.get_or_create(
                            competitor=competitor,
                            prompt=prompt,
                            defaults={
                                'track_status': 'INIT',
                                'track_message': 'Ready for processing',
                                'platform': 'ChatGPT',  # Default platform
                            }
                        )
                        if created:
                            created_count += 1
                    except Exception as create_error:
                        logger.error(f"Error creating CompetitorPromptAnalytics for prompt {prompt.id}: {str(create_error)}")
                        skipped_count += 1
            
            logger.info(f"Linked {created_count} new prompts (with completed analytics) to competitor {competitor.id}, skipped {skipped_count}")
            return created_count
        
        except Exception as e:
            logger.error(f"Error linking prompts to competitor {competitor.id}: {str(e)}")
            raise
    
    def _process_competitor_prompts(self, competitor: Competitor) -> None:
        """
        Process all INIT prompts for this competitor.
        Uses existing PromptAnalytics data instead of making new API calls.
        
        Args:
            competitor: Competitor instance
        """
        try:
            # Get all INIT competitor-prompt pairs (process all, not just first batch)
            competitor_prompts = CompetitorPromptAnalytics.objects.filter(
                competitor=competitor,
                track_status='INIT'
            ).select_related('prompt', 'competitor')
            
            total_count = competitor_prompts.count()
            if total_count == 0:
                logger.info(f"No INIT prompts found for competitor {competitor.id}")
                # Still try to aggregate if there are any completed ones
                self._aggregate_competitor_analytics(competitor)
                return
            
            logger.info(f"Processing {total_count} prompts for competitor {competitor.id}")
            
            # Process in batches
            processed_count = 0
            failed_count = 0
            
            for comp_prompt in competitor_prompts:
                try:
                    # Mark as scheduled
                    with transaction.atomic():
                        cp = CompetitorPromptAnalytics.objects.select_for_update().get(id=comp_prompt.id)
                        if cp.track_status != 'INIT':
                            logger.warning(f"CompetitorPromptAnalytics {cp.id} is not INIT (status: {cp.track_status}), skipping")
                            continue
                        cp.track_status = 'SCHD'
                        cp.track_message = "Scheduled for processing"
                        cp.save(update_fields=['track_status', 'track_message', 'modified_at'])
                    
                    # Process this prompt-competitor pair
                    self._process_single_competitor_prompt(comp_prompt)
                    processed_count += 1
                    
                except Exception as prompt_error:
                    failed_count += 1
                    logger.error(f"Error processing competitor-prompt {comp_prompt.id}: {str(prompt_error)}", exc_info=True)
                    # Mark as failed
                    try:
                        with transaction.atomic():
                            cp = CompetitorPromptAnalytics.objects.select_for_update().get(id=comp_prompt.id)
                            cp.track_status = 'FAIL'
                            cp.track_message = f"Failed: {str(prompt_error)}"
                            cp.save(update_fields=['track_status', 'track_message', 'modified_at'])
                    except Exception as save_error:
                        logger.error(f"Failed to save error status for competitor-prompt {comp_prompt.id}: {str(save_error)}")
            
            logger.info(f"Completed processing for competitor {competitor.id}: {processed_count} succeeded, {failed_count} failed out of {total_count} total")
            
            # Aggregate after all prompts processed (even if some failed)
            self._aggregate_competitor_analytics(competitor)
            
        except Exception as e:
            logger.error(f"Error processing competitor prompts for {competitor.id}: {str(e)}", exc_info=True)
            raise
    
    def _process_single_competitor_prompt(self, comp_prompt: CompetitorPromptAnalytics) -> None:
        """
        Process a single competitor-prompt pair.
        Uses existing PromptAnalytics data instead of making new API calls.
        
        Args:
            comp_prompt: CompetitorPromptAnalytics instance
        """
        try:
            # Mark as processing
            with transaction.atomic():
                cp = CompetitorPromptAnalytics.objects.select_for_update().get(id=comp_prompt.id)
                cp.track_status = 'PROC'
                cp.track_message = "Extracting from existing analytics"
                cp.save(update_fields=['track_status', 'track_message', 'modified_at'])
            
            # Get existing PromptAnalytics for this prompt
            # Try to get the most recent completed analytics with context_summary
            prompt_analytics = PromptAnalytics.objects.filter(
                prompt=comp_prompt.prompt,
                track_status='COMP'  # Only use completed analytics
            ).exclude(
                context_summary__isnull=True
            ).exclude(
                context_summary=''
            ).order_by('-tracked_at', '-created_at').first()
            
            # If no analytics with context_summary, try any completed analytics
            if not prompt_analytics:
                prompt_analytics = PromptAnalytics.objects.filter(
                    prompt=comp_prompt.prompt,
                    track_status='COMP'
                ).order_by('-tracked_at', '-created_at').first()
            
            if not prompt_analytics:
                raise ValueError(f"No completed PromptAnalytics found for prompt {comp_prompt.prompt.id} (prompt text: {comp_prompt.prompt.prompt[:50]}...)")
            
            # Use existing context_summary from PromptAnalytics
            response_text = prompt_analytics.context_summary or ''
            
            # If context_summary is empty, try to use response_text or other fields
            if not response_text:
                # Check if there's any text we can use
                # Some analytics might have the response in a different field
                logger.warning(f"PromptAnalytics {prompt_analytics.id} has empty context_summary for prompt {comp_prompt.prompt.id}")
                # Still proceed but with empty text - competitor won't be found, which is correct
                response_text = ''
            
            competitor_name = comp_prompt.competitor.name
            
            # Analyze competitor presence in existing response
            analytics = self._analyze_competitor_mention(
                response_text=response_text,
                competitor_name=competitor_name,
                competitor_url=comp_prompt.competitor.url
            )
            
            # Update CompetitorPromptAnalytics with results
            with transaction.atomic():
                cp = CompetitorPromptAnalytics.objects.select_for_update().get(id=comp_prompt.id)
                cp.track_status = 'COMP'
                cp.track_message = "Completed successfully (using existing analytics)"
                cp.tracked_at = timezone.now()
                cp.is_mentioned = analytics['is_mentioned']
                cp.position = analytics['position']
                cp.mention_count = analytics['mention_count']
                cp.sentiment_category = analytics['sentiment_category']
                cp.sentiment_score = analytics['sentiment_score']
                cp.response_text = response_text  # Store the context_summary we used
                cp.citation_list = prompt_analytics.citation_list  # Reuse citations from PromptAnalytics
                cp.platform = prompt_analytics.platform  # Use same platform as PromptAnalytics
                cp.save()
            
            logger.info(f"Completed competitor-prompt {comp_prompt.id}: mentioned={analytics['is_mentioned']}, position={analytics['position']} (from existing analytics)")
        
        except Exception as e:
            logger.error(f"Error processing competitor-prompt {comp_prompt.id}: {str(e)}")
            with transaction.atomic():
                cp = CompetitorPromptAnalytics.objects.select_for_update().get(id=comp_prompt.id)
                cp.track_status = 'FAIL'
                cp.track_message = f"Failed: {str(e)}"
                cp.save(update_fields=['track_status', 'track_message', 'modified_at'])
            raise
    
    def _analyze_competitor_mention(
        self, 
        response_text: str, 
        competitor_name: str, 
        competitor_url: str
    ) -> Dict[str, Any]:
        """
        Analyze if and how a competitor is mentioned in the AI response.
        
        Args:
            response_text: Full AI response text
            competitor_name: Name of the competitor
            competitor_url: URL of the competitor
        
        Returns:
            dict: Analytics data about competitor mention
        """
        # Simple keyword-based detection (can be enhanced with NLP)
        response_lower = response_text.lower()
        competitor_lower = competitor_name.lower()
        
        is_mentioned = competitor_lower in response_lower
        mention_count = response_lower.count(competitor_lower)
        
        # Find position (which numbered item in a list)
        position = None
        if is_mentioned:
            # Try to find position in numbered lists
            lines = response_text.split('\n')
            for i, line in enumerate(lines):
                if competitor_lower in line.lower():
                    # Extract number if present (e.g., "1. CompetitorName" -> 1)
                    import re
                    match = re.match(r'^\s*(\d+)', line)
                    if match:
                        position = int(match.group(1))
                        break
        
        # Extract citations (URLs or references)
        citations = []
        if is_mentioned:
            import re
            # Find URLs near competitor mentions
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
            urls = re.findall(url_pattern, response_text)
            citations = [url for url in urls if competitor_lower in url.lower() or 'citation' in url.lower()]
        
        # Simple sentiment analysis (can be enhanced with AI)
        sentiment_category = 'neutral'
        sentiment_score = 0.0
        
        if is_mentioned:
            # Check for positive words nearby
            positive_words = ['best', 'great', 'excellent', 'top', 'leading', 'premier', 'quality']
            negative_words = ['poor', 'worst', 'bad', 'inferior', 'low-quality']
            
            positive_count = sum(1 for word in positive_words if word in response_lower)
            negative_count = sum(1 for word in negative_words if word in response_lower)
            
            if positive_count > negative_count:
                sentiment_category = 'positive'
                sentiment_score = 0.5
            elif negative_count > positive_count:
                sentiment_category = 'negative'
                sentiment_score = -0.5
        
        return {
            'is_mentioned': is_mentioned,
            'position': position,
            'mention_count': mention_count,
            'sentiment_category': sentiment_category,
            'sentiment_score': Decimal(str(sentiment_score)),
            'citations': citations
        }
    
    def _aggregate_competitor_analytics(self, competitor: Competitor) -> None:
        """
        Aggregate all CompetitorPromptAnalytics data into:
        1. Competitor aggregate fields
        2. CompetitorAnalytics (historical record)
        3. ShareOfVoiceAnalytics
        
        Args:
            competitor: Competitor instance
        """
        try:
            logger.info(f"Aggregating analytics for competitor {competitor.id}")
            
            # Get all completed competitor-prompt analytics
            analytics_qs = CompetitorPromptAnalytics.objects.filter(
                competitor=competitor,
                track_status='COMP'
            )
            
            if not analytics_qs.exists():
                logger.warning(f"No completed analytics found for competitor {competitor.id}")
                return
            
            # Aggregate metrics
            totals = analytics_qs.aggregate(
                total_mentions=Sum('mention_count'),
                avg_position=Avg('position'),
                avg_sentiment=Avg('sentiment_score'),
                mentioned_count=Count('id', filter=Q(is_mentioned=True))
            )

            total_citations = 0
            for citation_list in analytics_qs.values_list('citation_list', flat=True):
                if citation_list and isinstance(citation_list, list):
                    total_citations += len(citation_list)
            
            # Update Competitor aggregate fields
            with transaction.atomic():
                comp = Competitor.objects.select_for_update().get(id=competitor.id)
                comp.total_mentions = totals['total_mentions'] or 0
                comp.average_position = totals['avg_position'] or 0.0
                comp.sentiment_score = totals['avg_sentiment'] or 0.0
                comp.visibility_score = self._calculate_visibility_score(
                    total_prompts=analytics_qs.count(),
                    mentioned_count=totals['mentioned_count'],
                    avg_position=totals['avg_position']
                )
                comp.save(update_fields=[
                    'total_mentions', 'average_position', 'sentiment_score', 
                    'visibility_score', 'modified_at'
                ])
            
            # Create CompetitorAnalytics snapshot
            CompetitorAnalytics.objects.create(
                competitor=competitor,
                platform='ChatGPT',
                total_mentions=totals['total_mentions'] or 0,
                position=totals['avg_position'] or 0.0,
                sentiment_score=totals['avg_sentiment'] or 0.0,
                timestamp=date.today()
            )
            
            # Update ShareOfVoice
            self._update_share_of_voice(competitor)
            competitor.refresh_from_db()
            self._create_metric_snapshot(
                competitor=competitor,
                totals=totals,
                total_citations=total_citations
            )
            
            logger.info(f"Successfully aggregated analytics for competitor {competitor.id}")
        
        except Exception as e:
            logger.error(f"Error aggregating competitor analytics: {str(e)}")
            raise
    
    def _calculate_visibility_score(
        self, 
        total_prompts: int, 
        mentioned_count: int, 
        avg_position: float
    ) -> Decimal:
        """
        Calculate visibility score based on mention frequency and position.
        
        Formula: (mentioned_count / total_prompts) * 100 * (1 / avg_position if avg_position else 1)
        
        Args:
            total_prompts: Total number of prompts tested
            mentioned_count: Number of prompts where competitor was mentioned
            avg_position: Average position when mentioned
        
        Returns:
            Decimal: Visibility score (0-100)
        """
        if total_prompts == 0:
            return Decimal('0.0')
        
        mention_rate = mentioned_count / total_prompts
        position_weight = 1.0 / (avg_position if avg_position and avg_position > 0 else 1.0)
        
        # Score = mention_rate * position_weight * 100
        # Cap at 100
        score = min(mention_rate * position_weight * 100, 100)
        return Decimal(str(round(score, 2)))
    
    def _update_share_of_voice(self, competitor: Competitor) -> None:
        """
        Update ShareOfVoiceAnalytics for this competitor.
        Calculates competitor's share relative to:
        1. Own brand (domain)
        2. Other competitors for same domain
        
        Args:
            competitor: Competitor instance
        """
        try:
            domain = competitor.domain
            domain_id = domain.id if hasattr(domain, 'id') else domain
            today = date.today()
            
            # Get own brand's mention count from PromptAnalytics
            # Note: Prompt doesn't have domain field directly, it's through group.domain
            own_mentions = PromptAnalytics.objects.filter(
                prompt__group__domain_id=domain_id,  # Access domain through group
                prompt__track_status='COMP',  # Only completed prompts
                track_status='COMP'  # Only completed analytics
            ).aggregate(total=Sum('total_mentions'))['total'] or 0
            
            # Get all competitors' mention counts for this domain
            competitors_mentions = Competitor.objects.filter(
                domain_id=domain_id,
                track_status='COMP'
            ).aggregate(total=Sum('total_mentions'))['total'] or 0
            
            # Total mentions in market
            total_market_mentions = own_mentions + competitors_mentions
            
            logger.info(f"Share of Voice calculation for domain {domain_id}: "
                       f"own_mentions={own_mentions}, competitors_mentions={competitors_mentions}, "
                       f"competitor.total_mentions={competitor.total_mentions}, "
                       f"total_market_mentions={total_market_mentions}")
            
            # Calculate competitor's share percentage
            if total_market_mentions > 0:
                competitor_share = (competitor.total_mentions / total_market_mentions) * 100
            else:
                competitor_share = 0.0
                logger.warning(f"No mentions found for share of voice calculation (domain={domain_id}), setting share to 0%")
            
            # Update ShareOfVoiceAnalytics for competitor
            sov_record, created = ShareOfVoiceAnalytics.objects.update_or_create(
                domain_id=domain_id,  # Use domain_id instead of domain object
                competitor=competitor,
                platform='ChatGPT',
                timestamp=today,
                defaults={
                    'share_percentage': Decimal(str(round(competitor_share, 2))),
                    'mention_count': competitor.total_mentions,
                    'market_position': None  # Will be calculated separately
                }
            )
            logger.info(f"{'Created' if created else 'Updated'} ShareOfVoice record for competitor {competitor.id}: {competitor_share:.2f}%")
            
            # Update own brand's ShareOfVoiceAnalytics
            own_share = (own_mentions / total_market_mentions) * 100 if total_market_mentions > 0 else 0.0
            own_sov_record, own_created = ShareOfVoiceAnalytics.objects.update_or_create(
                domain_id=domain_id,  # Use domain_id instead of domain object
                competitor=None,  # NULL = own brand
                platform='ChatGPT',
                timestamp=today,
                defaults={
                    'share_percentage': Decimal(str(round(own_share, 2))),
                    'mention_count': own_mentions,
                    'market_position': None
                }
            )
            logger.info(f"{'Created' if own_created else 'Updated'} ShareOfVoice record for own brand: {own_share:.2f}%")
            
            # Calculate market positions (ranks)
            self._calculate_market_positions(domain, today)
            
            # Update competitor's share_of_voice_percentage field
            with transaction.atomic():
                comp = Competitor.objects.select_for_update().get(id=competitor.id)
                comp.share_of_voice_percentage = Decimal(str(round(competitor_share, 2)))
                comp.save(update_fields=['share_of_voice_percentage', 'modified_at'])
            
            logger.info(f"Updated share of voice for competitor {competitor.id}: {competitor_share:.2f}%")
        
        except Exception as e:
            logger.error(f"Error updating share of voice: {str(e)}")
            raise
    
    def _calculate_market_positions(self, domain: Domain, timestamp: date) -> None:
        """
        Calculate and update market positions (ranks) for all players in the domain.
        
        Args:
            domain: Domain instance
            timestamp: Date for this ranking
        """
        try:
            # Get all SOV records for this domain and timestamp, ordered by share
            sov_records = ShareOfVoiceAnalytics.objects.filter(
                domain=domain,
                platform='ChatGPT',
                timestamp=timestamp
            ).order_by('-share_percentage')
            
            # Assign ranks
            for rank, sov in enumerate(sov_records, start=1):
                sov.market_position = rank
                sov.save(update_fields=['market_position'])
            
            logger.info(f"Updated market positions for domain {domain.id}, {len(sov_records)} players")
        
        except Exception as e:
            logger.error(f"Error calculating market positions: {str(e)}")
            raise

    def _create_metric_snapshot(self, competitor: Competitor, totals: Dict[str, Any], total_citations: int) -> None:
        """
        Persist a snapshot of competitor metrics after each processing run.
        """
        try:
            current_share = Decimal(str(competitor.share_of_voice_percentage or 0))
            last_snapshot = CompetitorMetricSnapshot.objects.filter(
                competitor=competitor
            ).order_by('-timestamp').first()

            trend_percentage = Decimal('0.0')
            if last_snapshot and last_snapshot.share_of_voice_percentage and last_snapshot.share_of_voice_percentage != 0:
                prev_share = Decimal(str(last_snapshot.share_of_voice_percentage))
                if prev_share != 0:
                    change = ((current_share - prev_share) / prev_share) * 100
                    trend_percentage = Decimal(str(round(change, 2)))

            CompetitorMetricSnapshot.objects.create(
                competitor=competitor,
                domain=competitor.domain,
                total_mentions=totals.get('total_mentions') or 0,
                total_citations=total_citations,
                visibility_score=competitor.visibility_score or 0,
                sentiment_score=competitor.sentiment_score or 0,
                average_position=competitor.average_position or 0,
                share_of_voice_percentage=current_share,
                trend_percentage=trend_percentage,
                track_status=competitor.track_status,
            )
        except Exception as e:
            logger.error(f"Error creating metric snapshot for competitor {competitor.id}: {str(e)}", exc_info=True)

