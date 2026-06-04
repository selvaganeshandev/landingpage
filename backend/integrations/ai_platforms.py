"""
Canonical AI-platform matching for GA4 ``sessionSource`` values.

This mirrors the "Session source matches regex" filter the team uses in the GA4
Explorations UI, so PromptMaxx classifies and counts the EXACT same sessions GA4
reports. When the GA4 regex changes, update ``PLATFORM_PATTERNS`` to match.

NOTE: this module is intentionally duplicated in ``engine/integrations`` and
``backend/integrations`` — the two Django projects do not share a Python
package. Edit BOTH copies together so they never drift apart.
"""
import re

# Ordered (regex, canonical label). Each pattern is a partial / "contains"
# match. This is the UNION of the two AI-source regexes clients use in their GA4
# "Session source matches regex" filters, so the GA4 Data API captures AI traffic
# for every client regardless of which platforms they get referrals from:
#
#   1) the team/original GA filter: chatgpt.com, chat.openai.com, gemini.google.com,
#      deepseek.com, perplexity, claude.ai, copilot.microsoft.com, deepl.com,
#      character.ai, meta.ai, grok, x.ai, bard.google.com, mistral.ai,
#      writesonic.com, quillbot
#   2) the newer client GA filter: aitastic.app, bnngpt.com, chat-gpt.org,
#      copy.ai, edgepilot, edgeservices, iask.ai, neeva, nimble.ai, openai.com,
#      copilot.com
#
# On the dominant platforms (chatgpt/gemini/perplexity/claude/copilot — the bulk
# of real AI traffic) this matches every client's GA exactly; the long-tail
# patterns just ensure no AI source is missed. For classification first match
# wins; for the GA4 filter the whole list is OR'd, so duplicate labels (several
# ChatGPT/Copilot/Gemini rows) are harmless. Filter matches with no specific
# label fall back to "Other AI" in resolve_platform's callers.
PLATFORM_PATTERNS = [
    # ChatGPT / OpenAI
    (r'chatgpt\.com',            'ChatGPT'),
    (r'chat\.openai\.com',       'ChatGPT'),
    (r'chat-gpt\.org',           'ChatGPT'),
    (r'openai\.com',             'ChatGPT'),
    # Gemini / Bard
    (r'gemini\.google\.com',     'Gemini'),
    (r'bard\.google\.com',       'Gemini'),
    # Claude
    (r'claude\.ai',              'Claude'),
    # Perplexity (bare "perplexity" matches "perplexity" and "perplexity.ai")
    (r'perplexity',              'Perplexity'),
    # Copilot (MS Copilot + Edge Copilot surfaces)
    (r'copilot\.microsoft\.com', 'Copilot'),
    (r'copilot\.com',            'Copilot'),
    (r'edgepilot',               'Copilot'),
    (r'edgeservices',            'Copilot'),
    # Other AI assistants
    (r'deepseek\.com',           'DeepSeek'),
    (r'deepl\.com',              'DeepL'),
    (r'character\.ai',           'Character.AI'),
    (r'(?:\w+\.)?meta\.ai',      'Meta AI'),
    (r'grok\.x\.com',            'Grok'),
    (r'grok\.com',               'Grok'),
    (r'x\.ai',                   'Grok'),
    (r'(?:\w+\.)?mistral\.ai',   'Mistral'),
    (r'writesonic\.com',         'Writesonic'),
    (r'quillbot',                'QuillBot'),
    (r'aitastic\.app',           'Aitastic'),
    (r'bnngpt\.com',             'BNNGPT'),
    (r'copy\.ai',                'Copy.ai'),
    (r'iask\.ai',                'iAsk'),
    (r'neeva',                   'Neeva'),
    (r'nimble\.ai',              'Nimble'),
]

# Combined regex for the GA4 ``dimensionFilter`` (matchType PARTIAL_REGEXP,
# which is what the "matches regex" UI option uses). Filtering with the same
# regex the team uses guarantees the API returns the identical row set.
AI_SOURCE_REGEX = '|'.join(pattern for pattern, _ in PLATFORM_PATTERNS)

_COMPILED = [(re.compile(pattern, re.IGNORECASE), label) for pattern, label in PLATFORM_PATTERNS]

# The 6 LLMs the product tracks in GEO monitoring. The GA traffic breakdown is
# reported using these SAME 6 canonical labels so the Traffic Attribution page
# stays consistent with the rest of the product. Any other AI source the regex
# matches (Copilot, DeepL, Mistral, etc.) still counts toward the AI-traffic
# TOTAL but rolls up under "Other AI" in the per-platform breakdown.
SUPPORTED_LLMS = {'ChatGPT', 'Claude', 'Gemini', 'Perplexity', 'Grok', 'DeepSeek'}


def resolve_platform(source):
    """Map a GA4 ``sessionSource`` string to one of the product's 6 canonical
    LLM labels (see :data:`SUPPORTED_LLMS`).

    Returns the LLM label, or ``None`` when ``source`` is not one of those 6
    (including AI sources outside the 6, e.g. Copilot / DeepL). Callers that
    filter via :data:`AI_SOURCE_REGEX` first treat a ``None`` here as "Other AI",
    so the GA breakdown is always the 6 LLMs + an "Other AI" bucket while the
    total still reconciles with GA.
    """
    if not source:
        return None
    text = source.strip().lower()
    for pattern, label in _COMPILED:
        if pattern.search(text):
            return label if label in SUPPORTED_LLMS else None
    return None
