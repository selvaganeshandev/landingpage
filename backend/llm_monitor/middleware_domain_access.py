"""Fail-closed domain-access backstop.

The 18 DRF ViewSets can be scoped with ``DomainScopedMixin``, but 157
function-based ``@api_view`` endpoints cannot — and any one left unscoped by
hand would leak another domain's data. This middleware is the safety net: for
any authenticated request that carries a domain id it hasn't been granted, it
returns 404 before the view runs. Views that already check agree with it; views
that forgot to check are covered anyway.

The same chokepoint enforces the **client read-only** rule. The ``client`` role
holds only the ``view_reports`` capability, but the vast majority of write
endpoints (every ``ModelViewSet`` plus the function-based ``@api_view`` writes)
are guarded solely by ``IsAuthenticated`` — no per-view read-only check was ever
wired up. Rather than annotate ~40 endpoints by hand (and hope none is missed),
this middleware rejects every unsafe HTTP method for a client in one place, so a
client physically cannot mutate anything regardless of which view it reaches.

Design constraints (see plan section 4):

* Reads ``domain_id`` from the **query string and URL kwargs only, never the
  request body** — touching the body in ``process_view`` (which runs before DRF
  parses the request) breaks DRF's own parsing. Read requests carry domain_id in
  the query/URL; body-based domain_id only appears on writes, and those are
  scoped by the view after DRF has parsed.
* Resolves the JWT itself. At ``process_view`` time ``request.user`` is Django's
  *session* user — ``AnonymousUser`` for a JWT bearer request, because DRF runs
  its authentication inside the view. Without resolving the token here the
  backstop would treat every API call as anonymous and skip enforcement.
* Returns 404 (not 403) so an out-of-scope domain id is indistinguishable from a
  non-existent one — object-existence privacy.
"""

from __future__ import annotations

import logging

from django.http import JsonResponse

from core.queryset_scoping import get_accessible_domain_ids

logger = logging.getLogger("security")

# Under this prefix a ``<int:pk>`` URL kwarg is a Domain primary key. Elsewhere
# (keywords, seo) ``pk`` is a different model's id, so it must not be treated as
# a domain id.
_DOMAINS_URL_PREFIX = "/domains/"

# HTTP methods that never mutate state. A client may call these freely; anything
# else is a write and is rejected for the client role.
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

# Write endpoints a read-only client must still reach to use the app at all:
# ending their own session, refreshing an expired access token, and pinning
# which of their granted domains is active (its own view already 403s a foreign
# domain — see ``update_active_domain`` and ``test_client_can_pin_own_domain``).
# These are session/UI-state actions, not data mutations.
_CLIENT_WRITE_EXEMPT_PATHS = frozenset({
    "/auth/logout/",
    "/auth/token/refresh/",
    "/auth/active-domain/",
    # Running an audit is open to anonymous visitors (AllowAny); a service
    # API key resolves to a client-role account and must not be treated more
    # strictly than a stranger. The view applies its own caps and flag.
    "/audits/",
})


class DomainAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        user = self._resolve_user(request)
        if user is None or not getattr(user, "is_authenticated", False):
            # Unauthenticated / AllowAny — let DRF handle auth and permissions.
            return None

        write_denied = self._client_write_denied(request, user)
        if write_denied is not None:
            return write_denied

        candidate_ids = self._candidate_domain_ids(request, view_kwargs)
        if not candidate_ids:
            return None

        accessible = get_accessible_domain_ids(user, request)
        for domain_id in candidate_ids:
            if domain_id not in accessible:
                logger.warning(
                    "[SECURITY_DENIED] user=%s org=%s domain=%s method=%s path=%s",
                    getattr(user, "id", None),
                    getattr(user, "organisation_id", None),
                    domain_id,
                    request.method,
                    request.path,
                )
                return JsonResponse({"error": "Domain not found"}, status=404)
        return None

    # -- helpers ---------------------------------------------------------------

    def _client_write_denied(self, request, user):
        """Return a 403 response when a client attempts a write, else ``None``.

        Read-only is enforced by role here rather than per-view: the client role
        may only ever issue safe methods, apart from the session/UI-state
        endpoints in ``_CLIENT_WRITE_EXEMPT_PATHS``.
        """
        if getattr(user, "role", None) != "client":
            return None
        if request.method in _SAFE_METHODS:
            return None
        if request.path in _CLIENT_WRITE_EXEMPT_PATHS:
            return None

        logger.warning(
            "[SECURITY_DENIED] client write blocked user=%s org=%s method=%s path=%s",
            getattr(user, "id", None),
            getattr(user, "organisation_id", None),
            request.method,
            request.path,
        )
        return JsonResponse(
            {"error": "Client accounts have read-only access."}, status=403
        )

    def _resolve_user(self, request):
        """Return the acting user, resolving a JWT bearer token if Django's
        session-based ``request.user`` is anonymous."""
        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            return user

        auth_header = request.META.get("HTTP_AUTHORIZATION", "")

        if auth_header.lower().startswith("api-key "):
            # Service API key (Settings > API keys): resolve so the client
            # write-block and the domain 404 backstop apply to keys too.
            from authentication.api_key_auth import ApiKeyAuthentication
            try:
                result = ApiKeyAuthentication().authenticate(request)
            except Exception:
                return None  # invalid key: let DRF return the 401
            return result[0] if result else None

        if not auth_header.startswith("Bearer "):
            return None

        # Imported lazily to avoid import cycles at Django startup.
        from authentication.jwt_auth import StatusCheckingJWTAuthentication

        try:
            result = StatusCheckingJWTAuthentication().authenticate(request)
        except Exception:
            # Invalid or suspended token: don't 404 here — let the view's own DRF
            # authentication produce the correct 401.
            return None
        if result is None:
            return None
        return result[0]

    def _candidate_domain_ids(self, request, view_kwargs) -> set[int]:
        ids: set[int] = set()
        self._add_int(ids, view_kwargs.get("domain_id"))
        if request.path.startswith(_DOMAINS_URL_PREFIX):
            self._add_int(ids, view_kwargs.get("pk"))
        # Query string only — never request.POST / request.body.
        self._add_int(ids, request.GET.get("domain_id"))
        return ids

    @staticmethod
    def _add_int(ids: set[int], value) -> None:
        if value is None:
            return
        try:
            ids.add(int(value))
        except (TypeError, ValueError):
            pass
