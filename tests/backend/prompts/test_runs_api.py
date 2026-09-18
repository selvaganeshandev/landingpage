"""
Tests for the Runs ledger endpoints (prompts/views_runs.py).

The engine already writes one PromptAnalyticsRun per prompt x engine execution;
these endpoints only read it. What matters here is that the read is correct and
that it cannot leak another organisation's domain:

  * access: anonymous 401, no DomainAccess 403, own domain 200, super_admin any
  * list: newest first, pagination, and every filter (engine, group, mention,
    cited, prompt, search, window)
  * summary: totals, averages, confidence band, low-confidence count, per engine
  * export: CSV header, one row per run, filters respected
  * a domain with no runs answers with zeros rather than an error
"""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from authentication.models import Account, Organisation
from domains.models import Domain, DomainAccess
from prompts.models import Prompt, PromptAnalyticsRun, PromptGroup
from prompts.views_runs import confidence_for


def _client(user=None):
    c = APIClient()
    if user is not None:
        c.force_authenticate(user=user)
    return c


class _Base(TestCase):
    def setUp(self):
        self.org = Organisation.objects.create(name='Agency')
        self.other_org = Organisation.objects.create(name='Other')
        self.admin = Account.objects.create_user(
            username='admin', email='admin@example.com', password='pw', organisation=self.org, role='admin')
        self.outsider = Account.objects.create_user(
            username='outsider', email='out@example.com', password='pw', organisation=self.other_org, role='admin')
        self.super_admin = Account.objects.create_user(
            username='super', email='super@example.com', password='pw', organisation=self.other_org, role='super_admin')

        self.domain = Domain.objects.create(name='HDFC Bank', url='https://hdfcbank.com', organisation=self.org)
        DomainAccess.objects.create(user=self.admin, domain=self.domain, granted_by=self.admin)

        self.loans = PromptGroup.objects.create(group_id='g-loans', theme='Loans', domain=self.domain)
        self.cards = PromptGroup.objects.create(group_id='g-cards', theme='Cards', domain=self.domain)
        self.p_loan = Prompt.objects.create(prompt='Best home loan rates in India?', group=self.loans)
        self.p_card = Prompt.objects.create(prompt='Which credit card has no annual fee?', group=self.cards)

        now = timezone.now()
        # p_loan: 3 runs on ChatGPT (2 mentions, 1 with citations), 1 on Gemini (no mention)
        self._run(self.p_loan, 'ChatGPT', now - timedelta(hours=1), mention=True, position=2, citations=3)
        self._run(self.p_loan, 'ChatGPT', now - timedelta(hours=2), mention=True, position=4, citations=0)
        self._run(self.p_loan, 'ChatGPT', now - timedelta(hours=3), mention=False)
        self._run(self.p_loan, 'Google Gemini', now - timedelta(hours=4), mention=False)
        # p_card: 1 run, and one outside the 30-day window
        self._run(self.p_card, 'ChatGPT', now - timedelta(days=2), mention=True, position=1, citations=1)
        self.old_run = self._run(self.p_card, 'ChatGPT', now - timedelta(days=90), mention=True)

    def _run(self, prompt, platform, when, mention=False, position=0, citations=0, sentiment='neutral'):
        return PromptAnalyticsRun.objects.create(
            prompt=prompt, platform=platform, region='IN', tracked_at=when,
            is_mention=mention, total_mentions=1 if mention else 0, total_citations=citations,
            position=position, sentiment_category=sentiment, sentiment_score=0.0,
            citation_list=[f'https://hdfcbank.com/{prompt.id}'] if citations else [],
            competitor_mention_list=['ICICI Bank'] if mention else [],
            context_summary='Answer text.',
        )

    def get(self, path, user=None, **params):
        params.setdefault('domain_id', self.domain.id)
        return _client(user or self.admin).get(path, params)


class AccessTests(_Base):
    def test_anonymous_is_rejected(self):
        for path in ('/prompts/runs/', '/prompts/runs/summary/', '/prompts/runs/export/'):
            self.assertEqual(_client().get(path, {'domain_id': self.domain.id}).status_code, 401, path)

    def test_other_org_cannot_read_the_ledger(self):
        for path in ('/prompts/runs/', '/prompts/runs/summary/', '/prompts/runs/export/'):
            self.assertEqual(self.get(path, user=self.outsider).status_code, 403, path)

    def test_super_admin_reads_any_domain(self):
        self.assertEqual(self.get('/prompts/runs/', user=self.super_admin).status_code, 200)

    def test_org_admin_without_an_explicit_grant_reads_own_org_only(self):
        # "Global domain access" widens an admin to their own organisation's
        # domains; it must not reach across organisations.
        colleague = Account.objects.create_user(
            username='colleague', email='colleague@example.com', password='pw',
            organisation=self.org, role='admin')
        self.assertFalse(DomainAccess.objects.filter(user=colleague, domain=self.domain).exists())
        self.assertEqual(self.get('/prompts/runs/', user=colleague).status_code, 200)

        foreign = Domain.objects.create(name='Rival', url='https://rival.com', organisation=self.other_org)
        r = _client(colleague).get('/prompts/runs/', {'domain_id': foreign.id})
        self.assertEqual(r.status_code, 403, 'another organisation stays out of reach')

    def test_domain_id_is_required(self):
        r = _client(self.admin).get('/prompts/runs/')
        self.assertEqual(r.status_code, 400)
        self.assertIn('domain_id', r.data['error'])


class ListTests(_Base):
    def test_newest_first_inside_the_window(self):
        r = self.get('/prompts/runs/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['total_count'], 5, 'the 90-day-old run is outside the default window')
        stamps = [row['tracked_at'] for row in r.data['runs']]
        self.assertEqual(stamps, sorted(stamps, reverse=True))
        first = r.data['runs'][0]
        self.assertEqual(first['prompt'], 'Best home loan rates in India?')
        self.assertEqual(first['group'], 'Loans', 'the group theme is the label')
        self.assertEqual((first['platform'], first['is_mention'], first['position'], first['total_citations']),
                         ('ChatGPT', True, 2.0, 3))
        self.assertEqual(first['competitors'], ['ICICI Bank'])
        self.assertEqual(first['context_summary'], 'Answer text.')

    def test_window_can_be_widened(self):
        self.assertEqual(self.get('/prompts/runs/', days=365).data['total_count'], 6)

    def test_explicit_date_range(self):
        today = timezone.now().date()
        r = self.get('/prompts/runs/', start_date=str(today - timedelta(days=1)), end_date=str(today))
        self.assertEqual(r.data['total_count'], 4, 'only today and yesterday')

    def test_filters(self):
        self.assertEqual(self.get('/prompts/runs/', platform='ChatGPT').data['total_count'], 4)
        self.assertEqual(self.get('/prompts/runs/', platform='Google Gemini').data['total_count'], 1)
        self.assertEqual(self.get('/prompts/runs/', group_id=self.cards.id).data['total_count'], 1)
        self.assertEqual(self.get('/prompts/runs/', prompt_id=self.p_loan.id).data['total_count'], 4)
        self.assertEqual(self.get('/prompts/runs/', mention='yes').data['total_count'], 3)
        self.assertEqual(self.get('/prompts/runs/', mention='no').data['total_count'], 2)
        self.assertEqual(self.get('/prompts/runs/', cited='yes').data['total_count'], 2)
        self.assertEqual(self.get('/prompts/runs/', search='credit card').data['total_count'], 1)
        self.assertEqual(self.get('/prompts/runs/', search='nothing here').data['total_count'], 0)

    def test_pagination(self):
        r = self.get('/prompts/runs/', limit=2, offset=0)
        self.assertEqual((len(r.data['runs']), r.data['total_count'], r.data['limit']), (2, 5, 2))
        second = self.get('/prompts/runs/', limit=2, offset=2)
        self.assertEqual(len(second.data['runs']), 2)
        self.assertNotEqual(r.data['runs'][0]['id'], second.data['runs'][0]['id'])
        # a silly limit is clamped, not an error
        self.assertLessEqual(len(self.get('/prompts/runs/', limit=9999).data['runs']), 200)
        self.assertEqual(self.get('/prompts/runs/', limit='abc').status_code, 200)

    def test_domain_without_runs_is_empty_not_broken(self):
        quiet = Domain.objects.create(name='Quiet', url='https://quiet.com', organisation=self.org)
        DomainAccess.objects.create(user=self.admin, domain=quiet, granted_by=self.admin)
        r = _client(self.admin).get('/prompts/runs/', {'domain_id': quiet.id})
        self.assertEqual((r.status_code, r.data['total_count'], r.data['runs']), (200, 0, []))


class SummaryTests(_Base):
    def test_totals_and_confidence(self):
        d = self.get('/prompts/runs/summary/').data
        self.assertEqual(d['total_runs'], 5)
        self.assertEqual(d['variants'], 2)
        self.assertEqual(d['engines'], 2)
        self.assertEqual(d['avg_runs_per_variant'], 2.5)
        self.assertEqual(d['confidence']['level'], 'low')
        self.assertEqual(d['low_confidence_variants'], 2, 'both variants sit under 6 runs')
        self.assertEqual(d['mentioned_runs'], 3)
        self.assertEqual(d['cited_runs'], 2)
        self.assertEqual(d['mention_rate'], 60)
        self.assertEqual(d['citation_rate'], 40)
        self.assertEqual(d['avg_position'], 2.3, 'positions 2, 4 and 1 on mentioned runs')
        self.assertIsNotNone(d['last_run_at'])

    def test_per_engine_breakdown(self):
        rows = {r['platform']: r for r in self.get('/prompts/runs/summary/').data['by_platform']}
        self.assertEqual(rows['ChatGPT']['runs'], 4)
        self.assertEqual(rows['ChatGPT']['mentioned'], 3)
        self.assertEqual(rows['ChatGPT']['mention_rate'], 75)
        self.assertEqual(rows['ChatGPT']['variants'], 2)
        self.assertEqual(rows['Google Gemini']['runs'], 1)
        self.assertEqual(rows['Google Gemini']['mention_rate'], 0)

    def test_filters_narrow_the_summary_too(self):
        d = self.get('/prompts/runs/summary/', platform='Google Gemini').data
        self.assertEqual((d['total_runs'], d['variants'], d['mention_rate']), (1, 1, 0))
        self.assertIsNone(d['avg_position'], 'no mentioned run means no average position')

    def test_empty_domain_summary_is_zeroed(self):
        quiet = Domain.objects.create(name='Quiet', url='https://quiet.com', organisation=self.org)
        DomainAccess.objects.create(user=self.admin, domain=quiet, granted_by=self.admin)
        d = _client(self.admin).get('/prompts/runs/summary/', {'domain_id': quiet.id}).data
        self.assertEqual((d['total_runs'], d['variants'], d['avg_runs_per_variant']), (0, 0, 0.0))
        self.assertEqual(d['confidence']['level'], 'none')
        self.assertIsNone(d['last_run_at'])
        self.assertEqual(d['by_platform'], [])

    def test_confidence_bands(self):
        self.assertEqual(confidence_for(25)['level'], 'high')
        self.assertEqual(confidence_for(9)['level'], 'good')
        self.assertEqual(confidence_for(4)['level'], 'fair')
        self.assertEqual(confidence_for(1)['level'], 'low')
        self.assertEqual(confidence_for(0)['level'], 'none')


class RunNumberAndVarianceTests(_Base):
    def test_run_number_counts_repeats_of_the_same_question(self):
        rows = self.get('/prompts/runs/', prompt_id=self.p_loan.id, platform='ChatGPT').data['runs']
        # newest first, so the newest of three ChatGPT runs is run 3
        self.assertEqual([r['run_number'] for r in rows], [3, 2, 1])
        self.assertTrue(all(r['runs_for_prompt'] == 3 for r in rows))

    def test_run_number_is_scoped_to_the_window(self):
        rows = self.get('/prompts/runs/', prompt_id=self.p_card.id, days=365).data['runs']
        self.assertEqual([r['run_number'] for r in rows], [2, 1], 'the 90-day-old run is run 1 once the window includes it')
        narrow = self.get('/prompts/runs/', prompt_id=self.p_card.id, days=30).data['runs']
        self.assertEqual([r['run_number'] for r in narrow], [1])

    def test_variance_only_keeps_questions_the_engines_disagreed_on(self):
        # p_loan: 2 mentions + 1 miss on ChatGPT (disagreement). p_card: all mentions.
        rows = self.get('/prompts/runs/', variance='only').data['runs']
        self.assertEqual({r['prompt_id'] for r in rows}, {self.p_loan.id})
        self.assertEqual(self.get('/prompts/runs/', variance='only').data['total_count'], 4)
        self.assertEqual(self.get('/prompts/runs/', variance='only', platform='ChatGPT').data['total_count'], 3)

    def test_summary_lists_groups_and_counts_unstable_questions(self):
        d = self.get('/prompts/runs/summary/').data
        labels = {g['label']: g['runs'] for g in d['groups']}
        self.assertEqual(labels, {'Loans': 4, 'Cards': 1})
        self.assertTrue(all(g['id'] for g in d['groups']))
        self.assertEqual(d['unstable_variants'], 1, 'only the loan question disagrees with itself')


class ExportTests(_Base):
    def test_csv_contains_one_row_per_run(self):
        r = self.get('/prompts/runs/export/')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r['Content-Type'].startswith('text/csv'))
        self.assertIn(f'promptmaxx-runs-{self.domain.id}.csv', r['Content-Disposition'])
        body = r.content.decode('utf-8-sig')
        lines = [ln for ln in body.strip().splitlines() if ln]
        self.assertEqual(lines[0], 'run_at,engine,region,group,prompt,run_number,mentioned,mentions,position,citations,sentiment,sentiment_score,cited_urls,competitors')
        self.assertEqual(len(lines), 6, 'header + 5 runs in the window')
        self.assertIn('Best home loan rates in India?', body)
        self.assertIn('ICICI Bank', body)

    def test_export_respects_filters(self):
        body = self.get('/prompts/runs/export/', platform='Google Gemini').content.decode('utf-8-sig')
        lines = [ln for ln in body.strip().splitlines() if ln]
        self.assertEqual(len(lines), 2)
        self.assertIn('Google Gemini', body)
