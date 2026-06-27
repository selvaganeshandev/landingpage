# BYOK (Bring Your Own Key) — Fixes & Enhancements

**Date:** 2026-06-24
**Area:** Organization-level API Key Management (OpenAI, Gemini, Perplexity, Anthropic, xAI, DeepSeek)
**Goal:** Make the BYOK feature actually work end-to-end — each organisation can add its own API keys from the UI instead of relying on `.env`.

---

## TL;DR of what was broken and fixed

The BYOK feature stored keys in the backend but **the engine never used them** (it always silently fell back to `.env`), the UI **always showed "Not Configured"**, and the "Connected" badge **didn't actually validate keys**. All four issues are fixed, and BYOK is now wired through every LLM code path.

---

## 1. Engine never used the stored keys (core defect)

**Symptom:** Keys added in the UI were ignored; the engine always used `.env`.

**Root causes & fixes:**

| Problem | Fix |
|--------|-----|
| Engine's `shared_models.Organisation` model didn't declare the API-key / enabled columns, so the ORM read `None`/`True` for every provider. | Added the 6 `*_api_key` + 6 `*_enabled` fields to `engine/shared_models/models.py`. |
| Migration state out of sync (columns already exist via the backend migration). | Added `engine/shared_models/migrations/0002_organisation_byok_api_keys.py` — a **state-only** migration (`SeparateDatabaseAndState`), no DDL. |
| Engine couldn't decrypt keys — it imported `decrypt_value` from the backend `authentication` app, which doesn't exist in the engine. | Added `engine/shared_models/crypto.py` (engine-local Fernet decrypt); `api_key_service.get_api_key` now uses it. Returns `""` on failure so it cleanly falls back to `.env`. |
| Backend and engine derived the Fernet key from **different** `SECRET_KEY`s, so decryption would have produced garbage. | Introduced a shared `API_KEY_ENCRYPTION_SECRET` setting in both projects. Backend defaults it to `SECRET_KEY` (so existing encrypted keys keep working); engine mirrors the default. |

**Files:**
- `engine/shared_models/models.py`
- `engine/shared_models/migrations/0002_organisation_byok_api_keys.py` *(new)*
- `engine/shared_models/crypto.py` *(new)*
- `engine/core/services/api_key_service.py`
- `backend/authentication/models.py` (`get_fernet` uses the shared secret)
- `backend/llm_monitor/settings.py` & `engine/llm_monitor_engine/settings.py` (`API_KEY_ENCRYPTION_SECRET`)

---

## 2. BYOK extended to all remaining LLM code paths

Previously only the analytics path was BYOK-aware. Now every engine path that calls an LLM resolves the **org's key (with `.env` fallback)** and honors the enable/disable toggle.

| Path | File | Change |
|------|------|--------|
| Prompt / keyword / group-title generation | `engine/core/chatgpt_client.py` | `ChatGPTClient(org_id=…)` resolves the org's OpenAI key lazily. |
| Domain processing (concurrent, multi-threaded) | `engine/core/domain_processor.py` | Per-thread org context (`threading.local`) + lock-guarded per-org client cache. |
| Topic processing | `engine/core/topic_processor.py` | Binds client to the domain's org. |
| Misinformation scan | `engine/core/misinformation_services/comparator.py`, `engine/core/misinformation_processor.py` | `ContentComparator(org_id=…)` resolves the org's key. |
| Quota / credit monitor | `engine/core/quota_monitor.py` | Now also probes each org's BYOK keys (additive; gated by `QUOTA_ALERT_INCLUDE_ORG_KEYS`, default `True`). |

---

## 3. UI always showed "Not Configured" (data-shape mismatch)

**Symptom:** every provider showed "Not Configured" even after saving a key.

**Cause:** the frontend expects a **nested** shape (`api_keys.openai.status`, `.configured`, …) but the backend returned **flat** keys (`openai_status`, `openai_configured`, …), so `api_keys['openai']` was `undefined`.

**Fix:** `backend/authentication/auth_views.py` → `_build_api_keys_payload` now returns the nested per-provider object the frontend reads.

---

## 4. "Connected" badge didn't validate the key

**Symptom:** a wrong/invalid key still showed **Connected**.

**Cause:** the status was presence-only (a key exists) — it never tested the key.

**Fix:** live validation on save.
- `engine/core/quota_monitor.py` → new `probe_key_state(provider, api_key)` (tiny 1-token test call).
- `backend/authentication/auth_views.py` → on save, the key is probed, mapped to a UI status (`CONNECTED` / `INVALID_KEY` / `OUT_OF_CREDITS` / `RATE_LIMITED` / `MODEL_UNAVAILABLE` / `ERROR`), and cached (24h). Cleared on delete. Falls back to `CONNECTED` (stored-but-unverified) if a probe genuinely can't run.
- `frontend/src/pages/OrganizationSettings.tsx` → added badge styles for the new states.

> Note: validation runs **on save**. Keys stored *before* this change show `Connected` (presence-based) until re-saved once.

---

## Behavioral clarification (not a bug)

- The **chat / AI Assistant** endpoint (`backend/chat/views.py`) is **OpenAI-only by design** — it calls `get_client('openai', org_id)`. So for the assistant, OpenAI must be enabled + keyed for that org. The other providers are used by the **analytics/tracking pipeline**, not the assistant.

---

## Full list of changed files

**Backend**
- `backend/authentication/models.py`
- `backend/authentication/auth_views.py`
- `backend/llm_monitor/settings.py`

**Engine**
- `engine/shared_models/models.py`
- `engine/shared_models/crypto.py` *(new)*
- `engine/shared_models/migrations/0002_organisation_byok_api_keys.py` *(new)*
- `engine/core/services/api_key_service.py`
- `engine/core/chatgpt_client.py`
- `engine/core/domain_processor.py`
- `engine/core/topic_processor.py`
- `engine/core/misinformation_services/comparator.py`
- `engine/core/misinformation_processor.py`
- `engine/core/quota_monitor.py`
- `engine/llm_monitor_engine/settings.py`

**Frontend**
- `frontend/src/pages/OrganizationSettings.tsx`

---

## Deployment steps (REQUIRED order)

1. **Apply the backend migration FIRST** (creates the DB columns):
   ```bash
   cd backend && python manage.py migrate authentication
   ```
2. **Apply the engine migration** (state-only, no DDL):
   ```bash
   cd engine && python manage.py migrate shared_models
   ```
3. **Restart BOTH** the backend server and the engine (Celery worker/beat / `start_engine.py`) — they cache the old model/clients in memory.
4. **Deploy the frontend** (rebuild) together with the backend.

### Environment
- `API_KEY_ENCRYPTION_SECRET` must be **identical** in backend and engine.
  - Default config (no custom `SECRET_KEY`): nothing to do — they already match.
  - If production sets a **custom `SECRET_KEY`**: set `API_KEY_ENCRYPTION_SECRET` to that same value in **both** backend and engine env.
- Optional: `QUOTA_ALERT_INCLUDE_ORG_KEYS=False` to disable per-org quota probing.

---

## ⚠️ Critical pre-push check

The engine `Organisation` model now **declares** the BYOK columns. If those columns are **missing from the database**, every `Organisation` query (backend *and* engine) raises a `ProgrammingError` and crashes.

**Therefore:** confirm the backend migration is applied on the production DB **before/with** this deploy:
```bash
cd backend && python manage.py showmigrations authentication
# 0005_organisation_anthropic_api_key_and_more must be [X]
```
If it is already `[X]` (the BYOK feature was deployed earlier), you're safe.

## Rollback
- Code changes are additive; revert the commit to roll back.
- Do **not** drop the DB columns on rollback (the backend model from the original feature still references them).
- The engine state-only migration can be reversed with `migrate shared_models 0001` if needed (no DDL impact).
