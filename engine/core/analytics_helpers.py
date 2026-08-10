from __future__ import annotations

import random
import re
import logging
import time
from typing import Any, Dict, List, Optional

from django.conf import settings

try:
	from .brand_identity import (
		TWO_PART_SUFFIXES as _TWO_PART_SUFFIXES,
		build_brand_identity,
		registrable_domain as _registrable_domain,
	)
except ImportError:  # pragma: no cover
	# Several standalone tests exec this file straight off disk with no parent
	# package, which makes the relative import above impossible — every other
	# sibling import in this module is function-local for exactly that reason.
	# These names are needed at module scope (competitor_extractor imports two
	# of them from here), so load the sibling by path instead.
	import importlib.util as _importlib_util
	import sys as _sys
	from pathlib import Path as _Path

	_bi_spec = _importlib_util.spec_from_file_location(
		'core_brand_identity',
		_Path(__file__).resolve().with_name('brand_identity.py'),
	)
	_brand_identity = _importlib_util.module_from_spec(_bi_spec)
	# Registered BEFORE exec: @dataclass resolves its own module out of
	# sys.modules while the class body is being processed, and blows up on None.
	_sys.modules['core_brand_identity'] = _brand_identity
	_bi_spec.loader.exec_module(_brand_identity)
	_TWO_PART_SUFFIXES = _brand_identity.TWO_PART_SUFFIXES
	build_brand_identity = _brand_identity.build_brand_identity
	_registrable_domain = _brand_identity.registrable_domain

try:
	from textblob import TextBlob
except Exception:  # pragma: no cover
	TextBlob = None  # type: ignore


logger = logging.getLogger(__name__)


def _brand_name_of(group: Any) -> str:
	"""The domain's display name, when the caller handed us its prompt group.

	Every platform handler already receives `group`, and `group.domain` is
	select_related at the call site, so this costs no query. It is the second
	half of the brand's identity — the half that recognises 'Canara HSBC Life
	Insurance' in prose, which the URL alone cannot.
	"""
	try:
		return getattr(getattr(group, 'domain', None), 'name', '') or ''
	except Exception:
		return ''


def process_prompt_with_gemini(prompt_text: str, user_domain: str, client: Any = None, group: Any = None) -> Dict[str, Any]:
    """Direct Gemini processor; currently delegates to wrapper implementation."""
    return process_prompt_with_gemini_wrapper(prompt_text, user_domain, client, group)


def process_prompt_with_perplexity(prompt_text: str, user_domain: str, client: Any = None, group: Any = None) -> Dict[str, Any]:
    """Direct Perplexity processor; currently delegates to wrapper implementation."""
    return process_prompt_with_perplexity_wrapper(prompt_text, user_domain, client, group)

def get_openai_client(org_id: Optional[int] = None):
	"""
	Return an OpenAI-compatible client pointed at OpenRouter, which now
	transports every ChatGPT call. Delegates to ClientFactory, which resolves the
	credential via OPENROUTER_ROUTED: per-org OpenAI BYOK keys are no longer
	consulted, so this resolves to the system .env OPENROUTER_API_KEY.
	Accepts optional org_id, still used for the provider-enabled check.
	"""
	try:
		from .services.client_factory import get_client
		return get_client('openai', org_id=org_id)
	except Exception as e:
		raise Exception(f"OpenAI client unavailable: {e}")


def get_gemini_client(org_id: Optional[int] = None) -> Dict[str, Any]:
	"""Return a Gemini config dict via ClientFactory."""
	try:
		from .services.client_factory import get_client
		return get_client('gemini', org_id=org_id)
	except Exception as e:
		raise Exception(f"Gemini client unavailable: {e}")


def get_perplexity_client(org_id: Optional[int] = None) -> Dict[str, Any]:
	"""Return a Perplexity client via ClientFactory."""
	try:
		from .services.client_factory import get_client
		return get_client('perplexity', org_id=org_id)
	except Exception as e:
		raise Exception(f"Perplexity client unavailable: {e}")


def get_anthropic_client(org_id: Optional[int] = None) -> Dict[str, Any]:
	"""Return an Anthropic client via ClientFactory."""
	try:
		from .services.client_factory import get_client
		return get_client('anthropic', org_id=org_id)
	except Exception as e:
		raise Exception(f"Anthropic client unavailable: {e}")


def get_xai_client(org_id: Optional[int] = None) -> Dict[str, Any]:
	"""Return an xAI (Grok) client via ClientFactory."""
	try:
		from .services.client_factory import get_client
		return get_client('xai', org_id=org_id)
	except Exception as e:
		raise Exception(f"xAI client unavailable: {e}")


def get_deepseek_client(org_id: Optional[int] = None) -> Dict[str, Any]:
	"""Return a DeepSeek client via ClientFactory."""
	try:
		from .services.client_factory import get_client
		return get_client('deepseek', org_id=org_id)
	except Exception as e:
		raise Exception(f"DeepSeek client unavailable: {e}")




def _get_domain_from_url(value: str) -> str:
	try:
		from urllib.parse import urlparse
		if not value:
			return ""
		parsed = urlparse(value if "://" in value else f"http://{value}")
		host = parsed.netloc or parsed.path
		domain = host.lower()
		if domain.startswith("www."):
			domain = domain[4:]
		if ":" in domain:
			domain = domain.split(":", 1)[0]
		return domain
	except Exception:
		v = str(value).lower()
		return v[4:] if v.startswith("www.") else v


def extract_position_from_response(response: str, user_domain: str, citation_urls: Optional[List[str]] = None, has_mention: bool = False, brand_name: str = "") -> Optional[int]:
	if not response:
		return None
	identity = build_brand_identity(user_domain or "", brand_name or "")
	if not identity.is_resolvable:
		return None
	lines = response.split("\n")
	found_position = None
	# Index the numbered items first so each item's search window ends where the NEXT item
	# begins. A fixed lookahead (e.g. lines[i:i+5]) bleeds item #1's window into items
	# #2-#5, so any brand in the top 5 was reported as position #1 — inflating #1 rates.
	numbered_items = []
	for i in range(len(lines)):
		line = lines[i].strip()
		# Match numbered patterns: "1.", "1)", "(1)", "1:", "1 -", etc.
		# Exclude '#' to avoid matching hashtags/years like "#2023"
		numbered_match = re.match(r'^[\*\s]*(\d+)[\.\)\:\-\s]+', line)
		if numbered_match:
			position = int(numbered_match.group(1))
			# Validate position is reasonable (1-100), not a year or other large number
			if position < 1 or position > 100:
				continue
			numbered_items.append((i, position))

	for idx, (line_no, position) in enumerate(numbered_items):
		end = numbered_items[idx + 1][0] if idx + 1 < len(numbered_items) else min(line_no + 5, len(lines))
		search_window = ' '.join(lines[line_no:end])
		if identity.appears_in(search_window):
			found_position = position
			break
	if found_position is not None:
		return found_position
	if citation_urls:
		full_text_lower = response.lower()
		for url in citation_urls:
			idx = full_text_lower.find(url.lower())
			if idx == -1:
				continue
			context = response[max(0, idx - 500): idx + 500]
			if identity.appears_in(context):
				m = re.search(r'(\d+)[\.\)\:]', context)
				if m:
					position = int(m.group(1))
					# Validate position is reasonable (1-100), not a year or other large number
					if 1 <= position <= 100:
						return position
				# If no valid position found but brand + citation exists, default to 1
				return 1
	if has_mention and identity.appears_in(response):
		return 1
	return None


# `_TWO_PART_SUFFIXES` and `_registrable_domain` now live in brand_identity.py
# and are imported at the top of this module — one copy, shared with the mention
# matching that needs the same notion of "the brand's own domain".
# competitor_extractor.py imports both from here, so the names stay exported.


def _is_same_or_subdomain(host: str, own_host: str) -> bool:
	"""True when `host` belongs to the brand itself, including subdomains."""
	if not host or not own_host:
		return False
	return _registrable_domain(host) == _registrable_domain(own_host)


def _extract_competitor_mentions(text: str, user_domain: str, all_urls: List[str] = None) -> List[str]:
	"""
	Extract competitor brand/company names from LLM response text.
	Uses multiple strategies: URL analysis, company name patterns, and keyword extraction.

	Args:
		text: The LLM response text
		user_domain: The user's domain (to exclude from competitors)
		all_urls: List of all URLs found in the text

	Returns:
		List of competitor names found in the text
	"""
	if not text:
		return []

	competitors = set()
	user_domain_clean = _get_domain_from_url(user_domain).lower()
	user_sld = user_domain_clean.split('.')[0] if user_domain_clean else ""

	# Strategy 1: Extract company names from URLs (MOST RELIABLE)
	# This is the most accurate source - if they have a URL, they're a real company
	if all_urls:
		# Common domains to exclude (not competitors)
		# Reference and community sites that get cited constantly and are not
		# anybody's competitor. Reddit's absence is why it was recorded as a
		# rival of a Kerala tourism brand.
		excluded_domains = {
			'google', 'facebook', 'twitter', 'linkedin', 'instagram', 'youtube',
			'github', 'stackoverflow', 'wikipedia', 'medium', 'amazon', 'aws',
			'microsoft', 'apple', 'w3', 'mozilla', 'chrome', 'example', 'test',
			'localhost', 'schema', 'json', 'xml',
			'reddit', 'quora', 'wikimedia', 'wiktionary', 'britannica',
			'tripadvisor', 'yelp', 'glassdoor', 'crunchbase', 'bloomberg',
			'forbes', 'reuters', 'bbc', 'cnn', 'nytimes', 'wsj', 'economictimes',
			'timesofindia', 'hindustantimes', 'livemint', 'moneycontrol',
			'investopedia', 'yahoo', 'bing', 'duckduckgo', 'archive',
			'x', 'threads', 'tiktok', 'pinterest', 'substack', 'blogspot',
			'wordpress', 'wix', 'squarespace', 'shopify', 'gov', 'nic',
		}

		for url in all_urls:
			domain = _get_domain_from_url(url)
			# Skip the brand's own site AND its subdomains. Matching only the
			# exact host let kite./support./coin.zerodha.com through as rivals.
			if not domain or _is_same_or_subdomain(domain, user_domain_clean):
				continue

			# Brand label from the REGISTRABLE domain, not the first hostname
			# label — otherwise every subdomain becomes its own "company".
			sld = _registrable_domain(domain).split('.')[0]

			# Skip if it's an excluded common domain or matches user's domain
			if sld.lower() in excluded_domains or sld.lower() == user_sld.lower():
				continue

			if sld and len(sld) >= 3:
				# Title case the SLD for cleaner names
				competitors.add(sld.title())

	# Strategy 2: DISABLED - Too unreliable, creates false positives
	# Only use URL-based and domain mention extraction

	# Strategy 3: Extract brand names from text - VERY STRICT RULES
	# Only accept brands that appear with .com/.io/.net/.org in text OR
	# are single compound words with clear mixed case (e.g., FlyNax, OxyClassifieds)

	# Pattern 1: Brand names with domain extensions mentioned in text
	# E.g., "FlyNax.com" or "visit OxyClassifieds.io"
	domain_mention_pattern = r'([A-Z][a-zA-Z]+)\.(com|io|net|org|co)\b'
	domain_matches = re.findall(domain_mention_pattern, text, re.IGNORECASE)

	# NOTE: `excluded_domains` is defined inside the URL strategy above, so it is
	# re-stated here rather than reached into; the text strategy previously
	# applied no exclusions at all, which is how "Wikipedia.org" in prose became
	# a tracked competitor.
	_text_excluded = {
		'google', 'facebook', 'twitter', 'linkedin', 'instagram', 'youtube',
		'github', 'stackoverflow', 'wikipedia', 'medium', 'amazon', 'reddit',
		'quora', 'tripadvisor', 'yelp', 'forbes', 'bloomberg', 'investopedia',
	}
	for match in domain_matches:
		brand_name = match[0].strip()
		if not brand_name or len(brand_name) < 3:
			continue
		if brand_name.lower() in {user_sld.lower()} | _text_excluded:
			continue
		competitors.add(brand_name)

	# Pattern 2: Single-word compound brands in numbered lists
	# Must be CamelCase or mixed case (e.g., FlyNax, OxyClassifieds, ClassiPress)
	# Pattern: "1. **BrandName**:" where BrandName is a single compound word
	single_brand_pattern = r'[\d\.\*\-•]\s+\*\*([A-Z][a-z]*[A-Z][a-zA-Z]+)\*\*\s*:'
	single_brand_matches = re.findall(single_brand_pattern, text)

	# Very strict filtering for single brands
	excluded_generic = {
		'creating', 'monetization', 'engagement', 'management', 'integration',
		'features', 'benefits', 'overview', 'pricing', 'examples', 'solutions',
		'marketplace', 'classified', 'wordpress', 'plugins', 'ecommerce'
	}

	for name in single_brand_matches:
		name = name.strip()
		if not name or len(name) < 3:
			continue

		# Skip if matches user's domain
		if name.lower() == user_sld.lower():
			continue

		# Must be a single word (no spaces)
		if ' ' in name:
			continue

		# Skip generic terms
		if name.lower() in excluded_generic:
			continue

		# Must have at least 2 capital letters (indicates compound brand name)
		capital_count = sum(1 for c in name if c.isupper())
		if capital_count >= 2:
			competitors.add(name)

	# Deduplicate by lowercase (keep the version with most capitals for brand consistency)
	# E.g., keep "FlyNax" instead of "flynax"
	deduplicated = {}
	for comp in competitors:
		comp_lower = comp.lower()
		if comp_lower not in deduplicated:
			deduplicated[comp_lower] = comp
		else:
			# Keep the version with more capital letters (more likely the official brand name)
			existing = deduplicated[comp_lower]
			if sum(1 for c in comp if c.isupper()) > sum(1 for c in existing if c.isupper()):
				deduplicated[comp_lower] = comp

	# Convert to list and return (limit to top 20 to avoid noise)
	competitor_list = sorted(list(deduplicated.values()))[:20]
	return competitor_list


# `_count_mentions_with_word_boundaries` was removed with the pattern lists it
# served: span-deduplicated counting now lives in BrandIdentity.mention_count,
# which counts regex word-groups rather than pre-escaped literal strings.


def _basic_text_metrics(text: str, user_domain: str, brand_name: str = "") -> Dict[str, Any]:
	# One identity, derived from the URL the brand owns AND the name people
	# write it as. Deriving it from the name alone — and treating that name as a
	# hostname — is what recorded 87 real mentions of CanaraHSBC as zero.
	identity = build_brand_identity(user_domain or "", brand_name or "")

	all_citation_matches = identity.citation_urls(text)
	has_citation = len(all_citation_matches) > 0

	mention_count = identity.mention_count(text)
	has_mention = mention_count > 0

	# FIXED: Use only domain-specific URLs for citation_count (Option B)
	# Citations should only count URLs that reference the brand/domain
	citation_count = len(all_citation_matches)  # Only domain URLs
	
	# Keep all_urls for reference but don't use for citation_count
	all_url_pattern = r"https?://[^\s\)\]]+"
	all_urls = re.findall(all_url_pattern, text, flags=re.IGNORECASE)
	
	polarity = 0.0
	sentiment = "neutral"
	if TextBlob is not None:
		blob = TextBlob(text)
		polarity = float(getattr(getattr(blob, 'sentiment', None), 'polarity', 0.0) or 0.0)
		if polarity > 0.1:
			sentiment = "positive"
		elif polarity < -0.1:
			sentiment = "negative"

	# Extract competitor mentions from the response text
	competitor_mentions = _extract_competitor_mentions(text, user_domain, all_urls)

	return {
		"is_mention": has_mention or has_citation,
		"mention_count": mention_count,
		"citations": all_citation_matches,
		"sentiment": sentiment,
		"sentiment_score": round(polarity, 3),
		"context_summary": text,
		"citation_count": citation_count,  # Now uses only domain URLs
		"has_citation": has_citation,
		"all_urls": all_urls,  # Kept for reference but not used for citation_count
		"competitor_mention_list": competitor_mentions,  # NEW: List of competitor names
	}


def process_prompt_with_chatgpt(prompt_text: str, user_domain: str, client: Any, group: Any = None) -> Dict[str, Any]:
    try:
        country_text = _resolve_country_text(group)
        # OpenRouter slug — a bare OpenAI model id is not valid on OpenRouter and
        # 404s, so the fallback carries the prefix.
        model_name = getattr(settings, 'OPENAI_CHATGPT_MODEL', 'openai/gpt-5-mini')
        user_message = _build_analytics_user_prompt(prompt_text, country_text)

        text = ""
        # Prefer the Responses API with the web_search tool so the model browses
        # before answering (mirrors ChatGPT.com behaviour and unblocks current-year
        # info even when the training cutoff is older). Falls back silently if the
        # installed SDK / model / key doesn't support it.
        if getattr(settings, 'OPENAI_CHATGPT_WEB_SEARCH', True):
            try:
                grounded_system = (
                    f"{_today_context_line()} "
                    "You are a helpful assistant with live web search. Use the web_search tool "
                    "for any information that could be time-sensitive, then cite the sources you "
                    f"found. Always answer in the context of {country_text} unless the user specifies otherwise."
                )
                resp = client.responses.create(
                    model=model_name,
                    tools=[{"type": "web_search"}],
                    input=[
                        {"role": "system", "content": grounded_system},
                        {"role": "user", "content": user_message},
                    ],
                    timeout=90,
                )
                text = getattr(resp, "output_text", "") or ""
                if not text and getattr(resp, "output", None):
                    parts = []
                    for item in resp.output:
                        for c in getattr(item, "content", []) or []:
                            chunk = getattr(c, "text", None)
                            if chunk:
                                parts.append(chunk)
                    text = "\n".join(parts)
            except Exception as ws_err:
                logger.warning(f"ChatGPT web_search path failed, falling back: {ws_err}")
                text = ""

        if not text:
            system_prompt = (
                f"{_today_context_line()} "
                "You are a helpful assistant answering from your training knowledge. "
                "Provide comprehensive, well-cited answers and clearly flag any information "
                "that may be out of date relative to today. "
                f"Always provide answers in the context of {country_text} unless the user specifies another country."
            )
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.7,
                max_tokens=getattr(settings, 'LLM_MAX_OUTPUT_TOKENS', 8000),
                timeout=60,
            )
            text = response.choices[0].message.content or ""

        # A reasoning model returns content=None when the token ceiling is eaten
        # by hidden reasoning before any text is emitted. Fail loudly instead of
        # letting an empty answer be recorded as a genuine "brand not mentioned"
        # result, which would silently deflate the score rather than surface the
        # problem. Mirrors the Perplexity path's empty-response guard.
        if not text:
            raise Exception("ChatGPT returned an empty response")

        # Same identity rules as every other platform — this block used to be a
        # second, drifting copy of the pattern list in _basic_text_metrics.
        identity = build_brand_identity(user_domain or "", _brand_name_of(group))

        all_citation_matches = identity.citation_urls(text)
        has_citation = len(all_citation_matches) > 0

        # FIXED: Use only domain-specific URLs for citation_count (Option B)
        # Citations should only count URLs that reference the brand/domain
        citation_count = len(all_citation_matches)  # Only domain URLs

        # Keep all_urls for reference but don't use for citation_count
        all_urls = re.findall(r"https?://[^\s\)\]]+", text, flags=re.IGNORECASE)

        mention_count = identity.mention_count(text)

        polarity = 0.0
        sentiment = "neutral"
        if TextBlob is not None:
            blob = TextBlob(text)
            polarity = float(getattr(getattr(blob, 'sentiment', None), 'polarity', 0.0) or 0.0)
            if polarity > 0.1:
                sentiment = "positive"
            elif polarity < -0.1:
                sentiment = "negative"

        # Extract competitor mentions from the response text
        competitor_mentions = _extract_competitor_mentions(text, user_domain, all_urls)

        print({
            "response_text": text,
            "is_mention": (mention_count > 0) or has_citation,
            "mention_count": mention_count,
            "citations": all_citation_matches,
            "sentiment": sentiment,
            "sentiment_score": round(polarity, 3),
            "context_summary": text,
            "citation_count": citation_count,
            "has_citation": has_citation,
            "all_urls": all_urls,
            "competitor_mention_list": competitor_mentions,
        })

        return {
            "response_text": text,
            "is_mention": (mention_count > 0) or has_citation,
            "mention_count": mention_count,
            "citations": all_citation_matches,
            "sentiment": sentiment,
            "sentiment_score": round(polarity, 3),
            "context_summary": text,
            "citation_count": citation_count,
            "has_citation": has_citation,
            "all_urls": all_urls,
            "competitor_mention_list": competitor_mentions,  # NEW: List of competitor names
        }
        
        
    except Exception as e:
        logger.error(f"ChatGPT processing failed: {e}")
        raise


# Models that have already rejected Google Search grounding. Sending the wrong
# tool name made every grounded call fail, which silently doubled the number of
# Gemini requests per prompt (one failed grounded call + one ungrounded fallback).
# Caching the failure keeps steady-state cost at one API call per prompt.
_GEMINI_GROUNDING_UNSUPPORTED: set = set()


def _gemini_search_tool(model_name: str) -> Dict[str, Any]:
    """Return the Google Search grounding tool config for this model generation.

    Gemini 1.5 uses ``google_search_retrieval``; 2.x and later use ``google_search``.
    """
    if '1.5' in (model_name or '').lower():
        return {"google_search_retrieval": {}}
    return {"google_search": {}}


def _build_gemini_prompt(prompt_text: str, country_text: str) -> str:
    """Shared prompt body so the AI Studio and Vertex paths stay identical."""
    return (
        f"{_today_context_line()}\n\n"
        f"Original Question: {prompt_text}\n\n"
        f"Context: Always provide answers in the context of {country_text} unless the user specifies another country.\n\n"
        "Based on your knowledge, please provide a comprehensive and detailed response with:\n\n"
        "1. A thorough answer incorporating the latest information\n"
        "2. Include all relevant URLs and links\n"
        "3. Mention specific companies, tools, platforms, and services\n"
        "4. Provide detailed citations with current sources and dates where possible\n"
        "5. Include pricing information, features, and comparisons from the most recent data\n"
        "6. Add any additional current resources, alternatives, or related tools\n"
        "7. Highlight which information comes from recent sources vs general knowledge\n\n"
        "Format your response with proper current links, detailed descriptions, and up-to-date references. "
        "Focus on providing the most current and relevant information available."
    )


# Cached Vertex client. Building it performs credential discovery, so it is reused
# for the life of the worker process (same rationale as the ClientFactory cache).
_VERTEX_CLIENT: Any = None


def _gemini_vertex_client() -> Any:
    """Return a cached google-genai client bound to Vertex AI."""
    global _VERTEX_CLIENT
    if _VERTEX_CLIENT is None:
        from google import genai as genai_sdk

        project = getattr(settings, 'VERTEX_PROJECT', None)
        if not project:
            raise RuntimeError(
                "GEMINI_BACKEND=vertex requires VERTEX_PROJECT to be set "
                "(and GOOGLE_APPLICATION_CREDENTIALS pointing at a service-account JSON)."
            )
        _VERTEX_CLIENT = genai_sdk.Client(
            vertexai=True,
            project=project,
            location=getattr(settings, 'VERTEX_LOCATION', 'us-central1'),
        )
    return _VERTEX_CLIENT


def _is_rate_limited(exc: Exception) -> bool:
    """Is this a 429 from Vertex, as opposed to a real failure?

    The SDK surfaces the status in different places depending on version and on
    whether the error came back as a typed error or a transport exception, so
    the code attribute is checked first and the message only as a fallback.
    """
    for attr in ('code', 'status_code'):
        if getattr(exc, attr, None) == 429:
            return True
    text = str(exc)
    return '429' in text or 'RESOURCE_EXHAUSTED' in text


def _call_with_backoff(fn, label: str):
    """Run a Vertex call, retrying only on 429.

    Exponential with full jitter. The jitter is the point, not a detail: twelve
    worker threads hit the limit within the same second, and a fixed backoff
    would march them all into the next window together and collide again.

    Anything that is not a 429 is re-raised immediately — retrying a bad request
    or an auth failure would just spend the wait budget before failing anyway.
    """
    attempts = max(0, int(getattr(settings, 'GEMINI_RATE_LIMIT_RETRIES', 4)))
    base = float(getattr(settings, 'GEMINI_RATE_LIMIT_BASE_DELAY', 2.0))
    max_wait = float(getattr(settings, 'GEMINI_RATE_LIMIT_MAX_WAIT', 90.0))

    waited = 0.0
    for attempt in range(attempts + 1):
        try:
            return fn()
        except Exception as exc:
            if not _is_rate_limited(exc) or attempt == attempts:
                raise
            delay = random.uniform(0, base * (2 ** attempt))
            if waited + delay > max_wait:
                logger.warning(
                    "Gemini rate limited on %s; wait budget %.0fs exhausted after "
                    "%d attempts, giving up.", label, max_wait, attempt + 1,
                )
                raise
            waited += delay
            logger.info(
                "Gemini rate limited on %s (attempt %d/%d); retrying in %.1fs.",
                label, attempt + 1, attempts + 1, delay,
            )
            time.sleep(delay)


def _process_prompt_with_gemini_vertex(prompt_text: str, user_domain: str, group: Any = None) -> Dict[str, Any]:
    """Vertex AI path for Gemini.

    Vertex authenticates with Application Default Credentials rather than an API
    key, so any per-organisation BYOK key is intentionally not used here - every
    call bills to VERTEX_PROJECT. Grounding stays behind GEMINI_WEB_SEARCH because
    on Vertex each grounded query is billed separately from tokens.
    """
    from google.genai import types as genai_types

    country_text = _resolve_country_text(group)
    prompt = _build_gemini_prompt(prompt_text, country_text)
    model_name = getattr(settings, 'VERTEX_GEMINI_MODEL', 'gemini-2.5-flash')
    client = _gemini_vertex_client()

    # Gemini 2.5 thinks by default and bills those tokens as output, which buys
    # nothing for mention detection. A negative budget leaves the model default.
    thinking_budget = int(getattr(settings, 'VERTEX_THINKING_BUDGET', 0))

    def _call(tools: Any) -> Any:
        config_kwargs: Dict[str, Any] = {
            'temperature': 0.7,
            'top_k': 40,
            'top_p': 0.95,
            'max_output_tokens': getattr(settings, 'LLM_MAX_OUTPUT_TOKENS', 8000),
            'tools': tools,
        }
        if thinking_budget >= 0:
            try:
                config_kwargs['thinking_config'] = genai_types.ThinkingConfig(
                    thinking_budget=thinking_budget
                )
            except Exception:
                # Older SDKs / non-thinking models do not expose ThinkingConfig.
                pass
        return client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=genai_types.GenerateContentConfig(**config_kwargs),
        )

    text = ""
    use_grounding = (
        getattr(settings, 'GEMINI_WEB_SEARCH', True)
        and model_name not in _GEMINI_GROUNDING_UNSUPPORTED
    )
    if use_grounding:
        try:
            text = getattr(_call_with_backoff(
                lambda: _call([genai_types.Tool(google_search=genai_types.GoogleSearch())]),
                'grounded generation',
            ), 'text', '') or ""
        except Exception as ws_err:
            # A rate limit says nothing about whether this model supports
            # grounding. Adding it to the unsupported set on a 429 would
            # silently disable grounding for the rest of the process over a
            # transient error.
            if _is_rate_limited(ws_err):
                raise
            _GEMINI_GROUNDING_UNSUPPORTED.add(model_name)
            logger.warning(
                "Vertex Gemini grounding unavailable for %s (%s); using ungrounded generation.",
                model_name, ws_err,
            )
            text = ""

    if not text:
        text = getattr(_call_with_backoff(lambda: _call(None), 'generation'), 'text', '') or ""
    return _basic_text_metrics(text, user_domain, _brand_name_of(group))


def process_prompt_with_gemini_wrapper(prompt_text: str, user_domain: str, client: Any = None, group: Any = None) -> Dict[str, Any]:
    try:
        # GEMINI_BACKEND=vertex routes through Vertex AI (billed to a GCP project);
        # anything else keeps the default API-key path. Reverting is env-only.
        if str(getattr(settings, 'GEMINI_BACKEND', 'aistudio')).lower() == 'vertex':
            return _process_prompt_with_gemini_vertex(prompt_text, user_domain, group)

        country_text = _resolve_country_text(group)
        import google.generativeai as genai
        genai.configure(api_key=(client or {}).get('api_key'), transport="rest")
        model_name = getattr(settings, 'GEMINI_MODEL', 'gemini-2.0-flash')
        prompt = _build_gemini_prompt(prompt_text, country_text)
        gen_config = genai.types.GenerationConfig(
            temperature=0.7,
            top_k=40,
            top_p=0.95,
            max_output_tokens=getattr(settings, 'LLM_MAX_OUTPUT_TOKENS', 8000),
        )

        text = ""
        # Use Google Search grounding when enabled so Gemini browses live (matches
        # the Gemini app behaviour). The tool name differs by model generation, and
        # once a model is known to reject grounding we skip the attempt entirely so
        # each prompt costs one API call instead of two.
        use_grounding = (
            getattr(settings, 'GEMINI_WEB_SEARCH', True)
            and model_name not in _GEMINI_GROUNDING_UNSUPPORTED
        )
        if use_grounding:
            try:
                grounded_model = genai.GenerativeModel(
                    model_name,
                    tools=[_gemini_search_tool(model_name)],
                )
                grounded = grounded_model.generate_content(prompt, generation_config=gen_config)
                text = grounded.text if getattr(grounded, 'text', None) else ""
            except Exception as ws_err:
                # Grounding is unavailable for this model/key. Remember it so we stop
                # paying for a failing grounded call on every subsequent prompt.
                _GEMINI_GROUNDING_UNSUPPORTED.add(model_name)
                logger.warning(
                    "Gemini grounding unavailable for %s (%s); disabling grounded "
                    "calls for this process and using ungrounded generation.",
                    model_name, ws_err,
                )
                text = ""

        if not text:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt, generation_config=gen_config)
            text = response.text if getattr(response, 'text', None) else ""
        return _basic_text_metrics(text, user_domain, _brand_name_of(group))
    except Exception as e:
        logger.error(f"Gemini processing failed: {e}")
        raise


def _extract_sonar_citations(response: Any) -> list:
    """Collect Sonar's source URLs from a chat-completions response.

    Two shapes have to be handled because the transport changed: the direct
    Perplexity API puts them in a top-level ``citations`` list, while OpenRouter
    normalises web-search sources into per-message ``annotations`` of type
    ``url_citation``. OpenRouter currently passes ``citations`` through as well,
    but reading both means the Citations page keeps working whichever one a
    given response carries. Order is preserved and duplicates dropped.
    """
    urls = []
    seen = set()

    def _add(url: Any) -> None:
        if isinstance(url, str) and url and url not in seen:
            seen.add(url)
            urls.append(url)

    for citation in getattr(response, 'citations', None) or []:
        # Legacy shape is a bare URL string; newer payloads use {"url": ...}.
        _add(citation.get('url') if isinstance(citation, dict) else citation)

    for choice in getattr(response, 'choices', None) or []:
        message = getattr(choice, 'message', None)
        for annotation in getattr(message, 'annotations', None) or []:
            if isinstance(annotation, dict):
                citation = annotation.get('url_citation') or {}
            else:
                citation = getattr(annotation, 'url_citation', None) or {}
            _add(citation.get('url') if isinstance(citation, dict) else getattr(citation, 'url', None))

    return urls


def process_prompt_with_perplexity_wrapper(prompt_text: str, user_domain: str, client: Any = None, group: Any = None) -> Dict[str, Any]:
    """Process a prompt with Perplexity using the OpenAI-compatible API.

    The ``client`` parameter is an OpenAI client instance created by
    ``client_factory.py``, pointed at OpenRouter rather than api.perplexity.ai
    (see OPENROUTER_ROUTED in api_key_service.py). We call the chat completions
    endpoint with the Sonar model, which has built-in web search and returns
    citations alongside the response.
    """
    try:
        country_text = _resolve_country_text(group)
        # OpenRouter slug — `perplexity/sonar`, not the bare `sonar` the direct
        # Perplexity API expects.
        model_name = getattr(settings, 'PERPLEXITY_MODEL', 'perplexity/sonar')
        user_message = _build_analytics_user_prompt(prompt_text, country_text)

        text = ""
        try:
            # client is an OpenAI-compatible client from client_factory
            # (base_url already set to OpenRouter)
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": (
                        f"{_today_context_line()} "
                        "You are a helpful assistant with access to the web. "
                        "Provide comprehensive, well-cited answers with URLs. "
                        f"Always provide answers in the context of {country_text} "
                        "unless the user specifies another country."
                    )},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.7,
                max_tokens=getattr(settings, 'LLM_MAX_OUTPUT_TOKENS', 8000),
                timeout=90,
            )
            text = response.choices[0].message.content if response.choices else ""

            # Sonar returns its sources out-of-band rather than in the prose, so
            # they are appended to the text for _basic_text_metrics to extract.
            citation_urls = _extract_sonar_citations(response)
            if citation_urls:
                sources = "\n".join(f"Source: {url}" for url in citation_urls)
                text = f"{text}\n\nCitations:\n{sources}"

            if text:
                logger.info(f"Perplexity API returned response of length {len(text)} for query: {prompt_text[:50]}...")
            else:
                logger.warning(f"Perplexity API returned no response content for query: {prompt_text[:50]}...")

        except Exception as lib_error:
            logger.error(f"Perplexity API call failed: {str(lib_error)}")
            text = ""

        return _basic_text_metrics(text or "", user_domain, _brand_name_of(group))
    except Exception as e:
        logger.error(f"Perplexity processing failed: {e}")
        raise


def _today_context_line() -> str:
    """Single line of date/recency context injected into every LLM call.

    Without this, LLMs answer as of their training cutoff and confidently
    cite years-old articles as "current" — leading to responses that
    reference 2023 sources when the actual date is years later. Telling
    the model what date it is doesn't grant new knowledge, but it forces
    the model to flag stale info instead of presenting it as current."""
    from datetime import date as _date
    today = _date.today()
    return (
        f"Today's date is {today.strftime('%B %d, %Y')} ({today.isoformat()}). "
        "Prioritize the most recent information you have. If your knowledge of a "
        "topic is older than 6 months relative to today, say so explicitly and "
        "label that information as potentially outdated. Do not present pre-cutoff "
        "information as 'current' or 'recent' without qualifying it."
    )


def _build_analytics_user_prompt(prompt_text: str, country_text: str) -> str:
    """Shared user-message body for the new providers — same shape as ChatGPT/Gemini paths."""
    return (
        f"{_today_context_line()}\n\n"
        f"Original Question: {prompt_text}\n\n"
        f"Context: Always provide answers in the context of {country_text} unless the user specifies another country.\n\n"
        "Based on your knowledge, please provide a comprehensive and detailed response with:\n\n"
        "1. A thorough answer incorporating the latest information\n"
        "2. Include all relevant URLs and links\n"
        "3. Mention specific companies, tools, platforms, and services\n"
        "4. Provide detailed citations with current sources and dates where possible\n"
        "5. Include pricing information, features, and comparisons from the most recent data\n"
        "6. Add any additional current resources, alternatives, or related tools\n"
        "7. Highlight which information comes from recent sources vs general knowledge\n\n"
        "Format your response with proper current links, detailed descriptions, and up-to-date references. "
        "Focus on providing the most current and relevant information available."
    )


def _resolve_country_text(group: Any) -> str:
    if group and hasattr(group, 'domain') and group.domain and hasattr(group.domain, 'country'):
        return group.domain.country or "United States"
    return "United States"


def process_prompt_with_claude(prompt_text: str, user_domain: str, client: Any = None, group: Any = None) -> Dict[str, Any]:
    try:
        from .services.openrouter_client import OpenRouterAnthropicClient
        # ClientFactory passes a ready OpenRouter-backed Claude client — use it
        # directly. Only build one from .env when no client was supplied (calling
        # cfg.get() on the client object raised TypeError and silently killed
        # Claude tracking).
        anthropic_client = client if isinstance(client, OpenRouterAnthropicClient) else OpenRouterAnthropicClient(
            api_key=getattr(settings, 'OPENROUTER_API_KEY', None),
            base_url=getattr(settings, 'OPENROUTER_BASE_URL', None),
            timeout=60,
            site_url=getattr(settings, 'OPENROUTER_SITE_URL', None),
            site_title=getattr(settings, 'OPENROUTER_SITE_TITLE', None),
        )
        country_text = _resolve_country_text(group)
        model_name = getattr(settings, 'ANTHROPIC_MODEL', 'anthropic/claude-sonnet-5')
        user_message = _build_analytics_user_prompt(prompt_text, country_text)

        text = ""
        # Ask for live browsing first so the model answers on current information.
        # The web_search tool below is Anthropic's spelling; the OpenRouter adapter
        # translates it into OpenRouter's `web` plugin, which uses a different
        # search backend than Anthropic's native tool. Falls back to the plain
        # messages call below if the grounded call fails.
        if getattr(settings, 'ANTHROPIC_WEB_SEARCH', True):
            try:
                grounded_system = (
                    f"{_today_context_line()} "
                    "You are a helpful assistant with live web search. Use the web_search tool "
                    "whenever information could be time-sensitive, and cite the sources you find. "
                    f"Always answer in the context of {country_text} unless the user specifies otherwise."
                )
                grounded = anthropic_client.messages.create(
                    model=model_name,
                    max_tokens=getattr(settings, 'LLM_MAX_OUTPUT_TOKENS', 8000),
                    temperature=0.7,
                    system=grounded_system,
                    tools=[{
                        "type": "web_search_20250305",
                        "name": "web_search",
                        "max_uses": 5,
                    }],
                    messages=[{"role": "user", "content": user_message}],
                )
                for block in getattr(grounded, 'content', []) or []:
                    if getattr(block, 'type', None) == 'text':
                        text += getattr(block, 'text', '') or ''
            except Exception as ws_err:
                logger.warning(f"Claude web_search path failed, falling back: {ws_err}")
                text = ""

        if not text:
            system_prompt = (
                f"{_today_context_line()} "
                "You are a helpful assistant. Provide comprehensive, well-cited answers. "
                f"Always provide answers in the context of {country_text} unless the user specifies another country."
            )
            response = anthropic_client.messages.create(
                model=model_name,
                max_tokens=getattr(settings, 'LLM_MAX_OUTPUT_TOKENS', 8000),
                temperature=0.7,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            for block in getattr(response, 'content', []) or []:
                if getattr(block, 'type', None) == 'text':
                    text += getattr(block, 'text', '') or ''
        return _basic_text_metrics(text, user_domain, _brand_name_of(group))
    except Exception as e:
        logger.error(f"Claude processing failed: {e}")
        raise


def process_prompt_with_grok(prompt_text: str, user_domain: str, client: Any = None, group: Any = None) -> Dict[str, Any]:
    try:
        from openai import OpenAI
        # ClientFactory passes a ready OpenAI-compatible xAI client — use it directly.
        xai_client = client if isinstance(client, OpenAI) else OpenAI(
            api_key=getattr(settings, 'XAI_API_KEY', None),
            base_url='https://api.x.ai/v1',
            timeout=60,
        )
        country_text = _resolve_country_text(group)
        model_name = getattr(settings, 'XAI_MODEL', 'grok-2-latest')
        user_message = _build_analytics_user_prompt(prompt_text, country_text)

        text = ""
        # Use xAI Live Search (search_parameters) to ground the answer in current
        # web data when enabled. xAI extends the OpenAI-compatible API with this
        # extra_body param. Falls back to a plain completion on any error.
        if getattr(settings, 'XAI_WEB_SEARCH', True):
            try:
                grounded_system = (
                    f"{_today_context_line()} "
                    "You are a helpful assistant with live web search. Browse for any "
                    "time-sensitive information and cite your sources. "
                    f"Always answer in the context of {country_text} unless the user specifies otherwise."
                )
                grounded = xai_client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": grounded_system},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=0.7,
                    max_tokens=getattr(settings, 'LLM_MAX_OUTPUT_TOKENS', 8000),
                    timeout=90,
                    extra_body={"search_parameters": {"mode": "auto"}},
                )
                text = grounded.choices[0].message.content if grounded.choices else ""
            except Exception as ws_err:
                logger.warning(f"Grok live-search path failed, falling back: {ws_err}")
                text = ""

        if not text:
            system_prompt = (
                f"{_today_context_line()} "
                "You are a helpful assistant. Provide comprehensive, well-cited answers and "
                "flag any information that may be out of date relative to today. "
                f"Always provide answers in the context of {country_text} unless the user specifies another country."
            )
            response = xai_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.7,
                max_tokens=getattr(settings, 'LLM_MAX_OUTPUT_TOKENS', 8000),
                timeout=60,
            )
            text = response.choices[0].message.content if response.choices else ""
        return _basic_text_metrics(text or "", user_domain, _brand_name_of(group))
    except Exception as e:
        logger.error(f"Grok processing failed: {e}")
        raise


def process_prompt_with_deepseek(prompt_text: str, user_domain: str, client: Any = None, group: Any = None) -> Dict[str, Any]:
    try:
        from openai import OpenAI
        # ClientFactory passes a ready OpenAI-compatible DeepSeek client — use it directly.
        ds_client = client if isinstance(client, OpenAI) else OpenAI(
            api_key=getattr(settings, 'DEEPSEEK_API_KEY', None),
            base_url='https://api.deepseek.com/v1',
            timeout=60,
        )
        country_text = _resolve_country_text(group)
        system_prompt = (
            f"{_today_context_line()} "
            "You are a helpful assistant. Provide comprehensive, well-cited answers and "
            "flag any information that may be out of date relative to today. "
            f"Always provide answers in the context of {country_text} unless the user specifies another country."
        )
        model_name = getattr(settings, 'DEEPSEEK_MODEL', 'deepseek-chat')
        response = ds_client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": _build_analytics_user_prompt(prompt_text, country_text)},
            ],
            temperature=0.7,
            max_tokens=getattr(settings, 'LLM_MAX_OUTPUT_TOKENS', 8000),
            timeout=60,
        )
        text = response.choices[0].message.content if response.choices else ""
        return _basic_text_metrics(text or "", user_domain, _brand_name_of(group))
    except Exception as e:
        logger.error(f"DeepSeek processing failed: {e}")
        raise
