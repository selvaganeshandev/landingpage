"""
Utility functions for competitor analytics synchronization
"""
import logging
import re
from django.db import transaction
from django.utils import timezone
from django.db.models import Q, Sum, Avg
from competitors.models import Competitor, CompetitorPromptAnalytics
from prompts.models import PromptAnalytics

logger = logging.getLogger(__name__)


def extract_competitor_citations(citation_list, competitor_name):
    """
    Extract citations that mention a specific competitor.

    Args:
        citation_list: List of citation objects/dicts from PromptAnalytics
        competitor_name: Name of the competitor to search for

    Returns:
        List of citations mentioning this competitor
    """
    if not citation_list or not competitor_name:
        return []

    competitor_citations = []
    # Create case-insensitive pattern to match competitor name
    pattern = re.compile(re.escape(competitor_name), re.IGNORECASE)

    for citation in citation_list:
        # Handle both dict and string citation formats
        citation_text = ""
        if isinstance(citation, dict):
            citation_text = str(citation.get('text', '')) + ' ' + str(citation.get('source', ''))
        elif isinstance(citation, str):
            citation_text = citation
        else:
            citation_text = str(citation)

        # Check if competitor name appears in citation
        if pattern.search(citation_text):
            competitor_citations.append(citation)

    return competitor_citations


def count_competitor_mentions(competitor_mention_list, competitor_name, context_summary=""):
    """
    Count how many times a competitor is mentioned.

    Args:
        competitor_mention_list: List of competitor names from PromptAnalytics
        competitor_name: Name of the competitor to count
        context_summary: Optional context text to search for additional mentions

    Returns:
        Integer count of mentions
    """
    if not competitor_mention_list:
        return 0

    count = 0

    # Count occurrences in competitor_mention_list
    # Handle both list of strings and list with duplicates
    for mentioned_name in competitor_mention_list:
        if isinstance(mentioned_name, str) and mentioned_name.lower() == competitor_name.lower():
            count += 1

    # If no direct match found, check if it's mentioned at all
    if count == 0:
        case_insensitive_matches = [
            name for name in competitor_mention_list
            if isinstance(name, str) and name.lower() == competitor_name.lower()
        ]
        if case_insensitive_matches:
            count = 1

    # Additional context-based counting (optional enhancement)
    if context_summary and count > 0:
        # Count additional explicit mentions in context
        pattern = re.compile(r'\b' + re.escape(competitor_name) + r'\b', re.IGNORECASE)
        context_mentions = len(pattern.findall(context_summary))
        # Use max of list count and context count
        count = max(count, context_mentions)

    return max(count, 1) if count > 0 or competitor_name.lower() in [
        name.lower() for name in competitor_mention_list if isinstance(name, str)
    ] else 0


def sync_competitor_prompt_analytics(domain_id=None, prompt_id=None, batch_size=100):
    """
    Sync CompetitorPromptAnalytics from PromptAnalytics.competitor_mention_list

    This function reads competitor mentions from PromptAnalytics and populates
    the CompetitorPromptAnalytics table with accurate metrics per competitor per platform.

    SCALABILITY FEATURES:
    - Batch processing to handle large datasets
    - Efficient database queries with select_related
    - Bulk create/update operations
    - Proper indexing on lookup fields

    Args:
        domain_id: If provided, only sync prompts for this domain
        prompt_id: If provided, only sync this specific prompt
        batch_size: Number of records to process in each batch (default: 100)

    Returns:
        dict with sync statistics
    """
    stats = {
        'created': 0,
        'updated': 0,
        'skipped': 0,
        'errors': 0,
        'processed_prompts': 0,
    }

    try:
        # Build queryset for PromptAnalytics with optimizations
        queryset = PromptAnalytics.objects.select_related(
            'prompt',
            'prompt__group',
            'prompt__group__domain'
        )

        if domain_id:
            queryset = queryset.filter(prompt__group__domain_id=domain_id)

        if prompt_id:
            queryset = queryset.filter(prompt_id=prompt_id)

        # Only process completed analytics with competitor mentions
        # Use prompt__track_status since PromptAnalytics.track_status is not updated
        queryset = queryset.filter(
            prompt__track_status='COMP',  # Only process completed prompts
            ~Q(competitor_mention_list=[]) & ~Q(competitor_mention_list__isnull=True)
        )

        total_records = queryset.count()
        logger.info(f"Starting sync for {total_records} PromptAnalytics records with competitor mentions...")

        # Get all competitors for efficient lookup (with prefetch for scalability)
        if domain_id:
            competitors = list(Competitor.objects.filter(domain_id=domain_id).values('id', 'name', 'domain_id'))
        else:
            competitors = list(Competitor.objects.all().values('id', 'name', 'domain_id'))

        # Build competitor name lookup map (case-insensitive for better matching)
        competitor_map = {}
        for comp in competitors:
            key = (comp['domain_id'], comp['name'].lower())
            competitor_map[key] = comp['id']

        # Process in batches for scalability
        offset = 0
        while offset < total_records:
            batch = queryset[offset:offset + batch_size]
            batch_updates = []
            batch_creates = []

            for pa in batch:
                try:
                    if not pa.competitor_mention_list or not isinstance(pa.competitor_mention_list, list):
                        stats['skipped'] += 1
                        continue

                    domain_id_for_prompt = pa.prompt.group.domain_id
                    platform = pa.platform or 'ChatGPT'

                    # Process each mentioned competitor
                    for competitor_name in set(pa.competitor_mention_list):  # Use set to avoid duplicates
                        if not competitor_name or not isinstance(competitor_name, str):
                            continue

                        # Find competitor ID
                        key = (domain_id_for_prompt, competitor_name.lower())
                        competitor_id = competitor_map.get(key)

                        if not competitor_id:
                            logger.warning(f"Competitor '{competitor_name}' not found for domain {domain_id_for_prompt}")
                            stats['skipped'] += 1
                            continue

                        # Count actual mentions of this specific competitor
                        mention_count = count_competitor_mentions(
                            pa.competitor_mention_list,
                            competitor_name,
                            pa.context_summary
                        )

                        # Extract competitor-specific citations
                        competitor_citations = extract_competitor_citations(
                            pa.citation_list,
                            competitor_name
                        )

                        # Prepare data for this competitor
                        defaults = {
                            'is_mentioned': True,
                            'mention_count': mention_count,
                            'position': int(pa.position) if pa.position else None,
                            'sentiment_category': pa.sentiment_category,
                            'sentiment_score': pa.sentiment_score,
                            'citation_list': competitor_citations,
                            'track_status': 'COMP',
                            'tracked_at': timezone.now(),
                        }

                        # Use update_or_create for each record
                        # This is more reliable than bulk operations for update scenarios
                        with transaction.atomic():
                            obj, created = CompetitorPromptAnalytics.objects.update_or_create(
                                competitor_id=competitor_id,
                                prompt_id=pa.prompt_id,
                                platform=platform,
                                defaults=defaults
                            )

                            if created:
                                stats['created'] += 1
                                logger.debug(f"Created CompetitorPromptAnalytics: {competitor_name} | {platform} | {mention_count} mentions | {len(competitor_citations)} citations")
                            else:
                                stats['updated'] += 1
                                logger.debug(f"Updated CompetitorPromptAnalytics: {competitor_name} | {platform} | {mention_count} mentions | {len(competitor_citations)} citations")

                    stats['processed_prompts'] += 1

                except Exception as e:
                    logger.error(f"Error processing PromptAnalytics {pa.id}: {str(e)}", exc_info=True)
                    stats['errors'] += 1
                    continue

            offset += batch_size
            logger.info(f"Processed batch: {offset}/{total_records} ({(offset/total_records*100):.1f}%)")

        # After syncing all CompetitorPromptAnalytics, update Competitor.total_citations
        # This ensures the aggregated field matches the sum across all platforms
        logger.info("Updating Competitor total_citations aggregated field...")

        # Get all competitors that were potentially updated
        if domain_id:
            competitors_to_update = Competitor.objects.filter(domain_id=domain_id)
        else:
            competitors_to_update = Competitor.objects.all()

        updated_competitors = 0
        for competitor in competitors_to_update:
            # Calculate total citations across all platforms
            total_citations = 0
            comp_analytics = CompetitorPromptAnalytics.objects.filter(
                competitor=competitor,
                is_mentioned=True
            )

            for ca in comp_analytics:
                if ca.citation_list and isinstance(ca.citation_list, list):
                    total_citations += len(ca.citation_list)

            # Calculate total mentions across all platforms
            total_mentions = comp_analytics.aggregate(
                total=Sum('mention_count')
            )['total'] or 0

            # Calculate average position across all platforms (where position is not null)
            avg_position = comp_analytics.filter(position__isnull=False).aggregate(
                avg=Avg('position')
            )['avg'] or 0

            # Calculate average sentiment across all platforms (where sentiment is not null)
            avg_sentiment = comp_analytics.filter(sentiment_score__isnull=False).aggregate(
                avg=Avg('sentiment_score')
            )['avg'] or 0

            # Calculate visibility score based on average position (100 - position * 20, capped at 0-100)
            visibility = 100.0 - (float(avg_position) * 20.0) if avg_position > 0 else 0.0
            visibility = max(0.0, min(100.0, visibility))

            # Update the competitor's aggregated fields
            fields_to_update = []

            if competitor.total_citations != total_citations:
                competitor.total_citations = total_citations
                fields_to_update.append('total_citations')

            if competitor.total_mentions != total_mentions:
                competitor.total_mentions = total_mentions
                fields_to_update.append('total_mentions')

            if float(competitor.average_position) != round(float(avg_position), 2):
                competitor.average_position = round(float(avg_position), 2)
                fields_to_update.append('average_position')

            if float(competitor.sentiment_score) != round(float(avg_sentiment), 2):
                competitor.sentiment_score = round(float(avg_sentiment), 2)
                fields_to_update.append('sentiment_score')

            if float(competitor.visibility_score) != round(visibility, 2):
                competitor.visibility_score = round(visibility, 2)
                fields_to_update.append('visibility_score')

            if fields_to_update:
                competitor.save(update_fields=fields_to_update)
                updated_competitors += 1
                logger.debug(
                    f"Updated {competitor.name}: "
                    f"{total_mentions} mentions, {total_citations} citations, "
                    f"avg position: {avg_position:.2f}, visibility: {visibility:.2f}, "
                    f"sentiment: {avg_sentiment:.2f}"
                )

        logger.info(f"Updated {updated_competitors} competitor aggregated fields")

        logger.info(f"Sync completed successfully: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Sync failed: {str(e)}", exc_info=True)
        stats['errors'] += 1
        return stats
