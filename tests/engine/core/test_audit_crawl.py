"""
Tests for core.audit_crawl — the on-site half of the audit (Findable pillar).

The score side is pure and tested directly; the fetch side is tested with
fetch_text mocked so nothing touches the network:

  * robots.txt parsing: missing file, per-bot blocks, wildcard, Allow override, Sitemap lines
  * sitemap parsing: urlset vs sitemap index
  * page analysis: JSON-LD types, author from three sources, dates, words, outbound hosts,
    question headings, tables
  * summary + the four Findable measures, including "no dates" -> not scored
  * URL discovery: homepage first, sitemap, index children, same-host + skip filters, limit
  * crawl_site end to end with a fake site
"""
from datetime import datetime, timezone as dt_timezone
from unittest.mock import patch

from django.test import SimpleTestCase

from core import audit_crawl as c


ROBOTS = """
User-agent: *
Disallow: /admin

User-agent: GPTBot
Disallow: /

User-agent: ClaudeBot
Disallow: /
Allow: /

Sitemap: https://example.com/sitemap.xml
"""

PAGE = """<html><head><title>Best savings account | Example Bank</title>
<meta name="author" content="Meta Author">
<meta property="article:modified_time" content="2026-06-15T10:00:00Z">
<script type="application/ld+json">{"@context":"https://schema.org","@graph":[
 {"@type":"Organization","name":"Example Bank"},
 {"@type":"Article","author":{"@type":"Person","name":"Priya Sharma"},"dateModified":"2026-07-01"},
 {"@type":"FAQPage"}]}</script>
<style>.x{}</style><script>var a=1;</script>
</head><body>
<h1>What is a savings account?</h1><h2>Rates</h2><h3>How do I open one?</h3>
<p>Some words here about savings accounts and interest rates for everyone.</p>
<table><tr><td>Rate</td></tr></table>
<a href="https://rbi.org.in/x">RBI</a><a href="https://www.rbi.org.in/y">RBI again</a>
<a href="https://moneycontrol.com/z">MC</a><a href="/internal">internal</a><a href="https://blog.example.com/p">sub</a>
<a href="https://www.facebook.com/examplebank">fb</a><a href="https://twitter.com/examplebank">tw</a><a href="https://play.google.com/store/apps/x">app</a>
</body></html>"""


class RobotsTests(SimpleTestCase):
    databases = []

    def test_missing_robots_allows_everyone(self):
        r = c.parse_robots(None)
        self.assertFalse(r['present'])
        self.assertTrue(all(r['allowed'].values()))
        self.assertEqual(r['sitemaps'], [])

    def test_blocks_allows_and_sitemaps(self):
        r = c.parse_robots(ROBOTS)
        self.assertTrue(r['present'])
        self.assertFalse(r['allowed']['GPTBot'])
        self.assertTrue(r['allowed']['ClaudeBot'], 'a later Allow: / undoes the block')
        self.assertTrue(r['allowed']['PerplexityBot'], 'wildcard group only blocks /admin')
        self.assertTrue(r['allowed']['Google-Extended'])
        self.assertEqual(r['sitemaps'], ['https://example.com/sitemap.xml'])

    def test_wildcard_root_block_applies_to_unnamed_bots(self):
        r = c.parse_robots("User-agent: *\nDisallow: /\n\nUser-agent: GPTBot\nAllow: /\n")
        self.assertTrue(r['allowed']['GPTBot'])
        self.assertFalse(r['allowed']['PerplexityBot'])


class SitemapTests(SimpleTestCase):
    databases = []

    def test_urlset(self):
        xml = '<urlset><url><loc>https://a.com/1</loc></url><url><loc> https://a.com/2 </loc></url></urlset>'
        self.assertEqual(c.parse_sitemap(xml), {'urls': ['https://a.com/1', 'https://a.com/2'], 'children': []})

    def test_index(self):
        xml = '<sitemapindex><sitemap><loc>https://a.com/s1.xml</loc></sitemap></sitemapindex>'
        self.assertEqual(c.parse_sitemap(xml), {'urls': [], 'children': ['https://a.com/s1.xml']})
        self.assertEqual(c.parse_sitemap(None), {'urls': [], 'children': []})


class AnalyseHtmlTests(SimpleTestCase):
    databases = []

    def test_extracts_every_signal(self):
        p = c.analyse_html('https://example.com/savings', PAGE, 'example.com')
        self.assertEqual(p['title'], 'Best savings account | Example Bank')
        self.assertTrue(p['has_schema'])
        self.assertEqual(p['schema_types'], ['Article', 'FAQPage', 'Organization', 'Person'])
        self.assertTrue(p['has_faq_schema'])
        self.assertEqual(p['author'], 'Priya Sharma', 'JSON-LD author wins over meta author')
        self.assertEqual(p['last_modified'], '2026-07-01', 'JSON-LD dateModified wins')
        self.assertGreater(p['word_count'], 10)
        self.assertEqual(p['external_links'], 2, 'rbi.org.in (www merged) + moneycontrol.com; own subdomain and social/app-store links excluded')
        self.assertEqual(p['headings'], 3)
        self.assertEqual(p['question_headings'], 2)
        self.assertTrue(p['has_table'])

    def test_falls_back_to_meta_author_and_meta_date(self):
        html = '<html><head><meta name="author" content="Meta Author"><meta property="article:modified_time" content="2025-01-02"></head><body><p>hi</p></body></html>'
        p = c.analyse_html('https://example.com/', html, 'example.com')
        self.assertEqual(p['author'], 'Meta Author')
        self.assertEqual(p['last_modified'], '2025-01-02')
        self.assertFalse(p['has_schema'])
        self.assertEqual(p['schema_types'], [])

    def test_visible_byline(self):
        html = '<html><body><div class="byline">By Ravi Kumar</div><p>text</p></body></html>'
        self.assertEqual(c.analyse_html('https://example.com/', html, 'example.com')['author'], 'By Ravi Kumar')

    def test_empty_page(self):
        p = c.analyse_html('https://example.com/', '', 'example.com')
        self.assertEqual(p['word_count'], 0)
        self.assertIsNone(p['last_modified'])
        self.assertEqual(p['author'], '')


class SummaryAndMeasureTests(SimpleTestCase):
    databases = []
    NOW = datetime(2026, 9, 13, tzinfo=dt_timezone.utc)

    def pages(self):
        return [
            {'url': 'https://e.com/', 'has_schema': True, 'schema_types': ['Organization', 'WebSite'], 'author': '', 'external_links': 0,
             'last_modified': '2026-08-01', 'word_count': 500, 'question_headings': 0, 'has_table': False},
            {'url': 'https://e.com/a', 'has_schema': True, 'schema_types': ['Article', 'FAQPage'], 'author': 'X', 'external_links': 6,
             'last_modified': '2024-01-01', 'word_count': 1500, 'question_headings': 3, 'has_table': True},
            {'url': 'https://e.com/b', 'has_schema': False, 'schema_types': [], 'author': '', 'external_links': 1,
             'last_modified': None, 'word_count': 400, 'question_headings': 0, 'has_table': False},
            {'url': 'https://e.com/c', 'parse_error': 'fetch failed'},
        ]

    def test_summary(self):
        robots = c.parse_robots(ROBOTS)
        s = c.summarise(self.pages(), robots, sitemap_present=True, llms_txt=False, now=self.NOW)
        self.assertEqual(s['pages_sampled'], 3, 'failed pages are not counted')
        self.assertEqual(s['bots_allowed'], 4)
        self.assertEqual(s['bots_total'], 5)
        self.assertEqual([b['bot'] for b in s['bots'] if not b['allowed']], ['GPTBot'])
        self.assertEqual(s['schema_coverage'], 67)
        self.assertEqual(s['recommended_types_present'], ['Organization', 'Article', 'FAQPage'])
        self.assertEqual(s['author_share'], 33)
        self.assertEqual(s['avg_word_count'], 800)
        self.assertEqual(s['avg_external_links'], 2.3)
        self.assertEqual(s['question_heading_share'], 33)
        self.assertEqual(s['table_share'], 33)
        self.assertEqual(s['dated_pages'], 2)
        self.assertEqual(s['stale_pages'], 1)
        self.assertEqual(s['freshest'], '2026-08-01')
        self.assertTrue(s['sitemap_present'])

    def test_measures(self):
        s = c.summarise(self.pages(), c.parse_robots(ROBOTS), True, True, now=self.NOW)
        m = c.crawl_measures(s)
        self.assertEqual(set(m), {'bot_access', 'answer_structure', 'authority_signals', 'page_freshness'})
        self.assertEqual(m['bot_access']['score'], 80)
        self.assertIn('blocked: GPTBot', m['bot_access']['evidence'])
        self.assertIn('sitemap, llms.txt', m['bot_access']['evidence'])
        # 0.5*0.67 + 0.25*(3/7) + 0.25*0.33 = 0.335+0.107+0.083 = 0.525
        self.assertEqual(m['answer_structure']['score'], 52)
        # 0.5*0.33 + 0.3*min(1, 2.3/5) + 0.2*1 = 0.165+0.138+0.2 = 0.503
        self.assertEqual(m['authority_signals']['score'], 50)
        self.assertEqual(m['page_freshness']['score'], 50)
        self.assertEqual(m['page_freshness']['value'], '1 of 2 dated pages 12mo+')

    def test_no_dates_is_reported_not_scored(self):
        pages = [{**p, 'last_modified': None} for p in self.pages() if not p.get('parse_error')]
        m = c.crawl_measures(c.summarise(pages, c.parse_robots(None), False, False, now=self.NOW))
        self.assertIsNone(m['page_freshness']['score'])
        self.assertIn('no publish/update dates', m['page_freshness']['value'])
        self.assertEqual(m['bot_access']['score'], 100)

    def test_no_pages_scores_only_bot_access(self):
        m = c.crawl_measures(c.summarise([], c.parse_robots(None), False, False))
        self.assertEqual(set(m), {'bot_access'})

    def test_measures_feed_scoring(self):
        from core import audit_scoring as s
        m = c.crawl_measures(c.summarise(self.pages(), c.parse_robots(ROBOTS), True, False, now=self.NOW))
        out = s.score_audit([], 'Example', 'e.com', [], crawl=m)
        findable = {x['key']: x for x in out['report']['measures'] if x['pillar'] == 'findable'}
        self.assertEqual(findable['bot_access']['score'], 80)
        self.assertEqual(findable['bot_access']['status'], 'pass')
        self.assertEqual(findable['page_freshness']['status'], 'fail')
        self.assertIsNotNone(out['report']['pillars']['findable'])


class DiscoveryTests(SimpleTestCase):
    databases = []

    def test_homepage_sitemap_index_and_filters(self):
        site = {
            'https://e.com/sitemap.xml': '<sitemapindex><sitemap><loc>https://e.com/s1.xml</loc></sitemap></sitemapindex>',
            'https://e.com/s1.xml': '<urlset>' + ''.join(f'<url><loc>{u}</loc></url>' for u in [
                'https://e.com/', 'https://www.e.com/a', 'https://e.com/tag/x', 'https://e.com/file.pdf',
                'https://other.com/b', 'https://e.com/c', 'https://e.com/d']) + '</urlset>',
        }
        with patch.object(c, 'fetch_text', side_effect=lambda u, timeout=15: site.get(u)):
            d = c.discover_urls('https://e.com', 'e.com', c.parse_robots('Sitemap: https://e.com/sitemap.xml'), limit=4)
        self.assertTrue(d['sitemap_present'])
        self.assertEqual(d['sitemap_children'], 1)
        self.assertEqual(d['urls'], ['https://e.com/', 'https://www.e.com/a', 'https://e.com/c', 'https://e.com/d'])

    def test_falls_back_to_homepage_links(self):
        html = '<a href="/pricing">p</a><a href="https://e.com/about?x=1">a</a><a href="https://other.com/z">o</a><a href="/login">l</a>'
        with patch.object(c, 'fetch_text', return_value=None):
            d = c.discover_urls('https://e.com', 'e.com', c.parse_robots(None), limit=10, homepage_html=html)
        self.assertFalse(d['sitemap_present'])
        self.assertEqual(d['urls'], ['https://e.com/', 'https://e.com/pricing', 'https://e.com/about'])


class CrawlSiteTests(SimpleTestCase):
    databases = []

    def setUp(self):
        # the certificate check opens a real socket; tests never touch the network
        p = patch.object(c, 'certificate_info', return_value={'expires': '2027-01-01', 'days_left': 300, 'issuer': 'Test CA'})
        p.start()
        self.addCleanup(p.stop)

    def test_end_to_end_with_a_fake_site(self):
        site = {
            'https://e.com/robots.txt': 'User-agent: *\nAllow: /\nSitemap: https://e.com/sitemap.xml',
            'https://e.com/llms.txt': '# e.com\n> about us',
            'https://e.com/sitemap.xml': '<urlset><url><loc>https://e.com/</loc></url><url><loc>https://e.com/a</loc></url><url><loc>https://e.com/down</loc></url></urlset>',
            'https://e.com/': PAGE,
            'https://e.com/a': '<html><body><h2>Why us?</h2><p>words words words</p></body></html>',
        }
        def resp(u, timeout=15):
            return {'text': site.get(u), 'status': 200 if u in site else 404, 'final_url': u, 'redirects': 0}
        with patch.object(c, 'fetch_text', side_effect=lambda u, timeout=15: site.get(u)),              patch.object(c, 'fetch_response', side_effect=resp),              patch('core.audit_technical.head_status', side_effect=lambda u, timeout=8: 404 if u.endswith('/internal') else 200):
            r = c.crawl_site('https://e.com', 'e.com', limit=10, budget_seconds=30, workers=2, follow_links=False)
        s = r['summary']
        self.assertEqual(s['pages_sampled'], 2)
        self.assertEqual(s['urls_discovered'], 3)
        self.assertTrue(s['llms_txt'])
        self.assertTrue(s['sitemap_present'])
        self.assertEqual(s['bots_allowed'], 5)
        self.assertEqual(s['schema_coverage'], 50)
        self.assertEqual([p['url'] for p in r['pages']], ['https://e.com/', 'https://e.com/a', 'https://e.com/down'])
        self.assertEqual(r['pages'][2]['parse_error'], 'HTTP 404')
        self.assertEqual(r['pages'][2]['status_code'], 404)
        self.assertEqual(r['measures']['bot_access']['score'], 100)
        self.assertIn('answer_structure', r['measures'])
        # technical layer: link check ran on the unsampled internal link, health + issues present
        self.assertEqual({k: s['link_check'][k] for k in ('checked', 'broken', 'examples')}, {'checked': 1, 'broken': 1, 'examples': [{'url': 'https://e.com/internal', 'status': 404}]})
        self.assertEqual(s['link_check']['external_checked'], 4, 'outbound links are checked too (social hosts excluded)')
        self.assertIsNone(s['cwv'], 'PageSpeed is off by default')
        self.assertIsNotNone(s['health']['score'])
        self.assertIn('broken_links', [i['key'] for i in s['technical_issues']])

    def test_llms_txt_that_is_really_html_does_not_count(self):
        site = {'https://e.com/llms.txt': '<!DOCTYPE html><html>404</html>'}
        with patch.object(c, 'fetch_text', side_effect=lambda u, timeout=15: site.get(u)),              patch.object(c, 'fetch_response', return_value={'text': None, 'status': 0, 'final_url': '', 'redirects': 0}):
            r = c.crawl_site('https://e.com', 'e.com', limit=3, budget_seconds=10, workers=1, link_checks=False)
        self.assertFalse(r['summary']['llms_txt'])
        self.assertEqual(r['pages'][0]['parse_error'], 'fetch failed')

    def test_follow_links_fetches_pages_the_sample_links_to(self):
        site = {
            'https://e.com/robots.txt': 'User-agent: *\nDisallow: /private\nSitemap: https://e.com/sitemap.xml',
            'https://e.com/sitemap.xml': '<urlset><url><loc>https://e.com/</loc></url></urlset>',
            'https://e.com/': '<html><head><title>Home page of e.com</title></head><body><h1>Home</h1>'
                              '<a href="/pricing">Pricing plans</a><a href="/private/x">private</a><a href="/list?sort=asc">sorted</a><a href="/doc.pdf">pdf</a></body></html>',
            'https://e.com/pricing': '<html><head><title>Pricing plans</title></head><body><h1>Pricing</h1><a href="/faq">FAQ page</a></body></html>',
            'https://e.com/faq': '<html><head><title>FAQ</title></head><body><h1>FAQ</h1></body></html>',
            'https://e.com/private/x': '<html><head><title>Private</title></head><body><h1>Private</h1></body></html>',
        }
        def resp(u, timeout=15):
            return {'text': site.get(u), 'status': 200 if u in site else 404, 'final_url': u, 'redirects': 0, 'chain': [], 'headers': {}, 'error': ''}
        with patch.object(c, 'fetch_text', side_effect=lambda u, timeout=15: site.get(u)),              patch.object(c, 'fetch_response', side_effect=resp),              patch('core.audit_technical.head_status', return_value=200):
            r = c.crawl_site('https://e.com', 'e.com', limit=10, budget_seconds=30, workers=2)
        urls = [p['url'] for p in r['pages']]
        self.assertEqual(urls[:2], ['https://e.com/', 'https://e.com/pricing'], 'sitemap first, then linked pages')
        self.assertIn('https://e.com/faq', urls, 'a second round follows links from round-one pages')
        self.assertIn('https://e.com/private/x', urls, 'robots-blocked pages are fetched so the block is reported')
        self.assertNotIn('https://e.com/list?sort=asc', urls, 'parameter URLs are not followed')
        self.assertNotIn('https://e.com/doc.pdf', urls)
        s = r['summary']
        self.assertEqual(s['pages_sampled'], 4)
        self.assertEqual(s['indexability']['not_indexable'], 1, '/private/x is blocked by robots.txt')
        self.assertIn('robots_blocked', [i['key'] for i in s['technical_issues']])
        self.assertEqual(s['sitemap_health']['listed'], 1)
        self.assertEqual(len(s['sitemap_health']['not_in_sitemap']), 3)
        self.assertEqual(r['pages'][0]['index'], {'verdict': 'indexable', 'reason': ''})
