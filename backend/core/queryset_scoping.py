"""Domain-scoped queryset helpers.

One implementation of "which domains may this user see", replacing the four
near-identical copies in seo_rankings, keywords, domains, and chat. Everything
is organisation-scoped: even a global-access user only ever sees domains in their
own organisation (tenant isolation is never bypassed here).

Result is memoized on the request so a single request that scopes several
querysets hits the DB once.
"""

from __future__ import annotations

from core.authorization import has_global_domain_access

_CACHE_ATTR = "_accessible_domain_ids_cache"


def get_accessible_domain_ids(user, request=None) -> set[int]:
    """Domain IDs the user may access, always within their own organisation.

    - global-access roles (super_admin, admin): every domain in the org
    - everyone else (user, client): domains granted via active DomainAccess rows

    When ``request`` is supplied the result is cached on it for the request's
    lifetime.
    """
    if request is not None:
        cached = getattr(request, _CACHE_ATTR, None)
        if cached is not None:
            return cached

    # Imported lazily so this pure-logic-adjacent module stays importable without
    # triggering Django app loading at import time.
    from domains.models import Domain, DomainAccess

    org_id = getattr(user, "organisation_id", None)
    if org_id is None:
        domain_ids: set[int] = set()
    elif has_global_domain_access(user):
        domain_ids = set(
            Domain.objects.filter(organisation_id=org_id).values_list("id", flat=True)
        )
    else:
        domain_ids = set(
            DomainAccess.objects.filter(
                user=user,
                is_active=True,
                domain__organisation_id=org_id,
            ).values_list("domain_id", flat=True)
        )

    if request is not None:
        setattr(request, _CACHE_ATTR, domain_ids)
    return domain_ids


def user_can_access_domain(user, domain_id, request=None) -> bool:
    """True when ``domain_id`` is in the user's accessible set. Tolerates a
    string/None domain_id (returns False on anything non-coercible)."""
    if domain_id is None:
        return False
    try:
        domain_id = int(domain_id)
    except (TypeError, ValueError):
        return False
    return domain_id in get_accessible_domain_ids(user, request)


def filter_by_accessible_domains(queryset, user, request=None, domain_field="domain_id"):
    """Restrict ``queryset`` to the user's accessible domains.

    ``domain_field`` is the lookup path to the domain FK on the model, e.g.
    ``"domain_id"`` or ``"prompt__group__domain_id"``.
    """
    allowed = get_accessible_domain_ids(user, request)
    return queryset.filter(**{f"{domain_field}__in": allowed})


class DomainScopedMixin:
    """DRF viewset mixin that scopes ``get_queryset`` to accessible domains.

    Set ``domain_field`` on the viewset when the domain FK is not ``domain_id``.
    """

    domain_field = "domain_id"

    def get_queryset(self):
        queryset = super().get_queryset()
        return filter_by_accessible_domains(
            queryset, self.request.user, self.request, domain_field=self.domain_field
        )
