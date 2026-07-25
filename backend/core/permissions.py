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


# Client read-only is NOT enforced here. Because almost every write endpoint sets
# its own ``permission_classes = [IsAuthenticated]`` (which would override any
# read-only class we attached individually, and can't be applied to 40+ views
# without one being missed), the rule is enforced fail-closed at a single
# chokepoint: ``llm_monitor.middleware_domain_access.DomainAccessMiddleware``
# rejects every unsafe HTTP method for the client role before the view runs.
