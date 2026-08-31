# Promptmaxx — Local Setup Guide

Everything needed to run the full stack on a fresh machine. Written for Windows
(Linux/macOS differences noted inline), and **verified against a working install**
— every version, command and environment key below was read off a machine where
the stack is running, not copied from memory.

---

## 0. What you are installing

Five processes plus two data stores. All of it runs on one machine.

```
llm-monitor/
├── backend/     Django REST API           :8000
├── engine/      Django + Celery workers   :8001  + 3 background processes
├── frontend/    React / Vite app UI       :8080
├── landing/     Next.js marketing site    :3000   (optional)
└── mcp-server/  MCP server for Claude     :8010   (optional)
```

Backend and engine **share one PostgreSQL database**. The backend queues work;
the engine's Celery workers execute it. If the workers are not running, the UI
looks alive but nothing ever finishes.

---

## 1. Prerequisites

Verified versions on the reference machine. Anything at or above these works.

| Requirement | Verified version | Check |
|---|---|---|
| Python | **3.12** (see note) | `python --version` |
| uv | 0.12.5 | `uv --version` |
| Node.js | 26.2.0 | `node --version` |
| npm | 11.13.0 | `npm --version` |
| PostgreSQL | 17.2 | `psql --version` |
| Redis (Windows: **Memurai**) | Memurai 4.1.2 | `memurai-cli --version` |
| Git | any | `git --version` |

> **Python version matters.** The venv on the reference machine is **3.12.14**,
> even though the system Python is 3.14. Some pinned dependencies do not yet
> build on 3.13+. Create the venv with 3.12 explicitly.
>
> The reference machine uses [uv](https://docs.astral.sh/uv/) to supply that
> interpreter. `uv python install 3.12` gets it without touching your system
> Python. Plain `python3.12 -m venv` works just as well if you already have it.

**Windows Redis:** use [Memurai](https://www.memurai.com/) (a native Redis
build, installs as a Windows service). Redis-on-WSL also works. Celery needs a
broker on `localhost:6379`; the app uses **database 5**.

---

## 2. Clone and create the database

```bash
git clone https://github.com/arun-andiselvam/llm-monitor.git
cd llm-monitor
```

```bash
psql -U postgres -c "CREATE DATABASE llm_monitor;"
```

---

## 3. Python environment

**The reference machine uses a single shared venv at `backend/.venv` for the
backend, the engine and all three Celery processes.** `backend/requirements.txt`
(341 packages) is a superset of `engine/requirements.txt` (70), so one
environment covers both. This is simpler to maintain and is what the run
commands in §7 assume.

```powershell
cd backend
uv venv --python 3.12 .venv          # or: py -3.12 -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\pip install -r ..\engine\requirements.txt
.\.venv\Scripts\pip install trafilatura
```

`trafilatura` (2.0.0) is **not** in either requirements file but is required by
the onboarding site-crawl. Without it, "Add Brand" fails with "couldn't read the
site".

> Prefer isolation? Create `engine/.venv` separately from
> `engine/requirements.txt` and point the engine commands at it. Both layouts
> work; only the paths in §7 change.

Verify:

```powershell
.\.venv\Scripts\python.exe -c "import django, celery, redis, trafilatura; print(django.get_version())"
# expect: 5.2   (celery 5.3.6, redis 5.0.8)
```

---

## 4. `backend/.env`

Gitignored — create it by hand. This is the **complete key set** from the
reference machine. Values shown are placeholders.

```ini
# --- core ---
DEBUG=True
SECRET_KEY=change-me
ALLOWED_HOSTS=localhost,127.0.0.1
SITE_URL=http://localhost:8000
FRONTEND_URL=http://localhost:8080
CORS_ALLOWED_ORIGINS=http://localhost:8080
ENGINE_API_URL=http://localhost:8001

# --- database (shared with the engine) ---
DB_NAME=llm_monitor
DB_USER=postgres
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432

# --- celery broker (Redis db 5) ---
CELERY_BROKER_URL=redis://localhost:6379/5

# --- LLM transport ---
# Nearly everything routes through OpenRouter. Model slugs need the vendor prefix.
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_INTERNAL_MODEL=openai/gpt-5-mini
OPENROUTER_GEMINI_MODEL=google/gemini-2.5-flash
OPENAI_CHATGPT_MODEL=gpt-4o
ANTHROPIC_MODEL=claude-sonnet-4-5
PERPLEXITY_MODEL=sonar

# --- Google Gemini (used directly for some analysis paths) ---
GOOGLE_GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-2.5-flash
GEMINI_BACKEND=api            # 'api' or 'vertex'

# --- image generation (content editor) ---
# Stage 1 writes the prompt with a text model; unset falls back to
# OPENROUTER_INTERNAL_MODEL. Stage 2 renders pixels — OpenRouter has NO free
# image models, so this stage always costs money.
IMAGE_PROMPT_TEXT_MODEL=
IMAGE_RENDER_MODEL=google/gemini-2.5-flash-image

# --- SEO data (needed for rankings, volume, backlinks) ---
DATAFORSEO_LOGIN=you@example.com
DATAFORSEO_PASSWORD=...
DATAFORSEO_USE_SANDBOX=False

# --- optional ---
GOOGLE_PAGESPEED_API_KEY=AIza...
```

Also read by `settings.py` but **not set on the reference machine** — add only
if you need that path: `OPENAI_API_KEY`, `OPENROUTER_BASE_URL` (defaults
correctly; see pitfall 3), `DATABLUE_API_KEY` (alternative SERP provider).

Create the media directory that generated images are written to. It is
gitignored, so it does not arrive with a clone:

```powershell
mkdir media          # inside backend/ ; MEDIA_ROOT = BASE_DIR / 'media'
```

---

## 5. `engine/.env`

The workers read **the engine's own `.env`**, not the backend's. Keys that
matter for background jobs must appear in both files.

```ini
DEBUG=True
SECRET_KEY=change-me
ALLOWED_HOSTS=localhost,127.0.0.1
FRONTEND_URL=http://localhost:8080
BACKEND_API_URL=http://localhost:8000

# same database as the backend
DB_NAME=llm_monitor
DB_USER=postgres
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432

CELERY_BROKER_URL=redis://localhost:6379/5
CELERY_RESULT_BACKEND=redis://localhost:6379/5

# which measurement platforms the sweeps run
ENABLED_PLATFORMS=chatgpt          # add gemini,perplexity,claude as keys allow

OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_INTERNAL_MODEL=openai/gpt-5-mini
OPENROUTER_GEMINI_MODEL=google/gemini-2.5-flash
OPENAI_CHATGPT_MODEL=gpt-4o
ANTHROPIC_MODEL=claude-sonnet-4-5
PERPLEXITY_MODEL=sonar

GEMINI_API_KEY=AIza...             # note: GEMINI_API_KEY here, not GOOGLE_GEMINI_API_KEY
GEMINI_MODEL=gemini-2.5-flash
GEMINI_BACKEND=api

DATAFORSEO_LOGIN=you@example.com
DATAFORSEO_PASSWORD=...
DATAFORSEO_USE_SANDBOX=False
```

Optional: `WEEKLY_SWEEP_BEAT_ENABLED=True` registers the weekly sweep (off by
default, and additionally guarded by a 6-day cooldown).

---

## 6. `frontend/.env`

Vite inlines these at **build** time — restart `npm run dev` after editing.
Never put a secret here; everything in this file ships to the browser.

```ini
VITE_API_BASE_URL=http://localhost:8000
VITE_ENGINE_URL=http://localhost:8001
```

Then:

```powershell
cd frontend
npm install
```

---

## 7. Migrate, create a login, and run

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser    # login is by email
```

Run all five processes. The three Celery commands run **from `engine/`** using
the backend venv's interpreter:

```powershell
# 1. backend API                          (from backend/)
.\.venv\Scripts\python.exe manage.py runserver 8000 --noreload

# 2. engine API                           (from engine/)
..\backend\.venv\Scripts\python.exe manage.py runserver 8001 --noreload

# 3. general worker                       (from engine/)
..\backend\.venv\Scripts\python.exe -m celery -A llm_monitor_engine worker --pool=solo -n default@%h -Q celery --loglevel=info

# 4. SEO worker                           (from engine/)
..\backend\.venv\Scripts\python.exe -m celery -A llm_monitor_engine worker --pool=solo -n seo@%h -Q seo,seo_instant --loglevel=info

# 5. beat — the scheduler                 (from engine/)
..\backend\.venv\Scripts\python.exe -m celery -A llm_monitor_engine beat --loglevel=info

# 6. frontend                             (from frontend/)
npm run dev
```

Two things that bite:

- **`--noreload` is deliberate.** `.env` is read once at startup. After changing
  a key, restart the process.
- **`--pool=solo` is a Windows requirement.** On Linux/macOS drop it and call
  `celery` directly: `celery -A llm_monitor_engine worker -Q celery ...`.
- **The SEO worker must listen on both `seo` and `seo_instant`.** Miss
  `seo_instant` and newly added keywords never get their first rank.

### One-click start (PowerShell)

Save beside the repo, adjust `$root`, run it. Each service gets its own titled
window.

```powershell
$root = "D:\Promptmaxx\llm-monitor"
$py   = "$root\backend\.venv\Scripts\python.exe"
function S($t,$d,$c){ Start-Process powershell -ArgumentList @("-NoExit","-Command",
  "`$host.UI.RawUI.WindowTitle='$t'; Set-Location '$d'; $c") }

S "PMX backend :8000"  "$root\backend"  "$py manage.py runserver 8000 --noreload"
S "PMX engine :8001"   "$root\engine"   "$py manage.py runserver 8001 --noreload"
S "PMX worker"         "$root\engine"   "$py -m celery -A llm_monitor_engine worker --pool=solo -n default@%h -Q celery --loglevel=info"
S "PMX worker seo"     "$root\engine"   "$py -m celery -A llm_monitor_engine worker --pool=solo -n seo@%h -Q seo,seo_instant --loglevel=info"
S "PMX beat"           "$root\engine"   "$py -m celery -A llm_monitor_engine beat --loglevel=info"
S "PMX frontend :8080" "$root\frontend" "npm run dev"
```

---

## 8. Optional: the landing site (`:3000`)

A separate Next.js 16 / React 19 marketing site. Nothing in the app depends on
it — skip it unless you are working on marketing pages.

```powershell
cd landing
npm install
npm run dev          # http://localhost:3000
```

---

## 9. Optional: the MCP server (`:8010`)

```powershell
cd mcp-server
uv venv --python 3.12 .venv
.\.venv\Scripts\pip install -e .
copy .env.example .env
```

In `mcp-server/.env` set `PROMPTMAXX_BASE_URL=http://localhost:8000` plus either
a service API key (`PROMPTMAXX_API_KEY=pmxk_...`, minted in the UI under
Organization Settings → **Get your API key**) or email/password.

Register with Claude Code:

```powershell
claude mcp add promptmaxx -- <abs-path>\mcp-server\.venv\Scripts\python.exe -m promptmaxx_mcp
```

HTTP mode for network clients: `python -m promptmaxx_mcp --http` (port 8010,
callers send `Authorization: Bearer pmxk_...`). Full guide:
`frontend/public/docs/mcp-connection.html`, served at `/docs/mcp-connection.html`.

---

## 10. Verify the install

| Check | Expect |
|---|---|
| `http://localhost:8000/` | JSON 401 — the auth wall means the backend is alive |
| `http://localhost:8080/` | login page |
| Log in with the superuser | dashboard loads |
| Organization Settings → Add Brand | site analyzed, keywords seeded (proves `trafilatura`) |
| Prompts → Generate | reaches 100% in ~1–2 min (proves worker + beat + OpenRouter) |
| SEO → Keywords → add one | rank appears within minutes (proves the `seo_instant` queue + DataForSEO) |
| Content Editor → generate an image | image saved under `backend/media/` (proves `IMAGE_RENDER_MODEL`) |
| Organization Settings → API Keys | Token Consumption panel shows calls and cost |

Quick port check:

```powershell
netstat -ano | findstr "LISTENING" | findstr ":8000 :8001 :8080 :6379 :5432"
```

---

## 11. Ports

| Port | Service |
|---|---|
| 8000 | Backend API (Django) |
| 8001 | Engine API (Django) |
| 8080 | Frontend (Vite) |
| 3000 | Landing site (Next.js, optional) |
| 8010 | MCP server, HTTP mode (optional) |
| 6379 | Redis / Memurai — broker, **db 5** |
| 5432 | PostgreSQL |

---

## 12. Common pitfalls

1. **Generation stuck at 0%** → a Celery worker or beat is not running. The
   backend only queues; the engine executes.
2. **Rank refresh does nothing** → the SEO worker must listen on **both** `seo`
   and `seo_instant`, and the DataForSEO credentials must be in the **engine's**
   `.env`, not just the backend's.
3. **401 "Incorrect API key" from OpenAI during generation** → `OPENROUTER_BASE_URL`
   is pointing at `api.openai.com` while the key is an OpenRouter `sk-or-` key.
   Leave it unset (it defaults correctly) or set
   `https://openrouter.ai/api/v1`, and use vendor-prefixed slugs like
   `openai/gpt-5-mini`.
4. **"Couldn't read the site" on Add Brand** → `trafilatura` is missing from the
   venv (§3).
5. **Changed a key, nothing happened** → `--noreload` reads `.env` at startup
   only. Restart the process.
6. **Image generation fails or returns nothing** → `IMAGE_RENDER_MODEL` must be
   an image-output model. OpenRouter has no free ones; every image costs.
7. **`pip install` fails compiling a wheel** → you are on Python 3.13+. Rebuild
   the venv on 3.12 (§1).
8. **Celery starts then immediately idles on Windows** → `--pool=solo` is
   missing. The default prefork pool does not work on Windows.
9. **Non-US client measured with US context** → the onboarding country map covers
   24 of 116 countries; unsupported picks silently fall back to United States.
   Known issue.
10. **Weekly sweep never runs** → it is only registered when
    `WEEKLY_SWEEP_BEAT_ENABLED=True` in the engine `.env`, and is further guarded
    by a 6-day cooldown and a kill switch.

---

## 13. Moving to a second machine — checklist

- [ ] PostgreSQL 17 installed, `llm_monitor` database created
- [ ] Memurai (or Redis) running on 6379
- [ ] Python 3.12 available (`uv python install 3.12`)
- [ ] Node 18+ (26.x verified)
- [ ] Repo cloned
- [ ] `backend/.venv` created from **both** requirements files, plus `trafilatura`
- [ ] `backend/.env`, `engine/.env`, `frontend/.env` written — **none are in git**
- [ ] `backend/media/` created
- [ ] `manage.py migrate` run, superuser created
- [ ] All five processes started (§7)
- [ ] §10 verification table walked end to end

The three `.env` files are the only thing a clone cannot give you. Copy them
from a working machine over a secure channel — never commit them.
