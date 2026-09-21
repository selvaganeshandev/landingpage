# Content Humanisation — How It Works

How PromptMaxx turns AI-generated articles into copy that reads as human-written
and survives AI-detector scoring.

Built in `38e71f35` (Sep 4, 2026) on top of the original three-pass pipeline.

**Source files**

| File | Role |
|---|---|
| `backend/content/views.py` | Orchestration — the background runner, the score-refine loop, brand profile assembly |
| `backend/content/claude_content_generator.py` | The prompts, the model rotation, the freeze/restore, Pass 3 |
| `backend/content/humanise_validation.py` | Guards and the Python-side style analysis (Django-free, directly testable) |
| `backend/llm_monitor/settings.py` | Tunables |

---

## The pipeline

```
pre_humanise_content (the original article, always kept)
        │
        ├─ freeze <table> / <img>  ──────────────► locked HTML-comment placeholders
        │
        ├─ Pass 1  humanise_content()          19 rules + strong-voice layer    [LLM]
        ├─ Pass 2  refine_humanised_content()  5 fixes + exact violation list   [LLM]
        ├─ Pass 3  post_process_content()      deterministic regex fixes     [Python]
        │
        ├─ Score-refine loop  ×N               rotate models, keep best score   [LLM]
        │
        ├─ restore <table> / <img>  ◄────────────  verbatim
        ├─ expand back to the word-count label
        │
        └─► content_html  +  human_detection_score
```

Every stage is **guarded**: a pass that fails validation or over-compresses keeps
the previous good version rather than failing the job.

---

## 1. Entry point and concurrency

Humanisation takes 1–2 minutes of LLM time, so it runs off-request in a
**bounded thread pool** — `backend/content/views.py:611`.

```python
_HUMANISE_MAX_WORKERS = getattr(settings, 'HUMANISE_MAX_CONCURRENCY', 4)
_HUMANISE_POOL = ThreadPoolExecutor(max_workers=_HUMANISE_MAX_WORKERS,
                                    thread_name_prefix='humanise')
```

**Why a pool, not bare threads.** It used to spawn one daemon thread per click
with no ceiling. N articles humanised at once meant N threads, each holding a
database connection and issuing two LLM calls of up to 128k output tokens.
Nothing bounded that but how fast a user could click. Work beyond the limit now
queues instead of spawning.

Django DB connections are per-thread, so the runner closes its connection on exit.

Bulk upload is unaffected — `_run_bulk_generation_queue` runs one thread per
batch, walks items serially, and does not humanise.

---

## 2. Freezing tables and images

Before any rewrite, `_freeze_protected()` lifts `<table>` and `<img>` blocks out
(`claude_content_generator.py:3812`).

```python
_PROTECT_RE = re.compile(r'<table\b.*?</table>|<img\b[^>]*/?>', re.IGNORECASE | re.DOTALL)
# each match → <!--PMX_FROZEN_0-->, <!--PMX_FROZEN_1--> ...
```

**Why.** The sentence-length rule, the list-reduction rule and the no-repeat-word
rule all mangle table cells. Images are atomic and were being dropped.

**Why HTML comments specifically.** `_sanitize_html_response`,
`_convert_markdown_to_html` and the Pass 3 post-processing all leave comments
intact, and the dash-cleanup regex only matches em/en dashes — not the ASCII
hyphens in `<!-- -->`.

`_restore_protected()` puts them back. Any placeholder a pass dropped is
**re-appended at the end**, so a table or image is never lost even if the model
deleted its marker.

Validation runs on the frozen text throughout, so the length-ratio check stays
consistent pass to pass.

---

## 3. Pass 1 — full humanisation (LLM)

`humanise_content()` — `claude_content_generator.py:3851`. One call, 19 rules.

### The rules, grouped

**Typography**

1. Replace every em-dash (—) and en-dash (–) with a comma, semicolon or full stop.
5. Straight quotes → curly quotes.

**Rhythm — the core anti-detection mechanic**

2. Alternating sentence-length pattern: `short, short, short, long, short, short, long…`
   - **short = 8–10 words**, **long = 15–25 words** (roughly a 70/30 ratio)
   - **Forbidden: 11–14 words** (the "gap zone"), under 7, over 25
12. Natural variation — slightly imperfect flow, varied pacing.

**Structure**

6. **Mandatory section variation.** Similar subsections must not all have the same
   paragraph count. Fixed formula: sections 1/5/9 → 2 paragraphs, 2/4/7/10 → 3,
   3/6/8 → 4. Uniform counts are an explicit reject condition.
13. Preserve `<ul>`/`<ol>` exactly — never flatten `<li>` into prose.
14. **Strict 2-item inline list rule.** Any comma-separated series of 3+ items
    *inside prose* is cut to exactly 2. "Three items in a row is an AI detection
    fingerprint." Items inside `<ul>`/`<ol>` are exempt. The prompt ships ~17
    worked examples.
15. **Forward-guiding endings.** Every section must end with an action or next
    step, not a flat fact.

**Vocabulary**

7. **Banned words** — `remain`, `especially`, `particularly`, `may`, `can`,
   `leverage`, `comprehensive`, `remarkably`, `significantly`, `furthermore`,
   `moreover`, `additionally`, `utilize`/`utilise`. Plus: **never open a sentence
   with a gerund** (-ing word), with restructure examples.
8. No buzzwords (cutting-edge, game-changer, seamlessly, revolutionise…) unless
   backed by specific data.
9. No clichés ("In today's world", "Needless to say", "It's no secret that").
10. No rhetorical questions, no "not just… but also…". Never open or close a
    section with a question.
16. **No-repeat rule.** No adjective or adverb appears more than once in the whole
    article. Ships a ~30-entry table of offenders with one-time-use synonyms, plus
    two exemption lists — domain vocabulary (`virtual`, `blockchain`, `NFT`…) and
    fixed phrases (`strong password`, `real estate`, `mobile-first`…) that are not
    descriptors.

**Voice**

3. Conversational, personalised, non-preachy.
4. Keywords and anchors distributed evenly, not clustered.
11. One idea per sentence. **No semicolons anywhere.** No joined actions
    ("Download the app and create a password" → two sentences). No colons
    introducing an inline list.

**Protective (must not violate)**

17. Preserve all HTML structure.
18. Preserve all `<a>` tags — exact href, anchor text, attributes.
19. Preserve all keyword placements.
20. **Length preservation** — final word count within 5% of input. Rules 2, 14 and
    6 all *remove* words, so every cut must be balanced by adding depth nearby
    (a concrete detail, a short example) — never filler or invented facts.

The prompt closes with a **checklist of 13 critical checks** the model runs over
its own output before returning.

### The strong-voice layer

Appended to Pass 1 when `HUMANISE_STRONG_MODE=True` (the default) —
`claude_content_generator.py:2910`. Inserted *before* the final "Return ONLY the
transformed HTML" directive so that stays last.

| | Rule |
|---|---|
| **A** | **Contractions** — `it's`, `you'll`, `don't`, `that's`. Roughly one every 2–3 sentences, never inside a fixed phrase or target keyword. *"This is the single strongest human signal, so do not skip it."* |
| **B** | **Varied openings** — no two consecutive sentences begin with the same word or structure |
| **C** | **Concrete over generic** — "a quick five-minute round" beats "a short session". Concrete detail raises unpredictability, which is what detectors miss |
| **D** | **Light natural asides** — at most one per major section, factual and professional |
| **E** | **Tone** — natural, never casual-sloppy. Never trade accuracy for voice |

It **defers explicitly** to the protective rules (17–19), the sentence-length
pattern (2), the banned words (7), one-idea/no-semicolon (11) and
no-rhetorical-question (10). On conflict, the original rules win.

Set `HUMANISE_STRONG_MODE=False` to revert to the exact original prompt — no code
change, no deploy.

---

## 4. Pass 2 — surgical refinement (LLM)

`refine_humanised_content()` — `claude_content_generator.py:4035`. Targets the
five things Pass 1 consistently fails.

1. **Descriptor repeats** (most important) — with the key insight that a synonym,
   once used as a replacement, is *spent* and cannot be reused. The prompt shows
   the wrong approach (replacing three "different"s with three "separate"s) beside
   the right one.
2. **Section paragraph variation** — the merge/split formula, stated as a
   structural change: actually add or remove `<p>` tags.
3. **Sentence length** — gap-zone sentences.
4. **-ing sentence starts.**
5. **Flat section endings.**

### The Python/LLM split — the most important design decision

Rules 3 and 4 ask the model to *find* sentences by counting words. **Measured
across 12 articles over five months: it never worked, on any model.** The gap
zone went *up* as often as down (14%→23%, 11%→20%, 17%→33%) and -ing openings
frequently *increased* (4→10, 2→8, 4→9).

The cause: the prompt asks the model to count — *"count the words in every
sentence you write"*, *"keep a mental tally"* — which is the one thing it is worst
at, and which also drove the runaway reasoning that emptied responses entirely
(see §9).

So the work is split:

> **Python finds the violations. The model rewrites the specific sentences it is handed.**

`find_style_violations()` — `humanise_validation.py:104` — returns the actual
offending sentences, not counts:

```python
GAP_ZONE   = (11, 14)   # forbidden
SHORT_BAND = (8, 10)    # target for cuts
LONG_BAND  = (15, 25)   # target for expansions
```

It also carries a `_NOT_GERUNDS` set — `nothing`, `something`, `everything`,
`king`, `during`, `building`… — so "Nothing changed." is not reported as an -ing
violation and mangled into "The nothing changed."

`format_violations_for_prompt()` renders them as a block, capped at **12 per
category** (a hundred quoted sentences would push the model straight back into
the unfocused scanning that never worked):

```
=== EXACT VIOLATIONS FOUND IN THIS ARTICLE ===
These were located by an automated word count, so the list is complete
and accurate. Fix these specific sentences. Do not search for others.

SENTENCES IN THE FORBIDDEN 11-14 WORD GAP ZONE (7 found — fix every one listed):
  Rewrite each to 8-10 words (cut) or 15-25 words (add detail).
  [12 words] "The platform offers a range of options for players who want…"
```

**Nothing is auto-rewritten in Python.** Programmatically restructuring prose
produces garbage ("Nothing is worse" → "The nothing is worse"), so detection feeds
the prompt rather than replacing it. It plays to the half of the model that works:
bad at locating a sentence, good at rewriting a named one.

---

## 5. Pass 3 — deterministic fixes (Python, no LLM)

`post_process_content()` — `claude_content_generator.py:4245`. Fixes what the
model handles inconsistently, with zero variance and zero cost.

1. **Em/en dashes** (rule 1)
2. **Semicolons** (rule 11) — `"; word"` → `". Word"`
3. **Protected phrase restoration** — undoes over-eager synonym swaps
   ("formidable password" → "strong password")
4. **Descriptor deduplication** (rule 16)

### Two bugs fixed in the dash handling

The original blanket `\s*—\s*` → `'. '` had two failures:

- It fired regardless of what preceded the dash, so *"Backwaters, Hills & — Wildlife"*
  became *"Backwaters, Hills &. Wildlife"*. A full stop after a symbol is a typo,
  and it shipped in headings.
- It ran over the whole HTML string **including tags**, so an em-dash inside an
  attribute (`class="x—y"`) became `class="x. y"` — silently breaking markup.

Now only text between tags is touched (`_apply_outside_tags`), and a dash becomes
a sentence break **only when it actually joins two words**:

```python
text = re.sub(r'(\w)\s*[—–]\s*(\w)', lambda m: m.group(1) + '. ' + m.group(2).upper(), text)
text = re.sub(r'\s*[—–]\s*', ' ', text)   # anything left collapses to a space
```

---

## 6. The guarded score-refine loop

`views.py:795`. After the three fixed passes, if an AI detector is available and
the text still scores too AI-like, run more refines and **keep the best-scoring
version**.

```python
HUMAN_SCORE_TARGET = config('HUMANISE_SCORE_TARGET', default=85.0, cast=float)
MAX_SCORE_REFINES  = config('HUMANISE_MAX_REFINES',  default=4,    cast=int)
```

Raised from 70/2 to 85/4 to push harder against the detector.

### Multi-model rotation — the anti-fingerprint mechanic

Passes 1–3 were all done by the paid Claude model. Running a **different model on
each refine breaks the single-model writing pattern that detectors key on.**

```python
_HUMANISE_REFINE_MODELS_DEFAULT = ['openai/gpt-5-mini', 'google/gemini-2.5-flash']
pass_model = refine_models[i % len(refine_models)]
```

Overridable via `HUMANISE_REFINE_MODELS` (comma-separated slugs).

Every model still goes through `_create_with_fallback()` — paid model first for
quality, free models on failure (e.g. a 402 out-of-credits) — so **an unavailable
slug can never fail the job.** That is what lets a funded OpenRouter key give full
paid quality while a $0 balance still works on free models instead of erroring.

### Why it can only help

- Skips silently when no detector key is set, or the text can't be scored
- Capped at `MAX_SCORE_REFINES`
- Every refine goes through `_pass_or_keep` (validation + shrink guard)
- A detector hiccup mid-loop just stops, keeping the best version so far
- A candidate is adopted **only if it scores higher**

The final score is stored on the record — `human_detection_score`,
`ai_detection_score`, and a `Human-written` / `AI-generated` label at the 50 mark.

---

## 7. Length preservation

Humanisation *shrinks* articles: rule 2 cuts sentences to 8–10 words, rule 14 cuts
3-item lists to 2, rule 6 merges paragraphs. A piece generated at 800–1000 words
came out around 600.

Two defences:

1. **In the prompt** — rule 20 in Pass 1, and a matching clause in Pass 2.
2. **Belt-and-braces backstop** — `views.py:855`. If the article still dropped
   below the label's minimum, `_ensure_min_word_count()` expands it back by
   **deepening existing sections** — no new structure, no invented facts.

The restore runs on the **restored** HTML (after tables and images are back), so
the expander's own rules protect them. Fully guarded: `_ensure_min_word_count`
never raises and returns the best version on any failure.

---

## 8. Guards — why they exist

`backend/content/humanise_validation.py`. From the module docstring:

> Pass 1 returned an empty string, Pass 2 apologised about being sent no HTML, and
> **253 characters of apology replaced a 10,192-character article** under a
> `completed` status. Nothing in the pipeline looked at what came back.

Kept free of Django and SDK imports so it can be tested directly:
`python tests/standalone/backend/content/test_humanise_validation.py`

### `raise_if_truncated(stage, response, source_html)`

Reads `stop_reason == 'length'` from the provider — the exact signal, available
only at the call site. Whatever came back is a fragment: either empty (the whole
budget went on hidden reasoning) or an article ending mid-sentence. Both otherwise
read as a perfectly successful response.

Deliberately **not** treated as transient — a ceiling that is too small is
deterministic, so retrying just costs the same failure again.

### `validate_pass_output(stage, source_html, output_html)`

Three structural checks. Matching apology wording was considered and rejected —
three different phrasings appeared across two passes, so such a list rots the
moment the model rephrases. What doesn't change is that a humanised article is
non-empty, is HTML, and is about as long as its input.

| Check | Catches |
|---|---|
| Non-empty | A dead pass |
| Contains `<` | Prose written *about* the task — an apology or refusal, whatever it says |
| Visible text ≥ 50% of input | Content loss |

The ratio check compares **prose, not bytes**. Raw HTML length is a bad proxy:
article 285 is ~8k of text wrapped in ~36k of inline Tailwind CSS, so a pass that
legitimately stripped the style bloat came back at 19% of source and was rejected
as truncated even though every heading and paragraph survived. Stripping tags
first measures what a reader actually loses.

### `output_ceiling(content_html)`

```python
needed = (len(content_html or '') // 4) * 2          # ~4 chars/token, doubled
return max(8192, min(128000, needed))
```

The humanise calls were pinned at **8192** output tokens — an eighth of one
percent of the context window and a fifteenth of the output ceiling, almost
certainly a leftover from an older Anthropic model where 8192 *was* the limit.
That cap is why article 285 (44,227 chars) came back truncated mid-CSS: a rewrite
emits roughly what it was given, and 8192 tokens is only ~30,000 characters.
**Every article over that silently lost its tail.**

Deliberately **not** a flat 128,000. Billing follows tokens actually generated, so
a high ceiling is free when output is short — but this same call demonstrated
runaway generation once already, burning the entire ceiling and emitting nothing.
A ceiling proportional to the input bounds the blast radius.

### `_pass_or_keep` — graceful degradation

`views.py:759`. A pass that fails validation, or compresses below 50% of the
**original** (not just the previous pass), keeps the previous good version.

Strictly safer than the old behaviour, where any bad pass aborted humanisation and
reverted the article to its un-humanised state.

---

## 9. `NO_REASONING` — the finding that unblocked all of this

`claude_content_generator.py:47`.

Reasoning tokens bill against `max_tokens` and are spent **before** any visible
text. The humanisation prompts demand exhaustive counting — *"count the words in
every sentence"*, *"keep a mental tally"* — which drives that spend unbounded: the
model reasons until the ceiling is hit and returns an **empty content field with
`finish_reason='length'`**. A total failure shaped exactly like a successful
response.

Measured on production 2026-07-27, `anthropic/claude-sonnet-5`, against the real
10,192-char article and the 13,877-char Pass 1 prompt:

| Attempt | Result |
|---|---|
| ceiling 8192 / 16000 / 32000 | `finish=length`, **0 chars out**. Raising the ceiling does not help — it only wastes more |
| `{"max_tokens": 1024}` on reasoning | still 0 chars. The reasoning cap is not honoured |
| `{"exclude": True}` | still 0 chars. Strips reasoning from the *response* while still generating and billing it |
| **`{"enabled": False}`** | `finish=stop`, 3,937 tokens, **102% of input** ✓ |

The trigger is **the prompt, not the article** — it reproduces on a 1,500-char
excerpt, while a short system prompt succeeds on the full article. Same mechanism
already documented for `gpt-5-mini` in `engine/core/analytics_helpers.py`.

```python
NO_REASONING = {'enabled': False}
```

Passed on every humanise and refine call.

---

## 10. Brand grounding

Separate from humanisation but shipped alongside it, and it feeds the same
generation path.

`_build_brand_profile(domain)` — `views.py:616` — assembles a block from the
domain's **own stored fields**, so content is grounded in this client's real
specifics instead of generic filler. Industry-agnostic: it just reflects whatever
the domain has stored.

```
- About the brand: …          - Target audience: …
- Industry / niche: …         - Use cases: …
- Business model: …           - Buying criteria: …
- Products / services: …      - Why customers choose them: …
- Regions served: …           - Common objections to address: …
- Price positioning: …
- Brand values: …
```

Fully defensive: every field optional (most domains predate some of them), JSON
list/dict fields flattened safely, **returns `''` when nothing is filled** — in
which case the generator behaves exactly as before. Never raises.

`_brand_context_block()` wraps it for the prompt
(`claude_content_generator.py:2948`):

> Ground the article in the real brand details below. Reference concrete specifics
> from this profile (its actual offerings, audience, region, price positioning and
> differentiators) instead of generic, could-be-anyone statements. **Do NOT invent
> facts that contradict this profile**; where a detail is missing, stay accurate
> and write around it rather than fabricating.

---

## 11. Configuration

All tunable without a deploy.

| Setting | Default | Effect |
|---|---|---|
| `HUMANISE_STRONG_MODE` | `True` | The natural-voice layer on Pass 1. `False` reverts to the exact original prompt |
| `HUMANISE_REFINE_MODELS` | `''` | Comma-separated slugs for the refine rotation. Empty → `gpt-5-mini, gemini-2.5-flash` |
| `HUMANISE_SCORE_TARGET` | `85.0` | Human-likeness score the loop chases |
| `HUMANISE_MAX_REFINES` | `4` | Cap on guarded refine passes |
| `HUMANISE_MAX_CONCURRENCY` | `4` | Thread-pool size |
| `CONTENT_MAX_TOKENS` | `64000` | Paid-model output ceiling |
| `CONTENT_FREE_MAX_TOKENS` | `8192` | Free-model output ceiling (clamped on fallback) |

---

## 12. Design principles

These are the ideas worth carrying to anything similar.

1. **Never let a model count.** It is the thing LLMs are worst at, and asking
   drives runaway reasoning. Count in Python — exact, instant, free — and hand the
   model the specific sentences. Detection in code, rewriting in the model.

2. **Detect, don't auto-fix, prose.** Programmatic restructuring produces garbage
   ("Nothing is worse" → "The nothing is worse"). Detection feeds the prompt; it
   does not replace it.

3. **Rotate models to break the fingerprint.** Detectors key on a single model's
   writing pattern. A different brain per pass is cheap and effective.

4. **Validate structurally, not by wording.** Any list of apology phrasings rots
   the moment the model rephrases. Non-empty, is-HTML, is-long-enough do not rot.

5. **Compare prose, not bytes.** 36k of inline CSS around 8k of text makes every
   byte-based ratio wrong.

6. **Every stage keeps the previous good version.** A bad pass should degrade the
   result, never destroy the article.

7. **Make the aggressive parts reversible from the environment.** `STRONG_MODE`,
   the score target, the refine cap and the model list are all one env var away
   from being dialled back.

8. **Guard the optional work so it can only help.** The score loop skips silently
   with no detector, caps its attempts, adopts a candidate only if it scores
   higher, and never fails the job.

9. **Scale ceilings to the input.** A flat maximum is free when output is short —
   until runaway generation burns all of it. Proportional bounds the blast radius.
