"""
Tests for core.audit_summary — the executive summary on top of the numbers.

DB-free. The digest is built from a stub audit + report; the rules summary is
checked for content and the LLM path for cleaning and its fallback.
"""
from types import SimpleNamespace

from django.test import SimpleTestCase

from core import audit_summary as s


def audit_stub(**over):
    base = dict(brand_name='HDFC Bank', host='hdfcbank.com', industry='Banking', geo_score=58, geo_stage='preferred',
                appearances=20, cited_runs=9, total_runs=24, engines_preferred=3, engines_total=4, share_of_voice=31.0)
    base.update(over)
    return SimpleNamespace(**base)


REPORT = {
    'geo': {
        'stage_label': 'Preferred',
        'engines': [{'platform': 'ChatGPT', 'answered': 6, 'mentioned': 5, 'cited': 3, 'mention_rate': 0.83, 'top_rival': 'Paisabazaar', 'top_rival_mentions': 4},
                    {'platform': 'Perplexity', 'answered': 6, 'mentioned': 2, 'cited': 0, 'mention_rate': 0.33, 'top_rival': 'Paisabazaar', 'top_rival_mentions': 5}],
        'evidence': [{'prompt_index': i} for i in range(1, 7)],
        'gap_counts': {'won': 3, 'visibility_gap': 2, 'position_gap': 1},
        'funnel': {'by_stage': {'top': {'rate': 100}, 'middle': {'rate': 50}, 'bottom': {'rate': 0}}},
        'competitors': {'rows': [{'name': 'HDFC Bank', 'is_you': True, 'prompts_ranked': 4, 'prompts_total': 6, 'avg_position': 2.0},
                                 {'name': 'Paisabazaar', 'is_you': False, 'prompts_ranked': 5, 'prompts_total': 6, 'avg_position': 1.4}],
                        'callouts': [{'title': 'Paisabazaar — the BOFU default'}]},
        'citation_control': {'owned': 12.0, 'competitor': 40.0, 'third_party': 48.0, 'total_citations': 25, 'top_sources': [{'host': 'paisabazaar.com'}]},
    },
    'measures': [{'label': 'Owned citation share', 'value': '12%', 'score': 48, 'target': 70, 'status': 'fail'},
                 {'label': 'Mention rate', 'value': '83%', 'score': 83, 'target': 80, 'status': 'pass'}],
    'pillars': {'findable': 70, 'cited': 40, 'chosen': 75},
    'narrative': {'available': True, 'dominant_framing': 'Established bank', 'framing_share': 61, 'consistency': 72,
                  'descriptors_missing': ['NRI expertise'], 'off_brand': [{'claim': 'Stricter eligibility'}]},
    'crawl': {'pages_sampled': 20, 'bots_allowed': 5, 'bots_total': 5, 'schema_coverage': 85, 'author_share': 0, 'avg_word_count': 900,
              'dated_pages': 0, 'stale_pages': 0, 'sitemap_present': True, 'llms_txt': False},
    'seo': None,
    'plan': {'today': 58, 'projected': 71, 'status_quo': 55,
             'buckets': [{'label': 'Now', 'from': 58, 'to': 66, 'items': [{'title': 'Add author bylines'}]}, {'label': 'Next', 'from': 66, 'to': 71, 'items': []}]},
}


class DigestTests(SimpleTestCase):
    databases = []

    def test_digest_is_numbers_only_and_complete(self):
        d = s.digest(audit_stub(), REPORT)
        self.assertEqual(d['brand'], 'HDFC Bank')
        self.assertEqual(d['mention_rate_pct'], 83)
        self.assertEqual(d['weakest_engine'], 'Perplexity')
        self.assertEqual(d['strongest_engine'], 'ChatGPT')
        self.assertEqual(d['top_rivals'][0]['name'], 'Paisabazaar')
        self.assertEqual(d['citations']['owned_pct'], 12.0)
        self.assertEqual(d['failing_measures'][0]['label'], 'Owned citation share')
        self.assertEqual(d['narrative']['dominant_framing'], 'Established bank')
        self.assertEqual(d['website']['pages_sampled'], 20)
        self.assertIsNone(d['seo'])
        self.assertEqual(d['plan']['projected'], 71)
        self.assertEqual(d['plan']['buckets'][0]['actions'], ['Add author bylines'])
        self.assertNotIn('response_text', str(d))

    def test_digest_of_a_minimal_report(self):
        d = s.digest(audit_stub(geo_score=None, total_runs=0, appearances=0), {'geo': {}})
        self.assertEqual(d['mention_rate_pct'], 0)
        self.assertIsNone(d['weakest_engine'])
        self.assertEqual(d['top_rivals'], [])
        self.assertIsNone(d['website'])
        self.assertIsNone(d['plan'])

    def test_fingerprint_changes_with_the_numbers(self):
        a = s.fingerprint(s.digest(audit_stub(), REPORT))
        b = s.fingerprint(s.digest(audit_stub(geo_score=59), REPORT))
        self.assertNotEqual(a, b)
        self.assertEqual(a, s.fingerprint(s.digest(audit_stub(), REPORT)))


class RulesSummaryTests(SimpleTestCase):
    databases = []

    def test_findings_from_numbers(self):
        out = s.rules_summary(s.digest(audit_stub(), REPORT))
        self.assertEqual(out['source'], 'rules')
        self.assertIn('HDFC Bank is Preferred (58/100)', out['headline'])
        self.assertIn('projects 71', out['headline'])
        self.assertEqual(len(out['key_findings']), 5)
        text = ' '.join(out['key_findings'])
        for needle in ('20 of 24', '83%', '3 of 4 engines', 'Perplexity', '12% of 25 citations', 'Paisabazaar', '3 won'):
            self.assertIn(needle, text, needle)
        self.assertIn('Established bank', out['sections']['narrative'])
        self.assertIn('58 today', out['sections']['plan'])
        self.assertTrue(out['fingerprint'])

    def test_minimal_report_still_summarises(self):
        out = s.rules_summary(s.digest(audit_stub(geo_score=0, geo_stage='absent', appearances=0, cited_runs=0, total_runs=6,
                                                  engines_preferred=0, engines_total=1), {'geo': {'stage_label': 'Absent', 'engines': []}}))
        self.assertGreaterEqual(len(out['key_findings']), 2)
        self.assertIn('Absent', out['headline'])
        self.assertEqual(out['sections']['competitors'], '')


class BuildSummaryTests(SimpleTestCase):
    databases = []

    LLM = {'headline': '  HDFC Bank is well placed\nbut rarely cited. ',
           'key_findings': ['Named on 83% of answers.', 'Cited on 9 of 24.', 'Paisabazaar leads BOFU.', '', 'Perplexity is the weak engine.', 'fifth', 'sixth is dropped'],
           'sections': {'geo': 'Strong on ChatGPT.', 'plan': 'Three moves.', 'website': 'The website section is not included in the digest.', 'bogus': 'ignored'}}

    def test_llm_summary_is_cleaned(self):
        out = s.build_summary(lambda *a, **k: self.LLM, object(), 'm', s.digest(audit_stub(), REPORT))
        self.assertEqual(out['source'], 'llm')
        self.assertEqual(out['headline'], 'HDFC Bank is well placed but rarely cited.')
        self.assertEqual(len(out['key_findings']), 5)
        self.assertNotIn('', out['key_findings'])
        self.assertNotIn('sixth is dropped', out['key_findings'])
        self.assertEqual(out['sections']['geo'], 'Strong on ChatGPT.')
        self.assertEqual(out['sections']['competitors'], '')
        self.assertEqual(out['sections']['website'], '', 'a "not included in the digest" blurb is dropped')
        self.assertNotIn('bogus', out['sections'])

    def test_thin_or_broken_reply_falls_back_to_rules(self):
        d = s.digest(audit_stub(), REPORT)
        self.assertEqual(s.build_summary(lambda *a, **k: {'headline': 'x', 'key_findings': ['one']}, object(), 'm', d)['source'], 'rules')
        self.assertEqual(s.build_summary(lambda *a, **k: ['not', 'a', 'dict'], object(), 'm', d)['source'], 'rules')

        def boom(*a, **k):
            raise RuntimeError('llm down')
        out = s.build_summary(boom, object(), 'm', d)
        self.assertEqual(out['source'], 'rules')
        self.assertEqual(len(out['key_findings']), 5)
