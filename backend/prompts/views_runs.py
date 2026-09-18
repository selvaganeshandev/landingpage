"""
Runs — the evidence ledger behind every number in GEO monitoring.

`PromptAnalyticsRun` is already written by the engine on every completed
prompt × engine execution (see engine/core/prompt_analytics_processor.py): one
immutable row per run, never updated by a later run. Nothing read it until now —
the product only ever showed the aggregates computed from it.

These endpoints expose that ledger as-is:

    GET  /prompts/runs/          one row per run, filtered and paginated
    GET  /prompts/runs/summary/  the KPI strip above the table
    GET  /prompts/runs/export/   the same rows as CSV

Deliberately read-only and additive: no migration, no change to the tracked
pipeline, no existing endpoint touched. Anything the ledger does not record
(per-run latency, per-run failure) is absent here rather than guessed — the
engine does not store it today.

Access follows the same rule as the mentions endpoints: super_admin and
global-access users see any domain, everyone else needs a DomainAccess row.
"""
import csv
import logging
from datetime import timedelta

from django.db.models import Avg, Count, F, Q, Window
from django.db.models.functions import RowNumber
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from domains.models import DomainAccess

from .models import PromptAnalyticsRun

logger = logging.getLogger(__name__)

DEFAULT_DAYS = 30
MAX_DAYS = 365
MAX_LIMIT = 200
EXPORT_LIMIT = 5000

# How many runs a variant needs before its rate is worth quoting. AI answers are
# non-deterministic, so a single run is an anecdote; these are the bands the
# report and the UI both use.
CONFIDENCE_BANDS = (
    (20, 'high', '●●●●'),
    (6, 'good', '●●●○'),
    (3, 'fair', '●●○○'),
    (0, 'low', '●○○○'),
)


def confidence_for(avg_runs):
    """Confidence band for an average runs-per-variant figure."""
    if not avg_runs:
        return {'level': 'none', 'marker': '○○○○', 'label': 'No runs yet'}
    for threshold, level, marker in CONFIDENCE_BANDS:
        if avg_runs >= threshold:
            return {
                'level': level,
                'marker': marker,
                'label': {
                    'high': 'High confidence',
                    'good': 'Good confidence',
                    'fair': 'Fair confidence',
                    'low': 'Low confidence — single runs are anecdotes',
                }[level],
            }
    return {'level': 'low', 'marker': '●○○○', 'label': 'Low confidence'}


def _has_domain_access(user, domain_id):
    """Who may read this domain's ledger.

    super_admin reads anything. "Global domain access" widens a user to every
    domain *in their own organisation* — so it is paired with an organisation
    check here rather than trusted on its own; the middleware scopes domain_id
    as well, and this makes the endpoint safe without it. Everyone else needs an
    explicit DomainAccess row.
    """
    if not (user and getattr(user, 'is_authenticated', False)):
        return False
    if getattr(user, 'role', '') == 'super_admin':
        return True
    from core.authorization import has_global_domain_access
    if has_global_domain_access(user):
        from domains.models import Domain
        own_org = getattr(user, 'organisation_id', None)
        if own_org and Domain.objects.filter(pk=domain_id, organisation_id=own_org).exists():
            return True
    return DomainAccess.objects.filter(user=user, domain_id=domain_id).exists()


def _int(value, default, lo, hi):
    try:
        return max(lo, min(int(value), hi))
    except (TypeError, ValueError):
        return default


def _window(request):
    """(since, until, days) from ?days=, or ?start_date=&end_date= (YYYY-MM-DD)."""
    until = timezone.now()
    start_raw = (request.GET.get('start_date') or '').strip()
    end_raw = (request.GET.get('end_date') or '').strip()
    if start_raw:
        from django.utils.dateparse import parse_date
        start = parse_date(start_raw)
        end = parse_date(end_raw) if end_raw else None
        if start:
            since = timezone.make_aware(timezone.datetime.combine(start, timezone.datetime.min.time()))
            if end:
                until = timezone.make_aware(timezone.datetime.combine(end, timezone.datetime.max.time()))
            return since, until, max(1, (until.date() - start).days + 1)
    days = _int(request.GET.get('days'), DEFAULT_DAYS, 1, MAX_DAYS)
    return until - timedelta(days=days), until, days


def _base_queryset(request, domain_id):
    """Every run for this domain inside the window, with the caller's filters applied."""
    since, until, days = _window(request)
    qs = (
        PromptAnalyticsRun.objects
        .filter(prompt__group__domain_id=domain_id, tracked_at__gte=since, tracked_at__lte=until)
        .select_related('prompt', 'prompt__group')
    )

    platform = (request.GET.get('platform') or '').strip()
    if platform and platform.lower() != 'all':
        qs = qs.filter(platform__iexact=platform)

    group_id = (request.GET.get('group_id') or '').strip()
    if group_id.isdigit():
        qs = qs.filter(prompt__group_id=int(group_id))

    prompt_id = (request.GET.get('prompt_id') or '').strip()
    if prompt_id.isdigit():
        qs = qs.filter(prompt_id=int(prompt_id))

    mention = (request.GET.get('mention') or 'any').strip().lower()
    if mention in ('yes', 'true', 'mentioned'):
        qs = qs.filter(is_mention=True)
    elif mention in ('no', 'false', 'absent'):
        qs = qs.filter(is_mention=False)

    if (request.GET.get('cited') or '').strip().lower() in ('yes', 'true'):
        qs = qs.filter(total_citations__gt=0)

    search = (request.GET.get('search') or '').strip()
    if search:
        qs = qs.filter(prompt__prompt__icontains=search)

    # "Variance only": prompts whose runs do not agree with each other — the
    # engine named the brand on some runs of the same question and not on
    # others. These are the rows worth reading, because a rate built on them is
    # hiding a coin flip.
    if (request.GET.get('variance') or '').strip().lower() in ('1', 'true', 'only', 'yes'):
        unstable = (qs.values('prompt_id')
                      .annotate(kinds=Count('is_mention', distinct=True))
                      .filter(kinds__gt=1)
                      .values_list('prompt_id', flat=True))
        qs = qs.filter(prompt_id__in=list(unstable))

    return qs, since, until, days


def _group_label(group):
    """What a prompt group is called on screen: its theme, else its group_id string."""
    return (getattr(group, 'theme', '') or getattr(group, 'group_id', '') or '').strip()


def _row(run, runs_for_prompt=None):
    citations = run.citation_list if isinstance(run.citation_list, list) else []
    competitors = run.competitor_mention_list if isinstance(run.competitor_mention_list, list) else []
    return {
        'id': run.id,
        'tracked_at': run.tracked_at.isoformat(),
        'platform': run.platform,
        'region': run.region,
        'prompt_id': run.prompt_id,
        'prompt': (run.prompt.prompt or '')[:500] if run.prompt_id else '',
        'group_id': run.prompt.group_id if run.prompt_id else None,
        'group': _group_label(run.prompt.group) if (run.prompt_id and run.prompt.group_id) else '',
        # "run 3 of 9" — which repeat of this question this row is, inside the
        # current window. Repeats are the whole point: one answer is an anecdote.
        'run_number': getattr(run, 'run_number', None),
        'runs_for_prompt': (runs_for_prompt or {}).get(run.prompt_id),
        'is_mention': run.is_mention,
        'total_mentions': run.total_mentions,
        'total_citations': run.total_citations,
        'position': float(run.position or 0),
        'sentiment_category': run.sentiment_category,
        'sentiment_score': float(run.sentiment_score or 0),
        'citations': citations[:25],
        'competitors': competitors[:25],
        'context_summary': (run.context_summary or '')[:1000],
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def runs_list(request):
    """One row per run: when it happened, on which engine, and what it recorded."""
    domain_id = (request.GET.get('domain_id') or '').strip()
    if not domain_id.isdigit():
        return Response({'error': 'domain_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
    if not _has_domain_access(request.user, int(domain_id)):
        return Response({'error': 'Forbidden: no access to this domain.'}, status=status.HTTP_403_FORBIDDEN)

    qs, since, until, days = _base_queryset(request, int(domain_id))
    total_count = qs.count()
    limit = _int(request.GET.get('limit'), 25, 1, MAX_LIMIT)
    offset = _int(request.GET.get('offset'), 0, 0, 10 ** 7)

    # RowNumber over the filtered set, so "run 3" means the third run of that
    # question inside the window the user is looking at.
    numbered = qs.annotate(run_number=Window(
        expression=RowNumber(), partition_by=[F('prompt_id')], order_by=F('tracked_at').asc()))
    page = list(numbered.order_by('-tracked_at', '-id')[offset:offset + limit])
    totals = dict(qs.filter(prompt_id__in={r.prompt_id for r in page})
                    .values_list('prompt_id')
                    .annotate(n=Count('id'))) if page else {}
    rows = [_row(r, totals) for r in page]

    return Response({
        'runs': rows,
        'total_count': total_count,
        'limit': limit,
        'offset': offset,
        'window': {'since': since.isoformat(), 'until': until.isoformat(), 'days': days},
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def runs_summary(request):
    """The KPI strip: how many runs, over how many variants, and how much to trust them."""
    domain_id = (request.GET.get('domain_id') or '').strip()
    if not domain_id.isdigit():
        return Response({'error': 'domain_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
    if not _has_domain_access(request.user, int(domain_id)):
        return Response({'error': 'Forbidden: no access to this domain.'}, status=status.HTTP_403_FORBIDDEN)

    qs, since, until, days = _base_queryset(request, int(domain_id))
    totals = qs.aggregate(
        total=Count('id'),
        variants=Count('prompt_id', distinct=True),
        engines=Count('platform', distinct=True),
        mentioned=Count('id', filter=Q(is_mention=True)),
        cited=Count('id', filter=Q(total_citations__gt=0)),
        avg_position=Avg('position', filter=Q(is_mention=True, position__gt=0)),
    )
    total = totals['total'] or 0
    variants = totals['variants'] or 0
    avg_runs = round(total / variants, 1) if variants else 0.0

    by_platform = []
    for row in (qs.values('platform')
                  .annotate(runs=Count('id'),
                            variants=Count('prompt_id', distinct=True),
                            mentioned=Count('id', filter=Q(is_mention=True)),
                            cited=Count('id', filter=Q(total_citations__gt=0)))
                  .order_by('-runs')):
        by_platform.append({
            'platform': row['platform'],
            'runs': row['runs'],
            'variants': row['variants'],
            'mentioned': row['mentioned'],
            'cited': row['cited'],
            'mention_rate': round(100 * row['mentioned'] / row['runs']) if row['runs'] else 0,
        })

    # Variants whose rate rests on too few runs to quote — the honest caveat the
    # prototype's "low confidence" alert is about.
    per_variant = qs.values('prompt_id').annotate(runs=Count('id'))
    low_confidence = sum(1 for v in per_variant if v['runs'] < 6)

    last_run = qs.order_by('-tracked_at').values_list('tracked_at', flat=True).first()

    groups = []
    for row in (qs.values('prompt__group_id', 'prompt__group__theme', 'prompt__group__group_id')
                  .annotate(runs=Count('id')).order_by('-runs')[:50]):
        if row['prompt__group_id']:
            groups.append({
                'id': row['prompt__group_id'],
                'label': (row['prompt__group__theme'] or row['prompt__group__group_id'] or '').strip(),
                'runs': row['runs'],
            })

    # Questions the engines answered inconsistently across repeats.
    unstable = (qs.values('prompt_id').annotate(kinds=Count('is_mention', distinct=True))
                  .filter(kinds__gt=1).count())

    return Response({
        'total_runs': total,
        'variants': variants,
        'engines': totals['engines'] or 0,
        'avg_runs_per_variant': avg_runs,
        'confidence': confidence_for(avg_runs),
        'low_confidence_variants': low_confidence,
        'mentioned_runs': totals['mentioned'] or 0,
        'cited_runs': totals['cited'] or 0,
        'mention_rate': round(100 * (totals['mentioned'] or 0) / total) if total else 0,
        'citation_rate': round(100 * (totals['cited'] or 0) / total) if total else 0,
        'avg_position': round(float(totals['avg_position']), 1) if totals['avg_position'] else None,
        'last_run_at': last_run.isoformat() if last_run else None,
        'by_platform': by_platform,
        'groups': groups,
        'unstable_variants': unstable,
        'window': {'since': since.isoformat(), 'until': until.isoformat(), 'days': days},
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def runs_export(request):
    """The filtered ledger as CSV — one row per run, for a spreadsheet or an auditor."""
    domain_id = (request.GET.get('domain_id') or '').strip()
    if not domain_id.isdigit():
        return Response({'error': 'domain_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
    if not _has_domain_access(request.user, int(domain_id)):
        return Response({'error': 'Forbidden: no access to this domain.'}, status=status.HTTP_403_FORBIDDEN)

    qs, _since, _until, _days = _base_queryset(request, int(domain_id))
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="promptmaxx-runs-{domain_id}.csv"'
    response.write('﻿')  # BOM so Excel reads UTF-8
    writer = csv.writer(response)
    writer.writerow(['run_at', 'engine', 'region', 'group', 'prompt', 'run_number', 'mentioned', 'mentions',
                     'position', 'citations', 'sentiment', 'sentiment_score', 'cited_urls', 'competitors'])
    numbered = qs.annotate(run_number=Window(
        expression=RowNumber(), partition_by=[F('prompt_id')], order_by=F('tracked_at').asc()))
    for run in numbered.order_by('-tracked_at', '-id')[:EXPORT_LIMIT].iterator():
        row = _row(run)
        writer.writerow([
            row['tracked_at'], row['platform'], row['region'], row['group'], row['prompt'], row['run_number'],
            'yes' if row['is_mention'] else 'no', row['total_mentions'], row['position'],
            row['total_citations'], row['sentiment_category'], row['sentiment_score'],
            ' | '.join(str(c) for c in row['citations']),
            ' | '.join(str(c) for c in row['competitors']),
        ])
    return response
