"""Audit Engine pipeline — runs one Audit row through its six stages.

    profile   read the site, work out brand / industry / competitors
    crawl     sample the site's pages for schema, bylines, citations, dates (Findable)
    prompts   write N buyer questions in a funnel mix (no Domain, no groups)
    engines   ask every prompt once on every configured engine, keep the evidence
    serp      discover keywords and rank them on Google (behind AUDIT_SEO_ENABLED)
    score     turn the evidence into the report (core.audit_scoring)
    publish   mark DONE, set the public expiry

Every stage is written to the Audit row before the next starts and every stage
is resumable: a worker restart re-enters run_audit() and each stage skips the
work whose output is already stored (profile in `grounding`, prompts in
`grounding['prompts']`, engine answers as AuditPromptResult rows, keywords as
AuditKeywordResult rows). Scoring is recomputed every time — it is cheap and
pure.

Reuse, not reinvention: the crawl is the misinformation crawler, prompt
writing is prompt_generation's entity → plan → expand → dedup stages with an
audit-shaped ground dict, the measured LLM calls are the exact
process_prompt_with_* handlers the tracked pipeline uses (so an audit's
"mentioned / cited" means the same as a tracked domain's), and the SERP lookup
is seo_ranking_processor's fetch + parse. What is new is only the glue and the
fact that none of it needs an Organisation.

Nothing here runs unless AUDIT_ENGINE_ENABLED is True.
"""
import json
import logging
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.utils import timezone

from shared_models.audit_models import Audit, AuditKeywordResult, AuditPageResult, AuditPromptResult

logger = logging.getLogger(__name__)


class AuditError(RuntimeError):
    """The audit cannot continue; the message is stored on the row for the UI."""


# ---- vocab ------------------------------------------------------------------

# client_factory provider -> (platform key used by analytics_helpers, canonical label)
PROVIDER_PLATFORMS = {
    'openai': ('chatgpt', 'ChatGPT'),
    'gemini': ('gemini', 'Google Gemini'),
    'anthropic': ('claude', 'Claude'),
    'perplexity': ('perplexity', 'Perplexity'),
    'xai': ('grok', 'Grok'),
    'deepseek': ('deepseek', 'DeepSeek'),
}

# ISO-3166 alpha-2 -> (country name the handlers put in the prompt, Google
# domain for SERP, language). Same 24 countries the onboarding map covers.
COUNTRIES = {
    'us': ('United States', 'google.com', 'en'),
    'gb': ('United Kingdom', 'google.co.uk', 'en'),
    'ca': ('Canada', 'google.ca', 'en'),
    'au': ('Australia', 'google.com.au', 'en'),
    'de': ('Germany', 'google.de', 'de'),
    'fr': ('France', 'google.fr', 'fr'),
    'es': ('Spain', 'google.es', 'es'),
    'it': ('Italy', 'google.it', 'it'),
    'jp': ('Japan', 'google.co.jp', 'ja'),
    'in': ('India', 'google.co.in', 'en'),
    'br': ('Brazil', 'google.com.br', 'pt'),
    'mx': ('Mexico', 'google.com.mx', 'es'),
    'nl': ('Netherlands', 'google.nl', 'nl'),
    'se': ('Sweden', 'google.se', 'sv'),
    'no': ('Norway', 'google.no', 'no'),
    'dk': ('Denmark', 'google.dk', 'da'),
    'fi': ('Finland', 'google.fi', 'fi'),
    'pl': ('Poland', 'google.pl', 'pl'),
    'be': ('Belgium', 'google.be', 'nl'),
    'at': ('Austria', 'google.at', 'de'),
    'ch': ('Switzerland', 'google.ch', 'de'),
    'ie': ('Ireland', 'google.ie', 'en'),
    'nz': ('New Zealand', 'google.co.nz', 'en'),
    'sg': ('Singapore', 'google.com.sg', 'en'),
    'ae': ('United Arab Emirates', 'google.ae', 'en'),
}

# prompt_generation intent -> funnel stage the report groups by
INTENT_FUNNEL = {
    'discovery': 'top', 'problem': 'top',
    'evaluation': 'middle', 'use_case': 'middle',
    'comparison': 'bottom', 'brand': 'bottom', 'trust': 'bottom',
}

# Names the shared competitor extractor derives from cited URLs that are not
# anybody's rival: regulators, registries, exchanges, reference and review
# sites. Audits show a competitor matrix, so these would otherwise headline it
# ("Sebi — the BOFU default"). Matched on the squashed (lowercase, alnum) name.
NON_VENDOR_NAMES = {
    # regulators, registries, exchanges, government (India + global)
    'sebi', 'rbi', 'nsdl', 'cdsl', 'cdslindia', 'bse', 'bseindia', 'nse', 'nseindia', 'amfi', 'amfiindia',
    'irdai', 'irda', 'pfrda', 'npci', 'uidai', 'trai', 'fssai', 'cgtmse', 'sidbi', 'nabard', 'mca', 'incometax',
    'incometaxindia', 'gst', 'gstcouncil', 'niti', 'nitiaayog', 'india', 'digitalindia', 'mygov', 'pib',
    'fda', 'sec', 'finra', 'fca', 'ftc', 'fdic', 'occ', 'cfpb', 'who', 'un', 'nih', 'cdc', 'ecb', 'federalreserve',
    'imf', 'worldbank', 'oecd', 'europa', 'gov', 'nic',
    # reference, news, review and community sites
    'investopedia', 'wikipedia', 'britannica', 'moneycontrol', 'economictimes', 'livemint', 'businessstandard',
    'ndtv', 'cnbc', 'cnbctv18', 'forbes', 'bloomberg', 'reuters', 'statista', 'g2', 'capterra', 'trustpilot',
    'gartner', 'techcrunch', 'medium', 'reddit', 'quora', 'youtube', 'google', 'linkedin', 'facebook', 'twitter',
    'x', 'instagram', 'github', 'stackoverflow', 'apple', 'microsoft', 'amazon', 'financialexpress',
    'thehindu', 'indiatoday', 'zeebiz', 'goodreturns', 'bankbazaar', 'paisabazaar', 'policybazaar',
}
# Hosts under these suffixes are institutions, not vendors.
NON_VENDOR_TLD_RE = re.compile(r'\.(gov|gov\.[a-z]{2}|nic\.in|edu|ac\.[a-z]{2}|edu\.[a-z]{2}|int|mil|org|org\.[a-z]{2})$')

MAX_SITE_CHARS = 6000
MAX_RESPONSE_CHARS = 20000
AUDIT_BRANDED_RATIO = 25  # percent of prompts that name the brand
KEYWORD_PROMPT_MATCH = 0.3  # token-overlap needed to pair a keyword with a prompt


def country_info(code: str):
    return COUNTRIES.get((code or '').strip().lower(), COUNTRIES['us'])


def _call_with_rate_limit_retry(fn, label: str):
    """Run one provider call, retrying only on 429. Exponential, full jitter.

    The engine stage asks every (prompt, engine) pair in one pool, so a provider
    now sees a burst where it used to see a trickle and a 429 is an ordinary
    event rather than an exception. That matters for the *result*, not just for
    tidiness: without a retry a rate-limited call is stored as a failed answer,
    and a missing answer reads as "the brand was not mentioned" — silently
    deflating the GEO score instead of surfacing the problem. This is what keeps
    the faster schedule from changing what the audit reports.

    The jitter is the point, not a detail: a dozen threads hit the limit inside
    the same second, and a fixed backoff would march them into the next window
    together and collide again. Mirrors analytics_helpers._call_with_backoff.

    Anything that is not a 429 is re-raised at once — retrying a bad request or
    an auth failure only spends the wait budget before failing anyway.
    """
    from core.analytics_helpers import _is_rate_limited

    attempts = max(0, int(getattr(settings, 'AUDIT_RATE_LIMIT_RETRIES', 4)))
    base = float(getattr(settings, 'AUDIT_RATE_LIMIT_BASE_DELAY', 2.0))
    max_wait = float(getattr(settings, 'AUDIT_RATE_LIMIT_MAX_WAIT', 120.0))

    waited = 0.0
    for attempt in range(attempts + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - re-raised below unless it is a 429
            if not _is_rate_limited(exc) or attempt == attempts:
                raise
            delay = random.uniform(0, base * (2 ** attempt))
            if waited + delay > max_wait:
                logger.warning(
                    '[Audit] %s rate limited; %.0fs wait budget exhausted after %d attempts.',
                    label, max_wait, attempt + 1,
                )
                raise
            waited += delay
            logger.info(
                '[Audit] %s rate limited (attempt %d/%d); retrying in %.1fs.',
                label, attempt + 1, attempts + 1, delay,
            )
            time.sleep(delay)


def _hosts_of(urls: List[str]) -> List[str]:
    from core.audit_scoring import normalize_host
    out, seen = [], set()
    for u in urls or []:
        h = normalize_host(u)
        if h and h not in seen:
            seen.add(h)
            out.append(h)
    return out


# ---- site reading -------------------------------------------------------------

def _strip_html(html: str) -> str:
    try:
        import trafilatura
        text = trafilatura.extract(html, include_comments=False, include_tables=True) or ''
        if len(text) >= 200:
            return text
    except Exception:  # noqa: BLE001 - trafilatura is optional here
        pass
    html = re.sub(r'(?is)<(script|style|noscript|svg).*?</\1>', ' ', html or '')
    text = re.sub(r'(?s)<[^>]+>', ' ', html)
    return re.sub(r'\s+', ' ', text).strip()


def _detect_stack(html: str) -> List[str]:
    """Cheap fingerprints from the raw HTML — cosmetic, best-effort."""
    if not html:
        return []
    probes = [
        ('WordPress', r'wp-content|wp-includes'),
        ('Shopify', r'cdn\.shopify\.com'),
        ('Webflow', r'webflow'),
        ('Wix', r'wixstatic\.com|wix\.com'),
        ('Squarespace', r'squarespace'),
        ('Drupal', r'/sites/default/files|drupal'),
        ('Next.js', r'/_next/'),
        ('React', r'react-dom|__NEXT_DATA__|data-reactroot'),
        ('Cloudflare', r'cloudflare|__cf_bm|cf-ray'),
        ('Akamai', r'akamai'),
        ('Google Tag Manager', r'googletagmanager\.com'),
        ('HubSpot', r'hs-scripts\.com|hubspot'),
    ]
    return [name for name, pat in probes if re.search(pat, html, flags=re.IGNORECASE)][:6]


def fetch_site(website: str):
    """(html, text, error). DataBlue when configured, plain HTTP otherwise."""
    html, err = None, None
    if getattr(settings, 'DATABLUE_API_KEY', ''):
        try:
            from core.misinformation_services.crawler import WebCrawler
            html, status, err = WebCrawler().crawl(website)
            if not html:
                err = err or f'HTTP {status}'
        except Exception as exc:  # noqa: BLE001
            err = str(exc)
    if not html:
        try:
            import requests
            resp = requests.get(
                website, timeout=20, allow_redirects=True,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; PromptMaxxAudit/1.0)'},
            )
            if resp.ok and resp.text:
                html, err = resp.text, None
            else:
                err = err or f'HTTP {resp.status_code}'
        except Exception as exc:  # noqa: BLE001
            err = err or str(exc)
    text = _strip_html(html)[:MAX_SITE_CHARS] if html else ''
    return html or '', text, err


def mention_order(text: str, names: List[str], brand_name: str = '') -> Dict[str, int]:
    """1-based order in which each name first appears in the answer.

    Rivals only get a position when the answer actually contains their name;
    the brand is included so its place among rivals is comparable. Matching is
    case-insensitive on the whole name and, as a fallback, on the name with
    spaces removed ('Angel One' vs 'AngelOne').
    """
    if not text:
        return {}
    low = text.lower()
    firsts = []
    for name in list(names) + ([brand_name] if brand_name else []):
        key = (name or '').strip()
        if not key:
            continue
        idx = low.find(key.lower())
        if idx < 0 and ' ' in key:
            idx = low.find(key.lower().replace(' ', ''))
        if idx >= 0:
            firsts.append((idx, key))
    firsts.sort()
    return {name: rank for rank, (_, name) in enumerate(firsts, 1)}


# ---- LLM plumbing -----------------------------------------------------------------

def _internal_llm():
    """(client, model) for the audit's own non-measured calls."""
    from core.services.client_factory import get_internal_client
    client = get_internal_client()
    if client is None:
        raise AuditError('No OpenRouter API key is configured.')
    model = getattr(settings, 'OPENROUTER_INTERNAL_MODEL', 'openai/gpt-5-mini')
    return client, model


def _chat_json(client, model, system, user, *, max_tokens=3000, expect_list=False):
    from core.prompt_generation import GenerationError, _chat, _json_from
    try:
        text, _tokens = _chat(client, model, system, user, max_tokens=max_tokens, temperature=0.3)
        return _json_from(text, expect_list=expect_list)
    except GenerationError as exc:
        raise AuditError(str(exc)) from exc


_PROFILE_SYSTEM = (
    "You profile a company from its website so buyer questions can be written "
    "about it. Return ONLY a JSON object with keys: brand_name (string), "
    "industry (short string, e.g. 'Retail banking'), description (1-2 sentences), "
    "categories (array of up to 8 product/service categories, lowercase), "
    "audience (string), regions (array of countries/regions served), "
    "use_cases (array, up to 8), buying_criteria (array, up to 6), "
    "competitors (array of up to 5 objects {name, website} — the direct rivals a "
    "buyer would compare this company against in its main market; website is the "
    "bare domain like 'icicibank.com' or null if unsure). No commentary."
)


# ---- the pipeline -------------------------------------------------------------------

# Per-page technical signals worth keeping (the link list itself is not).
_PAGE_DETAIL_KEYS = (
    'title_length', 'description_length', 'h1_count', 'noindex', 'canonical_status', 'viewport', 'images',
    'images_missing_alt', 'mixed_content', 'hreflang', 'og', 'https', 'internal_links', 'generic_anchors',
    'internal_anchors', 'schema_gaps', 'has_person_schema', 'credential_mentions',
    # Phase Q
    'title_issue', 'description_issue', 'title_equals_h1', 'heading_issues', 'images_missing_dimensions', 'og_missing',
    'twitter_card', 'json_ld_invalid', 'rich_result_blockers', 'thin', 'has_params', 'param_links', 'hreflang_invalid',
    'scripts', 'stylesheets', 'images_legacy', 'images_srcset', 'soft_404', 'lang', 'favicon', 'meta_refresh',
)


def _page_details(page: Dict[str, Any]) -> Dict[str, Any]:
    tech = page.get('tech') or {}
    out = {k: tech[k] for k in _PAGE_DETAIL_KEYS if k in tech and tech[k] not in (None, '', [], False, 0)}
    for k in ('status_code', 'redirects', 'final_url', 'depth', 'x_robots', 'fetch_error', 'html_bytes'):
        if page.get(k) not in (None, '', 0) or k == 'depth' and page.get(k) == 0:
            out[k] = page[k]
    if page.get('index'):
        out['index'] = page['index']
    if page.get('redirect_chain'):
        out['redirect_chain'] = page['redirect_chain'][:5]
    return out


def _issue_delta(current: List[Dict[str, Any]], previous: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """What changed since the last audit of this site: issues gone, issues new, counts up or down."""
    if previous is None:
        return None
    cur = {i['key']: i for i in current or [] if i.get('key')}
    prev = {i['key']: i for i in previous or [] if i.get('key')}
    fixed = [{'key': k, 'label': v.get('label', k), 'was': v.get('count', 0)} for k, v in prev.items() if k not in cur]
    new = [{'key': k, 'label': v.get('label', k), 'count': v.get('count', 0)} for k, v in cur.items() if k not in prev]
    changed = [{'key': k, 'label': cur[k].get('label', k), 'from': prev[k].get('count', 0), 'to': cur[k].get('count', 0)}
               for k in cur if k in prev and cur[k].get('count', 0) != prev[k].get('count', 0)]
    return {'fixed': fixed[:20], 'new': new[:20], 'changed': changed[:20], 'previous_total': len(prev), 'current_total': len(cur)}


class AuditProcessor:
    def __init__(self, audit_id: int):
        self.audit_id = audit_id
        self.audit: Optional[Audit] = None

    # -- entry --

    def run(self) -> Dict[str, Any]:
        if not getattr(settings, 'AUDIT_ENGINE_ENABLED', False):
            logger.warning('[Audit] AUDIT_ENGINE_ENABLED is off; audit %s not run', self.audit_id)
            return {'status': 'disabled'}
        try:
            self.audit = Audit.objects.get(pk=self.audit_id)
        except Audit.DoesNotExist:
            logger.error('[Audit] audit %s does not exist', self.audit_id)
            return {'status': 'missing'}
        if self.audit.status == 'DONE':
            return {'status': 'already_done'}
        if self.audit.status == 'FAIL':
            # An explicit re-run clears the error first; a stray task must not
            # silently spend money on an audit someone already gave up on.
            logger.info('[Audit] audit %s is FAIL; not re-running', self.audit_id)
            return {'status': 'failed_previously'}

        started = time.monotonic()
        try:
            self._snapshot_config()
            self.stage_profile()
            self.stage_crawl()
            self.stage_prompts()
            self.stage_engines()
            self.stage_serp()
            self.stage_score()
            self.stage_publish()
        except Exception as exc:  # noqa: BLE001 - everything ends on the row
            logger.exception('[Audit] audit %s failed at stage %s', self.audit_id, self.audit.stage)
            self.audit.mark_failed(f"{self.audit.stage or 'start'}: {exc}")
            return {'status': 'failed', 'error': str(exc)}
        logger.info('[Audit] audit %s done in %.0fs', self.audit_id, time.monotonic() - started)
        return {'status': 'done', 'geo_score': self.audit.geo_score}

    # -- config --

    def _snapshot_config(self):
        cfg = dict(self.audit.config or {})
        providers = [p for p in (cfg.get('engines') or getattr(settings, 'AUDIT_ENGINES', [])) if p in PROVIDER_PLATFORMS]
        if not providers:
            raise AuditError('No AI engines are configured for audits (AUDIT_ENGINES).')
        cfg.setdefault('prompt_count', int(getattr(settings, 'AUDIT_PROMPT_COUNT', 12)))
        cfg['engines'] = providers
        cfg.setdefault('runs_per_prompt', max(1, min(10, int(getattr(settings, 'AUDIT_RUNS_PER_PROMPT', 1)))))
        cfg.setdefault('seo_enabled', bool(getattr(settings, 'AUDIT_SEO_ENABLED', False)))
        cfg.setdefault('keyword_count', int(getattr(settings, 'AUDIT_KEYWORD_COUNT', 50)))
        cfg.setdefault('crawl_enabled', bool(getattr(settings, 'AUDIT_CRAWL_ENABLED', True)))
        cfg.setdefault('narrative_enabled', bool(getattr(settings, 'AUDIT_NARRATIVE_ENABLED', True)))
        cfg.setdefault('summary_enabled', bool(getattr(settings, 'AUDIT_SUMMARY_ENABLED', True)))
        deep = (getattr(self.audit, 'source', '') or '') in ('manual', 'api')
        cfg.setdefault('crawl_depth', 'deep' if deep else 'standard')
        cfg.setdefault('crawl_pages', int(getattr(settings, 'AUDIT_CRAWL_PAGES_DEEP', 60) if deep else getattr(settings, 'AUDIT_CRAWL_PAGES', 20)))
        cfg.setdefault('internal_model', getattr(settings, 'OPENROUTER_INTERNAL_MODEL', ''))
        cfg.setdefault('started_at', timezone.now().isoformat())
        self.audit.config = cfg
        self.audit.save(update_fields=['config', 'modified_at'])

    @property
    def cfg(self) -> Dict[str, Any]:
        return self.audit.config or {}

    # -- stage 1: profile --

    def stage_profile(self):
        audit = self.audit
        if (audit.grounding or {}).get('profile'):
            audit.set_stage('profile', progress=12)
            return
        audit.set_stage('profile')

        html, text, err = fetch_site(audit.website)
        # Kept for the crawl stage's link discovery (not persisted).
        self._homepage_html = html
        client, model = _internal_llm()
        if text:
            user = f"URL: {audit.website}\n\nPage text:\n{text}"
            source = 'site'
        else:
            # Unreadable site: answer from what is publicly known, and say so.
            logger.info('[Audit] %s unreadable (%s); profiling from model knowledge', audit.website, err)
            user = (
                f"The website {audit.website} could not be read. Profile the company that owns "
                f"this domain from what you know about it. If you do not know it, infer the most "
                f"likely brand name from the domain and leave other fields minimal."
            )
            source = 'knowledge'
        data = _chat_json(client, model, _PROFILE_SYSTEM, user)

        def as_list(v):
            from core.prompt_generation import _as_list
            return _as_list(v)

        competitors = []
        for c in data.get('competitors') or []:
            if isinstance(c, dict):
                name, site = (c.get('name') or '').strip(), (c.get('website') or '')
            else:
                name, site = str(c).strip(), ''
            if name:
                from core.audit_scoring import normalize_host
                competitors.append({'name': name, 'host': normalize_host(site)})

        from core.audit_scoring import normalize_host
        audit.brand_name = (data.get('brand_name') or '').strip()[:255] or audit.host.split('.')[0].title()
        audit.industry = (data.get('industry') or '').strip()[:255]
        audit.competitors = competitors[:5]
        audit.tech_stack = _detect_stack(html)
        audit.grounding = {
            **(audit.grounding or {}),
            'profile': {
                'source': source,
                'crawl_error': err,
                'description': (data.get('description') or '').strip()[:1000],
                'categories': as_list(data.get('categories'))[:8],
                'audience': (data.get('audience') or '').strip()[:600],
                'regions': as_list(data.get('regions'))[:6],
                'use_cases': as_list(data.get('use_cases'))[:8],
                'buying_criteria': as_list(data.get('buying_criteria'))[:6],
                'site_excerpt': text[:4000],
            },
        }
        audit.save(update_fields=['brand_name', 'industry', 'competitors', 'tech_stack', 'grounding', 'modified_at'])
        audit.set_stage('profile', progress=12, source=source, competitors=len(competitors))

    # -- stage 1b: crawl --

    def stage_crawl(self):
        """Sample the site's own pages. Never fatal: a blocked or slow site just
        leaves the Findable measures "not measured"."""
        audit = self.audit
        if not self.cfg.get('crawl_enabled', True):
            audit.set_stage('crawl', progress=20, skipped=True)
            return
        existing = (audit.grounding or {}).get('crawl')
        if existing and existing.get('complete'):
            audit.set_stage('crawl', progress=20)
            return
        audit.set_stage('crawl', progress=13)
        try:
            from core.audit_crawl import crawl_site
            deep = self.cfg.get('crawl_depth') == 'deep'
            result = crawl_site(
                audit.website, audit.host,
                homepage_html=getattr(self, '_homepage_html', None),
                limit=max(3, int(self.cfg.get('crawl_pages') or 20)),
                budget_seconds=int(getattr(settings, 'AUDIT_CRAWL_BUDGET_SECONDS_DEEP', 150) if deep else getattr(settings, 'AUDIT_CRAWL_BUDGET_SECONDS', 60)),
                link_checks=bool(getattr(settings, 'AUDIT_CRAWL_LINK_CHECKS', True)),
                link_check_limit=int(getattr(settings, 'AUDIT_CRAWL_LINK_CHECK_LIMIT_DEEP', 100) if deep else getattr(settings, 'AUDIT_CRAWL_LINK_CHECK_LIMIT', 25)),
                cwv=bool(getattr(settings, 'AUDIT_CWV_ENABLED', False)),
                cwv_api_key=str(getattr(settings, 'AUDIT_PAGESPEED_API_KEY', '') or ''),
                cwv_pages=int(getattr(settings, 'AUDIT_CWV_PAGES_DEEP', 3)) if deep else 1,
                backlinks=bool(getattr(settings, 'AUDIT_BACKLINKS_ENABLED', False)),
                follow_links=bool(getattr(settings, 'AUDIT_CRAWL_FOLLOW_LINKS', True)),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning('[Audit] crawl failed for %s: %s', audit.host, exc)
            audit.grounding = {**(audit.grounding or {}), 'crawl': {'complete': True, 'error': str(exc)[:300], 'summary': {}, 'measures': {}}}
            audit.save(update_fields=['grounding', 'modified_at'])
            audit.set_stage('crawl', progress=20, error=str(exc)[:120])
            return

        AuditPageResult.objects.filter(audit=audit).delete()
        rows = []
        for p in result['pages']:
            if not p.get('url'):
                continue
            rows.append(AuditPageResult(
                audit=audit, url=p['url'][:1000], title=(p.get('title') or '')[:255],
                fetched=not p.get('parse_error'), error=(p.get('parse_error') or '')[:200],
                word_count=int(p.get('word_count') or 0), schema_types=list(p.get('schema_types') or []),
                author=(p.get('author') or '')[:120], external_links=min(32767, int(p.get('external_links') or 0)),
                last_modified=p.get('last_modified') or None,
                question_headings=min(32767, int(p.get('question_headings') or 0)),
                has_table=bool(p.get('has_table')), has_faq_schema=bool(p.get('has_faq_schema')),
                details=_page_details(p),
            ))
        AuditPageResult.objects.bulk_create(rows, ignore_conflicts=True)

        summary = result['summary']
        audit.grounding = {
            **(audit.grounding or {}),
            'crawl': {'complete': True, 'summary': summary, 'measures': result['measures'], 'robots': result['robots']},
        }
        audit.save(update_fields=['grounding', 'modified_at'])
        audit.set_stage('crawl', progress=20, pages=summary.get('pages_sampled', 0), seconds=summary.get('seconds'))

    # -- stage 2: prompts --

    def _ground(self) -> Dict[str, Any]:
        p = (self.audit.grounding or {}).get('profile', {})
        country_name = country_info(self.audit.country)[0]
        return {
            'brand_name': self.audit.brand_name,
            'url': self.audit.website,
            'country': country_name,
            'business_model': '',
            'price_positioning': '',
            'description': p.get('description', ''),
            'categories': list(p.get('categories') or []),
            'niches': [],
            'regions': list(p.get('regions') or []) or [country_name],
            'audience': p.get('audience', ''),
            'use_cases': list(p.get('use_cases') or []),
            'buying_criteria': list(p.get('buying_criteria') or []),
            'objections': [],
            'competitors': [c['name'] for c in (self.audit.competitors or []) if c.get('name')],
            'differentiators': [],
            'avoid': [],
            'seeds': [],
            'site_excerpt': p.get('site_excerpt', ''),
        }

    def stage_prompts(self):
        audit = self.audit
        if (audit.grounding or {}).get('prompts'):
            audit.set_stage('prompts', progress=30)
            return
        audit.set_stage('prompts')

        from core.prompt_generation import (
            GenerationError, build_plan, stage_dedup, stage_entities, stage_expand,
        )
        client, model = _internal_llm()
        ground = self._ground()
        target = max(4, int(self.cfg.get('prompt_count') or 12))
        try:
            entities, _t = stage_entities(client, model, ground)
            plan = build_plan(ground, entities, target, 'balanced', AUDIT_BRANDED_RATIO)
            rendered, _t = stage_expand(client, model, ground, plan)
        except GenerationError as exc:
            raise AuditError(str(exc)) from exc
        candidates = stage_dedup(rendered)

        # Round-robin across funnel stages so a 12-prompt audit is not twelve
        # discovery questions; unbranded before branded within each stage.
        buckets: Dict[str, List[Dict[str, Any]]] = {'top': [], 'middle': [], 'bottom': []}
        for c in candidates:
            buckets[INTENT_FUNNEL.get(c.get('intent'), 'middle')].append(c)
        for rows in buckets.values():
            rows.sort(key=lambda c: bool(c.get('is_branded')))
        chosen: List[Dict[str, Any]] = []
        while len(chosen) < target and any(buckets.values()):
            for stage in ('top', 'middle', 'bottom'):
                if len(chosen) >= target:
                    break
                if buckets[stage]:
                    chosen.append(buckets[stage].pop(0))
        if not chosen:
            raise AuditError('No usable prompts could be written for this site.')

        prompts = [
            {
                'index': i + 1,
                'text': c['text'],
                'topic': c.get('entity', ''),
                'funnel_stage': INTENT_FUNNEL.get(c.get('intent'), 'middle'),
                'intent': c.get('intent', ''),
                'is_branded': bool(c.get('is_branded')),
            }
            for i, c in enumerate(chosen)
        ]
        audit.grounding = {**(audit.grounding or {}), 'prompts': prompts}
        audit.save(update_fields=['grounding', 'modified_at'])
        audit.set_stage('prompts', progress=30, count=len(prompts), candidates=len(candidates))

    # -- stage 3: engines --

    def _group_stand_in(self):
        """What the measured handlers read off `group`: brand name + country."""
        country_name = country_info(self.audit.country)[0]
        return SimpleNamespace(domain=SimpleNamespace(
            name=self.audit.brand_name, country=country_name, url=self.audit.website,
        ))

    def _resolve_engines(self):
        """[(platform_key, label, handler, client)] for every configured provider with a key."""
        from core import analytics_helpers as ah
        from core.services.client_factory import get_client
        handlers = {
            'chatgpt': ah.process_prompt_with_chatgpt,
            'gemini': ah.process_prompt_with_gemini,
            'perplexity': ah.process_prompt_with_perplexity,
            'claude': ah.process_prompt_with_claude,
            'grok': ah.process_prompt_with_grok,
            'deepseek': ah.process_prompt_with_deepseek,
        }
        engines = []
        for provider in self.cfg.get('engines') or []:
            platform, label = PROVIDER_PLATFORMS[provider]
            try:
                client = get_client(provider, org_id=None)
            except Exception as exc:  # noqa: BLE001
                logger.warning('[Audit] %s client unavailable: %s', provider, exc)
                client = None
            engines.append((platform, label, handlers[platform], client))
        return engines

    def _drop_non_vendors(self, names: List[str], urls: List[str]) -> List[str]:
        """Keep declared competitors always; drop regulators, registries,
        reference sites, institution hosts and ≤3-letter words the shared
        extractor mistakes for brands (SEBI, NSDL, 'Sip')."""
        from core.audit_scoring import normalize_host

        def squash(v):
            return re.sub(r'[^a-z0-9]', '', (v or '').lower())

        declared = {squash(c.get('name')) for c in (self.audit.competitors or []) if c.get('name')}
        # First label of every cited host -> host, to recognise institution TLDs.
        label_host = {}
        for u in urls:
            h = normalize_host(u)
            if h:
                label_host.setdefault(squash(h.split('.')[0]), h)
        kept = []
        for name in names:
            key = squash(name)
            if key in declared:
                kept.append(name)
                continue
            if key in NON_VENDOR_NAMES or len(key) <= 3:
                continue
            host = label_host.get(key, '')
            if host and NON_VENDOR_TLD_RE.search(host):
                continue
            kept.append(name)
        return kept

    def _evidence_row(self, prompt, label, result, latency_ms) -> Dict[str, Any]:
        from core.analytics_helpers import extract_position_from_response
        from core.competitor_extractor import _clean_competitor_name
        text = result.get('response_text') or result.get('context_summary') or ''
        position = None
        if result.get('is_mention'):
            try:
                position = extract_position_from_response(
                    text, self.audit.website, result.get('citations') or [],
                    True, self.audit.brand_name,
                )
            except Exception:  # noqa: BLE001
                position = None
        # The handlers' competitor list can carry the brand's own domain back
        # as a "competitor" ('hdfcbank.com' -> 'Hdfcbank'); drop anything that
        # is the brand by name or by host label.
        def squash(v):
            return re.sub(r'[^a-z0-9]', '', (v or '').lower())
        own = {squash(self.audit.brand_name), squash(self.audit.host.split('.')[0])} - {''}
        competitors, seen = [], set()
        for name in result.get('competitor_mention_list') or []:
            cleaned = _clean_competitor_name(name)
            key = squash(cleaned)
            if cleaned and key and key not in own and key not in seen:
                seen.add(key)
                competitors.append(cleaned)
        # The extractor's text and URL strategies can name the same rival twice
        # ('Paisa' from prose, '5Paisa' from 5paisa.com); keep the longer form.
        keys = {c: squash(c) for c in competitors}
        competitors = [
            c for c in competitors
            if not any(o != c and keys[o].endswith(keys[c]) and len(keys[o]) > len(keys[c]) for o in competitors)
        ]
        competitors = self._drop_non_vendors(competitors, result.get('all_urls') or [])
        return {
            'status': 'ok',
            'is_mention': bool(result.get('is_mention')),
            'is_cited': bool(result.get('has_citation')),
            'position': position,
            'sentiment': result.get('sentiment') or '',
            'competitors_mentioned': competitors[:12],
            'rival_positions': mention_order(text, competitors[:12], self.audit.brand_name),
            'cited_domains': _hosts_of(result.get('all_urls') or []),
            'response_text': text[:MAX_RESPONSE_CHARS],
            'latency_ms': latency_ms,
            'error': '',
        }

    def stage_engines(self):
        audit = self.audit
        prompts = (audit.grounding or {}).get('prompts') or []
        if not prompts:
            raise AuditError('No prompts to run.')
        engines = self._resolve_engines()
        runs = max(1, int(self.cfg.get('runs_per_prompt') or 1))
        total = len(prompts) * len(engines) * runs
        # Only answered (prompt, engine, run) triples are skipped on resume: a
        # re-run after a provider outage must re-ask the failed ones.
        existing = set(
            AuditPromptResult.objects.filter(audit=audit, status='ok')
            .values_list('prompt_index', 'platform', 'run_index')
        )
        done = len(existing)
        audit.set_stage('engines', progress=30, done=done, total=total)

        group = self._group_stand_in()
        # One pool over every (prompt, engine, run) triple.
        #
        # This used to open a fresh pool inside the prompt loop, so each prompt
        # cost max(engine latency) and that was paid once per prompt: measured
        # on audit #26, eight prompts x ~78s = ~625s of an 11.9 minute audit,
        # against a floor of 93s (the single slowest call). The calls are
        # independent of each other, so the nesting bought nothing.
        #
        # Nothing about the calls changes - same prompts, same models, same
        # parameters, same answers, same scores. Only the schedule. The two
        # things that could have made the result differ are handled: 429s are
        # retried (see _call_with_rate_limit_retry) so a burst cannot turn into
        # a missing answer, and the cap keeps the burst small enough that the
        # providers stay happy. Raising the cap trades provider goodwill for
        # wall clock; 8-12 is the useful range.
        max_workers = max(1, int(getattr(settings, 'AUDIT_MAX_CONCURRENT_CALLS', 8)))

        def run_one(prompt, label, handler, client):
            """Pool thread: network only, no ORM."""
            started = time.monotonic()
            if client is None:
                return {'status': 'skipped', 'error': 'no API key for this engine'}
            try:
                result = _call_with_rate_limit_retry(
                    lambda: handler(prompt['text'], audit.website, client, group), label,
                )
            except Exception as exc:  # noqa: BLE001
                from core.analytics_helpers import _is_rate_limited
                return {
                    'status': 'rate_limited' if _is_rate_limited(exc) else 'failed',
                    'error': str(exc)[:1000],
                    'latency_ms': int((time.monotonic() - started) * 1000),
                }
            latency = int((time.monotonic() - started) * 1000)
            if result.get('fallback'):
                return {'status': 'failed', 'error': 'engine returned no answer', 'latency_ms': latency}
            return {'result': result, 'latency_ms': latency}

        # Resume is unchanged: only answered triples are skipped, so a re-run
        # after a provider outage still re-asks the failed ones.
        todo = [
            (prompt, run_index, label, handler, client)
            for prompt in prompts
            for run_index in range(1, runs + 1)
            for _platform, label, handler, client in engines
            if (prompt['index'], label, run_index) not in existing
        ]

        if todo:
            with ThreadPoolExecutor(max_workers=min(max_workers, len(todo)), thread_name_prefix='audit') as pool:
                futures = {
                    pool.submit(run_one, prompt, label, handler, client): (prompt, run_index, label)
                    for prompt, run_index, label, handler, client in todo
                }
                # Rows are written here, on the main thread, as each answer
                # lands - never inside the pool, so the workers stay ORM-free.
                for future in as_completed(futures):
                    prompt, run_index, label = futures[future]
                    out = future.result()
                    if 'result' in out:
                        fields = self._evidence_row(prompt, label, out['result'], out['latency_ms'])
                    else:
                        fields = {
                            'status': out['status'], 'error': out.get('error', ''),
                            'latency_ms': out.get('latency_ms'), 'is_mention': False, 'is_cited': False,
                        }
                    AuditPromptResult.objects.update_or_create(
                        audit=audit, prompt_index=prompt['index'], platform=label, run_index=run_index,
                        defaults={
                            'prompt_text': prompt['text'],
                            'topic': prompt.get('topic', '')[:255],
                            'funnel_stage': prompt.get('funnel_stage', ''),
                            **fields,
                        },
                    )
                    done += 1
                    # 30 -> 70 across the engine stage
                    audit.set_stage('engines', progress=30 + int(40 * done / total), done=done, total=total)

        answered = AuditPromptResult.objects.filter(audit=audit, status='ok').count()
        if answered == 0:
            raise AuditError('No engine returned an answer — check the provider keys.')
        audit.set_stage('engines', progress=70, done=done, total=total, answered=answered)

    # -- stage 4: serp --

    def stage_serp(self):
        audit = self.audit
        if not self.cfg.get('seo_enabled'):
            audit.set_stage('serp', progress=72, skipped=True)
            return
        if AuditKeywordResult.objects.filter(audit=audit).exists() and (audit.stage_detail or {}).get('serp', {}).get('complete'):
            audit.set_stage('serp', progress=85)
            return
        audit.set_stage('serp', progress=72)

        keywords = self._discover_keywords()
        _name, _region, language = country_info(audit.country)
        isocode = (audit.country or 'us').lower()
        from core.audit_serp import fetch_serp
        from core.seo_ranking_processor import parse_json_serp_response

        volumes = self._keyword_volumes(keywords, isocode, language)
        existing = set(AuditKeywordResult.objects.filter(audit=audit).values_list('keyword', flat=True))
        done = len(existing)
        total = len(keywords)
        todo = [kw for kw in keywords if kw not in existing]

        def rank_one(kw):
            """Pool thread: network only, no ORM.

            A raised exception here means we never got an answer, and the
            caller must NOT store that as a position. Writing an unanswered
            lookup down as 'no position' is indistinguishable from a real
            absence in the report, so a broken key or a rate limit would tell
            the prospect they rank for nothing on Google when nobody asked.
            """
            data = fetch_serp(kw, isocode, language)
            if not data:
                return {'position': None, 'url': '', 'outranked': []}
            parsed = parse_json_serp_response(data, audit.website)
            position = parsed.get('rank') or None
            # parse_json_serp_response returns competitors keyed by rank, with a
            # dict per entry: {'2': {'domain': 'x.com', 'rank': 2, ...}}.
            entries = []
            for key, value in (parsed.get('competitors') or {}).items():
                if isinstance(value, dict):
                    domain, rank = value.get('domain'), value.get('rank')
                else:  # tolerate a plain {domain: rank} map
                    domain, rank = key, value
                if domain and isinstance(rank, (int, float)) and rank:
                    entries.append((domain, rank))
            entries.sort(key=lambda pair: pair[1])
            return {
                'position': position,
                'url': parsed.get('url') or '',
                'outranked': [d for d, r in entries if position is None or r < position][:10],
            }

        # One pool over the keywords, for the same reason the engine stage uses
        # one: these lookups are independent, and 25 of them in series added
        # minutes to an audit that now takes about three.
        max_workers = max(1, int(getattr(settings, 'AUDIT_MAX_CONCURRENT_CALLS', 8)))
        unanswered = []

        if todo:
            with ThreadPoolExecutor(max_workers=min(max_workers, len(todo)), thread_name_prefix='audit-serp') as pool:
                futures = {pool.submit(rank_one, kw): kw for kw in todo}
                for future in as_completed(futures):
                    kw = futures[future]
                    try:
                        out = future.result()
                    except Exception as exc:  # noqa: BLE001
                        # No row is written: the keyword stays absent from the
                        # report rather than appearing as an unranked one, and
                        # a re-run will ask again because it is not in
                        # `existing`.
                        logger.warning('[Audit] SERP lookup failed for %r: %s', kw, exc)
                        unanswered.append(kw)
                        continue
                    AuditKeywordResult.objects.update_or_create(
                        audit=audit, keyword=kw,
                        defaults={
                            'search_volume': volumes.get(kw.lower()),
                            'position': int(out['position']) if out['position'] else None,
                            'ranking_url': out['url'][:1000],
                            'outranked_by': out['outranked'],
                            'geo_engines_mentioning': self._engines_mentioning_for(kw),
                        },
                    )
                    done += 1
                    audit.set_stage('serp', progress=72 + int(13 * done / max(total, 1)), done=done, total=total)

        if unanswered and done == 0:
            # Every lookup failed — almost always a credentials or quota problem.
            # Failing the stage is better than publishing an SEO section built
            # from nothing.
            raise AuditError(
                'No keyword could be ranked (%d attempted). Check the DataForSEO credentials.' % len(unanswered)
            )

        audit.set_stage(
            'serp', progress=85, done=done, total=total, complete=True,
            ranked=done, unanswered=len(unanswered),
        )

    def _discover_keywords(self) -> List[str]:
        cached = (self.audit.grounding or {}).get('keywords')
        if cached:
            return cached
        client, model = _internal_llm()
        p = (self.audit.grounding or {}).get('profile', {})
        count = max(5, int(self.cfg.get('keyword_count') or 50))
        system = (
            "You list the Google search queries buyers type when looking for what a "
            "company sells. Return ONLY a JSON array of strings: short commercial "
            "queries (2-5 words, lowercase, no brand names unless the query is about "
            "the brand), most valuable first, no duplicates."
        )
        user = json.dumps({
            'brand': self.audit.brand_name,
            'industry': self.audit.industry,
            'country': country_info(self.audit.country)[0],
            'categories': p.get('categories', []),
            'use_cases': p.get('use_cases', []),
            'how_many': count,
        })
        rows = _chat_json(client, model, system, user, max_tokens=4000, expect_list=True)
        keywords, seen = [], set()
        for k in rows:
            k = re.sub(r'\s+', ' ', str(k)).strip().lower()[:255]
            if k and k not in seen:
                seen.add(k)
                keywords.append(k)
        keywords = keywords[:count]
        if not keywords:
            raise AuditError('No keywords could be discovered for this site.')
        self.audit.grounding = {**(self.audit.grounding or {}), 'keywords': keywords}
        self.audit.save(update_fields=['grounding', 'modified_at'])
        return keywords

    @staticmethod
    def _keyword_volumes(keywords: List[str], isocode: str, language: str) -> Dict[str, Optional[int]]:
        try:
            from core.dataforseo_volume import fetch_search_volume, location_code_for
            data = fetch_search_volume(keywords, location_code_for(isocode), language_code=language)
            return {k: (v or {}).get('search_volume') for k, v in data.items()}
        except Exception as exc:  # noqa: BLE001
            logger.warning('[Audit] volume lookup skipped: %s', exc)
            return {}

    def _engines_mentioning_for(self, keyword: str) -> Optional[int]:
        """Engines mentioning the brand on the prompt most like this keyword, if any."""
        from core.prompt_generation import _fingerprint
        kw = _fingerprint(keyword)
        if not kw:
            return None
        best, best_score = None, 0.0
        for p in (self.audit.grounding or {}).get('prompts') or []:
            fp = _fingerprint(p['text'])
            if not fp:
                continue
            score = len(kw & fp) / len(kw | fp)
            if score > best_score:
                best, best_score = p, score
        if best is None or best_score < KEYWORD_PROMPT_MATCH:
            return None
        return AuditPromptResult.objects.filter(
            audit=self.audit, prompt_index=best['index'], status='ok', is_mention=True,
        ).count()

    # -- stage 5: score --

    def _narrative(self, prompt_rows):
        """How the engines describe the brand. Cached; one LLM call; never fatal."""
        audit = self.audit
        cached = (audit.grounding or {}).get('narrative')
        if cached:
            return cached
        if not self.cfg.get('narrative_enabled', True):
            return {'available': False, 'reason': 'disabled'}
        try:
            from core.audit_narrative import build_narrative
            client, model = _internal_llm()
            rows = list(AuditPromptResult.objects.filter(audit=audit, status='ok', is_mention=True)
                        .values('platform', 'prompt_text', 'response_text', 'status', 'is_mention'))
            rivals = []
            for r in prompt_rows:
                for c in r.get('competitors_mentioned') or []:
                    if c not in rivals:
                        rivals.append(c)
            # LLM output is stochastic (a reasoning model can spend its whole
            # budget thinking); the retry sends half the answers so there is
            # less to reason about.
            last = None
            for attempt, limit in enumerate((12, 6)):
                try:
                    out = build_narrative(
                        _chat_json, client, model, brand_name=audit.brand_name, host=audit.host, industry=audit.industry,
                        profile=(audit.grounding or {}).get('profile') or {}, rows=rows, competitors=rivals, limit=limit,
                    )
                    break
                except AuditError as exc:
                    last = exc
                    logger.info('[Audit] narrative attempt %d failed for audit %s: %s', attempt + 1, audit.pk, exc)
            else:
                raise last
        except Exception as exc:  # noqa: BLE001 - the report is complete without it
            logger.warning('[Audit] narrative failed for audit %s: %s', audit.pk, exc)
            # Not cached: a transient model failure should be retried by the
            # next re-run / re-score instead of sticking to the audit forever.
            return {'available': False, 'reason': f'could not be generated: {str(exc)[:120]}'}
        audit.grounding = {**(audit.grounding or {}), 'narrative': out}
        audit.save(update_fields=['grounding', 'modified_at'])
        return out

    def _summary(self, report):
        """Executive summary. Cached per report fingerprint; LLM when enabled, rules otherwise; never fatal."""
        from core.audit_summary import build_summary, digest, fingerprint, rules_summary
        audit = self.audit
        d = digest(audit, report)
        fp = fingerprint(d)
        cached = (audit.grounding or {}).get('summary')
        if cached and cached.get('fingerprint') == fp and cached.get('source') == 'llm':
            return cached
        out = None
        if self.cfg.get('summary_enabled', True):
            try:
                client, model = _internal_llm()
                out = build_summary(_chat_json, client, model, d)
            except Exception as exc:  # noqa: BLE001
                logger.warning('[Audit] summary failed for audit %s: %s', audit.pk, exc)
        if out is None:
            out = rules_summary(d)
        if out.get('source') == 'llm':
            audit.grounding = {**(audit.grounding or {}), 'summary': out}
            audit.save(update_fields=['grounding', 'modified_at'])
        return out

    def stage_score(self):
        from core.audit_scoring import score_audit
        audit = self.audit
        audit.set_stage('score', progress=88)
        prompt_rows = list(AuditPromptResult.objects.filter(audit=audit).values(
            'prompt_index', 'prompt_text', 'funnel_stage', 'platform', 'status', 'run_index',
            'is_mention', 'is_cited', 'position', 'sentiment', 'competitors_mentioned', 'rival_positions', 'cited_domains',
        ))
        keyword_rows = None
        if self.cfg.get('seo_enabled'):
            keyword_rows = list(AuditKeywordResult.objects.filter(audit=audit).values(
                'keyword', 'search_volume', 'position', 'ranking_url', 'outranked_by', 'geo_engines_mentioning',
            ))
        competitor_hosts = [c.get('host') for c in (audit.competitors or []) if c.get('host')]
        crawl = (audit.grounding or {}).get('crawl') or {}
        out = score_audit(
            prompt_rows, audit.brand_name, audit.host, competitor_hosts, keyword_rows=keyword_rows,
            crawl=crawl.get('measures') or None, crawl_summary=crawl.get('summary') or None,
        )
        for field, value in out['headline'].items():
            setattr(audit, field, value)
        report = out['report']
        report['profile'] = {
            'brand_name': audit.brand_name,
            'host': audit.host,
            'industry': audit.industry,
            'country': audit.country,
            'competitors': audit.competitors,
            'tech_stack': audit.tech_stack,
            'description': ((audit.grounding or {}).get('profile') or {}).get('description', ''),
        }
        report['config'] = {
            k: self.cfg.get(k) for k in ('prompt_count', 'engines', 'runs_per_prompt', 'seo_enabled', 'keyword_count', 'crawl_enabled', 'crawl_pages', 'crawl_depth')
        }
        if crawl.get('complete') and crawl.get('summary'):
            pages = list(AuditPageResult.objects.filter(audit=audit).values(
                'url', 'title', 'fetched', 'word_count', 'schema_types', 'author', 'external_links',
                'last_modified', 'question_headings', 'has_table', 'has_faq_schema', 'details',
            ))
            for p in pages:
                if p['last_modified']:
                    p['last_modified'] = p['last_modified'].isoformat()
            report['crawl'] = {**crawl['summary'], 'error': crawl.get('error'), 'pages': pages[:100]}
            # Issue history: compare with the last published audit of the same host.
            try:
                previous = (Audit.objects.filter(host=audit.host, status='DONE').exclude(pk=audit.pk)
                            .order_by('-completed_at', '-id').values_list('report', 'completed_at').first())
                if previous and isinstance(previous[0], dict) and (previous[0].get('crawl') or {}).get('technical_issues') is not None:
                    delta = _issue_delta(crawl['summary'].get('technical_issues') or [], previous[0]['crawl']['technical_issues'])
                    if delta:
                        delta['previous_completed_at'] = previous[1].isoformat() if previous[1] else None
                        delta['previous_health'] = (previous[0]['crawl'].get('health') or {}).get('score')
                    report['crawl']['issue_delta'] = delta
            except Exception as exc:  # noqa: BLE001 - history is a nicety
                logger.info('[Audit] issue history skipped for %s: %s', audit.host, exc)
        else:
            report['crawl'] = None
        report['narrative'] = self._narrative(prompt_rows)
        # Headline columns are read by the summary's digest, so set them first.
        for field, value in out['headline'].items():
            setattr(audit, field, value)
        report['summary'] = self._summary(report)
        report['generated_at'] = timezone.now().isoformat()
        audit.report = report
        audit.save(update_fields=[
            'geo_score', 'geo_stage', 'appearances', 'cited_runs', 'total_runs', 'engines_preferred',
            'engines_total', 'share_of_voice', 'seo_visibility', 'keywords_top10', 'keywords_total',
            'report', 'modified_at',
        ])
        audit.set_stage('score', progress=95, geo_score=audit.geo_score)

    # -- stage 6: publish --

    def stage_publish(self):
        audit = self.audit
        ttl = int(getattr(settings, 'AUDIT_PUBLIC_TTL_DAYS', 30))
        now = timezone.now()
        audit.status = 'DONE'
        audit.stage = 'publish'
        audit.progress = 100
        audit.completed_at = now
        audit.error = ''
        if not audit.expires_at:
            from datetime import timedelta
            audit.expires_at = now + timedelta(days=ttl)
        audit.save(update_fields=['status', 'stage', 'progress', 'completed_at', 'error', 'expires_at', 'modified_at'])

        # Emails are best-effort and come AFTER the row is DONE: a Mailgun
        # outage must never turn a finished audit into a failed one.
        outcome = {'emailed': False, 'alerted': False}
        try:
            from core.audit_notifications import notify_audit_published
            outcome = notify_audit_published(audit)
        except Exception as exc:  # noqa: BLE001
            logger.warning('[Audit] notifications failed for audit %s: %s', audit.pk, exc)
        if outcome.get('emailed'):
            # The leads table reads these columns, so an automatic send is
            # recorded the same way the "Email report" button records one.
            try:
                from core.audit_notifications import requester_address
                audit.record_email([requester_address(audit)])
            except Exception as exc:  # noqa: BLE001 - bookkeeping must not fail a published audit
                logger.info('[Audit] could not record the email for audit %s: %s', audit.pk, exc)
        merged = dict(audit.stage_detail or {})
        merged['publish'] = {**merged.get('publish', {}), **outcome}
        audit.stage_detail = merged
        audit.save(update_fields=['stage_detail'])


def run_audit(audit_id: int) -> Dict[str, Any]:
    return AuditProcessor(audit_id).run()
