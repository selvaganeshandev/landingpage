"""AI prompt generation — the six-stage pipeline behind "Generate with AI".

    ground     read the site and the brand record
    entities   turn that into a vocabulary of things people ask about
    expand     render (entity x intent x modifier) tuples into real questions
    dedup      drop near-identical questions
    score      keep the ones an LLM would answer by naming brands
    assemble   cluster into themed groups and write candidates

Two decisions shape the whole file.

First, *the plan is built in Python, not asked of the model*. If you ask an LLM
for "60% unbranded across seven intents" you get approximately that; if code
builds the tuples, the mix is exact and testable. The model only ever renders a
tuple into natural language.

Second, unbranded questions dominate by default. "Is FNP any good?" tells you
nothing — the model will obviously mention FNP. The commercial signal is in
"best flower delivery in Bangalore", where the LLM *chooses* who to name and a
brand can be invisible without knowing it.
"""
import json
import logging
import re
from typing import Any, Dict, List

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Intent taxonomy. `branded` marks intents that name the brand by definition —
# the planner uses this to honour the requested branded/unbranded ratio.
INTENTS = {
    'discovery':  {'branded': False, 'label': 'Discovery'},
    'comparison': {'branded': False, 'label': 'Comparison'},
    'evaluation': {'branded': False, 'label': 'Evaluation'},
    'use_case':   {'branded': False, 'label': 'Use case'},
    'problem':    {'branded': False, 'label': 'Problem'},
    'brand':      {'branded': True,  'label': 'Brand'},
    'trust':      {'branded': True,  'label': 'Trust'},
}

# Focus presets expand to explicit weights rather than being passed to the
# model as adjectives, so "comparison-heavy" is a guarantee, not a hint.
FOCUS_WEIGHTS = {
    'balanced':   {'discovery': 3, 'comparison': 2, 'evaluation': 2, 'use_case': 2, 'problem': 1, 'brand': 1, 'trust': 1},
    'discovery':  {'discovery': 6, 'comparison': 1, 'evaluation': 2, 'use_case': 3, 'problem': 1, 'brand': 1, 'trust': 0},
    'comparison': {'discovery': 2, 'comparison': 6, 'evaluation': 3, 'use_case': 1, 'problem': 0, 'brand': 1, 'trust': 1},
    'defence':    {'discovery': 1, 'comparison': 2, 'evaluation': 1, 'use_case': 1, 'problem': 1, 'brand': 4, 'trust': 5},
}

# How the model is told to phrase each intent. Kept here rather than inline so
# the taxonomy is legible in one place.
INTENT_BRIEF = {
    'discovery':  "someone looking for the best option in a category, without naming any brand",
    'comparison': "someone comparing options or asking for alternatives to a named competitor",
    'evaluation': "someone asking what to look for or how to choose",
    'use_case':   "someone with a specific occasion, audience or situation in mind",
    'problem':    "someone describing a problem, not a product",
    'brand':      "someone asking directly about the brand by name",
    'trust':      "someone checking whether the brand is trustworthy, or asking about a concern",
}

OVERSAMPLE = 2.5   # generate this multiple of the target, then select the best
RENDER_BATCH = 20  # tuples per LLM call


class GenerationError(RuntimeError):
    """Pipeline failed in a way the user needs to see."""


# --------------------------------------------------------------------------
# LLM plumbing
# --------------------------------------------------------------------------

def _client(organisation=None):
    """OpenRouter client, preferring the organisation's own key (BYOK)."""
    from openai import OpenAI

    key = None
    if organisation is not None:
        encrypted = getattr(organisation, 'openrouter_api_key', None)
        if encrypted:
            try:
                from shared_models.crypto import decrypt_value
                key = decrypt_value(encrypted)
            except Exception as exc:
                logger.warning("[PromptGen] could not read org OpenRouter key: %s", exc)
    key = key or getattr(settings, 'OPENROUTER_API_KEY', None)
    if not key:
        raise GenerationError(
            "No OpenRouter API key available. Add one in Settings > API Keys."
        )
    base = getattr(settings, 'OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
    return OpenAI(api_key=key, base_url=base, timeout=90)


def _chat(client, model, system, user, *, max_tokens=2000, temperature=0.7):
    """One completion, returning text. Raises GenerationError on failure.

    The default model (openai/gpt-5-mini) is a REASONING model, and that changes
    what max_tokens means: it caps reasoning *plus* answer, and reasoning is
    spent first. A budget sized for the answer alone therefore returns
    finish_reason="length" with content of None — a silent empty string, not an
    error.

    That is not hypothetical. On 2026-08-05 a 25-tuple plan was rendered in two
    batches; the first exhausted its 2000 tokens on reasoning and was dropped by
    the caller's `unusable batch` guard. Because build_plan emits unbranded
    intents before branded ones, that lost batch was *every unbranded prompt* —
    the user asked for a 30/70 mix and received five prompts, all branded, with
    only a WARNING in a log to explain it.

    So: keep reasoning short (this is rendering, not problem-solving) and give
    the answer real headroom. `extra_body` is passed through to OpenRouter and
    is ignored by providers that do not implement it.
    """
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            extra_body={"reasoning": {"effort": "low"}},
        )
    except Exception as exc:
        raise GenerationError(f"LLM call failed: {exc}") from exc

    usage = getattr(resp, 'usage', None)
    tokens = getattr(usage, 'total_tokens', 0) or 0
    text = (resp.choices[0].message.content or '').strip() if resp.choices else ''

    # An empty reply is nearly always the truncation above. Say so plainly —
    # the previous silence is what let a half-empty result look like a complete
    # one.
    if not text:
        finish = getattr(resp.choices[0], 'finish_reason', '?') if resp.choices else '?'
        reasoning = getattr(getattr(usage, 'completion_tokens_details', None), 'reasoning_tokens', '?')
        logger.error(
            "[PromptGen] empty completion (finish_reason=%s, reasoning_tokens=%s, max_tokens=%s) "
            "— raise max_tokens if this repeats",
            finish, reasoning, max_tokens,
        )
    return text, tokens


def _json_from(text: str, expect_list=True):
    """Pull JSON out of a model reply that may be fenced or prefaced.

    The existing prompt code scrapes strings out of replies and fails silently
    when the shape drifts; this at least fails loudly.
    """
    cleaned = re.sub(r'^```(?:json)?|```$', '', text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # Fall back to the outermost bracketed span.
    opener, closer = ('[', ']') if expect_list else ('{', '}')
    start, end = cleaned.find(opener), cleaned.rfind(closer)
    if start != -1 and end > start:
        try:
            return json.loads(cleaned[start:end + 1])
        except json.JSONDecodeError:
            pass
    raise GenerationError("Model did not return usable JSON")


# --------------------------------------------------------------------------
# Stage 1 — ground
# --------------------------------------------------------------------------

def _as_list(value) -> List[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str) and value.strip():
        return [p.strip() for p in value.split(',') if p.strip()]
    return []


def stage_ground(run, domain) -> Dict[str, Any]:
    """Assemble brand context from the wizard, the domain record and the site.

    The wizard's answers win over the stored record: the user just looked at
    both and corrected one of them.
    """
    cfg = run.config or {}

    ground = {
        'brand_name': cfg.get('brand_name') or domain.name,
        'url': domain.url,
        'country': cfg.get('country') or domain.country,
        'business_model': cfg.get('business_model') or getattr(domain, 'business_model', ''),
        'price_positioning': cfg.get('price_positioning') or getattr(domain, 'price_positioning', ''),
        'description': cfg.get('short_description') or getattr(domain, 'short_description', '') or '',
        'categories': _as_list(cfg.get('offering_categories')) or _as_list(getattr(domain, 'offering_categories', None)),
        'niches': _as_list(cfg.get('niches')) or _as_list(getattr(domain, 'niches', None)),
        'regions': _as_list(cfg.get('regions_served')) or _as_list(getattr(domain, 'regions_served', None)),
        'audience': cfg.get('target_audience') or getattr(domain, 'target_audience', '') or '',
        'use_cases': _as_list(cfg.get('use_cases')) or _as_list(getattr(domain, 'use_cases', None)),
        'buying_criteria': _as_list(cfg.get('buying_criteria')) or _as_list(getattr(domain, 'buying_criteria', None)),
        'objections': _as_list(cfg.get('common_objections')) or _as_list(getattr(domain, 'common_objections', None)),
        'competitors': _as_list(cfg.get('key_competitors')) or _as_list(getattr(domain, 'key_competitors', None)),
        'differentiators': _as_list(cfg.get('differentiators')) or _as_list(getattr(domain, 'differentiators', None)),
        'avoid': _as_list(cfg.get('topics_to_avoid')) or _as_list(getattr(domain, 'topics_to_avoid', None)),
        'seeds': [s for s in (cfg.get('seed_questions') or []) if str(s).strip()],
    }

    # Site read is best-effort — the wizard already collected enough to run.
    #
    # The class is WebCrawler; this imported `Crawler` and so raised ImportError
    # on every single run since the feature shipped. Being inside a broad
    # `except Exception` meant it never surfaced as a failure: generation simply
    # proceeded with no site context at all, logging one WARNING per run. Every
    # prompt generated so far was written without the model ever seeing the site.
    try:
        from core.misinformation_services.crawler import WebCrawler
        content, _status, _err = WebCrawler().crawl(domain.url)
        if content:
            ground['site_excerpt'] = re.sub(r'\s+', ' ', content)[:4000]
        else:
            logger.warning("[PromptGen] no site content for %s (status %s)", domain.url, _status)
    except Exception as exc:
        logger.warning("[PromptGen] crawl skipped for %s: %s", domain.url, exc)

    return ground


# --------------------------------------------------------------------------
# Stage 2 — entities
# --------------------------------------------------------------------------

def stage_entities(client, model, ground) -> Dict[str, List[str]]:
    """Expand the confirmed facts into a richer vocabulary to build from."""
    system = (
        "You extract the vocabulary a brand's customers use. "
        "Return ONLY a JSON object with keys: categories, use_cases, audiences, "
        "problems, criteria. Each is an array of short noun phrases, lowercase, "
        "at most 12 entries each. No commentary."
    )
    user = json.dumps({
        'brand': ground['brand_name'],
        'business_model': ground['business_model'],
        'description': ground['description'][:1200],
        'known_categories': ground['categories'],
        'known_use_cases': ground['use_cases'],
        'audience': ground['audience'][:600],
        'buying_criteria': ground['buying_criteria'],
        'site_excerpt': ground.get('site_excerpt', '')[:2000],
    })

    # 1200 left almost no room once reasoning took its share — see _chat.
    text, tokens = _chat(client, model, system, user, max_tokens=3000, temperature=0.4)
    data = _json_from(text, expect_list=False)

    merged = {
        'categories': _as_list(data.get('categories')) or ground['categories'],
        'use_cases': _as_list(data.get('use_cases')) or ground['use_cases'],
        'audiences': _as_list(data.get('audiences')),
        'problems': _as_list(data.get('problems')),
        'criteria': _as_list(data.get('criteria')) or ground['buying_criteria'],
    }
    if not merged['categories']:
        raise GenerationError(
            "Could not work out what this brand sells. Add a few categories in the wizard."
        )
    return merged, tokens


# --------------------------------------------------------------------------
# Stage 3 — plan and expand
# --------------------------------------------------------------------------

def build_plan(ground, entities, target, focus, branded_ratio) -> List[Dict[str, Any]]:
    """Deterministic (entity x intent x modifier) tuples honouring the mix.

    Nothing here calls an LLM. Doing the arithmetic in code is what makes the
    requested funnel mix and branded ratio exact rather than aspirational.
    """
    weights = FOCUS_WEIGHTS.get(focus, FOCUS_WEIGHTS['balanced'])
    wanted = max(1, int(target * OVERSAMPLE))

    branded_target = int(round(wanted * (branded_ratio / 100.0)))
    unbranded_target = wanted - branded_target

    branded_intents = [i for i in INTENTS if INTENTS[i]['branded'] and weights.get(i, 0)]
    unbranded_intents = [i for i in INTENTS if not INTENTS[i]['branded'] and weights.get(i, 0)]

    def allocate(intents, total):
        """Split `total` across `intents` proportional to their weights."""
        if not intents or total <= 0:
            return {}
        pool = sum(weights[i] for i in intents)
        out = {i: max(1, int(total * weights[i] / pool)) for i in intents}
        # Trim or pad to land exactly on `total`.
        while sum(out.values()) > total:
            out[max(out, key=out.get)] -= 1
        while sum(out.values()) < total:
            out[min(out, key=out.get)] += 1
        return {i: n for i, n in out.items() if n > 0}

    allocation = {}
    allocation.update(allocate(unbranded_intents, unbranded_target))
    allocation.update(allocate(branded_intents, branded_target))

    # Modifier pools, longest-lived first so early tuples are the most useful.
    categories = entities['categories'] or ground['categories'] or [ground['brand_name']]
    modifiers = {
        'region': ground['regions'],
        'use_case': entities['use_cases'],
        'audience': entities['audiences'],
        'criterion': entities['criteria'],
        'competitor': ground['competitors'],
        'problem': entities['problems'],
    }

    plan: List[Dict[str, Any]] = []
    for intent, count in allocation.items():
        for n in range(count):
            entity = categories[n % len(categories)]
            mod_key, mod_val = None, None
            # Each intent leans on the modifier that makes it realistic.
            preference = {
                'discovery': ['region', 'criterion'],
                'comparison': ['competitor', 'criterion'],
                'evaluation': ['criterion', 'audience'],
                'use_case': ['use_case', 'audience'],
                'problem': ['problem'],
                'brand': [],
                'trust': ['problem'],
            }[intent]
            for key in preference:
                pool = modifiers.get(key) or []
                if pool:
                    mod_key, mod_val = key, pool[n % len(pool)]
                    break
            plan.append({
                'intent': intent,
                'entity': entity,
                'modifier_key': mod_key,
                'modifier': mod_val,
                'is_branded': INTENTS[intent]['branded'],
            })
    return plan


def stage_expand(client, model, ground, plan) -> (List[Dict[str, Any]], int):
    """Render each planned tuple into a natural question."""
    system = (
        "You write the exact questions real people type into ChatGPT. "
        "Rules: one sentence, under 20 words, conversational, no marketing "
        "language, no brand voice. When the brief says the question is "
        "unbranded, DO NOT mention the brand at all. "
        "Return ONLY a JSON array of objects: [{\"i\": <index>, \"q\": \"...\"}]"
    )

    out: List[Dict[str, Any]] = []
    total_tokens = 0
    dropped = 0
    seeds = ground.get('seeds') or []

    for start in range(0, len(plan), RENDER_BATCH):
        batch = plan[start:start + RENDER_BATCH]
        briefs = []
        for idx, item in enumerate(batch):
            brief = {
                'i': idx,
                'about': item['entity'],
                'asker': INTENT_BRIEF[item['intent']],
                'mention_brand': item['is_branded'],
            }
            if item['modifier']:
                brief[item['modifier_key']] = item['modifier']
            briefs.append(brief)

        user_payload = {
            'brand': ground['brand_name'],
            'country': ground['country'],
            'questions_to_write': briefs,
        }
        if seeds:
            user_payload['match_the_style_of'] = seeds

        text, tokens = _chat(
            client, model,
            system,
            json.dumps(user_payload),
            # RENDER_BATCH is 20 questions per call. At ~25 tokens each that is
            # 500 for the answer alone, before reasoning and JSON overhead —
            # 2000 was not enough and cost whole batches.
            max_tokens=6000,
        )
        total_tokens += tokens

        try:
            rows = _json_from(text)
        except GenerationError:
            # Losing a batch is not cosmetic: build_plan emits unbranded intents
            # first, so the batch at offset 0 carries the generic prompts that
            # are the entire point of visibility monitoring. Dropping it quietly
            # produced an all-branded result that looked deliberate.
            dropped += len(batch)
            logger.error(
                "[PromptGen] LOST %s planned prompts — unusable batch at offset %s "
                "(model returned nothing parseable)", len(batch), start,
            )
            continue

        for row in rows:
            try:
                item = batch[int(row['i'])]
            except (KeyError, ValueError, IndexError, TypeError):
                continue
            q = str(row.get('q', '')).strip()
            if q:
                out.append({**item, 'text': q})

    if not out:
        raise GenerationError("The model returned no usable prompts. Try again.")

    # Surviving a partial loss is right — some prompts beat none — but the user
    # is about to review a list whose mix no longer matches what they asked for,
    # so record how skewed it may be.
    if dropped:
        branded = sum(1 for c in out if c.get('is_branded'))
        logger.error(
            "[PromptGen] rendered %s of %s planned (%s lost); surviving mix is %s branded / %s unbranded",
            len(out), len(plan), dropped, branded, len(out) - branded,
        )
    return out, total_tokens


# --------------------------------------------------------------------------
# Stage 4 — dedup
# --------------------------------------------------------------------------

_STOP = {
    'the', 'a', 'an', 'is', 'are', 'for', 'to', 'of', 'in', 'on', 'and', 'or',
    'what', 'which', 'best', 'good', 'can', 'i', 'me', 'my', 'you', 'your',
    'where', 'how', 'do', 'does', 'with', 'any', 'some',
}


def _fingerprint(text: str) -> frozenset:
    words = re.findall(r'[a-z0-9]+', text.lower())
    return frozenset(w for w in words if w not in _STOP)


def stage_dedup(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Drop near-identical questions by token-set overlap.

    At 5-30 prompts an embedding model would be overkill; the planner already
    prevents most repetition by construction, and Jaccard on content words
    catches the rest.
    """
    kept: List[Dict[str, Any]] = []
    seen: List[frozenset] = []
    for cand in candidates:
        fp = _fingerprint(cand['text'])
        if not fp:
            continue
        duplicate = False
        for other in seen:
            union = len(fp | other)
            if union and len(fp & other) / union >= 0.8:
                duplicate = True
                break
        if not duplicate:
            seen.append(fp)
            kept.append(cand)
    return kept


# --------------------------------------------------------------------------
# Stage 5 — score
# --------------------------------------------------------------------------

def stage_score(client, model, ground, candidates) -> (List[Dict[str, Any]], int):
    """Rate each candidate on realism and whether it would surface brands.

    A question that returns generic prose names nobody, so tracking it forever
    yields a permanent zero. That is the filter that matters.
    """
    system = (
        "Score each question for brand-visibility monitoring. "
        "realism: 0-1, would a real person type this. "
        "elicits_brands: 0-1, would an AI assistant answer it by naming "
        "specific companies or products. Generic informational questions score "
        "low. Return ONLY a JSON array: [{\"i\": <index>, \"realism\": 0.0, "
        "\"elicits_brands\": 0.0}]"
    )

    total_tokens = 0
    for start in range(0, len(candidates), 25):
        batch = candidates[start:start + 25]
        payload = [{'i': i, 'q': c['text']} for i, c in enumerate(batch)]
        try:
            text, tokens = _chat(
                client, model, system, json.dumps(payload),
                max_tokens=4000, temperature=0.1,
            )
            total_tokens += tokens
            rows = _json_from(text)
        except GenerationError:
            # Unscored candidates keep neutral scores rather than being lost.
            for c in batch:
                c.setdefault('score_realism', 0.5)
                c.setdefault('score_elicits_brands', 0.5)
            continue

        for row in rows:
            try:
                c = batch[int(row['i'])]
            except (KeyError, ValueError, IndexError, TypeError):
                continue
            c['score_realism'] = float(row.get('realism', 0.5) or 0)
            c['score_elicits_brands'] = float(row.get('elicits_brands', 0.5) or 0)

    for c in candidates:
        c.setdefault('score_realism', 0.5)
        c.setdefault('score_elicits_brands', 0.5)
    return candidates, total_tokens


def select_best(candidates, target) -> List[Dict[str, Any]]:
    """Take the best `target`, stratified by intent.

    A flat top-N sort would collapse a 5-prompt run into five near-identical
    discovery questions, which is exactly the failure this pipeline exists to
    avoid. Selecting per intent preserves the requested mix.
    """
    by_intent: Dict[str, List[Dict[str, Any]]] = {}
    for c in candidates:
        by_intent.setdefault(c['intent'], []).append(c)
    for rows in by_intent.values():
        rows.sort(
            key=lambda c: (c['score_elicits_brands'] * 2 + c['score_realism']),
            reverse=True,
        )

    chosen: List[Dict[str, Any]] = []
    # Round-robin across intents in the planner's proportions.
    while len(chosen) < target and any(by_intent.values()):
        for intent in list(by_intent):
            if len(chosen) >= target:
                break
            if by_intent[intent]:
                chosen.append(by_intent[intent].pop(0))
            else:
                del by_intent[intent]
    return chosen


# --------------------------------------------------------------------------
# Stage 6 — assemble
# --------------------------------------------------------------------------

def stage_assemble(run, candidates):
    """Cluster and persist. The planner already knows the cluster key."""
    from shared_models.models import PromptCandidate

    rows = []
    for c in candidates:
        entity = (c.get('entity') or 'general').strip()
        intent = c['intent']
        title = f"{entity.title()} — {INTENTS[intent]['label']}"
        rows.append(PromptCandidate(
            run=run,
            text=c['text'],
            intent=intent,
            entity=entity,
            is_branded=bool(c.get('is_branded')),
            cluster_key=f"{entity.lower()}::{intent}",
            cluster_title=title,
            score_realism=c.get('score_realism', 0.5),
            score_elicits_brands=c.get('score_elicits_brands', 0.5),
            status='pending',
        ))
    PromptCandidate.objects.bulk_create(rows, batch_size=200)
    return len(rows)


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------

def run_generation(run_id: int) -> Dict[str, Any]:
    """Walk the six stages for one run, updating progress as it goes."""
    from shared_models.models import PromptGenerationRun

    run = PromptGenerationRun.objects.select_related('domain', 'domain__organisation').get(id=run_id)
    domain = run.domain
    cfg = run.config or {}
    target = max(1, int(cfg.get('target_count') or 20))
    focus = cfg.get('funnel_mix') or 'balanced'
    branded_ratio = int(cfg.get('branded_ratio', 30) or 0)

    internal_model = getattr(settings, 'OPENROUTER_INTERNAL_MODEL', 'openai/gpt-5-mini')
    tokens = 0

    try:
        client = _client(getattr(domain, 'organisation', None))

        run.mark('ground', 5)
        ground = stage_ground(run, domain)
        run.grounding = ground
        run.save(update_fields=['grounding', 'modified_at'])

        run.mark('entities', 20)
        entities, t = stage_entities(client, internal_model, ground)
        tokens += t

        run.mark('expand', 40)
        plan = build_plan(ground, entities, target, focus, branded_ratio)
        rendered, t = stage_expand(client, internal_model, ground, plan)
        tokens += t

        run.mark('dedup', 65)
        deduped = stage_dedup(rendered)

        run.mark('score', 75)
        scored, t = stage_score(client, internal_model, ground, deduped)
        tokens += t

        # Topics-to-avoid is applied here, as a filter — naming a topic inside
        # a generation prompt tends to summon it.
        avoid = [a.lower() for a in ground.get('avoid', [])]
        if avoid:
            scored = [
                c for c in scored
                if not any(a in c['text'].lower() for a in avoid)
            ]

        best = select_best(scored, target)

        run.mark('assemble', 92)
        created = stage_assemble(run, best)

        run.status = 'DONE'
        run.stage = 'assemble'
        run.progress = 100
        run.tokens_used = tokens
        run.completed_at = timezone.now()
        run.save(update_fields=[
            'status', 'stage', 'progress', 'tokens_used', 'completed_at', 'modified_at',
        ])
        logger.info("[PromptGen] run %s produced %s candidates", run_id, created)
        return {'run_id': run_id, 'candidates': created}

    except Exception as exc:
        logger.exception("[PromptGen] run %s failed", run_id)
        run.status = 'FAIL'
        run.error = str(exc)[:2000]
        run.tokens_used = tokens
        run.save(update_fields=['status', 'error', 'tokens_used', 'modified_at'])
        return {'run_id': run_id, 'error': str(exc)}
