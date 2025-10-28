from typing import List, Dict, Any
import random
from django.conf import settings


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
            return
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key, timeout=60)
        except Exception as e:
            # Defer to local generation if client cannot be created
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
            return self._local_generate_prompts(keywords, domain_name)

        # Create a system prompt for generating prompts
        system_prompt = f"""
        You are an expert content strategist and SEO specialist. Your task is to generate high-quality, 
        engaging prompts based on keywords for the domain "{domain_name}".
        
        For each keyword, create a comprehensive prompt that:
        1. Incorporates the keyword naturally
        2. Asks for detailed, actionable information
        3. Encourages comprehensive responses
        4. Is relevant to the domain's industry/niche
        5. Follows best practices for AI prompt engineering
        
        Return the prompts in a structured format with:
        - prompt_text: The actual prompt
        - keyword: The original keyword it's based on
        - category: A relevant category for grouping
        - priority: High, Medium, or Low based on keyword importance
        
        Generate at least 10 distinct prompts overall (quality over quantity), and avoid
        repeating the same keyword across prompts unless necessary.
        """
        
        # Prepare the user message with keywords
        # Use up to KEYWORD_EXTRACT_LIMIT keywords to ensure diversity
        kw_limit = getattr(settings, 'KEYWORD_EXTRACT_LIMIT', 50)
        keywords_text = ", ".join(keywords[:kw_limit])
        user_message = f"""
        Generate prompts for these keywords related to {domain_name}:
        
        Keywords: {keywords_text}
        
        Please provide comprehensive, engaging prompts that would generate valuable content 
        when used with AI tools like ChatGPT. Focus on creating prompts that encourage 
        detailed, informative responses.
        """
        
        try:
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
            content = response.choices[0].message.content
            return self._parse_prompts_response(content, keywords)
            
        except Exception as e:
            print(f"Error generating prompts with ChatGPT, using local generation: {str(e)}")
            return self._local_generate_prompts(keywords, domain_name)
    
    def _parse_prompts_response(self, content: str, original_keywords: List[str]) -> List[Dict[str, Any]]:
        """
        Parse the ChatGPT response to extract structured prompts
        """
        prompts = []
        
        # Simple parsing - in a real implementation, you might want more sophisticated parsing
        lines = content.split('\n')
        current_prompt = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('**Prompt:**') or line.startswith('Prompt:'):
                if current_prompt:
                    prompts.append(current_prompt)
                current_prompt = {
                    'prompt_text': line.replace('**Prompt:**', '').replace('Prompt:', '').strip(),
                    'keyword': '',
                    'category': 'General',
                    'priority': 'Medium'
                }
            elif line.startswith('**Keyword:**') or line.startswith('Keyword:'):
                current_prompt['keyword'] = line.replace('**Keyword:**', '').replace('Keyword:', '').strip()
            elif line.startswith('**Category:**') or line.startswith('Category:'):
                current_prompt['category'] = line.replace('**Category:**', '').replace('Category:', '').strip()
            elif line.startswith('**Priority:**') or line.startswith('Priority:'):
                current_prompt['priority'] = line.replace('**Priority:**', '').replace('Priority:', '').strip()
        
        # Add the last prompt if exists
        if current_prompt:
            prompts.append(current_prompt)
        
        # If no structured prompts found, create simple prompts from keywords
        if not prompts:
            kw_limit = getattr(settings, 'KEYWORD_EXTRACT_LIMIT', 50)
            diverse_templates = [
                "What are the top 5 things to know about {kw}?",
                "Explain {kw} for beginners with practical examples.",
                "Compare popular options related to {kw} and when to use each.",
                "What are common mistakes with {kw} and how to avoid them?",
                "Give a step-by-step guide to get started with {kw}.",
                "What are the latest trends and tools around {kw}?",
                "List best practices for succeeding with {kw}.",
                "How does {kw} differ across use cases and industries?",
                "What metrics matter when evaluating {kw}?",
                "Suggest alternatives to {kw} and trade-offs."
            ]
            for i, keyword in enumerate(original_keywords[:kw_limit]):
                tpl = diverse_templates[i % len(diverse_templates)]
                prompts.append({
                    'prompt_text': tpl.format(kw=keyword),
                    'keyword': keyword,
                    'category': 'General',
                    'priority': 'Medium'
                })
        
        return prompts

    def _local_generate_prompts(self, keywords: List[str], domain_name: str) -> List[Dict[str, Any]]:
        # Deterministic, diverse, domain-agnostic prompts using up to KEYWORD_EXTRACT_LIMIT keywords
        prompts: List[Dict[str, Any]] = []
        kw_limit = getattr(settings, 'KEYWORD_EXTRACT_LIMIT', 50)
        diverse_templates = [
            "What is {kw} and why does it matter?",
            "Create a beginner-friendly guide to {kw} with examples.",
            "What tools, platforms, or frameworks are best for {kw}?",
            "Compare the leading approaches to {kw} and their pros/cons.",
            "Outline a step-by-step plan to implement {kw} effectively.",
            "What are common pitfalls in {kw} and mitigation strategies?",
            "List advanced tips and best practices for {kw}.",
            "Provide a checklist to evaluate success with {kw}.",
            "Summarize recent developments and trends in {kw}.",
            "Suggest practical alternatives to {kw} and when to choose them."
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
        
        # Create a system prompt for grouping
        system_prompt = """
        You are an expert in natural language processing and content organization. 
        Your task is to group related prompts into logical sets based on their content, 
        keywords, and themes.
        
        For each group, provide:
        1. A descriptive group title
        2. Primary prompts (1-3 most important prompts in the group)
        3. Secondary prompts (supporting prompts in the group)
        4. Group description explaining the common theme
        
        Group prompts that:
        - Share similar topics or themes
        - Target the same audience
        - Have complementary content
        - Can be used together in a content strategy
        
        Ensure each group has at least 1 primary prompt.
        """
        
        # Prepare the user message with prompts
        prompts_text = "\n".join([
            f"{i+1}. {prompt['prompt_text']} (Keyword: {prompt.get('keyword', 'N/A')})"
            for i, prompt in enumerate(prompts)
        ])
        
        user_message = f"""
        Group these prompts into logical sets:
        
        {prompts_text}
        
        Please organize them into groups with clear themes and provide a group title, 
        primary prompts, secondary prompts, and description for each group.
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
            print(f"Error grouping prompts with ChatGPT: {str(e)}")
            # Fallback: create simple groups
            return self._create_fallback_groups(prompts)
    
    def _parse_grouped_prompts(self, content: str, original_prompts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse the grouped prompts response
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
                    groups.append(current_group)
                current_group = {
                    'title': line,
                    'description': '',
                    'primary_prompts': [],
                    'secondary_prompts': []
                }
            elif line.startswith('**Title:**') or line.startswith('Title:'):
                current_group['title'] = line.replace('**Title:**', '').replace('Title:', '').strip()
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
            groups.append(current_group)
        
        # If no groups found, create fallback groups
        if not groups:
            return self._create_fallback_groups(original_prompts)
        
        return groups
    
    def _create_fallback_groups(self, prompts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Create fallback groups when ChatGPT grouping fails
        """
        if not prompts:
            return []
        
        # Simple grouping by category
        groups = {}
        for prompt in prompts:
            category = prompt.get('category', 'General')
            if category not in groups:
                groups[category] = {
                    'title': f"{category} Prompts",
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
