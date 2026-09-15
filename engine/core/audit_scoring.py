"""Audit Engine scoring — turns per-run evidence into the numbers on the report.

Pure functions over plain dicts. No ORM, no network, no Django settings: the
worker feeds it rows read from `audit_prompt_results` / `audit_keyword_results`
and writes the returned dict straight into `Audit.report` plus the headline
columns. Keeping it side-effect free is what makes it unit-testable without a
database and safe to re-run on the same evidence.

Input row shapes (only these keys are read):

    prompt result: {
        'prompt_index': int, 'prompt_text': str, 'funnel_stage': str,
        'platform': str, 'status': 'ok' | 'failed' | 'rate_limited' | 'skipped',
        'is_mention': bool, 'is_cited': bool, 'position': float | None,
        'sentiment': 'positive' | 'neutral' | 'negative' | '',
        'competitors_mentioned': [str], 'cited_domains': [str],
        'rival_positions': {name: int},   # order each rival is named in, 1 = first (optional)
        'run_index': int,                 # 1..N when a prompt is asked several times (optional)
    }
    keyword result: {
        'keyword': str, 'search_volume': int | None, 'position': int | None,
        'ranking_url': str, 'outranked_by': [str],
    }

The GEO score reuses the platform's visibility-score weights (Placement 35%,
Frequency 25%, Sourcing 25%, Framing 15%) so an audit score and a tracked
domain's score mean the same thing; the bands are the ones the report prints.
"""
import re
from collections import Counter, defaultdict

# ---- score bands -----------------------------------------------------------

GEO_BANDS = [
    # (upper bound inclusive, stage key, label)
    (25, 'absent', 'Absent'),
    (50, 'present', 'Present'),
    (75, 'preferred', 'Preferred'),
    (100, 'default', 'Default'),
]

# Visibility-score weights, identical to the tracked-domain formula.
WEIGHTS = {'placement': 0.35, 'frequency': 0.25, 'sourcing': 0.25, 'framing': 0.15}

# A brand named 1st scores 1.0; each place later loses this much, floor 0.
PLACEMENT_DECAY_PER_RANK = 0.2

FRAMING_VALUE = {'positive': 1.0, 'neutral': 0.7, 'negative': 0.2, '': 0.7}

# An engine "prefers" the brand when it mentions it on more than half its prompts.
PREFERRED_MENTION_RATE = 0.5

# A brand named this deep or later in an answer is "buried" (position gap).
TOP_POSITION = 3

FUNNEL_STAGES = ['top', 'middle', 'bottom']
FUNNEL_LABELS = {'top': 'TOFU', 'middle': 'MOFU', 'bottom': 'BOFU'}

# Anything ranking here or better on Google counts as visible on that keyword.
SEO_TOP_N = 10
SEO_STRIKING_DISTANCE = (11, 20)


def geo_stage_for(score):
    """0-100 -> ('present', 'Present'). Scores outside 0-100 are clamped."""
    s = max(0, min(100, int(round(score or 0))))
    for upper, key, label in GEO_BANDS:
        if s <= upper:
            return key, label
    return GEO_BANDS[-1][1], GEO_BANDS[-1][2]


def normalize_host(value):
    """'https://www.HDFCBank.com/x' -> 'hdfcbank.com'. Empty stays empty."""
    host = (value or '').strip().lower()
    for prefix in ('https://', 'http://'):
        if host.startswith(prefix):
            host = host[len(prefix):]
    host = host.split('/')[0].split('?')[0].split('#')[0]
    # Answers wrap URLs in markdown — `https://x.com`, (https://x.com), "x.com",
    # — and the shared URL regex keeps the closing mark, so strip it here.
    host = host.strip("`'\"*_,;:!)]}>.")
    if host.startswith('www.'):
        host = host[4:]
    return host.strip('.')


# robots of the state: regulators, registries, universities. Their citations are
# real third-party sourcing, but "earn the citations sebi.gov.in holds" is not
# an action anyone can take, so they are skipped when picking a rival to beat.
_INSTITUTION_HOST_RE = re.compile(r'\.(gov|gov\.[a-z]{2}|nic\.in|edu|ac\.[a-z]{2}|edu\.[a-z]{2}|int|mil|org|org\.[a-z]{2})$')


def _institution_host(host):
    return bool(host) and bool(_INSTITUTION_HOST_RE.search(host))


def _same_site(host, brand_host):
    """cited host belongs to the brand, including subdomains."""
    return bool(host) and bool(brand_host) and (host == brand_host or host.endswith('.' + brand_host))


def _ok(rows):
    return [r for r in rows if r.get('status', 'ok') == 'ok']


# ---- component scores ------------------------------------------------------

def frequency_component(rows):
    """Mention rate over completed runs, 0-1."""
    ok = _ok(rows)
    if not ok:
        return 0.0
    return sum(1 for r in ok if r.get('is_mention')) / len(ok)


def placement_component(rows):
    """Average placement where mentioned, mapped so 1st = 1.0. 0 when never mentioned."""
    positions = [
        float(r['position']) for r in _ok(rows)
        if r.get('is_mention') and r.get('position') is not None
    ]
    if not positions:
        return 0.0
    avg = sum(positions) / len(positions)
    return max(0.0, min(1.0, 1.0 - (avg - 1.0) * PLACEMENT_DECAY_PER_RANK))


def sourcing_component(rows):
    """Citation rate over completed runs, 0-1."""
    ok = _ok(rows)
    if not ok:
        return 0.0
    return sum(1 for r in ok if r.get('is_cited')) / len(ok)


def framing_component(rows):
    """How favourably the brand is framed where it is mentioned. Neutral when never mentioned."""
    mentioned = [r for r in _ok(rows) if r.get('is_mention')]
    if not mentioned:
        return 0.0
    return sum(FRAMING_VALUE.get(r.get('sentiment') or '', 0.7) for r in mentioned) / len(mentioned)


def geo_score(rows):
    """Weighted 0-100 score plus its four weighted parts (each already × weight × 100)."""
    parts = {
        'placement': placement_component(rows),
        'frequency': frequency_component(rows),
        'sourcing': sourcing_component(rows),
        'framing': framing_component(rows),
    }
    breakdown = {k: round(v * WEIGHTS[k] * 100, 1) for k, v in parts.items()}
    score = int(round(sum(breakdown.values())))
    return max(0, min(100, score)), breakdown


# ---- aggregations ----------------------------------------------------------

def engine_summary(rows):
    """Per platform: prompts asked, mentioned, cited, avg position, top rival cited."""
    by_platform = defaultdict(list)
    for r in rows:
        by_platform[r.get('platform') or 'Unknown'].append(r)
    out = []
    for platform, prow in sorted(by_platform.items()):
        ok = _ok(prow)
        mentioned = [r for r in ok if r.get('is_mention')]
        positions = [float(r['position']) for r in mentioned if r.get('position') is not None]
        rivals = Counter()
        for r in ok:
            for c in r.get('competitors_mentioned') or []:
                rivals[c] += 1
        out.append({
            'platform': platform,
            'asked': len(prow),
            'answered': len(ok),
            'mentioned': len(mentioned),
            'cited': sum(1 for r in ok if r.get('is_cited')),
            'mention_rate': round(len(mentioned) / len(ok), 3) if ok else 0.0,
            'avg_position': round(sum(positions) / len(positions), 1) if positions else None,
            'top_rival': rivals.most_common(1)[0][0] if rivals else None,
            'top_rival_mentions': rivals.most_common(1)[0][1] if rivals else 0,
            'preferred': bool(ok) and len(mentioned) / len(ok) > PREFERRED_MENTION_RATE,
        })
    return out


def share_of_voice(rows, brand_name):
    """Brand vs every rival named, as percentages of all brand mentions."""
    counts = Counter()
    for r in _ok(rows):
        if r.get('is_mention'):
            counts[brand_name] += 1
        for c in r.get('competitors_mentioned') or []:
            if c and c != brand_name:
                counts[c] += 1
    total = sum(counts.values())
    ranked = [
        {'name': name, 'mentions': n, 'share': round(100 * n / total, 1) if total else 0.0,
         'is_you': name == brand_name}
        for name, n in counts.most_common()
    ]
    if brand_name not in counts:
        ranked.append({'name': brand_name, 'mentions': 0, 'share': 0.0, 'is_you': True})
    brand_share = next((x['share'] for x in ranked if x['is_you']), 0.0)
    return brand_share, ranked


def citation_control(rows, brand_host, competitor_hosts):
    """Who owns the citations: owned / competitor / third-party %, plus top sources."""
    comp = {normalize_host(h) for h in competitor_hosts or [] if h}
    brand_host = normalize_host(brand_host)
    owned = competitor = third = 0
    sources = Counter()
    for r in _ok(rows):
        for raw in r.get('cited_domains') or []:
            host = normalize_host(raw)
            if not host:
                continue
            sources[host] += 1
            if _same_site(host, brand_host):
                owned += 1
            elif any(_same_site(host, c) for c in comp):
                competitor += 1
            else:
                third += 1
    total = owned + competitor + third
    pct = (lambda n: round(100 * n / total, 1) if total else 0.0)
    return {
        'owned': pct(owned),
        'competitor': pct(competitor),
        'third_party': pct(third),
        'total_citations': total,
        'top_sources': [{'host': h, 'count': n} for h, n in sources.most_common(8)],
    }


def _platform_outcome(prows):
    """Collapse one platform's runs of a prompt into one outcome.

    With several runs the majority decides: cited when cited on at least half
    the answered runs, else mentioned when mentioned on at least half, else
    absent; failed only when nothing answered.
    """
    ok = _ok(prows)
    if not ok:
        return 'failed'
    n = len(ok)
    if sum(1 for r in ok if r.get('is_cited')) * 2 >= n:
        return 'cited'
    if sum(1 for r in ok if r.get('is_mention')) * 2 >= n:
        return 'mentioned'
    return 'absent'


def gap_type(prows):
    """Why a prompt is lost, in the report's vocabulary.

    won              named in the top positions on at least one engine
    position_gap     named, but never inside the top TOP_POSITION
    visibility_gap   never named while the engines name rivals
    educational      nobody is named — a definitional answer, not a real gap
    no_data          no engine answered
    """
    ok = _ok(prows)
    if not ok:
        return 'no_data'
    mentioned = [r for r in ok if r.get('is_mention')]
    if mentioned:
        positions = [float(r['position']) for r in mentioned if r.get('position') is not None]
        if positions and min(positions) <= TOP_POSITION:
            return 'won'
        return 'position_gap'
    rivals_named = any((r.get('competitors_mentioned') or r.get('cited_domains')) for r in ok)
    return 'visibility_gap' if rivals_named else 'educational'


def prompt_evidence(rows, brand_host):
    """One line per prompt: per-engine outcome, who was cited instead, and the gap type."""
    by_prompt = defaultdict(list)
    for r in rows:
        by_prompt[r.get('prompt_index', 0)].append(r)
    out = []
    for idx in sorted(by_prompt):
        prow = by_prompt[idx]
        by_platform = defaultdict(list)
        for r in prow:
            by_platform[r.get('platform') or 'Unknown'].append(r)
        engines = {p: _platform_outcome(prs) for p, prs in by_platform.items()}
        instead = Counter()
        rivals = Counter()
        for r in _ok(prow):
            if not r.get('is_cited'):
                for raw in r.get('cited_domains') or []:
                    host = normalize_host(raw)
                    if host and not _same_site(host, normalize_host(brand_host)):
                        instead[host] += 1
            for c in r.get('competitors_mentioned') or []:
                rivals[c] += 1
        positions = [float(r['position']) for r in _ok(prow) if r.get('is_mention') and r.get('position') is not None]
        out.append({
            'prompt_index': idx,
            'prompt_text': prow[0].get('prompt_text', ''),
            'funnel_stage': prow[0].get('funnel_stage', ''),
            'engines': engines,
            'runs': len(prow),
            'best_position': min(positions) if positions else None,
            'top_competitor': rivals.most_common(1)[0][0] if rivals else None,
            'cited_instead': [h for h, _ in instead.most_common(3)],
            'gap_type': gap_type(prow),
        })
    return out


def funnel_matrix(rows):
    """Mention rate per funnel stage × engine — the heatmap — plus per-stage totals."""
    platforms = sorted({r.get('platform') or 'Unknown' for r in rows})
    cells = {}
    by_stage = {}
    for stage in FUNNEL_STAGES:
        srows = [r for r in rows if r.get('funnel_stage') == stage]
        cells[stage] = {}
        for p in platforms:
            prs = _ok([r for r in srows if (r.get('platform') or 'Unknown') == p])
            mentioned = sum(1 for r in prs if r.get('is_mention'))
            cited = sum(1 for r in prs if r.get('is_cited'))
            cells[stage][p] = {
                'asked': len(prs), 'mentioned': mentioned, 'cited': cited,
                'rate': round(100 * mentioned / len(prs)) if prs else None,
            }
        ok = _ok(srows)
        mentioned = sum(1 for r in ok if r.get('is_mention'))
        by_stage[stage] = {
            'label': FUNNEL_LABELS[stage],
            'prompts': len({r.get('prompt_index') for r in srows}),
            'asked': len(ok), 'mentioned': mentioned,
            'rate': round(100 * mentioned / len(ok)) if ok else None,
        }
    return {'stages': FUNNEL_STAGES, 'labels': FUNNEL_LABELS, 'platforms': platforms, 'cells': cells, 'by_stage': by_stage}


def competitor_matrix(rows, brand_name, limit=12):
    """How every named brand shows up across the prompts, brand included.

    prompts_ranked  distinct prompts on which the brand was named
    share           prompts_ranked / prompts asked
    avg_position    order of mention where recorded (1 = named first)
    stages          share of prompts per funnel stage where the brand was named
    """
    prompts_all = {r.get('prompt_index') for r in rows}
    stage_of = {r.get('prompt_index'): r.get('funnel_stage') for r in rows}
    stage_totals = Counter(stage_of.values())
    named = defaultdict(set)          # name -> prompt indexes
    positions = defaultdict(list)     # name -> positions
    mentions = Counter()
    for r in _ok(rows):
        idx = r.get('prompt_index')
        if r.get('is_mention'):
            named[brand_name].add(idx)
            mentions[brand_name] += 1
            if r.get('position') is not None:
                positions[brand_name].append(float(r['position']))
        for c in r.get('competitors_mentioned') or []:
            if c and c != brand_name:
                named[c].add(idx)
                mentions[c] += 1
        for c, pos in (r.get('rival_positions') or {}).items():
            if c and c != brand_name and pos:
                positions[c].append(float(pos))
    total = len(prompts_all) or 1
    out = []
    for name, idxs in named.items():
        stages = {}
        for s in FUNNEL_STAGES:
            n = sum(1 for i in idxs if stage_of.get(i) == s)
            stages[s] = {'ranked': n, 'of': stage_totals.get(s, 0), 'share': round(100 * n / stage_totals[s]) if stage_totals.get(s) else None}
        out.append({
            'name': name,
            'is_you': name == brand_name,
            'prompts_ranked': len(idxs),
            'prompts_total': len(prompts_all),
            'share': round(100 * len(idxs) / total),
            'mentions': mentions[name],
            'avg_position': round(sum(positions[name]) / len(positions[name]), 1) if positions[name] else None,
            'stages': stages,
        })
    out.sort(key=lambda x: (-x['prompts_ranked'], x['avg_position'] if x['avg_position'] is not None else 99, x['name']))
    if brand_name not in named:
        out.append({'name': brand_name, 'is_you': True, 'prompts_ranked': 0, 'prompts_total': len(prompts_all), 'share': 0,
                    'mentions': 0, 'avg_position': None,
                    'stages': {s: {'ranked': 0, 'of': stage_totals.get(s, 0), 'share': 0 if stage_totals.get(s) else None} for s in FUNNEL_STAGES}})
    rivals = [x for x in out if not x['is_you']]
    callouts = []
    if rivals:
        bofu = max(rivals, key=lambda x: (x['stages']['bottom']['share'] or 0, x['prompts_ranked']))
        if (bofu['stages']['bottom']['share'] or 0) >= 50:
            callouts.append({'name': bofu['name'], 'title': f"{bofu['name']} — the BOFU default",
                             'text': f"named on {bofu['stages']['bottom']['ranked']} of {bofu['stages']['bottom']['of']} decision-stage prompts — the most common answer when buyers are ready to choose."})
        tofu = max(rivals, key=lambda x: (x['stages']['top']['share'] or 0, x['prompts_ranked']))
        if (tofu['stages']['top']['share'] or 0) >= 50 and tofu['name'] != bofu['name']:
            callouts.append({'name': tofu['name'], 'title': f"{tofu['name']} — owns TOFU mindshare",
                             'text': f"named on {tofu['stages']['top']['ranked']} of {tofu['stages']['top']['of']} awareness-stage prompts — the highest of any brand at that stage."})
        placed = [x for x in rivals if x['avg_position'] is not None and x['prompts_ranked'] >= 2]
        if placed:
            best = min(placed, key=lambda x: x['avg_position'])
            callouts.append({'name': best['name'], 'title': f"{best['name']} — best citation order",
                             'text': f"average position {best['avg_position']} on {best['prompts_ranked']} prompts — the strongest of any tracked brand."})
    return {'rows': out[:limit], 'callouts': callouts[:3]}


# ---- SEO half ----------------------------------------------------------------

def seo_summary(keyword_rows):
    """Top-10 count, striking distance, and a 0-100 visibility index.

    Visibility index = volume-weighted share of keywords in the top 10, with a
    linear position credit (pos 1 = full, pos 10 = 10%). Null volumes count as 1
    so a keyword set without volume data still produces a number.
    """
    rows = list(keyword_rows or [])
    if not rows:
        return {'keywords_total': 0, 'top10': 0, 'striking_distance': 0, 'visibility': None, 'top_keywords': []}
    lo, hi = SEO_STRIKING_DISTANCE
    top10 = sum(1 for r in rows if r.get('position') and r['position'] <= SEO_TOP_N)
    striking = sum(1 for r in rows if r.get('position') and lo <= r['position'] <= hi)
    weighted = total_weight = 0.0
    for r in rows:
        w = float(r.get('search_volume') or 1)
        total_weight += w
        pos = r.get('position')
        if pos and pos <= SEO_TOP_N:
            weighted += w * (SEO_TOP_N + 1 - pos) / SEO_TOP_N
    visibility = round(100 * weighted / total_weight, 1) if total_weight else 0.0
    top_keywords = sorted(rows, key=lambda r: -(r.get('search_volume') or 0))[:6]
    return {
        'keywords_total': len(rows),
        'top10': top10,
        'striking_distance': striking,
        'visibility': visibility,
        'top_keywords': [
            {
                'keyword': r.get('keyword', ''),
                'search_volume': r.get('search_volume'),
                'position': r.get('position'),
                'ranking_url': r.get('ranking_url', ''),
                'outranked_by': list(r.get('outranked_by') or [])[:3],
                'geo_engines_mentioning': r.get('geo_engines_mentioning'),
            }
            for r in top_keywords
        ],
    }


# ---- Findable / Cited / Chosen measures ---------------------------------------

def _measure(key, pillar, label, value, score, target, evidence=''):
    return {
        'key': key, 'pillar': pillar, 'label': label, 'value': value,
        'score': None if score is None else int(round(max(0, min(100, score)))),
        'target': target, 'evidence': evidence,
        'status': None if score is None else ('pass' if score >= target else 'fail'),
    }


def measures(rows, brand_name, brand_host, competitor_hosts, seo=None, crawl=None):
    """The twelve measures under Findable / Cited / Chosen.

    Findable measures need crawl data the SEO stage produces; when `crawl` is
    absent they are returned with score None ("not measured") rather than
    guessed, and the pillar averages only what was measured.
    """
    crawl = crawl or {}
    summary = engine_summary(rows)
    ctrl = citation_control(rows, brand_host, competitor_hosts)
    ok = _ok(rows)
    mentioned = [r for r in ok if r.get('is_mention')]
    mention_rate = frequency_component(rows)
    positions = [float(r['position']) for r in mentioned if r.get('position') is not None]
    avg_pos = (sum(positions) / len(positions)) if positions else None
    negative = sum(1 for r in mentioned if r.get('sentiment') == 'negative')
    negative_rate = (negative / len(mentioned)) if mentioned else 0.0
    engines_pref = sum(1 for e in summary if e['preferred'])
    engines_total = len(summary)
    sov_share, _ = share_of_voice(rows, brand_name)

    def crawl_measure(key, label, target):
        v = crawl.get(key)
        if v is None:
            return _measure(key, 'findable', label, None, None, target, 'not measured')
        return _measure(key, 'findable', label, v.get('value'), v.get('score'), target, v.get('evidence', ''))

    out = [
        # Findable — can the engines reach and read you (crawl stage)
        crawl_measure('bot_access', 'AI crawlability', 80),
        crawl_measure('answer_structure', 'Answer structure', 70),
        crawl_measure('page_freshness', 'Page freshness', 70),
        crawl_measure('authority_signals', 'Authority signals', 70),
        # Cited — are you the source the engines use
        _measure('owned_citation_share', 'cited', 'Owned citation share',
                 f"{ctrl['owned']}%", ctrl['owned'] * 4, 70,
                 f"{ctrl['owned']}% of {ctrl['total_citations']} citations point at {brand_host}"),
        _measure('competitor_citation_share', 'cited', 'Competitor citation share',
                 f"{ctrl['competitor']}%", 100 - ctrl['competitor'] * 3, 70,
                 f"rivals hold {ctrl['competitor']}% of citations"),
        _measure('citation_rate', 'cited', 'Citation rate',
                 f"{round(100 * sourcing_component(rows))}%", sourcing_component(rows) * 200, 70,
                 f"cited on {sum(1 for r in ok if r.get('is_cited'))} of {len(ok)} answers"),
        _measure('third_party_reliance', 'cited', 'Third-party reliance',
                 f"{ctrl['third_party']}%", 100 - ctrl['third_party'] * 0.8, 60,
                 'share of citations that are neither yours nor a rival\'s'),
        # Chosen — are you the answer the engines give
        _measure('mention_rate', 'chosen', 'Mention rate',
                 f"{round(100 * mention_rate)}% of runs", mention_rate * 100, 80,
                 f"named in {len(mentioned)} of {len(ok)} answers"),
        _measure('placement', 'chosen', 'Placement',
                 f"avg {round(avg_pos, 1)}" if avg_pos else 'never named',
                 placement_component(rows) * 100, 80,
                 'order in which you are named among brands'),
        _measure('engine_coverage', 'chosen', 'Engine coverage',
                 f"{engines_pref} of {engines_total}",
                 (100 * engines_pref / engines_total) if engines_total else 0, 80,
                 f"engines naming you on more than half their prompts"),
        _measure('negative_sentiment', 'chosen', 'Negative sentiment',
                 f"{round(100 * negative_rate)}%", 100 - negative_rate * 300, 80,
                 f"{negative} of {len(mentioned)} mentions are negative"),
    ]
    # Share of voice rides on Chosen too; it is a headline number, so it is
    # reported as its own measure only when there is anyone to compare against.
    out.append(_measure('share_of_voice', 'chosen', 'Share of voice',
                        f"{sov_share}%", sov_share * 2, 80,
                        'your share of every brand mention across all answers'))
    return out


def pillar_scores(measure_list):
    """Mean of the measured scores per pillar; None for a pillar with nothing measured."""
    buckets = defaultdict(list)
    for m in measure_list:
        if m['score'] is not None:
            buckets[m['pillar']].append(m['score'])
    return {
        p: (int(round(sum(v) / len(v))) if v else None)
        for p, v in ((p, buckets.get(p, [])) for p in ('findable', 'cited', 'chosen'))
    }


# ---- quick wins ------------------------------------------------------------------

def quick_wins(rows, evidence, ctrl, seo, measure_list):
    """Up to three actions ordered by projected lift. Heuristic, evidence-backed.

    Every win names the evidence that produced it; nothing is suggested unless
    the data shows the gap (an audit with a 100% mention rate must not be told
    to "publish pages for prompts where no engine names you").
    """
    wins = []

    # 1. A rival's site is cited where you are absent/uncited on several prompts.
    rival_gap = Counter()
    for p in evidence:
        for host in p['cited_instead']:
            if not _institution_host(host):
                rival_gap[host] += 1
    if rival_gap:
        host, n = rival_gap.most_common(1)[0]
        wins.append({
            'title': f"Earn the citations {host} holds on {n} of your prompt{'s' if n != 1 else ''}",
            'why': f"Engines cite {host} on {n} prompt{'s' if n != 1 else ''} where you are mentioned but not cited, or absent.",
            # One prompt you can name is worth more than a vague engine gap;
            # scales with how many prompts the rival owns.
            'projected_geo_lift': min(8, 2 + n),
            'effort_hours': 6,
        })

    # 2. Engines that never prefer you.
    weak = [e for e in engine_summary(rows) if e['answered'] and not e['preferred']]
    if weak:
        e = min(weak, key=lambda x: x['mention_rate'])
        rival = f" — {e['top_rival']} is named {e['top_rival_mentions']}×" if e['top_rival'] else ''
        wins.append({
            'title': f"Close the {e['platform']} gap",
            'why': f"{e['platform']} names you on {round(100 * e['mention_rate'])}% of prompts{rival}.",
            'projected_geo_lift': 2 + int(round(3 * (1 - e['mention_rate']))),
            'effort_hours': 8,
        })

    # 3. Striking-distance keywords are the cheapest SEO win.
    if seo and seo.get('striking_distance'):
        wins.append({
            'title': f"Push {seo['striking_distance']} keywords from page 2 into the top 10",
            'why': 'Positions 11–20 already rank; a content refresh moves them, not new pages.',
            'projected_geo_lift': 2,
            'effort_hours': 10,
        })

    # 4. Prompts where no engine names you at all.
    absent = [p for p in evidence if p['engines'] and all(v == 'absent' for v in p['engines'].values())]
    if absent:
        wins.append({
            'title': f"Publish answer pages for the {len(absent)} prompt{'s' if len(absent) != 1 else ''} where no engine names you",
            'why': 'Engines cannot recommend what they cannot read; each absent prompt needs a page that answers it.',
            'projected_geo_lift': min(6, 1 + len(absent)),
            'effort_hours': 12,
        })

    # 5. Mentioned but rarely the source: the engines are citing other people's
    #    pages about you.
    if ctrl.get('total_citations') and ctrl.get('owned', 0) < 30:
        others = ctrl.get('competitor', 0) + ctrl.get('third_party', 0)
        wins.append({
            'title': 'Become the page the engines cite',
            'why': (f"Only {ctrl['owned']}% of {ctrl['total_citations']} citations point at your site; "
                    f"{round(others, 1)}% go to rivals and third parties. Comparison tables, pricing "
                    "and FAQ pages are what get cited."),
            'projected_geo_lift': 3,
            'effort_hours': 8,
        })

    wins.sort(key=lambda w: -w['projected_geo_lift'])
    return wins[:3]



# ---- visibility plan ------------------------------------------------------------

# Actions a failing measure implies. lift is GEO points when the measure reaches
# its target; effort in hours; owner is who usually does it.
MEASURE_ACTIONS = {
    'bot_access': ('Allow the AI crawlers in robots.txt', 'Engines cannot cite pages their crawlers are blocked from.', 6, 1, 'dev'),
    'answer_structure': ('Add FAQPage / HowTo schema and question-shaped headings to key pages',
                         'Engines extract and cite answer-shaped content; schema tells them what each block is.', 4, 8, 'dev'),
    'authority_signals': ('Add author bylines and outbound citations to content pages',
                          'Bylines and cited sources are the trust signals engines use before citing a page.', 4, 6, 'content'),
    'page_freshness': ('Refresh the stale pages and publish dateModified', 'Pages older than 12 months lose citations fastest.', 3, 8, 'content'),
    'owned_citation_share': ('Become the page the engines cite: comparison tables, pricing and FAQ pages',
                             'Most citations point at other people\'s pages about you.', 5, 8, 'content'),
    'third_party_reliance': ('Earn citations from the sources the engines already trust',
                             'Third-party pages carry most of the citations on your prompts.', 3, 10, 'outreach'),
    'placement': ('Publish comparison content that names you first', 'You are named, but after the rivals.', 3, 6, 'content'),
    'negative_sentiment': ('Address the negative framing the engines repeat', 'Some answers describe you negatively.', 3, 4, 'content'),
}
BUCKETS = [
    ('now', 'Now', 'Stop the bleeding', 3, 8),      # up to 3 items, each ≤ 8h
    ('next', 'Next', 'Win the biggest answers', 4, 24),
    ('later', 'Later', 'Widen the lead', 6, 10 ** 6),
]
MAX_PROJECTED_LIFT = 30
BUCKET_CONFIDENCE = {'now': 1.0, 'next': 0.75, 'later': 0.5}


def visibility_plan(score, rows, evidence, measure_list, ctrl, seo, quick_win_list, crawl_summary=None):
    """Every gap's action, sequenced Now / Next / Later with the projected score at each step.

    Sources, in priority order: the quick wins (already evidence-gated), failing
    measures, lost prompts, SEO striking distance, crawl findings. Items are
    deduped by key, ranked by lift per hour, then bucketed; the projection is
    today's score plus the cumulative lift, capped.
    """
    items = []
    seen = set()

    def add(key, title, why, lift, hours, owner, source=None):
        if key in seen or lift <= 0:
            return
        seen.add(key)
        items.append({'key': key, 'title': title, 'why': why, 'projected_geo_lift': int(lift),
                      'effort_hours': int(hours), 'owner': owner, 'source': source})

    has_prompt_gaps = any(ev.get('gap_type') in ('visibility_gap', 'position_gap') for ev in evidence)
    for i, w in enumerate(quick_win_list or []):
        # The aggregate "publish answer pages for N prompts" win is replaced by
        # one action per prompt below, so it is not counted twice.
        if has_prompt_gaps and w['title'].startswith('Publish answer pages for'):
            continue
        add(f"win:{w.get('title', i)}", w['title'], w['why'], w.get('projected_geo_lift', 0), w.get('effort_hours', 6), 'content', 'quick_win')

    by_key = {m['key']: m for m in measure_list}
    for key, (title, why, lift, hours, owner) in MEASURE_ACTIONS.items():
        m = by_key.get(key)
        if not m or m.get('status') != 'fail':
            continue
        evidence_text = ' · '.join(str(x) for x in (m.get('value'), m.get('evidence')) if x)
        add(f"measure:{key}", title, f"{why} ({m.get('label')}: {evidence_text}).", lift, hours, owner, key)

    crawl_summary = crawl_summary or {}
    if crawl_summary.get('pages_sampled') and not crawl_summary.get('sitemap_present'):
        add('crawl:sitemap', 'Publish a sitemap.xml and reference it from robots.txt', 'Crawlers found no sitemap, so new pages are discovered late.', 2, 1, 'dev', 'crawl')
    # Technical-SEO issues from the crawl's technical layer: critical ones are
    # cheap, fast dev fixes; warnings only when there is room in the plan.
    for issue in (crawl_summary.get('technical_issues') or []):
        if issue.get('severity') == 'critical':
            add(f"tech:{issue['key']}", issue.get('action') or issue.get('label', ''),
                f"{issue.get('label', '')}: {issue.get('count', 0)} of {issue.get('of', 0)} sampled pages. {issue.get('fix', '')}", 2, 3, 'dev', 'crawl')
    for issue in (crawl_summary.get('technical_issues') or []):
        if issue.get('severity') == 'warning' and issue.get('count', 0) >= max(2, (crawl_summary.get('pages_sampled') or 0) // 2):
            add(f"tech:{issue['key']}", issue.get('action') or issue.get('label', ''),
                f"{issue.get('label', '')}: {issue.get('count', 0)} of {issue.get('of', 0)} sampled pages. {issue.get('fix', '')}", 1, 4, 'dev', 'crawl')

    for ev in evidence:
        gap = ev.get('gap_type')
        if gap == 'visibility_gap':
            rival = f" ({ev['top_competitor']} is named instead)" if ev.get('top_competitor') else ''
            add(f"prompt:{ev['prompt_index']}", f"Publish an answer page for “{ev.get('prompt_text', '')}”",
                f"No engine names you on this {ev.get('funnel_stage') or ''} prompt{rival}.", 2, 6, 'content', f"prompt:{ev['prompt_index']}")
        elif gap == 'position_gap':
            add(f"prompt:{ev['prompt_index']}", f"Move up the order on “{ev.get('prompt_text', '')}”",
                f"You are named, but never in the top {TOP_POSITION}.", 2, 4, 'content', f"prompt:{ev['prompt_index']}")

    if seo and seo.get('striking_distance'):
        add('seo:striking', f"Push {seo['striking_distance']} keywords from page 2 into the top 10",
            'Positions 11–20 already rank; a refresh moves them, not new pages.', 2, 10, 'seo', 'seo')

    items.sort(key=lambda x: (-(x['projected_geo_lift'] / max(1, x['effort_hours'])), -x['projected_geo_lift']))

    buckets = []
    remaining = list(items)
    running = int(score or 0)
    total_lift = 0
    for key, label, subtitle, cap, max_hours in BUCKETS:
        chosen = []
        for it in list(remaining):
            if len(chosen) >= cap:
                break
            if it['effort_hours'] <= max_hours:
                chosen.append(it)
                remaining.remove(it)
        # Item lifts are nominal. Two corrections keep the projection honest:
        # headroom — the closer to 100, the less any action can add — and
        # diminishing returns for the later, less certain buckets.
        nominal = sum(it['projected_geo_lift'] for it in chosen)
        headroom = min(1.0, 1.5 * (100 - running) / 100)
        lift = int(round(nominal * headroom * BUCKET_CONFIDENCE[key]))
        allowed = max(0, MAX_PROJECTED_LIFT - total_lift)
        lift = min(lift, allowed)
        total_lift += lift
        start, running = running, min(100, running + lift)
        buckets.append({'key': key, 'label': label, 'subtitle': subtitle, 'from': start, 'to': running,
                        'lift': running - start, 'hours': sum(it['effort_hours'] for it in chosen), 'items': chosen})

    stale = (crawl_summary.get('stale_pages') or 0)
    drift = min(6, 1 + stale + (2 if (ctrl or {}).get('owned', 100) < 20 else 0))
    return {
        'today': int(score or 0),
        'projected': running,
        'status_quo': max(0, int(score or 0) - drift),
        'status_quo_note': f"drifts to {max(0, int(score or 0) - drift)} as cited pages age" if drift else '',
        'buckets': buckets,
        'unscheduled': len(remaining),
    }


# ---- entry point ---------------------------------------------------------------------

def score_audit(prompt_rows, brand_name, brand_host, competitor_hosts=(), keyword_rows=None, crawl=None, crawl_summary=None):
    """Everything the report needs, in one dict. Also returns the headline columns.

    Returns {'headline': {...columns on Audit...}, 'report': {...Audit.report...}}.
    """
    rows = list(prompt_rows or [])
    score, breakdown = geo_score(rows)
    stage_key, stage_label = geo_stage_for(score)
    summary = engine_summary(rows)
    sov_share, sov_ranked = share_of_voice(rows, brand_name)
    ctrl = citation_control(rows, brand_host, competitor_hosts)
    evidence = prompt_evidence(rows, brand_host)
    funnel = funnel_matrix(rows)
    competitors = competitor_matrix(rows, brand_name)
    seo = seo_summary(keyword_rows) if keyword_rows is not None else None
    ms = measures(rows, brand_name, brand_host, competitor_hosts, seo=seo, crawl=crawl)
    pillars = pillar_scores(ms)
    ok = _ok(rows)

    headline = {
        'geo_score': score,
        'geo_stage': stage_key,
        'appearances': sum(1 for r in ok if r.get('is_mention')),
        'cited_runs': sum(1 for r in ok if r.get('is_cited')),
        'total_runs': len(ok),
        'engines_preferred': sum(1 for e in summary if e['preferred']),
        'engines_total': len(summary),
        'share_of_voice': sov_share,
        'seo_visibility': seo['visibility'] if seo else None,
        'keywords_top10': seo['top10'] if seo else 0,
        'keywords_total': seo['keywords_total'] if seo else 0,
    }
    report = {
        'version': 2,
        'geo': {
            'score': score,
            'stage': stage_key,
            'stage_label': stage_label,
            'breakdown': breakdown,
            'weights': WEIGHTS,
            'engines': summary,
            'evidence': evidence,
            'funnel': funnel,
            'competitors': competitors,
            'gap_counts': dict(Counter(e['gap_type'] for e in evidence)),
            'runs_per_prompt': max((int(r.get('run_index') or 1) for r in rows), default=1),
            'share_of_voice': sov_ranked,
            'citation_control': ctrl,
            'runs_total': len(rows),
            'runs_answered': len(ok),
        },
        'seo': seo,
        'measures': ms,
        'pillars': pillars,
        'quick_wins': quick_wins(rows, evidence, ctrl, seo, ms),
    }
    report['plan'] = visibility_plan(score, rows, evidence, ms, ctrl, seo, report['quick_wins'], crawl_summary=crawl_summary)
    return {'headline': headline, 'report': report}
