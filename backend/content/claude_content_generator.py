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
1. Replace all em-dashes (\u2014) with commas, semicolons, or full stops as contextually appropriate.
2. Restructure sentences: approximately 60% should be 8\u201310 words, 40% should be 15\u201325 words.
3. Make the tone conversational, personalised, and non-preachy.
4. Distribute anchor text and keywords evenly across all sections (not cluttered in one place).
5. Replace straight quotes (" ') with curly quotes (\u201c \u201d \u2018 \u2019).
6. MANDATORY SECTION VARIATION: Count every similar section (e.g. game reviews, product listings, feature descriptions). If there are N similar sections, you MUST use at least 3 different paragraph counts among them. For 10 sections: give 3 sections exactly 2 paragraphs, give 4 sections exactly 3 paragraphs, give 3 sections exactly 4 paragraphs. Having all sections with the same paragraph count (e.g. all 3 paragraphs) is a HARD FAILURE — the output will be rejected. Merge short paragraphs or split long ones to achieve variation.
7. BANNED WORDS — scan the entire output and rewrite every sentence that contains any of these: "remain", "remains", "remaining", "especially", "particularly", "may", "can", "leverage", "comprehensive", "remarkably", "significantly", "furthermore", "moreover", "additionally", "utilize", "utilise". Replace with simpler alternatives (e.g. "leverage" → "use", "comprehensive" → "full/complete/detailed", "remarkably" → "unusually/notably", "can earn" → "earn", "may help" → "helps"). Also NEVER start any sentence with a gerund (-ing word). Scan every sentence opening: if it starts with "Setting", "Buying", "Converting", "Understanding", "Owning", "Mining", "Purchasing", "Connecting", "Trading", "Earning", "Staking", "Timing", "Playing", "Farming", "Building", "Creating", or ANY other -ing word, restructure it. Examples: "Setting up a wallet..." → "Your first step is a wallet setup..." / "Buying cryptocurrency..." → "You buy cryptocurrency..." / "Understanding gas fees..." → "Gas fees are..." / "Owning LAND..." → "LAND ownership..." / "Earning opportunities..." → "The earning opportunities..." / "Staking allows..." → "The staking mechanism allows..." / "Timing your transactions..." → "Time your transactions...".
8. Remove buzzwords (cutting-edge, innovative, advanced technology, leverage, game-changer, harness, empower, seamlessly, revolutionise) unless backed by specific data.
9. Remove clich\u00e9s ("In today\u2019s world", "Needless to say", "It\u2019s no secret that").
10. Remove rhetorical questions, generic connectors ("not just... but also..."). Never open or close a section with a question.
11. One idea per sentence; prefer clarity over complexity.
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
   This is a HARD RULE with zero exceptions. Three items in a row is an AI detection fingerprint. Scan every sentence for commas between nouns/verbs — if there are 3+ items, cut to 2.
15. Maintain logical flow: introductions should lead into the topic naturally, and conclusions must guide the reader forward (e.g. next steps, what to do now) — never summarise what was already said. Do not end sections with "In conclusion" or recap sentences.
16. STRICT NO-REPEAT RULE: Never use the same adjective, adverb, or descriptive word twice in the entire content. After writing, scan for repeated descriptors and replace duplicates with synonyms. Common offenders to watch: "substantial" (use: significant/considerable/sizeable — but each only once), "straightforward" (use: simple/direct/easy), "unusually" (use: notably/surprisingly), "diverse" (use: varied/wide-ranging), "unique" (use: distinct/one-of-a-kind). If a word already appeared earlier, you MUST use a different synonym. Remove generic phrasings like "XYZ is not just abc", "From abc to xyz".

CRITICAL CHECKS — After transforming, scan the full output line by line and fix ANY violations:
□ No sentence starts with an -ing word (Setting, Buying, Converting, Understanding, Owning, Mining, Purchasing, Connecting, Trading, Earning, Staking, Timing, Playing, Farming, Building, Creating, etc.)
□ No comma-separated list has 3+ items anywhere — scan every comma between nouns/verbs and verify only 2 items exist
□ None of the banned words from Rule 7 appear anywhere
□ Count the paragraph count of each similar section (e.g. game reviews) — they MUST have at least 3 different counts (e.g. some 2, some 3, some 4). If all sections have the same count, merge or split paragraphs to create variation
□ No word like "comprehensive", "remarkably", "leverage", "especially", "particularly" survived
□ No adjective or adverb appears more than once in the entire content — search for "substantial", "straightforward", "unusually", "diverse", "unique" and ensure each appears at most once

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
                if 'overloaded' in error_str or '529' in error_str or 'rate' in error_str:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 2
                        time.sleep(wait_time)
                        continue
                raise Exception(f"Claude API error during humanisation: {str(e)}")

        raise Exception(f"Claude API error during humanisation after {max_retries} retries: {str(last_error)}")

