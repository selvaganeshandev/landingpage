"""
LLM quota / credit monitor.

LLM providers do NOT expose a remaining-balance ("% of quota") value through the
normal API key, so this probes each ENABLED (key-configured) provider with a
tiny request and classifies the result:

    OK | OUT_OF_CREDITS | RATE_LIMIT | INVALID_KEY | MODEL_UNAVAILABLE | ERROR

When a paid key is depleted / erroring — or recovers — it emails the configured
recipients via the existing Mailgun service. A small JSON state file dedupes
alerts so you only get mailed on a state change (or a periodic reminder while a
key stays depleted), not on every scheduled run.

Config (engine/.env, read in settings.py):
    QUOTA_ALERT_ENABLED=True
    QUOTA_ALERT_RECIPIENTS=boss@example.com,ops@example.com   # comma-separated
    QUOTA_ALERT_REPEAT_HOURS=12        # re-remind if still depleted after N hours
    GEMINI_MODEL=gemini-flash-latest   # default stable version alias

This module is additive and isolated — it makes only tiny probe calls and never
raises into the Celery scheduler.
"""
import json
import logging
import os
import re
from datetime import timedelta

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# The ONLY condition that triggers an email: the LLM is not working because its
# credits/quota are not enabled / are exhausted. Transient failures (rate limits,
# network errors, model config) are NOT emailed — they're shown in the report
# only — so the boss is alerted strictly when a provider needs a top-up.
ALERT_STATES = {"OUT_OF_CREDITS"}
# Other non-OK states are surfaced in the report table but never trigger a mail.
BAD_STATES = {"OUT_OF_CREDITS", "INVALID_KEY", "MODEL_UNAVAILABLE", "ERROR"}
WARN_STATES = {"RATE_LIMIT"}


def _cfg(name, default):
    return getattr(settings, name, default)


def _result(label, key, key_set, state, detail=""):
    return {"label": label, "key": key, "key_set": key_set, "state": state, "detail": (detail or "")[:300]}


# ---------------------------------------------------------------------------
# Per-provider probes (tiny, cheap calls)
# ---------------------------------------------------------------------------
def _probe_openai(api_key, model):
    """Probe ChatGPT through OpenRouter — the transport every OpenAI call now uses.

    The label stays "OpenAI / ChatGPT" so the quota dashboard and alert history
    remain continuous, but the credential being tested is the OpenRouter key.
    """
    if not api_key:
        return _result("OpenAI / ChatGPT", "openai", False, "NOT_CONFIGURED")
    try:
        from openai import OpenAI
        OpenAI(
            api_key=api_key,
            base_url=_cfg("OPENROUTER_BASE_URL", None) or "https://openrouter.ai/api/v1",
            timeout=30,
        ).chat.completions.create(
            model=model, messages=[{"role": "user", "content": "ping"}], max_tokens=1
        )
        return _result("OpenAI / ChatGPT", "openai", True, "OK")
    except Exception as e:
        m = str(e)
        ml = m.lower()
        if "insufficient_quota" in ml or "exceeded your current quota" in ml:
            st = "OUT_OF_CREDITS"
        elif "rate_limit" in ml or "rate limit" in ml:
            st = "RATE_LIMIT"
        elif "invalid_api_key" in ml or "incorrect api key" in ml or "401" in m:
            st = "INVALID_KEY"
        else:
            st = "ERROR"
        return _result("OpenAI / ChatGPT", "openai", True, st, m)


def _probe_anthropic(api_key, model):
    """Probe Claude through OpenRouter — the transport every Claude call now uses.

    The label stays "Anthropic / Claude" so the quota dashboard and alert history
    remain continuous, but the credential being tested is the OpenRouter key.
    """
    if not api_key:
        return _result("Anthropic / Claude", "anthropic", False, "NOT_CONFIGURED")
    try:
        from .services.openrouter_client import OpenRouterAnthropicClient
        OpenRouterAnthropicClient(
            api_key=api_key,
            base_url=_cfg("OPENROUTER_BASE_URL", None),
            timeout=30,
        ).messages.create(
            model=model, max_tokens=1, messages=[{"role": "user", "content": "ping"}]
        )
        return _result("Anthropic / Claude", "anthropic", True, "OK")
    except Exception as e:
        m = str(e)
        ml = m.lower()
        if "credit" in ml or "billing" in ml or "insufficient" in ml:
            st = "OUT_OF_CREDITS"
        elif "rate" in ml and "limit" in ml:
            st = "RATE_LIMIT"
        elif "authentication" in ml or "invalid x-api-key" in ml or "no auth credentials" in ml or "401" in m:
            st = "INVALID_KEY"
        else:
            st = "ERROR"
        return _result("Anthropic / Claude", "anthropic", True, st, m)


def _probe_gemini(api_key, model):
    if not api_key:
        return _result("Google Gemini", "gemini", False, "NOT_CONFIGURED")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    try:
        r = requests.post(
            url, json={"contents": [{"parts": [{"text": "ping"}]}]}, timeout=30
        )
        if r.status_code == 200:
            return _result("Google Gemini", "gemini", True, "OK")
        try:
            err = r.json().get("error", {})
        except Exception:
            err = {}
        gstatus = err.get("status", "")
        gmsg = err.get("message", r.text or "")
        if r.status_code == 429 or gstatus == "RESOURCE_EXHAUSTED":
            # 429 / RESOURCE_EXHAUSTED is usually a transient per-minute rate
            # limit, not a depleted balance. Only call it depletion when the
            # message actually points at billing/credits, otherwise a busy
            # minute would flap the provider in and out of the alert set.
            gml = (gmsg or "").lower()
            st = ("OUT_OF_CREDITS"
                  if any(t in gml for t in ("billing", "credit", "free tier", "plan"))
                  else "RATE_LIMIT")
        elif r.status_code == 404:
            st = "MODEL_UNAVAILABLE"
        elif r.status_code in (400, 401, 403):
            st = "INVALID_KEY"
        else:
            st = "ERROR"
        return _result("Google Gemini", "gemini", True, st, f"HTTP {r.status_code} {gstatus} {gmsg}")
    except Exception as e:
        return _result("Google Gemini", "gemini", True, "ERROR", str(e))


# Perplexity rejects max_tokens below 16 outright. The probe must satisfy the
# strictest provider it talks to, otherwise the request is refused on its
# parameters and the key is never actually judged — which reported every valid
# Perplexity key as INVALID_KEY and made it unsaveable through BYOK settings.
_PROBE_MAX_TOKENS = 16

# Wording that identifies WHY a call was refused. Matched against the provider's
# message, so keep these specific: a bare "invalid" also appears in
# `invalid_request` / `invalid-argument`, which are PARAMETER complaints and say
# nothing about the key.
_AUTH_HINTS = ("api key", "authentication", "unauthorized", "forbidden", "invalid_api_key")
_CREDIT_HINTS = ("insufficient", "credit", "billing", "quota", "balance")
_MODEL_HINTS = ("model not found", "model_not_found", "unknown model", "does not exist")


def _status_code_of(exc):
    """HTTP status carried by an SDK exception, or parsed from its message."""
    status = getattr(exc, "status_code", None)
    if isinstance(status, int):
        return status
    match = re.search(r"Error code:\s*(\d{3})", str(exc))
    return int(match.group(1)) if match else None


def _classify_openai_compatible_error(exc):
    """Map a provider error to a quota state.

    The order is deliberate. A message about billing means the key authenticated
    fine, so credits are judged before anything else. Only a 401/403 or
    auth-specific wording may blame the KEY — a 400 is usually a bad *parameter*
    (max_tokens, an unknown model) and must never be reported as an invalid key,
    because that sends the operator off rotating a key that was never broken.
    """
    message = str(exc)
    lowered = message.lower()
    status = _status_code_of(exc)

    if any(hint in lowered for hint in _CREDIT_HINTS):
        return "OUT_OF_CREDITS"
    if status == 429 or ("rate" in lowered and "limit" in lowered):
        return "RATE_LIMIT"
    if status in (401, 403) or any(hint in lowered for hint in _AUTH_HINTS):
        return "INVALID_KEY"
    if status == 404 or any(hint in lowered for hint in _MODEL_HINTS):
        return "MODEL_UNAVAILABLE"
    return "ERROR"


def _probe_openai_compatible(label, key, api_key, base_url, model):
    """Perplexity / xAI / DeepSeek expose OpenAI-compatible chat endpoints."""
    if not api_key:
        return _result(label, key, False, "NOT_CONFIGURED")
    try:
        from openai import OpenAI
        OpenAI(api_key=api_key, base_url=base_url, timeout=30).chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=_PROBE_MAX_TOKENS,
        )
        return _result(label, key, True, "OK")
    except Exception as e:
        return _result(label, key, True, _classify_openai_compatible_error(e), str(e))


# Provider slug → (display label, probe callable). Used for both the system
# (.env) probes and the per-organisation BYOK probes.
_PROVIDER_LABELS = {
    "openai": "OpenAI / ChatGPT",
    "anthropic": "Anthropic / Claude",
    "gemini": "Google Gemini",
    "perplexity": "Perplexity",
    "xai": "xAI / Grok",
    "deepseek": "DeepSeek",
}


def _probe_provider(provider, api_key):
    """Dispatch to the right provider probe with the configured probe model."""
    if provider == "openrouter":
        # The shared credential behind ChatGPT, Claude and Perplexity. Probed
        # against OpenRouter itself rather than any one vendor, so a valid key
        # is not marked broken because one model happens to be unavailable.
        return _probe_openai_compatible(
            "OpenRouter", "openrouter", api_key,
            _cfg("OPENROUTER_BASE_URL", None) or "https://openrouter.ai/api/v1",
            _cfg("QUOTA_PROBE_OPENROUTER_MODEL", "openai/gpt-4o-mini"))
    if provider == "openai":
        return _probe_openai(api_key, _cfg("QUOTA_PROBE_OPENAI_MODEL", "openai/gpt-4o-mini"))
    if provider == "anthropic":
        return _probe_anthropic(api_key, _cfg("QUOTA_PROBE_ANTHROPIC_MODEL", "anthropic/claude-sonnet-5"))
    if provider == "gemini":
        return _probe_gemini(api_key, _cfg("GEMINI_MODEL", "gemini-flash-latest"))
    if provider == "perplexity":
        # Perplexity runs on OpenRouter now, so the credential under test is the
        # OpenRouter key and the endpoint is OpenRouter's. The label and slug are
        # unchanged so the quota dashboard and alert history stay continuous.
        return _probe_openai_compatible("Perplexity", "perplexity", api_key,
                                        _cfg("OPENROUTER_BASE_URL", None) or "https://openrouter.ai/api/v1",
                                        _cfg("QUOTA_PROBE_PERPLEXITY_MODEL", "perplexity/sonar"))
    if provider == "xai":
        return _probe_openai_compatible("xAI / Grok", "xai", api_key,
                                        "https://api.x.ai/v1", _cfg("QUOTA_PROBE_XAI_MODEL", "grok-2-latest"))
    if provider == "deepseek":
        return _probe_openai_compatible("DeepSeek", "deepseek", api_key,
                                        "https://api.deepseek.com/v1", _cfg("QUOTA_PROBE_DEEPSEEK_MODEL", "deepseek-chat"))
    return _result(provider, provider, True, "ERROR", f"unknown provider {provider}")


def probe_key_state(provider, api_key):
    """Public helper: live-probe a single (provider, api_key) and return just the
    state string (OK | INVALID_KEY | OUT_OF_CREDITS | RATE_LIMIT |
    MODEL_UNAVAILABLE | ERROR | NOT_CONFIGURED) plus a short detail.

    Used by the backend to validate a key the moment a user saves it.
    Returns a (state, detail) tuple; never raises.
    """
    try:
        r = _probe_provider(provider, api_key)
        return r.get("state", "ERROR"), (r.get("detail", "") or "")
    except Exception as e:
        return "ERROR", str(e)


def check_org_quotas():
    """Probe each organisation's configured BYOK keys.

    Each result gets an org-scoped label ("OpenAI / ChatGPT — Acme") and a unique
    key ("openai@org42") so it dedupes and renders independently of the system
    (.env) probes. Disable via QUOTA_ALERT_INCLUDE_ORG_KEYS=False. Never raises.
    """
    if not _cfg("QUOTA_ALERT_INCLUDE_ORG_KEYS", True):
        return []
    try:
        from shared_models.models import Organisation
        from shared_models.crypto import decrypt_value
    except Exception as e:
        logger.warning(f"[QuotaMonitor] org probing unavailable: {e}")
        return []

    results = []
    try:
        orgs = list(Organisation.objects.all())
    except Exception as e:
        logger.warning(f"[QuotaMonitor] could not load organisations: {e}")
        return []

    for org in orgs:
        for provider, label in _PROVIDER_LABELS.items():
            if not getattr(org, f"{provider}_enabled", True):
                continue
            if provider in ("anthropic", "perplexity", "openai"):
                # ChatGPT, Claude and Perplexity all run on OpenRouter now, so a
                # stored per-org OpenAI/Anthropic/Perplexity key no longer
                # authenticates anything. Probing it would raise a false
                # INVALID_KEY alert against a credential the pipeline never uses —
                # and for a stored OpenAI key the probe fails in a particularly
                # misleading way: OpenRouter cannot parse an sk-proj- credential
                # and answers 401 "Missing Authentication header", which reads as
                # a missing key rather than an unused one. The system OpenRouter
                # key is probed in check_all_quotas().
                continue
            encrypted = getattr(org, f"{provider}_api_key", None)
            if not encrypted:
                continue  # provider falls back to the system .env probe
            api_key = decrypt_value(encrypted)
            if not api_key:
                continue
            try:
                r = _probe_provider(provider, api_key)
            except Exception as e:
                r = _result(label, provider, True, "ERROR", str(e))
            r["label"] = f"{label} — {org.name}"
            r["key"] = f"{provider}@org{org.id}"
            results.append(r)

        # Dedicated Content Generation key (Claude) — Strategy pipeline only.
        # Probed with the same anthropic probe so a REAL provider outage
        # (OUT_OF_CREDITS / INVALID_KEY) is surfaced and, for OUT_OF_CREDITS,
        # triggers the existing Mailgun alert. The internal soft monthly token
        # budget is NOT consulted here — exceeding it is a dashboard-only warning
        # and never overrides the live provider status.
        cg_encrypted = getattr(org, "content_generation_api_key", None)
        if cg_encrypted:
            cg_api_key = decrypt_value(cg_encrypted)
            if cg_api_key:
                try:
                    r = _probe_provider("anthropic", cg_api_key)
                except Exception as e:
                    r = _result("Anthropic / Claude", "anthropic", True, "ERROR", str(e))
                r["label"] = f"Anthropic (Claude) Content Generation — {org.name}"
                r["key"] = f"content_generation_claude@org{org.id}"
                results.append(r)
    return results


def check_all_quotas():
    """Probe every provider whose key is configured. Returns a list of result dicts.

    Includes the system (.env) keys plus every organisation's BYOK keys.
    """
    results = [
        _probe_openai(_cfg("OPENROUTER_API_KEY", ""), _cfg("QUOTA_PROBE_OPENAI_MODEL", "openai/gpt-4o-mini")),
        _probe_anthropic(_cfg("OPENROUTER_API_KEY", ""), _cfg("QUOTA_PROBE_ANTHROPIC_MODEL", "anthropic/claude-sonnet-5")),
        _probe_gemini(_cfg("GEMINI_API_KEY", ""), _cfg("GEMINI_MODEL", "gemini-flash-latest")),
        _probe_provider("perplexity", _cfg("OPENROUTER_API_KEY", "")),
        _probe_openai_compatible("xAI / Grok", "xai", _cfg("XAI_API_KEY", ""),
                                 "https://api.x.ai/v1", _cfg("QUOTA_PROBE_XAI_MODEL", "grok-2-latest")),
        _probe_openai_compatible("DeepSeek", "deepseek", _cfg("DEEPSEEK_API_KEY", ""),
                                 "https://api.deepseek.com/v1", _cfg("QUOTA_PROBE_DEEPSEEK_MODEL", "deepseek-chat")),
    ]
    try:
        results.extend(check_org_quotas())
    except Exception as e:
        logger.warning(f"[QuotaMonitor] org quota probing failed: {e}")
    return results


# ---------------------------------------------------------------------------
# State (dedupe alerts) + email
# ---------------------------------------------------------------------------
def _state_path():
    base = str(_cfg("BASE_DIR", os.getcwd()))
    return _cfg("QUOTA_ALERT_STATE_FILE", os.path.join(base, "quota_alert_state.json"))


def _load_state():
    try:
        with open(_state_path(), "r") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _save_state(state):
    """Write the dedupe state atomically.

    A partially-written file would be unreadable by the next run, which resets
    the dedupe and re-alerts, so the write goes to a temp file and is swapped in
    with os.replace().
    """
    path = _state_path()
    tmp = f"{path}.tmp"
    try:
        with open(tmp, "w") as fh:
            json.dump(state, fh)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except Exception as e:
        logger.warning(f"[QuotaMonitor] could not save state: {e}")


def _parse_ts(value):
    """Parse an ISO timestamp from the state file; None if missing/corrupt."""
    if not value:
        return None
    try:
        return timezone.datetime.fromisoformat(value)
    except Exception:
        return None


def _elapsed_since(value):
    """Time since an ISO timestamp, or None if it can't be determined."""
    ts = _parse_ts(value)
    if ts is None:
        return None
    try:
        return timezone.now() - ts
    except Exception:
        return None


def _icon(state):
    return {
        "OK": "🟢", "OUT_OF_CREDITS": "🔴", "INVALID_KEY": "🔴",
        "MODEL_UNAVAILABLE": "🔴", "ERROR": "🔴", "RATE_LIMIT": "🟡",
        "NOT_CONFIGURED": "⚪",
    }.get(state, "•")


# Human-friendly status text (no raw provider error dumps in the email).
_STATUS_LABEL = {
    "OK": "Operational",
    "OUT_OF_CREDITS": "Credits exhausted",
    "INVALID_KEY": "Invalid / unauthorized key",
    "MODEL_UNAVAILABLE": "Configured model unavailable",
    "RATE_LIMIT": "Temporarily rate-limited",
    "ERROR": "Unexpected error",
    "NOT_CONFIGURED": "Not configured",
}
_STATUS_NOTE = {
    "OK": "Operational",
    "OUT_OF_CREDITS": "Credits/quota exhausted — top-up required",
    "INVALID_KEY": "API key invalid or unauthorized",
    "MODEL_UNAVAILABLE": "Configured model is unavailable",
    "RATE_LIMIT": "Temporarily rate-limited (usually transient)",
    "ERROR": "Unexpected error while contacting the provider",
    "NOT_CONFIGURED": "No key configured — skipped",
}
_STATUS_COLOR = {
    "OK": "#16a34a", "RATE_LIMIT": "#d97706", "NOT_CONFIGURED": "#9ca3af",
}  # everything else (bad states) → red


def _color(state):
    return _STATUS_COLOR.get(state, "#dc2626")


def _build_email(results, recovered=None):
    """Return (subject, text_body, html_body) — a clean, professional report.

    The alert is keyed on CREDIT DEPLETION only. `recovered` is a list of provider
    keys that were depleted last check and are now working again.
    """
    recovered = recovered or []
    by_key = {r["key"]: r for r in results}
    depleted = [r for r in results if r["state"] in ALERT_STATES]  # OUT_OF_CREDITS
    recovered_rows = [by_key[k] for k in recovered if k in by_key]
    generated = timezone.now().strftime("%d %b %Y, %H:%M UTC")

    if depleted:
        headline = "Action Required — Credits Depleted"
        banner_color = "#dc2626"
        names = ", ".join(r["label"] for r in depleted)
        summary = (f"{names} cannot be used because the credits are depleted — this is "
                   "blocking brand-mention / AI-visibility tracking for that provider.")
        subject = "Action Required: LLM credits depleted — " + names
    else:
        # Only reached on a recovery-only notification.
        headline = "Credits Restored"
        banner_color = "#16a34a"
        names = ", ".join(r["label"] for r in recovered_rows) or "Provider"
        summary = f"{names} credits are restored and the provider is working again."
        subject = "Resolved: LLM credits restored — " + names

    # ---- plain-text fallback ----
    tlines = [f"LLM CREDIT STATUS — {headline}", generated, "", summary, ""]
    for r in results:
        tlines.append(f"  {_icon(r['state'])} {r['label']}: {_STATUS_LABEL.get(r['state'], r['state'])}")
    if depleted:
        tlines += ["", "ACTION REQUIRED — top up / enable credits for:"]
        tlines += [f"  - {r['label']}" for r in depleted]
        tlines += ["", "Tracking repopulates automatically on the next run once restored."]
    if recovered_rows:
        tlines += ["", "RESTORED: " + ", ".join(r["label"] for r in recovered_rows)]
    tlines += ["", "— Automated alert from the PromptMaxx engine"]
    text_body = "\n".join(tlines)

    # ---- HTML ----
    # Soft status chip (coloured dot + tinted label) per state.
    _CHIP = {
        "OK":             ("#ecfdf5", "#047857", "#10b981"),
        "RATE_LIMIT":     ("#fffbeb", "#b45309", "#f59e0b"),
        "NOT_CONFIGURED": ("#f1f5f9", "#64748b", "#94a3b8"),
    }

    def _chip(state):
        bg, fg, dot = _CHIP.get(state, ("#fef2f2", "#b91c1c", "#ef4444"))  # bad states → red
        return (
            f'<span style="display:inline-block;padding:5px 11px 5px 9px;border-radius:999px;'
            f'background:{bg};color:{fg};font-size:12px;font-weight:600;white-space:nowrap;">'
            f'<span style="display:inline-block;width:7px;height:7px;border-radius:50%;'
            f'background:{dot};margin-right:7px;vertical-align:middle;"></span>'
            f'{_STATUS_LABEL.get(state, state)}</span>'
        )

    def _pill(count, text, bg, fg):
        return (f'<span style="display:inline-block;padding:5px 12px;border-radius:999px;'
                f'background:{bg};color:{fg};font-size:12px;font-weight:600;margin:0 8px 8px 0;">'
                f'{count} {text}</span>')

    # Status summary strip (surface the headline counts before the detail table).
    n_ok = sum(1 for r in results if r["state"] == "OK")
    n_attention = sum(1 for r in results if r["state"] in BAD_STATES)
    n_other = len(results) - n_ok - n_attention
    pills = _pill(n_ok, "operational", "#ecfdf5", "#047857")
    if n_attention:
        pills += _pill(n_attention, "need attention", "#fef2f2", "#b91c1c")
    if n_other:
        pills += _pill(n_other, "other", "#f1f5f9", "#64748b")

    rows = ""
    for i, r in enumerate(results):
        stripe = "#ffffff" if i % 2 == 0 else "#fafbfc"
        note = _STATUS_NOTE.get(r["state"], "")
        rows += (
            f'<tr style="background:{stripe};">'
            '<td style="padding:13px 24px;border-bottom:1px solid #eef1f5;">'
            f'<div style="font-weight:600;color:#0f172a;font-size:14px;">{r["label"]}</div>'
            f'<div style="color:#94a3b8;font-size:12px;margin-top:3px;">{note}</div>'
            '</td>'
            '<td style="padding:13px 24px;border-bottom:1px solid #eef1f5;text-align:right;'
            f'white-space:nowrap;vertical-align:top;">{_chip(r["state"])}</td>'
            '</tr>'
        )

    action_block = ""
    if depleted:
        items = "".join(f'<li style="margin:5px 0;color:#7f1d1d;font-size:14px;">{r["label"]}</li>' for r in depleted)
        action_block = (
            '<div style="padding:16px 18px;background:#fef2f2;border:1px solid #fecaca;border-radius:10px;">'
            '<div style="font-weight:700;color:#991b1b;font-size:14px;margin-bottom:6px;">Action required — credits depleted</div>'
            '<div style="color:#7f1d1d;font-size:13px;margin-bottom:8px;">Top up or re-enable credits for:</div>'
            f'<ul style="margin:0;padding-left:20px;">{items}</ul>'
            '<div style="color:#b91c1c;font-size:12px;margin-top:10px;">Tracking resumes automatically on the next scheduled run once credits are restored.</div>'
            '</div>'
        )
    elif recovered_rows:
        items = "".join(f'<li style="margin:5px 0;color:#166534;font-size:14px;">{r["label"]}</li>' for r in recovered_rows)
        action_block = (
            '<div style="padding:16px 18px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;">'
            '<div style="font-weight:700;color:#166534;font-size:14px;margin-bottom:6px;">Credits restored</div>'
            f'<ul style="margin:0;padding-left:20px;">{items}</ul>'
            '</div>'
        )

    html_body = f"""\
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0;padding:0;background:#eef1f5;">
<div style="max-width:600px;margin:0 auto;padding:28px 14px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <div style="padding:0 4px 14px;">
    <span style="font-size:15px;font-weight:700;color:#0f172a;letter-spacing:-0.01em;">Prompt<span style="color:#4f46e5;">Maxx</span></span>
    <span style="font-size:12px;color:#94a3b8;margin-left:8px;">LLM Credit Monitor</span>
  </div>
  <div style="background:#ffffff;border-radius:14px;overflow:hidden;border:1px solid #e2e8f0;box-shadow:0 1px 2px rgba(15,23,42,0.06);">
    <div style="background:{banner_color};padding:22px 24px;">
      <div style="color:#ffffff;font-size:18px;font-weight:700;letter-spacing:-0.01em;">{headline}</div>
      <div style="color:#ffffffd9;font-size:13px;margin-top:5px;line-height:1.5;">{summary}</div>
    </div>
    <div style="padding:16px 24px 8px;border-bottom:1px solid #f1f5f9;">
      {pills}
    </div>
    <table style="width:100%;border-collapse:collapse;">
      <tbody>{rows}</tbody>
    </table>
    <div style="padding:20px 24px 4px;">
      {action_block}
    </div>
    <div style="padding:16px 24px;border-top:1px solid #f1f5f9;color:#94a3b8;font-size:12px;">
      Automated report from the PromptMaxx engine · {generated}
    </div>
  </div>
  <div style="text-align:center;color:#b0b7c3;font-size:11px;margin-top:14px;">
    You are receiving this because you are a configured LLM credit alert recipient.
  </div>
</div>
</body></html>"""
    return subject, text_body, html_body


def run_quota_check_and_alert():
    """Probe all providers, email recipients on a state change / depletion /
    recovery (deduped), and persist the new state. Safe to call on a schedule."""
    if not _cfg("QUOTA_ALERT_ENABLED", True):
        return {"skipped": "QUOTA_ALERT_ENABLED is False"}

    recipients = _cfg("QUOTA_ALERT_RECIPIENTS", [])
    if isinstance(recipients, str):
        recipients = [e.strip() for e in recipients.split(",") if e.strip()]

    results = check_all_quotas()
    cur = {r["key"]: r["state"] for r in results if r["state"] != "NOT_CONFIGURED"}

    state = _load_state()

    # We ONLY care about credit depletion. A provider must look depleted on
    # CONFIRM_RUNS consecutive checks before it counts — a single bad probe
    # (network blip, momentary throttle) must never move a key in or out of the
    # alert set, because every such move would otherwise send mail.
    observed = sorted(k for k, s in cur.items() if s in ALERT_STATES)
    prev_pending = state.get("pending", {}) or {}
    pending = {}
    for k in observed:
        try:
            pending[k] = int(prev_pending.get(k, 0)) + 1
        except (TypeError, ValueError):
            pending[k] = 1
    confirm_runs = max(1, int(_cfg("QUOTA_ALERT_CONFIRM_RUNS", 2) or 2))
    depleted_now = sorted(k for k, seen in pending.items() if seen >= confirm_runs)

    prev_depleted = sorted(state.get("depleted", []))
    last_alert = state.get("last_alert_ts")

    newly_depleted = [k for k in depleted_now if k not in prev_depleted]   # a key just ran out
    recovered = [k for k in prev_depleted if k not in depleted_now]        # a key got topped up
    notify_recovery = bool(_cfg("QUOTA_ALERT_ON_RECOVERY", True)) and bool(recovered)

    # Reminder while still depleted (so it isn't forgotten), capped by REPEAT_HOURS.
    # Set REPEAT_HOURS=0 to disable reminders entirely — then a depleted provider
    # is mailed about exactly once, when it first runs out.
    try:
        repeat_hours = int(_cfg("QUOTA_ALERT_REPEAT_HOURS", 12))
    except (TypeError, ValueError):
        repeat_hours = 12
    stale = False
    if depleted_now and repeat_hours > 0:
        elapsed = _elapsed_since(last_alert)
        stale = elapsed is None or elapsed > timedelta(hours=repeat_hours)

    # Hard floor between ANY two alert mails. This is the backstop: even if the
    # depleted set churns (duplicate schedulers, a flapping provider, a broken
    # mailer that never lets last_alert_ts advance), recipients can never be
    # mailed more often than this.
    min_interval = max(0, int(_cfg("QUOTA_ALERT_MIN_INTERVAL_MINUTES", 60) or 0))
    since_attempt = _elapsed_since(state.get("last_attempt_ts"))
    cooling_down = bool(min_interval) and since_attempt is not None and since_attempt < timedelta(minutes=min_interval)

    # Email ONLY when: a key newly ran out of credits, a key recovered, or a
    # still-depleted reminder is due — and never while cooling down.
    triggered = bool(newly_depleted) or notify_recovery or (bool(depleted_now) and stale)
    should_email = bool(recipients) and triggered and not cooling_down
    if triggered and cooling_down:
        logger.info(
            f"[QuotaMonitor] alert suppressed (cooldown {min_interval}m): "
            f"depleted={depleted_now} recovered={recovered}"
        )

    emailed = False
    if should_email:
        subject, text_body, html_body = _build_email(results, recovered=recovered)
        try:
            from core.mailgun_email_service import MailgunEmailService
            res = MailgunEmailService().send_report_email(
                recipients=recipients, subject=subject, body_text=text_body, body_html=html_body
            )
            emailed = bool(res.get("success", True))
            logger.info(f"[QuotaMonitor] alert emailed to {recipients}: depleted={depleted_now} recovered={recovered}")
        except Exception as e:
            logger.error(f"[QuotaMonitor] failed to send alert email: {e}", exc_info=True)
    elif not recipients:
        logger.warning("[QuotaMonitor] no QUOTA_ALERT_RECIPIENTS configured — skipping email")

    new_state = {"statuses": cur, "pending": pending}
    if should_email and not emailed:
        # The notification did not go out. Do NOT commit the transition —
        # keep the previous depleted set so the same alert is retried on a
        # later run instead of being silently swallowed. last_attempt_ts
        # (set below) is what paces those retries.
        new_state["depleted"] = prev_depleted
        if prev_depleted:
            new_state["last_alert_ts"] = last_alert
    else:
        new_state["depleted"] = depleted_now
        # Keep the last-alert timestamp only while still depleted (drives the
        # reminder); clear it once everything is back so the next outage alerts
        # immediately.
        if emailed and depleted_now:
            new_state["last_alert_ts"] = timezone.now().isoformat()
        elif depleted_now:
            new_state["last_alert_ts"] = last_alert

    new_state["last_attempt_ts"] = (
        timezone.now().isoformat() if should_email else state.get("last_attempt_ts")
    )
    new_state = {k: v for k, v in new_state.items() if v is not None}
    _save_state(new_state)

    return {"statuses": cur, "depleted": depleted_now, "recovered": recovered,
            "emailed": emailed, "suppressed": bool(triggered and cooling_down),
            "recipients": recipients}
