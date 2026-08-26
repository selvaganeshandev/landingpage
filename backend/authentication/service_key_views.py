"""Mint / list / revoke service API keys (Settings > API keys).

Admin-only. Minting returns the plaintext exactly once; only its SHA-256
hash is stored. Each org gets one hidden service account (role 'client' —
org-wide read-only under the existing middleware) that every key of that
org authenticates as.
"""

import hashlib
import logging
import secrets

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Account, ServiceApiKey, ServiceApiKeyUsage, decrypt_value, encrypt_value

logger = logging.getLogger(__name__)

PREFIX = "pmxk_"


def _require_admin(request):
    if getattr(request.user, "role", None) not in ("super_admin", "admin"):
        return Response({"error": "Only admins can manage API keys"},
                        status=status.HTTP_403_FORBIDDEN)
    if request.user.organisation_id is None:
        return Response({"error": "No organisation"}, status=status.HTTP_400_BAD_REQUEST)
    return None


def _service_account(organisation):
    """One hidden read-only member per org; created on first mint."""
    email = f"service+org{organisation.id}@promptmaxx.local"
    account, created = Account.objects.get_or_create(
        email=email,
        defaults={
            "username": email,
            "role": "client",
            "organisation": organisation,
            "is_active": True,
            "is_service_account": True,
            "first_name": "API",
            "last_name": "Service",
        },
    )
    if created:
        account.set_unusable_password()
        account.save(update_fields=["password"])
    return account


def _serialize(key: ServiceApiKey) -> dict:
    return {
        "id": key.id,
        "name": key.name,
        "key_prefix": key.key_prefix,
        "created_at": key.created_at,
        "created_by": getattr(key.created_by, "email", None),
        "expires_at": key.expires_at,
        "revoked": key.revoked,
        "last_used_at": key.last_used_at,
    }


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def service_api_keys(request):
    denied = _require_admin(request)
    if denied:
        return denied
    org = request.user.organisation

    if request.method == "GET":
        keys = ServiceApiKey.objects.filter(organisation=org)
        return Response({"keys": [_serialize(k) for k in keys]})

    name = (request.data.get("name") or "").strip()
    if not name:
        return Response({"error": "name is required"}, status=status.HTTP_400_BAD_REQUEST)

    plaintext = PREFIX + secrets.token_urlsafe(32)
    key = ServiceApiKey.objects.create(
        organisation=org,
        service_account=_service_account(org),
        created_by=request.user,
        name=name,
        key_hash=hashlib.sha256(plaintext.encode()).hexdigest(),
        key_prefix=f"{PREFIX}...{plaintext[-4:]}",
        encrypted_key=encrypt_value(plaintext),
    )
    logger.info("[ServiceApiKey] minted key %s (%s) for org %s by %s",
                key.id, name, org.id, request.user.email)
    return Response({
        "key": _serialize(key),
        "plaintext": plaintext,
        "notice": "Store this key now — it is shown only once.",
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def revoke_service_api_key(request, key_id):
    denied = _require_admin(request)
    if denied:
        return denied
    try:
        key = ServiceApiKey.objects.get(id=key_id, organisation=request.user.organisation)
    except ServiceApiKey.DoesNotExist:
        return Response({"error": "Key not found"}, status=status.HTTP_404_NOT_FOUND)
    if key.revoked:
        return Response({"error": "Already revoked"}, status=status.HTTP_400_BAD_REQUEST)
    key.revoked = True
    key.save(update_fields=["revoked"])
    logger.info("[ServiceApiKey] revoked key %s by %s", key.id, request.user.email)
    return Response({"key": _serialize(key)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reveal_service_api_key(request, key_id):
    """Return the decrypted key so an admin can copy it again.

    Same security posture as the BYOK reveal: admin-only, never logged,
    marked no-store so browsers/proxies don't cache it. Revoked keys are
    not revealable.
    """
    denied = _require_admin(request)
    if denied:
        return denied
    try:
        key = ServiceApiKey.objects.get(id=key_id, organisation=request.user.organisation)
    except ServiceApiKey.DoesNotExist:
        return Response({"error": "Key not found"}, status=status.HTTP_404_NOT_FOUND)
    if key.revoked:
        return Response({"error": "Key is revoked"}, status=status.HTTP_400_BAD_REQUEST)
    if not key.encrypted_key:
        return Response({"error": "This key predates recoverable storage — mint a new one"},
                        status=status.HTTP_400_BAD_REQUEST)
    response = Response({"plaintext": decrypt_value(key.encrypted_key)})
    response["Cache-Control"] = "no-store"
    return response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def service_api_key_usage(request, key_id):
    """Usage box data: what this key has actually been used for."""
    denied = _require_admin(request)
    if denied:
        return denied
    try:
        key = ServiceApiKey.objects.get(id=key_id, organisation=request.user.organisation)
    except ServiceApiKey.DoesNotExist:
        return Response({"error": "Key not found"}, status=status.HTTP_404_NOT_FOUND)

    from datetime import timedelta
    from django.db.models import Count
    from django.utils import timezone

    qs = ServiceApiKeyUsage.objects.filter(key=key)
    day_ago = timezone.now() - timedelta(hours=24)
    top = list(
        qs.values("path").annotate(calls=Count("id")).order_by("-calls")[:5])
    recent = list(
        qs.order_by("-created_at").values("path", "method", "created_at")[:20])
    return Response({
        "total_calls": qs.count(),
        "calls_24h": qs.filter(created_at__gte=day_ago).count(),
        "last_used_at": key.last_used_at,
        "top_endpoints": top,
        "recent": recent,
    })
