"""Date-window arithmetic for the Insights dashboard.

Pure stdlib on purpose: the two things that were wrong here are arithmetic, and
arithmetic should be testable without Django, a database or a request.

    python tests/standalone/backend/analytics/test_window_utils.py
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Tuple


DEFAULT_WINDOW_DAYS = 30
MIN_WINDOW_DAYS = 1
# The UI sends a flat 3650 for its "All time" preset, and the view clamps that
# down to the domain's first real data date. Anything beyond it is a typo or a
# probe, not a question about the data.
MAX_WINDOW_DAYS = 3650


class InvalidWindow(ValueError):
    """The requested window cannot be honoured. Callers should answer 400."""


def parse_days(raw, default: int = DEFAULT_WINDOW_DAYS) -> int:
    """Read the `days` query parameter.

    `int(request.query_params.get('days', 30))` raised straight out of the view:
    `?days=abc` was a 500, and `?days=-5` silently inverted the window so
    start_date landed AFTER end_date and the page rendered nonsense instead of
    an error. The explicit start_date/end_date path in the same view has
    validated properly all along; this brings the shortcut into line with it.
    """
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return default
    try:
        days = int(str(raw).strip())
    except (TypeError, ValueError):
        raise InvalidWindow('days must be a whole number of days')
    if days < MIN_WINDOW_DAYS:
        raise InvalidWindow(f'days must be at least {MIN_WINDOW_DAYS}')
    if days > MAX_WINDOW_DAYS:
        raise InvalidWindow(f'days must not exceed {MAX_WINDOW_DAYS}')
    return days


def window_start(end_date: date, days: int) -> date:
    """First day of an inclusive `days`-long window ending on `end_date`."""
    return end_date - timedelta(days=days - 1)


def previous_window(start_date: date, days: int) -> Tuple[date, date]:
    """The equally long window immediately before the current one.

    The current window is inclusive of both ends, so a 30-day window running
    1-30 July has a previous window of 1-30 June. Subtracting a flat `days`
    from the day before the start (the old behaviour) reached back to 31 May,
    making the baseline 31 days against the current 30 — so every "% vs last
    period" on the page was measured against an inflated denominator, in the
    same direction, every time.
    """
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days - 1)
    return prev_start, prev_end
