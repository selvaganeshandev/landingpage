"""
Signal handlers for competitor model events
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Competitor

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Competitor)
def sync_competitor_on_create(sender, instance, created, **kwargs):
    """
    Automatically sync CompetitorPromptAnalytics when a new competitor is added.
    This ensures historical prompt mentions are immediately visible in the UI.
    """
    if created:  # Only run for newly created competitors
        logger.info(f"New competitor added: {instance.name} (ID: {instance.id}) for domain {instance.domain_id}")

        try:
            # Import here to avoid circular dependency
            from .utils import sync_competitor_prompt_analytics

            logger.info(f"Running automatic sync for domain {instance.domain_id} after adding competitor '{instance.name}'")
            stats = sync_competitor_prompt_analytics(domain_id=instance.domain_id)
            logger.info(f"Automatic sync completed for competitor '{instance.name}': {stats}")

        except Exception as e:
            logger.error(f"Error in automatic sync for competitor '{instance.name}': {str(e)}", exc_info=True)
            # Don't raise - we don't want to block competitor creation if sync fails
