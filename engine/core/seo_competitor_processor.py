"""
SEO Competitor Processor — Aggregates competitor domains from SERP data.

Strategy:
1. First try to read stored snippets_details.competitors (set during rank processing).
2. If a keyword has no stored competitors data, make a fresh DataBlue call
   (single keyword, top results only — far cheaper than full rank processing).
Results are stored in SeoCompetitorAnalysis.analysis_json.
"""
import logging
from urllib.parse import urlparse

from core import datablue_service

logger = logging.getLogger(__name__)

# Domains to exclude from competitor results
EXCLUDE_DOMAINS = {
    'google.com', 'google.co.uk', 'google.co.in', 'google.com.au',
    'youtube.com', 'facebook.com', 'twitter.com', 'instagram.com',
    'linkedin.com', 'pinterest.com', 'reddit.com', 'tiktok.com',
    'wikipedia.org', 'amazon.com', 'ebay.com', 'bing.com', 'yahoo.com',
    'quora.com', 'tumblr.com', 'wordpress.com', 'blogger.com',
    'wix.com', 'squarespace.com', 'shopify.com',
}


def _extract_domain(url: str) -> str:
    if not url:
        return ''
    try:
        parsed = urlparse(url if '://' in url else f'https://{url}')
        domain = (parsed.netloc or parsed.path).lower().replace('www.', '')
        return domain.split('/')[0]
    except Exception:
        return ''


def _fetch_top10_competitors(kw_text: str, region: str, isocode: str,
                              language_code: str, uule: str,
                              platform: str, api_key: str = '') -> dict:
    """
    Fetch SERP via DataBlue and return a competitors dict keyed by rank,
    same shape as parse_json_serp_response produces.

    On the v2 (google-search-v2) endpoint `region` (Google domain), `uule` and
    `platform` (desktop|mobile) ARE forwarded so competitor SERPs match the
    keyword's device/geo. `api_key` is read from Django settings.
    """
    page_json = datablue_service.fetch_one(
        keyword_text=kw_text,
        isocode=isocode,
        language_code=language_code,
        platform=platform,
        region=region,
        uule=uule,
    )
    if not page_json:
        return {}

    competitors = {}
    for item in page_json.get('organic_results', []):
        if not isinstance(item, dict):
            continue
        item_url = item.get('link', '')
        item_domain = _extract_domain(item_url)
        item_rank = item.get('rank') or item.get('position', 0)
        try:
            item_rank = int(item_rank)
        except (ValueError, TypeError):
            item_rank = 0

        if item_rank and item_domain:
            competitors[str(item_rank)] = {
                'url': item_url,
                'domain': item_domain,
                'rank': item_rank,
            }
    return competitors


def analyze_competitors_for_domain(domain_id: int) -> dict:
    """
    Aggregate competitor domains from SERP data for a domain.
    - Uses stored snippets_details.competitors if available.
    - Falls back to a fresh DataBlue call if not.
    Updates SeoCompetitorAnalysis to COMP on success, FAIL on error.
    """
    from shared_models.seo_models import SeoKeywordRank, SeoCompetitorAnalysis
    from django.conf import settings

    try:
        analysis = SeoCompetitorAnalysis.objects.filter(
            domain_id=domain_id, status='SCHD'
        ).first()
        if not analysis:
            logger.warning(f"[CompAnalysis] No SCHD analysis found for domain {domain_id}")
            return {'error': 'no_analysis_record'}

        keywords = list(
            SeoKeywordRank.objects.filter(domain_id=domain_id)
            .select_related('keyword')
        )
        total_kw = len(keywords)

        # Get the project domain to self-exclude
        project_domain_clean = ''
        try:
            from shared_models.models import Domain
            project_domain = Domain.objects.get(id=domain_id)
            project_domain_clean = (project_domain.url or '').lower()
            project_domain_clean = (
                project_domain_clean
                .replace('https://', '').replace('http://', '')
                .replace('www.', '').split('/')[0]
            )
        except Exception:
            pass

        datablue_key = getattr(settings, 'DATABLUE_API_KEY', '') or ''

        domain_counts = {}   # {competitor_domain: hit_count}
        domain_kw_ids = {}   # {competitor_domain: [kw_ids]}
        fresh_calls = 0

        for kw in keywords:
            # Try stored data first
            competitors = {}
            if kw.snippets_details and isinstance(kw.snippets_details, dict):
                competitors = kw.snippets_details.get('competitors', {})

            # Fall back to fresh DataBlue call if no stored competitor data
            if not competitors and datablue_key:
                kw_text = kw.keyword.keyword if kw.keyword else ''
                if kw_text:
                    competitors = _fetch_top10_competitors(
                        kw_text=kw_text,
                        region=kw.region or 'google.com',
                        isocode=kw.isocode or 'us',
                        language_code=kw.language_code or 'en',
                        uule=kw.geo_target_uule or '',
                        platform=kw.platform or 'desktop',
                    )
                    fresh_calls += 1

                    # Cache the fetched competitors so future analyses don't re-fetch
                    if competitors:
                        sd = kw.snippets_details or {}
                        sd['competitors'] = competitors
                        SeoKeywordRank.objects.filter(id=kw.id).update(snippets_details=sd)

            for _rank_str, comp_data in competitors.items():
                if not isinstance(comp_data, dict):
                    continue
                comp_d = comp_data.get('domain', '').lower().replace('www.', '')
                if not comp_d:
                    continue
                if project_domain_clean and (
                    comp_d == project_domain_clean or
                    project_domain_clean in comp_d or
                    comp_d in project_domain_clean
                ):
                    continue
                if comp_d in EXCLUDE_DOMAINS:
                    continue

                domain_counts[comp_d] = domain_counts.get(comp_d, 0) + 1
                domain_kw_ids.setdefault(comp_d, []).append(kw.id)

        sorted_domains = dict(
            sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:100]
        )

        SeoCompetitorAnalysis.objects.filter(id=analysis.id).update(
            status='COMP',
            total_keywords=total_kw,
            unique_domains=len(sorted_domains),
            total_domain_hits=sum(sorted_domains.values()) if sorted_domains else 0,
            analysis_json={
                'domains': sorted_domains,
                'keys': domain_kw_ids,
            },
        )

        logger.info(
            f"[CompAnalysis] Domain {domain_id}: {total_kw} keywords → "
            f"{len(sorted_domains)} unique competitors "
            f"({fresh_calls} fresh SERP calls made)"
        )
        return {
            'success': True,
            'total_keywords': total_kw,
            'unique_domains': len(sorted_domains),
            'fresh_calls': fresh_calls,
        }

    except Exception as e:
        logger.error(f"[CompAnalysis] Error for domain {domain_id}: {e}", exc_info=True)
        try:
            from shared_models.seo_models import SeoCompetitorAnalysis
            SeoCompetitorAnalysis.objects.filter(
                domain_id=domain_id, status='SCHD'
            ).update(status='FAIL')
        except Exception:
            pass
        return {'error': str(e)}
