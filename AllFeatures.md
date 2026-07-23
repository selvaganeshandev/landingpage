# AllFeatures

A page-by-page catalogue of every feature in LLM Monitor: what each element
shows, where its data comes from, and how it is calculated.

---

## Table of contents

- [Insights (`/insights`)](#insights-insights)
  - [Page filters](#page-filters)
  - [1. AI Visibility](#1-ai-visibility)

---

# Insights (`/insights`)

**Route:** `frontend/src/App.tsx:87` → renders `pages/Dashboard.tsx`
**Permission:** `MODULES.DASHBOARD`
**API:** `GET /analytics/dashboard/summary/`
(`frontend/src/services/api.ts:1253` → `backend/analytics/views_dashboard.py:440`)

## Page filters

All four filters refetch the entire page (`Dashboard.tsx:296-301`).

| Filter | Parameter | Behaviour |
|---|---|---|
| Domain selector | `domain_id` | Required. From Zustand store, falls back to the server-side active domain |
| LLM selector | `llm_model` | Single platform, or all platforms when omitted |
| Date range | `start_date` + `end_date` | Applied only when **both** dates are picked; a partial range is ignored |
| Time period | `days` | Default 30. Ignored when an explicit date range is applied |

### LLM selector

The dropdown (`Dashboard.tsx:58`) sends a lowercase slug. The backend maps it to
the exact platform string stored in the database (`views_dashboard.py:460`). This
map must stay in sync with the engine's authoritative map
(`engine/core/domain_processor.py:833`), which writes the values.

| Dropdown label | Slug sent | DB platform string |
|---|---|---|
| All LLMs | *(omitted)* | — no filter — |
| ChatGPT | `chatgpt` | `ChatGPT` |
| Gemini | `gemini` | `Google Gemini` |
| Claude | `claude` | `Claude` |
| Perplexity | `perplexity` | `Perplexity` |
| Grok | `grok` | `Grok` |
| DeepSeek | `deepseek` | `DeepSeek` |

Which platforms actually produce data is controlled by `ENABLED_PLATFORMS`
(`engine/llm_monitor_engine/settings.py:310`), which defaults to `chatgpt,gemini`.

Selecting a single LLM re-filters every metric on the page. Selecting "All LLMs"
returns the **mention-weighted mean** across platforms, not a plain average — so
per-platform mentions and citations sum exactly to the "All LLMs" totals.

---

## 1. AI Visibility

**Component:** `frontend/src/components/VisibilityScore.tsx`
**Mounted at:** `frontend/src/pages/Dashboard.tsx:408` (Row 1, left card)

A semicircular 0–100 gauge with a band label, a five-stage maturity ladder, and
three supporting metrics: Total Mentions, Avg Position, and a
positive/neutral/negative sentiment bar.

### Data sources

| Card element | API field | Source | Code |
|---|---|---|---|
| Gauge score | `brand.visibility_score` | `DomainMetricSnapshot`, mention-weighted | `views_dashboard.py:612` |
| Total Mentions | `brand.total_mentions` | Live `PromptAnalytics` | `views_dashboard.py:597` |
| Avg Position | `brand.avg_position` | Live `PromptAnalytics` | `views_dashboard.py:605` |
| Sentiment bar | `brand.sentiment.*` | Live `PromptAnalytics` categories | `views_dashboard.py:687` |

Live figures come from `live_domain_window_metrics()` (`views_dashboard.py:183`),
which reads `PromptAnalytics` rows with `track_status='COMP'`, windowed on
`COALESCE(tracked_at, created_at)` so weekly re-runs stay inside the rolling window.

**Trailing vs historical windows.** `PromptAnalytics` rows are updated in place on
every run, so `tracked_at` always points at the most recent run and no per-day
history survives there. Windows are therefore served two ways:

| Window | Source | Meaning |
|---|---|---|
| Includes the latest run (all trailing periods) | Live `PromptAnalytics` | Current state |
| Ends before the latest run (historical range) | `DomainMetricSnapshot` + `SentimentAnalytics` | State as of the end of the window |

The historical path (`snapshot_window_metrics()`, `views_dashboard.py:284`) engages
only when a window has no live rows but does have snapshots. A period with no
data in either source correctly stays at zero. Two values cannot be rebuilt from
snapshots: Cited Pages (no per-URL detail is retained) and the citation count,
which falls back to the domain citation total rather than the citation-URL event
count the live path uses.

### How the score is calculated

**Step 1 — the engine scores each platform, each processing day**
(`engine/core/prompt_analytics_processor.py:1283`), storing the result on a
`DomainMetricSnapshot`:

```
score = 100 × ( 0.4·norm_mentions
              + 0.3·norm_citations
              + 0.2·norm_sentiment
              + 0.1·norm_position )
```

| Component | Weight | Normalization |
|---|---|---|
| Mentions | 40% | `mentions / MAX(total_mentions)` across all domains |
| Citations | 30% | `citations / MAX(total_citations)` across all domains |
| Sentiment | 20% | `(avg_sentiment + 1) / 2` — maps −1..1 onto 0..1 |
| Position | 10% | `1 − (avg_position / MAX(average_position))` |

Each normalized value is clamped to 0–1 before weighting.

**Step 2 — the dashboard combines snapshots for the selected window**
(`views_dashboard.py:612`). Snapshot `mentions` is a cumulative running total
re-recorded on each processing day, so only the **latest snapshot per platform**
is used; those are then weighted by mentions:

```
visibility = Σ(latest_snapshot.visibility_score × mentions) / Σ(mentions)
```

**Step 3 — live gating** (`views_dashboard.py:619`). If the window contains zero
live mentions, the score is forced to `0.0` rather than surfacing a stale
snapshot value.

### Worked example — Appkodes, 30 days

**Step 1 output.** The latest snapshot per platform, as written by the engine on
its last processing run:

| Platform | Date | Mentions | Citations | Avg pos | Sentiment | Score |
|---|---|---|---|---|---|---|
| ChatGPT | 2026-07-21 | 52 | 5 | 1.00 | 0.11 | 20.12 |
| Google Gemini | 2026-07-21 | 152 | 21 | 1.33 | 0.10 | 21.07 |
| Claude | 2026-07-21 | 121 | 23 | 3.50 | 0.08 | 17.12 |

Each score is computed at write time against the normalization ceilings **as
they stood on that date**. Because those ceilings are `MAX()` values across all
domains, they move as data grows, so a stored score cannot be re-derived from
today's ceilings — the snapshot value is the record of truth.

**Step 2 — combining platforms**, weighted by mentions:

```
(20.12 × 52) + (21.07 × 152) + (17.12 × 121)
--------------------------------------------  =  19.45
                    325
```

| Platform | Score | Mentions | Share of weight |
|---|---|---|---|
| ChatGPT | 20.12 | 52 | 16% |
| Gemini | 21.07 | 152 | 47% |
| Claude | 17.12 | 121 | 37% |

The gauge renders **19.45**, and Total Mentions below it reads **325** — the same
325 used as the weight base.

Avg Position is derived the same way, from live data:
`(1.00 × 52 + 1.41 × 152 + 5.40 × 121) / 325 = 2.83`

### Score bands

Frontend-only (`VisibilityScore.tsx:30`). Drives the label, gauge colour, and
maturity ladder.

| Range | Label | Description |
|---|---|---|
| 70–100 | Great | Frequently mentioned and often preferred by LLMs |
| 50–69 | Good | Regularly mentioned across AI platforms |
| 30–49 | Average | Moderately visible in AI answers |
| 15–29 | Below Average | Occasionally surfaced by LLMs |
| 0–14 | Poor | Rarely mentioned in AI answers |

---
