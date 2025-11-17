"""
Competitor Extractor for Engine
Wraps the backend competitor extraction service for use in the engine
"""
from django.db.models import Count
from django.utils import timezone
from collections import Counter
import re
from typing import List, Tuple
from shared_models.models import Domain, PromptAnalytics, Competitor


def extract_competitors_for_domain(domain_id: int) -> Tuple[int, List[str]]:
    """
    Extract top competitors from prompt analytics for a domain

    Args:
        domain_id: ID of the domain to extract competitors for

    Returns:
        Tuple of (created_count, list_of_competitor_names)
    """
    try:
        domain = Domain.objects.get(id=domain_id)
    except Domain.DoesNotExist:
        print(f"Domain with ID {domain_id} does not exist")
        return 0, []

    min_competitors = 3
    max_competitors = 5
    min_mentions_threshold = 2

    print(f"Starting competitor extraction for domain: {domain.name}")

    # Step 1: Get all prompt analytics for this domain
    analytics_qs = PromptAnalytics.objects.filter(
        prompt__group__domain=domain
    ).values_list('competitor_mention_list', flat=True)

    # Step 2: Extract and count all competitor mentions
    competitor_counter = Counter()

    for mention_list in analytics_qs:
        if mention_list and isinstance(mention_list, list):
            for competitor_name in mention_list:
                if competitor_name and isinstance(competitor_name, str):
                    # Clean and normalize the competitor name
                    cleaned_name = _clean_competitor_name(competitor_name)
                    if cleaned_name and cleaned_name.lower() != domain.name.lower():
                        competitor_counter[cleaned_name] += 1

    print(f"Found {len(competitor_counter)} unique competitor mentions")

    # Step 3: Filter competitors by minimum threshold
    filtered_competitors = {
        name: count for name, count in competitor_counter.items()
        if count >= min_mentions_threshold
    }

    print(f"Filtered to {len(filtered_competitors)} competitors with >= {min_mentions_threshold} mentions")

    # Step 4: Get top N competitors (between min and max)
    sorted_competitors = sorted(
        competitor_counter.items(),
        key=lambda x: x[1],
        reverse=True
    )
    top_competitors = [
        item for item in sorted_competitors
        if item[0] in filtered_competitors
    ][:max_competitors]
    
    target_count = min(max_competitors, len(sorted_competitors))
    if len(top_competitors) < target_count:
        existing = {name for name, _ in top_competitors}
        for name, count in sorted_competitors:
            if name in existing:
                continue
            top_competitors.append((name, count))
            if len(top_competitors) == target_count:
                break
    
    if len(top_competitors) < min_competitors:
        top_competitors = sorted_competitors[:min_competitors]

    print(f"Selected top {len(top_competitors)} competitors")

    # Step 5: Create Competitor records
    created_competitors = []
    created_count = 0

    for competitor_name, mention_count in top_competitors:
        # Try to extract/guess URL
        competitor_url = _guess_competitor_url(competitor_name)

        # Create or update competitor
        competitor, created = Competitor.objects.get_or_create(
            domain=domain,
            name=competitor_name,
            defaults={
                'url': competitor_url,
                'total_mentions': mention_count,
                'track_status': 'INIT',
                'track_message': 'Auto-extracted from prompt analytics',
                'tracked_at': timezone.now(),
            }
        )

        if created:
            created_count += 1
            created_competitors.append(competitor_name)
            print(f"Created competitor: {competitor_name} ({mention_count} mentions)")
        else:
            # Update mention count if competitor already exists
            if competitor.total_mentions != mention_count:
                competitor.total_mentions = mention_count
                competitor.save()
                print(f"Updated competitor: {competitor_name} ({mention_count} mentions)")

    print(f"Competitor extraction complete. Created {created_count} new competitors.")
    return created_count, created_competitors


def _clean_competitor_name(name: str) -> str:
    """
    Clean and normalize competitor name
    """
    if not name:
        return ""

    # Remove common suffixes and prefixes
    name = name.strip()

    # Remove URL protocols and www
    name = re.sub(r'^https?://(www\.)?', '', name, flags=re.IGNORECASE)

    # Remove trailing slashes and paths
    name = name.split('/')[0]

    # Remove common company suffixes for cleaner names
    suffixes = [
        r'\s+(Inc\.?|LLC|Ltd\.?|Corporation|Corp\.?|Company|Co\.?)$',
        r'\.(com|net|org|io|ai)$'
    ]
    for suffix in suffixes:
        name = re.sub(suffix, '', name, flags=re.IGNORECASE)

    # Capitalize properly
    name = name.strip()

    # If it's all lowercase or all uppercase, title case it
    if name.islower() or name.isupper():
        name = name.title()

    return name


def _guess_competitor_url(competitor_name: str) -> str:
    """
    Attempt to guess competitor URL from name
    """
    # Clean the name for URL
    clean_name = competitor_name.lower().strip()

    # Remove spaces and special characters
    clean_name = re.sub(r'[^a-z0-9]', '', clean_name)

    # Common patterns
    possible_urls = [
        f"https://www.{clean_name}.com",
        f"https://{clean_name}.com",
        f"https://www.{clean_name}.io",
        f"https://{clean_name}.io",
    ]

    # Return the most likely one (first .com)
    return possible_urls[0]
