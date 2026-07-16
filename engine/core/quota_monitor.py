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
    if not api_key:
        return _result("OpenAI / ChatGPT", "openai", False, "NOT_CONFIGURED")
    try:
        from openai import OpenAI
        OpenAI(api_key=api_key, timeout=30).chat.completions.create(
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
    if not api_key:
        return _result("Anthropic / Claude", "anthropic", False, "NOT_CONFIGURED")
    try:
        import anthropic
        anthropic.Anthropic(api_key=api_key, timeout=30).messages.create(
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
        elif "authentication" in ml or "invalid x-api-key" in ml or "401" in m:
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
            st = "OUT_OF_CREDITS"
        elif r.status_code == 404:
            st = "MODEL_UNAVAILABLE"
        elif r.status_code in (400, 401, 403):
            st = "INVALID_KEY"
        else:
            st = "ERROR"
        return _result("Google Gemini", "gemini", True, st, f"HTTP {r.status_code} {gstatus} {gmsg}")
    except Exception as e:
        return _result("Google Gemini", "gemini", True, "ERROR", str(e))


def _probe_openai_compatible(label, key, api_key, base_url, model):
    """Perplexity / xAI / DeepSeek expose OpenAI-compatible chat endpoints."""
    if not api_key:
        return _result(label, key, False, "NOT_CONFIGURED")
    try:
        from openai import OpenAI
        OpenAI(api_key=api_key, base_url=base_url, timeout=30).chat.completions.create(
            model=model, messages=[{"role": "user", "content": "ping"}], max_tokens=1
        )
        return _result(label, key, True, "OK")
    except Exception as e:
        m = str(e)
        ml = m.lower()
        if "insufficient" in ml or "credit" in ml or "billing" in ml or "quota" in ml:
            st = "OUT_OF_CREDITS"
        elif "rate" in ml and "limit" in ml:
            st = "RATE_LIMIT"
        elif "401" in m or "authentication" in ml or "invalid" in ml:
            st = "INVALID_KEY"
        else:
            st = "ERROR"
        return _result(label, key, True, st, m)


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
    if provider == "openai":
        return _probe_openai(api_key, _cfg("QUOTA_PROBE_OPENAI_MODEL", "gpt-4o-mini"))
    if provider == "anthropic":
        return _probe_anthropic(api_key, _cfg("QUOTA_PROBE_ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"))
    if provider == "gemini":
        return _probe_gemini(api_key, _cfg("GEMINI_MODEL", "gemini-flash-latest"))
    if provider == "perplexity":
        return _probe_openai_compatible("Perplexity", "perplexity", api_key,
                                        "https://api.perplexity.ai", _cfg("QUOTA_PROBE_PERPLEXITY_MODEL", "sonar"))
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
        _probe_openai(_cfg("OPENAI_API_KEY", ""), _cfg("QUOTA_PROBE_OPENAI_MODEL", "gpt-4o-mini")),
        _probe_anthropic(_cfg("ANTHROPIC_API_KEY", ""), _cfg("QUOTA_PROBE_ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")),
        _probe_gemini(_cfg("GEMINI_API_KEY", ""), _cfg("GEMINI_MODEL", "gemini-flash-latest")),
        _probe_openai_compatible("Perplexity", "perplexity", _cfg("PERPLEXITY_API_KEY", ""),
                                 "https://api.perplexity.ai", _cfg("QUOTA_PROBE_PERPLEXITY_MODEL", "sonar")),
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
    try:
        with open(_state_path(), "w") as fh:
            json.dump(state, fh)
    except Exception as e:
        logger.warning(f"[QuotaMonitor] could not save state: {e}")


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
    rows = ""
    for r in results:
        c = _color(r["state"])
        badge = (f'<span style="display:inline-block;padding:3px 10px;border-radius:12px;'
                 f'background:{c};color:#fff;font-size:12px;font-weight:600;white-space:nowrap;">'
                 f'{_STATUS_LABEL.get(r["state"], r["state"])}</span>')
        rows += (
            '<tr>'
            f'<td style="padding:12px 16px;border-bottom:1px solid #eef0f3;font-weight:600;color:#111827;">{r["label"]}</td>'
            f'<td style="padding:12px 16px;border-bottom:1px solid #eef0f3;text-align:center;">{badge}</td>'
            f'<td style="padding:12px 16px;border-bottom:1px solid #eef0f3;color:#6b7280;font-size:13px;">{_STATUS_NOTE.get(r["state"], "")}</td>'
            '</tr>'
        )

    action_block = ""
    if depleted:
        items = "".join(f'<li style="margin:4px 0;">{r["label"]}</li>' for r in depleted)
        action_block = (
            '<div style="margin:20px 0 4px;padding:16px 18px;background:#fef2f2;border:1px solid #fecaca;border-radius:8px;">'
            '<div style="font-weight:700;color:#991b1b;margin-bottom:6px;">⚠ Action required — credits depleted</div>'
            '<div style="color:#7f1d1d;font-size:14px;margin-bottom:8px;">Please top up / enable credits for:</div>'
            f'<ul style="margin:0;padding-left:20px;color:#7f1d1d;font-size:14px;">{items}</ul>'
            '<div style="color:#7f1d1d;font-size:13px;margin-top:10px;">Tracking repopulates automatically on the next scheduled run once credits are restored.</div>'
            '</div>'
        )
    elif recovered_rows:
        items = "".join(f'<li style="margin:4px 0;">{r["label"]}</li>' for r in recovered_rows)
        action_block = (
            '<div style="margin:20px 0 4px;padding:16px 18px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;">'
            '<div style="font-weight:700;color:#166534;margin-bottom:6px;">✓ Credits restored</div>'
            f'<ul style="margin:0;padding-left:20px;color:#166534;font-size:14px;">{items}</ul>'
            '</div>'
        )

    html_body = f"""\
<!DOCTYPE html><html><body style="margin:0;padding:0;background:#f4f5f7;">
<div style="max-width:600px;margin:0 auto;padding:24px 12px;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;">
  <div style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
    <div style="background:{banner_color};padding:18px 24px;">
      <div style="color:#ffffff;font-size:18px;font-weight:700;">LLM Credit Status — {headline}</div>
      <div style="color:#ffffffcc;font-size:13px;margin-top:2px;">{summary}</div>
    </div>
    <div style="padding:20px 24px;">
      <table style="width:100%;border-collapse:collapse;">
        <thead><tr>
          <th style="text-align:left;padding:8px 16px;font-size:12px;color:#9ca3af;text-transform:uppercase;letter-spacing:.04em;border-bottom:2px solid #eef0f3;">Provider</th>
          <th style="text-align:center;padding:8px 16px;font-size:12px;color:#9ca3af;text-transform:uppercase;letter-spacing:.04em;border-bottom:2px solid #eef0f3;">Status</th>
          <th style="text-align:left;padding:8px 16px;font-size:12px;color:#9ca3af;text-transform:uppercase;letter-spacing:.04em;border-bottom:2px solid #eef0f3;">Note</th>
        </tr></thead>
        <tbody>{rows}</tbody>
      </table>
      {action_block}
    </div>
    <div style="padding:14px 24px;border-top:1px solid #eef0f3;color:#9ca3af;font-size:12px;">
      Automated alert from the PromptMaxx engine · {generated}
    </div>
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
    # We ONLY care about credit depletion. Track the set of providers that are
    # out of credits now vs last check; transient errors/rate-limits are ignored.
    depleted_now = sorted(k for k, s in cur.items() if s in ALERT_STATES)

    state = _load_state()
    prev_depleted = sorted(state.get("depleted", []))
    last_alert = state.get("last_alert_ts")

    newly_depleted = [k for k in depleted_now if k not in prev_depleted]   # a key just ran out
    recovered = [k for k in prev_depleted if k not in depleted_now]        # a key got topped up
    notify_recovery = bool(_cfg("QUOTA_ALERT_ON_RECOVERY", True)) and bool(recovered)

    # Reminder while still depleted (so it isn't forgotten), capped by REPEAT_HOURS.
    repeat_hours = int(_cfg("QUOTA_ALERT_REPEAT_HOURS", 12) or 12)
    stale = False
    if depleted_now:
        if not last_alert:
            stale = True
        else:
            try:
                stale = timezone.now() - timezone.datetime.fromisoformat(last_alert) > timedelta(hours=repeat_hours)
            except Exception:
                stale = True

    # Email ONLY when: a key newly ran out of credits, a key recovered, or a
    # still-depleted reminder is due. Nothing else sends mail.
    should_email = bool(recipients) and (bool(newly_depleted) or notify_recovery or (bool(depleted_now) and stale))

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

    new_state = {"statuses": cur, "depleted": depleted_now}
    # Keep the last-alert timestamp only while still depleted (drives the reminder);
    # clear it once everything is back so the next outage alerts immediately.
    if emailed and depleted_now:
        new_state["last_alert_ts"] = timezone.now().isoformat()
    elif depleted_now:
        new_state["last_alert_ts"] = last_alert
    _save_state(new_state)

    return {"statuses": cur, "depleted": depleted_now, "recovered": recovered,
            "emailed": emailed, "recipients": recipients}
