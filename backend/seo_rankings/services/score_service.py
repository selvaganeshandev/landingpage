"""
Score calculation service.
Ported from Rankmax: calculation.py + formulate.py
Pure Python math — no database dependency in these functions.
"""
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Q

from seo_rankings.models import SeoKeywordRank, SeoRankHistory, SeoDomainDailyMetrics


def rank_formulation(live_rank, past_rank, total_rank_length=100):
    """
    Calculate rank difference between two positions.
    Ported from Rankmax centralised.py → rankFormulation()
    """
    live_rank = int(live_rank)
    past_rank = int(past_rank)

    if live_rank == 0 and past_rank == 0:
        return 0
    elif live_rank == 0 and past_rank > 0:
        return past_rank - total_rank_length
    elif live_rank > 0 and past_rank == 0:
        return total_rank_length - live_rank
    elif live_rank > past_rank:
        return past_rank - live_rank
    elif past_rank > live_rank:
        return past_rank - live_rank
    else:
        return live_rank - past_rank


def check_status(num):
    """Convert rank difference to direction string."""
    if num > 0:
        return 'up'
    elif num == 0:
        return '-'
    else:
        return 'down'


def score_allocation_calc(rank_now, score_per_day, total_rank_length=100):
    """
    Allocate score bucket based on current rank position.
    Ported from Rankmax calculation.py → scoreAllocationCalc()
    """
    if rank_now and rank_now > 0:
        if rank_now == 1:
            score_per_day['eq__first'] += 1
        elif rank_now == 2:
            score_per_day['eq__second'] += 1
        elif rank_now == 3:
            score_per_day['eq__third'] += 1
        elif rank_now <= 10:
            score_per_day['gte__four__lte__ten'] += 1
        elif rank_now <= total_rank_length:
            score_per_day['gt__ten__lte__limit'] += 1
        else:
            score_per_day['gt__limit'] += 1
    else:
        score_per_day['gt__limit'] += 1

    return score_per_day


def score_meter_calc(score_per_day, all_key_count):
    """
    Calculate the Rankmax score from score buckets.
    Ported from Rankmax calculation.py → scoreMeterCalc()

    Scoring weights:
        Position 1  → 1.00
        Position 2  → 0.75
        Position 3  → 0.50
        Position 4-10 → 0.20
        Position 11-100 → 0.10
        Not ranked (>100) → -0.10
    Formula: sum((count * weight / total_keywords) * 100)
    """
    if all_key_count == 0:
        return 0.0

    weight_map = {
        'eq__first': 1.0,
        'eq__second': 0.75,
        'eq__third': 0.50,
        'gte__four__lte__ten': 0.20,
        'gt__ten__lte__limit': 0.10,
        'gt__limit': -0.10,
    }

    result = []
    for key, val in score_per_day.items():
        meter_mark = weight_map.get(key, 0)
        result.append(round(float(((float(val) * float(meter_mark)) / float(all_key_count)) * 100), 2))

    total_sum = sum(result)
    return total_sum if total_sum > 0 else 0.0


def activity_calc(improved_count, declined_count, total_count):
    """
    Calculate activity level percentage.
    Ported from Rankmax calculation.py → activityCalc()
    """
    if total_count > 0:
        return round(float(((improved_count - declined_count) / total_count) * 100), 2)
    return 0.0


def compute_rank_changes(seo_kw_rank, live_rank):
    """
    Compute 1D, 7D, 15D, 30D rank changes from history table.
    Replaces Rankmax's array-index approach (rank[1], rank[7], rank[15], rank[30]).
    """
    today = date.today()
    changes = {}

    periods = {
        'day': 1,
        'week': 7,
        'half_month': 15,
        'month': 30,
    }

    for period_name, days_ago in periods.items():
        target_date = today - timedelta(days=days_ago)
        history = SeoRankHistory.objects.filter(
            seo_keyword_rank=seo_kw_rank,
            snapshot_date=target_date
        ).first()

        if history:
            diff = rank_formulation(live_rank, history.rank_position)
            changes[f'{period_name}_val'] = abs(diff)
            changes[f'{period_name}_mark'] = check_status(diff)
        else:
            changes[f'{period_name}_val'] = 0
            changes[f'{period_name}_mark'] = '-'

    # Since-start: compare with the oldest history entry
    oldest = SeoRankHistory.objects.filter(
        seo_keyword_rank=seo_kw_rank
    ).order_by('snapshot_date').first()

    if oldest and live_rank > 0:
        diff = rank_formulation(live_rank, oldest.rank_position)
        changes['status_from_start'] = check_status(diff)
    else:
        changes['status_from_start'] = '-'

    return changes


def calculate_domain_daily_metrics(domain_id):
    """
    Calculate and store daily aggregated metrics for a domain.
    Replaces Rankmax formulate.py → dashboardNewGraph()

    This creates/updates one SeoDomainDailyMetrics row per day.
    """
    today = date.today()

    all_keywords = SeoKeywordRank.objects.filter(domain_id=domain_id)
    total_count = all_keywords.count()

    if total_count == 0:
        return None

    score_per_day = defaultdict(int)
    improved_count = 0
    declined_count = 0
    no_change_count = 0
    top_1 = top_3 = top_10 = top_50 = top_100 = not_ranked = 0
    desktop_count = 0
    mobile_count = 0

    for kw in all_keywords:
        rank = kw.rank_now

        # Score allocation
        score_per_day = score_allocation_calc(rank, score_per_day)

        # Comparison buckets
        if rank == 0:
            not_ranked += 1
        elif rank == 1:
            top_1 += 1
        elif rank <= 3:
            top_3 += 1
        elif rank <= 10:
            top_10 += 1
        elif rank <= 50:
            top_50 += 1
        elif rank <= 100:
            top_100 += 1
        else:
            not_ranked += 1

        # Device tracking
        if kw.platform == 'desktop':
            desktop_count += 1
        else:
            mobile_count += 1

        # Day change for activity
        if kw.day_mark == 'up':
            improved_count += 1
        elif kw.day_mark == 'down':
            declined_count += 1
        else:
            no_change_count += 1

    score = score_meter_calc(score_per_day, total_count)
    activity = activity_calc(improved_count, declined_count, total_count)

    # Get previous best score
    previous_best = SeoDomainDailyMetrics.objects.filter(
        domain_id=domain_id
    ).order_by('-score_meter').values_list('score_meter', flat=True).first()

    top_score = max(Decimal(str(score)), previous_best or Decimal('0'))

    metrics, _ = SeoDomainDailyMetrics.objects.update_or_create(
        domain_id=domain_id,
        snapshot_date=today,
        defaults={
            'score_meter': Decimal(str(score)),
            'top_score': top_score,
            'improved_count': improved_count,
            'declined_count': declined_count,
            'no_change_count': no_change_count,
            'activity_level': Decimal(str(activity)),
            'top_1_count': top_1,
            'top_3_count': top_3,
            'top_10_count': top_10,
            'top_50_count': top_50,
            'top_100_count': top_100,
            'not_ranked_count': not_ranked,
            'desktop_count': desktop_count,
            'mobile_count': mobile_count,
            'total_keywords': total_count,
        }
    )

    return metrics
