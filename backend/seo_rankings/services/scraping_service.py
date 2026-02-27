"""
SEO Ranking Engine — Scraping and orchestration service.
Ported from Rankmax: automation_proxy.py + automation_engine.py + centralised.py

This is the main entry point that:
1. Calls ScrapingDog API for each keyword
2. Parses the SERP response
3. Saves rank data to PostgreSQL
4. Recalculates domain-level metrics
"""
import logging
import urllib.parse
import base64
from datetime import date, datetime

import requests
from django.conf import settings
from django.db import transaction

from seo_rankings.models import (
    SeoKeywordRank, SeoRankHistory, SeoSerpFeatureHistory, SeoDomainDailyMetrics
)
from seo_rankings.services.parser_service import parse_json_serp_response, extract_domain
from seo_rankings.services.score_service import (
    compute_rank_changes, calculate_domain_daily_metrics, check_status, rank_formulation
)

logger = logging.getLogger(__name__)

# ScrapingDog API endpoint
SCRAPINGDOG_URL = "https://api.scrapingdog.com/google"


def _get_api_key():
    """Get ScrapingDog API key from Django settings."""
    return getattr(settings, 'SCRAPINGDOG_API_KEY', None) or ''


def _generate_uule(location):
    """
    Generate UULE parameter for Google location targeting.
    Ported from Rankmax automation_proxy.py → __automation_generate_uule__()
    """
    if not location:
        return ''

    canonical_char_codes = {
        4: "E", 5: "F", 6: "G", 7: "H", 8: "I", 9: "J", 10: "K", 11: "L",
        12: "M", 13: "N", 14: "O", 15: "P", 16: "Q", 17: "R", 18: "S",
        19: "T", 20: "U", 21: "V", 22: "W", 23: "X", 24: "Y", 25: "Z",
        26: "a", 27: "b", 28: "c", 29: "d", 30: "e", 31: "f", 32: "g",
        33: "h", 34: "i", 35: "j", 36: "k", 37: "l", 38: "m", 39: "n",
        40: "o", 41: "p", 42: "q", 43: "r", 44: "s", 45: "t", 46: "u",
        47: "v", 48: "w", 49: "x", 50: "y", 51: "z",
    }

    loc_len = len(location)
    canonical_value = canonical_char_codes.get(loc_len)
    if not canonical_value:
        return ''

    prefix = "w+CAIQICI" + canonical_value
    encoded_location = base64.urlsafe_b64encode(location.encode("utf-8")).decode("utf-8")
    uule = prefix + encoded_location
    return uule.rstrip('=')


def _find_location(location_string):
    """Extract location from parentheses. E.g. 'New York (New York, US)' → 'New York, US'"""
    if not location_string:
        return None
    start = location_string.find('(')
    end = location_string.find(')')
    if start != -1 and end != -1:
        return location_string[start + 1:end].strip()
    return None


def fetch_serp_data(keyword_text, region, isocode, language_code, uule='', platform='desktop'):
    """
    Call ScrapingDog API to fetch Google SERP data.
    Ported from Rankmax automation_proxy.py → __automation_collective_request_json__()

    Makes up to 10 paginated calls (page 0-9) = ~100 results.
    Returns merged JSON response.
    """
    api_key = _get_api_key()
    if not api_key:
        logger.error("SCRAPINGDOG_API_KEY not configured")
        return None

    session = requests.Session()
    all_organic = []
    merged_json = {}
    base_rank = 0

    for page_num in range(10):
        params = {
            'api_key': api_key,
            'query': keyword_text,
            'country': isocode,
            'language': language_code,
            'domain': region,
            'page': page_num,
            'advance_search': 'false',
        }
        if uule:
            params['uule'] = uule

        try:
            resp = session.get(SCRAPINGDOG_URL, params=params, timeout=(3.05, 15))
            if resp.status_code == 200:
                page_json = resp.json()
                if not isinstance(page_json, dict):
                    continue

                if page_num == 0:
                    merged_json = page_json.copy()
                    page_organic = page_json.get('organic_results', [])
                    first_ranks = [
                        x.get('rank') for x in page_organic
                        if isinstance(x, dict) and isinstance(x.get('rank'), int)
                    ]
                    base_rank = max(first_ranks) if first_ranks else len(page_organic)
                    all_organic.extend(page_organic)
                else:
                    page_organic = page_json.get('organic_results', [])
                    for item in page_organic:
                        if isinstance(item, dict):
                            base_rank += 1
                            item['rank'] = base_rank
                    all_organic.extend(page_organic)

            elif resp.status_code == 429:
                logger.warning(f"ScrapingDog rate limit hit on page {page_num} for '{keyword_text}'")
                break
            else:
                logger.warning(f"ScrapingDog error {resp.status_code} on page {page_num} for '{keyword_text}'")
                break

        except requests.RequestException as e:
            logger.error(f"ScrapingDog request failed for '{keyword_text}' page {page_num}: {e}")
            break

    if merged_json:
        merged_json['organic_results'] = all_organic

    return merged_json if merged_json else None


def process_single_keyword(seo_kw_rank_id):
    """
    Process a single keyword: fetch SERP → parse → save to PostgreSQL.
    This is the core function called per keyword.

    Replaces Rankmax centralised.py → mongopush() with PostgreSQL writes.
    """
    try:
        seo_kw = SeoKeywordRank.objects.select_related('keyword', 'domain').get(id=seo_kw_rank_id)
    except SeoKeywordRank.DoesNotExist:
        logger.error(f"SeoKeywordRank {seo_kw_rank_id} not found")
        return False

    keyword_text = seo_kw.keyword.keyword
    target_url = seo_kw.target_url or seo_kw.domain.url

    # Build UULE for location targeting
    uule = seo_kw.geo_target_uule
    if not uule and seo_kw.geo_target:
        location = _find_location(seo_kw.geo_target)
        if location:
            uule = _generate_uule(location)

    # Mark as busy
    SeoKeywordRank.objects.filter(id=seo_kw.id).update(auto_call_status='busy')

    try:
        # Step 1: Fetch SERP data from ScrapingDog
        json_data = fetch_serp_data(
            keyword_text=keyword_text,
            region=seo_kw.region,
            isocode=seo_kw.isocode,
            language_code=seo_kw.language_code,
            uule=uule,
            platform=seo_kw.platform,
        )

        if not json_data:
            SeoKeywordRank.objects.filter(id=seo_kw.id).update(auto_call_status='fail')
            logger.warning(f"No SERP data for keyword '{keyword_text}' (ID: {seo_kw.id})")
            return False

        # Step 2: Parse the SERP response
        parsed = parse_json_serp_response(
            json_data=json_data,
            target_url=target_url,
            exact_domain=False,
        )

        live_rank = parsed['rank']
        today = date.today()

        with transaction.atomic():
            # Step 3: Save rank to history table
            SeoRankHistory.objects.update_or_create(
                seo_keyword_rank=seo_kw,
                snapshot_date=today,
                defaults={'rank_position': live_rank}
            )

            # Step 4: Compute rank changes from history
            changes = compute_rank_changes(seo_kw, live_rank)

            # Step 5: Calculate best rank
            if live_rank > 0:
                if seo_kw.top_rank and seo_kw.top_rank > 0:
                    top_rank = min(live_rank, seo_kw.top_rank)
                else:
                    top_rank = live_rank
            else:
                top_rank = seo_kw.top_rank

            # Step 6: Build today/best snippet
            kw_snip = seo_kw.keyword_snippet or {'tdy': {}, 'best': {}}
            kw_snip['tdy'] = parsed.get('today_snippet', {})
            if live_rank > 0 and top_rank and live_rank <= top_rank:
                kw_snip['best'] = parsed.get('today_snippet', {})

            # Step 7: Update SeoKeywordRank with all new data
            SeoKeywordRank.objects.filter(id=seo_kw.id).update(
                rank_now=live_rank,
                top_rank=top_rank,
                site_url=parsed.get('url', ''),
                day_val=changes['day_val'],
                day_mark=changes['day_mark'],
                week_val=changes['week_val'],
                week_mark=changes['week_mark'],
                half_month_val=changes['half_month_val'],
                half_month_mark=changes['half_month_mark'],
                month_val=changes['month_val'],
                month_mark=changes['month_mark'],
                status_from_start=changes['status_from_start'],
                featured_snippet=parsed['featured_snippet'],
                knowledge_panel=parsed['knowledge_panel'],
                ads=parsed['ads'],
                review=parsed['review'],
                total_rating=parsed['total_rating'],
                total_review=parsed['total_review'],
                snippets_details=parsed['snippets_details'],
                keyword_snippet=kw_snip,
                search_results=parsed['search_results'],
                cannibalisation=parsed['cannibalisation'],
                last_ranked_date=datetime.now(),
                auto_call_status='done',
                auto_refresh_count=seo_kw.auto_refresh_count + 1,
            )

            # Step 8: Update SERP feature history
            SeoSerpFeatureHistory.objects.update_or_create(
                seo_keyword_rank=seo_kw,
                defaults={
                    'featured_snippet_url_list': parsed['snippets_details'].get('featured_box', {}).get('link', ''),
                    'featured_snippet_history': parsed['snippets_details'].get('featured_box', {}),
                    'ad_snippet_history': parsed['snippets_details'].get('ads', {}),
                    'comp_today': parsed['competitors'],
                }
            )

        logger.info(f"Ranked keyword '{keyword_text}' → position {live_rank} (ID: {seo_kw.id})")
        return True

    except Exception as e:
        logger.error(f"Error processing keyword '{keyword_text}' (ID: {seo_kw.id}): {e}", exc_info=True)
        SeoKeywordRank.objects.filter(id=seo_kw.id).update(auto_call_status='fail')
        return False


def process_domain_rankings(domain_id):
    """
    Process all keywords for a domain, then recalculate domain metrics.
    This is the main orchestrator function.

    Replaces Rankmax automation_engine.py → __automation_concurrency_task__()

    Flow:
        1. Reset all keyword statuses to 'avail'
        2. Process each keyword (fetch SERP → parse → save)
        3. Calculate domain-level metrics (Rankmax score, activity, comparisons)
    """
    keywords = SeoKeywordRank.objects.filter(
        domain_id=domain_id,
        auto_call_status__in=['avail', 'fail']
    )

    total = keywords.count()
    if total == 0:
        logger.info(f"No keywords to process for domain {domain_id}")
        return {'processed': 0, 'success': 0, 'failed': 0}

    logger.info(f"Starting SEO rank check for domain {domain_id}: {total} keywords")

    success_count = 0
    fail_count = 0

    for seo_kw in keywords:
        result = process_single_keyword(seo_kw.id)
        if result:
            success_count += 1
        else:
            fail_count += 1

    # After all keywords processed, recalculate domain metrics
    metrics = calculate_domain_daily_metrics(domain_id)

    logger.info(
        f"Domain {domain_id} SEO check complete: "
        f"{success_count} success, {fail_count} failed"
        f"{f', score={metrics.score_meter}' if metrics else ''}"
    )

    return {
        'processed': total,
        'success': success_count,
        'failed': fail_count,
        'score': float(metrics.score_meter) if metrics else None,
    }
