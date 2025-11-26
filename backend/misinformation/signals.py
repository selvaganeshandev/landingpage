"""
Django Signals for Misinformation Module
Triggers misinformation scans when prompt_analytics is updated.
"""
import logging
import threading
from django.db.models.signals import post_save
from django.dispatch import receiver

from prompts.models import PromptAnalytics

logger = logging.getLogger(__name__)


def run_scan_in_background(domain_id: int, prompt_analytics_ids: list):
    """
    Run misinformation scan in a background thread to avoid blocking the request.
    """
    from .tasks import run_misinformation_scan
    try:
        run_misinformation_scan(
            domain_id=domain_id,
            prompt_analytics_ids=prompt_analytics_ids
        )
        logger.info(f"Misinformation scan completed for domain {domain_id}")
    except Exception as e:
        logger.error(f"Failed to run misinformation scan for domain {domain_id}: {e}")


@receiver(post_save, sender=PromptAnalytics)
def trigger_misinformation_scan(sender, instance, created, **kwargs):
    """
    Trigger misinformation scan when prompt analytics is updated.

    Only triggers for:
    - Completed analytics (track_status='COMP')
    - Analytics where brand is mentioned (is_mention=True)
    """
    # Only process completed analytics with mentions
    if instance.track_status != 'COMP':
        return

    if not instance.is_mention:
        return

    # Check if there are citations to analyze
    citation_list = instance.citation_list or []
    context_summary = instance.context_summary or ""

    if not citation_list and not context_summary:
        return

    logger.info(
        f"Misinformation scan triggered for prompt_analytics {instance.id} "
        f"(domain: {instance.prompt.group.domain_id})"
    )

    # Run scan in background thread to avoid blocking
    domain_id = instance.prompt.group.domain_id
    thread = threading.Thread(
        target=run_scan_in_background,
        args=(domain_id, [instance.id]),
        daemon=True
    )
    thread.start()
