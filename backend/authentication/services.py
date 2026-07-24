"""Client-account lifecycle logic.

Kept out of the views so ``auth_views.py`` (already over the size budget) stays
thin: views parse/serialize, this service owns creation, domain granting,
suspension, token revocation, activity logging, and the welcome email.

All operations are organisation-scoped — a caller can only ever create or touch
clients inside their own organisation.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.db import transaction

from domains.models import DEFAULT_CLIENT_ACCESS_LEVEL, Domain, DomainAccess
from llm_monitor.email_utils import send_mail

from .models import Account, ClientActivityLog

logger = logging.getLogger("security")


def _blacklist_user_tokens(user: Account) -> None:
    """Blacklist every outstanding refresh token for ``user`` so a
    suspended/disabled account cannot mint new access tokens. Combined with the
    per-request status check in StatusCheckingJWTAuthentication, this locks the
    account out on its next request rather than at token expiry."""
    # Imported lazily: token_blacklist tables only exist once that app migrated.
    from rest_framework_simplejwt.token_blacklist.models import (
        BlacklistedToken,
        OutstandingToken,
    )

    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)


def _client_ip(request) -> str | None:
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class ClientDomainError(ValueError):
    """Raised when requested domains don't all belong to the acting org."""


class ClientService:
    """Create and manage client accounts within a single organisation."""

    # -- reads -----------------------------------------------------------------

    @staticmethod
    def list_clients(organisation):
        """All client accounts in the organisation, newest first."""
        return (
            Account.objects.filter(organisation=organisation, role="client")
            .order_by("-created_at")
        )

    @staticmethod
    def granted_domains(client: Account):
        """Active domain grants for a client, as Domain rows."""
        return Domain.objects.filter(
            user_access__user=client,
            user_access__is_active=True,
        ).distinct()

    # -- writes ----------------------------------------------------------------

    @classmethod
    @transaction.atomic
    def create_client(
        cls,
        *,
        acting_user: Account,
        email: str,
        password: str,
        first_name: str = "",
        last_name: str = "",
        domain_ids: list[int] | None = None,
        request=None,
    ) -> Account:
        """Create a client account granted the given domains and email them
        their credentials. Atomic: any failure rolls the whole thing back, and
        the email only fires after a successful commit."""
        organisation = acting_user.organisation
        domains = cls._validate_domains(organisation, domain_ids or [])

        client = Account.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role="client",
            organisation=organisation,
            account_status="active",
            is_active=True,
        )

        cls._grant_domains(client, domains, granted_by=acting_user)

        # Land the client on a domain so their dashboard loads on first login.
        if domains:
            client.active_domain_id = domains[0].id
            client.save(update_fields=["active_domain_id", "modified_at"])

        logger.info(
            "[SECURITY_AUDIT_ADMIN_ACTION] action=create_client actor=%s client=%s domains=%s",
            acting_user.id, client.id, [d.id for d in domains],
        )

        domain_names = [d.name for d in domains]
        transaction.on_commit(
            lambda: cls._send_welcome_email(client, password, domain_names)
        )
        return client

    @classmethod
    @transaction.atomic
    def update_client(
        cls,
        *,
        acting_user: Account,
        client_id: int,
        domain_ids: list[int] | None = None,
        account_status: str | None = None,
        request=None,
    ) -> Account:
        """Update a client's domain grants and/or status.

        Domain grants use soft delete: domains no longer listed have their
        DomainAccess row deactivated (history preserved); newly listed domains
        are (re)activated. Suspending/disabling also blacklists live tokens.
        """
        client = Account.objects.get(
            id=client_id, role="client", organisation=acting_user.organisation
        )

        if domain_ids is not None:
            domains = cls._validate_domains(acting_user.organisation, domain_ids)
            cls._sync_domain_grants(client, domains, granted_by=acting_user)

        if account_status is not None:
            client.account_status = account_status
            client.is_active = account_status == "active"
            client.save(update_fields=["account_status", "is_active", "modified_at"])
            if account_status != "active":
                _blacklist_user_tokens(client)

        logger.info(
            "[SECURITY_AUDIT_ADMIN_ACTION] action=update_client actor=%s client=%s status=%s",
            acting_user.id, client.id, account_status,
        )
        return client

    @classmethod
    @transaction.atomic
    def deactivate_client(cls, *, acting_user: Account, client_id: int) -> Account:
        """Soft-delete: disable the account, revoke all grants, kill live tokens.
        The account and its history rows are retained for auditing/restore."""
        client = Account.objects.get(
            id=client_id, role="client", organisation=acting_user.organisation
        )
        client.account_status = "disabled"
        client.is_active = False
        client.save(update_fields=["account_status", "is_active", "modified_at"])
        DomainAccess.objects.filter(user=client).update(is_active=False)
        _blacklist_user_tokens(client)

        logger.info(
            "[SECURITY_AUDIT_ADMIN_ACTION] action=deactivate_client actor=%s client=%s",
            acting_user.id, client.id,
        )
        return client

    # -- activity log ----------------------------------------------------------

    @staticmethod
    def log_activity(user: Account, action: str, request=None, domain=None, details=None):
        """Best-effort activity record; never breaks the calling flow."""
        try:
            ClientActivityLog.objects.create(
                user=user,
                action=action,
                domain=domain,
                details=details or {},
                ip_address=_client_ip(request),
            )
        except Exception:  # logging must never take down the request
            logger.exception("Failed to write ClientActivityLog for user=%s", getattr(user, "id", None))

    # -- helpers ---------------------------------------------------------------

    @staticmethod
    def _validate_domains(organisation, domain_ids: list[int]) -> list[Domain]:
        if not domain_ids:
            return []
        domains = list(Domain.objects.filter(id__in=domain_ids, organisation=organisation))
        found = {d.id for d in domains}
        missing = set(domain_ids) - found
        if missing:
            raise ClientDomainError(
                f"Domains not found in your organisation: {sorted(missing)}"
            )
        return domains

    @staticmethod
    def _grant_domains(client: Account, domains: list[Domain], *, granted_by: Account) -> None:
        """Grant (or reactivate) access to exactly these domains. Uses
        update_conflicts so re-granting a previously revoked domain updates the
        soft-deleted row instead of raising on the unique (user, domain)."""
        if not domains:
            return
        rows = [
            DomainAccess(
                user=client,
                domain=d,
                granted_by=granted_by,
                access_level=DEFAULT_CLIENT_ACCESS_LEVEL,
                is_active=True,
            )
            for d in domains
        ]
        DomainAccess.objects.bulk_create(
            rows,
            update_conflicts=True,
            unique_fields=["user", "domain"],
            update_fields=["is_active", "granted_by", "access_level"],
        )

    @classmethod
    def _sync_domain_grants(cls, client: Account, domains: list[Domain], *, granted_by: Account) -> None:
        """Make the client's active grants exactly ``domains``: activate the
        listed ones, deactivate the rest (soft delete)."""
        keep_ids = {d.id for d in domains}
        cls._grant_domains(client, domains, granted_by=granted_by)
        DomainAccess.objects.filter(user=client).exclude(domain_id__in=keep_ids).update(
            is_active=False
        )

    @staticmethod
    def _send_welcome_email(client: Account, temp_password: str, domain_names: list[str]) -> None:
        login_url = getattr(settings, "SITE_URL", "").rstrip("/") + "/signin"
        support_email = getattr(settings, "DEFAULT_FROM_EMAIL", "")
        domains_html = "".join(f"<li>{name}</li>" for name in domain_names) or "<li>(none yet)</li>"
        display_name = (client.first_name or client.email).strip()

        html = f"""
        <p>Hi {display_name},</p>
        <p>An account has been created for you to view your AI-visibility dashboards.</p>
        <p><strong>Your domains:</strong></p>
        <ul>{domains_html}</ul>
        <p><strong>Login:</strong> <a href="{login_url}">{login_url}</a><br/>
        <strong>Email:</strong> {client.email}<br/>
        <strong>Temporary password:</strong> {temp_password}</p>
        <p>Please sign in and change your password. Questions? Contact {support_email}.</p>
        """.strip()

        text = (
            f"Hi {display_name},\n\n"
            f"An account has been created for you.\n"
            f"Domains: {', '.join(domain_names) or '(none yet)'}\n"
            f"Login: {login_url}\n"
            f"Email: {client.email}\n"
            f"Temporary password: {temp_password}\n\n"
            f"Please sign in and change your password."
        )
        try:
            send_mail(
                subject="Your dashboard access is ready",
                message=text,
                from_email=support_email or None,
                recipient_list=[client.email],
                fail_silently=True,
                html_message=html,
            )
        except Exception:
            logger.exception("Failed to send client welcome email to %s", client.email)
