"""
Tests for core.audit_narrative — how the engines describe the brand.

DB-free. The LLM call is injected (chat_json), so these pin the excerpting, the
per-engine sampling, the shape cleaning, and the "nothing to analyse" path.
"""
from django.test import SimpleTestCase

from core import audit_narrative as n


ANSWER = "Some intro text. " * 30 + "HDFC Bank is a large private bank known for its app. " + "More text. " * 60


def row(platform='ChatGPT', text=ANSWER, mention=True, status='ok'):
    return {'platform': platform, 'prompt_text': 'Best bank?', 'response_text': text, 'status': status, 'is_mention': mention}


LLM = {
    'dominant_framing': 'Established private bank', 'framing_share': '61', 'consistency': 72.4,
    'descriptors_present': [{'descriptor': 'Established, trusted bank', 'share': 61}, {'descriptor': 'Digital-first', 'share': 44}, 'Competitive rates'],
    'descriptors_missing': ['Wealth & NRI expertise', '', 'Accessible for first-time earners'],
    'by_engine': [{'platform': 'Claude', 'leads_with': 'Trust & history', 'tone': 'Neutral', 'matches_profile': 'yes'},
                  {'platform': 'ChatGPT', 'leads_with': 'Interest rates', 'tone': 'weird', 'matches_profile': 'maybe'},
                  {'platform': 'Grok', 'leads_with': 'x', 'tone': 'positive', 'matches_profile': 'yes'}],
    'off_brand': [{'platform': 'Perplexity', 'claim': 'Stricter eligibility than most', 'why': 'profile says accessible'}],
    'narrative_gap': 'Rivals   are framed as\n comprehensive platforms.  ',
}


class ExcerptTests(SimpleTestCase):
    databases = []

    def test_window_around_first_mention(self):
        ex = n.excerpt(ANSWER, 'HDFC Bank', 'hdfcbank.com', chars=300)
        self.assertIn('HDFC Bank is a large', ex)
        self.assertLessEqual(len(ex), 300)

    def test_falls_back_to_host_label_then_start(self):
        text = 'blah ' * 100 + 'hdfcbank offers loans ' + 'x ' * 50
        self.assertIn('hdfcbank offers', n.excerpt(text, 'Nope', 'hdfcbank.com', chars=120))
        self.assertTrue(n.excerpt('plain text', 'Nope', 'nope.com').startswith('plain'))
        self.assertEqual(n.excerpt('', 'X', 'x.com'), '')


class SelectAnswersTests(SimpleTestCase):
    databases = []

    def test_only_mentioned_answered_rows_spread_across_engines(self):
        rows = [row('ChatGPT'), row('ChatGPT'), row('ChatGPT'), row('Claude'), row('Claude', mention=False),
                row('Perplexity', status='failed'), row('Gemini', text='   ')]
        out = n.select_answers(rows, 'HDFC Bank', 'hdfcbank.com', limit=3)
        self.assertEqual([a['platform'] for a in out], ['ChatGPT', 'Claude', 'ChatGPT'])
        self.assertTrue(all(a['excerpt'] for a in out))

    def test_limit(self):
        self.assertEqual(len(n.select_answers([row() for _ in range(30)], 'HDFC Bank', 'hdfcbank.com')), n.MAX_ANSWERS)


class BuildNarrativeTests(SimpleTestCase):
    databases = []

    def test_nothing_to_analyse(self):
        out = n.build_narrative(lambda *a, **k: LLM, object(), 'm', brand_name='HDFC Bank', host='hdfcbank.com',
                                industry='Banking', profile={}, rows=[row(mention=False)], competitors=[])
        self.assertFalse(out['available'])
        self.assertIn('never named', out['reason'])

    def test_shape_is_cleaned(self):
        calls = []

        def chat_json(client, model, system, user, **kw):
            calls.append(user)
            return LLM

        out = n.build_narrative(chat_json, object(), 'm', brand_name='HDFC Bank', host='hdfcbank.com', industry='Banking',
                                profile={'description': 'Accessible banking'}, rows=[row('ChatGPT'), row('Claude')], competitors=['ICICI Bank'])
        self.assertTrue(out['available'])
        self.assertEqual(out['dominant_framing'], 'Established private bank')
        self.assertEqual(out['framing_share'], 61)
        self.assertEqual(out['consistency'], 72)
        self.assertEqual(out['descriptors_present'][:2], [{'descriptor': 'Established, trusted bank', 'share': 61}, {'descriptor': 'Digital-first', 'share': 44}])
        self.assertEqual(out['descriptors_present'][2], {'descriptor': 'Competitive rates', 'share': 0})
        self.assertEqual(out['descriptors_missing'], ['Wealth & NRI expertise', 'Accessible for first-time earners'])
        # engines: only those analysed, in audit order; bad tone/match values normalised
        self.assertEqual([e['platform'] for e in out['by_engine']], ['ChatGPT', 'Claude'])
        self.assertEqual(out['by_engine'][0]['tone'], 'neutral')
        self.assertEqual(out['by_engine'][0]['matches_profile'], 'partial')
        self.assertEqual(out['by_engine'][1]['tone'], 'neutral')
        self.assertEqual(out['by_engine'][1]['matches_profile'], 'yes')
        self.assertEqual(out['off_brand'][0]['platform'], 'Perplexity')
        self.assertEqual(out['narrative_gap'], 'Rivals are framed as comprehensive platforms.')
        self.assertEqual(out['answers_analysed'], 2)
        self.assertEqual(out['engines_analysed'], ['ChatGPT', 'Claude'])
        self.assertIn('Accessible banking', calls[0])
        self.assertIn('ICICI Bank', calls[0])

    def test_garbage_reply_is_survivable(self):
        out = n.build_narrative(lambda *a, **k: ['not', 'a', 'dict'], object(), 'm', brand_name='HDFC Bank', host='hdfcbank.com',
                                industry='', profile={}, rows=[row()], competitors=[])
        self.assertTrue(out['available'])
        self.assertEqual(out['dominant_framing'], '')
        self.assertEqual(out['by_engine'], [])
