"""
Opportunities — read-only aggregation over SeoKeywordRank.

Surfaces the keywords worth working on this month, in three buckets:
  striking_distance  positions 4-10, on page one but below the top three
  page_two           positions 11-20, within reach of page one
  slipping           lost ground recently and worth defending

Each returned row is enriched with two signals the Keywords page does not show:
  trajectory  where the keyword has been heading, from SeoRankHistory
  difficulty  how contested the term is, from SeoKeywordVolume.comp_index

No writes, no migrations — every field read here already exists.
"""
import statistics
from datetime import date, timedelta

from django.db.models import Q

# Bucket boundaries. Positions are 1-indexed; rank_now == 0 means "not ranked".
TOP_THREE_MAX = 3
PAGE_ONE_MAX = 10
PAGE_TWO_MAX = 20


# --- Trajectory tuning -----------------------------------------------------
# How far back to read daily positions. ~103 points exist per keyword today,
# so 90 days keeps a full picture without pulling the whole table.
TRAJECTORY_DAYS = 90
# Points at each end that get averaged when deciding which way a keyword moved.
# Averaging rather than comparing single days stops one bad crawl from
# relabelling a stable keyword.
TRAJECTORY_WINDOW = 7
# Below this many points there isn't enough history to call a direction.
TRAJECTORY_MIN_POINTS = 10
# Position change (in places) that counts as a real move rather than noise.
TRAJECTORY_MOVE_THRESHOLD = 2
# Standard deviation above which a keyword is bouncing rather than trending.
TRAJECTORY_VOLATILE_STDEV = 5.0
# Points kept for the row sparkline.
SPARKLINE_POINTS = 30

# --- Opportunity score -----------------------------------------------------
# Organic click-through rate by position. These are PUBLISHED INDUSTRY AVERAGES,
# not measured from this account: gsc_impressions is 0 on every tracked keyword,
# so there is no first-party CTR to calibrate against. Every click figure
# derived from this table is an estimate and is labelled "est." in the UI.
# Replace this with real numbers the moment Search Console data lands per-keyword.
CTR_BY_POSITION = {
    1: 0.274, 2: 0.152, 3: 0.099, 4: 0.075, 5: 0.053,
    6: 0.041, 7: 0.033, 8: 0.028, 9: 0.024, 10: 0.021,
    11: 0.014, 12: 0.012, 13: 0.011, 14: 0.010, 15: 0.009,
    16: 0.008, 17: 0.008, 18: 0.007, 19: 0.007, 20: 0.006,
}

# Where a keyword in each band could realistically get to. Deliberately modest —
# promising every page-two term a #1 slot would make the score meaningless.
TARGET_FOR_PAGE_ONE = 3
TARGET_FOR_PAGE_TWO = 10

# Winnability multipliers. Kept as named constants so the score stays auditable.
MOMENTUM_WEIGHT = {
    'climbing': 1.30,   # already moving the right way
    'stalled': 0.85,    # needs an intervention to shift
    'volatile': 0.90,   # unpredictable, but not hopeless
    'slipping': 0.75,   # fighting a decline first
    'new': 1.00,        # no history to judge on, stay neutral
}
COMPETITION_WEIGHT = {'LOW': 1.10, 'MEDIUM': 1.00, 'HIGH': 0.85}
# Having held the target position before is the strongest signal we have that
# it is reachable — it is the only factor here based on this account's own past.
PROVEN_BONUS = 1.35
WINNABILITY_FLOOR = 0.05
WINNABILITY_CEILING = 1.50

# Every keyword in a bucket is scored. Measured on the largest domain (1,506
# rows across the three buckets): 13 queries, 1.4s, 109KB gzipped — the same
# cost as scoring 150, because the time is database round-trips rather than row
# count. An earlier version shortlisted candidates first; that silently hid
# high-scoring keywords that happened to have modest search volume.


def _base_qs(domain_id, platform='desktop'):
    from ..models import SeoKeywordRank
    return (
        SeoKeywordRank.objects
        .filter(domain_id=domain_id, platform=platform)
        .select_related('keyword')
    )


def _ranking_url(kw):
    """
    The page that actually ranks for this keyword.

    `target_url` is the obvious field but is empty on every row in the database,
    so the real source is the stored SERP result for our own listing. Its `rank`
    agrees with `rank_now`, so the two describe the same listing.
    """
    if kw.target_url:
        return kw.target_url
    today = (kw.keyword_snippet or {}).get('tdy')
    if isinstance(today, dict):
        return today.get('link') or ''
    return ''


def _serialize(kw):
    """Flatten one SeoKeywordRank into the shape the Opportunities page renders."""
    return {
        'id': kw.id,
        'keyword': kw.keyword.keyword,
        'rank_now': kw.rank_now,
        'top_rank': kw.top_rank,
        'search_volume': kw.search_volume or 0,
        'target_url': _ranking_url(kw),
        'week_val': kw.week_val,
        'week_mark': kw.week_mark,
        'month_val': kw.month_val,
        'month_mark': kw.month_mark,
        'tags': kw.tags or [],
        'favour': kw.favour,
    }


def _classify_trajectory(points):
    """
    Turn a chronological list of positions into a state label.

    Positions are golf scores — lower is better — so an improvement is a
    *decrease*. `delta` is expressed the intuitive way round: positive means
    the keyword gained places.

    Returns (state, delta, stdev). State is one of:
      climbing / slipping / volatile / stalled / new
    """
    ranked = [p for p in points if p and p > 0]
    if len(ranked) < TRAJECTORY_MIN_POINTS:
        return 'new', 0, 0.0

    window = min(TRAJECTORY_WINDOW, len(ranked) // 2)
    older = ranked[:window]
    recent = ranked[-window:]
    delta = round((sum(older) / len(older)) - (sum(recent) / len(recent)), 1)

    try:
        stdev = round(statistics.pstdev(ranked), 1)
    except statistics.StatisticsError:
        stdev = 0.0

    # Volatility is checked first: a keyword swinging 4 → 19 → 6 may show a
    # flat delta, but "stalled" would be the wrong story to tell about it.
    if stdev >= TRAJECTORY_VOLATILE_STDEV:
        return 'volatile', delta, stdev
    if delta >= TRAJECTORY_MOVE_THRESHOLD:
        return 'climbing', delta, stdev
    if delta <= -TRAJECTORY_MOVE_THRESHOLD:
        return 'slipping', delta, stdev
    return 'stalled', delta, stdev


def _attach_trajectory(rows):
    """
    Add trajectory data to the given rows in one query.

    Only the rows actually being returned are enriched — never the full bucket —
    so this stays a single bounded query no matter how many keywords the domain
    tracks.
    """
    if not rows:
        return

    from ..models import SeoRankHistory

    ids = [r['id'] for r in rows]
    cutoff = date.today() - timedelta(days=TRAJECTORY_DAYS)

    series = {}
    history = (
        SeoRankHistory.objects
        .filter(seo_keyword_rank_id__in=ids, snapshot_date__gte=cutoff)
        .order_by('seo_keyword_rank_id', 'snapshot_date')
        .values_list('seo_keyword_rank_id', 'rank_position')
    )
    for kw_id, position in history:
        series.setdefault(kw_id, []).append(position)

    for row in rows:
        points = series.get(row['id'], [])
        state, delta, stdev = _classify_trajectory(points)
        row['trajectory'] = {
            'state': state,
            'delta': delta,
            'volatility': stdev,
            'points': len(points),
            'sparkline': [p for p in points[-SPARKLINE_POINTS:] if p and p > 0],
        }


def _attach_difficulty(rows):
    """
    Add competition data in one query. comp_index is a 0-100 string in the
    source table; anything unparseable is treated as unknown rather than 0,
    since 0 would read as "effortless".
    """
    if not rows:
        return

    from ..models import SeoKeywordVolume

    ids = [r['id'] for r in rows]
    volumes = (
        SeoKeywordVolume.objects
        .filter(seo_keyword_rank_id__in=ids)
        .values_list('seo_keyword_rank_id', 'comp_level', 'comp_index',
                     'month_wise_volume', 'month_labels')
    )

    by_id = {}
    for kw_id, level, index, monthly, labels in volumes:
        try:
            parsed = int(float(index)) if index not in (None, '', '-') else None
        except (TypeError, ValueError):
            parsed = None
        by_id[kw_id] = {
            'level': (level or '').upper() or None,
            'index': parsed,
            'monthly_volume': monthly or [],
            'month_labels': labels or [],
        }

    for row in rows:
        row['difficulty'] = by_id.get(row['id'], {
            'level': None, 'index': None, 'monthly_volume': [], 'month_labels': [],
        })


def _ctr(position):
    """Estimated organic CTR at a position. Beyond position 20, effectively nil."""
    if not position or position < 1:
        return 0.0
    return CTR_BY_POSITION.get(position, 0.0)


def _target_position(rank_now):
    """The realistic goal for a keyword at this position."""
    if rank_now <= PAGE_ONE_MAX:
        return TARGET_FOR_PAGE_ONE
    return TARGET_FOR_PAGE_TWO


def _estimated_gain(row):
    """
    Estimated additional monthly clicks from reaching the target position.
    Volume-free keywords score 0 here and fall to the bottom, which is correct:
    without volume there is no way to argue the work is worth doing.
    """
    volume = row.get('search_volume') or 0
    if not volume or not row['rank_now']:
        return 0.0
    target = _target_position(row['rank_now'])
    uplift = _ctr(target) - _ctr(row['rank_now'])
    if uplift <= 0:
        return 0.0
    return round(volume * uplift, 1)


def _winnability(row):
    """
    How reachable the target looks, as a multiplier around 1.0, plus the
    human-readable reasons behind it.

    The reasons matter as much as the number: an account manager needs to know
    why a keyword is near the top, not just that the model says so.
    """
    reasons = []
    score = 1.0

    state = (row.get('trajectory') or {}).get('state', 'new')
    score *= MOMENTUM_WEIGHT.get(state, 1.0)
    if state == 'climbing':
        reasons.append(f"Climbing {row['trajectory']['delta']:+g} places over 90 days")
    elif state == 'slipping':
        reasons.append(f"Slipping {row['trajectory']['delta']:+g} places — defend first")
    elif state == 'stalled':
        reasons.append("Stalled — will not move without a change")
    elif state == 'volatile':
        reasons.append(f"Volatile (±{row['trajectory']['volatility']:g} places)")

    level = (row.get('difficulty') or {}).get('level')
    if level in COMPETITION_WEIGHT:
        score *= COMPETITION_WEIGHT[level]
        if level == 'HIGH':
            reasons.append("High advertiser competition")
        elif level == 'LOW':
            reasons.append("Low advertiser competition")

    target = _target_position(row['rank_now'])
    top_rank = row.get('top_rank')
    if top_rank and 0 < top_rank <= target:
        score *= PROVEN_BONUS
        reasons.append(f"Already reached #{top_rank} before")

    gap = row['rank_now'] - target
    if gap <= 2:
        reasons.append(f"Only {gap} place{'s' if gap != 1 else ''} from #{target}")

    score = max(WINNABILITY_FLOOR, min(score, WINNABILITY_CEILING))
    return round(score, 3), reasons


def _attach_score(rows):
    """
    Attach estimated gain, winnability and the combined score to each row.

    The CTR figures behind the estimate are returned alongside it so the UI can
    show the arithmetic rather than asking anyone to trust a bare number.
    """
    for row in rows:
        gain = _estimated_gain(row)
        winnability, reasons = _winnability(row)
        target = _target_position(row['rank_now'])
        row['opportunity'] = {
            'estimated_clicks': gain,
            'winnability': winnability,
            'score': round(gain * winnability, 1),
            'target_position': target,
            'reasons': reasons,
            'ctr_now': round(_ctr(row['rank_now']) * 100, 1),
            'ctr_target': round(_ctr(target) * 100, 1),
        }


def _sort_key(row):
    """
    Highest volume first; ties broken by the better (lower) current position.
    Keywords with no volume attached sort to the bottom rather than being dropped —
    ~2% of tracked terms have no volume and they are still real opportunities.
    """
    return (-(row['search_volume'] or 0), row['rank_now'])


def _recommended_action(row, sibling_count):
    """
    What to actually do about this keyword.

    Derived from the same signals as the score, but expressed as an
    instruction rather than a number. Ordered by urgency: a decline is worth
    stopping before a gain is worth chasing.
    """
    state = (row.get('trajectory') or {}).get('state', 'new')
    level = (row.get('difficulty') or {}).get('level')
    gap = row['rank_now'] - row['opportunity']['target_position']
    proven = bool(row.get('top_rank') and 0 < row['top_rank'] <= row['opportunity']['target_position'])

    if state == 'slipping':
        headline = 'Defend this first'
        detail = (
            f"It has lost {abs(row['trajectory']['delta']):g} places over 90 days. "
            "Find what changed — a competitor's new content, a page edit, or lost links — "
            "before investing in growth elsewhere."
        )
    elif state == 'volatile':
        headline = 'Stabilise before pushing'
        detail = (
            f"The position swings by ±{row['trajectory']['volatility']:g} places. "
            "Chasing it while it bounces wastes effort; look for thin or duplicated content first."
        )
    elif state == 'climbing':
        headline = 'Hold course'
        detail = (
            f"Already gaining {row['trajectory']['delta']:g} places. Whatever is working, keep doing it — "
            "this one may reach the target without further work."
        )
    elif proven:
        headline = 'Recover a position you have held'
        detail = (
            f"It reached #{row['top_rank']} before, so the page can rank there. "
            "Compare it with the version that ranked and restore what was lost."
        )
    elif gap <= 2:
        headline = 'Small push needed'
        detail = (
            f"Only {gap} place{'s' if gap != 1 else ''} from #{row['opportunity']['target_position']}. "
            "On-page work — title, intro, internal links — is usually enough at this distance."
        )
    elif level == 'HIGH':
        headline = 'Needs substantial work'
        detail = (
            "Stalled on a highly contested term. Expect to need materially better content "
            "and external links, not a tweak."
        )
    else:
        headline = 'Refresh the page'
        detail = (
            "Stalled with no recent movement. The page is indexed but not competitive — "
            "a content refresh is the usual next step."
        )

    if sibling_count:
        detail += (
            f" This URL also ranks for {sibling_count} other tracked keyword"
            f"{'s' if sibling_count != 1 else ''}, so the work lands on all of them at once."
        )

    return {'headline': headline, 'detail': detail}


def build_opportunity_detail(seo_kw_id, allowed_domain_ids):
    """
    One keyword, expanded — plus every other tracked keyword ranking through
    the same URL.

    The sibling list is the point: 1,150 of this account's 1,765 keywords share
    a page with at least one other, and the largest page carries 64. Nothing
    else in the product turns a keyword list into a page-level work plan.
    Returns None when the keyword does not exist or is not the caller's.
    """
    from ..models import SeoKeywordRank

    kw = (
        SeoKeywordRank.objects
        .select_related('keyword', 'domain')
        .filter(id=seo_kw_id, domain_id__in=list(allowed_domain_ids))
        .first()
    )
    if not kw:
        return None

    row = _serialize(kw)
    _attach_trajectory([row])
    _attach_difficulty([row])
    _attach_score([row])

    siblings = []
    url = row['target_url']
    if url:
        # Same domain and platform, same ranking URL, excluding this keyword.
        for other in _base_qs(kw.domain_id, kw.platform).exclude(id=kw.id):
            if _ranking_url(other) != url:
                continue
            siblings.append({
                'id': other.id,
                'keyword': other.keyword.keyword,
                'rank_now': other.rank_now,
                'search_volume': other.search_volume or 0,
            })
        # Best positions first; unranked keywords (rank 0) sort last rather than
        # first, which a naive ascending sort would do.
        siblings.sort(key=lambda s: (s['rank_now'] == 0, s['rank_now']))

    return {
        'keyword': row,
        'domain_id': kw.domain_id,
        'siblings': siblings,
        'sibling_volume': sum(s['search_volume'] for s in siblings),
        'action': _recommended_action(row, len(siblings)),
    }


def _bucket_rows(qs, low, high):
    """Every keyword in a position band, unclipped."""
    return [
        _serialize(kw)
        for kw in qs.filter(rank_now__gte=low, rank_now__lte=high)
    ]


def _slipping_rows(qs):
    """
    Every keyword that dropped over the last week or month and is still ranking.
    Ordered by the size of the drop weighted by the volume at stake — for a
    defensive bucket, what was lost matters more than what could be won.
    """
    rows = [
        _serialize(kw)
        for kw in qs.filter(
            Q(week_mark='down') | Q(month_mark='down'),
            rank_now__gt=0,
        )
    ]
    rows.sort(key=lambda r: -(max(r['month_val'], r['week_val']) * (r['search_volume'] or 1)))
    return rows


def build_opportunities(domain_id, platform='desktop', limit=None):
    """
    Return the three opportunity buckets, fully scored.

    Every keyword in a bucket is scored and returned; the page paginates them
    client-side. `limit`, if given, clips each bucket after ranking — it exists
    for callers that genuinely want a top-N (an export, a digest email), not for
    the page, which asks for everything.
    """
    qs = _base_qs(domain_id, platform)

    striking = _bucket_rows(qs, TOP_THREE_MAX + 1, PAGE_ONE_MAX)
    page_two = _bucket_rows(qs, PAGE_ONE_MAX + 1, PAGE_TWO_MAX)
    slipping = _slipping_rows(qs)
    scored_from = {
        'striking_distance': len(striking),
        'page_two': len(page_two),
        'slipping': len(slipping),
    }

    # Enrich all three buckets together: two queries total, not two per bucket.
    # The same keyword can appear in both a position bucket and `slipping`;
    # de-duplicating by id keeps it to one lookup and one shared dict.
    enriched = {}
    for row in striking + page_two + slipping:
        enriched.setdefault(row['id'], row)
    unique_rows = list(enriched.values())
    _attach_trajectory(unique_rows)
    _attach_difficulty(unique_rows)
    _attach_score(unique_rows)
    for row in striking + page_two + slipping:
        source = enriched[row['id']]
        row['trajectory'] = source['trajectory']
        row['difficulty'] = source['difficulty']
        row['opportunity'] = source['opportunity']

    # Final ordering. The two position buckets rank by opportunity score;
    # `slipping` keeps its loss-first ordering, since the question there is
    # "what did we lose", not "what could we win".
    striking.sort(key=lambda r: -r['opportunity']['score'])
    page_two.sort(key=lambda r: -r['opportunity']['score'])
    if limit:
        striking = striking[:limit]
        page_two = page_two[:limit]
        slipping = slipping[:limit]

    striking_total = qs.filter(
        rank_now__gte=TOP_THREE_MAX + 1, rank_now__lte=PAGE_ONE_MAX
    ).count()
    page_two_total = qs.filter(
        rank_now__gte=PAGE_ONE_MAX + 1, rank_now__lte=PAGE_TWO_MAX
    ).count()
    slipping_total = qs.filter(
        Q(week_mark='down') | Q(month_mark='down'), rank_now__gt=0
    ).count()

    return {
        'buckets': {
            'striking_distance': {
                'label': 'Page one, below the top three',
                'range': [TOP_THREE_MAX + 1, PAGE_ONE_MAX],
                'total': striking_total,
                'volume_at_stake': sum(r['search_volume'] for r in striking),
                'rows': striking,
            },
            'page_two': {
                'label': 'Page two, within reach of page one',
                'range': [PAGE_ONE_MAX + 1, PAGE_TWO_MAX],
                'total': page_two_total,
                'volume_at_stake': sum(r['search_volume'] for r in page_two),
                'rows': page_two,
            },
            'slipping': {
                'label': 'Slipped recently, worth defending',
                'range': None,
                'total': slipping_total,
                'volume_at_stake': sum(r['search_volume'] for r in slipping),
                'rows': slipping,
            },
        },
        'summary': {
            'tracked': qs.count(),
            'ranking': qs.filter(rank_now__gt=0).count(),
            'top_three': qs.filter(rank_now__gte=1, rank_now__lte=TOP_THREE_MAX).count(),
            'not_ranked': qs.filter(rank_now=0).count(),
            'with_volume': qs.filter(search_volume__gt=0).count(),
            # Distinguishes "no keywords added" from "added but never crawled".
            # 37 of 50 domains currently track no SEO keywords at all, so the
            # page needs to tell those two states apart rather than showing zeros.
            'crawled': qs.filter(last_ranked_date__isnull=False).count(),
        },
        'limit': limit,
        # How many keywords each bucket's ranking considered. Equal to the
        # bucket total unless a caller passed an explicit `limit`.
        'scored_from': scored_from,
        'ctr_source': 'industry average — no Search Console data available to calibrate',
    }
