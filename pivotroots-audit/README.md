# PivotRoots — free AI Visibility Audit landing page

Next.js port of `pivotroots-audit-lp.html`, wired to the PromptMaxx audit engine.
A visitor enters their website, brand name and a work email on that domain; the
page starts an audit, shows the engine's **seven stages** and the answers as
they arrive, then shows the score with a **Download PDF** button.

Standalone: own deps, own build. Not wired into `frontend/`, `landing/` or `UI/`.

## Stack

- Next.js 16 (App Router), React 19, TypeScript — same versions as `landing/`
- Plain CSS in `src/app/globals.css`, a port of the original page's stylesheet
- Fonts via `next/font` (Archivo, Inter, JetBrains Mono); no UI library

## Run

```sh
cp .env.example .env.local   # AUDIT_API_URL is required: local stack or production, your choice
npm install
npm run dev                  # http://localhost:3100
npm run build && npm start
npm run typecheck && npm run lint
```

## How it talks to the engine

The browser only ever calls this app's own route handlers, which proxy to the
backend's public audit endpoints (`backend/audits/views.py`). No CORS entry is
needed for the PivotRoots domain and the backend host is never in page source.

| Page calls                       | Backend                              | Notes |
|----------------------------------|--------------------------------------|-------|
| `POST /api/audits`               | `POST /audits/`                      | body `{url, email, brand_name, country}`; 201 new · 200 reused (same host inside `AUDIT_REPEAT_HOURS`) · 400/429/503 refused |
| `GET  /api/audits/<token>`       | `GET /audits/public/<token>/`        | polled every 2.5 s while `status` is `INIT`/`PROC`; carries `stage`, `stage_detail`, `live` |
| `GET  /api/audits/<token>/pdf`   | `GET /audits/public/<token>/pdf/`    | streamed through as `pivotroots-ai-visibility-audit-<host>.pdf`; 409 until DONE |

The visitor's IP is forwarded (`X-Forwarded-For`) so the backend's per-IP daily
cap counts visitors, not this server. **Deploy behind a proxy that sets
`X-Forwarded-For` or `X-Real-IP`** (nginx, Vercel, Cloudflare do); without it
every visitor shares one cap of `AUDIT_PER_IP_DAILY`.

### The seven stages

`src/lib/stages.ts` mirrors `Audit.STAGE_ORDER` in `backend/audits/models.py`:
`profile → crawl → prompts → engines → serp → score → publish`. Each card shows
the engine's live counter for that stage (`stage_detail`), e.g. `48 / 48 answers`.
`serp` renders as "not in the free audit" when `AUDIT_SEO_ENABLED` is off.

### The live feed

`live` on the public status payload is the newest engine answers while the
audit runs (added to `PublicAuditSerializer` for this page). The page keeps a
rolling six so answers that scrolled past between polls are not lost.

### Resuming

Starting an audit rewrites the URL to `/audit/<token>`; that route renders the
same page with the live panel in place of the form, so a refresh, a bookmark or
a forwarded link lands on the running/finished audit. Links expire with the
backend's `AUDIT_PUBLIC_TTL_DAYS` (30 by default).

## Links from email blasts

`/?d=<domain>&e=<email>&b=<brand>&c=<campaign>&m=<market>` prefills the form;
`c` goes into the `dataLayer` events (`audit_start`, `audit_complete`,
`audit_refused`) and `m` overrides `AUDIT_DEFAULT_COUNTRY` for that visitor.

## Copy that quotes numbers

`src/lib/site.ts` holds the engine list, prompt count, "2 minutes" and the
report TTL that the copy quotes. Keep `ENGINES` / `PROMPT_COUNT` in step with
the backend's `AUDIT_ENGINES` / `AUDIT_PROMPT_COUNT`, or the page promises more
than the engine runs. `NEXT_PUBLIC_SHOW_POWERED_BY=true` shows the
"Audit engine powered by PromptMaxx" footer line.

## Backend changes that shipped with this page

- `POST /audits/` accepts `brand_name`; the engine's profile stage keeps a
  supplied name instead of guessing one from the homepage.
- `GET /audits/public/<token>/` carries `live` while the audit runs.
- Tests: `tests/backend/audits/test_api.py` (`test_brand_name_from_the_form_is_kept`,
  `test_live_feed_while_running_then_empty_when_done`).

## Not done here

- The PDF is the backend's PromptMaxx-branded report (`backend/audits/pdf.py`);
  only the filename is PivotRoots'. White-labelling the document itself is a
  backend change.
- The engine emails the requester only when `AUDIT_AUTO_EMAIL_ON_PUBLISH` is on
  in the engine's `.env`; the page's copy does not promise an email.
