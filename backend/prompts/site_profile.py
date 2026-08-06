"""Infer a brand profile from the project's own website.

The generation wizard asks for thirteen facts about the brand before it can
write anything. Typing all of them by hand is the slowest part of the flow, and
most of the answers are already stated plainly on the brand's own homepage — so
this reads the site once and proposes them.

Deliberately a *proposal*, not a save. Nothing here writes to Domain: the view
returns the fields and the wizard fills only the inputs the user has left empty,
so a value they typed is never overwritten by a guess. The wizard's normal
submit path (`_persist_brand_facts`) is still what commits anything.

Why synchronous: this is a one-off, user-initiated action behind an explicit
button, and the whole thing lands in ~15s (crawl ~3s, model ~10s). That is worth
one gunicorn thread. It is NOT suitable for anything automatic or bulk — if this
ever needs to run unattended or across many domains, move it onto the engine's
Celery queue rather than raising the timeout here.

The crawler is the misinformation module's WebCrawler, which already carries the
SSRF guard (`is_safe_url`) this needs — the URL comes from user-created project
data, so it cannot be trusted to point somewhere public.
"""
import json
import logging
import re
from typing import Any, Dict, Optional

from django.conf import settings

logger = logging.getLogger(__name__)

# Mirrors views_generation's field lists. Text fields arrive as strings, list
# fields as arrays; the wizard maps them straight onto its own inputs.
TEXT_FIELDS = ('short_description', 'target_audience', 'business_model', 'price_positioning')
LIST_FIELDS = (
    'niches', 'offering_categories', 'regions_served', 'use_cases',
    'buying_criteria', 'differentiators', 'key_competitors',
)

# business_model and price_positioning are rendered as fixed choice chips in the
# wizard, so a free-text answer would arrive and match nothing. Constrain the
# model to the exact slugs the UI offers.
BUSINESS_MODELS = ('b2c_ecommerce', 'd2c_brand', 'b2b_saas', 'local_services', 'marketplace', 'agency_services', 'other')
PRICE_POSITIONS = ('budget', 'mid_market', 'premium', 'mixed')

# Slugs are what the model is constrained to and what the wizard maps onto its
# choice chips. Domain, however, stores whatever the wizard submits — which is
# the chip's own label. Persisting a slug would round-trip as a value no chip
# matches, so it would silently read back as "not set".
BUSINESS_MODEL_LABELS = {
    'b2c_ecommerce': 'B2C ecommerce',
    'd2c_brand': 'D2C brand',
    'b2b_saas': 'B2B SaaS',
    'local_services': 'Local services',
    'marketplace': 'Marketplace',
    'agency_services': 'Agency / services',
    'other': 'Other',
}
PRICE_POSITION_LABELS = {
    'budget': 'Budget',
    'mid_market': 'Mid-market',
    'premium': 'Premium',
    'mixed': 'Mixed',
}


def to_storage(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Convert an inferred payload into the shape Domain stores."""
    stored = dict(fields)
    if 'business_model' in stored:
        stored['business_model'] = BUSINESS_MODEL_LABELS.get(
            stored['business_model'], stored['business_model'])
    if 'price_positioning' in stored:
        stored['price_positioning'] = PRICE_POSITION_LABELS.get(
            stored['price_positioning'], stored['price_positioning'])
    return stored

# Enough of the page to characterise a brand without paying for a whole site.
MAX_SITE_CHARS = 6000

_SYSTEM = (
    "You read a company's website and extract factual brand attributes for a "
    "marketing tool. Return ONLY a JSON object, no prose and no code fence.\n\n"
    "Keys and types:\n"
    '  short_description   string, one sentence, what the company does\n'
    '  target_audience     string, who buys from them\n'
    f'  business_model      string, exactly one of: {", ".join(BUSINESS_MODELS)}\n'
    f'  price_positioning   string, exactly one of: {", ".join(PRICE_POSITIONS)}\n'
    '  offering_categories array of short noun phrases — what they sell\n'
    '  niches              array of specific market segments they serve\n'
    '  regions_served      array of cities/countries/regions, or ["All over"] if global\n'
    '  use_cases           array of problems customers solve with this\n'
    '  buying_criteria     array of what customers compare on (price, speed, ...)\n'
    '  differentiators     array of what this brand claims sets it apart\n'
    '  key_competitors     array of named competing brands, ONLY if the page names them\n\n'
    "Omit any key you cannot support from the page. Do not invent competitors, "
    "regions or prices — an absent key is far better than a confident guess, "
    "because the user sees these as pre-filled answers and may not check them."
)


def _strip_html(html: str) -> str:
    """Crude tag strip. The model only needs prose, not structure."""
    text = re.sub(r'(?is)<(script|style|noscript)\b.*?</\1>', ' ', html)
    text = re.sub(r'(?s)<[^>]+>', ' ', text)
    text = re.sub(r'&nbsp;?', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def _json_from(text: str) -> Dict[str, Any]:
    """Parse the model's reply, tolerating a code fence or a prose preamble."""
    if not text:
        return {}
    fenced = re.search(r'```(?:json)?\s*(.+?)\s*```', text, re.S)
    if fenced:
        text = fenced.group(1)
    start, end = text.find('{'), text.rfind('}')
    if start == -1 or end == -1 or end < start:
        return {}
    try:
        parsed = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _clean(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Keep only known keys with usable values, in the shape the wizard expects.

    Anything unrecognised is dropped rather than passed through: these values
    land directly in form inputs, and a stray key or a dict where a string
    belongs would surface as broken UI.
    """
    out: Dict[str, Any] = {}

    for key in TEXT_FIELDS:
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            out[key] = value.strip()

    for key in LIST_FIELDS:
        value = raw.get(key)
        if isinstance(value, str):
            value = [v.strip() for v in value.split(',')]
        if isinstance(value, list):
            items = [str(v).strip() for v in value if str(v).strip()]
            if items:
                out[key] = items[:12]

    # Drop choice fields the model free-texted; a value the chips cannot render
    # would show as "nothing selected" while claiming to be filled in.
    if out.get('business_model') not in BUSINESS_MODELS:
        out.pop('business_model', None)
    if out.get('price_positioning') not in PRICE_POSITIONS:
        out.pop('price_positioning', None)

    return out


def infer_profile(domain) -> Dict[str, Any]:
    """Crawl `domain.url` and propose wizard fields from what the page says.

    Returns {'fields': {...}, 'error': str|None}. A failure is reported rather
    than raised: the wizard stays perfectly usable by hand, so a dead site or a
    model hiccup should degrade to "fill it in yourself", never to a broken step.
    """
    url = (getattr(domain, 'url', '') or '').strip()
    if not url:
        return {'fields': {}, 'error': 'This project has no website URL.'}
    if not url.startswith(('http://', 'https://')):
        url = f'https://{url}'

    try:
        from misinformation.services.crawler import WebCrawler
        html, status, err = WebCrawler().crawl(url)
    except Exception as exc:
        logger.warning('[SiteProfile] crawl raised for %s: %s', url, exc)
        return {'fields': {}, 'error': 'Could not reach the site.'}

    if not html:
        logger.info('[SiteProfile] no content for %s (status %s): %s', url, status, err)
        return {'fields': {}, 'error': f'Could not read the site (HTTP {status or 0}).'}

    text = _strip_html(html)[:MAX_SITE_CHARS]
    if len(text) < 200:
        return {'fields': {}, 'error': 'The site had too little text to read.'}

    # Prefer the organisation's own OpenRouter key so the spend lands on the
    # account that benefits, matching how generation itself bills.
    client = None
    org = getattr(domain, 'organisation', None)
    if org is not None:
        try:
            key = org.openrouter_key
            if key:
                from openai import OpenAI
                client = OpenAI(
                    api_key=key,
                    base_url=getattr(settings, 'OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1'),
                    timeout=60,
                )
        except Exception as exc:
            logger.warning('[SiteProfile] org key unusable, falling back: %s', exc)

    if client is None:
        try:
            from core.openrouter_client import get_internal_client
            client = get_internal_client(timeout=60)
        except Exception as exc:
            logger.error('[SiteProfile] no OpenRouter client: %s', exc)
            # Reaches the user verbatim (toast / analysis warning), so it names
            # no provider — the transport is never surfaced in the UI.
            return {'fields': {}, 'error': 'No AI API key is configured.'}

    model = getattr(settings, 'OPENROUTER_INTERNAL_MODEL', 'openai/gpt-5-mini')
    user = f"Brand: {getattr(domain, 'name', '') or ''}\nURL: {url}\n\nPage text:\n{text}"

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{'role': 'system', 'content': _SYSTEM}, {'role': 'user', 'content': user}],
            # The default internal model (openai/gpt-5-mini) is a REASONING
            # model: max_tokens caps reasoning + answer together, and reasoning
            # is spent first. At 1200 the whole budget went to reasoning, the
            # reply came back finish_reason="length" with content None, and the
            # feature silently reported "nothing usable on the site" — a total
            # failure that looks exactly like an unhelpful homepage. Budget for
            # both, and keep reasoning short: this is extraction from text that
            # is already in front of the model, not a problem to think through.
            max_tokens=4000,
            temperature=0.2,   # extraction, not invention
            extra_body={'reasoning': {'effort': 'low'}},
        )
        reply = (response.choices[0].message.content or '') if response.choices else ''
        if not reply:
            finish = getattr(response.choices[0], 'finish_reason', '?') if response.choices else '?'
            logger.error('[SiteProfile] empty reply for %s (finish_reason=%s)', url, finish)
    except Exception as exc:
        logger.error('[SiteProfile] model call failed for %s: %s', url, exc)
        return {'fields': {}, 'error': 'Could not read the site right now. Try again.'}

    fields = _clean(_json_from(reply))
    if not fields:
        return {'fields': {}, 'error': 'Nothing usable could be read from the site.'}

    logger.info('[SiteProfile] %s -> %s field(s)', url, len(fields))
    return {'fields': fields, 'error': None}
