"""Audit Engine — technical SEO and site-health layer over the crawl sample.

audit_crawl.py fetches a sample of the site's pages and records the GEO
signals (schema, bylines, citations, dates). This module reads the same parsed
pages a second time for the classic technical-SEO signals and folds everything
into one weighted Website Health score, an issue list and the "winning content
patterns" block — the parts of an agency audit that need no paid service.

Per page (page_signals)      title / description / H1 hygiene, canonical,
                             noindex, viewport, image alt, mixed content,
                             hreflang, Open Graph, internal links + anchor
                             text, schema field gaps, Person schema,
                             credential mentions
Across the sample            link graph → crawl depth + orphan candidates
                             (link_graph), site counts, issue list, 8-category
                             health score, content patterns (technical_summary)
Optional, network            Core Web Vitals via Google PageSpeed Insights
                             (fetch_cwv — free API key, off unless enabled)
                             and HEAD checks on unsampled internal links
                             (check_links)

Everything here is additive: the GEO score and the four Findable measures in
audit_crawl.crawl_measures() do not read any of these keys, so audits scored
before this module existed keep their numbers. Every function tolerates
missing input and returns "not measured" (None) rather than raising.
"""
import logging
import re
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

# Anchor text that tells a crawler nothing about the target page.
GENERIC_ANCHORS = {
    '', 'click here', 'here', 'read more', 'learn more', 'more', 'link', 'this', 'this page', 'continue',
    'continue reading', 'view', 'view more', 'see more', 'see all', 'go', 'next', 'previous', 'prev', 'details',
    'page', 'download', 'submit', 'button', 'image', 'icon', 'logo',
}
# Trust / expertise claims AI engines treat as E-E-A-T evidence.
CREDENTIAL_RE = re.compile(
    r"\b(award(?:s|ed|-winning)?|certified|certification|accredited|accreditation|iso\s?\d{4,5}|"
    r"years? of experience|featured in|as seen (?:in|on)|trusted by|recogni[sz]ed|winner|licen[cs]ed|"
    r"registered with|member of|sebi[- ]registered|fda[- ]approved|peer[- ]reviewed)\b", re.I)
# Fields AI engines actually use from each schema type; a type without them is
# "present but thin". Only top-level and @graph nodes are checked.
SCHEMA_REQUIRED = {
    'Organization': ['name', 'url', 'logo', 'description', 'sameAs'],
    'Article': ['headline', 'author', 'datePublished', 'dateModified'],
    'BlogPosting': ['headline', 'author', 'datePublished', 'dateModified'],
    'NewsArticle': ['headline', 'author', 'datePublished', 'dateModified'],
    'Product': ['name', 'description', 'offers'],
    'FAQPage': ['mainEntity'],
    'HowTo': ['name', 'step'],
    'Person': ['name', 'url'],
    'LocalBusiness': ['name', 'address', 'telephone'],
}
ASSET_RE = re.compile(r'\.(pdf|jpe?g|png|gif|svg|webp|mp4|mp3|zip|css|js|xml|ico|woff2?|ttf)(\?|$)', re.I)
MIXED_RE = re.compile(r'''(?:<(?:img|script|iframe|video|audio|source|link)\b[^>]*?\s(?:src|href)=["'])http://''', re.I)

TITLE_RANGE = (30, 60)        # characters; outside = "length issue"
DESC_RANGE = (70, 160)
THIN_WORDS = 200              # a content page under this is "thin"
DUPLICATE_SIMILARITY = 0.8    # shingle overlap above which two pages are near-duplicates
SHINGLE_KEEP = 128            # min-hash sample size kept per page
UTILITY_PATH_RE = re.compile(r'/(contact|login|signin|signup|register|privacy|terms|cookie|legal|disclaimer|sitemap|thank|cart|checkout|account)', re.I)
PARAM_RE = re.compile(r'[?&](page|p|sort|order|filter|utm_[a-z]+|ref|sessionid|sid)=', re.I)
LANG_CODE_RE = re.compile(r'^(x-default|[a-z]{2,3}(-[a-z]{2,4})?(-[a-z]{2})?)$', re.I)
SOFT_404_RE = re.compile(r'\b(page not found|404 not found|not found|no longer available|this page (does not|doesn.t) exist|nothing found)\b', re.I)
LEGACY_IMAGE_RE = re.compile(r'\.(jpe?g|png|gif|bmp)(\?|$)', re.I)
HTML_HEAVY_BYTES = 300_000          # HTML alone over this is a heavy page
SCRIPTS_MANY = 30                   # script tags per page before we call it script-heavy
CERT_WARN_DAYS = 30
SECURITY_HEADERS = {
    'content-security-policy': 'Content-Security-Policy',
    'x-content-type-options': 'X-Content-Type-Options',
    'x-frame-options': 'X-Frame-Options',
    'referrer-policy': 'Referrer-Policy',
}
# The exact thing to add, per issue - printed under the fix so a developer can paste it.
FIX_SNIPPETS = {
    'missing_title': '<title>Primary topic - Brand</title>',
    'missing_description': '<meta name="description" content="One or two sentences, 70-160 characters, that say what the page offers.">',
    'missing_h1': '<h1>The page topic, once</h1>',
    'canonical_missing': '<link rel="canonical" href="https://www.example.com/this-page/">',
    'param_urls': '<link rel="canonical" href="https://www.example.com/this-page/">  (on every ?sort= / ?page= variant)',
    'missing_viewport': '<meta name="viewport" content="width=device-width, initial-scale=1">',
    'noindex': 'remove: <meta name="robots" content="noindex">',
    'x_robots_noindex': 'remove the response header: X-Robots-Tag: noindex',
    'robots_blocked': 'robots.txt: delete the Disallow: line that matches these paths (or add Allow: /path)',
    'og_incomplete': '<meta property="og:title" content="..."><meta property="og:description" content="..."><meta property="og:image" content="https://.../1200x630.jpg">',
    'images_missing_alt': '<img src="..." alt="What the image shows">',
    'images_dimensions': '<img src="..." width="800" height="450" alt="...">',
    'legacy_image_formats': '<picture><source type="image/webp" srcset="hero.webp"><img src="hero.jpg" alt="..."></picture>',
    'hsts_missing': 'response header: Strict-Transport-Security: max-age=31536000; includeSubDomains',
    'security_headers': 'response headers: X-Content-Type-Options: nosniff / X-Frame-Options: SAMEORIGIN / Referrer-Policy: strict-origin-when-cross-origin / Content-Security-Policy: ...',
    'http_no_redirect': 'server rule: redirect http://* to https://* with a 301',
    'mixed_content': 'change src="http://..." to src="https://..." (or protocol-relative "//...") for scripts, styles, images, iframes',
    'lang_missing': '<html lang="en">',
    'meta_refresh': 'replace <meta http-equiv="refresh" content="0;url=..."> with a server-side 301 redirect',
    'invalid_json_ld': 'validate the block at https://validator.schema.org - usually a trailing comma or an unescaped quote',
    'rich_result_blockers': '{"@context":"https://schema.org","@type":"Article","headline":"...","image":["..."],"datePublished":"2026-01-01","author":{"@type":"Person","name":"..."}}',
    'schema_gaps': '{"@type":"Organization","name":"...","url":"...","logo":"...","description":"...","sameAs":["https://www.linkedin.com/company/..."]}',
    'redirect_chains': 'point the first URL straight at the final URL (one 301, not two)',
    'redirected': 'update the link / sitemap entry to the final URL',
    'broken_links': 'fix the target page or change the link; 301 old URLs that moved',
    'sitemap_errors': 'remove URLs that 404, redirect or carry noindex from sitemap.xml',
    'not_in_sitemap': 'add the URL to sitemap.xml with <lastmod>',
    'duplicate_titles': 'give each page its own <title>',
    'duplicate_descriptions': 'give each page its own meta description',
    'title_length': 'keep <title> between 30 and 60 characters',
    'title_equals_h1': '<title>Topic + benefit - Brand</title> with <h1>Topic</h1> (different wording, same subject)',
    'description_length': 'keep the description between 70 and 160 characters',
    'multiple_h1': 'keep one <h1>; change the others to <h2>',
    'heading_structure': 'use h1 > h2 > h3 in order; remove empty headings',
    'thin_content': 'expand to 300+ words that answer the page\'s question, or merge into a stronger page',
    'duplicate_content': '<link rel="canonical" href="https://www.example.com/the-one-to-keep/"> on the copies, or merge them',
    'hreflang_errors': '<link rel="alternate" hreflang="en-in" href="https://www.example.com/in/"> on every language version, each pointing to all the others',
    'soft_404': 'return a real 404 status for missing pages (or redirect to the replacement page)',
    'html_heavy': 'move inline scripts/styles to files, remove hidden markup, paginate long lists',
    'script_heavy': 'defer or remove unused scripts; combine tag-manager pixels',
    'cert_expiring': 'renew the TLS certificate (Let\'s Encrypt renews automatically when configured)',
    'no_favicon': '<link rel="icon" href="/favicon.ico">',
    'orphans': 'add a contextual link from a related page or the navigation',
    'broken_external_links': 'replace the link with a live source, or remove it',
}
STOPWORDS = {'the', 'and', 'for', 'with', 'your', 'you', 'our', 'from', 'that', 'this', 'are', 'how', 'what', 'best', 'top', 'guide',
             'online', 'india', 'free', 'new', 'get', 'more', 'about', 'all', 'can', 'one', 'why', 'who', 'when', 'where', 'into', 'vs'}
# Google rich-result requirements per type (a subset of the schema.org "required" fields that actually block eligibility).
RICH_RESULT_REQUIRED = {
    'FAQPage': ['mainEntity'], 'HowTo': ['name', 'step'], 'Product': ['name'], 'Article': ['headline', 'image', 'datePublished'],
    'BlogPosting': ['headline', 'image', 'datePublished'], 'NewsArticle': ['headline', 'image', 'datePublished'],
    'BreadcrumbList': ['itemListElement'], 'Organization': ['name', 'url'], 'LocalBusiness': ['name', 'address'],
    'Recipe': ['name', 'image'], 'Event': ['name', 'startDate', 'location'], 'JobPosting': ['title', 'datePosted', 'hiringOrganization', 'jobLocation'],
    'VideoObject': ['name', 'thumbnailUrl', 'uploadDate'], 'Review': ['itemReviewed', 'reviewRating'],
}
INTERNAL_LINK_TARGET = 20     # internal links per page for full credit
WORDS_TARGET = 1200           # words per page for full content-depth credit
CITATIONS_TARGET = 5          # outbound citations per page (Pixis threshold)

# Website Health categories: key, label, weight (sums to 100). A category with
# no evidence scores None and its weight is shared among the rest.
HEALTH_CATEGORIES = [
    ('crawlability', 'AI crawlability', 12),
    ('schema', 'Structured data (schema)', 20),
    ('depth', 'Content depth', 16),
    ('eeat', 'E-E-A-T signals', 15),
    ('internal_linking', 'Internal linking', 10),
    ('technical', 'On-page & technical SEO', 10),
    ('backlinks', 'Backlink authority', 7),
    ('freshness', 'Content freshness', 7),
    ('cwv', 'Core Web Vitals', 3),
]

# LCP ms, CLS, INP ms — Google's "good" / "poor" thresholds.
CWV_THRESHOLDS = {'lcp_ms': (2500, 4000), 'cls': (0.1, 0.25), 'inp_ms': (200, 500)}
CWV_POINTS = {'good': 100, 'needs_improvement': 50, 'poor': 0}
PSI_ENDPOINT = 'https://www.googleapis.com/pagespeedonline/v5/runPagespeed'


# ---- url helpers ----------------------------------------------------------------

def norm_url(url: str) -> str:
    """One identity per page: lowercase host without www, no fragment, no trailing slash."""
    try:
        p = urlparse(url.strip())
    except Exception:  # noqa: BLE001
        return url
    host = (p.netloc or '').lower()
    host = host[4:] if host.startswith('www.') else host
    path = (p.path or '/').rstrip('/') or '/'
    q = f"?{p.query}" if p.query else ''
    return f"{(p.scheme or 'https').lower()}://{host}{path}{q}"


def _same_site(url: str, host: str) -> bool:
    try:
        h = urlparse(url).netloc.lower()
    except Exception:  # noqa: BLE001
        return False
    h = h[4:] if h.startswith('www.') else h
    return h == host or h.endswith('.' + host)


def _path(url: str) -> str:
    try:
        return urlparse(url).path or '/'
    except Exception:  # noqa: BLE001
        return url


def _short(url: str) -> str:
    """host/path for link targets, so a dead link on a subdomain is not shown as a bare '/'."""
    try:
        p = urlparse(url)
        host = (p.netloc or '').lower()
        host = host[4:] if host.startswith('www.') else host
        return (host + (p.path or '/'))[:70]
    except Exception:  # noqa: BLE001
        return url[:70]


# ---- per page ------------------------------------------------------------------

def _rel_values(tag) -> List[str]:
    rel = tag.get('rel') or []
    if isinstance(rel, str):
        rel = rel.split()
    return [str(r).lower() for r in rel]


def _schema_gaps(blocks) -> List[str]:
    """'Organization missing description, sameAs' for each thin node."""
    nodes = []
    for b in blocks or []:
        if isinstance(b, dict):
            nodes.append(b)
            if isinstance(b.get('@graph'), list):
                nodes.extend(n for n in b['@graph'] if isinstance(n, dict))
    gaps = []
    seen = set()
    for n in nodes:
        t = n.get('@type')
        types = [t] if isinstance(t, str) else [str(x) for x in t] if isinstance(t, list) else []
        for typ in types:
            req = SCHEMA_REQUIRED.get(typ)
            if not req or typ in seen:
                continue
            seen.add(typ)
            missing = [f for f in req if n.get(f) in (None, '', [], {})]
            if missing:
                gaps.append(f"{typ} missing {', '.join(missing)}")
    return gaps


def _length_issue(n: int, lo: int, hi: int) -> Optional[str]:
    return None if n == 0 else 'short' if n < lo else 'long' if n > hi else None


def _heading_issues(soup) -> List[str]:
    """Skipped levels (H1 → H3), empty headings; the H1 count is reported separately."""
    issues = []
    last = 0
    empty = 0
    skipped = 0
    for h in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        level = int(h.name[1])
        if not h.get_text(strip=True):
            empty += 1
        if last and level > last + 1:
            skipped += 1
        last = level
    if skipped:
        issues.append(f"{skipped} skipped level{'s' if skipped != 1 else ''}")
    if empty:
        issues.append(f"{empty} empty heading{'s' if empty != 1 else ''}")
    return issues


def _rich_result_blockers(blocks) -> List[str]:
    """Schema types present but missing a field Google requires for the rich result."""
    nodes = []
    for b in blocks or []:
        if isinstance(b, dict):
            nodes.append(b)
            if isinstance(b.get('@graph'), list):
                nodes.extend(n for n in b['@graph'] if isinstance(n, dict))
    out = []
    seen = set()
    for n in nodes:
        t = n.get('@type')
        for typ in ([t] if isinstance(t, str) else [str(x) for x in t] if isinstance(t, list) else []):
            req = RICH_RESULT_REQUIRED.get(typ)
            if not req or typ in seen:
                continue
            seen.add(typ)
            missing = [f for f in req if n.get(f) in (None, '', [], {})]
            if missing:
                out.append(f"{typ}: {', '.join(missing)}")
    return out


def shingles(text: str, keep: int = SHINGLE_KEEP) -> List[int]:
    """Min-hash style sample of 5-word shingles; two pages' overlap estimates their similarity."""
    words = re.findall(r'[a-z0-9]+', (text or '').lower())
    if len(words) < 30:
        return []
    hashes = {hash(' '.join(words[i:i + 5])) & 0xFFFFFFFF for i in range(len(words) - 4)}
    return sorted(hashes)[:keep]


def similarity(a: List[int], b: List[int]) -> float:
    if not a or not b:
        return 0.0
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb)


def page_signals(url: str, soup, raw_html: str, host: str, meta: Dict[str, str], blocks, types: Iterable[str], body_text: str,
                 ld_tags: int = 0, external_urls: Optional[List[str]] = None) -> Dict[str, Any]:
    """Technical / on-page signals for one parsed page. Pure; never raises to the caller."""
    out: Dict[str, Any] = {}
    parsed = urlparse(url)
    title = (soup.title.get_text(strip=True) if soup.title else '') or ''
    desc = (meta.get('description') or '').strip()
    out['title_length'] = len(title)
    out['description_length'] = len(desc)
    out['meta_description'] = desc[:200]
    out['title_issue'] = _length_issue(len(title), *TITLE_RANGE)
    out['description_issue'] = _length_issue(len(desc), *DESC_RANGE)
    h1s = soup.find_all('h1')
    out['h1_count'] = len(h1s)
    h1_text = h1s[0].get_text(' ', strip=True) if h1s else ''
    out['h1_text'] = h1_text[:160]
    out['title_equals_h1'] = bool(title and h1_text and title.strip().lower() == h1_text.strip().lower())
    out['heading_issues'] = _heading_issues(soup)
    robots_meta = f"{meta.get('robots', '')} {meta.get('googlebot', '')}".lower()
    out['noindex'] = 'noindex' in robots_meta
    out['nofollow_meta'] = 'nofollow' in robots_meta

    canonical = None
    for link in soup.find_all('link'):
        if 'canonical' in _rel_values(link) and link.get('href'):
            canonical = urljoin(url, link['href'].strip())
            break
    out['canonical'] = (canonical or '')[:500]
    out['canonical_status'] = 'missing' if not canonical else ('ok' if norm_url(canonical) == norm_url(url) else 'mismatch')

    out['viewport'] = bool(meta.get('viewport'))
    imgs = soup.find_all('img')
    out['images'] = len(imgs)
    out['images_missing_alt'] = sum(1 for i in imgs if i.get('alt') is None)
    out['images_missing_dimensions'] = sum(1 for i in imgs if not (i.get('width') and i.get('height')))
    out['images_lazy'] = sum(1 for i in imgs if (i.get('loading') or '').lower() == 'lazy')
    out['mixed_content'] = len(MIXED_RE.findall(raw_html or '')) if parsed.scheme == 'https' else 0
    hreflangs = [(str(link.get('hreflang')).strip(), urljoin(url, link.get('href') or '')) for link in soup.find_all('link')
                 if link.get('hreflang') and 'alternate' in _rel_values(link)]
    out['hreflang'] = len(hreflangs)
    out['hreflang_entries'] = hreflangs[:40]
    out['hreflang_invalid'] = [code for code, _ in hreflangs if not LANG_CODE_RE.match(code)][:5]
    out['og'] = bool(meta.get('og:title'))
    out['og_missing'] = [k for k in ('og:title', 'og:description', 'og:image') if not meta.get(k)]
    out['twitter_card'] = bool(meta.get('twitter:card'))
    out['https'] = parsed.scheme == 'https'
    out['json_ld_tags'] = int(ld_tags or 0)
    out['json_ld_invalid'] = max(0, int(ld_tags or 0) - len([b for b in (blocks or []) if isinstance(b, (dict, list))]))
    out['rich_result_blockers'] = _rich_result_blockers(blocks)[:6]
    out['external_urls'] = list(external_urls or [])[:20]
    words = len(re.findall(r'\w+', body_text or ''))
    out['thin'] = bool(words < THIN_WORDS and not UTILITY_PATH_RE.search(parsed.path or '') and (parsed.path or '/') != '/')
    out['shingles'] = shingles(body_text)
    out['title_words'] = [w for w in re.findall(r'[a-z0-9]{3,}', title.lower()) if w not in STOPWORDS][:8]
    # small technical checks: page weight, scripts, image formats, soft 404, lang, favicon, meta refresh
    # scripts were stripped from the soup before parsing, so count them in the raw HTML (JSON-LD blocks excluded)
    out['scripts'] = max(0, len(re.findall(r'<script\b', raw_html or '', flags=re.I)) - int(ld_tags or 0))
    out['stylesheets'] = sum(1 for link in soup.find_all('link') if 'stylesheet' in _rel_values(link))
    out['images_legacy'] = sum(1 for i in imgs if LEGACY_IMAGE_RE.search(i.get('src') or '') and not i.get('srcset') and not (i.parent and i.parent.name == 'picture'))
    out['images_srcset'] = sum(1 for i in imgs if i.get('srcset'))
    head_text = (title + ' ' + h1_text).lower()
    out['soft_404'] = bool(SOFT_404_RE.search(head_text) or (words < 60 and SOFT_404_RE.search((body_text or '')[:400])))
    html_tag = soup.find('html')
    out['lang'] = (html_tag.get('lang') or '').strip() if html_tag else ''
    out['favicon'] = any('icon' in _rel_values(link) for link in soup.find_all('link'))
    out['meta_refresh'] = any((m.get('http-equiv') or '').lower() == 'refresh' for m in soup.find_all('meta'))

    internal: List[str] = []
    seen = set()
    generic = 0
    total_anchors = 0
    param_links = 0
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        if not href or href.startswith(('#', 'mailto:', 'tel:', 'javascript:')):
            continue
        target = urljoin(url, href)
        if not _same_site(target, host) or ASSET_RE.search(_path(target)):
            continue
        if PARAM_RE.search(target):
            param_links += 1
        total_anchors += 1
        text = a.get_text(' ', strip=True).lower()
        if text in GENERIC_ANCHORS or len(text) < 3:
            generic += 1
        key = norm_url(target)
        if key not in seen and key != norm_url(url) and len(internal) < 300:
            seen.add(key)
            internal.append(key)
    out['internal_links'] = len(internal)
    out['internal_anchors'] = total_anchors
    out['generic_anchors'] = generic
    out['internal_urls'] = internal
    out['param_links'] = param_links
    out['has_params'] = bool(parsed.query)

    out['schema_gaps'] = _schema_gaps(blocks)[:6]
    out['has_person_schema'] = 'Person' in set(types or [])
    out['credential_mentions'] = len(CREDENTIAL_RE.findall(body_text or ''))
    return out


# ---- link graph (depth + orphans) ------------------------------------------------------

def link_graph(pages: List[Dict[str, Any]], website: str) -> Dict[str, Any]:
    """Crawl depth from the homepage and pages no sampled page links to — over the sample only."""
    home = norm_url(website.rstrip('/') + '/')
    nodes = {}
    for p in pages:
        if p.get('parse_error') or not p.get('url'):
            continue
        tech = p.get('tech') or {}
        nodes[norm_url(p['url'])] = set(tech.get('internal_urls') or [])
    if not nodes:
        return {'depth': {}, 'orphans': [], 'unreached': [], 'unsampled': []}
    start = home if home in nodes else next(iter(nodes))
    depth = {start: 0}
    queue = deque([start])
    while queue:
        u = queue.popleft()
        for v in nodes.get(u, ()):
            if v in nodes and v not in depth:
                depth[v] = depth[u] + 1
                queue.append(v)
    incoming = Counter()
    unsampled = set()
    for u, edges in nodes.items():
        for v in edges:
            if v in nodes:
                if v != u:
                    incoming[v] += 1
            else:
                unsampled.add(v)
    orphans = [u for u in nodes if u != start and incoming[u] == 0]
    unreached = [u for u in nodes if u not in depth]
    return {'depth': depth, 'orphans': orphans, 'unreached': unreached, 'unsampled': sorted(unsampled)}


# ---- network helpers (optional) ------------------------------------------------------

def head_status(url: str, timeout: int = 8) -> int:
    """HTTP status of a URL, following redirects; 0 when unreachable."""
    import requests
    from core.audit_crawl import USER_AGENT
    try:
        r = requests.head(url, timeout=timeout, allow_redirects=True, headers={'User-Agent': USER_AGENT})
        if r.status_code in (403, 405, 501):  # servers that refuse HEAD
            r = requests.get(url, timeout=timeout, allow_redirects=True, stream=True, headers={'User-Agent': USER_AGENT})
            r.close()
        return int(r.status_code)
    except Exception as exc:  # noqa: BLE001
        logger.debug('[AuditTech] head %s: %s', url, exc)
        return 0


# Outbound links: only hard errors count. Many big sites (exchanges, regulators)
# answer bots with 403 or drop the connection, which says nothing about the link.
EXTERNAL_BROKEN = {404, 410, 500, 502, 503, 504}


def check_links(urls: List[str], limit: int = 25, timeout: int = 8, workers: int = 4, budget_seconds: int = 15, strict: bool = False) -> Dict[str, Any]:
    """HEAD a sample of links; broken = 4xx/5xx/unreachable (internal) or hard errors only (`strict`, for outbound links)."""
    sample = list(urls)[:limit]
    if not sample:
        return {'checked': 0, 'broken': 0, 'examples': []}
    results: Dict[str, int] = {}
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix='audit-links') as pool:
        futures = {pool.submit(head_status, u, timeout): u for u in sample}
        try:
            for fut in as_completed(futures, timeout=budget_seconds):
                results[futures[fut]] = fut.result()
        except Exception:  # noqa: BLE001 - budget exhausted: report what finished
            pass
    broken = [(u, s) for u, s in results.items() if ((s in EXTERNAL_BROKEN) if strict else (s == 0 or s >= 400))]
    return {
        'checked': len(results), 'broken': len(broken),
        'examples': [{'url': u, 'status': s} for u, s in broken[:100]],
    }


def _rate(metric: str, value: Optional[float]) -> Optional[str]:
    if value is None:
        return None
    good, poor = CWV_THRESHOLDS[metric]
    return 'good' if value <= good else 'poor' if value > poor else 'needs_improvement'


def parse_cwv(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Field (CrUX p75) metrics when Google has them, else Lighthouse lab values. None when neither."""
    if not isinstance(data, dict):
        return None
    out: Dict[str, Any] = {'source': None, 'lcp_ms': None, 'cls': None, 'inp_ms': None, 'performance_score': None, 'mobile_friendly': None}
    field = ((data.get('loadingExperience') or {}).get('metrics') or {})
    if field:
        lcp = (field.get('LARGEST_CONTENTFUL_PAINT_MS') or {}).get('percentile')
        cls = (field.get('CUMULATIVE_LAYOUT_SHIFT_SCORE') or {}).get('percentile')
        inp = (field.get('INTERACTION_TO_NEXT_PAINT') or {}).get('percentile')
        if lcp is not None or cls is not None or inp is not None:
            out.update({'source': 'field', 'lcp_ms': lcp, 'cls': (cls / 100) if cls is not None else None, 'inp_ms': inp})
    lh = data.get('lighthouseResult') or {}
    audits = lh.get('audits') or {}
    if out['source'] is None and audits:
        def num(key):
            v = (audits.get(key) or {}).get('numericValue')
            return float(v) if isinstance(v, (int, float)) else None
        out.update({'source': 'lab', 'lcp_ms': num('largest-contentful-paint'), 'cls': num('cumulative-layout-shift'),
                    'inp_ms': num('interaction-to-next-paint')})
    perf = ((lh.get('categories') or {}).get('performance') or {}).get('score')
    if isinstance(perf, (int, float)):
        out['performance_score'] = round(100 * perf)
    vp = (audits.get('viewport') or {}).get('score')
    out['mobile_friendly'] = (vp == 1) if isinstance(vp, (int, float)) else None
    if out['source'] is None:
        return None
    for k in ('lcp_ms', 'cls', 'inp_ms'):
        if out[k] is not None:
            out[k] = round(out[k], 3 if k == 'cls' else 0)
        out[f"{k}_rating"] = _rate(k, out[k])
    points = [CWV_POINTS[out[f"{k}_rating"]] for k in ('lcp_ms', 'cls', 'inp_ms') if out.get(f"{k}_rating")]
    out['score'] = round(sum(points) / len(points)) if points else None
    return out


def fetch_cwv(url: str, api_key: str = '', timeout: int = 60) -> Optional[Dict[str, Any]]:
    """One PageSpeed Insights call for the homepage (mobile). Free, but keyless calls get a zero quota (429)."""
    import requests
    params = {'url': url, 'strategy': 'mobile', 'category': 'performance'}
    if api_key:
        params['key'] = api_key
    try:
        r = requests.get(PSI_ENDPOINT, params=params, timeout=timeout)
        if not r.ok:
            logger.info('[AuditTech] PSI %s for %s', r.status_code, url)
            return None
        return parse_cwv(r.json())
    except Exception as exc:  # noqa: BLE001
        logger.info('[AuditTech] PSI failed for %s: %s', url, exc)
        return None


# ---- site level ----------------------------------------------------------------------

def robots_blocks(path: str, robots: Optional[Dict[str, Any]]) -> bool:
    """Does the wildcard group's Disallow list block this path (longest matching rule wins, Allow beats Disallow on ties)?"""
    if not robots:
        return False
    best_len, blocked = -1, False
    for kind, rules in (('disallow', robots.get('disallow') or []), ('allow', robots.get('allow') or [])):
        for rule in rules:
            pattern = rule.rstrip('$')
            prefix = pattern.split('*', 1)[0]
            if not prefix or not path.startswith(prefix):
                continue
            if '*' in pattern:
                regex = '^' + re.escape(pattern).replace(r'\*', '.*')
                if not re.match(regex, path):
                    continue
            n = len(pattern)
            if n > best_len or (n == best_len and kind == 'allow'):
                best_len, blocked = n, (kind == 'disallow')
    return blocked


def indexability(page: Dict[str, Any], robots: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """One verdict per page: indexable, or the first reason it is not."""
    t = page.get('tech') or {}
    status = page.get('status_code') or 0
    if page.get('parse_error') and status >= 400:
        return {'verdict': 'not_indexable', 'reason': f'HTTP {status}'}
    if page.get('parse_error'):
        return {'verdict': 'unknown', 'reason': page['parse_error']}
    if robots_blocks(_path(page.get('url', '')), robots):
        return {'verdict': 'not_indexable', 'reason': 'blocked by robots.txt'}
    if t.get('noindex'):
        return {'verdict': 'not_indexable', 'reason': 'noindex meta tag'}
    if 'noindex' in (page.get('x_robots') or '').lower():
        return {'verdict': 'not_indexable', 'reason': 'X-Robots-Tag: noindex'}
    if t.get('canonical_status') == 'mismatch':
        return {'verdict': 'canonicalised', 'reason': 'canonical points to another URL'}
    if (page.get('redirects') or 0) > 0:
        return {'verdict': 'redirected', 'reason': f"{page['redirects']} redirect{'s' if page['redirects'] > 1 else ''} to {page.get('final_url') or 'another URL'}"}
    return {'verdict': 'indexable', 'reason': ''}


def fetch_cwv_pages(urls: List[str], api_key: str = '') -> Optional[Dict[str, Any]]:
    """PageSpeed for the homepage plus key pages; the homepage's numbers stay the headline, the rest go under `pages`."""
    results = []
    for u in urls[:5]:
        r = fetch_cwv(u, api_key)
        if r:
            results.append({'url': u, **r})
    if not results:
        return None
    head = dict(results[0])
    head.pop('url', None)
    head['pages'] = [{k: r.get(k) for k in ('url', 'lcp_ms', 'cls', 'inp_ms', 'lcp_ms_rating', 'cls_rating', 'inp_ms_rating', 'score', 'performance_score', 'mobile_friendly')}
                     for r in results]
    scores = [r['score'] for r in results if r.get('score') is not None]
    head['site_score'] = round(sum(scores) / len(scores)) if scores else head.get('score')
    return head


def sitemap_health(pages: List[Dict[str, Any]], sitemap_urls: List[str]) -> Dict[str, Any]:
    """Sitemap URLs that error, redirect or are noindexed; crawled pages the sitemap does not list."""
    listed = {norm_url(u) for u in (sitemap_urls or [])}
    if not listed:
        return {'listed': 0, 'checked': 0, 'errors': [], 'not_in_sitemap': []}
    errors = []
    not_listed = []
    checked = 0
    for p in pages:
        key = norm_url(p.get('url', ''))
        if key in listed:
            checked += 1
            status = p.get('status_code') or 0
            t = p.get('tech') or {}
            if status >= 400:
                errors.append({'url': p['url'], 'problem': f'HTTP {status}'})
            elif (p.get('redirects') or 0) > 0:
                errors.append({'url': p['url'], 'problem': 'redirects'})
            elif t.get('noindex'):
                errors.append({'url': p['url'], 'problem': 'noindex'})
        elif not p.get('parse_error'):
            not_listed.append(p['url'])
    return {'listed': len(listed), 'checked': checked, 'errors': errors[:50], 'not_in_sitemap': not_listed[:50]}


def hreflang_errors(pages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Invalid language codes and missing return tags, checked over the pages in the sample."""
    by_url = {norm_url(p['url']): (p.get('tech') or {}) for p in pages if not p.get('parse_error')}
    errors = []
    for key, t in by_url.items():
        for code in t.get('hreflang_invalid') or []:
            errors.append({'url': key, 'problem': f'invalid hreflang code "{code}"'})
        for code, target in t.get('hreflang_entries') or []:
            tkey = norm_url(target)
            if tkey == key or tkey not in by_url:
                continue
            back = {norm_url(h) for _, h in (by_url[tkey].get('hreflang_entries') or [])}
            if key not in back:
                errors.append({'url': key, 'problem': f'{_path(target)} ({code}) has no return tag'})
        if len(errors) >= 50:
            break
    return errors[:50]


def duplicate_groups(pages: List[Dict[str, Any]]) -> List[List[str]]:
    """Groups of pages whose body text is near-identical."""
    items = [(p['url'], (p.get('tech') or {}).get('shingles') or []) for p in pages if not p.get('parse_error')]
    items = [(u, s) for u, s in items if s]
    groups: List[List[str]] = []
    assigned = set()
    for i, (u, s) in enumerate(items):
        if u in assigned:
            continue
        group = [u]
        for v, s2 in items[i + 1:]:
            if v not in assigned and similarity(s, s2) >= DUPLICATE_SIMILARITY:
                group.append(v)
        if len(group) > 1:
            assigned.update(group)
            groups.append(group)
        if len(groups) >= 20:
            break
    return groups


def link_opportunities(pages: List[Dict[str, Any]], limit: int = 20) -> List[Dict[str, str]]:
    """Page A talks about page B's topic (B's title words appear in A) but never links to B."""
    ok = [p for p in pages if not p.get('parse_error') and p.get('tech')]
    out = []
    texts = {}
    for p in ok:
        t = p['tech']
        texts[p['url']] = ' '.join(t.get('title_words') or []) + ' ' + (p.get('title') or '').lower() + ' ' + (t.get('h1_text') or '').lower()
    for target in ok:
        words = target['tech'].get('title_words') or []
        if len(words) < 2:
            continue
        tkey = norm_url(target['url'])
        for source in ok:
            if source is target:
                continue
            links = set(source['tech'].get('internal_urls') or [])
            if tkey in links:
                continue
            # the source's own title/H1 shares at least two significant words with the target's title
            hits = [w for w in words if w in texts[source['url']]]
            if len(hits) >= 2:
                out.append({'from': source['url'], 'to': target['url'], 'topic': ' '.join(hits[:3])})
                if len(out) >= limit:
                    return out
    return out


def _share(n: int, of: int) -> Optional[int]:
    return round(100 * n / of) if of else None


def _priority(score: Optional[float]) -> str:
    if score is None:
        return 'not_measured'
    return 'on_track' if score >= 80 else 'important' if score >= 60 else 'critical'


def health_score(base: Dict[str, Any], tech: Dict[str, Any]) -> Dict[str, Any]:
    """Nine weighted categories → one 0-100 site score; unmeasured categories drop out."""
    n = base.get('pages_sampled') or 0
    bots_total = base.get('bots_total') or 1
    scores: Dict[str, Optional[float]] = {}
    detail: Dict[str, str] = {}

    bots = (base.get('bots_allowed') or 0) / bots_total
    noindex = (tech.get('noindex_pages') or 0) / n if n else 0
    scores['crawlability'] = 100 * (0.6 * bots + 0.2 * (1 if base.get('sitemap_present') else 0) + 0.2 * (1 - noindex))
    detail['crawlability'] = f"{base.get('bots_allowed')} of {bots_total} AI crawlers allowed · sitemap {'found' if base.get('sitemap_present') else 'missing'}"

    if n:
        from core.audit_crawl import RECOMMENDED_SCHEMA
        coverage = (base.get('schema_coverage') or 0) / 100
        variety = len(base.get('recommended_types_present') or []) / len(RECOMMENDED_SCHEMA)
        scores['schema'] = 100 * (0.6 * coverage + 0.4 * variety)
        detail['schema'] = f"schema on {base.get('schema_coverage')}% of pages · {len(base.get('recommended_types_present') or [])} of {len(RECOMMENDED_SCHEMA)} key types"

        words = min(1.0, (base.get('avg_word_count') or 0) / WORDS_TARGET)
        shape = max(base.get('question_heading_share') or 0, base.get('table_share') or 0) / 100
        h1_ok = 1 - ((tech.get('missing_h1') or 0) + (tech.get('multiple_h1') or 0)) / n
        scores['depth'] = 100 * (0.5 * words + 0.3 * shape + 0.2 * max(0.0, h1_ok))
        detail['depth'] = f"{base.get('avg_word_count')} words/page · question headings on {base.get('question_heading_share')}% · tables on {base.get('table_share')}%"

        author = (base.get('author_share') or 0) / 100
        cites = min(1.0, (base.get('avg_external_links') or 0) / CITATIONS_TARGET)
        person = (tech.get('person_schema_share') or 0) / 100
        cred = (tech.get('credential_share') or 0) / 100
        scores['eeat'] = 100 * (0.4 * author + 0.3 * cites + 0.15 * person + 0.15 * cred)
        detail['eeat'] = f"bylines on {base.get('author_share')}% · {base.get('avg_external_links')} citations/page · Person schema on {tech.get('person_schema_share')}% · credentials on {tech.get('credential_share')}%"

        links = min(1.0, (tech.get('avg_internal_links') or 0) / INTERNAL_LINK_TARGET)
        anchors = (tech.get('descriptive_anchor_share') or 0) / 100
        orphan = (tech.get('orphan_pages') or 0) / n
        scores['internal_linking'] = 100 * (0.6 * links + 0.25 * anchors + 0.15 * (1 - orphan))
        detail['internal_linking'] = f"{tech.get('avg_internal_links')} internal links/page · {tech.get('descriptive_anchor_share')}% descriptive anchors · {tech.get('orphan_pages')} orphan candidates"

        issues = ((tech.get('missing_title') or 0) + (tech.get('missing_description') or 0) + (tech.get('canonical_missing') or 0)
                  + (tech.get('mixed_content_pages') or 0) + (tech.get('http_pages') or 0) + (tech.get('error_pages') or 0)
                  + (tech.get('redirect_chains') or 0) + (tech.get('json_ld_invalid') or 0)
                  + 0.5 * ((tech.get('duplicate_titles') or 0) + (tech.get('missing_viewport') or 0) + (tech.get('thin_pages') or 0)
                           + len([u for g in (tech.get('duplicate_groups') or []) for u in g])))
        if (tech.get('site') or {}).get('http_redirects_to_https') is False:
            issues += 2
        issues += (tech.get('soft_404_pages') or 0)
        cert_days = ((tech.get('site') or {}).get('certificate') or {}).get('days_left')
        if cert_days is not None and cert_days < 14:
            issues += 2
        alt = 1 - ((tech.get('images_missing_alt_share') or 0) / 100)
        lc = tech.get('link_check') or {}
        broken = (lc.get('broken') or 0) / lc['checked'] if lc.get('checked') else 0
        scores['technical'] = 100 * (0.6 * max(0.0, 1 - issues / n) + 0.2 * alt + 0.2 * (1 - broken))
        detail['technical'] = f"{tech.get('missing_title', 0)} missing titles · {tech.get('missing_description', 0)} missing descriptions · {tech.get('canonical_missing', 0)} without canonical · {lc.get('broken', 0)} of {lc.get('checked', 0)} links broken"

        dated, stale = base.get('dated_pages') or 0, base.get('stale_pages') or 0
        scores['freshness'] = 100 * (1 - stale / dated) if dated else None
        detail['freshness'] = f"{stale} of {dated} dated pages older than 12 months" if dated else 'no publish/update dates found'
    bl = tech.get('backlinks') or {}
    scores['backlinks'] = bl.get('score')
    detail['backlinks'] = (f"authority {bl.get('authority_score') if bl.get('authority_score') is not None else '—'}/100 · "
                           f"{bl.get('referring_domains', 0):,} referring domains · {bl.get('backlinks', 0):,} backlinks"
                           if bl else 'not measured (needs the DataForSEO backlinks check)')
    cwv = tech.get('cwv') or {}
    scores['cwv'] = cwv.get('score')
    detail['cwv'] = (f"LCP {cwv.get('lcp_ms')} ms · CLS {cwv.get('cls')} · INP {cwv.get('inp_ms')} ms ({cwv.get('source')} data)"
                     if cwv else 'not measured (needs the free PageSpeed API key)')

    cats = []
    total_w = sum(w for k, _, w in HEALTH_CATEGORIES if scores.get(k) is not None)
    acc = 0.0
    for key, label, weight in HEALTH_CATEGORIES:
        s = scores.get(key)
        s = round(max(0, min(100, s))) if s is not None else None
        if s is not None and total_w:
            acc += s * weight / total_w
        cats.append({'key': key, 'label': label, 'weight': weight, 'score': s, 'priority': _priority(s), 'detail': detail.get(key, '')})
    return {'score': round(acc) if total_w else None, 'categories': cats}


def technical_issues(ok: List[Dict[str, Any]], tech: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The issue list: what is wrong, on how many sampled pages, examples, and the fix."""
    n = len(ok)
    issues = []

    def add(key, label, severity, pages, fix, action, of=None, urls=None):
        pages = list(pages)
        count = len(pages)
        if count == 0:
            return
        issues.append({'key': key, 'label': label, 'severity': severity, 'count': count, 'of': of if of is not None else n,
                       'examples': [_path(p.get('url', '')) for p in pages[:5]], 'fix': fix, 'action': action,
                       'urls': (urls if urls is not None else [p.get('url', '') for p in pages])[:100]})

    t = lambda p: p.get('tech') or {}  # noqa: E731
    wt = [p for p in ok if p.get('tech')]  # tech-based checks only judge pages the parser reached
    site = tech.get('site') or {}
    if site.get('http_redirects_to_https') is False:
        issues.append({'key': 'http_no_redirect', 'label': 'http:// does not redirect to https://', 'severity': 'critical', 'count': 1, 'of': 1,
                       'examples': ['/'], 'urls': [], 'fix': 'Both versions of the site are reachable, so engines see two copies and users can land on the insecure one.',
                       'action': 'Redirect every http:// URL to https://'})
    if site.get('ssl_error'):
        issues.append({'key': 'ssl_error', 'label': 'SSL certificate problem', 'severity': 'critical', 'count': 1, 'of': 1, 'examples': ['/'], 'urls': [],
                       'fix': 'A page failed the TLS handshake (expired or mismatched certificate); browsers show a warning and crawlers stop.',
                       'action': 'Renew or fix the SSL certificate'})
    add('robots_blocked', 'Pages blocked by robots.txt', 'critical', [p for p in ok if (p.get('index') or {}).get('reason') == 'blocked by robots.txt'],
        'Crawlers are told not to fetch these pages, so nothing on them can rank or be cited.', 'Unblock the pages in robots.txt')
    add('x_robots_noindex', 'Pages with X-Robots-Tag: noindex', 'critical', [p for p in ok if 'noindex' in (p.get('x_robots') or '').lower()],
        'The server header hides the page from every index, the same as a noindex meta tag.', 'Remove the X-Robots-Tag noindex header')
    add('noindex', 'Pages carrying noindex', 'critical', [p for p in wt if t(p).get('noindex')],
        'A noindex page is invisible to Google and to every AI crawler; remove it unless the page is meant to be hidden.', 'Remove noindex from pages that should rank')
    add('error_pages', 'Sampled pages returning errors', 'critical', [p for p in ok if (p.get('status_code') or 200) >= 400],
        'URLs in the sitemap or navigation that return 4xx/5xx waste crawl budget and break trust.', 'Fix or remove the URLs that return errors')
    add('missing_title', 'Pages without a <title>', 'critical', [p for p in wt if not t(p).get('title_length')],
        'The title is the first thing every engine reads; without it the page cannot be matched to a query.', 'Write a unique title for every page')
    add('http_pages', 'Pages served over HTTP', 'critical', [p for p in wt if t(p) and not t(p).get('https')],
        'Engines and browsers mark HTTP pages as not secure; move everything to HTTPS with a redirect.', 'Serve every page over HTTPS')
    add('mixed_content', 'HTTPS pages loading HTTP assets', 'critical', [p for p in wt if t(p).get('mixed_content')],
        'Mixed content is blocked by browsers and flagged by crawlers; load scripts, images and styles over HTTPS.', 'Fix mixed content on HTTPS pages')
    add('missing_description', 'Pages without a meta description', 'warning', [p for p in wt if t(p) and not t(p).get('description_length')],
        'Engines fall back to whatever text they find; a description is the summary you control.', 'Add a meta description to every page')
    titles = Counter((p.get('title') or '').strip().lower() for p in wt if (p.get('title') or '').strip())
    add('duplicate_titles', 'Pages sharing a title', 'warning', [p for p in wt if titles[(p.get('title') or '').strip().lower()] > 1],
        'Duplicate titles make pages compete with each other and look like duplicates to crawlers.', 'Make every page title unique')
    descs = Counter((t(p).get('meta_description') or '').strip().lower() for p in wt if (t(p).get('meta_description') or '').strip())
    add('duplicate_descriptions', 'Pages sharing a meta description', 'warning', [p for p in ok if descs[(t(p).get('meta_description') or '').strip().lower()] > 1],
        'A description that repeats across pages is ignored; write one per page.', 'Make meta descriptions unique')
    add('missing_h1', 'Pages without an H1', 'warning', [p for p in wt if t(p) and t(p).get('h1_count') == 0],
        'The H1 tells engines what the page is about; every page needs exactly one.', 'Add a single H1 to every page')
    add('multiple_h1', 'Pages with more than one H1', 'warning', [p for p in wt if (t(p).get('h1_count') or 0) > 1],
        'Several H1s dilute the page topic; keep one and demote the rest to H2.', 'Keep one H1 per page')
    add('canonical_missing', 'Pages without a canonical tag', 'warning', [p for p in wt if t(p).get('canonical_status') == 'missing'],
        'Without a canonical, tracking parameters and duplicates split the page\'s authority.', 'Add a self-referencing canonical to every page')
    add('canonical_mismatch', 'Pages whose canonical points elsewhere', 'info', [p for p in wt if t(p).get('canonical_status') == 'mismatch'],
        'The page tells engines to index a different URL; correct for duplicates, a mistake otherwise.', 'Check canonical tags that point to another URL')
    add('missing_viewport', 'Pages without a mobile viewport', 'warning', [p for p in wt if t(p) and not t(p).get('viewport')],
        'Google indexes the mobile version first; a page with no viewport tag fails mobile-friendliness.', 'Add the viewport meta tag')
    alt_pages = [p for p in wt if (t(p).get('images') or 0) >= 3 and (t(p).get('images_missing_alt') or 0) / max(1, t(p).get('images') or 1) > 0.2]
    add('images_missing_alt', 'Pages where 20%+ of images lack alt text', 'warning', alt_pages,
        'Alt text is how crawlers and AI engines read images; missing alt is also an accessibility failure.', 'Add alt text to images')
    add('redirected', 'Sampled URLs that redirect', 'info', [p for p in ok if (p.get('redirects') or 0) == 1],
        'Sitemap and navigation links should point at the final URL; each redirect costs crawl budget.', 'Update links and sitemap to final URLs')
    add('redirect_chains', 'Redirect chains (2+ hops)', 'warning', [p for p in ok if (p.get('redirects') or 0) >= 2],
        'Every extra hop slows users and crawlers and leaks link authority; point the first URL straight at the last.', 'Collapse redirect chains to a single hop')
    add('title_length', 'Titles too short or too long', 'info', [p for p in wt if t(p).get('title_issue')],
        f'Titles under {TITLE_RANGE[0]} characters waste the space; over {TITLE_RANGE[1]} get cut off in results.', 'Rewrite titles to 30-60 characters')
    add('description_length', 'Meta descriptions too short or too long', 'info', [p for p in wt if t(p).get('description_issue')],
        f'Descriptions under {DESC_RANGE[0]} characters say too little; over {DESC_RANGE[1]} are truncated.', 'Rewrite descriptions to 70-160 characters')
    add('title_equals_h1', 'Title identical to H1', 'info', [p for p in wt if t(p).get('title_equals_h1')],
        'The title tag and the H1 can carry different phrasings of the topic; identical copies waste one of them.', 'Vary the title and H1 wording')
    add('heading_structure', 'Heading structure problems', 'info', [p for p in wt if t(p).get('heading_issues')],
        'Skipped levels (H1 → H3) and empty headings confuse the outline engines extract.', 'Fix heading levels and remove empty headings')
    add('images_dimensions', 'Images without width/height', 'warning', [p for p in wt if (t(p).get('images') or 0) >= 3 and (t(p).get('images_missing_dimensions') or 0) / max(1, t(p).get('images') or 1) > 0.5],
        'Images without dimensions cause layout shift (CLS) while they load.', 'Add width and height attributes to images')
    add('og_incomplete', 'Missing Open Graph tags', 'info', [p for p in wt if t(p) and t(p).get('og_missing')],
        'og:title, og:description and og:image control how the page looks when shared and in some AI answer cards.', 'Add the three core Open Graph tags')
    add('invalid_json_ld', 'Invalid JSON-LD blocks', 'warning', [p for p in wt if t(p).get('json_ld_invalid')],
        'A JSON-LD block that does not parse is ignored entirely - the schema might as well not be there.', 'Fix the JSON syntax of the structured data')
    add('rich_result_blockers', 'Schema missing rich-result fields', 'warning', [p for p in wt if t(p).get('rich_result_blockers')],
        'The type is present but lacks a field Google requires, so the rich result will not show.', 'Add the required schema fields')
    add('thin_content', 'Thin content pages', 'warning', [p for p in wt if t(p).get('thin')],
        f'Content pages under {THIN_WORDS} words rarely rank or get cited.', 'Expand or merge thin pages')
    add('param_urls', 'Parameter URLs without a canonical', 'warning', [p for p in wt if t(p).get('has_params') and t(p).get('canonical_status') != 'ok'],
        'Sorted, filtered and paginated URLs create duplicates unless they canonicalise to the clean URL.', 'Canonicalise parameter URLs')
    dup = tech.get('duplicate_groups') or []
    if dup:
        flat = [u for g in dup for u in g]
        issues.append({'key': 'duplicate_content', 'label': 'Near-duplicate pages', 'severity': 'warning', 'count': len(flat), 'of': n,
                       'examples': [_path(u) for u in flat[:5]], 'urls': flat[:100],
                       'fix': 'Pages with the same body text compete with each other; keep one and canonicalise or merge the rest.',
                       'action': 'Merge or canonicalise duplicate pages'})
    sm = tech.get('sitemap_health') or {}
    if sm.get('errors'):
        issues.append({'key': 'sitemap_errors', 'label': 'Sitemap URLs that error, redirect or are noindexed', 'severity': 'warning', 'count': len(sm['errors']),
                       'of': sm.get('checked', 0), 'examples': [f"{_path(e['url'])} ({e['problem']})" for e in sm['errors'][:5]], 'urls': [e['url'] for e in sm['errors']][:100],
                       'fix': 'A sitemap should list only live, indexable, final URLs; anything else wastes crawl budget and trust.', 'action': 'Clean the sitemap'})
    if sm.get('not_in_sitemap'):
        issues.append({'key': 'not_in_sitemap', 'label': 'Crawled pages missing from the sitemap', 'severity': 'info', 'count': len(sm['not_in_sitemap']), 'of': n,
                       'examples': [_path(u) for u in sm['not_in_sitemap'][:5]], 'urls': sm['not_in_sitemap'][:100],
                       'fix': 'Pages reachable by links but absent from the sitemap are discovered late.', 'action': 'Add the missing pages to the sitemap'})
    hl = tech.get('hreflang_errors') or []
    if hl:
        issues.append({'key': 'hreflang_errors', 'label': 'hreflang errors', 'severity': 'warning', 'count': len(hl), 'of': tech.get('hreflang_pages', 0),
                       'examples': [f"{_path(e['url'])}: {e['problem']}" for e in hl[:5]], 'urls': [e['url'] for e in hl][:100],
                       'fix': 'Invalid codes or missing return tags make engines ignore the whole hreflang set.', 'action': 'Fix hreflang codes and return tags'})
    cert = (site or {}).get('certificate') or {}
    if cert.get('days_left') is not None and cert['days_left'] < CERT_WARN_DAYS:
        issues.append({'key': 'cert_expiring', 'label': f"SSL certificate expires in {cert['days_left']} days" if cert['days_left'] >= 0 else 'SSL certificate has expired',
                       'severity': 'critical' if cert['days_left'] < 14 else 'warning', 'count': 1, 'of': 1, 'examples': [f"expires {cert.get('expires')}"], 'urls': [],
                       'fix': 'When the certificate lapses every visitor and crawler gets a security warning instead of the site.', 'action': 'Renew the SSL certificate'})
    missing_headers = [SECURITY_HEADERS[h] for h, present in ((site or {}).get('security_headers') or {}).items() if h in SECURITY_HEADERS and not present]
    if missing_headers and any(t(p).get('https') for p in ok):
        issues.append({'key': 'security_headers', 'label': 'Missing security headers', 'severity': 'info', 'count': len(missing_headers), 'of': len(SECURITY_HEADERS),
                       'examples': missing_headers, 'urls': [],
                       'fix': 'These headers stop clickjacking, MIME sniffing and referrer leaks; scanners and some buyers check for them.', 'action': 'Send the standard security headers'})
    add('soft_404', 'Soft 404s (page says "not found" but returns 200)', 'critical', [p for p in wt if t(p).get('soft_404')],
        'The server tells crawlers the page exists, so the "not found" page gets indexed and wastes crawl budget.', 'Return a real 404 status for missing pages')
    add('meta_refresh', 'Meta-refresh redirects', 'warning', [p for p in wt if t(p).get('meta_refresh')],
        'A meta refresh is a slow client-side redirect that passes little authority; crawlers treat it as a weak signal.', 'Replace meta refresh with a server 301')
    add('html_heavy', f'HTML over {HTML_HEAVY_BYTES // 1000} KB', 'warning', [p for p in ok if (p.get('html_bytes') or 0) > HTML_HEAVY_BYTES],
        'A huge HTML document slows first paint and crawling before a single image loads.', 'Slim the HTML')
    add('script_heavy', f'{SCRIPTS_MANY}+ script tags on a page', 'info', [p for p in wt if (t(p).get('scripts') or 0) >= SCRIPTS_MANY],
        'Every script is a request and main-thread work; script-heavy pages fail INP and get crawled less.', 'Reduce the number of scripts')
    add('legacy_image_formats', 'Pages where most images are JPG/PNG without WebP or srcset', 'info',
        [p for p in wt if (t(p).get('images') or 0) >= 3 and (t(p).get('images_legacy') or 0) / max(1, t(p).get('images') or 1) > 0.6],
        'Modern formats are 30-50% smaller; srcset lets phones download smaller copies.', 'Serve WebP/AVIF with srcset')
    add('lang_missing', 'Pages without <html lang>', 'info', [p for p in wt if t(p) and not t(p).get('lang')],
        'The lang attribute tells engines and screen readers which language the page is in.', 'Add lang to the <html> tag')
    if wt and not any(t(p).get('favicon') for p in wt[:3]):
        issues.append({'key': 'no_favicon', 'label': 'No favicon declared', 'severity': 'info', 'count': 1, 'of': 1, 'examples': ['/'], 'urls': [],
                       'fix': 'Google shows the favicon next to results and AI answer cards; without it the site looks unfinished.', 'action': 'Add a favicon link'})
    if site and site.get('hsts') is False and any(t(p).get('https') for p in ok):
        issues.append({'key': 'hsts_missing', 'label': 'No HSTS header', 'severity': 'info', 'count': 1, 'of': 1, 'examples': ['/'], 'urls': [],
                       'fix': 'Strict-Transport-Security tells browsers to always use HTTPS; a small trust and speed win.', 'action': 'Send a Strict-Transport-Security header'})
    add('schema_gaps', 'Schema blocks missing key fields', 'info', [p for p in wt if t(p).get('schema_gaps')],
        'Schema is present but thin - engines cannot use an Organization without a description or an Article without an author.', 'Complete the required schema fields')
    lc = tech.get('link_check') or {}
    if lc.get('broken'):
        issues.append({'key': 'broken_links', 'label': 'Broken internal links', 'severity': 'critical', 'count': lc['broken'], 'of': lc.get('checked', 0),
                       'examples': [f"{_short(e['url'])} ({e['status'] or 'unreachable'})" for e in lc.get('examples', [])[:5]],
                       'urls': [e['url'] for e in lc.get('examples', [])][:100],
                       'fix': 'Links to pages that return errors send crawlers and buyers to dead ends.', 'action': 'Fix the broken internal links'})
    if lc.get('external_broken'):
        issues.append({'key': 'broken_external_links', 'label': 'Broken outbound links', 'severity': 'warning', 'count': lc['external_broken'], 'of': lc.get('external_checked', 0),
                       'examples': [f"{_short(e['url'])} ({e['status'] or 'unreachable'})" for e in lc.get('external_examples', [])[:5]],
                       'urls': [e['url'] for e in lc.get('external_examples', [])][:100],
                       'fix': 'Citing a dead source hurts the trust signal a citation is meant to give.', 'action': 'Replace or remove dead outbound links'})
    if tech.get('orphan_examples'):
        issues.append({'key': 'orphans', 'label': 'Pages no sampled page links to', 'severity': 'info', 'count': tech.get('orphan_pages', 0), 'of': n,
                       'examples': [_path(u) for u in tech['orphan_examples'][:5]], 'urls': list(tech['orphan_examples'])[:100],
                       'fix': 'Pages reached only from the sitemap get less crawl attention and no internal authority.', 'action': 'Link orphan pages from related content'})
    for i in issues:
        i['snippet'] = FIX_SNIPPETS.get(i['key'], '')
    order = {'critical': 0, 'warning': 1, 'info': 2}
    issues.sort(key=lambda i: (order.get(i['severity'], 3), -i['count']))
    return issues


def content_patterns(base: Dict[str, Any], tech: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The three page shapes AI engines cite most, and whether the sample shows them."""
    q = base.get('question_heading_share') or 0
    cites = base.get('avg_external_links') or 0
    tables = base.get('table_share') or 0

    def status(v, full, partial):
        return 'present' if v >= full else 'partial' if v >= partial else 'missing'
    return [
        {'key': 'answer_blocks', 'title': 'Question headings with a short answer block',
         'status': status(q, 50, 20), 'evidence': f"question-shaped headings on {q}% of sampled pages",
         'advice': 'Open each section with the question buyers ask, then answer it in 1-3 sentences before the detail; engines lift these blocks verbatim.'},
        {'key': 'front_loaded_facts', 'title': 'Statistics and cited sources in the opening paragraphs',
         'status': status(cites, CITATIONS_TARGET, 2), 'evidence': f"{cites} outbound citations per page on average (target {CITATIONS_TARGET})",
         'advice': 'Put a number and its source in the first 500 words ("According to X, 41% of ..."); front-loaded facts are what crawlers extract first.'},
        {'key': 'comparison_tables', 'title': 'Comparison tables and feature matrices',
         'status': status(tables, 40, 15), 'evidence': f"tables on {tables}% of sampled pages",
         'advice': 'Tables that compare you with rivals or with the old way of doing things are the most extractable content on the web.'},
    ]


def technical_summary(pages: List[Dict[str, Any]], base: Dict[str, Any], *, website: str = '', sitemap_children: int = 0,
                      link_check: Optional[Dict[str, Any]] = None, cwv: Optional[Dict[str, Any]] = None,
                      backlinks: Optional[Dict[str, Any]] = None, sitemap_urls: Optional[List[str]] = None,
                      site: Optional[Dict[str, Any]] = None, robots: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Site-level technical numbers + issues + health score, merged into the crawl summary."""
    ok = [p for p in pages if not p.get('parse_error')]
    n = len(ok)
    t = lambda p: p.get('tech') or {}  # noqa: E731
    with_tech = [p for p in ok if p.get('tech')]
    m = len(with_tech)
    out: Dict[str, Any] = {'sitemap_children': int(sitemap_children or 0), 'link_check': link_check, 'cwv': cwv, 'backlinks': backlinks,
                           'site': site or {}}
    # Indexability verdict for every fetched page (failed fetches included - a 404 in the sitemap is a finding).
    verdicts = Counter()
    for p in pages:
        if p.get('url'):
            p['index'] = indexability(p, robots)
            verdicts[p['index']['verdict']] += 1
    out['indexability'] = {k: verdicts.get(k, 0) for k in ('indexable', 'not_indexable', 'canonicalised', 'redirected', 'unknown')}
    if not m:
        out.update({'technical_issues': technical_issues(ok, out), 'health': health_score(base, out), 'content_patterns': content_patterns(base, out)})
        return out

    anchors = sum(t(p).get('internal_anchors') or 0 for p in with_tech)
    generic = sum(t(p).get('generic_anchors') or 0 for p in with_tech)
    out['avg_internal_links'] = round(sum(t(p).get('internal_links') or 0 for p in with_tech) / m, 1)
    out['descriptive_anchor_share'] = round(100 * (anchors - generic) / anchors) if anchors else None
    out['missing_title'] = sum(1 for p in with_tech if not t(p).get('title_length'))
    titles = Counter((p.get('title') or '').strip().lower() for p in ok if (p.get('title') or '').strip())
    out['duplicate_titles'] = sum(1 for p in ok if titles[(p.get('title') or '').strip().lower()] > 1)
    out['title_length_issues'] = sum(1 for p in with_tech if t(p).get('title_length') and not (TITLE_RANGE[0] <= t(p)['title_length'] <= TITLE_RANGE[1]))
    out['missing_description'] = sum(1 for p in with_tech if not t(p).get('description_length'))
    descs = Counter((t(p).get('meta_description') or '').strip().lower() for p in with_tech if (t(p).get('meta_description') or '').strip())
    out['duplicate_descriptions'] = sum(1 for p in with_tech if descs[(t(p).get('meta_description') or '').strip().lower()] > 1)
    out['description_length_issues'] = sum(1 for p in with_tech if t(p).get('description_length') and not (DESC_RANGE[0] <= t(p)['description_length'] <= DESC_RANGE[1]))
    out['missing_h1'] = sum(1 for p in with_tech if t(p).get('h1_count') == 0)
    out['multiple_h1'] = sum(1 for p in with_tech if (t(p).get('h1_count') or 0) > 1)
    out['noindex_pages'] = sum(1 for p in with_tech if t(p).get('noindex'))
    out['canonical_missing'] = sum(1 for p in with_tech if t(p).get('canonical_status') == 'missing')
    out['canonical_mismatch'] = sum(1 for p in with_tech if t(p).get('canonical_status') == 'mismatch')
    out['missing_viewport'] = sum(1 for p in with_tech if not t(p).get('viewport'))
    images = sum(t(p).get('images') or 0 for p in with_tech)
    missing_alt = sum(t(p).get('images_missing_alt') or 0 for p in with_tech)
    out['images_total'] = images
    out['images_missing_alt'] = missing_alt
    out['images_missing_alt_share'] = _share(missing_alt, images)
    out['mixed_content_pages'] = sum(1 for p in with_tech if t(p).get('mixed_content'))
    out['http_pages'] = sum(1 for p in with_tech if not t(p).get('https'))
    out['redirected_pages'] = sum(1 for p in ok if (p.get('redirects') or 0) > 0)
    out['error_pages'] = sum(1 for p in ok if (p.get('status_code') or 200) >= 400)
    out['hreflang_pages'] = sum(1 for p in with_tech if t(p).get('hreflang'))
    out['og_share'] = _share(sum(1 for p in with_tech if t(p).get('og')), m)
    gaps = Counter(g for p in with_tech for g in (t(p).get('schema_gaps') or []))
    out['schema_gaps'] = [{'gap': g, 'pages': c} for g, c in gaps.most_common(6)]
    out['person_schema_share'] = _share(sum(1 for p in with_tech if t(p).get('has_person_schema')), m)
    out['credential_share'] = _share(sum(1 for p in with_tech if t(p).get('credential_mentions')), m)

    graph = link_graph(pages, website or (ok[0].get('url') if ok else ''))
    depth = graph['depth']
    for p in ok:
        d = depth.get(norm_url(p['url']))
        p['depth'] = d
    out['orphan_pages'] = len(graph['orphans'])
    out['orphan_examples'] = graph['orphans'][:8]
    out['unreached_pages'] = len(graph['unreached'])
    out['max_depth'] = max(depth.values()) if depth else None
    out['deep_pages'] = sum(1 for d in depth.values() if d >= 4)
    # Tier-2 checks
    out['title_equals_h1'] = sum(1 for p in with_tech if t(p).get('title_equals_h1'))
    out['heading_issue_pages'] = sum(1 for p in with_tech if t(p).get('heading_issues'))
    out['thin_pages'] = sum(1 for p in with_tech if t(p).get('thin'))
    out['redirect_chains'] = sum(1 for p in ok if (p.get('redirects') or 0) >= 2)
    out['json_ld_invalid'] = sum(t(p).get('json_ld_invalid') or 0 for p in with_tech)
    out['rich_result_blockers'] = [{'blocker': b, 'pages': c} for b, c in Counter(b for p in with_tech for b in (t(p).get('rich_result_blockers') or [])).most_common(6)]
    out['og_complete_share'] = _share(sum(1 for p in with_tech if not t(p).get('og_missing')), m)
    out['images_missing_dimensions_share'] = _share(sum(t(p).get('images_missing_dimensions') or 0 for p in with_tech), images)
    out['images_lazy_share'] = _share(sum(t(p).get('images_lazy') or 0 for p in with_tech), images)
    out['param_link_pages'] = sum(1 for p in with_tech if t(p).get('param_links'))
    out['duplicate_groups'] = duplicate_groups(pages)
    out['sitemap_health'] = sitemap_health(pages, sitemap_urls or [])
    out['hreflang_errors'] = hreflang_errors(pages) if out['hreflang_pages'] else []
    out['link_opportunities'] = link_opportunities(pages)
    out['soft_404_pages'] = sum(1 for p in with_tech if t(p).get('soft_404'))
    out['avg_html_kb'] = round(sum(p.get('html_bytes') or 0 for p in ok) / n / 1000, 1) if n else None
    out['avg_scripts'] = round(sum(t(p).get('scripts') or 0 for p in with_tech) / m, 1)
    out['lang_missing_pages'] = sum(1 for p in with_tech if not t(p).get('lang'))
    out['images_legacy_share'] = _share(sum(t(p).get('images_legacy') or 0 for p in with_tech), images)

    out['technical_issues'] = technical_issues(ok, out)
    out['health'] = health_score(base, out)
    out['content_patterns'] = content_patterns(base, out)
    return out
