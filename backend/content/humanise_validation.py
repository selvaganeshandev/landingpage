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

# Below this share of the input, the output is truncated rather than rewritten.
# Humanisation preserves all HTML, links and keywords, so a pass returns roughly
# what it was given — measured 102% and 101% on production. Half is a
# deliberately loose floor that only a broken pass falls through.
MIN_OUTPUT_RATIO = 0.5


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
