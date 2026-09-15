"""Audit Engine endpoints.

    POST   /audits/                 public   run an audit for a URL (rate-limited)
    GET    /audits/                 auth     the leads table
    GET    /audits/config/          auth     feature flags the UI keys off
    GET    /audits/public/<token>/  public   progress, then the report
    GET    /audits/public/<token>/pdf/  public   the report as a PDF download (DONE only)
    GET    /audits/<id>/pdf/        auth     same PDF for the leads table
    GET    /audits/<id>/            auth     everything stored for one audit
    DELETE /audits/<id>/            admin    remove an audit and its evidence
    POST   /audits/<id>/claim/      admin    turn it into a tracked Domain
    POST   /audits/claim/<token>/   admin    same, from the public report page (token = credential)
    POST   /audits/<id>/rerun/      admin    resume a failed audit

Visibility: audits have no organisation (most come from strangers on the
landing page), so the leads table is a super_admin view. Organisation admins
see only what their own people ran or claimed. Everyone else gets 403.
"""
import logging

from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from llm_monitor.pagination import CustomPageNumberPagination

from . import services
from .models import Audit
from .serializers import (
    AuditCreateSerializer, AuditDetailSerializer, AuditListSerializer, PublicAuditSerializer,
)

logger = logging.getLogger(__name__)

ADMIN_ROLES = ('admin', 'super_admin')


def _refused(exc):
    body = {'error': exc.message, **exc.extra}
    return Response(body, status=exc.status)


def _visible_audits(user):
    """None when the user may not see the leads table at all."""
    role = getattr(user, 'role', '')
    if role == 'super_admin':
        return Audit.objects.all()
    if role == 'admin':
        org = getattr(user, 'organisation', None)
        if org is None:
            return Audit.objects.none()
        return Audit.objects.filter(
            Q(requested_by__organisation=org) | Q(claimed_domain__organisation=org)
        ).distinct()
    return None


def _public_urls(request, audit):
    base = request.build_absolute_uri('/').rstrip('/')
    return {
        'status_url': f'{base}/audits/public/{audit.public_token}/',
        'public_token': audit.public_token,
    }


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def audit_list_create(request):
    if request.method == 'POST':
        return _create(request)

    if not request.user or not request.user.is_authenticated:
        return Response({'detail': 'Authentication credentials were not provided.'}, status=status.HTTP_401_UNAUTHORIZED)
    qs = _visible_audits(request.user)
    if qs is None:
        return Response({'error': 'You do not have access to audits.'}, status=status.HTTP_403_FORBIDDEN)

    qs = qs.select_related('requested_by', 'claimed_domain')
    source = request.query_params.get('source')
    if source:
        qs = qs.filter(source=source)
    audit_status = request.query_params.get('status')
    if audit_status:
        qs = qs.filter(status=audit_status)
    geo_stage = request.query_params.get('geo_stage')
    if geo_stage:
        qs = qs.filter(geo_stage=geo_stage)
    claimed = request.query_params.get('claimed')
    if claimed in ('true', '1'):
        qs = qs.filter(claimed_domain__isnull=False)
    elif claimed in ('false', '0'):
        qs = qs.filter(claimed_domain__isnull=True)
    search = (request.query_params.get('search') or '').strip()
    if search:
        qs = qs.filter(Q(host__icontains=search) | Q(brand_name__icontains=search) | Q(requester_email__icontains=search))
    ordering = request.query_params.get('ordering') or '-created_at'
    if ordering.lstrip('-') in ('created_at', 'geo_score', 'opens', 'completed_at', 'host'):
        qs = qs.order_by(ordering)

    paginator = CustomPageNumberPagination()
    page = paginator.paginate_queryset(qs, request)
    return paginator.get_paginated_response(AuditListSerializer(page, many=True).data)


def _create(request):
    form = AuditCreateSerializer(data=request.data)
    if not form.is_valid():
        return Response({'error': 'Enter a valid website address.', 'details': form.errors}, status=status.HTTP_400_BAD_REQUEST)
    data = form.validated_data
    user = request.user if request.user and request.user.is_authenticated else None
    # ApiKeyAuthentication sets request.auth to the ServiceApiKey row.
    via_api_key = user is not None and getattr(getattr(request, 'auth', None), 'key_prefix', None) is not None
    try:
        audit, reused = services.create_audit(
            data['url'], country=data['country'], user=user, email=data['email'],
            ip=services.client_ip(request), force=data['force'], via_api_key=via_api_key,
        )
    except services.AuditRefused as exc:
        return _refused(exc)
    payload = {
        'id': audit.pk, 'host': audit.host, 'status': audit.status, 'reused': reused,
        **_public_urls(request, audit),
    }
    if audit.status == 'FAIL':
        # Dispatch failed synchronously; say so rather than returning a row the
        # visitor will poll forever.
        return Response({**payload, 'error': 'The audit engine is unavailable right now.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response(payload, status=status.HTTP_200_OK if reused else status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def audit_config(request):
    from django.conf import settings
    return Response({
        'enabled': services.enabled(),
        'engines': list(getattr(settings, 'AUDIT_ENGINES', [])),
        'prompt_count': int(getattr(settings, 'AUDIT_PROMPT_COUNT', 12)),
        'seo_enabled': bool(getattr(settings, 'AUDIT_SEO_ENABLED', False)),
        'keyword_count': int(getattr(settings, 'AUDIT_KEYWORD_COUNT', 50)),
        'public_ttl_days': int(getattr(settings, 'AUDIT_PUBLIC_TTL_DAYS', 30)),
        'can_manage': getattr(request.user, 'role', '') in ADMIN_ROLES,
        'can_list': _visible_audits(request.user) is not None,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def audit_public(request, token):
    audit = get_object_or_404(Audit, public_token=token)
    if audit.is_expired:
        return Response({'error': 'This audit link has expired.'}, status=status.HTTP_404_NOT_FOUND)
    if audit.status == 'DONE':
        audit.record_open()
        audit.refresh_from_db(fields=['opens', 'last_opened_at'])
        try:
            from .notifications import maybe_alert_warm_lead
            maybe_alert_warm_lead(audit)
        except Exception as exc:  # noqa: BLE001 - never let mail break the public page
            logger.warning('[Audit] warm-lead alert failed for audit %s: %s', audit.pk, exc)
    return Response(PublicAuditSerializer(audit).data)


def _pdf_response(audit):
    from .pdf import build_audit_pdf
    if audit.status != 'DONE':
        return Response({'error': 'The audit has not finished yet.'}, status=status.HTTP_409_CONFLICT)
    try:
        data = build_audit_pdf(audit)
    except Exception as exc:  # noqa: BLE001 - a rendering bug must not 500 the page
        logger.exception('[Audit] PDF build failed for audit %s', audit.pk)
        return Response({'error': f'Could not build the PDF: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    safe = ''.join(ch if ch.isalnum() or ch in '-._' else '-' for ch in (audit.host or 'audit'))
    resp = HttpResponse(data, content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="promptmaxx-audit-{safe}.pdf"'
    resp['Content-Length'] = str(len(data))
    return resp


@api_view(['GET'])
@permission_classes([AllowAny])
def audit_public_pdf(request, token):
    audit = get_object_or_404(Audit, public_token=token)
    if audit.is_expired:
        return Response({'error': 'This audit link has expired.'}, status=status.HTTP_404_NOT_FOUND)
    return _pdf_response(audit)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def audit_pdf(request, pk):
    audit, err = _owned_audit(request, pk)
    if err:
        return err
    return _pdf_response(audit)


def _issues_csv_response(audit):
    """Every technical-SEO issue as one CSV row per affected URL - the "send to the developer" list."""
    import csv
    import io as _io
    if audit.status != 'DONE':
        return Response({'error': 'The audit has not finished yet.'}, status=status.HTTP_409_CONFLICT)
    crawl = (audit.report or {}).get('crawl') or {}
    issues = crawl.get('technical_issues')
    if issues is None:
        return Response({'error': 'This audit has no technical SEO issue list.'}, status=status.HTTP_404_NOT_FOUND)
    buf = _io.StringIO()
    w = csv.writer(buf)
    w.writerow(['severity', 'issue', 'url', 'action', 'why', 'how_to_fix', 'pages_affected', 'of'])
    for i in issues:
        urls = i.get('urls') or i.get('examples') or ['']
        for u in urls:
            w.writerow([i.get('severity', ''), i.get('label', ''), u, i.get('action', ''), i.get('fix', ''), i.get('snippet', ''), i.get('count', ''), i.get('of', '')])
    safe = ''.join(ch if ch.isalnum() or ch in '-._' else '-' for ch in (audit.host or 'audit'))
    resp = HttpResponse(buf.getvalue().encode('utf-8-sig'), content_type='text/csv; charset=utf-8')
    resp['Content-Disposition'] = f'attachment; filename="promptmaxx-issues-{safe}.csv"'
    return resp


@api_view(['GET'])
@permission_classes([AllowAny])
def audit_public_issues_csv(request, token):
    audit = get_object_or_404(Audit, public_token=token)
    if audit.is_expired:
        return Response({'error': 'This audit link has expired.'}, status=status.HTTP_404_NOT_FOUND)
    return _issues_csv_response(audit)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def audit_issues_csv(request, pk):
    audit, err = _owned_audit(request, pk)
    if err:
        return err
    return _issues_csv_response(audit)


def _owned_audit(request, pk):
    qs = _visible_audits(request.user)
    if qs is None:
        return None, Response({'error': 'You do not have access to audits.'}, status=status.HTTP_403_FORBIDDEN)
    audit = qs.filter(pk=pk).select_related('requested_by', 'claimed_domain').first()
    if audit is None:
        return None, Response({'error': 'Audit not found.'}, status=status.HTTP_404_NOT_FOUND)
    return audit, None


@api_view(['GET', 'DELETE'])
@permission_classes([IsAuthenticated])
def audit_detail(request, pk):
    audit, err = _owned_audit(request, pk)
    if err:
        return err
    if request.method == 'DELETE':
        if getattr(request.user, 'role', '') not in ADMIN_ROLES:
            return Response({'error': 'Only administrators can delete audits.'}, status=status.HTTP_403_FORBIDDEN)
        audit.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    data = AuditDetailSerializer(audit).data
    data.update(_public_urls(request, audit))
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def audit_claim(request, pk):
    if getattr(request.user, 'role', '') not in ADMIN_ROLES:
        return Response({'error': 'Only organization administrators can add domains'}, status=status.HTTP_403_FORBIDDEN)
    audit, err = _owned_audit(request, pk)
    if err:
        return err
    try:
        domain = services.claim(audit, request.user)
    except services.AuditRefused as exc:
        return _refused(exc)
    return Response({
        'success': True,
        'message': 'Domain created from audit',
        'audit': AuditListSerializer(audit).data,
        'domain': {
            'id': domain.id, 'name': domain.name, 'url': domain.url,
            'country': domain.country, 'processing_status': domain.processing_status,
        },
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def audit_claim_by_token(request, token):
    """Claim from the public report page.

    A prospect who ran an audit on the landing page, then signed up, holds the
    public link but is not in the leads table's visible set (the audit has no
    organisation yet). The token is the credential here, exactly as it is for
    reading the report — so any admin holding it may claim it into their org.
    """
    if getattr(request.user, 'role', '') not in ADMIN_ROLES:
        return Response({'error': 'Only organization administrators can add domains'}, status=status.HTTP_403_FORBIDDEN)
    audit = get_object_or_404(Audit, public_token=token)
    if audit.is_expired:
        return Response({'error': 'This audit link has expired.'}, status=status.HTTP_404_NOT_FOUND)
    try:
        domain = services.claim(audit, request.user)
    except services.AuditRefused as exc:
        body = {'error': exc.message, **exc.extra, 'audit_id': audit.pk}
        return Response(body, status=exc.status)
    return Response({
        'success': True,
        'message': 'Domain created from audit',
        'audit': AuditListSerializer(audit).data,
        'domain': {
            'id': domain.id, 'name': domain.name, 'url': domain.url,
            'country': domain.country, 'processing_status': domain.processing_status,
        },
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def audit_rerun(request, pk):
    if getattr(request.user, 'role', '') not in ADMIN_ROLES:
        return Response({'error': 'Only administrators can re-run audits.'}, status=status.HTTP_403_FORBIDDEN)
    audit, err = _owned_audit(request, pk)
    if err:
        return err
    try:
        dispatched = services.rerun(audit)
    except services.AuditRefused as exc:
        return _refused(exc)
    audit.refresh_from_db()
    if not dispatched:
        return Response({'error': 'The audit engine is unavailable right now.', 'audit': AuditListSerializer(audit).data},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response({'success': True, 'audit': AuditListSerializer(audit).data})
