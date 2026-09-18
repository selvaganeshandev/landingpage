# Deploying PromptMaxx — handover guide

Everything you need to deploy `app.promptmaxx.co` from your own machine.

Read [`deployment.md`](deployment.md) and [`server-connect.md`](server-connect.md)
in this repo before your first deploy — this file is the condensed version of both.

---

## What Arun must give you first

You cannot deploy until all four are in place. Ask for them together:

| # | Thing | Notes |
|---|---|---|
| 1 | Your SSH public key added to the server | You generate the key, send only the `.pub` |
| 2 | GitHub push access to `arun-andiselvam/llm-monitor` | Needed for the `production` branch |
| 3 | The two `VITE_` values for `frontend/.env.local` | Not in git. The build is broken without them |
| 4 | *(optional)* `backend/.env` | Only for the local pre-flight check in Phase 1 |

The server pulls from GitHub using **its own** deploy key, so you never put your
GitHub credentials on the server.

> **Note on `backend/.env`:** local development connects to the **production**
> database through an SSH tunnel, not a local one. That file therefore carries
> live database credentials. You can skip it — Phase 2 runs the identical check
> on the server anyway.

---

## One-off setup

### 1. Generate an SSH key

```bash
ssh-keygen -t ed25519 -C "<your-name>-llm-monitor" -f ~/.ssh/llm_monitor
```

Send Arun **`~/.ssh/llm_monitor.pub`** only — never the private file.

### 2. Add a host alias

Once he confirms the key is installed:

```bash
cat >> ~/.ssh/config <<'EOF'
Host promptmaxx
    HostName 64.227.190.42
    User root
    IdentityFile ~/.ssh/llm_monitor
    IdentitiesOnly yes
EOF
```

Test it:

```bash
ssh promptmaxx 'whoami; hostname'      # expect: root / LLM-Monitor-Product
```

### 3. Clone the repo

```bash
git clone git@github.com:arun-andiselvam/llm-monitor.git
cd llm-monitor
git checkout production
```

### 4. Frontend toolchain

Node 24 / npm 11.

```bash
cd frontend && npm ci
```

### 5. Create `frontend/.env.local`

**This file is not in git and the frontend build is wrong without it.**

```
VITE_API_BASE_URL=https://promtmaxxservice.rankmax.io
VITE_ENGINE_URL=http://64.227.190.42:8001
```

---

## The server at a glance

| | |
|---|---|
| Host | `64.227.190.42` — `app.promptmaxx.co`, `promtmaxx.rankmax.io` |
| API | `promtmaxxservice.rankmax.io` |
| Deploy root | `/root/python/v3.12/llm-monitor` |
| Python | `/root/python/v3.12/env/bin/python` |
| Frontend webroot | `/var/www/html` — **not** the repo's `frontend/dist` |
| Branch deployed | **`production`**, not `main` |

Services: `gunicorn`, `engine`, `engine-celery`, `engine-celery-beat`,
`engine-celery-seo`, `nginx`.

The frontend is **built on your machine and uploaded**. It is not built on the
server — the `frontend/dist` directory there is stale and unused.

---

## Before you start: check for queued work

Anything sitting in a queued state in the database **starts executing the moment
the engine restarts**, including rows created during local testing — remember
that local dev talks to the production database.

```bash
ssh promptmaxx 'cd /root/python/v3.12/llm-monitor/backend && /root/python/v3.12/env/bin/python manage.py shell -c "
from prompts.models import PromptGenerationRun as R
print(list(R.objects.filter(status=\"INIT\").values_list(\"id\",\"domain_id\")))"'
```

A non-empty list means a run will fire seconds after the restart and spend real
OpenRouter credits. Delete it first, or ask Arun.

---

## Phase 1 — get the code into git

Zero production impact. **Pushing is not deploying** — the server only changes in
Phase 2.

```bash
git checkout production
git fetch --all

git log --oneline production..origin/main    # candidates to ship
git log --oneline origin/main..production    # MUST be empty
```

**If the second list is empty**, `production` fast-forwards cleanly:

```bash
git merge --ff-only origin/main
```

**If the second list is NOT empty**, the branches have drifted and carry the same
work under different hashes. **Stop and ask Arun.** Do not plain-merge `main`
into `production` — you will replay commits that are already live. The fix is to
cherry-pick the specific commits instead.

Then check nothing is uncommitted and push:

```bash
git status --porcelain | grep -v '^??'      # empty, except .claude/settings.local.json
git push origin production
```

> Never commit `.claude/settings.local.json`. It is per-machine and has
> historically contained an SSH passphrase in plaintext.

### Optional local boot check

Only if you have `backend/.env`:

```bash
cd backend && .venv/bin/python3.14 manage.py check     # want "no issues"
cd ../engine && ../backend/.venv/bin/python3.14 manage.py check
```

The engine reports one `rest_framework.W001` pagination warning. It is
pre-existing and not yours.

---

## Phase 1.5 — settings the release needs

Skip only if you have checked and the answer is none. **A missing setting is the
one failure here that is completely silent**: a missing migration raises, a
missing route 404s, a mis-built bundle shows up in the hash check — but a
setting that is not there just makes the server behave differently, with nothing
in the logs to say so.

Settings take effect at the restart in 2d, so they must be in place before it.

### There are two `.env` files, and they are not interchangeable

| File | Read by |
|---|---|
| `/root/python/v3.12/llm-monitor/backend/.env` | Django / gunicorn — the API |
| `/root/python/v3.12/llm-monitor/engine/.env` | the engine and **all three celery workers** |

Each project loads the `.env` beside its own `manage.py`. They routinely hold
**different values for the same key** — locally `AUDIT_PROMPT_COUNT` is 6 in one
and 8 in the other — so "it is already set" is never an answer until you say
*which file*. A worker setting written to `backend/.env` changes nothing, and
nothing warns you.

Read what is there now before you add anything:

```bash
ssh promptmaxx 'grep -E "^(AUDIT|MAILGUN|DATABLUE|DATAFORSEO)_" /root/python/v3.12/llm-monitor/backend/.env'
ssh promptmaxx 'grep -E "^(AUDIT|MAILGUN|DATABLUE|DATAFORSEO)_" /root/python/v3.12/llm-monitor/engine/.env'
```

Append what the release needs — to the right file, and never overwriting the
file wholesale:

```bash
ssh promptmaxx "grep -q '^SETTING_NAME=' /root/python/v3.12/llm-monitor/engine/.env \
  || echo 'SETTING_NAME=value' >> /root/python/v3.12/llm-monitor/engine/.env"
```

### Defaults are a decision, not a safety net

A new setting with a default **changes production the moment the code lands**,
without anyone typing anything. Before deploying, list every setting the release
adds and ask of each: *if nobody sets this, is the default what production
should do?* Where the answer is no, set it explicitly here. The per-release
`DEPLOY_COMMANDS.md` is where that list belongs.

---

## Phase 2 — backend and engine

New API endpoints are additive: the currently-deployed frontend never calls them,
so this phase changes no existing behaviour.

### 2a. Pre-flight

```bash
# WRITE THIS DOWN — it is your rollback point
ssh promptmaxx 'cd /root/python/v3.12/llm-monitor && git rev-parse HEAD'

# Must be empty — `git reset --hard` would discard anything listed here
ssh promptmaxx 'cd /root/python/v3.12/llm-monitor && git status --porcelain | grep -v "^??"'
```

### 2b. Pull

```bash
ssh promptmaxx 'cd /root/python/v3.12/llm-monitor && git fetch origin && git reset --hard origin/production'
```

### 2c. Migrations

```bash
ssh promptmaxx 'cd /root/python/v3.12/llm-monitor/backend && /root/python/v3.12/env/bin/python manage.py showmigrations | grep -B3 "\[ \]"'
```

Nothing listed means nothing to do. Otherwise apply them **by name** — never a
bare `manage.py migrate`:

```bash
ssh promptmaxx 'cd /root/python/v3.12/llm-monitor/backend && /root/python/v3.12/env/bin/python manage.py migrate <app> <number>'
```

Read the migration file first:

- `AddField`, `CreateModel`, `ADD COLUMN IF NOT EXISTS` — additive and safe.
- `RemoveField`, `AlterField`, `RunSQL` that drops anything — **stop and ask Arun.**
  These need a maintenance window **and a snapshot first** (below).

### Snapshot the database before anything that is not purely additive

`migrate <app> <previous>` reverses the *schema*. It does not bring back data a
dropped column took with it. The webroot has a backup in 3a; give the database
the same courtesy, and take it **before** the migration, not after:

```bash
ssh promptmaxx 'set -a; . /root/python/v3.12/llm-monitor/backend/.env; set +a;
  PGPASSWORD="$DB_PASSWORD" pg_dump -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" \
    -U "$DB_USER" -d "$DB_NAME" -Fc \
    -f "/root/db-$(date +%Y%m%d-%H%M%S).dump"'

ssh promptmaxx 'ls -lh /root/db-*.dump | tail -1'    # confirm it is not 0 bytes
```

To restore it:

```bash
ssh promptmaxx 'set -a; . /root/python/v3.12/llm-monitor/backend/.env; set +a;
  PGPASSWORD="$DB_PASSWORD" pg_restore -h "${DB_HOST:-localhost}" -p "${DB_PORT:-5432}" \
    -U "$DB_USER" -d "$DB_NAME" --clean --if-exists /root/db-<timestamp>.dump'
```

An additive release does not need this. Take it anyway if you are unsure which
kind you have — it costs a minute and the alternative has no undo.

### 2d. Verify it boots, THEN restart

Checking before restarting is what keeps a bad deploy from becoming an outage.

```bash
ssh promptmaxx 'cd /root/python/v3.12/llm-monitor/backend && /root/python/v3.12/env/bin/python manage.py check'

ssh promptmaxx 'systemctl restart gunicorn engine engine-celery engine-celery-beat engine-celery-seo'
ssh promptmaxx 'systemctl is-active gunicorn engine engine-celery engine-celery-beat engine-celery-seo nginx'
```

All six must report `active`.

### 2e. Smoke test

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://app.promptmaxx.co/                          # 200
curl -s -o /dev/null -w '%{http_code}\n' https://promtmaxxservice.rankmax.io/auth/profile/   # 401
ssh promptmaxx 'tail -25 /var/log/celery/worker.log'
```

**`401` is the correct answer** for an unauthenticated call — it proves the route
exists and auth is wired. `404` means the route did not deploy. `500` means it
deployed broken.

---

## Phase 3 — frontend

The only user-visible change, and the only irreversible-by-default one.

### 3a. Back up the webroot

There is no other copy:

```bash
ssh promptmaxx "cp -a /var/www/html /var/www/html.bak-\$(date +%Y%m%d-%H%M%S)"
```

### 3b. Build locally

From the `production` branch:

```bash
cd frontend && rm -rf dist && npm run build
```

Note the `index-XXXXXXX.js` filename it prints — you need it in 3e.

### 3c. Verify the bundle — do not skip this

```bash
grep -ro 'localhost:8000\|localhost:8001' dist/assets/*.js | wc -l   # MUST be 0
grep -rlo 'promtmaxxservice.rankmax.io' dist/assets/*.js | head -1   # must print a file
```

> **The trap this catches.** Vite gives `.env.local` the highest priority. If you
> have been running the app locally you will have pointed it at `localhost:8000`
> — and building in that state ships a production frontend that calls localhost
> for every user. The whole app fails and it looks like a backend outage.
> Always restore the production values before building.

### 3d. Upload

```bash
rsync -az --delete -e "ssh -i ~/.ssh/llm_monitor" dist/ root@64.227.190.42:/var/www/html/
ssh promptmaxx 'rm -f /var/www/html/.DS_Store'
```

### 3e. Confirm the new bundle is live

Filenames are content-hashed, so this proves the deploy landed rather than a
cache being served:

```bash
curl -s https://app.promptmaxx.co/ | grep -o 'index-[A-Za-z0-9_-]*\.js'
```

It must match the filename `npm run build` printed in 3b.

---

## Rollback

| Layer | Command |
|---|---|
| Frontend | `rsync -a --delete /var/www/html.bak-<ts>/ /var/www/html/` |
| Backend / engine | `git reset --hard <sha from 2a>` then restart the five services |
| Migrations | `manage.py migrate <app> <previous_number>` — schema only |
| Dropped data | `pg_restore` from the 2c snapshot; there is no other route |
| A setting | edit the right `.env` (see Phase 1.5) and restart the five services |

Additive migrations usually need **no** rollback — old code ignores new columns
and tables quite happily. Reverting the code alone is normally enough, and faster.

---

## Post-deploy checklist

- [ ] `systemctl is-active` — all six report `active`
- [ ] `https://app.promptmaxx.co/` returns 200
- [ ] The served bundle hash matches what you built
- [ ] New endpoints return 401, not 404 or 500
- [ ] `/var/log/celery/worker.log` shows no new tracebacks
- [ ] `showmigrations | grep -c "\[ \]"` is 0
- [ ] Every setting the release needs is in the **right** `.env` (Phase 1.5)
- [ ] Database snapshot taken, if the release was not purely additive
- [ ] Rollback point written down somewhere you can find it

---

## Four things people get wrong

1. **The server runs `production`, not `main`.** Deploying `main` is the most
   common mistake here.
2. **`frontend/.env.local` must hold production URLs at build time.** See 3c.
3. **You can stop after any phase.** Phase 1 is just git. Phase 3 is the only
   user-facing step. Never jump straight to Phase 3.
4. **Phase 2 is usually invisible to users, but check rather than assume.** It is
   invisible when the release only *adds* endpoints, because the deployed
   frontend never calls them. A release that removes or changes an endpoint, or
   changes what an existing setting does, is not invisible — and then Phase 2
   and Phase 3 have to ship together.

If anything looks different from what this file describes — unexpected pending
migrations, a dirty working tree on the server, drifted branches — **stop and
ask Arun.** None of these steps are urgent enough to guess at.
