"""Capability-based authorization for RBAC.

Single source of truth for what each role may do. Views and permission classes
ask ``user_has_capability`` / ``has_global_domain_access`` instead of hardcoding
role-name checks, so adding or re-scoping a role happens in one place.

Pure logic — no Django ORM, no DB access. Safe to import anywhere.
"""

from __future__ import annotations

# Capabilities are coarse-grained verbs, not per-module permissions. The 24-module
# UserPermission grid is a separate, finer layer applied on top of these.
CAP_MANAGE_ORG = "manage_org"
CAP_MANAGE_USERS = "manage_users"
CAP_MANAGE_DOMAINS = "manage_domains"
CAP_EXECUTE_SCANS = "execute_scans"
CAP_VIEW_REPORTS = "view_reports"
# Holders see every domain in their organisation; non-holders are limited to the
# domains explicitly granted to them via DomainAccess.
CAP_GLOBAL_DOMAIN_ACCESS = "global_domain_access"

ROLE_CAPABILITIES: dict[str, frozenset[str]] = {
    "super_admin": frozenset({
        CAP_MANAGE_ORG,
        CAP_MANAGE_USERS,
        CAP_MANAGE_DOMAINS,
        CAP_EXECUTE_SCANS,
        CAP_VIEW_REPORTS,
        CAP_GLOBAL_DOMAIN_ACCESS,
    }),
    "admin": frozenset({
        CAP_MANAGE_USERS,
        CAP_MANAGE_DOMAINS,
        CAP_EXECUTE_SCANS,
        CAP_VIEW_REPORTS,
        CAP_GLOBAL_DOMAIN_ACCESS,
    }),
    "user": frozenset({
        CAP_EXECUTE_SCANS,
        CAP_VIEW_REPORTS,
    }),
    "client": frozenset({
        CAP_VIEW_REPORTS,
    }),
}


def user_has_capability(user, capability: str) -> bool:
    """True only for an authenticated, active, non-suspended user whose role
    grants ``capability``.

    The ``account_status`` gate means a suspended/disabled account is denied every
    capability even while holding a still-valid JWT — the authentication layer
    (see the custom JWTAuthentication) rejects such tokens, and this is the
    defense-in-depth check at the authorization layer.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if not getattr(user, "is_active", False):
        return False
    if getattr(user, "account_status", "active") != "active":
        return False
    return capability in ROLE_CAPABILITIES.get(getattr(user, "role", ""), frozenset())


def has_global_domain_access(user) -> bool:
    """True when the user may see every domain in their organisation.

    The one predicate all domain scoping is expressed in — no scoping code checks
    ``role == 'super_admin'`` directly.
    """
    return user_has_capability(user, CAP_GLOBAL_DOMAIN_ACCESS)
