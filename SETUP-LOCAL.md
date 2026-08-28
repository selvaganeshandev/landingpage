# Promptmaxx — Local Setup Guide

Complete instructions to run the full stack on a local machine (written for Windows;
Linux/macOS differences noted inline). Verified against a working local install.

---

## 1. Prerequisites

| Requirement | Version | Check |
|---|---|---|
| Python | 3.12+ | `python --version` |
| Node.js + npm | 18+ | `node --version` |
| PostgreSQL | 14+ | running locally, a database created (e.g. `llm_monitor`) |
| Redis | any recent | running on `localhost:6379` (Windows: Memurai or Redis-on-WSL both work) |
| Git | any | — |

---

## 2. Clone

```bash
git clone https://github.com/arun-andiselvam/llm-monitor.git
cd llm-monitor
```

The repo has three apps side by side:

```
llm-monitor/
├── backend/     # Django REST API  (port 8000)
├── engine/      # Django + Celery workers (port 8001 + background jobs)
├── frontend/    # React/Vite UI   (port 8080)
└── mcp-server/  # optional MCP server for Claude / integrations
```

---

## 3. Backend (port 8000)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt      # Linux: .venv/bin/pip
.\.venv\Scripts\pip install trafilatura              # used by onboarding site-crawl; not in requirements
```

Create `backend/.env` (gitignored). Minimum working set:

```ini
DEBUG=True
SECRET_KEY=change-me
ALLOWED_HOSTS=localhost,127.0.0.1
# --- database ---
DB_NAME=llm_monitor
DB_USER=postgres
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432
SITE_URL=http://localhost:8000
CORS_ALLOWED_ORIGINS=http://localhost:8080
# --- LLM transports ---
OPENAI_API_KEY=sk-proj-...                       # OpenAI direct (measurement fallbacks, some paths)
OPENROUTER_API_KEY=sk-or-v1-...                  # OpenRouter (generation, humanise, internal calls)
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1 # IMPORTANT: must point at OpenRouter, not api.openai.com
OPENROUTER_INTERNAL_MODEL=openai/gpt-4o-mini     # OpenRouter slugs need the vendor prefix
OPENAI_INTERNAL_MODEL=gpt-4o-mini
# --- SEO collectors (optional but needed for rankings/backlinks/volume) ---
DATABLUE_API_KEY=wh_...                          # SERP scraping (rank tracking)
DATAFORSEO_LOGIN=you@example.com                 # volume + backlinks
DATAFORSEO_PASSWORD=...
# --- AI detection (optional) ---
HUGGINGFACE_API_KEY=hf_...                       # token needs "Inference Providers" permission
```

Migrate and create your login:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser   # email-based login
```

> Password reset later (non-interactive environments):
> `manage.py shell` → `u = get_user_model().objects.get(email='...'); u.set_password('...'); u.save()`

Run:

```powershell
.\.venv\Scripts\python.exe manage.py runserver 8000 --noreload
```

`--noreload` matters: `.env` is read at startup only — after changing keys, restart the process.

---

## 4. Engine (port 8001 + Celery)

```powershell
cd ..\engine
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

Create `engine/.env` — same DB block as the backend (they share one database), plus:

```ini
DEBUG=True
SECRET_KEY=change-me
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=llm_monitor
DB_USER=postgres
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432
SITE_URL=http://localhost:8001
CORS_ALLOWED_ORIGINS=http://localhost:8080
OPENAI_API_KEY=sk-proj-...
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_INTERNAL_MODEL=openai/gpt-4o-mini
OPENAI_INTERNAL_MODEL=gpt-4o-mini
ENABLED_PLATFORMS=chatgpt                        # add gemini,perplexity,claude when keys exist
# SEO keys must ALSO be here — the workers read the engine's .env, not the backend's:
DATABLUE_API_KEY=wh_...
DATAFORSEO_LOGIN=you@example.com
DATAFORSEO_PASSWORD=...
```

The engine is **four processes**:

```powershell
# 1. engine web API
.\.venv\Scripts\python.exe manage.py runserver 8001 --noreload

# 2. general worker (AI sweeps, prompt generation, analytics)
.\.venv\Scripts\celery.exe -A llm_monitor_engine worker --pool=solo --loglevel=info

# 3. SEO worker (rank crawls + instant lane for freshly added keywords)
.\.venv\Scripts\celery.exe -A llm_monitor_engine worker --pool=solo -Q seo,seo_instant --hostname=seo@%h --loglevel=info

# 4. beat (the clock — schedules everything)
.\.venv\Scripts\celery.exe -A llm_monitor_engine beat --loglevel=info
```

> Linux/macOS: drop `--pool=solo` (it is a Windows requirement) and use `celery -A llm_monitor_engine worker ...`.

**If any of these four are missing, things silently sit in queues**: prompt
generation stuck at 0%, rank refreshes never running, etc. All four must be up.

---

## 5. Frontend (port 8080)

```powershell
cd ..\frontend
npm install
npm run dev          # serves http://localhost:8080
```

Log in with the superuser you created. UI talks to the backend on :8000.

---

## 6. One-click start (optional)

Create `start-promptmaxx.ps1` beside the repo (adjust the root path) — opens each
service in its own titled window:

```powershell
$root = "C:\path\to\llm-monitor"
function S($t,$d,$c){ Start-Process powershell -ArgumentList @("-NoExit","-Command",
  "`$host.UI.RawUI.WindowTitle='$t'; Set-Location '$d'; $c") }
S "PMX backend :8000"  "$root\backend"  ".\.venv\Scripts\python.exe manage.py runserver 8000 --noreload"
S "PMX engine :8001"   "$root\engine"   ".\.venv\Scripts\python.exe manage.py runserver 8001 --noreload"
S "PMX worker"         "$root\engine"   ".\.venv\Scripts\celery.exe -A llm_monitor_engine worker --pool=solo --loglevel=info"
S "PMX worker seo"     "$root\engine"   ".\.venv\Scripts\celery.exe -A llm_monitor_engine worker --pool=solo -Q seo,seo_instant --hostname=seo@%h --loglevel=info"
S "PMX beat"           "$root\engine"   ".\.venv\Scripts\celery.exe -A llm_monitor_engine beat --loglevel=info"
S "PMX frontend :8080" "$root\frontend" "npm run dev"
```

---

## 7. Verify the install

| Check | Expect |
|---|---|
| `http://localhost:8000/` in a browser | JSON 401 (auth wall — backend alive) |
| `http://localhost:8080/` | login page |
| Add a brand (Organization Settings → Add Brand) | site analyzed, keywords seeded |
| Prompts → Generate | run reaches 100% within ~1–2 min (proves worker + beat + OpenRouter) |
| SEO → Keywords → add one | rank appears within minutes (proves seo_instant worker + DataBlue key) |

---

## 8. Optional: the MCP server (Claude / integrations)

```powershell
cd ..\mcp-server
python -m venv .venv
.\.venv\Scripts\pip install -e .
copy .env.example .env
```

In `mcp-server/.env` set `PROMPTMAXX_BASE_URL=http://localhost:8000` and either a
service API key (`PROMPTMAXX_API_KEY=pmxk_...` — minted in the UI under
Organization Settings → **Get your API key**) or email/password. Register with
Claude Code:

```powershell
claude mcp add promptmaxx -- <abs-path>\mcp-server\.venv\Scripts\python.exe -m promptmaxx_mcp
```

HTTP mode for network clients: `python -m promptmaxx_mcp --http` (port 8010,
callers authenticate with `Authorization: Bearer pmxk_...`). Full guide:
`frontend/public/docs/mcp-connection.html` (served at `/docs/mcp-connection.html`).

---

## 9. Ports summary

| Port | Service |
|---|---|
| 8000 | Backend API (Django) |
| 8001 | Engine web API (Django) |
| 8080 | Frontend (Vite) |
| 8010 | MCP server HTTP mode (optional) |
| 6379 | Redis (broker, db 5) |
| 5432 | PostgreSQL |

---

## 10. Common pitfalls (all learned the hard way)

1. **"Generation stuck at 0%"** → Celery worker or beat isn't running (§4). The backend only queues; the engine executes.
2. **Rank refresh does nothing** → the SEO worker must listen on **both** `seo` and `seo_instant` queues; DataBlue key must be in the **engine's** `.env`.
3. **401 "Incorrect API key" from OpenAI on generation** → `OPENROUTER_BASE_URL` points at api.openai.com while the key is an OpenRouter `sk-or-` key. Point it at `https://openrouter.ai/api/v1` and use vendor-prefixed model slugs (`openai/gpt-4o-mini`).
4. **"couldn't read the site" on Add Brand** → `trafilatura` missing in the backend venv (§3).
5. **Changed a key, nothing happened** → `--noreload` servers read `.env` at startup; restart the process.
6. **AI-detect 403** → the HuggingFace token needs the *Inference Providers* permission (fine-grained token checkbox, or a classic Read token).
7. **Non-US client measured with US context** → the onboarding country map covers 24 of 116 countries; unsupported picks silently fall back to United States. Known issue.
8. **Weekly sweep didn't run** → it's registered only when `WEEKLY_SWEEP_BEAT_ENABLED=True` in the engine `.env`, and guarded by a 6-day cooldown + kill switch.
