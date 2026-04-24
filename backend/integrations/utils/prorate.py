"""
Prorate utility for GSC and GA organic report metrics.

When the current reporting period is incomplete (e.g. only 5 days into April),
count-based metrics (clicks, sessions, revenue …) are extrapolated to the full
period using:

    prorated_value = (raw_value / days_elapsed) * total_days_in_period

Rate and average metrics (CTR, Bounce Rate, Avg Position, Avg Session Duration)
are intentionally NOT prorated — they are already normalised per-unit.
"""

from datetime import date, timedelta


# Metric keys that should be prorated (counts / totals only)
COUNT_METRICS_GSC = {'total_clicks', 'total_impressions'}
COUNT_METRICS_GA = {
    'total_sessions',
    'total_users',
    'total_page_views',
    'total_conversions',
    'total_revenue',
}

# Default reporting lag per provider — GA4 typically has same/next-day data,
# GSC has a ~3-day delay. Callers can override these when they know better.
DEFAULT_LAG_GA  = 1
DEFAULT_LAG_GSC = 3


def calculate_prorate_factor(start_date, end_date, data_lag_days=0):
    """
    Calculate the prorate factor for a date range.

    Args:
        start_date    (date): Period start (inclusive).
        end_date      (date): Period end   (inclusive).
        data_lag_days (int):  Reporting lag of the data source. The "days
                              elapsed" denominator uses today − lag, so the
                              factor reflects only the days for which real
                              data exists. Default 0 (no lag) preserves the
                              pre-existing behavior for generic callers.

    Returns:
        tuple: (days_elapsed, total_days, factor)
            - days_elapsed : int   — days of data actually available
            - total_days   : int   — total days the period spans
            - factor       : float — multiply raw count by this to project to
                                     the full period. 1.0 when already complete.
    """
    # Effective "last day of real data" — accounts for provider reporting lag.
    data_cutoff = date.today() - timedelta(days=data_lag_days)
    total_days = (end_date - start_date).days + 1

    # Period is fully in the past (all data available) — no proration
    if data_cutoff >= end_date:
        return total_days, total_days, 1.0

    # Period has not started yet — edge case, treat as complete (no data)
    if data_cutoff < start_date:
        return total_days, total_days, 1.0

    days_elapsed = (data_cutoff - start_date).days + 1
    factor = total_days / days_elapsed if days_elapsed > 0 else 1.0
    return days_elapsed, total_days, factor


def apply_prorate_gsc(data: dict, start_date, end_date, data_lag_days=DEFAULT_LAG_GSC) -> dict:
    """
    Apply prorate to a GSC insight data dict.

    Adds keys: is_prorated, days_elapsed, total_days.
    Prorates all keys in COUNT_METRICS_GSC.
    CTR and avg_position are left unchanged.

    Args:
        data          : dict with raw GSC metric values.
        start_date    : period start date.
        end_date      : period end date.
        data_lag_days : GSC reporting lag (default 3). The prorate factor
                        is based on today − lag, matching the actual data
                        available from the GSC API.

    Returns:
        Modified copy of data with prorated values.
    """
    days_elapsed, total_days, factor = calculate_prorate_factor(
        start_date, end_date, data_lag_days=data_lag_days
    )
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


def apply_prorate_ga(data: dict, start_date, end_date, data_lag_days=DEFAULT_LAG_GA) -> dict:
    """
    Apply prorate to a GA insight data dict.

    Adds keys: is_prorated, days_elapsed, total_days.
    Prorates all keys in COUNT_METRICS_GA.
    Bounce rate and avg_session_duration are left unchanged.

    Args:
        data          : dict with raw GA metric values.
        start_date    : period start date.
        end_date      : period end date.
        data_lag_days : GA reporting lag (default 1). The prorate factor is
                        based on today − lag, matching the actual data
                        available from the GA Data API.

    Returns:
        Modified copy of data with prorated values.
    """
    days_elapsed, total_days, factor = calculate_prorate_factor(
        start_date, end_date, data_lag_days=data_lag_days
    )
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
