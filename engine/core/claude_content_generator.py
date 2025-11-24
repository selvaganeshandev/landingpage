"""
Claude API Content Generator
This module handles content generation using the Claude API
"""

import os
import time
from anthropic import Anthropic
from django.conf import settings
from decouple import config


class ClaudeContentGenerator:
    """
    Claude content generator for creating SEO-optimized articles
    """

    def __init__(self):
        api_key = config('CLAUDE_API_KEY', default=None)
        if not api_key:
            raise ValueError("CLAUDE_API_KEY not found in environment variables")
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-5-20250929"

    def generate_content(self, params):
        """
        Generate content based on provided parameters

        Args:
            params (dict): Generation parameters including:
                - title (str): Article title
                - keywords (str): Target keywords
                - article_type (str): Type of article
                - tone (str): Tone of content
                - style (str): Writing style
                - goal (str): Content goal
                - audience (str): Target audience
                - depth (str): Content depth
                - word_count (int): Target word count
                - source_reference (str): Optional source context

        Returns:
            dict: Generated content with metadata
        """
        start_time = time.time()

        # Build the system and user prompts
        system_prompt, user_prompt = self._build_prompts(params)

        # Call Claude API
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            )

            # Extract content from response
            content_html = response.content[0].text

            # Calculate generation time
            generation_time = time.time() - start_time

            # Calculate actual word count
            actual_word_count = len(content_html.split())

            return {
                'content_html': content_html,
                'generation_time_seconds': round(generation_time, 2),
                'prompt_tokens': response.usage.input_tokens,
                'completion_tokens': response.usage.output_tokens,
                'actual_word_count': actual_word_count,
                'model_used': self.model
            }

        except Exception as e:
            raise Exception(f"Claude API error: {str(e)}")

    def _build_prompts(self, params):
        """
        Build the system and user prompts based on parameters
        Returns: (system_prompt, user_prompt)
        """
        title = params.get('title', '')
        keywords = params.get('keywords', '')
        article_type = params.get('article_type', 'blog')
        tone = params.get('tone', 'professional')
        style = params.get('style', 'informative')
        goal = params.get('goal', 'educate')
        audience = params.get('audience', 'general')
        depth = params.get('depth', 'comprehensive')
        word_count = params.get('word_count', 1500)
        source_reference = params.get('source_reference', '')

        # Build system prompt for SEO optimization
        system_prompt = """You are an expert SEO content writer. Create content that:
- Naturally incorporates target keywords without keyword stuffing
- Uses proper HTML formatting with semantic tags (h2, h3, p, ul, ol, strong, em)
- Includes engaging headings and subheadings (use h2 for main sections, h3 for subsections)
- Optimizes for featured snippets where applicable
- Maintains readability score suitable for web content
- Creates comprehensive, well-researched content that provides real value
- Ensures content is factually accurate and up-to-date
- Optimizes for both search engines and AI model responses
- Includes actionable insights and practical takeaways
- Uses short paragraphs (2-3 sentences) for better readability
- Adds bullet points or numbered lists where appropriate
- Returns ONLY the HTML content (no markdown, no code blocks)"""

        # Map article types to descriptions
        article_type_descriptions = {
            'blog': 'a well-structured blog post with engaging introduction, main body sections, and conclusion',
            'guide': 'a detailed how-to guide with step-by-step instructions and practical examples',
            'comparison': 'a comparison article analyzing multiple options side-by-side with pros and cons',
            'listicle': 'a list-based article with numbered or bulleted items, each with explanations',
            'technical': 'a technical article with in-depth analysis, technical details, and code examples where relevant'
        }

        article_description = article_type_descriptions.get(article_type, article_type_descriptions['blog'])

        # Build user prompt with specific requirements
        user_prompt = f"""Write {article_description} with the following specifications:

**Title:** {title}

**Target Keywords:** {keywords}

**Content Specifications:**
- Tone: {tone}
- Style: {style}
- Goal: {goal}
- Target Audience: {audience}
- Content Depth: {depth}
- Target Word Count: ~{word_count} words
"""

        if source_reference:
            user_prompt += f"""
**Context/Source:**
{source_reference}
"""

        user_prompt += """
**Structure Guidelines:**
"""

        if article_type == 'guide':
            user_prompt += """- Introduction: Hook + Problem statement + What readers will learn
- Prerequisites (if applicable)
- Step-by-step instructions with clear headings
- Tips and best practices
- Common mistakes to avoid
- Conclusion with next steps
"""
        elif article_type == 'comparison':
            user_prompt += """- Introduction: Context + What's being compared
- Comparison criteria/factors
- Detailed comparison of each option
- Pros and cons for each
- Use cases and recommendations
- Final verdict/conclusion
"""
        elif article_type == 'listicle':
            user_prompt += """- Engaging introduction explaining the list
- Each list item with a descriptive heading
- Detailed explanation for each item
- Examples or use cases
- Conclusion summarizing key points
"""
        elif article_type == 'technical':
            user_prompt += """- Introduction: Problem/concept overview
- Technical background
- Detailed explanation with examples
- Implementation details (if applicable)
- Best practices and considerations
- Performance/security considerations
- Conclusion and further resources
"""
        else:  # blog
            user_prompt += """- Compelling introduction with a hook
- 3-5 main body sections with h2 headings
- Supporting subsections with h3 headings as needed
- Conclusion with key takeaways
"""

        user_prompt += """
Begin writing the article now. Return ONLY the HTML content."""

        return system_prompt, user_prompt

    def regenerate_section(self, original_content, section_to_improve, improvement_instructions):
        """
        Regenerate a specific section of content

        Args:
            original_content (str): The original HTML content
            section_to_improve (str): The section heading or description
            improvement_instructions (str): Specific instructions for improvement

        Returns:
            str: The regenerated section content
        """
        system_prompt = """You are an expert SEO content editor. When regenerating content sections:
- Maintain the same tone and style as the original article
- Use proper HTML formatting with semantic tags
- Improve clarity and readability
- Ensure SEO optimization
- Keep content factually accurate
- Return ONLY the HTML content (no markdown, no code blocks)"""

        user_prompt = f"""Below is the original article content:

{original_content}

Please regenerate the following section:
**Section:** {section_to_improve}

**Improvement Instructions:** {improvement_instructions}

Return ONLY the regenerated HTML content for this specific section."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            )

            return response.content[0].text

        except Exception as e:
            raise Exception(f"Claude API error during regeneration: {str(e)}")
