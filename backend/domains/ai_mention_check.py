"""Opt-in, on-demand AI Mention Check for the Domain Overview page.

Fires a few live LLM queries about an arbitrary domain and reports RAW signals —
how often the brand is mentioned, whether it's cited, and the sentiment — for any
domain, tracked or not. This is deliberately separate from the tracked-domain AI
pipeline: it computes NO normalized "visibility score" (that is relative to tracked
domains) and needs no Domain/Prompt rows.

Cost + latency: each check spends real LLM credits and can take tens of seconds, so it
is button-triggered on the frontend and cached 24h here. Requires an LLM API key
(``OPENAI_API_KEY`` or ``GOOGLE_GEMINI_API_KEY``); returns ``available: False`` otherwise.

Query-build + mention/citation/sentiment parsing mirror the engine's proven logic in
``engine/core/analytics_helpers.py`` (kept self-contained so the backend needs no
cross-project import).
"""
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from django.conf import settings
from django.core.cache import cache

from domains.site_audit import normalize_target

try:
    from textblob import TextBlob
except Exception:  # noqa: BLE001
    TextBlob = None

logger = logging.getLogger(__name__)

CACHE_TTL = 60 * 60 * 24  # 24h
NUM_QUERIES = 3


def _today_line():
    today = date.today()
    return (
        f"Today's date is {today.strftime('%B %d, %Y')} ({today.isoformat()}). "
        "Prioritize the most recent information; flag anything that may be outdated."
    )


def _build_user_prompt(question):
    return (
        f"{_today_line()}\n\n"
        f"Question: {question}\n\n"
        "Give a comprehensive answer. Mention specific companies, tools, platforms and "
        "services by name, and include relevant URLs / citations to your sources."
    )


def _brand_queries(host):
    return [
        f"What is {host}? Give an overview of the company or product and cite sources.",
        f"What are the best alternatives and main competitors to {host}?",
        f"What is the reputation of {host}? Summarize reviews and opinions with sources.",
    ][:NUM_QUERIES]


def _count_mentions(text, patterns):
    """Non-overlapping, word-boundary mention count (mirrors the engine)."""
    if not text or not patterns:
        return 0
    spans = []
    lowered = text.lower()
    for pattern in patterns:
        if not pattern or len(pattern) < 3:
            continue
        regex = r"\b" + re.escape(pattern.lower()) + r"\b"
        try:
            for match in re.finditer(regex, lowered):
                span = match.span()
                if not any(not (span[1] <= s[0] or span[0] >= s[1]) for s in spans):
                    spans.append(span)
        except re.error:
            continue
    return len(spans)


def _parse(text, host, sld):
    text = text or ""
    escaped_domain = re.escape(host.replace(".", r"\."))
    direct = re.findall(r"https?://[^\s\)\]]*" + escaped_domain + r"[^\s\)\]]*", text, re.IGNORECASE)
    escaped_sld = re.escape(sld.replace(" ", "[-_]?")) if sld else ""
    brand = re.findall(r"https?://[^\s\)\]]*" + escaped_sld + r"[^\s\)\]]*", text, re.IGNORECASE) if escaped_sld else []
    citations = list(set(direct + brand))

    patterns = [
        p for p in [
            host, sld,
            host.replace(".com", "").replace(".org", "").replace(".net", "").replace(".io", ""),
            sld.replace(" ", ""), sld.replace(" ", "-"), sld.replace(" ", "_"),
        ] if p and len(p) >= 3
    ]
    mention_count = _count_mentions(text, patterns)

    polarity, sentiment = 0.0, "neutral"
    if TextBlob is not None and text:
        try:
            polarity = float(TextBlob(text).sentiment.polarity)
            sentiment = "positive" if polarity > 0.1 else "negative" if polarity < -0.1 else "neutral"
        except Exception:  # noqa: BLE001
            pass

    return {
        "mention_count": mention_count,
        "citation_count": len(citations),
        "citations": citations,
        "sentiment": sentiment,
        "sentiment_score": round(polarity, 3),
    }


# --------------------------------------------------------------------------- #
# Providers
# --------------------------------------------------------------------------- #
def _ask_openai(api_key, user_message):
    from openai import OpenAI

    client = OpenAI(api_key=api_key, timeout=90)
    model = getattr(settings, "OPENAI_CHATGPT_MODEL", "gpt-4o")
    # Prefer the Responses API with web_search so the model browses before answering.
    if getattr(settings, "OPENAI_CHATGPT_WEB_SEARCH", True):
        try:
            resp = client.responses.create(
                model=model,
                tools=[{"type": "web_search"}],
                input=[
                    {"role": "system", "content": _today_line() + " Use the web_search tool for time-sensitive info and cite sources."},
                    {"role": "user", "content": user_message},
                ],
                timeout=90,
            )
            text = getattr(resp, "output_text", "") or ""
            if text:
                return text
        except Exception as exc:  # noqa: BLE001
            logger.info("[ai_mention_check] OpenAI web_search failed, falling back: %s", exc)

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _today_line()},
            {"role": "user", "content": user_message},
        ],
        temperature=0.7,
        max_tokens=2000,
        timeout=60,
    )
    return resp.choices[0].message.content or ""


def _ask_gemini(api_key, user_message):
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(getattr(settings, "GEMINI_MODEL", "gemini-flash-latest"))
    resp = model.generate_content(user_message)
    return getattr(resp, "text", "") or ""


def _ask_anthropic(api_key, user_message):
    from anthropic import Anthropic

    client = Anthropic(api_key=api_key, timeout=90)
    model = getattr(settings, "ANTHROPIC_MODEL", "claude-sonnet-4-6")
    resp = client.messages.create(
        model=model,
        max_tokens=2000,
        system=_today_line(),
        messages=[{"role": "user", "content": user_message}],
    )
    parts = [b.text for b in getattr(resp, "content", []) if getattr(b, "type", None) == "text"]
    return "\n".join(parts)


def _ask_perplexity(api_key, user_message):
    # Perplexity exposes an OpenAI-compatible API; `sonar` has built-in web search.
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url="https://api.perplexity.ai", timeout=90)
    model = getattr(settings, "PERPLEXITY_MODEL", "sonar")
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _today_line()},
            {"role": "user", "content": user_message},
        ],
        max_tokens=2000,
    )
    return resp.choices[0].message.content or ""


# The four engines the GEO model measures, in report order.
ENGINES = [
    ("OpenAI", "openai", _ask_openai),
    ("Google Gemini", "gemini", _ask_gemini),
    ("Perplexity", "perplexity", _ask_perplexity),
    ("Claude", "anthropic", _ask_anthropic),
]

_KEY_SOURCES = {
    "openai": ("openai_key", "OPENAI_API_KEY"),
    "gemini": ("gemini_key", "GOOGLE_GEMINI_API_KEY"),
    "anthropic": ("anthropic_key", "ANTHROPIC_API_KEY"),
    "perplexity": ("perplexity_key", "PERPLEXITY_API_KEY"),
    "xai": ("xai_key", "XAI_API_KEY"),
}


def _resolve_key(org, provider):
    """Resolve an API key BYOK-first (the org's decrypted key), then ``.env`` fallback —
    mirrors the existing pattern in content/claude_content_generator.py."""
    attr, env_setting = _KEY_SOURCES[provider]
    if org is not None:
        try:
            key = getattr(org, attr, None)  # transparently decrypts; "" if unset
            if key:
                return key
        except Exception as exc:  # noqa: BLE001
            logger.warning("[ai_mention_check] org key resolution failed: %s", exc)
    return getattr(settings, env_setting, None)


def _select_provider(org):
    """Pick the first provider with a usable key (org BYOK or .env). Returns
    (provider_label, api_key, ask_fn) or (None, None, None)."""
    key = _resolve_key(org, "openai")
    if key:
        return "ChatGPT", key, _ask_openai
    key = _resolve_key(org, "gemini")
    if key:
        return "Gemini", key, _ask_gemini
    return None, None, None


# --------------------------------------------------------------------------- #
# AI Visibility Index (AVI) — the 60-point, live-prompt half of the GEO score
# --------------------------------------------------------------------------- #
AVI_MAX = 60
FUNNEL_STAGES = ("TOFU", "MOFU", "BOFU")
# Citation frequency is weighted toward high-intent BOFU queries.
FUNNEL_WEIGHTS = {"TOFU": 1.0, "MOFU": 1.5, "BOFU": 2.0}
PROMPTS_PER_STAGE = 2

_PROMPT_GEN_SYSTEM = (
    "You generate realistic prompts that a real buyer would type into an AI assistant while "
    "researching a category. Return ONLY a JSON array, no markdown."
)


def available_engines(org):
    """Engines with a usable key (BYOK first, then .env)."""
    engines = []
    for label, provider, ask in ENGINES:
        key = _resolve_key(org, provider)
        if key:
            engines.append({"label": label, "provider": provider, "key": key, "ask": ask})
    return engines


def generate_funnel_prompts(host, context, engine, per_stage=PROMPTS_PER_STAGE):
    """Ask one engine to write TOFU/MOFU/BOFU prompts for this brand's category.

    TOFU/MOFU prompts must NOT name the brand — the whole point is to see whether the brand
    surfaces organically for category questions. BOFU may name it (decision-stage).
    """
    message = (
        f"{_PROMPT_GEN_SYSTEM}\n\n"
        f"Brand domain: {host}\n"
        f"What they do (from their own site): {context[:1200]}\n\n"
        f"Write {per_stage * 3} prompts about this brand's CATEGORY:\n"
        f"- {per_stage} TOFU: educational/awareness questions. MUST NOT mention the brand.\n"
        f"- {per_stage} MOFU: comparison / 'best X for Y' questions. MUST NOT mention the brand.\n"
        f"- {per_stage} BOFU: decision-stage questions; may name the brand or compare it to rivals.\n\n"
        'Return ONLY: [{"prompt": "...", "stage": "TOFU"}, ...]'
    )
    text = engine["ask"](engine["key"], message)
    raw = (text or "").strip()
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        return []
    try:
        items = json.loads(match.group(0))
    except Exception:  # noqa: BLE001
        return []
    prompts = []
    for item in items:
        if not isinstance(item, dict):
            continue
        stage = str(item.get("stage", "")).upper().strip()
        text_val = str(item.get("prompt", "")).strip()
        if text_val and stage in FUNNEL_STAGES:
            prompts.append({"prompt": text_val, "stage": stage})
    return prompts


# Hosts that are never "competitors" — social, code hosts, encyclopedias, CDNs.
# NOTE: deliberately does NOT exclude big vendors (Microsoft/AWS/Google Cloud): for share
# of voice those ARE the competitors. The engine's own exclusion list is tuned for a
# different job (finding niche rivals) and would delete the loudest brands here.
_NON_BRAND_HOSTS = {
    "facebook.com", "twitter.com", "x.com", "linkedin.com", "instagram.com", "youtube.com",
    "reddit.com", "github.com", "stackoverflow.com", "wikipedia.org", "medium.com",
    "w3.org", "mozilla.org", "schema.org", "gravatar.com", "gstatic.com", "googleapis.com",
    "doubleclick.net", "cloudfront.net", "example.com",
}


# Sentence-starters / generic words that look like brands to a title-case regex.
_PHRASE_STOPWORDS = {
    "The", "This", "That", "These", "Those", "For", "With", "When", "Where", "What",
    "How", "Why", "Here", "There", "Some", "Many", "Most", "Both", "Each", "Other",
    "Best", "Top", "Key", "Overall", "However", "Additionally", "Based", "According",
    "If", "In", "On", "At", "As", "It", "You", "Your", "Our", "We", "They", "And", "But",
}
# Acronyms that are jargon, not brands.
_ACRONYM_STOPWORDS = {
    "AI", "API", "APIS", "SEO", "GEO", "FAQ", "CEO", "CTO", "CMS", "CRM", "SaaS", "SAAS",
    "B2B", "B2C", "ROI", "KPI", "URL", "URLS", "HTML", "CSS", "SDK", "UI", "UX", "IT",
    "ML", "LLM", "LLMS", "RAG", "TOFU", "MOFU", "BOFU", "US", "USA", "UK", "EU", "PDF",
    "HTTP", "HTTPS", "JSON", "XML", "SQL", "NLP", "GPU", "CPU", "RAM", "OS", "VM", "CDN",
    "DNS", "SSL", "TLS", "VPN", "SLA", "GDPR", "PII", "MVP", "QA", "RD", "HR", "PR",
}


def _brand_label(registered_domain):
    """acme.com -> Acme (a countable brand name)."""
    return (registered_domain or "").split(".")[0].replace("-", " ").strip().title()


def _extract_brand_mentions(text, own_host):
    """Count competitor BRAND mentions in a response.

    Share of voice counts how often each brand is *named*, not just linked — most rivals
    appear in prose ("Microsoft Azure", "AWS") with no URL at all. Counting only cited
    hosts (the previous behaviour) shrank the denominator and inflated relative SoV.

    Candidates come from cited hosts + `Brand.com` mentions; each is then counted by
    word-boundary occurrences across the text.
    """
    import tldextract

    text = text or ""
    own = tldextract.extract(own_host)
    own_reg = f"{own.domain}.{own.suffix}" if own.suffix else own.domain
    own_sld = own.domain.lower()

    candidates = set()
    for url in re.findall(r"https?://[^\s\)\]\"'>]+", text, re.IGNORECASE):
        try:
            host = re.sub(r"^https?://", "", url).split("/")[0].split(":")[0].lower()
            ext = tldextract.extract(host)
            reg = f"{ext.domain}.{ext.suffix}" if ext.suffix else ext.domain
        except Exception:  # noqa: BLE001
            continue
        if not reg or reg == own_reg or reg in _NON_BRAND_HOSTS:
            continue
        if ext.domain and len(ext.domain) >= 3 and ext.domain.lower() != own_sld:
            candidates.add(_brand_label(reg))

    # "FlyNax.com" / "visit Acme.io" style brand mentions in prose.
    for name, _tld in re.findall(r"\b([A-Z][A-Za-z0-9\-]{2,})\.(com|io|net|org|ai|co)\b", text):
        if name.lower() != own_sld:
            candidates.add(name.strip().title())

    # Multi-word title-case product names ("Microsoft Azure", "Google Cloud Platform").
    for phrase in re.findall(r"\b([A-Z][a-z]{2,}(?: [A-Z][A-Za-z]{2,}){1,2})\b", text):
        if phrase.split()[0] in _PHRASE_STOPWORDS:
            continue
        if own_sld not in phrase.lower():
            candidates.add(phrase)

    # Acronym brands that never carry a URL ("AWS", "GCP", "IBM").
    for acronym in re.findall(r"\b([A-Z]{2,6})\b", text):
        if acronym in _ACRONYM_STOPWORDS or acronym.lower() == own_sld:
            continue
        candidates.add(acronym)

    counts = {}
    for brand in candidates:
        if len(brand) < 3:
            continue
        hits = len(re.findall(r"\b" + re.escape(brand) + r"\b", text))
        if hits:
            counts[brand] = hits

    # Drop a candidate that is only ever part of a longer brand we already counted
    # ("Microsoft" inside "Microsoft Azure") so one rival isn't counted twice.
    for brand in list(counts):
        longer = [b for b in counts if b != brand and brand in b.split()]
        if longer and counts[brand] <= max(counts[b] for b in longer):
            counts.pop(brand, None)
    return counts


def _extract_position(text, host, citations, has_mention):
    """Rank of the brand inside an AI answer's list (1 = recommended first).

    Ported from the engine's extract_position_from_response — 'mention quality' in the GEO
    model is position AND engine spread; without this we cannot tell 'recommended first'
    from 'listed tenth'.
    """
    if not text:
        return None
    clean = (host or "").lower()
    if not clean:
        return None
    sld = clean.split(".")[0]
    variants = [v for v in {
        clean, sld,
        clean.replace(".com", "").replace(".org", "").replace(".net", "").replace(".io", ""),
        sld.replace(" ", ""), sld.replace(" ", "-"), sld.replace(" ", "_"),
    } if v and len(v) >= 3]

    lines = text.split("\n")
    # Index the numbered items first so each item's text window stops at the NEXT item.
    # (The engine's version uses a fixed 5-line lookahead, which bleeds item #1's window
    # into items #2-#5 — any brand in the top 5 then reports as #1.)
    numbered = []
    for i, raw in enumerate(lines):
        match = re.match(r"^[\*\s]*(\d+)[\.\)\:\-\s]+", raw.strip())
        if not match:
            continue
        position = int(match.group(1))
        if 1 <= position <= 100:  # guard against years / stray numbers
            numbered.append((i, position))

    for idx, (line_no, position) in enumerate(numbered):
        end = numbered[idx + 1][0] if idx + 1 < len(numbered) else min(line_no + 5, len(lines))
        window = " ".join(lines[line_no:end]).lower()
        if any(v in window for v in variants):
            return position

    lowered = text.lower()
    for url in citations or []:
        idx = lowered.find(url.lower())
        if idx == -1:
            continue
        context = lowered[max(0, idx - 500): idx + 500]
        if any(v in context for v in variants):
            found = re.search(r"(\d+)[\.\)\:]", context)
            if found:
                position = int(found.group(1))
                if 1 <= position <= 100:
                    return position
            return 1

    if has_mention and any(v in lowered for v in variants):
        return 1
    return None


def _position_quality(position):
    """How valuable a mention at this rank is (1 = recommended first)."""
    if not position:
        return 0.0
    if position == 1:
        return 1.0
    if position <= 3:
        return 0.7
    if position <= 10:
        return 0.4
    return 0.2


def score_avi(results, engines_tested, competitors, own_mentions):
    """AI Visibility Index (60 pts).

    Mirrors the GEO model: citation frequency (BOFU-weighted, 30) + citation share vs the
    strongest competitor observed (20) + mention quality (10 = engine spread 5 + position 5).
    Per the model, position only earns full credit in proportion to how consistently the
    brand appeared, so a lone #1 on one prompt cannot max it out.
    """
    total_prompts = len(results) or 1

    # 1) BOFU-weighted citation frequency (30)
    num = den = 0.0
    for r in results:
        w = FUNNEL_WEIGHTS.get(r["stage"], 1.0)
        den += w
        if r["mentioned"]:
            num += w
    weighted_rate = (num / den) if den else 0.0
    citation_score = round(30 * weighted_rate, 1)

    # 2) Relative share of voice vs the loudest competitor (20)
    loudest = max(competitors.values()) if competitors else 0
    if own_mentions <= 0 and loudest <= 0:
        rel_sov = 0.0
    elif loudest <= 0:
        rel_sov = 1.0
    else:
        rel_sov = min(1.0, own_mentions / loudest)
    sov_score = round(20 * rel_sov, 1)

    # 3a) Engine spread (5)
    present = {r["engine"] for r in results if r["mentioned"]}
    spread = (len(present) / engines_tested) if engines_tested else 0.0
    spread_score = round(5 * spread, 1)

    # 3b) Position quality (5), scaled by consistency
    ranked = [r["position"] for r in results if r["mentioned"] and r.get("position")]
    citation_rate = sum(1 for r in results if r["mentioned"]) / total_prompts
    pos_quality = (sum(_position_quality(p) for p in ranked) / len(ranked)) if ranked else 0.0
    position_score = round(5 * pos_quality * citation_rate, 1)

    avg_position = round(sum(ranked) / len(ranked), 1) if ranked else None
    first_rate = round(100 * sum(1 for p in ranked if p == 1) / len(ranked), 1) if ranked else 0.0
    top3_rate = round(100 * sum(1 for p in ranked if p <= 3) / len(ranked), 1) if ranked else 0.0

    total = round(citation_score + sov_score + spread_score + position_score, 1)
    return {
        "score": total,
        "max": AVI_MAX,
        "citation_frequency": {"score": citation_score, "max": 30,
                               "weighted_rate_pct": round(100 * weighted_rate, 1)},
        "relative_sov": {"score": sov_score, "max": 20, "pct": round(100 * rel_sov, 1)},
        "engine_spread": {"score": spread_score, "max": 5,
                          "engines_present": len(present), "engines_tested": engines_tested},
        "position": {"score": position_score, "max": 5,
                     "avg_position": avg_position,
                     "first_rate_pct": first_rate,
                     "top3_rate_pct": top3_rate,
                     "ranked_mentions": len(ranked)},
    }


# --------------------------------------------------------------------------- #
# Orchestrator
# --------------------------------------------------------------------------- #
def run_avi(name, context="", org=None):
    """Full AI Visibility Index run: funnel prompts x every available engine.

    Returns the AVI score plus the report-style blocks (visibility by model, funnel x engine
    heatmap, relative SoV, prompts won/lost). Cached 24h. Costs
    ``prompts x engines`` live LLM calls, so this is button-triggered from the UI.
    """
    from django.utils import timezone

    host, _ = normalize_target(name)
    if not host:
        return {"available": False, "domain_name": "", "error": "No domain provided"}

    engines = available_engines(org)
    if not engines:
        return {
            "available": False,
            "domain_name": host,
            "error": "No LLM API key available. Add your keys in Organisation settings (BYOK), "
                     "or set OPENAI_API_KEY / GOOGLE_GEMINI_API_KEY on the server.",
        }

    cache_key = f"domov:avi:{host}:{'-'.join(e['provider'] for e in engines)}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    prompts = generate_funnel_prompts(host, context or host, engines[0])
    if not prompts:
        # Fall back to the simple brand queries so a failed generation still yields signal.
        prompts = [{"prompt": q, "stage": "BOFU"} for q in _brand_queries(host)]

    sld = host.split(".")[0]
    jobs = [(p, e) for p in prompts for e in engines]

    def _one(job):
        prompt, engine = job
        try:
            text = engine["ask"](engine["key"], _build_user_prompt(prompt["prompt"]))
        except Exception as exc:  # noqa: BLE001
            logger.warning("[avi] %s failed on %s: %s", engine["label"], host, exc)
            text = ""
        parsed = _parse(text, host, sld)
        mentioned = parsed["mention_count"] > 0 or parsed["citation_count"] > 0
        brands = _extract_brand_mentions(text, host)
        return {
            "prompt": prompt["prompt"],
            "stage": prompt["stage"],
            "engine": engine["label"],
            "mentioned": mentioned,
            "mention_count": parsed["mention_count"],
            "citation_count": parsed["citation_count"],
            "sentiment": parsed["sentiment"],
            "position": _extract_position(text, host, parsed["citations"], mentioned),
            # Top rival in this specific answer — powers the per-prompt gap analysis.
            "top_competitor": max(brands, key=brands.get) if brands else None,
            "competitors": brands,
        }

    with ThreadPoolExecutor(max_workers=min(8, len(jobs))) as executor:
        results = list(executor.map(_one, jobs))

    # Aggregate brand mentions across every response -> relative share of voice.
    competitors = {}
    for r in results:
        for comp, count in r["competitors"].items():
            competitors[comp] = competitors.get(comp, 0) + count
        r.pop("competitors", None)
    own_mentions = sum(r["mention_count"] for r in results)
    top_competitors = sorted(competitors.items(), key=lambda kv: kv[1], reverse=True)[:8]

    # Sentiment measured only where the brand was actually cited (the report's
    # "sentiment when cited" — overall sentiment is meaningless if you're absent).
    cited = [r for r in results if r["mentioned"]]
    sentiment_when_cited = {
        "positive": sum(1 for r in cited if r["sentiment"] == "positive"),
        "neutral": sum(1 for r in cited if r["sentiment"] == "neutral"),
        "negative": sum(1 for r in cited if r["sentiment"] == "negative"),
        "sample": len(cited),
    }

    avi = score_avi(results, len(engines), competitors, own_mentions)

    # Visibility by model: share of prompts where the brand appeared on that engine.
    visibility_by_model = []
    for engine in engines:
        rows = [r for r in results if r["engine"] == engine["label"]]
        hit = sum(1 for r in rows if r["mentioned"])
        visibility_by_model.append({
            "engine": engine["label"],
            "visibility_pct": round(100 * hit / len(rows), 1) if rows else 0.0,
            "appeared": hit,
            "prompts": len(rows),
        })

    # Funnel stage x engine citation-rate heatmap.
    heatmap = []
    for stage in FUNNEL_STAGES:
        row = {"stage": stage, "cells": []}
        for engine in engines:
            rows = [r for r in results if r["stage"] == stage and r["engine"] == engine["label"]]
            hit = sum(1 for r in rows if r["mentioned"])
            row["cells"].append({
                "engine": engine["label"],
                "rate_pct": round(100 * hit / len(rows), 1) if rows else 0.0,
                "prompts": len(rows),
            })
        heatmap.append(row)

    won = sorted({r["prompt"] for r in results if r["mentioned"]})
    lost = sorted({r["prompt"] for r in results} - set(won))

    # Per-prompt intelligence: who beat us, and what kind of gap it is.
    prompt_rows = []
    for prompt in prompts:
        rows = [r for r in results if r["prompt"] == prompt["prompt"]]
        hits = [r for r in rows if r["mentioned"]]
        rivals = {}
        for r in rows:
            if r.get("top_competitor"):
                rivals[r["top_competitor"]] = rivals.get(r["top_competitor"], 0) + 1
        if not hits:
            gap = "Educational SERP" if prompt["stage"] == "TOFU" else "Visibility Gap"
            visibility = "Not Cited"
        elif len(hits) == len(rows):
            gap, visibility = "Defended", "Consistent"
        else:
            gap, visibility = "Defended", "Inconsistent"
        prompt_rows.append({
            "prompt": prompt["prompt"],
            "stage": prompt["stage"],
            "visibility": visibility,
            "gap_type": gap,
            "engines_hit": len(hits),
            "engines_tested": len(rows),
            "top_competitor": max(rivals, key=rivals.get) if rivals else None,
            "best_position": min([r["position"] for r in hits if r.get("position")], default=None),
        })
    prompt_rows.sort(key=lambda p: (-p["engines_hit"], p["stage"]))

    out = {
        "available": True,
        "domain_name": host,
        "checked_at": timezone.now().isoformat(),
        "engines": [e["label"] for e in engines],
        "prompts_tested": len(prompts),
        "responses": len(results),
        "avi": avi,
        "visibility_by_model": visibility_by_model,
        "funnel_heatmap": heatmap,
        "relative_sov": {
            "own_mentions": own_mentions,
            "top_competitors": [{"domain": d, "mentions": c} for d, c in top_competitors],
            "loudest": top_competitors[0][0] if top_competitors else None,
            "pct": avi["relative_sov"]["pct"],
        },
        "sentiment_when_cited": sentiment_when_cited,
        "prompt_intelligence": prompt_rows,
        "prompts_won": won,
        "prompts_lost": lost,
        "results": results,
        # Honesty: this sample is directional, not definitive (same caveat the GEO report makes).
        "sample_note": f"{len(prompts)} prompts x {len(engines)} engines = {len(results)} responses, "
                       f"single run each. Directional baseline, not a statistically stable rate.",
        "error": None,
    }
    cache.set(cache_key, out, CACHE_TTL)
    return out


def run_ai_mention_check(name, org=None):
    """Live, cached AI mention check for `name`. Returns raw signals (no normalized score).

    `org` is the requester's Organisation; its BYOK key is used first, falling back to the
    system `.env` key (same resolution as the rest of the platform).
    """
    from django.utils import timezone

    host, _ = normalize_target(name)
    if not host:
        return {"available": False, "domain_name": "", "error": "No domain provided"}

    provider, api_key, ask = _select_provider(org)
    if not provider:
        return {
            "available": False,
            "domain_name": host,
            "error": "No LLM API key available. Add your OpenAI or Gemini key in Organisation settings (BYOK), or set OPENAI_API_KEY / GOOGLE_GEMINI_API_KEY on the server.",
        }

    cache_key = f"domov:aicheck:{provider}:{host}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    sld = host.split(".")[0]
    queries = _brand_queries(host)

    def _one(question):
        try:
            text = ask(api_key, _build_user_prompt(question))
        except Exception as exc:  # noqa: BLE001
            logger.warning("[ai_mention_check] query failed for %s: %s", host, exc)
            text = ""
        parsed = _parse(text, host, sld)
        parsed["query"] = question
        parsed["mentioned"] = parsed["mention_count"] > 0 or parsed["citation_count"] > 0
        return parsed

    # Run the queries concurrently so total latency ≈ the slowest single call.
    with ThreadPoolExecutor(max_workers=len(queries)) as executor:
        results = list(executor.map(_one, queries))

    totals = {
        "mentions": sum(r["mention_count"] for r in results),
        "citations": sum(r["citation_count"] for r in results),
        "queries_with_mention": sum(1 for r in results if r["mentioned"]),
        "total_queries": len(results),
        "sentiment": {
            "positive": sum(1 for r in results if r["sentiment"] == "positive"),
            "neutral": sum(1 for r in results if r["sentiment"] == "neutral"),
            "negative": sum(1 for r in results if r["sentiment"] == "negative"),
        },
    }

    out = {
        "available": True,
        "domain_name": host,
        "provider": provider,
        "checked_at": timezone.now().isoformat(),
        "queries": [
            {
                "query": r["query"],
                "mentioned": r["mentioned"],
                "mention_count": r["mention_count"],
                "citation_count": r["citation_count"],
                "sentiment": r["sentiment"],
            }
            for r in results
        ],
        "totals": totals,
        "error": None,
    }
    cache.set(cache_key, out, CACHE_TTL)
    return out
