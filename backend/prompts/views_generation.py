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
import logging

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from domains.models import Domain
from .models import Prompt, PromptCandidate, PromptGenerationRun, PromptGroup

logger = logging.getLogger(__name__)

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

    # A failed run is worth surfacing once so the user can retry, but only if
    # nothing newer superseded it.
    if run is None:
        run = PromptGenerationRun.objects.filter(
            domain=domain, status='FAIL',
        ).order_by('-created_at').first()

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
    with transaction.atomic():
        for key, rows in clusters.items():
            rows.sort(key=lambda c: c.score_elicits_brands, reverse=True)
            title = rows[0].cluster_title or key.replace('::', ' — ').title()

            # group_id is unique per domain; suffix on collision rather than
            # merging into someone else's group.
            base, name, n = title[:90], title[:100], 2
            while PromptGroup.objects.filter(group_id=name, domain=domain).exists():
                name = f"{base} ({n})"[:100]
                n += 1

            group = PromptGroup.objects.create(group_id=name, domain=domain)
            created_groups += 1

            for i, cand in enumerate(rows):
                # Duplicate prompt text inside a group violates unique_together.
                if Prompt.objects.filter(prompt=cand.text, group=group).exists():
                    continue
                Prompt.objects.create(
                    prompt=cand.text,
                    group=group,
                    type='primary' if i == 0 else 'secondary',
                    track_status='INIT',
                )
                created_prompts += 1

        run.candidates.filter(id__in=[c.id for c in candidates]).update(status='accepted')
        run.candidates.exclude(id__in=[c.id for c in candidates]).update(status='rejected')
        run.status = 'ACPT'
        run.save(update_fields=['status', 'modified_at'])

    logger.info(
        "[PromptGen] run %s accepted: %s groups, %s prompts",
        run.id, created_groups, created_prompts,
    )
    return Response({
        'groups_created': created_groups,
        'prompts_created': created_prompts,
    })


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
