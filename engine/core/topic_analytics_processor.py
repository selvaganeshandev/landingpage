"""
Topic Analytics Processor: Calculates keyword and topic analytics from prompts
"""
import logging
import re
from typing import Dict, Any, List
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, Avg, Count, Q
from django.utils import timezone
from datetime import date
from shared_models.models import (
    Domain, Keyword, Topic, TopicKeyword, PromptKeyword, 
    Prompt, PromptAnalytics, KeywordAnalytics, TopicAnalytics
)

logger = logging.getLogger(__name__)


class TopicAnalyticsProcessor:
    """
    Processor for calculating keyword and topic analytics from prompts
    Runs after Topic Processor completes
    """
    
    def process_analytics_for_domain(self, domain: Domain) -> Dict[str, Any]:
        """
        Process analytics for all topics in a domain
        
        Args:
            domain: Domain to process analytics for
            
        Returns:
            Dict with processing results
        """
        try:
            logger.info(f"Starting topic analytics processing for domain {domain.id} ({domain.name})")
            
            # Get all topics for this domain
            topics = Topic.objects.filter(domain=domain, track_status__in=['INIT', 'PROC', 'COMP'])
            
            if not topics.exists():
                logger.warning(f"No topics found for domain {domain.id}")
                return {
                    'success': False,
                    'message': 'No topics found for domain',
                    'keywords_processed': 0,
                    'topics_processed': 0
                }
            
            keywords_processed = 0
            topics_processed = 0
            
            # Process each topic
            for topic in topics:
                try:
                    # Update topic status to PROC
                    with transaction.atomic():
                        topic_fresh = Topic.objects.select_for_update().get(id=topic.id)
                        if topic_fresh.track_status == 'INIT':
                            topic_fresh.track_status = 'PROC'
                            topic_fresh.track_message = 'Processing keyword analytics'
                            topic_fresh.tracked_at = timezone.now()
                            topic_fresh.save(update_fields=['track_status', 'track_message', 'tracked_at'])
                    
                    # Process keyword analytics for this topic
                    keyword_count = self._process_keyword_analytics_for_topic(topic)
                    keywords_processed += keyword_count
                    
                    # Aggregate keyword analytics to topic level
                    self._aggregate_topic_analytics(topic)
                    
                    # Mark topic as COMP
                    with transaction.atomic():
                        topic_fresh = Topic.objects.select_for_update().get(id=topic.id)
                        topic_fresh.track_status = 'COMP'
                        topic_fresh.track_message = f'Completed processing {keyword_count} keywords'
                        topic_fresh.tracked_at = timezone.now()
                        topic_fresh.save(update_fields=['track_status', 'track_message', 'tracked_at'])
                    
                    topics_processed += 1
                    logger.info(f"Completed analytics processing for topic {topic.id} ({topic.name})")
                    
                except Exception as e:
                    logger.error(f"Error processing topic {topic.id}: {str(e)}", exc_info=True)
                    # Mark topic as FAIL
                    try:
                        with transaction.atomic():
                            topic_fresh = Topic.objects.select_for_update().get(id=topic.id)
                            topic_fresh.track_status = 'FAIL'
                            topic_fresh.track_message = f'Error: {str(e)}'
                            topic_fresh.tracked_at = timezone.now()
                            topic_fresh.save(update_fields=['track_status', 'track_message', 'tracked_at'])
                    except:
                        pass
            
            logger.info(f"Completed topic analytics processing for domain {domain.id}: {keywords_processed} keywords, {topics_processed} topics")
            
            return {
                'success': True,
                'message': f'Processed {keywords_processed} keywords across {topics_processed} topics',
                'keywords_processed': keywords_processed,
                'topics_processed': topics_processed
            }
            
        except Exception as e:
            logger.error(f"Error processing topic analytics for domain {domain.id}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'Error: {str(e)}',
                'keywords_processed': 0,
                'topics_processed': 0
            }
    
    def _process_keyword_analytics_for_topic(self, topic: Topic) -> int:
        """
        Process analytics for all keywords in a topic
        
        Args:
            topic: Topic to process keywords for
            
        Returns:
            Number of keywords processed
        """
        # Get all TopicKeyword records for this topic
        topic_keywords = TopicKeyword.objects.filter(topic=topic, track_status='INIT')
        total_topic_keywords = topic_keywords.count()
        
        logger.info(f"Processing keyword analytics for topic {topic.id} ({topic.name}): Found {total_topic_keywords} TopicKeyword records with status INIT")
        
        if total_topic_keywords == 0:
            # Check if there are any TopicKeywords at all
            all_topic_keywords = TopicKeyword.objects.filter(topic=topic)
            all_count = all_topic_keywords.count()
            if all_count > 0:
                statuses = all_topic_keywords.values_list('track_status', flat=True).distinct()
                logger.warning(f"No INIT TopicKeywords found for topic {topic.id}. Total TopicKeywords: {all_count}, Statuses: {list(statuses)}")
            else:
                logger.warning(f"No TopicKeywords found at all for topic {topic.id} ({topic.name})")
        
        keyword_count = 0
        
        for topic_keyword in topic_keywords:
            try:
                keyword = topic_keyword.keyword
                logger.debug(f"Processing keyword {keyword.keyword} (ID: {keyword.id}) for topic {topic.id}")
                
                # Find all prompts linked to this keyword
                prompt_keywords = PromptKeyword.objects.filter(keyword=keyword)
                prompt_ids = [pk.prompt_id for pk in prompt_keywords]
                
                logger.debug(f"Found {len(prompt_ids)} PromptKeyword records linking prompts to keyword {keyword.keyword}")
                
                if not prompt_ids:
                    logger.warning(f"No prompts found for keyword {keyword.keyword} (ID: {keyword.id}) - marking TopicKeyword as COMP")
                    # Mark as COMP even if no prompts
                    topic_keyword.track_status = 'COMP'
                    topic_keyword.save(update_fields=['track_status'])
                    keyword_count += 1
                    continue
                
                # Get all PromptAnalytics for these prompts, grouped by platform
                prompt_analytics = PromptAnalytics.objects.filter(
                    prompt_id__in=prompt_ids,
                    track_status='COMP'
                )
                
                analytics_count = prompt_analytics.count()
                logger.debug(f"Found {analytics_count} PromptAnalytics records (status=COMP) for {len(prompt_ids)} prompts linked to keyword {keyword.keyword}")
                
                if analytics_count == 0:
                    # Check if there are any PromptAnalytics at all (even with different status)
                    all_prompt_analytics = PromptAnalytics.objects.filter(prompt_id__in=prompt_ids)
                    all_analytics_count = all_prompt_analytics.count()
                    if all_analytics_count > 0:
                        statuses = all_prompt_analytics.values_list('track_status', flat=True).distinct()
                        logger.warning(f"No COMP PromptAnalytics found for keyword {keyword.keyword}. Total PromptAnalytics: {all_analytics_count}, Statuses: {list(statuses)}")
                    else:
                        logger.warning(f"No PromptAnalytics found at all for prompts linked to keyword {keyword.keyword}")
                
                # Group by platform
                platforms = prompt_analytics.values_list('platform', flat=True).distinct()
                logger.debug(f"Found {len(platforms)} platforms with analytics: {list(platforms)}")
                
                if not platforms:
                    logger.warning(f"No platforms found in PromptAnalytics for keyword {keyword.keyword} - marking TopicKeyword as COMP")
                    topic_keyword.track_status = 'COMP'
                    topic_keyword.save(update_fields=['track_status'])
                    keyword_count += 1
                    continue
                
                # Process each platform
                for platform in platforms:
                    platform_analytics = prompt_analytics.filter(platform=platform)
                    platform_count = platform_analytics.count()
                    logger.debug(f"Processing platform {platform}: {platform_count} PromptAnalytics records")
                    
                    # Calculate keyword metrics from prompt analytics
                    metrics = self._calculate_keyword_metrics(keyword, platform_analytics)
                    logger.debug(f"Calculated metrics for {keyword.keyword} - {platform}: mentions={metrics['mentions']}, visibility={metrics['visibility_score']}, sentiment={metrics['sentiment_score']}")
                    
                    # Create or update KeywordAnalytics
                    self._create_keyword_analytics(keyword, platform, metrics)
                    logger.info(f"✅ Created/updated KeywordAnalytics for keyword {keyword.keyword} - {platform}")
                
                # Mark TopicKeyword as COMP
                topic_keyword.track_status = 'COMP'
                topic_keyword.save(update_fields=['track_status'])
                logger.debug(f"Marked TopicKeyword {topic_keyword.id} as COMP")
                
                keyword_count += 1
                
            except Exception as e:
                logger.error(f"Error processing keyword {topic_keyword.keyword.keyword}: {str(e)}", exc_info=True)
                continue
        
        logger.info(f"Completed processing {keyword_count} keywords for topic {topic.id} ({topic.name})")
        return keyword_count
    
    def _calculate_keyword_metrics(self, keyword: Keyword, prompt_analytics) -> Dict[str, Any]:
        """
        Calculate keyword metrics from prompt analytics
        
        Args:
            keyword: Keyword to calculate metrics for
            prompt_analytics: QuerySet of PromptAnalytics records
            
        Returns:
            Dictionary with calculated metrics
        """
        if not prompt_analytics.exists():
            return {
                'mentions': 0,
                'avg_position': Decimal('0.00'),
                'visibility_score': Decimal('0.00'),
                'sentiment_score': Decimal('0.00')
            }
        
        # Count mentions: search for keyword in context_summary
        keyword_lower = keyword.keyword.lower()
        mentions = 0
        
        for analytics in prompt_analytics:
            if analytics.context_summary:
                # Count occurrences of keyword in context_summary (case-insensitive)
                text_lower = analytics.context_summary.lower()
                # Use word boundaries to avoid partial matches
                pattern = r'\b' + re.escape(keyword_lower) + r'\b'
                matches = len(re.findall(pattern, text_lower))
                mentions += matches
        
        # Calculate average position
        positions = [float(pa.position) for pa in prompt_analytics if pa.position and pa.position > 0]
        avg_position = Decimal(str(sum(positions) / len(positions))) if positions else Decimal('0.00')
        
        # Calculate visibility score (inverse of position, normalized to 0-100)
        # Lower position = higher visibility
        if avg_position > 0:
            visibility_score = Decimal(str(max(0, min(100, 100 / avg_position))))
        else:
            visibility_score = Decimal('0.00')
        
        # Calculate average sentiment score
        sentiment_scores = [float(pa.sentiment_score) for pa in prompt_analytics if pa.sentiment_score is not None]
        sentiment_score = Decimal(str(sum(sentiment_scores) / len(sentiment_scores))) if sentiment_scores else Decimal('0.00')
        
        return {
            'mentions': mentions,
            'avg_position': avg_position,
            'visibility_score': visibility_score,
            'sentiment_score': sentiment_score
        }
    
    def _create_keyword_analytics(self, keyword: Keyword, platform: str, metrics: Dict[str, Any]) -> None:
        """
        Create or update KeywordAnalytics record
        
        Args:
            keyword: Keyword instance
            platform: Platform name
            metrics: Dictionary with metrics
        """
        try:
            today = date.today()
            
            with transaction.atomic():
                analytics, created = KeywordAnalytics.objects.get_or_create(
                    keyword=keyword,
                    platform=platform,
                    timestamp=today,
                    defaults={
                        'mentions': metrics['mentions'],
                        'avg_position': metrics['avg_position'],
                        'visibility_score': metrics['visibility_score'],
                        'sentiment_score': metrics['sentiment_score'],
                        'track_status': 'COMP',
                        'tracked_at': timezone.now()
                    }
                )
                
                if not created:
                    # Update existing record
                    analytics.mentions = metrics['mentions']
                    analytics.avg_position = metrics['avg_position']
                    analytics.visibility_score = metrics['visibility_score']
                    analytics.sentiment_score = metrics['sentiment_score']
                    analytics.track_status = 'COMP'
                    analytics.tracked_at = timezone.now()
                    analytics.save(update_fields=[
                        'mentions', 'avg_position', 'visibility_score', 
                        'sentiment_score', 'track_status', 'tracked_at', 'modified_at'
                    ])
                
                logger.debug(f"Created/updated KeywordAnalytics for {keyword.keyword} - {platform}")
                
        except Exception as e:
            logger.error(f"Error creating KeywordAnalytics for {keyword.keyword} - {platform}: {str(e)}", exc_info=True)
    
    def _aggregate_topic_analytics(self, topic: Topic) -> None:
        """
        Aggregate keyword analytics to topic level
        
        Args:
            topic: Topic to aggregate analytics for
        """
        try:
            logger.info(f"Aggregating analytics for topic {topic.id} ({topic.name})")
            
            # Test database connection and model
            try:
                test_count = TopicAnalytics.objects.count()
                logger.debug(f"Database connection test: Found {test_count} existing TopicAnalytics records")
            except Exception as db_test_error:
                logger.error(f"❌ Database connection test failed: {str(db_test_error)}", exc_info=True)
                raise
            
            # Get all keywords for this topic
            topic_keywords = TopicKeyword.objects.filter(topic=topic, track_status='COMP')
            keyword_ids = [tk.keyword_id for tk in topic_keywords]
            
            logger.debug(f"Found {len(keyword_ids)} completed keywords for topic {topic.id}")
            
            if not keyword_ids:
                logger.warning(f"No completed keywords found for topic {topic.id} - creating zero analytics")
                # Create zero analytics even if no keywords
                total_mentions = 0
                avg_visibility = Decimal('0.00')
                avg_sentiment = Decimal('0.00')
                platforms = []
            else:
                # Get all KeywordAnalytics for these keywords
                keyword_analytics = KeywordAnalytics.objects.filter(
                    keyword_id__in=keyword_ids,
                    track_status='COMP'
                )
                
                analytics_count = keyword_analytics.count()
                logger.debug(f"Found {analytics_count} keyword analytics records for topic {topic.id}")
                
                if not keyword_analytics.exists():
                    logger.warning(f"No keyword analytics found for topic {topic.id} - creating zero analytics")
                    # Create zero analytics even if no keyword analytics
                    platforms = []
                    platform_metrics = {}
                else:
                    # Get unique platforms
                    platforms = list(keyword_analytics.values_list('platform', flat=True).distinct())
                    
                    # Aggregate metrics per platform
                    platform_metrics = {}
                    for platform in platforms:
                        platform_analytics = keyword_analytics.filter(platform=platform)
                        
                        platform_mentions = platform_analytics.aggregate(
                            total=Sum('mentions')
                        )['total'] or 0
                        
                        platform_visibility = platform_analytics.aggregate(
                            avg=Avg('visibility_score')
                        )['avg'] or Decimal('0.00')
                        
                        platform_sentiment = platform_analytics.aggregate(
                            avg=Avg('sentiment_score')
                        )['avg'] or Decimal('0.00')
                        
                        platform_metrics[platform] = {
                            'mentions': platform_mentions,
                            'visibility': platform_visibility,
                            'sentiment': platform_sentiment
                        }
                    
                    logger.debug(f"Aggregated metrics for topic {topic.id} across {len(platforms)} platforms: {platform_metrics}")
            
            # Calculate overall aggregated metrics for topic (across all platforms)
            if platform_metrics:
                total_mentions = sum(m['mentions'] for m in platform_metrics.values())
                all_visibilities = [m['visibility'] for m in platform_metrics.values()]
                all_sentiments = [m['sentiment'] for m in platform_metrics.values()]
                avg_visibility = sum(all_visibilities) / len(all_visibilities) if all_visibilities else Decimal('0.00')
                avg_sentiment = sum(all_sentiments) / len(all_sentiments) if all_sentiments else Decimal('0.00')
            else:
                total_mentions = 0
                avg_visibility = Decimal('0.00')
                avg_sentiment = Decimal('0.00')
            
            # Update topic metrics (overall aggregated)
            with transaction.atomic():
                topic_fresh = Topic.objects.select_for_update().get(id=topic.id)
                topic_fresh.total_mentions = total_mentions
                topic_fresh.visibility_score = Decimal(str(avg_visibility))
                topic_fresh.sentiment_score = Decimal(str(avg_sentiment))
                topic_fresh.platform_list = platforms
                topic_fresh.save(update_fields=[
                    'total_mentions', 'visibility_score', 'sentiment_score', 
                    'platform_list', 'modified_at'
                ])
                logger.debug(f"Updated topic {topic.id} overall metrics")
            
            # Create TopicAnalytics time-series records for each platform
            today = date.today()
            records_created = 0
            records_updated = 0
            errors = []
            
            # If no platforms found, create a record with "All Platforms" to track that analytics were processed
            if not platforms:
                logger.warning(f"No platforms found for topic {topic.id} - creating TopicAnalytics with 'All Platforms'")
                platforms = ['All Platforms']
                platform_metrics['All Platforms'] = {
                    'mentions': 0,
                    'visibility': Decimal('0.00'),
                    'sentiment': Decimal('0.00')
                }
            
            # Create TopicAnalytics records for all platforms (whether from data or fallback)
            logger.info(f"Creating TopicAnalytics records for {len(platforms)} platforms: {platforms}")
            
            # Wrap all TopicAnalytics creation in a transaction
            try:
                logger.info(f"Starting transaction to create TopicAnalytics for {len(platforms)} platforms: {platforms}")
                with transaction.atomic():
                    logger.info(f"Inside transaction block, processing {len(platforms)} platforms")
                    for platform in platforms:
                        logger.info(f"Processing platform: {platform}")
                        try:
                            metrics = platform_metrics.get(platform, {
                                'mentions': 0,
                                'visibility': Decimal('0.00'),
                                'sentiment': Decimal('0.00')
                            })
                            
                            logger.info(f"Attempting to create TopicAnalytics for topic {topic.id}, platform {platform}: mentions={metrics['mentions']}, visibility={metrics['visibility']}, sentiment={metrics['sentiment']}")
                            
                            # Use update_or_create for atomic operation
                            try:
                                analytics_record, created = TopicAnalytics.objects.update_or_create(
                                    topic=topic,
                                    platform=platform,
                                    timestamp=today,
                                    defaults={
                                        'total_mentions': metrics['mentions'],
                                        'visibility_score': Decimal(str(metrics['visibility'])),
                                        'sentiment_score': Decimal(str(metrics['sentiment']))
                                    }
                                )
                                
                                logger.info(f"✅ update_or_create returned: created={created}, record_id={analytics_record.id}")
                                
                                if created:
                                    records_created += 1
                                    logger.info(f"✅ Created TopicAnalytics record (ID: {analytics_record.id}) for topic {topic.id}, platform {platform}")
                                else:
                                    records_updated += 1
                                    logger.info(f"✅ Updated TopicAnalytics record (ID: {analytics_record.id}) for topic {topic.id}, platform {platform}")
                                
                                # Immediately verify within transaction
                                verify_in_tx = TopicAnalytics.objects.filter(
                                    id=analytics_record.id
                                ).exists()
                                logger.info(f"✅ Verification within transaction: record exists={verify_in_tx}")
                                
                            except Exception as create_ex:
                                error_msg = f"❌ Exception in update_or_create for topic {topic.id}, platform {platform}: {str(create_ex)}"
                                logger.error(error_msg, exc_info=True)
                                errors.append(error_msg)
                                raise  # Re-raise to rollback transaction
                                
                        except Exception as e:
                            error_msg = f"❌ Error creating TopicAnalytics for topic {topic.id}, platform {platform}: {str(e)}"
                            logger.error(error_msg, exc_info=True)
                            errors.append(error_msg)
                            raise  # Re-raise to rollback transaction
                    
                    # Transaction will auto-commit when exiting the with block
                    logger.info(f"✅ Transaction completed for TopicAnalytics creation for topic {topic.id}: {records_created} created, {records_updated} updated")
                    
            except Exception as tx_error:
                error_msg = f"❌ Transaction error creating TopicAnalytics for topic {topic.id}: {str(tx_error)}"
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
            
            # Verify records after transaction
            logger.info(f"Verifying TopicAnalytics records after transaction for {len(platforms)} platforms")
            for platform in platforms:
                verify_record = TopicAnalytics.objects.filter(
                    topic=topic,
                    platform=platform,
                    timestamp=today
                ).first()
                if verify_record:
                    logger.info(f"✅ Verified TopicAnalytics record exists: ID={verify_record.id}, platform={platform}, mentions={verify_record.total_mentions}")
                else:
                    error_msg = f"❌ ERROR: TopicAnalytics record not found after creation for topic {topic.id}, platform {platform}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            # Final verification - query database directly
            verify_count = TopicAnalytics.objects.filter(topic=topic, timestamp=today).count()
            if verify_count > 0:
                logger.info(f"✅ FINAL VERIFICATION: {verify_count} TopicAnalytics record(s) exist for topic {topic.id} on {today}")
                # List all records for debugging
                all_records = TopicAnalytics.objects.filter(topic=topic, timestamp=today)
                for record in all_records:
                    logger.info(f"   - Record ID={record.id}, platform={record.platform}, mentions={record.total_mentions}, visibility={record.visibility_score}, sentiment={record.sentiment_score}")
            else:
                if platforms:  # Only log error if we expected to create records
                    error_msg = f"❌ CRITICAL ERROR: No TopicAnalytics records found after creation for topic {topic.id} on {today}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    
                    # Try to diagnose the issue
                    logger.error(f"   Diagnosing issue for topic {topic.id}:")
                    logger.error(f"   - Topic exists: {Topic.objects.filter(id=topic.id).exists()}")
                    logger.error(f"   - Platforms attempted: {platforms}")
                    logger.error(f"   - Total TopicAnalytics in DB: {TopicAnalytics.objects.count()}")
                    
                    # Check if there are any TopicAnalytics for this topic at all
                    any_for_topic = TopicAnalytics.objects.filter(topic=topic).count()
                    logger.error(f"   - TopicAnalytics for this topic (any date): {any_for_topic}")
            
            if errors:
                logger.error(f"❌ Errors occurred while creating TopicAnalytics for topic {topic.id}: {errors}")
                # Log detailed error information but don't raise to allow processing to continue
                for error in errors:
                    logger.error(f"   - {error}")
            else:
                logger.info(f"✅ SUCCESS: All TopicAnalytics records created/updated successfully for topic {topic.id}")
            
            logger.info(f"Successfully aggregated analytics for topic {topic.id} ({topic.name}): {records_created} created, {records_updated} updated across {len(platforms)} platforms")
            
        except Exception as e:
            logger.error(f"❌ Error aggregating topic analytics for topic {topic.id}: {str(e)}", exc_info=True)
            # Don't re-raise to allow processing to continue for other topics
    
    def link_prompts_to_keywords(self, prompt: Prompt, keywords: List[Keyword]) -> None:
        """
        Link prompts to keywords by creating PromptKeyword records
        This should be called when prompts are created from keywords
        
        Args:
            prompt: Prompt instance
            keywords: List of Keyword instances
        """
        try:
            with transaction.atomic():
                for keyword in keywords:
                    # Check if link already exists
                    if not PromptKeyword.objects.filter(prompt=prompt, keyword=keyword).exists():
                        PromptKeyword.objects.create(
                            prompt=prompt,
                            keyword=keyword,
                            relevance_score=Decimal('100.00')  # Default relevance
                        )
                        logger.debug(f"Linked prompt {prompt.id} to keyword {keyword.keyword}")
        except Exception as e:
            logger.error(f"Error linking prompts to keywords: {str(e)}", exc_info=True)
    
    def handle_keyword_movement(self, keyword: Keyword, old_topic: Topic, new_topic: Topic) -> None:
        """
        Handle keyword movement from one topic to another
        Re-aggregates analytics for both topics
        
        Args:
            keyword: Keyword that moved
            old_topic: Previous topic
            new_topic: New topic
        """
        try:
            logger.info(f"Handling keyword movement: {keyword.keyword} from {old_topic.name} to {new_topic.name}")
            
            # Remove from old topic
            TopicKeyword.objects.filter(topic=old_topic, keyword=keyword).delete()
            
            # Add to new topic
            TopicKeyword.objects.create(
                topic=new_topic,
                keyword=keyword,
                relevance_score=Decimal('100.00'),
                track_status='INIT'
            )
            
            # Mark keyword as used for topic generation (can be used multiple times)
            keyword.last_used_for_topic_generation = timezone.now()
            keyword.save(update_fields=['last_used_for_topic_generation', 'modified_at'])
            logger.debug(f"Marked keyword '{keyword.keyword}' as used for topic generation (moved to {new_topic.name})")
            
            # Re-aggregate both topics
            self._aggregate_topic_analytics(old_topic)
            self._aggregate_topic_analytics(new_topic)
            
            logger.info(f"Successfully moved keyword {keyword.keyword} and re-aggregated topics")
            
        except Exception as e:
            logger.error(f"Error handling keyword movement: {str(e)}", exc_info=True)
    
    def schedule_tick(self) -> Dict[str, Any]:
        """
        Periodic scheduler for topic analytics updates:
        - Finds topics that need analytics recalculation
        - Processes keyword analytics for those topics
        - Re-aggregates topic analytics
        - Creates/updates time-series records
        
        Returns:
            Dict with scheduling results
        """
        try:
            from django.conf import settings
            
            # Find topics that need analytics updates:
            # 1. Topics with INIT or PROC status (not yet completed)
            # 2. Topics with COMP status but have new prompts processed (need recalculation)
            # 3. Topics that haven't been updated recently (for periodic updates)
            
            # Priority 1: Topics in INIT or PROC status (incomplete processing)
            pending_topics = Topic.objects.filter(
                track_status__in=['INIT', 'PROC'],
                domain__processing_status='COMP'  # Only process for completed domains
            ).select_related('domain').order_by('modified_at')[:1]
            
            if pending_topics.exists():
                topic = pending_topics.first()
                logger.info(f"Scheduling topic analytics for incomplete topic: {topic.id} ({topic.name})")
                
                # Process this topic
                keyword_count = self._process_keyword_analytics_for_topic(topic)
                self._aggregate_topic_analytics(topic)
                
                # Mark as COMP
                with transaction.atomic():
                    topic_fresh = Topic.objects.select_for_update().get(id=topic.id)
                    topic_fresh.track_status = 'COMP'
                    topic_fresh.track_message = f'Completed processing {keyword_count} keywords'
                    topic_fresh.tracked_at = timezone.now()
                    topic_fresh.save(update_fields=['track_status', 'track_message', 'tracked_at', 'modified_at'])
                
                return {
                    'scheduled': True,
                    'topic_id': topic.id,
                    'topic_name': topic.name,
                    'keywords_processed': keyword_count,
                    'reason': 'incomplete_topic'
                }
            
            # Priority 2: Topics with new prompts processed (need recalculation)
            # Find topics where new PromptAnalytics have been created since last topic update
            from datetime import timedelta
            recent_threshold = timezone.now() - timedelta(hours=1)  # Check last hour
            
            topics_with_new_data = Topic.objects.filter(
                track_status='COMP',
                domain__processing_status='COMP',
                modified_at__lt=recent_threshold  # Not updated recently
            ).select_related('domain')
            
            for topic in topics_with_new_data[:1]:  # Process one at a time
                # Check if there are new PromptAnalytics for keywords in this topic
                topic_keywords = TopicKeyword.objects.filter(topic=topic)
                keyword_ids = [tk.keyword_id for tk in topic_keywords]
                
                if not keyword_ids:
                    continue
                
                # Check if any prompts linked to these keywords have new analytics
                prompt_keywords = PromptKeyword.objects.filter(keyword_id__in=keyword_ids)
                prompt_ids = [pk.prompt_id for pk in prompt_keywords]
                
                if not prompt_ids:
                    continue
                
                # Check for recent PromptAnalytics
                recent_analytics = PromptAnalytics.objects.filter(
                    prompt_id__in=prompt_ids,
                    track_status='COMP',
                    modified_at__gte=recent_threshold
                ).exists()
                
                if recent_analytics:
                    logger.info(f"Scheduling topic analytics recalculation for topic: {topic.id} ({topic.name}) - new prompts processed")
                    
                    # Re-process keyword analytics
                    keyword_count = self._process_keyword_analytics_for_topic(topic)
                    self._aggregate_topic_analytics(topic)
                    
                    return {
                        'scheduled': True,
                        'topic_id': topic.id,
                        'topic_name': topic.name,
                        'keywords_processed': keyword_count,
                        'reason': 'new_prompts_processed'
                    }
            
            # No topics need processing
            return {
                'scheduled': False,
                'reason': 'no_topics_need_processing'
            }
            
        except Exception as e:
            logger.error(f"Error in topic analytics schedule_tick: {str(e)}", exc_info=True)
            return {
                'scheduled': False,
                'error': str(e)
            }

