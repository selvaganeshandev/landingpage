"""DRF permission classes built on the capability layer.

These gate *actions* (can this user manage users? execute scans?). Per-object
domain scoping is enforced separately by the middleware backstop and the
queryset helpers — a permission class here answers "may this role do this kind
of thing at all", not "may they touch this specific domain".
"""

from __future__ import annotations

from rest_framework.permissions import BasePermission

from core.authorization import (
    CAP_EXECUTE_SCANS,
    CAP_MANAGE_DOMAINS,
    CAP_MANAGE_ORG,
    CAP_MANAGE_USERS,
    user_has_capability,
)


class _RequiresCapability(BasePermission):
    """Base: subclass and set ``capability``."""

    capability: str = ""
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view) -> bool:
        return user_has_capability(request.user, self.capability)


class CanManageUsers(_RequiresCapability):
    capability = CAP_MANAGE_USERS
    message = "Only administrators can manage users."


class CanManageDomains(_RequiresCapability):
    capability = CAP_MANAGE_DOMAINS
    message = "Only administrators can manage domains."


class CanManageOrg(_RequiresCapability):
    capability = CAP_MANAGE_ORG
    message = "Only super administrators can manage the organisation."


class CanExecuteScans(_RequiresCapability):
    capability = CAP_EXECUTE_SCANS
    message = "You do not have permission to run scans."


# ---------------------------------------------------------------------------
# Fine-grained action permissions
# ---------------------------------------------------------------------------
# The capability layer above answers "may this role do this kind of thing at
# all". These answer the narrower question "has this specific member been
# granted this specific action", and are backed by the UserPermission grid that
# admins edit on the team-member permissions page.

MODULE_PROMPTS_ADD = "prompts_add"
MODULE_PROMPTS_EDIT = "prompts_edit"
MODULE_PROMPTS_DELETE = "prompts_delete"
MODULE_KEYWORDS_ADD = "keywords_add"
MODULE_KEYWORDS_EDIT = "keywords_edit"
MODULE_KEYWORDS_DELETE = "keywords_delete"


def user_has_module_permission(user, module: str) -> bool:
    """True when ``user`` may perform the action named by ``module``.

    Admins and super admins bypass the grid entirely — they could already do
    every one of these actions, and making them grant themselves rights they
    hold by role would be a regression. Clients are always denied: every unsafe
    method is rejected for them at the middleware anyway, and answering True
    here would imply otherwise. Everyone else needs an explicit grant.

    The active/status gates mirror ``user_has_capability`` so a suspended
    account holding a still-valid JWT is denied at this layer too.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if not getattr(user, "is_active", False):
        return False
    if getattr(user, "account_status", "active") != "active":
        return False

    role = getattr(user, "role", "")
    if role in ("admin", "super_admin"):
        return True
    if role == "client":
        return False

    # Imported lazily: core.permissions is imported during app loading, before
    # the authentication app's models are ready.
    from authentication.models import UserPermission

    return UserPermission.objects.filter(user=user, module=module).exists()


class _RequiresModulePermission(BasePermission):
    """Base for DRF-class use: subclass and set ``module``."""

    module: str = ""

    def has_permission(self, request, view) -> bool:
        return user_has_module_permission(request.user, self.module)


# Client read-only is NOT enforced here. Because almost every write endpoint sets
# its own ``permission_classes = [IsAuthenticated]`` (which would override any
# read-only class we attached individually, and can't be applied to 40+ views
# without one being missed), the rule is enforced fail-closed at a single
# chokepoint: ``llm_monitor.middleware_domain_access.DomainAccessMiddleware``
# rejects every unsafe HTTP method for the client role before the view runs.
