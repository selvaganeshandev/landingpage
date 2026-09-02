"""Public /v1/ surface for external API consumers (Enque, MCP, scripts).

Deliberately tiny and stable: a workspace picker and a key-verification
endpoint. "Workspace" is the external name for a Domain (a client). The
list reflects exactly what the presented credential may reach — the same
gates the product applies everywhere else (service accounts and
super_admins see the organisation; other users see their DomainAccess
rows).

Workspace ids are the numeric domain ids every existing endpoint already
takes (domain_id / pk); they are stable for the life of the domain.
"""
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from domains.models import Domain

from .throttling import ServiceKeyThrottle, apply_rate_headers


def _reachable_domains(user):
    if user.role == 'super_admin' or getattr(user, 'is_service_account', False):
        return Domain.objects.filter(organisation=user.organisation)
    from domains.models import DomainAccess
    return Domain.objects.filter(
        organisation=user.organisation,
        id__in=DomainAccess.objects.filter(
            user=user, domain__organisation=user.organisation
        ).values_list('domain_id', flat=True),
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([ServiceKeyThrottle])
def workspaces(request):
    """GET /v1/workspaces — the clients this credential may reach.

    {"workspaces": [{"id": 104, "name": "Tanishq USA", "url": "https://..."}]}
    `id` is the domain_id every workspace-scoped endpoint takes.
    """
    rows = _reachable_domains(request.user).order_by('name').values('id', 'name', 'url')
    response = Response({'workspaces': list(rows)})
    return apply_rate_headers(request, response)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([ServiceKeyThrottle])
def me(request):
    """GET /v1/me — who this credential is; lets a consumer verify a key
    at save time without touching any data endpoint.
    """
    user = request.user
    key = request.auth if hasattr(request.auth, 'key_prefix') else None
    payload = {
        'account_id': user.pk,
        'display_name': (
            f"{key.name} ({user.organisation.name})" if key is not None
            else (user.get_full_name() or user.email or str(user.pk))
        ),
        'organisation': {'id': user.organisation_id, 'name': user.organisation.name},
        'read_only': bool(getattr(user, 'is_service_account', False)),
    }
    if key is not None:
        payload['key'] = {
            'name': key.name,
            'prefix': key.key_prefix,
            'expires_at': key.expires_at.isoformat() if key.expires_at else None,
        }
    response = Response(payload)
    return apply_rate_headers(request, response)
