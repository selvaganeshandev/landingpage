"""Turn Search Console queries into seeds for prompt generation.

The generation wizard writes questions from a brand brief. This reads the
questions people actually typed instead — the only source in the product based
on real language rather than invented language.

Two rules decide what survives, and both follow from what the product measures:

Branded queries are dropped outright. Visibility monitoring asks whether an LLM
names you to someone who does not know you exist; someone who types your brand
name into ChatGPT will be shown you regardless, so those queries answer a
question nobody asked. On a typical site they are also the majority of traffic —
the top Search Console queries for one live domain are "pivotroots",
"pivot roots", "pivotroots bangalore", "pivotroots digital private limited".

What remains is tiered by whether an answer to it would name any brand at all. A
prompt whose answer is a paragraph of explanation teaches nothing about
visibility. Decision-intent queries — "best crm for small business",
"alternatives to X", "cheapest Y in Mumbai" — force the model to produce a list
of names, which is exactly where a brand either appears or does not.

Ranking within a tier uses impressions rather than clicks. Clicks measure demand
already won; impressions at a weak position measure demand being lost, which is
the demand worth monitoring.
"""
import logging
import re

logger = logging.getLogger(__name__)

# Google caps a Search Analytics request at 25,000 rows. A thousand is deep
# enough to reach the long tail on a mid-size site without the response getting
# unwieldy, and the branded head is stripped from it anyway.
QUERY_ROW_LIMIT = 1000

# Comparison and shortlist language. These make a model answer with names, which
# is the only kind of answer visibility can be measured in — and they frequently
# carry no question word at all, which is why word shape alone is a poor filter.
_DECISION_MARKERS = {
    'best', 'top', 'vs', 'versus', 'alternative', 'alternatives', 'compare',
    'comparison', 'cheapest', 'cheap', 'affordable', 'leading', 'recommended',
    'review', 'reviews', 'rated', 'rating', 'which', 'near', 'nearby', 'list',
    'options', 'providers', 'companies', 'agencies', 'vendors', 'suppliers',
    'services', 'tools', 'software', 'platforms', 'brands',
}

# Advice-shaped questions: a buyer working out how to choose. They name brands
# often enough to be worth tracking, just less reliably than the above.
_ADVISORY_MARKERS = {
    'how', 'what', 'which', 'who', 'where', 'when', 'why', 'should', 'need',
    'choose', 'choosing', 'select', 'pick', 'worth', 'better', 'difference',
}

TIER_DECISION = 1
TIER_ADVISORY = 2
TIER_INFORMATIONAL = 3

TIER_LABELS = {
    TIER_DECISION: 'Decision intent',
    TIER_ADVISORY: 'Advice question',
    TIER_INFORMATIONAL: 'Informational',
}


def _tokens(text):
    return {w for w in re.findall(r"[a-z0-9]+", (text or '').lower())}


def brand_tokens(domain):
    """Words that make a query branded: the brand name and its host.

    Both are needed. "artiscent perfume" is branded through the name; a query
    carrying only the bare domain — "utimf" — is branded through the host, and
    the two often differ.
    """
    tokens = _tokens(domain.name)

    host = (domain.url or '').lower()
    host = re.sub(r'^https?://', '', host).split('/')[0]
    host = host[4:] if host.startswith('www.') else host
    # Drop the public suffix: "co", "in", "com" are not brand words, and
    # treating them as such would mark every query mentioning a country branded.
    tokens |= {p for p in host.split('.')[:-1] if len(p) > 2}

    # A brand written as one word in the domain but spaced in queries —
    # "pivotroots" against "pivot roots" — only matches once the concatenation
    # itself is a token, which it already is above. Nothing further is needed.
    return {t for t in tokens if len(t) > 2}


def is_branded(query, brand):
    """True when the searcher already knew the brand."""
    q = (query or '').lower()
    words = _tokens(q)
    if words & brand:
        return True
    # Catches "pivotrootsbangalore" and misspellings joined to the brand, which
    # tokenising alone misses.
    compact = re.sub(r'[^a-z0-9]', '', q)
    return any(len(b) > 3 and b in compact for b in brand)


def classify(query):
    """Which tier a non-branded query belongs to."""
    words = _tokens(query)
    if words & _DECISION_MARKERS:
        return TIER_DECISION
    if words & _ADVISORY_MARKERS or (query or '').strip().endswith('?'):
        return TIER_ADVISORY
    return TIER_INFORMATIONAL


def rank_candidates(rows, domain, min_words=3, limit=100):
    """Filter and order Search Console rows into prompt seeds.

    `rows` are Search Console API rows: {keys: [query], impressions, clicks,
    ctr, position}. Returns dicts ready for the review table, best first.
    """
    brand = brand_tokens(domain)
    candidates, branded_dropped, short_dropped = [], 0, 0

    for row in rows or []:
        keys = row.get('keys') or []
        query = (keys[0] if keys else '').strip()
        if not query:
            continue

        if is_branded(query, brand):
            branded_dropped += 1
            continue

        # Below three words a query is usually a bare category ("crm software")
        # rather than something a person would type into a chat assistant.
        if len(query.split()) < min_words:
            short_dropped += 1
            continue

        impressions = int(row.get('impressions') or 0)
        position = float(row.get('position') or 0)
        tier = classify(query)

        # Demand you are losing counts for more than demand you already win, so
        # a weak average position lifts a query rather than sinking it.
        losing = position > 10
        candidates.append({
            'query': query,
            'impressions': impressions,
            'clicks': int(row.get('clicks') or 0),
            'position': round(position, 1),
            'tier': tier,
            'tier_label': TIER_LABELS[tier],
            'sort_key': (tier, 0 if losing else 1, -impressions),
        })

    candidates.sort(key=lambda c: c['sort_key'])
    for c in candidates:
        c.pop('sort_key', None)

    logger.info(
        "[GSCSeeds] domain %s: %s candidates (%s branded, %s too short of %s rows)",
        domain.id, len(candidates), branded_dropped, short_dropped, len(rows or []),
    )
    return candidates[:limit], {
        'total_rows': len(rows or []),
        'branded_dropped': branded_dropped,
        'short_dropped': short_dropped,
    }


def fetch_search_console_queries(integration, site_url, days=90):
    """Pull the long tail from Search Console, ordered by impressions.

    Ordered by impressions, not clicks, and a thousand rows deep: the stored
    GSCTrafficInsight keeps only the top 100 by clicks, which is the branded
    head this feature exists to throw away.
    """
    from datetime import date, timedelta

    from googleapiclient.discovery import build
    from integrations.google_oauth import get_credentials_from_integration

    credentials = get_credentials_from_integration(integration)
    if not credentials:
        raise RuntimeError('Search Console credentials are no longer valid.')

    service = build('searchconsole', 'v1', credentials=credentials)
    end = date.today()
    start = end - timedelta(days=days)

    response = service.searchanalytics().query(
        siteUrl=site_url,
        body={
            'startDate': start.strftime('%Y-%m-%d'),
            'endDate': end.strftime('%Y-%m-%d'),
            'dimensions': ['query'],
            'rowLimit': QUERY_ROW_LIMIT,
            'orderBys': [{'dimension': 'impressions', 'sortOrder': 'DESCENDING'}],
        },
    ).execute()

    return response.get('rows', [])
