from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from shared_models.models import Domain
from .domain_processor import DomainProcessor
from .prompt_analytics_processor import PromptAnalyticsProcessor
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
    currently_processing = Domain.objects.filter(track_status='SCHD').count()
    available_slots = max(0, max_concurrent - currently_processing)
    if available_slots <= 0:
        return

    # Pick up to available_slots domains in INIT (not yet scheduled)
    domain_ids = list(
        Domain.objects.filter(track_status__in=['INIT'])
        .order_by('modified_at')
        .values_list('id', flat=True)[:available_slots]
    )

    for domain_id in domain_ids:
        # Mark as scheduled if INIT
        with transaction.atomic():
            domain = Domain.objects.select_for_update().get(id=domain_id)
            if domain.track_status == 'INIT':
                domain.track_status = 'SCHD'
                domain.tracked_at = timezone.now()
                domain.save(update_fields=['track_status', 'tracked_at', 'modified_at'])

        process_domain_task.delay(domain_id)


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_prompt_analytics_task(self, domain_id):
    processor = PromptAnalyticsProcessor(max_concurrent_prompts=getattr(settings, 'MAX_CONCURRENT_PROMPT_ANALYTICS', 10))
    return processor.process_domain(domain_id)


@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_prompt_analytics_scheduler(self):
    processor = PromptAnalyticsProcessor(max_concurrent_prompts=getattr(settings, 'MAX_CONCURRENT_PROMPT_ANALYTICS', 10))
    return processor.schedule_tick()


