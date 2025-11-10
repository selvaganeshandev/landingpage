from typing import List, Dict, Any
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
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or getattr(settings, 'OPENAI_API_KEY', None)
        self.client = None  # lazy init

    def _ensure_client(self):
        if self.client is not None:
            return
        if not self.api_key:
            logger.debug("OPENAI_API_KEY not set, client will not be initialized")
            return
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key, timeout=60)
            logger.debug("OpenAI client initialized successfully")
        except Exception as e:
            # Defer to local generation if client cannot be created
            logger.warning(f"Failed to initialize OpenAI client: {str(e)}")
            self.client = None
    
    def generate_prompts_from_keywords(self, keywords: List[str], domain_name: str) -> List[Dict[str, Any]]:
        """
        Generate prompts from keywords using ChatGPT
        
        Args:
            keywords: List of keywords to generate prompts from
            domain_name: Name of the domain for context
            
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

        # Create a system prompt for generating short, natural prompts like real ChatGPT users write
        system_prompt = f"""Generate short, natural prompts that real ChatGPT users would type for keywords related to "{domain_name}".

Guidelines:
- Keep prompts SHORT (1 sentence, max 15-20 words)
- Use conversational, natural language (like "What is...", "Tell me about...", "How to...")
- Make them feel like real user queries, not formal business questions
- Incorporate the keyword naturally
- Each prompt should be a simple, direct question or request

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

Generate 10-15 distinct short prompts. Return ONLY the JSON array, no markdown, no explanations."""
        
        # Prepare the user message with keywords
        # Use up to KEYWORD_EXTRACT_LIMIT keywords to ensure diversity
        kw_limit = getattr(settings, 'KEYWORD_EXTRACT_LIMIT', 50)
        keywords_text = ", ".join(keywords[:kw_limit])
        user_message = f"""Generate short, natural prompts (1 sentence each) for these keywords: {keywords_text}

Make them like real ChatGPT user queries - short and conversational. Return ONLY JSON array."""
        
        try:
            logger.info(f"Generating prompts using ChatGPT for {len(keywords)} keywords, domain: {domain_name}")
            response = self.client.chat.completions.create(
                model="gpt-4o",
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
            for i, keyword in enumerate(original_keywords[:kw_limit]):
                tpl = diverse_templates[i % len(diverse_templates)]
                prompts.append({
                    'prompt_text': tpl.format(kw=keyword),
                    'keyword': keyword,
                    'category': 'General',
                    'priority': 'Medium'
                })
        
        # Ensure we have at least some prompts
        if not prompts and original_keywords:
            logger.warning(f"Failed to generate any prompts, creating minimal prompts from keywords")
            for keyword in original_keywords[:10]:
                prompts.append({
                    'prompt_text': f"What is {keyword}?",
                    'keyword': keyword,
                    'category': 'General',
                    'priority': 'Medium'
                })
        
        return prompts

    def _local_generate_prompts(self, keywords: List[str], domain_name: str) -> List[Dict[str, Any]]:
        # Generate short, natural prompts like real ChatGPT users write
        prompts: List[Dict[str, Any]] = []
        kw_limit = getattr(settings, 'KEYWORD_EXTRACT_LIMIT', 50)
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
        for i, kw in enumerate(keywords[:kw_limit]):
            tpl = diverse_templates[i % len(diverse_templates)]
            prompts.append({
                'prompt_text': tpl.format(kw=kw),
                'keyword': kw,
                'category': 'General',
                'priority': 'Medium'
            })
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
        1. A descriptive group title (as a TERM or PHRASE, NOT a question)
           - Use noun phrases like "Product Features", "Pricing Information", "User Guide"
           - Avoid questions like "What is...", "How to...", "Tell me about..."
           - Keep it short (2-4 words), descriptive, and category-like
        2. Primary prompts (1-3 most important prompts in the group)
        3. Secondary prompts (supporting prompts in the group)
        4. Group description explaining the common theme
        
        Group prompts that:
        - Share similar topics or themes
        - Target the same audience
        - Have complementary content
        - Can be used together in a content strategy
        
        Ensure each group has at least 1 primary prompt.
        IMPORTANT: Group titles must be TERMS or PHRASES, never questions.
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
        IMPORTANT: Group titles must be TERMS or PHRASES (like "Product Features", "User Guide"), 
        NOT questions. Provide a group title, primary prompts, secondary prompts, and description for each group.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
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
        Ensure a group title is term-based (not a question)
        Converts questions to terms/phrases
        """
        if not title:
            return 'General Topics'
        
        title_clean = title.strip()
        
        # Remove question marks
        if title_clean.endswith('?'):
            title_clean = title_clean[:-1].strip()
        
        # Check if it starts with question words and convert to term
        question_starters = ['What is', 'How to', 'Tell me', 'Explain', 'What are', 'Why is', 'When to', 'Where to', 'How does', 'What do']
        for starter in question_starters:
            if title_clean.startswith(starter):
                # Extract the main term after the question starter
                remaining = title_clean[len(starter):].strip()
                if remaining:
                    # Capitalize and add context to make it a term
                    remaining = remaining.strip('?').strip()
                    if remaining:
                        # Convert to term format
                        return remaining.title() + ' Information'
                # If nothing after question starter, use generic term
                return 'General Topics'
        
        # If it's already a term/phrase (no question words), return as-is
        # But ensure it's capitalized properly
        if title_clean:
            # Capitalize first letter of each word
            words = title_clean.split()
            if len(words) <= 4:  # Keep it short (2-4 words)
                return ' '.join(word.capitalize() for word in words)
            else:
                # If too long, truncate and add context
                return ' '.join(word.capitalize() for word in words[:3]) + ' Topics'
        
        return 'General Topics'
    
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
        Convert a category name to a term-based group title (not a question)
        Examples:
        - "General" -> "General Topics"
        - "Product" -> "Product Information"
        - "Features" -> "Product Features"
        """
        # Common category to term mappings
        category_terms = {
            'General': 'General Topics',
            'Product': 'Product Information',
            'Features': 'Product Features',
            'Pricing': 'Pricing Information',
            'Support': 'Support Resources',
            'Guide': 'User Guide',
            'Comparison': 'Product Comparison',
            'Benefits': 'Product Benefits',
            'Use Cases': 'Use Cases',
            'Technical': 'Technical Details'
        }
        
        # If exact match, use it
        if category in category_terms:
            return category_terms[category]
        
        # If category ends with common question words, remove them
        category_clean = category.strip()
        question_starters = ['What is', 'How to', 'Tell me', 'Explain', 'What are', 'Why is', 'When to', 'Where to']
        for starter in question_starters:
            if category_clean.startswith(starter):
                # Extract the main term after the question starter
                remaining = category_clean[len(starter):].strip()
                if remaining:
                    # Capitalize and add context
                    return remaining.title() + ' Information'
        
        # Default: add "Information" or "Topics" to make it a term
        if category_clean:
            # If it's already a noun phrase, use it as-is
            if len(category_clean.split()) <= 3 and not category_clean.endswith('?'):
                return category_clean
            # Otherwise, create a simple term
            return category_clean + ' Topics'
        
        return 'General Topics'
