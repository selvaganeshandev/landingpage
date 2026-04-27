"""
SEO Ranking Engine — Scraping and orchestration service.

This is the main entry point that:
1. Calls DataBlue API for each keyword (replaces ScrapingDog as of the SERP migration)
2. Parses the SERP response
3. Saves rank data to PostgreSQL
4. Recalculates domain-level metrics
"""
import logging
from datetime import date, datetime

from django.db import transaction

from seo_rankings.models import (
    SeoKeywordRank, SeoRankHistory, SeoSerpFeatureHistory, SeoDomainDailyMetrics
)
from seo_rankings.services.parser_service import parse_json_serp_response, extract_domain
from seo_rankings.services.score_service import (
    compute_rank_changes, calculate_domain_daily_metrics, check_status, rank_formulation
)
from seo_rankings.services import datablue_service

logger = logging.getLogger(__name__)


def fetch_serp_data(keyword_text, region, isocode, language_code, uule='', platform='desktop'):
    """
    Fetch Google SERP data via DataBlue.

    Signature kept stable so existing callers don't need changes; `region`,
    `uule` and `platform` are accepted but not forwarded — DataBlue handles
    geo via country+language and returns DATABLUE_NUM_RESULTS in one call.
    """
    return datablue_service.fetch_one(
        keyword_text=keyword_text,
        isocode=isocode,
        language_code=language_code,
    )


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

    # Mark as busy
    SeoKeywordRank.objects.filter(id=seo_kw.id).update(auto_call_status='busy')

    try:
        # Step 1: Fetch SERP data from DataBlue
        json_data = fetch_serp_data(
            keyword_text=keyword_text,
            region=seo_kw.region,
            isocode=seo_kw.isocode,
            language_code=seo_kw.language_code,
            uule='',
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
