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
    Competitor processing scheduler - picks INIT competitors and processes them.
    Should be run periodically via Celery Beat.
    """
    processor = CompetitorProcessor(max_concurrent_prompts=getattr(settings, 'MAX_CONCURRENT_COMPETITOR_PROMPTS', 10))
    return processor.schedule_tick()


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_single_competitor_task(self, competitor_id: int):
    """
    Process a single competitor (for manual/on-demand processing).
    
    Args:
        competitor_id: ID of competitor to process
    """
    from shared_models.models import Competitor
    try:
        competitor = Competitor.objects.get(id=competitor_id)
        processor = CompetitorProcessor(max_concurrent_prompts=getattr(settings, 'MAX_CONCURRENT_COMPETITOR_PROMPTS', 10))
        
        # Mark as INIT so it gets picked up
        with transaction.atomic():
            comp = Competitor.objects.select_for_update().get(id=competitor_id)
            comp.track_status = 'INIT'
            comp.save(update_fields=['track_status', 'modified_at'])
        
        # Trigger scheduler
        return processor.schedule_tick()
    except Competitor.DoesNotExist:
        logger.error(f"Competitor {competitor_id} not found")
        return {'error': 'competitor_not_found'}
    except Exception as e:
        logger.error(f"Error processing competitor {competitor_id}: {str(e)}")
        return {'error': str(e)}


