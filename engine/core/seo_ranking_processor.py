"""
SEO Ranking Processor — Engine-side processor for SEO keyword rank checking.

Uses DataBlue API (replaces ScrapingDog as of the SERP migration) to fetch
Google SERP data, parses it, and saves to PostgreSQL.

Two paths:
  - process_single_keyword(seo_kw_id):   one keyword, one HTTP call (Celery per-keyword task)
  - process_domain_rankings(domain_id):  batch — async pipelined fetch + DB writes
                                         (rankmax automation_engine pattern)
"""
import logging
from datetime import date, timedelta

from django.utils import timezone

from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.db import connection, transaction

from core import datablue_service

# Concurrency for DataBlue API calls (configurable via Django settings)
DATABLUE_CONCURRENCY = getattr(settings, 'DATABLUE_CONCURRENCY', 100)

logger = logging.getLogger(__name__)


def _extract_domain(url):
    """Extract domain from URL."""
    if not url:
        return ''
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url if '://' in url else f'https://{url}')
        domain = parsed.netloc or parsed.path
        domain = domain.lower().replace('www.', '')
        return domain.split('/')[0]
    except Exception:
        return ''


def fetch_serp_data(keyword_text, region, isocode, language_code, uule='', platform='desktop'):
    """
    Fetch Google SERP data via DataBlue.

    Signature kept stable so existing callers don't break; `region`, `uule`,
    and `platform` are accepted but not forwarded — DataBlue handles geo via
    country+language and returns DATABLUE_NUM_RESULTS in one call.
    """
    return datablue_service.fetch_one(
        keyword_text=keyword_text,
        isocode=isocode,
        language_code=language_code,
    )


def parse_json_serp_response(json_data, target_url, exact_domain=False):
    """
    Parse SERP JSON response (DataBlue, normalized to ScrapingDog shape) to
    extract rank and SERP features.
    """
    result = {
        'rank': 0,
        'url': '',
        'featured_snippet': False,
        'knowledge_panel': False,
        'ads': False,
        'review': False,
        'total_rating': '-',
        'total_review': '-',
        'search_results': '-',
        'snippets_details': {},
        'competitors': {},
        'cannibalisation': [],
        'today_snippet': {},
    }

    if not json_data or not isinstance(json_data, dict):
        return result

    target_domain = _extract_domain(target_url)

    # Search results count
    search_info = json_data.get('search_information', {})
    if isinstance(search_info, dict):
        total_results = search_info.get('total_results')
        if total_results:
            result['search_results'] = str(total_results)

    # Featured snippet
    featured = json_data.get('answer_box') or json_data.get('featured_snippet')
    if featured and isinstance(featured, dict):
        result['featured_snippet'] = True
        result['snippets_details']['featured_box'] = featured

    # Knowledge panel
    knowledge = json_data.get('knowledge_graph')
    if knowledge and isinstance(knowledge, dict):
        result['knowledge_panel'] = True
        result['snippets_details']['knowledge_panel'] = knowledge

    # Ads
    ads_top = json_data.get('ads', [])
    if ads_top:
        result['ads'] = True
        result['snippets_details']['ads'] = ads_top

    # Organic results - find rank
    organic = json_data.get('organic_results', [])
    cannibalisation_urls = []
    competitors = {}

    for item in organic:
        if not isinstance(item, dict):
            continue

        item_url = item.get('link', '')
        item_domain = _extract_domain(item_url)
        item_rank = item.get('rank') or item.get('position', 0)

        if not isinstance(item_rank, int):
            try:
                item_rank = int(item_rank)
            except (ValueError, TypeError):
                item_rank = 0

        # Check if this is our target
        is_match = False
        if exact_domain:
            is_match = (item_domain == target_domain)
        else:
            is_match = (target_domain in item_domain or item_domain in target_domain)

        if is_match:
            if result['rank'] == 0:
                result['rank'] = item_rank
                result['url'] = item_url
                result['today_snippet'] = {
                    'title': item.get('title', ''),
                    'snippet': item.get('snippet', ''),
                    'link': item_url,
                    'rank': item_rank,
                }
            else:
                cannibalisation_urls.append({
                    'url': item_url,
                    'rank': item_rank,
                    'title': item.get('title', ''),
                })
        else:
            if item_rank and item_rank <= 10:
                competitors[str(item_rank)] = {
                    'url': item_url,
                    'domain': item_domain,
                    'title': item.get('title', ''),
                    'rank': item_rank,
                }

    # Rating from organic results
    if organic:
        for item in organic:
            if not isinstance(item, dict):
                continue
            item_domain = _extract_domain(item.get('link', ''))
            if target_domain in item_domain or item_domain in target_domain:
                rich_snippet = item.get('rich_snippet', {})
                if isinstance(rich_snippet, dict):
                    top_info = rich_snippet.get('top', {})
                    if isinstance(top_info, dict):
                        rating = top_info.get('detected_extensions', {}).get('rating')
                        reviews = top_info.get('detected_extensions', {}).get('reviews')
                        if rating:
                            result['review'] = True
                            result['total_rating'] = str(rating)
                        if reviews:
                            result['total_review'] = str(reviews)
                break

    result['cannibalisation'] = cannibalisation_urls
    result['competitors'] = competitors
    # Store competitors inside snippets_details for later competitor analysis
    result['snippets_details']['competitors'] = competitors

    return result


def _rank_formulation(live_rank, past_rank):
    """Calculate rank change value."""
    if live_rank == 0 or past_rank == 0:
        return 0
    return past_rank - live_rank


def _check_status(num):
    """Return direction string."""
    if num > 0:
        return 'up'
    elif num < 0:
        return 'down'
    return '-'


class SeoRankingProcessor:
    """Processes SEO keyword rankings using DataBlue API."""

    def process_single_keyword(self, seo_kw_id):
        """Process a single keyword: fetch SERP -> parse -> save to PostgreSQL.

        Used by the Celery per-keyword task (process_seo_keyword_task). For
        domain-wide batches use process_domain_rankings, which pipelines fetch
        and DB writes via async fetch_many.
        """
        from shared_models.seo_models import SeoKeywordRank, SeoRankHistory, SeoSerpFeatureHistory

        try:
            seo_kw = SeoKeywordRank.objects.select_related('keyword').get(id=seo_kw_id)
        except SeoKeywordRank.DoesNotExist:
            logger.error(f"SeoKeywordRank {seo_kw_id} not found")
            return False

        # Guard against broken FK or missing keyword
        if not seo_kw.keyword:
            logger.error(f"SeoKeywordRank {seo_kw_id} has no linked keyword — skipping")
            SeoKeywordRank.objects.filter(id=seo_kw.id).update(auto_call_status='fail')
            return False

        keyword_text = seo_kw.keyword.keyword
        target_url = seo_kw.target_url or ''

        # Get domain URL for target matching
        try:
            from shared_models.models import Domain
            domain = Domain.objects.get(id=seo_kw.domain_id)
            if not target_url:
                target_url = domain.url or ''
        except Exception:
            pass

        # Mark as busy
        SeoKeywordRank.objects.filter(id=seo_kw.id).update(auto_call_status='busy')

        try:
            # Step 1: Fetch SERP data
            json_data = datablue_service.fetch_one(
                keyword_text=keyword_text,
                isocode=seo_kw.isocode,
                language_code=seo_kw.language_code,
            )

            if not json_data:
                SeoKeywordRank.objects.filter(id=seo_kw.id).update(auto_call_status='fail')
                logger.warning(f"No SERP data for keyword '{keyword_text}' (ID: {seo_kw.id})")
                return False

            # Step 2: Parse the response
            parsed = parse_json_serp_response(
                json_data=json_data,
                target_url=target_url,
                exact_domain=False,
            )

            return self._persist_parsed(seo_kw, parsed)

        except Exception as e:
            logger.error(f"Error processing keyword '{keyword_text}' (ID: {seo_kw.id}): {e}", exc_info=True)
            SeoKeywordRank.objects.filter(id=seo_kw.id).update(auto_call_status='fail')
            return False

    def _persist_parsed(self, seo_kw, parsed):
        """Write a parsed SERP result to the rank/history/snippet tables.

        Shared by process_single_keyword and the batch on_result callback so
        both code paths follow identical DB semantics.
        """
        from shared_models.seo_models import SeoKeywordRank, SeoRankHistory, SeoSerpFeatureHistory

        live_rank = parsed['rank']
        today = date.today()
        keyword_text = seo_kw.keyword.keyword if seo_kw.keyword else ''

        with transaction.atomic():
            # Save rank history
            SeoRankHistory.objects.update_or_create(
                seo_keyword_rank_id=seo_kw.id,
                snapshot_date=today,
                defaults={'rank_position': live_rank}
            )

            # Compute rank changes from history
            changes = self._compute_rank_changes(seo_kw.id, live_rank)

            # Calculate best rank
            if live_rank > 0:
                if seo_kw.top_rank and seo_kw.top_rank > 0:
                    top_rank = min(live_rank, seo_kw.top_rank)
                else:
                    top_rank = live_rank
            else:
                top_rank = seo_kw.top_rank

            # Build snippets
            kw_snip = seo_kw.keyword_snippet or {'tdy': {}, 'best': {}}
            kw_snip['tdy'] = parsed.get('today_snippet', {})
            if live_rank > 0 and top_rank and live_rank <= top_rank:
                kw_snip['best'] = parsed.get('today_snippet', {})

            # Update keyword rank record
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
                last_ranked_date=timezone.now(),
                auto_call_status='done',
                auto_refresh_count=seo_kw.auto_refresh_count + 1,
            )

            # Update SERP feature history
            SeoSerpFeatureHistory.objects.update_or_create(
                seo_keyword_rank_id=seo_kw.id,
                defaults={
                    'featured_snippet_url_list': parsed['snippets_details'].get('featured_box', {}).get('link', ''),
                    'featured_snippet_history': parsed['snippets_details'].get('featured_box', {}),
                    'ad_snippet_history': parsed['snippets_details'].get('ads', {}),
                    'comp_today': parsed['competitors'],
                }
            )

        logger.info(f"Ranked keyword '{keyword_text}' -> position {live_rank} (ID: {seo_kw.id})")
        return True

    def process_domain_rankings(self, domain_id, batch_size=500):
        """Process all keywords for a domain in batches via async pipelined
        fetch + DB writes (rankmax pattern).

        Flow per batch:
          1. Load up to batch_size 'avail' keyword rows.
          2. datablue_service.fetch_many(items, on_result=cb) dispatches all
             HTTP requests concurrently (capped by DATABLUE_CONCURRENCY).
          3. As each SERP response lands, the on_result callback runs in a
             thread pool — it parses + writes to DB while later fetches are
             still in flight.

        Returns a dict including `remaining` so the caller can reschedule for
        any leftover 'avail' rows. Failed rows are NOT retried in the same run
        (preserves the existing daily-scheduler retry semantics).
        """
        from shared_models.seo_models import SeoKeywordRank, SeoDomainDailyMetrics
        from shared_models.models import Domain

        keyword_ids = list(
            SeoKeywordRank.objects.filter(
                domain_id=domain_id,
                auto_call_status='avail'
            ).values_list('id', flat=True)[:batch_size]
        )

        total_pending = SeoKeywordRank.objects.filter(
            domain_id=domain_id,
            auto_call_status='avail'
        ).count()

        total = len(keyword_ids)
        if total == 0:
            logger.info(f"No SEO keywords to process for domain {domain_id}")
            return {'processed': 0, 'success': 0, 'failed': 0, 'remaining': 0}

        # Load keyword rows + their text in one pass
        seo_kw_rows = list(
            SeoKeywordRank.objects.select_related('keyword').filter(id__in=keyword_ids)
        )
        seo_kw_by_id = {row.id: row for row in seo_kw_rows}

        # Resolve domain target URL once (used as fallback for parser matching)
        try:
            domain_obj = Domain.objects.get(id=domain_id)
            domain_url = domain_obj.url or ''
        except Exception:
            domain_url = ''

        # Build the items dict for fetch_many; skip rows with no keyword link
        items = {}
        skipped_no_keyword = []
        for row in seo_kw_rows:
            if not row.keyword:
                skipped_no_keyword.append(row.id)
                continue
            items[row.id] = {
                'keyword': row.keyword.keyword,
                'isocode': row.isocode or '',
                'language_code': row.language_code or '',
            }

        # Mark all to-be-processed rows busy in one query (atomic batch flip)
        if items:
            SeoKeywordRank.objects.filter(id__in=list(items.keys())).update(
                auto_call_status='busy'
            )
        if skipped_no_keyword:
            SeoKeywordRank.objects.filter(id__in=skipped_no_keyword).update(
                auto_call_status='fail'
            )
            logger.error(
                f"[SEO] {len(skipped_no_keyword)} keyword rows had no linked keyword — marked fail"
            )

        # Read at call-time so .env / settings tweaks take effect on the next
        # batch without needing a worker restart. The module-level constant
        # only captures the value at first import, which silently locks in
        # whatever was set when the worker started.
        concurrency = getattr(settings, 'DATABLUE_CONCURRENCY', DATABLUE_CONCURRENCY)
        logger.info(
            f"Starting SEO rank check for domain {domain_id}: "
            f"batch={total}/{total_pending} pending, concurrency={concurrency}"
        )

        success_count = 0
        fail_count = 0
        timed_out = False

        def _on_result(fetch_result):
            """Per-result callback — runs in a thread pool while other fetches
            are still in flight. Wrap everything so a single failure can never
            kill the pipeline.
            """
            from django.db import connection as thread_conn
            try:
                thread_conn.close_if_unusable_or_obsolete()

                kw_id = fetch_result.get('item_id')
                seo_kw = seo_kw_by_id.get(kw_id)
                if seo_kw is None:
                    return False

                if not fetch_result.get('success'):
                    SeoKeywordRank.objects.filter(id=kw_id).update(auto_call_status='fail')
                    return False

                json_data = fetch_result.get('data')
                target_url = seo_kw.target_url or domain_url
                parsed = parse_json_serp_response(
                    json_data=json_data,
                    target_url=target_url,
                    exact_domain=False,
                )
                return self._persist_parsed(seo_kw, parsed)
            except Exception as e:
                kw_id = fetch_result.get('item_id') if isinstance(fetch_result, dict) else None
                logger.error(
                    f"[SEO] on_result callback failed for keyword ID {kw_id}: {e}",
                    exc_info=True,
                )
                try:
                    if kw_id is not None:
                        SeoKeywordRank.objects.filter(id=kw_id).update(auto_call_status='fail')
                except Exception:
                    pass
                return False
            finally:
                try:
                    thread_conn.close()
                except Exception:
                    pass

        try:
            results = datablue_service.fetch_many(
                items=items,
                on_result=_on_result,
                concurrency=concurrency,
            )
            for r in results:
                cb_ok = r.get('cb') is True
                if cb_ok:
                    success_count += 1
                else:
                    fail_count += 1
        except SoftTimeLimitExceeded:
            timed_out = True
            logger.warning(
                f"[SEO] Domain {domain_id} hit time limit during fetch_many."
            )

        # Recalculate domain metrics (wrapped so it never kills the task)
        metrics = None
        try:
            metrics = self._calculate_domain_metrics(domain_id)
        except Exception as e:
            logger.error(f"[SEO] Error calculating metrics for domain {domain_id}: {e}", exc_info=True)

        # Count how many unprocessed keywords remain (only 'avail', not 'fail')
        remaining = SeoKeywordRank.objects.filter(
            domain_id=domain_id,
            auto_call_status='avail'
        ).count()

        processed_count = success_count + fail_count
        logger.info(
            f"Domain {domain_id} SEO batch complete: "
            f"{success_count} success, {fail_count} failed, {remaining} remaining"
            f"{f', score={metrics.score_meter}' if metrics else ''}"
            f"{' (timed out)' if timed_out else ''}"
        )

        return {
            'processed': processed_count,
            'success': success_count,
            'failed': fail_count,
            'remaining': remaining,
            'timed_out': timed_out,
            'score': float(metrics.score_meter) if metrics else None,
        }

    def _compute_rank_changes(self, seo_kw_id, live_rank):
        """Compute rank changes from history (1D, 7D, 15D, 30D)."""
        from shared_models.seo_models import SeoRankHistory, SeoKeywordRank

        today = date.today()
        changes = {
            'day_val': 0, 'day_mark': '-',
            'week_val': 0, 'week_mark': '-',
            'half_month_val': 0, 'half_month_mark': '-',
            'month_val': 0, 'month_mark': '-',
            'status_from_start': '-',
        }

        periods = [
            ('day', 1),
            ('week', 7),
            ('half_month', 15),
            ('month', 30),
        ]

        for key, days_ago in periods:
            target_date = today - timedelta(days=days_ago)
            past = SeoRankHistory.objects.filter(
                seo_keyword_rank_id=seo_kw_id,
                snapshot_date__lte=target_date,
            ).order_by('-snapshot_date').first()

            if past and past.rank_position > 0:
                val = _rank_formulation(live_rank, past.rank_position)
                changes[f'{key}_val'] = val
                changes[f'{key}_mark'] = _check_status(val)

        # Since start
        try:
            seo_kw = SeoKeywordRank.objects.get(id=seo_kw_id)
            if seo_kw.rank_since_start and seo_kw.rank_since_start > 0 and live_rank > 0:
                since_val = _rank_formulation(live_rank, seo_kw.rank_since_start)
                changes['status_from_start'] = _check_status(since_val)
        except SeoKeywordRank.DoesNotExist:
            pass

        return changes

    def _calculate_domain_metrics(self, domain_id):
        """Calculate domain-level daily SEO metrics."""
        from shared_models.seo_models import SeoKeywordRank, SeoDomainDailyMetrics

        today = date.today()
        keywords = SeoKeywordRank.objects.filter(domain_id=domain_id)
        total = keywords.count()

        if total == 0:
            return None

        # Count buckets
        top_1 = keywords.filter(rank_now=1).count()
        top_3 = keywords.filter(rank_now__gte=1, rank_now__lte=3).count()
        top_10 = keywords.filter(rank_now__gte=1, rank_now__lte=10).count()
        top_50 = keywords.filter(rank_now__gte=1, rank_now__lte=50).count()
        top_100 = keywords.filter(rank_now__gte=1, rank_now__lte=100).count()
        not_ranked = keywords.filter(rank_now=0).count()

        # Device counts
        desktop = keywords.filter(platform='desktop').count()
        mobile = keywords.filter(platform='mobile').count()

        # Performance counts
        improved = keywords.filter(day_mark='up').count()
        declined = keywords.filter(day_mark='down').count()
        no_change = total - improved - declined

        # Activity level
        activity = 0.0
        if total > 0:
            activity = ((improved - declined) / total) * 100

        # Score calculation (Rankmax algorithm) — use DB counts instead of loading all objects
        score_per_day = {
            'first': keywords.filter(rank_now=1).count(),
            'second': keywords.filter(rank_now=2).count(),
            'third': keywords.filter(rank_now=3).count(),
            'top_ten': keywords.filter(rank_now__gte=4, rank_now__lte=10).count(),
            'top_hundred': keywords.filter(rank_now__gte=11, rank_now__lte=100).count(),
            'beyond_hundred': keywords.filter(rank_now=0).count() + keywords.filter(rank_now__gt=100).count(),
        }

        score = 0.0
        if total > 0:
            score = (
                (score_per_day['first'] * 1.0 / total) +
                (score_per_day['second'] * 0.75 / total) +
                (score_per_day['third'] * 0.50 / total) +
                (score_per_day['top_ten'] * 0.20 / total) +
                (score_per_day['top_hundred'] * 0.10 / total) +
                (score_per_day['beyond_hundred'] * -0.10 / total)
            ) * 100

        score = round(max(score, 0), 2)

        # Save metrics
        metrics, _ = SeoDomainDailyMetrics.objects.update_or_create(
            domain_id=domain_id,
            snapshot_date=today,
            defaults={
                'score_meter': score,
                'improved_count': improved,
                'declined_count': declined,
                'no_change_count': no_change,
                'activity_level': round(activity, 2),
                'top_1_count': top_1,
                'top_3_count': top_3,
                'top_10_count': top_10,
                'top_50_count': top_50,
                'top_100_count': top_100,
                'not_ranked_count': not_ranked,
                'desktop_count': desktop,
                'mobile_count': mobile,
                'total_keywords': total,
                'rating_0_2': 0,
                'rating_2_4': 0,
                'rating_4_5': 0,
                'ads_you_above_below': 0,
                'ads_you_above': 0,
                'ads_you_below': 0,
                'ads_others_above_below': 0,
                'ads_others_above': 0,
                'ads_others_below': 0,
            }
        )

        # Update top score
        if metrics.top_score is None or score > float(metrics.top_score):
            metrics.top_score = score
            metrics.save(update_fields=['top_score'])

        return metrics
