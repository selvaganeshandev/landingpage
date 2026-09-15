"""
Tests for core.audit_scoring — the pure scoring layer behind the Audit Engine.

DB-free (SimpleTestCase, databases = []): every function takes plain dicts and
touches no model, so these pin the arithmetic without a database:

  * score bands and their edges
  * the four weighted components, each in isolation
  * a fully-absent brand scores 0, a perfect brand scores 100
  * failed / rate-limited runs are excluded from every denominator
  * share of voice, citation control, per-engine summary and evidence rows
  * SEO visibility index and striking distance
  * the twelve measures: crawl-dependent ones report "not measured", never guess
  * score_audit() returns headline columns consistent with the report body
"""
from django.test import SimpleTestCase

from core import audit_scoring as s


def row(**overrides):
    base = {
        'prompt_index': 1, 'prompt_text': 'Best savings account?', 'funnel_stage': 'middle',
        'platform': 'ChatGPT', 'status': 'ok', 'is_mention': False, 'is_cited': False,
        'position': None, 'sentiment': '', 'competitors_mentioned': [], 'cited_domains': [],
    }
    base.update(overrides)
    return base


BRAND = 'HDFC Bank'
HOST = 'hdfcbank.com'
RIVALS = ['icicibank.com', 'paisabazaar.com']


class BandTests(SimpleTestCase):
    databases = []

    def test_band_edges(self):
        self.assertEqual(s.geo_stage_for(0), ('absent', 'Absent'))
        self.assertEqual(s.geo_stage_for(25), ('absent', 'Absent'))
        self.assertEqual(s.geo_stage_for(26), ('present', 'Present'))
        self.assertEqual(s.geo_stage_for(50), ('present', 'Present'))
        self.assertEqual(s.geo_stage_for(51), ('preferred', 'Preferred'))
        self.assertEqual(s.geo_stage_for(75), ('preferred', 'Preferred'))
        self.assertEqual(s.geo_stage_for(76), ('default', 'Default'))
        self.assertEqual(s.geo_stage_for(100), ('default', 'Default'))

    def test_out_of_range_and_none_are_clamped(self):
        self.assertEqual(s.geo_stage_for(None)[0], 'absent')
        self.assertEqual(s.geo_stage_for(-5)[0], 'absent')
        self.assertEqual(s.geo_stage_for(140)[0], 'default')


class HostTests(SimpleTestCase):
    databases = []

    def test_normalize_host(self):
        self.assertEqual(s.normalize_host('https://www.HDFCBank.com/savings?x=1'), 'hdfcbank.com')
        self.assertEqual(s.normalize_host('hdfcbank.com'), 'hdfcbank.com')
        self.assertEqual(s.normalize_host('https://coin.zerodha.com`'), 'coin.zerodha.com')
        self.assertEqual(s.normalize_host('groww.in`),'), 'groww.in')
        self.assertEqual(s.normalize_host('"paytm.com".'), 'paytm.com')
        self.assertEqual(s.normalize_host(''), '')
        self.assertEqual(s.normalize_host(None), '')


class ComponentTests(SimpleTestCase):
    databases = []

    def test_frequency_is_mention_rate_over_completed_runs(self):
        rows = [row(is_mention=True), row(is_mention=False), row(status='failed', is_mention=True)]
        self.assertAlmostEqual(s.frequency_component(rows), 0.5)

    def test_placement_first_is_perfect_and_decays(self):
        self.assertAlmostEqual(s.placement_component([row(is_mention=True, position=1)]), 1.0)
        self.assertAlmostEqual(s.placement_component([row(is_mention=True, position=3)]), 0.6)
        self.assertAlmostEqual(s.placement_component([row(is_mention=True, position=9)]), 0.0)

    def test_placement_ignores_unmentioned_and_positionless(self):
        self.assertEqual(s.placement_component([row(is_mention=False, position=1)]), 0.0)
        self.assertEqual(s.placement_component([row(is_mention=True, position=None)]), 0.0)

    def test_sourcing_is_citation_rate(self):
        rows = [row(is_cited=True), row(), row(), row()]
        self.assertAlmostEqual(s.sourcing_component(rows), 0.25)

    def test_framing_averages_sentiment_where_mentioned(self):
        rows = [row(is_mention=True, sentiment='positive'), row(is_mention=True, sentiment='negative'), row()]
        self.assertAlmostEqual(s.framing_component(rows), 0.6)

    def test_empty_evidence_scores_zero(self):
        self.assertEqual(s.frequency_component([]), 0.0)
        self.assertEqual(s.placement_component([]), 0.0)
        self.assertEqual(s.sourcing_component([]), 0.0)
        self.assertEqual(s.framing_component([]), 0.0)


class GeoScoreTests(SimpleTestCase):
    databases = []

    def test_absent_brand_scores_zero(self):
        score, breakdown = s.geo_score([row(), row(platform='Claude')])
        self.assertEqual(score, 0)
        self.assertEqual(set(breakdown), {'placement', 'frequency', 'sourcing', 'framing'})

    def test_perfect_brand_scores_100(self):
        rows = [row(is_mention=True, is_cited=True, position=1, sentiment='positive', platform=p)
                for p in ('ChatGPT', 'Claude', 'Perplexity')]
        score, breakdown = s.geo_score(rows)
        self.assertEqual(score, 100)
        self.assertEqual(breakdown, {'placement': 35.0, 'frequency': 25.0, 'sourcing': 25.0, 'framing': 15.0})

    def test_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(s.WEIGHTS.values()), 1.0)

    def test_failed_runs_do_not_count_against_the_brand(self):
        good = [row(is_mention=True, is_cited=True, position=1, sentiment='positive')]
        with_failures = good + [row(status='rate_limited', platform='Perplexity'), row(status='failed', platform='Claude')]
        self.assertEqual(s.geo_score(good)[0], s.geo_score(with_failures)[0])


class AggregationTests(SimpleTestCase):
    databases = []

    def setUp(self):
        self.rows = [
            row(prompt_index=1, platform='ChatGPT', is_mention=True, is_cited=True, position=1,
                cited_domains=['https://www.hdfcbank.com/savings', 'rbi.org.in']),
            row(prompt_index=1, platform='Perplexity', is_mention=True, position=2,
                competitors_mentioned=['Paisabazaar'], cited_domains=['paisabazaar.com', 'paisabazaar.com']),
            row(prompt_index=2, platform='ChatGPT', is_mention=False,
                competitors_mentioned=['ICICI Bank', 'Paisabazaar'], cited_domains=['icicibank.com']),
            row(prompt_index=2, platform='Perplexity', status='failed'),
        ]

    def test_engine_summary(self):
        by = {e['platform']: e for e in s.engine_summary(self.rows)}
        self.assertEqual(by['ChatGPT']['asked'], 2)
        self.assertEqual(by['ChatGPT']['mentioned'], 1)
        self.assertEqual(by['ChatGPT']['cited'], 1)
        self.assertEqual(by['ChatGPT']['mention_rate'], 0.5)
        self.assertFalse(by['ChatGPT']['preferred'])  # exactly half is not "more than half"
        self.assertEqual(by['ChatGPT']['top_rival'], 'ICICI Bank')
        self.assertEqual(by['Perplexity']['answered'], 1)
        self.assertTrue(by['Perplexity']['preferred'])
        self.assertEqual(by['Perplexity']['avg_position'], 2.0)

    def test_share_of_voice(self):
        share, ranked = s.share_of_voice(self.rows, BRAND)
        # brand 2, Paisabazaar 2, ICICI 1 -> 5 mentions
        self.assertEqual(share, 40.0)
        self.assertEqual(ranked[0]['mentions'], 2)
        self.assertTrue(any(r['is_you'] for r in ranked))
        self.assertEqual(sum(r['mentions'] for r in ranked), 5)

    def test_share_of_voice_lists_brand_even_when_absent(self):
        share, ranked = s.share_of_voice([row(competitors_mentioned=['ICICI Bank'])], BRAND)
        self.assertEqual(share, 0.0)
        self.assertEqual([r for r in ranked if r['is_you']][0]['mentions'], 0)

    def test_citation_control(self):
        ctrl = s.citation_control(self.rows, HOST, RIVALS)
        # hdfcbank(1 owned) rbi(1 third) paisabazaar x2 (competitor) icici (competitor) = 5
        self.assertEqual(ctrl['total_citations'], 5)
        self.assertEqual(ctrl['owned'], 20.0)
        self.assertEqual(ctrl['competitor'], 60.0)
        self.assertEqual(ctrl['third_party'], 20.0)
        self.assertEqual(ctrl['top_sources'][0], {'host': 'paisabazaar.com', 'count': 2})

    def test_citation_control_treats_subdomains_as_owned(self):
        ctrl = s.citation_control([row(cited_domains=['blog.hdfcbank.com'])], HOST, RIVALS)
        self.assertEqual(ctrl['owned'], 100.0)

    def test_prompt_evidence(self):
        ev = s.prompt_evidence(self.rows, HOST)
        self.assertEqual(len(ev), 2)
        self.assertEqual(ev[0]['engines'], {'ChatGPT': 'cited', 'Perplexity': 'mentioned'})
        self.assertEqual(ev[0]['cited_instead'], ['paisabazaar.com'])
        self.assertEqual(ev[1]['engines'], {'ChatGPT': 'absent', 'Perplexity': 'failed'})
        self.assertEqual(ev[1]['cited_instead'], ['icicibank.com'])


class SeoTests(SimpleTestCase):
    databases = []

    def test_empty_keywords(self):
        out = s.seo_summary([])
        self.assertEqual(out['keywords_total'], 0)
        self.assertIsNone(out['visibility'])

    def test_counts_and_visibility(self):
        kws = [
            {'keyword': 'a', 'search_volume': 1000, 'position': 1},    # full credit
            {'keyword': 'b', 'search_volume': 1000, 'position': 10},   # 10% credit
            {'keyword': 'c', 'search_volume': 1000, 'position': 15},   # striking distance, no credit
            {'keyword': 'd', 'search_volume': 1000, 'position': None}, # unranked
        ]
        out = s.seo_summary(kws)
        self.assertEqual(out['keywords_total'], 4)
        self.assertEqual(out['top10'], 2)
        self.assertEqual(out['striking_distance'], 1)
        self.assertAlmostEqual(out['visibility'], 27.5)  # (1.0 + 0.1) / 4
        self.assertEqual(len(out['top_keywords']), 4)

    def test_null_volume_counts_as_one(self):
        out = s.seo_summary([{'keyword': 'a', 'search_volume': None, 'position': 1}])
        self.assertEqual(out['visibility'], 100.0)


class MeasureTests(SimpleTestCase):
    databases = []

    def test_crawl_measures_are_not_guessed_without_crawl_data(self):
        ms = s.measures([row(is_mention=True, position=1)], BRAND, HOST, RIVALS)
        findable = [m for m in ms if m['pillar'] == 'findable']
        self.assertEqual(len(findable), 4)
        self.assertTrue(all(m['score'] is None and m['status'] is None for m in findable))
        self.assertIsNone(s.pillar_scores(ms)['findable'])

    def test_crawl_measures_are_used_when_present(self):
        crawl = {'bot_access': {'value': '6 of 6', 'score': 82, 'evidence': 'robots allow'}}
        ms = {m['key']: m for m in s.measures([row()], BRAND, HOST, RIVALS, crawl=crawl)}
        self.assertEqual(ms['bot_access']['score'], 82)
        self.assertEqual(ms['bot_access']['status'], 'pass')
        self.assertIsNone(ms['page_freshness']['score'])

    def test_thirteen_measures_across_three_pillars(self):
        ms = s.measures([row()], BRAND, HOST, RIVALS)
        self.assertEqual(len(ms), 13)
        self.assertEqual({m['pillar'] for m in ms}, {'findable', 'cited', 'chosen'})
        self.assertEqual(len({m['key'] for m in ms}), 13)

    def test_pillar_scores_average_only_measured(self):
        ms = [
            {'pillar': 'chosen', 'score': 80}, {'pillar': 'chosen', 'score': 40},
            {'pillar': 'cited', 'score': None},
        ]
        self.assertEqual(s.pillar_scores(ms), {'findable': None, 'cited': None, 'chosen': 60})

    def test_scores_are_clamped_to_0_100(self):
        ms = {m['key']: m for m in s.measures(
            [row(is_mention=True, is_cited=True, position=1, sentiment='positive',
                 cited_domains=['hdfcbank.com'])], BRAND, HOST, RIVALS)}
        for m in ms.values():
            if m['score'] is not None:
                self.assertTrue(0 <= m['score'] <= 100, m)


class QuickWinTests(SimpleTestCase):
    databases = []

    def test_rival_citation_gap_is_first_win(self):
        rows = [row(prompt_index=i, cited_domains=['paisabazaar.com']) for i in range(1, 5)]
        result = s.score_audit(rows, BRAND, HOST, RIVALS)
        wins = result['report']['quick_wins']
        self.assertTrue(1 <= len(wins) <= 3)
        self.assertIn('paisabazaar.com', wins[0]['title'])
        self.assertEqual(wins, sorted(wins, key=lambda w: -w['projected_geo_lift']))

    def test_rival_gap_skips_institution_hosts(self):
        rows = [row(prompt_index=i, cited_domains=['sebi.gov.in', 'rbi.org.in', 'paisabazaar.com']) for i in range(1, 4)]
        wins = s.score_audit(rows, BRAND, HOST, RIVALS)['report']['quick_wins']
        gap = [w for w in wins if w['title'].startswith('Earn the citations')]
        self.assertEqual(len(gap), 1)
        self.assertIn('paisabazaar.com', gap[0]['title'])
        self.assertNotIn('sebi', gap[0]['title'])

    def test_absent_brand_gets_a_fallback_win(self):
        wins = s.score_audit([row()], BRAND, HOST, RIVALS)['report']['quick_wins']
        self.assertTrue(any('Publish answer pages' in w['title'] for w in wins))

    def test_fully_mentioned_brand_is_not_told_to_publish_for_absent_prompts(self):
        rows = [row(prompt_index=i, is_mention=True, position=1, cited_domains=['news.example.com'])
                for i in range(1, 4)]
        wins = s.score_audit(rows, BRAND, HOST, RIVALS)['report']['quick_wins']
        self.assertFalse(any('Publish answer pages' in w['title'] for w in wins))
        # ...but it is told to become the cited source: 0% owned citations.
        self.assertTrue(any('Become the page' in w['title'] for w in wins))

    def test_no_wins_when_nothing_is_wrong(self):
        rows = [row(prompt_index=i, is_mention=True, is_cited=True, position=1,
                    cited_domains=['hdfcbank.com']) for i in range(1, 4)]
        self.assertEqual(s.score_audit(rows, BRAND, HOST, RIVALS)['report']['quick_wins'], [])


class ScoreAuditTests(SimpleTestCase):
    databases = []

    def test_headline_matches_report(self):
        rows = [
            row(prompt_index=1, platform='ChatGPT', is_mention=True, is_cited=True, position=1, sentiment='positive'),
            row(prompt_index=1, platform='Claude', is_mention=True, position=2),
            row(prompt_index=2, platform='ChatGPT', is_mention=True, position=1),
            row(prompt_index=2, platform='Claude', status='failed'),
        ]
        kws = [{'keyword': 'a', 'search_volume': 100, 'position': 3}]
        out = s.score_audit(rows, BRAND, HOST, RIVALS, keyword_rows=kws)
        h, r = out['headline'], out['report']
        self.assertEqual(h['geo_score'], r['geo']['score'])
        self.assertEqual(h['geo_stage'], r['geo']['stage'])
        self.assertEqual(h['total_runs'], 3)
        self.assertEqual(h['appearances'], 3)
        self.assertEqual(h['cited_runs'], 1)
        self.assertEqual(h['engines_total'], 2)
        self.assertEqual(h['engines_preferred'], 2)
        self.assertEqual(h['keywords_total'], 1)
        self.assertEqual(h['keywords_top10'], 1)
        self.assertEqual(h['seo_visibility'], r['seo']['visibility'])
        self.assertEqual(r['version'], 2)
        self.assertEqual(r['geo']['runs_total'], 4)
        self.assertEqual(r['geo']['runs_answered'], 3)
        self.assertIn('pillars', r)
        self.assertEqual(len(r['measures']), 13)

    def test_no_keywords_means_no_seo_section(self):
        out = s.score_audit([row()], BRAND, HOST, RIVALS)
        self.assertIsNone(out['report']['seo'])
        self.assertIsNone(out['headline']['seo_visibility'])
        self.assertEqual(out['headline']['keywords_total'], 0)

    def test_empty_audit_does_not_crash(self):
        out = s.score_audit([], BRAND, HOST, [])
        self.assertEqual(out['headline']['geo_score'], 0)
        self.assertEqual(out['headline']['geo_stage'], 'absent')
        self.assertEqual(out['report']['geo']['engines'], [])


class GapTypeTests(SimpleTestCase):
    databases = []

    def test_each_gap_type(self):
        self.assertEqual(s.gap_type([row(is_mention=True, position=2)]), 'won')
        self.assertEqual(s.gap_type([row(is_mention=True, position=5), row(platform='Claude', is_mention=True, position=4)]), 'position_gap')
        self.assertEqual(s.gap_type([row(is_mention=True, position=None)]), 'position_gap', 'named but order unknown counts as buried')
        self.assertEqual(s.gap_type([row(competitors_mentioned=['ICICI Bank'])]), 'visibility_gap')
        self.assertEqual(s.gap_type([row(cited_domains=['paisabazaar.com'])]), 'visibility_gap')
        self.assertEqual(s.gap_type([row()]), 'educational')
        self.assertEqual(s.gap_type([row(status='failed')]), 'no_data')

    def test_evidence_carries_gap_type_and_best_position(self):
        rows = [
            row(prompt_index=1, platform='ChatGPT', is_mention=True, position=4, competitors_mentioned=['Paisabazaar']),
            row(prompt_index=1, platform='Claude', is_mention=True, position=1, competitors_mentioned=['Paisabazaar', 'ICICI Bank']),
            row(prompt_index=2, platform='ChatGPT', competitors_mentioned=['ICICI Bank']),
        ]
        ev = {e['prompt_index']: e for e in s.prompt_evidence(rows, HOST)}
        self.assertEqual(ev[1]['gap_type'], 'won')
        self.assertEqual(ev[1]['best_position'], 1.0)
        self.assertEqual(ev[1]['top_competitor'], 'Paisabazaar')
        self.assertEqual(ev[1]['runs'], 2)
        self.assertEqual(ev[2]['gap_type'], 'visibility_gap')
        self.assertIsNone(ev[2]['best_position'])

    def test_gap_counts_in_report(self):
        rows = [row(prompt_index=1, is_mention=True, position=1), row(prompt_index=2), row(prompt_index=3, competitors_mentioned=['X'])]
        counts = s.score_audit(rows, BRAND, HOST, [])['report']['geo']['gap_counts']
        self.assertEqual(counts, {'won': 1, 'educational': 1, 'visibility_gap': 1})


class MultiRunTests(SimpleTestCase):
    databases = []

    def test_platform_outcome_is_majority_over_runs(self):
        runs = [row(run_index=1, is_mention=True, is_cited=True), row(run_index=2, is_mention=True), row(run_index=3)]
        self.assertEqual(s._platform_outcome(runs), 'mentioned', '2 of 3 mentioned, only 1 cited')
        runs = [row(run_index=1, is_cited=True, is_mention=True), row(run_index=2, is_cited=True, is_mention=True), row(run_index=3)]
        self.assertEqual(s._platform_outcome(runs), 'cited')
        self.assertEqual(s._platform_outcome([row(), row(is_mention=True)]), 'mentioned', 'a tie rounds up')
        self.assertEqual(s._platform_outcome([row(status='failed'), row(status='rate_limited')]), 'failed')

    def test_evidence_collapses_runs_and_reports_runs_per_prompt(self):
        rows = [row(prompt_index=1, run_index=i, is_mention=True, position=1) for i in (1, 2, 3)]
        out = s.score_audit(rows, BRAND, HOST, [])
        ev = out['report']['geo']['evidence'][0]
        self.assertEqual(ev['engines'], {'ChatGPT': 'mentioned'})
        self.assertEqual(ev['runs'], 3)
        self.assertEqual(out['report']['geo']['runs_per_prompt'], 3)
        self.assertEqual(out['headline']['total_runs'], 3, 'every run counts in the rate denominators')


class FunnelMatrixTests(SimpleTestCase):
    databases = []

    def test_cells_and_stage_totals(self):
        rows = [
            row(prompt_index=1, funnel_stage='top', platform='ChatGPT', is_mention=True),
            row(prompt_index=1, funnel_stage='top', platform='Claude'),
            row(prompt_index=2, funnel_stage='bottom', platform='ChatGPT', is_mention=True, is_cited=True),
            row(prompt_index=2, funnel_stage='bottom', platform='Claude', status='failed'),
        ]
        f = s.funnel_matrix(rows)
        self.assertEqual(f['stages'], ['top', 'middle', 'bottom'])
        self.assertEqual(f['platforms'], ['ChatGPT', 'Claude'])
        self.assertEqual(f['cells']['top']['ChatGPT'], {'asked': 1, 'mentioned': 1, 'cited': 0, 'rate': 100})
        self.assertEqual(f['cells']['top']['Claude']['rate'], 0)
        self.assertEqual(f['cells']['bottom']['Claude'], {'asked': 0, 'mentioned': 0, 'cited': 0, 'rate': None})
        self.assertEqual(f['cells']['middle']['ChatGPT']['rate'], None)
        self.assertEqual(f['by_stage']['top'], {'label': 'TOFU', 'prompts': 1, 'asked': 2, 'mentioned': 1, 'rate': 50})
        self.assertEqual(f['by_stage']['bottom']['rate'], 100)
        self.assertEqual(f['by_stage']['middle']['prompts'], 0)


class CompetitorMatrixTests(SimpleTestCase):
    databases = []

    def test_rows_shares_positions_and_callouts(self):
        rows = [
            row(prompt_index=1, funnel_stage='top', is_mention=True, position=2, competitors_mentioned=['Paisabazaar'], rival_positions={'Paisabazaar': 1}),
            row(prompt_index=2, funnel_stage='bottom', competitors_mentioned=['Paisabazaar', 'ICICI Bank'], rival_positions={'Paisabazaar': 1, 'ICICI Bank': 2}),
            row(prompt_index=3, funnel_stage='bottom', competitors_mentioned=['Paisabazaar'], rival_positions={'Paisabazaar': 2}),
            row(prompt_index=4, funnel_stage='top', status='failed'),
        ]
        m = s.competitor_matrix(rows, BRAND)
        by = {r['name']: r for r in m['rows']}
        self.assertEqual(m['rows'][0]['name'], 'Paisabazaar', 'most prompts first')
        self.assertEqual(by['Paisabazaar']['prompts_ranked'], 3)
        self.assertEqual(by['Paisabazaar']['prompts_total'], 4)
        self.assertEqual(by['Paisabazaar']['share'], 75)
        self.assertEqual(by['Paisabazaar']['avg_position'], 1.3)
        self.assertEqual(by['Paisabazaar']['stages']['bottom'], {'ranked': 2, 'of': 2, 'share': 100})
        self.assertEqual(by['ICICI Bank']['avg_position'], 2.0)
        self.assertTrue(by[BRAND]['is_you'])
        self.assertEqual(by[BRAND]['prompts_ranked'], 1)
        self.assertEqual(by[BRAND]['avg_position'], 2.0)
        titles = [c['title'] for c in m['callouts']]
        self.assertIn('Paisabazaar — the BOFU default', titles)
        self.assertIn('Paisabazaar — best citation order', titles)

    def test_absent_brand_still_listed(self):
        m = s.competitor_matrix([row(competitors_mentioned=['X'])], BRAND)
        you = [r for r in m['rows'] if r['is_you']][0]
        self.assertEqual(you['prompts_ranked'], 0)
        self.assertEqual(you['share'], 0)

    def test_empty(self):
        m = s.competitor_matrix([], BRAND)
        self.assertEqual(len(m['rows']), 1)
        self.assertEqual(m['callouts'], [])


class VisibilityPlanTests(SimpleTestCase):
    databases = []

    def rows(self):
        return [
            row(prompt_index=1, funnel_stage='top', is_mention=True, position=5, competitors_mentioned=['Paisabazaar']),
            row(prompt_index=2, funnel_stage='bottom', competitors_mentioned=['Paisabazaar'], cited_domains=['paisabazaar.com']),
            row(prompt_index=3, funnel_stage='middle'),
        ]

    def test_plan_shape_and_projection(self):
        crawl = {'bot_access': {'value': '3 of 5', 'score': 60, 'evidence': 'blocked: GPTBot, ClaudeBot'}}
        out = s.score_audit(self.rows(), BRAND, HOST, RIVALS, crawl=crawl,
                            crawl_summary={'pages_sampled': 5, 'sitemap_present': False, 'stale_pages': 2})
        plan = out['report']['plan']
        self.assertEqual(plan['today'], out['headline']['geo_score'])
        self.assertEqual([b['key'] for b in plan['buckets']], ['now', 'next', 'later'])
        now, nxt, later = plan['buckets']
        # chain: each bucket starts where the previous ended
        self.assertEqual(now['from'], plan['today'])
        self.assertEqual(nxt['from'], now['to'])
        self.assertEqual(later['from'], nxt['to'])
        self.assertEqual(plan['projected'], later['to'])
        self.assertGreater(plan['projected'], plan['today'])
        self.assertLessEqual(plan['projected'], 100)
        self.assertLess(plan['status_quo'], plan['today'])
        # Now holds at most 3 short items, ranked by lift per hour
        self.assertLessEqual(len(now['items']), 3)
        self.assertTrue(all(i['effort_hours'] <= 8 for i in now['items']))
        keys = [i['key'] for b in plan['buckets'] for i in b['items']]
        self.assertEqual(len(keys), len(set(keys)), 'no duplicate actions across buckets')
        self.assertIn('measure:bot_access', keys, 'a failing crawl measure becomes an action')
        self.assertIn('crawl:sitemap', keys)
        self.assertIn('prompt:2', keys, 'a visibility-gap prompt becomes an answer-page action')
        self.assertIn('prompt:1', keys, 'a position-gap prompt becomes a move-up action')
        by = {i['key']: i for b in plan['buckets'] for i in b['items']}
        self.assertEqual(by['measure:bot_access']['owner'], 'dev')
        self.assertIn('GPTBot', by['measure:bot_access']['why'])
        self.assertTrue(by['prompt:1']['title'].startswith('Move up the order'))
        for it in by.values():
            self.assertTrue(it['title'] and it['why'] and it['projected_geo_lift'] > 0 and it['effort_hours'] > 0)

    def test_quick_wins_lead_the_plan(self):
        out = s.score_audit(self.rows(), BRAND, HOST, RIVALS)
        # every quick win is in the plan, except the aggregate answer-pages win,
        # which the plan replaces with one action per prompt
        wins = [w['title'] for w in out['report']['quick_wins'] if not w['title'].startswith('Publish answer pages for')]
        self.assertTrue(wins)
        plan_titles = [i['title'] for b in out['report']['plan']['buckets'] for i in b['items']]
        for w in wins:
            self.assertIn(w, plan_titles)

    def test_perfect_audit_has_an_empty_plan(self):
        rows = [row(prompt_index=i, is_mention=True, is_cited=True, position=1, sentiment='positive', cited_domains=['hdfcbank.com'])
                for i in range(1, 4)]
        plan = s.score_audit(rows, BRAND, HOST, RIVALS)['report']['plan']
        self.assertEqual(sum(len(b['items']) for b in plan['buckets']), 0)
        self.assertEqual(plan['projected'], plan['today'])

    def test_projection_is_capped(self):
        rows = [row(prompt_index=i, competitors_mentioned=['X'], cited_domains=['x.com']) for i in range(1, 13)]
        plan = s.score_audit(rows, BRAND, HOST, RIVALS)['report']['plan']
        self.assertLessEqual(plan['projected'] - plan['today'], s.MAX_PROJECTED_LIFT)
        self.assertLessEqual(plan['projected'], 100)

    def test_projection_respects_headroom_near_100(self):
        # Mentioned and first everywhere but never cited: real actions exist, little room to grow.
        rows = [row(prompt_index=i, is_mention=True, position=1, sentiment='positive', cited_domains=['news.example.com'])
                for i in range(1, 7)]
        plan = s.score_audit(rows, BRAND, HOST, RIVALS)['report']['plan']
        self.assertGreater(sum(len(b['items']) for b in plan['buckets']), 0)
        self.assertLessEqual(plan['projected'] - plan['today'], 12)

    def test_aggregate_answer_pages_win_is_not_double_counted(self):
        rows = [row(prompt_index=i, competitors_mentioned=['X'], cited_domains=['x.com']) for i in range(1, 4)]
        out = s.score_audit(rows, BRAND, HOST, RIVALS)
        self.assertTrue(any(w['title'].startswith('Publish answer pages for') for w in out['report']['quick_wins']))
        titles = [i['title'] for b in out['report']['plan']['buckets'] for i in b['items']]
        self.assertFalse(any(t.startswith('Publish answer pages for') for t in titles))
        self.assertEqual(sum(1 for t in titles if t.startswith('Publish an answer page for')), 3)
