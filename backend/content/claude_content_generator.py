"""
Claude API Content Generator
This module handles content generation using the Claude API
"""

import os
import re
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

    def match_reference_content(self, title, keywords, article_type, reference_docs):
        """
        Check if any reference repository documents contain content relevant
        to the given title and keywords. Returns matched excerpts or empty string.

        Args:
            title (str): Article title
            keywords (str): Target keywords (comma-separated)
            article_type (str): Type of article
            reference_docs (QuerySet): ReferenceDocument objects with extracted_text

        Returns:
            str: Relevant excerpts from matched documents, or empty string
        """
        import logging
        logger = logging.getLogger(__name__)

        # Build document text for the prompt
        docs_text = ""
        for doc in reference_docs:
            if not doc.extracted_text or not doc.extracted_text.strip():
                continue
            # Truncate each doc to 15,000 chars to stay within token limits
            text = doc.extracted_text[:15000]
            docs_text += f"\n{'=' * 50}\nDOCUMENT: {doc.file_name} (Type: {doc.file_type.upper()})\n{'=' * 50}\n{text}\n"

        if not docs_text.strip():
            return ''

        system_prompt = """You are a content research assistant. Your task is to analyze brand reference documents and find content that is relevant to a specific article topic.

INSTRUCTIONS:
1. Read each reference document carefully
2. For each document, check if it contains information relevant to the given article title and keywords
3. If relevant content is found, extract ONLY the relevant paragraphs/sections
4. Preserve exact brand names, product names, statistics, facts, and specific terminology
5. Keep total extracted content under 2000 words
6. Tag each excerpt with its source document name

OUTPUT FORMAT:
If relevant content is found:
---
[Source: {document_name}]
{extracted relevant paragraph or section}

[Source: {document_name}]
{extracted relevant paragraph or section}
---

If NO document contains relevant content:
NO_RELEVANT_CONTENT

IMPORTANT:
- Only extract content that is DIRECTLY useful for writing the given article
- Do NOT extract generic/unrelated sections even if they are interesting
- Do NOT summarize - preserve the original wording for brand accuracy
- Do NOT add your own commentary"""

        user_prompt = f"""I am about to write an article. Check if any of the brand's reference documents contain content relevant to this topic:

**Article Title:** {title}
**Target Keywords:** {keywords}
**Content Type:** {article_type}

Below are the brand's reference documents:
{docs_text}

Now extract ONLY the relevant portions. If nothing is relevant, return exactly: NO_RELEVANT_CONTENT"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                temperature=0.2,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )

            matched_content = response.content[0].text.strip()

            if 'NO_RELEVANT_CONTENT' in matched_content:
                logger.info("No relevant reference content found for this topic")
                return ''

            logger.info(f"Found relevant reference content ({len(matched_content)} chars)")
            return matched_content

        except Exception as e:
            logger.warning(f"Reference content matching failed (non-fatal): {str(e)}")
            return ''

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

    def generate_meta_tags(self, title, content_html, keywords=''):
        """
        Generate SEO meta_title and meta_description from generated content.
        Separate lightweight call that runs AFTER content generation.
        Gracefully returns empty strings on any failure.

        Args:
            title (str): The article title
            content_html (str): The generated HTML content
            keywords (str): Target keywords (comma-separated)

        Returns:
            dict: { 'meta_title': str, 'meta_description': str }
        """
        import json
        import logging
        logger = logging.getLogger(__name__)

        # Extract first ~500 words of plain text for context
        plain_text = re.sub(r'<[^>]+>', ' ', content_html)
        plain_text = re.sub(r'\s+', ' ', plain_text).strip()
        words = plain_text.split()
        content_excerpt = ' '.join(words[:500])

        system_prompt = (
            "You are an SEO specialist. Generate a meta title and meta description "
            "for the given content.\n\n"
            "Rules:\n"
            "- meta_title: Max 60 characters. Include the primary keyword. "
            "Make it compelling for search results.\n"
            "- meta_description: Max 160 characters. Summarize the content value "
            "proposition. Include a call-to-action or benefit.\n"
            "- Return ONLY valid JSON, no markdown, no code blocks.\n\n"
            'Return format: {"meta_title": "...", "meta_description": "..."}'
        )

        user_prompt = (
            f"Generate SEO meta tags for this content:\n\n"
            f"Title: {title}\n"
            f"Keywords: {keywords}\n\n"
            f"Content excerpt:\n{content_excerpt}\n\n"
            f"Return ONLY the JSON object."
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=256,
                temperature=0.3,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )

            result_text = response.content[0].text.strip()

            # Clean up potential markdown code blocks
            if result_text.startswith('```'):
                result_text = result_text.split('```')[1]
                if result_text.startswith('json'):
                    result_text = result_text[4:]
                result_text = result_text.strip()

            meta = json.loads(result_text)

            return {
                'meta_title': str(meta.get('meta_title', ''))[:200],
                'meta_description': str(meta.get('meta_description', ''))[:500],
            }

        except Exception as e:
            logger.warning(f"Meta tag generation failed (non-fatal): {str(e)}")
            return {
                'meta_title': '',
                'meta_description': '',
            }

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
        additional_instructions = params.get('additional_instructions', '')
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

        if additional_instructions:
            user_prompt += f"""
**Additional Instructions:**
{additional_instructions}
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

        # Add reference repository context if available
        reference_repository_context = params.get('reference_repository_context', '')
        if reference_repository_context:
            user_prompt += f"""
**Brand Reference Repository (Use as Source Material):**
The following content was extracted from the brand's internal reference documents
(brand guides, previous content, presentations, templates, data sheets).
This is verified brand-specific information.

USE THIS CONTENT TO:
- Use the exact brand terminology, product names, and service descriptions found here
- Incorporate specific facts, statistics, and data points from these references
- Match the brand's communication style demonstrated in these references
- Include relevant details that only someone with internal brand knowledge would know
- Ensure consistency with existing brand content

DO NOT:
- Copy paragraphs verbatim - rephrase and integrate naturally
- Force irrelevant reference content into the article
- Contradict any facts stated in these references

Reference Content:
--- START REFERENCE CONTENT ---
{reference_repository_context}
--- END REFERENCE CONTENT ---
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
        additional_instructions = params.get('additional_instructions', '')

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

        if additional_instructions:
            user_prompt += f"""
**Additional Instructions:** {additional_instructions}
"""

        # Add reference repository context if available
        reference_repository_context = params.get('reference_repository_context', '')
        if reference_repository_context:
            user_prompt += f"""
**Brand Reference Repository (Plan Outline Using This):**
The following content was extracted from the brand's internal reference documents.
Use it to plan the outline structure:

- Create sections that cover topics/themes mentioned in these references
- Use the brand's specific terminology and product names in section headings
- Include key points based on facts and details found in these references
- Ensure the outline structure can accommodate insights from this material

Reference Content:
--- START REFERENCE CONTENT ---
{reference_repository_context}
--- END REFERENCE CONTENT ---
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
        additional_instructions = params.get('additional_instructions', '')
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

        if additional_instructions:
            user_prompt += f"""**Additional Instructions:** {additional_instructions}
"""

        # Add reference repository context if available
        reference_repository_context = params.get('reference_repository_context', '')
        if reference_repository_context:
            user_prompt += f"""
**Brand Reference Repository (Use as Source Material):**
The following content was extracted from the brand's internal reference documents.
Incorporate relevant details from this material into the appropriate outline sections:

- Use exact brand terminology, product names, and service descriptions
- Include specific facts, statistics, and data points where they fit each section
- Match the brand's tone and style demonstrated in these references
- Do NOT copy verbatim - rephrase and integrate naturally into each section

Reference Content:
--- START REFERENCE CONTENT ---
{reference_repository_context}
--- END REFERENCE CONTENT ---
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

    def rewrite_text(self, original_text, prompt, max_retries=3):
        """
        Rewrite a portion of text based on user instructions

        Args:
            original_text (str): The text to rewrite
            prompt (str): Instructions for how to rewrite the text
            max_retries (int): Maximum number of retries for transient errors

        Returns:
            str: The rewritten text
        """
        system_prompt = """You are a skilled editor and content writer. Your task is to rewrite the provided text according to the user's instructions.

Guidelines:
- Maintain the core meaning and information unless explicitly asked to change it
- Match the approximate length of the original text unless asked to make it longer or shorter
- Return ONLY the rewritten text, no explanations or comments
- Do not add any HTML tags unless the original text contains them
- Preserve any formatting style from the original text"""

        user_prompt = f"""Please rewrite the following text according to these instructions:

Instructions: {prompt}

Original text:
{original_text}

Rewritten text:"""

        last_error = None
        for attempt in range(max_retries):
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

                rewritten_text = response.content[0].text.strip()
                return rewritten_text

            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                # Retry on overloaded or rate limit errors
                if 'overloaded' in error_str or '529' in error_str or 'rate' in error_str:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 2  # 2, 4, 6 seconds
                        time.sleep(wait_time)
                        continue
                # For other errors, raise immediately
                raise Exception(f"Claude API error during rewrite: {str(e)}")

        raise Exception(f"Claude API error during rewrite after {max_retries} retries: {str(last_error)}")

    def humanise_content(self, content_html, max_retries=3):
        """
        Apply humanisation rules to the full content HTML in a single API call.

        Args:
            content_html (str): The full HTML content to humanise
            max_retries (int): Maximum number of retries for transient errors

        Returns:
            str: The humanised HTML content
        """
        system_prompt = """You are an expert content editor specialising in making AI-generated content read naturally human-written. Apply ALL of the following rules to the provided HTML content in a single pass:

TRANSFORMATION RULES:
1. Replace ALL em-dashes (—) and en-dashes (–) with commas, semicolons, or full stops. Search the entire output for any dash character (— or –) and replace it. For example: "a few minutes—perfect for gaming" → "a few minutes. Perfect for gaming".
2. STRICT SENTENCE LENGTH PATTERN: Follow this alternating rhythm throughout the ENTIRE content — short, short, short, long, short, short, long, short, short, short, long. Where "short" = exactly 8–10 words and "long" = exactly 15–25 words. This creates a roughly 70/30 ratio. FORBIDDEN: sentences of 11–14 words (the "gap zone") and sentences under 7 words or over 25 words. If you write a sentence of 11–14 words, you MUST rewrite it: either cut words to reach 8–10, or add detail to reach 15–25. Count the words in every sentence you write.
3. Make the tone conversational, personalised, and non-preachy.
4. Distribute anchor text and keywords evenly across all sections (not cluttered in one place).
5. Replace straight quotes (" ') with curly quotes (\u201c \u201d \u2018 \u2019).
6. MANDATORY SECTION VARIATION — THIS IS THE MOST IMPORTANT STRUCTURAL RULE: If the content has similar subsections (e.g. 10 game reviews), you MUST assign paragraph counts BEFORE writing using this exact formula:
   - Sections 1, 5, 9: give exactly 2 paragraphs
   - Sections 2, 4, 7, 10: give exactly 3 paragraphs
   - Sections 3, 6, 8: give exactly 4 paragraphs
   This means for 10 game sections: 3 sections with 2 paragraphs, 4 sections with 3 paragraphs, 3 sections with 4 paragraphs. Do NOT give all sections the same number of paragraphs. If every section has 3 paragraphs, the output is REJECTED. To create a 2-paragraph section, merge the middle paragraph into the first or last. To create a 4-paragraph section, split one long paragraph into two shorter ones.
7. BANNED WORDS — scan the entire output and rewrite every sentence that contains any of these: "remain", "remains", "remaining", "especially", "particularly", "may", "can", "leverage", "comprehensive", "remarkably", "significantly", "furthermore", "moreover", "additionally", "utilize", "utilise". Replace with simpler alternatives (e.g. "leverage" → "use", "comprehensive" → "full/complete/detailed", "remarkably" → "unusually/notably", "can earn" → "earn", "may help" → "helps"). Also NEVER start any sentence with a gerund (-ing word). Scan every sentence opening: if it starts with "Setting", "Buying", "Converting", "Understanding", "Owning", "Mining", "Purchasing", "Connecting", "Trading", "Earning", "Staking", "Timing", "Playing", "Farming", "Building", "Creating", or ANY other -ing word, restructure it. Examples: "Setting up a wallet..." → "Your first step is a wallet setup..." / "Buying cryptocurrency..." → "You buy cryptocurrency..." / "Understanding gas fees..." → "Gas fees are..." / "Owning LAND..." → "LAND ownership..." / "Earning opportunities..." → "The earning opportunities..." / "Staking allows..." → "The staking mechanism allows..." / "Timing your transactions..." → "Time your transactions...".
8. Remove buzzwords (cutting-edge, innovative, advanced technology, leverage, game-changer, harness, empower, seamlessly, revolutionise) unless backed by specific data.
9. Remove clich\u00e9s ("In today\u2019s world", "Needless to say", "It\u2019s no secret that").
10. Remove rhetorical questions, generic connectors ("not just... but also..."). Never open or close a section with a question.
11. STRICT: One idea per sentence. NEVER use semicolons (;) anywhere in the content — replace every semicolon with a full stop and start a new sentence. Never combine two separate actions with "and" (e.g. "Download the app and create a password" → "Download the app. Create a password."). Never use colons (:) to introduce a list within a sentence — restructure as separate sentences instead.
12. Add natural human variation; slightly imperfect flow, varied pacing and rhythm.
13. Use bullet points only when they genuinely improve readability, not as term:definition structures.
14. STRICT 2-ITEM LIST RULE: Scan the ENTIRE content for every comma-separated series or list. Any series with 3 or more items MUST be reduced to exactly 2 items joined by "and" or "or". Drop the least important item(s). This applies to ALL patterns:
   - "collect, breed, and battle" → "collect and battle"
   - "trade, sell, or transfer" → "trade or sell"
   - "items, characters, or land parcels" → "items or characters"
   - "attributes, abilities, and visual characteristics" → "attributes and abilities"
   - "quests, win battles, or achieve milestones" → "complete quests or win battles"
   - "buy, breed, or craft" → "buy or craft"
   - "virtual land parcels, interactive experiences, art galleries, and social spaces" → "virtual land parcels and interactive experiences"
   - "Gold, Wood, and Food tokens" → "Gold and Wood tokens"
   - "time, skills, and strategic decisions" → "time and skills"
   - "card editions, splinters (factions), and regular expansions" → "card editions and regular expansions"
   - "events, concerts, and exhibitions" → "events and exhibitions"
   - "explore, capture creatures, and battle" → "explore and capture creatures"
   - "creating a wallet, downloading the app, and connecting" → "creating a wallet and downloading the app"
   - "stake TLM...use it...or exchange it" → pick only 2 of the 3 actions
   - "tournament victories, selling Illuvials, and trading resources" → "tournament victories and selling Illuvials"
   - "stake tokens, participate in farming, or play games" → "stake tokens or play games"
   This is a HARD RULE with zero exceptions. Three items in a row is an AI detection fingerprint. This also applies to sequential sentences that list 3+ options ("You do X. You do Y. You do Z." — reduce to 2). Scan every sentence for commas between nouns/verbs — if there are 3+ items, cut to 2.
15. MANDATORY FORWARD-GUIDING ENDINGS: Every section and subsection MUST end with a forward-looking statement that tells the reader what to do next, what to explore, or what comes next in their journey. Examples of good endings: "Start by exploring the free areas before deciding to invest." / "Head to the official website to create your first deck." / "Try the free mining tools first, then upgrade once you understand the mechanics." BAD endings (flat facts): "The mobile-first design ensures smooth performance." / "The platform's governance model gives you a voice." These are just statements — they do not guide the reader forward. Rewrite every section ending to include an action or next step.
16. STRICT NO-REPEAT RULE: No descriptive word (adjective/adverb) should appear more than ONCE in the entire content. After transforming, scan the full output and replace every duplicate descriptor with a synonym. Use each synonym only once too. Here are the top offenders with their one-time-use alternatives:
   - "multiple" (use ONE of: several, numerous, many, a handful of, a few, assorted — each only once)
   - "various" (use ONE of: a range of, mixed, assorted, different, varied — each only once)
   - "distinct" (use ONE of: unique, individual, one-of-a-kind, specific, particular — each only once)
   - "accessible" (use ONE of: approachable, open to, within reach, easy to enter, beginner-friendly — each only once)
   - "strategic" (use ONE of: tactical, calculated, planned, methodical — each only once)
   - "valuable" (use ONE of: prized, sought-after, worthwhile, lucrative — each only once)
   - "competitive" (use ONE of: intense, contested, head-to-head, fierce — each only once)
   - "powerful" (use ONE of: formidable, potent, robust, mighty — each only once)
   - "hefty" (use ONE of: sizeable, steep, large, considerable — each only once)
   - "ideal" (use ONE of: perfect, well-suited, fitting, apt — each only once)
   - "rare" (use ONE of: scarce, uncommon, hard-to-find, elusive — each only once)
   - "regular" (use ONE of: frequent, recurring, periodic, routine — each only once)
   - "transparent" (use ONE of: open, clear, visible, verifiable — each only once)
   - "genuine" (use ONE of: authentic, actual, verifiable, proven — each only once)
   - "immersive" (use ONE of: engaging, absorbing, captivating, vivid — each only once)
   - "different" (use ONE of: varied, assorted, distinct, separate, diverse — each only once)
   - "several" (use ONE of: a handful of, a few, numerous, many, some — each only once)
   - "official" (use ONE of: authorised, verified, authentic, legitimate — each only once)
   - "traditional" (use ONE of: conventional, classic, standard, established — each only once)
   - "popular" (use ONE of: well-known, widely used, favoured, common — each only once)
   - "simple" (use ONE of: elementary, basic, foundational, entry-level — each only once)
   - "dedicated" (use ONE of: committed, focused, loyal, devoted — each only once)
   - "considerable" (use ONE of: sizeable, notable, meaningful, significant — each only once)
   - "frequent" (use ONE of: recurring, periodic, routine, regular — each only once)
   - "one-of-a-kind" (use ONE of: unique, singular, individual, distinct — each only once. NEVER use "one-of-a-kind" more than once)
   - "approachable" (use ONE of: beginner-friendly, welcoming, easy to enter, open to newcomers — each only once)
   - "sizeable" (use ONE of: large, hefty, steep, substantial — each only once)
   - "limited" (use ONE of: restricted, capped, constrained, modest — each only once)
   - "initial" (use ONE of: starting, upfront, opening — each only once)
   - "competitive" (use ONE of: intense, fierce, contested, head-to-head — each only once)
   - "basic" (use ONE of: elementary, foundational, entry-level, introductory — each only once)
   NOTE: Technical domain terms are exempt from this rule (e.g. "virtual" for virtual worlds, "digital" for digital assets, "mobile" for mobile devices, "free" for free-to-play, "in-game", "blockchain", "NFT"). These are domain vocabulary and not descriptive repetition.
   NEVER CHANGE these words in these fixed phrases: "strong password", "real money", "real estate", "real-world", "real value", "mobile-first", "true ownership", "open rewards", "open world". These words have fixed meanings and are NOT descriptors.
   Remove generic phrasings like "XYZ is not just abc", "From abc to xyz".

CRITICAL CHECKS — After transforming, scan the full output line by line and fix ANY violations before returning:
□ Search for em-dashes (—) and en-dashes (–) — replace every one with a comma, semicolon, or full stop
□ No sentence starts with an -ing word (Setting, Buying, Converting, Understanding, Owning, Mining, Purchasing, Connecting, Trading, Earning, Staking, Timing, Playing, Farming, Building, Creating, etc.)
□ No comma-separated list has 3+ items anywhere — scan every comma between nouns/verbs and verify only 2 items exist. Also check sequential sentences listing 3+ options
□ None of the banned words from Rule 7 appear anywhere
□ Count the paragraph count of each similar section (e.g. game reviews) — they MUST have at least 3 different counts (e.g. some 2, some 3, some 4). If all sections have the same count, merge or split paragraphs to create variation
□ No word like "comprehensive", "remarkably", "leverage", "especially", "particularly" survived
□ No descriptive word appears more than once — search for these high-risk repeats: "multiple", "various", "distinct", "accessible", "strategic", "valuable", "competitive", "powerful", "hefty", "ideal", "rare", "regular", "transparent", "genuine", "immersive", "different", "several", "official", "traditional", "popular", "simple", "dedicated", "considerable", "frequent", "substantial", "straightforward", "unusually", "diverse", "unique". If ANY appears twice, replace the duplicate with a synonym from Rule 16
□ Every section/subsection ends with a forward-guiding statement (action, next step, what to try) — not a flat fact. Check the last sentence of EVERY section
□ Count words in a sample of 20 sentences — at least 60% must be 8–10 words, no more than 10% in the 11–14 gap zone. Rewrite any gap-zone sentences
□ Search for ALL semicolons (;) in the output — replace every one with a full stop. No semicolons allowed anywhere
□ No descriptive phrase appears verbatim twice (e.g. "limited earning potential", "one-of-a-kind NFT", "powerful teams"). If found, rewrite one instance
□ Count paragraph counts for all similar sections — verify at least 3 different counts exist (e.g. 2, 3, 4). If all are the same, restructure immediately

Additionally avoid these patterns:
- "XYZ is not just abc. It is jkl"
- "XYZ doesn\u2019t just blah blah. It does blah"
- "QUESTION? ANSWER." pattern
- "From abc to xyz, my brand is best"

PROTECTIVE RULES (MUST NOT violate):
17. Preserve ALL HTML structure exactly (headings h2-h5, tables, lists, images, divs, spans, blockquotes).
18. Preserve ALL hyperlinks (<a> tags) with their exact href attribute, anchor text, and all attributes (rel, target, etc.).
19. Preserve ALL keyword placements; do not remove or rephrase target keywords.

Return ONLY the transformed HTML content. Do not add any explanations, comments, or markdown code blocks."""

        user_prompt = f"""Apply all humanisation rules to the following HTML content. Return ONLY the transformed HTML:

{content_html}"""

        last_error = None
        for attempt in range(max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=8192,
                    temperature=0.7,
                    system=system_prompt,
                    messages=[
                        {
                            "role": "user",
                            "content": user_prompt
                        }
                    ]
                )

                humanised_content = response.content[0].text.strip()

                # Strip any accidental markdown code block wrapping
                if humanised_content.startswith('```'):
                    humanised_content = humanised_content.split('```')[1]
                    if humanised_content.startswith('html'):
                        humanised_content = humanised_content[4:]
                    humanised_content = humanised_content.strip()

                return humanised_content

            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                is_transient = (
                    'overloaded' in error_str or '529' in error_str
                    or 'rate' in error_str or 'connection' in error_str
                    or 'timeout' in error_str or 'name resolution' in error_str
                )
                if is_transient and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 3  # 3, 6, 9 seconds
                    time.sleep(wait_time)
                    continue
                raise Exception(f"Claude API error during humanisation: {str(e)}")

        raise Exception(f"Claude API error during humanisation after {max_retries} retries: {str(last_error)}")

    def refine_humanised_content(self, content_html, max_retries=3):
        """
        Pass 2: Focused refinement that fixes the 5 rules that consistently
        fail in the first humanisation pass.

        This method uses a short, laser-focused prompt with lower temperature
        to precisely fix: descriptor repeats, section paragraph variation,
        sentence length gaps, -ing sentence starts, and compound actions.

        Args:
            content_html (str): The humanised HTML from Pass 1
            max_retries (int): Maximum number of retries for transient errors

        Returns:
            str: The refined HTML content
        """
        system_prompt = """You are a precise content proofreader. The content has already been humanised. Your ONLY job is to fix these specific issues. Make minimal, surgical changes.

=== FIX 1: DESCRIPTOR REPEATS (MOST IMPORTANT) ===
PROCESS: Before returning, you MUST do a full-text search for EVERY word in this list. If ANY word appears more than once, replace the 2nd/3rd/4th occurrence with a DIFFERENT synonym each time.

CRITICAL RULE: Once you use a synonym as a replacement, that synonym is "spent" and CANNOT be used again anywhere. Keep a mental tally.

Example of WRONG approach: replacing "different planets", "different heroes", "different preferences" → "separate planets", "separate heroes", "separate preferences" (WRONG — you used "separate" three times!)

Example of CORRECT approach: "different planets" stays as "different", "different heroes" → "separate heroes", "different preferences" → "diverse preferences" (each word used exactly once)

MANDATORY SCAN LIST — check every one:
• "different" / "separate" / "assorted" / "varied" / "diverse" / "distinct" / "mixed" — if ANY of these appears 2+, replace extras
• "genuine" / "authentic" / "actual" / "verifiable" — if ANY appears 2+, replace extras
• "powerful" / "formidable" / "potent" / "robust" — if ANY appears 2+, replace extras
• "fitting" / "ideal" / "perfect" / "well-suited" / "suitable" / "apt" — if ANY appears 2+, replace extras
• "modest" / "limited" / "restricted" / "capped" / "constrained" — if ANY appears 2+, replace extras
• "substantial" / "sizeable" / "hefty" / "considerable" / "notable" — if ANY appears 2+, replace extras
• "specific" / "particular" / "precise" / "exact" / "defined" — if ANY appears 2+, replace extras
• "well-known" / "popular" / "favoured" / "established" / "recognised" — if ANY appears 2+, replace extras
• "frequent" / "recurring" / "periodic" / "routine" / "regular" — if ANY appears 2+, replace extras
• "unique" / "singular" / "one-of-a-kind" / "uncommon" / "individual" — if ANY appears 2+, replace extras
• "dedicated" / "committed" / "devoted" / "loyal" — if ANY appears 2+, replace extras
• "elementary" / "basic" / "foundational" / "entry-level" / "introductory" — if ANY appears 2+, replace extras
• "approachable" / "accessible" / "beginner-friendly" / "welcoming" / "inviting" — if ANY appears 2+, replace extras

Also scan for repeated DESCRIPTIVE PHRASES: "earning potential", "entry cost", "earning opportunities", etc. If any phrase appears 3+ times, rewrite some instances differently (e.g. "income prospects", "startup cost", "income avenues").

NEVER CHANGE these words/phrases (they have fixed meanings, not descriptors):
- "strong password" (security term), "real money" / "real estate" / "real-world" / "real value" (fixed phrases)
- "mobile-first" (tech term), "true ownership" (fixed phrase), "open rewards" / "open world" (fixed meanings)
- "first" when used as an adverb ("try X first", "explore first"), "simple mining" (specific mechanic)

EXEMPT: domain terms "virtual", "digital", "mobile", "free", "in-game", "blockchain", "NFT", "play to earn", "crypto", "gaming".

=== FIX 2: SECTION PARAGRAPH VARIATION (STRUCTURAL) ===
Count the paragraphs in each similar subsection (e.g. game reviews under a common parent heading). If they all have the same paragraph count, you MUST restructure.

REQUIRED FORMULA for 10 similar sections:
• Sections 1, 5, 9 → MERGE to exactly 2 paragraphs (combine the 2nd and 3rd paragraph into one)
• Sections 2, 4, 7, 10 → keep at exactly 3 paragraphs (no change if already 3)
• Sections 3, 6, 8 → SPLIT to exactly 4 paragraphs (find the longest paragraph and split it into two)

HOW TO MERGE (3→2 paragraphs): Take paragraphs 2 and 3, join their text into one paragraph. Keep paragraph 1 separate.
HOW TO SPLIT (3→4 paragraphs): Find the paragraph with the most sentences. Split it after the 2nd or 3rd sentence to create a new paragraph break.

This is a STRUCTURAL change. You MUST actually add or remove <p> tags / paragraph breaks to achieve the target counts. Do NOT skip this.

=== FIX 3: SENTENCE LENGTH ===
Scan for sentences of 11-14 words ("gap zone"). These are FORBIDDEN.
- If 11-14 words: CUT words to reach 8-10, OR add detail to reach 15-25.
- Also fix sentences under 7 words (merge with adjacent sentence) and over 25 words (split into two).

=== FIX 4: -ING SENTENCE STARTS ===
If any sentence starts with an -ing word (Earning, Setting, Buying, Mining, Trading, etc.), add "The" or restructure:
- "Earning opportunities..." → "The earning opportunities..."

=== FIX 5: FLAT SECTION ENDINGS ===
Check the LAST sentence of every section/subsection. If it states a fact without guiding the reader forward, rewrite it to include an action:
- BAD: "This makes it fitting for busy Indians." → GOOD: "Try the quick matches during your lunch break to test the earning potential."
- BAD: "The mobile-first design ensures smooth performance." → GOOD: "Download the app to experience the mobile-optimised gameplay yourself."

=== PROTECTIVE RULES ===
- Preserve ALL HTML structure (headings, tables, lists, images, divs, spans, blockquotes).
- Preserve ALL hyperlinks (<a> tags) with exact href, anchor text, and attributes.
- Preserve ALL keyword placements. Do not remove target keywords.
- Do NOT change meaning or tone. Only fix the issues above.

Return ONLY the fixed HTML. No explanations, no markdown code blocks."""

        user_prompt = f"""Review and fix ONLY the 5 specific issues described above in this HTML content. Make minimal changes. Return ONLY the fixed HTML:

{content_html}"""

        last_error = None
        for attempt in range(max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=8192,
                    temperature=0.1,
                    system=system_prompt,
                    messages=[
                        {
                            "role": "user",
                            "content": user_prompt
                        }
                    ]
                )

                refined_content = response.content[0].text.strip()

                # Strip any accidental markdown code block wrapping
                if refined_content.startswith('```'):
                    refined_content = refined_content.split('```')[1]
                    if refined_content.startswith('html'):
                        refined_content = refined_content[4:]
                    refined_content = refined_content.strip()

                return refined_content

            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                is_transient = (
                    'overloaded' in error_str or '529' in error_str
                    or 'rate' in error_str or 'connection' in error_str
                    or 'timeout' in error_str or 'name resolution' in error_str
                )
                if is_transient and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 3  # 3, 6, 9 seconds
                    time.sleep(wait_time)
                    continue
                raise Exception(f"Claude API error during refinement: {str(e)}")

        raise Exception(f"Claude API error during refinement after {max_retries} retries: {str(last_error)}")

    # ===== Synonym groups for descriptor deduplication =====
    # Each group contains ONLY words that are safe to interchange as descriptors.
    # Generic words (first, strong, real, small, open, big, right, true) are EXCLUDED
    # because they have non-descriptor meanings in fixed phrases.
    # No word appears in more than one group.
    SYNONYM_GROUPS = [
        ["different", "separate", "varied", "diverse", "distinct", "assorted",
         "mixed", "wide-ranging", "contrasting", "numerous"],
        ["genuine", "authentic", "actual", "verifiable", "proven"],
        ["powerful", "formidable", "potent", "robust", "mighty", "dominant"],
        ["fitting", "ideal", "perfect", "well-suited", "suitable", "apt"],
        ["modest", "limited", "restricted", "capped", "constrained", "moderate"],
        ["substantial", "sizeable", "hefty", "considerable", "notable", "meaningful"],
        ["specific", "precise", "particular", "exact", "defined", "targeted"],
        ["well-known", "popular", "favoured", "widely-used", "established", "recognised"],
        ["frequent", "recurring", "periodic", "routine", "regular", "ongoing", "repeated"],
        ["unique", "singular", "one-of-a-kind", "uncommon", "individual", "exclusive"],
        ["dedicated", "committed", "devoted", "loyal", "passionate"],
        ["elementary", "basic", "foundational", "entry-level", "introductory"],
        ["approachable", "accessible", "beginner-friendly", "welcoming", "inviting"],
        ["opening", "starting", "initial", "upfront"],
        ["large", "significant", "major", "steep", "extensive"],
        ["rare", "scarce", "elusive", "hard-to-find", "prized", "sought-after"],
        ["immersive", "engaging", "absorbing", "captivating", "vivid", "gripping"],
        ["competitive", "intense", "contested", "head-to-head", "fierce", "cutthroat"],
        ["strategic", "tactical", "calculated", "planned", "methodical"],
        ["valuable", "worthwhile", "lucrative", "rewarding", "profitable"],
        ["transparent", "clear", "visible", "traceable", "auditable"],
    ]

    # Protected phrases where a group word has a non-descriptor meaning.
    # The dedup will skip any match that is part of one of these phrases.
    PROTECTED_PHRASES = [
        # "strong" removed from groups entirely, but protect common collocations
        "strong password", "strong passwords",
        # "real" removed from groups entirely, but protect fixed phrases
        "real money", "real estate", "real-world", "real world", "real value",
        # "first" removed from groups entirely, but protect compound terms
        "mobile-first", "first step", "first account",
        # "open" removed from groups entirely, but protect fixed meanings
        "open rewards", "open world", "open-world", "open source", "open gaming",
        # "true" removed from groups entirely
        "true ownership",
        # "simple" removed from groups to avoid "simple mining" → wrong replacement
        "simple mining",
        # "small" removed from groups entirely
        "small amount",
        # "focused" removed from groups to avoid "focused prompt" → wrong replacement
        "focused prompt",
    ]

    def post_process_content(self, html_content):
        """
        Programmatic post-processing (Pass 3) that deterministically fixes
        issues the AI model inconsistently handles:
        1. Removes all em-dashes and en-dashes (Rule 1)
        2. Removes all semicolons (Rule 11)
        3. Restores protected phrases corrupted by AI (e.g. "formidable password" → "strong password")
        4. Deduplicates repeated descriptors (Rule 16)

        Args:
            html_content (str): The HTML content to post-process

        Returns:
            str: Content with deterministic fixes applied
        """
        # --- Step 1: Remove em-dashes and en-dashes ---
        # Replace "word—word" with "word. Word" (new sentence)
        # Handle cases like "ecosystem—you" → "ecosystem. You"
        html_content = re.sub(
            r'(\w)—(\w)',
            lambda m: m.group(1) + '. ' + m.group(2).upper(),
            html_content
        )
        html_content = re.sub(
            r'(\w)–(\w)',
            lambda m: m.group(1) + '. ' + m.group(2).upper(),
            html_content
        )
        # Handle spaced dashes: "word — word" or "word – word"
        html_content = re.sub(
            r'\s*—\s*',
            '. ',
            html_content
        )
        html_content = re.sub(
            r'\s*–\s*',
            '. ',
            html_content
        )

        # --- Step 2: Remove semicolons ---
        # Replace "; word" with ". Word" (new sentence)
        html_content = re.sub(
            r';\s*(\w)',
            lambda m: '. ' + m.group(1).upper(),
            html_content
        )

        # --- Step 3: Restore protected phrases corrupted by AI ---
        html_content = self._restore_protected_phrases(html_content)

        # --- Step 4: Deduplicate descriptors ---
        html_content = self._deduplicate_descriptors(html_content)

        return html_content

    def _restore_protected_phrases(self, html_content):
        """
        Restore protected phrases that the AI model incorrectly modified.
        The AI sometimes replaces adjectives in fixed phrases despite being told
        not to. This deterministically catches and reverses those replacements.
        E.g. "formidable password" → "strong password",
             "mobile-earliest" → "mobile-first",
             "verifiable money" → "real money".
        """
        # Map of corrupted phrase → correct phrase
        # Covers all protected words removed from synonym groups:
        # strong, real, first, true, open, simple, small, focused
        corrupted_to_correct = {
            # "strong password(s)" — AI replaces "strong" with powerful-group synonyms
            'formidable password': 'strong password',
            'robust password': 'strong password',
            'potent password': 'strong password',
            'mighty password': 'strong password',
            'dominant password': 'strong password',
            'formidable passwords': 'strong passwords',
            'robust passwords': 'strong passwords',
            'potent passwords': 'strong passwords',
            'mighty passwords': 'strong passwords',
            'dominant passwords': 'strong passwords',
            # "real money" — AI replaces "real" with genuine-group synonyms
            'verifiable money': 'real money',
            'authentic money': 'real money',
            'actual money': 'real money',
            'proven money': 'real money',
            'genuine money': 'real money',
            # "real estate"
            'verifiable estate': 'real estate',
            'authentic estate': 'real estate',
            'actual estate': 'real estate',
            'proven estate': 'real estate',
            'genuine estate': 'real estate',
            # "real value"
            'verifiable value': 'real value',
            'authentic value': 'real value',
            'actual value': 'real value',
            'proven value': 'real value',
            # "real-world" / "real world"
            'verifiable-world': 'real-world',
            'authentic-world': 'real-world',
            'actual-world': 'real-world',
            'proven-world': 'real-world',
            'genuine-world': 'real-world',
            'verifiable world': 'real world',
            'authentic world': 'real world',
            'actual world': 'real world',
            'proven world': 'real world',
            # "mobile-first" — AI replaces "first" with opening-group synonyms
            'mobile-earliest': 'mobile-first',
            'mobile-starting': 'mobile-first',
            'mobile-initial': 'mobile-first',
            'mobile-opening': 'mobile-first',
            'mobile-upfront': 'mobile-first',
            'mobile-beginning': 'mobile-first',
            # "true ownership" — AI replaces "true" with genuine-group synonyms
            'authentic ownership': 'true ownership',
            'genuine ownership': 'true ownership',
            'actual ownership': 'true ownership',
            'verifiable ownership': 'true ownership',
            'proven ownership': 'true ownership',
            'verified ownership': 'true ownership',
            # "open rewards/world/source/gaming" — AI replaces "open"
            'accessible rewards': 'open rewards',
            'approachable rewards': 'open rewards',
            'unrestricted rewards': 'open rewards',
            'accessible gaming': 'open gaming',
            'approachable gaming': 'open gaming',
            'unrestricted gaming': 'open gaming',
            # "simple mining" — AI replaces "simple"
            'elementary mining': 'simple mining',
            'foundational mining': 'simple mining',
            'introductory mining': 'simple mining',
            'entry-level mining': 'simple mining',
            'basic mining': 'simple mining',
            # "small amount" — AI replaces "small"
            'modest amount': 'small amount',
            'restricted amount': 'small amount',
            'constrained amount': 'small amount',
            'limited amount': 'small amount',
            'minimal amount': 'small amount',
            # "focused prompt" — AI replaces "focused"
            'dedicated prompt': 'focused prompt',
            'committed prompt': 'focused prompt',
            'devoted prompt': 'focused prompt',
            # "first step" — AI replaces "first"
            'initial step': 'first step',
            'opening step': 'first step',
            'starting step': 'first step',
            # "first account" — AI replaces "first"
            'initial account': 'first account',
            'opening account': 'first account',
            'starting account': 'first account',
            # Awkward collocations the AI produces
            'prized prizes': 'exclusive prizes',
            'prized rewards': 'exclusive rewards',
        }

        for corrupted, correct in corrupted_to_correct.items():
            # Case-insensitive search, case-preserving replacement
            pattern = re.compile(re.escape(corrupted), re.IGNORECASE)
            html_content = pattern.sub(
                lambda m, c=correct: (
                    c[0].upper() + c[1:] if m.group(0)[0].isupper() else c
                ),
                html_content
            )

        return html_content

    def _deduplicate_descriptors(self, html_content):
        """
        Scans for repeated descriptors and replaces duplicates with unused
        synonyms from the same semantic group, while protecting fixed phrases.
        """

        for group in self.SYNONYM_GROUPS:
            # Collect all occurrences of any word from this group
            all_occurrences = []

            for word in group:
                escaped = re.escape(word)
                # Word boundary match, case insensitive
                # Use \b for simple words, custom boundaries for hyphenated
                if '-' in word:
                    pattern = re.compile(
                        r'(?<![a-zA-Z])' + escaped + r'(?![a-zA-Z])',
                        re.IGNORECASE
                    )
                else:
                    pattern = re.compile(
                        r'\b' + escaped + r'\b',
                        re.IGNORECASE
                    )

                for match in pattern.finditer(html_content):
                    # Skip if inside an HTML tag (between < and >)
                    pre_text = html_content[:match.start()]
                    last_open = pre_text.rfind('<')
                    last_close = pre_text.rfind('>')
                    if last_open > last_close:
                        continue  # Inside an HTML tag, skip

                    # Skip if this match is part of a protected phrase
                    match_start = match.start()
                    match_end = match.end()
                    is_protected = False
                    for phrase in self.PROTECTED_PHRASES:
                        # Check a window around the match for the protected phrase
                        window_start = max(0, match_start - 30)
                        window_end = min(len(html_content), match_end + 30)
                        window = html_content[window_start:window_end].lower()
                        if phrase.lower() in window:
                            is_protected = True
                            break
                    if is_protected:
                        continue

                    all_occurrences.append({
                        'start': match_start,
                        'end': match_end,
                        'original': match.group(),
                        'word_lower': word.lower(),
                    })

            # Sort by position in text
            all_occurrences.sort(key=lambda x: x['start'])

            if len(all_occurrences) <= 1:
                continue

            # Keep the first occurrence, replace subsequent ones
            used_words = {all_occurrences[0]['word_lower']}
            replacements = []

            for occ in all_occurrences[1:]:
                if occ['word_lower'] not in used_words:
                    # This word hasn't been used yet, keep it
                    used_words.add(occ['word_lower'])
                    continue

                # This word (or a synonym) already used — find an unused synonym
                available = [w for w in group if w.lower() not in used_words]
                if not available:
                    continue  # All synonyms exhausted, skip

                replacement = available[0]
                used_words.add(replacement.lower())

                # Match the capitalisation of the original
                original = occ['original']
                if original[0].isupper():
                    replacement = replacement[0].upper() + replacement[1:]

                replacements.append((occ['start'], occ['end'], replacement))

            # Apply replacements in reverse order to preserve string positions
            for start, end, repl in reversed(replacements):
                html_content = html_content[:start] + repl + html_content[end:]

        return html_content

