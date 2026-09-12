"""Turn an uploaded spreadsheet of prompts into reviewable candidates.

The upload path deliberately produces the *same* artefacts as AI generation: a
PromptGenerationRun in DONE with PromptCandidate rows hanging off it. That is
what lets the review table, the inline edits, the cluster-to-PromptGroup
promotion in accept_generation_run, and the discard path all work here with no
special casing — an uploaded list and a generated one are indistinguishable by
the time they reach review.

The only real work is therefore parsing and grouping:

  parse   pull the prompt text out of .xlsx/.xls/.csv, whatever shape it is in
  group   assign each prompt a theme and a funnel intent, so uploaded prompts
          cluster into PromptGroups the same way generated ones do

Grouping uses the internal model because the alternative — one group per row, or
one giant group — makes the Prompts page unusable at any real list size. The
model call climbs the shared paid-then-free ladder; if every rung fails the
prompts are grouped by keyword overlap instead (cluster_by_overlap), which is
coarser but still real topics; losing the file is not an option.
"""
import csv
import io
import json
import logging
import re
from typing import Any, Dict, List

from django.conf import settings

# OpenRouter-only argument: api.openai.com rejects `reasoning`. No-op extra_body
# when OPENROUTER_BASE_URL points directly at OpenAI (local dev, bare key).
def _reasoning_extra_body():
    from django.conf import settings as _s
    return {"reasoning": {"effort": "low"}} if 'openrouter' in (getattr(_s, 'OPENROUTER_BASE_URL', '') or '') else {}


logger = logging.getLogger(__name__)

# Guard rails. The cap is about the review table staying usable and the grouping
# call staying affordable, not about the parser.
MAX_PROMPTS = 500
MIN_PROMPT_CHARS = 8
MAX_PROMPT_CHARS = 400
GROUP_BATCH = 40

# Header names worth trusting when picking the column that holds the prompt.
_PROMPT_HEADERS = ('prompt', 'question', 'query', 'search', 'keyword', 'text')

# Intents PromptCandidate accepts. The model is constrained to these so the
# review table's filters and the mix reporting keep working.
_INTENTS = ('discovery', 'comparison', 'evaluation', 'use_case', 'problem', 'brand', 'trust')


class UploadError(Exception):
    """Something about the file itself is wrong and the user can fix it."""


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------

def _clean(value: Any) -> str:
    if value is None:
        return ''
    text = re.sub(r'\s+', ' ', str(value)).strip()
    # Spreadsheets love wrapping text in quotes; strip a single matched pair.
    if len(text) > 1 and text[0] == text[-1] and text[0] in ('"', "'"):
        text = text[1:-1].strip()
    return text


def _is_id_column(name: str) -> bool:
    """`id`, `prompt_id`, `ID` … — a key column, never the text."""
    n = name.strip().lower()
    return n == 'id' or n.endswith('_id') or n.endswith(' id')


def _pick_column(header_row: List[str]) -> int:
    """Index of the column holding prompt text.

    An exact header match wins over a partial one, and id columns never count.
    The old scan returned the first cell that merely *contained* a known word,
    so a sheet headed `prompt_id, variant, prompt` picked column 0 — then, since
    "prompt_id" is not exactly "prompt", kept that row as data. A 50-prompt
    upload came through as one prompt whose text was the word "prompt_id".

    Falls back to the first column: a single-column export with no header is
    the most common shape by far.
    """
    cells = [(c or '').strip().lower() for c in header_row]
    for idx, cell in enumerate(cells):
        if cell in _PROMPT_HEADERS:
            return idx
    for idx, cell in enumerate(cells):
        if not _is_id_column(cell) and any(h in cell for h in _PROMPT_HEADERS):
            return idx
    return 0


def _looks_like_header(row: List[str], col: int) -> bool:
    cell = (row[col] if col < len(row) else '').strip().lower()
    # Exact names, or a name that clearly labels a column ("prompt text",
    # "search query") — but never a real question, which is what a partial
    # match on "question" would otherwise treat as a header and drop.
    if cell in _PROMPT_HEADERS or _is_id_column(cell):
        return True
    words = cell.split()
    return 0 < len(words) <= 3 and any(w in _PROMPT_HEADERS for w in words)


def _rows_from_xlsx(data: bytes) -> List[List[str]]:
    from openpyxl import load_workbook
    try:
        # read_only keeps a large sheet from being loaded whole; data_only takes
        # cached formula results rather than the formula text.
        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception as exc:
        raise UploadError("That file could not be opened as a spreadsheet.") from exc

    rows: List[List[str]] = []
    for sheet in wb.worksheets:
        for raw in sheet.iter_rows(values_only=True):
            rows.append([_clean(c) for c in (raw or ())])
        if rows:
            break   # first non-empty sheet wins; a second sheet is usually notes
    wb.close()
    return rows


def _rows_from_csv(data: bytes) -> List[List[str]]:
    for encoding in ('utf-8-sig', 'utf-8', 'latin-1'):
        try:
            text = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise UploadError("That file's text encoding could not be read.")

    try:
        dialect = csv.Sniffer().sniff(text[:4000], delimiters=',;\t|')
    except csv.Error:
        dialect = csv.excel   # single column, nothing to sniff
    return [[_clean(c) for c in row] for row in csv.reader(io.StringIO(text), dialect)]


def parse_prompts(filename: str, data: bytes) -> List[str]:
    """Extract prompt strings from an uploaded file.

    Order is preserved and duplicates are dropped case-insensitively, so a list
    pasted together from several sources does not create duplicate groups.
    """
    name = (filename or '').lower()
    if name.endswith(('.xlsx', '.xlsm', '.xls')):
        rows = _rows_from_xlsx(data)
    elif name.endswith('.csv'):
        rows = _rows_from_csv(data)
    else:
        raise UploadError("Upload a .csv, .xlsx or .xls file.")

    rows = [r for r in rows if any(c for c in r)]
    if not rows:
        raise UploadError("That file has no rows in it.")

    col = _pick_column(rows[0])
    if _looks_like_header(rows[0], col):
        rows = rows[1:]

    seen, prompts = set(), []
    for row in rows:
        text = row[col] if col < len(row) else ''
        if len(text) < MIN_PROMPT_CHARS:
            continue
        text = text[:MAX_PROMPT_CHARS]
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        prompts.append(text)
        if len(prompts) >= MAX_PROMPTS:
            break

    if not prompts:
        raise UploadError(
            "No prompts found. Put one prompt per row, in the first column or "
            "under a column named 'prompt'."
        )
    return prompts


# --------------------------------------------------------------------------
# Grouping
# --------------------------------------------------------------------------

# Grouping happens in two passes.
#
# One pass could not work: prompts are classified in batches, and a batch has no
# idea what themes the other batches invented, so the same subject came back as
# "Car Loan", "Car Loans" and "Vehicle Finance" and each became its own group.
# Deciding the vocabulary once, up front, is what makes the groups agree.
_THEMES_SYSTEM = (
    "You are organising a brand's tracked search prompts into a small set of "
    "reporting groups.\n\n"
    "Return a SHORT list of broad themes that between them cover every prompt. "
    "Fewer, bigger groups are the goal: a theme covering ten prompts is useful, "
    "a theme covering one is noise. Merge anything related — different questions "
    "about the same product, feature or concern belong to ONE theme.\n\n"
    "Name each theme after the subject in 2-4 words, Title Case. Do not name it "
    "after the question type: 'Home Loan', not 'Home Loan Comparison'.\n\n"
    'Return ONLY a JSON array of strings, at most {max_themes} of them.'
)

_ASSIGN_SYSTEM = (
    "You file search prompts into pre-agreed themes for a brand-monitoring tool.\n\n"
    "theme: choose from the provided list, copied EXACTLY. Pick the closest one "
    "even if the fit is loose — every prompt must land in one of them. Only "
    "invent a theme if a prompt is genuinely about nothing on the list.\n"
    f"intent: exactly one of {', '.join(_INTENTS)}. This is a label on the "
    "prompt, not a grouping key, so it never splits a theme.\n"
    "branded: true only if the prompt names the brand itself.\n\n"
    'Return ONLY a JSON array: [{"i": <index>, "theme": "...", '
    '"intent": "...", "branded": false}]. One object per prompt, no commentary.'
)


def _target_theme_count(n: int) -> int:
    """How many groups a list of n prompts should produce.

    Roughly one theme per six prompts, floored at 2 and capped at 8. The old
    behaviour keyed groups on theme AND intent and let each batch pick its own
    names, which turned 14 prompts into 10 groups — a page of one-prompt cards
    that is harder to read than an ungrouped list.
    """
    return max(2, min(8, round(n / 6) or 1))


def _json_array(text: str) -> List[Dict[str, Any]]:
    if not text:
        return []
    fenced = re.search(r'```(?:json)?\s*(.+?)\s*```', text, re.S)
    if fenced:
        text = fenced.group(1)
    start, end = text.find('['), text.rfind(']')
    if start == -1 or end == -1 or end < start:
        return []
    try:
        parsed = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _client_and_model(domain):
    """Organisation's own OpenRouter key where present, else the platform's."""
    org = getattr(domain, 'organisation', None)
    model = getattr(settings, 'OPENROUTER_INTERNAL_MODEL', 'openai/gpt-5-mini')
    if org is not None:
        try:
            key = org.openrouter_key
            if key:
                from openai import OpenAI
                return OpenAI(
                    api_key=key,
                    base_url=getattr(settings, 'OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1'),
                    timeout=90,
                ), model
        except Exception as exc:
            logger.warning('[Upload] org key unusable, falling back: %s', exc)
    from core.openrouter_client import get_internal_client
    return get_internal_client(timeout=90), model


def _ask(client, model, system: str, payload: Any, *, max_tokens: int) -> str:
    """One completion, returning text ('' on any failure).

    Paid model first, then the shared free fallbacks — the same ladder Analyze
    Site, keyword seeding and content generation already climb. This path used
    to make a single call and give up: one 402 on an empty balance (or a 404 on
    a retired free slug) returned '' and every uploaded prompt landed in one
    catch-all group. That is how a 100-prompt upload became one card with 99
    "variants" in production.
    """
    # Lazy: domains.views pulls in the whole domains app at import time.
    from domains.views import create_with_free_fallback
    try:
        resp = create_with_free_fallback(
            client,
            model=model,
            messages=[
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': json.dumps(payload)},
            ],
            # Reasoning model: max_tokens covers reasoning AND answer, and
            # reasoning is spent first. Budget for both or the reply comes back
            # empty with finish_reason="length". (Dropped automatically on the
            # free attempts, which are not reasoning models.)
            max_tokens=max_tokens,
            temperature=0.1,
            extra_body=_reasoning_extra_body(),
        )
        return (resp.choices[0].message.content or '') if resp.choices else ''
    except Exception as exc:
        logger.error('[Upload] every model failed: %s', exc)
        return ''


def propose_themes(client, model, brand: str, prompts: List[str]) -> List[str]:
    """Agree a small shared vocabulary of themes before assigning anything."""
    limit = _target_theme_count(len(prompts))
    # A long list does not need sending whole to name its themes; the first
    # slice is representative and keeps the call small.
    sample = prompts[:120]
    text = _ask(
        client, model,
        _THEMES_SYSTEM.replace('{max_themes}', str(limit)),
        {'brand': brand, 'prompt_count': len(prompts), 'prompts': sample},
        max_tokens=3000,
    )
    themes = []
    for raw in _json_array(text):
        name = _clean(raw)[:60]
        if name and name.lower() not in {t.lower() for t in themes}:
            themes.append(name)
    return themes[:limit]


# Words that carry no topic. Short, on purpose: over-stripping turns "how to
# open a savings account" into "savings" and merges unrelated questions.
_STOPWORDS = frozenset((
    'a an the and or of to in on for with is are was were be been am i my me we our you your it its '
    'this that these those what which who whom whose how why when where can could should would do does '
    'did will shall may might must have has had get got there here than then also just any some all '
    'best good top vs versus about from by at as into over under up down out off not no yes if so'
).split())


def _tokens(text: str) -> List[str]:
    return [w for w in re.findall(r'[a-z0-9]+', text.lower()) if len(w) > 2 and w not in _STOPWORDS]


def cluster_by_overlap(prompts: List[str]) -> List[Dict[str, Any]]:
    """Group prompts by shared vocabulary when no model is available.

    The last rung of the grouping ladder: every model failed, and the choice is
    between this and one giant "Uploaded Prompts" card. Prompts about the same
    thing share words — "car loan", "forex card", "sip" — so rare-word overlap
    (idf-weighted, so "bank" counts for little and "forex" for a lot) is enough
    to split a real list into readable topics. Cosine similarity against a mean
    centroid, seeded greedily and then refined k-means style, so a big cluster
    does not repel new members the way raw overlap does. On a 100-prompt
    banking upload it recovers the same topics the model finds.

    Themes are named from the words the cluster shares most, in the order they
    appear in the prompts ("Home Loan", not "Loan Home"). Deterministic,
    dependency-free, and always returns one entry per prompt, in order.
    """
    import math
    n = len(prompts)
    if n == 0:
        return []
    toks = [_tokens(p) for p in prompts]
    sets = [set(t) for t in toks]
    df: Dict[str, int] = {}
    for t in sets:
        for w in t:
            df[w] = df.get(w, 0) + 1
    idf = {w: math.log(1 + n / c) for w, c in df.items()}

    def vec(ws):
        v = {w: idf[w] for w in ws}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {w: x / norm for w, x in v.items()}

    def cos(a: Dict[str, float], b: Dict[str, float]) -> float:
        return sum(a[w] * b[w] for w in a.keys() & b.keys())

    def centroid(members):
        acc: Dict[str, float] = {}
        for i in members:
            for w, x in vecs[i].items():
                acc[w] = acc.get(w, 0.0) + x
        norm = math.sqrt(sum(x * x for x in acc.values())) or 1.0
        return {w: x / norm for w, x in acc.items()}

    vecs = [vec(t) for t in sets]
    target = _target_theme_count(n)
    JOIN = 0.30   # cosine below this seeds a new cluster while there is room

    # Greedy seeding: each prompt joins its nearest cluster or starts one.
    clusters: List[List[int]] = []
    cents: List[Dict[str, float]] = []
    for i, v in enumerate(vecs):
        if not v:
            continue
        best, best_s = -1, 0.0
        for k, c in enumerate(cents):
            s_ = cos(v, c)
            if s_ > best_s:
                best, best_s = k, s_
        if best < 0 or (best_s < JOIN and len(clusters) < target):
            clusters.append([i])
            cents.append(dict(v))
        else:
            clusters[best].append(i)
            cents[best] = centroid(clusters[best])

    # Merge the two closest clusters until at the target: a long list must not
    # fan out into a page of one-prompt cards.
    while len(clusters) > target:
        bi, bj, bs = 0, 1, -1.0
        for a in range(len(clusters)):
            for b in range(a + 1, len(clusters)):
                s_ = cos(cents[a], cents[b])
                if s_ > bs:
                    bi, bj, bs = a, b, s_
        clusters[bi] += clusters[bj]
        del clusters[bj], cents[bj]
        cents[bi] = centroid(clusters[bi])

    # Refine: reassign every prompt to its nearest centroid, twice. Greedy
    # order leaves early prompts in clusters that later grew away from them.
    for _ in range(2):
        fresh: List[List[int]] = [[] for _ in clusters]
        for i, v in enumerate(vecs):
            if not v:
                continue
            k = max(range(len(cents)), key=lambda k: cos(v, cents[k]))
            fresh[k].append(i)
        clusters = [m for m in fresh if m]
        cents = [centroid(m) for m in clusters]

    empties = [i for i, v in enumerate(vecs) if not v]
    if empties:
        if not clusters:
            clusters.append([])
        max(clusters, key=len).extend(empties)

    out: List[Dict[str, Any]] = [None] * n   # type: ignore[list-item]
    used: set = set()
    for members in clusters:
        # Score words by how many members carry them, weighted by rarity, then
        # order the top two as they appear in the prompts themselves.
        share: Dict[str, float] = {}
        for i in members:
            for w in sets[i]:
                share[w] = share.get(w, 0.0) + idf[w]
        top = [w for w, _ in sorted(share.items(), key=lambda kv: -kv[1])[:2]]
        if len(top) == 2:
            first_after = sum(1 for i in members if top[0] in toks[i] and top[1] in toks[i]
                              and toks[i].index(top[0]) > toks[i].index(top[1]))
            both = sum(1 for i in members if top[0] in toks[i] and top[1] in toks[i])
            if both and first_after > both / 2:
                top.reverse()
        name = ' '.join(w.capitalize() for w in top) or 'Uploaded Prompts'
        base, k = name, 2
        while name.lower() in used:
            name, k = f'{base} {k}', k + 1
        used.add(name.lower())
        for i in members:
            out[i] = {'text': prompts[i], 'theme': name[:60], 'intent': 'discovery', 'branded': False}
    return out


def group_prompts(domain, prompts: List[str]) -> List[Dict[str, Any]]:
    """Assign a theme and intent to each prompt.

    Always returns one entry per input prompt, in order. Anything the model
    fails to classify falls back to the catch-all group rather than being
    dropped — the user uploaded it, so it has to appear in review.
    """
    fallback = {'theme': 'Uploaded Prompts', 'intent': 'discovery', 'branded': False}
    out: List[Dict[str, Any]] = [dict(fallback, text=p) for p in prompts]

    try:
        client, model = _client_and_model(domain)
    except Exception as exc:
        logger.error('[Upload] no LLM client, grouping by keyword overlap: %s', exc)
        return cluster_by_overlap(prompts)

    brand = (getattr(domain, 'name', '') or '').strip()

    themes = propose_themes(client, model, brand, prompts)
    if not themes:
        # Every model failed (out of credits, retired slugs). Assignment without
        # an agreed list is what once produced a group per prompt, and one giant
        # catch-all card is what users reported as "100 prompts became 1". Word
        # overlap is the honest middle: real topics, no model, no cost.
        logger.warning('[Upload] no themes proposed, grouping by keyword overlap')
        return cluster_by_overlap(prompts)
    logger.info('[Upload] %s theme(s) for %s prompts: %s', len(themes), len(prompts), themes)

    # Match case-insensitively but store the agreed spelling, so "car loan" and
    # "Car Loan" cannot become two groups.
    canonical = {t.lower(): t for t in themes}

    for start in range(0, len(prompts), GROUP_BATCH):
        batch = prompts[start:start + GROUP_BATCH]
        text = _ask(
            client, model, _ASSIGN_SYSTEM,
            {
                'brand': brand,
                'themes': themes,
                'prompts': [{'i': i, 'q': q} for i, q in enumerate(batch)],
            },
            max_tokens=6000,
        )

        for row in _json_array(text):
            try:
                idx = int(row['i'])
            except (KeyError, TypeError, ValueError):
                continue
            if not 0 <= idx < len(batch):
                continue
            raw_theme = _clean(row.get('theme'))[:60]
            theme = canonical.get(raw_theme.lower()) or raw_theme or themes[0]
            intent = str(row.get('intent', '')).strip().lower()
            if intent not in _INTENTS:
                intent = 'discovery'
            out[start + idx] = {
                'text': batch[idx],
                'theme': theme,
                'intent': intent,
                'branded': bool(row.get('branded')),
            }

    return out


def to_candidate_rows(grouped: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Shape grouped prompts into PromptCandidate kwargs.

    cluster_key is what accept_generation_run groups on, so it must be stable
    and lowercased; cluster_title is what the resulting PromptGroup is named.
    """
    rows = []
    for g in grouped:
        theme = g['theme']
        intent = g['intent']
        rows.append({
            'text': g['text'],
            'intent': intent,
            'entity': theme,
            'is_branded': g['branded'],
            # Theme alone. Including the intent split every subject across as
            # many groups as it had question types — "Car Loan" became "Car Loan
            # — Comparison" and "Car Loan — Discovery", one prompt in each.
            # Intent stays on the candidate as a label; it just no longer
            # decides what belongs together.
            'cluster_key': theme.lower(),
            'cluster_title': theme,
            # Uploaded prompts are the user's own choice, so they are not
            # scored. A flat 0.5 keeps accept's "best scoring is primary"
            # ordering deterministic without pretending to a judgement.
            'score_realism': 0.5,
            'score_elicits_brands': 0.5,
            'status': 'pending',
        })
    return rows
