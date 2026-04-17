"""
Prorate utility for GSC and GA organic report metrics.

When the current reporting period is incomplete (e.g. only 5 days into April),
count-based metrics (clicks, sessions, revenue …) are extrapolated to the full
period using:

    prorated_value = (raw_value / days_elapsed) * total_days_in_period

Rate and average metrics (CTR, Bounce Rate, Avg Position, Avg Session Duration)
are intentionally NOT prorated — they are already normalised per-unit.
"""

from datetime import date


# Metric keys that should be prorated (counts / totals only)
COUNT_METRICS_GSC = {'total_clicks', 'total_impressions'}
COUNT_METRICS_GA = {
    'total_sessions',
    'total_users',
    'total_page_views',
    'total_conversions',
    'total_revenue',
}


def calculate_prorate_factor(start_date, end_date):
    """
    Calculate the prorate factor for a date range.

    Args:
        start_date (date): Period start (inclusive).
        end_date   (date): Period end   (inclusive).

    Returns:
        tuple: (days_elapsed, total_days, factor)
            - days_elapsed : int   — how many days of data actually exist
            - total_days   : int   — total days the period spans
            - factor       : float — multiply raw count by this to get prorated value
                             1.0 when the period is complete.
    """
    today = date.today()
    total_days = (end_date - start_date).days + 1

    # Period is fully in the past — no proration needed
    if today >= end_date:
        return total_days, total_days, 1.0

    # Period has not started yet — edge case, treat as complete (no data)
    if today < start_date:
        return total_days, total_days, 1.0

    days_elapsed = (today - start_date).days + 1
    factor = total_days / days_elapsed if days_elapsed > 0 else 1.0
    return days_elapsed, total_days, factor


def apply_prorate_gsc(data: dict, start_date, end_date) -> dict:
    """
    Apply prorate to a GSC insight data dict.

    Adds keys: is_prorated, days_elapsed, total_days.
    Prorates all keys in COUNT_METRICS_GSC.
    CTR and avg_position are left unchanged.

    Args:
        data       : dict with raw GSC metric values.
        start_date : period start date.
        end_date   : period end date.

    Returns:
        Modified copy of data with prorated values.
    """
    days_elapsed, total_days, factor = calculate_prorate_factor(start_date, end_date)
    result = dict(data)
    result['is_prorated'] = factor != 1.0
    result['days_elapsed'] = days_elapsed
    result['total_days'] = total_days
    result['prorate_factor'] = round(factor, 4)

    if factor != 1.0:
        for key in COUNT_METRICS_GSC:
            if key in result and result[key] is not None:
                result[key] = round(result[key] * factor)

    return result


def apply_prorate_ga(data: dict, start_date, end_date) -> dict:
    """
    Apply prorate to a GA insight data dict.

    Adds keys: is_prorated, days_elapsed, total_days.
    Prorates all keys in COUNT_METRICS_GA.
    Bounce rate and avg_session_duration are left unchanged.

    Args:
        data       : dict with raw GA metric values.
        start_date : period start date.
        end_date   : period end date.

    Returns:
        Modified copy of data with prorated values.
    """
    days_elapsed, total_days, factor = calculate_prorate_factor(start_date, end_date)
    result = dict(data)
    result['is_prorated'] = factor != 1.0
    result['days_elapsed'] = days_elapsed
    result['total_days'] = total_days
    result['prorate_factor'] = round(factor, 4)

    if factor != 1.0:
        for key in COUNT_METRICS_GA:
            if key in result and result[key] is not None:
                if key == 'total_revenue':
                    result[key] = round(result[key] * factor, 2)
                else:
                    result[key] = round(result[key] * factor)

    return result
