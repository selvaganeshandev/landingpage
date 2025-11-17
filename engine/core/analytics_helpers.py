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

def get_openai_client():
	"""
	Initialize and return OpenAI client using settings from database or .env.
	Uses the same method as ChatGPTClient for consistency - reads from settings.OPENAI_API_KEY
	which comes from engine/.env via python-decouple.
	"""
	# First try database Settings model (if available)
	try:
		from serp.models import Settings
		settings_obj = Settings.objects.first()
		if settings_obj and settings_obj.chatgpt_enabled and settings_obj.chatgpt_api_key:
			from openai import OpenAI
			return OpenAI(api_key=settings_obj.chatgpt_api_key, timeout=60)
	except (ImportError, Exception):
		pass  # Fall through to .env method
	
	# Fallback to .env file (same as ChatGPTClient)
	api_key = getattr(settings, "OPENAI_API_KEY", None)
	if not api_key:
		raise Exception("OpenAI API key not configured. Set OPENAI_API_KEY in engine/.env file")
	
	try:
		from openai import OpenAI  # lazy import
		return OpenAI(api_key=api_key, timeout=60)
	except Exception as e:
		raise Exception(f"Failed to initialize OpenAI client: {e}")


def get_gemini_client() -> Dict[str, Any]:
	api_key = getattr(settings, "GEMINI_API_KEY", None)
	if not api_key:
		raise Exception("Gemini API key not configured")
	return {"api_key": api_key, "timeout": 60}


def get_perplexity_client() -> Dict[str, Any]:
	api_key = getattr(settings, "PERPLEXITY_API_KEY", None)
	if not api_key:
		raise Exception("Perplexity API key not configured")
	return {"api_key": api_key, "timeout": 60}


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
		numbered_match = re.match(r'^[\*\s#]*(\d+)[\.\)\:\-\s]+', line)
		if numbered_match:
			position = int(numbered_match.group(1))
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
				return int(m.group(1)) if m else 1
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

	# Strategy 1: Extract company names from URLs
	if all_urls:
		for url in all_urls:
			domain = _get_domain_from_url(url)
			if not domain or domain == user_domain_clean:
				continue

			# Extract SLD (second-level domain) as potential competitor name
			sld = domain.split('.')[0] if domain else ""
			if sld and len(sld) >= 3 and sld != user_sld:
				# Title case the SLD for cleaner names
				competitors.add(sld.title())

	# Strategy 2: Extract company names using common patterns
	# Pattern: "Company Name Inc/LLC/Ltd/Corp"
	company_patterns = [
		r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Inc\.?|LLC|Ltd\.?|Corporation|Corp\.?|Company|Co\.?)\b',
		# Pattern: "Brand.com" or "Brand.io" mentioned in text
		r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)*)\.(com|io|net|org)\b',
		# Pattern: Capitalized names followed by context words (insurance, software, platform, etc.)
		r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:insurance|software|platform|service|app|tool|website|marketplace)\b',
	]

	for pattern in company_patterns:
		matches = re.findall(pattern, text, flags=re.IGNORECASE)
		for match in matches:
			# match can be a tuple if pattern has multiple groups
			name = match[0] if isinstance(match, tuple) else match
			name = name.strip()
			if name and len(name) >= 3 and name.lower() != user_sld.lower():
				competitors.add(name.title())

	# Strategy 3: Extract mentions of brands in numbered lists or bullets
	# Pattern: "1. BrandName - description" or "• BrandName:"
	list_patterns = [
		r'[\d\.\*\-•]\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*[\:\-]',
		r'\*\*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\*\*',  # **BrandName** in markdown
	]

	for pattern in list_patterns:
		matches = re.findall(pattern, text)
		for name in matches:
			name = name.strip()
			if name and len(name) >= 3 and name.lower() != user_sld.lower():
				# Filter out common words that might match
				if name.lower() not in ['here', 'there', 'this', 'that', 'these', 'those', 'with', 'from', 'about', 'what', 'when', 'where', 'which', 'while', 'their', 'other']:
					competitors.add(name.title())

	# Convert to list and return (limit to top 20 to avoid noise)
	competitor_list = sorted(list(competitors))[:20]
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
        country_text = "India"
        system_prompt = f"You are a helpful assistant with access to current web search results. When answering questions, analyze the provided search results and combine them with your knowledge to provide comprehensive, up-to-date responses with current citations and links. Always prioritize the most recent and relevant information from the search results. Always provide answers in the context of {country_text} unless the user specifies another country."

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": (
                    "Original Question: " + prompt_text +
                    "\n\nBased on your knowledge, please provide a comprehensive and detailed response with:\n\n"
                    "1. A thorough answer incorporating the latest information\n"
                    "2. Include all relevant URLs and links\n"
                    "3. Mention specific companies, tools, platforms, and services\n"
                    "4. Provide detailed citations with current sources and dates where possible\n"
                    "5. Include pricing information, features, and comparisons from the most recent data\n"
                    "6. Add any additional current resources, alternatives, or related tools\n"
                    "7. Highlight which information comes from recent sources vs general knowledge\n\n"
                    "Format your response with proper current links, detailed descriptions, and up-to-date references. "
                    "Focus on providing the most current and relevant information available."
                )}
            ],
            temperature=0.7,
            max_tokens=3000,
            timeout=60
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
        import google.generativeai as genai
        genai.configure(api_key=(client or {}).get('api_key'), transport="rest")
        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = (
            f"Original Question: {prompt_text}\n\nBased on your knowledge, please provide a comprehensive and detailed response with:\n\n"
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
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                top_k=40,
                top_p=0.95,
                max_output_tokens=3000,
            )
        )
        text = response.text if getattr(response, 'text', None) else ""
        return _basic_text_metrics(text, user_domain)
    except Exception as e:
        logger.error(f"Gemini processing failed: {e}")
        raise


def process_prompt_with_perplexity_wrapper(prompt_text: str, user_domain: str, client: Any = None, group: Any = None) -> Dict[str, Any]:
    try:
        try:
            from perplexity import Perplexity
            perplexity_client = Perplexity(api_key=(client or {}).get('api_key'))
            user_message = prompt_text
            if len(user_message) > 250:
                user_message = user_message[:250].rsplit(' ', 1)[0] + "..."
            
            search_response = perplexity_client.search.create(query=user_message)
            
            # Extract text from response - check multiple possible response structures
            text = None
            
            # First, check if response has results array with snippets (search results)
            if hasattr(search_response, 'results') and search_response.results:
                text_parts = []
                for result in search_response.results:
                    snippet = getattr(result, 'snippet', '') or getattr(result, 'text', '') or getattr(result, 'content', '')
                    if snippet and snippet.strip():
                        text_parts.append(snippet.strip())
                if text_parts:
                    text = "\n".join(text_parts)
            
            # If no results, check the response object itself for answer/text/content
            if not text:
                # Check for direct answer field (most common for chat completions)
                if hasattr(search_response, 'answer') and search_response.answer:
                    text = str(search_response.answer).strip()
                # Check for choices array (chat completions format)
                elif hasattr(search_response, 'choices') and search_response.choices:
                    choice = search_response.choices[0] if search_response.choices else None
                    if choice:
                        if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                            text = str(choice.message.content).strip()
                        elif hasattr(choice, 'text'):
                            text = str(choice.text).strip()
                        elif hasattr(choice, 'content'):
                            text = str(choice.content).strip()
                # Check for other common response fields
                elif hasattr(search_response, 'text') and search_response.text:
                    text = str(search_response.text).strip()
                elif hasattr(search_response, 'content') and search_response.content:
                    text = str(search_response.content).strip()
                elif hasattr(search_response, 'response') and search_response.response:
                    text = str(search_response.response).strip()
                elif hasattr(search_response, 'message') and search_response.message:
                    text = str(search_response.message).strip()
            
            # If still no text found, use empty string instead of the prompt
            if not text or not text.strip():
                logger.warning(f"Perplexity API returned no response content for query: {user_message[:50]}...")
                text = ""
            else:
                logger.info(f"Perplexity API returned response of length {len(text)} for query: {user_message[:50]}...")
            
            # Close the client
            try:
                perplexity_client.close()
            except:
                pass
                
        except Exception as lib_error:
            logger.error(f"Perplexity API call failed: {str(lib_error)}")
            # Return empty string instead of the prompt text
            text = ""
        
        return _basic_text_metrics(text, user_domain)
    except Exception as e:
        logger.error(f"Perplexity processing failed: {e}")
        raise
