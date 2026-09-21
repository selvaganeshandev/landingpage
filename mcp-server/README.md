# Promptmaxx MCP Server

Read-only MCP server exposing Promptmaxx client data to Claude: AI-visibility
mentions, share of voice, content gaps, SEO rank tracking, generated content,
the AI-generated keyword universe, and site-health audits — 27 tools across 7
modules.

Standalone by design: **the Promptmaxx backend is untouched.** Every contract
defect the integration audit found is absorbed in this layer (normalization,
warnings, error mapping) or documented below — never fixed at the source.

## Install

```
cd mcp-server
python -m venv .venv
.venv\Scripts\pip install -e .
copy .env.example .env    # then fill in credentials
```

## Configure

`.env` next to `pyproject.toml` (or plain environment variables):

| Variable | Meaning |
|---|---|
| `PROMPTMAXX_BASE_URL` | Backend URL, default `http://localhost:8000` |
| `PROMPTMAXX_EMAIL` / `PROMPTMAXX_PASSWORD` | Login credentials; the server logs in itself and re-logs-in when the 8h token expires |
| `PROMPTMAXX_ACCESS_TOKEN` | Optional ready-made token; used until it 401s, then email/password login takes over |
| `PROMPTMAXX_MCP_ALLOW_INSIGHTS` | `1` registers `get_competitive_insights` (off by default — see F12 below) |

**Single process only.** The API has no machine credential (finding F8), only
rotating-refresh JWTs. This server sidesteps the rotation race by re-logging-in
instead of refreshing, but two server processes sharing one account will still
fight. Run one.

## Register with Claude Code

```
claude mcp add promptmaxx -- <absolute-path>\mcp-server\.venv\Scripts\python.exe -m promptmaxx_mcp
```

## Verify

```
.venv\Scripts\python scripts\smoke.py
```

Calls every tool against the live instance and prints a pass/fail table. The
backend ships no OpenAPI spec and no versioned contract (finding F9), so this
script **is** the contract check — run it after any Promptmaxx update to catch
API drift before Claude does. Default test ids (domain 1, keyword 1, content 2,
run 1, mention 6) are overridable via `SMOKE_*` env vars.

## Data caveats (backend defects this server cannot fix)

- **F2 — competitor extraction is broken.** Competitor names derive from cited
  URL hostnames: publishers, tools, and unrelated brands appear as
  "competitors" while real rivals named in prose are missing. Every competitor
  tool injects `data_quality_warning` into its response.
- **F12 — false narrative.** `competitive-insights` turns the bad competitor
  set into ready-made sentences ("Amc leads with 42% share" — a US TV network,
  told to a stock broker). The tool is gated off by default; when enabled it
  carries a SEVERE audit-only warning.
- **F3 — country fallback.** 92 of 116 selectable countries silently measure
  as "United States" (the backend's country map has 24 entries). Not
  mitigable client-side: treat non-US clients' measurements with suspicion
  unless the country is in the map.
- **F4 — one metric, two values.** `visibility_score` differs between the
  client record and the dashboard (different unlabeled windows). Every
  response carries `source_endpoint`; always say which surface a number came
  from.
- **F14 — publish gate.** Mentions endpoints serve only published rows; the
  dashboard counts everything. Totals can legitimately disagree.
- **F1 — content 500 on fresh databases.** A state-only migration means fresh
  deployments lack the AI-detection columns; `GET /content/` 500s. The server
  maps that 500 to a readable error naming the defect and the corrective
  migration (`content/0009`, uncommitted).

## Known API security finding (not wrapped, needs a backend fix someday)

- **F13** — `GET /prompts/mentions/filters/` is unauthenticated (`AllowAny`,
  "Temporarily allow all for testing") and computes across all tenants. This
  server never calls it; its existence is a backend liability regardless.

## What this deliberately does not do

- **No writes.** Every tool is a GET. The server cannot trigger runs, spend
  the platform's model budget, or cause a runaway. All tools (bar the
  path-param health check) pass `domain_id` as a query parameter, the shape
  the backend's `DomainAccessMiddleware` enforces tenancy on.
- **No `/prompts/export/data/`.** US-locale timestamps and a 0..100 sentiment
  scale (F5, F6); everything it offers is served clean by the wrapped
  endpoints (ISO 8601, sentiment tagged `-1..1`).
- **No `/prompts/mentions/filters/`** (F13, above).
- **No binary exports** (xlsx/pdf) — binary payloads don't belong in a
  context window.
- **No backlinks (activity 4).** The competitor-backlink code was removed
  from Promptmaxx on cost grounds; the own-domain path is dormant pending a
  Moz key. Backlinks are Enque's to own via its DataForSEO connector.
- **No ephemeral keyword-research output** (F10):
  `generate-semantic-keywords` / `suggest-keywords` persist nothing, so there
  is nothing to read. The persisted lanes (keyword universe, generation runs)
  are wrapped in M7. `SecondaryKeyword` has no read endpoint at all.

## Modules

| Module | Tools |
|---|---|
| M1 clients | `list_clients`, `get_client`, `get_site_health` |
| M2 AI visibility | `list_mentions`, `get_mention`, `get_visibility_summary`, `get_share_of_voice`, `get_sentiment_summary`, `get_historical_trends` |
| M3 competitors | `list_content_gaps`, `get_answer_gap_analysis`, `list_competitors`, (`get_competitive_insights` — gated) |
| M4 SEO tracking | `list_seo_keywords`, `get_keyword_history`, `get_keyword_serp_features`, `get_keyword_volume`, `get_seo_overview`, `get_seo_metrics`, `list_seo_opportunities` |
| M5 content | `list_content`, `get_content` |
| M6 organic reports | `list_report_sheets`, `get_report_sheet_data` (GSC/GA; empty without Google integrations) |
| M7 keyword universe | `list_keyword_universe`, `get_active_generation_run`, `get_generation_run` |

Not wrapped: the raw GA4 / Search Console proxies
(`/integrations/google/ga4/run-report/`, `/integrations/google/search-console/query/`).
They accept caller-defined dimensions, metrics and filters and hit Google live
on every call — see `docs/GOOGLE_DATA_API.md`. Wrap them here only with a
fixed, small parameter surface so a tool call cannot burn the property's GA4
quota.

Normalization applied throughout (`normalize.py`): display fields stripped
from mentions, Tailwind classes scrubbed from analytics, sentiment tagged with
its scale, camelCase gap keys converted to snake_case, `/keywords/` filtered
by domain client-side (the endpoint has no domain filter server-side).
