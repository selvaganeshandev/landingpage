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
	"""Return OpenAI client if configured in Django settings; else raise."""
	api_key = getattr(settings, "OPENAI_API_KEY", None)
	if not api_key:
		raise Exception("OpenAI API key not configured")
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
	mention_patterns = [p for p in [clean, sld, clean.replace('.com','').replace('.org','').replace('.net','').replace('.io',''), sld.replace(' ','') , sld.replace(' ','-'), sld.replace(' ','_')] if p and len(p) >= 3]
	has_mention = any(p.lower() in text.lower() for p in mention_patterns)
	all_url_pattern = r"https?://[^\s\)\]]+"
	all_urls = re.findall(all_url_pattern, text, flags=re.IGNORECASE)
	citation_count = len(all_urls)
	mention_count = sum(1 for pattern in mention_patterns if pattern.lower() in text.lower())
	polarity = 0.0
	sentiment = "neutral"
	if TextBlob is not None:
		blob = TextBlob(text)
		polarity = float(getattr(getattr(blob, 'sentiment', None), 'polarity', 0.0) or 0.0)
		if polarity > 0.1:
			sentiment = "positive"
		elif polarity < -0.1:
			sentiment = "negative"
	return {
		"is_mention": has_mention or has_citation,
		"mention_count": mention_count,
		"citations": all_citation_matches,
		"sentiment": sentiment,
		"sentiment_score": round(polarity, 3),
		"context_summary": text,
		"citation_count": citation_count,
		"has_citation": has_citation,
		"all_urls": all_urls,
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

        all_urls = re.findall(r"https?://[^\s\)\]]+", text, flags=re.IGNORECASE)
        citation_count = len(all_urls)
        mention_count = sum(1 for pattern in mention_patterns if pattern.lower() in text.lower())

        polarity = 0.0
        sentiment = "neutral"
        if TextBlob is not None:
            blob = TextBlob(text)
            polarity = float(getattr(getattr(blob, 'sentiment', None), 'polarity', 0.0) or 0.0)
            if polarity > 0.1:
                sentiment = "positive"
            elif polarity < -0.1:
                sentiment = "negative"

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
            if hasattr(search_response, 'results') and search_response.results:
                text = "\n".join([getattr(r, 'snippet', '') for r in search_response.results if getattr(r, 'snippet', '')])
            else:
                text = user_message
        except Exception:
            text = prompt_text
        return _basic_text_metrics(text, user_domain)
    except Exception as e:
        logger.error(f"Perplexity processing failed: {e}")
        raise
