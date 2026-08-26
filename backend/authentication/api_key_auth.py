"""Service API key authentication (Settings > API keys).

Header:  Authorization: Api-Key pmxk_...
Resolves to the key's hidden service account (role 'client'), so
DomainAccessMiddleware org-scoping and the client read-only rule apply
unchanged. Only safe methods will ever succeed with these keys.
"""

import hashlib

from django.utils import timezone
from rest_framework import authentication, exceptions

KEYWORD = "Api-Key"
PREFIX = "pmxk_"


class ApiKeyAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        header = authentication.get_authorization_header(request).decode("utf-8")
        if not header:
            return None
        parts = header.split()
        if len(parts) != 2 or parts[0].lower() != KEYWORD.lower():
            return None  # not ours — let JWT auth try
        plaintext = parts[1]
        if not plaintext.startswith(PREFIX):
            raise exceptions.AuthenticationFailed("Invalid API key.")

        from .models import ServiceApiKey

        digest = hashlib.sha256(plaintext.encode()).hexdigest()
        try:
            key = ServiceApiKey.objects.select_related("service_account").get(
                key_hash=digest)
        except ServiceApiKey.DoesNotExist:
            raise exceptions.AuthenticationFailed("Invalid API key.")
        if key.revoked:
            raise exceptions.AuthenticationFailed("API key revoked.")
        if key.expires_at and key.expires_at < timezone.now():
            raise exceptions.AuthenticationFailed("API key expired.")
        account = key.service_account
        if not account.is_active or getattr(account, "account_status", "active") != "active":
            raise exceptions.AuthenticationFailed("Service account inactive.")

        ServiceApiKey.objects.filter(pk=key.pk).update(last_used_at=timezone.now())
        # The middleware and DRF both run this authenticator on one request —
        # mark the request so usage is logged once, not twice.
        if not getattr(request, "_service_key_usage_logged", False):
            try:
                from .models import ServiceApiKeyUsage
                ServiceApiKeyUsage.objects.create(
                    key=key, path=request.path[:255], method=request.method)
                request._service_key_usage_logged = True
            except Exception:  # usage logging must never break authentication
                pass
        return (account, key)

    def authenticate_header(self, request):
        return KEYWORD
