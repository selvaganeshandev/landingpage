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
one giant group — makes the Prompts page unusable at any real list size. If the
model is unavailable the fallback is a single "Uploaded prompts" cluster, which
is worse but still perfectly usable; losing the file is not an option.
"""
import csv
import io
import json
import logging
import re
from typing import Any, Dict, List

from django.conf import settings

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


def _pick_column(header_row: List[str]) -> int:
    """Index of the column holding prompt text.

    Prefers a header that names itself, then falls back to the first column —
    a single-column export with no header is the most common shape by far.
    """
    for idx, cell in enumerate(header_row):
        if any(h in cell.lower() for h in _PROMPT_HEADERS):
            return idx
    return 0


def _looks_like_header(row: List[str], col: int) -> bool:
    cell = (row[col] if col < len(row) else '').lower()
    return cell in _PROMPT_HEADERS or any(cell == h for h in _PROMPT_HEADERS)


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
    """One completion, returning text ('' on any failure)."""
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': json.dumps(payload)},
            ],
            # Reasoning model: max_tokens covers reasoning AND answer, and
            # reasoning is spent first. Budget for both or the reply comes back
            # empty with finish_reason="length".
            max_tokens=max_tokens,
            temperature=0.1,
            extra_body={'reasoning': {'effort': 'low'}},
        )
        return (resp.choices[0].message.content or '') if resp.choices else ''
    except Exception as exc:
        logger.error('[Upload] model call failed: %s', exc)
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
        logger.error('[Upload] no LLM client, using single group: %s', exc)
        return out

    brand = (getattr(domain, 'name', '') or '').strip()

    themes = propose_themes(client, model, brand, prompts)
    if not themes:
        # Assignment without an agreed list is what produced a group per prompt.
        # One honest catch-all group beats that; the user can regroup by editing.
        logger.warning('[Upload] no themes proposed, filing everything together')
        return out
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
