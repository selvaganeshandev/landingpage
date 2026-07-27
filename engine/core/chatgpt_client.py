from typing import List, Dict, Any, Optional
import random
import json
import re
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class ChatGPTClient:
    """
    Client for OpenAI ChatGPT API integration
    """
    
    def __init__(self, api_key: str = None, org_id: int = None):
        self.org_id = org_id
        # Key resolution order: explicit arg > per-org BYOK (resolved lazily in
        # _ensure_client) > .env. When an org_id is supplied we defer to
        # _ensure_client so the per-org key wins; otherwise keep the legacy
        # .env behaviour so existing callers are unaffected.
        if api_key:
            self.api_key = api_key
        elif org_id is not None:
            self.api_key = None  # resolved lazily via BYOK below
        else:
            self.api_key = getattr(settings, 'OPENAI_API_KEY', None)
        self.client = None  # lazy init

    def _resolve_byok_key(self):
        """Resolve the OpenAI key for self.org_id via the BYOK service (DB key,
        falling back to .env). Returns None if the provider is disabled for the
        org or no key is configured anywhere."""
        try:
            from .services.api_key_service import get_org_settings, get_api_key, is_enabled
            org = get_org_settings(self.org_id)
            if not is_enabled(org, 'openai'):
                logger.info(f"OpenAI disabled for org {self.org_id}; skipping client init")
                return None
            return get_api_key(org, 'openai')
        except Exception as e:
            logger.warning(f"BYOK key resolution failed for org {self.org_id}: {e}")
            # Fall back to .env on any resolution error
            return getattr(settings, 'OPENAI_API_KEY', None)

    def _ensure_client(self):
        if self.client is not None:
            return
        if not self.api_key and self.org_id is not None:
            self.api_key = self._resolve_byok_key()
        if not self.api_key:
            logger.debug("OPENAI_API_KEY not set, client will not be initialized")
            return
        try:
            # Internal (non-measured) work runs through OpenRouter on the cheap
            # internal slug. The tracked ChatGPT call does NOT use this class —
            # it shares the transport but keeps OPENAI_CHATGPT_MODEL so the
            # measurement still reflects real ChatGPT output.
            from .services.client_factory import get_internal_client
            self.client = get_internal_client(self.org_id)
            # Keep api_key populated so the "is an LLM usable" guards elsewhere in
            # this class stay meaningful; it is now the OpenRouter credential.
            self.api_key = getattr(settings, 'OPENROUTER_API_KEY', None) or self.api_key
            logger.debug("Internal LLM client (OpenRouter) initialized successfully")
        except Exception as e:
            # Defer to local generation if client cannot be created
            logger.warning(f"Failed to initialize internal LLM client: {str(e)}")
            self.client = None
    
    def generate_prompts_from_keywords(self, keywords: List[str], domain_name: str, country: str = "United States") -> List[Dict[str, Any]]:
        """
        Generate prompts from keywords using ChatGPT
        
        Args:
            keywords: List of keywords to generate prompts from
            domain_name: Name of the domain for context
            country: Country name for context (default: "United States")
            
        Returns:
            List of generated prompts with metadata
        """
        if not keywords:
            return []
        
        # Try OpenAI; if not available, fall back to local generation
        self._ensure_client()
        if not self.client:
            if not self.api_key:
                logger.warning(f"OPENAI_API_KEY not configured, using local generation for {len(keywords)} keywords")
            else:
                logger.warning(f"Failed to initialize OpenAI client, using local generation for {len(keywords)} keywords")
            return self._local_generate_prompts(keywords, domain_name)

        # Calculate total prompts: keywords * PROMPT_MIN_COUNT (prompts per keyword)
        prompts_per_keyword = getattr(settings, 'PROMPT_MIN_COUNT', 2)
        total_prompts = len(keywords) * prompts_per_keyword
        
        # Create a system prompt for generating short, natural prompts like real ChatGPT users write
        system_prompt = f"""Generate short, natural prompts that real ChatGPT users would type for the given keywords.

Context: Generate prompts that are relevant to users in {country}. Consider local context, services, and preferences when appropriate.

Guidelines:
- Keep prompts SHORT (1 sentence, max 15-20 words)
- Use conversational, natural language (like "What is...", "Tell me about...", "How to...")
- Make them feel like real user queries, not formal business questions
- Incorporate the keyword naturally
- Each prompt should be a simple, direct question or request
- Consider {country}-specific context when relevant (e.g., local services, regulations, market conditions)

Return ONLY a JSON array with this structure:
[
  {{
    "prompt_text": "Short natural prompt (1 sentence)",
    "keyword": "original keyword",
    "category": "Category name",
    "priority": "High|Medium|Low"
  }},
  ...
]

Generate exactly {total_prompts} distinct short prompts ({prompts_per_keyword} prompts per keyword). Return ONLY the JSON array, no markdown, no explanations."""
        
        # Prepare the user message with keywords
        # Use up to KEYWORD_EXTRACT_LIMIT keywords to ensure diversity
        kw_limit = getattr(settings, 'KEYWORD_EXTRACT_LIMIT', 50)
        keywords_text = ", ".join(keywords[:kw_limit])
        user_message = f"""Generate short, natural prompts (1 sentence each) for these keywords: {keywords_text}

Make them like real ChatGPT user queries - short and conversational. Return ONLY JSON array."""
        
        try:
            logger.info(f"Generating prompts using ChatGPT (gpt-4o-mini) for {len(keywords)} keywords, domain: {domain_name}")
            response = self.client.chat.completions.create(
                model=getattr(settings, "OPENROUTER_INTERNAL_MODEL", "openai/gpt-5-mini"),  # Using cheaper mini model
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=3000,
                timeout=60
            )
            
            # Parse the response
            content = response.choices[0].message.content.strip()
            logger.debug(f"Received ChatGPT response (length: {len(content)} chars)")
            parsed_prompts = self._parse_prompts_response(content, keywords)
            
            # Limit to calculated total (keywords * prompts_per_keyword)
            prompts_per_keyword = getattr(settings, 'PROMPT_MIN_COUNT', 2)
            expected_total = len(keywords) * prompts_per_keyword
            if len(parsed_prompts) > expected_total:
                logger.info(f"Limiting prompts from {len(parsed_prompts)} to {expected_total} (calculated: {len(keywords)} keywords × {prompts_per_keyword} prompts per keyword)")
                parsed_prompts = parsed_prompts[:expected_total]
            
            logger.info(f"Successfully parsed {len(parsed_prompts)} prompts from ChatGPT response")
            return parsed_prompts
            
        except Exception as e:
            logger.error(f"Error generating prompts with ChatGPT: {str(e)}, falling back to local generation", exc_info=True)
            return self._local_generate_prompts(keywords, domain_name)
    
    def _parse_prompts_response(self, content: str, original_keywords: List[str]) -> List[Dict[str, Any]]:
        """
        Parse the ChatGPT response to extract structured prompts
        Tries JSON parsing first, then falls back to line-based parsing, then template-based generation
        """
        prompts = []
        
        # Step 1: Try JSON parsing (preferred method)
        try:
            # Remove markdown code blocks if present
            content_clean = content.strip()
            if content_clean.startswith('```json'):
                content_clean = content_clean[7:].strip()
            elif content_clean.startswith('```'):
                content_clean = content_clean[3:].strip()
            if content_clean.endswith('```'):
                content_clean = content_clean[:-3].strip()
            
            # Try to parse as JSON
            parsed_data = json.loads(content_clean)
            
            # Handle different JSON structures
            if isinstance(parsed_data, list):
                prompts = parsed_data
            elif isinstance(parsed_data, dict):
                # If it's a dict, look for common keys
                if 'prompts' in parsed_data:
                    prompts = parsed_data['prompts']
                elif 'data' in parsed_data:
                    prompts = parsed_data['data']
                else:
                    # Try to extract array from dict values
                    for value in parsed_data.values():
                        if isinstance(value, list):
                            prompts = value
                            break
            
            # Validate parsed prompts
            if prompts:
                validated_prompts = []
                for p in prompts:
                    if isinstance(p, dict) and 'prompt_text' in p:
                        validated_prompts.append({
                            'prompt_text': str(p.get('prompt_text', '')).strip(),
                            'keyword': str(p.get('keyword', '')).strip() or '',
                            'category': str(p.get('category', 'General')).strip() or 'General',
                            'priority': str(p.get('priority', 'Medium')).strip() or 'Medium'
                        })
                    elif isinstance(p, str) and p.strip():
                        # If it's just a string, treat it as prompt_text
                        validated_prompts.append({
                            'prompt_text': p.strip(),
                            'keyword': '',
                            'category': 'General',
                            'priority': 'Medium'
                        })
                
                if validated_prompts:
                    logger.info(f"Successfully parsed {len(validated_prompts)} prompts from JSON response")
                    return validated_prompts
                    
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Failed to parse JSON response: {str(e)}, trying line-based parsing")
        
        # Step 2: Fallback to line-based parsing (for non-JSON responses)
        lines = content.split('\n')
        current_prompt = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('**Prompt:**') or line.startswith('Prompt:'):
                if current_prompt and current_prompt.get('prompt_text'):
                    prompts.append(current_prompt)
                current_prompt = {
                    'prompt_text': line.replace('**Prompt:**', '').replace('Prompt:', '').strip(),
                    'keyword': '',
                    'category': 'General',
                    'priority': 'Medium'
                }
            elif line.startswith('**Keyword:**') or line.startswith('Keyword:'):
                if current_prompt:
                    current_prompt['keyword'] = line.replace('**Keyword:**', '').replace('Keyword:', '').strip()
            elif line.startswith('**Category:**') or line.startswith('Category:'):
                if current_prompt:
                    current_prompt['category'] = line.replace('**Category:**', '').replace('Category:', '').strip()
            elif line.startswith('**Priority:**') or line.startswith('Priority:'):
                if current_prompt:
                    current_prompt['priority'] = line.replace('**Priority:**', '').replace('Priority:', '').strip()
            elif current_prompt and not current_prompt.get('prompt_text'):
                # If we have a current prompt but no prompt_text yet, this line might be the prompt
                if not line.startswith('**') and len(line) > 10:
                    current_prompt['prompt_text'] = line
        
        # Add the last prompt if exists
        if current_prompt and current_prompt.get('prompt_text'):
            prompts.append(current_prompt)
        
        # Step 3: If still no prompts found, try regex extraction
        if not prompts:
            # Try to extract quoted strings or numbered list items
            quoted_prompts = re.findall(r'"([^"]+)"', content)
            if not quoted_prompts:
                quoted_prompts = re.findall(r"'([^']+)'", content)
            if not quoted_prompts:
                # Try numbered list format
                quoted_prompts = re.findall(r'\d+\.\s*(.+?)(?=\n|$)', content, re.MULTILINE)
            
            if quoted_prompts:
                for prompt_text in quoted_prompts:
                    prompt_text = prompt_text.strip()
                    if len(prompt_text) > 10:  # Minimum length check
                        prompts.append({
                            'prompt_text': prompt_text,
                            'keyword': '',
                            'category': 'General',
                            'priority': 'Medium'
                        })
        
        # Step 4: If no structured prompts found, create short simple prompts from keywords
        if not prompts:
            logger.warning(f"No prompts could be parsed from ChatGPT response, using template-based fallback")
            kw_limit = getattr(settings, 'KEYWORD_EXTRACT_LIMIT', 50)
            prompts_per_keyword = getattr(settings, 'PROMPT_MIN_COUNT', 2)
            prompt_limit = len(original_keywords) * prompts_per_keyword
            # Short, natural templates like real ChatGPT users write
            diverse_templates = [
                "What is {kw}?",
                "Tell me about {kw}.",
                "How does {kw} work?",
                "What are the benefits of {kw}?",
                "Explain {kw} in simple terms.",
                "What is {kw} used for?",
                "How to use {kw}?",
                "What are the features of {kw}?",
                "Compare {kw} with alternatives.",
                "What should I know about {kw}?",
                "Is {kw} worth it?",
                "How to choose {kw}?",
                "What are the pros and cons of {kw}?",
                "Tell me everything about {kw}.",
                "What makes {kw} good?"
            ]
            # Generate prompts_per_keyword prompts for each keyword
            prompt_count = 0
            for keyword in original_keywords[:kw_limit]:
                if prompt_count >= prompt_limit:
                    break
                # Generate prompts_per_keyword prompts for this keyword
                for i in range(prompts_per_keyword):
                    if prompt_count >= prompt_limit:
                        break
                    tpl = diverse_templates[prompt_count % len(diverse_templates)]
                    prompts.append({
                        'prompt_text': tpl.format(kw=keyword),
                        'keyword': keyword,
                        'category': 'General',
                        'priority': 'Medium'
                    })
                    prompt_count += 1
        
        # Ensure we have at least some prompts
        if not prompts and original_keywords:
            logger.warning(f"Failed to generate any prompts, creating minimal prompts from keywords")
            prompts_per_keyword = getattr(settings, 'PROMPT_MIN_COUNT', 2)
            prompt_limit = len(original_keywords) * prompts_per_keyword
            keyword_index = 0
            prompt_count = 0
            while prompt_count < prompt_limit and keyword_index < len(original_keywords):
                keyword = original_keywords[keyword_index]
                prompts.append({
                    'prompt_text': f"What is {keyword}?",
                    'keyword': keyword,
                    'category': 'General',
                    'priority': 'Medium'
                })
                prompt_count += 1
                # Move to next keyword after generating prompts_per_keyword prompts for current keyword
                if prompt_count % prompts_per_keyword == 0:
                    keyword_index += 1
        
        # Final limit check to ensure we don't exceed the calculated limit
        prompts_per_keyword = getattr(settings, 'PROMPT_MIN_COUNT', 2)
        prompt_limit = len(original_keywords) * prompts_per_keyword
        if len(prompts) > prompt_limit:
            prompts = prompts[:prompt_limit]
        
        return prompts

    def generate_group_title(self, prompts_texts: List[str]) -> Optional[str]:
        """
        Generate a concise title (2-4 words) for a cluster of prompts using ALL prompts in the group.
        Returns None if the OpenAI client is unavailable or the call fails.
        """
        if not prompts_texts:
            return None

        self._ensure_client()
        if not self.client:
            return None

        # Use ALL prompts (not just a sample) to generate a comprehensive title
        # Limit to 50 prompts to avoid extremely long requests, but use all available if less
        all_prompts = prompts_texts[:50] if len(prompts_texts) > 50 else prompts_texts
        prompts_block = "\n".join([f"{idx + 1}. {text}" for idx, text in enumerate(all_prompts)])

        system_prompt = (
            "You create concise, professional topic titles. "
            "Output only the title, no explanations. "
            "Title must be 2-4 words, noun-based, no numbers, no questions."
        )
        user_prompt = (
            f"Generate a short, descriptive title that represents ALL {len(all_prompts)} prompts in this group:\n\n"
            f"{prompts_block}\n\n"
            "Consider all prompts (both primary and secondary) when generating the title. "
            "Return only the title."
        )

        try:
            response = self.client.chat.completions.create(
                model=getattr(settings, "OPENROUTER_INTERNAL_MODEL", "openai/gpt-5-mini"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                # gpt-5-mini is a reasoning model: it spends hidden reasoning
                # tokens before emitting any text, so a tight ceiling returns
                # finish_reason='length' with content=None and the .strip() below
                # raises. This is a ceiling, not a target - short answers stop early.
                max_tokens=1000,
                timeout=30,
            )
            title = response.choices[0].message.content.strip()
            # Use first line only and strip quotes
            title = title.splitlines()[0].strip().strip('"').strip("'")
            return title or None
        except Exception as exc:
            logger.warning(f"Failed to generate group title with ChatGPT: {exc}")
            return None

    def _extract_title_from_prompt(self, prompt: str) -> str:
        """
        Extract key terms from a single prompt to create a title.
        Uses GPT-4o-mini for intelligent extraction.

        Example:
            Input: "What helps with relieving vaginal dryness?"
            Output: "Vaginal Dryness Relief"
        """
        self._ensure_client()
        if not self.client:
            raise Exception("OpenAI client not available")

        system_prompt = (
            "You are a keyword extraction expert. Extract the main topic/subject from the user's question. "
            "Return a concise, descriptive title that captures the full essence of the question. "
            "Remove question words (what, how, why, etc.) and filler words (the, a, some, best, etc.). "
            "Keep the complete core subject matter - don't truncate important context like company names or specific products. "
            "Keep it brief but complete (maximum 6 words). "
            "Format: Title Case (e.g., 'Vaginal Dryness Relief', 'Employee Rewards Program India', 'Indiabulls Securities Trading'). "
            "Return ONLY the extracted title, nothing else."
        )

        try:
            response = self.client.chat.completions.create(
                model=getattr(settings, "OPENROUTER_INTERNAL_MODEL", "openai/gpt-5-mini"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Extract key terms from: {prompt}"},
                ],
                temperature=0.1,  # Low temperature for consistent extraction
                # Ceiling raised for the reasoning model - see note above. The
                # answer is still short; the budget just has to cover reasoning.
                max_tokens=1000,
                timeout=30,
            )
            title = response.choices[0].message.content.strip()
            # Clean up the response
            title = title.strip('"').strip("'").strip('.')

            # Validate: should be 2-4 words
            word_count = len(title.split())
            if word_count < 2 or word_count > 6:
                logger.warning(f"GPT returned {word_count} words for '{prompt}': '{title}'")

            return title if title else "General"
        except Exception as exc:
            logger.warning(f"Failed to extract title from prompt using GPT: {exc}")
            raise  # Re-raise to trigger fallback in caller

    def _local_generate_prompts(self, keywords: List[str], domain_name: str) -> List[Dict[str, Any]]:
        # Generate short, natural prompts like real ChatGPT users write
        prompts: List[Dict[str, Any]] = []
        kw_limit = getattr(settings, 'KEYWORD_EXTRACT_LIMIT', 50)
        prompts_per_keyword = getattr(settings, 'PROMPT_MIN_COUNT', 2)
        prompt_limit = len(keywords) * prompts_per_keyword
        # Short, conversational templates (1 sentence, max 15-20 words)
        diverse_templates = [
            "What is {kw}?",
            "Tell me about {kw}.",
            "How does {kw} work?",
            "What are the benefits of {kw}?",
            "Explain {kw} in simple terms.",
            "What is {kw} used for?",
            "How to use {kw}?",
            "What are the features of {kw}?",
            "Compare {kw} with alternatives.",
            "What should I know about {kw}?",
            "Is {kw} worth it?",
            "How to choose {kw}?",
            "What are the pros and cons of {kw}?",
            "Tell me everything about {kw}.",
            "What makes {kw} good?",
            "Why is {kw} popular?",
            "How to get started with {kw}?",
            "What are the best {kw} options?",
            "Should I use {kw}?",
            "What do I need to know about {kw}?"
        ]
        # Generate prompts_per_keyword prompts for each keyword
        prompt_count = 0
        for kw in keywords[:kw_limit]:
            if prompt_count >= prompt_limit:
                break
            # Generate prompts_per_keyword prompts for this keyword
            for i in range(prompts_per_keyword):
                if prompt_count >= prompt_limit:
                    break
                tpl = diverse_templates[prompt_count % len(diverse_templates)]
                prompts.append({
                    'prompt_text': tpl.format(kw=kw),
                    'keyword': kw,
                    'category': 'General',
                    'priority': 'Medium'
                })
                prompt_count += 1
        return prompts
    
    def group_prompts_with_nlp(self, prompts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Use ChatGPT to group related prompts using NLP techniques
        
        Args:
            prompts: List of prompts to group
            
        Returns:
            List of grouped prompts with group information
        """
        if not prompts:
            return []
        
        # Create a system prompt for grouping - request term-based group names (not questions)
        system_prompt = """
        You are an expert in natural language processing and content organization. 
        Your task is to group related prompts into logical sets based on their content, 
        keywords, and themes.
        
        For each group, provide:
        1. A descriptive group title (as a TERM, NOT a question or incomplete sentence)
           - Use noun phrases with MAXIMUM 2 words that represent the MAIN TOPIC/SUBJECT
           - Focus on the actual subject matter (e.g., "Medicine Apps", "Purchase Delivery")
           - If 2 words, join them with a space (e.g., "Product Features", "Medicine Purchase")
           - If 1 word, use just that word if it's the main topic (e.g., "Medicines", "Pricing")
           - Avoid questions like "What is...", "How to...", "Tell me about..."
           - Avoid incomplete sentences or phrases
           - NEVER include numbers in titles (no "1", "2", "Cluster 1", etc.)
           - NEVER use descriptive/qualitative words like "good", "best", "there", "here" in titles
           - NEVER use verbs like "buy", "purchase" alone - combine with nouns or use the noun instead
           - Each group title must be UNIQUE and DISTINCT from other groups
           - Examples: "Medicine Apps", "Purchase Delivery", "Pricing", "Support Resources"
        2. Primary prompts (1-3 most important prompts in the group)
        3. Secondary prompts (supporting prompts in the group)
        4. Group description explaining the common theme
        
        Group prompts that:
        - Share similar topics or themes
        - Target the same audience
        - Have complementary content
        - Can be used together in a content strategy
        
        Ensure each group has at least 1 primary prompt.
        IMPORTANT: Group titles must be TERMS (1-2 words max, joined with space if 2 words), never questions or incomplete sentences.
        """
        
        # Prepare the user message with prompts
        prompts_text = "\n".join([
            f"{i+1}. {prompt['prompt_text']} (Keyword: {prompt.get('keyword', 'N/A')})"
            for i, prompt in enumerate(prompts)
        ])
        
        user_message = f"""
        Group these prompts into logical sets:
        
        {prompts_text}
        
        Please organize them into groups with clear themes. 
        IMPORTANT: Group titles must be TERMS with MAXIMUM 2 words:
        - If 2 words: join with space (e.g., "Product Features", "Pricing Information")
        - If 1 word: use just that word (e.g., "Features", "Pricing")
        - NOT questions or incomplete sentences
        - NEVER include numbers in titles (no "1", "2", "Cluster 1", etc.)
        - Each group title must be UNIQUE and DISTINCT from other groups
        - Examples: "Product Features", "User Guide", "Pricing", "Support Resources"
        
        Provide a group title, primary prompts, secondary prompts, and description for each group.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=getattr(settings, "OPENROUTER_INTERNAL_MODEL", "openai/gpt-5-mini"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,  # Lower temperature for more consistent grouping
                max_tokens=4000,
                timeout=60
            )
            
            content = response.choices[0].message.content
            return self._parse_grouped_prompts(content, prompts)
            
        except Exception as e:
            logger.error(f"Error grouping prompts with ChatGPT: {str(e)}, using fallback grouping", exc_info=True)
            # Fallback: create simple groups with term-based names
            return self._create_fallback_groups(prompts)
    
    def _parse_grouped_prompts(self, content: str, original_prompts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse the grouped prompts response
        Ensures group titles are terms/phrases, not questions
        """
        groups = []
        
        # Simple parsing - in a real implementation, you might want more sophisticated parsing
        lines = content.split('\n')
        current_group = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('**Group') or line.startswith('Group'):
                if current_group:
                    # Ensure title is term-based before adding
                    if current_group.get('title'):
                        current_group['title'] = self._ensure_term_based_title(current_group['title'])
                    groups.append(current_group)
                current_group = {
                    'title': line,
                    'description': '',
                    'primary_prompts': [],
                    'secondary_prompts': []
                }
            elif line.startswith('**Title:**') or line.startswith('Title:'):
                title = line.replace('**Title:**', '').replace('Title:', '').strip()
                current_group['title'] = self._ensure_term_based_title(title)
            elif line.startswith('**Description:**') or line.startswith('Description:'):
                current_group['description'] = line.replace('**Description:**', '').replace('Description:', '').strip()
            elif line.startswith('**Primary:**') or line.startswith('Primary:'):
                # Extract primary prompts
                primary_text = line.replace('**Primary:**', '').replace('Primary:', '').strip()
                current_group['primary_prompts'] = [p.strip() for p in primary_text.split(',') if p.strip()]
            elif line.startswith('**Secondary:**') or line.startswith('Secondary:'):
                # Extract secondary prompts
                secondary_text = line.replace('**Secondary:**', '').replace('Secondary:', '').strip()
                current_group['secondary_prompts'] = [p.strip() for p in secondary_text.split(',') if p.strip()]
        
        # Add the last group if exists
        if current_group:
            # Ensure title is term-based before adding
            if current_group.get('title'):
                current_group['title'] = self._ensure_term_based_title(current_group['title'])
            groups.append(current_group)
        
        # If no groups found, create fallback groups
        if not groups:
            return self._create_fallback_groups(original_prompts)
        
        return groups
    
    def _ensure_term_based_title(self, title: str) -> str:
        """
        Ensure a group title is term-based (not a question or incomplete sentence)
        Converts to max 2 words, joined with space if 2 words
        """
        if not title or not title.strip():
            return 'General'
        
        title_clean = title.strip()
        
        # Remove question marks
        if title_clean.endswith('?'):
            title_clean = title_clean[:-1].strip()
        
        # Remove common question starters
        question_starters = [
            'what is', 'what are', 'what do', 'what does', 'what did',
            'how to', 'how does', 'how do', 'how can', 'how will',
            'why is', 'why are', 'why do', 'why does',
            'when to', 'when is', 'when are', 'when do', 'when does',
            'where to', 'where is', 'where are', 'where do', 'where does',
            'who is', 'who are', 'who do', 'who does',
            'tell me', 'explain', 'describe', 'show me', 'give me'
        ]
        
        text_lower = title_clean.lower()
        for starter in question_starters:
            if text_lower.startswith(starter):
                # Extract the main term after the question starter
                remaining = title_clean[len(starter):].strip()
                title_clean = remaining.strip('?').strip(' :-\'".,')
                break
        
        # Split into words and filter
        words = title_clean.split()
        
        # Filter out stop words and keep meaningful words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this',
            'that', 'these', 'those', 'it', 'its', 'they', 'them', 'their'
        }
        
        meaningful_words = []
        for word in words:
            # Remove punctuation
            word_clean = word.strip('.,!?;:\'"()[]{}').lower()
            if word_clean and word_clean not in stop_words and len(word_clean) > 1:
                meaningful_words.append(word_clean)
        
        # Limit to max 2 words
        if len(meaningful_words) > 2:
            meaningful_words = meaningful_words[:2]
        
        # If no meaningful words, return default
        if not meaningful_words:
            return 'General'
        
            # Capitalize first letter of each word
        capitalized = [word.capitalize() for word in meaningful_words]
        
        # Join with space if 2 words, otherwise return single word
        if len(capitalized) == 2:
            return f"{capitalized[0]} {capitalized[1]}"
        else:
            return capitalized[0]
    
    def _create_fallback_groups(self, prompts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Create fallback groups when ChatGPT grouping fails
        Uses term-based group names (not questions)
        """
        if not prompts:
            return []
        
        # Simple grouping by category with term-based names
        groups = {}
        for prompt in prompts:
            category = prompt.get('category', 'General')
            if category not in groups:
                # Create term-based group title (not a question)
                # Convert category to a term/phrase format
                group_title = self._category_to_term(category)
                groups[category] = {
                    'title': group_title,
                    'description': f"Prompts related to {category}",
                    'primary_prompts': [],
                    'secondary_prompts': []
                }
            
            # Add to primary or secondary based on priority
            if prompt.get('priority', 'Medium') == 'High':
                groups[category]['primary_prompts'].append(prompt['prompt_text'])
            else:
                groups[category]['secondary_prompts'].append(prompt['prompt_text'])
        
        # Ensure each group has at least one primary prompt
        for group in groups.values():
            if not group['primary_prompts'] and group['secondary_prompts']:
                # Move first secondary to primary
                group['primary_prompts'].append(group['secondary_prompts'].pop(0))
        
        return list(groups.values())
    
    def _category_to_term(self, category: str) -> str:
        """
        Convert a category name to a term-based group title (max 2 words, joined with space)
        Examples:
        - "General" -> "General"
        - "Product" -> "Product"
        - "Product Features" -> "Product Features"
        - "Pricing Information" -> "Pricing Information"
        """
        # Use the same normalization logic as _ensure_term_based_title
        return self._ensure_term_based_title(category)
