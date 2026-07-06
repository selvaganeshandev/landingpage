from __future__ import annotations

import re
import logging
from typing import Any, Dict, List, Optional

from django.conf import settings

try:
	from textblob import TextBlob
except Exception:  # pragma: no cover
	TextBlob = None  # type: ignore

logger = logging.getLogger(__name__)


def process_prompt_with_gemini(prompt_text: str, user_domain: str, client: Any = None, group: Any = None) -> Dict[str, Any]:
    """Direct Gemini processor; currently delegates to wrapper implementation."""
    return process_prompt_with_gemini_wrapper(prompt_text, user_domain, client, group)


def process_prompt_with_perplexity(prompt_text: str, user_domain: str, client: Any = None, group: Any = None) -> Dict[str, Any]:
    """Direct Perplexity processor; currently delegates to wrapper implementation."""
    return process_prompt_with_perplexity_wrapper(prompt_text, user_domain, client, group)

def get_openai_client(org_id: Optional[int] = None):
	"""
	Return an OpenAI client. Delegates to ClientFactory which applies:
	  1. Organisation DB key (BYOK)
	  2. .env OPENAI_API_KEY fallback
	Accepts optional org_id for per-organisation key resolution.
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


def extract_position_from_response(response: str, user_domain: str, citation_urls: Optional[List[str]] = None, has_mention: bool = False) -> Optional[int]:
	if not response:
		return None
	clean = _get_domain_from_url(user_domain)
	if not clean:
		return None
	sld = clean.split(".")[0] if clean else ""
	brand_variations = [
		clean.lower(),
		sld.lower(),
		clean.replace(".com", "").replace(".org", "").replace(".net", "").replace(".io", "").lower(),
		sld.replace(" ", "").lower(),
		sld.replace(" ", "-").lower(),
		sld.replace(" ", "_").lower(),
	]
	brand_variations = [v for v in brand_variations if v and len(v) >= 3]
	lines = response.split("\n")
	found_position = None
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
			search_window = ' '.join(lines[i:min(i + 5, len(lines))]).lower()
			if any(variant in search_window for variant in brand_variations):
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
			context = full_text_lower[max(0, idx - 500): idx + 500]
			if any(variant in context for variant in brand_variations):
				m = re.search(r'(\d+)[\.\)\:]', context)
				if m:
					position = int(m.group(1))
					# Validate position is reasonable (1-100), not a year or other large number
					if 1 <= position <= 100:
						return position
				# If no valid position found but brand + citation exists, default to 1
				return 1
	if has_mention and any(v in response.lower() for v in brand_variations):
		return 1
	return None


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
		excluded_domains = {
			'google', 'facebook', 'twitter', 'linkedin', 'instagram', 'youtube',
			'github', 'stackoverflow', 'wikipedia', 'medium', 'amazon', 'aws',
			'microsoft', 'apple', 'w3', 'mozilla', 'chrome', 'example', 'test',
			'localhost', 'schema', 'json', 'xml'
		}

		for url in all_urls:
			domain = _get_domain_from_url(url)
			if not domain or domain == user_domain_clean:
				continue

			# Extract SLD (second-level domain) as potential competitor name
			sld = domain.split('.')[0] if domain else ""

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

	for match in domain_matches:
		brand_name = match[0].strip()
		if brand_name and len(brand_name) >= 3 and brand_name.lower() != user_sld.lower():
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


def _count_mentions_with_word_boundaries(text: str, mention_patterns: List[str]) -> int:
	"""
	Count mentions using regex with word boundaries to avoid overlaps.
	Deduplicates by matched span ranges to prevent double-counting.

	Args:
		text: Text to search in
		mention_patterns: List of patterns to search for

	Returns:
		Count of unique mentions (non-overlapping matches)
	"""
	if not text or not mention_patterns:
		return 0
	
	# Track matched spans to avoid overlaps
	matched_spans = []
	text_lower = text.lower()
	
	for pattern in mention_patterns:
		if not pattern or len(pattern) < 3:
			continue
		
		# Escape special regex characters in pattern
		escaped_pattern = re.escape(pattern.lower())
		# Use word boundaries to match whole words only
		# \b matches word boundaries (between word and non-word characters)
		pattern_regex = r'\b' + escaped_pattern + r'\b'
		
		try:
			# Find all non-overlapping matches
			for match in re.finditer(pattern_regex, text_lower, flags=re.IGNORECASE):
				span = match.span()  # (start, end) tuple
				
				# Check if this span overlaps with any existing match
				overlaps = False
				for existing_span in matched_spans:
					# Check for overlap: spans overlap if one starts before the other ends
					if not (span[1] <= existing_span[0] or span[0] >= existing_span[1]):
						overlaps = True
						break
				
				# Only add if no overlap
				if not overlaps:
					matched_spans.append(span)
		except re.error as e:
			logger.warning(f"Regex error for pattern '{pattern}': {e}")
			continue
	
	return len(matched_spans)


def _basic_text_metrics(text: str, user_domain: str) -> Dict[str, Any]:
	clean = _get_domain_from_url(user_domain)
	sld = clean.split(".")[0] if clean else ""
	escaped_domain = re.escape(clean.replace('.', r'\.'))
	direct_citation_pattern = r"https?://[^\s\)\]]*" + escaped_domain + r"[^\s\)\]]*"
	direct_citation_matches = re.findall(direct_citation_pattern, text, flags=re.IGNORECASE)
	escaped_sld = re.escape(sld.replace(' ', '[-_]?'))
	brand_in_url_pattern = r"https?://[^\s\)\]]*" + escaped_sld + r"[^\s\)\]]*"
	brand_url_matches = re.findall(brand_in_url_pattern, text, flags=re.IGNORECASE)
	all_citation_matches = list(set(direct_citation_matches + brand_url_matches))
	has_citation = len(all_citation_matches) > 0
	
	# Build mention patterns list
	mention_patterns = [p for p in [
		clean, 
		sld, 
		clean.replace('.com','').replace('.org','').replace('.net','').replace('.io',''), 
		sld.replace(' ',''), 
		sld.replace(' ','-'), 
		sld.replace(' ','_')
	] if p and len(p) >= 3]
	
	# Count mentions using regex with word boundaries and deduplication
	mention_count = _count_mentions_with_word_boundaries(text, mention_patterns)
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
        model_name = getattr(settings, 'OPENAI_CHATGPT_MODEL', 'gpt-4o')
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
                max_tokens=3000,
                timeout=60,
            )
            text = response.choices[0].message.content

        domain_clean = _get_domain_from_url(user_domain)
        sld = domain_clean.split('.') [0] if domain_clean else ""

        escaped_domain = re.escape(domain_clean.replace('.', r'\.'))
        direct_citation_pattern = r"https?://[^\s\)\]]*" + escaped_domain + r"[^\s\)\]]*"
        direct_citation_matches = re.findall(direct_citation_pattern, text, flags=re.IGNORECASE)

        escaped_sld = re.escape(sld.replace(' ', '[-_]?'))
        brand_in_url_pattern = r"https?://[^\s\)\]]*" + escaped_sld + r"[^\s\)\]]*"
        brand_url_matches = re.findall(brand_in_url_pattern, text, flags=re.IGNORECASE)

        all_citation_matches = list(set(direct_citation_matches + brand_url_matches))
        has_citation = len(all_citation_matches) > 0

        mention_patterns = [p for p in [
            domain_clean,
            sld,
            domain_clean.replace('.com','').replace('.org','').replace('.net','').replace('.io',''),
            sld.replace(' ', ''), sld.replace(' ', '-'), sld.replace(' ', '_')
        ] if p and len(p) >= 3]

        # FIXED: Use only domain-specific URLs for citation_count (Option B)
        # Citations should only count URLs that reference the brand/domain
        citation_count = len(all_citation_matches)  # Only domain URLs
        
        # Keep all_urls for reference but don't use for citation_count
        all_urls = re.findall(r"https?://[^\s\)\]]+", text, flags=re.IGNORECASE)
        
        # FIXED: Count mentions using regex with word boundaries and deduplication
        mention_count = _count_mentions_with_word_boundaries(text, mention_patterns)

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


def process_prompt_with_gemini_wrapper(prompt_text: str, user_domain: str, client: Any = None, group: Any = None) -> Dict[str, Any]:
    try:
        country_text = _resolve_country_text(group)
        import google.generativeai as genai
        genai.configure(api_key=(client or {}).get('api_key'), transport="rest")
        model_name = getattr(settings, 'GEMINI_MODEL', 'gemini-2.0-flash')
        prompt = (
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
        gen_config = genai.types.GenerationConfig(
            temperature=0.7,
            top_k=40,
            top_p=0.95,
            max_output_tokens=3000,
        )

        text = ""
        # Use Google Search grounding when enabled so Gemini browses live (matches
        # the Gemini app behaviour). Falls back to ungrounded generate_content if
        # the SDK / model on this key doesn't support the tool.
        if getattr(settings, 'GEMINI_WEB_SEARCH', True):
            try:
                grounded_model = genai.GenerativeModel(
                    model_name,
                    tools=[{"google_search_retrieval": {}}],
                )
                grounded = grounded_model.generate_content(prompt, generation_config=gen_config)
                text = grounded.text if getattr(grounded, 'text', None) else ""
            except Exception as ws_err:
                logger.warning(f"Gemini google_search_retrieval path failed, falling back: {ws_err}")
                text = ""

        if not text:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt, generation_config=gen_config)
            text = response.text if getattr(response, 'text', None) else ""
        return _basic_text_metrics(text, user_domain)
    except Exception as e:
        logger.error(f"Gemini processing failed: {e}")
        raise


def process_prompt_with_perplexity_wrapper(prompt_text: str, user_domain: str, client: Any = None, group: Any = None) -> Dict[str, Any]:
    """Process a prompt with Perplexity using the OpenAI-compatible API.

    The ``client`` parameter is an OpenAI client instance created by
    ``client_factory.py`` with ``base_url='https://api.perplexity.ai'``.
    We call the chat completions endpoint with the ``sonar`` model which
    has built-in web search and returns citations inline in the response.
    """
    try:
        country_text = _resolve_country_text(group)
        model_name = getattr(settings, 'PERPLEXITY_MODEL', 'sonar')
        user_message = _build_analytics_user_prompt(prompt_text, country_text)

        text = ""
        try:
            # client is an OpenAI-compatible client from client_factory
            # (base_url already set to https://api.perplexity.ai)
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
                max_tokens=3000,
                timeout=90,
            )
            text = response.choices[0].message.content if response.choices else ""

            # Perplexity may also return citations in the response metadata
            if hasattr(response, 'citations') and response.citations:
                # Append citation URLs to the text so _basic_text_metrics can extract them
                citation_urls = "\n".join(
                    f"Source: {url}" for url in response.citations if url
                )
                if citation_urls:
                    text = f"{text}\n\nCitations:\n{citation_urls}"

            if text:
                logger.info(f"Perplexity API returned response of length {len(text)} for query: {prompt_text[:50]}...")
            else:
                logger.warning(f"Perplexity API returned no response content for query: {prompt_text[:50]}...")

        except Exception as lib_error:
            logger.error(f"Perplexity API call failed: {str(lib_error)}")
            text = ""

        return _basic_text_metrics(text or "", user_domain)
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
        from anthropic import Anthropic
        cfg = client or {}
        anthropic_client = Anthropic(api_key=cfg.get('api_key'), timeout=cfg.get('timeout', 60))
        country_text = _resolve_country_text(group)
        model_name = getattr(settings, 'ANTHROPIC_MODEL', 'claude-sonnet-4-6')
        user_message = _build_analytics_user_prompt(prompt_text, country_text)

        text = ""
        # Try Claude's server-side web_search tool first so the model browses live
        # (matches Claude.ai behaviour for time-sensitive queries). Falls back to
        # the plain messages call below if tools aren't available on this key/model.
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
                    max_tokens=3000,
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
                max_tokens=3000,
                temperature=0.7,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            for block in getattr(response, 'content', []) or []:
                if getattr(block, 'type', None) == 'text':
                    text += getattr(block, 'text', '') or ''
        return _basic_text_metrics(text, user_domain)
    except Exception as e:
        logger.error(f"Claude processing failed: {e}")
        raise


def process_prompt_with_grok(prompt_text: str, user_domain: str, client: Any = None, group: Any = None) -> Dict[str, Any]:
    try:
        from openai import OpenAI
        cfg = client or {}
        xai_client = OpenAI(
            api_key=cfg.get('api_key'),
            base_url=cfg.get('base_url', 'https://api.x.ai/v1'),
            timeout=cfg.get('timeout', 60),
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
                    max_tokens=3000,
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
                max_tokens=3000,
                timeout=60,
            )
            text = response.choices[0].message.content if response.choices else ""
        return _basic_text_metrics(text or "", user_domain)
    except Exception as e:
        logger.error(f"Grok processing failed: {e}")
        raise


def process_prompt_with_deepseek(prompt_text: str, user_domain: str, client: Any = None, group: Any = None) -> Dict[str, Any]:
    try:
        from openai import OpenAI
        cfg = client or {}
        ds_client = OpenAI(
            api_key=cfg.get('api_key'),
            base_url=cfg.get('base_url', 'https://api.deepseek.com/v1'),
            timeout=cfg.get('timeout', 60),
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
            max_tokens=3000,
            timeout=60,
        )
        text = response.choices[0].message.content if response.choices else ""
        return _basic_text_metrics(text or "", user_domain)
    except Exception as e:
        logger.error(f"DeepSeek processing failed: {e}")
        raise
