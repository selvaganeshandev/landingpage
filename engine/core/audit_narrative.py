"""Audit Engine brand narrative — not whether the engines name you, but how.

One internal LLM call over the answers that mention the brand: what framing
dominates, which descriptors appear (and how often), which descriptors the
brand would want but never gets, the tone each engine leads with, and how the
rivals are framed by comparison. The prompt gets excerpts around the brand's
first mention rather than whole answers, which keeps it cheap and on topic.

Pure orchestration: no ORM, no settings. The processor passes the answers and
stores the result in grounding['narrative'] so a re-run does not pay twice.
"""
import json
import re
from typing import Any, Dict, List, Optional

MAX_ANSWERS = 12
EXCERPT_CHARS = 900
TONES = ('positive', 'neutral', 'cautionary', 'negative')

_SYSTEM = (
    "You analyse how AI assistants describe a brand. You are given excerpts of AI answers "
    "that mention the brand, plus a short profile of what the brand says about itself. "
    "Return ONLY a JSON object with keys:\n"
    "  dominant_framing   string, 2-5 words, the single most common way the answers characterise the brand\n"
    "  framing_share      integer 0-100, % of answers that use that framing\n"
    "  consistency        integer 0-100, how consistently the answers describe the brand the same way\n"
    "  descriptors_present array of {descriptor: string (2-5 words), share: integer 0-100} — up to 6, most common first\n"
    "  descriptors_missing array of strings — up to 4 things the brand's own profile emphasises that NO answer says\n"
    "  by_engine          array of {platform: string, leads_with: string (2-6 words), tone: one of positive|neutral|cautionary|negative, "
    "matches_profile: one of yes|partial|no}\n"
    "  off_brand          array of {platform: string, claim: string (quote or close paraphrase), why: string} — up to 3 places an answer "
    "contradicts the brand's profile or leads with a limitation\n"
    "  narrative_gap      string, 1-2 sentences comparing how the answers frame the brand versus the rivals they name\n"
    "Base everything on the excerpts. Do not invent claims. No commentary outside the JSON."
)


def excerpt(text: str, brand_name: str, host: str, chars: int = EXCERPT_CHARS) -> str:
    """The window of an answer around the brand's first mention (whole start if none)."""
    if not text:
        return ''
    low = text.lower()
    idx = -1
    for needle in (brand_name or '', (host or '').split('.')[0]):
        needle = needle.strip().lower()
        if needle:
            idx = low.find(needle)
            if idx >= 0:
                break
    if idx < 0:
        return text[:chars]
    start = max(0, idx - chars // 3)
    return text[start:start + chars]


def select_answers(rows: List[Dict[str, Any]], brand_name: str, host: str, limit: int = MAX_ANSWERS) -> List[Dict[str, str]]:
    """Answered rows that mention the brand, spread across engines, as excerpts."""
    mentioned = [r for r in rows if r.get('status', 'ok') == 'ok' and r.get('is_mention') and (r.get('response_text') or '').strip()]
    by_platform: Dict[str, List[Dict[str, Any]]] = {}
    for r in mentioned:
        by_platform.setdefault(r.get('platform') or 'Unknown', []).append(r)
    out: List[Dict[str, str]] = []
    # round-robin so one engine cannot dominate the sample
    while len(out) < limit and any(by_platform.values()):
        for platform in list(by_platform):
            if len(out) >= limit:
                break
            if by_platform[platform]:
                r = by_platform[platform].pop(0)
                out.append({'platform': platform, 'prompt': (r.get('prompt_text') or '')[:200],
                            'excerpt': excerpt(r.get('response_text') or '', brand_name, host)})
            else:
                del by_platform[platform]
    return out


def _clean(data: Dict[str, Any], platforms: List[str]) -> Dict[str, Any]:
    def pct(v):
        try:
            return max(0, min(100, int(round(float(v)))))
        except (TypeError, ValueError):
            return None

    present = []
    for d in data.get('descriptors_present') or []:
        if isinstance(d, dict) and d.get('descriptor'):
            present.append({'descriptor': str(d['descriptor']).strip()[:80], 'share': pct(d.get('share')) or 0})
        elif isinstance(d, str) and d.strip():
            present.append({'descriptor': d.strip()[:80], 'share': 0})
    missing = [str(m).strip()[:80] for m in (data.get('descriptors_missing') or []) if str(m).strip()][:4]
    by_engine = []
    for e in data.get('by_engine') or []:
        if not isinstance(e, dict):
            continue
        tone = str(e.get('tone') or 'neutral').lower()
        by_engine.append({
            'platform': str(e.get('platform') or '')[:40],
            'leads_with': str(e.get('leads_with') or '')[:80],
            'tone': tone if tone in TONES else 'neutral',
            'matches_profile': str(e.get('matches_profile') or 'partial').lower() if str(e.get('matches_profile') or '').lower() in ('yes', 'partial', 'no') else 'partial',
        })
    # keep only engines that actually answered, in the audit's order
    order = {p: i for i, p in enumerate(platforms)}
    by_engine = sorted([e for e in by_engine if e['platform'] in order], key=lambda e: order[e['platform']])
    off_brand = []
    for o in data.get('off_brand') or []:
        if isinstance(o, dict) and o.get('claim'):
            off_brand.append({'platform': str(o.get('platform') or '')[:40], 'claim': str(o['claim']).strip()[:240], 'why': str(o.get('why') or '').strip()[:240]})
    return {
        'available': True,
        'dominant_framing': str(data.get('dominant_framing') or '').strip()[:80],
        'framing_share': pct(data.get('framing_share')),
        'consistency': pct(data.get('consistency')),
        'descriptors_present': present[:6],
        'descriptors_missing': missing,
        'by_engine': by_engine,
        'off_brand': off_brand[:3],
        'narrative_gap': re.sub(r'\s+', ' ', str(data.get('narrative_gap') or '')).strip()[:600],
    }


def build_narrative(chat_json, client, model, *, brand_name: str, host: str, industry: str, profile: Dict[str, Any],
                    rows: List[Dict[str, Any]], competitors: List[str], limit: int = MAX_ANSWERS) -> Dict[str, Any]:
    """Run the narrative call. `chat_json(client, model, system, user, ...)` is injected so this stays testable.

    Returns {'available': False, 'reason': ...} when there is nothing to analyse.
    """
    answers = select_answers(rows, brand_name, host, limit=limit)
    if not answers:
        return {'available': False, 'reason': 'The engines never named the brand, so there is no framing to analyse.'}
    platforms = []
    for a in answers:
        if a['platform'] not in platforms:
            platforms.append(a['platform'])
    user = json.dumps({
        'brand': brand_name, 'website': host, 'industry': industry,
        'brand_profile': {
            'description': (profile or {}).get('description', ''),
            'categories': (profile or {}).get('categories', []),
            'audience': (profile or {}).get('audience', ''),
            'buying_criteria': (profile or {}).get('buying_criteria', []),
        },
        'rivals_named_by_engines': competitors[:8],
        'answers': answers,
    })
    # Reasoning models spend hidden tokens before the JSON; the answer itself is
    # small, so give the ceiling real headroom rather than lose the whole call.
    data = chat_json(client, model, _SYSTEM, user, max_tokens=8000, expect_list=False)
    out = _clean(data if isinstance(data, dict) else {}, platforms)
    out['answers_analysed'] = len(answers)
    out['engines_analysed'] = platforms
    return out
