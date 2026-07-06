"""
Daily Content Generation usage digest email.

Once a night a consolidated usage report is mailed to every active super-admin of
each organisation that has an Anthropic Admin (usage-reporting) key configured.
The report shows LIVE usage pulled directly from Anthropic's usage_report API:

    * Today's consumption (input/output/total tokens + estimated cost, or
      "No activity today" when nothing was generated).
    * Month-to-date (MTD) consumption + estimated cost.

The monthly token-limit / budget-bar concept was removed — live Anthropic usage
and cost replace it entirely.

This is additive and isolated — it only reads the Admin key + calls Anthropic,
and never raises into the Celery beat loop.
"""
import logging

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def _cfg(name, default):
    return getattr(settings, name, default)


# ---------------------------------------------------------------------------
# Live Anthropic usage fetch (engine-side mirror of the backend helper)
# ---------------------------------------------------------------------------
class AnthropicCreditError(Exception):
    """Raised when Anthropic's usage/billing API signals exhausted credits."""
    pass


# Anthropic pricing in USD per MILLION tokens. Keep in sync with the backend
# ANTHROPIC_PRICING map (authentication/auth_views.py).
# We define:
# - input_uncached: Standard input tokens
# - input_cached: Tokens read from prompt cache (typically 10% of base rate)
# - input_cache_creation: Tokens written to prompt cache (typically 125% of base rate)
# - output: Output tokens generated
ANTHROPIC_PRICING = {
    # Haiku family
    'claude-3-5-haiku':  {'input_uncached': 0.80,  'input_cached': 0.08, 'input_cache_creation': 1.00,  'output': 4.00},
    'claude-3-haiku':    {'input_uncached': 0.25,  'input_cached': 0.03, 'input_cache_creation': 0.31,  'output': 1.25},
    'claude-haiku':      {'input_uncached': 1.00,  'input_cached': 0.10, 'input_cache_creation': 1.25,  'output': 5.00},
    # Sonnet family
    'claude-3-5-sonnet': {'input_uncached': 3.00,  'input_cached': 0.30, 'input_cache_creation': 3.75,  'output': 15.00},
    'claude-sonnet-4-5': {'input_uncached': 3.00,  'input_cached': 0.30, 'input_cache_creation': 3.75,  'output': 15.00},
    'claude-3-sonnet':   {'input_uncached': 3.00,  'input_cached': 0.30, 'input_cache_creation': 3.75,  'output': 15.00},
    'claude-sonnet':     {'input_uncached': 3.00,  'input_cached': 0.30, 'input_cache_creation': 3.75,  'output': 15.00},
    # Opus family
    'claude-3-opus':     {'input_uncached': 15.00, 'input_cached': 1.50, 'input_cache_creation': 18.75, 'output': 75.00},
    'claude-opus':       {'input_uncached': 15.00, 'input_cached': 1.50, 'input_cache_creation': 18.75, 'output': 75.00},
    # Default fallback — sonnet rates
    '_default':          {'input_uncached': 3.00,  'input_cached': 0.30, 'input_cache_creation': 3.75,  'output': 15.00},
}


def _get_model_rates(model_name):
    model_lower = (model_name or '').lower()
    best_key = None
    for key in ANTHROPIC_PRICING:
        if key == '_default':
            continue
        if model_lower.startswith(key) and (best_key is None or len(key) > len(best_key)):
            best_key = key
    return ANTHROPIC_PRICING[best_key] if best_key else ANTHROPIC_PRICING['_default']


def _fetch_live_anthropic_usage(admin_key, start_dt, end_dt):
    """Aggregate live usage/cost from Anthropic's usage_report API.
    Returns {input_tokens, output_tokens, total_tokens, estimated_cost_usd,
    caching_savings_usd, caching_savings_pct}.
    Raises AnthropicCreditError when credits are exhausted."""
    import requests as req
    r = req.get(
        'https://api.anthropic.com/v1/organizations/usage_report/messages',
        headers={'x-api-key': admin_key, 'anthropic-version': '2023-06-01'},
        params={
            'starting_at': start_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'ending_at': end_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'bucket_width': '1d',
            'group_by[]': 'model',
        },
        timeout=20,
    )
    if r.status_code == 402:
        raise AnthropicCreditError('OUT_OF_CREDITS')
    if r.status_code != 200:
        try:
            msg = (r.json().get('error', {}).get('message') or '').lower()
            if any(w in msg for w in ('credit', 'billing', 'insufficient')):
                raise AnthropicCreditError('OUT_OF_CREDITS')
        except AnthropicCreditError:
            raise
        except Exception:
            pass
        r.raise_for_status()

    data = r.json().get('data', [])
    total_input = total_output = 0.0
    total_cost = 0.0
    total_normal_input_cost = 0.0
    total_actual_input_cost = 0.0

    for bucket in data:
        rates = _get_model_rates(bucket.get('model', ''))
        
        uncached_inp = bucket.get('uncached_input_tokens', 0) or 0
        cached_read = bucket.get('cache_read_input_tokens', 0) or 0
        
        cache_write_obj = bucket.get('cache_creation', {}) or {}
        if not cache_write_obj:
            cache_write_obj = {}
        cached_write = (cache_write_obj.get('ephemeral_5m_input_tokens', 0) or 0) + \
                       (cache_write_obj.get('ephemeral_1h_input_tokens', 0) or 0)
        
        inp = uncached_inp + cached_read + cached_write
        out = bucket.get('output_tokens', 0) or 0
        
        total_input += inp
        total_output += out
        
        cost_uncached = (uncached_inp / 1_000_000) * rates['input_uncached']
        cost_cached = (cached_read / 1_000_000) * rates['input_cached']
        cost_write = (cached_write / 1_000_000) * rates['input_cache_creation']
        cost_out = (out / 1_000_000) * rates['output']
        
        total_cost += cost_uncached + cost_cached + cost_write + cost_out
        total_actual_input_cost += cost_uncached + cost_cached + cost_write
        total_normal_input_cost += (inp / 1_000_000) * rates['input_uncached']

    caching_savings_usd = max(0.0, total_normal_input_cost - total_actual_input_cost)
    caching_savings_pct = (caching_savings_usd / total_normal_input_cost * 100.0) if total_normal_input_cost > 0 else 0.0

    return {
        'input_tokens': int(total_input),
        'output_tokens': int(total_output),
        'total_tokens': int(total_input + total_output),
        'estimated_cost_usd': round(total_cost, 4),
        'caching_savings_usd': round(caching_savings_usd, 4),
        'caching_savings_pct': round(caching_savings_pct, 2),
    }


def _fmt(n):
    """Thousands-separated integer formatting (handles negatives)."""
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return "0"


def _fmt_usd(n):
    try:
        return f"${float(n):,.4f}"
    except (TypeError, ValueError):
        return "$0.0000"


# ---------------------------------------------------------------------------
# Email rendering (dark-mode, responsive)
# ---------------------------------------------------------------------------
def _metric_cell(label, value):
    return (
        '<td style="padding:10px 14px;background:#0f1623;border:1px solid #1f2937;'
        'border-radius:10px;">'
        f'<div style="color:#9ca3af;font-size:11px;text-transform:uppercase;'
        f'letter-spacing:.05em;">{label}</div>'
        f'<div style="color:#f3f4f6;font-size:18px;font-weight:700;margin-top:2px;">{value}</div>'
        "</td>"
    )


def _metrics_grid(stats):
    """Two rows: total tokens / est. cost on top, input / output below."""
    return (
        '<table role="presentation" width="100%" style="border-collapse:separate;border-spacing:8px;">'
        "<tr>"
        + _metric_cell("Total Tokens", _fmt(stats["total_tokens"]))
        + _metric_cell("Estimated Cost", _fmt_usd(stats["estimated_cost_usd"]))
        + "</tr><tr>"
        + _metric_cell("Input Tokens", _fmt(stats["input_tokens"]))
        + _metric_cell("Output Tokens", _fmt(stats["output_tokens"]))
        + "</tr></table>"
    )


def _build_digest_email(org, today, month, now):
    """Return (subject, text_body, html_body) for one organisation's digest.

    `today` and `month` are live-usage dicts from _fetch_live_anthropic_usage.
    """
    subject = f"Daily Content Generation Usage Report - {org.name}"
    today_label = now.strftime("%d %b %Y")
    month_label = now.strftime("%B %Y")
    no_activity = today["total_tokens"] == 0

    # ---- plain-text fallback ----
    tlines = [
        f"Daily Content Generation Usage Report — {org.name}",
        today_label,
        "",
        "TODAY'S CONSUMPTION:",
    ]
    if no_activity:
        tlines.append("  No activity today")
    else:
        tlines += [
            f"  Input Tokens:   {_fmt(today['input_tokens'])}",
            f"  Output Tokens:  {_fmt(today['output_tokens'])}",
            f"  Total Tokens:   {_fmt(today['total_tokens'])}",
            f"  Estimated Cost: {_fmt_usd(today['estimated_cost_usd'])}",
        ]
    tlines += [
        "",
        f"MONTH-TO-DATE ({month_label}):",
        f"  Input Tokens:   {_fmt(month['input_tokens'])}",
        f"  Output Tokens:  {_fmt(month['output_tokens'])}",
        f"  Total Tokens:   {_fmt(month['total_tokens'])}",
        f"  Estimated Cost: {_fmt_usd(month['estimated_cost_usd'])}",
        "",
        "— Automated digest from the PromptMaxx engine (live Anthropic usage)",
    ]
    text_body = "\n".join(tlines)

    # ---- today block (HTML) ----
    if no_activity:
        today_block = (
            '<div style="padding:18px;background:#0f1623;border:1px dashed #374151;'
            'border-radius:12px;text-align:center;color:#9ca3af;font-size:14px;">'
            "No activity today</div>"
        )
    else:
        today_block = _metrics_grid(today)

    def _section(title, inner):
        return (
            '<div style="margin-top:18px;">'
            f'<div style="color:#D4A04A;font-size:13px;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:.06em;margin-bottom:8px;">{title}</div>'
            f"{inner}</div>"
        )

    html_body = f"""\
<!DOCTYPE html><html><body style="margin:0;padding:0;background:#0b0f17;">
<div style="max-width:600px;margin:0 auto;padding:24px 12px;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;">
  <div style="background:#151b26;border:1px solid #1f2937;border-radius:16px;overflow:hidden;">
    <div style="padding:22px 24px;background:linear-gradient(135deg,#1f2937 0%,#111827 100%);border-bottom:1px solid #1f2937;">
      <div style="color:#D4A04A;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;">Content Generation</div>
      <div style="color:#f9fafb;font-size:20px;font-weight:700;margin-top:4px;">Daily Usage Report</div>
      <div style="color:#9ca3af;font-size:13px;margin-top:4px;">{org.name} · {today_label}</div>
    </div>
    <div style="padding:18px 18px 24px;">
      {_section("Today's Consumption", today_block)}
      {_section(f"Month to Date · {month_label}", _metrics_grid(month))}
    </div>
    <div style="padding:14px 24px;border-top:1px solid #1f2937;color:#6b7280;font-size:12px;">
      Live Anthropic usage · {now.strftime('%d %b %Y, %H:%M UTC')}
    </div>
  </div>
</div>
</body></html>"""
    return subject, text_body, html_body


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def run_daily_usage_digests():
    """Build and send the daily live-usage digest to every eligible organisation.

    Eligible = has an Anthropic Admin key configured AND at least one active
    super-admin recipient. Live usage is fetched per org from Anthropic; an org
    whose fetch fails (credit/network/API error) is skipped and logged. Always
    sends when usage is available, even if today's usage is zero. Never raises;
    returns a small summary dict.
    """
    if not _cfg("USAGE_DIGEST_ENABLED", True):
        return {"skipped": "USAGE_DIGEST_ENABLED is False"}

    try:
        from shared_models.models import Account, Organisation
        from shared_models.crypto import decrypt_value
    except Exception as e:
        logger.warning(f"[UsageDigest] models unavailable: {e}")
        return {"error": str(e)}

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Orgs with an Anthropic Admin (usage-reporting) key configured.
    orgs = (
        Organisation.objects.exclude(content_admin_api_key__isnull=True)
        .exclude(content_admin_api_key="")
    )

    sent, skipped, failed = [], [], []
    try:
        from core.mailgun_email_service import MailgunEmailService
        mailer = MailgunEmailService()
    except Exception as e:
        logger.error(f"[UsageDigest] mail service unavailable: {e}", exc_info=True)
        return {"error": f"mail service unavailable: {e}"}

    for org in orgs:
        try:
            recipients = list(
                Account.objects.filter(
                    organisation=org, role="super_admin", is_active=True
                )
                .exclude(email="")
                .values_list("email", flat=True)
            )
            recipients = [e for e in recipients if e]
            if not recipients:
                skipped.append({"org": org.id, "reason": "no active super_admin recipients"})
                continue

            admin_key = decrypt_value(org.content_admin_api_key) if org.content_admin_api_key else ""
            if not admin_key:
                skipped.append({"org": org.id, "reason": "admin key empty after decrypt"})
                continue

            try:
                today = _fetch_live_anthropic_usage(admin_key, today_start, now)
                month = _fetch_live_anthropic_usage(admin_key, month_start, now)
            except AnthropicCreditError:
                skipped.append({"org": org.id, "reason": "OUT_OF_CREDITS"})
                continue
            except Exception as fe:
                logger.warning(f"[UsageDigest] org {org.id} live fetch failed: {fe}")
                failed.append({"org": org.id, "reason": f"live fetch failed: {fe}"})
                continue

            subject, text_body, html_body = _build_digest_email(org, today, month, now)
            res = mailer.send_report_email(
                recipients=recipients, subject=subject,
                body_text=text_body, body_html=html_body,
            )
            if res.get("success", True):
                sent.append({"org": org.id, "recipients": len(recipients)})
            else:
                failed.append({"org": org.id, "reason": res.get("message", "send failed")})
        except Exception as e:
            logger.error(f"[UsageDigest] org {org.id} digest failed: {e}", exc_info=True)
            failed.append({"org": org.id, "reason": str(e)})

    logger.info(f"[UsageDigest] sent={len(sent)} skipped={len(skipped)} failed={len(failed)}")
    return {"sent": sent, "skipped": skipped, "failed": failed}
