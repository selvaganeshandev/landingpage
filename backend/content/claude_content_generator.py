"""
Claude API Content Generator
This module handles content generation using the Claude API
"""

import os
import re
import time
import logging
from anthropic import Anthropic
from django.conf import settings
from decouple import config

logger = logging.getLogger(__name__)


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

    # Maps the word_count value stored by the UI dropdown to the (lower, upper)
    # word-count range the generated content must fall within. Each tuple is
    # (match_threshold, lower_bound, upper_bound): we pick the first row where
    # word_count <= match_threshold. Labels listed in the frontend:
    #   Main article / web-page:
    #     value=300  → "Below 500 words" (legacy) → 300-500
    #     value=700  → "Below 800 words"          → 500-800
    #     value=800  → "800-1,000 words"          → 800-1000
    #     value=1500 → "1,000-2,000 words"        → 1000-2000
    #     value=2500 → "2,000-3,000 words"        → 2000-3000
    #     value=3500 → "3,000+ words"             → 3000-4500
    #   Social media:
    #     value=50   → "Short (50-100 words)"
    #     value=150  → "Medium (150-250 words)"
    #     value=300  → "Long (300-500 words)"
    #     value=500  → "Thread (500+ words)"
    #   Community:
    #     value=150  → "Brief (150-300 words)"
    #     value=400  → "Standard (400-600 words)"
    #     value=800  → "Detailed (800-1,200 words)"
    #     value=1500 → "Comprehensive (1,500+ words)"
    _WORD_COUNT_RANGES_LIST = [
        (100, 50, 100),       # social Short
        (250, 150, 250),      # social Medium / community Brief
        (300, 300, 500),      # social Long / main "Below 500 words" (legacy)
        (500, 400, 600),      # community Standard / social Thread
        (700, 500, 800),      # main "Below 800 words"
        (800, 800, 1000),     # main "800-1,000 words" / community Detailed
        (1500, 1000, 2000),   # main "1,000-2,000 words"
        (2500, 2000, 3000),   # main "2,000-3,000 words"
        (3500, 3000, 4500),   # main "3,000+ words" (some headroom)
    ]

    @classmethod
    def _word_count_range(cls, word_count):
        """Return the (lower, upper) word count bounds for a dropdown value."""
        if not word_count or word_count <= 0:
            return (1000, 2000)
        for threshold, lower, upper in cls._WORD_COUNT_RANGES_LIST:
            if word_count <= threshold:
                return (lower, upper)
        # Beyond the largest threshold: treat input as the lower bound.
        return (word_count, int(word_count * 1.25))

    @classmethod
    def _upper_word_limit(cls, word_count):
        """Return the upper-bound word count for the dropdown value."""
        return cls._word_count_range(word_count)[1]

    @classmethod
    def _lower_word_limit(cls, word_count):
        """Return the lower-bound word count for the dropdown value."""
        return cls._word_count_range(word_count)[0]

    @classmethod
    def _calculate_max_tokens(cls, word_count, is_section=False):
        """Calculate dynamic max_tokens based on requested word count.
        HTML content uses ~2.5 tokens per word once h2/h3/<ul>/<li>/<strong>
        markup is included. The previous 2.0 ratio + 500 buffer hit max_tokens
        before Claude could finish long-form articles (3000+ words), causing
        the last sections / subheadings to be dropped and the article to end
        mid-thought. The bump gives Claude enough headroom to complete every
        planned section and reach a proper conclusion.
        """
        if is_section:
            return max(4096, int(word_count * 2.5) + 500)
        upper = cls._upper_word_limit(word_count)
        tokens = int(upper * 2.5) + 1500
        # Floor 2048 for tiny requests; cap at 24576 for very large ones
        # (still well within Sonnet 4.5's 64K output limit).
        return max(2048, min(tokens, 24576))

    @classmethod
    def _calculate_outline_max_tokens(cls, word_count, extended=False):
        # Outline JSON is structurally smaller than the article body, but its
        # size still scales with section count + key_points (which scale with
        # word_count). The previous fixed 2048-token cap silently truncated
        # outlines for 2500+ word articles, dropping trailing sections from
        # the bulk-upload pipeline. `extended=True` doubles the budget for
        # the validation-retry path.
        upper = cls._upper_word_limit(word_count)
        tokens = int(upper * 0.6) + 1024
        base = max(2048, min(tokens, 8192))
        if extended:
            return min(base * 2, 16384)
        return base

    @staticmethod
    def _strip_code_fences(content):
        """Remove markdown code fences Claude occasionally wraps HTML in.

        Handles patterns like:
            ```html\n<h2>...</h2>\n```
            ```\n<p>...</p>\n```
        Only strips fences that wrap the entire response — inline code blocks
        inside the content are left untouched.
        """
        if not content:
            return content
        stripped = content.strip()
        # Leading fence: ```html / ```HTML / ```
        stripped = re.sub(r'^```[a-zA-Z]*\s*\r?\n', '', stripped)
        # Trailing fence
        stripped = re.sub(r'\r?\n```\s*$', '', stripped)
        return stripped.strip()

    @staticmethod
    def _decode_escaped_html(content):
        """Decode HTML entities when the response came back entity-escaped.

        Sometimes Claude returns content like "&lt;h2&gt;Title&lt;/h2&gt;"
        which, when rendered via innerHTML, appears as literal text rather
        than an H2 tag. Detect that case and unescape.
        """
        if not content:
            return content
        escaped_brackets = content.count('&lt;') + content.count('&gt;')
        raw_brackets = content.count('<') + content.count('>')
        # Only decode when the content is predominantly entity-escaped,
        # otherwise we'd corrupt legitimate entities inside normal HTML.
        if escaped_brackets > 0 and escaped_brackets > raw_brackets:
            import html as _html
            return _html.unescape(content)
        return content

    @staticmethod
    def _unwrap_outer_code_block(content):
        """Strip a <pre><code>...</code></pre> wrapper around the whole response."""
        if not content:
            return content
        stripped = content.strip()
        m = re.match(
            r'^<pre[^>]*>\s*<code[^>]*>(.*)</code>\s*</pre>$',
            stripped, re.IGNORECASE | re.DOTALL
        )
        if m:
            return m.group(1).strip()
        m = re.match(
            r'^<code[^>]*>(.*)</code>$',
            stripped, re.IGNORECASE | re.DOTALL
        )
        if m:
            return m.group(1).strip()
        return content

    @classmethod
    def _sanitize_html_response(cls, content):
        """Run the full cleanup pipeline on Claude's HTML response."""
        content = cls._strip_code_fences(content)
        content = cls._unwrap_outer_code_block(content)
        content = cls._decode_escaped_html(content)
        return content

    @staticmethod
    def _parse_keywords(keywords):
        """Split a comma-separated keyword string into a cleaned list.

        Returns a list of deduplicated, non-empty keyword strings preserving
        input order (so the first keyword can be treated as primary).
        """
        if not keywords:
            return []
        parts = [k.strip() for k in str(keywords).split(',')]
        seen = set()
        result = []
        for kw in parts:
            if not kw:
                continue
            key = kw.lower()
            if key in seen:
                continue
            seen.add(key)
            result.append(kw)
        return result

    @classmethod
    def _format_keywords_for_prompt(cls, keywords, word_count):
        """Build an explicit, enumerated keyword block for the generation prompts.

        Each keyword is listed on its own line so Claude treats them as discrete
        items rather than a single "topic blob". Returns a fallback single-line
        block if there is only 0-1 keyword (no enumeration needed).
        """
        kw_list = cls._parse_keywords(keywords)
        if not kw_list:
            return "**Target Keywords:** (none provided)\n"
        if len(kw_list) == 1:
            return f"**Target Keyword (MUST appear in content):** {kw_list[0]}\n"

        upper = cls._upper_word_limit(word_count)
        # Frequency targets scale with article length.
        if upper <= 500:
            freq = "1-2 times"
        elif upper <= 1500:
            freq = "2-3 times"
        else:
            freq = "3-5 times"

        numbered = "\n".join(f"  {i}. \"{kw}\"" for i, kw in enumerate(kw_list, 1))
        primary = kw_list[0]
        secondary = ", ".join(f'"{k}"' for k in kw_list[1:])

        return (
            "**Target Keywords (EVERY keyword below MUST appear in the final content):**\n"
            f"{numbered}\n\n"
            "KEYWORD USAGE RULES:\n"
            f"- Each of the {len(kw_list)} keywords above MUST appear in the content at least once — do NOT silently drop any of them.\n"
            f"- Aim for approximately {freq} per keyword across the article.\n"
            "- Spread keywords across different sections/paragraphs — do not cluster them all in the intro.\n"
            f"- Primary keyword \"{primary}\": use it in the introduction, in at least one h2 heading, and in the conclusion.\n"
            f"- Secondary keywords ({secondary}): weave them into body paragraphs where they fit naturally.\n"
            "- Use keywords naturally — no keyword stuffing, no awkward phrasing.\n"
            "- Use exact spellings as listed (same casing or natural capitalisation at sentence start); do not substitute synonyms for the keyword itself.\n"
        )

    @classmethod
    def _missing_keywords(cls, content_html, keywords):
        """Return the list of keywords that do not appear in the HTML content.

        Comparison is case-insensitive substring match against the plain text
        extracted from the HTML.
        """
        kw_list = cls._parse_keywords(keywords)
        if not kw_list or not content_html:
            return []
        plain_text = re.sub(r'<[^>]+>', ' ', content_html)
        plain_text = re.sub(r'\s+', ' ', plain_text).lower()
        return [kw for kw in kw_list if kw.lower() not in plain_text]

    @staticmethod
    def _count_lists(content_html):
        """Return the number of top-level <ul> and <ol> blocks in the HTML."""
        if not content_html:
            return 0
        # Count only opening tags, case-insensitive; attribute-tolerant.
        return len(re.findall(r'<(?:ul|ol)\b', content_html, flags=re.IGNORECASE))

    @staticmethod
    def _count_tables(content_html):
        """Return the number of <table> blocks in the HTML."""
        if not content_html:
            return 0
        return len(re.findall(r'<table\b', content_html, flags=re.IGNORECASE))

    @classmethod
    def _required_list_count(cls, word_count, user_requested_list=False):
        """Minimum <ul>/<ol> blocks expected given the target word count.

        Short content (below ~600 words cap) has no hard list requirement —
        a concise piece can be all prose. Medium articles need one list,
        long articles need two so enumerations aren't all buried in paragraphs.

        When the content creator explicitly asks for a list in their
        instructions, force a minimum of 1 even on short articles.
        """
        upper = cls._upper_word_limit(word_count)
        if upper < 600:
            base = 0
        elif upper <= 1000:
            base = 1
        else:
            base = 2
        if user_requested_list:
            return max(1, base)
        return base

    # ------------------------------------------------------------------
    # Free-text prompt detection: list / table requests from the client
    # ------------------------------------------------------------------
    # When users fill in "Additional Instructions" or "Key Messages" they
    # often ask for structured output using everyday words rather than HTML
    # terms. Examples we see in production:
    #   - "Include a table comparing the plans"
    #   - "List the main points"
    #   - "Cover these topics as bullet points"
    #   - "Show the differences between A and B"
    #   - "Categorise the items"
    #   - "Add a menu of options"
    #   - "Show pros and cons side by side"
    #
    # The regexes below are deliberately broad so any of these phrasings
    # (and close variants) will trigger:
    #   1. The strong "REQUIRED" structure block in the generation prompt
    #   2. The list / table safety-net post-processing pass after generation
    # That way a brief instruction like "use a list and table" can't be
    # quietly ignored, and Claude won't return paragraphs when the client
    # explicitly asked for structured formatting.
    #
    # Tip: keep these patterns in sync with the comparison/listing intent
    # detectors above (`_COMPARISON_SIGNALS`, `_LISTING_SIGNALS`) — those
    # look at the article title/keywords; these look at the user's
    # free-text instructions.

    # Words/phrases that mean "I want list-style output (<ul> or <ol>)".
    # Covers explicit list terminology AND common enumeration nouns the
    # client might use ("points", "topics", "categories", "items", "menus",
    # "steps", "tips", "options", …).
    _USER_LIST_REQUEST_SIGNALS = [
        # Explicit list / bullet / numbered terminology
        r'\blists?\b',                          # list, lists
        r'\blisting\b',                         # listing
        r'\blistify\b',                         # listify
        r'\bbullet(ed|s)?\b',                   # bullet, bulleted, bullets
        r'\bbullet[- ]?points?\b',              # bullet point, bullet-points
        r'\bnumbered\b',                        # numbered (list/items/format)
        r'\bordered\b',                         # ordered (list)

        # Enumeration nouns clients commonly use to mean "list these out"
        # ("the main points", "cover the topics", "list the categories",
        # "menu items", …)
        r'\bpoints?\b',                         # point, points
        r'\btopics?\b',                         # topic, topics
        r'\bcategor(y|ies|ize|ized|ization|ising|ised|isation)\b',  # category, categorise, …
        r'\bitems?\b',                          # item, items
        r'\bmenus?\b',                          # menu, menus
        r'\bsteps?\b',                          # step, steps
        r'\btips?\b',                           # tip, tips
        r'\boptions?\b',                        # option, options
        r'\bchecklists?\b',                     # checklist, checklists
        r'\btakeaways?\b',                      # takeaway, takeaways
        r'\bhighlights?\b',                     # highlight, highlights

        # Compound phrasings that almost always mean an ordered/unordered list
        r'\bstep[- ]by[- ]step\b',              # step-by-step / step by step
        r'\btop\s+\d+\b',                       # "top 5", "top 10"
        r'\bbest\s+\d+\b',                      # "best 5"
        r'\b\d+\s+(ways|tips|reasons|things|points|items|options|topics|features|benefits|methods|examples|ideas|tools|mistakes)\b',

        # Raw HTML hints (advanced clients sometimes write these)
        r'<ul\b',
        r'<ol\b',
    ]

    # Words/phrases that mean "I want a real HTML <table>".
    # Covers explicit table terminology AND comparison phrasings that are
    # naturally tabular ("compare X and Y", "differences between", "vs",
    # "side by side", "pros and cons", …).
    _USER_TABLE_REQUEST_SIGNALS = [
        # Explicit table terminology
        r'\btables?\b',                         # table, tables
        r'\btabular\b',                         # tabular (format/layout)
        r'<table\b',                            # raw HTML

        # Comparison phrasings that should render as a table
        r'\bcompar(e|ed|es|ing|ison|isons)\b',  # compare, compared, comparison, comparing
        r'\bdifferenc(e|es)\b',                 # difference, differences
        r'\bvs\.?\b',                           # vs, vs.
        r'\bversus\b',                          # versus
        r'\bside[- ]by[- ]side\b',              # side-by-side, side by side
        r'\bpros\s+and\s+cons\b',               # pros and cons
        r'\badvantages?\s+and\s+disadvantages?\b',  # advantages and disadvantages
    ]

    @classmethod
    def _user_requested_list_format(cls, additional_instructions, key_messages=''):
        """Did the client ask for list-style output in their instructions?

        Scans the free-text fields the client controls (Additional Instructions
        + Key Messages) for words that mean "render this as a <ul> or <ol>".
        We detect both explicit list terms ("list", "bullet points",
        "numbered") AND common enumeration nouns that clients use in plain
        English ("points", "topics", "categories", "items", "menus", "steps",
        "tips", "options", "checklist", "step-by-step", "top 5", …).

        Examples that return True:
            "Cover the main topics in a list"
            "Add bullet points for the key benefits"
            "Categorise the items"
            "Include a menu of services"
            "Step-by-step instructions please"
            "Top 10 tips"

        Returns:
            bool: True if any list-style intent is found, otherwise False.
        """
        text = ' '.join([
            str(additional_instructions or ''),
            str(key_messages or ''),
        ]).lower()
        if not text.strip():
            return False
        return any(re.search(p, text) for p in cls._USER_LIST_REQUEST_SIGNALS)

    @classmethod
    def _user_requested_table_format(cls, additional_instructions, key_messages=''):
        """Did the client ask for table-style output in their instructions?

        Scans the free-text fields the client controls (Additional Instructions
        + Key Messages) for words that mean "render this as an HTML <table>".
        We detect both explicit table terms ("table", "tabular") AND comparison
        phrasings that are naturally tabular ("compare", "comparison",
        "difference between", "vs", "versus", "side-by-side", "pros and
        cons", "advantages and disadvantages").

        Examples that return True:
            "Include a table comparing the plans"
            "Show the differences between A and B"
            "Add a tabular layout for pricing"
            "Pros and cons of each option"
            "Compare the top 3 tools"

        Returns:
            bool: True if any table-style intent is found, otherwise False.
        """
        text = ' '.join([
            str(additional_instructions or ''),
            str(key_messages or ''),
        ]).lower()
        if not text.strip():
            return False
        return any(re.search(p, text) for p in cls._USER_TABLE_REQUEST_SIGNALS)

    # Phrases in the title or keywords that strongly signal the reader
    # wants two or more entities compared side-by-side. Used to force a
    # comparison <table> into the article so the differences are scannable
    # rather than buried in prose.
    _COMPARISON_SIGNALS = [
        r'\bvs\.?\b',
        r'\bv\.?s\.?\b',
        r'\bversus\b',
        r'\bcompare[sd]?\b',
        r'\bcomparison\b',
        r'\bdifference[s]? between\b',
        r'\bwhich is better\b',
        r'\bwhat is better\b',
        r'\b(is |which )(one )?better\b',
    ]

    # Phrases signalling a listable article (types of X, top N, categories,
    # features list, …). Used to nudge the prompt toward explicit <ul>/<ol>
    # structures for scannability.
    _LISTING_SIGNALS = [
        r'\btypes? of\b',
        r'\bkinds? of\b',
        r'\bcategor(y|ies)\b',
        r'\btop \d+\b',
        r'\bbest \d+\b',
        r'\b\d+ (ways|tips|tools|reasons|benefits|features|steps|examples|options|ideas|mistakes|methods)\b',
        r'\bhow to\b',
        r'\bstep[- ]by[- ]step\b',
        r'\bchecklist\b',
        r'\bfeatures? of\b',
    ]

    @classmethod
    def _is_comparison_intent(cls, title, keywords, article_type):
        """Return True when the content should include a comparison table.

        Triggered when article_type is explicitly 'comparison', or when the
        title/keywords contain comparison-intent phrasing ("vs", "versus",
        "difference between", "which is better", …).
        """
        if article_type == 'comparison':
            return True
        haystack_parts = []
        if title:
            haystack_parts.append(str(title).lower())
        if keywords:
            haystack_parts.append(str(keywords).lower())
        if not haystack_parts:
            return False
        combined = ' '.join(haystack_parts)
        return any(re.search(pat, combined) for pat in cls._COMPARISON_SIGNALS)

    @classmethod
    def _is_listing_intent(cls, title, keywords, article_type):
        """Return True when the content is shaped as a list/enumeration piece.

        Used to reinforce list-formatting rules in the generation prompt so
        enumerations of types, categories, features, or steps render as
        <ul>/<ol> blocks instead of prose.
        """
        if article_type in ('listicle', 'guide'):
            return True
        haystack_parts = []
        if title:
            haystack_parts.append(str(title).lower())
        if keywords:
            haystack_parts.append(str(keywords).lower())
        if not haystack_parts:
            return False
        combined = ' '.join(haystack_parts)
        return any(re.search(pat, combined) for pat in cls._LISTING_SIGNALS)

    @classmethod
    def _format_structure_hints(cls, title, keywords, article_type, word_count,
                                user_requested_list=False, user_requested_table=False):
        """Build an explicit structural-rules block for the generation prompt.

        Returns a string (may be empty) that instructs Claude to use a
        comparison <table> when the topic implies comparison, and to use
        <ul>/<ol> for types/categories/features/steps when the topic implies
        enumeration. Always safe to append — returns '' when no signals match.

        When the content creator explicitly asks for a list or table in their
        instructions, the corresponding REQUIRED block is forced in even when
        the topic-intent detection doesn't match.
        """
        parts = []

        is_comparison = cls._is_comparison_intent(title, keywords, article_type)
        if is_comparison:
            parts.append(
                "**COMPARISON TABLE (REQUIRED):**\n"
                "The topic involves comparing two or more entities, so the content MUST include at least one HTML comparison table.\n"
                "- Use this exact structure: <table><thead><tr><th>Criteria</th><th>Entity A</th><th>Entity B</th></tr></thead><tbody><tr><td>...</td><td>...</td><td>...</td></tr></tbody></table>\n"
                "- Columns: one per entity being compared (name each in <th>). Rows: one per criterion (price, key features, pros, cons, specs, target user, availability, etc.).\n"
                "- Include 6-10 meaningful comparison rows — the kind of differences a buyer would weigh, not filler.\n"
                "- Place the table near the top of the article (after a short intro paragraph) so readers can scan the differences first.\n"
                "- Follow the table with 1-2 short paragraphs interpreting the comparison and highlighting which entity suits which use case.\n"
                "- Do NOT use markdown pipe tables (| col1 | col2 |). Use real HTML <table> tags only.\n"
                "- Do NOT duplicate the same table twice — one well-built comparison table is enough.\n"
            )
        elif user_requested_table:
            # User asked for a table but the topic isn't an explicit comparison.
            # Use a more flexible "data table" instruction so any tabular content
            # (specs, pricing tiers, pros/cons, options summary, …) qualifies.
            parts.append(
                "**HTML TABLE (REQUIRED — content creator explicitly asked for a table):**\n"
                "The content MUST include at least one real HTML <table> block. This is a hard requirement from the content creator's instructions, not a suggestion.\n"
                "- Use this exact shape: <table><thead><tr><th>Column 1</th><th>Column 2</th>...</tr></thead><tbody><tr><td>...</td><td>...</td></tr></tbody></table>\n"
                "- Pick the section of the article whose content is most naturally tabular: a comparison of options, a feature/spec breakdown, pros vs cons, pricing tiers, before-vs-after, criteria-by-option, or any structured data set.\n"
                "- Use 3-6 columns and 4-8 rows of meaningful data. Header cells go in <thead>, data rows in <tbody>.\n"
                "- Precede the table with a short intro sentence and follow it with 1-2 short paragraphs interpreting the data.\n"
                "- Do NOT use markdown pipe tables (| col1 | col2 |). Use real HTML <table> tags only.\n"
                "- Do NOT skip the table because \"prose works fine\" — the content creator specifically requested tabular formatting.\n"
            )

        is_listing = cls._is_listing_intent(title, keywords, article_type)
        if is_listing or user_requested_list:
            header = (
                "**LISTING FORMAT (REQUIRED — content creator explicitly asked for lists):**\n"
                if user_requested_list and not is_listing
                else "**LISTING FORMAT (REQUIRED):**\n"
            )
            intro = (
                "The content creator's instructions specifically request list formatting, so the article MUST include at least one <ul> or <ol> block.\n"
                if user_requested_list and not is_listing
                else "The topic naturally maps to an enumeration (types, categories, features, steps, options).\n"
            )
            parts.append(
                header
                + intro
                + "- Render each enumerated set as a <ul> (unordered) or <ol> (ordered when sequence matters) — not as prose or comma-separated sentences.\n"
                "- Each <li> should start with a <strong>Label:</strong> followed by a concise explanation (1-2 sentences).\n"
                "- Precede each list with a short intro sentence so the list has context.\n"
                "- For \"types/kinds/categories\" topics: one <ul> per category group. For \"top N\" / \"best N\" topics: use <ol> with N items, ranked.\n"
                "- For step-by-step guides: use <ol> with one step per <li>; keep each step actionable.\n"
            )

        # Always add a concise SEO structural checklist — cheap to include
        # and keeps the article professionally formatted regardless of topic.
        parts.append(
            "**PROFESSIONAL SEO STRUCTURE:**\n"
            "- Introduction (1-2 short paragraphs): establish the topic, include the primary keyword, and set reader expectations.\n"
            "- Body: 4-6 <h2> sections (fewer for articles under 500 words). Each <h2> should cover a distinct sub-topic with 2-4 short paragraphs OR a <ul>/<ol>/<table> where the content fits that shape better than prose.\n"
            "- Use <h3> subsections only when a <h2> section needs further breakdown — don't stack heading levels unnecessarily.\n"
            "- Keep paragraphs to 2-4 sentences. Prefer short, scannable sentences (15-25 words) over long ones.\n"
            "- Use <strong> sparingly to highlight key terms, figures, or lead-ins inside list items.\n"
            "- Conclusion (required): a final <h2> such as \"Conclusion\", \"Final Verdict\", \"Key Takeaways\", or a topical closer. Summarise the main points and, where applicable, end with a recommendation or call-to-action.\n"
            "- Never end the article mid-sentence or mid-section. The last HTML block must be a complete closing paragraph (or a <ul> of key takeaways followed by one closing paragraph).\n"
        )

        return "\n".join(parts)

    @staticmethod
    def _promote_bold_leadin_paragraphs_to_list(content_html):
        """Deterministic converter: finds 3+ consecutive <p> paragraphs that
        each start with a <strong>Term:</strong> label and fuses them into a
        single <ul>. This is the most common "prose enumeration" pattern
        Claude produces (e.g. "<p><strong>Speed:</strong> ...</p><p><strong>"
        "Cost:</strong> ...</p><p><strong>Security:</strong> ...</p>").

        Runs purely on regex — no API cost — so it's safe to call on every
        generation regardless of whether lists are already present.
        """
        if not content_html:
            return content_html, 0

        # A run is 3+ consecutive <p><strong>Label(:|.|—)?</strong> ...</p>
        # paragraphs with only whitespace between them.
        run_pattern = re.compile(
            r'(?:<p[^>]*>\s*<strong>[^<]{1,80}</strong>[^<]{0,800}</p>\s*){3,}',
            re.IGNORECASE | re.DOTALL,
        )
        # Individual paragraph extractor inside a matched run.
        p_pattern = re.compile(
            r'<p[^>]*>\s*(<strong>[^<]{1,80}</strong>[^<]{0,800})\s*</p>',
            re.IGNORECASE | re.DOTALL,
        )

        replacements = 0

        def convert(run_match):
            nonlocal replacements
            block = run_match.group(0)
            items = p_pattern.findall(block)
            if len(items) < 3:
                return block
            lis = "\n".join(f"  <li>{item.strip()}</li>" for item in items)
            replacements += 1
            return f"<ul>\n{lis}\n</ul>\n"

        new_html = run_pattern.sub(convert, content_html)
        return new_html, replacements

    def _ensure_lists_in_content(self, content_html, word_count, user_requested_list=False):
        """Safety net that guarantees long-form content has the expected
        number of <ul>/<ol> blocks.

        Runs in up to three passes — cheapest first:
          1. Deterministic regex converter (no API call) that promotes
             sequential "<strong>Label:</strong> …" paragraphs into a <ul>.
          2. Claude fix pass with few-shot examples. Retries once if the
             first response still contains fewer lists than required.
          3. Final log if still short — returns best-effort content rather
             than failing generation.

        When user_requested_list=True the required count is forced to at
        least 1 even on short articles, since the content creator
        specifically asked for list formatting.
        """
        if not content_html:
            return content_html, 0
        required = self._required_list_count(
            word_count, user_requested_list=user_requested_list
        )
        if required <= 0:
            return content_html, 0

        # Pass 1: deterministic regex promotion — cheap, no API cost.
        content_html, promoted = self._promote_bold_leadin_paragraphs_to_list(
            content_html
        )
        if promoted:
            logger.info(
                f"List-fix pass (regex) promoted {promoted} paragraph run(s) to <ul>"
            )

        current = self._count_lists(content_html)
        if current >= required:
            return content_html, 0

        # Pass 2: Claude call with few-shot examples. One retry if the first
        # response still falls short.
        upper = self._upper_word_limit(word_count)
        system_prompt = f"""You are an HTML restructuring assistant. Transform existing prose into HTML that uses <ul> or <ol> where enumerations appear.

RULES:
1. A paragraph that mentions 3+ parallel items (features, benefits, types, options, tips, tools, costs, permits, etc.) MUST be split into a short intro line plus a <ul> where each item becomes one <li>.
2. 3+ consecutive paragraphs that each describe one item in a parallel set (same sentence structure, or each starts with a bolded label) MUST be fused into a single <ul>.
3. 3+ consecutive paragraphs that describe sequential steps (First/Next/Finally, 1/2/3) MUST be fused into an <ol>.
4. Inside each <li>, if there is a natural term-definition shape, use "<li><strong>Term:</strong> description.</li>".
5. Preserve all headings (<h1>-<h6>), hyperlinks (<a>), images (<img>), and tables exactly.
6. Do NOT invent new content. Only restructure existing content.
7. Keep the total word count at or below {upper} words.
8. Return ONLY the updated HTML — no explanations, no markdown code blocks, no ```html fences.

EXAMPLES (study the transformation shape, not the topic):

BEFORE (prose enumeration in one paragraph):
<p>The key benefits include improved speed, lower costs, better scalability, and enhanced security for your users.</p>

AFTER (converted to <ul>):
<p>The key benefits include:</p>
<ul>
  <li><strong>Improved speed:</strong> faster load times for visitors.</li>
  <li><strong>Lower costs:</strong> reduced infrastructure overhead.</li>
  <li><strong>Better scalability:</strong> handles growing traffic smoothly.</li>
  <li><strong>Enhanced security:</strong> protects user data end to end.</li>
</ul>

BEFORE (sequential "first/next/finally" paragraphs):
<p>First, research your niche thoroughly to understand the market.</p>
<p>Next, create a business plan with clear financial projections.</p>
<p>Finally, secure funding through loans or investor partnerships.</p>

AFTER (converted to <ol>):
<ol>
  <li>Research your niche thoroughly to understand the market.</li>
  <li>Create a business plan with clear financial projections.</li>
  <li>Secure funding through loans or investor partnerships.</li>
</ol>

BEFORE (parallel-structure paragraphs):
<p>Yoast SEO helps you optimise on-page SEO and generate XML sitemaps.</p>
<p>WooCommerce turns your WordPress site into an online store.</p>
<p>WPForms lets you build contact and lead capture forms without code.</p>

AFTER (converted to <ul>):
<ul>
  <li><strong>Yoast SEO:</strong> optimises on-page SEO and generates XML sitemaps.</li>
  <li><strong>WooCommerce:</strong> turns your WordPress site into an online store.</li>
  <li><strong>WPForms:</strong> builds contact and lead capture forms without code.</li>
</ul>"""

        def _run_fix_call(html_in):
            user_prompt = (
                f"The HTML article below currently has {self._count_lists(html_in)} "
                f"<ul>/<ol> block(s). It MUST end up with at least {required} "
                f"<ul>/<ol> block(s). Identify enumerations in the existing "
                "content (parallel items, sequential steps, feature lists, "
                "benefit lists, type lists, option lists) and transform them "
                "into <ul> or <ol> using the rules and examples above. "
                f"Keep the word count at or below {upper} words. "
                f"Return ONLY the updated HTML with at least {required} "
                "<ul>/<ol> block(s).\n\n"
                f"Article HTML:\n{html_in}"
            )
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self._calculate_max_tokens(word_count),
                temperature=0.3,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            out = self._sanitize_html_response(response.content[0].text)
            out = self._convert_markdown_to_html(out)
            return out, response.usage.output_tokens

        total_extra_tokens = 0
        try:
            fixed, extra = _run_fix_call(content_html)
            total_extra_tokens += extra
            if fixed and len(fixed) >= len(content_html) * 0.5:
                new_count = self._count_lists(fixed)
                if new_count >= required:
                    logger.info(
                        f"List-fix pass (Claude) added lists: {current} -> {new_count} "
                        f"(required {required})"
                    )
                    return fixed, total_extra_tokens
                # First attempt fell short — retry once with the partial output
                # as a new starting point (it may already have some progress).
                logger.warning(
                    f"List-fix pass 1 produced {new_count} lists (<{required}); retrying"
                )
                retry_input = fixed if new_count > current else content_html
                fixed2, extra2 = _run_fix_call(retry_input)
                total_extra_tokens += extra2
                if fixed2 and len(fixed2) >= len(content_html) * 0.5:
                    new_count2 = self._count_lists(fixed2)
                    logger.info(
                        f"List-fix pass (Claude retry) final list count: {new_count2} "
                        f"(required {required})"
                    )
                    return fixed2, total_extra_tokens
                return fixed, total_extra_tokens
            logger.warning(
                "List-fix pass output looks too short; keeping original content"
            )
            return content_html, total_extra_tokens
        except Exception as e:
            logger.warning(f"List-fix pass failed (non-fatal): {e}")
            return content_html, total_extra_tokens

    def _ensure_table_in_content(self, content_html, word_count):
        """Safety net that inserts an HTML <table> when the content creator
        explicitly asked for one but the article was returned as paragraphs.

        Runs a single Claude fix pass that converts the most tabular section
        of the existing article into an HTML <table>. It must NOT invent new
        facts — it only restructures existing content. On any failure (or if
        the fix pass still produces no <table>) the original content is
        returned unchanged so generation never blocks on the safety net.

        Returns (fixed_html, extra_completion_tokens).
        """
        if not content_html:
            return content_html, 0
        if self._count_tables(content_html) > 0:
            return content_html, 0

        upper = self._upper_word_limit(word_count)
        system_prompt = (
            "You are an HTML restructuring assistant. The article below was "
            "supposed to include an HTML <table> (the content creator "
            "specifically asked for one) but currently has none. Find the "
            "section whose content is most naturally tabular — a comparison "
            "of options, a feature/spec breakdown, pros vs cons, pricing "
            "tiers, before-vs-after, criteria-by-option, or any structured "
            "data set — and convert that section into a real HTML <table>.\n\n"
            "RULES:\n"
            "1. Add exactly ONE <table> block. Use "
            "<table><thead><tr><th>...</th></tr></thead><tbody>"
            "<tr><td>...</td></tr></tbody></table>.\n"
            "2. Use 3-6 columns and 4-8 rows of meaningful data drawn from "
            "the existing article. Do NOT invent new facts, prices, or "
            "statistics that aren't already in the article.\n"
            "3. Place the <table> inside the section it summarises. Keep a "
            "short intro sentence above the table and (where natural) a "
            "1-sentence interpretation below it.\n"
            "4. Preserve all headings, paragraphs, lists, links, and images "
            "outside the converted section.\n"
            "5. Do NOT use markdown pipe tables (| col1 | col2 |). Use real "
            "HTML <table> tags only.\n"
            f"6. Keep total word count at or below {upper} words.\n"
            "7. Return ONLY the updated HTML — no markdown fences, no "
            "commentary, no ```html blocks."
        )
        user_prompt = (
            "The HTML article below has no <table> block. Insert exactly one "
            "<table> by converting the most tabular content into rows and "
            "columns. Do NOT invent facts. Return ONLY the updated HTML.\n\n"
            f"Article HTML:\n{content_html}"
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self._calculate_max_tokens(word_count),
                temperature=0.3,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            fixed = response.content[0].text
            fixed = self._sanitize_html_response(fixed)
            fixed = self._convert_markdown_to_html(fixed)
            extra_tokens = response.usage.output_tokens

            if not fixed or len(fixed) < len(content_html) * 0.5:
                logger.warning(
                    "Table-fix pass output looks too short; keeping original content"
                )
                return content_html, extra_tokens
            if self._count_tables(fixed) == 0:
                logger.warning(
                    "Table-fix pass did not add a <table>; keeping original content"
                )
                return content_html, extra_tokens

            logger.info(
                "Table-fix pass added <table> (user-requested table formatting)"
            )
            return fixed, extra_tokens
        except Exception as e:
            logger.warning(f"Table-fix pass failed (non-fatal): {e}")
            return content_html, 0

    def _fix_missing_keywords(self, content_html, missing, word_count):
        """Run a focused Claude call that weaves missing keywords into existing
        content without changing structure or exceeding the word-count cap.

        Returns (fixed_html, extra_completion_tokens). On any failure returns
        the original content unchanged (0 extra tokens) — this is a best-effort
        safety net, not a blocker.
        """
        if not missing or not content_html:
            return content_html, 0
        upper = self._upper_word_limit(word_count)
        missing_list = "\n".join(f"- \"{kw}\"" for kw in missing)

        system_prompt = (
            "You are an SEO editor. Your only job is to insert missing SEO "
            "keywords into existing HTML content naturally. Rules:\n"
            "- Insert each missing keyword at least once, in a contextually "
            "appropriate sentence or list item.\n"
            "- Preserve ALL existing HTML tags, attributes, headings, lists, "
            "tables, and hyperlinks exactly.\n"
            "- Do NOT add new sections or headings. Weave keywords into "
            "existing paragraphs or <li> items.\n"
            f"- Keep the final word count at or below {upper} words.\n"
            "- Use the exact spelling of each keyword as provided. Do NOT "
            "substitute synonyms for the keyword itself.\n"
            "- Return ONLY the updated HTML content, no explanations, no "
            "markdown code blocks."
        )
        user_prompt = (
            f"The HTML article below is missing these SEO keywords:\n"
            f"{missing_list}\n\n"
            "Insert each missing keyword naturally into the existing content "
            f"while staying within {upper} words. Return ONLY the updated HTML.\n\n"
            f"Article HTML:\n{content_html}"
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self._calculate_max_tokens(word_count),
                temperature=0.3,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            fixed = response.content[0].text
            fixed = self._sanitize_html_response(fixed)
            fixed = self._convert_markdown_to_html(fixed)
            extra_tokens = response.usage.output_tokens

            # If the fix pass somehow produced a much shorter or empty output,
            # fall back to the original content.
            if not fixed or len(fixed) < len(content_html) * 0.5:
                logger.warning(
                    "Keyword-fix pass output looks too short; keeping original content"
                )
                return content_html, extra_tokens

            still_missing = self._missing_keywords(fixed, ", ".join(missing))
            if still_missing:
                logger.warning(
                    f"Keyword-fix pass still missing: {still_missing}"
                )
            else:
                logger.info(
                    f"Keyword-fix pass inserted missing keywords: {missing}"
                )
            return fixed, extra_tokens
        except Exception as e:
            logger.warning(f"Keyword-fix pass failed (non-fatal): {e}")
            return content_html, 0

    @classmethod
    def _enforce_word_count_limit(cls, content_html, word_count, outline=None):
        """Cap content at the user-selected word count range's upper bound,
        preserving the conclusion so the article never ends mid-thought.

        Behaviour:
        1. A small overshoot (up to 15% over the upper bound) is allowed so
           we don't strip the conclusion just because the article is a few
           paragraphs long. A complete-but-slightly-long article reads
           better than a truncated one that matches the target exactly.
        2. If `outline` is provided (bulk-upload path), trim *within* sections
           so every planned section heading is preserved in the output.
           This stops middle sections from being silently dropped when the
           generated article overshoots the word cap.
        3. Otherwise (single-article path), identify the "conclusion section"
           (the last <h1>/<h2>/<h3> and everything after it) and always keep
           it. Body blocks before the conclusion are included greedily in
           document order until the remaining budget is used up.
        4. If no heading exists, we fall back to preserving the final block
           so the article still has a proper closing paragraph.
        """
        if not content_html or not word_count or word_count <= 0:
            return content_html

        upper = cls._upper_word_limit(word_count)
        plain_text = re.sub(r'<[^>]+>', ' ', content_html)
        current_words = len(plain_text.split())

        # Allow a modest overshoot (15%) — prefer a complete article with a
        # real conclusion over hitting the word cap exactly.
        soft_cap = int(upper * 1.15)
        if current_words <= soft_cap:
            return content_html

        # Outline-aware path: keep every planned section heading, trim
        # trailing body blocks within sections instead. Falls through to the
        # legacy algorithm if the helper can't run (no headings detected).
        if outline:
            outline_aware = cls._enforce_word_count_outline_aware(
                content_html, word_count, upper, current_words
            )
            if outline_aware is not None:
                return outline_aware

        # Split by top-level block elements.
        block_pattern = re.compile(
            r'<(h[1-6]|p|ul|ol|blockquote|pre|table|div|figure)\b[^>]*>.*?</\1>',
            re.IGNORECASE | re.DOTALL
        )
        matches = list(block_pattern.finditer(content_html))
        if not matches:
            return content_html

        # Locate the conclusion section: last <h1>/<h2>/<h3> and everything
        # after it. This keeps the article's closing thoughts intact even
        # when we have to drop earlier body paragraphs.
        heading_re = re.compile(r'^<h[1-3]\b', re.IGNORECASE)
        conclusion_start = None
        for i in range(len(matches) - 1, -1, -1):
            if heading_re.match(matches[i].group(0)):
                conclusion_start = i
                break

        if conclusion_start is None:
            # No heading in the doc — treat the final block as the closing.
            conclusion_blocks = [matches[-1].group(0)]
            body_matches = matches[:-1]
        else:
            conclusion_blocks = [m.group(0) for m in matches[conclusion_start:]]
            body_matches = matches[:conclusion_start]

        conclusion_words = sum(
            len(re.sub(r'<[^>]+>', ' ', b).split()) for b in conclusion_blocks
        )
        # Reserve budget for the conclusion; never let the conclusion take
        # more than half the article, otherwise a bloated closing would
        # crowd out the body entirely.
        body_budget = max(upper - conclusion_words, int(upper * 0.5))

        kept_body = []
        kept_words = 0
        for m in body_matches:
            block_html = m.group(0)
            block_words = len(re.sub(r'<[^>]+>', ' ', block_html).split())
            if kept_body and kept_words + block_words > body_budget:
                break
            kept_body.append(block_html)
            kept_words += block_words
            if kept_words >= body_budget:
                break

        kept_parts = kept_body + conclusion_blocks
        if not kept_parts:
            return content_html
        truncated = '\n'.join(kept_parts)
        final_words = kept_words + conclusion_words
        logger.info(
            f"Enforced word count limit: {current_words} -> {final_words} words "
            f"(target {word_count}, upper {upper}, conclusion preserved)"
        )
        return truncated

    @classmethod
    def _enforce_word_count_outline_aware(cls, content_html, word_count, upper, current_words):
        # Trim content while preserving every section heading. Returns the
        # trimmed HTML, or None if outline-aware trimming can't run (no
        # headings detected) — caller falls back to the legacy trim.
        block_pattern = re.compile(
            r'<(h[1-6]|p|ul|ol|blockquote|pre|table|div|figure)\b[^>]*>.*?</\1>',
            re.IGNORECASE | re.DOTALL
        )
        matches = list(block_pattern.finditer(content_html))
        if not matches:
            return None

        heading_re = re.compile(r'^<h[1-3]\b', re.IGNORECASE)

        # Group blocks into sections (each section = heading + following
        # body blocks). Anything before the first heading becomes a "lead"
        # section with heading=None.
        sections = []
        current = {"heading": None, "blocks": []}
        for m in matches:
            block = m.group(0)
            if heading_re.match(block):
                if current["heading"] is not None or current["blocks"]:
                    sections.append(current)
                current = {"heading": block, "blocks": []}
            else:
                current["blocks"].append(block)
        if current["heading"] is not None or current["blocks"]:
            sections.append(current)

        if not any(s["heading"] for s in sections):
            return None

        def words_of(block):
            return len(re.sub(r'<[^>]+>', ' ', block).split())

        for s in sections:
            s["heading_words"] = words_of(s["heading"]) if s["heading"] else 0
            s["block_words"] = [words_of(b) for b in s["blocks"]]

        total_words = sum(
            s["heading_words"] + sum(s["block_words"]) for s in sections
        )
        target = int(upper * 1.05)

        # Greedy trim: drop the trailing body block of whichever section
        # has the most trimmable content (>1 body block first, so we don't
        # gut shorter sections). Section headings are never dropped.
        while total_words > target:
            best_i = -1
            best_words = 0
            for i, s in enumerate(sections):
                if len(s["blocks"]) > 1:
                    last = s["block_words"][-1]
                    if last > best_words:
                        best_words = last
                        best_i = i
            # Fallback: if every section is down to one body block, keep
            # trimming the longest trailing block (heading still preserved).
            if best_i < 0:
                for i, s in enumerate(sections):
                    if s["blocks"]:
                        last = s["block_words"][-1]
                        if last > best_words:
                            best_words = last
                            best_i = i
            if best_i < 0:
                break

            sections[best_i]["blocks"].pop()
            sections[best_i]["block_words"].pop()
            total_words -= best_words

        parts = []
        for s in sections:
            if s["heading"]:
                parts.append(s["heading"])
            parts.extend(s["blocks"])

        if not parts:
            return None

        sections_with_heading = sum(1 for s in sections if s["heading"])
        logger.info(
            f"Enforced word count limit (outline-aware): {current_words} -> "
            f"{total_words} words (target {word_count}, upper {upper}, "
            f"{sections_with_heading} section heading(s) preserved)"
        )
        return '\n'.join(parts)

    def _continue_truncated_content(self, truncated_html):
        """
        When content generation is truncated (stop_reason='max_tokens'),
        make a small follow-up API call to complete the last incomplete
        sentence/paragraph and close any open HTML tags.

        This is a lightweight call (~500-1000 tokens) that only finishes
        what was cut off — it does NOT regenerate or add new sections.

        Args:
            truncated_html: The incomplete HTML content

        Returns:
            tuple: (complete_html, extra_completion_tokens)
        """
        # Send only the last 2000 chars as context — enough for Claude to
        # understand what needs to be completed
        context_tail = truncated_html[-2000:] if len(truncated_html) > 2000 else truncated_html

        try:
            continuation_response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                temperature=0.7,
                system=(
                    "You are completing an HTML article that was cut off mid-generation. "
                    "Your job is to ONLY finish the last incomplete sentence or paragraph "
                    "and close any open HTML tags properly. "
                    "Do NOT add new sections, headings, or content beyond completing "
                    "what was already started. Keep it brief and natural. "
                    "Return ONLY the continuation HTML (not the full article)."
                ),
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "The following HTML article was cut off. "
                            "Complete ONLY the last incomplete part and close "
                            "any open tags:\n\n"
                            f"...{context_tail}"
                        )
                    }
                ]
            )

            continuation_text = continuation_response.content[0].text.strip()
            extra_tokens = continuation_response.usage.output_tokens

            # Merge: append continuation to truncated content
            complete_html = truncated_html + continuation_text

            logger.info(
                f"Auto-continuation successful: added {len(continuation_text)} chars, "
                f"{extra_tokens} extra tokens"
            )
            return complete_html, extra_tokens

        except Exception as e:
            logger.warning(f"Auto-continuation failed (non-fatal): {e}")
            # Return original truncated content if continuation fails —
            # better to have truncated content than no content
            return truncated_html, 0

    @staticmethod
    def _extract_heading_titles(html_content):
        """Return a list of (level, normalized_text) for every heading in
        the HTML. Used to detect which planned outline sections actually made
        it into the generated content.
        """
        if not html_content:
            return []
        heading_pattern = re.compile(
            r'<h([1-6])\b[^>]*>(.*?)</h\1>',
            re.IGNORECASE | re.DOTALL
        )
        out = []
        for m in heading_pattern.finditer(html_content):
            level = int(m.group(1))
            text = re.sub(r'<[^>]+>', '', m.group(2))
            text = re.sub(r'\s+', ' ', text).strip().lower()
            if text:
                out.append((level, text))
        return out

    @classmethod
    def _normalize_heading(cls, text):
        text = re.sub(r'<[^>]+>', '', text or '')
        text = re.sub(r'[^a-z0-9\s]', ' ', text.lower())
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    @classmethod
    def _heading_matches(cls, planned_title, generated_heading_text):
        """Loose match: planned title and generated heading share enough
        meaningful words. Catches small phrasing tweaks (e.g. planned
        "Benefits of Solar Power" vs generated "Key Benefits of Solar").
        """
        a = cls._normalize_heading(planned_title)
        b = cls._normalize_heading(generated_heading_text)
        if not a or not b:
            return False
        if a == b or a in b or b in a:
            return True
        stop = {
            'the', 'a', 'an', 'and', 'or', 'of', 'to', 'for', 'in', 'on',
            'with', 'by', 'is', 'are', 'how', 'what', 'why', 'your', 'you'
        }
        a_words = {w for w in a.split() if w not in stop and len(w) > 2}
        b_words = {w for w in b.split() if w not in stop and len(w) > 2}
        if not a_words:
            return False
        overlap = a_words & b_words
        return len(overlap) >= max(2, int(len(a_words) * 0.6))

    def _complete_missing_outline_sections(self, content_html, outline, params):
        """Detect outline sections that didn't make it into the generated
        content and ask Claude to write ONLY those sections, then merge
        them back in.

        Fixes a recurring issue where the outline-driven path silently
        skipped sections — typically when Claude ran long earlier and
        truncated before reaching the trailing sections, or when the model
        merged two planned subheadings into one.

        Args:
            content_html: HTML returned by the main generation call.
            outline: List of outline section dicts (type/title/key_points/
                estimated_words).
            params: The original generation params (used to keep tone /
                style / language consistent in the backfill call).

        Returns:
            tuple: (merged_html, extra_completion_tokens)
        """
        if not outline or not content_html:
            return content_html, 0

        generated_headings = self._extract_heading_titles(content_html)
        if not generated_headings:
            # No headings in output at all — leave untouched; the main
            # generator already returned something the caller will trim.
            return content_html, 0

        missing = []
        for section in outline:
            planned_title = (section.get('title') or '').strip()
            if not planned_title:
                continue
            if any(self._heading_matches(planned_title, gh_text)
                   for _, gh_text in generated_headings):
                continue
            missing.append(section)

        if not missing:
            return content_html, 0

        logger.warning(
            f"Outline path: {len(missing)} planned section(s) missing from "
            f"generated content — backfilling: "
            f"{[s.get('title') for s in missing]}"
        )

        outline_text = ""
        target_words = 0
        for section in missing:
            section_type = section.get('type', 'h2')
            section_title = section.get('title', '')
            key_points = section.get('key_points', [])
            est_words = int(section.get('estimated_words', 150) or 150)
            target_words += est_words
            indent = "  " if section_type == 'h3' else ""
            outline_text += (
                f"\n{indent}{section_type.upper()}: {section_title} "
                f"(~{est_words} words)\n"
            )
            for point in key_points:
                outline_text += f"{indent}  - {point}\n"

        tone = params.get('tone', 'professional')
        style = params.get('style', 'informative')
        audience = params.get('audience', 'general')
        target_language = params.get('target_language', 'us_english')
        language_display = target_language.replace('_', ' ').title()

        system_prompt = (
            "You are continuing an in-progress HTML article. Write ONLY the "
            "missing sections requested below, using proper HTML semantic "
            "tags (<h2>, <h3>, <p>, <ul>, <ol>, <li>, <strong>). "
            "Do NOT repeat sections that already exist. Do NOT add a new "
            "conclusion / wrap-up — the article already has one. Return "
            "ONLY the HTML for the requested sections, no preamble, no "
            "markdown, no code fences."
        )

        user_prompt = (
            f"Write ONLY these missing sections of the article, in order:\n"
            f"{outline_text}\n"
            f"Tone: {tone}\n"
            f"Style: {style}\n"
            f"Target audience: {audience}\n"
            f"Language: {language_display}\n\n"
            f"Each section should hit its target word count. Cover the "
            f"listed key points. Use <ul>/<ol> for any enumerations of 3+ "
            f"parallel items.\n\n"
            f"Return ONLY the new HTML."
        )

        max_tokens = self._calculate_max_tokens(max(target_words, 800))

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=0.7,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            new_html = response.content[0].text
            extra_tokens = response.usage.output_tokens
            new_html = self._sanitize_html_response(new_html)
            new_html = self._convert_markdown_to_html(new_html)

            # Insert before the conclusion if we can identify one;
            # otherwise append at the end of the article.
            conclusion_re = re.compile(
                r'<h[1-3]\b[^>]*>\s*[^<]*\b('
                r'conclusion|final\s+verdict|key\s+takeaways|summary|'
                r'wrap[\s\-]?up|closing\s+thoughts|in\s+conclusion|'
                r'final\s+thoughts'
                r')\b',
                re.IGNORECASE
            )
            m = conclusion_re.search(content_html)
            if m:
                merged = (
                    content_html[:m.start()]
                    + new_html.strip()
                    + '\n'
                    + content_html[m.start():]
                )
            else:
                merged = content_html.rstrip() + '\n' + new_html.strip()

            logger.info(
                f"Backfilled {len(missing)} missing outline section(s), "
                f"{extra_tokens} extra tokens"
            )
            return merged, extra_tokens
        except Exception as e:
            logger.warning(
                f"Missing-section backfill failed (non-fatal): {e}"
            )
            return content_html, 0

    @staticmethod
    def _deduplicate_internal_links(html_content):
        """
        Remove duplicate internal link URLs from generated content.
        Keeps only the FIRST occurrence of each URL and converts subsequent
        duplicates to plain text (anchor text preserved, link removed).
        This is important for SEO — repeated identical links hurt rankings.
        """
        seen_urls = set()

        def replace_duplicate(match):
            full_tag = match.group(0)
            url = match.group(1)
            anchor_text = match.group(2)

            # Normalize URL for comparison (lowercase, strip trailing slash)
            normalized_url = url.lower().rstrip('/')

            if normalized_url in seen_urls:
                # Duplicate — return just the anchor text without the link
                return anchor_text
            else:
                seen_urls.add(normalized_url)
                return full_tag

        # Match <a href="...">text</a> patterns
        import re
        deduped = re.sub(
            r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
            replace_duplicate,
            html_content,
            flags=re.IGNORECASE | re.DOTALL
        )
        return deduped

    @staticmethod
    def _convert_markdown_to_html(content):
        """
        Convert any remaining markdown syntax in the generated content to proper HTML.
        Handles: headings (# ## ###), tables (| pipe syntax |), bold (**), italic (*).
        This ensures the editor always receives clean HTML regardless of LLM output format.
        """
        import re

        # Convert markdown headings to HTML headings
        # Must process ### before ## before # to avoid partial matches
        content = re.sub(r'^###\s+(.+?)$', r'<h3>\1</h3>', content, flags=re.MULTILINE)
        content = re.sub(r'^##\s+(.+?)$', r'<h2>\1</h2>', content, flags=re.MULTILINE)
        content = re.sub(r'^#\s+(.+?)$', r'<h1>\1</h1>', content, flags=re.MULTILINE)

        # Convert markdown bold **text** to <strong>text</strong>
        # (but not inside already-converted HTML tags)
        content = re.sub(r'\*\*([^*]+?)\*\*', r'<strong>\1</strong>', content)

        # Convert markdown tables to HTML tables
        lines = content.split('\n')
        result_lines = []
        table_lines = []
        in_table = False

        for line in lines:
            stripped = line.strip()
            # Detect table row: starts and ends with |
            if stripped.startswith('|') and stripped.endswith('|'):
                # Skip separator rows like |---|---|
                if re.match(r'^\|[\s\-:|]+\|$', stripped):
                    if not in_table:
                        in_table = True
                    continue
                table_lines.append(stripped)
                if not in_table:
                    in_table = True
            else:
                # End of table — convert collected rows
                if in_table and table_lines:
                    result_lines.append(ClaudeContentGenerator._table_lines_to_html(table_lines))
                    table_lines = []
                    in_table = False
                result_lines.append(line)

        # Handle table at end of content
        if in_table and table_lines:
            result_lines.append(ClaudeContentGenerator._table_lines_to_html(table_lines))

        return '\n'.join(result_lines)

    @staticmethod
    def _table_lines_to_html(table_lines):
        """Convert a list of markdown table rows to an HTML table."""
        if not table_lines:
            return ''

        html = '<table><thead><tr>'
        # First row is header
        header_cells = [cell.strip() for cell in table_lines[0].split('|')[1:-1]]
        for cell in header_cells:
            # Remove bold markdown from headers
            cell = re.sub(r'\*\*(.+?)\*\*', r'\1', cell)
            html += f'<th>{cell}</th>'
        html += '</tr></thead><tbody>'

        # Remaining rows are data
        for row in table_lines[1:]:
            cells = [cell.strip() for cell in row.split('|')[1:-1]]
            html += '<tr>'
            for cell in cells:
                html += f'<td>{cell}</td>'
            html += '</tr>'

        html += '</tbody></table>'
        return html

    def _filter_chunks_by_keywords(self, title, keywords, reference_docs):
        """
        Pre-filter document chunks locally using keyword matching.
        Returns only chunks that contain at least one relevant keyword.
        This runs in Python with zero API cost.
        """
        from domains.models import ReferenceDocumentChunk

        # Skip documents still being processed (async extraction not yet complete)
        reference_docs = [
            doc for doc in reference_docs
            if getattr(doc, 'extraction_status', 'completed') == 'completed'
        ]

        # Build search terms from title and keywords
        # Include both exact phrases and individual words for broader matching
        search_terms = []
        if title:
            # Add full title as a phrase match (lowered)
            search_terms.append(title.lower().strip())
            # Extract meaningful words from title (skip short/common words)
            search_terms.extend([
                word.lower() for word in title.split()
                if len(word) > 3
            ])
        if keywords:
            # Split comma-separated keywords and their individual words
            for kw in keywords.split(','):
                kw = kw.strip().lower()
                if kw:
                    search_terms.append(kw)
                    search_terms.extend([
                        word for word in kw.split()
                        if len(word) > 3
                    ])

        # Always include high-value generic terms that capture brand context
        # These ensure brand voice, guidelines, and differentiators are not missed
        brand_context_terms = [
            'brand', 'guideline', 'tone of voice', 'voice', 'style guide',
            'usp', 'unique selling', 'differentiator', 'value proposition',
            'tagline', 'mission', 'vision', 'about us', 'why choose',
            'testimonial', 'review', 'customer feedback',
        ]
        search_terms.extend(brand_context_terms)

        # Remove duplicates
        search_terms = list(set(search_terms))

        if not search_terms:
            return []

        # Get all chunks for these documents
        doc_ids = [doc.id for doc in reference_docs]
        all_chunks = ReferenceDocumentChunk.objects.filter(
            document_id__in=doc_ids
        ).select_related('document').order_by('document', 'chunk_index')

        # Score each chunk by how many keywords it contains
        scored_chunks = []
        for chunk in all_chunks:
            chunk_lower = chunk.chunk_text.lower()
            score = sum(1 for term in search_terms if term in chunk_lower)
            if score > 0:
                scored_chunks.append((score, chunk))

        # Sort by score (highest first) and limit to top chunks
        scored_chunks.sort(key=lambda x: x[0], reverse=True)

        # Dynamic cap: scale with total document size for large reference sets
        # Base: 50K chars. For large docs, allow up to 80K to capture more relevant content.
        # This adds marginal API cost (~$0.02) but significantly improves quality
        # for large reference documents.
        total_doc_chars = sum(len(c.chunk_text) for _, c in scored_chunks)
        max_chars = min(80000, max(50000, total_doc_chars // 10))

        selected_chunks = []
        total_chars = 0
        for score, chunk in scored_chunks:
            if total_chars + len(chunk.chunk_text) > max_chars:
                break
            selected_chunks.append(chunk)
            total_chars += len(chunk.chunk_text)

        # Guarantee: Always include the FIRST chunk of each document
        # (often contains intro, brand overview, key messaging — valuable context
        # that keyword matching might miss)
        first_chunk_ids = set(c.id for c in selected_chunks)
        for doc in reference_docs:
            try:
                from domains.models import ReferenceDocumentChunk
                first_chunk = ReferenceDocumentChunk.objects.filter(
                    document=doc, chunk_index=0
                ).first()
                if first_chunk and first_chunk.id not in first_chunk_ids:
                    # Add first chunk if we have room (use 10K extra budget for this)
                    if total_chars + len(first_chunk.chunk_text) <= max_chars + 10000:
                        selected_chunks.append(first_chunk)
                        total_chars += len(first_chunk.chunk_text)
                        first_chunk_ids.add(first_chunk.id)
            except Exception:
                continue

        return selected_chunks

    def match_reference_content(self, title, keywords, article_type, reference_docs):
        """
        Check if any reference repository documents contain content relevant
        to the given title and keywords. Uses keyword-based chunk filtering
        to efficiently search entire documents (not just the first 30K chars).

        Args:
            title (str): Article title
            keywords (str): Target keywords (comma-separated)
            article_type (str): Type of article
            reference_docs (QuerySet): ReferenceDocument objects with extracted_text

        Returns:
            str: Relevant excerpts from matched documents, or empty string
        """

        # Step 1: Try keyword-based chunk filtering (covers entire document)
        filtered_chunks = self._filter_chunks_by_keywords(title, keywords, reference_docs)

        if filtered_chunks:
            # Build docs_text from matched chunks
            docs_text = ""
            for chunk in filtered_chunks:
                doc_name = chunk.document.file_name
                doc_type = chunk.document.file_type.upper()
                docs_text += (
                    f"\n{'=' * 50}\n"
                    f"DOCUMENT: {doc_name} (Type: {doc_type}) - Section {chunk.chunk_index + 1}\n"
                    f"{'=' * 50}\n"
                    f"{chunk.chunk_text}\n"
                )
            logger.info(
                f"[REF-MATCH] Chunk filtering: {len(filtered_chunks)} relevant chunks "
                f"({len(docs_text)} chars) from keyword pre-filter"
            )
        else:
            # Fallback: use original truncation approach for documents without chunks
            logger.info("[REF-MATCH] No chunks found, falling back to truncated text")
            docs_text = ""
            for doc in reference_docs:
                if not doc.extracted_text or not doc.extracted_text.strip():
                    continue
                text = doc.extracted_text[:30000]
                docs_text += (
                    f"\n{'=' * 50}\n"
                    f"DOCUMENT: {doc.file_name} (Type: {doc.file_type.upper()})\n"
                    f"{'=' * 50}\n"
                    f"{text}\n"
                )

        if not docs_text.strip():
            return ''

        # Step 2: Send pre-filtered content to Claude for final extraction
        system_prompt = """You are a content research assistant. Your task is to analyze brand reference documents and find content that is relevant to a specific article topic.

INSTRUCTIONS:
1. Read each reference document carefully
2. For each document, check if it contains information relevant to the given article title and keywords
3. Extract TWO types of content:
   a) DIRECTLY relevant content: paragraphs about the article topic (product info, stats, facts, pricing, features)
   b) BRAND CONTEXT content: brand voice guidelines, tone instructions, USPs, taglines, differentiators, customer testimonials that should inform how the article is written
4. Preserve exact brand names, product names, statistics, facts, and specific terminology
5. Keep total extracted content under 4000 words
6. Tag each excerpt with its source document name and category (DIRECT or BRAND_CONTEXT)

OUTPUT FORMAT:
If relevant content is found:
---
[Source: {document_name}] [DIRECT]
{extracted relevant paragraph or section}

[Source: {document_name}] [BRAND_CONTEXT]
{brand voice, USP, or style information}
---

If NO document contains relevant content:
NO_RELEVANT_CONTENT

IMPORTANT:
- Extract BOTH topic-specific content AND brand personality/voice content
- Only extract content that is useful for writing the given article
- Do NOT summarize - preserve the original wording for brand accuracy
- Do NOT add your own commentary
- Brand guidelines, tone of voice, and USPs are ALWAYS relevant regardless of article topic"""

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
                max_tokens=4096,  # Increased from 2048 to allow richer reference extraction
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

        # Dynamic max_tokens based on requested word count
        word_count = params.get('word_count', 1500)
        max_tokens = self._calculate_max_tokens(word_count)

        # Call Claude API
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
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
            total_prompt_tokens = response.usage.input_tokens
            total_completion_tokens = response.usage.output_tokens

            # Detect truncation: if Claude stopped due to token limit, content is incomplete
            # Auto-continue with a small follow-up call to finish the last paragraph
            if response.stop_reason == 'max_tokens':
                logger.warning(
                    f"Content truncated for word_count={word_count}: "
                    f"stop_reason=max_tokens, max_tokens={max_tokens}. "
                    f"Attempting auto-continuation..."
                )
                content_html, extra_tokens = self._continue_truncated_content(content_html)
                total_completion_tokens += extra_tokens

            # Post-processing: strip code fences / decode entities so the
            # editor renders real HTML tags (not literal <h2> text).
            content_html = self._sanitize_html_response(content_html)

            # Post-processing: convert any remaining markdown to HTML
            content_html = self._convert_markdown_to_html(content_html)

            # Post-processing: deduplicate internal links (SEO best practice)
            content_html = self._deduplicate_internal_links(content_html)

            # Post-processing: cheap regex promotion of sequential bold
            # lead-in paragraphs into <ul>. Runs every time (no API cost),
            # independent of the list-count safety net.
            content_html, _promoted = self._promote_bold_leadin_paragraphs_to_list(
                content_html
            )

            # Post-processing: detect missing keywords and weave them in.
            # Runs BEFORE the word-count enforcement so any content the fix
            # pass adds is still capped by the final truncation step.
            missing = self._missing_keywords(content_html, params.get('keywords', ''))
            if missing:
                logger.info(
                    f"Missing keywords detected after generation: {missing}. "
                    f"Running keyword-fix pass."
                )
                content_html, extra_tokens = self._fix_missing_keywords(
                    content_html, missing, word_count
                )
                total_completion_tokens += extra_tokens

            # Did the client ask for lists or tables in their instructions?
            # We check Additional Instructions + Key Messages for everyday
            # phrasings ("table", "list", "points", "topics", "categories",
            # "difference", "items", "comparison", "menus", "step-by-step",
            # "pros and cons", …) so the safety nets below honour those
            # requests even when the article title/keywords don't trigger
            # the topic-intent detectors.
            user_wants_list = self._user_requested_list_format(
                params.get('additional_instructions', ''),
                params.get('key_messages', ''),
            )
            user_wants_table = self._user_requested_table_format(
                params.get('additional_instructions', ''),
                params.get('key_messages', ''),
            )

            # Safety net 1 — Lists.
            # If the article ended up as pure paragraphs (or fewer lists than
            # the word-count threshold expects, or fewer than the client's
            # explicit request expects), convert prose enumerations into
            # <ul>/<ol> via a focused fix pass.
            list_count_before = self._count_lists(content_html)
            required_lists = self._required_list_count(
                word_count, user_requested_list=user_wants_list
            )
            if list_count_before < required_lists:
                content_html, extra_tokens = self._ensure_lists_in_content(
                    content_html, word_count, user_requested_list=user_wants_list
                )
                total_completion_tokens += extra_tokens
            logger.info(
                f"Lists in final content: {self._count_lists(content_html)} "
                f"(required {required_lists})"
            )

            # Safety net 2 — Tables.
            # When the client clearly asked for a table (e.g. "include a
            # comparison table", "show the differences", "pros and cons")
            # but Claude returned no <table> at all, run a focused fix pass
            # that converts the most tabular section of the article into a
            # real HTML <table> without inventing new facts.
            if user_wants_table and self._count_tables(content_html) == 0:
                logger.info(
                    "Client asked for a table but generated content has none; "
                    "running table-fix pass."
                )
                content_html, extra_tokens = self._ensure_table_in_content(
                    content_html, word_count
                )
                total_completion_tokens += extra_tokens

            # Post-processing: enforce the word count range the user selected
            content_html = self._enforce_word_count_limit(content_html, word_count)

            # Calculate generation time
            generation_time = time.time() - start_time

            # Calculate actual word count
            plain_text = re.sub(r'<[^>]+>', ' ', content_html)
            actual_word_count = len(plain_text.split())

            return {
                'content_html': content_html,
                'generation_time_seconds': round(generation_time, 2),
                'prompt_tokens': total_prompt_tokens,
                'completion_tokens': total_completion_tokens,
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
- Adapts structure and formatting to the content's natural flow — avoid rigid, repetitive section patterns
- Prioritizes any user-provided formatting or structural preferences over defaults
- Returns ONLY the HTML content (no markdown, no code blocks)

LIST FORMATTING — USE <ul> / <ol> WHEREVER THEY IMPROVE SCANNABILITY:
- Convert any enumeration of 3+ parallel items (features, benefits, use cases, tips, pros, cons, types, options, examples, reasons, tools, platforms, key takeaways) into a <ul> — do NOT leave them as prose or comma-separated sentences.
- Use <ol> for any sequence where order matters (step-by-step, ranked lists, process flows, numbered best practices, timelines).
- Every long-form article (500+ words) MUST contain at least one <ul> or <ol> block. Articles 1000+ words should contain two or more list blocks spread across different sections.
- Inside each <li>, use <strong> for the lead-in term followed by a short explanation. Example: <li><strong>Scalability:</strong> handles traffic spikes without rewriting code.</li>
- Do NOT use lists for only 1-2 items; write those as prose instead.
- Do NOT nest lists more than one level deep."""

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
        keywords_block = self._format_keywords_for_prompt(keywords, word_count)
        user_prompt = f"""Write {article_description} with the following specifications:

**Title:** {title}

{keywords_block}
**Target Market:**
- Country: {country_display}
- Language: {language_display}

**Content Specifications:**
- Tone: {tone}
- Style: {style}
- Goal: {goal}
- Target Audience: {audience}
- Content Depth: {depth}
- Target Word Count: {self._lower_word_limit(word_count)}-{self._upper_word_limit(word_count)} words (HARD LIMIT: the final article MUST be between {self._lower_word_limit(word_count)} and {self._upper_word_limit(word_count)} words — do NOT exceed {self._upper_word_limit(word_count)} words under any circumstance)

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

        # additional_instructions are added at the end of the prompt with priority framing
        # (see below, after structure guidelines) so they override defaults

        # Add references if provided (with fetched content when available)
        if references and len(references) > 0:
            user_prompt += """
**Reference Materials (research notes — read for FACTS, do NOT use as a template):**
The content below is research material you have read. Treat it the way a journalist treats source interviews: extract facts, statistics, and data points, then write the article in your own original voice and structure. Do NOT base the article's wording, sentence flow, or section order on the references.
"""
            for i, ref in enumerate(references, 1):
                ref_type = ref.get('type', 'article').capitalize()
                ref_url = ref.get('url', '')
                ref_desc = ref.get('description', '')
                fetched_content = ref.get('fetched_content', '')
                fetched_title = ref.get('fetched_title', '')

                user_prompt += f"\n--- Reference {i} ---"
                user_prompt += f"\n[{ref_type}] {ref_url}"
                if fetched_title:
                    user_prompt += f"\nTitle: {fetched_title}"
                if ref_desc:
                    user_prompt += f"\nDescription: {ref_desc}"
                if fetched_content:
                    user_prompt += f"\nExtracted Content:\n{fetched_content}"
                else:
                    user_prompt += f"\n[NOTE: Content could not be fetched from this URL. Do NOT guess what this page contains.]"

            user_prompt += """

CRITICAL RULES for using references — STRICT ANTI-DUPLICATION:
- Use ONLY facts, statistics, prices, and examples that appear in the extracted content above. Do NOT fabricate.
- Match the currency, units, and cultural context of the target country specified above.
- If a reference could not be fetched, ignore it entirely — do not guess its content.
- ORIGINALITY IS MANDATORY. The final article MUST be substantially different from every reference in:
  (a) Wording — never copy any sentence or 6+ consecutive words verbatim from a reference. Rephrase every fact in your own voice.
  (b) Section structure — choose your OWN headings and section order. Do NOT mirror a reference's outline, headings, or paragraph order.
  (c) Examples and analogies — invent your own framing, transitions, and examples; do not reuse the references' phrasings, openings, or closings.
  (d) Sentence flow — vary sentence length, paragraph rhythm, and explanation style versus the references.
- When multiple references are provided, SYNTHESISE across them — do not pattern your article after a single source.
- If only one reference is provided, treat it strictly as a fact-source, NEVER as a writing template. The reader of your article must not be able to recognise which page you read.
- Cite or reference the source material where appropriate (e.g. "according to [source]"), but the surrounding prose must be entirely your own.
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
**Suggested Structure (adapt based on content needs and any additional instructions below):**
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
            user_prompt += """- Start with a compelling introduction
- Organize the body into logical sections using h2 headings
- Use subsections (h3) where they add clarity
- Vary the structure: mix paragraphs, <ul> lists, and explanatory blocks as appropriate
- Use <ul> for feature/benefit/tip/type/option enumerations (3+ parallel items)
- Use <ol> for step-by-step instructions, ranked items, or ordered processes
- End with a conclusion or key takeaways (a short <ul> of takeaways works well)
"""

        # Detect list / table requests inside the client's free-text fields
        # (Additional Instructions + Key Messages). Catches everyday phrasings
        # such as "table", "list", "points", "topics", "categories",
        # "difference", "items", "comparison", "menus", "step-by-step",
        # "pros and cons", and similar. When found we (a) force the matching
        # REQUIRED structure block into the prompt below and (b) reinforce
        # the request directly under the PRIORITY INSTRUCTIONS so it isn't
        # lost in the surrounding context.
        user_wants_list = self._user_requested_list_format(
            additional_instructions, key_messages
        )
        user_wants_table = self._user_requested_table_format(
            additional_instructions, key_messages
        )

        # Topic-aware structural hints (comparison tables, listing formats,
        # SEO structure checklist). Added before the priority instructions so
        # user-provided additional_instructions still override the defaults.
        structure_hints = self._format_structure_hints(
            title, keywords, article_type, word_count,
            user_requested_list=user_wants_list,
            user_requested_table=user_wants_table,
        )
        if structure_hints:
            user_prompt += "\n" + structure_hints + "\n"

        if additional_instructions:
            user_prompt += f"""
**PRIORITY INSTRUCTIONS (from content creator — follow these over the suggested structure above):**
The following instructions take precedence over the default structure guidelines. If these conflict with the structure suggestions, follow these instructions:
{additional_instructions}
"""
            # Short structural reinforcement so brief client prompts like
            # "use a list", "include a table", "list the topics", or
            # "show the differences" can't be lost in the wider context.
            explicit_reinforcement = []
            if user_wants_list:
                explicit_reinforcement.append(
                    "- The instructions above ask for list-style output (e.g. list / points / topics / categories / items / menus / steps) — your final HTML MUST contain at least one <ul> or <ol> block. Do NOT return only paragraphs."
                )
            if user_wants_table:
                explicit_reinforcement.append(
                    "- The instructions above ask for a table (e.g. table / comparison / difference / pros and cons / vs) — your final HTML MUST contain at least one real <table> block with <thead>/<tbody>. Do NOT skip it because prose works fine; tabular data is what was asked for."
                )
            if explicit_reinforcement:
                user_prompt += "\n" + "\n".join(explicit_reinforcement) + "\n"

        lower_limit = self._lower_word_limit(word_count)
        upper_limit = self._upper_word_limit(word_count)
        target_mid = (lower_limit + upper_limit) // 2

        user_prompt += f"""
**IMPORTANT - Content Completion Rule:**
- Target approximately {target_mid} words so you stay comfortably within the {lower_limit}-{upper_limit} range. Plan sections to fit that budget.
- Every target keyword listed above MUST appear at least once in the final HTML — spread them across different sections, not clustered together.
- Always complete every sentence and paragraph fully. If you are approaching your output limit, wrap up the current section with a proper conclusion rather than starting a new section.
- Never end mid-sentence or leave content incomplete. Every article MUST end with a proper closing section (e.g. \"Conclusion\", \"Final Verdict\", or \"Key Takeaways\") and valid closing HTML tags.
- Return well-formed HTML only. No markdown syntax (no `#` headings, no `|` tables, no ``` code fences). Use real <h2>/<h3>/<table>/<ul>/<ol>/<strong> tags.

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

        # For section regeneration, use word_count if available, else default
        section_word_count = params.get('word_count', 1500)
        max_tokens = self._calculate_max_tokens(section_word_count, is_section=True)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
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

    def generate_outline(self, params, extended_tokens=False):
        """
        Generate a content outline based on provided parameters

        Args:
            params (dict): Generation parameters (same as generate_content)
            extended_tokens (bool): When True, requests a doubled token budget.
                Used by the bulk-upload validation-retry path so an outline
                that was truncated on the first attempt has enough headroom
                to come back complete.

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

        keywords_block = self._format_keywords_for_prompt(keywords, word_count)
        user_prompt = f"""Create a detailed outline for a {article_description} with these specifications:

**Title:** {title}
{keywords_block}**Target Market:** {country_display} ({language_display})
**Tone:** {tone}
**Style:** {style}
**Target Audience:** {audience}
**Target Word Count:** {self._lower_word_limit(word_count)}-{self._upper_word_limit(word_count)} words (total across all sections must stay within this range)

OUTLINE KEYWORD DISTRIBUTION:
- Every target keyword listed above MUST be represented in the outline.
- Each keyword should appear in at least one section title OR in the key_points of at least one section.
- The primary (first) keyword should appear in the introduction section and at least one body section.
- Do not silently drop secondary keywords — plan a section or key_point where each fits naturally.
"""

        if key_messages:
            user_prompt += f"""
**Key Messages to Include:** {key_messages}
"""

        if topics_to_avoid:
            user_prompt += f"""
**Topics to Avoid:** {topics_to_avoid}
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

        # Add fetched reference URL content if available so the outline
        # structure is shaped around what the reference URLs actually contain.
        references = params.get('references', [])
        if references and len(references) > 0:
            user_prompt += """
**Reference URLs (facts source ONLY — do NOT copy the references' outline):**
The content below was extracted from the reference URLs the user provided.

- Use the references as a FACTS SOURCE: which data points, statistics, and examples are available to cite.
- Do NOT replicate the references' section structure, heading wording, or order. Design an ORIGINAL outline tailored to the title, keywords, and target audience.
- Section headings must be written in your own words — never reuse a reference page's headings verbatim.
- key_points should describe what your section will cover, not paraphrase what the reference says.
- Do NOT invent facts, statistics, or examples that do not appear in the reference content.
- If a reference could not be fetched, ignore it — do not guess its content.
"""
            for i, ref in enumerate(references, 1):
                ref_url = ref.get('url', '')
                fetched_content = ref.get('fetched_content', '')
                fetched_title = ref.get('fetched_title', '')
                if fetched_content:
                    user_prompt += f"\n--- Reference {i}: {fetched_title or ref_url} ---\n{fetched_content}\n"
                elif ref_url:
                    user_prompt += f"\n--- Reference {i}: {ref_url} [Content could not be fetched — do NOT guess] ---\n"

        if additional_instructions:
            user_prompt += f"""
**PRIORITY INSTRUCTIONS (from content creator — adapt the outline structure to honor these):**
{additional_instructions}
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
- Target total content length: {self._lower_word_limit(word_count)}-{self._upper_word_limit(word_count)} words
- Include 4-6 main sections (h2) for articles of 1000+ words; fewer (2-3) for shorter articles under 500 words
- Add subsections (h3) where appropriate
- Each section should have 2-4 key points
- Sum of estimated_words across all sections MUST fall within {self._lower_word_limit(word_count)}-{self._upper_word_limit(word_count)}
- Use descriptive, engaging headings that incorporate keywords naturally
- Structure should flow logically from introduction to conclusion

Return ONLY the JSON array, nothing else."""

        outline_max_tokens = self._calculate_outline_max_tokens(
            word_count, extended=extended_tokens
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=outline_max_tokens,
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
            if response.stop_reason == 'max_tokens':
                logger.warning(
                    f"Outline generation hit max_tokens cap "
                    f"(word_count={word_count}, max_tokens={outline_max_tokens}, "
                    f"extended={extended_tokens}). The outline JSON may be "
                    f"incomplete — caller validation should retry or fall back."
                )

            # Clean up the response if it has markdown code blocks
            if '```' in outline_text:
                parts = outline_text.split('```')
                for part in parts[1:]:
                    cleaned = part.strip()
                    if cleaned.startswith('json'):
                        cleaned = cleaned[4:].strip()
                    if cleaned.startswith('['):
                        outline_text = cleaned
                        break

            # Extract JSON array if there's surrounding text
            outline_text = outline_text.strip()
            if not outline_text.startswith('['):
                start_idx = outline_text.find('[')
                if start_idx != -1:
                    outline_text = outline_text[start_idx:]
            if not outline_text.endswith(']'):
                end_idx = outline_text.rfind(']')
                if end_idx != -1:
                    outline_text = outline_text[:end_idx + 1]

            # Remove trailing commas before ] or } (common LLM JSON error)
            outline_text = re.sub(r',\s*([}\]])', r'\1', outline_text)

            # Parse the JSON
            try:
                outline_sections = json.loads(outline_text)
            except json.JSONDecodeError:
                # Retry: ask Claude to fix the malformed JSON. Use the same
                # token budget as the original outline call so the repair
                # itself isn't truncated.
                fix_response = self.client.messages.create(
                    model=self.model,
                    max_tokens=outline_max_tokens,
                    temperature=0,
                    messages=[
                        {
                            "role": "user",
                            "content": f"The following JSON is malformed. Fix it and return ONLY valid JSON, nothing else:\n\n{outline_text}"
                        }
                    ]
                )
                fixed_text = fix_response.content[0].text.strip()
                if '```' in fixed_text:
                    parts = fixed_text.split('```')
                    for part in parts[1:]:
                        cleaned = part.strip()
                        if cleaned.startswith('json'):
                            cleaned = cleaned[4:].strip()
                        if cleaned.startswith('[') or cleaned.startswith('{'):
                            fixed_text = cleaned
                            break
                start_idx = fixed_text.find('[')
                end_idx = fixed_text.rfind(']')
                if start_idx != -1 and end_idx != -1:
                    fixed_text = fixed_text[start_idx:end_idx + 1]
                outline_sections = json.loads(fixed_text)

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
- Returns ONLY the HTML content (no markdown, no code blocks)

LIST FORMATTING — USE <ul> / <ol> WHEREVER THEY IMPROVE SCANNABILITY:
- Convert any enumeration of 3+ parallel items (features, benefits, use cases, tips, pros, cons, types, options, examples, reasons, tools, platforms, key takeaways) into a <ul>.
- Use <ol> for any sequence where order matters (step-by-step, ranked lists, process flows).
- Every article 500+ words MUST contain at least one <ul> or <ol>. Articles 1000+ words should contain two or more list blocks across different sections.
- Inside each <li>, use <strong> for the lead-in term, followed by a short explanation.
- Do NOT use lists for only 1-2 items; write those as prose."""

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

        keywords_block = self._format_keywords_for_prompt(keywords, params.get('word_count', 1500))
        user_prompt = f"""Write content following this exact outline structure:

**Title:** {title}
{keywords_block}**Tone:** {tone}
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

        # Add fetched reference URL content if available
        references = params.get('references', [])
        if references and len(references) > 0:
            user_prompt += """
**Reference Materials (research notes — read for FACTS, do NOT use as a template):**
The content below is research material you have read. Extract facts only. Do NOT mirror the references' wording, sentence flow, or paragraph order.
"""
            for i, ref in enumerate(references, 1):
                ref_url = ref.get('url', '')
                fetched_content = ref.get('fetched_content', '')
                fetched_title = ref.get('fetched_title', '')
                if fetched_content:
                    user_prompt += f"\n--- Reference {i}: {fetched_title or ref_url} ---\n{fetched_content}\n"
                elif ref_url:
                    user_prompt += f"\n--- Reference {i}: {ref_url} [Content could not be fetched — do NOT guess] ---\n"
            user_prompt += """
CRITICAL RULES for using references — STRICT ANTI-DUPLICATION:
- Use ONLY facts from the extracted content above. Do NOT fabricate data.
- Match the currency, units, and cultural context of the target country.
- Originality is mandatory: rephrase every fact in your own voice. NEVER copy any sentence or 6+ consecutive words verbatim from a reference.
- Section structure is yours to plan: do NOT mirror the references' headings or paragraph order. Use the approved outline above as the structure — references are facts only.
- Examples, analogies, openings, transitions, and closings must be your own. The reader must not be able to identify which page you read.
- When multiple references are given, synthesise across them — do not pattern after a single source.
- Cite where appropriate (e.g. "according to [source]"), but the surrounding prose must be entirely original.
"""

        # Detect list / table requests inside the client's free-text fields
        # (Additional Instructions + Key Messages). Catches everyday phrasings
        # such as "table", "list", "points", "topics", "categories",
        # "difference", "items", "comparison", "menus", "step-by-step",
        # "pros and cons", and similar. Used in this outline-driven path to
        # force the matching REQUIRED structure block into the prompt and to
        # drive the safety-net post-processing passes below.
        user_wants_list = self._user_requested_list_format(
            additional_instructions, key_messages
        )
        user_wants_table = self._user_requested_table_format(
            additional_instructions, key_messages
        )

        # Topic-aware structural hints (comparison tables, listing formats,
        # SEO structure checklist). Applied in addition to — not in place of —
        # the approved outline so tables/lists show up where the topic calls
        # for them.
        structure_hints = self._format_structure_hints(
            title, keywords, article_type, params.get('word_count', 1500),
            user_requested_list=user_wants_list,
            user_requested_table=user_wants_table,
        )
        if structure_hints:
            user_prompt += "\n" + structure_hints + "\n"

        if additional_instructions:
            user_prompt += f"""
**PRIORITY INSTRUCTIONS (from content creator — follow these over defaults):**
{additional_instructions}
"""
            # Short structural reinforcement so brief client prompts like
            # "use a list", "include a table", "list the topics", or
            # "show the differences" can't be lost in the wider context.
            explicit_reinforcement = []
            if user_wants_list:
                explicit_reinforcement.append(
                    "- The instructions above ask for list-style output (e.g. list / points / topics / categories / items / menus / steps) — your final HTML MUST contain at least one <ul> or <ol> block. Do NOT return only paragraphs."
                )
            if user_wants_table:
                explicit_reinforcement.append(
                    "- The instructions above ask for a table (e.g. table / comparison / difference / pros and cons / vs) — your final HTML MUST contain at least one real <table> block with <thead>/<tbody>. Do NOT skip it because prose works fine; tabular data is what was asked for."
                )
            if explicit_reinforcement:
                user_prompt += "\n" + "\n".join(explicit_reinforcement) + "\n"

        requested_word_count = params.get('word_count', 1500)
        lower_limit = self._lower_word_limit(requested_word_count)
        upper_limit = self._upper_word_limit(requested_word_count)
        target_mid = (lower_limit + upper_limit) // 2

        user_prompt += f"""
IMPORTANT:
- Follow the outline structure exactly (same headings, same order)
- Cover all key points mentioned for each section
- Target approximately {target_mid} words so you stay comfortably within the {lower_limit}-{upper_limit} range. Match the estimated word count for each section and budget accordingly — do NOT exceed the upper bound.
- Every target keyword MUST appear at least once across the final article.
- Use h2 tags for main sections, h3 tags for subsections. For comparison/listing topics, honour the structural rules above (tables for comparisons, <ul>/<ol> for enumerations).
- Always complete every sentence and paragraph fully. If you are approaching your output limit, wrap up the current section with a proper conclusion rather than starting a new section.
- Never end mid-sentence or leave content incomplete. Every article MUST end with a proper closing section (Conclusion / Final Verdict / Key Takeaways) and valid closing HTML tags.
- Return ONLY the HTML content, no markdown (no `#`, no `|` tables, no ``` fences)."""

        # Target word count is what the user selected; the outline's
        # estimated_words is advisory and must not push us past the user
        # range's upper bound. requested_word_count is defined above when
        # building the user prompt — reuse it here.
        max_tokens = self._calculate_max_tokens(requested_word_count)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
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
            total_prompt_tokens = response.usage.input_tokens
            total_completion_tokens = response.usage.output_tokens

            # Auto-continue on truncation
            if response.stop_reason == 'max_tokens':
                logger.warning(
                    f"Outline content truncated: target={requested_word_count} words, "
                    f"max_tokens={max_tokens}. Attempting auto-continuation..."
                )
                content_html, extra_tokens = self._continue_truncated_content(content_html)
                total_completion_tokens += extra_tokens

            # Post-processing: strip code fences / decode entities so the
            # editor renders real HTML tags (not literal <h2> text).
            content_html = self._sanitize_html_response(content_html)
            # Post-processing: convert any remaining markdown to HTML
            content_html = self._convert_markdown_to_html(content_html)
            # Post-processing: deduplicate internal links
            content_html = self._deduplicate_internal_links(content_html)
            # Post-processing: cheap regex promotion of sequential bold
            # lead-in paragraphs into <ul> (no API cost).
            content_html, _promoted = self._promote_bold_leadin_paragraphs_to_list(
                content_html
            )
            # Post-processing: detect missing keywords and weave them in.
            missing = self._missing_keywords(content_html, params.get('keywords', ''))
            if missing:
                logger.info(
                    f"Missing keywords detected after outline generation: {missing}. "
                    f"Running keyword-fix pass."
                )
                content_html, extra_tokens = self._fix_missing_keywords(
                    content_html, missing, requested_word_count
                )
                total_completion_tokens += extra_tokens
            # Safety net 1 — Lists.
            # If the article ended up as pure paragraphs (or fewer lists than
            # the word-count threshold expects, or fewer than the client's
            # explicit request expects), convert prose enumerations into
            # <ul>/<ol> via a focused fix pass. user_wants_list captures
            # everyday phrasings like "list", "points", "topics", "categories",
            # "items", "menus", "step-by-step" from the client's instructions.
            required_lists = self._required_list_count(
                requested_word_count, user_requested_list=user_wants_list
            )
            if self._count_lists(content_html) < required_lists:
                content_html, extra_tokens = self._ensure_lists_in_content(
                    content_html, requested_word_count,
                    user_requested_list=user_wants_list,
                )
                total_completion_tokens += extra_tokens
            logger.info(
                f"Lists in final content: {self._count_lists(content_html)} "
                f"(required {required_lists})"
            )

            # Safety net 2 — Tables.
            # When the client clearly asked for a table (e.g. "include a
            # comparison table", "show the differences", "pros and cons")
            # but Claude returned no <table> at all, run a focused fix pass
            # that converts the most tabular section of the article into a
            # real HTML <table> without inventing new facts.
            if user_wants_table and self._count_tables(content_html) == 0:
                logger.info(
                    "Client asked for a table but outline-based content has "
                    "none; running table-fix pass."
                )
                content_html, extra_tokens = self._ensure_table_in_content(
                    content_html, requested_word_count
                )
                total_completion_tokens += extra_tokens

            # Safety net 3 — Missing outline sections.
            # If the main generation skipped any planned section heading
            # (e.g. Claude ran long earlier and stopped before the trailing
            # sections, or merged two planned subheadings into one), write
            # ONLY the missing sections in a focused follow-up call and
            # merge them back in before conclusion. Runs before word-count
            # enforcement so the new sections are included in the budget.
            content_html, extra_tokens = self._complete_missing_outline_sections(
                content_html, outline, params
            )
            total_completion_tokens += extra_tokens

            # Post-processing: enforce the word count range the user
            # selected. Pass the outline so trimming preserves every planned
            # section heading instead of silently dropping middle sections.
            content_html = self._enforce_word_count_limit(
                content_html, requested_word_count, outline=outline
            )

            generation_time = time.time() - start_time
            plain_text = re.sub(r'<[^>]+>', ' ', content_html)
            actual_word_count = len(plain_text.split())

            return {
                'content_html': content_html,
                'generation_time_seconds': round(generation_time, 2),
                'prompt_tokens': total_prompt_tokens,
                'completion_tokens': total_completion_tokens,
                'actual_word_count': actual_word_count,
                'model_used': self.model
            }

        except Exception as e:
            raise Exception(f"Claude API error: {str(e)}")

    def rewrite_text(self, original_text, prompt, max_retries=3):
        """
        Rewrite a portion of text based on user instructions.

        This is the backend for the editor's "Optimize with custom prompt"
        button: the user selects a passage, types an instruction (e.g.
        "convert to a list", "make this a comparison table", "show the
        differences as bullet points"), and we rewrite that selection in
        place.

        We honour list / table requests in the same way the main content
        generators do — via the shared `_user_requested_list_format` /
        `_user_requested_table_format` detectors plus the
        `_ensure_lists_in_content` / `_ensure_table_in_content` safety nets
        — so a brief instruction like "use a list" can't be ignored.

        Args:
            original_text (str): The text to rewrite (HTML or plain).
            prompt (str): User's rewrite instruction.
            max_retries (int): Retries for transient API errors.

        Returns:
            str: The rewritten text/HTML.
        """
        # Did the client ask for list / table output in their rewrite prompt?
        # Catches the same everyday phrasings used elsewhere ("table", "list",
        # "points", "topics", "categories", "difference", "items",
        # "comparison", "menus", "step-by-step", "pros and cons", …).
        user_wants_list = self._user_requested_list_format(prompt)
        user_wants_table = self._user_requested_table_format(prompt)

        system_prompt = """You are a skilled editor and content writer. Your task is to rewrite the provided text according to the user's instructions.

Guidelines:
- Maintain the core meaning and information unless explicitly asked to change it
- Match the approximate length of the original text unless asked to make it longer or shorter
- Return ONLY the rewritten text, no explanations or comments
- If the original text contains HTML tags, output HTML. Use <h2>, <h3> tags for headings — NEVER use markdown hashtag syntax (# or ##)
- Use <table>, <thead>, <tbody>, <tr>, <th>, <td> for tables — NEVER use markdown pipe (|) table syntax
- Preserve the heading hierarchy (H1, H2, H3) from the original text. Do not remove or flatten headings
- Preserve any formatting style from the original text
- Wrap EVERY paragraph of running text in <p>...</p> tags. Do NOT leave plain prose floating between block elements (between </h2> and <table>, between </ul> and <h2>, etc.) — every paragraph must have its own <p> opening and closing tag, otherwise the editor will render the text without paragraph styling
- Use <strong> ONLY to emphasise specific words/phrases inside a <p> or <li>. Do NOT wrap whole paragraphs, headings, or list items in <strong> — that makes the entire passage render bold"""

        # Append structural rules to the system prompt only when the user's
        # instruction asks for a list or a table, so default rewrites stay
        # untouched.
        if user_wants_list:
            system_prompt += (
                "\n\nLIST FORMATTING (the user asked for list-style output):\n"
                "- Your rewritten HTML MUST contain at least one <ul> or <ol> block.\n"
                "- Use <ol> when sequence/order matters (steps, ranked items); otherwise use <ul>.\n"
                "- Inside each <li>, lead with a <strong>Term:</strong> when there is a natural label, then a short explanation.\n"
                "- Do NOT return only paragraphs when the instruction asks for a list, points, topics, categories, items, menus, or steps."
            )
        if user_wants_table:
            system_prompt += (
                "\n\nTABLE FORMATTING (the user asked for tabular output):\n"
                "- Your rewritten HTML MUST contain at least one real HTML <table> block, with <thead> for column headers and <tbody> for data rows.\n"
                "- 3-6 columns and 4-8 rows of meaningful data, pulled from the existing text. Do NOT invent new facts.\n"
                "- Do NOT use markdown pipe tables (| col1 | col2 |). Use real <table> tags only.\n"
                "- Do NOT skip the table because prose works fine — tabular data is what was asked for."
            )

        user_prompt = f"""Please rewrite the following text according to these instructions:

Instructions: {prompt}

Original text:
{original_text}

Rewritten text:"""

        # Reinforce the user's structural intent right before the rewrite,
        # mirroring what the main generators do under PRIORITY INSTRUCTIONS.
        explicit_reinforcement = []
        if user_wants_list:
            explicit_reinforcement.append(
                "- The instruction above asks for list-style output (e.g. list / points / topics / categories / items / menus / steps) — your rewritten HTML MUST include at least one <ul> or <ol>. Do NOT return only paragraphs."
            )
        if user_wants_table:
            explicit_reinforcement.append(
                "- The instruction above asks for a table (e.g. table / comparison / difference / pros and cons / vs) — your rewritten HTML MUST include at least one real <table> with <thead>/<tbody>."
            )
        if explicit_reinforcement:
            user_prompt = (
                user_prompt.rstrip("\n").rsplit("\n\nRewritten text:", 1)[0]
                + "\n\n"
                + "\n".join(explicit_reinforcement)
                + "\n\nRewritten text:"
            )

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

                # Post-processing: clean up Claude's response so the editor
                # renders real HTML instead of literal tags.
                # _sanitize_html_response() handles three failure modes we
                # were seeing in the editor's "Optimize with custom prompt":
                #   1. Output wrapped in ```html ... ``` markdown code fences
                #      (the editor would then store `<h1>` etc. as visible text).
                #   2. Output wrapped in <pre><code>...</code></pre>.
                #   3. Output entity-escaped (`&lt;h1&gt;Title&lt;/h1&gt;`).
                # The main generators (generate_content / generate_content_from_outline)
                # already run this; rewrite_text was missing it, which is why
                # rewrites occasionally surfaced raw HTML tags in the editor.
                rewritten_text = self._sanitize_html_response(rewritten_text)

                # Post-processing: convert any markdown to HTML
                # (fixes Issue 4: hashtag headings, Issue 5: pipe tables)
                rewritten_text = self._convert_markdown_to_html(rewritten_text)
                rewritten_text = self._deduplicate_internal_links(rewritten_text)

                # Safety nets — only run when the client explicitly asked for
                # a list or a table. Default rewrites are untouched.
                if user_wants_list or user_wants_table:
                    # Word-count proxy for the safety nets: use the rewritten
                    # text's own length so the helpers' upper-bound caps
                    # match the size of the selection being rewritten.
                    plain = re.sub(r'<[^>]+>', ' ', rewritten_text)
                    wc_proxy = max(150, len(plain.split()))

                    if user_wants_list and self._count_lists(rewritten_text) == 0:
                        logger.info(
                            "Optimize-with-custom-prompt: client asked for a "
                            "list but rewrite has none; running list-fix pass."
                        )
                        rewritten_text, _ = self._ensure_lists_in_content(
                            rewritten_text, wc_proxy, user_requested_list=True
                        )

                    if user_wants_table and self._count_tables(rewritten_text) == 0:
                        logger.info(
                            "Optimize-with-custom-prompt: client asked for a "
                            "table but rewrite has none; running table-fix pass."
                        )
                        rewritten_text, _ = self._ensure_table_in_content(
                            rewritten_text, wc_proxy
                        )

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
13. PRESERVE existing <ul> and <ol> list structures exactly. Do NOT flatten <li> items into prose, paragraphs, or comma-separated sentences. You may shorten or rephrase text inside each <li>, but keep the <ul>/<ol>/<li> tags intact and keep every list item. Lists with 3+ <li> elements stay as-is — the 2-item rule below applies only to inline comma-separated series inside a sentence, NOT to <li> items inside a <ul>/<ol>.
14. STRICT 2-ITEM INLINE LIST RULE: Scan every sentence for comma-separated series INSIDE prose (not inside <ul>/<ol>). Any inline comma-separated series with 3+ items MUST be reduced to exactly 2 items joined by "and" or "or". Drop the least important item(s). This rule does NOT apply to items inside <ul> or <ol> — those stay as-is. This applies to ALL inline patterns:
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
□ No INLINE comma-separated list has 3+ items in prose sentences — scan every comma between nouns/verbs and verify only 2 items exist. Also check sequential sentences listing 3+ options. Items inside <ul>/<ol> are exempt and must be preserved.
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

                # Post-processing: fix any markdown that slipped through
                humanised_content = self._convert_markdown_to_html(humanised_content)

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

