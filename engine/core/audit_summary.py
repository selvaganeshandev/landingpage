"""Audit Engine executive summary — the words on top of the numbers.

Two producers of the same shape so the section always exists:

  rules_summary(digest)   deterministic findings built from the numbers alone
  build_summary(...)      one internal LLM call over a compact digest of the
                          report; falls back to the rules when the model
                          returns nothing usable

Shape:
    {
      'headline': str,                      # one sentence
      'key_findings': [str, ...],           # up to 5, most important first
      'sections': {geo, competitors, narrative, website, plan: str},   # one-paragraph intros
      'source': 'llm' | 'rules',
      'fingerprint': str,                   # what the summary was built from
    }

The digest is the only thing the model sees — never the raw answers — so the
call is small and the summary cannot cite anything the report does not show.
"""
import hashlib
import json
import re
from typing import Any, Dict, List

_SYSTEM = (
    "You write the executive summary of an AI-visibility audit for a marketing lead. "
    "You get a digest of the audit's numbers. Return ONLY a JSON object with keys:\n"
    "  headline      one sentence, plain English, the single most important conclusion\n"
    "  key_findings  array of 5 strings, each one sentence with a number from the digest, most important first\n"
    "  sections      object with keys geo, competitors, narrative, website, plan — each a 1-2 sentence intro to that "
    "section of the report, written from the digest. The sections are: geo = how often the AI engines name and cite "
    "the brand (engines, mention rate, funnel stages, gap counts); competitors = the rivals the engines name instead "
    "(top_rivals, callouts, citations); narrative = how the engines describe the brand (narrative); website = the "
    "brand's own site (website: crawlers, schema, bylines, freshness); plan = the recommended actions and projected "
    "score (plan). Leave a key as an empty string only when its data is null in the digest.\n"
    "Rules: use only numbers present in the digest; no invented facts; no marketing fluff; name rivals and engines "
    "exactly as given; refer to the brand by name. No commentary outside the JSON."
)


def digest(audit, report: Dict[str, Any]) -> Dict[str, Any]:
    """The compact, numbers-only view of a report that both producers read."""
    geo = report.get('geo') or {}
    engines = geo.get('engines') or []
    ctrl = geo.get('citation_control') or {}
    comp = (geo.get('competitors') or {}).get('rows') or []
    rivals = [c for c in comp if not c.get('is_you')][:5]
    measures = report.get('measures') or []
    failing = [m for m in measures if m.get('status') == 'fail']
    nar = report.get('narrative') or {}
    plan = report.get('plan') or {}
    crawl = report.get('crawl') or {}
    seo = report.get('seo') or {}
    weakest = min((e for e in engines if e.get('answered')), key=lambda e: e.get('mention_rate', 0), default=None)
    strongest = max((e for e in engines if e.get('answered')), key=lambda e: e.get('mention_rate', 0), default=None)
    return {
        'brand': getattr(audit, 'brand_name', '') or getattr(audit, 'host', ''),
        'host': getattr(audit, 'host', ''),
        'industry': getattr(audit, 'industry', ''),
        'geo_score': getattr(audit, 'geo_score', None),
        'geo_stage': geo.get('stage_label') or getattr(audit, 'geo_stage', ''),
        'appearances': getattr(audit, 'appearances', 0),
        'cited_runs': getattr(audit, 'cited_runs', 0),
        'total_runs': getattr(audit, 'total_runs', 0),
        'mention_rate_pct': round(100 * getattr(audit, 'appearances', 0) / getattr(audit, 'total_runs', 1)) if getattr(audit, 'total_runs', 0) else 0,
        'engines_preferred': getattr(audit, 'engines_preferred', 0),
        'engines_total': getattr(audit, 'engines_total', 0),
        'share_of_voice_pct': float(getattr(audit, 'share_of_voice', 0) or 0),
        'engines': [{'platform': e.get('platform'), 'mention_rate_pct': round(100 * e.get('mention_rate', 0)), 'cited': e.get('cited'),
                     'answered': e.get('answered'), 'top_rival': e.get('top_rival'), 'top_rival_mentions': e.get('top_rival_mentions')} for e in engines],
        'weakest_engine': weakest.get('platform') if weakest else None,
        'strongest_engine': strongest.get('platform') if strongest else None,
        'gap_counts': geo.get('gap_counts') or {},
        'prompts_total': len(geo.get('evidence') or []),
        'funnel_rates_pct': {k: v.get('rate') for k, v in ((geo.get('funnel') or {}).get('by_stage') or {}).items()},
        'top_rivals': [{'name': c.get('name'), 'prompts_ranked': c.get('prompts_ranked'), 'prompts_total': c.get('prompts_total'),
                        'avg_position': c.get('avg_position')} for c in rivals],
        'callouts': [c.get('title') for c in (geo.get('competitors') or {}).get('callouts') or []],
        'citations': {'owned_pct': ctrl.get('owned'), 'competitor_pct': ctrl.get('competitor'), 'third_party_pct': ctrl.get('third_party'),
                      'total': ctrl.get('total_citations'), 'top_sources': [s.get('host') for s in (ctrl.get('top_sources') or [])[:3]]},
        'pillars': report.get('pillars') or {},
        'failing_measures': [{'label': m.get('label'), 'value': m.get('value'), 'score': m.get('score'), 'target': m.get('target')} for m in failing][:8],
        'narrative': {
            'available': bool(nar.get('available')),
            'dominant_framing': nar.get('dominant_framing'), 'framing_share_pct': nar.get('framing_share'),
            'consistency_pct': nar.get('consistency'), 'descriptors_missing': nar.get('descriptors_missing') or [],
            'off_brand': [o.get('claim') for o in (nar.get('off_brand') or [])][:2],
        } if nar else {'available': False},
        'website': {
            'pages_sampled': crawl.get('pages_sampled'), 'bots_allowed': crawl.get('bots_allowed'), 'bots_total': crawl.get('bots_total'),
            'schema_coverage_pct': crawl.get('schema_coverage'), 'author_share_pct': crawl.get('author_share'),
            'avg_word_count': crawl.get('avg_word_count'), 'dated_pages': crawl.get('dated_pages'), 'stale_pages': crawl.get('stale_pages'),
            'sitemap': crawl.get('sitemap_present'), 'llms_txt': crawl.get('llms_txt'),
            # technical layer (absent on reports crawled before it existed)
            'health_score': (crawl.get('health') or {}).get('score'),
            'weakest_health_categories': [c['label'] for c in sorted(
                [c for c in (crawl.get('health') or {}).get('categories', []) if c.get('score') is not None],
                key=lambda c: c['score'])[:2]],
            'top_technical_issues': [f"{i['label']} ({i['count']} of {i['of']})" for i in (crawl.get('technical_issues') or [])[:3]],
            'core_web_vitals_score': (crawl.get('cwv') or {}).get('score'),
            'indexability': crawl.get('indexability'),
            'broken_internal_links': (crawl.get('link_check') or {}).get('broken'),
            'issues_fixed_since_last_audit': len((crawl.get('issue_delta') or {}).get('fixed') or []) if crawl.get('issue_delta') else None,
            'issues_new_since_last_audit': len((crawl.get('issue_delta') or {}).get('new') or []) if crawl.get('issue_delta') else None,
            'backlinks': ({'authority_score': crawl['backlinks'].get('authority_score'), 'referring_domains': crawl['backlinks'].get('referring_domains'),
                           'backlinks': crawl['backlinks'].get('backlinks')} if crawl.get('backlinks') else None),
        } if crawl else None,
        'seo': {'keywords_total': seo.get('keywords_total'), 'top10': seo.get('top10'), 'striking_distance': seo.get('striking_distance'),
                'visibility': seo.get('visibility')} if seo else None,
        'plan': {
            'today': plan.get('today'), 'projected': plan.get('projected'), 'status_quo': plan.get('status_quo'),
            'buckets': [{'label': b.get('label'), 'from': b.get('from'), 'to': b.get('to'),
                         'actions': [i.get('title') for i in (b.get('items') or [])][:4]} for b in (plan.get('buckets') or [])],
        } if plan else None,
    }


def fingerprint(d: Dict[str, Any]) -> str:
    key = json.dumps({k: d.get(k) for k in ('geo_score', 'total_runs', 'prompts_total', 'engines_total', 'pillars')}, sort_keys=True, default=str)
    key += json.dumps({'nar': (d.get('narrative') or {}).get('available'), 'plan': (d.get('plan') or {}).get('projected')}, sort_keys=True)
    return hashlib.sha1(key.encode('utf-8')).hexdigest()[:12]


def _pct(v) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return '—'
    return f"{int(f)}%" if f == int(f) else f"{f:.1f}%"


def rules_summary(d: Dict[str, Any]) -> Dict[str, Any]:
    """Findings from the numbers alone. Always available."""
    brand = d.get('brand') or 'The brand'
    findings: List[str] = []
    stage = d.get('geo_stage') or 'unscored'
    findings.append(f"{brand} is {stage} with a GEO score of {d.get('geo_score', '—')}: named in {d.get('appearances', 0)} of "
                    f"{d.get('total_runs', 0)} answers ({d.get('mention_rate_pct', 0)}%) and cited in {d.get('cited_runs', 0)}.")
    if d.get('engines_total'):
        findings.append(f"{d.get('engines_preferred', 0)} of {d['engines_total']} engines prefer {brand} (name it on more than half of prompts)"
                        + (f"; weakest is {d['weakest_engine']}" if d.get('weakest_engine') and d.get('engines_total', 0) > 1 else '') + '.')
    cit = d.get('citations') or {}
    if cit.get('total'):
        findings.append(f"Only {_pct(cit.get('owned_pct', 0))} of {cit['total']} citations point at {d.get('host')}; "
                        f"{_pct(cit.get('competitor_pct', 0))} go to rivals and {_pct(cit.get('third_party_pct', 0))} to third parties"
                        + (f" (top: {', '.join(cit.get('top_sources') or [])})" if cit.get('top_sources') else '') + '.')
    rivals = d.get('top_rivals') or []
    if rivals:
        r = rivals[0]
        findings.append(f"{r['name']} is the most-named rival, on {r.get('prompts_ranked', 0)} of {r.get('prompts_total', 0)} prompts"
                        + (f" at an average position of {r['avg_position']}" if r.get('avg_position') is not None else '') + '.')
    gaps = d.get('gap_counts') or {}
    if gaps:
        parts = [f"{n} {k.replace('_', ' ')}" for k, n in gaps.items()]
        findings.append(f"Across {d.get('prompts_total', 0)} prompts: {', '.join(parts)}.")
    web = d.get('website') or {}
    if web and web.get('pages_sampled'):
        findings.append(f"On-site: {web.get('bots_allowed')} of {web.get('bots_total')} AI crawlers allowed, schema on {web.get('schema_coverage_pct')}% of "
                        f"{web['pages_sampled']} sampled pages, author bios on {web.get('author_share_pct')}%.")
    plan = d.get('plan') or {}
    headline = f"{brand} is {stage} ({d.get('geo_score', '—')}/100)"
    if plan.get('projected') is not None and plan.get('today') is not None and plan['projected'] > plan['today']:
        headline += f" — the plan projects {plan['projected']} within 90 days."
    else:
        headline += '.'
    nar = d.get('narrative') or {}
    sections = {
        'geo': f"{d.get('mention_rate_pct', 0)}% mention rate across {d.get('total_runs', 0)} answers on {d.get('engines_total', 0)} engine(s).",
        'competitors': (f"{rivals[0]['name']} leads the rivals on prompts ranked." if rivals else ''),
        'narrative': (f"Engines mostly frame {brand} as \"{nar.get('dominant_framing')}\"." if nar.get('available') and nar.get('dominant_framing') else ''),
        'website': ((f"{web.get('pages_sampled')} pages sampled; {web.get('bots_allowed')} of {web.get('bots_total')} AI crawlers allowed."
                     + (f" Website health {web['health_score']}/100." if web.get('health_score') is not None else '')
                     + (f" Top issue: {web['top_technical_issues'][0]}." if web.get('top_technical_issues') else ''))
                    if web and web.get('pages_sampled') else ''),
        'plan': (f"{plan.get('today')} today → {plan.get('projected')} projected; status quo {plan.get('status_quo')}." if plan.get('projected') is not None else ''),
    }
    return {'headline': headline, 'key_findings': findings[:5], 'sections': sections, 'source': 'rules', 'fingerprint': fingerprint(d)}


def _clean(data: Dict[str, Any], d: Dict[str, Any]) -> Dict[str, Any]:
    def s(v, limit):
        text = re.sub(r'\s+', ' ', str(v or '')).strip()
        # a model sometimes quotes the digest's field names back ("(engines_preferred: 0, engines_total: 1)"); drop such asides
        text = re.sub(r'\s*\(([^()]*\b[a-z]+_[a-z_]+\b[^()]*)\)', '', text)
        text = re.sub(r'\b[a-z]+_[a-z_]+\b', lambda m: m.group(0).replace('_', ' '), text)
        if len(text) > limit:
            # cut at the last full sentence inside the limit, never mid-word
            cut = text[:limit]
            end = max(cut.rfind('. '), cut.rfind('! '), cut.rfind('? '))
            text = cut[:end + 1] if end > limit // 2 else cut.rsplit(' ', 1)[0]
        return text
    findings = [s(f, 300) for f in (data.get('key_findings') or []) if s(f, 300)][:5]
    sections_in = data.get('sections') if isinstance(data.get('sections'), dict) else {}
    sections = {k: s(sections_in.get(k), 400) for k in ('geo', 'competitors', 'narrative', 'website', 'plan')}
    # A model that did not understand a section says so instead of writing
    # the intro; that sentence must never reach the report.
    meta = re.compile(r'\b(digest|not (included|available|provided)|no data|n/a)\b', re.I)
    sections = {k: ('' if meta.search(v) else v) for k, v in sections.items()}
    headline = s(data.get('headline'), 240)
    if not headline or len(findings) < 3:
        raise ValueError('summary too thin')
    return {'headline': headline, 'key_findings': findings, 'sections': sections, 'source': 'llm', 'fingerprint': fingerprint(d)}


def build_summary(chat_json, client, model, d: Dict[str, Any]) -> Dict[str, Any]:
    """LLM summary of the digest; rules summary when the model gives nothing usable."""
    try:
        data = chat_json(client, model, _SYSTEM, json.dumps(d), max_tokens=8000, expect_list=False)
        return _clean(data if isinstance(data, dict) else {}, d)
    except Exception:  # noqa: BLE001 - the rules summary is the guaranteed floor
        return rules_summary(d)
