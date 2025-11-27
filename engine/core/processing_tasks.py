from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from shared_models.models import Domain
from .domain_processor import DomainProcessor
from .prompt_analytics_processor import PromptAnalyticsProcessor
from .competitor_processor import CompetitorProcessor
from .ga_insights_processor import GAInsightsProcessor
from .gsc_insights_processor import GSCInsightsProcessor
import logging

# Import from engine's integrations app
from integrations.models import Integration

logger = logging.getLogger(__name__)


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_domain_task(self, domain_id: int):
    processor = DomainProcessor()
    processor._process_single_domain(domain_id)


@shared_task(bind=True, ignore_result=True, max_retries=3)
def scheduler_tick(self):
    max_concurrent = getattr(settings, 'MAX_CONCURRENT_DOMAINS', 10)

    # Count current in-flight (scheduled) domains
    currently_processing = Domain.objects.filter(processing_status='SCHD').count()
    available_slots = max(0, max_concurrent - currently_processing)
    if available_slots <= 0:
        return
    
    # Pick up to available_slots domains in INIT (not yet scheduled)
    domain_ids = list(
        Domain.objects.filter(processing_status__in=['INIT'])
        .order_by('modified_at')
        .values_list('id', flat=True)[:available_slots]
    )

    for domain_id in domain_ids:
        # Mark as scheduled if INIT
        with transaction.atomic():
            domain = Domain.objects.select_for_update().get(id=domain_id)
            if domain.processing_status == 'INIT':
                domain.processing_status = 'SCHD'
                domain.tracked_at = timezone.now()
                domain.save(update_fields=['processing_status', 'tracked_at', 'modified_at'])

        process_domain_task.delay(domain_id)


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_prompt_analytics_task(self, prompt_id):
    processor = PromptAnalyticsProcessor(max_concurrent_prompts=getattr(settings, 'MAX_CONCURRENT_PROMPT_ANALYTICS', 10))
    return processor.process_single_prompt(prompt_id)


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_prompt_analytics_scheduler(self):
    processor = PromptAnalyticsProcessor(max_concurrent_prompts=getattr(settings, 'MAX_CONCURRENT_PROMPT_ANALYTICS', 10))
    return processor.schedule_tick()


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_competitor_scheduler(self):
    """
    DEPRECATED: Competitor processing scheduler - no longer used.
    Competitor processing is now manual-only via process_single_competitor_task.
    This task is kept for backward compatibility but is not scheduled in Celery Beat.
    """
    logger.warning("process_competitor_scheduler is deprecated. Use manual processing via POST /api/competitors/{id}/process/")
    return {'scheduled': False, 'reason': 'deprecated', 'message': 'Use manual processing instead'}


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_single_competitor_task(self, competitor_id: int):
    """
    Process a single competitor (manual/on-demand processing only).
    This is the primary method for processing competitors - triggered via API endpoint.
    
    Args:
        competitor_id: ID of competitor to process
    """
    from shared_models.models import Competitor
    try:
        processor = CompetitorProcessor(max_concurrent_prompts=getattr(settings, 'MAX_CONCURRENT_COMPETITOR_PROMPTS', 10))
        
        # Get the competitor
        with transaction.atomic():
            competitor = Competitor.objects.select_for_update().get(id=competitor_id)
            
            # Allow reprocessing if COMP or failed before, or if INIT
            # Reset to INIT if it's already COMP (for reprocessing)
            if competitor.track_status == 'COMP':
                logger.info(f"Competitor {competitor_id} is already COMP, resetting to INIT for reprocessing")
                competitor.track_status = 'INIT'
                competitor.track_message = 'Resetting for reprocessing'
                competitor.save(update_fields=['track_status', 'track_message', 'modified_at'])
            elif competitor.track_status not in ['INIT', 'FAIL']:
                logger.warning(f"Competitor {competitor_id} is in status {competitor.track_status}, skipping")
                return {'error': f'Competitor already in status {competitor.track_status}'}
            
            # Mark as SCHD
            competitor.track_status = 'SCHD'
            competitor.track_message = f"Scheduled for processing at {timezone.now()}"
            competitor.save(update_fields=['track_status', 'track_message', 'modified_at'])
        
        logger.info(f"Processing competitor {competitor_id} ({competitor.name})")
        
        # Link prompts to competitor
        processor._link_prompts_to_competitor(competitor)
        
        # Mark as processing
        with transaction.atomic():
            competitor = Competitor.objects.select_for_update().get(id=competitor_id)
            competitor.track_status = 'PROC'
            competitor.track_message = "Processing competitor analytics"
            competitor.save(update_fields=['track_status', 'track_message', 'modified_at'])
        
        # Process prompts
        processor._process_competitor_prompts(competitor)
        
        # Aggregate analytics
        processor._aggregate_competitor_analytics(competitor)
        
        # Mark as complete
        with transaction.atomic():
            competitor = Competitor.objects.select_for_update().get(id=competitor_id)
            competitor.track_status = 'COMP'
            competitor.track_message = f"Completed at {timezone.now()}"
            competitor.tracked_at = timezone.now()
            competitor.save(update_fields=['track_status', 'track_message', 'tracked_at', 'modified_at'])
        
        logger.info(f"Successfully completed competitor {competitor_id}")
        return {'success': True, 'competitor_id': competitor_id}
        
    except Competitor.DoesNotExist:
        logger.error(f"Competitor {competitor_id} not found")
        return {'error': 'competitor_not_found'}
    except Exception as e:
        logger.error(f"Error processing competitor {competitor_id}: {str(e)}")
        # Mark as failed
        try:
            with transaction.atomic():
                competitor = Competitor.objects.select_for_update().get(id=competitor_id)
                competitor.track_status = 'FAIL'
                competitor.track_message = f"Processing failed: {str(e)}"
                competitor.save(update_fields=['track_status', 'track_message', 'modified_at'])
        except:
            pass
        return {'error': str(e)}


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_topics_for_domain_task(self, domain_id: int):
    """
    Process topics for a domain by grouping keywords using NLP
    Triggered when domain processing_status becomes COMP
    
    Args:
        domain_id: ID of domain to process topics for
    """
    from shared_models.models import Domain
    from core.topic_processor import TopicProcessor
    from core.topic_analytics_processor import TopicAnalyticsProcessor
    
    try:
        domain = Domain.objects.get(id=domain_id)
        
        # Step 1: Group keywords into topics
        logger.info(f"Starting topic processing for domain {domain_id}")
        topic_processor = TopicProcessor()
        result = topic_processor.process_topics_for_domain(domain)
        
        if not result.get('success'):
            logger.error(f"Topic processing failed for domain {domain_id}: {result.get('message')}")
            return result
        
        # Step 2: Process topic analytics
        logger.info(f"Starting topic analytics processing for domain {domain_id}")
        analytics_processor = TopicAnalyticsProcessor()
        analytics_result = analytics_processor.process_analytics_for_domain(domain)
        
        if not analytics_result.get('success'):
            logger.error(f"Topic analytics processing failed for domain {domain_id}: {analytics_result.get('message')}")
            return analytics_result
        
        logger.info(f"Successfully completed topic processing for domain {domain_id}")
        return {
            'success': True,
            'topics_created': result.get('topics_created', 0),
            'keywords_processed': analytics_result.get('keywords_processed', 0),
            'topics_processed': analytics_result.get('topics_processed', 0)
        }
        
    except Domain.DoesNotExist:
        logger.error(f"Domain {domain_id} not found")
        return {'error': 'domain_not_found'}
    except Exception as e:
        logger.error(f"Error processing topics for domain {domain_id}: {str(e)}", exc_info=True)
        return {'error': str(e)}


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_topic_analytics_scheduler(self):
    """
    Periodic scheduler for topic analytics updates.
    Runs via Celery Beat to continuously update topic analytics when new prompts are processed.
    """
    from core.topic_analytics_processor import TopicAnalyticsProcessor
    
    try:
        processor = TopicAnalyticsProcessor()
        result = processor.schedule_tick()
        logger.debug(f"Topic analytics scheduler tick: {result}")
        return result
    except Exception as e:
        logger.error(f"Error in topic analytics scheduler: {str(e)}", exc_info=True)
        return {'scheduled': False, 'error': str(e)}


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_ga_insights_task(self, integration_id: int, days_back: int = 30):
    """Process GA insights for an integration (legacy - kept for backward compatibility)"""
    processor = GAInsightsProcessor()
    return processor.process_integration(integration_id, days_back)


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_gsc_insights_task(self, integration_id: int, days_back: int = 30):
    """Process GSC insights for an integration (legacy - kept for backward compatibility)"""
    processor = GSCInsightsProcessor()
    return processor.process_integration(integration_id, days_back)


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_ga_insight_task(self, insight_id: int):
    """Process a single GA insight record"""
    try:
        logger.info(f"[GA Task] Starting processing for insight {insight_id}")
        processor = GAInsightsProcessor()
        result = processor.process_insight(insight_id)
        logger.info(f"[GA Task] Completed processing for insight {insight_id}: {result.get('success', False)}")
        return result
    except Exception as e:
        logger.error(f"[GA Task] Error processing insight {insight_id}: {str(e)}", exc_info=True)
        raise


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_gsc_insight_task(self, insight_id: int):
    """Process a single GSC insight record"""
    try:
        logger.info(f"[GSC Task] Starting processing for insight {insight_id}")
        processor = GSCInsightsProcessor()
        result = processor.process_insight(insight_id)
        logger.info(f"[GSC Task] Completed processing for insight {insight_id}: {result.get('success', False)}")
        return result
    except Exception as e:
        logger.error(f"[GSC Task] Error processing insight {insight_id}: {str(e)}", exc_info=True)
        raise


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_integration_insights_scheduler(self):
    """Scheduler to pick up INIT records and process them one by one"""
    from integrations.models import GATrafficInsight, GSCTrafficInsight
    
    logger.info("[Integration Scheduler] Starting scheduler run")
    processed = 0
    
    # Process GA insights with INIT status (one at a time)
    # Use select_for_update to prevent race conditions
    try:
        # First, count how many INIT records match criteria
        init_count = GATrafficInsight.objects.filter(
            track_status='INIT',
            integration__status='active',
            integration__provider_id__isnull=False
        ).exclude(integration__provider_id='').count()
        logger.info(f"[Integration Scheduler] Found {init_count} GA INIT records matching criteria")
        
        with transaction.atomic():
            # Change nowait=True to nowait=False to wait for locks instead of failing silently
            ga_insight = GATrafficInsight.objects.select_for_update(nowait=False).filter(
                track_status='INIT',
                integration__status='active',  # Only process active integrations
                integration__provider_id__isnull=False
            ).exclude(integration__provider_id='').order_by('created_at').first()
            
            if ga_insight:
                logger.info(f"[Integration Scheduler] Found GA insight {ga_insight.id} (domain {ga_insight.domain_id}, integration {ga_insight.integration.id})")
                # Check if same integration is already processing
                proc_exists = GATrafficInsight.objects.filter(
                    integration=ga_insight.integration,
                    track_status='PROC'
                ).exists()
                
                if not proc_exists:
                    logger.info(f"[Integration Scheduler] Dispatching process_ga_insight_task for insight {ga_insight.id}")
                    process_ga_insight_task.delay(ga_insight.id)
                    processed += 1
                else:
                    logger.info(f"[Integration Scheduler] Integration {ga_insight.integration.id} already has a PROC insight, skipping")
            else:
                logger.info("[Integration Scheduler] No GA insight found matching criteria")
    except Exception as e:
        logger.error(f"[Integration Scheduler] Error processing GA insights: {str(e)}", exc_info=True)
    
    # Process GSC insights with INIT status (one at a time)
    try:
        # Count GSC INIT records
        gsc_init_count = GSCTrafficInsight.objects.filter(
            track_status='INIT',
            integration__status='active',
            integration__provider_id__isnull=False
        ).exclude(integration__provider_id='').count()
        logger.info(f"[Integration Scheduler] Found {gsc_init_count} GSC INIT records matching criteria")
        
        with transaction.atomic():
            # Change nowait=True to nowait=False to wait for locks instead of failing silently
            gsc_insight = GSCTrafficInsight.objects.select_for_update(nowait=False).filter(
                track_status='INIT',
                integration__status='active',  # Only process active integrations
                integration__provider_id__isnull=False
            ).exclude(integration__provider_id='').order_by('created_at').first()
            
            if gsc_insight:
                logger.info(f"[Integration Scheduler] Found GSC insight {gsc_insight.id} (domain {gsc_insight.domain_id}, integration {gsc_insight.integration.id})")
                # Check if same integration is already processing
                proc_exists = GSCTrafficInsight.objects.filter(
                    integration=gsc_insight.integration,
                    track_status='PROC'
                ).exists()
                
                if not proc_exists:
                    logger.info(f"[Integration Scheduler] Dispatching process_gsc_insight_task for insight {gsc_insight.id}")
                    process_gsc_insight_task.delay(gsc_insight.id)
                    processed += 1
                else:
                    logger.info(f"[Integration Scheduler] Integration {gsc_insight.integration.id} already has a PROC insight, skipping")
            else:
                logger.info("[Integration Scheduler] No GSC insight found matching criteria")
    except Exception as e:
        logger.error(f"[Integration Scheduler] Error processing GSC insights: {str(e)}", exc_info=True)
    
    logger.info(f"[Integration Scheduler] Scheduler run completed. Processed: {processed}")
    return {'processed': processed}

