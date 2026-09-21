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

Run the tests:  python tests/standalone/backend/content/test_humanise_validation.py
"""
import re
import statistics

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
# The prompt used to ask the model to COUNT -- "count the words in every
# sentence you write", "keep a mental tally" -- which is the one thing it is
# worst at, and which drove the runaway reasoning that emptied the response
# entirely. Python counts perfectly and instantly, so the split is: Python
# measures, the model rewrites the specific sentences it is handed. Nothing is
# auto-rewritten here -- programmatically restructuring prose produces garbage
# ("Nothing is worse" -> "The nothing is worse"), so detection feeds the
# refinement prompt instead of replacing it.
#
# ---------------------------------------------------------------------------
# What replaced the gap-zone ban, and why
# ---------------------------------------------------------------------------
# Measured across 200 articles holding BOTH their pre- and post-humanise text
# (burstiness computed per article, then averaged — pooling every sentence into
# one set instead reports 0.463 -> 0.517, which is inflated because it mixes
# between-article differences in mean length into the spread):
#
#                         before humanise   after humanise
#   sentences at 11-14w        16.8%            22.8%   <- the BANNED band GREW
#   burstiness (sd/mean)       0.400            0.451
#
# So the ban fails at its own stated goal: forbidding 11-14 words leaves 36%
# MORE sentences there. Humanisation does lift burstiness overall, but it is
# not enough — 58% of humanised articles still land under 0.45, and 32% come
# out LESS bursty than the draft they started from.
#
# Burstiness — variance in sentence length — is the strongest signal a modern
# detector reads: humans are irregular, models are even. The old rule floored
# sentences at 7 words and capped them at 25, which forbids exactly the tails
# that would fix those 58%. So the lever is inverted: stop banning the tails
# and start asking for them.
#
# Python computes this exactly and for free — no model, no API, no per-call
# cost — which is the same split that already works elsewhere in this module.
BURSTINESS_TARGET = 0.45   # drafts already average 0.400, humanised 0.451
SHORT_SENTENCE = 8         # under this many words counts as a short sentence
LONG_SENTENCE = 28         # over this many words counts as a long one
SHORT_SHARE_TARGET = 0.10  # at least this share of sentences should be short
LONG_SHARE_TARGET = 0.10   # ... and this share long
# A run of this many consecutive sentences within MONOTONE_SPREAD words of each
# other reads as machine-even regardless of what the overall figures say.
MONOTONE_RUN = 4
MONOTONE_SPREAD = 4

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


def _visible_text(html):
    """The prose a reader sees, with tags and whitespace collapsed away."""
    return _WS_RE.sub(' ', _TAG_RE.sub(' ', html or '')).strip()


def _text_sentences(html):
    """Plain-text sentences from HTML, tags and whitespace stripped."""
    text = _WS_RE.sub(' ', _TAG_RE.sub(' ', html or '')).strip()
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if len(s.split()) > 1]


def sentence_lengths(html):
    """Word count of every sentence a reader sees, in order."""
    return [len(s.split()) for s in _text_sentences(html)]


def burstiness(html):
    """Variance in sentence length, as std dev over mean. 0.0 for no variation.

    The one number worth optimising. Measured over 200 articles here, drafts
    average 0.400 and humanised output 0.451 — better, but 58% of articles still
    finish under the 0.45 a detector reads as human, and 32% come out less
    bursty than the draft. That is the gap this replaces the gap-zone ban to
    close.

    Returns 0.0 rather than raising on an article too short to measure, so a
    caller can treat "cannot tell" and "no variation" the same way: neither is
    a reason to ask the model for changes.
    """
    lengths = sentence_lengths(html)
    if len(lengths) < 2:
        return 0.0
    mean = statistics.mean(lengths)
    if not mean:
        return 0.0
    return statistics.pstdev(lengths) / mean


def length_profile(html):
    """Everything the prompt needs to know about sentence-length spread."""
    lengths = sentence_lengths(html)
    total = len(lengths)
    if not total:
        return {'count': 0, 'burstiness': 0.0, 'mean': 0.0,
                'short': 0, 'long': 0, 'need_short': 0, 'need_long': 0}
    short = sum(1 for n in lengths if n < SHORT_SENTENCE)
    long_ = sum(1 for n in lengths if n > LONG_SENTENCE)
    return {
        'count': total,
        'burstiness': burstiness(html),
        'mean': statistics.mean(lengths),
        'short': short,
        'long': long_,
        # How many MORE of each are needed to hit the target share. The prompt
        # asks for a specific number of rewrites, not a percentage — a model
        # given "10%" has to count the article to act on it, which is the thing
        # it cannot do.
        'need_short': max(0, int(round(total * SHORT_SHARE_TARGET)) - short),
        'need_long': max(0, int(round(total * LONG_SHARE_TARGET)) - long_),
    }


def _monotone_runs(html):
    """Stretches of consecutive sentences that are all nearly the same length.

    Overall dispersion can look acceptable while a section still reads as
    machine-even, because a long passage of 16-word sentences averages out
    against variation elsewhere. This catches the passage.
    """
    sentences = _text_sentences(html)
    runs, start = [], 0
    for i in range(1, len(sentences) + 1):
        window = [len(s.split()) for s in sentences[start:i]]
        if i < len(sentences) and max(window) - min(window) <= MONOTONE_SPREAD:
            continue
        if i - start >= MONOTONE_RUN:
            runs.append((i - start, sentences[start]))
        start = i
    return runs


def find_style_violations(html):
    """Return what the model must fix, as real sentences rather than counts.

    The gap-zone, too-short and too-long categories are GONE: measurement on 200
    real articles showed the 11-14 ban grew that band from 16.8% to 22.8%, and
    left 58% of humanised articles under the 0.45 burstiness a detector reads as
    human. The tails it forbade are what would close that gap, so they are now
    requested rather than banned.

    Keys kept for callers: ``ing_starts`` (a genuine generated-text tell that
    the ban does help with) plus the new ``profile`` and ``monotone_runs``.
    """
    ing = []
    for sentence in _text_sentences(html):
        words = sentence.split()
        first = words[0].strip('“"‘\'(').lower()
        if first.endswith('ing') and first not in _NOT_GERUNDS and len(first) > 4:
            ing.append((len(words), sentence))
    return {
        'ing_starts': ing,
        'profile': length_profile(html),
        'monotone_runs': _monotone_runs(html),
    }


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
        "SENTENCES STARTING WITH AN -ING WORD",
        violations.get('ing_starts'),
        '  Restructure each, e.g. "Earning opportunities..." -> "The earning opportunities...".',
    )
    block(
        "PASSAGES WHERE EVERY SENTENCE IS THE SAME LENGTH",
        violations.get('monotone_runs'),
        "  Each number is how many consecutive sentences run at nearly one "
        "length, starting from the quoted one. Break the run up: make one of "
        "them very short and one much longer. An even rhythm is the clearest "
        "sign of generated text.",
    )

    # The dispersion ask. Phrased as a COUNT of rewrites, never a percentage —
    # a model handed "10%" has to count the article to act on it, which is the
    # thing it cannot do and the reason the old word-count rules never worked.
    profile = violations.get('profile') or {}
    if profile.get('count'):
        need_short = profile.get('need_short', 0)
        need_long = profile.get('need_long', 0)
        if need_short or need_long or profile.get('burstiness', 0) < BURSTINESS_TARGET:
            asks = []
            if need_short:
                asks.append(
                    f"  - Cut {need_short} sentence(s) down to UNDER {SHORT_SENTENCE} "
                    f"words. Short, blunt sentences are the strongest signal here."
                )
            if need_long:
                asks.append(
                    f"  - Expand {need_long} sentence(s) to OVER {LONG_SENTENCE} "
                    f"words by adding a concrete clause — never filler."
                )
            asks.append(
                "  - Do NOT even out the rest. Uneven is the point: real writing "
                "mixes 5-word sentences with 35-word ones, and an article where "
                "every sentence is a similar length reads as machine-written "
                "however good the wording is."
            )
            sections.append(
                "SENTENCE-LENGTH VARIATION IS TOO LOW "
                f"(measured {profile['burstiness']:.2f}, target {BURSTINESS_TARGET:.2f} — "
                f"{profile['short']} short and {profile['long']} long out of "
                f"{profile['count']} sentences):\n" + "\n".join(asks)
            )

    if not sections:
        return ""
    return (
        "\n\n=== EXACT MEASUREMENTS FOR THIS ARTICLE ===\n"
        "These were computed by counting the article, so the figures are exact "
        "and complete. Act on these specific items. Do not search for others, "
        "and do not try to count anything yourself.\n\n"
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

    # Compare PROSE, not bytes. Raw HTML length is a bad proxy: article 285 is
    # ~8k of text wrapped in ~36k of inline Tailwind CSS, so a pass that
    # legitimately stripped the style bloat came back at 19% of the source and
    # was rejected as truncated even though every heading and paragraph survived.
    # Stripping tags first measures what a reader actually loses.
    source_text = _visible_text(source_html)
    output_text = _visible_text(output_html)
    if len(output_text) < len(source_text) * MIN_OUTPUT_RATIO:
        raise Exception(
            f"{stage} returned {len(output_text)} chars of text from {len(source_text)} "
            f"(under {MIN_OUTPUT_RATIO:.0%}) — content was lost, refusing to save"
        )

    return output_html
