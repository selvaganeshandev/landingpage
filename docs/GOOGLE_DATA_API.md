# Google Analytics & Search Console Data — External API

How another application pulls GA4 and Search Console data out of PromptMaxx
with a service API key, and which endpoints return what.

**Date:** 2026-09-21
**Area:** `backend/integrations/`, `backend/seo_rankings/`

**Source files**

| File | Role |
|---|---|
| `backend/integrations/google_proxy.py` | Raw GA4 `runReport` and GSC `searchAnalytics.query` proxies (new) |
| `backend/integrations/google_oauth.py` | OAuth flow, stored credentials, the fixed-shape GA endpoints |
| `backend/integrations/views.py` | `gsc-keywords/`, `traffic-insights/` |
| `backend/seo_rankings/views.py` | SEO Report sheets (`/seo/report-sheets/...`) |
| `backend/authentication/api_key_auth.py` | `Api-Key pmxk_...` authentication |
| `backend/llm_monitor/middleware_domain_access.py` | Org scoping + client read-only rule |
| `tests/backend/integrations/test_google_proxy.py` | Proxy tests (Google mocked) |

---

## 1. Authentication

Mint a key in **Settings > API keys** (or `POST /auth/service-api-keys/` with a
JWT). The plaintext `pmxk_...` is shown once.

```
Authorization: Api-Key pmxk_xxxxxxxxxxxxxxxxxxxx
```

`Authorization: Bearer pmxk_...` is accepted too.

The key resolves to a hidden service account with role `client` and
`is_service_account=True`:

- **Read-only.** Only safe HTTP methods succeed. Every endpoint below is GET.
- **Org-wide.** It can read every domain in its organisation. A `domain_id`
  from another organisation returns **404** (not 403 — the response must not
  confirm the domain exists).
- Every request is logged to `ServiceApiKeyUsage` (visible under the key in
  Settings).

Base URL is the backend (`http://localhost:8000` locally). Find domain IDs with
`GET /domains/`.

---

## 2. Prerequisites in PromptMaxx

Per domain, in **Domain Settings > Integrations**:

1. Connect Google (OAuth). Scopes are `analytics.readonly` and
   `webmasters.readonly` — PromptMaxx can never write to GA4 or GSC.
2. Select the GA4 property and the Search Console site. An endpoint returns
   400 `Integration has no property/site selected` until this is done.

For the pre-shaped sheets (section 3) the sheets must also be configured under
**SEO Reports > Configure**; the data endpoint only returns configured sheets.

---

## 3. Pre-shaped reports (SEO Report sheets)

These are the same tables the SEO Reports page renders — computed by
PromptMaxx, with period columns, WoW/MoM/YoY change and month proration.

```
GET /seo/report-sheets/?domain_id=12              # configured sheets
GET /seo/report-sheets/data/?domain_id=12         # live data for all sheets
GET /seo/report-sheets/data/?domain_id=12&sheet_ids=3,7
GET /seo/report-sheets/export/?domain_id=12       # xlsx
```

Response: `{reports: [{sheet_id, sheet_name, sheet_type, columns, rows,
total_rows}], count}`. Parse by `sheet_type`:

| `sheet_type` | What it holds |
|---|---|
| `gsc_overview` | Clicks / Impressions / CTR split Total, Branded, Non-Branded + Avg Position, per period |
| `gsc_queries` | Query-level clicks, impressions, CTR, position |
| `gsc_branded_queries` | Same, queries containing the domain name |
| `gsc_non_branded_queries` | Same, queries excluding the domain name (regex) |
| `gsc_pages` | Page-level GSC metrics |
| `ga_overview` | Sessions, Users, Page Views, Bounce Rate per period |
| `ga_landing_pages` | Landing pages, **Organic Search channel only** |
| `ga_organic_traffic_breakup` | Organic sessions bucketed by URL first path segment, with drill-downs |
| `ga_other_sources` | Sessions / Users by default channel group |
| `ga_country_events` | Organic sessions, users, engagement + configured event counts by country |
| `ga_gsc_reconcile` | GA organic sessions vs GSC clicks |

Brand detection in these sheets is the domain name only (`utimf.com` →
`utimf`). For a custom brand term list use the GSC proxy in section 5 with a
regex filter.

---

## 4. Fixed-shape GA / GSC endpoints

```
GET /integrations/google/analytics-data/?domain_id=12&start_date=2026-08-01&end_date=2026-08-31
    daily sessions, totalUsers, screenPageViews, bounceRate, averageSessionDuration

GET /integrations/google/ai-referrals/?domain_id=12[&days=30|&start_date&end_date]
    AI-platform referral traffic: visits, users, conversions, revenue, bounce rate,
    landing pages, conversion paths (cached 15 min per window)

GET /integrations/google/ai-referrals/timeseries/?domain_id=12[&days=30]
    daily AI-referred sessions + users

GET /integrations/gsc-keywords/?domain_id=12[&article_title=...]
    top GSC queries, optionally related to a title

GET /integrations/traffic-insights/?domain_id=12
    stored GA + GSC insight rollups
```

---

## 5. Raw report proxies

For any data point the sheets do not compute — conversions by landing page,
key events by query, a custom brand regex, device or country splits — the
caller describes the report and PromptMaxx forwards it to Google with the
domain's stored credentials. Nothing is cached; each call is one Google API
request and counts against the property's GA4 quota, so cache on the consumer
side.

Both endpoints share the error contract:

| Status | Meaning |
|---|---|
| 400 | Bad parameter (`domain_id` missing, bad filter syntax, bad date, bad limit, no property/site selected, no credentials) |
| 404 | No active integration for that domain, or domain not in your organisation |
| 502 | Google returned an error — the message is passed through (`quota exceeded`, unknown metric name, …) |

### 5.1 GA4 — `GET /integrations/google/ga4/run-report/`

Proxies GA4 Data API `properties.runReport`.

| Param | Meaning |
|---|---|
| `domain_id` | required |
| `metrics` | comma-separated GA4 metric names. Default `sessions`. Max 10 |
| `dimensions` | comma-separated GA4 dimension names. Max 9 |
| `start_date`, `end_date` | `YYYY-MM-DD`. Default: 30 days ending yesterday |
| `filter` | repeatable; `<dimension><op><value>`, all AND-ed (see operators) |
| `order_by` | a metric or dimension name; prefix `-` for descending |
| `limit` | rows, default 1000, max 10000 |
| `offset` | row offset for paging |

Filter operators (dimension filters only):

| Op | GA4 match |
|---|---|
| `=` | EXACT |
| `*` | CONTAINS |
| `^` | BEGINS_WITH |
| `~` | FULL_REGEXP |
| `!~` | NOT FULL_REGEXP |

The value is everything after the first operator, so `pagePath=/a~b` filters on
`/a~b`.

Response:

```json
{
  "success": true,
  "property_id": "123456",
  "date_range": {"start": "2026-08-01", "end": "2026-08-31"},
  "dimensions": ["landingPagePlusQueryString"],
  "metrics": ["sessions", "keyEvents"],
  "rows": [
    {"landingPagePlusQueryString": "/pricing", "sessions": 120.0, "keyEvents": 7.0}
  ],
  "row_count": 1,
  "total_rows": 1,
  "offset": 0
}
```

Metric values are floats. Use `total_rows` + `offset` to page.

Examples:

```bash
BASE=http://localhost:8000
KEY="Authorization: Api-Key pmxk_xxx"

# Conversions and revenue by organic landing page
curl -H "$KEY" "$BASE/integrations/google/ga4/run-report/?domain_id=12\
&dimensions=landingPagePlusQueryString\
&metrics=sessions,keyEvents,conversions,totalRevenue\
&filter=sessionDefaultChannelGroup=Organic%20Search\
&order_by=-sessions&limit=500"

# One key event by landing page
curl -H "$KEY" "$BASE/integrations/google/ga4/run-report/?domain_id=12\
&dimensions=landingPagePlusQueryString,eventName&metrics=eventCount\
&filter=eventName=Register_submit\
&filter=sessionDefaultChannelGroup=Organic%20Search"

# Organic sessions by country and device, excluding admin pages
curl -H "$KEY" "$BASE/integrations/google/ga4/run-report/?domain_id=12\
&dimensions=country,deviceCategory&metrics=sessions,engagedSessions\
&filter=sessionDefaultChannelGroup=Organic%20Search\
&filter=landingPagePlusQueryString!~^/admin"
```

Metric and dimension names are GA4's own — see the
[GA4 API schema](https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema).

### 5.2 Search Console — `GET /integrations/google/search-console/query/`

Proxies Search Console `searchAnalytics.query`.

| Param | Meaning |
|---|---|
| `domain_id` | required |
| `dimensions` | comma-separated: `query`, `page`, `country`, `device`, `date`, `searchAppearance`. Default `query` |
| `start_date`, `end_date` | `YYYY-MM-DD`. Default: 30 days ending 3 days ago (GSC data lag) |
| `filter` | repeatable; `<dimension><op><value>`, all AND-ed |
| `search_type` | `web` (default), `image`, `video`, `news`, `discover`, `googleNews` |
| `limit` | rows, default 1000, max 25000 |
| `offset` | `startRow` for paging |

Filter operators:

| Op | GSC operator |
|---|---|
| `=` | equals |
| `!=` | notEquals |
| `*` | contains |
| `!*` | notContains |
| `~` | includingRegex |
| `!~` | excludingRegex |

Response:

```json
{
  "success": true,
  "site_url": "sc-domain:example.com",
  "date_range": {"start": "2026-08-01", "end": "2026-08-31"},
  "dimensions": ["query", "page"],
  "rows": [
    {"query": "buy widgets", "page": "https://example.com/w",
     "clicks": 10, "impressions": 200, "ctr": 0.05, "position": 4.2}
  ],
  "row_count": 1,
  "offset": 0
}
```

`ctr` is a fraction (0.05 = 5 %). GSC does not return a total row count; page
until `row_count < limit`.

Examples:

```bash
# Non-branded queries with your own brand term list
curl -H "$KEY" "$BASE/integrations/google/search-console/query/?domain_id=12\
&dimensions=query,page\
&filter=query!~(?i)mybrand|my%20brand|mybrnd\
&limit=5000"

# Branded queries, India only, mobile
curl -H "$KEY" "$BASE/integrations/google/search-console/query/?domain_id=12\
&dimensions=query&filter=query~(?i)mybrand&filter=country=ind&filter=device=MOBILE"

# Daily clicks for one page
curl -H "$KEY" "$BASE/integrations/google/search-console/query/?domain_id=12\
&dimensions=date&filter=page=https://example.com/pricing\
&start_date=2026-07-01&end_date=2026-08-31"
```

---

## 6. What is not available through PromptMaxx

- **Creating or editing GA4 key events / goals.** The OAuth scope is
  read-only. Configure key events in GA4 Admin, then read them by name
  (`filter=eventName=...`) or through the `ga_country_events` sheet.
- **Google OAuth tokens.** No endpoint returns the stored refresh token; the
  proxies are the only way to reuse the connection.
- **Metric filters** (e.g. `sessions > 100`) on the GA4 proxy. Filter on the
  consumer side.
