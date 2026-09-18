"""Audit Engine emails sent by the worker when an audit is published.

Two messages, both best-effort and both silent no-ops when Mailgun is not
configured (MailgunEmailService already refuses cleanly without a key):

  * the requester's copy — "your audit is ready" with the public link, to the
    email the landing-page visitor left or the admin who ran it;
  * the lead alert — to AUDIT_LEAD_ALERT_EMAILS, only for landing-page audits,
    so the team hears about a new prospect the moment their report exists.

Nothing here may fail the audit: stage_publish wraps the call and records the
outcome in stage_detail['publish'] instead of raising.
"""
import logging
from typing import Dict, List, Optional

from django.conf import settings

logger = logging.getLogger(__name__)

GEO_LABELS = {'absent': 'Absent', 'present': 'Present', 'preferred': 'Preferred', 'default': 'Default'}


def public_url(audit) -> str:
    base = (getattr(settings, 'FRONTEND_URL', '') or 'http://localhost:8080').rstrip('/')
    return f'{base}/audit/{audit.public_token}'


def app_url(audit) -> str:
    base = (getattr(settings, 'FRONTEND_URL', '') or 'http://localhost:8080').rstrip('/')
    return f'{base}/audits/{audit.pk}'


def lead_alert_recipients() -> List[str]:
    raw = getattr(settings, 'AUDIT_LEAD_ALERT_EMAILS', '') or ''
    if isinstance(raw, (list, tuple)):
        return [str(r).strip() for r in raw if str(r).strip()]
    return [r.strip() for r in str(raw).split(',') if r.strip()]


def requester_address(audit) -> Optional[str]:
    if audit.requester_email:
        return audit.requester_email
    user = getattr(audit, 'requested_by', None)
    return getattr(user, 'email', None) or None


def _headline(audit) -> str:
    stage = GEO_LABELS.get(audit.geo_stage or '', 'unscored')
    return (
        f"GEO score {audit.geo_score if audit.geo_score is not None else '—'} · {stage} · "
        f"mentioned on {audit.appearances} of {audit.total_runs} answers, cited on {audit.cited_runs}"
    )


def _ready_email(audit) -> Dict[str, str]:
    brand = audit.brand_name or audit.host
    link = public_url(audit)
    text = (
        f"Your AI visibility audit of {brand} is ready.\n\n"
        f"{_headline(audit)}\n\n"
        f"Open the report: {link}\n\n"
        "The link works without a login and stays live for "
        f"{int(getattr(settings, 'AUDIT_PUBLIC_TTL_DAYS', 30))} days. Claim the audit from the report "
        "to keep it as the Day-0 baseline of a project.\n\n— PromptMaxx"
    )
    html = (
        f"<p>Your AI visibility audit of <strong>{brand}</strong> is ready.</p>"
        f"<p>{_headline(audit)}</p>"
        f'<p><a href="{link}">Open the report</a></p>'
        f"<p style='color:#6b7280;font-size:13px'>The link works without a login and stays live for "
        f"{int(getattr(settings, 'AUDIT_PUBLIC_TTL_DAYS', 30))} days. Claim the audit from the report to keep it "
        "as the Day-0 baseline of a project.</p><p>— PromptMaxx</p>"
    )
    return {'subject': f'Your AI visibility audit of {brand} is ready', 'text': text, 'html': html}


def _lead_email(audit) -> Dict[str, str]:
    brand = audit.brand_name or audit.host
    who = audit.requester_email or 'no email left'
    text = (
        f"New audit lead from the landing page: {audit.host}\n\n"
        f"Brand: {brand}\nIndustry: {audit.industry or '—'}\n{_headline(audit)}\nVisitor email: {who}\n\n"
        f"Leads table: {app_url(audit)}\nPublic report: {public_url(audit)}"
    )
    return {'subject': f'New audit lead: {audit.host} (GEO {audit.geo_score})', 'text': text, 'html': ''}


def notify_audit_published(audit) -> Dict[str, bool]:
    """Send what publication warrants. Returns what actually went out.

    The report email to the requester is gated by AUDIT_AUTO_EMAIL_ON_PUBLISH
    (off by default): audits run from inside the app are emailed on demand with
    the "Email report" button instead. Turn the flag on for the landing-page
    funnel, where the email is how a visitor receives the audit they asked for.
    Team lead alerts are unaffected — they are already opt-in through
    AUDIT_LEAD_ALERT_EMAILS.
    """
    from core.mailgun_email_service import MailgunEmailService

    outcome = {'emailed': False, 'alerted': False}
    auto_email = bool(getattr(settings, 'AUDIT_AUTO_EMAIL_ON_PUBLISH', False))
    recipients_configured = lead_alert_recipients()
    if not auto_email and not recipients_configured:
        return outcome
    try:
        service = MailgunEmailService()
    except Exception as exc:  # noqa: BLE001
        logger.warning('[Audit] email service unavailable: %s', exc)
        return outcome

    to = requester_address(audit) if auto_email else None
    if to:
        msg = _ready_email(audit)
        res = service.send_report_email([to], msg['subject'], msg['text'], body_html=msg['html'] or None)
        outcome['emailed'] = bool(res.get('success'))
        if not outcome['emailed']:
            logger.info('[Audit] ready email not sent for audit %s: %s', audit.pk, res.get('message'))

    recipients = lead_alert_recipients()
    if recipients and audit.source == 'landing':
        msg = _lead_email(audit)
        res = service.send_report_email(recipients, msg['subject'], msg['text'])
        outcome['alerted'] = bool(res.get('success'))
        if not outcome['alerted']:
            logger.info('[Audit] lead alert not sent for audit %s: %s', audit.pk, res.get('message'))
    return outcome
