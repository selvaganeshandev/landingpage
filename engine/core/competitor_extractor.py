"""
Competitor Extractor for Engine
Wraps the backend competitor extraction service for use in the engine
"""
from django.db.models import Count
from django.utils import timezone
from collections import Counter
import re
from typing import List, Tuple, Dict
from shared_models.models import Domain, PromptAnalytics, Competitor, Prompt
import logging

logger = logging.getLogger(__name__)


def _identify_domain_niche(domain: Domain) -> Dict[str, any]:
    """
    Identify the business niche/category of a domain based on its prompts.

    Returns:
        Dict with 'niche', 'keywords', and 'description'
    """
    # Get sample prompts to understand the business
    prompts = Prompt.objects.filter(group__domain=domain)[:10]
    prompt_texts = ' '.join([p.prompt.lower() for p in prompts])

    # Define niche patterns with keywords
    niche_patterns = {
        'insurance_comparison': {
            'keywords': ['insurance', 'policy', 'premium', 'coverage', 'insurer', 'term insurance', 'health insurance', 'life insurance', 'car insurance', 'compare insurance', 'insurance aggregator'],
            'description': 'Insurance comparison and aggregation platforms',
            'relevant_competitors': ['insurance', 'policy', 'bazaar', 'cover', 'assurance', 'insure']
        },
        'clone_scripts': {
            'keywords': ['clone', 'script', 'airbnb clone', 'uber clone', 'vrbo', 'rental script', 'marketplace script'],
            'description': 'Clone scripts and marketplace software',
            'relevant_competitors': ['sharetribe', 'rent', 'marketplace', 'script', 'clone']
        },
        'classified_ads': {
            'keywords': ['classified', 'classifieds', 'ad posting', 'listing', 'directory'],
            'description': 'Classified advertising platforms',
            'relevant_competitors': ['classified', 'listing', 'directory', 'ads', 'post']
        },
        'ecommerce': {
            'keywords': ['ecommerce', 'e-commerce', 'online store', 'shopping cart', 'product catalog'],
            'description': 'E-commerce platforms',
            'relevant_competitors': ['shop', 'commerce', 'cart', 'store', 'woo']
        },
        'no_code': {
            'keywords': ['no-code', 'no code', 'app builder', 'website builder', 'drag and drop'],
            'description': 'No-code development platforms',
            'relevant_competitors': ['builder', 'no-code', 'nocode', 'visual']
        },
        'saas': {
            'keywords': ['saas', 'subscription', 'cloud', 'software as a service'],
            'description': 'SaaS platforms',
            'relevant_competitors': ['cloud', 'saas', 'subscription']
        }
    }

    # Score each niche based on keyword matches
    niche_scores = {}
    for niche_name, niche_data in niche_patterns.items():
        score = sum(1 for keyword in niche_data['keywords'] if keyword in prompt_texts)
        if score > 0:
            niche_scores[niche_name] = score

    # Get the top niche
    if niche_scores:
        top_niche = max(niche_scores, key=niche_scores.get)
        return niche_patterns[top_niche]

    # Default to general business if no clear niche
    return {
        'keywords': [],
        'description': 'General business software',
        'relevant_competitors': []
    }


def _score_competitor_relevance(competitor_name: str, domain_niche: Dict[str, any]) -> float:
    """
    Score how relevant a competitor is to the domain's niche.

    Returns:
        Float between 0.0 and 1.0 (higher is more relevant)
    """
    comp_lower = competitor_name.lower()

    # Base score starts at 0.5 (neutral)
    score = 0.5

    # Boost score if competitor name contains niche-relevant keywords
    relevant_keywords = domain_niche.get('relevant_competitors', [])
    for keyword in relevant_keywords:
        if keyword in comp_lower:
            score += 0.2
            break

    # Penalize if competitor is a well-known general platform (not niche-specific)
    general_platforms = ['shopify', 'magento', 'woocommerce', 'wordpress', 'squarespace',
                        'wix', 'google', 'facebook', 'amazon', 'microsoft']
    if any(platform in comp_lower for platform in general_platforms):
        score -= 0.3

    # Special boost for insurance comparison platforms
    if domain_niche.get('description', '').lower().find('insurance') >= 0:
        # Tier 1: Major insurance aggregators/comparison platforms (highest relevance)
        tier1_insurance = ['coverfox', 'insurancedekho', 'turtlemint', 'easypolicy', 'renewbuy']
        if any(provider in comp_lower for provider in tier1_insurance):
            score = 0.9  # Very high relevance

        # Tier 2: Insurance-related keywords in name
        elif any(keyword in comp_lower for keyword in ['insurance', 'policy', 'cover', 'assure']):
            score = 0.7  # High relevance

    # Special boost for known clone script/marketplace providers
    elif domain_niche.get('description', '').lower().find('clone') >= 0 or \
         domain_niche.get('description', '').lower().find('marketplace') >= 0:

        # Tier 1: Premium marketplace/rental script providers (highest relevance)
        tier1_providers = ['rentall', 'sharetribe', 'trioangle', 'yo!rent', 'rentnow']
        if any(provider in comp_lower for provider in tier1_providers):
            score = 0.9  # Very high relevance

        # Tier 2: Classified script providers (high relevance)
        elif any(indicator in comp_lower for indicator in ['flynax', 'oxy', 'classipress', 'classified']):
            score = 0.7  # High relevance

        # Tier 3: General script/clone indicators
        elif any(indicator in comp_lower for indicator in ['script', 'clone', 'rental', 'marketplace']):
            score += 0.2

    # Ensure score is between 0 and 1
    return max(0.0, min(1.0, score))


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

    # Step 3.5: Identify domain niche for relevance scoring
    domain_niche = _identify_domain_niche(domain)
    logger.info(f"Identified niche for {domain.name}: {domain_niche.get('description')}")
    print(f"Identified niche: {domain_niche.get('description')}")

    # Step 4: Score and sort competitors by relevance + mention count
    # Prioritize niche relevance heavily over mention frequency
    competitor_scores = []
    for name, count in competitor_counter.items():
        relevance_score = _score_competitor_relevance(name, domain_niche)
        # Composite score: (mention_count * 0.2) + (relevance * 10 * 0.8)
        # This prioritizes niche relevance (80%) over frequency (20%)
        composite_score = (count * 0.2) + (relevance_score * 10 * 0.8)
        competitor_scores.append((name, count, relevance_score, composite_score))
        logger.debug(f"Competitor: {name}, mentions={count}, relevance={relevance_score:.2f}, composite={composite_score:.2f}")

    # Sort by composite score (relevance + mentions)
    sorted_competitors = sorted(
        competitor_scores,
        key=lambda x: x[3],  # Sort by composite score
        reverse=True
    )

    # Filter by relevance threshold (only include if relevance > 0.4 OR high mentions)
    quality_competitors = [
        (name, count) for name, count, relevance, composite in sorted_competitors
        if relevance >= 0.4 or count >= 5  # Either relevant OR mentioned a lot
    ]

    # Apply minimum threshold filter
    quality_competitors = [
        item for item in quality_competitors
        if item[0] in filtered_competitors
    ]

    # Select top N
    top_competitors = quality_competitors[:max_competitors]

    # Ensure minimum count
    if len(top_competitors) < min_competitors and len(quality_competitors) >= min_competitors:
        top_competitors = quality_competitors[:min_competitors]

    print(f"Selected top {len(top_competitors)} niche-relevant competitors")
    for name, count in top_competitors:
        matching_score = [s for s in sorted_competitors if s[0] == name]
        if matching_score:
            relevance = matching_score[0][2]
            print(f"  - {name}: {count} mentions, relevance={relevance:.2f}")

    # Step 5: Create Competitor records
    created_competitors = []
    created_count = 0

    # Real cited hosts for this domain, keyed by brand label. The URL was
    # previously GUESSED as https://www.<name>.com and never checked, which is
    # why 98% of competitor records pointed at a fabricated address —
    # wikipedia.org was stored as wikipedia.com, and Zerodha's own
    # kite.zerodha.com became an unrelated business at kite.com. The real URL
    # is already in citation_list; use it.
    real_urls = _cited_urls_by_brand(domain)

    for competitor_name, mention_count in top_competitors:
        competitor_url = real_urls.get(competitor_name.lower()) or _guess_competitor_url(competitor_name)

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


def _cited_urls_by_brand(domain):
    """{brand label -> real https://<registrable domain>} from cited URLs.

    Built from the citation lists the engine already stores, so a competitor's
    address is something an AI actually linked to rather than a guess. Where a
    brand was never cited by URL we fall back to guessing, and the caller marks
    nothing — but at least the guess is no longer the default.
    """
    from collections import Counter
    from core.analytics_helpers import _get_domain_from_url, _registrable_domain

    hosts = Counter()
    qs = PromptAnalytics.objects.filter(
        prompt__group__domain=domain
    ).values_list('citation_list', flat=True)
    for citation_list in qs:
        if not isinstance(citation_list, list):
            continue
        for entry in citation_list:
            url = None
            if isinstance(entry, dict):
                for field in ('url', 'source', 'link', 'href', 'uri'):
                    value = entry.get(field)
                    if value and isinstance(value, str):
                        url = value
                        break
            elif isinstance(entry, str):
                url = entry
            if not url:
                continue
            registrable = _registrable_domain(_get_domain_from_url(url))
            if registrable:
                hosts[registrable] += 1

    out = {}
    for registrable, _count in hosts.most_common():
        label = registrable.split('.')[0]
        out.setdefault(label.lower(), f"https://{registrable}")
    return out


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
