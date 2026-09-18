"""Lead alerts the backend raises after publication.

The engine emails "new lead" when a landing-page audit publishes; the backend
covers the two signals that only it can see:

  * warm lead  — an unclaimed landing-page audit whose public report has been
                 opened AUDIT_WARM_LEAD_OPENS times (the prototype's
                 "unclaimed + opened 5+ times = warm"); fires once, on the
                 exact count, so a popular report does not spam the team;
  * claimed    — someone turned an audit into a project.

Recipients come from AUDIT_LEAD_ALERT_EMAILS. Every path is fail-silent: a
mail problem must never break a public GET or a claim.
"""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def recipients():
    raw = getattr(settings, 'AUDIT_LEAD_ALERT_EMAILS', '') or ''
    if isinstance(raw, (list, tuple)):
        return [str(r).strip() for r in raw if str(r).strip()]
    return [r.strip() for r in str(raw).split(',') if r.strip()]


def _app_url(audit):
    base = (getattr(settings, 'FRONTEND_URL', '') or 'http://localhost:8080').rstrip('/')
    return f'{base}/audits/{audit.pk}'


def _public_url(audit):
    base = (getattr(settings, 'FRONTEND_URL', '') or 'http://localhost:8080').rstrip('/')
    return f'{base}/audit/{audit.public_token}'


def _send(subject, body):
    to = recipients()
    if not to:
        return False
    try:
        from llm_monitor.email_utils import send_mail
        return bool(send_mail(subject, body, recipient_list=to, fail_silently=True))
    except Exception as exc:  # noqa: BLE001
        logger.warning('[Audit] lead alert not sent: %s', exc)
        return False


def report_email(audit):
    """The "your audit is ready" message, as (subject, text, html).

    Mirrors the engine's publish-time email so a report sent by hand from the
    audit page reads exactly like one sent automatically.
    """
    brand = audit.brand_name or audit.host
    link = _public_url(audit)
    ttl = int(getattr(settings, 'AUDIT_PUBLIC_TTL_DAYS', 30))
    stage = (audit.geo_stage or '').replace('_', ' ') or 'unscored'
    headline = (
        f"GEO score {audit.geo_score if audit.geo_score is not None else '—'} · {stage} · "
        f"mentioned on {audit.appearances} of {audit.total_runs} answers, cited on {audit.cited_runs}"
    )
    text = (
        f"The AI visibility audit of {brand} is ready.\n\n{headline}\n\n"
        f"Open the report: {link}\n\n"
        f"The link works without a login and stays live for {ttl} days.\n\n— PromptMaxx"
    )
    html = (
        f"<p>The AI visibility audit of <strong>{brand}</strong> is ready.</p>"
        f"<p>{headline}</p>"
        f'<p><a href="{link}">Open the report</a></p>'
        f"<p style='color:#6b7280;font-size:13px'>The link works without a login and stays live for {ttl} days.</p>"
        "<p>— PromptMaxx</p>"
    )
    return f'AI visibility audit of {brand}', text, html


def send_report_email(audit, addresses):
    """Email the public report link to `addresses`. Returns True when Mailgun accepted it."""
    if not addresses:
        return False
    subject, text, html = report_email(audit)
    try:
        from llm_monitor.email_utils import send_mail
        return bool(send_mail(subject, text, recipient_list=list(addresses), fail_silently=True, html_message=html))
    except Exception as exc:  # noqa: BLE001 - a mail problem must not 500 the request
        logger.warning('[Audit] report email not sent for audit %s: %s', audit.pk, exc)
        return False


def maybe_alert_warm_lead(audit):
    """Call after a public open has been counted (audit.opens is current)."""
    threshold = int(getattr(settings, 'AUDIT_WARM_LEAD_OPENS', 5))
    if threshold <= 0 or audit.source != 'landing' or audit.is_claimed or audit.opens != threshold:
        return False
    body = (
        f"Warm lead: the public report for {audit.host} has been opened {audit.opens} times and is still unclaimed.\n\n"
        f"Brand: {audit.brand_name or audit.host}\nGEO score: {audit.geo_score}\n"
        f"Visitor email: {audit.requester_email or 'no email left'}\n\n"
        f"Leads table: {_app_url(audit)}\nPublic report: {_public_url(audit)}"
    )
    return _send(f'Warm audit lead: {audit.host} opened {audit.opens}×', body)


def alert_claimed(audit, domain, user):
    body = (
        f"The audit of {audit.host} was claimed and is now the project '{domain.name}'.\n\n"
        f"Claimed by: {getattr(user, 'email', '')}\n"
        f"Organisation: {getattr(getattr(user, 'organisation', None), 'name', '')}\n"
        f"Source: {audit.source}\nGEO score: {audit.geo_score}\n\n"
        f"Audit: {_app_url(audit)}"
    )
    return _send(f'Audit claimed: {audit.host} → {domain.name}', body)
