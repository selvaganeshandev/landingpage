"""
Combined (primary + secondary domain) SEO report merging.

This module is PURELY ADDITIVE. It takes the output dicts produced by the
existing ``_fetch_*`` functions in ``views.py`` (run once per domain with the
*same* sheet configuration) and pools them into a single result that looks
exactly like a normal single-domain report sheet — "show it as now", with both
domains' numbers combined.

Design guarantees
-----------------
* Existing single-domain fetchers are NOT modified. The merge runs only when a
  caller passes both a primary and a secondary result.
* Because the same ``sheet`` config drives both fetches, the two results share
  an identical ``columns`` list. The merge is therefore column-name driven.
* Combination rules by column kind:
    - COUNT  (Clicks, Impressions, Sessions, Users, Page Views, Events,
              Leads, keyword counts, search volumes): summed. Prorated cells
              formatted "raw (projected)" sum each part independently.
    - RATE   (CTR, Avg Position, Bounce Rate, Engagement Rate): recomputed on
              the pooled totals — CTR = clicks/impr, position/bounce =
              traffic-weighted average — never naively averaged.
    - CHANGE (MOM %, WOW %, YOY %, Difference, Change): recomputed from the
              merged period values. YOY base (absent from the output) is
              back-computed from each domain's reported YOY % and current value.
    - RANK   (keyword positions): unioned across domains; for a keyword tracked
              on both, the better (lower) rank wins.
* SAFETY: every handler is wrapped so that ANY failure, empty/errored secondary,
  or structure the merger does not recognise falls back to the PRIMARY result
  unchanged. Combined mode can never be worse than the single-domain report and
  never raises.
"""

import logging
import re

logger = logging.getLogger(__name__)

# Sheet types the merger combines. Anything not listed (or that raises) falls
# back to primary-only so the sheet still renders with the primary domain.
_MERGEABLE = {
    'gsc_pages', 'gsc_queries', 'gsc_branded_queries', 'gsc_non_branded_queries',
    'ga_landing_pages', 'ga_other_sources',
    'gsc_overview', 'ga_overview', 'domain_metrics',
    'ga_gsc_reconcile',
    'ga_organic_traffic_breakup', 'ga_country_events',
    'keyword_ranking', 'keyword_ranking_summary',
}

_CHANGE_RE = re.compile(r'(MOM|WOW|YOY)\s*%', re.IGNORECASE)
_RATE_TOKENS = ('CTR', 'Position', 'Bounce Rate', 'Engagement Rate')

# Rank sentinel used by the keyword/summary fetchers for "not ranked".
_NOT_RANKED = 101


# ── cell parsing helpers ────────────────────────────────────────────────────

def _is_change_col(name):
    n = str(name)
    return bool(_CHANGE_RE.search(n)) or 'Change' in n or 'Difference' in n


def _is_rate_col(name):
    return any(tok in str(name) for tok in _RATE_TOKENS)


def _parse_count(cell):
    """Parse a count cell into (raw, projected, had_projection).

    Handles plain numbers and the prorated "raw (projected)" string format.
    Returns (None, None, False) for blanks/non-numeric.
    """
    if cell is None or cell == '':
        return None, None, False
    if isinstance(cell, (int, float)):
        return float(cell), None, False
    s = str(cell).strip().replace(',', '')
    m = re.match(r'^(-?\d+(?:\.\d+)?)\s*\((-?\d+(?:\.\d+)?)\)$', s)
    if m:
        return float(m.group(1)), float(m.group(2)), True
    try:
        return float(s), None, False
    except ValueError:
        return None, None, False


def _fmt_count(raw_sum, proj_sum, had_proj):
    """Inverse of _parse_count for summed values. Keeps integers integer."""
    def _trim(x):
        if x is None:
            return None
        return int(x) if float(x).is_integer() else round(x, 2)
    r = _trim(raw_sum)
    if had_proj and proj_sum is not None:
        return f"{r} ({_trim(proj_sum)})"
    return r if r is not None else 0


def _num(cell):
    """Best-effort numeric value of any cell (uses projected part if present)."""
    raw, proj, had = _parse_count(cell)
    if had and proj is not None:
        return proj
    if raw is not None:
        return raw
    s = str(cell).strip().replace('%', '').replace('+', '').replace(',', '')
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _pct_str(cur, base):
    if base is None or cur is None or base == 0:
        return 'N/A'
    return f"{round((cur - base) / base * 100, 1):+.1f}%"


def _parse_pct(cell):
    """Parse '+5.0%' / '-3.2%' / 'N/A' → 0.05 / -0.032 / None."""
    if cell is None:
        return None
    s = str(cell).strip().replace('%', '').replace('+', '')
    if s in ('', 'N/A', 'NA', 'None'):
        return None
    try:
        return float(s) / 100.0
    except ValueError:
        return None


# ── column-family helpers (wide tables: dim in rows, metric+period in cols) ──

def _metric_of_change(col):
    """'Clicks MOM %' -> 'Clicks'; 'Avg Position YOY %' -> 'Avg Position'."""
    return re.sub(r'\s+(MOM|WOW|YOY)\s*%$', '', str(col)).strip()


def _period_cols_for_metric(columns, ml):
    """Ordered period value columns for a metric label (cols ending ' <ml>')."""
    suffix = ' ' + ml
    return [c for c in columns if c.endswith(suffix) and not _is_change_col(c)]


def _sibling_col(period_metric_col, ml_from, ml_to):
    """'21 Jun CTR' with ml_from='CTR', ml_to='Clicks' -> '21 Jun Clicks'."""
    if period_metric_col.endswith(' ' + ml_from):
        return period_metric_col[: -len(ml_from)] + ml_to
    return None


# ── generic merge for the "wide per-dimension" family ───────────────────────
# gsc_pages/queries/branded/non_branded, ga_landing_pages, ga_other_sources.

def _merge_wide(sheet_type, primary, secondary):
    columns = primary.get('columns') or []
    if not columns or columns[:1] != ['Sr No']:
        return None
    dim_col = columns[1]
    value_cols = columns[2:]

    p_rows = primary.get('rows') or []
    s_rows = secondary.get('rows') or []
    s_index = {str(r.get(dim_col)): r for r in s_rows}

    # union of dimension keys: primary order, then secondary-only keys
    ordered_keys = [str(r.get(dim_col)) for r in p_rows]
    seen = set(ordered_keys)
    for r in s_rows:
        k = str(r.get(dim_col))
        if k not in seen:
            ordered_keys.append(k)
            seen.add(k)
    p_index = {str(r.get(dim_col)): r for r in p_rows}

    count_cols = [c for c in value_cols if not _is_change_col(c) and not _is_rate_col(c)]
    rate_cols = [c for c in value_cols if not _is_change_col(c) and _is_rate_col(c)]
    change_cols = [c for c in value_cols if _is_change_col(c)]

    merged_rows = []
    for idx, key in enumerate(ordered_keys, 1):
        pr = p_index.get(key, {})
        sr = s_index.get(key, {})
        row = {'Sr No': idx, dim_col: key}

        # 1) counts: sum raw + projected parts independently
        for c in count_cols:
            pra, prp, ph = _parse_count(pr.get(c))
            sra, srp, sh = _parse_count(sr.get(c))
            raw = (pra or 0) + (sra or 0)
            had = ph or sh
            proj = ((prp if prp is not None else pra) or 0) + ((srp if srp is not None else sra) or 0) if had else None
            row[c] = _fmt_count(raw, proj, had)

        # 2) rates: recompute on pooled siblings
        for c in rate_cols:
            row[c] = _recompute_rate_wide(c, columns, pr, sr, row)

        # 3) changes: recompute from merged period values
        for c in change_cols:
            row[c] = _recompute_change_wide(c, columns, merged_rows, row, pr, sr)

        merged_rows.append(row)

    out = dict(primary)
    out['rows'] = merged_rows
    out['total_rows'] = len(merged_rows)
    return out


def _recompute_rate_wide(col, columns, pr, sr, merged_row):
    """Recompute a CTR/Position rate cell on pooled traffic for one period."""
    is_ctr = 'CTR' in col
    is_pos = 'Position' in col
    ml = 'CTR' if is_ctr else ('Avg Position' if 'Avg Position' in col else None)
    # locate sibling clicks/impressions columns for this period
    clicks_col = _sibling_col(col, ml, 'Clicks') if ml else None
    impr_col = _sibling_col(col, ml, 'Impressions') if ml else None
    if clicks_col not in columns:
        clicks_col = None
    if impr_col not in columns:
        impr_col = None

    p_impr = _num(pr.get(impr_col)) if impr_col else None
    s_impr = _num(sr.get(impr_col)) if impr_col else None

    if is_ctr and clicks_col and impr_col:
        clicks = (_num(pr.get(clicks_col)) or 0) + (_num(sr.get(clicks_col)) or 0)
        impr = (p_impr or 0) + (s_impr or 0)
        return round(clicks / impr * 100, 2) if impr else 0

    # weighted average fallback (position, or CTR without count siblings)
    pv, sv = _num(pr.get(col)), _num(sr.get(col))
    wp = p_impr if p_impr is not None else (1 if pv is not None else 0)
    ws = s_impr if s_impr is not None else (1 if sv is not None else 0)
    tot = (wp or 0) + (ws or 0)
    if tot:
        val = ((pv or 0) * (wp or 0) + (sv or 0) * (ws or 0)) / tot
        return round(val, 1 if is_pos else 2)
    return pv if pv is not None else sv


def _recompute_change_wide(col, columns, merged_rows, merged_row, pr, sr):
    """Recompute MOM/WOW/YOY % for a metric from the merged row's period cols."""
    ml = _metric_of_change(col)
    period_cols = _period_cols_for_metric(columns, ml)
    if 'YOY' in col.upper():
        # back-compute each domain's prior-year base from its reported YOY %
        cur_col = period_cols[-1] if period_cols else None
        if not cur_col:
            return 'N/A'
        p_cur, s_cur = _num(pr.get(cur_col)), _num(sr.get(cur_col))
        p_yoy, s_yoy = _parse_pct(pr.get(col)), _parse_pct(sr.get(col))
        p_base = (p_cur / (1 + p_yoy)) if (p_cur is not None and p_yoy is not None and (1 + p_yoy) != 0) else None
        s_base = (s_cur / (1 + s_yoy)) if (s_cur is not None and s_yoy is not None and (1 + s_yoy) != 0) else None
        base = (p_base or 0) + (s_base or 0) if (p_base is not None or s_base is not None) else None
        cur = (p_cur or 0) + (s_cur or 0)
        return _pct_str(cur, base)
    # MOM / WOW: last two merged period values
    if len(period_cols) < 2:
        return 'N/A'
    cur = _num(merged_row.get(period_cols[-1]))
    prev = _num(merged_row.get(period_cols[-2]))
    return _pct_str(cur, prev)


# ── metric-down family (rows = metrics, cols = periods) ─────────────────────
# gsc_overview (legacy rows), ga_overview, domain_metrics, country section 1.

def _classify_metric_row(label):
    l = str(label)
    if 'CTR' in l:
        return 'ctr'
    if 'Position' in l:
        return 'position'
    if 'Bounce Rate' in l or 'Engagement Rate' in l:
        return 'rate_weighted'
    if 'Score' in l:  # Rankmax Score — average across domains
        return 'avg'
    return 'count'


def _merge_metric_down(sheet_type, primary, secondary, dim_col='Metric'):
    columns = primary.get('columns') or []
    if not columns or columns[0] != dim_col:
        return None
    period_cols = [c for c in columns[1:] if not _is_change_col(c)]
    change_cols = [c for c in columns[1:] if _is_change_col(c)]

    p_rows = primary.get('rows') or []
    p_by_label = {str(r.get(dim_col)): r for r in p_rows}
    s_by_label = {str(r.get(dim_col)): r for r in (secondary.get('rows') or [])}

    # first pass: merge count + avg rows (CTR/position/bounce deferred — they
    # depend on the merged counts and on each domain's own weight row)
    merged_by_label = {}
    merged_rows = []
    for pr in p_rows:
        label = str(pr.get(dim_col))
        sr = s_by_label.get(label, {})
        kind = _classify_metric_row(label)
        row = {dim_col: label}
        if kind == 'count':
            for c in period_cols:
                pra, prp, ph = _parse_count(pr.get(c))
                sra, srp, sh = _parse_count(sr.get(c))
                raw = (pra or 0) + (sra or 0)
                had = ph or sh
                proj = ((prp if prp is not None else pra) or 0) + ((srp if srp is not None else sra) or 0) if had else None
                row[c] = _fmt_count(raw, proj, had)
        elif kind == 'avg':
            for c in period_cols:
                pv, sv = _num(pr.get(c)), _num(sr.get(c))
                vals = [v for v in (pv, sv) if v is not None]
                row[c] = round(sum(vals) / len(vals), 1) if vals else 0
        else:
            row['__deferred__'] = (kind, pr, sr)  # resolve in 2nd pass
        merged_rows.append(row)
        merged_by_label[label] = row

    # 2nd pass: rate rows (CTR from merged counts; position/bounce weighted by
    # each domain's own impressions/sessions row)
    for row in merged_rows:
        if '__deferred__' not in row:
            continue
        kind, pr, sr = row.pop('__deferred__')
        label = str(row[dim_col])
        for c in period_cols:
            row[c] = _recompute_rate_metric_down(
                kind, label, c, merged_by_label, p_by_label, s_by_label, pr, sr
            )

    # change columns (recompute per row from merged period values / YOY back-calc)
    for row in merged_rows:
        label = str(row[dim_col])
        pr = p_by_label.get(label, {})
        sr = s_by_label.get(label, {})
        for cc in change_cols:
            row[cc] = _recompute_change_metric_down(
                cc, period_cols, row, pr, sr, label, merged_by_label
            )

    out = dict(primary)
    out['rows'] = merged_rows
    out['total_rows'] = len(merged_rows)
    return out


def _ctr_sibling_labels(ctr_label):
    """'CTR'->('Clicks','Impressions'); 'Branded CTR'->('Branded Clicks',...)."""
    prefix = ctr_label.replace('CTR', '').strip()
    if prefix:
        return f"{prefix} Clicks", f"{prefix} Impressions"
    return 'Clicks', 'Impressions'


def _merged_val(merged_by_label, label, col):
    row = merged_by_label.get(label)
    return _num(row.get(col)) if row else None


def _weight_label(label, available):
    """Pick the per-domain weight row label for a position/bounce/engagement
    metric: impressions for position, sessions for bounce/engagement."""
    if 'Position' in label:
        prefix = re.sub(r'(Avg Position|Position)', '', label).strip()
        for cand in ((f"{prefix} Impressions" if prefix else None), 'Impressions',
                     'Total Impressions'):
            if cand and cand in available:
                return cand
    for cand in ('Organic Sessions', 'Sessions', 'Users'):
        if cand in available:
            return cand
    return None


def _recompute_rate_metric_down(kind, label, col, merged_by_label,
                                p_by_label, s_by_label, pr, sr):
    if kind == 'ctr':
        clicks_lbl, impr_lbl = _ctr_sibling_labels(label)
        clicks = _merged_val(merged_by_label, clicks_lbl, col)
        impr = _merged_val(merged_by_label, impr_lbl, col)
        if clicks is not None and impr:
            return round(clicks / impr * 100, 2)
        # fall through to weighted average if counts unavailable

    # position / bounce / engagement → weight by each domain's own traffic row
    wlbl = _weight_label(label, set(p_by_label) | set(s_by_label))
    pv, sv = _num(pr.get(col)), _num(sr.get(col))
    p_w = _num((p_by_label.get(wlbl) or {}).get(col)) if wlbl else None
    s_w = _num((s_by_label.get(wlbl) or {}).get(col)) if wlbl else None
    if (p_w or s_w):
        p_w, s_w = (p_w or 0), (s_w or 0)
        tot = p_w + s_w
        if tot:
            digits = 1 if 'Position' in label else 2
            return round(((pv or 0) * p_w + (sv or 0) * s_w) / tot, digits)
    vals = [v for v in (pv, sv) if v is not None]
    return round(sum(vals) / len(vals), 1 if 'Position' in label else 2) if vals else 0


def _recompute_change_metric_down(cc, period_cols, row, pr, sr, label, merged_by_label):
    if 'YOY' in cc.upper():
        cur_col = period_cols[-1] if period_cols else None
        if not cur_col:
            return 'N/A'
        p_cur, s_cur = _num(pr.get(cur_col)), _num(sr.get(cur_col))
        p_yoy, s_yoy = _parse_pct(pr.get(cc)), _parse_pct(sr.get(cc))
        p_base = (p_cur / (1 + p_yoy)) if (p_cur is not None and p_yoy is not None and (1 + p_yoy) != 0) else None
        s_base = (s_cur / (1 + s_yoy)) if (s_cur is not None and s_yoy is not None and (1 + s_yoy) != 0) else None
        base = (p_base or 0) + (s_base or 0) if (p_base is not None or s_base is not None) else None
        cur = _num(row.get(cur_col))
        return _pct_str(cur, base)
    if len(period_cols) < 2:
        return 'N/A'
    cur = _num(row.get(period_cols[-1]))
    prev = _num(row.get(period_cols[-2]))
    if cc == 'Change':  # numeric delta (domain_metrics)
        if cur is None or prev is None:
            return 0
        d = cur - prev
        return int(d) if float(d).is_integer() else round(d, 2)
    return _pct_str(cur, prev)


# ── count-only join (no rates): breakup main/drill, country event subtables ──

def _merge_count_join(columns, p_rows, s_rows, dim_cols):
    """Join two row lists on dim_cols, sum every non-dim/non-change column,
    recompute change cols. Used for pure-count tables."""
    change_cols = [c for c in columns if _is_change_col(c)]
    sum_cols = [c for c in columns if c not in dim_cols and c not in change_cols and c != 'Sr No']

    def keyof(r):
        return tuple(str(r.get(d, '')) for d in dim_cols)

    s_index = {keyof(r): r for r in s_rows}
    ordered, seen = [], set()
    for r in p_rows:
        k = keyof(r)
        ordered.append((k, r))
        seen.add(k)
    p_index = {keyof(r): r for r in p_rows}
    for r in s_rows:
        k = keyof(r)
        if k not in seen:
            ordered.append((k, None))
            seen.add(k)

    has_srno = 'Sr No' in columns
    merged = []
    for idx, (k, _) in enumerate(ordered, 1):
        pr = p_index.get(k, {})
        sr = s_index.get(k, {})
        row = {}
        if has_srno:
            row['Sr No'] = idx
        for d in dim_cols:
            row[d] = pr.get(d, sr.get(d, ''))
        for c in sum_cols:
            pra, prp, ph = _parse_count(pr.get(c))
            sra, srp, sh = _parse_count(sr.get(c))
            raw = (pra or 0) + (sra or 0)
            had = ph or sh
            proj = ((prp if prp is not None else pra) or 0) + ((srp if srp is not None else sra) or 0) if had else None
            row[c] = _fmt_count(raw, proj, had)
        for c in change_cols:
            ml = _metric_of_change(c)
            pcols = _period_cols_for_metric(columns, ml) if ml else \
                [x for x in columns if x not in dim_cols and not _is_change_col(x) and x != 'Sr No']
            if len(pcols) >= 2:
                row[c] = _pct_str(_num(row.get(pcols[-1])), _num(row.get(pcols[-2])))
            else:
                row[c] = 'N/A'
        merged.append(row)
    return merged


# ── keyword ranking (best-rank union) ───────────────────────────────────────

def _rank_val(cell):
    """Rank cell → int (lower = better). 'NA'/blank → None."""
    if cell is None or cell == '' or str(cell).strip().upper() in ('NA', 'N/A'):
        return None
    try:
        v = int(float(str(cell).strip()))
        return v
    except (ValueError, TypeError):
        return None


def _merge_keyword_rank(columns, p_rows, s_rows, dim_col, period_cols,
                        attr_cols, change_col, change_kind):
    """Union keywords; best (min) rank per period; recompute change."""
    s_index = {str(r.get(dim_col)): r for r in s_rows}
    ordered = [str(r.get(dim_col)) for r in p_rows]
    seen = set(ordered)
    for r in s_rows:
        k = str(r.get(dim_col))
        if k not in seen:
            ordered.append(k)
            seen.add(k)
    p_index = {str(r.get(dim_col)): r for r in p_rows}

    has_srno = 'Sr No' in columns
    merged = []
    for idx, key in enumerate(ordered, 1):
        pr = p_index.get(key, {})
        sr = s_index.get(key, {})
        row = {}
        if has_srno:
            row['Sr No'] = idx
        row[dim_col] = key
        for a in attr_cols:
            # search volume: same keyword → identical; take max as a guard
            if 'Volume' in a:
                pv, sv = _num(pr.get(a)), _num(sr.get(a))
                row[a] = int(max(pv or 0, sv or 0))
            else:
                row[a] = pr.get(a) if pr.get(a) not in (None, '') else sr.get(a, '')
        for c in period_cols:
            pr_rank, sr_rank = _rank_val(pr.get(c)), _rank_val(sr.get(c))
            ranks = [r for r in (pr_rank, sr_rank) if r is not None]
            row[c] = min(ranks) if ranks else (pr.get(c) if c in pr else sr.get(c, 'NA'))
        if change_col and len(period_cols) >= 2:
            cur = _rank_val(row.get(period_cols[-1]))
            prev = _rank_val(row.get(period_cols[-2]))
            if cur is not None and prev is not None:
                row[change_col] = prev - cur  # positive = improved
            else:
                row[change_col] = 'NA'
        merged.append(row)
    return merged


def _bucket_of(rank):
    if rank is None or rank >= _NOT_RANKED:
        return None
    if rank <= 5:
        return 'Top 5'
    if rank <= 10:
        return 'Top 6-10'
    if rank <= 20:
        return 'Top 11-20'
    if rank <= 30:
        return 'Top 21-30'
    if rank <= 50:
        return 'Top 31-50'
    return 'Above 50'


# ── top-level dispatch ──────────────────────────────────────────────────────

def _secondary_usable(secondary):
    if not secondary or secondary.get('error'):
        return False
    return bool(secondary.get('columns') or secondary.get('tables') or secondary.get('rows'))


def merge_sheet(sheet, primary, secondary):
    """Merge a secondary domain's sheet output into the primary's.

    Returns a NEW result dict (never mutates inputs). On any problem returns the
    primary result unchanged so combined mode is never worse than single-domain.
    """
    sheet_type = getattr(sheet, 'sheet_type', None)
    try:
        if sheet_type not in _MERGEABLE or not _secondary_usable(secondary):
            return primary

        if sheet_type in ('gsc_pages', 'gsc_queries', 'gsc_branded_queries',
                          'gsc_non_branded_queries', 'ga_landing_pages',
                          'ga_other_sources'):
            return _merge_wide(sheet_type, primary, secondary) or primary

        if sheet_type in ('ga_overview', 'domain_metrics'):
            return _merge_metric_down(sheet_type, primary, secondary) or primary

        if sheet_type == 'gsc_overview':
            return _merge_gsc_overview(primary, secondary) or primary

        if sheet_type == 'ga_gsc_reconcile':
            return _merge_reconcile(primary, secondary) or primary

        if sheet_type == 'ga_organic_traffic_breakup':
            return _merge_tables_count(primary, secondary, first_dim='Page Type',
                                       drill_dim=('Page URL', 'Category')) or primary

        if sheet_type == 'ga_country_events':
            return _merge_country_events(primary, secondary) or primary

        if sheet_type == 'keyword_ranking':
            return _merge_keyword_ranking(sheet, primary, secondary) or primary

        if sheet_type == 'keyword_ranking_summary':
            return _merge_keyword_summary(primary, secondary) or primary

        return primary
    except Exception as e:  # never break a report because of merging
        logger.warning(f"combined report merge failed for {sheet_type}: {e}", exc_info=True)
        return primary


# ── per-sheet wrappers that handle the `tables` structures ──────────────────

def _merge_gsc_overview(primary, secondary):
    # legacy metric-down rows
    out = _merge_metric_down('gsc_overview', primary, secondary) or dict(primary)
    out = dict(out)
    # sub-tables: Clicks / Impressions are count joins on 'Months'; CTR recompute
    p_tables = primary.get('tables') or []
    s_tables = secondary.get('tables') or []
    if p_tables and len(p_tables) == len(s_tables):
        merged_tables = []
        for pt, st in zip(p_tables, s_tables):
            title = pt.get('title', '')
            cols = pt.get('columns', [])
            if 'CTR' in title:
                merged_tables.append(_merge_ctr_table(pt, st, merged_tables))
            else:
                rows = _merge_count_join(cols, pt.get('rows', []), st.get('rows', []), ['Months'])
                merged_tables.append({'title': title, 'columns': cols, 'rows': rows})
        out['tables'] = merged_tables
    return out


def _merge_ctr_table(pt, st, prior_merged):
    """CTR sub-table = merged Clicks ÷ merged Impressions, by 'Months' row."""
    cols = pt.get('columns', [])
    clicks_tbl = next((t for t in prior_merged if 'Clicks' in t.get('title', '')), None)
    impr_tbl = next((t for t in prior_merged if 'Impressions' in t.get('title', '')), None)
    rows = []
    p_rows = pt.get('rows', [])
    s_index = {str(r.get('Months')): r for r in st.get('rows', [])}
    cl_index = {str(r.get('Months')): r for r in (clicks_tbl or {}).get('rows', [])}
    im_index = {str(r.get('Months')): r for r in (impr_tbl or {}).get('rows', [])}
    # value columns of CTR table (Total CTR / Branded / Non-Branded)
    val_map = {  # CTR column -> (clicks column, impressions column) in sibling tables
        'Total CTR': ('Total Clicks', 'Total Impressions'),
        'Branded': ('Branded', 'Branded'),
        'Non-Branded': ('Non-Branded', 'Non-Branded'),
    }
    change_cols = [c for c in cols if _is_change_col(c)]
    for pr in p_rows:
        month = str(pr.get('Months'))
        cl = cl_index.get(month, {})
        im = im_index.get(month, {})
        row = {'Months': month}
        for c in cols:
            if c == 'Months' or _is_change_col(c):
                continue
            cl_col, im_col = val_map.get(c, (None, None))
            clv = _num(cl.get(cl_col)) if cl_col else None
            imv = _num(im.get(im_col)) if im_col else None
            row[c] = round(clv / imv * 100, 2) if (clv is not None and imv) else _num(pr.get(c))
        for cc in change_cols:
            row[cc] = 'N/A'  # CTR change recomputed only if periods available
        rows.append(row)
    return {'title': pt.get('title', 'CTR'), 'columns': cols, 'rows': rows}


def _merge_reconcile(primary, secondary):
    columns = primary.get('columns') or []
    if 'Month' not in columns:
        return None
    p_rows = primary.get('rows') or []
    s_index = {str(r.get('Month')): r for r in (secondary.get('rows') or [])}
    sum_cols = ['Sessions', 'Clicks', 'New Users', 'Lead Count Events', 'Direct Leads']
    merged = []
    for idx, pr in enumerate(p_rows, 1):
        month = str(pr.get('Month'))
        sr = s_index.get(month, {})
        row = {'Sr No': idx, 'Month': month}
        for c in sum_cols:
            if c not in columns:
                continue
            pra, prp, ph = _parse_count(pr.get(c))
            sra, srp, sh = _parse_count(sr.get(c))
            raw = (pra or 0) + (sra or 0)
            had = ph or sh
            proj = ((prp if prp is not None else pra) or 0) + ((srp if srp is not None else sra) or 0) if had else None
            row[c] = _fmt_count(raw, proj, had)
        # Bounce Rate: session-weighted
        if 'Bounce Rate' in columns:
            p_s = _num(pr.get('Sessions')) or 0
            s_s = _num(sr.get('Sessions')) or 0
            pv, sv = _num(pr.get('Bounce Rate')), _num(sr.get('Bounce Rate'))
            tot = p_s + s_s
            row['Bounce Rate'] = round(((pv or 0) * p_s + (sv or 0) * s_s) / tot, 2) if tot else (pv or sv or 0)
        # Clicks to Sessions Ratio: recompute on merged totals
        if 'Clicks to Sessions Ratio' in columns:
            sess = _num(row.get('Sessions')) or 0
            clk = _num(row.get('Clicks')) or 0
            row['Clicks to Sessions Ratio'] = round(sess / clk, 2) if clk else 'N/A'
        merged.append(row)
    out = dict(primary)
    out['rows'] = merged
    out['total_rows'] = len(merged)
    return out


def _merge_tables_count(primary, secondary, first_dim, drill_dim):
    """Breakup: section-1 table joins on first_dim; drill tables on drill_dim."""
    p_tables = primary.get('tables') or []
    s_tables = secondary.get('tables') or []
    if not p_tables:
        # legacy single table
        cols = primary.get('columns') or []
        rows = _merge_count_join(cols, primary.get('rows', []), secondary.get('rows', []), [first_dim])
        out = dict(primary)
        out['rows'] = rows
        out['total_rows'] = len(rows)
        return out
    s_by_title = {t.get('title'): t for t in s_tables}
    merged_tables = []
    for pt in p_tables:
        title = pt.get('title')
        st = s_by_title.get(title, {'rows': []})
        cols = pt.get('columns', [])
        dims = [first_dim] if first_dim in cols else [c for c in drill_dim if c in cols]
        if not dims:
            merged_tables.append(pt)
            continue
        rows = _merge_count_join(cols, pt.get('rows', []), st.get('rows', []), dims)
        merged_tables.append({'title': title, 'columns': cols, 'rows': rows})
    out = dict(primary)
    out['tables'] = merged_tables
    if merged_tables:
        out['columns'] = merged_tables[0]['columns']
        out['rows'] = merged_tables[0]['rows']
        out['total_rows'] = len(merged_tables[0]['rows'])
    return out


def _merge_country_events(primary, secondary):
    p_tables = primary.get('tables') or []
    s_tables = secondary.get('tables') or []
    if not p_tables:
        return _merge_metric_down('ga_country_events', primary, secondary)
    s_by_title = {t.get('title'): t for t in s_tables}
    merged_tables = []
    for pt in p_tables:
        title = pt.get('title')
        st = s_by_title.get(title, {'rows': [], 'columns': pt.get('columns', [])})
        cols = pt.get('columns', [])
        if cols and cols[0] == 'Metric':  # Overall Metrics section → metric-down
            merged = _merge_metric_down(
                'ga_country_events',
                {'columns': cols, 'rows': pt.get('rows', [])},
                {'columns': cols, 'rows': st.get('rows', [])},
            )
            merged_tables.append({'title': title, 'columns': cols,
                                  'rows': (merged or {}).get('rows', pt.get('rows', []))})
        else:  # Country × period → count join
            rows = _merge_count_join(cols, pt.get('rows', []), st.get('rows', []), ['Country'])
            merged_tables.append({'title': title, 'columns': cols, 'rows': rows})
    out = dict(primary)
    out['tables'] = merged_tables
    if merged_tables:
        out['columns'] = merged_tables[0]['columns']
        out['rows'] = merged_tables[0]['rows']
        out['total_rows'] = len(merged_tables[0]['rows'])
    return out


def _merge_keyword_ranking(sheet, primary, secondary):
    columns = primary.get('columns') or []
    if 'Keywords' not in columns:
        return None
    attr_cols = [c for c in ('Avg. Volume', 'Landing Pages', 'Base Ranking') if c in columns]
    change_col = next((c for c in columns if _is_change_col(c)), None)
    fixed = {'Sr No', 'Keywords', *attr_cols}
    if change_col:
        fixed.add(change_col)
    period_cols = [c for c in columns if c not in fixed]
    rows = _merge_keyword_rank(
        columns, primary.get('rows', []), secondary.get('rows', []),
        'Keywords', period_cols, attr_cols, change_col,
        'monthly' if getattr(sheet, 'schedule', '') == 'monthly' else 'weekly',
    )
    out = dict(primary)
    out['rows'] = rows
    out['total_rows'] = len(rows)
    # recompute bracket overview from merged ranks (avoids double-counting overlaps)
    if primary.get('overview') and period_cols:
        out['overview'] = _recompute_kw_overview(primary['overview'], rows, period_cols, change_col)
    return out


def _recompute_kw_overview(template_overview, merged_rows, period_cols, change_col):
    buckets = ['Top 5', 'Top 6-10', 'Top 11-20', 'Top 21-30', 'Top 31-50', 'Above 50']
    label_key = next((k for k in (template_overview[0].keys()) if 'ranking' in k.lower()), None) \
        if template_overview else None
    if not label_key:
        return template_overview
    counts = {b: {c: 0 for c in period_cols} for b in buckets}
    for r in merged_rows:
        for c in period_cols:
            b = _bucket_of(_rank_val(r.get(c)))
            if b:
                counts[b][c] += 1
    new_overview = []
    for b in buckets:
        row = {label_key: b}
        for c in period_cols:
            row[c] = counts[b][c]
        if change_col and len(period_cols) >= 2:
            row[change_col] = counts[b][period_cols[-1]] - counts[b][period_cols[-2]]
        new_overview.append(row)
    total = {label_key: 'Total keywords'}
    for c in period_cols:
        total[c] = sum(counts[b][c] for b in buckets)
    if change_col and len(period_cols) >= 2:
        total[change_col] = total[period_cols[-1]] - total[period_cols[-2]]
    new_overview.append(total)
    return new_overview


def _merge_keyword_summary(primary, secondary):
    p_tables = primary.get('tables') or []
    s_tables = secondary.get('tables') or []
    if not p_tables or len(p_tables) < 1:
        return None
    s_by_title = {t.get('title'): t for t in s_tables}
    main = p_tables[0]
    s_main = s_by_title.get(main.get('title'), {'rows': []})
    cols = main.get('columns', [])
    dim_col = 'Primary Keywords' if 'Primary Keywords' in cols else (
        'Keywords' if 'Keywords' in cols else None)
    if not dim_col:
        return None
    attr_cols = [c for c in ('Category', 'Search Volume - USA', 'Intent',
                             'New Ranking URL') if c in cols]
    change_col = next((c for c in cols if _is_change_col(c)), None)
    fixed = {'Sr No', dim_col, *attr_cols}
    if change_col:
        fixed.add(change_col)
    period_cols = [c for c in cols if c not in fixed]
    merged_main_rows = _merge_keyword_rank(
        cols, main.get('rows', []), s_main.get('rows', []),
        dim_col, period_cols, attr_cols, change_col, 'summary',
    )
    merged_tables = [{'title': main.get('title'), 'columns': cols, 'rows': merged_main_rows}]
    # Overview / Overview (Search Volumes): recompute from merged main rows
    for ov in p_tables[1:]:
        merged_tables.append(_recompute_summary_overview(ov, merged_main_rows, period_cols))
    out = dict(primary)
    out['tables'] = merged_tables
    out['columns'] = cols
    out['rows'] = merged_main_rows
    out['total_rows'] = len(merged_main_rows)
    return out


def _recompute_summary_overview(ov, merged_main_rows, period_cols):
    cols = ov.get('columns', [])
    title = ov.get('title', '')
    is_volume = 'Volume' in title
    label_key = cols[0] if cols else 'Overview'
    ov_periods = [c for c in cols[1:] if not _is_change_col(c)]
    change_col = next((c for c in cols if _is_change_col(c)), None)
    buckets = ['Top 5', 'Top 6-10', 'Top 11-20', 'Top 21-30', 'Top 31-50', 'Above 50']
    # map overview period columns to main-table period columns positionally
    pmap = dict(zip(ov_periods, period_cols[-len(ov_periods):])) if period_cols else {}
    agg = {b: {c: 0 for c in ov_periods} for b in buckets}
    for r in merged_main_rows:
        vol = _num(r.get('Search Volume - USA')) or 0
        for oc in ov_periods:
            mc = pmap.get(oc)
            if not mc:
                continue
            b = _bucket_of(_rank_val(r.get(mc)))
            if b:
                agg[b][oc] += (vol if is_volume else 1)
    rows = []
    for b in buckets:
        row = {label_key: b}
        for oc in ov_periods:
            row[oc] = int(agg[b][oc])
        if change_col and len(ov_periods) >= 2:
            row[change_col] = int(agg[b][ov_periods[-1]] - agg[b][ov_periods[-2]])
        rows.append(row)
    total = {label_key: 'Total Keywords'}
    for oc in ov_periods:
        total[oc] = int(sum(agg[b][oc] for b in buckets))
    if change_col and len(ov_periods) >= 2:
        total[change_col] = int(total[ov_periods[-1]] - total[ov_periods[-2]])
    rows.append(total)
    return {'title': title, 'columns': cols, 'rows': rows}
