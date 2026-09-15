"""
Audit Engine API tests.

Covers the four public/authenticated surfaces and every guard in
audits.services, with the engine dispatch mocked:

  1. POST /audits/         flag off -> 503; bad URL -> 400; anonymous creates a
                           'landing' audit and dispatches; repeat window reuses;
                           per-IP and global caps -> 429; admin force bypasses
                           the repeat window; engine down -> row FAIL + 503
  2. GET /audits/public/<token>/  progress before DONE, report after, opens counted,
                           expired -> 404, no requester fields leak
  3. GET /audits/          401 anonymous, 403 for clients, super_admin sees all,
                           org admin sees only their org's; filters + search
  4. GET/DELETE /audits/<id>/     detail carries evidence rows; delete is admin-only
  5. POST /audits/<id>/claim/     creates the Domain from the profile, links back,
                           clears expiry; refuses unfinished / already claimed /
                           already tracked; keyword seeding is started
  6. POST /audits/<id>/rerun/     FAIL -> PROC + dispatch; DONE refused
  7. GET /audits/config/   flags and permissions for the UI
"""
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from audits import services
from audits.models import Audit, AuditPageResult, AuditPromptResult
from authentication.models import Account, Organisation
from domains.models import Domain, DomainAccess

ON = dict(AUDIT_ENGINE_ENABLED=True, AUDIT_REPEAT_HOURS=24, AUDIT_PER_IP_DAILY=3, AUDIT_GLOBAL_DAILY=50)


def _user(org, role, suffix):
    return Account.objects.create_user(
        username=f'{role}{suffix}', email=f'{role}{suffix}@example.com', password='pw',
        organisation=org, role=role,
    )


def _client(user=None):
    c = APIClient()
    if user is not None:
        c.force_authenticate(user=user)
    return c


def _done_audit(**overrides):
    fields = dict(
        host='hdfcbank.com', website='https://hdfcbank.com', country='in', source='landing',
        status='DONE', stage='publish', progress=100, brand_name='HDFC Bank', industry='Retail banking',
        competitors=[{'name': 'ICICI Bank', 'host': 'icicibank.com'}],
        geo_score=58, geo_stage='preferred', appearances=20, cited_runs=9, total_runs=24,
        report={'version': 1, 'geo': {'score': 58}},
        grounding={'profile': {'description': 'A bank.', 'audience': 'salaried people',
                               'categories': ['savings accounts'], 'regions': ['India'],
                               'use_cases': ['salary account'], 'buying_criteria': ['rates']}},
        completed_at=timezone.now(), expires_at=timezone.now() + timedelta(days=30),
    )
    fields.update(overrides)
    return Audit.objects.create(**fields)


class _Base(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name='Agency')
        self.other_org = Organisation.objects.create(name='Other')
        self.superadmin = _user(self.org, 'super_admin', '1')
        self.admin = _user(self.org, 'admin', '1')
        self.other_admin = _user(self.other_org, 'admin', '2')
        self.client_user = _user(self.org, 'client', '1')
        self.dispatch = patch.object(services, 'dispatch', return_value=True)
        self.dispatch_mock = self.dispatch.start()
        self.addCleanup(self.dispatch.stop)


@override_settings(**ON)
class CreateTests(_Base):
    def test_flag_off_is_503(self):
        with override_settings(AUDIT_ENGINE_ENABLED=False):
            r = _client().post('/audits/', {'url': 'hdfcbank.com'}, format='json')
        self.assertEqual(r.status_code, 503)
        self.assertEqual(Audit.objects.count(), 0)

    def test_bad_url_is_400(self):
        for bad in ('', 'not a url', 'http://', 'localhost', 'a b.com'):
            r = _client().post('/audits/', {'url': bad}, format='json')
            self.assertEqual(r.status_code, 400, bad)
        self.assertEqual(Audit.objects.count(), 0)

    def test_anonymous_creates_landing_audit_and_dispatches(self):
        r = _client().post('/audits/', {'url': 'https://www.HDFCBank.com/x', 'country': 'IN', 'email': 'lead@example.com'},
                           format='json', REMOTE_ADDR='203.0.113.9')
        self.assertEqual(r.status_code, 201, r.data)
        audit = Audit.objects.get()
        self.assertEqual(audit.host, 'hdfcbank.com')
        self.assertEqual(audit.website, 'https://hdfcbank.com')
        self.assertEqual(audit.country, 'in')
        self.assertEqual(audit.source, 'landing')
        self.assertEqual(audit.requester_email, 'lead@example.com')
        self.assertEqual(audit.requester_ip, '203.0.113.9')
        self.assertIsNone(audit.requested_by)
        self.assertEqual(audit.status, 'INIT')
        self.dispatch_mock.assert_called_once_with(audit)
        self.assertEqual(r.data['public_token'], audit.public_token)
        self.assertIn(f'/audits/public/{audit.public_token}/', r.data['status_url'])
        self.assertFalse(r.data['reused'])

    def test_forwarded_ip_is_used_behind_proxy(self):
        _client().post('/audits/', {'url': 'hdfcbank.com'}, format='json',
                       HTTP_X_FORWARDED_FOR='198.51.100.7, 10.0.0.1', REMOTE_ADDR='10.0.0.1')
        self.assertEqual(Audit.objects.get().requester_ip, '198.51.100.7')

    def test_admin_creates_manual_audit(self):
        r = _client(self.admin).post('/audits/', {'url': 'hdfcbank.com'}, format='json')
        self.assertEqual(r.status_code, 201)
        audit = Audit.objects.get()
        self.assertEqual(audit.source, 'manual')
        self.assertEqual(audit.requested_by, self.admin)

    def test_repeat_within_window_reuses_existing(self):
        first = _client().post('/audits/', {'url': 'hdfcbank.com'}, format='json').data
        second = _client().post('/audits/', {'url': 'www.hdfcbank.com'}, format='json')
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.data['reused'])
        self.assertEqual(second.data['id'], first['id'])
        self.assertEqual(Audit.objects.count(), 1)
        self.assertEqual(self.dispatch_mock.call_count, 1)

    def test_repeat_for_another_country_is_a_new_audit(self):
        first = _client().post('/audits/', {'url': 'hdfcbank.com', 'country': 'in'}, format='json').data
        us = _client().post('/audits/', {'url': 'hdfcbank.com', 'country': 'us'}, format='json')
        self.assertEqual(us.status_code, 201, 'a different market is not a repeat')
        self.assertFalse(us.data['reused'])
        self.assertNotEqual(us.data['id'], first['id'])
        self.assertEqual(Audit.objects.count(), 2)
        self.assertEqual(self.dispatch_mock.call_count, 2)
        # the same market again is still reused
        again = _client().post('/audits/', {'url': 'hdfcbank.com', 'country': 'us'}, format='json')
        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.data['id'], us.data['id'])
        self.assertEqual(Audit.objects.count(), 2)

    def test_failed_audit_does_not_block_a_retry(self):
        Audit.objects.create(host='hdfcbank.com', website='https://hdfcbank.com', status='FAIL')
        r = _client().post('/audits/', {'url': 'hdfcbank.com'}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Audit.objects.count(), 2)

    def test_admin_force_bypasses_repeat_window(self):
        _client().post('/audits/', {'url': 'hdfcbank.com'}, format='json')
        r = _client(self.admin).post('/audits/', {'url': 'hdfcbank.com', 'force': True}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Audit.objects.count(), 2)

    def test_anonymous_force_is_ignored(self):
        _client().post('/audits/', {'url': 'hdfcbank.com'}, format='json')
        r = _client().post('/audits/', {'url': 'hdfcbank.com', 'force': True}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data['reused'])

    def test_per_ip_daily_cap(self):
        for i in range(3):
            r = _client().post('/audits/', {'url': f'site{i}.com'}, format='json', REMOTE_ADDR='203.0.113.9')
            self.assertEqual(r.status_code, 201)
        r = _client().post('/audits/', {'url': 'site9.com'}, format='json', REMOTE_ADDR='203.0.113.9')
        self.assertEqual(r.status_code, 429)
        # a different IP is unaffected
        r = _client().post('/audits/', {'url': 'site9.com'}, format='json', REMOTE_ADDR='203.0.113.10')
        self.assertEqual(r.status_code, 201)

    def test_admin_bypasses_per_ip_cap_but_not_global(self):
        with override_settings(AUDIT_PER_IP_DAILY=1, AUDIT_GLOBAL_DAILY=2):
            self.assertEqual(_client(self.admin).post('/audits/', {'url': 'a.com'}, format='json').status_code, 201)
            self.assertEqual(_client(self.admin).post('/audits/', {'url': 'b.com'}, format='json').status_code, 201)
            r = _client(self.admin).post('/audits/', {'url': 'c.com'}, format='json')
        self.assertEqual(r.status_code, 429)
        self.assertIn('daily limit', r.data['error'])

    def test_engine_down_fails_row_and_returns_503(self):
        self.dispatch.stop()
        with patch('audits.services.requests.post', side_effect=services.requests.ConnectionError('refused')):
            r = _client().post('/audits/', {'url': 'hdfcbank.com'}, format='json')
        self.dispatch_mock = self.dispatch.start()
        self.assertEqual(r.status_code, 503)
        audit = Audit.objects.get()
        self.assertEqual(audit.status, 'FAIL')
        self.assertIn('Could not reach the processing engine', audit.error)

    def test_dispatch_posts_audit_id_to_engine(self):
        self.dispatch.stop()
        audit = Audit.objects.create(host='x.com', website='https://x.com')
        with patch('audits.services.requests.post') as post, override_settings(ENGINE_API_URL='http://engine:8001/'):
            post.return_value.raise_for_status.return_value = None
            self.assertTrue(services.dispatch(audit))
        self.dispatch_mock = self.dispatch.start()
        post.assert_called_once_with('http://engine:8001/api/audits/run/', json={'audit_id': audit.pk}, timeout=10)


@override_settings(**ON)
class PublicTests(_Base):
    def test_unknown_token_is_404(self):
        self.assertEqual(_client().get('/audits/public/nope/').status_code, 404)

    def test_progress_before_done_has_no_report(self):
        audit = Audit.objects.create(host='x.com', website='https://x.com', requester_email='lead@example.com', requester_ip='1.2.3.4')
        audit.set_stage('engines', done=3, total=48)
        r = _client().get(f'/audits/public/{audit.public_token}/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['status'], 'PROC')
        self.assertEqual(r.data['stage'], 'engines')
        self.assertEqual(r.data['stage_index'], 4)
        self.assertEqual(r.data['stage_total'], 7)
        self.assertEqual(r.data['stage_label'], 'Asking the AI engines')
        self.assertEqual(r.data['stage_detail'], {'engines': {'done': 3, 'total': 48}})
        self.assertIsNone(r.data['report'])
        self.assertEqual(r.data['error'], '')
        for leaked in ('requester_email', 'requester_ip', 'requested_by', 'config', 'grounding', 'id', 'page_results'):
            self.assertNotIn(leaked, r.data)
        audit.refresh_from_db()
        self.assertEqual(audit.opens, 0)

    def test_done_returns_report_and_counts_opens(self):
        audit = _done_audit()
        c = _client()
        r1 = c.get(f'/audits/public/{audit.public_token}/')
        r2 = c.get(f'/audits/public/{audit.public_token}/')
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.data['report'], {'version': 1, 'geo': {'score': 58}})
        self.assertEqual(r1.data['geo_score'], 58)
        self.assertEqual(r1.data['geo_stage'], 'preferred')
        self.assertEqual(r2.data['opens'], 2)
        audit.refresh_from_db()
        self.assertEqual(audit.opens, 2)

    def test_failed_shows_generic_message(self):
        audit = Audit.objects.create(host='x.com', website='https://x.com')
        audit.mark_failed('OpenRouter 402 insufficient credits sk-or-...')
        r = _client().get(f'/audits/public/{audit.public_token}/')
        self.assertEqual(r.data['status'], 'FAIL')
        self.assertNotIn('OpenRouter', r.data['error'])
        self.assertTrue(r.data['error'])

    def test_expired_is_404_unless_claimed(self):
        audit = _done_audit(expires_at=timezone.now() - timedelta(days=1))
        self.assertEqual(_client().get(f'/audits/public/{audit.public_token}/').status_code, 404)
        domain = Domain.objects.create(name='HDFC', url='https://hdfcbank.com', organisation=self.org)
        Audit.objects.filter(pk=audit.pk).update(claimed_domain=domain, claimed_at=timezone.now())
        self.assertEqual(_client().get(f'/audits/public/{audit.public_token}/').status_code, 200)


@override_settings(**ON)
class ListTests(_Base):
    def setUp(self):
        super().setUp()
        self.mine = _done_audit(host='mine.com', website='https://mine.com', source='manual', requested_by=self.admin)
        self.lead = _done_audit(host='lead.com', website='https://lead.com', source='landing', geo_score=20, geo_stage='absent')
        self.theirs = _done_audit(host='theirs.com', website='https://theirs.com', source='manual', requested_by=self.other_admin)

    def test_anonymous_is_401(self):
        self.assertEqual(_client().get('/audits/').status_code, 401)

    def test_client_role_is_403(self):
        self.assertEqual(_client(self.client_user).get('/audits/').status_code, 403)

    def test_super_admin_sees_everything(self):
        r = _client(self.superadmin).get('/audits/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual({row['host'] for row in r.data['results']}, {'mine.com', 'lead.com', 'theirs.com'})
        self.assertEqual(r.data['count'], 3)

    def test_org_admin_sees_only_own_org(self):
        r = _client(self.admin).get('/audits/')
        self.assertEqual([row['host'] for row in r.data['results']], ['mine.com'])
        # ...including audits claimed into the org by someone else
        domain = Domain.objects.create(name='Lead', url='https://lead.com', organisation=self.org)
        Audit.objects.filter(pk=self.lead.pk).update(claimed_domain=domain)
        r = _client(self.admin).get('/audits/')
        self.assertEqual({row['host'] for row in r.data['results']}, {'mine.com', 'lead.com'})

    def test_filters_and_search(self):
        c = _client(self.superadmin)
        self.assertEqual([r['host'] for r in c.get('/audits/?source=landing').data['results']], ['lead.com'])
        self.assertEqual([r['host'] for r in c.get('/audits/?geo_stage=absent').data['results']], ['lead.com'])
        self.assertEqual(c.get('/audits/?claimed=true').data['count'], 0)
        self.assertEqual(c.get('/audits/?claimed=false').data['count'], 3)
        self.assertEqual([r['host'] for r in c.get('/audits/?search=THEIRS').data['results']], ['theirs.com'])
        self.assertEqual([r['host'] for r in c.get('/audits/?ordering=geo_score').data['results']][0], 'lead.com')

    def test_row_shape(self):
        row = _client(self.superadmin).get('/audits/?search=mine').data['results'][0]
        self.assertEqual(row['requested_by_email'], self.admin.email)
        self.assertEqual(row['stage_index'], 7)
        self.assertFalse(row['is_claimed'])
        self.assertIn('public_token', row)
        self.assertNotIn('report', row)


@override_settings(**ON)
class DetailTests(_Base):
    def setUp(self):
        super().setUp()
        self.audit = _done_audit(requested_by=self.admin)
        AuditPromptResult.objects.create(audit=self.audit, prompt_index=1, prompt_text='q?', platform='ChatGPT', is_mention=True)
        AuditPageResult.objects.create(audit=self.audit, url='https://hdfcbank.com/', word_count=1200, schema_types=['Organization'], author='Priya')

    def test_detail_carries_evidence_and_public_url(self):
        r = _client(self.admin).get(f'/audits/{self.audit.pk}/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['report'], self.audit.report)
        self.assertEqual(len(r.data['prompt_results']), 1)
        self.assertEqual(r.data['prompt_results'][0]['platform'], 'ChatGPT')
        self.assertEqual(r.data['keyword_results'], [])
        self.assertEqual(len(r.data['page_results']), 1)
        self.assertEqual(r.data['page_results'][0]['schema_types'], ['Organization'])
        self.assertEqual(r.data['page_results'][0]['author'], 'Priya')
        self.assertIn(f'/audits/public/{self.audit.public_token}/', r.data['status_url'])

    def test_other_org_cannot_see_it(self):
        self.assertEqual(_client(self.other_admin).get(f'/audits/{self.audit.pk}/').status_code, 404)
        self.assertEqual(_client(self.client_user).get(f'/audits/{self.audit.pk}/').status_code, 403)

    def test_delete_is_admin_only_and_cascades(self):
        self.assertEqual(_client(self.client_user).delete(f'/audits/{self.audit.pk}/').status_code, 403)
        r = _client(self.admin).delete(f'/audits/{self.audit.pk}/')
        self.assertEqual(r.status_code, 204)
        self.assertEqual(Audit.objects.count(), 0)
        self.assertEqual(AuditPromptResult.objects.count(), 0)
        self.assertEqual(AuditPageResult.objects.count(), 0)


@override_settings(**ON)
class ClaimTests(_Base):
    def setUp(self):
        super().setUp()
        self.audit = _done_audit(requested_by=self.admin, expires_at=timezone.now() + timedelta(days=3))
        self.seed = patch('domains.keyword_seeder.seed_keywords_in_background')
        self.seed_mock = self.seed.start()
        self.addCleanup(self.seed.stop)

    def test_claim_creates_domain_from_profile(self):
        r = _client(self.admin).post(f'/audits/{self.audit.pk}/claim/')
        self.assertEqual(r.status_code, 201, r.data)
        domain = Domain.objects.get()
        self.assertEqual(domain.name, 'HDFC Bank')
        self.assertEqual(domain.url, 'https://hdfcbank.com')
        self.assertEqual(domain.organisation, self.org)
        self.assertEqual(domain.country, 'India')
        self.assertEqual(domain.processing_status, 'COMP')
        self.assertEqual(domain.short_description, 'A bank.')
        self.assertEqual(domain.target_audience, 'salaried people')
        self.assertEqual(domain.offering_categories, ['savings accounts'])
        self.assertEqual(domain.key_competitors, 'ICICI Bank')
        self.assertTrue(DomainAccess.objects.filter(domain=domain, user=self.admin).exists())
        self.seed_mock.assert_called_once_with(domain.id)

        self.audit.refresh_from_db()
        self.assertEqual(self.audit.claimed_domain, domain)
        self.assertEqual(self.audit.claimed_by, self.admin)
        self.assertIsNotNone(self.audit.claimed_at)
        self.assertIsNone(self.audit.expires_at, 'claimed audits never expire')
        self.assertEqual(r.data['domain']['id'], domain.id)
        self.assertTrue(r.data['audit']['is_claimed'])

    def test_claim_requires_admin(self):
        self.assertEqual(_client(self.client_user).post(f'/audits/{self.audit.pk}/claim/').status_code, 403)
        self.assertEqual(_client().post(f'/audits/{self.audit.pk}/claim/').status_code, 401)

    def test_super_admin_can_claim_a_landing_lead(self):
        lead = _done_audit(host='lead.com', website='https://lead.com', brand_name='Lead Co')
        r = _client(self.superadmin).post(f'/audits/{lead.pk}/claim/')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Domain.objects.get().organisation, self.org)

    def test_unfinished_audit_cannot_be_claimed(self):
        Audit.objects.filter(pk=self.audit.pk).update(status='PROC')
        r = _client(self.admin).post(f'/audits/{self.audit.pk}/claim/')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Domain.objects.count(), 0)

    def test_double_claim_is_refused_with_domain_id(self):
        first = _client(self.admin).post(f'/audits/{self.audit.pk}/claim/')
        second = _client(self.admin).post(f'/audits/{self.audit.pk}/claim/')
        self.assertEqual(second.status_code, 400)
        self.assertEqual(second.data['domain_id'], first.data['domain']['id'])
        self.assertEqual(Domain.objects.count(), 1)

    def test_already_tracked_host_is_refused(self):
        existing = Domain.objects.create(name='HDFC old', url='http://www.hdfcbank.com/', organisation=self.org)
        r = _client(self.admin).post(f'/audits/{self.audit.pk}/claim/')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data['domain_id'], existing.pk)
        self.audit.refresh_from_db()
        self.assertFalse(self.audit.is_claimed)


@override_settings(**ON)
class RerunTests(_Base):
    def test_failed_audit_is_resumed(self):
        audit = Audit.objects.create(host='x.com', website='https://x.com', requested_by=self.admin)
        audit.set_stage('engines')
        audit.mark_failed('boom')
        r = _client(self.admin).post(f'/audits/{audit.pk}/rerun/')
        self.assertEqual(r.status_code, 200, r.data)
        audit.refresh_from_db()
        self.assertEqual(audit.status, 'PROC')
        self.assertEqual(audit.error, '')
        self.assertIsNone(audit.completed_at)
        self.assertEqual(audit.stage, 'engines', 'the resume point is kept')
        self.dispatch_mock.assert_called_once_with(audit)

    def test_stalled_processing_audit_can_be_rerun(self):
        audit = Audit.objects.create(host='x.com', website='https://x.com', requested_by=self.admin, status='PROC')
        Audit.objects.filter(pk=audit.pk).update(modified_at=timezone.now() - timedelta(hours=1))
        self.assertEqual(_client(self.admin).post(f'/audits/{audit.pk}/rerun/').status_code, 200)

    def test_done_or_live_audit_is_refused(self):
        done = _done_audit(requested_by=self.admin)
        self.assertEqual(_client(self.admin).post(f'/audits/{done.pk}/rerun/').status_code, 400)
        live = Audit.objects.create(host='y.com', website='https://y.com', requested_by=self.admin, status='PROC')
        self.assertEqual(_client(self.admin).post(f'/audits/{live.pk}/rerun/').status_code, 400)
        self.dispatch_mock.assert_not_called()

    def test_rerun_requires_admin(self):
        audit = Audit.objects.create(host='x.com', website='https://x.com', status='FAIL', requested_by=self.admin)
        self.assertEqual(_client(self.client_user).post(f'/audits/{audit.pk}/rerun/').status_code, 403)


@override_settings(**ON, AUDIT_ENGINES=['openai', 'gemini'], AUDIT_PROMPT_COUNT=12)
class ConfigTests(_Base):
    def test_config_reflects_flags_and_role(self):
        r = _client(self.admin).get('/audits/config/')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data['enabled'])
        self.assertEqual(r.data['engines'], ['openai', 'gemini'])
        self.assertEqual(r.data['prompt_count'], 12)
        self.assertTrue(r.data['can_manage'])
        self.assertTrue(r.data['can_list'])
        r = _client(self.client_user).get('/audits/config/')
        self.assertFalse(r.data['can_manage'])
        self.assertFalse(r.data['can_list'])
        with override_settings(AUDIT_ENGINE_ENABLED=False):
            self.assertFalse(_client(self.admin).get('/audits/config/').data['enabled'])

    def test_config_requires_auth(self):
        self.assertEqual(_client().get('/audits/config/').status_code, 401)


class ServiceHelperTests(TestCase):
    def test_normalize_host(self):
        self.assertEqual(services.normalize_host('HTTPS://www.HDFCBank.com/x?y#z'), 'hdfcbank.com')
        self.assertEqual(services.normalize_host('hdfcbank.com.'), 'hdfcbank.com')
        self.assertEqual(services.normalize_host('user@hdfcbank.com:8080/'), 'hdfcbank.com')
        for bad in ('', 'localhost', 'a b.com', '-x.com', 'x', 'http://'):
            self.assertEqual(services.normalize_host(bad), '', bad)


@override_settings(**ON)
class ClaimByTokenTests(_Base):
    """The public-page claim: the token is the credential, not the leads table."""

    def setUp(self):
        super().setUp()
        self.lead = _done_audit(host='lead.com', website='https://lead.com', brand_name='Lead Co')
        self.seed = patch('domains.keyword_seeder.seed_keywords_in_background')
        self.seed.start()
        self.addCleanup(self.seed.stop)

    def test_org_admin_can_claim_a_lead_they_cannot_list(self):
        # Not visible in the leads table for this org...
        self.assertEqual(_client(self.other_admin).get(f'/audits/{self.lead.pk}/').status_code, 404)
        # ...but claimable by token.
        r = _client(self.other_admin).post(f'/audits/claim/{self.lead.public_token}/')
        self.assertEqual(r.status_code, 201, r.data)
        domain = Domain.objects.get()
        self.assertEqual(domain.organisation, self.other_org)
        self.assertEqual(domain.name, 'Lead Co')
        self.assertEqual(r.data['audit']['id'], self.lead.pk)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.claimed_by, self.other_admin)
        # now it is in their leads table
        self.assertEqual(_client(self.other_admin).get(f'/audits/{self.lead.pk}/').status_code, 200)

    def test_requires_admin_and_a_live_token(self):
        self.assertEqual(_client().post(f'/audits/claim/{self.lead.public_token}/').status_code, 401)
        self.assertEqual(_client(self.client_user).post(f'/audits/claim/{self.lead.public_token}/').status_code, 403)
        self.assertEqual(_client(self.admin).post('/audits/claim/nope/').status_code, 404)
        Audit.objects.filter(pk=self.lead.pk).update(expires_at=timezone.now() - timedelta(days=1))
        self.assertEqual(_client(self.admin).post(f'/audits/claim/{self.lead.public_token}/').status_code, 404)

    def test_double_claim_returns_audit_and_domain_ids(self):
        first = _client(self.admin).post(f'/audits/claim/{self.lead.public_token}/')
        second = _client(self.admin).post(f'/audits/claim/{self.lead.public_token}/')
        self.assertEqual(second.status_code, 400)
        self.assertEqual(second.data['domain_id'], first.data['domain']['id'])
        self.assertEqual(second.data['audit_id'], self.lead.pk)


@override_settings(**ON, AUDIT_LEAD_ALERT_EMAILS='sales@agency.in, ops@agency.in', AUDIT_WARM_LEAD_OPENS=3, FRONTEND_URL='https://app.example.com')
class LeadAlertTests(_Base):
    """Backend-side alerts: warm lead on the Nth open, claimed lead on claim."""

    def setUp(self):
        super().setUp()
        self.mail = patch('llm_monitor.email_utils.send_mail', return_value=1)
        self.mail_mock = self.mail.start()
        self.addCleanup(self.mail.stop)
        self.seed = patch('domains.keyword_seeder.seed_keywords_in_background')
        self.seed.start()
        self.addCleanup(self.seed.stop)

    def test_warm_lead_fires_once_on_the_threshold(self):
        lead = _done_audit(host='lead.com', website='https://lead.com', source='landing', requester_email='v@example.com')
        c = _client()
        for _ in range(5):
            self.assertEqual(c.get(f'/audits/public/{lead.public_token}/').status_code, 200)
        self.assertEqual(self.mail_mock.call_count, 1)
        subject, body = self.mail_mock.call_args.args[:2]
        self.assertIn('Warm audit lead: lead.com opened 3', subject)
        self.assertIn('v@example.com', body)
        self.assertIn(f'https://app.example.com/audits/{lead.pk}', body)
        self.assertEqual(self.mail_mock.call_args.kwargs['recipient_list'], ['sales@agency.in', 'ops@agency.in'])
        self.assertTrue(self.mail_mock.call_args.kwargs['fail_silently'])

    def test_manual_or_claimed_audits_do_not_raise_warm_alerts(self):
        manual = _done_audit(host='m.com', website='https://m.com', source='manual')
        domain = Domain.objects.create(name='Lead', url='https://c.com', organisation=self.org)
        claimed = _done_audit(host='c.com', website='https://c.com', source='landing', claimed_domain=domain)
        c = _client()
        for a in (manual, claimed):
            for _ in range(4):
                c.get(f'/audits/public/{a.public_token}/')
        self.mail_mock.assert_not_called()

    def test_claim_sends_an_alert(self):
        audit = _done_audit(requested_by=self.admin)
        r = _client(self.admin).post(f'/audits/{audit.pk}/claim/')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.mail_mock.call_count, 1)
        subject, body = self.mail_mock.call_args.args[:2]
        self.assertEqual(subject, 'Audit claimed: hdfcbank.com → HDFC Bank')
        self.assertIn(self.admin.email, body)
        self.assertIn('Agency', body)

    def test_mail_failure_never_breaks_the_request(self):
        self.mail_mock.side_effect = RuntimeError('mailgun down')
        lead = _done_audit(host='lead.com', website='https://lead.com', source='landing')
        c = _client()
        for _ in range(3):
            self.assertEqual(c.get(f'/audits/public/{lead.public_token}/').status_code, 200)
        audit = _done_audit(requested_by=self.admin)
        self.assertEqual(_client(self.admin).post(f'/audits/{audit.pk}/claim/').status_code, 201)

    def test_no_recipients_means_no_mail(self):
        with override_settings(AUDIT_LEAD_ALERT_EMAILS=''):
            lead = _done_audit(host='lead.com', website='https://lead.com', source='landing')
            c = _client()
            for _ in range(3):
                c.get(f'/audits/public/{lead.public_token}/')
        self.mail_mock.assert_not_called()


@override_settings(**ON)
class PdfTests(_Base):
    """The downloadable report: public by token, authenticated by id, DONE only."""

    REPORT = {
        'version': 2,
        'geo': {
            'score': 58, 'stage': 'preferred', 'stage_label': 'Preferred',
            'breakdown': {'placement': 20, 'frequency': 15, 'sourcing': 13, 'framing': 10},
            'engines': [{'platform': 'ChatGPT', 'asked': 6, 'answered': 6, 'mentioned': 4, 'cited': 2, 'mention_rate': 0.67,
                         'avg_position': 1.5, 'top_rival': 'Paisabazaar', 'top_rival_mentions': 3, 'preferred': True}],
            'evidence': [{'prompt_index': 1, 'prompt_text': 'Best savings account?', 'funnel_stage': 'top',
                          'engines': {'ChatGPT': 'cited'}, 'runs': 1, 'best_position': 1, 'top_competitor': 'Paisabazaar',
                          'cited_instead': [], 'gap_type': 'won'},
                         {'prompt_index': 2, 'prompt_text': 'Cheapest home loan & rates <2026>?', 'funnel_stage': 'bottom',
                          'engines': {'ChatGPT': 'absent'}, 'runs': 1, 'best_position': None, 'top_competitor': 'Paisabazaar',
                          'cited_instead': ['paisabazaar.com'], 'gap_type': 'visibility_gap'}],
            'funnel': {'stages': ['top', 'middle', 'bottom'], 'labels': {'top': 'TOFU', 'middle': 'MOFU', 'bottom': 'BOFU'},
                       'platforms': ['ChatGPT'],
                       'cells': {'top': {'ChatGPT': {'asked': 1, 'mentioned': 1, 'cited': 1, 'rate': 100}},
                                 'middle': {'ChatGPT': {'asked': 0, 'mentioned': 0, 'cited': 0, 'rate': None}},
                                 'bottom': {'ChatGPT': {'asked': 1, 'mentioned': 0, 'cited': 0, 'rate': 0}}},
                       'by_stage': {'top': {'label': 'TOFU', 'prompts': 1, 'asked': 1, 'mentioned': 1, 'rate': 100},
                                    'middle': {'label': 'MOFU', 'prompts': 0, 'asked': 0, 'mentioned': 0, 'rate': None},
                                    'bottom': {'label': 'BOFU', 'prompts': 1, 'asked': 1, 'mentioned': 0, 'rate': 0}}},
            'competitors': {'rows': [{'name': 'Paisabazaar', 'is_you': False, 'prompts_ranked': 2, 'prompts_total': 2, 'share': 100,
                                      'mentions': 3, 'avg_position': 1.0,
                                      'stages': {'top': {'ranked': 1, 'of': 1, 'share': 100}, 'middle': {'ranked': 0, 'of': 0, 'share': None},
                                                 'bottom': {'ranked': 1, 'of': 1, 'share': 100}}},
                                     {'name': 'HDFC Bank', 'is_you': True, 'prompts_ranked': 1, 'prompts_total': 2, 'share': 50,
                                      'mentions': 1, 'avg_position': 1.0,
                                      'stages': {'top': {'ranked': 1, 'of': 1, 'share': 100}, 'middle': {'ranked': 0, 'of': 0, 'share': None},
                                                 'bottom': {'ranked': 0, 'of': 1, 'share': 0}}}],
                            'callouts': [{'name': 'Paisabazaar', 'title': 'Paisabazaar — the BOFU default', 'text': 'named on 1 of 1'}]},
            'gap_counts': {'won': 1, 'visibility_gap': 1}, 'runs_per_prompt': 1,
            'share_of_voice': [{'name': 'Paisabazaar', 'mentions': 3, 'share': 75.0, 'is_you': False},
                               {'name': 'HDFC Bank', 'mentions': 1, 'share': 25.0, 'is_you': True}],
            'citation_control': {'owned': 20.0, 'competitor': 60.0, 'third_party': 20.0, 'total_citations': 5,
                                 'top_sources': [{'host': 'paisabazaar.com', 'count': 3}]},
            'runs_total': 2, 'runs_answered': 2,
        },
        'seo': None,
        'crawl': {'pages_sampled': 2, 'urls_discovered': 2, 'robots_present': True, 'bots_allowed': 5, 'bots_total': 5,
                  'bots': [{'bot': 'GPTBot', 'engine': 'ChatGPT', 'allowed': True}], 'sitemap_present': True, 'llms_txt': False,
                  'schema_coverage': 50, 'schema_types': ['Organization'], 'recommended_types_present': ['Organization'],
                  'author_share': 0, 'avg_word_count': 900, 'avg_external_links': 1.0, 'question_heading_share': 50, 'table_share': 0,
                  'dated_pages': 0, 'stale_pages': 0, 'freshest': None,
                  # technical layer (Phase O)
                  'sitemap_children': 3, 'link_check': {'checked': 12, 'broken': 1, 'examples': [{'url': 'https://hdfcbank.com/old-offer', 'status': 404}]},
                  'cwv': {'source': 'field', 'lcp_ms': 3680, 'cls': 0.0, 'inp_ms': 425, 'lcp_ms_rating': 'needs_improvement', 'cls_rating': 'good',
                          'inp_ms_rating': 'needs_improvement', 'performance_score': 65, 'score': 67},
                  'backlinks': {'source': 'dataforseo', 'authority_score': 37, 'referring_domains': 2048, 'referring_domains_nofollow': 300, 'backlinks': 17629,
                                'backlinks_nofollow': 4000, 'dofollow_share': 77, 'broken_backlinks': 120, 'referring_ips': 900, 'referring_pages': 15000,
                                'first_seen': '2019-04-02', 'target': 'hdfcbank.com', 'score': 55},
                  # Phase Q
                  'indexability': {'indexable': 1, 'not_indexable': 1, 'canonicalised': 0, 'redirected': 0, 'unknown': 0},
                  'site': {'hsts': False, 'ssl_error': False, 'http_redirects_to_https': False},
                  'sitemap_health': {'listed': 40, 'checked': 2, 'errors': [{'url': 'https://hdfcbank.com/gone', 'problem': 'HTTP 404'}], 'not_in_sitemap': []},
                  'redirect_chains': 1, 'thin_pages': 1, 'duplicate_groups': [['https://hdfcbank.com/a', 'https://hdfcbank.com/b']],
                  'link_opportunities': [{'from': 'https://hdfcbank.com/blog/nri', 'to': 'https://hdfcbank.com/nri-account', 'topic': 'nri account'}],
                  'issue_delta': {'fixed': [{'key': 'noindex', 'label': 'Pages carrying noindex', 'was': 2}], 'new': [{'key': 'thin_content', 'label': 'Thin content pages', 'count': 1}],
                                  'changed': [{'key': 'missing_h1', 'label': 'Pages without an H1', 'from': 3, 'to': 1}], 'previous_total': 3, 'current_total': 3,
                                  'previous_completed_at': '2026-09-01T10:00:00+00:00', 'previous_health': 61},
                  'avg_internal_links': 31.5, 'descriptive_anchor_share': 88, 'person_schema_share': 0, 'credential_share': 50,
                  'schema_gaps': [{'gap': 'Organization missing description, sameAs', 'pages': 2}],
                  'technical_issues': [
                      {'key': 'broken_links', 'label': 'Broken internal links', 'severity': 'critical', 'count': 1, 'of': 12, 'examples': ['/old-offer (404)'],
                       'fix': 'Links to pages that return errors send crawlers and buyers to dead ends.', 'action': 'Fix the broken internal links'},
                      {'key': 'missing_h1', 'label': 'Pages without an H1', 'severity': 'warning', 'count': 1, 'of': 2, 'examples': ['/'],
                       'fix': 'The H1 tells engines what the page is about.', 'action': 'Add a single H1 to every page'}],
                  'health': {'score': 71, 'categories': [
                      {'key': 'crawlability', 'label': 'AI crawlability', 'weight': 13, 'score': 100, 'priority': 'on_track', 'detail': '5 of 5 AI crawlers allowed'},
                      {'key': 'eeat', 'label': 'E-E-A-T signals', 'weight': 17, 'score': 22, 'priority': 'critical', 'detail': 'bylines on 0%'},
                      {'key': 'cwv', 'label': 'Core Web Vitals', 'weight': 3, 'score': 67, 'priority': 'important', 'detail': 'LCP 3680 ms'}]},
                  'content_patterns': [
                      {'key': 'answer_blocks', 'title': 'Question headings with a short answer block', 'status': 'present', 'evidence': 'question-shaped headings on 50% of sampled pages', 'advice': 'Keep doing it.'},
                      {'key': 'comparison_tables', 'title': 'Comparison tables and feature matrices', 'status': 'missing', 'evidence': 'tables on 0% of sampled pages', 'advice': 'Add comparison tables.'}],
                  'pages': [{'url': 'https://hdfcbank.com/', 'title': 'Home', 'fetched': True, 'word_count': 1200, 'schema_types': ['Organization'],
                             'author': '', 'external_links': 2, 'last_modified': None, 'question_headings': 1, 'has_table': False, 'has_faq_schema': False,
                             'details': {'title_length': 40, 'description_length': 0, 'h1_count': 0, 'noindex': False, 'canonical_status': 'ok',
                                         'viewport': True, 'internal_links': 31, 'depth': 0, 'status_code': 200}}]},
        'measures': [{'key': 'bot_access', 'pillar': 'findable', 'label': 'AI crawlability', 'value': '5 of 5', 'score': 100, 'target': 80, 'evidence': '', 'status': 'pass'},
                     {'key': 'mention_rate', 'pillar': 'chosen', 'label': 'Mention rate', 'value': '67% of runs', 'score': 67, 'target': 80, 'evidence': '', 'status': 'fail'},
                     {'key': 'page_freshness', 'pillar': 'findable', 'label': 'Page freshness', 'value': None, 'score': None, 'target': 70, 'evidence': 'not measured', 'status': None}],
        'pillars': {'findable': 100, 'cited': None, 'chosen': 67},
        'quick_wins': [{'title': 'Earn the citations paisabazaar.com holds on 1 of your prompts', 'why': 'Engines cite it.', 'projected_geo_lift': 3, 'effort_hours': 6}],
        'summary': {'headline': 'HDFC Bank is Preferred but rarely the cited source.', 'source': 'llm',
                    'key_findings': ['Named on 20 of 24 answers.', 'Cited on only 9.', 'Paisabazaar owns BOFU.', 'Perplexity is the weak engine.', 'Findable is strong.'],
                    'sections': {'geo': 'Strong on ChatGPT, weak on Perplexity.', 'competitors': '', 'narrative': 'Framed as established.', 'website': 'Crawlable.', 'plan': 'Three moves first.'}},
        'narrative': {'available': True, 'dominant_framing': 'Established private bank', 'framing_share': 61, 'consistency': 72,
                      'descriptors_present': [{'descriptor': 'Trusted bank', 'share': 61}], 'descriptors_missing': ['NRI expertise'],
                      'by_engine': [{'platform': 'ChatGPT', 'leads_with': 'Interest rates', 'tone': 'positive', 'matches_profile': 'yes'}],
                      'off_brand': [{'platform': 'ChatGPT', 'claim': 'Stricter eligibility than most', 'why': 'site says accessible'}],
                      'narrative_gap': 'Rivals are framed as broader platforms.', 'answers_analysed': 4, 'engines_analysed': ['ChatGPT']},
        'plan': {'today': 58, 'projected': 66, 'status_quo': 55, 'status_quo_note': 'drifts to 55 as cited pages age', 'unscheduled': 0,
                 'buckets': [{'key': 'now', 'label': 'Now', 'subtitle': 'Stop the bleeding', 'from': 58, 'to': 61, 'lift': 3, 'hours': 6,
                              'items': [{'key': 'win:1', 'title': 'Earn the citations paisabazaar.com holds on 1 of your prompts', 'why': 'Engines cite it.',
                                         'projected_geo_lift': 3, 'effort_hours': 6, 'owner': 'content', 'source': 'quick_win'}]},
                             {'key': 'next', 'label': 'Next', 'subtitle': 'Win the biggest answers', 'from': 61, 'to': 66, 'lift': 5, 'hours': 8,
                              'items': [{'key': 'measure:owned_citation_share', 'title': 'Become the page the engines cite', 'why': 'Most citations point elsewhere.',
                                         'projected_geo_lift': 5, 'effort_hours': 8, 'owner': 'content', 'source': 'owned_citation_share'}]},
                             {'key': 'later', 'label': 'Later', 'subtitle': 'Widen the lead', 'from': 66, 'to': 66, 'lift': 0, 'hours': 0, 'items': []}]},
        'config': {'prompt_count': 2, 'engines': ['openai'], 'runs_per_prompt': 1, 'seo_enabled': False, 'keyword_count': 50},
    }

    def _text(self, content):
        import io as _io
        from pypdf import PdfReader
        reader = PdfReader(_io.BytesIO(content))
        return ' '.join((p.extract_text() or '') for p in reader.pages), len(reader.pages)

    def test_public_pdf_downloads_for_a_done_audit(self):
        audit = _done_audit(report=self.REPORT)
        r = _client().get(f'/audits/public/{audit.public_token}/pdf/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/pdf')
        self.assertIn('promptmaxx-audit-hdfcbank.com.pdf', r['Content-Disposition'])
        self.assertTrue(r.content.startswith(b'%PDF'))
        text, pages = self._text(r.content)
        self.assertGreaterEqual(pages, 2)
        for needle in ('HDFC Bank', 'GEO audit', 'Prompt evidence', 'Funnel stage heatmap', 'Competitor matrix',
                       'Website health', 'Findable', 'Quick wins', 'Visibility plan', 'Stop the bleeding', 'Become the page the engines cite',
                       'Brand narrative', 'Established private bank', 'NRI expertise', 'Stricter eligibility',
                       'Key findings', 'Paisabazaar owns BOFU', 'rarely the cited source', 'Strong on ChatGPT, weak on Perplexity',
                       'Methodology', 'Paisabazaar', 'Visibility gap', 'Cheapest home loan & rates <2026>?',
                       # Phase O technical layer
                       'Website health scorecard', 'E-E-A-T signals', 'Core Web Vitals', '3680 ms', 'Technical SEO issues',
                       'Backlink analysis', '37/100', '2,048', '17,629', '77% dofollow',
                       'Indexability', 'both versions reachable', 'Sitemap health', '40 URLs listed', 'Since the previous audit', 'health was 61',
                       'Internal link opportunities', 'nri account', 'Redirect chains',
                       'Broken internal links', 'Fix the broken internal links', 'Winning content patterns', 'feature matrices',
                       'index with 3', '1 of 12 broken', 'no description'):
            self.assertIn(needle, text, needle)
        # a public download does not count as a report open
        audit.refresh_from_db()
        self.assertEqual(audit.opens, 0)

    def test_issues_csv_download(self):
        audit = _done_audit(requested_by=self.admin, report=self.REPORT)
        r = _client().get(f'/audits/public/{audit.public_token}/issues.csv')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r['Content-Type'].startswith('text/csv'))
        self.assertIn('promptmaxx-issues-hdfcbank.com.csv', r['Content-Disposition'])
        body = r.content.decode('utf-8-sig')
        lines = body.strip().splitlines()
        self.assertEqual(lines[0], 'severity,issue,url,action,why,how_to_fix,pages_affected,of')
        self.assertIn('critical,Broken internal links,/old-offer (404),Fix the broken internal links', body)
        self.assertIn('warning,Pages without an H1,/,Add a single H1 to every page', body)
        # owner route + no-issue-list report
        r2 = _client(self.admin).get(f'/audits/{audit.pk}/issues.csv')
        self.assertEqual(r2.status_code, 200)
        old = _done_audit(report={'version': 1, 'geo': {'score': 58, 'engines': [], 'evidence': []}, 'measures': [], 'quick_wins': []})
        self.assertEqual(_client().get(f'/audits/public/{old.public_token}/issues.csv').status_code, 404)

    def test_pdf_survives_an_old_minimal_report(self):
        audit = _done_audit(report={'version': 1, 'geo': {'score': 58, 'engines': [], 'evidence': []}, 'measures': [], 'quick_wins': []})
        r = _client().get(f'/audits/public/{audit.public_token}/pdf/')
        self.assertEqual(r.status_code, 200)
        text, _ = self._text(r.content)
        self.assertIn('HDFC Bank', text)
        self.assertIn('Methodology', text)

    def test_unfinished_expired_and_unknown(self):
        running = Audit.objects.create(host='x.com', website='https://x.com', status='PROC')
        self.assertEqual(_client().get(f'/audits/public/{running.public_token}/pdf/').status_code, 409)
        expired = _done_audit(host='e.com', website='https://e.com', expires_at=timezone.now() - timedelta(days=1))
        self.assertEqual(_client().get(f'/audits/public/{expired.public_token}/pdf/').status_code, 404)
        self.assertEqual(_client().get('/audits/public/nope/pdf/').status_code, 404)

    def test_authenticated_pdf_respects_visibility(self):
        audit = _done_audit(requested_by=self.admin, report=self.REPORT)
        self.assertEqual(_client().get(f'/audits/{audit.pk}/pdf/').status_code, 401)
        self.assertEqual(_client(self.client_user).get(f'/audits/{audit.pk}/pdf/').status_code, 403)
        self.assertEqual(_client(self.other_admin).get(f'/audits/{audit.pk}/pdf/').status_code, 404)
        r = _client(self.admin).get(f'/audits/{audit.pk}/pdf/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/pdf')

    def test_build_failure_is_a_clean_500_not_a_crash(self):
        audit = _done_audit(report=self.REPORT)
        with patch('audits.pdf.build_audit_pdf', side_effect=RuntimeError('font missing')):
            r = _client().get(f'/audits/public/{audit.public_token}/pdf/')
        self.assertEqual(r.status_code, 500)
        self.assertIn('Could not build the PDF', r.data['error'])


@override_settings(**ON)
class ApiKeySourceTests(_Base):
    """A service API key files the audit under source 'api' and is trusted like an admin."""

    def setUp(self):
        super().setUp()
        import hashlib
        from authentication.models import ServiceApiKey
        self.service = _user(self.org, 'client', 'svc')
        self.raw = 'pmxk_test_' + 'x' * 20
        self.key = ServiceApiKey.objects.create(organisation=self.org, service_account=self.service, created_by=self.admin,
                                                name='enque', key_hash=hashlib.sha256(self.raw.encode()).hexdigest(), key_prefix='pmxk_...xxxx')

    def _api(self):
        # The real header, so ApiKeyAuthentication AND the client-write
        # middleware both run — force_authenticate would skip the middleware.
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f'Api-Key {self.raw}')
        return c

    def test_api_key_creates_an_api_audit(self):
        with override_settings(AUDIT_PER_IP_DAILY=1):
            for host in ('a.com', 'b.com'):
                r = self._api().post('/audits/', {'url': host}, format='json', REMOTE_ADDR='203.0.113.9')
                self.assertEqual(r.status_code, 201, r.data)
        audit = Audit.objects.get(host='a.com')
        self.assertEqual(audit.source, 'api')
        self.assertEqual(audit.requested_by, self.service)
        # ...and the org admin sees it in the leads table
        self.assertIn('a.com', [row['host'] for row in _client(self.admin).get('/audits/').data['results']])

    def test_api_key_may_force_a_fresh_audit(self):
        self._api().post('/audits/', {'url': 'a.com'}, format='json')
        r = self._api().post('/audits/', {'url': 'a.com', 'force': True}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Audit.objects.filter(host='a.com').count(), 2)

    def test_plain_client_user_is_still_a_landing_source(self):
        r = _client(self.client_user).post('/audits/', {'url': 'c.com'}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Audit.objects.get(host='c.com').source, 'landing')


@override_settings(**ON)
class ClaimSeedsPromptsTests(_Base):
    def setUp(self):
        super().setUp()
        self.seed = patch('domains.keyword_seeder.seed_keywords_in_background')
        self.seed.start()
        self.addCleanup(self.seed.stop)
        self.audit = _done_audit(requested_by=self.admin, grounding={
            'profile': {'description': 'A bank.'},
            'prompts': [
                {'index': 1, 'text': 'Best savings account in India?', 'topic': 'savings accounts', 'funnel_stage': 'top'},
                {'index': 2, 'text': 'Which bank has the highest FD rate?', 'topic': 'savings accounts', 'funnel_stage': 'middle'},
                {'index': 3, 'text': 'Cheapest home loan?', 'topic': 'home loans', 'funnel_stage': 'bottom'},
                {'index': 4, 'text': '   ', 'topic': 'home loans', 'funnel_stage': 'bottom'},
            ],
        })

    def test_claim_creates_groups_and_prompts_in_init(self):
        from prompts.models import Prompt, PromptGroup
        r = _client(self.admin).post(f'/audits/{self.audit.pk}/claim/')
        self.assertEqual(r.status_code, 201, r.data)
        domain_id = r.data['domain']['id']
        groups = {g.group_id: g for g in PromptGroup.objects.filter(domain_id=domain_id)}
        self.assertEqual(set(groups), {'Savings Accounts', 'Home Loans'})
        self.assertTrue(all(g.track_status == 'INIT' for g in groups.values()))
        self.assertIn('Seeded from audit', groups['Savings Accounts'].track_message)
        savings = list(Prompt.objects.filter(group=groups['Savings Accounts']).order_by('id'))
        self.assertEqual([p.prompt for p in savings], ['Best savings account in India?', 'Which bank has the highest FD rate?'])
        self.assertEqual([p.type for p in savings], ['primary', 'secondary'])
        self.assertTrue(all(p.track_status == 'INIT' for p in savings))
        self.assertEqual(Prompt.objects.filter(group=groups['Home Loans']).count(), 1, 'blank prompt text is skipped')

    def test_seeding_can_be_switched_off(self):
        from prompts.models import PromptGroup
        with override_settings(AUDIT_CLAIM_SEEDS_PROMPTS=False):
            r = _client(self.admin).post(f'/audits/{self.audit.pk}/claim/')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(PromptGroup.objects.filter(domain_id=r.data['domain']['id']).count(), 0)

    def test_seeding_failure_does_not_break_the_claim(self):
        with patch('audits.services.seed_prompts_from_audit', side_effect=RuntimeError('db hiccup')):
            r = _client(self.admin).post(f'/audits/{self.audit.pk}/claim/')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Domain.objects.count(), 1)


class CleanupCommandTests(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name='Agency')
        self.admin = _user(self.org, 'admin', 'c1')

    def _with_evidence(self, **over):
        audit = _done_audit(**over)
        AuditPromptResult.objects.create(audit=audit, prompt_index=1, prompt_text='q?', platform='ChatGPT', response_text='long answer')
        AuditPageResult.objects.create(audit=audit, url=f'https://{audit.host}/')
        audit.grounding = {'profile': {'description': 'x'}, 'prompts': [{'index': 1, 'text': 'q?'}], 'crawl': {'complete': True}, 'narrative': {'available': True}}
        audit.save(update_fields=['grounding'])
        return audit

    def test_trims_expired_unclaimed_keeps_claimed_and_recent(self):
        from io import StringIO
        from django.core.management import call_command
        old = self._with_evidence(host='old.com', website='https://old.com', expires_at=timezone.now() - timedelta(days=45))
        recent = self._with_evidence(host='recent.com', website='https://recent.com', expires_at=timezone.now() - timedelta(days=2))
        domain = Domain.objects.create(name='Kept', url='https://kept.com', organisation=self.org)
        kept = self._with_evidence(host='kept.com', website='https://kept.com', expires_at=timezone.now() - timedelta(days=400), claimed_domain=domain)
        failed_old = Audit.objects.create(host='f.com', website='https://f.com', status='FAIL')
        Audit.objects.filter(pk=failed_old.pk).update(created_at=timezone.now() - timedelta(days=60))
        failed_new = Audit.objects.create(host='g.com', website='https://g.com', status='FAIL')

        out = StringIO()
        call_command('cleanup_audits', '--days', '30', '--dry-run', stdout=out)
        self.assertIn('would trim audit', out.getvalue())
        self.assertEqual(AuditPromptResult.objects.filter(audit=old).count(), 1, 'dry run changes nothing')

        out = StringIO()
        call_command('cleanup_audits', '--days', '30', stdout=out)
        self.assertIn('1 audits trimmed, 1 failed audits deleted', out.getvalue())
        old.refresh_from_db()
        self.assertEqual(AuditPromptResult.objects.filter(audit=old).count(), 0)
        self.assertEqual(AuditPageResult.objects.filter(audit=old).count(), 0)
        self.assertEqual(old.status, 'DONE', 'the row and its report survive')
        self.assertEqual(old.report, {'version': 1, 'geo': {'score': 58}})
        self.assertNotIn('prompts', old.grounding)
        self.assertIn('profile', old.grounding)
        self.assertIn('trimmed_at', old.grounding)
        self.assertEqual(AuditPromptResult.objects.filter(audit=recent).count(), 1)
        self.assertEqual(AuditPromptResult.objects.filter(audit=kept).count(), 1)
        self.assertFalse(Audit.objects.filter(pk=failed_old.pk).exists())
        self.assertTrue(Audit.objects.filter(pk=failed_new.pk).exists())
        # idempotent: a second run finds nothing
        out = StringIO()
        call_command('cleanup_audits', '--days', '30', stdout=out)
        self.assertIn('0 audits trimmed, 0 failed audits deleted', out.getvalue())
