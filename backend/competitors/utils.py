"""
Utility functions for competitor analytics synchronization
"""
import logging
from django.db import transaction
from django.utils import timezone
from competitors.models import Competitor, CompetitorPromptAnalytics
from prompts.models import PromptAnalytics

logger = logging.getLogger(__name__)


def sync_competitor_prompt_analytics(domain_id=None, prompt_id=None):
    """
    Sync CompetitorPromptAnalytics from PromptAnalytics.competitor_mention_list

    This function reads competitor mentions from PromptAnalytics and populates
    the CompetitorPromptAnalytics table for efficient querying.

    Args:
        domain_id: If provided, only sync prompts for this domain
        prompt_id: If provided, only sync this specific prompt

    Returns:
        dict with sync statistics
    """
    stats = {
        'created': 0,
        'updated': 0,
        'skipped': 0,
        'errors': 0
    }

    try:
        # Build queryset for PromptAnalytics
        queryset = PromptAnalytics.objects.select_related('prompt', 'prompt__group', 'prompt__group__domain')

        if domain_id:
            queryset = queryset.filter(prompt__group__domain_id=domain_id)

        if prompt_id:
            queryset = queryset.filter(prompt_id=prompt_id)

        # Get all competitors for the domain(s) for name matching
        if domain_id:
            competitors = list(Competitor.objects.filter(domain_id=domain_id).values('id', 'name', 'domain_id'))
        else:
            competitors = list(Competitor.objects.all().values('id', 'name', 'domain_id'))

        # Build competitor name lookup map (case-insensitive)
        competitor_map = {}
        for comp in competitors:
            key = (comp['domain_id'], comp['name'].lower())
            competitor_map[key] = comp['id']

        logger.info(f"Starting sync for {queryset.count()} PromptAnalytics records...")

        # Process each PromptAnalytics record
        for pa in queryset:
            try:
                if not pa.competitor_mention_list or not isinstance(pa.competitor_mention_list, list):
                    continue

                domain_id_for_prompt = pa.prompt.group.domain_id

                # Process each mentioned competitor
                for competitor_name in pa.competitor_mention_list:
                    if not competitor_name:
                        continue

                    # Find competitor ID
                    key = (domain_id_for_prompt, competitor_name.lower())
                    competitor_id = competitor_map.get(key)

                    if not competitor_id:
                        logger.warning(f"Competitor '{competitor_name}' not found for domain {domain_id_for_prompt}")
                        stats['skipped'] += 1
                        continue

                    # Create or update CompetitorPromptAnalytics
                    # IMPORTANT: Don't copy citation_list from PromptAnalytics as it contains ALL citations
                    # for the entire response, not specific citations for each competitor
                    empty_citation_list = []
                    logger.debug(f"Creating CompetitorPromptAnalytics with empty citation_list for {competitor_name}")

                    with transaction.atomic():
                        obj, created = CompetitorPromptAnalytics.objects.update_or_create(
                            competitor_id=competitor_id,
                            prompt_id=pa.prompt_id,
                            platform=pa.platform or 'ChatGPT',
                            defaults={
                                'is_mentioned': True,
                                'mention_count': 1,  # Basic count - could be enhanced
                                'position': int(pa.position) if pa.position else None,
                                'sentiment_category': pa.sentiment_category,
                                'sentiment_score': pa.sentiment_score,
                                'citation_list': empty_citation_list,
                                'track_status': 'COMP',
                                'tracked_at': timezone.now(),
                            }
                        )

                        if created:
                            stats['created'] += 1
                        else:
                            stats['updated'] += 1

            except Exception as e:
                logger.error(f"Error processing PromptAnalytics {pa.id}: {str(e)}")
                stats['errors'] += 1
                continue

        logger.info(f"Sync completed: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Sync failed: {str(e)}")
        stats['errors'] += 1
        return stats
