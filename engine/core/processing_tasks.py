from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from shared_models.models import Domain
from .domain_processor import DomainProcessor
from .prompt_analytics_processor import PromptAnalyticsProcessor
from .competitor_processor import CompetitorProcessor
import logging


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


