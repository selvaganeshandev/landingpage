# Performance Audit

> **Status: items 1–5 fixed and deployed 2026-08-06** (revision `0d78ae52`).
> Results, measured the same way as the baselines below:
>
> | | before | after |
> |---|---|---|
> | first-load payload | 3.69 MB | **0.94 MB** (−74%) |
> | `/prompts/mentions/` | 1,402 ms · 67 q | **137 ms · 7 q** (−90%) |
> | `/prompts/groups/` | 348 ms · 181 q | **59 ms · 12 q** (−83%) |
>
> Every change was verified byte-identical against production data before
> deploying — response payloads hash the same before and after.
>
> Item 2 below records a wrong diagnosis worth keeping: the first attempt fixed
> the string copying and moved the endpoint only 1,402 → 1,271 ms. Re-profiling
> showed the real cost was regex backtracking, not allocation. **Item 6
> (dashboard summary) and route-level code splitting remain open.**

Measured against **production** (`64.227.190.42`, revision `d2925aef`) on 2026-08-06,
using the live database and a real org-1 account (51 projects, project 98 =
UTI Mutual Fund).

Every number below is measured, not estimated. Timings are the best of three
**warm** runs — a cold first request costs ~3.4s on any endpoint while Django
imports and the JWT machinery load, and that one-off is excluded throughout so it
does not disguise the real costs.

---

## Summary

| # | Problem | Impact | Effort |
|---|---|---|---|
| 1 | JS/CSS served **uncompressed** | 3.5 MB → 0.9 MB, every first visit | one line |
| 2 | No code splitting | whole app downloaded to view any page | medium |
| 3 | `/prompts/mentions/` spends 87% of its time in one helper | 1,174 ms → ~150 ms | small |
| 4 | `/prompts/groups/` issues 181 queries for 20 rows | 262 ms, grows with data | small |
| 5 | `/prompts/mentions/` N+1 on three relations | 60 needless queries | small |
| 6 | Dashboard summary: 19 duplicate queries | 296 ms | small |

Nothing here is architectural. Items 1, 3, 4 and 5 are a few hours' work and
account for most of the observable slowness.

---

## Measurements

```
endpoint                warm ms  queries   dup   db ms
----------------------------------------------------------
domains list                 34        6     1       9
dashboard summary           296       41    19      74
prompt groups               262      181   140     144
mentions                   1174       67    58      88     <-- worst
citations                   393       19    11     181
seo keywords                 59        6     2      15
```

`dup` counts queries whose SQL is identical to another in the same request — the
signature of an N+1. Note `mentions`: only 88 ms of its 1,174 ms is database, so
**the database is not the problem there.** Nearly 1.1 s is Python.

---

## 1. Static assets are served uncompressed

The single largest win, and a one-line fix.

```
GET /assets/index--wvizl59.js   →   3,554,287 bytes
content-encoding:  (absent)
```

`/etc/nginx/nginx.conf` has `gzip on;` but the `gzip_types` line beneath it is
commented out. **nginx's default `gzip_types` is `text/html` alone**, so `gzip on`
compresses the HTML shell and nothing else — the JavaScript and CSS, which are
99% of the payload, go over the wire raw.

The build itself already reports what compression would achieve: **922 KB
gzipped** versus 3.5 MB raw. That is a **74% reduction on every first visit**, and
on a slow Indian mobile connection it is the difference between a few seconds and
half a minute before the app renders.

Fix — uncomment in `nginx.conf` and reload:

```nginx
gzip_vary on;
gzip_proxied any;
gzip_comp_level 6;
gzip_types text/plain text/css application/json application/javascript
           text/xml application/xml application/xml+rss text/javascript;
```

Cache headers are already correct (`max-age=31536000, immutable`), so this cost is
paid once per release rather than per page view — but it is paid by every user on
every release, and right now it is four times larger than it needs to be.

## 2. The entire application is one chunk

`React.lazy` appears **zero** times in `App.tsx`. Every route is a static import,
so all 46,025 lines across 40+ page components compile into a single 3.4 MB
bundle. Opening the login screen downloads the Content Editor (4,309 lines), the
Report Builder (2,975) and Organisation Settings (3,772).

`xlsx` (420 KB) is already split out, so the tooling supports this — it simply has
not been applied to routes.

Route-level `React.lazy` + `Suspense` would cut the initial download to the shell
plus one page. Combined with gzip, first load lands in the low hundreds of KB.

## 3. `/prompts/mentions/` — 1,020 ms in one helper

Profiling a single 20-row request:

```
644 calls   1.020 s cumulative   prompts/views.py:136(_extract_headline_from_context)
```

644 calls, 1.02 s — **87% of the whole request**, for one page of twenty rows.

The cause is in the first four lines of the helper:

```python
url_lower = url.lower()
context_lower = context_summary.lower()      # <-- per citation, not per mention
idx = context_lower.find(url_lower)
```

`context_summary` is the LLM's full response. Measured across 200 live rows:

```
context_summary   avg 13,051 chars   median 11,376   max 178,205
citations         avg 24.4 per mention   max 62
```

The helper is called once per citation, and each call lowercases the *entire*
response again. At 24 citations per mention across 20 mentions that is ~490 full
copies of a 13 KB string — roughly **6.4 MB of pointless string allocation per
request**, before the regexes even run. On a row near the 178 KB maximum, one
mention alone copies several megabytes.

Fix: hoist the lowercase out of the citation loop and compute it once per mention,
passing it in. Precompiling the two module-level regexes (`re` is currently
imported *inside* the function) is worth a little more. Expect ~1,174 ms → ~150 ms.

Worth noting while in there: `_extract_headline_from_context` is defined **three
times** in the same file — lines 136, 464 and 983 — as a nested function. Any fix
must be applied to all three, or deduplicated into one module-level helper.

## 4. `/prompts/groups/` — 181 queries to return 20 rows

140 of the 181 are duplicates:

```
x80   SELECT COUNT(*) FROM prompt_analytics INNER JOIN prompts ON ...
x16   SELECT ... FROM prompts WHERE group_id = N
x16   SELECT prompt FROM prompts WHERE group_id = N AND type = 'secondary'
```

That 80× `COUNT(*)` is a per-prompt aggregate evaluated in a Python loop. It should
be a single grouped annotation:

```python
.annotate(mention_count=Count('prompts__analytics', filter=Q(...)))
```

and the two per-group prompt fetches should be `prefetch_related`. 181 queries → a
handful. This one also **degrades as the client's data grows**, which matters given
50 projects are about to migrate in.

## 5. `/prompts/mentions/` N+1 on relations

```
x20   SELECT ... FROM prompts        WHERE id = N
x20   SELECT ... FROM prompt_groups  WHERE id = N
x20   SELECT ... FROM domains        WHERE id = N
```

Exactly one per row per relation — a missing
`select_related('prompt', 'prompt__group', 'prompt__group__domain')`. 60 queries
become 0. Small next to item 3, but free.

## 6. Dashboard summary — 19 duplicate queries

41 queries, 19 duplicated, 296 ms (74 ms database). Less urgent than the above,
but the same `select_related`/annotation treatment applies. The view also logs
several full sample rows at INFO on every request, which is not free at this size.

---

## What is already fine

Worth stating so effort is not wasted here:

- **`domains list` 34 ms, `seo keywords` 59 ms, `topics` 7 ms** — no action needed.
- **Cache headers** — `immutable`, one year. Correct.
- **Polling** — only one interval in the codebase (Competitors, 10 s), and every
  `setInterval` has a matching `clearInterval`. No leaks.
- **Database indexes** — the slowest single query measured was 54 ms; nothing
  suggests a missing index.

---

## Suggested order

1. **nginx `gzip_types`** — one line, 74% off every first load
2. **`_extract_headline_from_context`** — hoist the `.lower()`; ~1 s off the mentions page
3. **`/prompts/groups/` annotation + prefetch** — 181 queries → a few; matters more as data grows
4. **`select_related` on mentions** — 60 queries → 0
5. **Route-level code splitting** — largest frontend win, but a day's work and needs regression testing

1 through 4 are small, independent, and individually verifiable.
