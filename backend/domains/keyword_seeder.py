"""Generate a brand's starting keyword set.

The old onboarding did this inline, which is most of why adding a domain took a
minute. The new onboarding creates the brand from a site read alone and is
instant — but it created no keywords at all, and three things depend on them:

  * Topics group Keyword rows, so the Topics page stayed empty forever.
  * SEO rankings track Keyword rows, so nothing was ever ranked.
  * Topic -> TopicKeyword -> Keyword -> PromptKeyword -> Prompt is how a topic
    reaches the prompts under it, which is what fills a topic card.

So the work is not skipped, it is moved off the request: onboarding returns as
soon as the brand exists and this runs behind it.

It lives in the backend rather than the engine because the backend owns the
Keyword model. The engine's shared_models.Keyword is a slim mirror — no
volume_level, intent, entity, topic or cluster_id — so a seeder written there
could not store what the generator produces.

The prompt is the old onboarding's, structurally unchanged: it is the one that
produced the keyword sets currently in production ("boutique hotel room rates
India"), and those group into topics cleanly. Only the brand context is richer,
because the site read means what the brand sells is known rather than guessed
from a niche list.
"""
import json
import logging
import re
import threading

from django.conf import settings
from django.db import close_old_connections

logger = logging.getLogger(__name__)

DEFAULT_KEYWORD_COUNT = 50


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

    Accepts the documented {"keywords": [...]} object or a bare array, because a
    reasoning model occasionally answers with the array alone.
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

    Never raises: a brand with no keywords is recoverable — they can be
    generated again — while a failed domain creation is not.
    """
    from keywords.models import Keyword, SecondaryKeyword
    from .views import get_openai_client

    existing = set(
        k.lower() for k in Keyword.objects.filter(domain=domain).values_list('keyword', flat=True)
    )
    if existing:
        logger.info(f"[KeywordSeed] domain {domain.id} already has {len(existing)} keywords, skipping")
        return 0

    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=getattr(settings, "OPENROUTER_INTERNAL_MODEL", "openai/gpt-5-mini"),
            messages=[
                {"role": "system", "content": "You are an expert SEO keyword researcher. Always respond with valid JSON only."},
                {"role": "user", "content": _build_prompt(domain, int(count))},
            ],
            temperature=0.7,
            # The internal model reasons before answering out of the same budget,
            # so 50 keywords of JSON needs headroom or the reply comes back
            # truncated — or empty with finish_reason=length.
            max_tokens=12000,
            extra_body={"reasoning": {"effort": "low"}},
        )
        reply = (response.choices[0].message.content or '') if response.choices else ''
    except Exception as exc:
        logger.error(f"[KeywordSeed] model call failed for domain {domain.id}: {exc}")
        return 0

    keyword_rows, secondary_rows, seen = [], [], set()
    for item in _keywords_from(reply):
        if not isinstance(item, dict):
            continue
        text = str(item.get('keyword') or '').strip()[:255]
        key = text.lower()
        if not text or key in seen or key in existing:
            continue
        seen.add(key)
        shared = dict(
            keyword=text,
            volume_level=str(item.get('volume_level') or 'medium')[:20],
            intent=str(item.get('intent') or 'informational')[:50],
            entity=str(item.get('entity') or '')[:255],
            attribute=str(item.get('attribute') or '')[:255],
            variable=str(item.get('variable') or '')[:255],
            source='ai-generated',
            topic=str(item.get('topic') or '')[:255],
            cluster_id=str(item.get('cluster_id') or '')[:100],
        )
        # Both tables, as the old onboarding did: Keyword is what the product
        # reads, SecondaryKeyword is kept for anything still reading it.
        keyword_rows.append(Keyword(
            domain=domain,
            # Prompts come from the generation wizard now, so these must not
            # re-trigger the old keyword -> prompt pipeline.
            auto_generate_prompts=False,
            **shared,
        ))
        secondary_rows.append(SecondaryKeyword(domain=domain, **shared))

    if not keyword_rows:
        logger.error(f"[KeywordSeed] domain {domain.id}: model returned nothing usable")
        return 0

    Keyword.objects.bulk_create(keyword_rows, ignore_conflicts=True)
    SecondaryKeyword.objects.bulk_create(secondary_rows, ignore_conflicts=True)
    logger.info(f"[KeywordSeed] domain {domain.id}: created {len(keyword_rows)} keywords")
    return len(keyword_rows)


def seed_keywords_in_background(domain_id, count=DEFAULT_KEYWORD_COUNT):
    """Run the seeder off the request thread, then queue topic grouping.

    A thread rather than a task queue because the backend has no Celery worker —
    only the engine does, and the engine cannot write these columns. The job is
    one model call, and losing it to a restart costs nothing that cannot be
    regenerated.
    """
    def run():
        try:
            from .models import Domain

            domain = Domain.objects.get(id=domain_id)
            created = generate_keywords_for_domain(domain, count=count)
            if not created:
                return

            # Group the new keywords straight away, so a new brand arrives with
            # its Topics page populated rather than an empty card and a button.
            try:
                import requests

                engine_api_url = getattr(settings, 'ENGINE_API_URL', 'http://localhost:8001').rstrip('/')
                requests.post(
                    f"{engine_api_url}/api/topics/generate/",
                    json={'domain_id': int(domain_id)},
                    timeout=10,
                )
            except Exception as exc:
                logger.warning(f"[KeywordSeed] could not queue topic grouping for {domain_id}: {exc}")
        except Exception as exc:
            logger.error(f"[KeywordSeed] background run failed for domain {domain_id}: {exc}")
        finally:
            # A thread gets its own connection; without this it leaks one per run.
            close_old_connections()

    threading.Thread(target=run, name=f'keyword-seed-{domain_id}', daemon=True).start()
