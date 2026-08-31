# Promptmaxx — Local Setup Guide

How to bring the full stack up on a second machine so it behaves **identically**
to the reference machine. Written for Windows; Linux/macOS differences are noted
inline.

Everything below was read off a running install on 2026-08-31 — versions, env
keys, commands and the admin account were verified against the live database and
the actual source, not copied from memory.

---

## 0. What you are installing

Five processes plus two data stores, all on one machine. No Docker.

```
llm-monitor/
├── backend/     Django REST API           :8000
├── engine/      Django + Celery workers   :8001  + 3 background processes
├── frontend/    React / Vite app UI       :8080
├── landing/     Next.js marketing site    :3000   (optional)
└── mcp-server/  MCP server for Claude     :8010   (optional)
```

Backend and engine **share one PostgreSQL database**. The backend records work
into that database; the engine's Celery **beat** picks it up and the **workers**
execute it. If the workers or beat are not running, the UI looks completely alive
but nothing ever finishes.

> The backend has **no Celery app of its own** — there is no
> `backend/llm_monitor/celery.py`, and its `settings.py` reads no `CELERY_*` keys.
> All background execution lives in the engine.

---

## 1. Prerequisites

Verified on the reference machine. Anything at or above these works.

| Requirement | Verified version | Check |
|---|---|---|
| Python (for the venv) | **3.12.14** | `py -3.12 --version` |
| Python (system, incidental) | 3.14.5 | `python --version` |
| uv | 0.12.5 | `uv --version` |
| Node.js | 26.2.0 | `node --version` |
| npm | 11.13.0 | `npm --version` |
| PostgreSQL | 17.x | `psql --version` |
| Redis — on Windows, **Memurai** | Memurai 4.1.2 | `memurai-cli --version` |
| Git | 2.55.0 | `git --version` |

> **Use Python 3.12, not 3.13+.** The venv here is 3.12.14 even though the system
> Python is 3.14.5, because some pinned wheels do not build on 3.13+.
> `uv python install 3.12` supplies the interpreter without touching your system
> Python; `py -3.12 -m venv` works too if you already have it.

**Windows Redis:** use [Memurai](https://www.memurai.com/) — a native Redis build
that installs as a Windows service, so it is running before you start anything.
Redis under WSL also works. Celery needs a broker on `localhost:6379`; the app
uses **database 5**.

**Windows console encoding:** several management commands print emoji. On a
default `cp1252` console they crash with
`UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f4ca'`.
Set `PYTHONIOENCODING=utf-8` for every Python process — permanently:

```powershell
setx PYTHONIOENCODING utf-8      # affects new shells only; reopen the shell
```

---

## 2. Carry these across from the working machine

A `git clone` gives you all the code, both `requirements.txt` files and the
`package-lock.json` files. It **cannot** give you the following — every item is
gitignored. Copy them over a secure channel; never commit them.

| Item | Why you need it |
|---|---|
| `backend/.env` | 28 keys: DB password, OpenRouter / Gemini / DataForSEO / PageSpeed keys |
| `engine/.env` | 25 keys — the workers read this file, **not** the backend's |
| `frontend/.env` | 2 keys (`frontend/.env.example` is tracked, so this one is reproducible) |
| `landing/.env.local` | 2 keys — only if you run the landing site |
| `mcp-server/.env` | 3 keys — only if you use the MCP server |
| `pg_dump` of `llm_monitor` | **optional.** Without it you get a working but empty app: no brands, prompts, keywords or rank history |
| `backend/media/` | **optional.** Generated images from the content editor |

§5 lists the full key set for every one of those files, so you can rebuild them
by hand if you only carry the secret *values* across.

---

## 3. Clone and create the database

```bash
git clone https://github.com/arun-andiselvam/llm-monitor.git
cd llm-monitor
```

```bash
psql -U postgres -c "CREATE DATABASE llm_monitor;"
```

**If you are restoring a dump, restore it now**, before migrating:

```bash
psql -U postgres -d llm_monitor -f llm_monitor.dump
```

---

## 4. Python environment — one shared venv

The reference machine uses a **single venv at `backend/.venv`** for the backend,
the engine and all three Celery processes. `backend/requirements.txt` (341
packages) is a superset of `engine/requirements.txt` (45), so one environment
covers both. There is **no `engine/.venv`** — the run commands in §7 depend on
that.

```powershell
cd backend
uv venv --python 3.12 .venv          # or: py -3.12 -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\pip install -r ..\engine\requirements.txt
.\.venv\Scripts\pip install trafilatura
```

`trafilatura` (2.0.0) is in **neither** requirements file but is required by the
onboarding site-crawl. Without it, "Add Brand" fails with "couldn't read the site".

Verify — these are the reference versions:

```powershell
.\.venv\Scripts\python.exe -c "import importlib.metadata as m; print(m.version('Django'), m.version('celery'), m.version('redis'), m.version('trafilatura'))"
# expect: 5.2 5.3.6 5.0.8 2.0.0
```

> Prefer isolated venvs? Create `engine/.venv` from `engine/requirements.txt` and
> point the engine commands at it instead. Both layouts work; only the
> interpreter paths in §7 change.

---

## 5. Environment files

Five files. None are in git. Values below are placeholders — bring the real ones.

### 5.1 `backend/.env` — 28 keys

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
DB_HOST=127.0.0.1
DB_PORT=5432

# --- inert here, but present on the reference machine ---
# The backend has no Celery app; nothing reads this key. Harmless.
CELERY_BROKER_URL=redis://localhost:6379/5

# --- LLM transport (nearly everything routes through OpenRouter) ---
# OpenRouter slugs need the vendor prefix.
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_INTERNAL_MODEL=openai/gpt-5-mini
OPENROUTER_GEMINI_MODEL=google/gemini-2.5-flash
OPENAI_CHATGPT_MODEL=gpt-4o
ANTHROPIC_MODEL=claude-sonnet-4-5
PERPLEXITY_MODEL=sonar

# --- Google Gemini (direct, for some analysis paths) ---
GOOGLE_GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-2.5-flash
GEMINI_BACKEND=api

# --- image generation (content editor) ---
# Stage 1 writes the prompt with a text model; empty falls back to
# OPENROUTER_INTERNAL_MODEL. Stage 2 renders pixels — OpenRouter has NO free
# image models, so this stage always costs money.
IMAGE_PROMPT_TEXT_MODEL=
IMAGE_RENDER_MODEL=google/gemini-2.5-flash-image

# --- SEO data (rankings, volume, backlinks) ---
DATAFORSEO_LOGIN=you@example.com
DATAFORSEO_PASSWORD=...
DATAFORSEO_USE_SANDBOX=False

# --- optional ---
GOOGLE_PAGESPEED_API_KEY=AIza...
```

> `GEMINI_BACKEND` — only the literal value `vertex` changes behaviour (it routes
> Gemini through Vertex AI and then also needs `VERTEX_PROJECT` and
> `GOOGLE_APPLICATION_CREDENTIALS`). Every other value, including the `api` used
> here and the code default `aistudio`, takes the plain API-key path.

`settings.py` reads many more keys than this — `OPENAI_API_KEY`,
`OPENROUTER_BASE_URL`, `DATABLUE_API_KEY`, `MAILGUN_*`, `MOZ_*`,
`SCRAPINGDOG_API_KEY`, `VERTEX_*` — but **none of them are set on the reference
machine**, and each has a working default. Add one only when you need that path.

### 5.2 `engine/.env` — 25 keys

The workers read the **engine's own** `.env`. Keys that matter to background jobs
must appear in both files.

```ini
DEBUG=True
SECRET_KEY=change-me
ALLOWED_HOSTS=localhost,127.0.0.1
FRONTEND_URL=http://localhost:8080
BACKEND_API_URL=http://localhost:8000

# Same database as the backend — you MUST set these.
# The engine's built-in defaults are DB_USER=arun / DB_PASSWORD=admin,
# which will not exist on your machine.
DB_NAME=llm_monitor
DB_USER=postgres
DB_PASSWORD=your-db-password
DB_HOST=127.0.0.1
DB_PORT=5432

CELERY_BROKER_URL=redis://localhost:6379/5
CELERY_RESULT_BACKEND=redis://localhost:6379/5

# Which measurement platforms the sweeps run.
ENABLED_PLATFORMS=chatgpt          # add gemini,perplexity,claude as keys allow

OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_INTERNAL_MODEL=openai/gpt-5-mini
OPENROUTER_GEMINI_MODEL=google/gemini-2.5-flash
OPENAI_CHATGPT_MODEL=gpt-4o
ANTHROPIC_MODEL=claude-sonnet-4-5
PERPLEXITY_MODEL=sonar

GEMINI_API_KEY=AIza...             # note: GEMINI_API_KEY here, NOT GOOGLE_GEMINI_API_KEY
GEMINI_MODEL=gemini-2.5-flash
GEMINI_BACKEND=api

DATAFORSEO_LOGIN=you@example.com
DATAFORSEO_PASSWORD=...
DATAFORSEO_USE_SANDBOX=False
```

Optional: `WEEKLY_SWEEP_BEAT_ENABLED=True` registers the weekly sweep. It is off
by default and further guarded by a 6-day cooldown and a preflight check.

### 5.3 `frontend/.env`

Vite inlines these at **build** time — restart `npm run dev` after editing. Never
put a secret here; everything in this file ships to the browser.
`frontend/.env.example` is tracked and documents the optional overrides.

```ini
VITE_API_BASE_URL=http://localhost:8000
VITE_ENGINE_URL=http://localhost:8001
```

```powershell
cd frontend
npm install
```

Port 8080 is hardcoded in `frontend/vite.config.ts`; no flag is needed.

### 5.4 `landing/.env.local` — only if you run the landing site

```ini
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:8080
```

### 5.5 `mcp-server/.env` — only if you use the MCP server

```ini
PROMPTMAXX_BASE_URL=http://localhost:8000
PROMPTMAXX_EMAIL=admin@local.test
PROMPTMAXX_PASSWORD=your-admin-password
```

### 5.6 The media directory

Generated images are written to `MEDIA_ROOT = backend/media`. It is gitignored,
so it does not arrive with a clone:

```powershell
mkdir backend\media
```

---

## 6. Migrate and create the admin account

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py migrate
```

The reference machine has **115 migrations applied and 0 pending**.

### Do NOT use `createsuperuser`

The user model is `authentication.Account` (`USERNAME_FIELD = 'email'`,
`REQUIRED_FIELDS = ['username']`). Its `organisation` field is **`null=False,
blank=False`**, and there is no custom `create_superuser` manager — so Django's
built-in `createsuperuser` never sets an organisation and fails on a NOT NULL
violation. It is also interactive, which is useless in an automated setup.

### Use `seed_admin` instead

`backend/authentication/management/commands/seed_admin.py` creates the
Organisation, the Account (`role='super_admin'`, staff, superuser, active) and
all 30 module permissions in one transaction:

```powershell
.\.venv\Scripts\python.exe manage.py seed_admin --email "admin@local.test" --password "your-password" --organisation-name "Local Dev Org"
```

Pass all three flags explicitly — the defaults are `admin@pivotroots.com` /
`admin123` / organisation `PivotRoots Updated`.

> **`seed_admin` DELETES any existing account with that email** (and its
> permission rows) before recreating it. That is fine on a fresh database. If you
> restored a dump in §3 and want to keep that account's data, change the password
> in place instead:
>
> ```powershell
> .\.venv\Scripts\python.exe manage.py shell -c "from authentication.models import Account; u=Account.objects.get(email='admin@local.test'); u.set_password('your-password'); u.save()"
> ```

Reference account, for comparison: `admin@local.test`, username `admin`, role
`super_admin`, organisation `Local Dev Org`, `pbkdf2_sha256` hash. (`seed_admin`
sets `username` to the email rather than `admin`, and creates 30 permission rows
where the reference account has 0. Neither difference affects login or behaviour
— login is by email, and `role='super_admin'` governs access.)

---

## 7. Run all five processes — without opening extra terminals

The three Celery commands run **from `engine/`** using the **backend venv's**
interpreter.

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

Three things that bite:

- **`--noreload` is deliberate.** `.env` is read once at startup. After changing a
  key, restart the process.
- **`--pool=solo` is a Windows requirement.** The default prefork pool does not
  work on Windows — the worker starts and then silently idles. On Linux/macOS drop
  it and call `celery` directly.
- **The SEO worker must listen on both `seo` and `seo_instant`.**
  `CELERY_TASK_ROUTES` sends rank crawls and backlink fetches to `seo`, and newly
  added keywords to `seo_instant`. Miss `seo_instant` and new keywords never get a
  first rank.

### Running them headless (no extra windows)

To keep everything in one session with logs on disk, start each as a hidden
process writing to `logs/`:

```powershell
$root = "D:\Promptmaxx\llm-monitor"
$py   = "$root\backend\.venv\Scripts\python.exe"
New-Item -ItemType Directory -Force "$root\logs" | Out-Null
$env:PYTHONIOENCODING = "utf-8"

function Svc($name, $dir, $exe, $argline) {
  Start-Process -FilePath $exe -ArgumentList $argline -WorkingDirectory $dir `
    -WindowStyle Hidden `
    -RedirectStandardOutput "$root\logs\$name.log" `
    -RedirectStandardError  "$root\logs\$name.err.log"
}

Svc backend  "$root\backend"  $py "manage.py runserver 8000 --noreload"
Svc engine   "$root\engine"   $py "manage.py runserver 8001 --noreload"
Svc worker   "$root\engine"   $py "-m celery -A llm_monitor_engine worker --pool=solo -n default@%h -Q celery --loglevel=info"
Svc seo      "$root\engine"   $py "-m celery -A llm_monitor_engine worker --pool=solo -n seo@%h -Q seo,seo_instant --loglevel=info"
Svc beat     "$root\engine"   $py "-m celery -A llm_monitor_engine beat --loglevel=info"
Svc frontend "$root\frontend" "npm.cmd" "run dev"
```

Read `logs/*.err.log` after starting — a process that dies on a bad `.env` key
exits immediately and leaves the reason there.

To stop everything: `Get-Process python,node | Stop-Process`.

---

## 8. Optional: the landing site (`:3000`)

A separate Next.js 16 / React 19 marketing site. Nothing in the app depends on it
— skip it unless you are working on marketing pages. Needs `landing/.env.local`
from §5.4.

```powershell
cd landing
npm install
npm run dev          # http://localhost:3000
```

---

## 9. Optional: the MCP server (`:8010`)

This one **does** get its own venv.

```powershell
cd mcp-server
uv venv --python 3.12 .venv
.\.venv\Scripts\pip install -e .
```

Create `mcp-server/.env` per §5.5 — either the email/password pair used on the
reference machine, or a service API key (`PROMPTMAXX_API_KEY=pmxk_...`, minted in
the UI under Organization Settings → **Get your API key**).

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
| Log in as `admin@local.test` | dashboard loads |
| Organization Settings → Add Brand | site analyzed, keywords seeded (proves `trafilatura`) |
| Prompts → Generate | reaches 100% in ~1–2 min (proves worker + beat + OpenRouter) |
| SEO → Keywords → add one | rank appears within minutes (proves the `seo_instant` queue + DataForSEO) |
| Content Editor → generate an image | image saved under `backend/media/` (proves `IMAGE_RENDER_MODEL`) |
| Organization Settings → API Keys | Token Consumption panel shows calls and cost |

Port check — all five should be listening:

```powershell
netstat -ano | findstr "LISTENING" | findstr ":8000 :8001 :8080 :6379 :5432"
```

Celery check — both workers should answer, and between them cover `celery`,
`seo` and `seo_instant`:

```powershell
cd engine
..\backend\.venv\Scripts\python.exe -m celery -A llm_monitor_engine inspect active_queues
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

## 12. Things NOT to do

- **Do not run `manage.py create_partitions`.** The command exists and looks like
  setup, but the reference machine's five analytics tables (`prompt_analytics`,
  `competitor_analytics`, `topic_analytics`, `sentiment_analytics`,
  `share_of_voice_analytics`) are **not partitioned** — `check_partition_status`
  reports "Table is NOT partitioned" for all five. Running it would give you a
  different database shape, not a matching one.
- **Do not run `manage.py createsuperuser`** — see §6.
- **Do not create `engine/.venv`** unless you also change every path in §7.
- **Do not commit any `.env` file.**

---

## 13. Common pitfalls

1. **`createsuperuser` fails with a NOT NULL error on `organisation_id`** → use
   `seed_admin` (§6).
2. **`UnicodeEncodeError: 'charmap' codec can't encode character`** → Windows
   console encoding. Set `PYTHONIOENCODING=utf-8` (§1).
3. **Generation stuck at 0%** → a Celery worker or beat is not running. The
   backend only records the request; the engine executes it.
4. **Rank refresh does nothing** → the SEO worker must listen on **both** `seo`
   and `seo_instant`, and the DataForSEO credentials must be in the **engine's**
   `.env`, not just the backend's.
5. **Engine cannot connect to the database** → `engine/.env` is missing its `DB_*`
   block. The engine's built-in defaults are `arun` / `admin`, not `postgres`.
6. **401 "Incorrect API key" from OpenAI during generation** →
   `OPENROUTER_BASE_URL` is pointing at `api.openai.com` while the key is an
   OpenRouter `sk-or-` key. Leave it unset — it already defaults to
   `https://openrouter.ai/api/v1` — and use vendor-prefixed slugs like
   `openai/gpt-5-mini`.
7. **"Couldn't read the site" on Add Brand** → `trafilatura` is missing from the
   venv (§4).
8. **Changed a key, nothing happened** → `--noreload` reads `.env` at startup
   only. Restart the process.
9. **Image generation fails or returns nothing** → `IMAGE_RENDER_MODEL` must be an
   image-output model. OpenRouter has no free ones; every image costs.
10. **`pip install` fails compiling a wheel** → you are on Python 3.13+. Rebuild
    the venv on 3.12 (§1).
11. **Celery starts then immediately idles on Windows** → `--pool=solo` is missing.
12. **Non-US client measured with US context** → the onboarding country map covers
    24 of 116 countries; unsupported picks silently fall back to United States.
    Known issue.
13. **Weekly sweep never runs** → only registered when
    `WEEKLY_SWEEP_BEAT_ENABLED=True` in the engine `.env`, and further guarded by
    a 6-day cooldown and a preflight check.

---

## 14. Second-machine checklist

- [ ] PostgreSQL installed, `llm_monitor` database created
- [ ] Memurai (or Redis) running on 6379
- [ ] Python 3.12 available (`uv python install 3.12`)
- [ ] Node 18+ (26.x verified)
- [ ] `PYTHONIOENCODING=utf-8` set
- [ ] Repo cloned
- [ ] Dump restored, if you want the existing data — **before** `migrate`
- [ ] `backend/.venv` built from **both** requirements files, plus `trafilatura`
- [ ] `backend/.env`, `engine/.env`, `frontend/.env` written — **none are in git**
- [ ] `landing/.env.local`, `mcp-server/.env` — only if using those
- [ ] `backend/media/` created (and copied over, if you want the old images)
- [ ] `manage.py migrate` clean — 115 applied, 0 pending
- [ ] `seed_admin` run with explicit `--email --password --organisation-name`
- [ ] `npm install` in `frontend/`
- [ ] All five processes started (§7), `logs/*.err.log` clean
- [ ] §10 verification table walked end to end

The `.env` files are the only thing a clone cannot give you. Copy them from a
working machine over a secure channel — never commit them.
