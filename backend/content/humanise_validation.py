"""Guards that stop a failed humanisation pass being saved over the article.

Both checks exist because of a real incident: Pass 1 returned an empty string,
Pass 2 apologised about being sent no HTML, and 253 characters of apology
replaced a 10,192-character article under a ``completed`` status. Nothing in the
pipeline looked at what came back.

Kept in its own module, free of Django and SDK imports, so it can be tested
directly — ``content/views.py`` and ``content/claude_content_generator.py`` both
carry import graphs that make their internals awkward to exercise in isolation.

The two guards catch different things and are both worth having:

  ``raise_if_truncated``   reads ``stop_reason`` from the provider — the exact
                           signal, available only at the call site.
  ``validate_pass_output`` inspects the text — a proxy, but it also catches
                           failures that report a clean stop, such as a model
                           replying in prose about the task instead of doing it.

Run the tests:  python content/test_humanise_validation.py   (from backend/)
"""
import re

# Below this share of the input, the output is truncated rather than rewritten.
# Humanisation preserves all HTML, links and keywords, so a pass returns roughly
# what it was given — measured 102% and 101% on production. Half is a
# deliberately loose floor that only a broken pass falls through.
MIN_OUTPUT_RATIO = 0.5

# anthropic/claude-sonnet-5 accepts 128,000 output tokens against a 1,000,000
# context window (confirmed from OpenRouter's model API on 2026-07-27). The
# humanise calls were pinned at 8192 — an eighth of one percent of the context
# and a fifteenth of the output ceiling — which is almost certainly a leftover
# from an older Anthropic model where 8192 WAS the limit.
#
# That cap is why article 285 (44,227 chars) came back truncated mid-CSS: a
# rewrite has to emit roughly what it was given, and 8192 tokens is only ~30,000
# characters. Every article over that silently lost its tail.
MODEL_MAX_OUTPUT_TOKENS = 128000
MIN_OUTPUT_TOKENS = 8192


def output_ceiling(content_html):
    """Token ceiling scaled to the article, since a rewrite returns what it was given.

    Roughly 4 characters per token, doubled so a rewrite that runs a little long
    (measured 102% of input) still fits, then clamped to what the model accepts.

    Deliberately NOT a flat 128,000. Billing follows tokens actually generated so
    a high ceiling is free when output is short, but this same call demonstrated
    runaway generation once already — with reasoning enabled it burned the entire
    ceiling and emitted nothing, wasting 32,000 tokens at the 32k setting. A
    ceiling proportional to the input bounds that blast radius.
    """
    needed = (len(content_html or '') // 4) * 2
    return max(MIN_OUTPUT_TOKENS, min(MODEL_MAX_OUTPUT_TOKENS, needed))


# --------------------------------------------------------------------------- #
# Style analysis — the counting the model cannot do
# --------------------------------------------------------------------------- #
# Rules 2 and 4 of the humanisation prompt ban 11-14 word sentences (the "gap
# zone") and -ing sentence openings. Both were measured across 12 articles
# humanised in February and today's runs: the gap zone goes UP as often as down
# (14%->23%, 11%->20%, 17%->33%) and -ing openings frequently INCREASE (4->10,
# 2->8, 4->9). They have never worked, on any model, in five months.
#
# The cause is that the prompt asks the model to count -- "count the words in
# every sentence you write", "keep a mental tally" -- which is the one thing it
# is worst at, and which is also what drove the runaway reasoning that emptied
# the response entirely. Python counts perfectly and instantly. So the split is:
# Python finds the violations, the model rewrites the specific sentences it is
# handed. Nothing is auto-rewritten here -- programmatically restructuring prose
# produces garbage ("Nothing is worse" -> "The nothing is worse"), so detection
# feeds the refinement prompt instead of replacing it.
GAP_ZONE = (11, 14)
SHORT_BAND = (8, 10)
LONG_BAND = (15, 25)

_TAG_RE = re.compile(r'<[^>]+>')
_WS_RE = re.compile(r'\s+')
_SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?])\s+')
# Words ending in -ing that are not gerunds, so a sentence opening with one is
# not a rule 4 violation. Without this, "Nothing changed." and "Something works."
# would be reported and the model asked to mangle them.
_NOT_GERUNDS = {
    'nothing', 'something', 'everything', 'anything', 'king', 'thing', 'being',
    'bring', 'during', 'spring', 'string', 'wing', 'ring', 'sing', 'morning',
    'evening', 'ceiling', 'sterling', 'shilling', 'viking', 'wedding', 'building',
}


def _text_sentences(html):
    """Plain-text sentences from HTML, tags and whitespace stripped."""
    text = _WS_RE.sub(' ', _TAG_RE.sub(' ', html or '')).strip()
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if len(s.split()) > 1]


def find_style_violations(html):
    """Return the exact sentences breaking the countable humanisation rules.

    Returns a dict of lists, each holding real sentences from the article rather
    than counts, so the refinement prompt can name them instead of asking the
    model to go looking.
    """
    gap, ing, too_short, too_long = [], [], [], []
    for sentence in _text_sentences(html):
        words = sentence.split()
        n = len(words)
        if GAP_ZONE[0] <= n <= GAP_ZONE[1]:
            gap.append((n, sentence))
        elif n < 7:
            too_short.append((n, sentence))
        elif n > LONG_BAND[1]:
            too_long.append((n, sentence))
        first = words[0].strip('“"‘\'(').lower()
        if first.endswith('ing') and first not in _NOT_GERUNDS and len(first) > 4:
            ing.append((n, sentence))
    return {'gap_zone': gap, 'ing_starts': ing, 'too_short': too_short, 'too_long': too_long}


def format_violations_for_prompt(violations, max_each=12):
    """Render violations as an instruction block, or '' when the article is clean.

    Capped per category because the whole point is a short, actionable list; a
    hundred quoted sentences would push the model straight back into the
    unfocused scanning that never worked.
    """
    sections = []

    def block(title, items, instruction):
        if not items:
            return
        lines = [f"{title} ({len(items)} found — fix every one listed):", instruction]
        for n, sentence in items[:max_each]:
            snippet = sentence if len(sentence) <= 160 else sentence[:157] + '...'
            lines.append(f'  [{n} words] "{snippet}"')
        if len(items) > max_each:
            lines.append(f"  ...and {len(items) - max_each} more of the same kind.")
        sections.append("\n".join(lines))

    block(
        "SENTENCES IN THE FORBIDDEN 11-14 WORD GAP ZONE",
        violations.get('gap_zone'),
        f"  Rewrite each to {SHORT_BAND[0]}-{SHORT_BAND[1]} words (cut) or "
        f"{LONG_BAND[0]}-{LONG_BAND[1]} words (add detail). Do not leave any at 11-14.",
    )
    block(
        "SENTENCES STARTING WITH AN -ING WORD",
        violations.get('ing_starts'),
        '  Restructure each, e.g. "Earning opportunities..." -> "The earning opportunities...".',
    )
    block(
        "SENTENCES UNDER 7 WORDS",
        violations.get('too_short'),
        "  Merge each into an adjacent sentence.",
    )
    block(
        "SENTENCES OVER 25 WORDS",
        violations.get('too_long'),
        "  Split each into two.",
    )

    if not sections:
        return ""
    return (
        "\n\n=== EXACT VIOLATIONS FOUND IN THIS ARTICLE ===\n"
        "These were located by an automated word count, so the list is complete "
        "and accurate. Fix these specific sentences. Do not search for others.\n\n"
        + "\n\n".join(sections)
    )


def raise_if_truncated(stage, response, source_html):
    """Reject a reply the model was cut off part-way through.

    ``stop_reason == 'length'`` means the token ceiling was hit, so whatever came
    back is a fragment — either empty (the entire budget went on hidden reasoning)
    or an article ending mid-sentence. Both are corruption, and both otherwise
    read as a perfectly successful response.

    This is the exact signal, unlike the ratio check below. Article 285 truncated
    to 49% of its input and was caught only because it fell a hair under the 50%
    floor; anything truncated to 55% would have sailed through.

    Deliberately not treated as a transient error by callers: a ceiling that is
    too small is deterministic, so retrying just costs the same failure again.
    """
    if getattr(response, 'stop_reason', None) != 'length':
        return
    emitted = 0
    try:
        emitted = len(response.content[0].text or '')
    except Exception:  # noqa: BLE001 - only used to enrich the message
        pass
    raise Exception(
        f"{stage} hit the model's token ceiling (stop_reason='length') after "
        f"emitting {emitted} chars from {len(source_html or '')} chars of input. "
        f"The output is truncated and has not been saved."
    )


def validate_pass_output(stage, source_html, output_html):
    """Reject a humanisation pass that did not return usable content.

    Checks are STRUCTURAL on purpose. Matching the apology wording was considered
    and rejected: three different phrasings appeared across two passes, so any
    such list starts rotting the moment the model rephrases. What does not change
    is that a humanised article is non-empty, is HTML, and is about as long as
    its input.

    Raises so the caller's existing handler marks the job failed and leaves
    ``content_html`` untouched.
    """
    if not output_html or not output_html.strip():
        raise Exception(
            f"{stage} returned an empty response for {len(source_html or '')} chars of input"
        )

    # The input is HTML and every pass is told to return HTML, so a reply with no
    # tag at all is prose the model wrote *about* the task rather than the
    # rewritten article. This is what catches an apology, whatever it says.
    if '<' not in output_html:
        raise Exception(
            f"{stage} returned {len(output_html)} chars containing no HTML tags "
            f"(likely a refusal or an error message, not content)"
        )

    if len(output_html) < len(source_html or '') * MIN_OUTPUT_RATIO:
        raise Exception(
            f"{stage} returned {len(output_html)} chars from {len(source_html or '')} "
            f"(under {MIN_OUTPUT_RATIO:.0%}) — truncated, refusing to save"
        )

    return output_html
