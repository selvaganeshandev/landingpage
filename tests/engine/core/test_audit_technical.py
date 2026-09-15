"""
Tests for core.audit_technical — the technical-SEO / site-health layer over the crawl sample.

Pure functions only; the two network helpers (head_status, fetch_cwv) are mocked:

  * page_signals: title/description/H1, canonical states, noindex, viewport, image alt,
    mixed content, hreflang, OG, internal links + generic anchors, schema field gaps,
    Person schema, credential mentions
  * link_graph: depth from the homepage, orphan candidates, unsampled links
  * technical_summary: site counts, issue list ordering, health score + priorities,
    content patterns, weight renormalisation when a category is unmeasured
  * parse_cwv: field data preferred over lab, ratings and score, None when neither
  * check_links: broken = 4xx / unreachable
  * analyse_html carries the block under page['tech'] and the GEO keys are unchanged
"""
from unittest.mock import patch

from django.test import SimpleTestCase

from core import audit_crawl as c
from core import audit_technical as t


def soup_of(html):
    from bs4 import BeautifulSoup
    return BeautifulSoup(html, 'html.parser')


PAGE = """<html><head><title>Best savings account in India for 2026 | Example</title>
<meta name="description" content="Compare the best savings accounts in India by interest rate, fees and minimum balance, updated monthly.">
<meta name="viewport" content="width=device-width">
<meta property="og:title" content="Best savings account">
<link rel="canonical" href="https://www.example.com/savings/">
<link rel="alternate" hreflang="hi" href="https://example.com/hi/savings">
<script type="application/ld+json">{"@context":"https://schema.org","@graph":[
 {"@type":"Organization","name":"Example","url":"https://example.com"},
 {"@type":"Article","headline":"x","author":{"@type":"Person","name":"P"},"datePublished":"2026-01-01"},
 {"@type":"Person","name":"Priya"}]}</script>
</head><body>
<h1>Best savings account</h1>
<img src="/a.png" alt="a"><img src="/b.png"><img src="/c.png" alt="">
<script src="http://cdn.example.com/x.js"></script>
<a href="/rates">Savings account rates</a><a href="/faq">click here</a><a href="/faq#top">FAQ</a>
<a href="https://example.com/open">Open an account</a><a href="/brochure.pdf">PDF</a>
<a href="https://other.com/x">other</a><a href="mailto:a@b.c">mail</a>
<p>We are an award-winning, SEBI-registered platform with 12 years of experience.</p>
</body></html>"""


class PageSignalTests(SimpleTestCase):
    databases = []

    def signals(self, html=PAGE, url='https://example.com/savings'):
        page = c.analyse_html(url, html, 'example.com')
        return page, page['tech']

    def test_extracts_every_signal(self):
        page, s = self.signals()
        self.assertEqual(s['title_length'], len('Best savings account in India for 2026 | Example'))
        self.assertGreater(s['description_length'], 70)
        self.assertEqual(s['h1_count'], 1)
        self.assertFalse(s['noindex'])
        self.assertEqual(s['canonical_status'], 'ok', 'www + trailing slash normalise to the same page')
        self.assertTrue(s['viewport'])
        self.assertTrue(s['og'])
        self.assertEqual((s['images'], s['images_missing_alt']), (3, 1), 'alt="" counts as present')
        self.assertEqual(s['mixed_content'], 1)
        self.assertEqual(s['hreflang'], 1)
        self.assertTrue(s['https'])
        # internal: /rates, /faq (twice, fragment dropped), /open — the pdf, other.com and mailto are not
        self.assertEqual(s['internal_links'], 3)
        self.assertEqual(s['internal_urls'], ['https://example.com/rates', 'https://example.com/faq', 'https://example.com/open'])
        self.assertEqual(s['internal_anchors'], 4)
        self.assertEqual(s['generic_anchors'], 1)
        self.assertEqual(s['schema_gaps'], ['Organization missing logo, description, sameAs', 'Article missing dateModified', 'Person missing url'])
        self.assertTrue(s['has_person_schema'])
        self.assertEqual(s['credential_mentions'], 3)
        # GEO keys unchanged by the tech layer
        self.assertEqual(page['schema_types'], ['Article', 'Organization', 'Person'])
        self.assertEqual(page['author'], 'P')

    def test_missing_everything(self):
        _, s = self.signals('<html><body><h1>a</h1><h1>b</h1><p>hi</p></body></html>', url='http://example.com/x')
        self.assertEqual(s['title_length'], 0)
        self.assertEqual(s['description_length'], 0)
        self.assertEqual(s['h1_count'], 2)
        self.assertEqual(s['canonical_status'], 'missing')
        self.assertFalse(s['viewport'])
        self.assertFalse(s['https'])
        self.assertEqual(s['mixed_content'], 0, 'only https pages can have mixed content')
        self.assertEqual(s['internal_links'], 0)
        self.assertEqual(s['schema_gaps'], [])

    def test_noindex_and_canonical_mismatch(self):
        html = '<html><head><meta name="robots" content="NOINDEX, follow"><link rel="canonical" href="/other"></head><body></body></html>'
        _, s = self.signals(html)
        self.assertTrue(s['noindex'])
        self.assertEqual(s['canonical_status'], 'mismatch')
        self.assertEqual(s['canonical'], 'https://example.com/other')

    def test_norm_url(self):
        self.assertEqual(t.norm_url('HTTPS://WWW.Example.com/a/#frag'), 'https://example.com/a')
        self.assertEqual(t.norm_url('https://example.com'), 'https://example.com/')
        self.assertEqual(t.norm_url('https://example.com/a?x=1'), 'https://example.com/a?x=1')


class GraphTests(SimpleTestCase):
    databases = []

    def pages(self):
        def page(url, links, **extra):
            return {'url': url, 'title': extra.get('title', url), 'tech': {'internal_urls': links, **extra.get('tech', {})}}
        return [
            page('https://e.com/', ['https://e.com/a', 'https://e.com/b', 'https://e.com/missing']),
            page('https://e.com/a', ['https://e.com/c', 'https://e.com/']),
            page('https://e.com/b', []),
            page('https://e.com/c', []),
            page('https://e.com/lonely', []),
            {'url': 'https://e.com/down', 'parse_error': 'HTTP 404', 'status_code': 404},
        ]

    def test_depth_orphans_unsampled(self):
        g = t.link_graph(self.pages(), 'https://e.com')
        self.assertEqual(g['depth'], {'https://e.com/': 0, 'https://e.com/a': 1, 'https://e.com/b': 1, 'https://e.com/c': 2})
        self.assertEqual(g['orphans'], ['https://e.com/lonely'])
        self.assertEqual(g['unreached'], ['https://e.com/lonely'])
        self.assertEqual(g['unsampled'], ['https://e.com/missing'])

    def test_empty(self):
        self.assertEqual(t.link_graph([], 'https://e.com'), {'depth': {}, 'orphans': [], 'unreached': [], 'unsampled': []})


class SummaryTests(SimpleTestCase):
    databases = []

    def base(self, **over):
        b = {'pages_sampled': 4, 'bots_allowed': 5, 'bots_total': 5, 'sitemap_present': True, 'schema_coverage': 50,
             'recommended_types_present': ['Organization', 'Article'], 'avg_word_count': 600, 'question_heading_share': 25,
             'table_share': 0, 'author_share': 25, 'avg_external_links': 1.0, 'dated_pages': 2, 'stale_pages': 1}
        b.update(over)
        return b

    def pages(self):
        def tech(**k):
            d = {'title_length': 40, 'description_length': 100, 'meta_description': 'd', 'h1_count': 1, 'noindex': False,
                 'canonical_status': 'ok', 'viewport': True, 'images': 0, 'images_missing_alt': 0, 'mixed_content': 0,
                 'hreflang': 0, 'og': True, 'https': True, 'internal_links': 10, 'internal_anchors': 10, 'generic_anchors': 2,
                 'internal_urls': [], 'schema_gaps': [], 'has_person_schema': False, 'credential_mentions': 0}
            d.update(k)
            return d
        return [
            {'url': 'https://e.com/', 'title': 'Home', 'tech': tech(internal_urls=['https://e.com/a', 'https://e.com/b', 'https://e.com/c'])},
            {'url': 'https://e.com/a', 'title': 'Same', 'tech': tech(meta_description='dup', noindex=True, canonical_status='missing')},
            {'url': 'https://e.com/b', 'title': 'Same', 'tech': tech(meta_description='dup', h1_count=0, images=5, images_missing_alt=3, mixed_content=2)},
            {'url': 'https://e.com/c', 'title': '', 'tech': tech(title_length=0, description_length=0, meta_description='', h1_count=2, viewport=False,
                                                                 schema_gaps=['Organization missing description'], has_person_schema=True, credential_mentions=2)},
            {'url': 'https://e.com/d', 'parse_error': 'HTTP 500', 'status_code': 500},
        ]

    def test_counts_issues_and_health(self):
        s = t.technical_summary(self.pages(), self.base(), website='https://e.com', sitemap_children=2,
                                link_check={'checked': 10, 'broken': 2, 'examples': [{'url': 'https://e.com/x', 'status': 404}]})
        self.assertEqual(s['sitemap_children'], 2)
        self.assertEqual(s['avg_internal_links'], 10.0)
        self.assertEqual(s['descriptive_anchor_share'], 80)
        self.assertEqual(s['missing_title'], 1)
        self.assertEqual(s['duplicate_titles'], 2)
        self.assertEqual(s['missing_description'], 1)
        self.assertEqual(s['duplicate_descriptions'], 2)
        self.assertEqual((s['missing_h1'], s['multiple_h1']), (1, 1))
        self.assertEqual(s['noindex_pages'], 1)
        self.assertEqual(s['canonical_missing'], 1)
        self.assertEqual(s['missing_viewport'], 1)
        self.assertEqual(s['images_missing_alt_share'], 60)
        self.assertEqual(s['mixed_content_pages'], 1)
        self.assertEqual(s['person_schema_share'], 25)
        self.assertEqual(s['credential_share'], 25)
        self.assertEqual(s['schema_gaps'], [{'gap': 'Organization missing description', 'pages': 1}])
        self.assertEqual(s['orphan_pages'], 0, 'every sampled page is linked from the homepage')
        self.assertEqual(s['max_depth'], 1)
        # issues: critical first, then by count
        keys = [(i['key'], i['severity']) for i in s['technical_issues']]
        self.assertEqual(keys[0][1], 'critical')
        self.assertIn(('noindex', 'critical'), keys)
        self.assertIn(('missing_title', 'critical'), keys)
        self.assertIn(('mixed_content', 'critical'), keys)
        self.assertIn(('broken_links', 'critical'), keys)
        self.assertIn(('duplicate_titles', 'warning'), keys)
        self.assertIn(('schema_gaps', 'info'), keys)
        self.assertNotIn('error_pages', [k for k, _ in keys], 'failed fetches are not in the ok list')
        broken = next(i for i in s['technical_issues'] if i['key'] == 'broken_links')
        self.assertEqual((broken['count'], broken['of'], broken['examples']), (2, 10, ['e.com/x (404)']))
        self.assertEqual(broken['action'], 'Fix the broken internal links')
        # health
        h = s['health']
        cats = {c['key']: c for c in h['categories']}
        self.assertEqual(set(cats), {'crawlability', 'schema', 'depth', 'eeat', 'internal_linking', 'technical', 'backlinks', 'freshness', 'cwv'})
        self.assertEqual(cats['backlinks']['priority'], 'not_measured')
        self.assertIsNone(cats['cwv']['score'])
        self.assertEqual(cats['cwv']['priority'], 'not_measured')
        self.assertEqual(cats['crawlability']['score'], 95)          # 0.6*1 + 0.2*1 + 0.2*(1-0.25)
        self.assertEqual(cats['schema']['score'], 41)                # 0.6*0.5 + 0.4*(2/7)
        self.assertEqual(cats['freshness']['score'], 50)
        self.assertEqual(cats['freshness']['priority'], 'critical')
        self.assertEqual(cats['crawlability']['priority'], 'on_track')
        self.assertTrue(0 < h['score'] < 100)
        # weighted mean over the measured categories (cwv and backlinks dropped)
        measured = [c for c in h['categories'] if c['score'] is not None]
        expected = round(sum(c['score'] * c['weight'] for c in measured) / sum(c['weight'] for c in measured))
        self.assertEqual(h['score'], expected)
        # content patterns
        pats = {p['key']: p['status'] for p in s['content_patterns']}
        self.assertEqual(pats, {'answer_blocks': 'partial', 'front_loaded_facts': 'missing', 'comparison_tables': 'missing'})

    def test_no_tech_blocks_still_scores_what_it_can(self):
        pages = [{'url': 'https://e.com/', 'title': 'x', 'tech': {}}]
        s = t.technical_summary(pages, self.base(pages_sampled=1), website='https://e.com')
        self.assertEqual(s['technical_issues'], [])
        self.assertIsNotNone(s['health']['score'])
        self.assertEqual(len(s['content_patterns']), 3)

    def test_cwv_feeds_the_health_score(self):
        cwv = {'source': 'field', 'lcp_ms': 1800, 'cls': 0.02, 'inp_ms': 150, 'score': 100}
        s = t.technical_summary(self.pages(), self.base(), website='https://e.com', cwv=cwv)
        cat = next(c for c in s['health']['categories'] if c['key'] == 'cwv')
        self.assertEqual((cat['score'], cat['priority']), (100, 'on_track'))
        self.assertIn('LCP 1800 ms', cat['detail'])


class CwvTests(SimpleTestCase):
    databases = []

    def test_field_data_preferred(self):
        data = {'loadingExperience': {'metrics': {
                    'LARGEST_CONTENTFUL_PAINT_MS': {'percentile': 3680, 'category': 'AVERAGE'},
                    'CUMULATIVE_LAYOUT_SHIFT_SCORE': {'percentile': 0, 'category': 'FAST'},
                    'INTERACTION_TO_NEXT_PAINT': {'percentile': 425, 'category': 'AVERAGE'}}},
                'lighthouseResult': {'categories': {'performance': {'score': 0.65}},
                                     'audits': {'largest-contentful-paint': {'numericValue': 9999}}}}
        out = t.parse_cwv(data)
        self.assertEqual(out['source'], 'field')
        self.assertEqual((out['lcp_ms'], out['cls'], out['inp_ms']), (3680, 0.0, 425))
        self.assertEqual((out['lcp_ms_rating'], out['cls_rating'], out['inp_ms_rating']), ('needs_improvement', 'good', 'needs_improvement'))
        self.assertEqual(out['score'], 67)
        self.assertEqual(out['performance_score'], 65)

    def test_lab_fallback_and_none(self):
        data = {'lighthouseResult': {'audits': {'largest-contentful-paint': {'numericValue': 5200.4}, 'cumulative-layout-shift': {'numericValue': 0.31}}}}
        out = t.parse_cwv(data)
        self.assertEqual(out['source'], 'lab')
        self.assertEqual((out['lcp_ms'], out['cls'], out['inp_ms']), (5200, 0.31, None))
        self.assertEqual((out['lcp_ms_rating'], out['cls_rating'], out['inp_ms_rating']), ('poor', 'poor', None))
        self.assertEqual(out['score'], 0)
        self.assertIsNone(t.parse_cwv({}))
        self.assertIsNone(t.parse_cwv({'error': {'code': 429}}))
        self.assertIsNone(t.parse_cwv(None))

    def test_fetch_cwv_never_raises(self):
        with patch('requests.get', side_effect=RuntimeError('offline')):
            self.assertIsNone(t.fetch_cwv('https://e.com'))

        class R:
            ok = False
            status_code = 429
        with patch('requests.get', return_value=R()):
            self.assertIsNone(t.fetch_cwv('https://e.com', api_key='k'))


class LinkCheckTests(SimpleTestCase):
    databases = []

    def test_broken_links(self):
        statuses = {'https://e.com/ok': 200, 'https://e.com/gone': 404, 'https://e.com/dead': 0, 'https://e.com/err': 503}
        with patch.object(t, 'head_status', side_effect=lambda u, timeout=8: statuses[u]):
            r = t.check_links(list(statuses), limit=10, workers=2)
        self.assertEqual((r['checked'], r['broken']), (4, 3))
        self.assertEqual({e['url'] for e in r['examples']}, {'https://e.com/gone', 'https://e.com/dead', 'https://e.com/err'})

    def test_strict_mode_for_outbound_links(self):
        statuses = {'https://x.org/ok': 200, 'https://x.org/forbidden': 403, 'https://x.org/dead': 0, 'https://x.org/gone': 404, 'https://x.org/down': 503}
        with patch.object(t, 'head_status', side_effect=lambda u, timeout=8: statuses[u]):
            r = t.check_links(list(statuses), limit=10, workers=2, strict=True)
        self.assertEqual({e['url'] for e in r['examples']}, {'https://x.org/gone', 'https://x.org/down'}, '403 and unreachable are not counted as broken outbound links')
        self.assertEqual(r['broken'], 2)

    def test_limit_and_empty(self):
        with patch.object(t, 'head_status', return_value=200) as hs:
            r = t.check_links([f'https://e.com/{i}' for i in range(40)], limit=5, workers=2)
        self.assertEqual(hs.call_count, 5)
        self.assertEqual(r['checked'], 5)
        self.assertEqual(t.check_links([]), {'checked': 0, 'broken': 0, 'examples': []})


class PlanIntegrationTests(SimpleTestCase):
    databases = []

    def test_critical_issues_become_plan_items(self):
        from core import audit_scoring as s
        crawl_summary = {'pages_sampled': 4, 'sitemap_present': True, 'technical_issues': [
            {'key': 'noindex', 'label': 'Pages carrying noindex', 'severity': 'critical', 'count': 1, 'of': 4, 'fix': 'Remove it.', 'action': 'Remove noindex from pages that should rank'},
            {'key': 'missing_h1', 'label': 'Pages without an H1', 'severity': 'warning', 'count': 3, 'of': 4, 'fix': 'Add one.', 'action': 'Add a single H1 to every page'},
            {'key': 'schema_gaps', 'label': 'Schema blocks missing key fields', 'severity': 'info', 'count': 4, 'of': 4, 'fix': '', 'action': 'Complete the required schema fields'},
        ]}
        plan = s.visibility_plan(40, [], [], [], {}, None, [], crawl_summary=crawl_summary)
        items = {it['key']: it for b in plan['buckets'] for it in b['items']}
        self.assertIn('tech:noindex', items)
        self.assertEqual(items['tech:noindex']['owner'], 'dev')
        self.assertIn('1 of 4 sampled pages', items['tech:noindex']['why'])
        self.assertIn('tech:missing_h1', items, 'a warning on half the sample is worth an action')
        self.assertNotIn('tech:schema_gaps', items, 'info issues are not plan items')


class BacklinksTests(SimpleTestCase):
    databases = []
    SUMMARY = {'target': 'pixis.ai', 'rank': 370, 'backlinks': 17629, 'referring_domains': 2100, 'referring_main_domains': 2048,
               'referring_ips': 900, 'referring_pages': 15000, 'backlinks_nofollow': 4000, 'referring_domains_nofollow': 300,
               'broken_backlinks': 120, 'first_seen': '2019-04-02 10:11:12 +00:00'}
    LIVE = {'target': 'sharekhan.com', 'rank': 338, 'backlinks': 28752, 'referring_domains': 2934, 'referring_main_domains': 2633,
            'referring_domains_nofollow': 1257, 'referring_links_attributes': {'nofollow': 7161, 'noopener': 3098}}

    def test_parse(self):
        from core.audit_backlinks import parse_backlinks
        b = parse_backlinks(self.SUMMARY)
        self.assertEqual(b['authority_score'], 37, 'DataForSEO rank 0-1000 becomes 0-100')
        self.assertEqual(b['referring_domains'], 2048, 'main domains preferred over all referring domains')
        self.assertEqual(b['backlinks'], 17629)
        self.assertEqual(b['dofollow_share'], 77)
        self.assertEqual(b['broken_backlinks'], 120)
        self.assertEqual(b['first_seen'], '2019-04-02')
        # 0.6*37 + 40*log10(2049)/log10(10001) = 22.2 + 40*0.828 = 55.3
        self.assertEqual(b['score'], 55)
        self.assertIsNone(parse_backlinks({}))
        self.assertIsNone(parse_backlinks(None))
        live = parse_backlinks(self.LIVE)
        self.assertEqual((live['authority_score'], live['referring_domains'], live['dofollow_share']), (34, 2633, 75), 'nofollow read from link attributes')
        tiny = parse_backlinks({'rank': 0, 'backlinks': 0, 'referring_main_domains': 0})
        self.assertEqual((tiny['authority_score'], tiny['score'], tiny['dofollow_share']), (0, 0, None))

    def test_health_category(self):
        from core.audit_backlinks import parse_backlinks
        base = {'pages_sampled': 0, 'bots_allowed': 5, 'bots_total': 5, 'sitemap_present': True}
        s = t.technical_summary([], base, website='https://pixis.ai', backlinks=parse_backlinks(self.SUMMARY))
        cat = next(c for c in s['health']['categories'] if c['key'] == 'backlinks')
        self.assertEqual((cat['score'], cat['priority']), (55, 'critical'))
        self.assertIn('authority 37/100', cat['detail'])
        self.assertIn('2,048 referring domains', cat['detail'])
        self.assertEqual(s['backlinks']['referring_domains'], 2048)

    def test_fetch_never_raises_and_carries_cost(self):
        from core import audit_backlinks as ab

        class Client:
            cost = 0.0245
            def __init__(self):
                pass
            def summary(self, target, include_subdomains=True):
                assert target == 'pixis.ai'
                return BacklinksTests.SUMMARY
        with patch('core.backlinks_processor.BacklinksClient', Client):
            b = ab.fetch_backlinks('pixis.ai')
        self.assertEqual((b['authority_score'], b['cost_usd']), (37, 0.0245))
        with patch('core.backlinks_processor.BacklinksClient', side_effect=RuntimeError('DATAFORSEO_LOGIN not configured')):
            self.assertIsNone(ab.fetch_backlinks('pixis.ai'))

    def test_crawl_site_passes_backlinks_through(self):
        site = {'https://e.com/': '<html><head><title>e</title></head><body><h1>e</h1></body></html>'}
        def resp(u, timeout=15):
            return {'text': site.get(u), 'status': 200 if u in site else 404, 'final_url': u, 'redirects': 0}
        with patch.object(c, 'fetch_text', side_effect=lambda u, timeout=15: site.get(u)),              patch.object(c, 'fetch_response', side_effect=resp),              patch('core.audit_backlinks.fetch_backlinks', return_value={'authority_score': 12, 'referring_domains': 40, 'backlinks': 90, 'score': 21}) as fb:
            r = c.crawl_site('https://e.com', 'e.com', limit=2, budget_seconds=20, workers=1, link_checks=False, backlinks=True)
            r_off = c.crawl_site('https://e.com', 'e.com', limit=2, budget_seconds=20, workers=1, link_checks=False)
        self.assertEqual(fb.call_count, 1, 'off by default, one call when on')
        self.assertEqual(r['summary']['backlinks']['authority_score'], 12)
        self.assertEqual(next(x for x in r['summary']['health']['categories'] if x['key'] == 'backlinks')['score'], 21)
        self.assertIsNone(r_off['summary']['backlinks'])


class TierTwoTests(SimpleTestCase):
    """Phase Q: indexability, robots path rules, sitemap health, duplicates, thin pages, hreflang, link opportunities, multi-page CWV."""
    databases = []

    def test_robots_path_rules(self):
        robots = {'disallow': ['/private', '/tmp/*.html$', '/'], 'allow': ['/public', '/']}
        self.assertFalse(t.robots_blocks('/public/page', robots), 'longer Allow wins')
        self.assertTrue(t.robots_blocks('/private/x', robots))
        self.assertTrue(t.robots_blocks('/tmp/a.html', robots), 'wildcard rule')
        self.assertFalse(t.robots_blocks('/tmp/a.php', robots))
        self.assertFalse(t.robots_blocks('/anything', robots), 'Allow: / ties Disallow: / and allow wins the tie')
        self.assertFalse(t.robots_blocks('/x', None))

    def test_indexability_verdicts(self):
        ok = {'url': 'https://e.com/a', 'tech': {'canonical_status': 'ok'}}
        self.assertEqual(t.indexability(ok)['verdict'], 'indexable')
        self.assertEqual(t.indexability({'url': 'https://e.com/a', 'parse_error': 'HTTP 404', 'status_code': 404}), {'verdict': 'not_indexable', 'reason': 'HTTP 404'})
        self.assertEqual(t.indexability({'url': 'https://e.com/private/a', 'tech': {}}, {'disallow': ['/private']})['reason'], 'blocked by robots.txt')
        self.assertEqual(t.indexability({'url': 'https://e.com/a', 'tech': {'noindex': True}})['reason'], 'noindex meta tag')
        self.assertEqual(t.indexability({'url': 'https://e.com/a', 'tech': {}, 'x_robots': 'noindex, nofollow'})['reason'], 'X-Robots-Tag: noindex')
        self.assertEqual(t.indexability({'url': 'https://e.com/a', 'tech': {'canonical_status': 'mismatch'}})['verdict'], 'canonicalised')
        self.assertEqual(t.indexability({'url': 'https://e.com/a', 'tech': {}, 'redirects': 2, 'final_url': 'https://e.com/b'})['verdict'], 'redirected')
        self.assertEqual(t.indexability({'url': 'https://e.com/a', 'parse_error': 'fetch failed'})['verdict'], 'unknown')

    def test_sitemap_health(self):
        pages = [{'url': 'https://e.com/', 'tech': {}}, {'url': 'https://e.com/gone', 'parse_error': 'HTTP 404', 'status_code': 404},
                 {'url': 'https://e.com/moved', 'tech': {}, 'redirects': 1}, {'url': 'https://e.com/hidden', 'tech': {'noindex': True}},
                 {'url': 'https://e.com/extra', 'tech': {}}]
        h = t.sitemap_health(pages, ['https://e.com/', 'https://e.com/gone', 'https://e.com/moved/', 'https://www.e.com/hidden', 'https://e.com/never-fetched'])
        self.assertEqual((h['listed'], h['checked']), (5, 4))
        self.assertEqual([e['problem'] for e in h['errors']], ['HTTP 404', 'redirects', 'noindex'])
        self.assertEqual(h['not_in_sitemap'], ['https://e.com/extra'])
        self.assertEqual(t.sitemap_health(pages, []), {'listed': 0, 'checked': 0, 'errors': [], 'not_in_sitemap': []})

    def test_duplicates_and_shingles(self):
        base = ' '.join(f'word{i}' for i in range(200))
        a = {'url': 'https://e.com/a', 'tech': {'shingles': t.shingles(base)}}
        b = {'url': 'https://e.com/b', 'tech': {'shingles': t.shingles(base + ' tail words')}}
        c_ = {'url': 'https://e.com/c', 'tech': {'shingles': t.shingles(' '.join(f'other{i}' for i in range(200)))}}
        short = {'url': 'https://e.com/s', 'tech': {'shingles': t.shingles('too short')}}
        self.assertEqual(t.duplicate_groups([a, b, c_, short]), [['https://e.com/a', 'https://e.com/b']])
        self.assertEqual(t.shingles('too short'), [])
        self.assertEqual(t.similarity([], [1]), 0.0)

    def test_thin_and_page_extras(self):
        html = '<html><head><title>Tiny page here</title><meta property="og:title" content="x"><meta name="twitter:card" content="summary">'
        html += '<link rel="alternate" hreflang="en-in" href="/en"><link rel="alternate" hreflang="en_US" href="/zz">'
        html += '<script type="application/ld+json">{not json</script><script type="application/ld+json">{"@type":"Product","description":"d"}</script></head>'
        html += '<body><h1>Tiny</h1><h3>Skipped</h3><h2></h2><p>short body</p><img src="a.png" alt="a" width="10" height="10"><img src="b.png" alt="b" loading="lazy">'
        html += '<a href="/list?sort=asc">sorted</a><a href="/list?page=2">p2</a><a href="/about">About us</a></body></html>'
        page = c.analyse_html('https://e.com/tiny', html, 'e.com')
        s = page['tech']
        self.assertTrue(s['thin'])
        self.assertEqual(s['title_issue'], 'short')
        self.assertIsNone(s['description_issue'], 'no description at all is a different issue, not a length one')
        self.assertFalse(s['title_equals_h1'])
        self.assertEqual(s['heading_issues'], ['1 skipped level', '1 empty heading'])
        self.assertEqual((s['images_missing_dimensions'], s['images_lazy']), (1, 1))
        self.assertEqual(s['og_missing'], ['og:description', 'og:image'])
        self.assertTrue(s['twitter_card'])
        self.assertEqual((s['json_ld_tags'], s['json_ld_invalid']), (2, 1))
        self.assertEqual(s['rich_result_blockers'], ['Product: name'])
        self.assertEqual(s['hreflang_invalid'], ['en_US'], 'underscores are the classic mistake')
        self.assertEqual(s['param_links'], 2)
        self.assertFalse(s['has_params'])
        self.assertEqual(s['title_words'], ['tiny', 'page', 'here'])
        home = c.analyse_html('https://e.com/', '<html><body><p>short</p></body></html>', 'e.com')
        self.assertFalse(home['tech']['thin'], 'the homepage is never thin')
        util = c.analyse_html('https://e.com/contact-us', '<html><body><p>short</p></body></html>', 'e.com')
        self.assertFalse(util['tech']['thin'], 'utility pages are never thin')

    def test_hreflang_return_tags(self):
        en = {'url': 'https://e.com/en', 'tech': {'hreflang_entries': [('en', 'https://e.com/en'), ('hi', 'https://e.com/hi')], 'hreflang_invalid': []}}
        hi = {'url': 'https://e.com/hi', 'tech': {'hreflang_entries': [('hi', 'https://e.com/hi')], 'hreflang_invalid': ['x-yy-zz']}}
        errs = t.hreflang_errors([en, hi])
        self.assertEqual([e['problem'] for e in errs], ['/hi (hi) has no return tag', 'invalid hreflang code "x-yy-zz"'])

    def test_link_opportunities(self):
        pages = [
            {'url': 'https://e.com/', 'title': 'Home', 'tech': {'title_words': ['home'], 'h1_text': 'Home', 'internal_urls': ['https://e.com/demat']}},
            {'url': 'https://e.com/demat', 'title': 'Demat account opening guide', 'tech': {'title_words': ['demat', 'account', 'opening'], 'h1_text': 'Demat account', 'internal_urls': []}},
            {'url': 'https://e.com/blog', 'title': 'How to open a demat account fast', 'tech': {'title_words': ['open', 'demat', 'account', 'fast'], 'h1_text': 'Open a demat account', 'internal_urls': []}},
            {'url': 'https://e.com/linked', 'title': 'Demat account fees', 'tech': {'title_words': ['demat', 'account', 'fees'], 'h1_text': 'Fees', 'internal_urls': ['https://e.com/demat']}},
        ]
        ops = t.link_opportunities(pages)
        pairs = {(o['from'], o['to']) for o in ops}
        self.assertIn(('https://e.com/blog', 'https://e.com/demat'), pairs, 'blog talks about demat accounts but never links the guide')
        self.assertNotIn(('https://e.com/linked', 'https://e.com/demat'), pairs, 'already linked')
        self.assertNotIn(('https://e.com/', 'https://e.com/demat'), pairs, 'home does not share two title words')

    def test_fetch_cwv_pages_aggregates(self):
        def fake(u, key=''):
            return None if 'skip' in u else {'source': 'field', 'lcp_ms': 1000 if 'a' in u else 5000, 'cls': 0.0, 'inp_ms': 100, 'score': 100 if 'a' in u else 33,
                                             'performance_score': 90, 'mobile_friendly': True}
        with patch.object(t, 'fetch_cwv', side_effect=fake):
            out = t.fetch_cwv_pages(['https://e.com/a', 'https://e.com/skip', 'https://e.com/b'])
            self.assertIsNone(t.fetch_cwv_pages(['https://e.com/skip']))
        self.assertEqual(out['lcp_ms'], 1000, 'the first page (homepage) stays the headline')
        self.assertEqual([p['url'] for p in out['pages']], ['https://e.com/a', 'https://e.com/b'])
        self.assertEqual(out['site_score'], 66)
        self.assertTrue(out['mobile_friendly'])

    def test_summary_emits_tier_two_issues(self):
        base = {'pages_sampled': 3, 'bots_allowed': 5, 'bots_total': 5, 'sitemap_present': True, 'schema_coverage': 0, 'recommended_types_present': [],
                'avg_word_count': 100, 'question_heading_share': 0, 'table_share': 0, 'author_share': 0, 'avg_external_links': 0, 'dated_pages': 0, 'stale_pages': 0}
        def tech(**k):
            d = {'title_length': 10, 'title_issue': 'short', 'description_length': 0, 'meta_description': '', 'h1_count': 1, 'noindex': False, 'canonical_status': 'ok',
                 'viewport': True, 'images': 0, 'images_missing_alt': 0, 'images_missing_dimensions': 0, 'mixed_content': 0, 'hreflang': 0, 'hreflang_entries': [],
                 'og': False, 'og_missing': ['og:image'], 'https': True, 'internal_links': 1, 'internal_anchors': 1, 'generic_anchors': 0, 'internal_urls': [],
                 'schema_gaps': [], 'has_person_schema': False, 'credential_mentions': 0, 'thin': True, 'json_ld_invalid': 1, 'rich_result_blockers': ['Product: name'],
                 'heading_issues': ['1 empty heading'], 'title_equals_h1': True, 'shingles': [], 'title_words': [], 'has_params': True, 'param_links': 0}
            d.update(k)
            return d
        pages = [{'url': 'https://e.com/', 'title': 'x', 'tech': tech(has_params=False, thin=False)},
                 {'url': 'https://e.com/a?page=2', 'title': 'x', 'tech': tech(canonical_status='missing')},
                 {'url': 'https://e.com/chain', 'title': 'x', 'tech': tech(), 'redirects': 3, 'final_url': 'https://e.com/final'}]
        s = t.technical_summary(pages, base, website='https://e.com', sitemap_urls=['https://e.com/', 'https://e.com/chain'],
                                site={'hsts': False, 'http_redirects_to_https': False, 'ssl_error': False}, robots={'disallow': [], 'allow': []},
                                link_check={'checked': 5, 'broken': 0, 'examples': [], 'external_checked': 3, 'external_broken': 1, 'external_examples': [{'url': 'https://x.org/dead', 'status': 404}]})
        keys = {i['key'] for i in s['technical_issues']}
        for k in ('http_no_redirect', 'hsts_missing', 'redirect_chains', 'title_length', 'title_equals_h1', 'heading_structure', 'og_incomplete',
                  'invalid_json_ld', 'rich_result_blockers', 'thin_content', 'param_urls', 'sitemap_errors', 'not_in_sitemap', 'broken_external_links'):
            self.assertIn(k, keys, k)
        self.assertEqual(s['indexability'], {'indexable': 2, 'not_indexable': 0, 'canonicalised': 0, 'redirected': 1, 'unknown': 0})
        self.assertEqual(s['redirect_chains'], 1)
        self.assertEqual(s['thin_pages'], 2)
        self.assertEqual(s['sitemap_health']['errors'][0]['problem'], 'redirects')
        first = s['technical_issues'][0]
        self.assertEqual(first['severity'], 'critical')
        self.assertIn('urls', first)
        chain = next(i for i in s['technical_issues'] if i['key'] == 'redirect_chains')
        self.assertEqual(chain['urls'], ['https://e.com/chain'])


class SmallChecksTests(SimpleTestCase):
    """Phase R: soft 404s, page weight, scripts, image formats, lang, favicon, meta refresh, certificate, security headers, snippets."""
    databases = []

    def test_page_signals(self):
        html = ('<html><head><title>Page not found</title><meta http-equiv="refresh" content="0;url=/home"><link rel="icon" href="/favicon.ico">'
                '<link rel="stylesheet" href="/a.css"><link rel="stylesheet" href="/b.css">'
                '<script src="/1.js"></script><script>var x=1;</script><script type="application/ld+json">{"@type":"WebSite","name":"x"}</script></head>'
                '<body><h1>Sorry</h1><img src="/a.jpg" alt="a"><img src="/b.png" alt="b" srcset="/b-2x.png 2x"><picture><source srcset="/c.webp"><img src="/c.jpg" alt="c"></picture>'
                '<img src="/d.webp" alt="d"><p>The page you requested could not be located.</p></body></html>')
        s = c.analyse_html('https://e.com/gone', html, 'e.com')['tech']
        self.assertTrue(s['soft_404'])
        self.assertTrue(s['meta_refresh'])
        self.assertTrue(s['favicon'])
        self.assertEqual(s['lang'], '')
        self.assertEqual(s['scripts'], 2, 'JSON-LD is not a script for this purpose')
        self.assertEqual(s['stylesheets'], 2)
        self.assertEqual((s['images_legacy'], s['images_srcset']), (1, 1), 'srcset or <picture> excuses a JPG/PNG')
        ok = c.analyse_html('https://e.com/fine', '<html lang="en-IN"><head><title>Savings accounts compared</title></head><body><h1>Savings</h1>' + '<p>word</p>' * 80 + '</body></html>', 'e.com')['tech']
        self.assertFalse(ok['soft_404'])
        self.assertEqual(ok['lang'], 'en-IN')
        self.assertFalse(ok['favicon'])

    def test_site_issues_and_snippets(self):
        base = {'pages_sampled': 2, 'bots_allowed': 5, 'bots_total': 5, 'sitemap_present': True, 'schema_coverage': 0, 'recommended_types_present': [],
                'avg_word_count': 500, 'question_heading_share': 0, 'table_share': 0, 'author_share': 0, 'avg_external_links': 0, 'dated_pages': 0, 'stale_pages': 0}
        tech = {'title_length': 40, 'description_length': 100, 'meta_description': 'd', 'h1_count': 1, 'noindex': False, 'canonical_status': 'ok', 'viewport': True,
                'images': 4, 'images_missing_alt': 0, 'images_missing_dimensions': 0, 'images_legacy': 4, 'mixed_content': 0, 'hreflang': 0, 'hreflang_entries': [],
                'og': True, 'og_missing': [], 'https': True, 'internal_links': 5, 'internal_anchors': 5, 'generic_anchors': 0, 'internal_urls': [], 'schema_gaps': [],
                'has_person_schema': False, 'credential_mentions': 0, 'thin': False, 'json_ld_invalid': 0, 'rich_result_blockers': [], 'heading_issues': [],
                'title_equals_h1': False, 'shingles': [], 'title_words': [], 'has_params': False, 'param_links': 0, 'scripts': 45, 'stylesheets': 2,
                'images_srcset': 0, 'soft_404': False, 'lang': '', 'favicon': False, 'meta_refresh': False}
        pages = [{'url': 'https://e.com/', 'title': 'Home', 'tech': dict(tech), 'html_bytes': 450_000},
                 {'url': 'https://e.com/missing', 'title': 'Not found', 'tech': {**tech, 'soft_404': True, 'meta_refresh': True}, 'html_bytes': 10_000}]
        site = {'hsts': True, 'ssl_error': False, 'http_redirects_to_https': True, 'certificate': {'expires': '2026-09-20', 'days_left': 5, 'issuer': 'X'},
                'security_headers': {'content-security-policy': False, 'x-content-type-options': True, 'x-frame-options': False, 'referrer-policy': False}}
        s = t.technical_summary(pages, base, website='https://e.com', site=site, robots={'disallow': [], 'allow': []})
        by = {i['key']: i for i in s['technical_issues']}
        self.assertEqual(by['cert_expiring']['severity'], 'critical')
        self.assertIn('5 days', by['cert_expiring']['label'])
        self.assertEqual(by['security_headers']['examples'], ['Content-Security-Policy', 'X-Frame-Options', 'Referrer-Policy'])
        self.assertEqual(by['soft_404']['urls'], ['https://e.com/missing'])
        self.assertEqual(by['soft_404']['severity'], 'critical')
        self.assertEqual(by['meta_refresh']['count'], 1)
        self.assertEqual(by['html_heavy']['urls'], ['https://e.com/'])
        self.assertEqual(by['script_heavy']['count'], 2)
        self.assertEqual(by['legacy_image_formats']['count'], 2)
        self.assertEqual(by['lang_missing']['count'], 2)
        self.assertIn('no_favicon', by)
        self.assertTrue(by['soft_404']['snippet'].startswith('return a real 404'))
        self.assertIn('<html lang', by['lang_missing']['snippet'])
        self.assertTrue(all('snippet' in i for i in s['technical_issues']))
        self.assertEqual(s['soft_404_pages'], 1)
        self.assertEqual(s['avg_html_kb'], 230.0)
        self.assertEqual(s['avg_scripts'], 45.0)
        self.assertEqual(s['images_legacy_share'], 100)
        # a healthy cert and full headers raise nothing
        s2 = t.technical_summary(pages[:1], base, website='https://e.com', robots={'disallow': [], 'allow': []},
                                 site={'hsts': True, 'ssl_error': False, 'http_redirects_to_https': True, 'certificate': {'days_left': 200},
                                       'security_headers': {k: True for k in t.SECURITY_HEADERS}})
        self.assertNotIn('cert_expiring', {i['key'] for i in s2['technical_issues']})
        self.assertNotIn('security_headers', {i['key'] for i in s2['technical_issues']})

    def test_certificate_info_never_raises(self):
        self.assertIsNone(c.certificate_info('invalid.invalid', timeout=1))
