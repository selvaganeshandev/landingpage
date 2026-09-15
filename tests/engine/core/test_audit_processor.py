"""
Tests for core.audit_processor — the six-stage Audit Engine pipeline.

Every network edge is mocked (site fetch, internal LLM, the measured engine
handlers, SERP, volume); what is under test is the glue: stage ordering, what
each stage writes to the row, resumability after a restart, the feature flag,
failure handling, and the SEO stage gate.

  * flag off -> nothing runs, row untouched
  * happy path (GEO only) -> DONE, evidence rows, headline scores, report, expiry
  * a failing engine is recorded as failed/rate_limited, not as "absent"
  * an engine with no key is 'skipped' and excluded from denominators
  * restart mid-engines resumes: already-stored (prompt, engine) pairs are not re-asked
  * every engine failing -> FAIL with a readable error, no DONE
  * unreadable site -> profile from model knowledge, still completes
  * SEO enabled -> keywords discovered, ranked, stored; report carries the seo block
  * FAIL / DONE rows are not re-run by a stray task
"""
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from core import audit_processor as ap
from shared_models.audit_models import Audit, AuditKeywordResult, AuditPageResult, AuditPromptResult


PROFILE = {
    'brand_name': 'HDFC Bank', 'industry': 'Retail banking',
    'description': 'A large Indian private bank.', 'categories': ['savings accounts', 'home loans'],
    'audience': 'salaried professionals', 'regions': ['India'],
    'use_cases': ['salary account'], 'buying_criteria': ['interest rate'],
    'competitors': [{'name': 'ICICI Bank', 'website': 'https://www.icicibank.com'}, {'name': 'Paisabazaar', 'website': None}],
}
ENTITIES = {'categories': ['savings accounts', 'home loans'], 'use_cases': ['salary account'],
            'audiences': ['students'], 'problems': ['high fees'], 'criteria': ['interest rate']}


def fake_expand(client, model, ground, plan):
    """Render the plan deterministically — one distinct question per tuple."""
    return [{**item, 'text': f"{item['intent']} question {i} about {item['entity']}?"} for i, item in enumerate(plan)], 0


def make_handler(mention=True, cited=True, fail=False, rate_limit=False, rival='Paisabazaar'):
    def handler(prompt_text, user_domain, client, group):
        if rate_limit:
            raise RuntimeError('429 rate limited')
        if fail:
            raise RuntimeError('boom')
        text = f"1. {group.domain.name} is good. 2. {rival} too. https://hdfcbank.com/x https://paisabazaar.com/y"
        return {
            'response_text': text, 'context_summary': text,
            'is_mention': mention, 'has_citation': cited, 'citations': ['https://hdfcbank.com/x'] if cited else [],
            'sentiment': 'positive', 'all_urls': ['https://hdfcbank.com/x', 'https://paisabazaar.com/y'],
            'competitor_mention_list': [rival, 'hdfcbank.com'],
        }
    return handler


class _Base(TestCase):
    """Wires the mocks; subclasses tweak `engines` before calling run()."""

    def setUp(self):
        self.audit = Audit.objects.create(
            public_token='tok-' + str(id(self))[-8:], host='hdfcbank.com',
            website='https://hdfcbank.com', country='in', source='manual',
        )
        self.engines = [
            ('chatgpt', 'ChatGPT', make_handler(), object()),
            ('claude', 'Claude', make_handler(mention=True, cited=False), object()),
        ]
        self.site = ('<html><body>' + 'HDFC Bank savings ' * 40 + '</body></html>', 'HDFC Bank savings ' * 40, None)
        self.narrative_llm = {'dominant_framing': 'Established bank', 'framing_share': 60, 'consistency': 70,
                              'descriptors_present': [{'descriptor': 'Trusted', 'share': 60}], 'descriptors_missing': ['NRI expertise'],
                              'by_engine': [{'platform': 'ChatGPT', 'leads_with': 'Rates', 'tone': 'positive', 'matches_profile': 'yes'}],
                              'off_brand': [], 'narrative_gap': 'Rivals are framed as broader.'}
        # _chat_json answers: profile first, then whatever the stages ask (keywords, narrative) — the
        # narrative call is recognised by its system prompt and served from narrative_llm.
        self.summary_llm = {'headline': 'HDFC Bank is doing fine.', 'key_findings': ['one 1', 'two 2', 'three 3'], 'sections': {}}
        self.llm_json = [PROFILE]  # consumed in order by _chat_json
        self.crawl = {
            'robots': {'present': True, 'allowed': {'GPTBot': True}, 'sitemaps': []},
            'summary': {'pages_sampled': 2, 'bots_allowed': 5, 'bots_total': 5, 'schema_coverage': 50,
                        'recommended_types_present': ['Organization'], 'author_share': 0, 'avg_word_count': 900,
                        'avg_external_links': 1.0, 'dated_pages': 1, 'stale_pages': 0, 'seconds': 1.2},
            'pages': [
                {'url': 'https://hdfcbank.com/', 'title': 'Home', 'word_count': 1200, 'schema_types': ['Organization'],
                 'author': '', 'external_links': 2, 'last_modified': '2026-08-01', 'question_headings': 1, 'has_table': False, 'has_faq_schema': False},
                {'url': 'https://hdfcbank.com/savings', 'parse_error': 'fetch failed'},
            ],
            'measures': {
                'bot_access': {'value': '5 of 5 AI crawlers', 'score': 100, 'evidence': 'all allowed'},
                'answer_structure': {'value': 'schema on 50%', 'score': 40, 'evidence': ''},
                'authority_signals': {'value': 'bylines on 0%', 'score': 26, 'evidence': ''},
                'page_freshness': {'value': '0 of 1 dated pages 12mo+', 'score': 100, 'evidence': ''},
            },
        }

        patches = [
            patch.object(ap, 'fetch_site', side_effect=lambda website: self.site),
            patch.object(ap, '_internal_llm', return_value=(object(), 'test-model')),
            patch.object(ap, '_chat_json', side_effect=lambda client, model, system, user, **k: (
                self.narrative_llm if 'how AI assistants describe a brand' in system
                else self.summary_llm if 'executive summary' in system
                else self.llm_json.pop(0))),
            patch('core.prompt_generation.stage_entities', return_value=(ENTITIES, 0)),
            patch('core.prompt_generation.stage_expand', side_effect=fake_expand),
            patch.object(ap.AuditProcessor, '_resolve_engines', side_effect=lambda: self.engines),
            patch('core.analytics_helpers.extract_position_from_response', return_value=1),
            # The crawl stage is network-only; tests feed it a canned result.
            patch('core.audit_crawl.crawl_site', side_effect=lambda *a, **k: self.crawl),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def run_audit(self):
        with override_settings(AUDIT_ENGINE_ENABLED=True, AUDIT_PROMPT_COUNT=4, AUDIT_SEO_ENABLED=False,
                               AUDIT_ENGINES=['openai', 'gemini', 'anthropic', 'perplexity'], AUDIT_RUNS_PER_PROMPT=1):
            return ap.run_audit(self.audit.pk)


class FlagTests(_Base):
    def test_flag_off_runs_nothing(self):
        with override_settings(AUDIT_ENGINE_ENABLED=False):
            result = ap.run_audit(self.audit.pk)
        self.audit.refresh_from_db()
        self.assertEqual(result['status'], 'disabled')
        self.assertEqual(self.audit.status, 'INIT')
        self.assertEqual(self.audit.stage, '')
        self.assertEqual(AuditPromptResult.objects.count(), 0)

    def test_missing_audit(self):
        with override_settings(AUDIT_ENGINE_ENABLED=True):
            self.assertEqual(ap.run_audit(999999)['status'], 'missing')

    def test_done_and_failed_rows_are_not_rerun(self):
        Audit.objects.filter(pk=self.audit.pk).update(status='DONE')
        self.assertEqual(self.run_audit()['status'], 'already_done')
        Audit.objects.filter(pk=self.audit.pk).update(status='FAIL')
        self.assertEqual(self.run_audit()['status'], 'failed_previously')


class HappyPathTests(_Base):
    def test_geo_only_audit_completes(self):
        result = self.run_audit()
        self.assertEqual(result['status'], 'done', result)
        a = Audit.objects.get(pk=self.audit.pk)

        # row state
        self.assertEqual(a.status, 'DONE')
        self.assertEqual(a.stage, 'publish')
        self.assertEqual(a.progress, 100)
        self.assertIsNotNone(a.completed_at)
        self.assertIsNotNone(a.expires_at)
        self.assertEqual(a.error, '')

        # profile
        self.assertEqual(a.brand_name, 'HDFC Bank')
        self.assertEqual(a.industry, 'Retail banking')
        self.assertEqual(a.competitors, [{'name': 'ICICI Bank', 'host': 'icicibank.com'}, {'name': 'Paisabazaar', 'host': ''}])
        self.assertEqual(a.grounding['profile']['source'], 'site')
        self.assertEqual(a.config['engines'], ['openai', 'gemini', 'anthropic', 'perplexity'])
        self.assertEqual(a.config['prompt_count'], 4)

        # prompts: 4 asked, funnel mix present
        prompts = a.grounding['prompts']
        self.assertEqual(len(prompts), 4)
        self.assertEqual([p['index'] for p in prompts], [1, 2, 3, 4])
        self.assertTrue({p['funnel_stage'] for p in prompts} <= {'top', 'middle', 'bottom'})
        self.assertGreaterEqual(len({p['funnel_stage'] for p in prompts}), 2)

        # crawl: page rows stored, Findable measured, report carries the block
        self.assertEqual(AuditPageResult.objects.filter(audit=a).count(), 2)
        home = AuditPageResult.objects.get(audit=a, url='https://hdfcbank.com/')
        self.assertTrue(home.fetched)
        self.assertEqual(home.schema_types, ['Organization'])
        self.assertEqual(str(home.last_modified), '2026-08-01')
        failed_page = AuditPageResult.objects.get(audit=a, url='https://hdfcbank.com/savings')
        self.assertFalse(failed_page.fetched)
        self.assertEqual(failed_page.error, 'fetch failed')
        self.assertTrue(a.grounding['crawl']['complete'])
        self.assertEqual(a.stage_detail['crawl'], {'pages': 2, 'seconds': 1.2})
        findable = {m['key']: m for m in a.report['measures'] if m['pillar'] == 'findable'}
        self.assertEqual(findable['bot_access']['score'], 100)
        self.assertEqual(findable['answer_structure']['score'], 40)
        self.assertEqual(a.report['pillars']['findable'], round((100 + 40 + 26 + 100) / 4))
        self.assertEqual(a.report['crawl']['pages_sampled'], 2)
        self.assertEqual(len(a.report['crawl']['pages']), 2)
        self.assertEqual(a.report['crawl']['pages'][0]['last_modified'], '2026-08-01')

        # evidence: 4 prompts x 2 engines
        rows = AuditPromptResult.objects.filter(audit=a)
        self.assertEqual(rows.count(), 8)
        self.assertEqual(set(rows.values_list('platform', flat=True)), {'ChatGPT', 'Claude'})
        chat = rows.get(prompt_index=1, platform='ChatGPT')
        self.assertTrue(chat.is_mention and chat.is_cited)
        self.assertEqual(float(chat.position), 1.0)
        self.assertEqual(chat.sentiment, 'positive')
        self.assertEqual(chat.competitors_mentioned, ['Paisabazaar'])  # own host is not a competitor
        self.assertEqual(chat.rival_positions, {'HDFC Bank': 1, 'Paisabazaar': 2}, 'order of first mention in the answer')
        self.assertEqual(chat.cited_domains, ['hdfcbank.com', 'paisabazaar.com'])
        self.assertIsNotNone(chat.latency_ms)
        claude = rows.get(prompt_index=1, platform='Claude')
        self.assertTrue(claude.is_mention)
        self.assertFalse(claude.is_cited)
        self.assertEqual(a.stage_detail['engines'], {'done': 8, 'total': 8, 'answered': 8})

        # scores
        self.assertEqual(a.total_runs, 8)
        self.assertEqual(a.appearances, 8)
        self.assertEqual(a.cited_runs, 4)
        self.assertEqual(a.engines_total, 2)
        self.assertEqual(a.engines_preferred, 2)
        self.assertGreater(a.geo_score, 50)
        self.assertIn(a.geo_stage, ('preferred', 'default'))
        self.assertEqual(a.keywords_total, 0)
        self.assertIsNone(a.seo_visibility)

        # report
        self.assertEqual(a.report['geo']['score'], a.geo_score)
        self.assertEqual(a.report['profile']['brand_name'], 'HDFC Bank')
        self.assertEqual(a.report['config']['seo_enabled'], False)
        self.assertIsNone(a.report['seo'])
        self.assertEqual(len(a.report['geo']['evidence']), 4)
        self.assertEqual(a.stage_detail['serp'], {'skipped': True})

    def test_near_duplicate_rival_names_are_merged(self):
        def noisy(prompt_text, user_domain, client, group):
            out = make_handler()(prompt_text, user_domain, client, group)
            out['competitor_mention_list'] = ['Paisa', '5Paisa', '5paisa.com', 'Groww', 'HDFC Bank']
            return out
        self.engines = [('chatgpt', 'ChatGPT', noisy, object())]
        self.assertEqual(self.run_audit()['status'], 'done')
        row = AuditPromptResult.objects.get(audit=self.audit, prompt_index=1)
        self.assertEqual(row.competitors_mentioned, ['5Paisa', 'Groww'])

    def test_regulators_reference_sites_and_short_words_are_not_rivals(self):
        def noisy(prompt_text, user_domain, client, group):
            out = make_handler()(prompt_text, user_domain, client, group)
            out['competitor_mention_list'] = ['Sebi', 'Nsdl', 'Sip', 'Groww', 'Investopedia', 'Rbi', 'Ngo', 'ICICI Bank', 'Amfiindia']
            out['all_urls'] = ['https://www.sebi.gov.in/x', 'https://nsdl.co.in/y', 'https://groww.in/z',
                               'https://www.ngo.org.in/a', 'https://www.amfiindia.com/b']
            return out
        self.engines = [('chatgpt', 'ChatGPT', noisy, object())]
        self.assertEqual(self.run_audit()['status'], 'done')
        row = AuditPromptResult.objects.get(audit=self.audit, prompt_index=1)
        # ICICI Bank is a declared competitor (PROFILE) and survives regardless; Groww is a real vendor.
        self.assertEqual(row.competitors_mentioned, ['Groww', 'ICICI Bank'])
        self.assertNotIn('Sebi', row.rival_positions)

    def test_unreadable_site_profiles_from_knowledge(self):
        self.site = ('', '', 'HTTP 403')
        self.assertEqual(self.run_audit()['status'], 'done')
        a = Audit.objects.get(pk=self.audit.pk)
        self.assertEqual(a.grounding['profile']['source'], 'knowledge')
        self.assertEqual(a.grounding['profile']['crawl_error'], 'HTTP 403')
        self.assertEqual(a.brand_name, 'HDFC Bank')


class EngineFailureTests(_Base):
    def test_failures_are_recorded_not_counted_as_absent(self):
        self.engines = [
            ('chatgpt', 'ChatGPT', make_handler(), object()),
            ('claude', 'Claude', make_handler(fail=True), object()),
            ('perplexity', 'Perplexity', make_handler(rate_limit=True), object()),
            ('gemini', 'Google Gemini', make_handler(), None),  # no key
        ]
        self.assertEqual(self.run_audit()['status'], 'done')
        a = Audit.objects.get(pk=self.audit.pk)
        by = {(r.prompt_index, r.platform): r for r in AuditPromptResult.objects.filter(audit=a)}
        self.assertEqual(by[(1, 'Claude')].status, 'failed')
        self.assertEqual(by[(1, 'Claude')].error, 'boom')
        self.assertEqual(by[(1, 'Perplexity')].status, 'rate_limited')
        self.assertEqual(by[(1, 'Google Gemini')].status, 'skipped')
        self.assertEqual(by[(1, 'ChatGPT')].status, 'ok')
        # denominators only count answered runs
        self.assertEqual(a.total_runs, 4)
        self.assertEqual(a.appearances, 4)
        self.assertEqual(a.stage_detail['engines']['answered'], 4)
        self.assertEqual(a.report['geo']['runs_total'], 16)

    def test_every_engine_failing_marks_audit_failed(self):
        self.engines = [('chatgpt', 'ChatGPT', make_handler(fail=True), object())]
        result = self.run_audit()
        self.assertEqual(result['status'], 'failed')
        a = Audit.objects.get(pk=self.audit.pk)
        self.assertEqual(a.status, 'FAIL')
        self.assertIn('No engine returned an answer', a.error)
        self.assertTrue(a.error.startswith('engines:'))
        self.assertEqual(a.stage, 'engines')
        self.assertIsNone(a.geo_score)

    def test_profile_llm_failure_marks_audit_failed(self):
        self.llm_json = []  # _chat_json will raise IndexError -> treated as a stage failure
        result = self.run_audit()
        self.assertEqual(result['status'], 'failed')
        a = Audit.objects.get(pk=self.audit.pk)
        self.assertEqual(a.status, 'FAIL')
        self.assertTrue(a.error.startswith('profile:'))


class ResumeTests(_Base):
    def test_restart_resumes_without_re_asking(self):
        calls = []

        def counting(prompt_text, user_domain, client, group):
            calls.append(prompt_text)
            return make_handler()(prompt_text, user_domain, client, group)

        self.engines = [('chatgpt', 'ChatGPT', counting, object())]

        # First run dies right after the engine stage stores its rows.
        with patch.object(ap.AuditProcessor, 'stage_serp', side_effect=RuntimeError('worker restarted')):
            self.assertEqual(self.run_audit()['status'], 'failed')
        self.assertEqual(len(calls), 4)
        self.assertEqual(AuditPromptResult.objects.filter(audit=self.audit).count(), 4)

        # Operator re-runs: clear the failure and enqueue again.
        Audit.objects.filter(pk=self.audit.pk).update(status='PROC', error='')
        self.llm_json = [PROFILE]  # would only be consumed if profile re-ran
        result = self.run_audit()
        self.assertEqual(result['status'], 'done')
        self.assertEqual(len(calls), 4, 'stored answers must not be re-asked')
        self.assertEqual(len(self.llm_json), 1, 'profile must not be re-generated')
        a = Audit.objects.get(pk=self.audit.pk)
        self.assertEqual(a.status, 'DONE')
        self.assertEqual(AuditPromptResult.objects.filter(audit=a).count(), 4)

    def test_partial_engine_rows_are_completed(self):
        # Simulate a crash after 2 of 4 prompts were answered on ChatGPT.
        Audit.objects.filter(pk=self.audit.pk).update(
            status='PROC', stage='engines', brand_name='HDFC Bank',
            grounding={
                'profile': {'source': 'site', 'categories': ['x']},
                'prompts': [{'index': i, 'text': f'q{i}?', 'topic': 't', 'funnel_stage': 'top'} for i in range(1, 5)],
            },
        )
        for i in (1, 2):
            AuditPromptResult.objects.create(audit=self.audit, prompt_index=i, prompt_text=f'q{i}?', platform='ChatGPT', is_mention=True)
        # A failed answer from the first attempt must be re-asked, not kept.
        AuditPromptResult.objects.create(audit=self.audit, prompt_index=3, prompt_text='q3?', platform='ChatGPT', status='failed', error='boom')
        calls = []

        def counting(prompt_text, user_domain, client, group):
            calls.append(prompt_text)
            return make_handler()(prompt_text, user_domain, client, group)

        self.engines = [('chatgpt', 'ChatGPT', counting, object())]
        self.assertEqual(self.run_audit()['status'], 'done')
        self.assertEqual(sorted(calls), ['q3?', 'q4?'])
        self.assertEqual(AuditPromptResult.objects.filter(audit=self.audit).count(), 4)
        self.assertEqual(AuditPromptResult.objects.get(audit=self.audit, prompt_index=3).status, 'ok')


class SeoStageTests(_Base):
    def test_seo_stage_ranks_discovered_keywords(self):
        self.llm_json = [PROFILE, ['hdfc savings account', 'home loan interest rate', 'gold loan rate']]
        serp = {
            'hdfc savings account': {'rank': 1, 'url': 'https://hdfcbank.com/savings', 'competitors': {'icicibank.com': 2}},
            'home loan interest rate': {'rank': 4, 'url': 'https://hdfcbank.com/home-loan',
                                        'competitors': {'sbi.co.in': 1, 'paisabazaar.com': 2, 'icicibank.com': 7}},
            'gold loan rate': {'rank': 0, 'url': '', 'competitors': {'muthootfinance.com': 1}},
        }
        with patch('core.seo_ranking_processor.fetch_serp_data', side_effect=lambda kw, *a, **k: {'kw': kw}), \
             patch('core.seo_ranking_processor.parse_json_serp_response', side_effect=lambda data, url: serp[data['kw']]), \
             patch.object(ap.AuditProcessor, '_keyword_volumes', return_value={'hdfc savings account': 74000, 'home loan interest rate': 201000}), \
             override_settings(AUDIT_ENGINE_ENABLED=True, AUDIT_PROMPT_COUNT=4, AUDIT_SEO_ENABLED=True, AUDIT_KEYWORD_COUNT=5):
            result = ap.run_audit(self.audit.pk)
        self.assertEqual(result['status'], 'done', result)
        a = Audit.objects.get(pk=self.audit.pk)
        kws = {k.keyword: k for k in AuditKeywordResult.objects.filter(audit=a)}
        self.assertEqual(set(kws), set(serp))
        self.assertEqual(kws['hdfc savings account'].position, 1)
        self.assertEqual(kws['hdfc savings account'].search_volume, 74000)
        self.assertEqual(kws['hdfc savings account'].outranked_by, [])
        self.assertEqual(kws['home loan interest rate'].outranked_by, ['sbi.co.in', 'paisabazaar.com'])
        self.assertIsNone(kws['gold loan rate'].position)
        self.assertIsNone(kws['gold loan rate'].search_volume)
        self.assertEqual(kws['gold loan rate'].outranked_by, ['muthootfinance.com'])
        self.assertEqual(a.keywords_total, 3)
        self.assertEqual(a.keywords_top10, 2)
        self.assertIsNotNone(a.seo_visibility)
        self.assertEqual(a.report['seo']['keywords_total'], 3)
        self.assertEqual(a.grounding['keywords'], list(serp))
        self.assertTrue(a.stage_detail['serp']['complete'])


class HelperTests(TestCase):
    def test_country_info_falls_back_to_us(self):
        self.assertEqual(ap.country_info('in')[0], 'India')
        self.assertEqual(ap.country_info('IN')[1], 'google.co.in')
        self.assertEqual(ap.country_info('zz')[0], 'United States')
        self.assertEqual(ap.country_info(None)[0], 'United States')

    def test_strip_html_and_stack_detection(self):
        html = '<html><head><script src="/wp-content/x.js"></script><style>a{}</style></head><body><p>Hello <b>there</b></p></body></html>'
        self.assertEqual(ap._strip_html(html), 'Hello there')
        self.assertEqual(ap._detect_stack(html), ['WordPress'])
        self.assertEqual(ap._detect_stack(''), [])

    def test_hosts_of_dedupes_and_normalises(self):
        self.assertEqual(ap._hosts_of(['https://www.A.com/x', 'http://a.com/y', 'b.com', '']), ['a.com', 'b.com'])

    def test_fetch_site_plain_http_fallback(self):
        class Resp:
            ok, status_code, text = True, 200, '<html><body>' + 'words ' * 100 + '</body></html>'
        with patch('requests.get', return_value=Resp()), override_settings(DATABLUE_API_KEY=''):
            html, text, err = ap.fetch_site('https://example.com')
        self.assertTrue(html.startswith('<html>'))
        self.assertTrue(text.startswith('words'))
        self.assertIsNone(err)

    def test_fetch_site_reports_http_error(self):
        class Resp:
            ok, status_code, text = False, 403, ''
        with patch('requests.get', return_value=Resp()), override_settings(DATABLUE_API_KEY=''):
            html, text, err = ap.fetch_site('https://example.com')
        self.assertEqual((html, text, err), ('', '', 'HTTP 403'))


class NotificationTests(_Base):
    """Publish-time emails: sent when addresses exist, never fatal, outcome recorded."""

    def test_requester_and_lead_alert_are_sent(self):
        Audit.objects.filter(pk=self.audit.pk).update(source='landing', requester_email='lead@example.com')
        sent = []

        class FakeService:
            def send_report_email(self, recipients, subject, body_text, body_html=None, **kw):
                sent.append((tuple(recipients), subject, body_text, body_html))
                return {'success': True}

        with patch('core.mailgun_email_service.MailgunEmailService', FakeService), \
             override_settings(AUDIT_LEAD_ALERT_EMAILS='sales@agency.in, ops@agency.in', FRONTEND_URL='https://app.example.com/'):
            self.assertEqual(self.run_audit()['status'], 'done')
        a = Audit.objects.get(pk=self.audit.pk)
        self.assertEqual(a.stage_detail['publish'], {'emailed': True, 'alerted': True})
        self.assertEqual(len(sent), 2)
        (to1, subj1, text1, html1), (to2, subj2, text2, _) = sent
        self.assertEqual(to1, ('lead@example.com',))
        self.assertIn('HDFC Bank', subj1)
        self.assertIn(f'https://app.example.com/audit/{a.public_token}', text1)
        self.assertIn(f'https://app.example.com/audit/{a.public_token}', html1)
        self.assertEqual(to2, ('sales@agency.in', 'ops@agency.in'))
        self.assertIn('New audit lead', subj2)
        self.assertIn(f'https://app.example.com/audits/{a.pk}', text2)
        self.assertIn('lead@example.com', text2)

    def test_manual_audit_emails_the_admin_but_raises_no_lead_alert(self):
        sent = []

        class FakeService:
            def send_report_email(self, recipients, subject, body_text, body_html=None, **kw):
                sent.append(tuple(recipients)); return {'success': True}

        from shared_models.models import Account, Organisation
        org = Organisation.objects.create(name='Agency')
        admin = Account.objects.create(username='a', email='admin@agency.in', organisation=org, role='admin')
        Audit.objects.filter(pk=self.audit.pk).update(source='manual', requested_by=admin)
        with patch('core.mailgun_email_service.MailgunEmailService', FakeService), \
             override_settings(AUDIT_LEAD_ALERT_EMAILS='sales@agency.in'):
            self.assertEqual(self.run_audit()['status'], 'done')
        self.assertEqual(sent, [('admin@agency.in',)])
        self.assertEqual(Audit.objects.get(pk=self.audit.pk).stage_detail['publish'], {'emailed': True, 'alerted': False})

    def test_unconfigured_mailgun_is_a_quiet_no_op(self):
        Audit.objects.filter(pk=self.audit.pk).update(requester_email='lead@example.com')
        with override_settings(MAILGUN_API_KEY='', MAILGUN_DOMAIN='', AUDIT_LEAD_ALERT_EMAILS=''):
            self.assertEqual(self.run_audit()['status'], 'done')
        a = Audit.objects.get(pk=self.audit.pk)
        self.assertEqual(a.status, 'DONE')
        self.assertEqual(a.stage_detail['publish'], {'emailed': False, 'alerted': False})

    def test_email_crash_never_fails_the_audit(self):
        Audit.objects.filter(pk=self.audit.pk).update(requester_email='lead@example.com')
        with patch('core.audit_notifications.notify_audit_published', side_effect=RuntimeError('smtp down')):
            self.assertEqual(self.run_audit()['status'], 'done')
        a = Audit.objects.get(pk=self.audit.pk)
        self.assertEqual(a.status, 'DONE')
        self.assertEqual(a.stage_detail['publish'], {'emailed': False, 'alerted': False})


class SummaryTests(_Base):
    def test_llm_summary_lands_in_the_report_and_is_cached_by_fingerprint(self):
        self.summary_llm = {'headline': 'HDFC Bank is Preferred.', 'key_findings': ['a 1', 'b 2', 'c 3'], 'sections': {'geo': 'x'}}
        self.assertEqual(self.run_audit()['status'], 'done')
        a = Audit.objects.get(pk=self.audit.pk)
        sm = a.report['summary']
        self.assertEqual(sm['source'], 'llm')
        self.assertEqual(sm['headline'], 'HDFC Bank is Preferred.')
        self.assertEqual(a.grounding['summary'], sm)
        # same numbers -> cached, no second call
        with patch('core.audit_summary.build_summary', side_effect=AssertionError('must not be called')):
            p = ap.AuditProcessor(a.pk); p.audit = a; p.stage_score()
        self.assertEqual(a.report['summary']['fingerprint'], sm['fingerprint'])

    def test_summary_disabled_uses_rules(self):
        with override_settings(AUDIT_SUMMARY_ENABLED=False):
            self.assertEqual(self.run_audit()['status'], 'done')
        sm = Audit.objects.get(pk=self.audit.pk).report['summary']
        self.assertEqual(sm['source'], 'rules')
        self.assertGreaterEqual(len(sm['key_findings']), 3)
        self.assertIn('HDFC Bank', sm['headline'])

    def test_summary_llm_failure_uses_rules_and_never_fails(self):
        with patch('core.audit_summary.build_summary', side_effect=RuntimeError('llm down')):
            self.assertEqual(self.run_audit()['status'], 'done')
        a = Audit.objects.get(pk=self.audit.pk)
        self.assertEqual(a.status, 'DONE')
        self.assertEqual(a.report['summary']['source'], 'rules')
        self.assertNotIn('summary', a.grounding, 'rules summaries are not cached')


class NarrativeTests(_Base):
    def test_narrative_lands_in_the_report_and_is_cached(self):
        self.assertEqual(self.run_audit()['status'], 'done')
        a = Audit.objects.get(pk=self.audit.pk)
        nar = a.report['narrative']
        self.assertTrue(nar['available'])
        self.assertEqual(nar['dominant_framing'], 'Established bank')
        self.assertEqual(nar['descriptors_missing'], ['NRI expertise'])
        self.assertEqual([e['platform'] for e in nar['by_engine']], ['ChatGPT'])
        self.assertEqual(a.grounding['narrative'], nar)
        # re-scoring reuses the cached narrative: no second LLM call
        with patch('core.audit_narrative.build_narrative', side_effect=AssertionError('must not be called')):
            p = ap.AuditProcessor(a.pk); p.audit = a; p.stage_score()

    def test_narrative_disabled(self):
        with override_settings(AUDIT_NARRATIVE_ENABLED=False):
            self.assertEqual(self.run_audit()['status'], 'done')
        nar = Audit.objects.get(pk=self.audit.pk).report['narrative']
        self.assertEqual(nar, {'available': False, 'reason': 'disabled'})

    def test_narrative_failure_never_fails_the_audit(self):
        with patch('core.audit_narrative.build_narrative', side_effect=RuntimeError('llm down')):
            self.assertEqual(self.run_audit()['status'], 'done')
        a = Audit.objects.get(pk=self.audit.pk)
        self.assertEqual(a.status, 'DONE')
        self.assertFalse(a.report['narrative']['available'])
        self.assertIn('llm down', a.report['narrative']['reason'])
        self.assertNotIn('narrative', a.grounding, 'a failed call is not cached, so a re-score retries it')
        # ...and the retry succeeds without a re-run of the whole audit
        p = ap.AuditProcessor(a.pk); p.audit = a; p.stage_score()
        self.assertTrue(a.report['narrative']['available'])

    def test_no_mentions_means_no_narrative_call(self):
        self.engines = [('chatgpt', 'ChatGPT', make_handler(mention=False, cited=False), object())]
        self.assertEqual(self.run_audit()['status'], 'done')
        nar = Audit.objects.get(pk=self.audit.pk).report['narrative']
        self.assertFalse(nar['available'])
        self.assertIn('never named', nar['reason'])


class CrawlStageTests(_Base):
    def test_crawl_disabled_is_skipped_and_findable_stays_unmeasured(self):
        with override_settings(AUDIT_CRAWL_ENABLED=False):
            self.assertEqual(self.run_audit()['status'], 'done')
        a = Audit.objects.get(pk=self.audit.pk)
        self.assertEqual(a.stage_detail['crawl'], {'skipped': True})
        self.assertEqual(AuditPageResult.objects.filter(audit=a).count(), 0)
        self.assertIsNone(a.report['pillars']['findable'])
        self.assertIsNone(a.report['crawl'])
        self.assertFalse(a.report['config']['crawl_enabled'])

    def test_crawl_crash_never_fails_the_audit(self):
        with patch('core.audit_crawl.crawl_site', side_effect=RuntimeError('DNS down')):
            self.assertEqual(self.run_audit()['status'], 'done')
        a = Audit.objects.get(pk=self.audit.pk)
        self.assertEqual(a.status, 'DONE')
        self.assertEqual(a.stage_detail['crawl'], {'error': 'DNS down'})
        self.assertEqual(a.grounding['crawl']['error'], 'DNS down')
        self.assertIsNone(a.report['pillars']['findable'])
        self.assertIsNone(a.report['crawl'])

    def test_resume_skips_a_completed_crawl(self):
        calls = []
        with patch('core.audit_crawl.crawl_site', side_effect=lambda *a, **k: (calls.append(1), self.crawl)[1]),              patch.object(ap.AuditProcessor, 'stage_prompts', side_effect=RuntimeError('worker restarted')):
            self.assertEqual(self.run_audit()['status'], 'failed')
        self.assertEqual(len(calls), 1)
        Audit.objects.filter(pk=self.audit.pk).update(status='PROC', error='')
        self.llm_json = [PROFILE]
        with patch('core.audit_crawl.crawl_site', side_effect=lambda *a, **k: (calls.append(1), self.crawl)[1]):
            self.assertEqual(self.run_audit()['status'], 'done')
        self.assertEqual(len(calls), 1, 'a completed crawl is not repeated')
        self.assertEqual(AuditPageResult.objects.filter(audit=self.audit).count(), 2)


class MultiRunTests(_Base):
    def test_each_prompt_is_asked_n_times_and_resume_fills_gaps(self):
        calls = []

        def counting(prompt_text, user_domain, client, group):
            calls.append(prompt_text)
            return make_handler()(prompt_text, user_domain, client, group)

        self.engines = [('chatgpt', 'ChatGPT', counting, object())]
        with override_settings(AUDIT_ENGINE_ENABLED=True, AUDIT_PROMPT_COUNT=4, AUDIT_SEO_ENABLED=False,
                               AUDIT_ENGINES=['openai'], AUDIT_RUNS_PER_PROMPT=3):
            self.assertEqual(ap.run_audit(self.audit.pk)['status'], 'done')
        a = Audit.objects.get(pk=self.audit.pk)
        self.assertEqual(a.config['runs_per_prompt'], 3)
        self.assertEqual(len(calls), 12, '4 prompts x 1 engine x 3 runs')
        rows = AuditPromptResult.objects.filter(audit=a)
        self.assertEqual(rows.count(), 12)
        self.assertEqual(sorted(set(rows.values_list('run_index', flat=True))), [1, 2, 3])
        self.assertEqual(a.stage_detail['engines'], {'done': 12, 'total': 12, 'answered': 12})
        self.assertEqual(a.total_runs, 12)
        self.assertEqual(a.report['geo']['runs_per_prompt'], 3)
        self.assertEqual(a.report['geo']['evidence'][0]['runs'], 3)
        self.assertEqual(a.report['geo']['evidence'][0]['engines'], {'ChatGPT': 'cited'})

        # Drop one run and re-score through the resume path: only that run is re-asked.
        rows.filter(prompt_index=2, run_index=2).update(status='failed')
        Audit.objects.filter(pk=a.pk).update(status='PROC', error='')
        calls.clear()
        with override_settings(AUDIT_ENGINE_ENABLED=True, AUDIT_PROMPT_COUNT=4, AUDIT_SEO_ENABLED=False,
                               AUDIT_ENGINES=['openai'], AUDIT_RUNS_PER_PROMPT=3):
            self.assertEqual(ap.run_audit(a.pk)['status'], 'done')
        self.assertEqual(len(calls), 1)
        self.assertEqual(AuditPromptResult.objects.get(audit=a, prompt_index=2, run_index=2).status, 'ok')

    def test_runs_per_prompt_is_clamped(self):
        with override_settings(AUDIT_ENGINE_ENABLED=True, AUDIT_PROMPT_COUNT=4, AUDIT_SEO_ENABLED=False,
                               AUDIT_ENGINES=['openai'], AUDIT_RUNS_PER_PROMPT=99):
            self.assertEqual(ap.run_audit(self.audit.pk)['status'], 'done')
        self.assertEqual(Audit.objects.get(pk=self.audit.pk).config['runs_per_prompt'], 10)


class MentionOrderTests(TestCase):
    def test_order_of_first_mention(self):
        text = "Zerodha and Groww lead; Angel One and AngelOne apps follow. Upstox too."
        self.assertEqual(ap.mention_order(text, ['Groww', 'Angel One', 'Upstox', 'Paytm'], 'Zerodha'),
                         {'Zerodha': 1, 'Groww': 2, 'Angel One': 3, 'Upstox': 4})

    def test_space_insensitive_fallback_and_empty(self):
        self.assertEqual(ap.mention_order("Try AngelOne first.", ['Angel One'], ''), {'Angel One': 1})
        self.assertEqual(ap.mention_order("", ['X'], 'Y'), {})
        self.assertEqual(ap.mention_order("nothing here", ['X'], 'Y'), {})


class DeepCrawlAndHistoryTests(_Base):
    """Phase Q: manual/API audits crawl deep; landing audits keep the small sample; issue history vs the last audit."""

    def test_manual_audit_uses_the_deep_crawl_settings(self):
        calls = []
        with patch('core.audit_crawl.crawl_site', side_effect=lambda *a, **k: (calls.append(k), self.crawl)[1]), \
             override_settings(AUDIT_CRAWL_PAGES=20, AUDIT_CRAWL_PAGES_DEEP=60, AUDIT_CRAWL_BUDGET_SECONDS_DEEP=150,
                               AUDIT_CRAWL_LINK_CHECK_LIMIT_DEEP=100, AUDIT_CWV_PAGES_DEEP=3):
            self.assertEqual(self.run_audit()['status'], 'done')
        k = calls[0]
        self.assertEqual((k['limit'], k['budget_seconds'], k['link_check_limit'], k['cwv_pages'], k['follow_links']), (60, 150, 100, 3, True))
        a = Audit.objects.get(pk=self.audit.pk)
        self.assertEqual(a.report['config']['crawl_depth'], 'deep')
        self.assertEqual(a.report['config']['crawl_pages'], 60)

    def test_landing_audit_keeps_the_standard_sample(self):
        self.audit.source = 'landing'
        self.audit.save(update_fields=['source'])
        calls = []
        with patch('core.audit_crawl.crawl_site', side_effect=lambda *a, **k: (calls.append(k), self.crawl)[1]), \
             override_settings(AUDIT_CRAWL_PAGES=20, AUDIT_CRAWL_PAGES_DEEP=60, AUDIT_CRAWL_BUDGET_SECONDS=60):
            self.assertEqual(self.run_audit()['status'], 'done')
        k = calls[0]
        self.assertEqual((k['limit'], k['budget_seconds'], k['cwv_pages']), (20, 60, 1))
        self.assertEqual(Audit.objects.get(pk=self.audit.pk).report['config']['crawl_depth'], 'standard')

    def test_issue_history_against_the_previous_audit(self):
        Audit.objects.create(
            public_token='tok-prev', host='hdfcbank.com', website='https://hdfcbank.com', country='in', source='manual', status='DONE',
            completed_at=timezone.now() - timedelta(days=7),
            report={'crawl': {'health': {'score': 40}, 'technical_issues': [
                {'key': 'missing_h1', 'label': 'Pages without an H1', 'count': 4},
                {'key': 'noindex', 'label': 'Pages carrying noindex', 'count': 1},
                {'key': 'thin_content', 'label': 'Thin content pages', 'count': 2}]}},
        )
        self.crawl['summary']['technical_issues'] = [
            {'key': 'missing_h1', 'label': 'Pages without an H1', 'severity': 'warning', 'count': 1, 'of': 2, 'examples': [], 'fix': '', 'action': ''},
            {'key': 'broken_links', 'label': 'Broken internal links', 'severity': 'critical', 'count': 3, 'of': 10, 'examples': [], 'fix': '', 'action': ''},
        ]
        self.assertEqual(self.run_audit()['status'], 'done')
        d = Audit.objects.get(pk=self.audit.pk).report['crawl']['issue_delta']
        self.assertEqual([f['key'] for f in d['fixed']], ['noindex', 'thin_content'])
        self.assertEqual([n['key'] for n in d['new']], ['broken_links'])
        self.assertEqual(d['changed'], [{'key': 'missing_h1', 'label': 'Pages without an H1', 'from': 4, 'to': 1}])
        self.assertEqual(d['previous_health'], 40)
        self.assertIsNotNone(d['previous_completed_at'])

    def test_no_previous_audit_means_no_delta(self):
        self.crawl['summary']['technical_issues'] = []
        self.assertEqual(self.run_audit()['status'], 'done')
        self.assertNotIn('issue_delta', Audit.objects.get(pk=self.audit.pk).report['crawl'])

    def test_page_details_carry_the_new_flags(self):
        self.crawl['pages'][0]['tech'] = {'thin': True, 'title_issue': 'long', 'og_missing': ['og:image'], 'rich_result_blockers': [], 'internal_urls': ['x'],
                                          'json_ld_invalid': 0, 'internal_links': 4}
        self.crawl['pages'][0]['index'] = {'verdict': 'indexable', 'reason': ''}
        self.crawl['pages'][0]['redirect_chain'] = [{'status': 301, 'url': 'http://hdfcbank.com/'}]
        self.assertEqual(self.run_audit()['status'], 'done')
        d = AuditPageResult.objects.get(audit=self.audit, url='https://hdfcbank.com/').details
        self.assertEqual((d['thin'], d['title_issue'], d['og_missing'], d['internal_links']), (True, 'long', ['og:image'], 4))
        self.assertNotIn('rich_result_blockers', d, 'empty values are not stored')
        self.assertNotIn('internal_urls', d, 'the link list itself is not persisted')
        self.assertNotIn('json_ld_invalid', d)
        self.assertEqual(d['index']['verdict'], 'indexable')
        self.assertEqual(d['redirect_chain'][0]['status'], 301)
