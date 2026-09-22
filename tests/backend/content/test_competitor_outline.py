"""Tests for competitor-informed outlines.

The feature reads the SERP stored against a tracked keyword, scrapes the pages
that rank, and hands the outline prompt their heading structures — answering
the client feedback that the landing page outline was "neither qualitatively
good nor quantitatively [sufficient]" and should "refer to top-ranking
competitors".

What matters most here is NOT the happy path. This sits in front of outline
generation, which worked perfectly well without it, so the bar is that it can
only ever add. Every failure — no tracked keyword, no scrape key, a page that
times out, a hostile payload — must return an empty string and let the outline
be built exactly as it was before.

Run with:  python backend/manage.py test tests.backend.content.test_competitor_outline
           --settings=tests.backend.test_settings
"""
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from content import competitor_outline as CO


PAGE = """<html><head><title>Best Gaming TVs 2026</title></head><body>
<h1>Best Gaming TVs of 2026</h1>
<nav><h2>Menu</h2></nav>
<h2>What to Look For in a Gaming TV</h2>
<h3>Refresh Rate and 120Hz</h3>
<h3>HDMI 2.1 Explained</h3>
<h2>Our Top Picks</h2>
<h2>Newsletter</h2>
</body></html>"""

COMPS = [
    {'rank': 1, 'url': 'https://a.test/x', 'title': 'Best Gaming TVs', 'domain': 'a.test'},
    {'rank': 2, 'url': 'https://b.test/y', 'title': 'Gaming TV Guide', 'domain': 'b.test'},
]


class FailurePathsTests(SimpleTestCase):
    """Every one of these must yield '' and never raise."""

    @override_settings(CONTENT_COMPETITOR_OUTLINE_ENABLED=False)
    def test_switched_off_produces_nothing(self):
        self.assertEqual(CO.build_competitor_brief(1, 'best tv'), '')

    def test_missing_domain_id(self):
        self.assertEqual(CO.build_competitor_brief(None, 'best tv'), '')

    def test_empty_keywords(self):
        self.assertEqual(CO.build_competitor_brief(1, ''), '')

    def test_lookup_raising_is_swallowed(self):
        with patch.object(CO, 'top_competitor_urls', side_effect=RuntimeError('db down')):
            self.assertEqual(CO.build_competitor_brief(1, 'best tv'), '')

    def test_scrape_returning_nothing(self):
        with patch.object(CO, 'top_competitor_urls', return_value=COMPS), \
             patch.object(CO, '_scrape', return_value=None):
            self.assertEqual(CO.build_competitor_brief(1, 'best tv'), '')

    def test_scrape_raising_is_swallowed(self):
        with patch.object(CO, 'top_competitor_urls', return_value=COMPS), \
             patch.object(CO, '_scrape', side_effect=RuntimeError('datablue down')):
            self.assertEqual(CO.build_competitor_brief(1, 'best tv'), '')

    def test_page_without_headings(self):
        with patch.object(CO, 'top_competitor_urls', return_value=COMPS), \
             patch.object(CO, '_scrape', return_value='<p>nothing structural</p>'):
            self.assertEqual(CO.build_competitor_brief(1, 'best tv'), '')

    def test_one_bad_page_does_not_lose_the_good_one(self):
        # A single unreachable competitor must not cost the whole brief.
        def half_broken(url):
            return None if 'a.test' in url else PAGE

        with patch.object(CO, 'top_competitor_urls', return_value=COMPS), \
             patch.object(CO, '_scrape', side_effect=half_broken):
            brief = CO.build_competitor_brief(1, 'best tv')
        self.assertIn('b.test', brief)
        self.assertNotIn('a.test', brief)


class HeadingExtractionTests(SimpleTestCase):

    def test_structure_is_extracted_in_order(self):
        got = CO.extract_headings(PAGE)
        self.assertEqual(got[0], ('h1', 'Best Gaming TVs of 2026'))
        self.assertIn(('h3', 'Refresh Rate and 120Hz'), got)

    def test_boilerplate_is_dropped(self):
        texts = [t for _, t in CO.extract_headings(PAGE)]
        # These say nothing about how the topic is covered and appear on
        # nearly every page on the web.
        self.assertNotIn('Menu', texts)
        self.assertNotIn('Newsletter', texts)

    def test_duplicates_are_collapsed(self):
        html = '<h2>Pricing</h2><h2>Pricing</h2><h2>Specs</h2>'
        self.assertEqual(len(CO.extract_headings(html)), 2)

    def test_entities_are_decoded(self):
        texts = [t for _, t in CO.extract_headings("<h2>Men&#039;s Watches &amp; Straps</h2>")]
        self.assertEqual(texts, ["Men's Watches & Straps"])

    def test_absurd_lengths_are_rejected(self):
        self.assertEqual(CO.extract_headings('<h2>ab</h2>'), [])
        self.assertEqual(CO.extract_headings('<h2>' + 'x' * 500 + '</h2>'), [])

    def test_garbage_input_does_not_raise(self):
        for junk in (None, '', '<h2>', '<<<>>>', '\x00\x01'):
            self.assertEqual(CO.extract_headings(junk), [])


class BriefContentTests(SimpleTestCase):

    def setUp(self):
        with patch.object(CO, 'top_competitor_urls', return_value=COMPS), \
             patch.object(CO, '_scrape', return_value=PAGE):
            self.brief = CO.build_competitor_brief(1, 'best gaming tv')

    def test_brief_carries_the_real_structure(self):
        self.assertIn('What to Look For in a Gaming TV', self.brief)
        self.assertIn('HDMI 2.1 Explained', self.brief)

    def test_pages_are_ordered_by_rank(self):
        self.assertLess(self.brief.index('#1'), self.brief.index('#2'))

    def test_model_is_told_not_to_copy_or_name_competitors(self):
        # The brief is evidence of what the search expects, not a template —
        # and naming rivals in a client's own landing page would be a bug.
        self.assertIn('not a template to copy', self.brief)
        self.assertIn('do NOT name these competitors', self.brief)

    def test_model_is_told_to_go_beyond_them(self):
        # Matching the incumbents is not a reason to outrank them.
        self.assertIn('at least one section none of them have', self.brief)
