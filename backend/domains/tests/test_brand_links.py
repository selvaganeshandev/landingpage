"""
Comprehensive tests for the Brand Links module.

Covers:
  1. BrandLink model creation and constraints (unique_together, max 20 per domain)
  2. BrandLinkChunk creation via _create_brand_link_chunks
  3. Brand Links API endpoints (GET list, POST create, GET detail, PATCH update, DELETE)
  4. Validation: missing platform, missing URL, invalid platform, duplicate URL
  5. Reference document endpoints still work (GET list, POST text note, DELETE)
  6. Domain endpoints still work (GET detail, PATCH / PUT update)
"""

from unittest.mock import patch

from django.db import IntegrityError
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from authentication.models import Account, Organisation
from domains.models import BrandLink, BrandLinkChunk, Domain, ReferenceDocument


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_org_and_user(suffix=""):
    """Create an Organisation + admin Account pair for testing."""
    org = Organisation.objects.create(name=f"TestOrg{suffix}")
    user = Account.objects.create_user(
        username=f"testuser{suffix}",
        email=f"testuser{suffix}@example.com",
        password="testpass123",
        organisation=org,
        role="admin",
    )
    return org, user


def _create_domain(org, url_suffix=""):
    return Domain.objects.create(
        name=f"Test Domain{url_suffix}",
        url=f"https://example{url_suffix}.com",
        organisation=org,
    )


def _auth_client(user):
    """Return an APIClient that is force-authenticated as *user*."""
    client = APIClient()
    client.force_authenticate(user=user)
    return client


# ---------------------------------------------------------------------------
# 1. Model-level tests
# ---------------------------------------------------------------------------

class BrandLinkModelTests(TestCase):
    """Tests for BrandLink and BrandLinkChunk models."""

    def setUp(self):
        self.org, self.user = _create_org_and_user()
        self.domain = _create_domain(self.org)

    # -- basic creation --
    def test_create_brand_link(self):
        link = BrandLink.objects.create(
            domain=self.domain,
            platform="facebook",
            url="https://facebook.com/test",
            label="FB Page",
            added_by=self.user,
        )
        self.assertEqual(link.platform, "facebook")
        self.assertEqual(link.extraction_status, "pending")
        self.assertIn("facebook.com", str(link))

    # -- unique_together (domain, url) --
    def test_unique_together_domain_url(self):
        BrandLink.objects.create(
            domain=self.domain,
            platform="facebook",
            url="https://facebook.com/test",
            added_by=self.user,
        )
        with self.assertRaises(IntegrityError):
            BrandLink.objects.create(
                domain=self.domain,
                platform="instagram",
                url="https://facebook.com/test",
                added_by=self.user,
            )

    def test_same_url_different_domains_allowed(self):
        """Same URL on different domains should NOT raise."""
        domain2 = _create_domain(self.org, url_suffix="2")
        url = "https://facebook.com/test"
        BrandLink.objects.create(domain=self.domain, platform="facebook", url=url, added_by=self.user)
        link2 = BrandLink.objects.create(domain=domain2, platform="facebook", url=url, added_by=self.user)
        self.assertEqual(link2.url, url)

    # -- MAX_LINKS_PER_DOMAIN enforced at API level; model constant exists --
    def test_max_links_constant(self):
        self.assertEqual(BrandLink.MAX_LINKS_PER_DOMAIN, 20)


# ---------------------------------------------------------------------------
# 2. Chunking tests
# ---------------------------------------------------------------------------

class BrandLinkChunkTests(TestCase):
    """Tests for _create_brand_link_chunks helper."""

    def setUp(self):
        self.org, self.user = _create_org_and_user()
        self.domain = _create_domain(self.org)

    def _make_link(self, text=""):
        return BrandLink.objects.create(
            domain=self.domain,
            platform="blog",
            url=f"https://blog.example.com/{BrandLink.objects.count()}",
            extracted_text=text,
            extraction_status="completed",
            added_by=self.user,
        )

    def test_empty_text_produces_no_chunks(self):
        from domains.views import _create_brand_link_chunks

        link = self._make_link("")
        _create_brand_link_chunks(link)
        self.assertEqual(link.chunks.count(), 0)

    def test_short_text_produces_one_chunk(self):
        from domains.views import _create_brand_link_chunks

        link = self._make_link("Hello world, this is a short text.")
        _create_brand_link_chunks(link)
        self.assertEqual(link.chunks.count(), 1)
        chunk = link.chunks.first()
        self.assertEqual(chunk.chunk_index, 0)
        self.assertIn("Hello world", chunk.chunk_text)

    def test_long_text_produces_multiple_chunks(self):
        from domains.views import _create_brand_link_chunks

        # 12000 chars should produce more than 1 chunk with default 5000/200 settings
        text = "A" * 12000
        link = self._make_link(text)
        _create_brand_link_chunks(link)
        self.assertGreater(link.chunks.count(), 1)
        # Verify ordering
        indices = list(link.chunks.values_list("chunk_index", flat=True))
        self.assertEqual(indices, sorted(indices))

    def test_rechunking_replaces_old_chunks(self):
        from domains.views import _create_brand_link_chunks

        link = self._make_link("Initial text")
        _create_brand_link_chunks(link)
        self.assertEqual(link.chunks.count(), 1)

        link.extracted_text = "B" * 15000
        link.save()
        _create_brand_link_chunks(link)
        self.assertGreater(link.chunks.count(), 1)
        # No leftover from initial
        self.assertFalse(link.chunks.filter(chunk_text__startswith="Initial").exists())


# ---------------------------------------------------------------------------
# 3. Brand Links API tests
# ---------------------------------------------------------------------------

@override_settings(ALLOWED_HOSTS=["*"])
class BrandLinkAPITests(TestCase):
    """Tests for the /domains/<domain_id>/brand-links/ endpoints."""

    def setUp(self):
        self.org, self.user = _create_org_and_user()
        self.domain = _create_domain(self.org)
        self.client = _auth_client(self.user)
        self.list_url = f"/domains/{self.domain.id}/brand-links/"

    # -- helpers --
    def _create_link_via_api(self, platform="facebook", url="https://facebook.com/test", label=""):
        with patch("threading.Thread"):
            return self.client.post(self.list_url, {
                "platform": platform,
                "url": url,
                "label": label,
            }, format="json")

    # -- GET list --
    def test_list_empty(self):
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["total_links"], 0)
        self.assertEqual(resp.data["max_links"], 20)

    def test_list_returns_created_links(self):
        self._create_link_via_api(url="https://facebook.com/a")
        self._create_link_via_api(platform="blog", url="https://blog.example.com/b")
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.data["total_links"], 2)

    # -- POST create --
    def test_create_brand_link_success(self):
        resp = self._create_link_via_api()
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn("brand_link", resp.data)
        self.assertEqual(resp.data["brand_link"]["platform"], "facebook")

    def test_create_brand_link_sets_added_by(self):
        resp = self._create_link_via_api()
        self.assertEqual(resp.data["brand_link"]["added_by"], self.user.id)

    # -- GET detail --
    def test_get_detail(self):
        create_resp = self._create_link_via_api()
        link_id = create_resp.data["brand_link"]["id"]
        resp = self.client.get(f"/domains/{self.domain.id}/brand-links/{link_id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["brand_link"]["id"], link_id)

    # -- PATCH update --
    def test_patch_label(self):
        create_resp = self._create_link_via_api()
        link_id = create_resp.data["brand_link"]["id"]
        resp = self.client.patch(
            f"/domains/{self.domain.id}/brand-links/{link_id}/",
            {"label": "Updated Label"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["brand_link"]["label"], "Updated Label")

    def test_patch_platform(self):
        create_resp = self._create_link_via_api()
        link_id = create_resp.data["brand_link"]["id"]
        resp = self.client.patch(
            f"/domains/{self.domain.id}/brand-links/{link_id}/",
            {"platform": "instagram"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["brand_link"]["platform"], "instagram")

    def test_patch_invalid_platform(self):
        create_resp = self._create_link_via_api()
        link_id = create_resp.data["brand_link"]["id"]
        resp = self.client.patch(
            f"/domains/{self.domain.id}/brand-links/{link_id}/",
            {"platform": "tiktok"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # -- DELETE --
    def test_delete_brand_link(self):
        create_resp = self._create_link_via_api()
        link_id = create_resp.data["brand_link"]["id"]
        resp = self.client.delete(f"/domains/{self.domain.id}/brand-links/{link_id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(BrandLink.objects.filter(id=link_id).exists())

    # -- 404 for wrong domain --
    def test_detail_wrong_domain_404(self):
        create_resp = self._create_link_via_api()
        link_id = create_resp.data["brand_link"]["id"]
        resp = self.client.get(f"/domains/999999/brand-links/{link_id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # -- unauthenticated --
    def test_unauthenticated_request_rejected(self):
        anon = APIClient()
        resp = anon.get(self.list_url)
        self.assertIn(resp.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])


# ---------------------------------------------------------------------------
# 4. Validation tests
# ---------------------------------------------------------------------------

@override_settings(ALLOWED_HOSTS=["*"])
class BrandLinkValidationTests(TestCase):
    """Validation edge cases for the brand-links POST endpoint."""

    def setUp(self):
        self.org, self.user = _create_org_and_user()
        self.domain = _create_domain(self.org)
        self.client = _auth_client(self.user)
        self.list_url = f"/domains/{self.domain.id}/brand-links/"

    def _post(self, data):
        with patch("threading.Thread"):
            return self.client.post(self.list_url, data, format="json")

    def test_missing_platform(self):
        resp = self._post({"url": "https://example.com"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Platform is required", resp.data.get("error", ""))

    def test_missing_url(self):
        resp = self._post({"platform": "facebook"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("URL is required", resp.data.get("error", ""))

    def test_invalid_platform(self):
        resp = self._post({"platform": "tiktok", "url": "https://tiktok.com/@brand"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid platform", resp.data.get("error", ""))

    def test_duplicate_url(self):
        self._post({"platform": "facebook", "url": "https://facebook.com/brand"})
        resp = self._post({"platform": "facebook", "url": "https://facebook.com/brand"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already added", resp.data.get("error", ""))

    def test_url_without_scheme_rejected(self):
        resp = self._post({"platform": "blog", "url": "www.example.com"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_max_links_per_domain(self):
        """Creating more than MAX_LINKS_PER_DOMAIN should be rejected."""
        for i in range(BrandLink.MAX_LINKS_PER_DOMAIN):
            self._post({"platform": "other", "url": f"https://example.com/page/{i}"})
        resp = self._post({"platform": "other", "url": "https://example.com/page/extra"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Maximum", resp.data.get("error", ""))


# ---------------------------------------------------------------------------
# 5. Reference Document endpoints still work
# ---------------------------------------------------------------------------

@override_settings(ALLOWED_HOSTS=["*"])
class ReferenceDocumentRegressionTests(TestCase):
    """Sanity checks that existing reference-repository endpoints still work."""

    def setUp(self):
        self.org, self.user = _create_org_and_user()
        self.domain = _create_domain(self.org)
        self.client = _auth_client(self.user)
        self.list_url = f"/domains/{self.domain.id}/reference-repository/"

    def test_get_list(self):
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("reference_documents", resp.data)

    def test_post_text_note(self):
        resp = self.client.post(self.list_url, {
            "file_type": "text",
            "title": "Brand Guidelines",
            "text_content": "Always use the Oxford comma.",
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn("reference_document", resp.data)

    def test_delete_text_note(self):
        create_resp = self.client.post(self.list_url, {
            "file_type": "text",
            "title": "Temp Note",
            "text_content": "Temporary content",
        }, format="json")
        doc_id = create_resp.data["reference_document"]["id"]
        resp = self.client.delete(f"/domains/{self.domain.id}/reference-repository/{doc_id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(ReferenceDocument.objects.filter(id=doc_id).exists())


# ---------------------------------------------------------------------------
# 6. Domain endpoints still work
# ---------------------------------------------------------------------------

@override_settings(ALLOWED_HOSTS=["*"])
class DomainEndpointRegressionTests(TestCase):
    """Sanity checks that core domain GET / PATCH endpoints still work."""

    def setUp(self):
        self.org, self.user = _create_org_and_user()
        self.domain = _create_domain(self.org)
        self.client = _auth_client(self.user)

    def test_get_domain_detail(self):
        resp = self.client.get(f"/domains/{self.domain.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["id"], self.domain.id)

    def test_patch_domain(self):
        resp = self.client.put(
            f"/domains/{self.domain.id}/",
            {"short_description": "Updated description"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.domain.refresh_from_db()
        self.assertEqual(self.domain.short_description, "Updated description")
