"""
SEO content gap analysis.

Where a competitor ranks for one of our tracked keywords and we do not — plus
what kind of page they win with, and which stage of the buyer journey the
keyword belongs to.

The spec this implements (ContentGap/SEO_Content_Gap_Analysis.docx) assumes
Ahrefs or SEMrush is used to discover which keywords competitors rank for.
That is not needed here: every crawl already stores the full SERP on
``SeoKeywordRank.snippets_details['competitors']`` as

    {"3": {"rank": 3, "url": ..., "title": ..., "domain": ...}, "4": {...}}

so the competitor's position, landing page and page title are already on hand
for every keyword we track. This module is therefore a query over data we own,
not an integration — no external call, no new table, no scheduled job.

Three of the document's four gap types fall out of that data directly:

    keyword gap        we rank poorly or not at all, a competitor ranks well
    content-type gap   what format wins the SERP (video, guide, comparison...)
    intent gap         which funnel stage the keyword sits in

The fourth, topic gap, needs semantic clustering across keywords and is
deliberately not attempted here — a keyword-level query cannot produce it
honestly, and guessing would make the other three look equally soft.

Scoring is NOT reinvented. Opportunity, estimated clicks and winnability come
from opportunities_service, so a keyword ranked the same way in both screens
carries the same numbers.
"""
import re
from collections import Counter
from urllib.parse import urlparse

from .opportunities_service import (
    CTR_BY_POSITION,
    TARGET_FOR_PAGE_ONE,
    TARGET_FOR_PAGE_TWO,
)

# A keyword is a gap when we sit at or beyond this. 0 means "not ranked at all"
# and is always a gap. Page three is the practical floor for "we are not here":
# below it a keyword earns effectively no clicks (see CTR_BY_POSITION, which
# runs out at 20).
GAP_RANK_FLOOR = 11

# A competitor only counts as winning the keyword if they are on page one.
# Someone at #28 is not taking traffic we could otherwise have.
COMPETITOR_WINS_ABOVE = 10

# Platforms that are never "our content gap" in the sense the document means —
# we cannot publish a page to close a youtube.com result. They are reported
# separately, because "the SERP is dominated by video" is itself a finding.
PLATFORM_DOMAINS = {
    "youtube.com", "facebook.com", "instagram.com", "twitter.com", "x.com",
    "linkedin.com", "pinterest.com", "reddit.com", "quora.com", "tiktok.com",
    "amazon.in", "amazon.com", "flipkart.com", "wikipedia.org",
}

# ---------------------------------------------------------------------------
# Content type — what kind of page is winning
# ---------------------------------------------------------------------------
# Matched against the URL path, the host and the SERP title together. Keyword
# patterns alone left 83% of results as "other": a page like
# coinmarketcap.com/currencies/xrp/ says what it is through its STRUCTURE, not
# through words a regex can find. So the rules below mix three signals —
# subdomain, path shape, and title — and the structural ones are what actually
# move the needle.
#
# Ordered: first match wins, most specific first.
CONTENT_TYPE_RULES = [
    ("video",       r"youtube\.com|vimeo\.com|/video/|/watch\b"),
    ("comparison",  r"\bvs\b|\bversus\b|\balternatives?\b|\bcompare[ds]?\b|\bbest\b|\btop\s*\d+|\bwhich\b"),
    ("review",      r"/review|\breviews?\b|\bratings?\b|\btestimonial"),
    ("tool",        r"/tools?/|/calculator|\bcalculator\b|/converter|\bconverter\b|/quiz|\bsimulator\b"),
    ("faq",         r"^support\.|^help\.|/faqs?\b|/help/|/support/|\bfaqs?\b|\bwhat is\b|\bhow do i\b"),
    ("docs",        r"^docs?\.|^developer\.|^api\.|/docs?/|/documentation|/api/"),
    ("guide",       r"/guides?/|/how-to|/tutorials?/|\bhow to\b|\btutorial\b|\bultimate guide\b|\bstep[- ]by[- ]step\b|\bexplained\b"),
    ("news",        r"^news\.|/news/|/press/|/\d{4}/\d{2}/|\bnews\b"),
    ("data",        r"/currencies?/|/coins?/|/markets?/|/prices?/|/charts?/|/statistics|\blive (price|chart)\b|\bprice\b.*\bchart\b|\bmarket cap\b"),
    ("product",     r"/products?/|/pricing|/plans?\b|/buy|/shop|/store|/order|/checkout|\bpricing\b"),
    ("article",     r"/blogs?/|/articles?/|/insights?/|/resources?/|/learn/|/knowledge"),
    ("category",    r"/collections?/|/categor|/c/|/browse/|/all-"),
]
CONTENT_TYPE_LABELS = {
    "video": "Video", "comparison": "Comparison", "guide": "Guide / how-to",
    "faq": "FAQ / support", "review": "Review", "article": "Blog / article",
    "product": "Product / pricing", "category": "Category / listing",
    "data": "Data / price page", "tool": "Interactive tool",
    "docs": "Documentation", "news": "News",
    "homepage": "Homepage", "other": "Other",
}

# Which funnel stage each winning format implies, used only when the keyword
# itself carries no signal. Google has already judged the intent by choosing
# what to rank; this reads that judgement back out.
TYPE_TO_INTENT = {
    "product": "decision", "category": "decision", "tool": "decision",
    "comparison": "consideration", "review": "consideration",
    "data": "consideration",
    "guide": "awareness", "faq": "awareness", "article": "awareness",
    "news": "awareness", "docs": "awareness", "video": "awareness",
}

# Buckets from the document's step 6. Thresholds sit on the shared opportunity
# score so the three screens cannot disagree about what a good opportunity is.
QUICK_WIN_MAX_RANK = 30      # already ranking somewhere — a nudge, not a build
STRATEGIC_MIN_VOLUME = 1000  # worth building for even from nothing


def _host(url):
    try:
        h = (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""
    return h[4:] if h.startswith("www.") else h


def classify_content_type(url, title=""):
    """What kind of page this is, from its host, path shape and SERP title.

    The host is matched with its own anchors (`^support.`) so a subdomain is a
    signal in its own right, and a path of depth 0 is called a homepage rather
    than falling through to "other" — a brand ranking with its front page is a
    meaningful and common result.
    """
    try:
        parsed = urlparse(url or "")
        host = (parsed.hostname or "").lower()
        path = (parsed.path or "").lower()
    except ValueError:
        host, path = "", ""
    if host.startswith("www."):
        host = host[4:]

    # Subdomain rules need the host anchored on its own, not buried in a blob.
    for name, pattern in CONTENT_TYPE_RULES:
        if pattern.startswith("^") and re.search(pattern, host):
            return name

    blob = f"{path} {title or ''}".lower()
    for name, pattern in CONTENT_TYPE_RULES:
        if re.search(pattern.lstrip("^") if pattern.startswith("^") else pattern, blob):
            return name

    # Nothing matched a rule. Fall back to the shape of the path, which still
    # says a great deal: a bare domain is a homepage, and beyond that the
    # length of the final slug separates the two things left. Category pages
    # name a thing — /women/shoes/slippers/, /motor-insurance/car-insurance.
    # Articles name a sentence — /what-are-direct-selling-agents-and-how-they-
    # work. Counting hyphens is crude but it is a property of how the whole web
    # builds URLs, not a vocabulary list that goes stale per industry.
    segments = [seg for seg in path.split("/") if seg]
    # A bare locale root (/en/, /ae/en/) is the front page in another language,
    # not a section — treat it as the homepage it is.
    if all(re.fullmatch(r"[a-z]{2}([-_][a-z]{2})?", seg) for seg in segments):
        return "homepage"
    slug = re.sub(r"\.(html?|php|aspx?)$", "", segments[-1])
    if slug.count("-") >= 4 or len(slug) > 40:
        return "article"
    return "category"


def serp_content_profile(serp):
    """Classify every page-one result, not just the leader.

    One URL is a weak signal — a bare domain tells you nothing. Ten results
    tell you what format actually wins this SERP, which is both a better
    classification and a more useful thing to show a user.

    Returns (dominant_type, [{type, label, count}, ...]).
    """
    counts = Counter(
        classify_content_type(c["url"], c["title"])
        for c in serp if c.get("rank") and c["rank"] <= COMPETITOR_WINS_ABOVE
    )
    if not counts:
        return "other", []
    # A homepage tells you little about format, so it only wins if nothing
    # more specific appears at all.
    ranked = counts.most_common()
    specific = [(k, v) for k, v in ranked if k not in ("homepage", "other")]
    dominant = specific[0][0] if specific else ranked[0][0]
    return dominant, [
        {"type": k, "label": CONTENT_TYPE_LABELS.get(k, "Other"), "count": v}
        for k, v in ranked
    ]


# ---------------------------------------------------------------------------
# Intent — which stage of the buyer journey the keyword sits in
# ---------------------------------------------------------------------------
# Read from the keyword first. When the keyword says nothing (which is most of
# them — 73% went unclassified on keyword patterns alone) the SERP is asked
# instead: Google has already decided what this query wants by choosing what to
# rank for it, and that decision is stored on every crawl.
INTENT_RULES = [
    ("decision",      r"\bbuy\b|\bprice\b|\bpricing\b|\bcost\b|\bcheap\b|\bdiscount\b|\boffers?\b|\bdeals?\b|\bcoupon\b|\bnear me\b|\bbook\b|\border\b|\bapply\b|\bdownload\b|\bsign ?up\b|\blogin\b|\bopen an? account\b|\bfees?\b|\bcharges?\b|\bquote\b"),
    ("consideration", r"\bbest\b|\btop\s*\d*\b|\bvs\b|\bversus\b|\bcompare\b|\bcomparison\b|\balternatives?\b|\breviews?\b|\bratings?\b|\bwhich\b|\brecommend"),
    ("awareness",     r"\bwhat\b|\bwhy\b|\bhow\b|\bwho\b|\bwhen\b|\bwhere\b|\bguide\b|\btutorial\b|\bmeaning\b|\bdefinition\b|\bexamples?\b|\btypes? of\b|\bbenefits?\b|\bexplained\b|\bis it\b|\bcan i\b|\bdifference between\b"),
    ("navigational",  r"\blogin\b|\bsign ?in\b|\bapp\b|\bwebsite\b|\bofficial\b|\bcustomer care\b|\bhelpline\b|\bcontact\b|\bportal\b|\bstatus\b|\btrack\b"),
]
INTENT_LABELS = {
    "awareness": "Awareness", "consideration": "Consideration",
    "decision": "Decision", "navigational": "Navigational",
    "unclassified": "Unclassified",
}
# What to publish for each stage — the document's step 5 recommendation.
INTENT_FORMAT_HINT = {
    "awareness": "Educational guide or explainer",
    "consideration": "Comparison or review page",
    "decision": "Product, pricing or booking page",
    "navigational": "Brand or support landing page",
    "unclassified": "Match the format already winning the SERP",
}


def classify_intent(keyword, dominant_type=None, has_ads=False):
    """Which funnel stage the query belongs to.

    Three signals, strongest first:

    1. the keyword's own wording — unambiguous whenever it is present;
    2. the format dominating page one — what Google decided the query wants;
    3. paid ads on the SERP — advertisers only bid where there is money, so an
       otherwise-neutral keyword with ads leans commercial rather than
       educational.

    Only (1) can return "navigational"; a SERP cannot distinguish that from a
    plain decision query, and guessing it would be worse than leaving it.
    """
    text = (keyword or "").lower()
    for name, pattern in INTENT_RULES:
        if re.search(pattern, text):
            return name

    from_serp = TYPE_TO_INTENT.get(dominant_type)
    if from_serp:
        # Ads turn an ambiguous informational read commercial, but never
        # override a SERP that is clearly transactional already.
        if has_ads and from_serp == "awareness":
            return "consideration"
        return from_serp

    return "consideration" if has_ads else "unclassified"


def _ctr(position):
    if not position or position < 1:
        return 0.0
    return CTR_BY_POSITION.get(position, 0.0)


def _estimated_gain(rank_now, volume):
    """Extra monthly clicks if this keyword reached its realistic target.

    Same model as the opportunities screen: published CTR by position times
    search volume. An estimate for ordering work, not a forecast — see the
    note on CTR_BY_POSITION.
    """
    if not volume:
        return 0
    target = TARGET_FOR_PAGE_ONE if 0 < rank_now <= 10 else TARGET_FOR_PAGE_TWO
    now = _ctr(rank_now) if rank_now else 0.0
    return max(0, int(round(volume * (_ctr(target) - now))))


def _bucket(rank_now, volume, gain):
    """Quick win, strategic bet or backlog — the document's step 6."""
    if rank_now and rank_now <= QUICK_WIN_MAX_RANK:
        return "quick_win"
    if (volume or 0) >= STRATEGIC_MIN_VOLUME:
        return "strategic_bet"
    return "backlog"


def _competitors_on_serp(row):
    """The SERP entries stored on a keyword, normalised to a list.

    The crawler writes a dict keyed by position; older rows may hold a list.
    Both are accepted so a schema wobble does not silently produce "no gaps".
    """
    blob = (row.snippets_details or {}).get("competitors")
    if isinstance(blob, dict):
        entries = list(blob.values())
    elif isinstance(blob, list):
        entries = blob
    else:
        return []
    out = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        try:
            rank = int(e.get("rank") or 0)
        except (TypeError, ValueError):
            continue
        url = e.get("url") or ""
        out.append({
            "rank": rank,
            "url": url,
            "title": e.get("title") or "",
            "domain": (e.get("domain") or _host(url) or "").lower(),
        })
    return sorted(out, key=lambda x: x["rank"] or 999)


def build_content_gaps(domain, platform=None, limit=None):
    """Gap rows for one domain, best opportunity first.

    A row is produced only where a competitor is on page one AND we are not —
    that is the whole definition of the gap. Keywords with no stored SERP are
    skipped rather than reported as "no competitors", and counted separately so
    the caller can say how much of the project has been analysed.
    """
    from ..models import SeoKeywordRank

    qs = (SeoKeywordRank.objects
          .filter(domain=domain)
          .select_related("keyword")
          .only("id", "rank_now", "search_volume", "platform", "target_url",
                "snippets_details", "ads", "keyword__keyword"))
    if platform and platform.lower() != "all":
        qs = qs.filter(platform=platform)

    rows, no_serp = [], 0
    for r in qs:
        serp = _competitors_on_serp(r)
        if not serp:
            no_serp += 1
            continue

        our_rank = r.rank_now or 0
        we_are_absent = our_rank == 0 or our_rank >= GAP_RANK_FLOOR
        if not we_are_absent:
            continue

        winners = [c for c in serp
                   if c["rank"] and c["rank"] <= COMPETITOR_WINS_ABOVE and c["domain"]]
        if not winners:
            continue

        # Split platforms out: "the SERP is all YouTube" is a real finding, but
        # it is not a page we can write.
        publishers = [c for c in winners if c["domain"] not in PLATFORM_DOMAINS]
        platforms = [c for c in winners if c["domain"] in PLATFORM_DOMAINS]
        lead = (publishers or winners)[0]

        volume = r.search_volume or 0
        gain = _estimated_gain(our_rank, volume)
        # The whole page one votes on the format, not just the leader. One
        # URL is too thin a signal — a competitor ranking with a bare domain
        # says nothing, while ten results say plainly what wins here.
        ctype, type_mix = serp_content_profile(serp)
        has_ads = bool(getattr(r, "ads", False))
        intent = classify_intent(r.keyword.keyword, ctype, has_ads)

        rows.append({
            "seo_keyword_rank_id": r.id,
            "keyword": r.keyword.keyword,
            "platform": r.platform,
            "our_rank": our_rank,
            "our_url": r.target_url or "",
            "search_volume": volume,
            "competitors_on_page_one": len(winners),
            # Every page-one domain, deduped — not the first five. The summary
            # counts from this list, and truncating it here undercounted any
            # domain that habitually ranks 6th to 10th. At most ten entries,
            # so keeping them all costs nothing.
            "competing_domains": list(dict.fromkeys(c["domain"] for c in winners)),
            "platform_results": len(platforms),
            "leader": {
                "domain": lead["domain"], "rank": lead["rank"],
                "url": lead["url"], "title": lead["title"],
            },
            "content_type": ctype,
            "content_type_label": CONTENT_TYPE_LABELS.get(ctype, "Other"),
            # The full distribution, so the page can show "6 of 10 results are
            # guides" rather than asking the user to trust a single label.
            "content_type_mix": type_mix,
            "leader_content_type": classify_content_type(lead["url"], lead["title"]),
            "has_ads": has_ads,
            "intent": intent,
            "intent_label": INTENT_LABELS[intent],
            "recommended_format": INTENT_FORMAT_HINT[intent],
            # Never ranked at all is a build; ranked but weak is an edit. This
            # is the document's step 5 decided from data instead of a manual
            # site audit.
            "action": "create" if our_rank == 0 else "optimise",
            "estimated_clicks": gain,
            "bucket": _bucket(our_rank, volume, gain),
            # Volume is the tie-breaker so two keywords with no click estimate
            # still order sensibly.
            "score": round(gain * 1.0 + (volume or 0) * 0.001, 1),
        })

    rows.sort(key=lambda x: (-x["score"], -x["search_volume"], x["keyword"]))
    if limit:
        rows = rows[:limit]
    return rows, no_serp


def summarise(rows, no_serp, total_tracked):
    """Headline counts for the page, derived from the same rows it renders."""
    buckets = Counter(r["bucket"] for r in rows)
    return {
        "gaps": len(rows),
        "keywords_analysed": total_tracked - no_serp,
        "keywords_without_serp": no_serp,
        "total_tracked": total_tracked,
        "estimated_clicks": sum(r["estimated_clicks"] for r in rows),
        "to_create": sum(1 for r in rows if r["action"] == "create"),
        "to_optimise": sum(1 for r in rows if r["action"] == "optimise"),
        "quick_wins": buckets.get("quick_win", 0),
        "strategic_bets": buckets.get("strategic_bet", 0),
        "backlog": buckets.get("backlog", 0),
        "by_content_type": [
            {"key": k, "label": CONTENT_TYPE_LABELS.get(k, "Other"), "count": v}
            for k, v in Counter(r["content_type"] for r in rows).most_common()
        ],
        "by_intent": [
            {"key": k, "label": INTENT_LABELS[k], "count": v}
            for k, v in Counter(r["intent"] for r in rows).most_common()
        ],
        "top_competitors": [
            {"domain": d, "keywords": n}
            for d, n in Counter(
                d for r in rows for d in r["competing_domains"]
            ).most_common(10)
        ],
    }


# ---------------------------------------------------------------------------
# Justification — why this particular keyword is a real gap
# ---------------------------------------------------------------------------
# The list view asserts "this is a gap". The detail view has to prove it, and
# proving it honestly means showing the evidence AGAINST acting too: a keyword
# whose page one is held by the tax authority's own e-filing portal is a gap in
# the arithmetic sense and a waste of a quarter in the practical one. Findings
# carry a stance so the page can show both sides rather than only the case for.
SUPPORTS, AGAINST, NEUTRAL = "supports", "against", "neutral"


def justify(row, serp, history):
    """Evidence for and against treating this keyword as a content gap.

    Each finding is {stance, title, detail}. Nothing here is scored into a
    verdict — the trade-off between "201,000 searches" and "the government
    holds #1" is a judgement the user makes, not one a rule should make for
    them.
    """
    from .share_of_voice_service import _is_non_rival

    findings = []
    our_rank = row["our_rank"]
    lead = row["leader"]

    # --- the definition itself
    if our_rank == 0:
        findings.append({
            "stance": SUPPORTS,
            "title": "You do not rank for this at all",
            "detail": "This keyword returns no position for your domain anywhere in the "
                      "top 30 results we capture. There is nothing to improve — this "
                      "needs a page.",
        })
    else:
        findings.append({
            "stance": SUPPORTS,
            "title": f"You sit at position {our_rank}, off page one",
            "detail": f"Position {our_rank} earns close to nothing: virtually all clicks "
                      f"go to the top ten. A page already exists and already ranks, "
                      f"which usually makes this cheaper to fix than to build.",
        })

    # A domain can hold several page-one positions, so name each one once —
    # "incometax.gov.in, incometax.gov.in, cleartax.in" reads like a bug.
    named = list(dict.fromkeys(row["competing_domains"]))[:5]
    findings.append({
        "stance": SUPPORTS,
        "title": f"{row['competitors_on_page_one']} of the top 10 positions belong to others",
        "detail": "Page one is occupied by " + ", ".join(named)
                  + ". Every one of those positions is traffic on a keyword you track.",
    })

    # --- demand
    volume = row["search_volume"]
    if volume >= STRATEGIC_MIN_VOLUME:
        findings.append({
            "stance": SUPPORTS,
            "title": f"{volume:,} searches a month",
            "detail": f"Demand is real and sustained. Reaching the target position would "
                      f"be worth roughly {row['estimated_clicks']:,} extra visits a month "
                      f"on published average click-through rates.",
        })
    elif volume == 0:
        findings.append({
            "stance": AGAINST,
            "title": "No search volume recorded",
            "detail": "We hold no volume figure for this keyword, so the traffic value of "
                      "closing the gap cannot be estimated. It may still matter for brand "
                      "or intent reasons, but it cannot be justified on traffic alone.",
        })
    else:
        findings.append({
            "stance": NEUTRAL,
            "title": f"{volume:,} searches a month",
            "detail": "Modest volume. Worth closing when it sits alongside related "
                      "keywords, harder to justify on its own.",
        })

    # --- is the leader actually displaceable?
    if _is_non_rival(lead["domain"]):
        findings.append({
            "stance": AGAINST,
            "title": f"{lead['domain']} is not a commercial rival",
            "detail": "The top result is a government, regulator or reference site. These "
                      "hold their own subject matter and are effectively impossible to "
                      "outrank on it. Look at whether the positions BELOW it are winnable "
                      "rather than treating #1 as the target.",
        })

    non_rivals = [c for c in serp
                  if c["rank"] and c["rank"] <= COMPETITOR_WINS_ABOVE
                  and _is_non_rival(c["domain"])]
    platforms = [c for c in serp
                 if c["rank"] and c["rank"] <= COMPETITOR_WINS_ABOVE
                 and c["domain"] in PLATFORM_DOMAINS]
    blocked = len({c["rank"] for c in non_rivals + platforms})
    if blocked >= 4:
        findings.append({
            "stance": AGAINST,
            "title": f"{blocked} of the top 10 are effectively closed",
            "detail": "Government, reference and social platform results cannot be "
                      f"displaced by publishing a page. Realistically you are competing "
                      f"for {COMPETITOR_WINS_ABOVE - blocked} positions, not ten.",
        })
    elif platforms:
        findings.append({
            "stance": NEUTRAL,
            "title": f"{len(platforms)} social or video results on page one",
            "detail": "Google is mixing formats here. That is a signal about what the "
                      "query wants as much as an obstacle — a video or a community answer "
                      "may serve this better than an article.",
        })

    # --- how settled is the format
    mix = row["content_type_mix"]
    dominant = next((m for m in mix if m["type"] == row["content_type"]), None)
    if dominant and dominant["count"] >= 6:
        findings.append({
            "stance": SUPPORTS,
            "title": f"The format is settled: {dominant['count']} of "
                     f"{row['competitors_on_page_one']} results are {dominant['label'].lower()}",
            "detail": "Google has made up its mind about what this query wants. Publishing "
                      "the same format is the low-risk move; publishing a different one "
                      "means arguing with a decision Google has already made.",
        })
    elif len(mix) >= 4:
        findings.append({
            "stance": NEUTRAL,
            "title": "Page one is mixed in format",
            "detail": "No single format dominates ("
                      + ", ".join(f"{m['count']}× {m['label'].lower()}" for m in mix[:4])
                      + "). An unsettled results page is easier to enter than a settled "
                        "one, but gives you less guidance on what to build.",
        })

    # --- have we ever ranked?
    ranked_days = [h for h in history if h["rank"] and h["rank"] > 0]
    if history and not ranked_days:
        findings.append({
            "stance": NEUTRAL,
            "title": f"Never ranked in {len(history)} days of tracking",
            "detail": "This keyword has been tracked without ever surfacing. That points "
                      "at a missing page rather than a weak one.",
        })
    elif ranked_days:
        best = min(h["rank"] for h in ranked_days)
        if best <= COMPETITOR_WINS_ABOVE:
            findings.append({
                "stance": SUPPORTS,
                "title": f"You have reached position {best} before",
                "detail": f"A page of yours has held page one for this keyword within the "
                          f"tracked history. Recovering a position you once held is "
                          f"markedly cheaper than winning one you never had.",
            })

    # --- intent alignment
    if row["intent"] != "unclassified":
        findings.append({
            "stance": NEUTRAL,
            "title": f"{row['intent_label']} intent — {row['recommended_format'].lower()}",
            "detail": "What the searcher wants at this stage, read from the wording of the "
                      "keyword and from what Google chose to rank. Matching it matters more "
                      "than word count.",
        })

    return findings


def _competitor_context(domain, hosts, exclude_id=None):
    """How much of the REST of this project each of these domains also holds.

    A results page tells you who beat you on one keyword. It does not tell you
    whether that domain is a one-off or the rival taking forty of your keywords
    — and those call for completely different responses. One pass over the
    project answers it for every domain on the page at once.
    """
    from ..models import SeoKeywordRank

    hosts = set(hosts)
    if not hosts:
        return {}

    stats = {h: {"gaps_held": 0, "ranks": [], "beats_us": 0, "we_beat": 0,
                 "search_volume": 0} for h in hosts}

    qs = (SeoKeywordRank.objects
          .filter(domain=domain)
          .only("id", "rank_now", "search_volume", "snippets_details"))
    if exclude_id:
        qs = qs.exclude(id=exclude_id)

    for r in qs.iterator(chunk_size=500):
        serp = _competitors_on_serp(r)
        if not serp:
            continue
        our_rank = r.rank_now or 0
        we_are_absent = our_rank == 0 or our_rank >= GAP_RANK_FLOOR

        best_by_host = {}
        for c in serp:
            if c["domain"] in hosts and c["rank"]:
                cur = best_by_host.get(c["domain"])
                if cur is None or c["rank"] < cur:
                    best_by_host[c["domain"]] = c["rank"]

        for host, rank in best_by_host.items():
            st = stats[host]
            if our_rank:
                if our_rank < rank:
                    st["we_beat"] += 1
                else:
                    st["beats_us"] += 1
            # Only page-one positions on keywords we are absent from count as
            # gaps, matching the definition the list view uses.
            if rank <= COMPETITOR_WINS_ABOVE and we_are_absent:
                st["gaps_held"] += 1
                st["ranks"].append(rank)
                st["search_volume"] += r.search_volume or 0

    return {
        h: {
            "gaps_held": st["gaps_held"],
            "avg_rank": round(sum(st["ranks"]) / len(st["ranks"]), 1)
                        if st["ranks"] else 0,
            "beats_us": st["beats_us"],
            "we_beat": st["we_beat"],
            "search_volume": st["search_volume"],
        }
        for h, st in stats.items()
    }


def gap_detail(seo_kw, history_days=90):
    """Everything known about one gap keyword, for the detail page.

    Returns None when the keyword is not in fact a gap — the detail page must
    not manufacture a case for a keyword the list view would never show.
    """
    from ..models import SeoRankHistory
    from .share_of_voice_service import _is_non_rival

    serp = _competitors_on_serp(seo_kw)
    if not serp:
        return None

    our_rank = seo_kw.rank_now or 0
    if not (our_rank == 0 or our_rank >= GAP_RANK_FLOOR):
        return None

    winners = [c for c in serp
               if c["rank"] and c["rank"] <= COMPETITOR_WINS_ABOVE and c["domain"]]
    if not winners:
        return None

    publishers = [c for c in winners if c["domain"] not in PLATFORM_DOMAINS]
    lead = (publishers or winners)[0]
    volume = seo_kw.search_volume or 0
    gain = _estimated_gain(our_rank, volume)
    ctype, type_mix = serp_content_profile(serp)
    has_ads = bool(seo_kw.ads)
    intent = classify_intent(seo_kw.keyword.keyword, ctype, has_ads)

    row = {
        "seo_keyword_rank_id": seo_kw.id,
        "keyword": seo_kw.keyword.keyword,
        "platform": seo_kw.platform,
        "our_rank": our_rank,
        "our_url": seo_kw.target_url or "",
        "search_volume": volume,
        "competitors_on_page_one": len(winners),
        "competing_domains": [c["domain"] for c in winners[:5]],
        "platform_results": len([c for c in winners if c["domain"] in PLATFORM_DOMAINS]),
        "leader": {"domain": lead["domain"], "rank": lead["rank"],
                   "url": lead["url"], "title": lead["title"]},
        "content_type": ctype,
        "content_type_label": CONTENT_TYPE_LABELS.get(ctype, "Other"),
        "content_type_mix": type_mix,
        "leader_content_type": classify_content_type(lead["url"], lead["title"]),
        "has_ads": has_ads,
        "intent": intent,
        "intent_label": INTENT_LABELS[intent],
        "recommended_format": INTENT_FORMAT_HINT[intent],
        "action": "create" if our_rank == 0 else "optimise",
        "estimated_clicks": gain,
        "bucket": _bucket(our_rank, volume, gain),
        "score": round(gain * 1.0 + volume * 0.001, 1),
    }

    history = [
        {"date": h.snapshot_date.isoformat(), "rank": h.rank_position}
        for h in SeoRankHistory.objects
        .filter(seo_keyword_rank=seo_kw)
        .order_by("-snapshot_date")[:history_days]
    ]
    history.reverse()

    # The whole results page, ours included, so the user can see the shape of
    # what they are entering rather than just the one leading row.
    # Context for the domains that actually took page one. Restricted to those
    # so the extra pass stays proportionate — nobody needs a profile of the
    # site sitting at #27.
    page_one_hosts = {c["domain"] for c in winners if c["domain"]}
    context = _competitor_context(seo_kw.domain, page_one_hosts,
                                  exclude_id=seo_kw.id)

    full_serp = []
    for c in sorted(serp, key=lambda c: c["rank"] or 999):
        ctype_here = classify_content_type(c["url"], c["title"])
        ctx = context.get(c["domain"], {})
        full_serp.append({
            "rank": c["rank"],
            "domain": c["domain"],
            "url": c["url"],
            "title": c["title"],
            "content_type": ctype_here,
            "content_type_label": CONTENT_TYPE_LABELS.get(ctype_here, "Other"),
            "is_platform": c["domain"] in PLATFORM_DOMAINS,
            "is_non_rival": _is_non_rival(c["domain"]),
            # Elsewhere in this project, excluding the keyword on screen.
            "gaps_held": ctx.get("gaps_held", 0),
            "avg_rank": ctx.get("avg_rank", 0),
            "beats_us": ctx.get("beats_us", 0),
            "we_beat": ctx.get("we_beat", 0),
            "context_volume": ctx.get("search_volume", 0),
        })

    # The page-one domains as rivals rather than as rows: who they are across
    # the whole project, worst offender first. The results table answers "who
    # beat me here"; this answers "who am I actually up against".
    competitors = sorted(
        [
            {
                "domain": h,
                "rank_here": min(c["rank"] for c in winners if c["domain"] == h),
                "positions_here": sum(1 for c in winners if c["domain"] == h),
                "is_non_rival": _is_non_rival(h),
                "is_platform": h in PLATFORM_DOMAINS,
                **context.get(h, {}),
            }
            for h in page_one_hosts
        ],
        key=lambda c: (-c.get("gaps_held", 0), c["rank_here"]),
    )

    return {
        **row,
        "serp": full_serp,
        "competitors": competitors,
        "history": history,
        "findings": justify(row, serp, history),
        "serp_features": {
            "featured_snippet": bool(seo_kw.featured_snippet),
            "knowledge_panel": bool(seo_kw.knowledge_panel),
            "ads": has_ads,
            "reviews": bool(seo_kw.review),
        },
    }
