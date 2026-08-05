# Deployment

How changes reach production. Written from the deploy performed on 2026-08-05
(AI prompt generation), which is the first one recorded end to end — every
command below was actually run and verified.

For SSH access see [`server-connect.md`](server-connect.md).

> **Verification status: VERIFIED** — 2026-08-05. Deployed `9024740d` +
> `404a13ff` + `0e9f902d` to `app.promptmaxx.co` with no downtime.

---

## The thing that confuses everyone first

**The server does not run `main`.**

| | Branch | Remote |
|---|---|---|
| Your laptop, day to day | `main` | `origin` |
| **The live server** | **`production`** | `origin` (on the server) |

Worse, both remotes are the *same GitHub repo*. `origin` was
`memepranav/llm-monitor`, which has since **moved** to
`arun-andiselvam/llm-monitor` — GitHub still accepts pushes to the old URL and
prints "This repository moved." Locally that repo is also configured as a second
remote named `arun`.

So `git remote -v` shows two remotes that look different but are not:

```
arun    https://github.com/arun-andiselvam/llm-monitor.git
origin  https://github.com/memepranav/llm-monitor.git   → redirects to arun-andiselvam
```

**Consequence:** `main` and `production` drift apart and accumulate *the same
work under different commit hashes* (someone has been rebasing or cherry-picking
between them). On 2026-08-05 they were 9 and 8 commits apart, and all 8 pairs
were identical by message. Only one commit was genuinely missing from
`production`.

**So: never merge `main` into `production`.** You will replay eight commits that
are already there. Cherry-pick the specific commits instead — see Step 2.

To see what is genuinely missing, compare the *messages*, not the hashes:

```bash
git log --oneline production..main    # candidates to ship
git log --oneline main..production    # already live
```

Anything appearing in both lists with the same message is already deployed.

---

## Layout on the server

| | |
|---|---|
| Host | `64.227.190.42` (`app.promptmaxx.co`, `promtmaxx.rankmax.io`) |
| API | `promtmaxxservice.rankmax.io` |
| Deploy root | `/root/python/v3.12/llm-monitor` |
| Python | `/root/python/v3.12/env/bin/python` |
| Frontend webroot | `/var/www/html` — **not** the repo's `frontend/dist` |

Services: `gunicorn` (backend), `engine`, `engine-celery`, `engine-celery-beat`,
`engine-celery-seo`, `nginx`.

### The frontend is NOT built on the server

Files in `/var/www/html` are owned by uid **501** — a macOS user id, not a Linux
one. They are built on your Mac and uploaded. The repo's `frontend/dist` on the
server is stale and unused; do not be fooled by it.

---

## The three phases

Each phase is independently reversible. **You can stop after any of them.** Run
them in order — never jump to Phase 3.

Phase 1 is completely safe: **pushing is not deploying.** The server only changes
when you explicitly reset it in Phase 2.

---

### Phase 1 — get the code into git

Zero production impact.

**1a. Commit your work on `main`.** Anything uncommitted does not deploy — this
is the classic way to ship a half-feature that will not boot.

```bash
git status --porcelain | grep -v '^??'     # must be empty (except settings.local.json)
```

> Never commit `.claude/settings.local.json`. It is per-machine and has
> historically contained the SSH key passphrase in plaintext.

**1b. Cherry-pick onto `production`.**

```bash
git checkout production
git cherry-pick <feature-sha> <fix-sha> ...
```

Conflicts are normal where both branches appended to the same file. On
2026-08-05 the conflict was in `engine/core/processing_tasks.py`: both branches
had added new tasks directly beneath the *same* `@shared_task(...)` decorator
line, so git could not tell which `def` the decorator belonged to. **The
resolution is almost always "keep both"** — give each function its own
decorator. Then:

```bash
grep -nE '^(<<<<<<<|>>>>>>>|=======$)' <file>   # must be empty
```

Do not grep for bare `=======`: this codebase uses `# ==== SECTION ====` comment
banners and you will get false positives.

**1c. Verify both projects still boot before pushing.**

```bash
cd backend && .venv/bin/python3.14 manage.py check   # want: "no issues"
cd ../engine && ../backend/.venv/bin/python3.14 manage.py check
```

The engine reports 1 pre-existing `rest_framework.W001` pagination warning. That
is expected and not yours.

**1d. Push both branches.**

```bash
git push arun production
git push origin main
```

---

### Phase 2 — backend and engine

New API endpoints are *additive*: the currently-deployed frontend never calls
them, so this phase changes no existing behaviour.

**2a. Pre-flight.** `git reset --hard` discards tracked modifications, so check
there are none, and confirm `.env` files are untracked (they hold production
secrets and live stop-gap flags — losing them is an outage):

```bash
ssh … 'cd /root/python/v3.12/llm-monitor && git status --porcelain | grep -v "^??"'   # must be empty
ssh … 'cd /root/python/v3.12/llm-monitor && git ls-files --error-unmatch backend/.env engine/.env'
#   ^ SHOULD FAIL with "did not match any file(s)". That failure is the good outcome.
ssh … 'git -C /root/python/v3.12/llm-monitor rev-parse HEAD'   # write this down — rollback point
```

**2b. Pull.** This is the established pattern, visible in the server's reflog as
`branch: Reset to origin/production`:

```bash
ssh … 'cd /root/python/v3.12/llm-monitor && git fetch origin && git reset --hard origin/production'
```

**2c. Migrations.**

```bash
ssh … 'cd /root/python/v3.12/llm-monitor/backend && /root/python/v3.12/env/bin/python manage.py showmigrations | grep -c "\[ \]"'
```

`0` means nothing pending. If not zero, apply **named** migrations, never a bare
`manage.py migrate`:

```bash
… manage.py migrate <app> <migration_number>
```

Check the operations first — `AddField` and `CreateModel` are additive and safe
to apply ahead of the code. `RemoveField`, `AlterField` and `RunSQL` are not, and
need a maintenance window.

**2d. Verify it boots, THEN restart.** Checking before restarting is what keeps a
bad deploy from becoming an outage:

```bash
ssh … 'cd /root/python/v3.12/llm-monitor/backend && /root/python/v3.12/env/bin/python manage.py check'
ssh … 'systemctl restart gunicorn engine engine-celery engine-celery-beat engine-celery-seo'
ssh … 'systemctl is-active gunicorn engine engine-celery engine-celery-beat engine-celery-seo nginx'
```

**2e. Smoke-test.** `401` is the *correct* result for an unauthenticated call —
it proves the route exists and auth is wired. `404` means the route did not
deploy; `500` means it deployed broken.

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://app.promptmaxx.co/                      # 200
curl -s -o /dev/null -w '%{http_code}\n' https://promtmaxxservice.rankmax.io/auth/profile/  # 401
ssh … 'tail -25 /var/log/celery/worker.log'
```

---

### Phase 3 — frontend

The only user-visible change, and the only irreversible-by-default one.

> #### Trap: `frontend/.env.local` points at localhost during local dev
>
> Vite gives `.env.local` the highest priority. Running the app locally means
> repointing it at `localhost:8000`/`8001` — **and if you build in that state you
> ship a production frontend that calls localhost.** The whole app fails for
> every user, and it looks like a backend outage.
>
> Always restore the production values before building, and always verify the
> bundle afterwards (3c).

```
VITE_API_BASE_URL=https://promtmaxxservice.rankmax.io
VITE_ENGINE_URL=http://64.227.190.42:8001
```

**3a. Back up the webroot.** There is no other copy:

```bash
ssh … "cp -a /var/www/html /var/www/html.bak-$(date +%Y%m%d-%H%M%S)"
```

**3b. Build locally** from the `production` branch:

```bash
cd frontend && rm -rf dist && npm run build
```

**3c. Verify the bundle before uploading.** Non-negotiable:

```bash
grep -ro 'localhost:8000\|localhost:8001' dist/assets/*.js | wc -l   # MUST be 0
grep -ro 'promtmaxxservice.rankmax.io' dist/assets/*.js | head -1     # must be present
```

**3d. Upload.**

```bash
rsync -az --delete -e "ssh -i '/Users/arun/My_Products/AI Project/key_ftp_access.pem'" \
  dist/ root@64.227.190.42:/var/www/html/
ssh … 'rm -f /var/www/html/.DS_Store'      # macOS ships this along
```

**3e. Confirm the new bundle is actually live.** Filenames are content-hashed, so
this proves the deploy landed rather than a cache being served:

```bash
curl -s https://app.promptmaxx.co/ | grep -o 'index-[A-Za-z0-9_-]*\.js'
```

Compare against the filename `npm run build` printed. They must match.

---

## Rollback

| Layer | Command |
|---|---|
| Frontend | `rsync -a --delete /var/www/html.bak-<ts>/ /var/www/html/` |
| Backend/engine | `git reset --hard <old-sha>` then restart the five services |
| Migrations | `manage.py migrate <app> <previous_number>` |

Additive migrations usually need **no** rollback: old code ignores new columns
and tables quite happily. Reverting the code alone is normally enough, and is
faster.

---

## Before you deploy, check for queued work

Anything sitting in a queued state in the database **starts executing the moment
the code that understands it goes live**, including rows you created while
testing locally against the production database (see
`local-dev-uses-production-database` in the assistant's memory — local dev
connects to the production DB through an SSH tunnel, not a local one).

On 2026-08-05 an `INIT` prompt-generation run left over from local testing would
have fired within 10 seconds of the engine restart, spending the customer's
OpenRouter credits on a real 6-stage generation. It was deleted first.

```bash
cd backend && .venv/bin/python3.14 manage.py shell -c "
from prompts.models import PromptGenerationRun as R
print(list(R.objects.filter(status='INIT').values_list('id','domain_id')))"
```

---

## Post-deploy checklist

- [ ] `systemctl is-active` — all six report `active`
- [ ] `https://app.promptmaxx.co/` returns 200
- [ ] The served bundle hash matches what you built
- [ ] New endpoints return 401, not 404 or 500
- [ ] `/var/log/celery/worker.log` shows no new tracebacks
- [ ] `showmigrations | grep -c "\[ \]"` is 0
- [ ] Rollback point written down somewhere you can find it
