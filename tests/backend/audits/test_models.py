"""
Audit Engine model tests.

Covers the state machine the worker and the UI both depend on:
  1. Defaults on a fresh row (queued, unguessable token, nothing scored)
  2. set_stage() advances stage/progress, merges stage_detail, flips INIT -> PROC
  3. mark_done() publishes with an expiry; mark_failed() keeps the error
  4. Expiry: unclaimed audits expire, claimed ones never do
  5. record_open() counts views without touching modified_at
  6. Child rows: uniqueness per (audit, prompt, platform, run) and per (audit, keyword)
  7. Deleting an audit cascades to its evidence rows
"""
from datetime import timedelta

from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.utils import timezone

from audits.models import Audit, AuditKeywordResult, AuditPageResult, AuditPromptResult
from authentication.models import Account, Organisation
from domains.models import Domain


def _audit(**overrides):
    fields = {'host': 'hdfcbank.com', 'website': 'https://hdfcbank.com', 'country': 'in'}
    fields.update(overrides)
    return Audit.objects.create(**fields)


class AuditDefaultsTests(TestCase):
    def test_fresh_audit_is_queued_with_a_token(self):
        audit = _audit()
        self.assertEqual(audit.status, 'INIT')
        self.assertEqual(audit.stage, '')
        self.assertEqual(audit.progress, 0)
        self.assertEqual(audit.stage_index, 0)
        self.assertGreaterEqual(len(audit.public_token), 20)
        self.assertIsNone(audit.geo_score)
        self.assertFalse(audit.is_claimed)
        self.assertFalse(audit.is_expired)

    def test_tokens_are_unique_per_audit(self):
        tokens = {_audit().public_token for _ in range(5)}
        self.assertEqual(len(tokens), 5)


class AuditStageTests(TestCase):
    def test_set_stage_advances_and_starts_processing(self):
        audit = _audit()
        audit.set_stage('profile')
        audit.refresh_from_db()
        self.assertEqual(audit.status, 'PROC')
        self.assertEqual(audit.stage, 'profile')
        self.assertEqual(audit.stage_index, 1)
        self.assertEqual(audit.progress, 0)

        audit.set_stage('engines', done=61, total=144)
        audit.refresh_from_db()
        self.assertEqual(audit.stage_index, 4)
        self.assertEqual(audit.progress, 42)
        self.assertEqual(audit.stage_detail, {'engines': {'done': 61, 'total': 144}})

    def test_set_stage_merges_detail_and_accepts_explicit_progress(self):
        audit = _audit()
        audit.set_stage('engines', done=10, total=144)
        audit.set_stage('engines', progress=45, done=80)
        audit.refresh_from_db()
        self.assertEqual(audit.progress, 45)
        self.assertEqual(audit.stage_detail['engines'], {'done': 80, 'total': 144})

    def test_set_stage_clamps_progress(self):
        audit = _audit()
        audit.set_stage('score', progress=250)
        self.assertEqual(audit.progress, 100)

    def test_unknown_stage_is_rejected(self):
        with self.assertRaises(ValueError):
            _audit().set_stage('teleport')

    @override_settings(AUDIT_PUBLIC_TTL_DAYS=7)
    def test_mark_done_publishes_with_expiry(self):
        audit = _audit()
        audit.set_stage('score')
        audit.mark_done()
        audit.refresh_from_db()
        self.assertEqual(audit.status, 'DONE')
        self.assertEqual(audit.stage, 'publish')
        self.assertEqual(audit.progress, 100)
        self.assertIsNotNone(audit.completed_at)
        self.assertAlmostEqual(
            (audit.expires_at - audit.completed_at).total_seconds(),
            timedelta(days=7).total_seconds(), delta=5,
        )

    def test_mark_done_keeps_an_existing_expiry(self):
        fixed = timezone.now() + timedelta(days=3)
        audit = _audit(expires_at=fixed)
        audit.mark_done()
        self.assertEqual(audit.expires_at, fixed)

    def test_mark_failed_records_error(self):
        audit = _audit()
        audit.set_stage('engines')
        audit.mark_failed('OpenRouter 429: rate limited')
        audit.refresh_from_db()
        self.assertEqual(audit.status, 'FAIL')
        self.assertEqual(audit.error, 'OpenRouter 429: rate limited')
        self.assertEqual(audit.stage, 'engines')  # where it died is kept for the UI
        self.assertIsNotNone(audit.completed_at)

    def test_mark_failed_truncates_long_errors(self):
        audit = _audit()
        audit.mark_failed('x' * 10000)
        self.assertEqual(len(audit.error), 4000)


class AuditExpiryAndClaimTests(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name='Audit Org')
        self.user = Account.objects.create_user(
            username='auditor', email='auditor@example.com', password='pw',
            organisation=self.org, role='admin',
        )

    def test_unclaimed_audit_expires(self):
        audit = _audit(expires_at=timezone.now() - timedelta(minutes=1))
        self.assertTrue(audit.is_expired)

    def test_no_expiry_means_never_expired(self):
        self.assertFalse(_audit(expires_at=None).is_expired)

    def test_claimed_audit_never_expires(self):
        domain = Domain.objects.create(name='HDFC', url='https://hdfcbank.com', organisation=self.org)
        audit = _audit(
            expires_at=timezone.now() - timedelta(days=1),
            claimed_domain=domain, claimed_by=self.user, claimed_at=timezone.now(),
        )
        self.assertTrue(audit.is_claimed)
        self.assertFalse(audit.is_expired)
        self.assertEqual(list(domain.audits.all()), [audit])

    def test_deleting_the_domain_keeps_the_audit(self):
        domain = Domain.objects.create(name='HDFC', url='https://hdfcbank.com', organisation=self.org)
        audit = _audit(claimed_domain=domain)
        domain.delete()
        audit.refresh_from_db()
        self.assertIsNone(audit.claimed_domain)

    def test_deleting_the_user_keeps_the_audit(self):
        audit = _audit(requested_by=self.user)
        self.user.delete()
        audit.refresh_from_db()
        self.assertIsNone(audit.requested_by)


class AuditOpenCountTests(TestCase):
    def test_record_open_increments_without_touching_modified_at(self):
        audit = _audit()
        before = audit.modified_at
        audit.record_open()
        audit.record_open()
        audit.refresh_from_db()
        self.assertEqual(audit.opens, 2)
        self.assertIsNotNone(audit.last_opened_at)
        self.assertEqual(audit.modified_at, before)


class AuditEvidenceRowTests(TestCase):
    def setUp(self):
        self.audit = _audit()

    def _result(self, **overrides):
        fields = {
            'audit': self.audit, 'prompt_index': 1, 'prompt_text': 'Best savings account?',
            'platform': 'ChatGPT', 'run_index': 1, 'is_mention': True, 'position': 2,
        }
        fields.update(overrides)
        return AuditPromptResult.objects.create(**fields)

    def test_prompt_result_defaults(self):
        row = self._result()
        self.assertEqual(row.status, 'ok')
        self.assertFalse(row.is_cited)
        self.assertEqual(row.competitors_mentioned, [])
        self.assertEqual(row.cited_domains, [])
        self.assertIsNone(row.latency_ms)

    def test_same_prompt_platform_run_is_unique(self):
        self._result()
        with self.assertRaises(IntegrityError):
            self._result()

    def test_same_prompt_on_another_platform_or_run_is_allowed(self):
        self._result()
        self._result(platform='Claude')
        self._result(run_index=2)
        self.assertEqual(self.audit.prompt_results.count(), 3)

    def test_keyword_is_unique_per_audit(self):
        AuditKeywordResult.objects.create(audit=self.audit, keyword='home loan', position=4)
        with self.assertRaises(IntegrityError):
            AuditKeywordResult.objects.create(audit=self.audit, keyword='home loan', position=9)

    def test_keyword_without_ranking_is_allowed(self):
        row = AuditKeywordResult.objects.create(audit=self.audit, keyword='gold loan rate')
        self.assertIsNone(row.position)
        self.assertIsNone(row.search_volume)

    def test_page_result_defaults_and_uniqueness(self):
        row = AuditPageResult.objects.create(audit=self.audit, url='https://hdfcbank.com/savings', word_count=900)
        self.assertTrue(row.fetched)
        self.assertEqual(row.schema_types, [])
        self.assertIsNone(row.last_modified)
        with self.assertRaises(IntegrityError):
            AuditPageResult.objects.create(audit=self.audit, url='https://hdfcbank.com/savings')

    def test_deleting_audit_cascades_to_evidence(self):
        self._result()
        AuditKeywordResult.objects.create(audit=self.audit, keyword='home loan')
        AuditPageResult.objects.create(audit=self.audit, url='https://hdfcbank.com/')
        self.audit.delete()
        self.assertEqual(AuditPromptResult.objects.count(), 0)
        self.assertEqual(AuditKeywordResult.objects.count(), 0)
        self.assertEqual(AuditPageResult.objects.count(), 0)
