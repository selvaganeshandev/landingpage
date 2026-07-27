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


print(f"\n{len(_PASS)} passed, {len(_FAIL)} failed")
if _FAIL:
    for name in _FAIL:
        print(f"  FAILED: {name}")
sys.exit(1 if _FAIL else 0)
