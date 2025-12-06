"""
Signal handlers for competitor model events
"""
import logging
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.db import transaction
from .models import Competitor

logger = logging.getLogger(__name__)

# Track domains that need syncing (to debounce rapid signals)
_pending_sync_domains = set()


@receiver(post_save, sender=Competitor)
def sync_competitor_on_create(sender, instance, created, **kwargs):
    """
    Automatically sync CompetitorPromptAnalytics when a new competitor is added.
    This ensures historical prompt mentions are immediately visible in the UI.

    DEBOUNCING: If multiple competitors are added rapidly for the same domain,
    we schedule a single sync operation using transaction.on_commit() to avoid
    race conditions and duplicate work.
    """
    if created:  # Only run for newly created competitors
        logger.info(f"New competitor added: {instance.name} (ID: {instance.id}) for domain {instance.domain_id}")

        domain_id = instance.domain_id

        # Check if sync is already pending for this domain
        if domain_id in _pending_sync_domains:
            logger.info(f"Sync already pending for domain {domain_id}, skipping duplicate")
            return

        # Mark this domain as pending sync
        _pending_sync_domains.add(domain_id)

        def run_sync():
            """Execute sync after transaction commits, then remove from pending set"""
            try:
                # Import here to avoid circular dependency
                from .utils import sync_competitor_prompt_analytics

                logger.info(f"Running automatic sync for domain {domain_id} after transaction commit")
                stats = sync_competitor_prompt_analytics(domain_id=domain_id)
                logger.info(f"Automatic sync completed for domain {domain_id}: {stats}")

            except Exception as e:
                logger.error(f"Error in automatic sync for domain {domain_id}: {str(e)}", exc_info=True)
                # Don't raise - we don't want to block competitor creation if sync fails
            finally:
                # Remove from pending set
                _pending_sync_domains.discard(domain_id)

        # Schedule sync to run AFTER the transaction commits
        # This ensures all competitors are saved before sync runs
        transaction.on_commit(run_sync)
