"""
Signal handlers for prompt analytics events
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import PromptAnalytics

logger = logging.getLogger(__name__)


@receiver(post_save, sender=PromptAnalytics)
def sync_competitors_on_prompt_completion(sender, instance, created, **kwargs):
    """
    Automatically sync competitor aggregated fields when a prompt is processed.
    This ensures competitor metrics stay up-to-date as new prompts are analyzed.
    """
    # Only sync when track_status changes to COMP (completed)
    if instance.track_status == 'COMP' and instance.competitor_mention_list:
        try:
            # Import here to avoid circular dependency
            from competitors.utils import sync_competitor_prompt_analytics

            domain_id = instance.prompt.group.domain_id
            logger.info(f"Prompt {instance.prompt_id} completed with competitor mentions. Triggering sync for domain {domain_id}")

            # Run sync for this domain to update aggregated fields
            stats = sync_competitor_prompt_analytics(domain_id=domain_id)
            logger.info(f"Auto-sync completed for domain {domain_id}: {stats}")

        except Exception as e:
            logger.error(f"Error in auto-sync after prompt completion: {str(e)}", exc_info=True)
            # Don't raise - we don't want to block prompt processing if sync fails
