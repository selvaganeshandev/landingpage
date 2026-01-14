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
        target_country = params.get('target_country', 'united_states')
        target_language = params.get('target_language', 'us_english')
        references = params.get('references', [])
        tone = params.get('tone', 'professional')
        style = params.get('style', 'informative')
        goal = params.get('goal', 'educate')
        audience = params.get('audience', 'general')
        depth = params.get('depth', 'comprehensive')
        word_count = params.get('word_count', 1500)
        source_reference = params.get('source_reference', '')
        # Domain content guidelines
        key_messages = params.get('key_messages', '')
        topics_to_avoid = params.get('topics_to_avoid', '')
        brand_values = params.get('brand_values', '')

        # Format country and language for display
        country_display = target_country.replace('_', ' ').title()
        language_display = target_language.replace('_', ' ').title()

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
            # Article Types
            'blog': 'a well-structured blog post with engaging introduction, main body sections, and conclusion',
            'guide': 'a detailed how-to guide with step-by-step instructions and practical examples',
            'comparison': 'a comparison article analyzing multiple options side-by-side with pros and cons',
            'listicle': 'a list-based article with numbered or bulleted items, each with explanations',
            'technical': 'a technical article with in-depth analysis, technical details, and code examples where relevant',
            # Web Page Content Types
            'landing_page': 'a high-converting landing page with compelling headlines, benefit-focused copy, and clear calls-to-action',
            'services_page': 'a professional services page describing offerings, benefits, and expertise',
            'product_page': 'a persuasive product page with features, specifications, benefits, and compelling product descriptions',
            'features_page': 'a detailed features page showcasing product/service capabilities with clear explanations',
            'resource_page': 'a lead-generating resource page promoting downloadable content with value propositions'
        }

        article_description = article_type_descriptions.get(article_type, article_type_descriptions['blog'])

        # Build user prompt with specific requirements
        user_prompt = f"""Write {article_description} with the following specifications:

**Title:** {title}

**Target Keywords:** {keywords}

**Target Market:**
- Country: {country_display}
- Language: {language_display}

**Content Specifications:**
- Tone: {tone}
- Style: {style}
- Goal: {goal}
- Target Audience: {audience}
- Content Depth: {depth}
- Target Word Count: ~{word_count} words

**IMPORTANT - Language & Spelling:** Write the entire content in {language_display}.
- Use spelling, grammar, and vocabulary conventions specific to {language_display}
- US English: color, favor, organize, center, traveled
- UK English: colour, favour, organise, centre, travelled
- Australian/NZ English: Follow UK spelling with local terminology
- Canadian English: Mix of US/UK (color but centre, organize but travelled)
- Use cultural references, idioms, and terminology appropriate for the {country_display} market
"""

        if source_reference:
            user_prompt += f"""
**Context/Source:**
{source_reference}
"""

        # Add brand guidelines if provided
        has_brand_guidelines = key_messages or topics_to_avoid or brand_values
        if has_brand_guidelines:
            user_prompt += """
**Brand Guidelines:**
"""
            if key_messages:
                user_prompt += f"""- Key Messages to Incorporate: {key_messages}
"""
            if brand_values:
                user_prompt += f"""- Brand Values to Reflect: {brand_values}
"""
            if topics_to_avoid:
                user_prompt += f"""- Topics/Themes to AVOID: {topics_to_avoid}
"""

        # Add references if provided
        if references and len(references) > 0:
            user_prompt += """
**Reference Materials:**
Use the following reference materials to inform and enhance your content. Extract relevant information, statistics, and insights from these sources:
"""
            for i, ref in enumerate(references, 1):
                ref_type = ref.get('type', 'article').capitalize()
                ref_url = ref.get('url', '')
                ref_desc = ref.get('description', '')
                user_prompt += f"\n{i}. [{ref_type}] {ref_url}"
                if ref_desc:
                    user_prompt += f"\n   Description: {ref_desc}"
            user_prompt += """

When using these references:
- Extract key facts, statistics, and insights
- Cite or reference the source material where appropriate
- Synthesize information from multiple sources
- Do NOT simply copy content - create original content informed by these references
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
        elif article_type == 'landing_page':
            user_prompt += """- Hero section: Compelling headline + subheadline + value proposition
- Problem statement: What pain points does your solution address
- Benefits section: Key benefits with icons/visual descriptions
- Features overview: Main features with brief explanations
- Social proof: Testimonials, logos, or trust indicators section
- Call-to-action section: Clear CTA with urgency
- FAQ section (optional): Address common objections
"""
        elif article_type == 'services_page':
            user_prompt += """- Hero section: Service name + brief description
- Overview: What the service is and who it's for
- Service details: Detailed breakdown of what's included
- Benefits: Why choose this service
- Process: How it works (step-by-step)
- Pricing or packages (if applicable)
- Call-to-action: Next steps to get started
"""
        elif article_type == 'product_page':
            user_prompt += """- Product title and tagline
- Product overview: Brief description and main value
- Key features: Detailed feature list with benefits
- Specifications: Technical specs in a structured format
- Use cases: Who should use this and why
- Comparison section (vs alternatives)
- Call-to-action: Purchase/demo button section
"""
        elif article_type == 'features_page':
            user_prompt += """- Headline: Communicate the overall value
- Feature categories with h2 headings
- Each feature with: Name, description, benefit
- Visual descriptions for feature icons/illustrations
- Use cases for key features
- Comparison with competitors (optional)
- Call-to-action to get started
"""
        elif article_type == 'resource_page':
            user_prompt += """- Attention-grabbing headline
- Resource overview: What it is and what readers will learn
- Key takeaways: Bullet points of main insights
- Who it's for: Target audience description
- Preview section: Sneak peek of content
- Social proof: Downloads count, testimonials
- Lead capture section: Form description with CTA
"""
        else:  # blog (default)
            user_prompt += """- Compelling introduction with a hook
- 3-5 main body sections with h2 headings
- Supporting subsections with h3 headings as needed
- Conclusion with key takeaways
"""

        user_prompt += """
Begin writing the content now. Return ONLY the HTML content."""

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

    def generate_outline(self, params):
        """
        Generate a content outline based on provided parameters

        Args:
            params (dict): Generation parameters (same as generate_content)

        Returns:
            dict: Generated outline with sections
        """
        import json
        start_time = time.time()

        title = params.get('title', '')
        keywords = params.get('keywords', '')
        article_type = params.get('article_type', 'blog')
        target_country = params.get('target_country', 'united_states')
        target_language = params.get('target_language', 'us_english')
        tone = params.get('tone', 'professional')
        style = params.get('style', 'informative')
        audience = params.get('audience', 'general')
        word_count = params.get('word_count', 1500)
        key_messages = params.get('key_messages', '')
        topics_to_avoid = params.get('topics_to_avoid', '')

        # Format for display
        country_display = target_country.replace('_', ' ').title()
        language_display = target_language.replace('_', ' ').title()

        # Map article types to descriptions
        article_type_descriptions = {
            'blog': 'blog post',
            'guide': 'how-to guide',
            'comparison': 'comparison article',
            'listicle': 'listicle',
            'technical': 'technical article',
            'landing_page': 'landing page',
            'services_page': 'services page',
            'product_page': 'product page',
            'features_page': 'features page',
            'resource_page': 'resource/guide page'
        }
        article_description = article_type_descriptions.get(article_type, 'blog post')

        system_prompt = """You are an expert content strategist. Create detailed content outlines that:
- Structure content logically for maximum engagement and SEO
- Include compelling section headings
- Provide key points to cover in each section
- Estimate word count per section
- Return the outline as a valid JSON array

IMPORTANT: Return ONLY valid JSON, no markdown code blocks, no extra text."""

        user_prompt = f"""Create a detailed outline for a {article_description} with these specifications:

**Title:** {title}
**Target Keywords:** {keywords}
**Target Market:** {country_display} ({language_display})
**Tone:** {tone}
**Style:** {style}
**Target Audience:** {audience}
**Target Word Count:** ~{word_count} words
"""

        if key_messages:
            user_prompt += f"""
**Key Messages to Include:** {key_messages}
"""

        if topics_to_avoid:
            user_prompt += f"""
**Topics to Avoid:** {topics_to_avoid}
"""

        user_prompt += f"""
Return a JSON array with this exact structure:
[
  {{
    "id": "1",
    "type": "h2",
    "title": "Section Heading",
    "key_points": ["Point 1", "Point 2", "Point 3"],
    "estimated_words": 200
  }},
  {{
    "id": "1.1",
    "type": "h3",
    "title": "Subsection Heading",
    "key_points": ["Point 1", "Point 2"],
    "estimated_words": 150
  }}
]

Guidelines:
- Include 4-6 main sections (h2) for a {word_count}-word article
- Add subsections (h3) where appropriate
- Each section should have 2-4 key points
- Distribute the {word_count} words across sections appropriately
- Use descriptive, engaging headings that incorporate keywords naturally
- Structure should flow logically from introduction to conclusion

Return ONLY the JSON array, nothing else."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            )

            outline_text = response.content[0].text.strip()

            # Clean up the response if it has markdown code blocks
            if outline_text.startswith('```'):
                outline_text = outline_text.split('```')[1]
                if outline_text.startswith('json'):
                    outline_text = outline_text[4:]
                outline_text = outline_text.strip()

            # Parse the JSON
            outline_sections = json.loads(outline_text)

            generation_time = time.time() - start_time

            return {
                'outline': outline_sections,
                'generation_time_seconds': round(generation_time, 2),
                'prompt_tokens': response.usage.input_tokens,
                'completion_tokens': response.usage.output_tokens,
                'model_used': self.model
            }

        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse outline JSON: {str(e)}")
        except Exception as e:
            raise Exception(f"Claude API error during outline generation: {str(e)}")

    def generate_content_from_outline(self, params, outline):
        """
        Generate full content based on an approved outline

        Args:
            params (dict): Generation parameters
            outline (list): List of outline sections

        Returns:
            dict: Generated content with metadata
        """
        start_time = time.time()

        # Build the system prompt
        system_prompt = """You are an expert SEO content writer. Create content that:
- Follows the provided outline structure exactly
- Naturally incorporates target keywords without keyword stuffing
- Uses proper HTML formatting with semantic tags (h2, h3, p, ul, ol, strong, em)
- Maintains readability score suitable for web content
- Creates comprehensive, well-researched content that provides real value
- Uses short paragraphs (2-3 sentences) for better readability
- Returns ONLY the HTML content (no markdown, no code blocks)"""

        title = params.get('title', '')
        keywords = params.get('keywords', '')
        article_type = params.get('article_type', 'blog')
        target_language = params.get('target_language', 'us_english')
        tone = params.get('tone', 'professional')
        style = params.get('style', 'informative')
        audience = params.get('audience', 'general')
        key_messages = params.get('key_messages', '')
        topics_to_avoid = params.get('topics_to_avoid', '')
        brand_values = params.get('brand_values', '')

        language_display = target_language.replace('_', ' ').title()

        # Build outline text
        outline_text = ""
        for section in outline:
            section_type = section.get('type', 'h2')
            section_title = section.get('title', '')
            key_points = section.get('key_points', [])
            est_words = section.get('estimated_words', 150)

            indent = "  " if section_type == 'h3' else ""
            outline_text += f"\n{indent}{section_type.upper()}: {section_title} (~{est_words} words)\n"
            for point in key_points:
                outline_text += f"{indent}  - {point}\n"

        user_prompt = f"""Write content following this exact outline structure:

**Title:** {title}
**Keywords:** {keywords}
**Tone:** {tone}
**Style:** {style}
**Target Audience:** {audience}
**Language:** {language_display}

**OUTLINE TO FOLLOW:**
{outline_text}

"""

        if key_messages:
            user_prompt += f"""**Key Messages:** {key_messages}
"""

        if topics_to_avoid:
            user_prompt += f"""**Topics to Avoid:** {topics_to_avoid}
"""

        if brand_values:
            user_prompt += f"""**Brand Values:** {brand_values}
"""

        user_prompt += """
IMPORTANT:
- Follow the outline structure exactly (same headings, same order)
- Cover all key points mentioned for each section
- Match the estimated word count for each section
- Use h2 tags for main sections, h3 tags for subsections
- Return ONLY the HTML content, no markdown"""

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

            content_html = response.content[0].text
            generation_time = time.time() - start_time
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

