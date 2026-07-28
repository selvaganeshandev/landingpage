"""RBAC & client-login security tests.

Run with:  python backend/manage.py test tests.backend.authentication.test_rbac_security --settings=tests.backend.test_settings

Covers the plan's verification matrix: capability rules, domain scoping, the
fail-closed middleware, immediate suspension, the update_active_domain fix,
soft-delete re-grant safety, and the client-management service. Building the test
DB from migrations also validates the hand-authored 0009/0010 migrations.
"""

from types import SimpleNamespace

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from authentication.models import Account, Organisation
from authentication.services import ClientService, ClientDomainError
from core.authorization import (
    CAP_GLOBAL_DOMAIN_ACCESS,
    CAP_MANAGE_USERS,
    CAP_VIEW_REPORTS,
    has_global_domain_access,
    user_has_capability,
)
from core.queryset_scoping import get_accessible_domain_ids
from domains.models import Domain, DomainAccess


def _fake_user(role="client", account_status="active", is_active=True, is_authenticated=True):
    """Lightweight stand-in for capability unit tests (no DB needed)."""
    return SimpleNamespace(
        is_authenticated=is_authenticated,
        is_active=is_active,
        account_status=account_status,
        role=role,
        organisation_id=1,
    )


class CapabilityTests(TestCase):
    def test_client_can_only_view_reports(self):
        u = _fake_user("client")
        self.assertTrue(user_has_capability(u, CAP_VIEW_REPORTS))
        self.assertFalse(user_has_capability(u, CAP_MANAGE_USERS))
        self.assertFalse(has_global_domain_access(u))

    def test_admin_and_super_admin_are_global(self):
        self.assertTrue(has_global_domain_access(_fake_user("admin")))
        self.assertTrue(has_global_domain_access(_fake_user("super_admin")))

    def test_user_is_domain_scoped(self):
        self.assertFalse(has_global_domain_access(_fake_user("user")))

    def test_suspended_account_denied_everything(self):
        u = _fake_user("admin", account_status="suspended")
        self.assertFalse(user_has_capability(u, CAP_MANAGE_USERS))
        self.assertFalse(user_has_capability(u, CAP_GLOBAL_DOMAIN_ACCESS))

    def test_unauthenticated_denied(self):
        self.assertFalse(user_has_capability(_fake_user(is_authenticated=False), CAP_VIEW_REPORTS))


class RbacSecurityTests(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name="Agency")
        self.other_org = Organisation.objects.create(name="Other Co")

        self.admin = Account.objects.create_user(
            username="admin@a.com", email="admin@a.com", password="pw",
            role="admin", organisation=self.org,
        )
        self.other_admin = Account.objects.create_user(
            username="admin@other.com", email="admin@other.com", password="pw",
            role="admin", organisation=self.other_org,
        )
        self.domain_a = Domain.objects.create(name="A", url="https://a.com", organisation=self.org)
        self.domain_b = Domain.objects.create(name="B", url="https://b.com", organisation=self.org)
        self.other_domain = Domain.objects.create(name="O", url="https://o.com", organisation=self.other_org)

        self.client_user = Account.objects.create_user(
            username="client@a.com", email="client@a.com", password="pw",
            role="client", organisation=self.org,
        )
        DomainAccess.objects.create(
            user=self.client_user, domain=self.domain_a, granted_by=self.admin, is_active=True,
        )

    def _auth(self, user) -> APIClient:
        api = APIClient()
        token = str(RefreshToken.for_user(user).access_token)
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return api

    # -- domain scoping --------------------------------------------------------

    def test_accessible_domain_ids_scoped_for_client(self):
        self.assertEqual(get_accessible_domain_ids(self.client_user), {self.domain_a.id})

    def test_accessible_domain_ids_global_for_admin(self):
        self.assertEqual(
            get_accessible_domain_ids(self.admin), {self.domain_a.id, self.domain_b.id}
        )

    def test_cross_org_isolation(self):
        # Other org's admin sees only their own domain, never this org's.
        self.assertEqual(get_accessible_domain_ids(self.other_admin), {self.other_domain.id})

    def test_client_domain_list_shows_only_granted(self):
        resp = self._auth(self.client_user).get("/domains/")
        self.assertEqual(resp.status_code, 200)
        ids = {d["id"] for d in resp.json()["domains"]}
        self.assertEqual(ids, {self.domain_a.id})

    # -- middleware backstop ---------------------------------------------------

    def test_client_foreign_domain_query_param_404(self):
        resp = self._auth(self.client_user).get(f"/alerts/alerts/?domain_id={self.domain_b.id}")
        self.assertEqual(resp.status_code, 404)

    def test_client_foreign_domain_detail_404(self):
        resp = self._auth(self.client_user).get(f"/domains/{self.domain_b.id}/")
        self.assertEqual(resp.status_code, 404)

    def test_client_own_domain_detail_allowed(self):
        resp = self._auth(self.client_user).get(f"/domains/{self.domain_a.id}/")
        self.assertEqual(resp.status_code, 200)

    def test_admin_reaches_any_org_domain(self):
        resp = self._auth(self.admin).get(f"/domains/{self.domain_b.id}/")
        self.assertEqual(resp.status_code, 200)

    # -- update_active_domain --------------------------------------------------

    def test_client_cannot_pin_foreign_domain(self):
        resp = self._auth(self.client_user).patch(
            "/auth/active-domain/", {"domain_id": self.domain_b.id}, format="json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_client_can_pin_own_domain(self):
        resp = self._auth(self.client_user).patch(
            "/auth/active-domain/", {"domain_id": self.domain_a.id}, format="json"
        )
        self.assertEqual(resp.status_code, 200)

    # -- client read-only write block ------------------------------------------

    def test_client_post_blocked_on_own_domain(self):
        # A write to a granted domain is still rejected — read-only is by role,
        # not by domain. The 403 fires in middleware before the serializer runs,
        # so an empty body is enough to prove the block.
        resp = self._auth(self.client_user).post(
            f"/alerts/alerts/?domain_id={self.domain_a.id}", {}, format="json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_client_delete_blocked(self):
        resp = self._auth(self.client_user).delete(f"/domains/{self.domain_a.id}/")
        self.assertEqual(resp.status_code, 403)

    def test_client_read_still_allowed_on_writable_viewset(self):
        resp = self._auth(self.client_user).get("/alerts/alerts/")
        self.assertEqual(resp.status_code, 200)

    def test_client_logout_not_blocked(self):
        # Exempt session action: the read-only guard must not 403 it.
        resp = self._auth(self.client_user).post("/auth/logout/", {}, format="json")
        self.assertNotEqual(resp.status_code, 403)

    def test_admin_write_not_blocked_by_readonly_guard(self):
        # The guard targets only the client role; an admin write is untouched by
        # it (any non-403 status proves the middleware let it through).
        resp = self._auth(self.admin).post(
            f"/alerts/alerts/?domain_id={self.domain_a.id}", {}, format="json"
        )
        self.assertNotEqual(resp.status_code, 403)

    # -- suspension ------------------------------------------------------------

    def test_suspended_login_rejected(self):
        Account.objects.filter(id=self.client_user.id).update(account_status="suspended")
        resp = APIClient().post(
            "/auth/login/", {"email": "client@a.com", "password": "pw"}, format="json"
        )
        self.assertEqual(resp.status_code, 401)

    def test_suspended_live_token_rejected(self):
        api = self._auth(self.client_user)  # token minted while active
        Account.objects.filter(id=self.client_user.id).update(account_status="suspended")
        resp = api.get("/auth/profile/")
        self.assertEqual(resp.status_code, 401)

    # -- grant-leak invariant --------------------------------------------------

    def test_client_excluded_from_member_autogrant_queryset(self):
        members = Account.objects.filter(
            organisation=self.org, is_active=True
        ).exclude(role="client")
        self.assertIn(self.admin, members)
        self.assertNotIn(self.client_user, members)


class ClientServiceTests(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name="Agency")
        self.other_org = Organisation.objects.create(name="Other Co")
        self.admin = Account.objects.create_user(
            username="admin@a.com", email="admin@a.com", password="pw",
            role="admin", organisation=self.org,
        )
        self.domain_a = Domain.objects.create(name="A", url="https://a.com", organisation=self.org)
        self.domain_b = Domain.objects.create(name="B", url="https://b.com", organisation=self.org)
        self.foreign = Domain.objects.create(name="O", url="https://o.com", organisation=self.other_org)

    def test_create_client_grants_only_listed_domains(self):
        client = ClientService.create_client(
            acting_user=self.admin, email="c@a.com", password="pw",
            domain_ids=[self.domain_a.id],
        )
        self.assertEqual(client.role, "client")
        granted = set(ClientService.granted_domains(client).values_list("id", flat=True))
        self.assertEqual(granted, {self.domain_a.id})
        self.assertEqual(client.active_domain_id, self.domain_a.id)

    def test_create_client_rejects_foreign_domain(self):
        with self.assertRaises(ClientDomainError):
            ClientService.create_client(
                acting_user=self.admin, email="c@a.com", password="pw",
                domain_ids=[self.foreign.id],
            )

    def test_revoke_then_regrant_no_integrity_error(self):
        client = ClientService.create_client(
            acting_user=self.admin, email="c@a.com", password="pw",
            domain_ids=[self.domain_a.id, self.domain_b.id],
        )
        # Revoke B
        ClientService.update_client(
            acting_user=self.admin, client_id=client.id, domain_ids=[self.domain_a.id],
        )
        self.assertFalse(
            DomainAccess.objects.get(user=client, domain=self.domain_b).is_active
        )
        # Re-grant B — must not raise on the unique (user, domain) row
        ClientService.update_client(
            acting_user=self.admin, client_id=client.id,
            domain_ids=[self.domain_a.id, self.domain_b.id],
        )
        self.assertTrue(
            DomainAccess.objects.get(user=client, domain=self.domain_b).is_active
        )

    def test_deactivate_client_disables_and_revokes(self):
        client = ClientService.create_client(
            acting_user=self.admin, email="c@a.com", password="pw",
            domain_ids=[self.domain_a.id],
        )
        ClientService.deactivate_client(acting_user=self.admin, client_id=client.id)
        client.refresh_from_db()
        self.assertEqual(client.account_status, "disabled")
        self.assertFalse(client.is_active)
        self.assertFalse(
            DomainAccess.objects.filter(user=client, is_active=True).exists()
        )
