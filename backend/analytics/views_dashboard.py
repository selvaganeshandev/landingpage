from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Avg, Count, Sum, Q, Min, Max
from django.db.models.functions import Coalesce
from datetime import timedelta, datetime, date
from decimal import Decimal
from urllib.parse import urlparse

# Backend models
from domains.models import Domain
from prompts.models import PromptAnalytics, DomainMetricSnapshot, PromptGroupMetricSnapshot, PromptGroup, Prompt
from competitors.models import Competitor
from .models import ShareOfVoiceAnalytics, SentimentAnalytics

# 'Mentions by Country' (Insights). Prompts are run for the India market and the
# engine stamps every analytics row region='GLOBAL' until a domain opts into
# per-region tracking, so both values count as India mentions.
INDIA_REGION_CODES = ('IN', 'GLOBAL')
INDIA_BAR_COLOR = 'bg-[#7C3AED]'


def _url_host(url):
    """Return the bare host (no scheme/www/path) from a URL or bare-host string.

    Mirrors the export's `_root_domain` normalization so the Insights
    'Cited Pages' count agrees with the exported report.
    """
    if not url:
        return ""
    raw = str(url).strip()
    if "://" not in raw:
        raw = "http://" + raw
    try:
        host = (urlparse(raw).netloc or "").lower()
    except ValueError:
        # Malformed cited URLs reach here straight from LLM output (an unbalanced
        # '[' makes urlparse raise "Invalid IPv6 URL"). One such citation used to
        # 500 the entire Insights page for the domain, so treat it as hostless.
        return ""
    return host[4:] if host.startswith("www.") else host


def _canonical_page(url):
    """Canonical key for a cited page: host (no scheme, no leading www) + path
    (no trailing slash), lowercased. Collapses http/https and www/non-www
    duplicates so the same underlying page is counted once for 'Cited Pages'.
    """
    raw = str(url).strip()
    if "://" not in raw:
        raw = "http://" + raw
    try:
        parsed = urlparse(raw)
    except ValueError:
        # Same malformed-URL guard as _url_host above.
        return ""
    host = (parsed.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = (parsed.path or "").rstrip("/").lower()
    return host + path


def _citation_entry_url(entry):
    """Best-effort URL string from a single citation_list entry.

    citation_list entries are dicts like {'url': ..., 'url_hash': ...} (see the
    engine's URLExtractor), but tolerate the legacy shapes ('source'/'link') and
    plain URL strings so no cited page is silently missed.
    """
    if isinstance(entry, dict):
        for field in ('url', 'source', 'link', 'href', 'uri'):
            val = entry.get(field)
            if val and isinstance(val, str):
                return val
        return None
    if isinstance(entry, str):
        return entry
    return None


def _dashboard_datetime_window(start_date, end_date):
    """Aware datetime window [start 00:00 .. end 23:59:59] for live
    PromptAnalytics queries, matching the snapshot date range the dashboard
    uses elsewhere."""
    start_dt = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    end_dt = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))
    return start_dt, end_dt


def count_cited_urls(domain_id, start_date, end_date, platform_filter=None):
    """Count every URL the AI cited (sum of citation_list lengths) for a domain
    in the given window.

    This matches the Citations page (misinformation citations dashboard), which
    counts citation_list entries, so the Insights 'Total Citations' headline
    agrees with the Citations page a client drills into.

    NOTE: this is intentionally different from the PromptAnalytics
    `total_citations` column (domain-specific citations) that feeds the
    visibility score / exports / snapshots — those are left untouched.
    """
    start_dt, end_dt = _dashboard_datetime_window(start_date, end_date)
    qs = PromptAnalytics.objects.annotate(
        # Keep BOTH dates: use tracked_at (last run) and fall back to created_at
        # (first creation) when a row has no tracked_at, so neither field is lost.
        _window_dt=Coalesce('tracked_at', 'created_at'),
    ).filter(
        prompt__group__domain_id=domain_id,
        track_status='COMP',
        # Window on the last-run date (tracked_at, with created_at fallback —
        # see _window_dt above). Analytics rows are updated in place on every
        # weekly run, so created_at alone stays the original date (often months
        # ago) and would drop freshly-refreshed prompts out of the rolling window —
        # the cause of dashboards reading 0 while data is actually being refreshed.
        _window_dt__gte=start_dt,
        _window_dt__lte=end_dt,
    )
    if platform_filter:
        qs = qs.filter(platform=platform_filter)
    total = 0
    for citation_list in qs.values_list('citation_list', flat=True):
        if isinstance(citation_list, list):
            total += len(citation_list)
    return total


def live_sentiment_breakdown(domain_id, start_date, end_date, platform_filter=None):
    """Positive/neutral/negative percentages from each mention's actual
    sentiment_category (live PromptAnalytics), matching the Sentiment page.

    The previous Insights logic bucketed each platform's AVERAGE sentiment
    score, which collapsed mixed responses into one category (e.g. one positive
    + one neutral response -> '100% positive'). Counting categories per mention
    reflects the real distribution. Only mention rows (is_mention=True) count,
    since sentiment is about how the brand was mentioned.
    """
    start_dt, end_dt = _dashboard_datetime_window(start_date, end_date)
    qs = PromptAnalytics.objects.annotate(
        # Keep BOTH dates: use tracked_at (last run) and fall back to created_at
        # (first creation) when a row has no tracked_at, so neither field is lost.
        _window_dt=Coalesce('tracked_at', 'created_at'),
    ).filter(
        prompt__group__domain_id=domain_id,
        is_mention=True,
        # Window on the last-run date (tracked_at, with created_at fallback —
        # see _window_dt above). Analytics rows are updated in place on every
        # weekly run, so created_at alone stays the original date (often months
        # ago) and would drop freshly-refreshed prompts out of the rolling window —
        # the cause of dashboards reading 0 while data is actually being refreshed.
        _window_dt__gte=start_dt,
        _window_dt__lte=end_dt,
    )
    if platform_filter:
        qs = qs.filter(platform=platform_filter)
    counts = {'positive': 0, 'neutral': 0, 'negative': 0}
    for category in qs.values_list('sentiment_category', flat=True):
        key = (category or '').strip().lower()
        if key not in counts:
            key = 'neutral'
        counts[key] += 1
    total = counts['positive'] + counts['neutral'] + counts['negative']
    if total == 0:
        return 0, 0, 0
    return (
        round(counts['positive'] / total * 100, 2),
        round(counts['neutral'] / total * 100, 2),
        round(counts['negative'] / total * 100, 2),
    )


def live_country_breakdown(domain_id, start_date, end_date, platform_filter=None):
    """Insights 'Mentions by Country' — India only, from live PromptAnalytics.

    Per-region tracking (DomainRegion, see docs/GEO_AI_MENTION_TRACKING_DESIGN.md)
    is opt-in and no domain enables it, so the engine writes every analytics row
    with region='GLOBAL' against the India market. India is therefore the only
    country with real mention data behind it, and it is the only row we return —
    the widget previously fell back to an invented IN/US/UK/Other split.

    Returns [] when the window has no mentions, so the card shows an empty state
    instead of a fabricated 100% bar. When real per-region rows start landing,
    the non-IN regions here become additional entries.
    """
    start_dt, end_dt = _dashboard_datetime_window(start_date, end_date)
    qs = PromptAnalytics.objects.annotate(
        _window_dt=Coalesce('tracked_at', 'created_at'),
    ).filter(
        prompt__group__domain_id=domain_id,
        track_status='COMP',
        _window_dt__gte=start_dt,
        _window_dt__lte=end_dt,
        region__in=INDIA_REGION_CODES,
    )
    if platform_filter:
        qs = qs.filter(platform=platform_filter)

    india_mentions = int(qs.aggregate(n=Sum('total_mentions'))['n'] or 0)
    if india_mentions <= 0:
        return []
    return [{
        'code': 'IN',
        'name': 'India',
        'percentage': 100.0,
        'count': india_mentions,
        'color': INDIA_BAR_COLOR,
    }]


def live_domain_window_metrics(domain_id, start_date, end_date, platform_filter=None, domain_host=None):
    """Compute the Insights current-window headline metrics directly from live
    PromptAnalytics (the source of truth), in a single pass.

    Returns totals + a per-platform breakdown so the Insights cards always match
    the Mentions/Citations/Sentiment detail pages and never drift from cached
    DomainMetricSnapshots. Only the headline cards use this — trend charts,
    share of voice, and the engine's alert generation keep reading snapshots
    independently, so they are unaffected.

    Keys returned:
      total_mentions  - sum of total_mentions (matches snapshot 'mentions')
      domain_citations- sum of total_citations (domain-specific; feeds visibility)
      cited_urls      - count of all citation_list entries (matches Citations page)
      avg_position    - mention-weighted average brand position
      avg_sentiment   - average sentiment_score over mention rows (-1..1)
      cited_pages     - count of DISTINCT domain-owned URLs cited by AI in the
                        window (0 when domain_host is not provided). This is the
                        'Cited Pages' metric: unique pages on the selected domain
                        that appeared in AI answers, distinct from the raw
                        cited_urls event count.
      platforms       - [{platform, mention_count, avg_position, citations}], desc
    """
    start_dt, end_dt = _dashboard_datetime_window(start_date, end_date)
    qs = PromptAnalytics.objects.annotate(
        # Keep BOTH dates: use tracked_at (last run) and fall back to created_at
        # (first creation) when a row has no tracked_at, so neither field is lost.
        _window_dt=Coalesce('tracked_at', 'created_at'),
    ).filter(
        prompt__group__domain_id=domain_id,
        track_status='COMP',
        # Window on the last-run date (tracked_at, with created_at fallback —
        # see _window_dt above). Analytics rows are updated in place on every
        # weekly run, so created_at alone stays the original date (often months
        # ago) and would drop freshly-refreshed prompts out of the rolling window —
        # the cause of dashboards reading 0 while data is actually being refreshed.
        _window_dt__gte=start_dt,
        _window_dt__lte=end_dt,
    )
    if platform_filter:
        qs = qs.filter(platform=platform_filter)

    total_mentions = 0
    domain_citations = 0
    cited_urls = 0
    pos_sum = 0.0
    pos_wt = 0
    sent_sum = 0.0
    sent_n = 0
    platforms = {}
    domain_pages = set()  # distinct domain-owned cited URLs (Cited Pages)

    for platform, is_m, tm, tc, pos, sscore, clist in qs.values_list(
        'platform', 'is_mention', 'total_mentions', 'total_citations',
        'position', 'sentiment_score', 'citation_list',
    ):
        tm = int(tm or 0)
        tc = int(tc or 0)
        n_urls = len(clist) if isinstance(clist, list) else 0
        total_mentions += tm
        domain_citations += tc
        cited_urls += n_urls

        p = platforms.setdefault(
            platform, {
                'mention_count': 0,
                'citations': 0,
                'pos_sum': 0.0,
                'pos_wt': 0,
                'cited_pages': set()
            }
        )
        p['mention_count'] += tm
        p['citations'] += tc

        # Cited Pages: unique pages ON the selected domain that AI cited. Only
        # counted when a domain_host is supplied so existing callers that omit it
        # keep their exact previous behavior.
        if domain_host and isinstance(clist, list):
            for entry in clist:
                url = _citation_entry_url(entry)
                if not url:
                    continue
                host = _url_host(url)
                if host and (host == domain_host or host.endswith('.' + domain_host)):
                    canonical_url = _canonical_page(url)
                    domain_pages.add(canonical_url)
                    p['cited_pages'].add(canonical_url)

        if is_m:
            sent_sum += float(sscore or 0)
            sent_n += 1
            if pos and float(pos) > 0:
                weight = tm if tm > 0 else 1
                pos_sum += float(pos) * weight
                pos_wt += weight
                p['pos_sum'] += float(pos) * weight
                p['pos_wt'] += weight

    avg_position = (pos_sum / pos_wt) if pos_wt > 0 else 0.0
    avg_sentiment = (sent_sum / sent_n) if sent_n > 0 else 0.0

    platform_list = []
    for name, p in platforms.items():
        ap = (p['pos_sum'] / p['pos_wt']) if p['pos_wt'] > 0 else 0
        platform_list.append({
            'platform': name,
            'mention_count': p['mention_count'],
            'avg_position': int(round(ap)),
            'citations': p['citations'],
            'cited_pages': len(p['cited_pages']),
        })
    platform_list.sort(key=lambda x: x['mention_count'], reverse=True)

    return {
        'total_mentions': total_mentions,
        'domain_citations': domain_citations,
        'cited_urls': cited_urls,
        'cited_pages': len(domain_pages),
        'avg_position': avg_position,
        'avg_sentiment': avg_sentiment,
        'platforms': platform_list,
    }


# --- Visibility score -------------------------------------------------------
#
# Weights are unchanged from the original formula; only the normalization is.
# Each component is now an ABSOLUTE rate rather than a ratio against MAX() across
# every domain in the database. That old normalization had two fatal properties:
#
#   1. No usable range. Dividing a domain's mentions by the largest domain's
#      total crushed real performance to near zero, while absent sentiment and
#      absent position each scored full/half credit for free. Every domain landed
#      between ~11 and ~29 and could never reach "Good" (50), regardless of how
#      well it actually performed.
#   2. Cross-tenant coupling. The MAX() had no organization filter, so one
#      customer's score moved when an unrelated customer's data grew, and a
#      stored score could not be reproduced later because the ceiling had shifted.
#
# Rates fix both: they are bounded 0-1 by construction, depend only on the
# domain's own tracked prompts, and are reproducible forever. They also put the
# brand on the same conceptual scale as competitors, which were already scored
# as mentioned_count / total_prompts.
VISIBILITY_WEIGHTS = {
    'mentions': 0.4,    # frequency  - how often the brand shows up at all
    'citations': 0.3,   # authority  - how often AI cites the brand's own site
    'sentiment': 0.2,   # perception - how favourably it is described
    'position': 0.1,    # prominence - where in the answer it appears
}

# Position at which prominence credit reaches zero. Position 1 scores 1.0,
# position 10 or worse scores 0.0. Absolute, so it never shifts with the data.
VISIBILITY_POSITION_FLOOR = 10.0


def compute_visibility_score(responses, mentioned, own_cited, avg_sentiment, avg_position):
    """Visibility score (0-100) from absolute rates. See VISIBILITY_WEIGHTS above.

    Args:
        responses:     total AI responses tracked in the window (the denominator)
        mentioned:     responses that mentioned the brand
        own_cited:     responses that cited the brand's own domain
        avg_sentiment: mean sentiment over mention rows, -1..1
        avg_position:  mean position over mention rows, 1 = best, 0 = unknown

    A domain with no mentions scores 0.0 — sentiment and position contribute
    nothing when there is nothing to be sentimental about or to position.
    """
    if not responses or not mentioned:
        return 0.0

    norm_mentions = max(0.0, min(1.0, mentioned / responses))
    norm_citations = max(0.0, min(1.0, own_cited / responses))
    norm_sentiment = max(0.0, min(1.0, (float(avg_sentiment or 0) + 1.0) / 2.0))
    if avg_position and float(avg_position) > 0:
        span = VISIBILITY_POSITION_FLOOR - 1.0
        norm_position = (VISIBILITY_POSITION_FLOOR - float(avg_position)) / span
        norm_position = max(0.0, min(1.0, norm_position))
    else:
        norm_position = 0.0

    w = VISIBILITY_WEIGHTS
    score = (
        w['mentions'] * norm_mentions
        + w['citations'] * norm_citations
        + w['sentiment'] * norm_sentiment
        + w['position'] * norm_position
    ) * 100
    return round(score, 2)


def live_visibility_score(domain_id, start_date, end_date, platform_filter=None, domain_host=None):
    """Compute the visibility score directly from live PromptAnalytics.

    Reads the same rows, over the same window, as every other headline figure on
    the card, so the gauge and the Total Mentions beneath it can no longer
    disagree about which population they describe.
    """
    start_dt, end_dt = _dashboard_datetime_window(start_date, end_date)
    qs = PromptAnalytics.objects.annotate(
        _window_dt=Coalesce('tracked_at', 'created_at'),
    ).filter(
        prompt__group__domain_id=domain_id,
        track_status='COMP',
        _window_dt__gte=start_dt,
        _window_dt__lte=end_dt,
    )
    if platform_filter:
        qs = qs.filter(platform=platform_filter)

    responses = 0
    mentioned = 0
    own_cited = 0
    sent_sum = 0.0
    pos_sum = 0.0
    pos_n = 0

    for is_mention, position, sentiment, citation_list in qs.values_list(
        'is_mention', 'position', 'sentiment_score', 'citation_list',
    ):
        responses += 1

        if domain_host and isinstance(citation_list, list):
            for entry in citation_list:
                url = _citation_entry_url(entry)
                host = _url_host(url) if url else ''
                if host and (host == domain_host or host.endswith('.' + domain_host)):
                    own_cited += 1
                    break

        if is_mention:
            mentioned += 1
            sent_sum += float(sentiment or 0)
            if position and float(position) > 0:
                pos_sum += float(position)
                pos_n += 1

    avg_sentiment = (sent_sum / mentioned) if mentioned else 0.0
    avg_position = (pos_sum / pos_n) if pos_n else 0.0
    return compute_visibility_score(responses, mentioned, own_cited, avg_sentiment, avg_position)


def live_visibility_by_snapshot_date(domain_id, start_date, end_date, snapshot_dates,
                                     platform_filter=None, domain_host=None):
    """Rate-based visibility per trend bucket, computed live from PromptAnalytics.

    The trend line historically plotted each snapshot's STORED ``visibility_score``,
    which the engine wrote under an older MAX()-normalized formula — a different
    scale from the gauge, so the line and the gauge disagreed (e.g. 33 vs 57 for
    the same domain/window).

    This recomputes visibility per period with the SAME rate-based
    ``compute_visibility_score`` the gauge uses, in a single pass over the window:
    each live row is assigned to the earliest ``snapshot_date >= its own date``
    (the snapshot that closes the period it falls in), so the returned keys line
    up with the trend's x-axis. Periods with no live rows are simply absent, so
    the caller falls back to the stored value and pure-historical windows are
    left untouched.

    Returns ``{snapshot_date: visibility_float}``.
    """
    import bisect
    if not snapshot_dates:
        return {}
    ordered = sorted(snapshot_dates)
    start_dt, end_dt = _dashboard_datetime_window(start_date, end_date)
    qs = PromptAnalytics.objects.annotate(
        _window_dt=Coalesce('tracked_at', 'created_at'),
    ).filter(
        prompt__group__domain_id=domain_id,
        track_status='COMP',
        _window_dt__gte=start_dt,
        _window_dt__lte=end_dt,
    )
    if platform_filter:
        qs = qs.filter(platform=platform_filter)

    acc = {}
    for window_dt, is_mention, position, sentiment, citation_list in qs.values_list(
        '_window_dt', 'is_mention', 'position', 'sentiment_score', 'citation_list',
    ):
        row_date = window_dt.date()
        idx = bisect.bisect_left(ordered, row_date)
        key = ordered[idx] if idx < len(ordered) else ordered[-1]
        bucket = acc.setdefault(key, {
            'responses': 0, 'mentioned': 0, 'own_cited': 0,
            'sent_sum': 0.0, 'pos_sum': 0.0, 'pos_n': 0,
        })
        bucket['responses'] += 1
        if domain_host and isinstance(citation_list, list):
            for entry in citation_list:
                url = _citation_entry_url(entry)
                host = _url_host(url) if url else ''
                if host and (host == domain_host or host.endswith('.' + domain_host)):
                    bucket['own_cited'] += 1
                    break
        if is_mention:
            bucket['mentioned'] += 1
            bucket['sent_sum'] += float(sentiment or 0)
            if position and float(position) > 0:
                bucket['pos_sum'] += float(position)
                bucket['pos_n'] += 1

    result = {}
    for key, b in acc.items():
        avg_sentiment = (b['sent_sum'] / b['mentioned']) if b['mentioned'] else 0.0
        avg_position = (b['pos_sum'] / b['pos_n']) if b['pos_n'] else 0.0
        result[key] = float(compute_visibility_score(
            b['responses'], b['mentioned'], b['own_cited'], avg_sentiment, avg_position))
    return result


def _latest_snapshot_per_platform(domain_id, start_date, end_date, platform_filter=None):
    """Return the newest DomainMetricSnapshot per platform inside the window.

    Snapshot `mentions`/`citations` are CUMULATIVE running totals re-recorded on
    each processing day, so the newest row per platform describes the domain's
    state as of the end of the window. Summing every row instead would count the
    same mentions once per snapshot date.
    """
    period_types = get_period_types_for_query((end_date - start_date).days or 1)
    qs = DomainMetricSnapshot.objects.filter(
        domain_id=domain_id,
        snapshot_date__gte=start_date,
        snapshot_date__lte=end_date,
        period_type__in=period_types,
    ).exclude(platform__isnull=True).exclude(platform='')
    if platform_filter:
        qs = qs.filter(platform=platform_filter)

    latest = {}
    for s in qs:
        current = latest.get(s.platform)
        # Tie-break on id so several period_type rows sharing the newest date
        # still contribute exactly one snapshot per platform.
        if current is None or (s.snapshot_date, s.id) > (current.snapshot_date, current.id):
            latest[s.platform] = s
    return list(latest.values())


def snapshot_window_metrics(domain_id, start_date, end_date, platform_filter=None):
    """Historical fallback for `live_domain_window_metrics`, read from snapshots.

    `PromptAnalytics` rows are updated IN PLACE on every run, so `tracked_at`
    always points at the most recent run and no per-day history survives there.
    Any window that ends before the latest run therefore has zero live rows, even
    though the period genuinely had activity. DomainMetricSnapshot is the only
    real history, so it backs historical windows.

    Returns the same keys as `live_domain_window_metrics` so callers can swap it
    in directly. Two keys cannot be reconstructed from snapshots:
      cited_urls  - snapshots store domain citation COUNTS, not the citation_list
                    URL events the live path counts, so this mirrors `citations`
                    (the same definition the trend chart already plots).
      cited_pages - no per-URL detail is retained; always 0.
    """
    snapshots = _latest_snapshot_per_platform(domain_id, start_date, end_date, platform_filter)

    total_mentions = sum(s.mentions for s in snapshots)
    total_citations = sum(s.citations or 0 for s in snapshots)

    pos_sum = sum(float(s.average_position or 0) * s.mentions for s in snapshots if s.mentions > 0)
    pos_wt = sum(s.mentions for s in snapshots if s.mentions > 0 and float(s.average_position or 0) > 0)
    avg_position = (pos_sum / pos_wt) if pos_wt > 0 else 0.0

    sent_sum = sum(float(s.sentiment_score or 0) * s.mentions for s in snapshots if s.mentions > 0)
    avg_sentiment = (sent_sum / total_mentions) if total_mentions > 0 else 0.0

    platform_list = [{
        'platform': s.platform,
        'mention_count': s.mentions,
        'avg_position': int(round(float(s.average_position or 0))),
        'citations': s.citations or 0,
        'cited_pages': 0,
    } for s in snapshots]
    platform_list.sort(key=lambda x: x['mention_count'], reverse=True)

    return {
        'total_mentions': total_mentions,
        'domain_citations': total_citations,
        'cited_urls': total_citations,
        'cited_pages': 0,
        'avg_position': avg_position,
        'avg_sentiment': avg_sentiment,
        'platforms': platform_list,
    }


def snapshot_sentiment_breakdown(domain_id, start_date, end_date, platform_filter=None):
    """Historical sentiment split, read from SentimentAnalytics.

    `SentimentAnalytics` keeps positive/neutral/negative percentages per theme
    per platform per date, so unlike DomainMetricSnapshot it can rebuild the
    sentiment bar for a past window. Rows on the newest date in the window are
    combined weighted by `mention_count`.
    """
    qs = SentimentAnalytics.objects.filter(
        domain_id=domain_id,
        snapshot_date__gte=start_date,
        snapshot_date__lte=end_date,
    )
    if platform_filter:
        qs = qs.filter(platform=platform_filter)

    newest = qs.aggregate(d=Max('snapshot_date'))['d']
    if not newest:
        return (0, 0, 0)

    rows = list(qs.filter(snapshot_date=newest))
    weight = sum(r.mention_count or 0 for r in rows)
    if weight <= 0:
        return (0, 0, 0)

    pos = sum(float(r.positive_percentage or 0) * (r.mention_count or 0) for r in rows) / weight
    neu = sum(float(r.neutral_percentage or 0) * (r.mention_count or 0) for r in rows) / weight
    neg = sum(float(r.negative_percentage or 0) * (r.mention_count or 0) for r in rows) / weight
    return (round(pos, 2), round(neu, 2), round(neg, 2))


def calculate_relative_time(dt):
    """Calculate relative time string like '2 hours ago'"""
    now = timezone.now()
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds >= 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "Just now"


def get_sentiment_category(sentiment_score):
    """Convert sentiment score to category"""
    if sentiment_score is None:
        return "neutral"
    score = float(sentiment_score)
    # Adjusted thresholds: positive > 0.1, negative < -0.1, neutral otherwise
    if score > 0.1:
        return "positive"
    elif score < -0.1:
        return "negative"
    else:
        return "neutral"


def format_date_for_chart(date_obj):
    """Format date for chart display (e.g., 'Oct 1', 'Nov 12')"""
    if isinstance(date_obj, str):
        date_obj = datetime.fromisoformat(date_obj.replace('Z', '+00:00'))
    if isinstance(date_obj, datetime):
        date_obj = date_obj.date()
    
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    return f"{month_names[date_obj.month - 1]} {date_obj.day}"


def get_period_type(days):
    """
    Determine the appropriate period type based on number of days.
    - daily: for periods < 30 days
    - weekly: for periods 30-90 days
    - monthly: for periods > 90 days
    """
    if days < 30:
        return 'daily'
    elif days <= 90:
        return 'weekly'
    else:
        return 'monthly'


def get_period_types_for_query(days):
    """
    Get list of period_types to query based on requested days.
    Always includes more granular period_types as fallback.
    This ensures we can query daily snapshots when weekly/monthly don't exist.
    """
    if days < 30:
        return ['daily']  # Only daily needed
    elif days <= 90:
        return ['weekly', 'daily']  # Try weekly first, fallback to daily
    else:
        return ['monthly', 'weekly', 'daily']  # Try monthly, fallback to weekly/daily


def _calculate_visibility_score(
    mentions: int = 0,
    citations: int = 0,
    sentiment_score: float = 0.0,
    average_position: float = 0.0,
    scope: str = 'domain'
) -> Decimal:
    """
    Calculate visibility score using weighted formula.
    
    Formula: weighted_score = (
        0.4 * norm_mentions +
        0.3 * norm_citations +
        0.2 * norm_sentiment +
        0.1 * norm_position
    ) * 100
    
    Weights:
    - Mentions: 40% (biggest driver - frequency)
    - Citations: 30% (authority/trust)
    - Sentiment: 20% (perception quality)
    - Position: 10% (ranking adjustment)
    
    Args:
        mentions: Total mentions count
        citations: Total citations count
        sentiment_score: Average sentiment score (-1.0 to 1.0)
        average_position: Average position in results
        scope: Normalization scope ('domain', 'group', 'snapshot')
    
    Returns:
        Decimal: Visibility score (0-100)
    """
    # Fetch normalization limits based on scope
    if scope == 'domain':
        # Normalize across all domains
        max_mentions = float(Domain.objects.aggregate(Max('total_mentions'))['total_mentions__max'] or 1)
        max_citations = float(Domain.objects.aggregate(Max('total_citations'))['total_citations__max'] or 1)
        max_position = float(Domain.objects.aggregate(Max('average_position'))['average_position__max'] or 1)
    elif scope == 'group':
        # Normalize across all groups in the same domain (will need domain_id passed)
        # For now, use domain normalization
        max_mentions = float(Domain.objects.aggregate(Max('total_mentions'))['total_mentions__max'] or 1)
        max_citations = float(Domain.objects.aggregate(Max('total_citations'))['total_citations__max'] or 1)
        max_position = float(Domain.objects.aggregate(Max('average_position'))['average_position__max'] or 1)
    else:  # snapshot
        # For snapshots, use domain normalization
        max_mentions = float(Domain.objects.aggregate(Max('total_mentions'))['total_mentions__max'] or 1)
        max_citations = float(Domain.objects.aggregate(Max('total_citations'))['total_citations__max'] or 1)
        max_position = float(Domain.objects.aggregate(Max('average_position'))['average_position__max'] or 1)
    
    # Ensure all values are float for division operations
    mentions_float = float(mentions) if mentions else 0.0
    citations_float = float(citations) if citations else 0.0
    sentiment_float = float(sentiment_score) if sentiment_score else 0.0
    position_float = float(average_position) if average_position else 0.0
    
    # Normalize components (0-1 range)
    norm_mentions = mentions_float / max_mentions if max_mentions > 0 else 0.0
    norm_citations = citations_float / max_citations if max_citations > 0 else 0.0
    norm_sentiment = (sentiment_float + 1.0) / 2.0  # Convert -1 to 1 range to 0-1 range
    norm_position = 1.0 - (position_float / max_position) if max_position > 0 and position_float > 0 else 1.0
    
    # Clamp normalized values to 0-1
    norm_mentions = max(0, min(1, norm_mentions))
    norm_citations = max(0, min(1, norm_citations))
    norm_sentiment = max(0, min(1, norm_sentiment))
    norm_position = max(0, min(1, norm_position))
    
    # Weighted score
    weighted_score = (
        0.4 * norm_mentions +
        0.3 * norm_citations +
        0.2 * norm_sentiment +
        0.1 * norm_position
    )
    
    # Scale to 0-100
    visibility_score = round(weighted_score * 100, 2)
    return Decimal(str(visibility_score))


def domain_data_start(domain_id):
    """Earliest date this domain has any Insights data for.

    Snapshots are the surviving history, but a freshly processed domain can have
    live analytics rows before its first snapshot is written, so take whichever
    is earlier. Returns None when the domain has no data at all.
    """
    earliest_snapshot = DomainMetricSnapshot.objects.filter(
        domain_id=domain_id
    ).aggregate(d=Min('snapshot_date'))['d']

    earliest_live = PromptAnalytics.objects.annotate(
        _window_dt=Coalesce('tracked_at', 'created_at'),
    ).filter(
        prompt__group__domain_id=domain_id,
        track_status='COMP',
    ).aggregate(d=Min('_window_dt'))['d']
    if earliest_live is not None:
        earliest_live = timezone.localtime(earliest_live).date()

    candidates = [d for d in (earliest_snapshot, earliest_live) if d is not None]
    return min(candidates) if candidates else None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    """
    Get comprehensive dashboard data for a domain, filtered by days and optionally by LLM platform.
    
    Query Parameters:
    - domain_id (required): Domain ID
    - days (optional, default=30): Number of days to look back (7, 30, 90, etc.)
    - llm_model (optional): Filter by LLM platform (chatgpt, claude, gemini, perplexity, grok). Use 'all' or omit for all platforms.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    domain_id = request.query_params.get('domain_id')
    days = int(request.query_params.get('days', 30))
    llm_model = request.query_params.get('llm_model')
    
    # Normalize platform name if provided (e.g., 'chatgpt' -> 'ChatGPT')
    platform_filter = None
    if llm_model and llm_model != 'all':
        # Map lowercase to proper case platform names (must match DB values exactly).
        # This must stay in sync with the engine's authoritative map in
        # engine/core/domain_processor.py:833 — that is what actually writes the
        # platform strings. The `.capitalize()` fallback below cannot be relied on
        # for multi-word or inner-capital names: it turns 'deepseek' into
        # 'Deepseek', which never matches the 'DeepSeek' the engine writes.
        platform_map = {
            'chatgpt': 'ChatGPT',
            'claude': 'Claude',
            'gemini': 'Google Gemini',  # Fixed: DB stores as "Google Gemini" not "Gemini"
            'perplexity': 'Perplexity',
            'grok': 'Grok',
            'deepseek': 'DeepSeek',
        }
        platform_filter = platform_map.get(llm_model.lower(), llm_model.capitalize())
        logger.info(f"Dashboard API: Filtering by platform: {platform_filter}")
    
    if not domain_id:
        return Response(
            {'error': 'domain_id is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get domain
    domain = get_object_or_404(Domain, id=domain_id)
    
    # Calculate date range
    # For "last N days", we want the last N days including today
    # If days=7 and today is Dec 15, we want Dec 9-15 (7 days: Dec 9, 10, 11, 12, 13, 14, 15)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days - 1)  # Subtract (days-1) to include today in the count

    # Optional explicit date range overrides the `days` window. Accepts ISO
    # YYYY-MM-DD. When provided, every date-windowed metric on the response
    # (mentions, citations, visibility, position, platform distribution,
    # recent mentions) honors this range. Cumulative fields like
    # total_prompts remain unfiltered by design.
    start_param = request.query_params.get('start_date')
    end_param = request.query_params.get('end_date')
    if start_param or end_param:
        try:
            if end_param:
                end_date = datetime.strptime(end_param, '%Y-%m-%d').date()
            if start_param:
                start_date = datetime.strptime(start_param, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'start_date and end_date must be YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if start_date > end_date:
            return Response(
                {'error': 'start_date cannot be after end_date'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Keep `days` consistent with the explicit range so previous-period
        # comparison + period_type fallback behave sensibly.
        days = (end_date - start_date).days + 1

    # A preset window wider than the domain's history (notably "All time",
    # which the UI sends as a flat 3650 days) is clamped to the first date we
    # actually hold data for. Two things were wrong without this: the chart
    # claimed a decade of history that never existed, and the previous-period
    # comparison was computed against the decade BEFORE that — always empty, so
    # every change on the card read "N/A".
    #
    # `is_all_time` tells the frontend the window covers everything we have, so
    # it can drop the comparison entirely rather than print N/A against a period
    # that could not have existed. Explicit start/end ranges are honored exactly
    # and never clamped.
    is_all_time = False
    if not (start_param or end_param):
        data_start = domain_data_start(domain_id)
        if data_start and start_date < data_start:
            start_date = data_start
            days = (end_date - start_date).days + 1
            is_all_time = True

    # Debug: Log calculated dates
    logger.info(f"Dashboard API: Calculated date range for {days} days - start_date: {start_date}, end_date: {end_date}")

    # Calculate previous period for change comparison
    prev_end_date = start_date - timedelta(days=1)
    prev_start_date = prev_end_date - timedelta(days=days)

    # Determine period type based on days (for display/trends)
    period_type = get_period_type(days)

    # Get period types to query (with fallback to more granular types)
    period_types = get_period_types_for_query(days)
    
    # 1. Get metrics from DomainMetricSnapshot (time snapshot functionality)
    # Use metric snapshots for aggregated metrics - much faster than querying raw analytics
    # Query with fallback to more granular period_types
    # DomainMetricSnapshot records are platform-specific, so we aggregate across all platforms
    # Debug: Log the query parameters
    logger.info(f"Dashboard API: Querying snapshots for domain {domain_id}, date range: {start_date} to {end_date}, period_types: {period_types}")
    
    snapshot_qs = DomainMetricSnapshot.objects.filter(
        domain_id=domain_id,
        snapshot_date__gte=start_date,
        snapshot_date__lte=end_date,
        period_type__in=period_types
    ).exclude(platform__isnull=True).exclude(platform='')  # Only use platform-specific snapshots
    
    # Apply platform filter if provided
    if platform_filter:
        snapshot_qs = snapshot_qs.filter(platform=platform_filter)
    
    # Debug: Log snapshot count and check all snapshots for this domain
    snapshot_count_before_agg = snapshot_qs.count()
    logger.info(f"Dashboard API: Found {snapshot_count_before_agg} snapshots matching criteria")
    
    # Debug: Check all snapshots for this domain to see what dates exist
    all_snapshots = DomainMetricSnapshot.objects.filter(domain_id=domain_id).exclude(platform__isnull=True).exclude(platform='')
    all_snapshot_count = all_snapshots.count()
    logger.info(f"Dashboard API: Total snapshots for domain {domain_id}: {all_snapshot_count}")
    if all_snapshot_count > 0:
        # Get date range of all snapshots
        date_range = all_snapshots.aggregate(
            min_date=Min('snapshot_date'),
            max_date=Max('snapshot_date')
        )
        logger.info(f"Dashboard API: Snapshot date range: {date_range['min_date']} to {date_range['max_date']}")
        # Get sample snapshots with dates
        sample_snapshots = list(all_snapshots[:10].values('snapshot_date', 'platform', 'period_type', 'mentions', 'citations'))
        logger.info(f"Dashboard API: Sample all snapshots: {sample_snapshots}")
    
    # Note: We do NOT adjust dates to use older snapshots
    # If no snapshots exist in the requested date range, we should return 0 values
    # This allows alert generation to work properly (comparing current period with no data vs previous period with data)
    if snapshot_count_before_agg == 0:
        logger.info(f"Dashboard API: No snapshots found in requested date range ({start_date} to {end_date}). Returning zero values for current period.")
    
    if snapshot_count_before_agg > 0:
        sample_snapshots = list(snapshot_qs[:5].values('snapshot_date', 'platform', 'period_type', 'mentions'))
        logger.info(f"Dashboard API: Sample filtered snapshots: {sample_snapshots}")
    
    # Get previous period metrics for change calculation
    prev_snapshot_qs = DomainMetricSnapshot.objects.filter(
        domain_id=domain_id,
        snapshot_date__gte=prev_start_date,
        snapshot_date__lte=prev_end_date,
        period_type__in=period_types
    ).exclude(platform__isnull=True).exclude(platform='')  # Only use platform-specific snapshots
    
    # Apply platform filter if provided
    if platform_filter:
        prev_snapshot_qs = prev_snapshot_qs.filter(platform=platform_filter)
    
    # --- Current-window headline metrics from LIVE PromptAnalytics ---
    # Mentions, citations, avg position, visibility and the platform breakdown
    # are computed directly from live PromptAnalytics so the Insights cards
    # always match the Mentions/Citations/Sentiment detail pages and never drift
    # from cached DomainMetricSnapshots. The snapshot queryset (snapshot_qs) is
    # still used below for the over-time TREND chart, and the engine's alert
    # generation reads snapshots independently — both are unaffected.
    # Host of the selected domain, used to identify which cited URLs are the
    # domain's own pages (the 'Cited Pages' metric).
    domain_host = _url_host(domain.url)
    live = live_domain_window_metrics(domain_id, start_date, end_date, platform_filter, domain_host)
    live_prev = live_domain_window_metrics(domain_id, prev_start_date, prev_end_date, platform_filter, domain_host)

    # Historical windows: PromptAnalytics is updated in place, so `tracked_at`
    # always points at the latest run and a window ending before that run has no
    # live rows at all — the page used to render entirely empty even for periods
    # that demonstrably had activity. Snapshots are the only surviving history,
    # so fall back to them whenever the window has no live data but snapshots do.
    # Trailing windows (which include the latest run) still take the live path
    # unchanged, so this only ever adds data where there was none.
    using_snapshot_history = False
    if live['total_mentions'] == 0:
        snap_live = snapshot_window_metrics(domain_id, start_date, end_date, platform_filter)
        if snap_live['total_mentions'] > 0:
            live = snap_live
            using_snapshot_history = True
    if live_prev['total_mentions'] == 0:
        snap_prev = snapshot_window_metrics(domain_id, prev_start_date, prev_end_date, platform_filter)
        if snap_prev['total_mentions'] > 0:
            live_prev = snap_prev

    total_mentions = live['total_mentions']
    prev_total_mentions = live_prev['total_mentions']
    # Total Citations = count of every URL the AI cited (matches the Citations page)
    total_citations = live['cited_urls']
    prev_total_citations = live_prev['cited_urls']
    # Cited Pages = distinct domain-owned pages cited by AI in the window.
    total_cited_pages = live['cited_pages']
    prev_total_cited_pages = live_prev['cited_pages']
    avg_position = live['avg_position']
    prev_avg_position = live_prev['avg_position']
    # Visibility score: keep the engine-computed snapshot value (its 0-100
    # normalization is calibrated per-snapshot and doesn't translate cleanly to
    # live window-aggregates), but GATE it on live presence — a domain with zero
    # live mentions in the window has no real visibility, so we never surface a
    # stale snapshot score for it (this was the phantom "22.14 with 0 mentions").
    #
    # Snapshot `mentions` is the platform's CUMULATIVE running total, re-recorded
    # on every processing day — not that day's new mentions. Summing every row in
    # the window therefore counts the same mentions once per snapshot date (e.g.
    # ChatGPT 57 on Jul 18 and 57 again on Jul 19 is one set of 57, not 114),
    # which skewed the weighting toward whichever platforms happened to be
    # processed on more days. Keeping only the LATEST snapshot per platform
    # reproduces the live mention total exactly (verified across domains and
    # across 7/30/90/180-day windows), so the weights now sum to the same
    # "Total Mentions" figure the card prints beneath the gauge.
    def _snapshot_weighted_visibility(sqs):
        latest_by_platform = {}
        for s in sqs:
            current = latest_by_platform.get(s.platform)
            # Tie-break on id so a platform with several rows on its latest date
            # (one per period_type) still contributes exactly one weight.
            if current is None or (s.snapshot_date, s.id) > (current.snapshot_date, current.id):
                latest_by_platform[s.platform] = s
        snapshots = [s for s in latest_by_platform.values() if s.mentions > 0]
        snap_mentions = sum(s.mentions for s in snapshots)
        if snap_mentions <= 0:
            return 0.0
        return sum(
            float(s.visibility_score or 0) * s.mentions for s in snapshots
        ) / snap_mentions
    # Trailing windows score LIVE from PromptAnalytics, using the rate-based
    # formula in compute_visibility_score() — same rows, same window as every
    # other figure on the card. Historical windows have no live rows to score, so
    # they keep the engine's stored snapshot value; those were written under the
    # old MAX()-normalized formula and stay on the old scale until the engine
    # reprocesses them.
    if using_snapshot_history:
        visibility_score = _snapshot_weighted_visibility(snapshot_qs) if total_mentions > 0 else 0.0
    else:
        visibility_score = live_visibility_score(
            domain_id, start_date, end_date, platform_filter, domain_host
        )
    prev_live_mentions = live_prev['total_mentions']
    if prev_live_mentions > 0 and not using_snapshot_history:
        prev_visibility_score = live_visibility_score(
            domain_id, prev_start_date, prev_end_date, platform_filter, domain_host
        )
    else:
        prev_visibility_score = _snapshot_weighted_visibility(prev_snapshot_qs) if prev_total_mentions > 0 else 0.0

    # Datetime window reused by the "recent mentions" section further below.
    end_datetime = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))
    start_datetime = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))

    logger.info(
        f"Dashboard API (live): domain={domain_id} mentions={total_mentions} "
        f"citations={total_citations} avg_position={avg_position:.2f} "
        f"visibility={visibility_score}"
    )
    
    # Calculate change percentages (only if previous period has data)
    def calculate_change(current, previous):
        """Calculate percentage change, return None if no previous data or both are zero"""
        # If both current and previous are 0, return None (no meaningful change)
        if (current == 0 or current is None) and (previous == 0 or previous is None):
            return None
        # If previous is 0 but current is not, return None (can't calculate percentage change from 0)
        if previous == 0 or previous is None:
            return None
        change = ((current - previous) / previous) * 100
        return round(change, 1)
    
    mentions_change = calculate_change(total_mentions, prev_total_mentions)
    citations_change = calculate_change(total_citations, prev_total_citations)
    cited_pages_change = calculate_change(total_cited_pages, prev_total_cited_pages)
    visibility_change = calculate_change(visibility_score, prev_visibility_score)
    position_change = calculate_change(avg_position, prev_avg_position)
    
    # Active alerts from domain
    active_alerts = domain.active_alerts or 0
    
    # Total prompts count for the domain (count individual prompts, not prompt groups)
    # Filter by platform/LLM if provided
    prompt_qs = Prompt.objects.filter(group__domain_id=domain_id)
    
    # If platform filter is provided, filter prompts that have analytics for that platform
    if platform_filter:
        # Get unique prompt IDs that have analytics for the specified platform
        prompt_ids_with_platform = PromptAnalytics.objects.filter(
            prompt__group__domain_id=domain_id,
            platform=platform_filter
        ).values_list('prompt_id', flat=True).distinct()
        prompt_qs = prompt_qs.filter(id__in=prompt_ids_with_platform)
    
    total_prompts = prompt_qs.count()
    
    metrics = {
        'total_mentions': int(total_mentions),
        'total_citations': int(total_citations),
        'total_cited_pages': int(total_cited_pages),
        'total_prompts': int(total_prompts),
        'visibility_score': round(visibility_score, 2),
        'avg_position': int(round(avg_position)) if avg_position > 0 else 0,
        'active_alerts': active_alerts,
        'mentions_change': mentions_change,
        'citations_change': citations_change,
        'cited_pages_change': cited_pages_change,
        'visibility_change': visibility_change,
        'position_change': position_change,
    }
    
    # 2. Brand performance - sentiment from each mention's actual category
    # (live PromptAnalytics), matching the Sentiment page. Previously this
    # bucketed each platform's AVERAGE sentiment score, which hid mixed
    # responses (e.g. one positive + one neutral -> "100% positive").
    positive_pct, neutral_pct, negative_pct = live_sentiment_breakdown(
        domain_id, start_date, end_date, platform_filter
    )
    # Historical window: rebuild the split from SentimentAnalytics, which (unlike
    # DomainMetricSnapshot) retains the positive/neutral/negative percentages.
    if using_snapshot_history and (positive_pct, neutral_pct, negative_pct) == (0, 0, 0):
        positive_pct, neutral_pct, negative_pct = snapshot_sentiment_breakdown(
            domain_id, start_date, end_date, platform_filter
        )
    
    brand = {
        'visibility_score': round(visibility_score, 2),
        'total_mentions': int(total_mentions),
        'avg_position': int(round(avg_position)) if avg_position > 0 else 0,
        'sentiment': {
            'positive_percentage': positive_pct,
            'neutral_percentage': neutral_pct,
            'negative_percentage': negative_pct
        }
    }
    
    # 3. Platform distribution - from the SAME live PromptAnalytics window as the
    # totals above, so per-platform mentions add up to Total Mentions and every
    # tracked platform (incl. Claude) is shown. Previously this read
    # PromptGroupMetricSnapshot, which could surface stale/phantom per-platform
    # mentions that no longer existed in the live data.
    platforms = live['platforms']
    
    # 4. Share of Voice (latest day in range)
    # Use the requested date range (do not adjust to use older data)
    sov_qs = ShareOfVoiceAnalytics.objects.filter(
        domain_id=domain_id,
        timestamp__gte=start_date,
        timestamp__lte=end_date
    )
    
    # Apply platform filter if provided
    if platform_filter:
        sov_qs = sov_qs.filter(platform=platform_filter)
    
    # Baseline for the share-of-voice trend: the most recent reading BEFORE the
    # current window opened. Share of voice is a percentage that already sums to
    # 100 across brands, so the meaningful trend is the change in percentage
    # POINTS (+3.2 = gained 3.2 points of share), not a percentage-of-percentage.
    #
    # Deliberately not restricted to the previous period: readings are irregular
    # (roughly weekly, and sparser for some domains), so a strict previous-window
    # filter would find nothing and silently report "no change". Taking the last
    # reading before the window always compares against real earlier data.
    baseline_qs = ShareOfVoiceAnalytics.objects.filter(
        domain_id=domain_id,
        timestamp__lt=start_date,
    )
    if platform_filter:
        baseline_qs = baseline_qs.filter(platform=platform_filter)

    baseline_shares = {}
    baseline_day = baseline_qs.aggregate(d=Max('timestamp'))['d']
    if baseline_day:
        for row in baseline_qs.filter(timestamp=baseline_day):
            baseline_shares[row.competitor_id] = float(row.share_percentage or 0)

    def _share_trend(competitor_id, current_share):
        """Change in share-of-voice POINTS vs the baseline reading.

        Returns None when this brand has no earlier reading to compare against —
        a brand first seen in this window has no trend, which is different from a
        trend of zero. The UI shows nothing rather than a misleading 0%.
        """
        if competitor_id not in baseline_shares:
            return None
        return round(current_share - baseline_shares[competitor_id], 2)

    share_of_voice = None
    if sov_qs.exists():
        latest_day = sov_qs.order_by('-timestamp').first().timestamp
        latest_rows = sov_qs.filter(timestamp=latest_day)
        
        your_brand = latest_rows.filter(competitor__isnull=True).first()
        competitors_rows = latest_rows.filter(
            competitor__isnull=False
        ).order_by('market_position')
        
        competitors_list = []
        for comp_row in competitors_rows:
            try:
                competitor = Competitor.objects.get(id=comp_row.competitor_id)
                competitors_list.append({
                    'competitor_id': comp_row.competitor_id,
                    'name': competitor.name,
                    'url': competitor.url,
                    'share_percentage': float(comp_row.share_percentage),
                    'mention_count': comp_row.mention_count,
                    'market_position': comp_row.market_position,
                    'trend': _share_trend(
                        comp_row.competitor_id, float(comp_row.share_percentage)
                    ),
                })
            except Competitor.DoesNotExist:
                continue
        
        # Build unified list with "You" first
        all_brands = []
        if your_brand:
            all_brands.append({
                'competitor_id': None,
                'name': 'You',  # Label as "You"
                'url': '',  # Domain URL can be added if needed
                'share_percentage': float(your_brand.share_percentage),
                'mention_count': your_brand.mention_count,
                'market_position': 1,
                # competitor_id is None for your own brand — the baseline map is
                # keyed the same way, so this looks up your own earlier reading.
                'trend': _share_trend(None, float(your_brand.share_percentage)),
                'is_you': True
            })
        
        for comp in competitors_list:
            comp['is_you'] = False
            all_brands.append(comp)
        
        share_of_voice = {
            'date': latest_day.isoformat() if latest_day else None,
            'brands': all_brands,  # Unified list with "You" first
            # Keep backward compatibility
            'your_brand': {
                'share_percentage': float(your_brand.share_percentage) if your_brand else 0,
                'mention_count': your_brand.mention_count if your_brand else 0,
                'market_position': 1
            } if your_brand else None,
            'competitors': competitors_list
        }
    
    # 5. Trends - use metric snapshots for time-series data
    trends = []
    
    # Get all snapshots ordered by date (use the adjusted query if available)
    trend_snapshots = snapshot_qs.order_by('snapshot_date')
    
    # Group by snapshot_date for the selected period_type
    snapshot_by_date = {}
    for snapshot in trend_snapshots:
        snapshot_date = snapshot.snapshot_date
        if snapshot_date not in snapshot_by_date:
            snapshot_by_date[snapshot_date] = {
                'mentions': 0,
                'citations': 0,
                'period_mentions': 0,
                'period_citations': 0,
                'period_cited_pages': 0,
                'visibility_sum': 0,
                'visibility_weight': 0
            }

        snapshot_by_date[snapshot_date]['mentions'] += snapshot.mentions
        snapshot_by_date[snapshot_date]['citations'] += (snapshot.citations or 0)
        # Per-period activity, written by the engine alongside the running
        # totals. Snapshots taken before those columns existed carry 0, which is
        # why the totals above are kept as a fallback (see `trends_are_period`).
        snapshot_by_date[snapshot_date]['period_mentions'] += (snapshot.period_mentions or 0)
        snapshot_by_date[snapshot_date]['period_citations'] += (snapshot.period_citations or 0)
        # MAX, not sum: cited pages is a DISTINCT count that the engine writes
        # domain-wide (identical on every platform row for the date), because a
        # page cited by two platforms is still one page. Summing would overcount.
        snapshot_by_date[snapshot_date]['period_cited_pages'] = max(
            snapshot_by_date[snapshot_date]['period_cited_pages'],
            snapshot.period_cited_pages or 0,
        )
        if snapshot.visibility_score and snapshot.mentions > 0:
            snapshot_by_date[snapshot_date]['visibility_sum'] += float(snapshot.visibility_score) * snapshot.mentions
            snapshot_by_date[snapshot_date]['visibility_weight'] += snapshot.mentions
    
    # Build trends array.
    #
    # Prefer the engine's PER-PERIOD columns: those describe activity within each
    # period, so the line rises AND falls like a real trend. `mentions` /
    # `citations` are running totals (all-time state as at that date), so a chart
    # built from them can only ever climb.
    #
    # Snapshots written before those columns existed carry 0, so fall back to the
    # running totals until the engine has reprocessed. `trends_are_period` tells
    # the frontend which it is getting, so it can label the chart honestly rather
    # than silently presenting totals as activity.
    trends_are_period = any(
        d['period_mentions'] or d['period_citations'] or d['period_cited_pages']
        for d in snapshot_by_date.values()
    )

    # Snapshots written before the engine recorded per-period counts carry 0 in
    # those columns — not because nothing happened that period, but because the
    # columns did not exist. Charting them in period mode would draw a long run
    # of false zeros and make a domain's history look wiped.
    #
    # So in period mode, start the series at the first date that actually has
    # period data and drop everything before it. A chart that begins a few weeks
    # ago is honest; one that claims a year of zero activity is not.
    #
    # Only LEADING dates are dropped. A zero after that point is a real quiet
    # period and is kept, so genuine gaps still show.
    ordered_dates = sorted(snapshot_by_date.keys())
    if trends_are_period:
        first_with_data = next(
            (
                d for d in ordered_dates
                if snapshot_by_date[d]['period_mentions']
                or snapshot_by_date[d]['period_citations']
                or snapshot_by_date[d]['period_cited_pages']
            ),
            None,
        )
        if first_with_data is not None:
            ordered_dates = [d for d in ordered_dates if d >= first_with_data]

    # Recompute each period's visibility with the SAME rate-based formula as the
    # gauge, so the line and the gauge share one scale. The stored snapshot
    # values are on an older MAX()-normalized scale, which made the line (e.g.
    # 33) disagree with the gauge (57). Periods with no live rows keep the stored
    # value, so pure-historical windows are unaffected.
    live_vis_map = live_visibility_by_snapshot_date(
        domain_id, start_date, end_date, ordered_dates, platform_filter, domain_host,
    )

    for snapshot_date in ordered_dates:
        data = snapshot_by_date[snapshot_date]
        stored_visibility = (
            data['visibility_sum'] / data['visibility_weight']
            if data['visibility_weight'] > 0 else 0
        )
        day_visibility = live_vis_map.get(snapshot_date, stored_visibility)

        point = {
            'date': format_date_for_chart(snapshot_date),
            'visibility': round(day_visibility, 2),
        }
        if trends_are_period:
            point['mentions'] = data['period_mentions']
            point['citations'] = data['period_citations']
            # Real measured value now — no longer estimated from a flat ratio.
            point['cited_pages'] = data['period_cited_pages']
        else:
            point['mentions'] = data['mentions']
            point['citations'] = data['citations']
            # Deliberately omitted: there is no cited-pages history on these
            # older snapshots, and the previous estimate
            # (citations x total_cited_pages/total_citations) was a scaled copy
            # of the citations line rather than a measurement.
        trends.append(point)

    # If no snapshots, create empty trend points for the date range
    if not trends:
        current_date = start_date
        while current_date <= end_date:
            trends.append({
                'date': format_date_for_chart(current_date),
                'mentions': 0,
                'citations': 0,
                'cited_pages': 0,
                'visibility': 0
            })
            if period_type == 'daily':
                current_date += timedelta(days=1)
            elif period_type == 'weekly':
                current_date += timedelta(days=7)
            else:  # monthly
                # Approximate month increment
                if current_date.month == 12:
                    current_date = date(current_date.year + 1, 1, current_date.day)
                else:
                    current_date = date(current_date.year, current_date.month + 1, current_date.day)
    
    # 6. Recent mentions - use PromptAnalytics for real-time recent data
    # This is the only part that still uses raw analytics (for recent activity)
    # Use the same datetime range as calculated above for consistency
    # end_datetime and start_datetime are already calculated above
    # Show all mentions regardless of position
    
    recent_analytics = PromptAnalytics.objects.annotate(
        # Last-run date with created_at fallback — see headline metrics above.
        _window_dt=Coalesce('tracked_at', 'created_at'),
    ).filter(
        prompt__group__domain_id=domain_id,
        track_status='COMP',
        _window_dt__gte=start_datetime,
        _window_dt__lte=end_datetime
    )

    # Apply platform filter if provided
    if platform_filter:
        recent_analytics = recent_analytics.filter(platform=platform_filter)

    recent_analytics = recent_analytics.order_by('-_window_dt')[:10]
    
    recent_mentions = []
    for a in recent_analytics:
        position = int(round(float(a.position or 0)))
        recent_mentions.append({
            'id': a.id,
            'platform': a.platform,
            'prompt': a.prompt.prompt if a.prompt else '',
            'position': position,
            'sentiment': get_sentiment_category(a.sentiment_score),
            'sentiment_score': float(a.sentiment_score or 0),
            'created_at': (a.tracked_at or a.created_at).isoformat(),
            'relative_time': calculate_relative_time(a.tracked_at or a.created_at),
            'citations': int(a.total_citations or 0)
        })
    
    return Response({
        'period_days': days,
        # The window actually served. `is_all_time` means it was widened to
        # cover the domain's entire history, so there is no previous period to
        # compare against and the UI hides the change rather than showing N/A.
        'window': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'is_all_time': is_all_time,
        },
        'domain_name': domain.name,
        'domain_url': domain.url,
        'metrics': metrics,
        'brand': brand,
        'platforms': platforms,
        'countries': live_country_breakdown(domain_id, start_date, end_date, platform_filter),
        'share_of_voice': share_of_voice,
        'trends': trends,
        # True  -> `trends` holds per-period activity (real rises and falls)
        # False -> `trends` holds running totals, so the line can only climb.
        'trends_are_period': trends_are_period,
        'recent_mentions': recent_mentions
    })
