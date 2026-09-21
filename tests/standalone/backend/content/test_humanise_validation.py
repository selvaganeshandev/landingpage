"""
Tests for the humanisation output guards.

These exist because of a real production incident on 2026-07-27: Pass 1 of the
humanise pipeline returned an EMPTY string (anthropic/claude-sonnet-5 spent its
whole token budget on hidden reasoning), Pass 2 received that empty string and
replied apologising about being sent no HTML, and those 253 characters of apology
were written over a 10,192-character article — with the job marked 'completed'.

Nothing in the pipeline inspected what came back. These guards are that check,
and the cases below are the shapes the failure actually took:

  - empty output ....................... Pass 1's real reply
  - prose with no HTML tag ............. Pass 2's apology
  - truncated output ................... article 285, cut to 49% mid-CSS
  - stop_reason == 'length' ............ the exact signal for both of the above

The module under test imports nothing from Django or any SDK, so this runs
standalone with no settings, database or network.

Run:  python tests/standalone/backend/content/test_humanise_validation.py
"""
import importlib.util
import sys
from pathlib import Path

_PATH = Path(__file__).resolve().parents[4] / 'backend' / 'content' / 'humanise_validation.py'
_spec = importlib.util.spec_from_file_location('humanise_validation_undertest', _PATH)
HV = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(HV)

_PASS, _FAIL = [], []


def check(name, condition, detail=''):
    (_PASS if condition else _FAIL).append(name)
    print(f"  {'PASS' if condition else 'FAIL'}  {name}"
          f"{('  -> ' + str(detail)) if detail and not condition else ''}")


def rejects(name, source, output):
    """The guard must raise for this (source, output) pair."""
    try:
        HV.validate_pass_output("Pass 1", source, output)
        check(name, False, "accepted, should have raised")
    except Exception as exc:
        check(name, True)
        return str(exc)
    return ""


def accepts(name, source, output):
    try:
        result = HV.validate_pass_output("Pass 1", source, output)
        check(name, result == output, result)
    except Exception as exc:
        check(name, False, f"raised: {exc}")


# A realistic humanised article: ~1.4k chars of tagged HTML.
ARTICLE = "<h2>Kerala Travel</h2>\n" + ("<p>Backwaters, tea hills and quiet beaches.</p>\n" * 30)


class _Block:
    def __init__(self, text):
        self.text = text


class _Response:
    """Stands in for the adapter's Message dataclass."""

    def __init__(self, stop_reason, text=""):
        self.stop_reason = stop_reason
        self.content = [_Block(text)]


print("\nhumanise_validation — validate_pass_output")

rejects("empty string is rejected", ARTICLE, "")
rejects("whitespace-only output is rejected", ARTICLE, "   \n\t  ")
rejects("None output is rejected", ARTICLE, None)

# The exact apology that overwrote article 1806 in production.
APOLOGY = ("No HTML content was provided in your message. Please paste the HTML content "
           "you'd like me to review and fix, and I'll apply the 5 specified fixes "
           "(descriptor repeats, paragraph variation, sentence length, -ing sentence "
           "starts, and flat section endings).")
msg = rejects("the real production apology is rejected", ARTICLE, APOLOGY)
check("apology is rejected for having no HTML, not for its wording",
      "no HTML tags" in msg, msg)

# Wording-independence is the point of the structural check: all three phrasings
# seen in production must be caught, and so must one nobody has seen yet.
for variant in (
    "No HTML content was included in your message.",
    "No HTML content was provided to review.",
    "I'm sorry, but I didn't receive any content to work with.",
    "Understood. Please go ahead and share the article.",
):
    rejects(f"prose variant rejected: {variant[:38]}...", ARTICLE, variant)

rejects("output truncated to 20% is rejected", ARTICLE, ARTICLE[:len(ARTICLE) // 5])
rejects("output truncated to 49% is rejected (article 285's shape)",
        ARTICLE, ARTICLE[:int(len(ARTICLE) * 0.49)])

accepts("a same-length rewrite is accepted", ARTICLE, ARTICLE.replace("quiet", "calm"))
accepts("a slightly longer rewrite is accepted (measured 102% in prod)",
        ARTICLE, ARTICLE + "<p>One more paragraph of rewritten copy.</p>")
accepts("a rewrite at 60% is accepted — shrinking is allowed, gutting is not",
        ARTICLE, ARTICLE[:int(len(ARTICLE) * 0.6)])

# A short-but-valid output must not be punished for being short in absolute terms;
# the check is proportional to its own input.
accepts("a short input with a proportional output is accepted",
        "<p>Tiny.</p>", "<p>Tiny rewritten.</p>")

# Article 285's real shape: ~8k of prose inside ~36k of inline Tailwind CSS. A
# pass that strips the style bloat keeps every word and drops 80% of the BYTES,
# so a byte-ratio check rejects a perfectly good result. The ratio is measured on
# visible text for exactly this reason.
_STYLE = ('style="--tw-ring-offset-shadow: 0 0 #0000; --tw-ring-shadow: 0 0 #0000; '
          '--tw-numeric-spacing: ; --tw-numeric-fraction: ; --tw-ring-inset: ; '
          '--tw-ring-offset-width: 0px; --tw-ring-offset-color: #fff;"')
BLOATED = "<div>" + "".join(
    f"<p {_STYLE}>Real prose that a reader actually sees on the page.</p>" for _ in range(20)
) + "</div>"
CLEANED = "<div>" + ("<p>Real prose that a reader genuinely sees on the page.</p>" * 20) + "</div>"
check("the bloated fixture is mostly markup",
      len(CLEANED) < len(BLOATED) * 0.75, (len(BLOATED), len(CLEANED)))
accepts("stripping inline CSS is not mistaken for truncation", BLOATED, CLEANED)
rejects("but genuinely losing the prose is still caught",
        BLOATED, '<div><p>Real prose that a reader actually sees.</p></div>')

print("\nhumanise_validation — raise_if_truncated")

try:
    HV.raise_if_truncated("Humanisation", _Response("stop", ARTICLE), ARTICLE)
    check("stop_reason='stop' passes through", True)
except Exception as exc:
    check("stop_reason='stop' passes through", False, exc)

try:
    HV.raise_if_truncated("Humanisation", _Response("length", ""), ARTICLE)
    check("stop_reason='length' with empty output raises", False, "no exception")
except Exception as exc:
    check("stop_reason='length' with empty output raises", True)
    check("the truncation error names the real reason",
          "stop_reason='length'" in str(exc), exc)

try:
    # Article 285's shape: plenty of text, still truncated. The ratio check would
    # miss this at 55%; stop_reason catches it regardless of how much came back.
    HV.raise_if_truncated("Humanisation", _Response("length", ARTICLE), ARTICLE)
    check("stop_reason='length' raises even when output looks substantial", False, "no exception")
except Exception as exc:
    check("stop_reason='length' raises even when output looks substantial", True)

try:
    HV.raise_if_truncated("Humanisation", _Response(None), ARTICLE)
    check("a missing stop_reason is not treated as truncation", True)
except Exception as exc:
    check("a missing stop_reason is not treated as truncation", False, exc)


print("\nhumanise_validation — output_ceiling")

check("a small article still gets the 8192 floor",
      HV.output_ceiling("<p>short</p>") == 8192, HV.output_ceiling("<p>short</p>"))
# Article 285: 44,227 chars needed ~11k output tokens and got 8192, so it truncated.
check("article 285's size clears the token count it actually needed",
      HV.output_ceiling("x" * 44227) >= 11057, HV.output_ceiling("x" * 44227))
# The largest article in the table, 201,276 chars.
check("the largest real article stays within the model's 128k ceiling",
      HV.output_ceiling("x" * 201276) <= 128000, HV.output_ceiling("x" * 201276))
check("a gigantic input is clamped, not passed through",
      HV.output_ceiling("x" * 5_000_000) == 128000, HV.output_ceiling("x" * 5_000_000))
check("the ceiling grows with the article",
      HV.output_ceiling("x" * 100000) > HV.output_ceiling("x" * 50000))

print("\nhumanise_validation — find_style_violations")

# The gap-zone, too-short and too-long categories were REMOVED on 2026-09-21.
# Measured across 200 articles holding both their pre- and post-humanise text,
# the 11-14 word ban GREW that band from 16.8% to 22.8%, and 58% of humanised
# articles still came out under the 0.45 burstiness a detector reads as human.
# The tails the rule forbade are what would fix that, so they are now requested
# rather than banned.

SAMPLE = (
    "<p>Kerala is lovely.</p>"
    "<p>The backwaters near Alleppey stay calm right through the summer months.</p>"
    "<p>Booking a houseboat early saves money.</p>"
    "<p>Travellers who want hill air head to Munnar, where the tea estates roll "
    "out across the slopes and the mornings turn cold enough for a jacket.</p>"
)
v = HV.find_style_violations(SAMPLE)
check("the gap-zone category is gone", 'gap_zone' not in v, sorted(v))
check("the too-short category is gone", 'too_short' not in v, sorted(v))
check("the too-long category is gone", 'too_long' not in v, sorted(v))
check("an -ing sentence opening is still caught",
      any(s2.startswith('Booking') for _, s2 in v['ing_starts']), v['ing_starts'])

# The blocklist matters: these open with -ing words that are not gerunds, and
# asking the model to "restructure" them produces "The nothing changed".
for word in ("Nothing", "Something", "Everything", "Morning", "During"):
    sample = f"<p>{word} about this sentence should ever be flagged by rule four.</p>"
    hits = HV.find_style_violations(sample)['ing_starts']
    check(f"'{word}' is not mistaken for a gerund opening", not hits, hits)

print("\nhumanise_validation — burstiness")

EVEN = "<p>" + " ".join(
    ["The market moved higher today across every major sector index."] * 8) + "</p>"
UNEVEN = (
    "<p>Markets rose. The Securities and Exchange Board of India has spent much of "
    "2024 and 2025 rewriting the rulebook for derivatives trading, a process that "
    "touched every broker in the country and reshaped how retail participation is "
    "measured. It worked. Nine out of ten retail traders lost money.</p>"
)
b_even, b_uneven = HV.burstiness(EVEN), HV.burstiness(UNEVEN)
check("identical-length sentences score 0 burstiness", b_even == 0.0, b_even)
check("varied sentences score far higher", b_uneven > HV.BURSTINESS_TARGET, b_uneven)
check("an empty article does not raise", HV.burstiness("") == 0.0)
check("a single sentence does not raise", HV.burstiness("<p>Only one here.</p>") == 0.0)

pe, pu = HV.length_profile(EVEN), HV.length_profile(UNEVEN)
check("even prose is asked for short sentences", pe['need_short'] >= 1, pe)
check("even prose is asked for long sentences", pe['need_long'] >= 1, pe)
check("varied prose is asked for nothing",
      pu['need_short'] == 0 and pu['need_long'] == 0, pu)
check("a run of same-length sentences is caught",
      len(HV.find_style_violations(EVEN)['monotone_runs']) >= 1)
check("varied prose has no monotone run",
      not HV.find_style_violations(UNEVEN)['monotone_runs'])

print("\nhumanise_validation — format_violations_for_prompt")

check("a clean article produces no violation block",
      HV.format_violations_for_prompt(
          {'ing_starts': [], 'monotone_runs': [], 'profile': HV.length_profile(UNEVEN)}) == "")

block = HV.format_violations_for_prompt(HV.find_style_violations(EVEN))
check("the block reports the measured burstiness", "measured 0.00" in block, block[:200])
check("the block asks for short sentences", "UNDER 8" in block, block[:400])
check("the block asks for long sentences", "OVER 28" in block, block[:400])
check("the block forbids levelling the rest out", "Do NOT even out" in block)
check("the model is told not to count", "do not try to count anything yourself" in block)

# The whole point is a short actionable list, not a wall of quotes.
many = {'ing_starts': [(12, f"Sentence {i} opens with a gerund and needs restructuring here.")
                       for i in range(40)],
        'monotone_runs': [], 'profile': HV.length_profile(UNEVEN)}
big_block = HV.format_violations_for_prompt(many, max_each=12)
check("long violation lists are capped", big_block.count('[12 words]') == 12,
      big_block.count('[12 words]'))
check("the cap says how many were omitted", "and 28 more" in big_block)

print(f"\n{len(_PASS)} passed, {len(_FAIL)} failed")
if _FAIL:
    for name in _FAIL:
        print(f"  FAILED: {name}")
sys.exit(1 if _FAIL else 0)
