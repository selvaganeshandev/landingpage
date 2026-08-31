"""Token-consumption reporting for the Settings > API Keys screen.

    GET /content/token-usage/?days=30

Aggregates ``ContentGenerationUsage`` for the caller's organisation into the
shapes the UI needs: a headline total, a breakdown per LLM, a breakdown per
feature, and a daily series.

Two things this deliberately does NOT do:

* It does not read OpenRouter's ``/activity`` endpoint — that requires a
  management/provisioning key, not the normal API key, and returns 403 with a
  standard one. Our own recorded rows are the source of truth.
* It does not invent a cost for Gemini. Google reports token counts and no
  price, so those rows carry cost=NULL and are reported as "not priced" rather
  than as zero, which would understate the tightest quota in the system.
"""

import logging
from datetime import timedelta

from django.db.models import Count, DecimalField, F, Q, Sum
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ContentGenerationUsage

logger = logging.getLogger(__name__)

MAX_DAYS = 365
DEFAULT_DAYS = 30


def _int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _decimal_or_none(value):
    """Serialise a Decimal for JSON, preserving the null/zero distinction."""
    return None if value is None else float(value)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def token_usage(request):
    """Token consumption for this organisation, grouped for the API Keys screen."""
    days = _int(request.query_params.get('days'), DEFAULT_DAYS)
    days = max(1, min(days, MAX_DAYS))

    since = timezone.now() - timedelta(days=days)
    org = request.user.organisation
    if org is None:
        return Response(
            {'status': 'error', 'message': 'No organisation on this account.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    rows = ContentGenerationUsage.objects.filter(
        organisation=org, created_at__gte=since,
    )

    provider_filter = (request.query_params.get('provider') or '').strip()
    if provider_filter:
        rows = rows.filter(provider=provider_filter)

    model_filter = (request.query_params.get('model') or '').strip()
    if model_filter:
        rows = rows.filter(model_name=model_filter)

    zero = DecimalField(max_digits=14, decimal_places=8)

    def totals(queryset):
        agg = queryset.aggregate(
            calls=Count('id'),
            input_tokens=Coalesce(Sum('input_tokens'), 0),
            output_tokens=Coalesce(Sum('output_tokens'), 0),
            total_tokens=Coalesce(Sum('total_tokens'), 0),
            cached_tokens=Coalesce(Sum('cached_tokens'), 0),
            # Sum only the priced rows. Gemini's NULLs are excluded rather than
            # counted as zero, and reported separately below.
            cost=Sum('cost'),
            failed=Count('id', filter=Q(status='failed')),
            byok_calls=Count('id', filter=Q(is_byok=True)),
        )
        agg['cost'] = _decimal_or_none(agg['cost'])
        return agg

    summary = totals(rows)
    # How much of the window is unpriced, so the UI can say so rather than
    # implying the cost figure covers everything.
    summary['unpriced_calls'] = rows.filter(cost__isnull=True).count()

    by_model = []
    for entry in (
        rows.values('model_name', 'provider')
        .annotate(
            calls=Count('id'),
            input_tokens=Coalesce(Sum('input_tokens'), 0),
            output_tokens=Coalesce(Sum('output_tokens'), 0),
            total_tokens=Coalesce(Sum('total_tokens'), 0),
            cached_tokens=Coalesce(Sum('cached_tokens'), 0),
            cost=Sum('cost'),
            failed=Count('id', filter=Q(status='failed')),
        )
        .order_by('-total_tokens')
    ):
        entry['cost'] = _decimal_or_none(entry['cost'])
        # Gemini is billed against a request quota, not dollars. Flagging it
        # lets the UI show "not priced" instead of a misleading $0.00.
        entry['priced'] = entry['provider'] != 'gemini'
        by_model.append(entry)

    by_feature = [
        {**e, 'cost': _decimal_or_none(e['cost'])}
        for e in rows.values('feature')
        .annotate(
            calls=Count('id'),
            total_tokens=Coalesce(Sum('total_tokens'), 0),
            cost=Sum('cost'),
        )
        .order_by('-total_tokens')
    ]

    daily = [
        {
            'date': e['day'].isoformat() if e['day'] else None,
            'calls': e['calls'],
            'total_tokens': e['total_tokens'],
            'cost': _decimal_or_none(e['cost']),
        }
        for e in rows.annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(
            calls=Count('id'),
            total_tokens=Coalesce(Sum('total_tokens'), 0),
            cost=Sum('cost'),
        )
        .order_by('day')
    ]

    # Live OpenRouter balance, so the screen can reconcile what we recorded
    # against what the provider actually charged. Never fatal.
    balance = None
    try:
        import requests as http

        from django.conf import settings as dj_settings

        key = None
        encrypted = getattr(org, 'openrouter_api_key', None)
        if encrypted:
            from authentication.models import decrypt_value
            candidate = decrypt_value(encrypted)
            key = candidate if candidate and candidate != encrypted else None
        key = key or getattr(dj_settings, 'OPENROUTER_API_KEY', None)

        if key:
            resp = http.get(
                'https://openrouter.ai/api/v1/credits',
                headers={'Authorization': f'Bearer {key}'},
                timeout=10,
            )
            if resp.ok:
                payload = (resp.json() or {}).get('data') or {}
                granted = float(payload.get('total_credits') or 0)
                used = float(payload.get('total_usage') or 0)
                balance = {
                    'granted': granted,
                    'used': used,
                    'remaining': granted - used,
                }
    except Exception as exc:  # noqa: BLE001
        logger.warning('Could not fetch OpenRouter balance: %s', exc)

    response = Response({
        'status': 'success',
        'data': {
            'days': days,
            'since': since.isoformat(),
            'summary': summary,
            'by_model': by_model,
            'by_feature': by_feature,
            'daily': daily,
            'openrouter_balance': balance,
            # Told plainly so nobody reads these figures as complete: only
            # instrumented call sites appear here.
            'coverage_note': (
                'Covers content generation and image generation. Engine-side '
                'platform measurement is not yet instrumented, so figures are a '
                'lower bound on total consumption.'
            ),
        },
    })
    response['Cache-Control'] = 'no-store'
    return response
