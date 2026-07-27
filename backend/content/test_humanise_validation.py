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

Run:  python content/test_humanise_validation.py     (from the backend/ directory)
"""
import importlib.util
import os
import sys

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'humanise_validation.py')
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

SAMPLE = (
    "<p>Kerala is lovely.</p>"                                            # 3 words  -> too short
    "<p>The backwaters near Alleppey stay calm right through the summer months.</p>"  # 11 -> gap zone
    "<p>Booking a houseboat early saves money.</p>"                       # 6 -> too short + -ing start
    "<p>Travellers who want hill air head to Munnar, where the tea estates roll "
    "out across the slopes and the mornings turn cold enough for a jacket.</p>"  # long, fine
)
v = HV.find_style_violations(SAMPLE)
gap_words = [n for n, _ in v['gap_zone']]
check("an 11-word sentence is caught in the gap zone", 11 in gap_words, v['gap_zone'])
check("a sentence under 7 words is caught", len(v['too_short']) >= 1, v['too_short'])
check("an -ing sentence opening is caught",
      any(s.startswith('Booking') for _, s in v['ing_starts']), v['ing_starts'])

# The blocklist matters: these open with -ing words that are not gerunds, and
# asking the model to "restructure" them produces "The nothing changed".
for word in ("Nothing", "Something", "Everything", "Morning", "During"):
    sample = f"<p>{word} about this sentence should ever be flagged by rule four.</p>"
    hits = HV.find_style_violations(sample)['ing_starts']
    check(f"'{word}' is not mistaken for a gerund opening", not hits, hits)

check("a clean article produces no violation block",
      HV.format_violations_for_prompt(
          {'gap_zone': [], 'ing_starts': [], 'too_short': [], 'too_long': []}) == "")

block = HV.format_violations_for_prompt(v)
check("the block quotes the offending sentence verbatim",
      "backwaters near Alleppey" in block, block[:200])
check("the block states the rule the model must apply",
      "8-10 words" in block and "15-25 words" in block, block[:200])

# The whole point is a short actionable list, not a wall of quotes.
many = {'gap_zone': [(12, f"Sentence number {i} sits in the eleven to fourteen word band here.")
                     for i in range(40)],
        'ing_starts': [], 'too_short': [], 'too_long': []}
big_block = HV.format_violations_for_prompt(many, max_each=12)
check("long violation lists are capped", big_block.count('[12 words]') == 12,
      big_block.count('[12 words]'))
check("the cap says how many were omitted", "and 28 more" in big_block)

print(f"\n{len(_PASS)} passed, {len(_FAIL)} failed")
if _FAIL:
    for name in _FAIL:
        print(f"  FAILED: {name}")
sys.exit(1 if _FAIL else 0)
