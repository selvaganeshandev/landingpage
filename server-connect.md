# Server Connection

How to open an SSH session to the PromptMaxx / LLM Monitor production host.

> **Verification status: VERIFIED** — connected successfully from this Mac on
> 2026-07-30. The key was already in `ssh-agent`, so `BatchMode=yes` succeeded
> with no passphrase prompt, which confirms the agent route below works.
>
> ```
> CONNECTED
> root
> LLM-Monitor-Product
>  16:09:16 up 3 days,  9:17,  1 user,  load average: 0.10, 0.05, 0.06
> Ubuntu 24.04.3 LTS
> ```

## Target

| | |
|---|---|
| Host | `64.227.190.42` |
| Hostname | `LLM-Monitor-Product` |
| OS | Ubuntu 24.04.3 LTS |
| User | `root` |
| Key | `/Users/arun/My_Products/AI Project/key_ftp_access.pem` |
| Key type | RSA 3072, `SHA256:b6WVushzoWbOwe6hupe0XnVuLEP7zuql5/SFwlwv5/0` |
| Passphrase | Required. **Not stored in this repo** — see below. |

The public hostnames `promtmaxx.rankmax.io` (frontend) and
`promtmaxxservice.rankmax.io` (backend API) both resolve to Cloudflare
(`104.21.52.87`, `172.67.197.71`). Those are **not** SSH targets — the origin
host is the bare IP above.

Note the key lives one directory *above* the repo, in `AI Project/`, not in
`~/.ssh/`. If you have seen a short lowercase string quoted alongside this key
and assumed it names a key file, it does not — no such file exists. That string
is the key's *passphrase*, and it is deliberately not written down here.

## Connecting

### 1. Load the key into ssh-agent once per boot

Do this interactively so the passphrase is typed by a human and never lands in
a file, a shell history entry, or a command argument:

```bash
ssh-add "/Users/arun/My_Products/AI Project/key_ftp_access.pem"
```

Confirm it is loaded:

```bash
ssh-add -l | grep key_ftp_access
```

Use `ssh-add --apple-use-keychain <key>` if you want macOS Keychain to hold the
passphrase so it survives reboots.

### 2. Connect

With the key in the agent, no passphrase prompt appears:

```bash
ssh -i "/Users/arun/My_Products/AI Project/key_ftp_access.pem" root@64.227.190.42
```

Smoke test in one shot:

```bash
ssh -o ConnectTimeout=15 \
    -i "/Users/arun/My_Products/AI Project/key_ftp_access.pem" \
    root@64.227.190.42 'whoami; hostname; uptime'
```

### Optional: an ssh config alias

Append to `~/.ssh/config` so the target is one word:

```
Host promptmaxx
    HostName 64.227.190.42
    User root
    IdentityFile "/Users/arun/My_Products/AI Project/key_ftp_access.pem"
    IdentitiesOnly yes
```

Then simply: `ssh promptmaxx`

## What is on the server

Deploy root: **`/root/python/v3.12/llm-monitor`** — the same repo tree as local
(`backend/`, `engine/`, `frontend/`, `landing/`, `scripts/`, …), checked out on
branch `main`.

Note it lives under `/root`, not `/var/www` or `/opt`. `/root` is also littered
with ad-hoc diagnostic scripts (`diag_*.py`, `check_*.py`, `citation_backfill.log`,
`deploy-backups/`, …) — the deploy directory is the nested path above, not `/root`.

### Deployed revision

Check what is actually live before debugging anything:

```bash
ssh promptmaxx 'git -C /root/python/v3.12/llm-monitor log --oneline -1'
```

Observed 2026-07-30: server was on `6337f051`, i.e. **two commits behind
`origin/main` (`15240793`)** — missing `9c318026` (brand recognised by URL) and
`15240793` (comparison-window sizing + `days` validation). A dashboard bug
reproduced locally but not in production, or vice versa, may just be this gap.

### Running services (systemd)

| Unit | Role | WorkingDirectory |
|---|---|---|
| `gunicorn.service` | Django backend | `…/llm-monitor/backend` |
| `engine.service` | Django engine | `…/llm-monitor/engine` |
| `engine-celery.service` | Celery worker | `…/llm-monitor/engine` |
| `engine-celery-beat.service` | Celery **beat** (scheduler) | `…/llm-monitor/engine` |
| `engine-celery-seo.service` | Celery SEO worker | `…/llm-monitor/engine` |
| `nginx.service` | Reverse proxy / TLS | — |

Useful one-liners:

```bash
systemctl status gunicorn engine engine-celery engine-celery-beat --no-pager
journalctl -u engine-celery -n 100 --no-pager
systemctl restart gunicorn engine
```

Beat runs **on the server** and is what drives the scheduled pipelines. That is
independent of local development, where beat is normally left off.

## Do not automate the passphrase

Driving the prompt with `expect` puts the passphrase in plaintext inside a
command string, which is then captured by shell history and by tool permission
records. That is exactly how it ended up committed to this repository (see
below). Use `ssh-agent` instead — that is what it exists for.

## Security note

The passphrase was found in plaintext in `.claude/settings.local.json`, inside a
stored `expect` permission rule. That file is **git-tracked and not ignored**,
and the string appears in **7 commits** of history across both GitHub remotes
(`memepranav/llm-monitor`, `arun-andiselvam/llm-monitor`). The server IP appears
in 23 commits.

The private key itself was **never** committed — verified: no
`BEGIN OPENSSH PRIVATE KEY` or `BEGIN RSA PRIVATE KEY` blob exists in history,
and no path matching `key_ftp_access` was ever tracked. The only `.pem` files in
history are `certifi` CA bundles from a tracked virtualenv.

A passphrase alone cannot unlock anything without the key file, so this is not
an immediate compromise. It still warrants action, because the leaked string is
paired with `root@<ip>` in the same file:

- Rotate the passphrase: `ssh-keygen -p -f "…/key_ftp_access.pem"`
- Remove the `expect` rule from `.claude/settings.local.json`
- Add `.claude/settings.local.json` to `.gitignore` and `git rm --cached` it —
  a `*.local.json` file is meant to be per-machine and untracked
- Retire the passphrase anywhere else it is reused

Purging it from history needs a force-push rewrite coordinated with the other
remote's owner; rotating the passphrase is the cheaper and more complete fix.
