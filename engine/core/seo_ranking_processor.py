"""
SEO Ranking Processor — Engine-side processor for SEO keyword rank checking.
Uses ScrapingDog API to fetch Google SERP data, parses it, and saves to PostgreSQL.

This processor runs within the Celery engine and directly accesses the
seo_rankings tables via shared_models (managed=False).
"""
import logging
import base64
from datetime import date, timedelta

from django.utils import timezone

import requests
from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)

# ScrapingDog API endpoint
SCRAPINGDOG_URL = "https://api.scrapingdog.com/google"


def _get_api_key():
    """Get ScrapingDog API key from Django settings."""
    return getattr(settings, 'SCRAPINGDOG_API_KEY', None) or ''


def _generate_uule(location):
    """Generate UULE parameter for Google location targeting."""
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
    """Extract location from parentheses. E.g. 'New York (New York, US)' -> 'New York, US'"""
    if not location_string:
        return None
    start = location_string.find('(')
    end = location_string.find(')')
    if start != -1 and end != -1:
        return location_string[start + 1:end].strip()
    return None


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
    Call ScrapingDog API to fetch Google SERP data.
    Makes up to 10 paginated calls (page 0-9) = ~100 results.
    """
    api_key = _get_api_key()
    if not api_key:
        logger.error("SCRAPINGDOG_API_KEY not configured")
        return None

    session = requests.Session()
    all_organic = []
    merged_json = {}
    base_rank = 0

    for page_num in range(3):
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


def parse_json_serp_response(json_data, target_url, exact_domain=False):
    """
    Parse ScrapingDog JSON response to extract rank and SERP features.
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
    """Processes SEO keyword rankings using ScrapingDog API."""

    def process_single_keyword(self, seo_kw_id):
        """Process a single keyword: fetch SERP -> parse -> save to PostgreSQL."""
        from shared_models.seo_models import SeoKeywordRank, SeoRankHistory, SeoSerpFeatureHistory

        try:
            seo_kw = SeoKeywordRank.objects.select_related('keyword').get(id=seo_kw_id)
        except SeoKeywordRank.DoesNotExist:
            logger.error(f"SeoKeywordRank {seo_kw_id} not found")
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

        # Build UULE for location targeting
        uule = seo_kw.geo_target_uule
        if not uule and seo_kw.geo_target:
            location = _find_location(seo_kw.geo_target)
            if location:
                uule = _generate_uule(location)

        # Mark as busy
        SeoKeywordRank.objects.filter(id=seo_kw.id).update(auto_call_status='busy')

        try:
            # Step 1: Fetch SERP data
            json_data = fetch_serp_data(
                keyword_text=keyword_text,
                region=seo_kw.region,
                isocode=seo_kw.isocode,
                language_code=seo_kw.language_code,
                uule=uule or '',
                platform=seo_kw.platform,
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

            live_rank = parsed['rank']
            today = date.today()

            with transaction.atomic():
                # Step 3: Save rank history
                SeoRankHistory.objects.update_or_create(
                    seo_keyword_rank_id=seo_kw.id,
                    snapshot_date=today,
                    defaults={'rank_position': live_rank}
                )

                # Step 4: Compute rank changes from history
                changes = self._compute_rank_changes(seo_kw.id, live_rank)

                # Step 5: Calculate best rank
                if live_rank > 0:
                    if seo_kw.top_rank and seo_kw.top_rank > 0:
                        top_rank = min(live_rank, seo_kw.top_rank)
                    else:
                        top_rank = live_rank
                else:
                    top_rank = seo_kw.top_rank

                # Step 6: Build snippets
                kw_snip = seo_kw.keyword_snippet or {'tdy': {}, 'best': {}}
                kw_snip['tdy'] = parsed.get('today_snippet', {})
                if live_rank > 0 and top_rank and live_rank <= top_rank:
                    kw_snip['best'] = parsed.get('today_snippet', {})

                # Step 7: Update keyword rank record
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

                # Step 8: Update SERP feature history
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

        except Exception as e:
            logger.error(f"Error processing keyword '{keyword_text}' (ID: {seo_kw.id}): {e}", exc_info=True)
            SeoKeywordRank.objects.filter(id=seo_kw.id).update(auto_call_status='fail')
            return False

    def process_domain_rankings(self, domain_id):
        """Process all keywords for a domain, then recalculate metrics."""
        from shared_models.seo_models import SeoKeywordRank, SeoDomainDailyMetrics

        keywords = SeoKeywordRank.objects.filter(
            domain_id=domain_id,
            auto_call_status__in=['avail', 'fail']
        )

        total = keywords.count()
        if total == 0:
            logger.info(f"No SEO keywords to process for domain {domain_id}")
            return {'processed': 0, 'success': 0, 'failed': 0}

        logger.info(f"Starting SEO rank check for domain {domain_id}: {total} keywords")

        success_count = 0
        fail_count = 0

        for seo_kw in keywords:
            result = self.process_single_keyword(seo_kw.id)
            if result:
                success_count += 1
            else:
                fail_count += 1

        # Recalculate domain metrics
        metrics = self._calculate_domain_metrics(domain_id)

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

        # Score calculation (Rankmax algorithm)
        score_per_day = {'first': 0, 'second': 0, 'third': 0, 'top_ten': 0, 'top_hundred': 0, 'beyond_hundred': 0}
        for kw in keywords:
            rank = kw.rank_now
            if rank == 1:
                score_per_day['first'] += 1
            elif rank == 2:
                score_per_day['second'] += 1
            elif rank == 3:
                score_per_day['third'] += 1
            elif 4 <= rank <= 10:
                score_per_day['top_ten'] += 1
            elif 11 <= rank <= 100:
                score_per_day['top_hundred'] += 1
            elif rank == 0 or rank > 100:
                score_per_day['beyond_hundred'] += 1

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
