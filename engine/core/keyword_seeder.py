"""Generate a brand's starting keyword set.

The old onboarding produced ~50 search keywords inline, which is most of why
adding a domain took a minute: the user waited on an LLM call for data they
would not look at for another hour. The new onboarding creates the brand from a
site read alone and is instant — but it created no keywords at all, and three
things quietly depend on them:

  * Topics group Keyword rows, so the Topics page stayed empty forever.
  * SEO rankings track Keyword rows, so nothing was ever ranked.
  * Prompt/keyword links are what let a topic reach the prompts under it, which
    is what fills a topic card's citations and competitors.

So the work is not skipped, it is moved: onboarding returns immediately and this
runs on the engine a moment later.

Keywords are what a *searcher* types — short noun phrases with intent, not
questions. That distinction matters because prompts are the question form, and
mixing the two produced topic chips that read as whole sentences.
"""
import json
import logging
import re

from django.conf import settings

logger = logging.getLogger(__name__)

DEFAULT_KEYWORD_COUNT = 50

# The old onboarding's prompt, kept verbatim in structure because it is the one
# that produced the keyword sets currently in production — "boutique hotel room
# rates India", "gateway hotels goa" — and those group into topics cleanly. Only
# the brand context is richer here: the new onboarding reads the site, so what
# the brand actually sells is known rather than inferred from a niche list.
_SYSTEM = (
    "You are an expert SEO keyword researcher. Always respond with valid JSON only."
)


def _build_prompt(domain, count):
    niches = domain.niches if isinstance(domain.niches, list) else []
    offerings = domain.offering_categories if isinstance(domain.offering_categories, list) else []
    use_cases = domain.use_cases if isinstance(domain.use_cases, list) else []
    niche_text = ", ".join(str(n) for n in niches[:10]) if niches else "general business"

    context = ""
    if domain.short_description:
        context += f"**What they do:** {domain.short_description}\n"
    if domain.target_audience:
        context += f"**Audience:** {domain.target_audience}\n"
    if offerings:
        context += f"**Offerings:** {', '.join(str(o) for o in offerings[:10])}\n"
    if use_cases:
        context += f"**Use cases:** {', '.join(str(u) for u in use_cases[:10])}\n"

    return f"""You are an expert SEO keyword researcher. Generate a comprehensive keyword universe for:

**Website:** {domain.url}
**Brand Name:** {domain.name}
**Country:** {domain.country or 'United States'}
**Industry Niches:** {niche_text}
{context}**Number of Keywords:** EXACTLY {count} unique, relevant keywords

Generate keywords that cover:
- Brand-related queries
- Product/service queries
- Informational queries
- Commercial/transactional queries

Keywords are SEARCH PHRASES, not questions: 2-6 words, the way a person types
into a search box.

For each keyword, provide:
1. **keyword**: The actual keyword phrase
2. **volume_level**: Estimated search volume (very-low, low, medium, high, very-high)
3. **intent**: Search intent type (informational, navigational, transactional, commercial)
4. **entity**: Main subject/noun of the keyword
5. **attribute**: Characteristic being queried (if applicable)
6. **variable**: Modifier/qualifier (if applicable)
7. **source**: Always set to "ai-generated"
8. **topic**: Main topic/category
9. **cluster_id**: Group identifier for related keywords

Return ONLY a valid JSON object with this structure:
{{
  "keywords": [
    {{
      "keyword": "example keyword",
      "volume_level": "medium",
      "intent": "informational",
      "entity": "product",
      "attribute": "price",
      "variable": "cheap",
      "source": "ai-generated",
      "topic": "pricing",
      "cluster_id": "cluster_1"
    }}
  ]
}}"""


def _keywords_from(text):
    """Pull the keyword array out of the reply, tolerating a fence or preamble.

    Accepts either the documented {"keywords": [...]} object or a bare array,
    because a reasoning model occasionally answers with the array alone.
    """
    if not text:
        return []
    fenced = re.search(r'```(?:json)?\s*(.+?)\s*```', text, re.S)
    if fenced:
        text = fenced.group(1)

    for opener, closer in (('{', '}'), ('[', ']')):
        start, end = text.find(opener), text.rfind(closer)
        if start == -1 or end == -1 or end < start:
            continue
        try:
            parsed = json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            rows = parsed.get('keywords')
            if isinstance(rows, list):
                return rows
        elif isinstance(parsed, list):
            return parsed
    return []


def generate_keywords_for_domain(domain, count=DEFAULT_KEYWORD_COUNT):
    """Write a starting keyword set for `domain`. Returns the number created.

    Never raises: a brand with no keywords is recoverable (the Keywords page can
    generate them on demand), a half-created brand is not.
    """
    from shared_models.models import Keyword

    existing = set(
        k.lower() for k in Keyword.objects.filter(domain=domain).values_list('keyword', flat=True)
    )
    if existing:
        logger.info('[KeywordSeed] domain %s already has %s keywords, skipping',
                    domain.id, len(existing))
        return 0

    try:
        from core.openrouter_client import get_internal_client
        client = get_internal_client(timeout=120)
    except Exception as exc:
        logger.error('[KeywordSeed] no client for domain %s: %s', domain.id, exc)
        return 0

    try:
        response = client.chat.completions.create(
            model=getattr(settings, 'OPENROUTER_INTERNAL_MODEL', 'openai/gpt-5-mini'),
            messages=[
                {'role': 'system', 'content': _SYSTEM},
                {'role': 'user', 'content': _build_prompt(domain, int(count))},
            ],
            # Same as the old onboarding: this is generation, not extraction.
            temperature=0.7,
            # The internal model reasons before answering and shares one budget
            # with the answer, so 50 keywords of JSON needs real headroom or the
            # reply comes back truncated — or empty with finish_reason=length.
            max_tokens=12000,
            extra_body={'reasoning': {'effort': 'low'}},
        )
        reply = (response.choices[0].message.content or '') if response.choices else ''
    except Exception as exc:
        logger.error('[KeywordSeed] model call failed for domain %s: %s', domain.id, exc)
        return 0

    rows, seen = [], set()
    for item in _keywords_from(reply):
        if not isinstance(item, dict):
            continue
        text = str(item.get('keyword') or '').strip()[:255]
        key = text.lower()
        if not text or key in seen or key in existing:
            continue
        seen.add(key)
        rows.append(Keyword(
            domain=domain,
            keyword=text,
            volume_level=str(item.get('volume_level') or 'medium')[:20],
            intent=str(item.get('intent') or 'informational')[:50],
            entity=str(item.get('entity') or '')[:255],
            attribute=str(item.get('attribute') or '')[:255],
            variable=str(item.get('variable') or '')[:255],
            topic=str(item.get('topic') or '')[:255],
            cluster_id=str(item.get('cluster_id') or '')[:100],
            source='ai-generated',
            # Prompts come from the generation wizard now, not from keywords, so
            # these must not re-trigger the old keyword->prompt pipeline.
            auto_generate_prompts=False,
        ))

    if not rows:
        logger.error('[KeywordSeed] domain %s: model returned nothing usable', domain.id)
        return 0

    Keyword.objects.bulk_create(rows, ignore_conflicts=True)
    logger.info('[KeywordSeed] domain %s: created %s keywords', domain.id, len(rows))
    return len(rows)
