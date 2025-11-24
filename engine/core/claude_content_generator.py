"""
Claude API Content Generator
This module handles content generation using the Claude API
"""

import os
import time
from anthropic import Anthropic
from django.conf import settings


class ClaudeContentGenerator:
    """
    Claude content generator for creating SEO-optimized articles
    """

    def __init__(self):
        api_key = os.getenv('CLAUDE_API_KEY')
        if not api_key:
            raise ValueError("CLAUDE_API_KEY not found in environment variables")
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"

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

        # Build the content generation prompt
        prompt = self._build_prompt(params)

        # Call Claude API
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=8000,
                temperature=0.7,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
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

    def _build_prompt(self, params):
        """
        Build the content generation prompt based on parameters
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

        # Map article types to descriptions
        article_type_descriptions = {
            'blog': 'a well-structured blog post with engaging introduction, main body sections, and conclusion',
            'guide': 'a detailed how-to guide with step-by-step instructions and practical examples',
            'comparison': 'a comparison article analyzing multiple options side-by-side with pros and cons',
            'listicle': 'a list-based article with numbered or bulleted items, each with explanations',
            'technical': 'a technical article with in-depth analysis, technical details, and code examples where relevant'
        }

        article_description = article_type_descriptions.get(article_type, article_type_descriptions['blog'])

        prompt = f"""You are an expert SEO content writer specializing in creating high-quality, engaging content optimized for AI visibility.

Write {article_description} with the following specifications:

**Title:** {title}

**Target Keywords:** {keywords}
(Naturally integrate these keywords throughout the content)

**Content Specifications:**
- Tone: {tone}
- Style: {style}
- Goal: {goal}
- Target Audience: {audience}
- Content Depth: {depth}
- Target Word Count: ~{word_count} words

"""

        if source_reference:
            prompt += f"""**Context/Source:**
{source_reference}

"""

        prompt += """**Requirements:**
1. Create comprehensive, well-researched content that provides real value
2. Use proper HTML formatting with semantic tags (h2, h3, p, ul, ol, strong, em)
3. Include engaging headings and subheadings (use h2 for main sections, h3 for subsections)
4. Naturally integrate target keywords without keyword stuffing
5. Add relevant examples, statistics, or case studies where appropriate
6. Ensure content is factually accurate and up-to-date
7. Optimize for both search engines and AI model responses
8. Include actionable insights and practical takeaways
9. Use short paragraphs (2-3 sentences) for better readability
10. Add bullet points or numbered lists where appropriate

**Structure Guidelines:**
"""

        if article_type == 'guide':
            prompt += """- Introduction: Hook + Problem statement + What readers will learn
- Prerequisites (if applicable)
- Step-by-step instructions with clear headings
- Tips and best practices
- Common mistakes to avoid
- Conclusion with next steps
"""
        elif article_type == 'comparison':
            prompt += """- Introduction: Context + What's being compared
- Comparison criteria/factors
- Detailed comparison of each option
- Pros and cons for each
- Use cases and recommendations
- Final verdict/conclusion
"""
        elif article_type == 'listicle':
            prompt += """- Engaging introduction explaining the list
- Each list item with a descriptive heading
- Detailed explanation for each item
- Examples or use cases
- Conclusion summarizing key points
"""
        elif article_type == 'technical':
            prompt += """- Introduction: Problem/concept overview
- Technical background
- Detailed explanation with examples
- Implementation details (if applicable)
- Best practices and considerations
- Performance/security considerations
- Conclusion and further resources
"""
        else:  # blog
            prompt += """- Compelling introduction with a hook
- 3-5 main body sections with h2 headings
- Supporting subsections with h3 headings as needed
- Conclusion with key takeaways
"""

        prompt += """
**Output Format:**
Return ONLY the HTML content (no markdown, no code blocks). Start directly with the content using proper HTML tags.

Begin writing the article now:"""

        return prompt

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
        prompt = f"""You are editing an existing article. Below is the original content:

{original_content}

Please regenerate the following section:
**Section:** {section_to_improve}

**Improvement Instructions:** {improvement_instructions}

Maintain the same tone and style as the rest of the article, but improve this section based on the instructions above.

Return ONLY the regenerated HTML content for this specific section (no markdown, no code blocks):"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0.7,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            return response.content[0].text

        except Exception as e:
            raise Exception(f"Claude API error during regeneration: {str(e)}")
