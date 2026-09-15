"""Audit Engine crawl stage — the on-site half of "can the engines find you".

Runs between profile and prompts. Reads robots.txt, sitemap.xml and llms.txt,
then samples up to AUDIT_CRAWL_PAGES pages of the site and records, per page,
the signals AI engines are known to reward: JSON-LD schema (coverage and which
types), author bylines, outbound citations, last-updated dates, word count and
answer-shaped structure (question headings, tables, lists).

Two halves, kept apart so the scoring is testable without a network:

  fetch side   discover_urls() / fetch_page() / crawl_site()  — HTTP only
  score side   analyse_html() / crawl_measures() / summarise() — pure functions

crawl_measures() returns the dict audit_scoring.measures() takes as `crawl=`,
so the four Findable measures light up with real numbers instead of
"not measured". Everything degrades: a site that blocks us, a missing sitemap
or a parser error produce fewer pages and honest "not measured" values, never
a failed audit — the processor wraps the whole stage.

Plain HTTP on purpose: this is a sample of a public site for structure, not a
render, and it must not spend DataBlue credits per page.

audit_technical.py adds the technical-SEO layer on top of the same sample:
per-page on-page signals (recorded under page['tech']), a link graph, broken-
link checks, an optional Core Web Vitals call and the weighted Website Health
score. summarise() merges its output; crawl_measures() does not read it, so the
GEO score is unchanged by anything technical.
"""
import json
import logging
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

USER_AGENT = 'Mozilla/5.0 (compatible; PromptMaxxAudit/1.0; +https://promptmaxx.co)'
FETCH_TIMEOUT = 15          # seconds per request
MAX_HTML_BYTES = 1_500_000  # skip pathological pages

# The crawlers whose robots.txt access decides whether an engine can read you.
AI_BOTS = [
    ('GPTBot', 'ChatGPT'),
    ('ClaudeBot', 'Claude'),
    ('PerplexityBot', 'Perplexity'),
    ('Google-Extended', 'Gemini'),
    ('GoogleOther', 'Google AI Overviews'),
]

# Schema types the engines actually extract; used for the "type variety" half
# of the answer-structure score.
RECOMMENDED_SCHEMA = ['Organization', 'Article', 'FAQPage', 'HowTo', 'Product', 'BreadcrumbList', 'Person']

# Hosts every footer links to; they are not citations of anything.
SOCIAL_HOSTS = (
    'facebook.com', 'twitter.com', 'x.com', 'instagram.com', 'linkedin.com', 'youtube.com', 'youtu.be',
    'pinterest.com', 'whatsapp.com', 'telegram.org', 't.me', 'apps.apple.com', 'itunes.apple.com',
    'play.google.com', 'google.com', 'goo.gl', 'threads.net', 'tiktok.com', 'snapchat.com',
)

STALE_AFTER_DAYS = 365
QUESTION_WORDS = ('what', 'how', 'why', 'which', 'when', 'where', 'who', 'can', 'should', 'is', 'are', 'does', 'do')

# URLs that are never worth a sample.
SKIP_PATH_RE = re.compile(
    r'(\.(pdf|jpg|jpeg|png|gif|svg|webp|mp4|zip|css|js|xml|ico)$)|/(tag|tags|category|author|page|wp-json|feed|cart|checkout|login|signin|signup|search)(/|$)',
    re.IGNORECASE,
)


# ---- fetch side ----------------------------------------------------------------

def _get(url: str, timeout: int = FETCH_TIMEOUT):
    import requests
    return requests.get(url, timeout=timeout, allow_redirects=True, headers={'User-Agent': USER_AGENT})


def fetch_response(url: str, timeout: int = FETCH_TIMEOUT) -> Dict[str, Any]:
    """Body plus the transport facts the technical audit needs: status, redirect chain, final URL, headers, error class."""
    out: Dict[str, Any] = {'text': None, 'status': 0, 'final_url': url, 'redirects': 0, 'chain': [], 'headers': {}, 'error': ''}
    try:
        resp = _get(url, timeout)
        out['status'] = int(resp.status_code)
        out['final_url'] = resp.url or url
        out['redirects'] = len(resp.history or [])
        out['chain'] = [{'status': int(h.status_code), 'url': h.url} for h in (resp.history or [])][:10]
        out['headers'] = {k.lower(): v for k, v in resp.headers.items()
                          if k.lower() in ('strict-transport-security', 'x-robots-tag', 'content-type', 'last-modified',
                                           'content-security-policy', 'x-content-type-options', 'x-frame-options', 'referrer-policy')}
        out['bytes'] = len(resp.content or b'')
        if resp.ok and resp.text and len(resp.content) <= MAX_HTML_BYTES:
            out['text'] = resp.text
    except Exception as exc:  # noqa: BLE001
        name = type(exc).__name__.lower()
        out['error'] = ('ssl' if 'ssl' in name else 'redirect_loop' if 'toomanyredirects' in name else
                        'timeout' if 'timeout' in name else 'connection')
        logger.debug('[AuditCrawl] %s: %s', url, exc)
    return out


def certificate_info(host: str, timeout: int = 6) -> Optional[Dict[str, Any]]:
    """Expiry and issuer of the site's TLS certificate, from one handshake. None when unreachable."""
    import socket
    import ssl
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as tls:
                cert = tls.getpeercert()
        expires = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z').replace(tzinfo=dt_timezone.utc)
        issuer = dict(x[0] for x in cert.get('issuer', ())).get('organizationName', '')
        return {'expires': expires.strftime('%Y-%m-%d'), 'days_left': (expires - datetime.now(dt_timezone.utc)).days, 'issuer': issuer}
    except Exception as exc:  # noqa: BLE001 - a failed handshake is reported by fetch_error, not here
        logger.debug('[AuditCrawl] certificate check %s: %s', host, exc)
        return None


def fetch_text(url: str, timeout: int = FETCH_TIMEOUT) -> Optional[str]:
    return fetch_response(url, timeout)['text']


def parse_robots(text: Optional[str]) -> Dict[str, Any]:
    """Which AI bots are allowed at the root. Missing robots.txt = everyone allowed."""
    allowed = {bot: True for bot, _ in AI_BOTS}
    sitemaps: List[str] = []
    if not text:
        return {'present': False, 'allowed': allowed, 'sitemaps': sitemaps, 'disallow': [], 'allow': []}
    groups: List[Dict[str, Any]] = []
    current = None
    for raw in text.splitlines():
        line = raw.split('#', 1)[0].strip()
        if not line or ':' not in line:
            continue
        key, value = [p.strip() for p in line.split(':', 1)]
        key = key.lower()
        if key == 'sitemap':
            sitemaps.append(value)
        elif key == 'user-agent':
            if current is None or current['rules']:
                current = {'agents': [], 'rules': []}
                groups.append(current)
            current['agents'].append(value.lower())
        elif key in ('allow', 'disallow') and current is not None:
            current['rules'].append((key, value))
    for bot, _ in AI_BOTS:
        name = bot.lower()
        group = next((g for g in groups if name in g['agents']), None) or next((g for g in groups if '*' in g['agents']), None)
        if not group:
            continue
        # Root-blocked when a Disallow: / applies and no more specific Allow undoes it.
        blocked = any(k == 'disallow' and v.strip() == '/' for k, v in group['rules'])
        unblocked = any(k == 'allow' and v.strip() == '/' for k, v in group['rules'])
        allowed[bot] = not blocked or unblocked
    star = next((g for g in groups if '*' in g['agents']), None)
    rules = [(k, v.strip()) for k, v in (star['rules'] if star else []) if v.strip()]
    return {'present': True, 'allowed': allowed, 'sitemaps': sitemaps,
            'disallow': [v for k, v in rules if k == 'disallow'][:200], 'allow': [v for k, v in rules if k == 'allow'][:200]}


def parse_sitemap(xml: Optional[str]) -> Dict[str, List[str]]:
    """{'urls': [...], 'children': [...]} from a urlset or a sitemap index."""
    if not xml:
        return {'urls': [], 'children': []}
    locs = re.findall(r'<loc>\s*([^<\s]+)\s*</loc>', xml, flags=re.IGNORECASE)
    if re.search(r'<sitemapindex', xml, flags=re.IGNORECASE):
        return {'urls': [], 'children': locs}
    return {'urls': locs, 'children': []}


def _same_site(url: str, host: str) -> bool:
    try:
        h = urlparse(url).netloc.lower()
    except Exception:  # noqa: BLE001
        return False
    h = h[4:] if h.startswith('www.') else h
    return h == host or h.endswith('.' + host)


def discover_urls(website: str, host: str, robots: Dict[str, Any], limit: int, homepage_html: Optional[str] = None) -> Dict[str, Any]:
    """Homepage first, then sitemap URLs, then homepage links — same host, deduped."""
    found: List[str] = [website.rstrip('/') + '/']
    seen = {found[0].rstrip('/').replace('://www.', '://')}  # www and bare host are one page
    sitemap_urls = list(robots.get('sitemaps') or []) or [urljoin(website, '/sitemap.xml'), urljoin(website, '/sitemap_index.xml')]
    sitemap_present = False
    children_seen = 0
    in_sitemap: List[str] = []
    for sm in sitemap_urls[:3]:
        data = parse_sitemap(fetch_text(sm))
        if data['urls'] or data['children']:
            sitemap_present = True
        for child in data['children'][:5]:
            children_seen += 1
            data['urls'].extend(parse_sitemap(fetch_text(child))['urls'])
            if len(data['urls']) >= limit * 3:
                break
        in_sitemap.extend(data['urls'][:5000])
        for u in data['urls']:
            key = u.rstrip('/').replace('://www.', '://')
            if key not in seen and _same_site(u, host) and not SKIP_PATH_RE.search(urlparse(u).path or ''):
                seen.add(key)
                found.append(u)
        if len(found) >= limit:
            break
    if len(found) < limit and homepage_html:
        for m in re.finditer(r'href=["\']([^"\'#?]+)', homepage_html, flags=re.IGNORECASE):
            u = urljoin(website, m.group(1))
            key = u.rstrip('/').replace('://www.', '://')
            if key not in seen and _same_site(u, host) and not SKIP_PATH_RE.search(urlparse(u).path or ''):
                seen.add(key)
                found.append(u)
            if len(found) >= limit:
                break
    return {'urls': found[:limit], 'sitemap_present': sitemap_present, 'sitemap_children': children_seen,
            'sitemap_urls': in_sitemap[:5000], 'sitemap_url_count': len(in_sitemap)}


# ---- score side ----------------------------------------------------------------

def _json_ld_blocks(soup) -> List[Any]:
    out = []
    for tag in soup.find_all('script', attrs={'type': re.compile(r'application/ld\+json', re.I)}):
        try:
            data = json.loads(tag.string or tag.get_text() or '')
        except Exception:  # noqa: BLE001
            continue
        out.extend(data if isinstance(data, list) else [data])
    return out


def _types_in(node, acc: set):
    if isinstance(node, dict):
        t = node.get('@type')
        if isinstance(t, str):
            acc.add(t)
        elif isinstance(t, list):
            acc.update(str(x) for x in t)
        for v in node.values():
            _types_in(v, acc)
    elif isinstance(node, list):
        for v in node:
            _types_in(v, acc)


def _first_date(*candidates) -> Optional[str]:
    for c in candidates:
        if not c:
            continue
        s = str(c).strip()
        m = re.match(r'(\d{4}-\d{2}-\d{2})', s)
        if m:
            return m.group(1)
    return None


def _find_in_ld(blocks, key) -> Optional[str]:
    for b in blocks:
        if isinstance(b, dict):
            v = b.get(key)
            if isinstance(v, str):
                return v
            graph = b.get('@graph')
            if isinstance(graph, list):
                for g in graph:
                    if isinstance(g, dict) and isinstance(g.get(key), str):
                        return g[key]
    return None


def _ld_author(blocks) -> Optional[str]:
    """Author name from any top-level or @graph node: a string, a Person dict, or a list of them."""
    nodes = []
    for b in blocks:
        if isinstance(b, dict):
            nodes.append(b)
            if isinstance(b.get('@graph'), list):
                nodes.extend(n for n in b['@graph'] if isinstance(n, dict))
    for n in nodes:
        a = n.get('author')
        if isinstance(a, list) and a:
            a = a[0]
        if isinstance(a, str) and a.strip():
            return a.strip()
        if isinstance(a, dict) and a.get('name'):
            return str(a['name']).strip()
    return None


def analyse_html(url: str, html: str, host: str) -> Dict[str, Any]:
    """Everything the crawl records about one page. Pure; no network."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:  # pragma: no cover - bs4 is in requirements.txt
        return {'url': url, 'parse_error': 'bs4 missing'}
    soup = BeautifulSoup(html or '', 'html.parser')
    for t in soup(['script', 'style', 'noscript', 'svg']):
        if not (t.name == 'script' and 'ld+json' in (t.get('type') or '')):
            t.decompose()

    ld_tags = len(soup.find_all('script', attrs={'type': re.compile(r'application/ld\+json', re.I)}))
    blocks = _json_ld_blocks(soup)
    types: set = set()
    _types_in(blocks, types)

    meta = {}
    for m in soup.find_all('meta'):
        k = (m.get('property') or m.get('name') or '').lower()
        if k:
            meta[k] = m.get('content') or ''

    # author: JSON-LD author/Person, meta author, rel=author, visible byline
    author = _ld_author(blocks)
    if not author:
        author = meta.get('author') or meta.get('article:author') or None
    if not author:
        rel = soup.find('a', attrs={'rel': re.compile(r'\bauthor\b', re.I)})
        author = rel.get_text(strip=True) if rel else None
    if not author:
        byline = soup.find(class_=re.compile(r'\b(byline|author)\b', re.I))
        if byline:
            text = byline.get_text(' ', strip=True)
            if 2 < len(text) < 80:
                author = text

    modified = _first_date(
        _find_in_ld(blocks, 'dateModified'), meta.get('article:modified_time'), meta.get('og:updated_time'),
        _find_in_ld(blocks, 'datePublished'), meta.get('article:published_time'),
        (soup.find('time') or {}).get('datetime') if soup.find('time') else None,
    )

    body_text = soup.get_text(' ', strip=True)
    words = len(re.findall(r'\w+', body_text))

    external_hosts = set()
    external_urls: List[str] = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.startswith('http') and not _same_site(href, host):
            h = urlparse(href).netloc.lower()
            h = h[4:] if h.startswith('www.') else h
            if h and not any(h == s or h.endswith('.' + s) for s in SOCIAL_HOSTS):
                external_hosts.add(h)
                if len(external_urls) < 20 and href.split('#')[0] not in external_urls:
                    external_urls.append(href.split('#')[0])

    headings = [h.get_text(' ', strip=True) for h in soup.find_all(['h1', 'h2', 'h3'])]
    q_headings = sum(1 for h in headings if h.endswith('?') or h.split(' ', 1)[0].lower() in QUESTION_WORDS)
    title = (soup.title.get_text(strip=True) if soup.title else '') or meta.get('og:title', '')

    # Technical-SEO layer: kept under one key so the GEO signals above stay flat
    # and unchanged; a failure here costs the page its tech block, nothing else.
    tech: Dict[str, Any] = {}
    try:
        from core.audit_technical import page_signals
        tech = page_signals(url, soup, html or '', host, meta, blocks, types, body_text, ld_tags=ld_tags, external_urls=external_urls)
    except Exception as exc:  # noqa: BLE001
        logger.debug('[AuditCrawl] tech signals failed for %s: %s', url, exc)

    return {
        'url': url,
        'title': title[:255],
        'word_count': words,
        'schema_types': sorted(types)[:20],
        'has_schema': bool(blocks),
        'author': (author or '')[:120],
        'external_links': len(external_hosts),
        'last_modified': modified,
        'headings': len(headings),
        'question_headings': q_headings,
        'has_table': bool(soup.find('table')),
        'has_list': bool(soup.find(['ul', 'ol'])),
        'has_faq_schema': 'FAQPage' in types,
        'tech': tech,
    }


def _stale(date_str: Optional[str], now: Optional[datetime] = None) -> Optional[bool]:
    if not date_str:
        return None
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=dt_timezone.utc)
    except ValueError:
        return None
    now = now or datetime.now(dt_timezone.utc)
    return (now - d) > timedelta(days=STALE_AFTER_DAYS)


def summarise(pages: List[Dict[str, Any]], robots: Dict[str, Any], sitemap_present: bool, llms_txt: bool, now: Optional[datetime] = None,
              website: str = '', sitemap_children: int = 0, link_check: Optional[Dict[str, Any]] = None,
              cwv: Optional[Dict[str, Any]] = None, backlinks: Optional[Dict[str, Any]] = None,
              sitemap_urls: Optional[List[str]] = None, site: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Site-level numbers the report prints and crawl_measures() scores, plus the technical layer."""
    ok = [p for p in pages if not p.get('parse_error')]
    n = len(ok)
    with_schema = sum(1 for p in ok if p.get('has_schema'))
    types = Counter()
    for p in ok:
        for t in p.get('schema_types') or []:
            types[t] += 1
    dated = [p for p in ok if p.get('last_modified')]
    stale = [p for p in dated if _stale(p['last_modified'], now)]
    allowed = robots.get('allowed') or {}
    base = {
        'pages_sampled': n,
        'robots_present': bool(robots.get('present')),
        'bots': [{'bot': bot, 'engine': engine, 'allowed': bool(allowed.get(bot, True))} for bot, engine in AI_BOTS],
        'bots_allowed': sum(1 for bot, _ in AI_BOTS if allowed.get(bot, True)),
        'bots_total': len(AI_BOTS),
        'sitemap_present': bool(sitemap_present),
        'llms_txt': bool(llms_txt),
        'schema_coverage': round(100 * with_schema / n) if n else None,
        'schema_types': [t for t, _ in types.most_common(12)],
        'recommended_types_present': [t for t in RECOMMENDED_SCHEMA if types.get(t)],
        'author_share': round(100 * sum(1 for p in ok if p.get('author')) / n) if n else None,
        'avg_word_count': round(sum(p.get('word_count', 0) for p in ok) / n) if n else None,
        'avg_external_links': round(sum(p.get('external_links', 0) for p in ok) / n, 1) if n else None,
        'question_heading_share': round(100 * sum(1 for p in ok if p.get('question_headings')) / n) if n else None,
        'table_share': round(100 * sum(1 for p in ok if p.get('has_table')) / n) if n else None,
        'dated_pages': len(dated),
        'stale_pages': len(stale),
        'freshest': max((p['last_modified'] for p in dated), default=None),
    }
    try:
        from core.audit_technical import technical_summary
        base.update(technical_summary(pages, base, website=website, sitemap_children=sitemap_children, link_check=link_check, cwv=cwv,
                                      backlinks=backlinks, sitemap_urls=sitemap_urls, site=site, robots=robots))
    except Exception as exc:  # noqa: BLE001 - the GEO half of the summary must survive a technical-layer bug
        logger.warning('[AuditCrawl] technical summary failed: %s', exc)
    return base


def crawl_measures(summary: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """The four Findable measures, shaped for audit_scoring.measures(crawl=...).

    A measure is only scored when the crawl produced the evidence for it —
    "no dates on any page" is reported, not scored as stale.
    """
    out: Dict[str, Dict[str, Any]] = {}
    n = summary.get('pages_sampled') or 0

    # bot access: robots.txt share of AI crawlers allowed at the root
    allowed, total = summary.get('bots_allowed', 0), summary.get('bots_total') or len(AI_BOTS)
    blocked = [b['bot'] for b in summary.get('bots', []) if not b['allowed']]
    extras = []
    if summary.get('sitemap_present'):
        extras.append('sitemap')
    if summary.get('llms_txt'):
        extras.append('llms.txt')
    out['bot_access'] = {
        'value': f'{allowed} of {total} AI crawlers',
        'score': round(100 * allowed / total) if total else None,
        'evidence': (f"blocked: {', '.join(blocked)}" if blocked else 'all AI crawlers allowed') + (f" · {', '.join(extras)} found" if extras else ''),
    }

    if n:
        # answer structure: schema coverage (50) + recommended types (25) + question/table shape (25)
        coverage = (summary.get('schema_coverage') or 0) / 100
        variety = len(summary.get('recommended_types_present') or []) / len(RECOMMENDED_SCHEMA)
        shape = max((summary.get('question_heading_share') or 0), (summary.get('table_share') or 0)) / 100
        out['answer_structure'] = {
            'value': f"schema on {summary.get('schema_coverage')}% · {len(summary.get('recommended_types_present') or [])} of {len(RECOMMENDED_SCHEMA)} key types",
            'score': round(100 * (0.5 * coverage + 0.25 * variety + 0.25 * shape)),
            'evidence': f"types: {', '.join(summary.get('recommended_types_present') or []) or 'none'} · question headings on {summary.get('question_heading_share')}% · tables on {summary.get('table_share')}%",
        }

        # authority: bylines (50) + outbound citations (30) + schema Person/Organization (20)
        author_share = (summary.get('author_share') or 0) / 100
        citations = min(1.0, (summary.get('avg_external_links') or 0) / 5)
        entity = 1.0 if ('Organization' in (summary.get('recommended_types_present') or []) or 'Person' in (summary.get('recommended_types_present') or [])) else 0.0
        out['authority_signals'] = {
            'value': f"bylines on {summary.get('author_share')}% · {summary.get('avg_external_links')} outbound citations/page",
            'score': round(100 * (0.5 * author_share + 0.3 * citations + 0.2 * entity)),
            'evidence': 'author bios, outbound citations and Organization/Person schema',
        }

        # freshness: only when dates exist
        dated, stale = summary.get('dated_pages') or 0, summary.get('stale_pages') or 0
        if dated:
            out['page_freshness'] = {
                'value': f"{stale} of {dated} dated pages 12mo+",
                'score': round(100 * (1 - stale / dated)),
                'evidence': f"latest update {summary.get('freshest')}" if summary.get('freshest') else '',
            }
        else:
            out['page_freshness'] = {'value': 'no publish/update dates found', 'score': None, 'evidence': 'add dateModified to page schema'}
    return out


# ---- orchestration ----------------------------------------------------------------

def fetch_page(url: str, host: str) -> Dict[str, Any]:
    resp = fetch_response(url)
    headers = resp.get('headers') or {}
    transport = {'status_code': resp.get('status') or 0, 'redirects': resp.get('redirects') or 0,
                 'final_url': resp.get('final_url') if resp.get('final_url') != url else '',
                 'redirect_chain': resp.get('chain') or [], 'hsts': 'strict-transport-security' in headers,
                 'html_bytes': int(resp.get('bytes') or 0),
                 'security_headers': {h: (h in headers) for h in ('content-security-policy', 'x-content-type-options', 'x-frame-options', 'referrer-policy')},
                 'x_robots': (headers.get('x-robots-tag') or '')[:120], 'fetch_error': resp.get('error') or ''}
    html = resp.get('text')
    if html is None:
        status = resp.get('status') or 0
        err = resp.get('error') or ''
        return {'url': url, 'parse_error': f'HTTP {status}' if status >= 400 else ('SSL error' if err == 'ssl' else 'redirect loop' if err == 'redirect_loop' else 'fetch failed'), **transport}
    try:
        return {**analyse_html(url, html, host), **transport}
    except Exception as exc:  # noqa: BLE001
        return {'url': url, 'parse_error': str(exc)[:200], **transport}


def crawl_site(website: str, host: str, homepage_html: Optional[str] = None, limit: int = 20, budget_seconds: int = 60, workers: int = 4,
               link_checks: bool = True, link_check_limit: int = 25, cwv: bool = False, cwv_api_key: str = '',
               backlinks: bool = False, follow_links: bool = True, cwv_pages: int = 1, external_link_limit: int = 30) -> Dict[str, Any]:
    """The whole stage: robots → sitemap → sample pages (+ pages found by following links) → link checks → summary. Time-boxed.

    `cwv` adds Google PageSpeed Insights calls (free API) for the homepage and,
    with `cwv_pages` > 1, a few key pages; `backlinks` one DataForSEO Backlinks
    Summary call (paid, ~$0.03). Side calls run alongside the page fetches and
    are dropped if they miss the budget. `follow_links` keeps fetching pages
    the sample links to until `limit` is reached, so sites with a thin sitemap
    still yield a real sample.
    """
    started = time.monotonic()
    cwv_future = None
    bl_future = None
    side_pool = None
    if cwv or backlinks:
        side_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix='audit-side')
    if backlinks:
        from core.audit_backlinks import fetch_backlinks
        bl_future = side_pool.submit(fetch_backlinks, host)
    robots = parse_robots(fetch_text(urljoin(website, '/robots.txt')))
    llms = fetch_text(urljoin(website, '/llms.txt'))
    llms_txt = bool(llms and not llms.lstrip().lower().startswith('<!doctype') and not llms.lstrip().lower().startswith('<html'))
    discovered = discover_urls(website, host, robots, limit, homepage_html)

    from core.audit_technical import link_graph, norm_url
    pages: List[Dict[str, Any]] = []
    order: List[str] = list(discovered['urls'])
    queued = {norm_url(u) for u in order}
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix='audit-crawl') as pool:
        batch = list(order)
        rounds = 0
        while batch:
            remaining = budget_seconds - int(time.monotonic() - started)
            if remaining <= 3:
                logger.info('[AuditCrawl] budget exhausted for %s after %d pages', host, len(pages))
                break
            futures = {pool.submit(fetch_page, u, host): u for u in batch}
            try:
                for fut in as_completed(futures, timeout=remaining):
                    pages.append(fut.result())
            except Exception:  # noqa: BLE001 - budget exhausted: keep what we have
                logger.info('[AuditCrawl] budget exhausted for %s after %d pages', host, len(pages))
                break
            batch = []
            rounds += 1
            if not follow_links or len(pages) >= limit or rounds >= 4:
                break
            # Next round: pages the sample links to that we have not fetched, sitemap-style filters applied.
            for u in link_graph(pages, website)['unsampled']:
                if len(order) + len(batch) >= limit:
                    break
                key = norm_url(u)
                if key in queued or '?' in u or SKIP_PATH_RE.search(urlparse(u).path or ''):
                    continue
                queued.add(key)
                batch.append(u)
            order.extend(batch)
    pages.sort(key=lambda p: order.index(p['url']) if p['url'] in order else 10 ** 6)
    discovered['urls'] = order[:max(limit, len(order))]

    # PageSpeed for the homepage (+ key pages) once the sample is known, so the key pages are real ones.
    if cwv:
        from core.audit_technical import fetch_cwv_pages
        key_pages = [website.rstrip('/') + '/']
        if cwv_pages > 1:
            ranked = sorted((p for p in pages if not p.get('parse_error') and norm_url(p['url']) != norm_url(key_pages[0])),
                            key=lambda p: -(p.get('word_count') or 0))
            key_pages += [p['url'] for p in ranked[:max(0, cwv_pages - 1)]]
        cwv_future = side_pool.submit(fetch_cwv_pages, key_pages, cwv_api_key)

    # Broken-link check: internal links the sample did not fetch, plus a sample of outbound links.
    link_check = None
    if link_checks:
        try:
            from core.audit_technical import check_links
            sampled = {norm_url(u) for u in order}
            candidates = [u for u in link_graph(pages, website)['unsampled'] if norm_url(u) not in sampled]
            external = []
            seen_ext = set()
            for p in pages:
                for u in ((p.get('tech') or {}).get('external_urls') or []):
                    if u not in seen_ext:
                        seen_ext.add(u)
                        external.append(u)
            left = budget_seconds - int(time.monotonic() - started)
            if (candidates or external) and left > 3:
                link_check = check_links(candidates, limit=link_check_limit, workers=workers, budget_seconds=min(20, left))
                left = budget_seconds - int(time.monotonic() - started)
                if external and left > 3:
                    ext = check_links(external, limit=external_link_limit, workers=workers, budget_seconds=min(15, left), strict=True)
                    link_check.update({'external_checked': ext['checked'], 'external_broken': ext['broken'], 'external_examples': ext['examples']})
        except Exception as exc:  # noqa: BLE001
            logger.info('[AuditCrawl] link check skipped for %s: %s', host, exc)

    # Site-level transport checks: does http:// redirect to https://, does the homepage send HSTS.
    site: Dict[str, Any] = {}
    try:
        home = next((p for p in pages if not p.get('parse_error')), None)
        site['hsts'] = bool(home and home.get('hsts'))
        site['ssl_error'] = any(p.get('fetch_error') == 'ssl' for p in pages)
        site['security_headers'] = (home or {}).get('security_headers') or {}
        if website.startswith('https://'):
            site['certificate'] = certificate_info(host)
        if website.startswith('https://'):
            plain = fetch_response('http://' + host + '/', timeout=8)
            site['http_redirects_to_https'] = (plain.get('final_url') or '').startswith('https://') if (plain.get('status') or 0) else None
    except Exception as exc:  # noqa: BLE001
        logger.info('[AuditCrawl] site checks skipped for %s: %s', host, exc)

    cwv_result = None
    bl_result = None
    for name, fut in (('Core Web Vitals', cwv_future), ('backlinks', bl_future)):
        if fut is None:
            continue
        try:
            value = fut.result(timeout=max(1, budget_seconds - int(time.monotonic() - started)))
        except Exception:  # noqa: BLE001 - slow or failed side call: not measured
            logger.info('[AuditCrawl] %s not measured for %s', name, host)
            value = None
        if fut is cwv_future:
            cwv_result = value
        else:
            bl_result = value
    if side_pool is not None:
        side_pool.shutdown(wait=False)

    summary = summarise(pages, robots, discovered['sitemap_present'], llms_txt, website=website,
                        sitemap_children=discovered.get('sitemap_children', 0), link_check=link_check, cwv=cwv_result,
                        backlinks=bl_result, sitemap_urls=discovered.get('sitemap_urls') or [], site=site)
    summary['seconds'] = round(time.monotonic() - started, 1)
    summary['urls_discovered'] = len(discovered['urls'])
    summary['sitemap_url_count'] = discovered.get('sitemap_url_count', 0)
    return {'robots': robots, 'summary': summary, 'pages': pages, 'measures': crawl_measures(summary)}
