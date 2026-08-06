"""API for AI prompt generation.

Four endpoints, one lifecycle:

    POST   generation-runs/              queue a run  (wizard -> INIT)
    GET    generation-runs/active/       what the page should show right now
    GET    generation-runs/<id>/         poll progress, then read candidates
    POST   generation-runs/<id>/accept/  promote chosen candidates to prompts
    POST   generation-runs/<id>/discard/ throw the run away

Nothing here runs the pipeline. The backend has no Celery, so queuing a run
means writing a row with status INIT and letting the engine's scheduler claim
it — the same handoff competitor processing uses.
"""
import json
import logging
import re

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from domains.models import Domain
from .models import Prompt, PromptCandidate, PromptGenerationRun, PromptGroup

logger = logging.getLogger(__name__)

# Everything built from Search Console lands in one group, and later fetches
# append to it rather than creating "GSC Based Prompts (2)".
GSC_GROUP_KEY = 'search-console'
GSC_GROUP_TITLE = 'GSC Based Prompts' 

# Wizard answers that are facts about the brand rather than about one run, and
# so are written back to the project. Filling these here improves competitor
# analysis and reporting too.
DOMAIN_TEXT_FIELDS = [
    'short_description', 'target_audience', 'business_model', 'price_positioning',
]
DOMAIN_LIST_FIELDS = [
    'niches', 'offering_categories', 'regions_served', 'use_cases',
    'buying_criteria', 'common_objections', 'differentiators',
]
# Stored as comma-separated text on Domain for historical reasons.
DOMAIN_CSV_FIELDS = ['key_competitors', 'topics_to_avoid']

# A run in one of these states is still the page's current business.
LIVE_STATES = ('INIT', 'PROC', 'DONE')


def _visible_domains(user):
    """Domains this user may act on, mirroring the rest of the app."""
    qs = Domain.objects.all()
    if getattr(user, 'role', None) == 'super_admin':
        return qs
    return qs.filter(organisation_id=getattr(user, 'organisation_id', None))


def _run_payload(run, include_candidates=False):
    data = {
        'id': run.id,
        'domain_id': run.domain_id,
        'status': run.status,
        'stage': run.stage,
        'stage_index': run.stage_index,
        'stage_total': len(PromptGenerationRun.STAGE_ORDER),
        'stage_label': run.get_stage_display() if run.stage else '',
        'progress': run.progress,
        'error': run.error,
        'tokens_used': run.tokens_used,
        'target_count': (run.config or {}).get('target_count'),
        'candidate_count': run.candidates.filter(status='pending').count(),
        'created_at': run.created_at,
        'completed_at': run.completed_at,
    }
    if include_candidates:
        data['candidates'] = [
            {
                'id': c.id,
                'text': c.text,
                'intent': c.intent,
                'intent_label': c.get_intent_display(),
                'entity': c.entity,
                'is_branded': c.is_branded,
                'cluster_key': c.cluster_key,
                'cluster_title': c.cluster_title,
                'score_realism': round(c.score_realism, 2),
                'score_elicits_brands': round(c.score_elicits_brands, 2),
                'status': c.status,
            }
            for c in run.candidates.all()
        ]
    return data


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_generation_run(request):
    """Queue a generation run from the wizard's answers."""
    domain_id = request.data.get('domain_id')
    config = request.data.get('config') or {}

    if not domain_id:
        return Response({'error': 'domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    domain = get_object_or_404(_visible_domains(request.user), id=domain_id)

    # One live run per domain. Without this a double-click bills the customer's
    # OpenRouter key twice for the same work.
    existing = PromptGenerationRun.objects.filter(
        domain=domain, status__in=LIVE_STATES,
    ).order_by('-created_at').first()
    if existing:
        return Response(
            {'error': 'A generation run is already in progress for this project.',
             'run': _run_payload(existing)},
            status=status.HTTP_409_CONFLICT,
        )

    try:
        target = int(config.get('target_count') or 20)
    except (TypeError, ValueError):
        target = 20
    if not 1 <= target <= 200:
        return Response(
            {'error': 'target_count must be between 1 and 200'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    config['target_count'] = target

    with transaction.atomic():
        run = PromptGenerationRun.objects.create(
            domain=domain,
            config=config,
            created_by=request.user,
            status='INIT',
        )
        _persist_brand_facts(domain, config)

    logger.info("[PromptGen] queued run %s for domain %s", run.id, domain.id)
    return Response(_run_payload(run), status=status.HTTP_201_CREATED)


def _persist_brand_facts(domain, config):
    """Write the wizard's brand answers back onto the project."""
    dirty = []
    for f in DOMAIN_TEXT_FIELDS:
        v = config.get(f)
        if isinstance(v, str) and v.strip():
            setattr(domain, f, v.strip())
            dirty.append(f)
    for f in DOMAIN_LIST_FIELDS:
        v = config.get(f)
        if isinstance(v, list) and v:
            setattr(domain, f, v)
            dirty.append(f)
    for f in DOMAIN_CSV_FIELDS:
        v = config.get(f)
        if isinstance(v, list) and v:
            setattr(domain, f, ', '.join(str(x) for x in v))
            dirty.append(f)
    if dirty:
        domain.save(update_fields=dirty)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def active_generation_run(request):
    """The run the page should be reflecting, if any.

    Lets /prompts show Processing or Review after a refresh or a trip to
    another page, which is the whole point of running this in the background.
    """
    domain_id = request.query_params.get('domain_id')
    if not domain_id:
        return Response({'error': 'domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    domain = get_object_or_404(_visible_domains(request.user), id=domain_id)
    run = PromptGenerationRun.objects.filter(
        domain=domain, status__in=LIVE_STATES,
    ).order_by('-created_at').first()

    # A failed run is worth surfacing so the user can retry — but only while it
    # is still the latest thing that happened. This used to take the newest FAIL
    # regardless of what came after, so a failure stayed on screen permanently
    # even once a later run had succeeded and been accepted: the page showed
    # "Generation failed" over the top of the source chooser, and there was no
    # way to start a new run at all.
    if run is None:
        latest = PromptGenerationRun.objects.filter(
            domain=domain,
        ).order_by('-created_at').first()
        if latest is not None and latest.status == 'FAIL':
            run = latest

    return Response(_run_payload(run) if run else {'run': None})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def generation_run_detail(request, run_id):
    """Poll progress; includes candidates once the run is ready."""
    run = get_object_or_404(
        PromptGenerationRun.objects.select_related('domain'), id=run_id,
    )
    get_object_or_404(_visible_domains(request.user), id=run.domain_id)
    return Response(_run_payload(run, include_candidates=(run.status in ('DONE', 'ACPT'))))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_generation_run(request, run_id):
    """Promote selected candidates into real, trackable prompts.

    Candidates sharing a cluster become one PromptGroup: the best-scoring one
    is the primary prompt and the rest are variants, which is exactly the
    existing schema. Prompts are created with track_status INIT so the normal
    engine pipeline picks them up with no special casing.
    """
    run = get_object_or_404(
        PromptGenerationRun.objects.select_related('domain'), id=run_id,
    )
    domain = get_object_or_404(_visible_domains(request.user), id=run.domain_id)

    if run.status not in ('DONE',):
        return Response(
            {'error': f'Run is {run.get_status_display()}, nothing to accept.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # {id: edited_text} — the review table allows inline edits.
    edits = request.data.get('edits') or {}
    accepted_ids = request.data.get('accepted_ids')

    candidates = list(run.candidates.all())
    if accepted_ids is not None:
        wanted = {int(i) for i in accepted_ids}
        candidates = [c for c in candidates if c.id in wanted]

    if not candidates:
        return Response(
            {'error': 'Select at least one prompt to add.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    clusters = {}
    for c in candidates:
        c.text = str(edits.get(str(c.id), c.text)).strip() or c.text
        clusters.setdefault(c.cluster_key or 'general', []).append(c)

    created_groups, created_prompts = 0, 0
    # (prompt, candidate) for every prompt created, so keyword linking can tie
    # each prompt to the keywords it is about.
    accepted_pairs = []
    with transaction.atomic():
        for key, rows in clusters.items():
            rows.sort(key=lambda c: c.score_elicits_brands, reverse=True)
            title = rows[0].cluster_title or key.replace('::', ' — ').title()

            # Search Console prompts append to their one group. Every other
            # cluster gets a fresh group, suffixed on collision rather than
            # merging into someone else's.
            if key == GSC_GROUP_KEY:
                group, made = PromptGroup.objects.get_or_create(
                    group_id=GSC_GROUP_TITLE, domain=domain,
                )
                if made:
                    created_groups += 1
            else:
                base, name, n = title[:90], title[:100], 2
                while PromptGroup.objects.filter(group_id=name, domain=domain).exists():
                    name = f"{base} ({n})"[:100]
                    n += 1

                group = PromptGroup.objects.create(group_id=name, domain=domain)
                created_groups += 1

            # A group being appended to already has a primary; a second one
            # would misreport which prompt leads the group.
            has_primary = group.prompts.filter(type='primary').exists()
            added_to_group = 0

            for i, cand in enumerate(rows):
                # Duplicate prompt text inside a group violates unique_together.
                if Prompt.objects.filter(prompt=cand.text, group=group).exists():
                    continue
                prompt = Prompt.objects.create(
                    prompt=cand.text,
                    group=group,
                    type='secondary' if has_primary else ('primary' if i == 0 else 'secondary'),
                    track_status='INIT',
                )
                created_prompts += 1
                added_to_group += 1
                accepted_pairs.append((prompt, cand))

            # A group that has already run sits at COMP, and the scheduler only
            # picks up groups in INIT — so prompts appended to it would never be
            # tracked at all. Reopening it is what makes an append reach the AI
            # platforms rather than sit there looking added.
            if added_to_group and group.track_status != 'INIT':
                group.track_status = 'INIT'
                group.track_message = 'Reopened: new prompts added'
                group.save(update_fields=['track_status', 'track_message', 'modified_at'])

        created_links, created_keywords = _link_prompts_to_keywords(domain, accepted_pairs)

        run.candidates.filter(id__in=[c.id for c in candidates]).update(status='accepted')
        run.candidates.exclude(id__in=[c.id for c in candidates]).update(status='rejected')
        run.status = 'ACPT'
        run.save(update_fields=['status', 'modified_at'])

    logger.info(
        "[PromptGen] run %s accepted: %s groups, %s prompts, %s keyword links "
        "(%s keywords derived)",
        run.id, created_groups, created_prompts, created_links, created_keywords,
    )
    return Response({
        'groups_created': created_groups,
        'prompts_created': created_prompts,
        'keyword_links': created_links,
        'keywords_derived': created_keywords,
    })


# Words that carry no signal when matching a prompt to a keyword. Question
# openers dominate prompt text and would otherwise make every prompt look
# similar to every keyword.
_MATCH_STOPWORDS = {
    'a', 'an', 'the', 'and', 'or', 'of', 'for', 'to', 'in', 'on', 'with', 'my',
    'our', 'your', 'their', 'is', 'are', 'be', 'do', 'does', 'did', 'can',
    'could', 'should', 'would', 'will', 'what', 'which', 'who', 'whom', 'how',
    'where', 'when', 'why', 'best', 'good', 'top', 'me', 'i', 'we', 'you',
    'it', 'that', 'this', 'these', 'those', 'about', 'into', 'from', 'by',
    'at', 'as', 'any', 'some', 'more', 'most', 'help', 'need', 'want', 'look',
}



def _json_array(text):
    """Parse a JSON array from a model reply, tolerating a fence or preamble."""
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


def _tokens(text):
    return {
        w for w in re.findall(r"[a-z0-9]+", (text or '').lower())
        if len(w) > 2 and w not in _MATCH_STOPWORDS
    }


def _link_prompts_to_keywords(domain, accepted_pairs):
    """Attach each accepted prompt to the keywords it is about.

    A topic reaches its prompts through Topic -> TopicKeyword -> Keyword ->
    PromptKeyword -> Prompt. The old pipeline generated one prompt per keyword,
    so that last link was free. The generation wizard writes prompts that came
    from a brand brief instead, so nothing linked them to anything: every topic
    card on a wizard-built project read "across 0 prompts" while the prompts
    underneath had tracked analytics all along.

    Matching is token overlap against the domain's own keywords — deterministic
    and free, no second model call. A prompt with no confident match gets a
    short keyword derived from the candidate's own entity and cluster, never the
    whole question: a keyword is what a searcher types, and storing sentences
    here is what filled the topic chips with paragraphs.

    Returns (links_created, keywords_created).
    """
    from keywords.models import Keyword
    from topics.models import PromptKeyword

    if not accepted_pairs:
        return 0, 0

    keywords = list(Keyword.objects.filter(domain=domain).only('id', 'keyword'))
    keyword_tokens = [(k, _tokens(k.keyword)) for k in keywords]
    by_text = {k.keyword.lower(): k for k in keywords}

    links, new_keywords = [], []
    now = timezone.now()

    for prompt, cand in accepted_pairs:
        prompt_tokens = _tokens(prompt.prompt)
        if not prompt_tokens:
            continue

        scored = []
        for keyword, tokens in keyword_tokens:
            if not tokens:
                continue
            # Share of the KEYWORD's words present in the prompt: a two-word
            # keyword fully contained in a long question is a strong match, and
            # Jaccard would score it near zero purely because the prompt is
            # longer.
            shared = len(tokens & prompt_tokens)
            overlap = shared / len(tokens)
            # Two conditions, because either alone is wrong. Coverage alone
            # accepts a two-word keyword matching on the single word "ai",
            # which pairs every prompt with every AI keyword. A raw count alone
            # favours long keywords that happen to share filler. Measured on
            # AppInventiv: this rule matches 7 of 10 wizard prompts, and the
            # three it rejects genuinely have no keyword about them.
            if shared >= 2 and overlap >= 0.5:
                scored.append((overlap, len(tokens), keyword))

        if scored:
            # Best coverage, then the most specific keyword among ties.
            scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
            for overlap, _size, keyword in scored[:3]:
                links.append(PromptKeyword(
                    prompt=prompt,
                    keyword=keyword,
                    relevance_score=round(overlap * 100, 2),
                ))
            continue

        # No match: derive a short keyword from what the candidate already
        # carries. entity is the subject the question is about; cluster_title is
        # its theme. Both are short by construction.
        parts = [p for p in ((cand.entity or '').strip(), (cand.cluster_title or '').strip()) if p]
        derived = ' '.join(dict.fromkeys(' '.join(parts).split()))[:255].strip()
        if not derived:
            continue

        existing = by_text.get(derived.lower())
        if existing is None:
            existing = Keyword.objects.create(
                keyword=derived,
                domain=domain,
                # These must not feed the old keyword -> prompt generator: every
                # generated prompt would derive another keyword, and the domain
                # would loop generate -> derive -> INIT -> generate.
                auto_generate_prompts=False,
                source='ai-prompt',
                intent=(cand.intent or None),
                entity=(cand.entity or None),
                topic=(cand.cluster_title or None),
                cluster_id=(cand.cluster_key or None),
                last_used_for_generation=now,
                last_used_for_topic_generation=None,
            )
            by_text[derived.lower()] = existing
            keyword_tokens.append((existing, _tokens(derived)))
            new_keywords.append(existing)

        links.append(PromptKeyword(prompt=prompt, keyword=existing, relevance_score=50))

    if links:
        PromptKeyword.objects.bulk_create(links, ignore_conflicts=True)

    return len(links), len(new_keywords)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_console_seeds(request):
    """Candidate prompt seeds from this project's Search Console queries.

    Three answers, and the card on the Prompts page renders one per state:
    Search Console is not connected (send them to Integrations), it is connected
    but has no usable queries yet, or here are the queries worth turning into
    prompts.

    Query params:
        domain_id: Required
    """
    domain_id = request.query_params.get('domain_id')
    if not domain_id:
        return Response({'error': 'domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    domain = get_object_or_404(_visible_domains(request.user), id=domain_id)

    from integrations.models import Integration
    from .gsc_seeds import fetch_search_console_queries, rank_candidates

    integration = Integration.objects.filter(
        domain=domain, type='search_console', status='active',
    ).order_by('-modified_at').first()

    if not integration:
        return Response({
            'connected': False,
            'candidates': [],
            'message': 'Google Search Console is not connected for this project.',
        })

    site_url = integration.provider_id
    try:
        rows = fetch_search_console_queries(integration, site_url)
    except Exception as exc:
        logger.error("[GSCSeeds] fetch failed for domain %s: %s", domain.id, exc)
        return Response({
            'connected': True,
            'site_url': site_url,
            'candidates': [],
            'error': 'Could not read Search Console right now. Please try again shortly.',
        }, status=status.HTTP_502_BAD_GATEWAY)

    candidates, stats = rank_candidates(rows, domain)

    return Response({
        'connected': True,
        'site_url': site_url,
        'candidates': candidates,
        'stats': stats,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_run_from_search_console(request):
    """Turn chosen Search Console queries into prompts, ready for review.

    A search query and a chat prompt are not the same sentence. "digital
    marketing agencies in andheri" is how a person types into a search box; the
    same person asks an assistant "Which digital marketing agencies work in
    Andheri?". So each query is rewritten into the question form, and nothing
    else about it is invented — the demand is real, only the phrasing changes.

    The result lands in the same PromptGenerationRun the AI wizard produces, so
    review, editing, accepting and keyword linking are the existing flow rather
    than a second one.

    Body:
        domain_id: Required
        queries: Required - list of Search Console query strings
    """
    domain_id = request.data.get('domain_id')
    queries = request.data.get('queries') or []

    if not domain_id:
        return Response({'error': 'domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    domain = get_object_or_404(_visible_domains(request.user), id=domain_id)

    queries = [str(q).strip() for q in queries if str(q).strip()][:100]
    if not queries:
        return Response({'error': 'Select at least one query.'}, status=status.HTTP_400_BAD_REQUEST)

    from .gsc_seeds import classify, TIER_LABELS

    system = (
        "You rewrite search queries as the question a person would type into an "
        "AI assistant. Return ONLY a JSON array, no prose, no code fence.\n\n"
        "Each element: {\"i\": <index of the input>, \"q\": \"the question\", "
        "\"entity\": \"the thing being asked about\", \"topic\": \"short theme\"}\n\n"
        "Rules: keep the intent and every qualifier of the original — place, "
        "budget, industry, product type. One sentence, under 25 words, "
        "conversational. NEVER name the brand being monitored; these questions "
        "measure whether an assistant recommends it unprompted, so a question "
        "that names it measures nothing."
    )

    payload = {
        'country': domain.country or '',
        'queries_to_rewrite': [{'i': i, 'query': q} for i, q in enumerate(queries)],
    }

    try:
        from domains.views import get_openai_client

        client = get_openai_client()
        response = client.chat.completions.create(
            model=getattr(settings, 'OPENROUTER_INTERNAL_MODEL', 'openai/gpt-5-mini'),
            messages=[
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': json.dumps(payload)},
            ],
            temperature=0.4,
            max_tokens=8000,
            extra_body={'reasoning': {'effort': 'low'}},
        )
        reply = (response.choices[0].message.content or '') if response.choices else ''
    except Exception as exc:
        logger.error("[GSCSeeds] rewrite failed for domain %s: %s", domain.id, exc)
        return Response(
            {'error': 'Could not rewrite the queries right now. Please try again.'},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    rows = _json_array(reply)
    if not rows:
        return Response(
            {'error': 'Nothing usable came back from the rewrite. Please try again.'},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    with transaction.atomic():
        run = PromptGenerationRun.objects.create(
            domain=domain,
            status='DONE',
            stage='assemble',
            progress=100,
            config={
                'source': 'search_console',
                'seed_questions': queries[:10],
                'target_count': len(queries),
                'branded_ratio': 0,
            },
            grounding={'source': 'search_console', 'query_count': len(queries)},
        )

        created = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            text = str(row.get('q') or '').strip()
            if not text:
                continue
            try:
                original = queries[int(row.get('i'))]
            except (TypeError, ValueError, IndexError):
                original = ''

            tier = classify(original) if original else 3
            PromptCandidate.objects.create(
                run=run,
                text=text,
                intent=str(row.get('intent') or '')[:16],
                entity=str(row.get('entity') or '')[:255],
                is_branded=False,
                # One cluster for every Search Console prompt. Left to the
                # model's per-query topic, five queries produced five groups of
                # one prompt each — the grouping carried no information and the
                # review screen read as a list of headings. Provenance is the
                # useful axis here: these came from real search demand, and
                # they are worth looking at together.
                cluster_key=GSC_GROUP_KEY,
                cluster_title=GSC_GROUP_TITLE,
                # Real demand, so realism is not in question — it was typed by a
                # person. The tier carries how likely an answer is to name any
                # brand at all, which is what the other score means elsewhere.
                score_realism=1.0,
                score_elicits_brands={1: 0.9, 2: 0.6, 3: 0.3}.get(tier, 0.3),
            )
            created += 1

    logger.info("[GSCSeeds] domain %s: run %s created with %s prompts from %s queries",
                domain.id, run.id, created, len(queries))

    return Response({
        'run_id': run.id,
        'candidates_created': created,
        'queries_used': len(queries),
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def discard_generation_run(request, run_id):
    """Throw a run away so the card returns to its idle state."""
    run = get_object_or_404(
        PromptGenerationRun.objects.select_related('domain'), id=run_id,
    )
    get_object_or_404(_visible_domains(request.user), id=run.domain_id)

    run.status = 'DISC'
    run.save(update_fields=['status', 'modified_at'])
    return Response({'status': 'discarded'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_prompt_file(request):
    """Turn an uploaded spreadsheet into a reviewable run.

    Produces exactly what generation produces — a DONE run with PromptCandidate
    rows — so review, inline edits, accept and discard all work unchanged. The
    difference is only in how the candidates were obtained.

    Synchronous: parsing is instant and grouping is one model call per 40
    prompts, so even a 500-row file lands well inside a request. Should the cap
    ever rise, this belongs on the engine's queue like generation itself.
    """
    domain_id = request.data.get('domain_id')
    upload = request.FILES.get('file')

    if not domain_id:
        return Response({'error': 'domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not upload:
        return Response({'error': 'No file was uploaded.'}, status=status.HTTP_400_BAD_REQUEST)

    domain = get_object_or_404(_visible_domains(request.user), id=domain_id)

    # Same one-live-run rule as generation: two sources competing for the review
    # panel would silently discard one of them.
    existing = PromptGenerationRun.objects.filter(
        domain=domain, status__in=LIVE_STATES,
    ).order_by('-created_at').first()
    if existing:
        return Response(
            {'error': 'Finish reviewing the current prompt list first.',
             'run': _run_payload(existing)},
            status=status.HTTP_409_CONFLICT,
        )

    from .upload_prompts import UploadError, group_prompts, parse_prompts, to_candidate_rows

    try:
        prompts = parse_prompts(upload.name, upload.read())
    except UploadError as exc:
        return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as exc:
        logger.error('[Upload] unreadable file %s: %s', upload.name, exc, exc_info=True)
        return Response({'error': 'That file could not be read.'},
                        status=status.HTTP_400_BAD_REQUEST)

    grouped = group_prompts(domain, prompts)

    with transaction.atomic():
        run = PromptGenerationRun.objects.create(
            domain=domain,
            created_by=request.user,
            status='DONE',
            stage='assemble',
            progress=100,
            config={
                'source': 'upload',
                'filename': upload.name,
                'target_count': len(prompts),
            },
        )
        PromptCandidate.objects.bulk_create(
            [PromptCandidate(run=run, **row) for row in to_candidate_rows(grouped)],
            batch_size=200,
        )

    logger.info(
        '[Upload] run %s for domain %s: %s prompts from %s',
        run.id, domain.id, len(prompts), upload.name,
    )
    return Response(_run_payload(run, include_candidates=True),
                    status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def prefill_from_site(request):
    """Propose wizard answers by reading the project's own website.

    Returns the fields only — nothing is saved. The wizard fills the inputs the
    user has left empty and leaves anything they typed alone, so a guess can
    never overwrite a fact the user supplied.

    Always 200, even on failure: an unreachable site is an ordinary outcome for
    this button, not a client error, and the wizard just carries on by hand with
    the message shown. Reserving non-2xx for real faults keeps the frontend's
    error handling meaningful.
    """
    domain_id = request.data.get('domain_id')
    if not domain_id:
        return Response({'error': 'domain_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    domain = get_object_or_404(_visible_domains(request.user), id=domain_id)

    from .site_profile import infer_profile
    result = infer_profile(domain)

    # Persist so the crawl is paid for once per project, not once per visit to
    # the wizard. The next open reads these straight off Domain and shows them
    # as "Saved" — the button is then only needed to deliberately refresh.
    if result['fields']:
        from .site_profile import to_storage
        _persist_brand_facts(domain, to_storage(result['fields']))

    return Response({'fields': result['fields'], 'error': result['error']})
