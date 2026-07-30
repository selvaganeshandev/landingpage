"""Tests for the Insights dashboard's date-window arithmetic.

Two defects are pinned here:

  1. the previous period was one day LONGER than the current one, so every
     "% vs last period" on the page compared 30 days against 31
  2. `days` went straight into int() — '?days=abc' was a 500 and '?days=-5'
     inverted the window instead of being rejected

Run:  python tests/standalone/backend/analytics/test_window_utils.py
"""
import importlib.util
import sys
from datetime import date
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = REPOSITORY_ROOT / 'backend' / 'analytics' / 'window_utils.py'

_spec = importlib.util.spec_from_file_location('window_utils_under_test', MODULE_PATH)
window_utils = importlib.util.module_from_spec(_spec)
sys.modules['window_utils_under_test'] = window_utils
_spec.loader.exec_module(window_utils)

parse_days = window_utils.parse_days
previous_window = window_utils.previous_window
window_start = window_utils.window_start
InvalidWindow = window_utils.InvalidWindow


def _inclusive_length(start, end):
    return (end - start).days + 1


def test_both_windows_are_the_same_length():
    print("  the previous period matches the current period exactly")
    for days in (1, 7, 30, 90, 365):
        end = date(2026, 7, 30)
        start = window_start(end, days)
        assert _inclusive_length(start, end) == days
        prev_start, prev_end = previous_window(start, days)
        assert _inclusive_length(prev_start, prev_end) == days, (
            f'{days}-day window produced a {_inclusive_length(prev_start, prev_end)}-day baseline'
        )


def test_the_regression_case_by_hand():
    print("  30 days ending 30 Jul compares against 1-30 Jun, not 31 May-30 Jun")
    start = window_start(date(2026, 7, 30), 30)
    assert start == date(2026, 7, 1)
    prev_start, prev_end = previous_window(start, 30)
    assert prev_start == date(2026, 6, 1), prev_start
    assert prev_end == date(2026, 6, 30), prev_end


def test_windows_are_adjacent_and_never_overlap():
    print("  the baseline ends the day before the current window starts")
    start = window_start(date(2026, 3, 1), 7)
    prev_start, prev_end = previous_window(start, 7)
    assert prev_end < start
    assert (start - prev_end).days == 1


def test_a_leap_day_does_not_shift_the_baseline_length():
    print("  February 2028 is 29 days and the arithmetic still balances")
    start = window_start(date(2028, 3, 31), 31)
    prev_start, prev_end = previous_window(start, 31)
    assert _inclusive_length(prev_start, prev_end) == 31


def test_days_defaults_when_absent():
    print("  a missing or blank days parameter falls back to 30")
    assert parse_days(None) == 30
    assert parse_days('') == 30
    assert parse_days('  ') == 30
    assert parse_days(None, default=7) == 7


def test_days_accepts_what_the_ui_sends():
    print("  every preset the UI can send is accepted")
    for raw in ('7', '30', '90', '180', '365', '3650', 30):
        assert parse_days(raw) == int(raw)


def test_garbage_is_rejected_not_crashed():
    print("  '?days=abc' is a 400, not a 500")
    for raw in ('abc', '3.5', '30; DROP TABLE', '١٢٣٤٥٦٧٨٩', {}):
        try:
            parse_days(raw)
        except InvalidWindow:
            continue
        raise AssertionError(f'accepted garbage: {raw!r}')


def test_out_of_range_windows_are_rejected():
    print("  zero, negative and absurd windows are refused")
    for raw in ('0', '-5', '-1', '3651', '999999'):
        try:
            parse_days(raw)
        except InvalidWindow:
            continue
        raise AssertionError(f'accepted out-of-range window: {raw!r}')


def main():
    print("=" * 78)
    print("INSIGHTS DATE WINDOWS")
    print("=" * 78)
    for test in (
        test_both_windows_are_the_same_length,
        test_the_regression_case_by_hand,
        test_windows_are_adjacent_and_never_overlap,
        test_a_leap_day_does_not_shift_the_baseline_length,
        test_days_defaults_when_absent,
        test_days_accepts_what_the_ui_sends,
        test_garbage_is_rejected_not_crashed,
        test_out_of_range_windows_are_rejected,
    ):
        test()
    print("=" * 78)
    print("ALL TESTS PASSED")


if __name__ == '__main__':
    main()
