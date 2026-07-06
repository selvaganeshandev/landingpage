# Design Doc — Geographic AI-Mention Tracking & Live Claude Usage Reporting

**Status:** Implemented & Verified (2026-07-06)
**Author:** Engineering
**Date:** 2026-07-06
**Related:** Insights Dashboard Enhancement (Mentions by Country, Country Filter) & Claude Admin Key Live Usage Integration.

---

## 1. Problem Statement

The Insights dashboard wants a **"Mentions by Country"** widget and a **country filter** that re-scopes the whole page (Semrush-style: "79% of AI mentions come from India, 9.6% from the US").

Today this is impossible: **an AI mention carries no geographic dimension anywhere in the pipeline.** The engine queries each LLM **once per (prompt, platform)** with no locale, so every mention is implicitly "global / unattributed." The only country data in the system is unrelated:

- `Domain.country` — a **single static** country per brand (context for prompt *generation*), not a distribution.
- `integrations` GA/GSC `geographic_breakdown` / `country_breakdown` — **website-traffic** geography (where visitors come from), a different concept from where a brand is *mentioned in AI answers*.

To ship Features E/F truthfully we must **capture geography at query time** and thread it through storage, aggregation, and the API.

---

## 2. Goals & Non-Goals

### Goals
- Attribute every AI mention/citation to a **region** (country-level to start).
- Let each domain opt into a **set of tracked regions** (not every domain needs all).
- Aggregate mentions/citations/visibility **per region**, additively, without changing any existing global metric.
- Expose `mentions_by_country` and an optional `country_code` filter on the **existing** `dashboard/summary` endpoint (additive).
- Preserve 100% backward compatibility: existing rows, snapshots, and API consumers behave identically when region is absent/default.

### Non-Goals (this phase)
- Sub-country geography (state/city).
- Region-specific competitor Share-of-Voice (later phase — `ShareOfVoiceAnalytics` would need the same treatment).
- Retroactively assigning a region to historical mentions (they become the `GLOBAL` default — see Migration).
- IP/proxy-based "real" geo-routing of LLM traffic (evaluated in §5.3, not chosen for v1).

---

## 3. Current Architecture (grounded)

**Query pipeline** — `engine/core/prompt_analytics_processor.py`
```
process_single_prompt(prompt_id)
  platforms = settings.ENABLED_PLATFORMS          # chatgpt, gemini, perplexity, claude, grok, deepseek
  for platform in platforms:
      client = ClientFactory.get_client(provider, org_id)   # per-org BYOK key
      result = self._process_prompt_with_<platform>(prompt.prompt, user_domain, client, group)
      # result = {is_mention, mention_count, citation_count, all_urls, sentiment, sentiment_score, position, response_text, context_summary}
  _create_analytics_record(prompt, results)
      → PromptAnalytics.update_or_create(prompt=…, platform=platform_label, defaults=…)
```

**Key models**
| Model | File | Current unique key |
|---|---|---|
| `PromptAnalytics` | `prompts/models.py:129` (engine mirror `shared_models`) | `(prompt, platform)` |
| `DomainMetricSnapshot` | `prompts/models.py:376` | `(domain, platform, snapshot_date, period_type)` |
| `PromptMetricSnapshot` | `prompts/models.py:226` | `(prompt, platform, snapshot_date, period_type)` |
| `PromptGroupMetricSnapshot` | `prompts/models.py` | `(group, platform, snapshot_date, period_type)` |

**Dashboard read** — `backend/analytics/views_dashboard.py:dashboard_summary` reads live `PromptAnalytics` for headline metrics and `DomainMetricSnapshot` for the trend series.

**Precedent that helps us:** the SERP layer (`engine/core/datablue_service.py`) already builds region-aware requests (`country`, `location`, `uule`, google-domain). We mirror its `country` config convention. And `ChatGPTClient.generate_prompts_from_keywords(..., country=…)` already localizes prompt *generation* — proof the country signal already flows into the engine, just not into mention querying.

---

## 4. The Core Challenge: LLMs Have No `country` Parameter

Unlike a SERP API, the chat completion APIs (OpenAI, Anthropic, Gemini, Grok, DeepSeek) accept **no location parameter**. Geography can only be introduced by:

| Approach | Mechanism | Fidelity | Cost | Verdict |
|---|---|---|---|---|
| **A. Prompt-side localization** | Add locale to the system/user message ("Answer for a user located in {country}. Prefer local sources.") | Medium — model may partially honor | Low | ✅ **v1 default** |
| **B. Web-grounded location hints** | For search-grounded platforms (Perplexity, Gemini-with-search, Grok), pass any supported region/locale hint in addition to A | Higher on those platforms | Low | ✅ layer on where supported |
| **C. Egress geo-routing** | Route API calls through in-region proxies so grounding sees a local IP | Highest, but fragile, ToS-risky, costly | High | ❌ not v1 (revisit) |

**Decision:** v1 = **A + B**. Each region is a **localized query context**, not a network location. This is honest as "AI visibility for a {country}-contextualized query," which is exactly what the dashboard claims.

---

## 5. Proposed Design

### 5.1 Regional configuration (per domain)

New model `DomainRegion` — the allow-list of regions a domain tracks. Avoids the N×P×**R** explosion for domains that only care about 1–2 markets.

```python
class DomainRegion(models.Model):
    domain        = FK(Domain, related_name='regions')
    country_code  = CharField(max_length=2)      # ISO-3166-1 alpha-2, e.g. 'IN', 'US'
    country_name  = CharField(max_length=100)     # display, e.g. 'India'
    locale        = CharField(max_length=10, blank=True)  # e.g. 'en-IN' (prompt-side hint)
    is_active     = BooleanField(default=True)
    is_primary    = BooleanField(default=False)   # exactly one; maps to legacy behavior
    created_at / modified_at
    class Meta:
        unique_together = ('domain', 'country_code')
```

- A domain with **no** `DomainRegion` rows behaves exactly as today (single implicit `GLOBAL` region — see §6).
- `Domain.country` seeds the initial primary region on migration.

### 5.2 Database schema changes (additive column + widened unique key)

Add a nullable `region` column to the analytics + snapshot tables and widen their unique constraints. `region` stores a `country_code` or the sentinel `'GLOBAL'`.

```python
# PromptAnalytics
region = CharField(max_length=8, default='GLOBAL', db_index=True)
unique_together = ('prompt', 'platform', 'region')     # was ('prompt','platform')

# DomainMetricSnapshot
region = CharField(max_length=8, default='GLOBAL', db_index=True)
unique_together = ('domain', 'platform', 'snapshot_date', 'period_type', 'region')

# PromptMetricSnapshot / PromptGroupMetricSnapshot — same pattern
```

**Why `default='GLOBAL'` and not null:** keeps the unique constraint total (Postgres treats NULLs as distinct, which would break `update_or_create`), and makes every existing row a valid, queryable "global" datapoint with zero backfill ambiguity.

> ⚠️ This is the one **non-additive-to-a-constraint** change. It is safe because: (a) new column has a default, so existing rows fill in as `GLOBAL`; (b) the widened unique key is a superset — every previously-unique row stays unique. But it **does** require a coordinated migration in **both** the `backend` and `engine` model definitions (they mirror each other over one DB — see project's dual-Django note). See §6.

### 5.3 Engine crawler changes

`process_single_prompt` gains a region loop **inside** the platform loop (or wrapping it):

```
regions = active_regions_for(domain)              # DomainRegion rows; [] → ['GLOBAL']
for region in regions:
    for platform in ENABLED_PLATFORMS:
        localized = localize_prompt(prompt.prompt, region)   # Approach A/B
        result = self._process_prompt_with_<platform>(localized, user_domain, client, group, region=region)
        results[(platform, region)] = result
_create_analytics_record(prompt, results)   # update_or_create keyed on (prompt, platform, region)
```

- `localize_prompt` prepends a locale system directive per region (config-driven template, e.g. `"Assume the user is in {country_name}. Prefer sources and context relevant to {country_name}."`). For web-grounded platforms, also pass any supported locale hint.
- `_create_analytics_record` writes one `PromptAnalytics` row per `(prompt, platform, region)`.
- `GLOBAL` region uses the **current, unmodified** prompt so existing behavior is preserved bit-for-bit when a domain has no regions configured.

**Snapshot generation** (`metric_snapshot_logger` / snapshot builders) groups by `region` as an extra key, writing per-region `DomainMetricSnapshot` rows.

### 5.4 Backend API changes (additive, existing endpoint)

`dashboard/summary` (`views_dashboard.py`) gains:

1. **New optional query param `country_code`** — when present, every date-windowed query adds `.filter(region=country_code)`. When **absent**, queries run exactly as today (all regions, i.e. unfiltered) → **zero change** for current callers.
2. **New response field `mentions_by_country`** — computed once from the same live `PromptAnalytics` window:
   ```json
   "mentions_by_country": [
     {"country_code": "IN", "country_name": "India", "mention_count": 4200, "percentage": 79.0},
     {"country_code": "US", "country_name": "United States", "mention_count": 510, "percentage": 9.6}
   ]
   ```
   Empty list when no regional data exists → the widget renders its empty state, nothing else changes.

Both are additive: no existing field renamed/removed, no endpoint renamed.

### 5.5 Frontend (Features E & F — already designed in the enhancement plan)

- **E — Mentions by Country:** new component using existing `Card`/`Table`/`Badge` primitives; stacked proportional bar + table (flag, country, %, count) fed by `mentions_by_country`.
- **F — Country Filter:** filter-bar tabs (🌍 Worldwide default = no `country_code`), wired to the new optional param; re-fetches the whole page scoped to the region.

These are unblocked the moment §5.4 ships and remain purely additive on the frontend.

---

## 6. Migration Strategy

**Dual-model coordination.** Per the project's architecture, `backend/*/models.py` and `engine/shared_models/models.py` describe the **same tables**. The `region` field + unique-key change must land in **both** definitions in the same migration wave, with **one** owning app running the schema migration and the other a `--state`/no-op mirror (matching how migrations are already split today). Confirm which side owns DDL before writing the migration.

**Phased, backward-compatible rollout:**

1. **Schema (dark):** add `region` (default `'GLOBAL'`) + widen unique keys. Deploy. All existing rows become `GLOBAL`. Nothing reads region yet. Fully backward compatible.
2. **Seed regions:** data migration creates one primary `DomainRegion` per domain from `Domain.country`. Still no behavior change (engine ignores regions until step 3).
3. **Engine (opt-in):** enable the region loop **behind a setting** (`GEO_TRACKING_ENABLED`, default off) and/or per-domain flag. Turn on for a pilot domain; verify per-region rows + snapshots.
4. **API additive fields:** ship `mentions_by_country` + `country_code` filter. Frontend E/F can now build.
5. **Backfill (optional, none required):** historical rows stay `GLOBAL`. If a domain wants history, it accrues region data going forward only — documented, not silently implied.

**Rollback:** disable `GEO_TRACKING_ENABLED` → engine reverts to single `GLOBAL` pass; API `country_code` filter simply matches only `GLOBAL`; `mentions_by_country` returns effectively one bucket. No schema rollback needed.

---

## 7. Cost & Performance

**The multiplier is the headline risk.** LLM calls per run:

```
calls = prompts × platforms × regions
```

Today: `N × P`. With regions: `N × P × R`. Example: 50 prompts × 6 platforms = **300** calls/run → with 5 regions = **1,500** calls/run (5×), at weekly cadence, **per domain**.

**Mitigations (all in v1):**
- **Region allow-list per domain** (`DomainRegion`) — most domains track 1–3 markets, not 50.
- **`is_active` gating** — pause a region without deleting its history.
- **Reuse existing cost controls** — BYOK keys, cheaper models, `ENABLED_PLATFORMS`, existing concurrency limits/quota_monitor.
- **Independent scheduling** — regions can run on staggered cadences (primary weekly, secondary monthly).
- **No silent scaling** — surface the projected call volume in the domain's region settings UI before enabling.

**DB growth:** row counts in the analytics/snapshot tables scale ×R for region-tracked domains. `region` is indexed; unique keys widened. Monitor table sizes; partition by `snapshot_date` later if needed.

---

## 8. Rollout Phases (implementation order)

| Phase | Work | Risk |
|---|---|---|
| **G1** | `DomainRegion` model + schema (`region` col, widened unique keys) in both backend & engine; migration; seed primary region from `Domain.country` | Medium — coordinated dual-model migration |
| **G2** | Engine region loop + `localize_prompt`, behind `GEO_TRACKING_ENABLED`; per-region snapshot grouping; pilot on one domain | Medium — cost multiplier, prompt-fidelity validation |
| **G3** | `dashboard/summary`: additive `country_code` filter + `mentions_by_country` | Low — additive, mirrors existing filter plumbing |
| **G4** | Frontend E (Mentions by Country) + F (Country Filter) | Low — additive, primitives exist |
| **G5** | Region management UI (add/remove/activate regions per domain, with projected-cost warning) | Low |

---

## 9. Risks & Open Questions

1. **Prompt-side geo fidelity.** Approach A is a *soft* signal — models may not meaningfully change answers by locale. **Mitigation:** validate on a pilot; measure whether per-region mention/citation distributions actually diverge before rolling out widely. If divergence is negligible, reconsider Approach C for grounded platforms.
2. **Cost explosion.** See §7 — must be opt-in and allow-listed, never on-by-default for all regions.
3. **Dual-model migration ownership.** ✅ **RESOLVED.** The **backend owns all DDL**; the **engine mirrors via state-only migrations**. Verified: `backend/prompts` has real migrations (no `SeparateDatabaseAndState`), while `engine/shared_models/migrations/0003_*` uses `SeparateDatabaseAndState(state_operations=[…])` (models are `managed=True` but the migration issues **no DDL**). G1 therefore = real backend migration (`prompts`, `domains`) + a hand-written engine state-only migration (`shared_models/0004_*`) mirroring the 0003 pattern.
4. **"GLOBAL" semantics in mixed state.** A domain mid-rollout will have historical `GLOBAL` rows + new per-region rows. The dashboard's unfiltered view must sum correctly without double counting (i.e. don't add `GLOBAL` + region rows for the same window). **Decision:** once a domain is region-tracking, the engine stops writing `GLOBAL` rows for new runs; unfiltered dashboard aggregates over whatever regions exist.
5. **Share-of-Voice / competitors per region.** Out of scope for v1; `ShareOfVoiceAnalytics` would need the same `region` treatment later.
6. **`region` length/sentinel.** `max_length=8` fits ISO alpha-2 and `'GLOBAL'`; revisit if we later add locale-qualified regions (`en-IN`).

---

## 10. Testing Strategy

- **Migration tests:** existing rows become `GLOBAL`; `update_or_create` still idempotent under the widened key.
- **Engine unit tests:** region loop produces exactly `platforms × active_regions` results; `[]` regions → single `GLOBAL` pass identical to current output.
- **Aggregation tests:** per-region snapshots sum to the correct unfiltered totals; no `GLOBAL`+region double-count (Risk #4).
- **API tests:** `country_code` absent → byte-identical to current response (except the additive `mentions_by_country` key); `country_code=IN` → correctly scoped.
- **Cost guardrail test:** projected-call estimator matches `prompts × platforms × active_regions`.
- **Frontend:** E/F render from `mentions_by_country`; empty state when absent; filter re-scopes without breaking Phase 1/2 widgets.

---

## Appendix — Summary of Additive vs Breaking

| Change | Type |
|---|---|
| `DomainRegion` model | Additive (new table) |
| `region` column (default `GLOBAL`) on analytics/snapshots | Additive column |
| Widened `unique_together` to include `region` | **Constraint change** (safe superset; needs migration) |
| Engine region loop behind `GEO_TRACKING_ENABLED` | Additive, default-off |
| `dashboard/summary` `country_code` param + `mentions_by_country` | Additive |
| Frontend E/F | Additive |

**Net:** everything is additive except the unique-key widening, which is a safe superset requiring a coordinated dual-model migration. No existing endpoint, field, or metric is renamed or removed.

---

## 11. Implementation & Verification Summary (2026-07-06)

Both the **Geographic AI-Mention Tracking** and the **Live Claude Usage Reporting** features have been fully implemented and verified.

### 11.1 Geographic Tracking & Insights Dashboard (Completed)
- **Database Schema**:
  - `DomainRegion` model added to allow domains to opt-in to regional tracking.
  - Nullable `region` column (default `'GLOBAL'`) added to prompt analytics and snapshots, widening the unique constraints safely.
  - Backend migrations (`domains/0008` and `prompts/0002`) and engine state migration (`shared_models/0004`) successfully executed.
- **Frontend Dashboard**:
  - `MentionsByCountry.tsx` component implemented, displaying a stacked proportional bar and country breakdown tables using custom SVG flag icons.
  - Scoped time-range presets (1M, 6M, All Time) implemented in `Dashboard.tsx`.
  - Scoped country filter tab successfully queries the backend summary endpoint.

### 11.2 Live Claude Usage & Admin Key Integration (Completed)
- **Encrypted Admin Key**: Added `content_admin_api_key` to Organisation model (backed by Fernet encryption/decryption properties).
- **Django Migrations**: Migrations `authentication/0007` (add admin key) and `authentication/0008` (remove token limit) applied. Engine state migrations `shared_models/0005` (add) and `shared_models/0006` (remove) synced.
- **Centralized Model Rates**: Implemented `ANTHROPIC_PRICING` mapping (input uncached, input cached read, cache creation write, output) and prefix-matching function.
- **Usage calculation**: Aggregates official Anthropic usage report parameters (`uncached_input_tokens`, `cache_read_input_tokens`, `cache_creation.ephemeral_5m_input_tokens`, `cache_creation.ephemeral_1h_input_tokens`, `output_tokens`) to compute actual USD costs and Prompt Caching savings.
- **Usage UI Panel**:
  - Features Card 1 (Claude generation key) and Card 2 (Anthropic admin key) separately.
  - Dynamic estimated cost, **Prompt Caching Savings** line (e.g. `Saved $4.50 (35%) via Prompt Caching`), a manual **Sync Now** refresh button, and a live data status indicator.
  - Credit exhaustion handling: displays a red `Credits Exhausted` banner if Anthropic returns HTTP `402` or credit-related errors.

