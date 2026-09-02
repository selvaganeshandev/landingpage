# Deploy commands — production `17d10966`

Exact, copy-paste commands to deploy the current `production` branch to
`app.promptmaxx.co`. This is the pre-filled companion to
[`DEPLOY_HANDOVER.md`](DEPLOY_HANDOVER.md) — read that first for the *why*; use
this for the *what to type*.

**State at time of writing**
- `production` (and `main`) at **`17d10966`** — deploy-ready, verified.
- Frontend bundle already built + verified against production URLs.
  Entry bundle: **`index-D-dZ8DcB.js`** (localhost refs: 0, prod URL present).
- **No migrations** in this release.

> These commands only affect the live server when run from a machine with the
> `~/.ssh/llm_monitor` key. Writing/reading this file changes nothing.

---

## 0. Prerequisites (one-time)

```bash
# SSH access must work (Arun installs your public key first):
ssh promptmaxx 'whoami; hostname'      # expect: root / LLM-Monitor-Product

# Add the key the new ask-agent "explore website" feature needs.
# (Missing => feature returns a clean "not configured" message, never a crash.)
ssh promptmaxx "grep -q '^DATABLUE_API_KEY=' /root/python/v3.12/llm-monitor/backend/.env \
  || echo 'DATABLUE_API_KEY=<DATABLUE_API_KEY — get from Arun / secrets vault>' >> /root/python/v3.12/llm-monitor/backend/.env"

# OPTIONAL — output-token caps (defaults apply if omitted: 64000 / 8192).
# Set CONTENT_MAX_TOKENS=24576 here if production should keep the OLD ceiling.
# ssh promptmaxx "echo 'CONTENT_MAX_TOKENS=64000'      >> /root/python/v3.12/llm-monitor/backend/.env"
# ssh promptmaxx "echo 'CONTENT_FREE_MAX_TOKENS=8192'  >> /root/python/v3.12/llm-monitor/backend/.env"
```

---

## 1. Before you start — check for queued work

```bash
ssh promptmaxx 'cd /root/python/v3.12/llm-monitor/backend && /root/python/v3.12/env/bin/python manage.py shell -c "
from prompts.models import PromptGenerationRun as R
print(list(R.objects.filter(status=\"INIT\").values_list(\"id\",\"domain_id\")))"'
```
A non-empty list = a run fires seconds after restart and spends OpenRouter
credits. Delete it first, or ask Arun.

---

## 2. Phase 2 — backend & engine (additive, invisible to users)

```bash
# 2a. Pre-flight — WRITE DOWN this SHA (your rollback point):
ssh promptmaxx 'cd /root/python/v3.12/llm-monitor && git rev-parse HEAD'
ssh promptmaxx 'cd /root/python/v3.12/llm-monitor && git status --porcelain | grep -v "^??"'   # must be empty

# 2b. Pull production:
ssh promptmaxx 'cd /root/python/v3.12/llm-monitor && git fetch origin && git reset --hard origin/production'

# 2c. Migrations — NONE in this release, so this prints nothing:
ssh promptmaxx 'cd /root/python/v3.12/llm-monitor/backend && /root/python/v3.12/env/bin/python manage.py showmigrations | grep -B3 "\[ \]"'

# 2d. Verify it BOOTS, then restart the five services:
ssh promptmaxx 'cd /root/python/v3.12/llm-monitor/backend && /root/python/v3.12/env/bin/python manage.py check'
ssh promptmaxx 'systemctl restart gunicorn engine engine-celery engine-celery-beat engine-celery-seo'
ssh promptmaxx 'systemctl is-active gunicorn engine engine-celery engine-celery-beat engine-celery-seo nginx'   # all 6 = active

# 2e. Smoke test — 401 is CORRECT (route exists + auth wired). 404 = not deployed, 500 = broken:
ssh promptmaxx "curl -s -o /dev/null -w '%{http_code}\n' https://app.promptmaxx.co/"                        # 200
ssh promptmaxx "curl -s -o /dev/null -w '%{http_code}\n' https://promtmaxxservice.rankmax.io/auth/profile/"  # 401
ssh promptmaxx "curl -s -o /dev/null -w '%{http_code}\n' https://promtmaxxservice.rankmax.io/v1/workspaces"  # 401 (new /v1 surface)
```

---

## 3. Phase 3 — frontend (only user-visible step; reversible)

```bash
# 3a. Back up the webroot (there is no other copy):
ssh promptmaxx "cp -a /var/www/html /var/www/html.bak-\$(date +%Y%m%d-%H%M%S)"

# 3b/3c. ALREADY DONE — dist/ built + verified against production URLs.
#        Entry bundle: index-D-dZ8DcB.js
#        Only re-run `npm run build` if you FIRST put the production URLs in
#        frontend/.env.local:
#          VITE_API_BASE_URL=https://promtmaxxservice.rankmax.io
#          VITE_ENGINE_URL=http://64.227.190.42:8001
#        Building with the local (localhost) env ships a broken frontend.

# 3d. Upload the built bundle:
cd frontend
rsync -az --delete -e "ssh -i ~/.ssh/llm_monitor" dist/ root@64.227.190.42:/var/www/html/
ssh promptmaxx 'rm -f /var/www/html/.DS_Store'

# 3e. Confirm the live site serves the bundle we built:
curl -s https://app.promptmaxx.co/ | grep -o 'index-[A-Za-z0-9_-]*\.js'
# ^ must print: index-D-dZ8DcB.js
```

---

## 4. Rollback

| Layer | Command |
|---|---|
| Frontend | `ssh promptmaxx "rsync -a --delete /var/www/html.bak-<ts>/ /var/www/html/"` |
| Backend / engine | `ssh promptmaxx 'cd /root/python/v3.12/llm-monitor && git reset --hard <SHA_FROM_2a>'` then restart the five services |
| Migrations | none to roll back this release |

---

## 5. Post-deploy checklist

- [ ] `systemctl is-active` — all six report `active`
- [ ] `https://app.promptmaxx.co/` returns 200
- [ ] Served bundle hash == `index-D-dZ8DcB.js`
- [ ] New endpoints return **401**, not 404/500 (`/v1/workspaces`, `/content/suggest-anchor-links/`, `/api/prompts/refresh-domain/`)
- [ ] `DATABLUE_API_KEY` present in prod `backend/.env` (ask-agent explore)
- [ ] `showmigrations | grep -c "\[ \]"` is 0
- [ ] Rollback SHA from 2a written down

---

## Why this is low-risk

- **No migrations / no schema change** → no DB maintenance window.
- **Phase 2 is additive** → the live frontend never calls the new endpoints, so
  backend changes are invisible until Phase 3.
- **Phase 3 backs up first** → one command restores the old UI.
- **Every step verifies** before moving on (`check`, `is-active`, smoke tests, hash match).
- The only real mistake to avoid is **rebuilding the frontend without production
  URLs** — the current `dist/` is already built correctly, so just upload it.
