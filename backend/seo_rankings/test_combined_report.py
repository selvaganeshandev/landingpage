"""
Synthetic unit tests for combined_report.merge_sheet — no DB / no Google APIs.
Run: python backend/seo_rankings/test_combined_report.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import combined_report as cr


class Sheet:
    def __init__(self, sheet_type, schedule='weekly'):
        self.sheet_type = sheet_type
        self.schedule = schedule


_failures = []


def check(name, got, expected):
    ok = got == expected
    if not ok:
        _failures.append(f"{name}: got {got!r} expected {expected!r}")
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")


def approx(name, got, expected, tol=0.05):
    ok = got is not None and abs(float(got) - expected) <= tol
    if not ok:
        _failures.append(f"{name}: got {got!r} expected ~{expected}")
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")


# ── 1. GSC wide (pages/queries): counts sum, CTR & position recomputed, WOW % ──
def test_gsc_wide():
    print("test_gsc_wide")
    cols = ['Sr No', 'Queries',
            'W1 Clicks', 'W2 Clicks', 'Clicks WOW %',
            'W1 Impressions', 'W2 Impressions', 'Impressions WOW %',
            'W1 CTR', 'W2 CTR', 'CTR WOW %',
            'W1 Avg Position', 'W2 Avg Position', 'Avg Position WOW %']
    primary = {'columns': cols, 'rows': [
        {'Sr No': 1, 'Queries': 'shoes',
         'W1 Clicks': 100, 'W2 Clicks': 120, 'Clicks WOW %': '+20.0%',
         'W1 Impressions': 1000, 'W2 Impressions': 1200, 'Impressions WOW %': '+20.0%',
         'W1 CTR': 10.0, 'W2 CTR': 10.0, 'CTR WOW %': '+0.0%',
         'W1 Avg Position': 5.0, 'W2 Avg Position': 4.0, 'Avg Position WOW %': '-20.0%'},
    ]}
    secondary = {'columns': cols, 'rows': [
        {'Sr No': 1, 'Queries': 'shoes',
         'W1 Clicks': 50, 'W2 Clicks': 80, 'Clicks WOW %': '+60.0%',
         'W1 Impressions': 1000, 'W2 Impressions': 800, 'Impressions WOW %': '-20.0%',
         'W1 CTR': 5.0, 'W2 CTR': 10.0, 'CTR WOW %': '+100.0%',
         'W1 Avg Position': 9.0, 'W2 Avg Position': 8.0, 'Avg Position WOW %': '-11.1%'},
        {'Sr No': 2, 'Queries': 'boots',
         'W1 Clicks': 10, 'W2 Clicks': 10, 'Clicks WOW %': '+0.0%',
         'W1 Impressions': 100, 'W2 Impressions': 100, 'Impressions WOW %': '+0.0%',
         'W1 CTR': 10.0, 'W2 CTR': 10.0, 'CTR WOW %': '+0.0%',
         'W1 Avg Position': 3.0, 'W2 Avg Position': 3.0, 'Avg Position WOW %': '+0.0%'},
    ]}
    out = cr.merge_sheet(Sheet('gsc_queries'), primary, secondary)
    r = out['rows'][0]
    check('shoes W2 Clicks sum', r['W2 Clicks'], 200)            # 120+80
    check('shoes W2 Impr sum', r['W2 Impressions'], 2000)        # 1200+800
    approx('shoes W2 CTR recomputed', r['W2 CTR'], 10.0)         # 200/2000
    # position impr-weighted W2: (4*1200 + 8*800)/2000 = 5.6
    approx('shoes W2 position weighted', r['W2 Avg Position'], 5.6)
    # clicks WOW: W1 merged=150, W2 merged=200 -> +33.3%
    check('shoes Clicks WOW %', r['Clicks WOW %'], '+33.3%')
    check('union adds boots', len(out['rows']), 2)
    check('boots present', out['rows'][1]['Queries'], 'boots')


# ── 2. GSC overview (metric-down) + YOY back-computation ─────────────────────
def test_metric_down_yoy():
    print("test_metric_down_yoy")
    cols = ['Metric', 'M1', 'M2', 'MOM %', 'YOY %']
    primary = {'columns': cols, 'rows': [
        {'Metric': 'Clicks', 'M1': 100, 'M2': 110, 'MOM %': '+10.0%', 'YOY %': '+10.0%'},
        {'Metric': 'Impressions', 'M1': 1000, 'M2': 1100, 'MOM %': '+10.0%', 'YOY %': '+10.0%'},
        {'Metric': 'CTR', 'M1': 10.0, 'M2': 10.0, 'MOM %': '+0.0%', 'YOY %': '+0.0%'},
    ]}
    secondary = {'columns': cols, 'rows': [
        {'Metric': 'Clicks', 'M1': 50, 'M2': 90, 'MOM %': '+80.0%', 'YOY %': '+50.0%'},
        {'Metric': 'Impressions', 'M1': 500, 'M2': 900, 'MOM %': '+80.0%', 'YOY %': '+50.0%'},
        {'Metric': 'CTR', 'M1': 10.0, 'M2': 10.0, 'MOM %': '+0.0%', 'YOY %': '+0.0%'},
    ]}
    out = cr.merge_sheet(Sheet('gsc_overview', 'monthly'), primary, secondary)
    rows = {r['Metric']: r for r in out['rows']}
    check('Clicks M2 sum', rows['Clicks']['M2'], 200)            # 110+90
    approx('CTR M2 recomputed', rows['CTR']['M2'], 10.0)         # 200/2000
    # Clicks MOM: M1 merged=150, M2 merged=200 -> +33.3%
    check('Clicks MOM %', rows['Clicks']['MOM %'], '+33.3%')
    # Clicks YOY back-compute: pbase=110/1.1=100, sbase=90/1.5=60 -> base160,cur200 -> +25%
    check('Clicks YOY % back-computed', rows['Clicks']['YOY %'], '+25.0%')


# ── 3. keyword ranking: union + best rank + overview recompute ───────────────
def test_keyword_rank():
    print("test_keyword_rank")
    cols = ['Sr No', 'Keywords', 'Avg. Volume', 'W1', 'W2', 'Change (W2 vs W1)']
    primary = {'columns': cols, 'overview': [
        {'primary keyword ranking': 'Top 5', 'W1': 1, 'W2': 1, 'Change (W2 vs W1)': 0},
        {'primary keyword ranking': 'Total keywords', 'W1': 1, 'W2': 1, 'Change (W2 vs W1)': 0},
    ], 'rows': [
        {'Sr No': 1, 'Keywords': 'a', 'Avg. Volume': 500, 'W1': 8, 'W2': 4,
         'Change (W2 vs W1)': 4},
    ]}
    secondary = {'columns': cols, 'rows': [
        {'Sr No': 1, 'Keywords': 'a', 'Avg. Volume': 500, 'W1': 3, 'W2': 9,
         'Change (W2 vs W1)': -6},     # overlaps 'a' — best rank should win
        {'Sr No': 2, 'Keywords': 'b', 'Avg. Volume': 200, 'W1': 'NA', 'W2': 2,
         'Change (W2 vs W1)': 'NA'},
    ]}
    out = cr.merge_sheet(Sheet('keyword_ranking'), primary, secondary)
    rows = {r['Keywords']: r for r in out['rows']}
    check('a W1 best rank', rows['a']['W1'], 3)                  # min(8,3)
    check('a W2 best rank', rows['a']['W2'], 4)                  # min(4,9)
    check('a change recomputed', rows['a']['Change (W2 vs W1)'], -1)  # 3-4
    check('b unioned', rows['b']['W2'], 2)
    # overview recomputed from merged ranks: W2 -> a=4(Top5), b=2(Top5) => 2
    ov = {r['primary keyword ranking']: r for r in out['overview']}
    check('overview Top5 W2 count', ov['Top 5']['W2'], 2)
    check('overview total W2', ov['Total keywords']['W2'], 2)


# ── 4. safety: errored / empty secondary returns primary unchanged ───────────
def test_fallback():
    print("test_fallback")
    primary = {'columns': ['Sr No', 'Queries', 'W1 Clicks'],
               'rows': [{'Sr No': 1, 'Queries': 'x', 'W1 Clicks': 5}]}
    check('errored secondary -> primary',
          cr.merge_sheet(Sheet('gsc_queries'), primary, {'error': 'GA down'}), primary)
    check('empty secondary -> primary',
          cr.merge_sheet(Sheet('gsc_queries'), primary, {}), primary)
    check('unsupported type -> primary',
          cr.merge_sheet(Sheet('competitor_ranking_summary'), primary,
                         {'columns': ['x'], 'rows': []}), primary)


# ── 5. domain_metrics: counts sum, numeric Change recomputed ─────────────────
def test_domain_metrics():
    print("test_domain_metrics")
    cols = ['Metric', 'P1', 'P2', 'Change']
    primary = {'columns': cols, 'rows': [
        {'Metric': 'Top 1 Keywords', 'P1': 5, 'P2': 7, 'Change': 2},
        {'Metric': 'Rankmax Score', 'P1': 80, 'P2': 90, 'Change': 10},
    ]}
    secondary = {'columns': cols, 'rows': [
        {'Metric': 'Top 1 Keywords', 'P1': 3, 'P2': 3, 'Change': 0},
        {'Metric': 'Rankmax Score', 'P1': 60, 'P2': 70, 'Change': 10},
    ]}
    out = cr.merge_sheet(Sheet('domain_metrics'), primary, secondary)
    rows = {r['Metric']: r for r in out['rows']}
    check('Top1 P2 sum', rows['Top 1 Keywords']['P2'], 10)       # 7+3
    check('Top1 Change recomputed', rows['Top 1 Keywords']['Change'], 2)  # P2sum 10 - P1sum 8
    approx('Rankmax averaged P2', rows['Rankmax Score']['P2'], 80.0)  # (90+70)/2


if __name__ == '__main__':
    test_gsc_wide()
    test_metric_down_yoy()
    test_keyword_rank()
    test_fallback()
    test_domain_metrics()
    print()
    if _failures:
        print(f"{len(_failures)} FAILURE(S):")
        for f in _failures:
            print("  -", f)
        sys.exit(1)
    print("ALL TESTS PASSED")
