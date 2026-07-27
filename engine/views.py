import json
import os
import re
import openai
import requests
from django.http import JsonResponse
from django.conf import settings
from rest_framework.decorators import api_view
from django.views.decorators.csrf import csrf_exempt
from llmtracker.models import LLMPrompt, LLMPromptAnalytics, LLMGroupPromptSummary
from account.models import Account
from serp.models import Groups, Settings, Keyword, Region
from django.db.models import Q
from textblob import TextBlob
from django.db import transaction
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def get_country_from_group(group) -> str:
    """
    Get the country name from a group by looking up the first keyword's region.
    Returns the region_country from the Region model, or empty string if not found.
    """
    try:
        # Get the first keyword from the group
        first_keyword = Keyword.objects.filter(fk_group=group).first()
        
        if not first_keyword or not first_keyword.region:
            return ""
        
        # Look up the region in the Region model
        region = Region.objects.filter(region_code=first_keyword.region).first()
        
        if region and region.region_country:
            return region.region_country
        
        return ""
    except Exception as e:
        logger.error(f"Error getting country from group: {str(e)}")
        return ""


def get_domain_from_url(value: str) -> str:
    """Return bare domain from a URL or domain string (strip scheme, www, port)."""
    try:
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


def extract_position_from_response(response: str, user_domain: str, citation_urls: list = None, has_mention: bool = False) -> int:
    """
    Extract brand position from LLM response text.
    Returns position number or None if not found.
    Similar to frontend extractPosition logic.
    """
    if not response:
        return None
    
    # Get clean domain and create brand variations
    domain_clean = get_domain_from_url(user_domain)
    if not domain_clean:
        return None
    
    # Extract brand name (SLD - second level domain)
    sld = domain_clean.split('.')[0] if '.' in domain_clean else domain_clean
    
    # Create brand variations for matching
    brand_variations = [
        domain_clean.lower(),
        sld.lower(),
        domain_clean.replace('.com', '').replace('.org', '').replace('.net', '').replace('.io', '').lower(),
        sld.replace(' ', '').lower(),
        sld.replace(' ', '-').lower(),
        sld.replace(' ', '_').lower(),
    ]
    
    # Filter out very short variations
    brand_variations = [v for v in brand_variations if v and len(v) >= 3]
    
    # Split response into lines
    lines = response.split('\n')
    found_position = None
    
    # Pass 1: Look for numbered list patterns
    for i in range(len(lines)):
        line = lines[i].strip()
        line_lower = line.lower()
        
        # Match numbered patterns: "1.", "1)", "(1)", "1:", "1 -", etc.
        # Exclude '#' to avoid matching hashtags/years like "#2023"
        numbered_match = re.match(r'^[\*\s]*(\d+)[\.\)\:\-\s]+', line)
        
        if numbered_match:
            position = int(numbered_match.group(1))
            # Validate position is reasonable (1-100), not a year or other large number
            if position < 1 or position > 100:
                continue
            
            # Create search window: current line + next 4 lines
            search_window_lines = lines[i:min(i + 5, len(lines))]
            search_window = ' '.join(search_window_lines).lower()
            
            # Check if brand appears in this numbered item's content
            contains_brand = any(
                variant in search_window 
                for variant in brand_variations 
                if len(variant) >= 3
            )
            
            if contains_brand:
                found_position = position
                break
    
    # If position found in numbered list, return it
    if found_position is not None:
        return found_position
    
    # Pass 2: Check if brand is mentioned with citations/URLs
    if citation_urls and len(citation_urls) > 0:
        full_text_lower = response.lower()
        
        for url in citation_urls:
            url_index = full_text_lower.find(url.lower())
            if url_index == -1:
                continue
            
            # Get context around URL (500 chars before and after)
            context_start = max(0, url_index - 500)
            context_end = min(len(response), url_index + 500)
            context = response[context_start:context_end].lower()
            
            # Check if brand is in this context
            brand_in_context = any(
                variant in context 
                for variant in brand_variations 
                if len(variant) >= 3
            )
            
            if brand_in_context:
                # Try to find position number in context
                pos_match = re.search(r'(\d+)[\.\)\:]', context)
                if pos_match:
                    position = int(pos_match.group(1))
                    # Validate position is reasonable (1-100), not a year or other large number
                    if 1 <= position <= 100:
                        return position
                # If no valid position found but brand + citation exists, default to 1
                return 1
    
    # Pass 3: If we have mentions but no numbered position found
    if has_mention:
        full_text_lower = response.lower()
        contains_brand = any(
            variant in full_text_lower 
            for variant in brand_variations 
            if len(variant) >= 3
        )
        
        if contains_brand:
            # Brand is mentioned but not in numbered list, default to position 1
            return 1
    
    return None


def process_prompt_with_chatgpt(prompt_text: str, user_domain: str, client, group=None) -> dict:
    """
    Process a single prompt with ChatGPT and return structured analytics.
    """
    try:
        # Get country-specific text if group is provided
        country_text = ""
        if group:
            country_name = get_country_from_group(group)
            if country_name:
                country_text = f" Always provide answers in the context of {country_name} unless the user specifies another country."
        
        system_prompt = f"You are a helpful assistant with access to current web search results. When answering questions, analyze the provided search results and combine them with your knowledge to provide comprehensive, up-to-date responses with current citations and links. Always prioritize the most recent and relevant information from the search results.{country_text}"
        
        response = client.chat.completions.create(
            model=getattr(settings, "OPENROUTER_INTERNAL_MODEL", "openai/gpt-5-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Original Question: " + prompt_text + "\n\nBased on your knowledge, please provide a comprehensive and detailed response with:\n\n1. A thorough answer incorporating the latest information\n2. Include all relevant URLs and links\n3. Mention specific companies, tools, platforms, and services\n4. Provide detailed citations with current sources and dates where possible\n5. Include pricing information, features, and comparisons from the most recent data\n6. Add any additional current resources, alternatives, or related tools\n7. Highlight which information comes from recent sources vs general knowledge\n\nFormat your response with proper current links, detailed descriptions, and up-to-date references. Focus on providing the most current and relevant information available."}
            ],
            temperature=0.7,
            max_tokens=3000,
            timeout=60  # 1 minute timeout for ChatGPT requests
        )

        text = response.choices[0].message.content
        print("\n\n")
        print(f"ChatGPT Response: {text}")
        
        # Enhanced brand analysis based on TypeScript implementation
        domain_clean = get_domain_from_url(user_domain)
        sld = domain_clean.split('.')[0] if domain_clean else ""
        
        # Check for direct citations (links containing domain/brand)
        escaped_domain = re.escape(domain_clean.replace('.', r'\.'))
        direct_citation_pattern = r"https?://[^\s\)\]]*" + escaped_domain + r"[^\s\)\]]*"
        direct_citation_matches = re.findall(direct_citation_pattern, text, flags=re.IGNORECASE)
        
        # Check for brand mentions in URLs (more flexible)
        escaped_sld = re.escape(sld.replace(' ', '[-_]?'))
        brand_in_url_pattern = r"https?://[^\s\)\]]*" + escaped_sld + r"[^\s\)\]]*"
        brand_url_matches = re.findall(brand_in_url_pattern, text, flags=re.IGNORECASE)
        
        # Combined citation check
        all_citation_matches = list(set(direct_citation_matches + brand_url_matches))
        has_citation = len(all_citation_matches) > 0
        
        # Enhanced mention detection with multiple patterns
        mention_patterns = [
            domain_clean,
            sld,
            # Remove common extensions for mention checking
            domain_clean.replace('.com', '').replace('.org', '').replace('.net', '').replace('.io', ''),
            # Check for brand name variations
            sld.replace(' ', ''),
            sld.replace(' ', '-'),
            sld.replace(' ', '_')
        ]
        
        # Filter out empty patterns
        mention_patterns = [pattern for pattern in mention_patterns if pattern and len(pattern) >= 3]
        
        has_mention = any(pattern and pattern.lower() in text.lower() for pattern in mention_patterns)
        
        # Count total URLs in response
        all_url_pattern = r"https?://[^\s\)\]]+"
        all_urls = re.findall(all_url_pattern, text, flags=re.IGNORECASE)
        citation_count = len(all_urls)
        
        # Calculate mention count
        mention_count = sum(1 for pattern in mention_patterns if pattern and pattern.lower() in text.lower())
        
        is_mentioned = has_mention or has_citation

        # Extract domains
        all_domains = extract_domains(text)
        first_party = []
        third_party = []

        for d in all_domains:
            if d == domain_clean:
                first_party.append(d)
            else:
                third_party.append(d)

        # Sentiment Analysis
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        if polarity > 0.1:
            sentiment = "positive"
        elif polarity < -0.1:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        return {
            "response_text": text,
            "is_mention": is_mentioned,
            "mention_count": mention_count,
            "citations": all_citation_matches,  # Store direct citation URLs
            "sentiment": sentiment,
            "sentiment_score": round(polarity, 3),
            "context_summary": text,
            "citation_count": citation_count,
            "has_citation": has_citation,
            "all_urls": all_urls
        }
        
    except Exception as e:
        logger.error(f"Error processing prompt with ChatGPT: {str(e)}")
        raise e


def process_prompt_with_gemini(prompt_text: str, user_domain: str, client, group=None) -> dict:
    """
    Process a single prompt with Gemini using Python library for better SSL and connection handling.
    """
    try:
        # Try to use Python library first (better for live environments)
        try:
            import google.generativeai as genai
            
            # Configure the API key
            genai.configure(api_key=client['api_key'],transport="rest")
            
            # Initialize the model
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            # Get country-specific text if group is provided
            country_text = ""
            if group:
                country_name = get_country_from_group(group)
                if country_name:
                    country_text = f" Always provide answers in the context of {country_name} unless the user specifies another country."
            
            # Prepare the prompt
            prompt = f"Original Question: {prompt_text}\n\nBased on your knowledge, please provide a comprehensive and detailed response with:\n\n1. A thorough answer incorporating the latest information\n2. Include all relevant URLs and links\n3. Mention specific companies, tools, platforms, and services\n4. Provide detailed citations with current sources and dates where possible\n5. Include pricing information, features, and comparisons from the most recent data\n6. Add any additional current resources, alternatives, or related tools\n7. Highlight which information comes from recent sources vs general knowledge\n\nFormat your response with proper current links, detailed descriptions, and up-to-date references. Focus on providing the most current and relevant information available.{country_text}"
            
            # Generate content using the Python library
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    top_k=40,
                    top_p=0.95,
                    max_output_tokens=3000,
                )
            )
            
            # Extract text from response
            text = response.text if response.text else ""
            logger.info("Gemini API call successful using Python library")
            
        except ImportError:
            # Library not available - skip processing
            logger.error("Google Generative AI library not installed, skipping Gemini processing")
            raise Exception("Google Generative AI library not installed")
            
        except Exception as lib_error:
            # Library failed - skip processing
            logger.error(f"Gemini library failed: {str(lib_error)}")
            raise Exception(f"Gemini processing failed: {str(lib_error)}")
        
        print("\n\n")
        print(f"Gemini Response: {text}")

        # Enhanced brand analysis based on TypeScript implementation
        domain_clean = get_domain_from_url(user_domain)
        sld = domain_clean.split('.')[0] if domain_clean else ""
        
        # Check for direct citations (links containing domain/brand)
        escaped_domain = re.escape(domain_clean.replace('.', r'\.'))
        direct_citation_pattern = r"https?://[^\s\)\]]*" + escaped_domain + r"[^\s\)\]]*"
        direct_citation_matches = re.findall(direct_citation_pattern, text, flags=re.IGNORECASE)
        
        # Check for brand mentions in URLs (more flexible)
        escaped_sld = re.escape(sld.replace(' ', '[-_]?'))
        brand_in_url_pattern = r"https?://[^\s\)\]]*" + escaped_sld + r"[^\s\)\]]*"
        brand_url_matches = re.findall(brand_in_url_pattern, text, flags=re.IGNORECASE)
        
        # Combined citation check
        all_citation_matches = list(set(direct_citation_matches + brand_url_matches))
        has_citation = len(all_citation_matches) > 0
        
        # Enhanced mention detection with multiple patterns
        mention_patterns = [
            domain_clean,
            sld,
            # Remove common extensions for mention checking
            domain_clean.replace('.com', '').replace('.org', '').replace('.net', '').replace('.io', ''),
            # Check for brand name variations
            sld.replace(' ', ''),
            sld.replace(' ', '-'),
            sld.replace(' ', '_')
        ]
        
        # Filter out empty patterns
        mention_patterns = [pattern for pattern in mention_patterns if pattern and len(pattern) >= 3]
        
        has_mention = any(pattern and pattern.lower() in text.lower() for pattern in mention_patterns)
        
        # Count total URLs in response
        all_url_pattern = r"https?://[^\s\)\]]+"
        all_urls = re.findall(all_url_pattern, text, flags=re.IGNORECASE)
        citation_count = len(all_urls)
        
        # Calculate mention count
        mention_count = sum(1 for pattern in mention_patterns if pattern and pattern.lower() in text.lower())
        
        is_mentioned = has_mention or has_citation

        # Extract domains
        all_domains = extract_domains(text)
        first_party = []
        third_party = []

        for d in all_domains:
            if d == domain_clean:
                first_party.append(d)
            else:
                third_party.append(d)

        # Sentiment Analysis
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        if polarity > 0.1:
            sentiment = "positive"
        elif polarity < -0.1:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        return {
            "response_text": text,
            "is_mention": is_mentioned,
            "mention_count": mention_count,
            "citations": all_citation_matches,  # Store direct citation URLs
            "sentiment": sentiment,
            "sentiment_score": round(polarity, 3),
            "context_summary": text,
            "citation_count": citation_count,
            "has_citation": has_citation,
            "all_urls": all_urls
        }
        
    except Exception as e:
        logger.error(f"Error processing prompt with Gemini: {str(e)}")
        raise e


def process_prompt_with_perplexity(prompt_text: str, user_domain: str, client, group=None) -> dict:
    """
    Process a single prompt with Perplexity Sonar, served over OpenRouter.

    Previously this used the standalone `perplexity` SDK's Search API against
    api.perplexity.ai. That transport is gone (see get_perplexity_client), so the
    call is now an OpenAI-compatible chat completion — which also means the old
    256-character query cap no longer applies and prompts are sent whole.
    """
    try:
        try:
            from openai import OpenAI

            perplexity_client = OpenAI(
                api_key=client['api_key'],
                base_url=client.get('base_url') or 'https://openrouter.ai/api/v1',
                timeout=client.get('timeout', 60),
            )

            # Get country-specific text if group is provided
            country_suffix = ""
            if group:
                country_name = get_country_from_group(group)
                if country_name:
                    country_suffix = f" Answer in the context of {country_name} unless otherwise specified."

            user_message = prompt_text + country_suffix

            response = perplexity_client.chat.completions.create(
                model=getattr(settings, 'PERPLEXITY_MODEL', 'perplexity/sonar'),
                messages=[{"role": "user", "content": user_message}],
                max_tokens=getattr(settings, 'LLM_MAX_OUTPUT_TOKENS', 1500),
            )
            text = (response.choices[0].message.content or "") if response.choices else ""
            if not text:
                raise Exception("Perplexity returned an empty response")

            logger.info("Perplexity API call successful via OpenRouter")

        except ImportError:
            logger.error("openai package not installed, skipping Perplexity processing")
            raise Exception("openai package not installed")

        except Exception as lib_error:
            logger.error(f"Perplexity call failed: {str(lib_error)}")
            raise Exception(f"Perplexity processing failed: {str(lib_error)}")

        print("\n\n")
        print(f"Perplexity Response: {text}")

        # Enhanced brand analysis based on TypeScript implementation
        domain_clean = get_domain_from_url(user_domain)
        sld = domain_clean.split('.')[0] if domain_clean else ""
        
        # Check for direct citations (links containing domain/brand)
        escaped_domain = re.escape(domain_clean.replace('.', r'\.'))
        direct_citation_pattern = r"https?://[^\s\)\]]*" + escaped_domain + r"[^\s\)\]]*"
        direct_citation_matches = re.findall(direct_citation_pattern, text, flags=re.IGNORECASE)
        
        # Check for brand mentions in URLs (more flexible)
        escaped_sld = re.escape(sld.replace(' ', '[-_]?'))
        brand_in_url_pattern = r"https?://[^\s\)\]]*" + escaped_sld + r"[^\s\)\]]*"
        brand_url_matches = re.findall(brand_in_url_pattern, text, flags=re.IGNORECASE)
        
        # Combined citation check
        all_citation_matches = list(set(direct_citation_matches + brand_url_matches))
        has_citation = len(all_citation_matches) > 0
        
        # Enhanced mention detection with multiple patterns
        mention_patterns = [
            domain_clean,
            sld,
            # Remove common extensions for mention checking
            domain_clean.replace('.com', '').replace('.org', '').replace('.net', '').replace('.io', ''),
            # Check for brand name variations
            sld.replace(' ', ''),
            sld.replace(' ', '-'),
            sld.replace(' ', '_')
        ]
        
        # Filter out empty patterns
        mention_patterns = [pattern for pattern in mention_patterns if pattern and len(pattern) >= 3]
        
        has_mention = any(pattern and pattern.lower() in text.lower() for pattern in mention_patterns)
        
        # Count total URLs in response
        all_url_pattern = r"https?://[^\s\)\]]+"
        all_urls = re.findall(all_url_pattern, text, flags=re.IGNORECASE)
        citation_count = len(all_urls)
        
        # Calculate mention count
        mention_count = sum(1 for pattern in mention_patterns if pattern and pattern.lower() in text.lower())
        
        is_mentioned = has_mention or has_citation

        # Extract domains
        all_domains = extract_domains(text)
        first_party = []
        third_party = []

        for d in all_domains:
            if d == domain_clean:
                first_party.append(d)
            else:
                third_party.append(d)

        # Sentiment Analysis
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        if polarity > 0.1:
            sentiment = "positive"
        elif polarity < -0.1:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        return {
            "response_text": text,
            "is_mention": is_mentioned,
            "mention_count": mention_count,
            "citations": all_citation_matches,  # Store direct citation URLs
            "sentiment": sentiment,
            "sentiment_score": round(polarity, 3),
            "context_summary": text,
            "citation_count": citation_count,
            "has_citation": has_citation,
            "all_urls": all_urls
        }
        
    except Exception as e:
        logger.error(f"Error processing prompt with Perplexity: {str(e)}")
        raise e


def process_prompt_with_gemini_wrapper(prompt_text: str, user_domain: str, client=None, group=None) -> dict:
    """
    Wrapper function to process a single prompt with Gemini and return structured analytics.
    This function integrates with the existing LLM tracker system.
    """
    try:
        return process_prompt_with_gemini(prompt_text, user_domain, client, group)
    except Exception as e:
        logger.error(f"Error processing prompt with Gemini: {str(e)}")
        raise e


def process_prompt_with_perplexity_wrapper(prompt_text: str, user_domain: str, client=None, group=None) -> dict:
    """
    Wrapper function to process a single prompt with Perplexity and return structured analytics.
    This function integrates with the existing LLM tracker system.
    """
    try:
        return process_prompt_with_perplexity(prompt_text, user_domain, client, group)
    except Exception as e:
        logger.error(f"Error processing prompt with Perplexity: {str(e)}")
        raise e


def process_llm_prompts_automatically():
    """
    Automatically process LLM prompts with status 'INIT'.
    Only processes one prompt at a time to avoid concurrency issues.
    """
    try:
        # Cleanup any stuck prompts first
        cleanup_stuck_prompts()
        
        # Check if more than 5 prompts are currently being processed (SCHD status)
        scheduled_prompts = LLMPrompt.objects.filter(track_status="SCHD")
        if scheduled_prompts.count() > 5:
            logger.info("More than 5 prompts are being processed. Skipping automatic processing.")
            return {
                "status": "skipped",
                "message": "A prompt is already being processed. Skipping automatic processing"
            }

        # Get the first prompt with INIT status
        init_prompt = LLMPrompt.objects.filter(track_status="INIT").first()
        if not init_prompt:
            logger.info("No prompts with INIT status found.")
            return {
                "status": "no_prompts",
                "message": "No prompts to process"
            }

        # Mark the prompt as scheduled
        with transaction.atomic():
            init_prompt.track_status = "SCHD"
            init_prompt.track_message = "Processing started"
            init_prompt.save()

        logger.info(f"Processing prompt {init_prompt.prompt_id}: {init_prompt.prompt[:50]}...")

        # Wrap entire processing in try-catch to ensure status is always updated
        try:
            # Get user domain from the group settings
            user_domain = init_prompt.fk_group.domain_name
            if not user_domain:
                user_domain = "example.com"  # Fallback if no domain is set

            # Initialize clients - check if models are enabled in settings
            openai_client = None
            gemini_client = None
            perplexity_client = None
                
            # Try to initialize ChatGPT client
            try:
                openai_client = get_openai_client()
                logger.info("ChatGPT client initialized successfully")
            except Exception as e:
                logger.warning(f"ChatGPT client initialization failed: {str(e)}")
                openai_client = None
                
            # Try to initialize Gemini client
            try:
                gemini_client = get_gemini_client()
                logger.info("Gemini client initialized successfully")
            except Exception as e:
                logger.warning(f"Gemini client initialization failed: {str(e)}")
                gemini_client = None
                
            # Try to initialize Perplexity client
            try:
                perplexity_client = get_perplexity_client()
                logger.info("Perplexity client initialized successfully")
            except Exception as e:
                logger.warning(f"Perplexity client initialization failed: {str(e)}")
                perplexity_client = None

            # Process with ChatGPT (if client available)
            chatgpt_analytics = None
            if openai_client is not None:
                try:
                    chatgpt_result = process_prompt_with_chatgpt(
                        init_prompt.prompt,
                        user_domain,
                        openai_client,
                        init_prompt.fk_group,
                    )
                    chatgpt_analytics = LLMPromptAnalytics.objects.create(
                        fk_prompt=init_prompt,
                        model="ChatGPT",
                        track_status="DONE",
                        is_mention=chatgpt_result["is_mention"],
                        mention_count=chatgpt_result["mention_count"],
                        citations=chatgpt_result["citations"],
                        sentiment=chatgpt_result["sentiment"],
                        sentiment_score=chatgpt_result["sentiment_score"],
                        context_summary=chatgpt_result["context_summary"],
                    )
                except Exception as ce:
                    # Record failure entry for ChatGPT
                    LLMPromptAnalytics.objects.create(
                        fk_prompt=init_prompt,
                        model="ChatGPT",
                        track_status="FAIL",
                        is_mention=False,
                        mention_count=0,
                        citations=[],
                        sentiment="neutral",
                        sentiment_score=0.0,
                        context_summary="",
                        track_message=f"ChatGPT processing failed: {str(ce)}",
                    )
            else:
                logger.info("ChatGPT client not available, skipping ChatGPT processing")


            # Process with Gemini (if client available)
            gemini_analytics = None
            if gemini_client is not None:
                try:
                    gemini_result = process_prompt_with_gemini_wrapper(
                        init_prompt.prompt,
                        user_domain,
                        gemini_client,
                        init_prompt.fk_group,
                    )
                    gemini_analytics = LLMPromptAnalytics.objects.create(
                        fk_prompt=init_prompt,
                        model="Gemini",
                        track_status="DONE",
                        is_mention=gemini_result["is_mention"],
                        mention_count=gemini_result["mention_count"],
                        citations=gemini_result["citations"],
                        sentiment=gemini_result["sentiment"],
                        sentiment_score=gemini_result["sentiment_score"],
                        context_summary=gemini_result["context_summary"],
                    )
                except Exception as ge:
                    # Record failure entry for Gemini
                    LLMPromptAnalytics.objects.create(
                        fk_prompt=init_prompt,
                        model="Gemini",
                        track_status="FAIL",
                        is_mention=False,
                        mention_count=0,
                        citations=[],
                        sentiment="neutral",
                        sentiment_score=0.0,
                        context_summary="",
                        track_message=f"Gemini processing failed: {str(ge)}",
                    )

            # Process with Perplexity (if client available)
            perplexity_analytics = None
            if perplexity_client is not None:
                try:
                    perplexity_result = process_prompt_with_perplexity_wrapper(
                        init_prompt.prompt,
                        user_domain,
                        perplexity_client,
                        init_prompt.fk_group,
                    )
                    perplexity_analytics = LLMPromptAnalytics.objects.create(
                        fk_prompt=init_prompt,
                        model="Perplexity",
                        track_status="DONE",
                        is_mention=perplexity_result["is_mention"],
                        mention_count=perplexity_result["mention_count"],
                        citations=perplexity_result["citations"],
                        sentiment=perplexity_result["sentiment"],
                        sentiment_score=perplexity_result["sentiment_score"],
                        context_summary=perplexity_result["context_summary"],
                    )
                except Exception as pe:
                    # Record failure entry for Perplexity
                    LLMPromptAnalytics.objects.create(
                        fk_prompt=init_prompt,
                        model="Perplexity",
                        track_status="FAIL",
                        is_mention=False,
                        mention_count=0,
                        citations=[],
                        sentiment="neutral",
                        sentiment_score=0.0,
                        context_summary="",
                        track_message=f"Perplexity processing failed: {str(pe)}",
                    )

            # Mark the prompt as completed after attempting all models
            with transaction.atomic():
                init_prompt.track_status = "COMP"
                init_prompt.track_message = "Processing completed successfully"
                init_prompt.save()

            # Update group summary after successful processing
            try:
                summary, created = LLMGroupPromptSummary.objects.get_or_create(
                    fk_user=init_prompt.fk_user,
                    fk_group=init_prompt.fk_group
                )
                summary.recalculate_summary()
            except Exception as e:
                logger.warning(f"Failed to update group summary: {str(e)}")

            logger.info(f"Successfully processed prompt {init_prompt.prompt_id}")

            # Get the first available analytics ID for response
            analytics_id = None
            if chatgpt_analytics:
                analytics_id = str(chatgpt_analytics.analytics_id)
            elif gemini_analytics:
                analytics_id = str(gemini_analytics.analytics_id)
            elif perplexity_analytics:
                analytics_id = str(perplexity_analytics.analytics_id)

            return {
                "status": "success",
                "message": "Prompt processed successfully",
                "prompt_id": str(init_prompt.prompt_id),
                "analytics_id": analytics_id,
            }

        except Exception as e:
            # Mark the prompt as failed - this ensures status is always updated
            try:
                with transaction.atomic():
                    init_prompt.track_status = "FAIL"
                    init_prompt.track_message = f"Processing failed: {str(e)}"
                    init_prompt.save()
            except Exception as save_error:
                logger.error(f"Failed to update prompt status to FAIL: {str(save_error)}")

            logger.error(f"Failed to process prompt {init_prompt.prompt_id}: {str(e)}")
            
            return {
                "status": "error",
                "message": f"Processing failed: {str(e)}",
                "prompt_id": str(init_prompt.prompt_id)
            }

    except Exception as e:
        logger.error(f"Error in automatic processing: {str(e)}")
        return {
            "status": "error",
            "message": f"System error: {str(e)}"
        }


@api_view(["POST"])
def add_prompt(request):
    """Add new prompts for all enabled LLM services from Settings with optional new fields"""
    try:
        required_fields = ["userid", "groupid", "prompts"]
        validation_required = all(field in request.data for field in required_fields)

        if not validation_required:
            return JsonResponse({"status": "false", "message": "Something went wrong"})

        userid = request.data["userid"].strip()
        groupid = request.data["groupid"].strip()
        prompts_input = request.data["prompts"]
        
        # Ensure prompts is always an array
        if isinstance(prompts_input, str):
            prompts = [prompts_input.strip()]
        elif isinstance(prompts_input, list):
            prompts = [str(p).strip() for p in prompts_input if p]
        else:
            return JsonResponse({"status": "false", "message": "Something went wrong"})
        
        if not prompts:
            return JsonResponse({"status": "false", "message": "Something went wrong"})

        # Validate user and group exist
        try:
            user_instance = Account.objects.get(id=userid)
            group_instance = Groups.objects.get(id=groupid, fk_user_id=userid)
        except Account.DoesNotExist:
            return JsonResponse({"status": "false", "message": "Invalid user"})
        except Groups.DoesNotExist:
            return JsonResponse({"status": "false", "message": "Invalid group"})

        created_prompts = []
        # Create prompts for each prompt text (one LLMPrompt per text)
        for prompt_text in prompts:
            # Create the main LLMPrompt record
            new_prompt = LLMPrompt()
            new_prompt.fk_user = user_instance
            new_prompt.fk_group = group_instance
            new_prompt.prompt = prompt_text
            new_prompt.track_status = "INIT"  # Set initial status
            new_prompt.save()
            
            # Only create the prompt record, analytics will be created during processing
            created_prompts.append({
                "promptId": str(new_prompt.prompt_id),
                "prompt": prompt_text,
                "track_status": new_prompt.track_status,
                "created_date": new_prompt.created_date.strftime("%Y-%m-%d %H:%M:%S")
            })

        return JsonResponse({
            "status": "true", 
            "message": "Saved successfully",
            "total_prompts": len(created_prompts)
        })

    except Exception as e:
        print(f"Error adding prompt: {str(e)}")
        return JsonResponse({"status": "false", "message": f"Error: {str(e)}"})


@api_view(["POST"])
def list_prompts(request):
    """List prompts with simple search filter"""
    try:
        required_fields = ["userid", "groupid"]
        validation_required = all(field in request.data for field in required_fields)

        if not validation_required:
            return JsonResponse({"status": "false", "message": "Invalid Params"})

        userid = request.data["userid"].strip()
        groupid = request.data["groupid"].strip()
        search_query = request.data.get("search", "").strip()

        # Validate user and group exist
        try:
            user_instance = Account.objects.get(id=userid)
            group_instance = Groups.objects.get(id=groupid, fk_user=user_instance)
        except Account.DoesNotExist:
            return JsonResponse({"status": "false", "message": "Invalid user"})
        except Groups.DoesNotExist:
            return JsonResponse({"status": "false", "message": "Invalid group"})

        # Get user domain for position extraction
        user_domain = group_instance.domain_name if group_instance.domain_name else ""

        # Build query for prompts
        query = Q(fk_user=user_instance, fk_group=group_instance)
        
        if search_query:
            query &= Q(prompt__icontains=search_query)

        
        # Get prompts with their analytics data
        prompts = LLMPrompt.objects.filter(query).prefetch_related('analytics').order_by('created_date')
        
        result_data = []
        for prompt in prompts:
            # Check if prompt is being processed
            is_processing = prompt.track_status in ["SCHD", "INIT"]
            
            if is_processing:
                # For processing prompts, show processing status
                result_data.append({
                    "prompt_id": str(prompt.prompt_id),
                    "prompt": prompt.prompt,
                    "is_mentioned_in_chatgpt": False,
                    "is_mentioned_in_gemini": False,
                    "is_mentioned_in_perplexity": False,
                    "tracked_at": "",
                    "track_status": prompt.track_status,
                    "track_message": prompt.track_message or "Processing",
                    "total_citations": 0,
                    "chatgpt_analytics_id": None,
                    "gemini_analytics_id": None,
                    "perplexity_analytics_id": None,
                    "chatgpt_citations_count": 0,
                    "gemini_citations_count": 0,
                    "perplexity_citations_count": 0,
                    "chatgpt_context_summary": None,
                    "gemini_context_summary": None,
                    "perplexity_context_summary": None,
                    "chatgpt_position": None,
                    "gemini_position": None,
                    "perplexity_position": None,
                    "average_position": None
                })
            else:
                # For completed prompts, get analytics data
                analytics = prompt.analytics.all()
                
                # Get the latest analytics record
                latest_analytics = None
                if analytics:
                    latest_analytics = max(analytics, key=lambda a: a.modified_date)
                latest_modified = latest_analytics.modified_date if latest_analytics else prompt.modified_date
                
                # Check ChatGPT, Gemini, and Perplexity mentions from analytics
                chatgpt_mentioned = False
                gemini_mentioned = False
                perplexity_mentioned = False
                
                # Collect citations data
                all_citations = []
                chatgpt_citations = []
                gemini_citations = []
                perplexity_citations = []

                # Collect context summaries
                chatgpt_context_summary = None
                gemini_context_summary = None
                perplexity_context_summary = None

                # Track latest analytics per model
                latest_chatgpt_analytics = None
                latest_gemini_analytics = None
                latest_perplexity_analytics = None
                
                for a in analytics:
                    if a.model == "ChatGPT" and a.is_mention:
                        chatgpt_mentioned = True
                    elif a.model == "Gemini" and a.is_mention:
                        gemini_mentioned = True
                    elif a.model == "Perplexity" and a.is_mention:
                        perplexity_mentioned = True
                    
                    # Collect citations
                    if a.citations:
                        all_citations.extend(a.citations)
                        if a.model == "ChatGPT":
                            chatgpt_citations.extend(a.citations)
                        elif a.model == "Gemini":
                            gemini_citations.extend(a.citations)
                        elif a.model == "Perplexity":
                            perplexity_citations.extend(a.citations)

                    # Collect context summaries
                    if a.model == "ChatGPT" and a.context_summary:
                        chatgpt_context_summary = a.context_summary
                    elif a.model == "Gemini" and a.context_summary:
                        gemini_context_summary = a.context_summary
                    elif a.model == "Perplexity" and a.context_summary:
                        perplexity_context_summary = a.context_summary

                    # Track latest analytics per model by modified_date
                    if a.model == "ChatGPT":
                        if (latest_chatgpt_analytics is None) or (a.modified_date > latest_chatgpt_analytics.modified_date):
                            latest_chatgpt_analytics = a
                    elif a.model == "Gemini":
                        if (latest_gemini_analytics is None) or (a.modified_date > latest_gemini_analytics.modified_date):
                            latest_gemini_analytics = a
                    elif a.model == "Perplexity":
                        if (latest_perplexity_analytics is None) or (a.modified_date > latest_perplexity_analytics.modified_date):
                            latest_perplexity_analytics = a
                
                # Remove duplicate citations
                unique_citations = list(set(all_citations))
                unique_chatgpt_citations = list(set(chatgpt_citations))
                unique_gemini_citations = list(set(gemini_citations))
                unique_perplexity_citations = list(set(perplexity_citations))
                
                # Extract positions from responses for each model
                chatgpt_position = None
                gemini_position = None
                perplexity_position = None
                
                if latest_chatgpt_analytics and chatgpt_context_summary:
                    chatgpt_position = extract_position_from_response(
                        chatgpt_context_summary, 
                        user_domain, 
                        unique_chatgpt_citations, 
                        chatgpt_mentioned
                    )
                
                if latest_gemini_analytics and gemini_context_summary:
                    gemini_position = extract_position_from_response(
                        gemini_context_summary, 
                        user_domain, 
                        unique_gemini_citations, 
                        gemini_mentioned
                    )
                
                if latest_perplexity_analytics and perplexity_context_summary:
                    perplexity_position = extract_position_from_response(
                        perplexity_context_summary, 
                        user_domain, 
                        unique_perplexity_citations, 
                        perplexity_mentioned
                    )
                
                # Calculate average position (only from models with valid positions)
                positions_list = [p for p in [chatgpt_position, gemini_position, perplexity_position] if p is not None]
                average_position = round(sum(positions_list) / len(positions_list), 1) if positions_list else None
                
                result_data.append({
                    "prompt_id": str(prompt.prompt_id),
                    "prompt": prompt.prompt,
                    "is_mentioned_in_chatgpt": chatgpt_mentioned,
                    "is_mentioned_in_gemini": gemini_mentioned,
                    "is_mentioned_in_perplexity": perplexity_mentioned,
                    "tracked_at": latest_modified.strftime("%b %d, %Y"),
                    "track_status": prompt.track_status,
                    "track_message": prompt.track_message,
                    "total_citations": len(unique_citations),
                    "chatgpt_analytics_id": str(latest_chatgpt_analytics.analytics_id) if latest_chatgpt_analytics else None,
                    "gemini_analytics_id": str(latest_gemini_analytics.analytics_id) if latest_gemini_analytics else None,
                    "perplexity_analytics_id": str(latest_perplexity_analytics.analytics_id) if latest_perplexity_analytics else None,
                    "chatgpt_citations_count": len(unique_chatgpt_citations),
                    "gemini_citations_count": len(unique_gemini_citations),
                    "perplexity_citations_count": len(unique_perplexity_citations),
                    "chatgpt_context_summary": chatgpt_context_summary,
                    "gemini_context_summary": gemini_context_summary,
                    "perplexity_context_summary": perplexity_context_summary,
                    "chatgpt_position": chatgpt_position,
                    "gemini_position": gemini_position,
                    "perplexity_position": perplexity_position,
                    "average_position": average_position
                })

        # Get group summary data
        try:
            summary, created = LLMGroupPromptSummary.objects.get_or_create(
                fk_user=user_instance,
                fk_group=group_instance
            )
            
            # Recalculate summary to ensure it's up to date
            summary.recalculate_summary()
            
            summary_data = {
                "total_prompts": summary.total_prompts,
                "total_citations": summary.total_citations,
                "total_mentions": summary.total_mentions,
                "last_tracked_at": summary.last_tracked_at.strftime("%Y-%m-%d %H:%M:%S") if summary.last_tracked_at else None,
                "created_date": summary.created_date.strftime("%Y-%m-%d %H:%M:%S"),
                "modified_date": summary.modified_date.strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            logger.warning(f"Failed to get group summary: {str(e)}")
            summary_data = {
                "total_prompts": 0,
                "total_citations": 0,
                "total_mentions": 0,
                "last_tracked_at": None,
                "created_date": None,
                "modified_date": None
            }

        return JsonResponse({
            "status": "true", 
            "data": result_data,
            "summary": summary_data
        })
    except Exception as e:
        print(f"Error listing prompts: {str(e)}")
        return JsonResponse({"status": "false", "message": "Something went wrong"})


@api_view(["POST"])
def delete_prompts(request):
    """Delete multiple prompts with prompt_ids"""
    try:
        required_fields = ["userid", "prompt_ids"]
        validation_required = all(field in request.data for field in required_fields)

        if not validation_required:
            return JsonResponse({"status": "false", "message": "Invalid Params - userid and prompt_ids are required"})

        userid = request.data["userid"].strip()
        prompt_ids = request.data["prompt_ids"]

        # Validate user exists
        try:
            user_instance = Account.objects.get(id=userid)
        except Account.DoesNotExist:
            return JsonResponse({"status": "false", "message": "Invalid user"})

        # Ensure prompt_ids is a list and not empty
        if not isinstance(prompt_ids, list):
            return JsonResponse({"status": "false", "message": "prompt_ids must be a list"})
        
        if not prompt_ids:
            return JsonResponse({"status": "false", "message": "prompt_ids list cannot be empty"})

        # Find and delete the prompts and their analytics
        deleted_count = 0
        affected_groups = set()
        
        for prompt_id in prompt_ids:
            try:
                # Convert string to UUID if needed
                if isinstance(prompt_id, str):
                    import uuid
                    try:
                        prompt_id = uuid.UUID(prompt_id)
                    except ValueError:
                        continue
                
                # Find the prompt
                prompt = LLMPrompt.objects.get(prompt_id=prompt_id, fk_user=user_instance)
                
                # Track affected group for summary update
                affected_groups.add(prompt.fk_group)
                
                # Get all analytics for this prompt before deletion
                analytics_list = LLMPromptAnalytics.objects.filter(fk_prompt=prompt)
                
                # Delete all analytics first (CASCADE should handle this, but being explicit)
                analytics_list.delete()
                
                # Then delete the prompt
                prompt.delete()
                
                deleted_count += 1
                print(f"Successfully deleted prompt {prompt_id}")
                
            except LLMPrompt.DoesNotExist:
                print(f"Prompt {prompt_id} not found for user {userid}")
            except Exception as e:
                print(f"Error deleting prompt {prompt_id}: {e}")

        # Update group summaries for affected groups
        if deleted_count > 0 and affected_groups:
            try:
                for group in affected_groups:
                    summary = LLMGroupPromptSummary.objects.filter(
                        fk_user=user_instance,
                        fk_group=group
                    ).first()
                    if summary:
                        summary.recalculate_summary()
            except Exception as e:
                logger.warning(f"Failed to update group summaries after deletion: {str(e)}")

        if deleted_count == 0:
            return JsonResponse({
                "status": "false", 
                "message": "No prompts were deleted"
            })

        return JsonResponse({
            "status": "true", 
            "message": "Deleted successfully"
        })

    except Exception as e:
        print(f"Error deleting prompts: {str(e)}")
        return JsonResponse({"status": "false", "message": f"Error: {str(e)}"})


def get_openai_client():
    """Initialize and return OpenAI client using settings from database or environment."""
    try:
        # Try database settings first
        try:
            from serp.models import Settings
            settings_obj = Settings.objects.first()
            if settings_obj and hasattr(settings_obj, 'chatgpt_enabled'):
                if not settings_obj.chatgpt_enabled:
                    raise Exception("ChatGPT is disabled in settings")
        except (ImportError, Exception) as db_err:
            logger.info(f"DB settings unavailable for OpenAI, trying env: {db_err}")

        # Every OpenAI call — this helper's internal work and the tracked ChatGPT
        # measurement in core.analytics_helpers alike — runs through OpenRouter.
        # A stored serp.Settings.chatgpt_api_key no longer authenticates anything
        # (see OPENROUTER_ROUTED in core/services/api_key_service.py), so the only
        # key consulted here is the OpenRouter one. NOTE: the chatgpt_enabled
        # raise above lands in this function's own `except Exception`, so it has
        # never actually blocked a call — behaviour left as-is, not a new bug.
        from django.conf import settings as django_settings
        api_key = getattr(django_settings, 'OPENROUTER_API_KEY', None) or os.environ.get('OPENROUTER_API_KEY')
        if not api_key:
            raise Exception("OPENROUTER_API_KEY not found in database or environment")

        return openai.OpenAI(
            api_key=api_key,
            base_url=getattr(django_settings, 'OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1'),
            timeout=60,
        )
    except Exception as e:
        raise Exception(f"Failed to initialize OpenAI client: {str(e)}")


def get_gemini_client():
    """Initialize and return Gemini client using settings from database or environment."""
    try:
        # Try database settings first (serp.Settings may have gemini fields on some setups)
        try:
            from serp.models import Settings
            settings_obj = Settings.objects.first()
            if settings_obj and hasattr(settings_obj, 'gemini_enabled') and hasattr(settings_obj, 'gemini_api_key'):
                if not settings_obj.gemini_enabled:
                    raise Exception("Gemini is disabled in settings")
                if not settings_obj.gemini_api_key:
                    raise Exception("Gemini API key is not configured in settings")
                return {
                    'api_key': settings_obj.gemini_api_key,
                    'base_url': 'https://generativelanguage.googleapis.com/v1beta',
                    'timeout': 60,
                }
        except (ImportError, Exception) as db_err:
            logger.info(f"DB settings unavailable for Gemini, trying env: {db_err}")

        # Fallback to environment variable
        from django.conf import settings as django_settings
        api_key = getattr(django_settings, 'GEMINI_API_KEY', None) or os.environ.get('GEMINI_API_KEY')
        if not api_key:
            raise Exception("Gemini API key not found in database or environment")

        return {
            'api_key': api_key,
            'base_url': 'https://generativelanguage.googleapis.com/v1beta',
            'timeout': 60,
        }
    except Exception as e:
        raise Exception(f"Failed to initialize Gemini client: {str(e)}")


def get_perplexity_client():
    """Return the credential/endpoint for Perplexity, which runs on OpenRouter.

    A stored per-org or .env PERPLEXITY_API_KEY no longer authenticates anything
    (see OPENROUTER_ROUTED in core/services/api_key_service.py), so the only key
    consulted here is the OpenRouter one.
    """
    try:
        from django.conf import settings as django_settings
        api_key = getattr(django_settings, 'OPENROUTER_API_KEY', None) or os.environ.get('OPENROUTER_API_KEY')
        if not api_key:
            raise Exception("OPENROUTER_API_KEY not found in database or environment")

        return {
            'api_key': api_key,
            'base_url': getattr(django_settings, 'OPENROUTER_BASE_URL', None) or 'https://openrouter.ai/api/v1',
            'timeout': 60,
        }
    except Exception as e:
        raise Exception(f"Failed to initialize Perplexity client: {str(e)}")


def cleanup_stuck_prompts():
    """
    Cleanup function to reset stuck prompts that have been in SCHD status for too long.
    This prevents infinite loops and ensures the system can recover from stuck states.
    """
    try:
        from django.utils import timezone
        from datetime import timedelta
        
        # Reset prompts stuck in SCHD status for more than 10 minutes
        stuck_threshold = timezone.now() - timedelta(minutes=10)
        stuck_prompts = LLMPrompt.objects.filter(
            track_status="SCHD",
            modified_date__lt=stuck_threshold
        )
        
        if stuck_prompts.exists():
            logger.warning(f"Cleaning up {stuck_prompts.count()} stuck prompts")
            stuck_prompts.update(
                track_status="FAIL",
                track_message="Reset from stuck SCHD status - processing timeout"
            )
            return stuck_prompts.count()
        
        return 0
        
    except Exception as e:
        logger.error(f"Error in cleanup_stuck_prompts: {str(e)}")
        return 0


def extract_domains(text: str) -> list:
    """
    Extract all domain names from text using regex pattern.
    Returns a list of unique domain names (lowercase, without www).
    """
    # Regex pattern to match domain names
    domain_pattern = r'(?:https?://)?(?:www\.)?([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.(?:[a-zA-Z]{2,}))'
    
    # Find all matches
    matches = re.findall(domain_pattern, text, re.IGNORECASE)
    
    # Clean and deduplicate domains
    domains = []
    for match in matches:
        domain = match.lower().replace("www.", "")
        if domain not in domains:
            domains.append(domain)
    
    return domains


def analyze_keyword_domain(keyword: str, user_domain: str, client):
    # Internal keyword/domain analysis via OpenRouter
    response = client.chat.completions.create(
        model=getattr(settings, "OPENROUTER_INTERNAL_MODEL", "openai/gpt-5-mini"),
        messages=[
            {"role": "system", "content": "You are an AI that provides clear answers and may reference relevant websites or brands."},
            {"role": "user", "content": f"Give me detailed information about {keyword}, including any relevant sources or brand names."}
        ],
        temperature=1,
        max_completion_tokens=300
    )

    text = response.choices[0].message.content

    print(text)
    # ------------------------------
    # 1. Detect mentions of the user domain
    # ------------------------------
    domain_clean = user_domain.lower().replace("www.", "")
    mention_count = len(re.findall(domain_clean, text.lower()))
    is_mentioned = mention_count > 0

    # ------------------------------
    # 2. Extract all domains and classify
    # ------------------------------
    all_domains = extract_domains(text)
    first_party = []
    third_party = []

    for d in all_domains:
        if d == domain_clean:
            first_party.append(d)
        else:
            third_party.append(d)

    # ------------------------------
    # 3. Sentiment Analysis
    # ------------------------------
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity  # -1 to 1
    if polarity > 0.1:
        sentiment = "positive"
    elif polarity < -0.1:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    return {
        "keyword": keyword,
        "response_text": text,
        "is_mentioned": is_mentioned,
        "mention_count": mention_count,
        "first_party_citations": first_party,
        "third_party_citations": third_party,
        "sentiment": sentiment,
        "sentiment_score": round(polarity, 3)
    }


@csrf_exempt
@api_view(["GET"])
@permission_classes((AllowAny,))
def manage_prompts(request):
    """Automatically process LLM prompts with INIT status using ChatGPT."""
    try:
        # Trigger automatic processing
        result = process_llm_prompts_automatically()
        
        if result["status"] == "success":
            return JsonResponse({
                "status": "true",
                "message": result["message"],
                "data": {
                    "prompt_id": result["prompt_id"],
                    "analytics_id": result["analytics_id"]
                }
            })
        elif result["status"] == "skipped":
            return JsonResponse({
                "status": "false",
                "message": result["message"]
            })
        elif result["status"] == "no_prompts":
            return JsonResponse({
                "status": "false",
                "message": result["message"]
            })
        else:  # error status
            return JsonResponse({
                "status": "false",
                "message": result["message"]
            })

    except Exception as e:
        logger.error(f"Error in manage_prompts: {str(e)}")
        return JsonResponse({"status": "false", "message": "Something went wrong"})


@api_view(["POST"])
def trigger_auto_processing(request):
    """Manually trigger automatic processing of LLM prompts."""
    try:
        result = process_llm_prompts_automatically()
        
        return JsonResponse({
            "status": "true" if result["status"] in ["success", "skipped", "no_prompts"] else "false",
            "message": result["message"],
            "data": result
        })

    except Exception as e:
        logger.error(f"Error in trigger_auto_processing: {str(e)}")
        return JsonResponse({"status": "false", "message": "Something went wrong"})


@api_view(["POST"])
def get_processing_status(request):
    """Get the current processing status of LLM prompts."""
    try:
        required_fields = ["userid"]
        validation_required = all(field in request.data for field in required_fields)

        if not validation_required:
            return JsonResponse({"status": "false", "message": "userid is required"})

        userid = request.data["userid"].strip()

        # Validate user exists
        try:
            user_instance = Account.objects.get(id=userid)
        except Account.DoesNotExist:
            return JsonResponse({"status": "false", "message": "Invalid user"})

        # Get status counts
        status_counts = {
            "INIT": LLMPrompt.objects.filter(fk_user=user_instance, track_status="INIT").count(),
            "SCHD": LLMPrompt.objects.filter(fk_user=user_instance, track_status="SCHD").count(),
            "DONE": LLMPrompt.objects.filter(fk_user=user_instance, track_status="DONE").count(),
            "FAIL": LLMPrompt.objects.filter(fk_user=user_instance, track_status="FAIL").count(),
        }

        # Get currently processing prompt (if any)
        current_processing = None
        scheduled_prompt = LLMPrompt.objects.filter(fk_user=user_instance, track_status="SCHD").first()
        if scheduled_prompt:
            current_processing = {
                "prompt_id": str(scheduled_prompt.prompt_id),
                "prompt": scheduled_prompt.prompt[:100] + "..." if len(scheduled_prompt.prompt) > 100 else scheduled_prompt.prompt,
                "track_message": scheduled_prompt.track_message,
                "started_at": scheduled_prompt.modified_date.strftime("%Y-%m-%d %H:%M:%S")
            }

        return JsonResponse({
            "status": "true",
            "data": {
                "status_counts": status_counts,
                "current_processing": current_processing,
                "total_prompts": sum(status_counts.values())
            }
        })

    except Exception as e:
        logger.error(f"Error in get_processing_status: {str(e)}")
        return JsonResponse({"status": "false", "message": "Something went wrong"})


@api_view(["GET"])
def get_citations_detail(request, analytics_id, model):
    """Get citations for a specific analytics record and model."""
    try:
        # Validate analytics_id format
        try:
            import uuid
            analytics_uuid = uuid.UUID(analytics_id)
        except ValueError:
            return JsonResponse({"status": "false", "message": "Invalid analytics_id format"})

        # Validate model (case-insensitive)
        valid_models = ["ChatGPT", "Gemini", "Perplexity"]
        model_lower = model.lower()
        valid_models_lower = [m.lower() for m in valid_models]
        
        if model_lower not in valid_models_lower:
            return JsonResponse({"status": "false", "message": f"Invalid model. Must be one of: {', '.join(valid_models)}"})
        
        # Normalize model name to proper case
        model_normalized = valid_models[valid_models_lower.index(model_lower)]

        # Get the analytics record
        try:
            analytics = LLMPromptAnalytics.objects.get(
                analytics_id=analytics_uuid,
                model=model_normalized
            )
        except LLMPromptAnalytics.DoesNotExist:
            return JsonResponse({"status": "false", "message": "Analytics record not found"})

        # Get citations (same format as original list_citations)
        citations = sorted(list(set(analytics.citations or [])))
        
        data = {
            "analytics_id": str(analytics.analytics_id),
            "model": analytics.model,
            "prompt_id": str(analytics.fk_prompt.prompt_id),
            "total_citations": len(citations),
            "citations": citations,
        }

        return JsonResponse({"status": "true", "data": data})

    except Exception as e:
        logger.error(f"Error in get_citations_detail: {str(e)}")
        return JsonResponse({"status": "false", "message": "Something went wrong"})


@api_view(["POST"])
def generate_prompts(request):
    """Generate prompts using ChatGPT based on a keyword with a specified limit."""
    try:
        # Validate required fields
        required_fields = ["userid", "keyword", "limit"]
        validation_required = all(field in request.data for field in required_fields)

        if not validation_required:
            return JsonResponse({
                "status": "false", 
                "message": "Missing required fields: userid, keyword and limit are required"
            })

        userid = request.data.get("userid", "").strip()
        keyword = request.data.get("keyword", "").strip()
        limit = request.data.get("limit")

        # Validate user exists
        if not userid:
            return JsonResponse({
                "status": "false", 
                "message": "userid cannot be empty"
            })

        try:
            user_instance = Account.objects.get(id=userid)
        except Account.DoesNotExist:
            return JsonResponse({
                "status": "false", 
                "message": "Invalid user"
            })

        # Validate keyword
        if not keyword:
            return JsonResponse({
                "status": "false", 
                "message": "Keyword cannot be empty"
            })

        # Validate limit
        try:
            limit = int(limit)
            if limit <= 0:
                return JsonResponse({
                    "status": "false", 
                    "message": "Limit must be a positive integer"
                })
            if limit > 50:
                return JsonResponse({
                    "status": "false", 
                    "message": "Limit cannot exceed 50 prompts"
                })
        except (ValueError, TypeError):
            return JsonResponse({
                "status": "false", 
                "message": "Limit must be a valid integer"
            })

        # Initialize ChatGPT client
        try:
            openai_client = get_openai_client()
        except Exception as e:
            logger.error(f"Failed to initialize ChatGPT client: {str(e)}")
            return JsonResponse({
                "status": "false", 
                "message": f"ChatGPT service not available: {str(e)}"
            })

        # Generate prompts using ChatGPT
        try:
            system_prompt = """You are an expert at generating diverse, relevant prompts for brand monitoring and LLM tracking. 
Generate prompts that would naturally lead to brand mentions or citations in AI responses. 
The prompts should cover different angles: comparisons, recommendations, tutorials, explanations, best practices, alternatives, etc.
Return ONLY a JSON array of prompts, with no additional text or formatting."""

            user_prompt = f"""Generate exactly {limit} diverse and relevant prompts related to the keyword: "{keyword}"

The prompts should:
1. Be natural questions or requests that someone might ask
2. Cover different aspects (comparisons, recommendations, how-to, explanations, alternatives)
3. Be likely to trigger detailed responses with citations
4. Be varied in structure and approach
5. Be suitable for brand/product monitoring

Return ONLY a JSON array format like this:
["prompt 1", "prompt 2", "prompt 3", ...]

Generate exactly {limit} prompts."""

            response = openai_client.chat.completions.create(
                model=getattr(settings, "OPENROUTER_INTERNAL_MODEL", "openai/gpt-5-mini"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.8,  # Higher temperature for more diverse prompts
                max_tokens=2000,
                timeout=60
            )

            generated_text = response.choices[0].message.content.strip()
            
            # Try to parse as JSON
            try:
                # Remove markdown code blocks if present
                if generated_text.startswith("```"):
                    # Remove ```json or ``` from start
                    generated_text = generated_text.split("\n", 1)[1] if "\n" in generated_text else generated_text[3:]
                if generated_text.endswith("```"):
                    generated_text = generated_text.rsplit("```", 1)[0]
                
                generated_text = generated_text.strip()
                
                # Parse JSON
                prompts_list = json.loads(generated_text)
                
                # Validate it's a list
                if not isinstance(prompts_list, list):
                    raise ValueError("Response is not a list")
                
                # Filter out empty strings and ensure all are strings
                prompts_list = [str(p).strip() for p in prompts_list if p and str(p).strip()]
                
                # Limit to requested count (in case GPT generated more)
                prompts_list = prompts_list[:limit]
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from ChatGPT: {generated_text}")
                # Fallback: Try to extract prompts from text
                # Split by newlines and filter
                prompts_list = [
                    line.strip().strip('"').strip("'").strip('-').strip()
                    for line in generated_text.split('\n')
                    if line.strip() and len(line.strip()) > 10
                ]
                prompts_list = prompts_list[:limit]
            
            if not prompts_list:
                return JsonResponse({
                    "status": "false", 
                    "message": "Failed to generate prompts"
                })

            logger.info(f"Successfully generated {len(prompts_list)} prompts for keyword: {keyword} (user: {userid})")

            return JsonResponse({
                "status": "true",
                "message": f"Successfully generated {len(prompts_list)} prompts",
                "data": {
                    "userid": userid,
                    "keyword": keyword,
                    "requested_limit": limit,
                    "generated_count": len(prompts_list),
                    "prompts": prompts_list
                }
            })

        except Exception as e:
            logger.error(f"Error generating prompts with ChatGPT: {str(e)}")
            return JsonResponse({
                "status": "false", 
                "message": f"Error generating prompts: {str(e)}"
            })

    except Exception as e:
        logger.error(f"Error in generate_prompts: {str(e)}")
        return JsonResponse({
            "status": "false", 
            "message": "Something went wrong"
        })


@api_view(["POST"])
def get_group_keywords(request):
    """Get paginated list of keywords for a specific user and group, including GSC keywords with source flags."""
    try:
        # Validate required fields
        required_fields = ["userid", "groupid"]
        validation_required = all(field in request.data for field in required_fields)

        if not validation_required:
            return JsonResponse({
                "status": "false", 
                "message": "Missing required fields: userid and groupid are required"
            })

        userid = request.data.get("userid", "").strip()
        groupid = request.data.get("groupid", "").strip()
        
        # Get limit and offset params (with defaults)
        limit = request.data.get("limit", 25)
        offset = request.data.get("offset", 0)

        # Validate userid
        if not userid:
            return JsonResponse({
                "status": "false", 
                "message": "userid cannot be empty"
            })

        # Validate groupid
        if not groupid:
            return JsonResponse({
                "status": "false", 
                "message": "groupid cannot be empty"
            })

        # Validate and convert limit and offset
        try:
            limit = int(limit)
            if limit < 1:
                limit = 25
            if limit > 100:  # Set a max limit to prevent abuse
                limit = 100
        except (ValueError, TypeError):
            limit = 25

        try:
            offset = int(offset)
            if offset < 0:
                offset = 0
        except (ValueError, TypeError):
            offset = 0

        # Validate user exists
        try:
            user_instance = Account.objects.get(id=userid)
        except Account.DoesNotExist:
            return JsonResponse({
                "status": "false", 
                "message": "Invalid user"
            })

        # Validate group exists and belongs to user
        try:
            group_instance = Groups.objects.get(id=groupid, fk_user_id=userid)
        except Groups.DoesNotExist:
            return JsonResponse({
                "status": "false", 
                "message": "Invalid group or group does not belong to user"
            })

        # Get keywords from Keyword model (tracked keywords)
        tracked_keywords_set = set(
            Keyword.objects.filter(
                fk_user_id=userid, 
                fk_group_id=groupid
            ).values_list('keyword', flat=True)
        )

        # Get keywords from GSC
        from serp.models import GSCDailyQuery, GSCWeeklyQuery, GSCMonthlyQuery
        
        gsc_keywords_set = set()
        gsc_source = None
        
        # Try to get from most recent GSCDailyQuery first
        latest_daily_gsc = GSCDailyQuery.objects.filter(
            fk_user_id=userid,
            fk_group_id=groupid
        ).order_by('-end_date').first()
        
        if latest_daily_gsc and latest_daily_gsc.queries:
            for query_data in latest_daily_gsc.queries:
                if isinstance(query_data, dict) and 'query' in query_data:
                    gsc_keywords_set.add(query_data['query'])
            if gsc_keywords_set:
                gsc_source = "daily"
        
        # Fallback to weekly if no daily data
        if not gsc_keywords_set:
            latest_weekly_gsc = GSCWeeklyQuery.objects.filter(
                fk_user_id=userid,
                fk_group_id=groupid
            ).order_by('-week_end_date').first()
            
            if latest_weekly_gsc and latest_weekly_gsc.queries:
                for query_data in latest_weekly_gsc.queries:
                    if isinstance(query_data, dict) and 'query' in query_data:
                        gsc_keywords_set.add(query_data['query'])
                if gsc_keywords_set:
                    gsc_source = "weekly"
        
        # Fallback to monthly if no weekly data
        if not gsc_keywords_set:
            latest_monthly_gsc = GSCMonthlyQuery.objects.filter(
                fk_user_id=userid,
                fk_group_id=groupid
            ).order_by('-month_end_date').first()
            
            if latest_monthly_gsc and latest_monthly_gsc.queries:
                for query_data in latest_monthly_gsc.queries:
                    if isinstance(query_data, dict) and 'query' in query_data:
                        gsc_keywords_set.add(query_data['query'])
                if gsc_keywords_set:
                    gsc_source = "monthly"

        # Create keyword objects with source flags
        all_keywords_dict = {}
        
        # Add tracked keywords
        for kw in tracked_keywords_set:
            all_keywords_dict[kw] = {
                "keyword": kw,
                "is_tracked": True,
                "is_gsc": kw in gsc_keywords_set
            }
        
        # Add GSC-only keywords (not in tracked)
        for kw in gsc_keywords_set:
            if kw not in all_keywords_dict:
                all_keywords_dict[kw] = {
                    "keyword": kw,
                    "is_tracked": False,
                    "is_gsc": True
                }
        
        # Sort keywords alphabetically
        all_keywords = sorted(all_keywords_dict.values(), key=lambda x: x['keyword'].lower())
        
        # Calculate totals
        total_tracked = len(tracked_keywords_set)
        total_gsc = len(gsc_keywords_set)
        total_keywords = len(all_keywords)
        total_both = len(tracked_keywords_set & gsc_keywords_set)  # Keywords in both sources
        
        # Apply offset and limit
        paginated_keywords = all_keywords[offset:offset + limit]
        
        # Calculate pagination info
        import math
        total_pages = math.ceil(total_keywords / limit) if total_keywords > 0 else 1
        current_page = (offset // limit) + 1
        
        logger.info(f"Retrieved {len(paginated_keywords)} keywords (limit: {limit}, offset: {offset}) for user {userid}, group {groupid}. Tracked: {total_tracked}, GSC: {total_gsc}, Total: {total_keywords}")

        return JsonResponse({
            "status": "true",
            "message": f"Successfully retrieved {len(paginated_keywords)} keywords",
            "data": {
                "userid": userid,
                "groupid": groupid,
                "limit": limit,
                "offset": offset,
                "current_page": current_page,
                "total_keywords": total_keywords,
                "total_tracked_keywords": total_tracked,
                "total_gsc_keywords": total_gsc,
                "total_both_sources": total_both,
                "total_pages": total_pages,
                "has_next": (offset + limit) < total_keywords,
                "has_previous": offset > 0,
                "gsc_source": gsc_source,
                "keywords": paginated_keywords
            }
        })

    except Exception as e:
        logger.error(f"Error in get_group_keywords: {str(e)}")
        return JsonResponse({
            "status": "false", 
            "message": "Something went wrong"
        })


@api_view(["POST"])
@permission_classes([AllowAny])
def reset_track_status(request):
    """
    Reset track_status for domains, prompt groups, or prompts to INIT.
    Useful for testing and reprocessing.
    
    Request body:
    {
        "entity_type": "domain" | "prompt_group" | "prompt",
        "entity_id": <id>,
        "reset_to": "INIT" (default) | "SCHD" | "PROC"
    }
    """
    try:
        from shared_models.models import Domain, PromptGroup, Prompt
        from django.utils import timezone
        
        data = json.loads(request.body)
        entity_type = data.get('entity_type')
        entity_id = data.get('entity_id')
        reset_to = data.get('reset_to', 'INIT')
        
        if not entity_type or not entity_id:
            return JsonResponse({
                "status": "error",
                "message": "entity_type and entity_id are required"
            }, status=400)
        
        if reset_to not in ['INIT', 'SCHD', 'PROC']:
            return JsonResponse({
                "status": "error",
                "message": "reset_to must be INIT, SCHD, or PROC"
            }, status=400)
        
        if entity_type == 'domain':
            try:
                entity = Domain.objects.get(id=entity_id)
                entity.processing_status = reset_to
                entity.track_message = f"Reset to {reset_to} via API"
                entity.tracked_at = timezone.now()
                entity.save(update_fields=['processing_status', 'track_message', 'tracked_at', 'modified_at'])
                
                return JsonResponse({
                    "status": "success",
                    "message": f"Domain {entity_id} reset to {reset_to}",
                    "entity_type": "domain",
                    "entity_id": entity_id,
                    "new_status": reset_to
                })
            except Domain.DoesNotExist:
                return JsonResponse({
                    "status": "error",
                    "message": f"Domain with id {entity_id} not found"
                }, status=404)
        
        elif entity_type == 'prompt_group':
            try:
                entity = PromptGroup.objects.get(id=entity_id)
                entity.track_status = reset_to
                entity.track_message = f"Reset to {reset_to} via API"
                entity.tracked_at = timezone.now()
                entity.save(update_fields=['track_status', 'track_message', 'tracked_at', 'modified_at'])
                
                return JsonResponse({
                    "status": "success",
                    "message": f"PromptGroup {entity_id} reset to {reset_to}",
                    "entity_type": "prompt_group",
                    "entity_id": entity_id,
                    "new_status": reset_to
                })
            except PromptGroup.DoesNotExist:
                return JsonResponse({
                    "status": "error",
                    "message": f"PromptGroup with id {entity_id} not found"
                }, status=404)
        
        elif entity_type == 'prompt':
            try:
                entity = Prompt.objects.get(id=entity_id)
                entity.track_status = reset_to
                entity.track_message = f"Reset to {reset_to} via API"
                entity.tracked_at = timezone.now()
                entity.save(update_fields=['track_status', 'track_message', 'tracked_at', 'modified_at'])
                
                return JsonResponse({
                    "status": "success",
                    "message": f"Prompt {entity_id} reset to {reset_to}",
                    "entity_type": "prompt",
                    "entity_id": entity_id,
                    "new_status": reset_to
                })
            except Prompt.DoesNotExist:
                return JsonResponse({
                    "status": "error",
                    "message": f"Prompt with id {entity_id} not found"
                }, status=404)
        
        else:
            return JsonResponse({
                "status": "error",
                "message": f"Invalid entity_type: {entity_type}. Must be 'domain', 'prompt_group', or 'prompt'"
            }, status=400)
    
    except json.JSONDecodeError:
        return JsonResponse({
            "status": "error",
            "message": "Invalid JSON in request body"
        }, status=400)
    except Exception as e:
        logger.error(f"Error resetting track_status: {str(e)}")
        return JsonResponse({
            "status": "error",
            "message": f"Error resetting track_status: {str(e)}"
        }, status=500)


