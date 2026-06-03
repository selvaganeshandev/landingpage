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
# match — exactly the alternation used in GA4's sessionSource regex filter:
#
#   chatgpt\.com|chat\.openai\.com|gemini\.google\.com|deepseek\.com|
#   perplexity(?:\.ai)?|claude\.ai|copilot\.microsoft\.com|deepl\.com|
#   character\.ai|(?:\w+\.)?meta\.ai|grok\.x\.com|grok\.com|x\.ai|
#   bard\.google\.com|(?:\w+\.)?mistral\.ai|writesonic\.com|quillbot
#
# Order matters only for classification (first match wins); for the GA4 filter
# the whole list is OR'd together, so duplicate labels (e.g. two ChatGPT rows)
# are harmless.
PLATFORM_PATTERNS = [
    (r'chatgpt\.com',            'ChatGPT'),
    (r'chat\.openai\.com',       'ChatGPT'),
    (r'gemini\.google\.com',     'Gemini'),
    (r'bard\.google\.com',       'Gemini'),
    (r'perplexity(?:\.ai)?',     'Perplexity'),   # matches bare "perplexity" AND "perplexity.ai"
    (r'claude\.ai',              'Claude'),
    (r'copilot\.microsoft\.com', 'Copilot'),
    (r'deepseek\.com',           'DeepSeek'),
    (r'character\.ai',           'Character.AI'),
    (r'(?:\w+\.)?meta\.ai',      'Meta AI'),
    (r'grok\.x\.com',            'Grok'),
    (r'grok\.com',               'Grok'),
    (r'x\.ai',                   'Grok'),
    (r'(?:\w+\.)?mistral\.ai',   'Mistral'),
    (r'deepl\.com',              'DeepL'),
    (r'writesonic\.com',         'Writesonic'),
    (r'quillbot',                'QuillBot'),
]

# Combined regex for the GA4 ``dimensionFilter`` (matchType PARTIAL_REGEXP,
# which is what the "matches regex" UI option uses). Filtering with the same
# regex the team uses guarantees the API returns the identical row set.
AI_SOURCE_REGEX = '|'.join(pattern for pattern, _ in PLATFORM_PATTERNS)

_COMPILED = [(re.compile(pattern, re.IGNORECASE), label) for pattern, label in PLATFORM_PATTERNS]


def resolve_platform(source):
    """Map a GA4 ``sessionSource`` string to a canonical AI-platform label.

    Returns the platform label, or ``None`` if ``source`` is not a known AI
    source. Callers that filter via :data:`AI_SOURCE_REGEX` first can treat a
    ``None`` here as "Other AI".
    """
    if not source:
        return None
    text = source.strip().lower()
    for pattern, label in _COMPILED:
        if pattern.search(text):
            return label
    return None
