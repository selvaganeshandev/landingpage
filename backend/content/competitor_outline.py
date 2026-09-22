"""Shape a landing-page outline from the pages that already rank for the keyword.

The outline used to be written from the title and keywords alone, which is what
the client's feedback was about — "neither qualitatively good nor quantitatively
[sufficient]" — asking instead that it "refer to top-ranking competitors and
create a comprehensive outline for a landing or product page".

Both halves of that already existed separately and had never been joined up:

  * every tracked keyword stores its SERP in ``SeoKeywordRank.snippets_details``
    as ``{"competitors": {"1": {url, rank, title, domain}, ...}}``
  * pages are scraped through DataBlue by the site health check

So this reads the ranked URLs, fetches them, pulls out their heading structure,
and hands the outline prompt a summary of what the winning pages actually cover.

EVERY failure path returns an empty string. No SERP stored, no DataBlue key, a
scrape that times out, a page with no headings, an unexpected payload shape — all
of them mean "no competitor brief", and the outline is generated exactly as it
was before. This is additive by construction: it can make an outline better and
cannot stop one being produced.

Bounded on purpose. Outline generation is interactive, so the scrape runs
concurrently against a single wall-clock deadline rather than page by page;
whatever has arrived when the deadline passes is what gets used. That is the
same shape as the health check's ``_remaining(cap)`` budget, and for the same
reason: five sequential 60-second fetches would turn a 20-second outline into a
five-minute one.
"""

from __future__ import annotations

import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.conf import settings

logger = logging.getLogger(__name__)

# Off switches and budgets, all overridable per environment.
def _enabled():
    try:
        return bool(getattr(settings, 'CONTENT_COMPETITOR_OUTLINE_ENABLED', True))
    except Exception:  # noqa: BLE001 - settings access must never break generation
        return True


def _max_pages():
    try:
        return max(1, int(getattr(settings, 'CONTENT_COMPETITOR_MAX_PAGES', 5)))
    except Exception:  # noqa: BLE001
        return 5


def _deadline_seconds():
    try:
        return max(5, int(getattr(settings, 'CONTENT_COMPETITOR_DEADLINE', 45)))
    except Exception:  # noqa: BLE001
        return 45


# Headings carry a page's structure, which is the thing being borrowed — not its
# prose. Matched with a regex rather than a parser because the input is a full
# raw document from an arbitrary site: BeautifulSoup would be a new dependency
# in this path and no more reliable against the markup real pages ship.
_HEADING_RE = re.compile(
    r'<(h[1-3])\b[^>]*>(.*?)</\1>', re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r'<[^>]+>')
_WS_RE = re.compile(r'\s+')

# Boilerplate that appears on nearly every page and says nothing about how the
# topic is covered. Dropped so the brief is signal rather than chrome.
_BOILERPLATE = {
    'menu', 'search', 'navigation', 'footer', 'header', 'share', 'follow us',
    'newsletter', 'subscribe', 'related posts', 'related articles', 'comments',
    'leave a reply', 'categories', 'tags', 'archives', 'recent posts',
    'sign up', 'log in', 'login', 'contact us', 'about us', 'quick links',
    'you may also like', 'popular posts', 'cookie', 'privacy policy',
    # Accessibility skip links. Real sites mark these up as headings, and they
    # showed up as an <h2> on a live scrape of icici.bank.in.
    'skip to main content', 'skip to content', 'skip navigation',
    'main content', 'breadcrumb', 'breadcrumbs', 'table of contents',
}


def _clean_heading(raw_html):
    """A heading's visible text, or '' if there is nothing usable in it."""
    text = _WS_RE.sub(' ', _TAG_RE.sub(' ', raw_html or '')).strip()
    # Entities are common in headings ("Men&#039;s"); decode the few that matter
    # rather than pulling in a parser for it.
    for entity, char in (('&amp;', '&'), ('&#039;', "'"), ('&quot;', '"'),
                         ('&nbsp;', ' '), ('&#8217;', "'"), ('&rsquo;', "'")):
        text = text.replace(entity, char)
    text = _WS_RE.sub(' ', text).strip()
    if len(text) < 3 or len(text) > 120:
        return ''
    if text.lower() in _BOILERPLATE:
        return ''
    return text


def extract_headings(html, limit=18):
    """Heading structure of a page, in document order, as (level, text).

    Returns [] for anything unusable, which is what the callers treat as "this
    page contributed nothing".
    """
    out = []
    seen = set()
    try:
        for match in _HEADING_RE.finditer(html or ''):
            level = match.group(1).lower()
            text = _clean_heading(match.group(2))
            if not text:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append((level, text))
            if len(out) >= limit:
                break
    except Exception as exc:  # noqa: BLE001 - a hostile page must not break this
        logger.warning("[CompetitorOutline] heading extraction failed: %s", exc)
        return []
    return out


def top_competitor_urls(domain_id, keywords, limit=5):
    """Ranked competitor pages for the FIRST keyword, best rank first.

    `keywords` arrives from the form as a comma-separated string; the first is
    the primary one and the only one whose SERP is worth borrowing. Matching is
    case-insensitive and falls back to a contains match, because what a writer
    types into the content form rarely matches a tracked keyword character for
    character.
    """
    primary = (keywords or '').split(',')[0].strip()
    if not primary or not domain_id:
        return []
    try:
        from seo_rankings.models import SeoKeywordRank

        qs = SeoKeywordRank.objects.filter(domain_id=domain_id).select_related('keyword')
        row = (qs.filter(keyword__keyword__iexact=primary).first()
               or qs.filter(keyword__keyword__icontains=primary).first())
        if row is None:
            logger.info("[CompetitorOutline] no tracked keyword matching %r", primary[:60])
            return []

        blob = row.snippets_details or {}
        competitors = blob.get('competitors') if isinstance(blob, dict) else None
        if not isinstance(competitors, dict):
            return []

        rows = []
        for value in competitors.values():
            if not isinstance(value, dict):
                continue
            url = (value.get('url') or '').strip()
            if not url.startswith(('http://', 'https://')):
                continue
            rows.append({
                'rank': value.get('rank') or 999,
                'url': url,
                'title': (value.get('title') or '').strip(),
                'domain': (value.get('domain') or '').strip(),
            })
        rows.sort(key=lambda r: r['rank'])
        return rows[:limit]
    except Exception as exc:  # noqa: BLE001 - never break outline generation
        logger.warning("[CompetitorOutline] competitor lookup failed: %s", exc)
        return []


def _scrape(url):
    """Raw HTML for one competitor page, or None.

    Imported lazily: domains.views is a large module and importing it at load
    time would pull it into every content request, not just this one.
    """
    try:
        from domains.views import _fetch_page_html_via_datablue
        return _fetch_page_html_via_datablue(url)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[CompetitorOutline] scrape failed for %s: %s", url, exc)
        return None


def gather_competitor_structures(competitors, deadline_seconds=None):
    """Scrape the given pages concurrently and return those that yielded headings.

    Runs against ONE wall-clock deadline rather than a per-page timeout, so the
    worst case is the deadline and not the sum of the fetches. Pages that have
    not arrived by then are dropped, because a slower outline helps nobody.
    """
    if not competitors:
        return []
    budget = deadline_seconds or _deadline_seconds()
    started = time.monotonic()
    results = []

    with ThreadPoolExecutor(max_workers=min(len(competitors), 5),
                            thread_name_prefix='comp-outline') as pool:
        futures = {pool.submit(_scrape, c['url']): c for c in competitors}
        for future in as_completed(futures, timeout=budget):
            comp = futures[future]
            try:
                html = future.result()
            except Exception:  # noqa: BLE001 - one bad page must not stop the rest
                continue
            if not html:
                continue
            headings = extract_headings(html)
            if headings:
                results.append({**comp, 'headings': headings})
            if time.monotonic() - started > budget:
                break

    results.sort(key=lambda r: r['rank'])
    logger.info("[CompetitorOutline] %d/%d competitor pages usable in %.1fs",
                len(results), len(competitors), time.monotonic() - started)
    return results


def format_competitor_brief(structures):
    """Render scraped structures as a prompt block, or '' when there is nothing.

    Deliberately shows each page's OWN structure rather than a merged list. A
    merged list reads as a template to copy; seeing that four of five pages open
    with a buying-criteria section, and how each frames it, is what lets the
    model judge what genuinely belongs.
    """
    if not structures:
        return ''
    lines = [
        "",
        "=== WHAT THE PAGES CURRENTLY RANKING FOR THIS KEYWORD ACTUALLY COVER ===",
        "These are the real heading structures of the top-ranking pages, scraped "
        "just now. They are evidence of what this search expects a page to cover "
        "— not a template to copy.",
        "",
        "Use them to make the outline COMPREHENSIVE:",
        "  - Include the sections that appear across several of these pages. "
        "Consistent coverage means the search expects it.",
        "  - Where they disagree, prefer what the better-ranked pages do.",
        "  - Add at least one section none of them have, so the page has a "
        "reason to outrank them rather than merely match them.",
        "  - Do NOT copy their wording, and do NOT name these competitors in "
        "the outline.",
        "",
    ]
    for item in structures:
        label = item.get('domain') or item.get('url', '')[:60]
        lines.append(f"--- #{item['rank']} {label} ---")
        if item.get('title'):
            lines.append(f"    page title: {item['title'][:110]}")
        for level, text in item['headings']:
            indent = {'h1': '    ', 'h2': '      ', 'h3': '        '}.get(level, '      ')
            lines.append(f"{indent}{level.upper()}: {text}")
        lines.append("")
    return "\n".join(lines)


def build_competitor_brief(domain_id, keywords, limit=None, deadline_seconds=None):
    """The whole thing: ranked competitors -> scraped -> heading brief, or ''.

    The single entry point callers need. Returns '' rather than raising for
    every failure mode, so a caller can append it unconditionally.
    """
    if not _enabled():
        return ''
    try:
        competitors = top_competitor_urls(domain_id, keywords, limit or _max_pages())
        if not competitors:
            return ''
        structures = gather_competitor_structures(competitors, deadline_seconds)
        return format_competitor_brief(structures)
    except Exception as exc:  # noqa: BLE001 - additive feature, never fatal
        logger.warning("[CompetitorOutline] brief unavailable: %s", exc)
        return ''
