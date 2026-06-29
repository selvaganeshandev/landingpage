"""
Daily Content Generation usage digest email.

Once a night a consolidated usage report is mailed to every active super-admin of
each organisation that has a dedicated Content Generation (Claude) key
configured. The report shows:

    * Today's consumption (requests + input/output/total tokens, or
      "No activity today" when nothing was generated).
    * Month-to-date (MTD) consumption.
    * Remaining balance against the optional custom monthly token budget, with a
      visual progress bar. When no budget is set the balance reads "Unlimited"
      and the bar is omitted.

This is additive and isolated — it only reads ContentGenerationUsage rows and
never raises into the Celery beat loop.
"""
import logging

from django.conf import settings
from django.db.models import Count, Sum
from django.utils import timezone

logger = logging.getLogger(__name__)


def _cfg(name, default):
    return getattr(settings, name, default)


def _agg(qs):
    """Aggregate a ContentGenerationUsage queryset into a metrics dict."""
    a = qs.aggregate(
        requests=Count("id"),
        input_tokens=Sum("input_tokens"),
        output_tokens=Sum("output_tokens"),
        total_tokens=Sum("total_tokens"),
    )
    return {
        "requests": a["requests"] or 0,
        "input_tokens": a["input_tokens"] or 0,
        "output_tokens": a["output_tokens"] or 0,
        "total_tokens": a["total_tokens"] or 0,
    }


def _fmt(n):
    """Thousands-separated integer formatting (handles negatives)."""
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return "0"


def _budget_view(limit, mtd_total):
    """Compute the budget display model for the email.

    Returns a dict with: unlimited (bool), limit, remaining, used_pct (float, may
    exceed 100), bar_pct (0-100, capped for rendering), and bar_color.
    """
    if limit is None:
        return {"unlimited": True}
    limit = int(limit)
    remaining = limit - int(mtd_total)
    used_pct = (mtd_total / limit * 100.0) if limit > 0 else 100.0
    bar_pct = max(0.0, min(100.0, used_pct))
    if used_pct >= 100:
        bar_color = "#dc2626"   # over / at budget — red
    elif used_pct >= 75:
        bar_color = "#d97706"   # nearing budget — amber
    else:
        bar_color = "#16a34a"   # healthy — green
    return {
        "unlimited": False,
        "limit": limit,
        "remaining": remaining,
        "used_pct": used_pct,
        "bar_pct": bar_pct,
        "bar_color": bar_color,
    }


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
    """Two rows of metric cells: requests/total on top, input/output below."""
    return (
        '<table role="presentation" width="100%" style="border-collapse:separate;border-spacing:8px;">'
        "<tr>"
        + _metric_cell("Requests", _fmt(stats["requests"]))
        + _metric_cell("Total Tokens", _fmt(stats["total_tokens"]))
        + "</tr><tr>"
        + _metric_cell("Input Tokens", _fmt(stats["input_tokens"]))
        + _metric_cell("Output Tokens", _fmt(stats["output_tokens"]))
        + "</tr></table>"
    )


def _build_digest_email(org, today, mtd, limit, now):
    """Return (subject, text_body, html_body) for one organisation's digest."""
    subject = f"Daily Content Generation Usage Report - {org.name}"
    today_label = now.strftime("%d %b %Y")
    month_label = now.strftime("%B %Y")
    no_activity = today["requests"] == 0 and today["total_tokens"] == 0
    budget = _budget_view(limit, mtd["total_tokens"])

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
            f"  Requests:      {_fmt(today['requests'])}",
            f"  Input Tokens:  {_fmt(today['input_tokens'])}",
            f"  Output Tokens: {_fmt(today['output_tokens'])}",
            f"  Total Tokens:  {_fmt(today['total_tokens'])}",
        ]
    tlines += [
        "",
        f"MONTH-TO-DATE ({month_label}):",
        f"  Requests:      {_fmt(mtd['requests'])}",
        f"  Input Tokens:  {_fmt(mtd['input_tokens'])}",
        f"  Output Tokens: {_fmt(mtd['output_tokens'])}",
        f"  Total Tokens:  {_fmt(mtd['total_tokens'])}",
        "",
    ]
    if budget["unlimited"]:
        tlines += ["Monthly Token Limit: Unlimited", "Remaining: Unlimited"]
    else:
        tlines += [
            f"Monthly Token Limit: {_fmt(budget['limit'])}",
            f"Used: {_fmt(mtd['total_tokens'])} ({budget['used_pct']:.1f}%)",
            f"Remaining: {_fmt(budget['remaining'])}",
        ]
    tlines += ["", "— Automated digest from the PromptMaxx engine"]
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

    # ---- budget block (HTML) ----
    if budget["unlimited"]:
        budget_block = (
            '<table role="presentation" width="100%" style="border-collapse:separate;border-spacing:8px;">'
            "<tr>"
            + _metric_cell("Monthly Token Limit", "Unlimited")
            + _metric_cell("Remaining", "Unlimited")
            + "</tr></table>"
        )
    else:
        over = budget["remaining"] < 0
        remaining_color = "#f87171" if over else "#34d399"
        budget_block = (
            '<table role="presentation" width="100%" style="border-collapse:separate;border-spacing:8px;">'
            "<tr>"
            + _metric_cell("Monthly Limit", _fmt(budget["limit"]))
            + _metric_cell("Used This Month", f'{_fmt(mtd["total_tokens"])} ({budget["used_pct"]:.1f}%)')
            + "</tr></table>"
            '<div style="margin:6px 8px 0;">'
            '<div style="height:14px;background:#0f1623;border:1px solid #1f2937;'
            'border-radius:999px;overflow:hidden;">'
            f'<div style="height:100%;width:{budget["bar_pct"]:.1f}%;background:{budget["bar_color"]};"></div>'
            "</div>"
            '<div style="display:flex;justify-content:space-between;margin-top:8px;">'
            '<span style="color:#9ca3af;font-size:12px;">Remaining</span>'
            f'<span style="color:{remaining_color};font-size:14px;font-weight:700;">{_fmt(budget["remaining"])} tokens</span>'
            "</div>"
            "</div>"
        )

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
      {_section(f"Month to Date · {month_label}", _metrics_grid(mtd))}
      {_section("Monthly Budget", budget_block)}
    </div>
    <div style="padding:14px 24px;border-top:1px solid #1f2937;color:#6b7280;font-size:12px;">
      Automated digest from the PromptMaxx engine · {now.strftime('%d %b %Y, %H:%M UTC')}
    </div>
  </div>
</div>
</body></html>"""
    return subject, text_body, html_body


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def run_daily_usage_digests():
    """Build and send the daily usage digest to every eligible organisation.

    Eligible = has a Content Generation key configured AND at least one active
    super-admin recipient. Always sends, even when today's usage is zero. Never
    raises; returns a small summary dict.
    """
    if not _cfg("USAGE_DIGEST_ENABLED", True):
        return {"skipped": "USAGE_DIGEST_ENABLED is False"}

    try:
        from shared_models.models import Account, ContentGenerationUsage, Organisation
    except Exception as e:
        logger.warning(f"[UsageDigest] models unavailable: {e}")
        return {"error": str(e)}

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Orgs with a configured Content Generation key (non-null, non-empty).
    orgs = (
        Organisation.objects.exclude(content_generation_api_key__isnull=True)
        .exclude(content_generation_api_key="")
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

            base = ContentGenerationUsage.objects.filter(organisation=org)
            today = _agg(base.filter(created_at__gte=today_start))
            mtd = _agg(base.filter(created_at__gte=month_start))
            limit = org.content_generation_token_limit

            subject, text_body, html_body = _build_digest_email(org, today, mtd, limit, now)
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
