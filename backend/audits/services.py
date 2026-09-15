"""Audit Engine — the rules behind the endpoints.

Kept out of views.py so the guards (feature flag, repeat window, per-IP and
global daily caps) and the two state changes that matter (dispatch to the
engine, claim into a Domain) can be unit-tested without HTTP and reused by a
management command or the landing site later.

The backend never runs an audit itself: it writes the row and POSTs the id to
the engine, which queues run_audit_task — the same hand-off shape as backlink
snapshots. If the engine cannot be reached the row is failed immediately so
the UI never waits on work nothing will pick up.
"""
import logging
import re
from datetime import timedelta

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Audit

logger = logging.getLogger(__name__)

ENGINE_TIMEOUT = 10  # seconds; the engine only queues, it does not run

_HOST_RE = re.compile(r'^(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$')


class AuditRefused(Exception):
    """A request that must not create an audit. `status` is the HTTP code."""

    def __init__(self, message, status=400, **extra):
        super().__init__(message)
        self.message = message
        self.status = status
        self.extra = extra


def enabled():
    return bool(getattr(settings, 'AUDIT_ENGINE_ENABLED', False))


def normalize_host(value):
    """'HTTPS://www.HDFCBank.com/x?y' -> 'hdfcbank.com'; '' when not a hostname."""
    host = (value or '').strip().lower()
    host = re.sub(r'^[a-z]+://', '', host)
    host = host.split('/')[0].split('?')[0].split('#')[0].split('@')[-1].split(':')[0]
    if host.startswith('www.'):
        host = host[4:]
    host = host.strip('.')
    return host if _HOST_RE.match(host) else ''


def client_ip(request):
    """First hop of X-Forwarded-For (nginx fronts gunicorn), else REMOTE_ADDR."""
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip() or None
    return request.META.get('REMOTE_ADDR') or None


def recent_audit_for(host, hours=None, country=None):
    """A non-failed audit of `host` inside the repeat window, newest first.

    The window is per host *and* market: an audit of a site for India says
    nothing about how the engines answer US buyers (different prompts, rivals
    and citations), so a request for another country is a new audit, not a
    repeat. `country=None` keeps the old host-only lookup for callers that
    only need "was this site audited recently".
    """
    if hours is None:
        hours = int(getattr(settings, 'AUDIT_REPEAT_HOURS', 24))
    if hours <= 0:
        return None
    since = timezone.now() - timedelta(hours=hours)
    qs = Audit.objects.filter(host=host, created_at__gte=since)
    if country:
        qs = qs.filter(country=country)
    return qs.exclude(status='FAIL').order_by('-created_at').first()


def _check_caps(ip, privileged):
    since = timezone.now() - timedelta(days=1)
    today = Audit.objects.filter(created_at__gte=since)
    global_cap = int(getattr(settings, 'AUDIT_GLOBAL_DAILY', 50))
    if global_cap > 0 and today.count() >= global_cap:
        raise AuditRefused('The audit engine has reached its daily limit. Try again tomorrow.', status=429)
    if privileged:
        return
    ip_cap = int(getattr(settings, 'AUDIT_PER_IP_DAILY', 3))
    if ip and ip_cap > 0 and today.filter(requester_ip=ip).count() >= ip_cap:
        raise AuditRefused('You have run the maximum number of audits for today.', status=429)


def create_audit(url, *, country='us', user=None, email='', ip=None, source=None, force=False, via_api_key=False):
    """Validate, guard, create the row and dispatch it. Returns (audit, reused).

    `reused` is True when a recent audit of the same host was returned instead
    of spending money on a duplicate; privileged callers can pass force=True
    to run a fresh one anyway.
    """
    if not enabled():
        raise AuditRefused('The audit engine is not available right now.', status=503)

    host = normalize_host(url)
    if not host:
        raise AuditRefused('Enter a valid website address, e.g. example.com.')

    country = (country or 'us').strip().lower()[:2] or 'us'
    email = (email or '').strip()[:254]
    privileged = bool(user is not None and getattr(user, 'is_authenticated', False)
                      and getattr(user, 'role', '') in ('admin', 'super_admin'))
    if via_api_key:
        # A service key is an organisation's own credential: it is trusted like
        # an admin (no per-IP cap, may force), and the audit is filed under
        # the key's service account so the org's leads table shows it.
        privileged = True
    if source is None:
        source = 'api' if via_api_key else 'manual' if privileged else 'landing'

    if not (force and privileged):
        existing = recent_audit_for(host, country=country)
        if existing is not None:
            return existing, True

    _check_caps(ip, privileged)

    audit = Audit.objects.create(
        host=host,
        website=f'https://{host}',
        country=country,
        source=source,
        requested_by=user if (user is not None and getattr(user, 'is_authenticated', False)) else None,
        requester_email=email,
        requester_ip=ip,
    )
    dispatch(audit)
    return audit, False


def dispatch(audit):
    """Hand the audit to the engine's worker. Fails the row if the engine is down."""
    engine_url = getattr(settings, 'ENGINE_API_URL', 'http://localhost:8001').rstrip('/')
    try:
        resp = requests.post(
            f'{engine_url}/api/audits/run/', json={'audit_id': audit.pk}, timeout=ENGINE_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error('[Audit] engine dispatch failed for audit %s: %s', audit.pk, exc)
        audit.mark_failed(f'Could not reach the processing engine: {exc}')
        return False
    return True


def rerun(audit):
    """Resume a failed audit (the engine skips stages whose output is stored)."""
    if not enabled():
        raise AuditRefused('The audit engine is not available right now.', status=503)
    stale = audit.status == 'PROC' and audit.modified_at < timezone.now() - timedelta(minutes=30)
    if audit.status != 'FAIL' and not stale:
        raise AuditRefused('Only failed or stalled audits can be re-run.')
    audit.status = 'PROC'
    audit.error = ''
    audit.completed_at = None
    audit.save(update_fields=['status', 'error', 'completed_at', 'modified_at'])
    return dispatch(audit)


COUNTRY_NAMES = {
    'us': 'United States', 'gb': 'United Kingdom', 'ca': 'Canada',
    'au': 'Australia', 'de': 'Germany', 'fr': 'France', 'es': 'Spain',
    'it': 'Italy', 'jp': 'Japan', 'in': 'India', 'br': 'Brazil',
    'mx': 'Mexico', 'nl': 'Netherlands', 'se': 'Sweden', 'no': 'Norway',
    'dk': 'Denmark', 'fi': 'Finland', 'pl': 'Poland', 'be': 'Belgium',
    'at': 'Austria', 'ch': 'Switzerland', 'ie': 'Ireland',
    'nz': 'New Zealand', 'sg': 'Singapore', 'ae': 'United Arab Emirates',
}


def seed_prompts_from_audit(audit, domain):
    """Create the domain's prompt groups from the audit's prompts (Day 0).

    One group per audit topic, named like the generation wizard names them
    (title-cased topic, suffixed on collision); the first prompt in a group is
    its primary. Groups start in INIT so the engine's scheduler picks them up
    exactly as it does for prompts added by hand. Returns counts.
    """
    from prompts.models import Prompt, PromptGroup

    prompts = (audit.grounding or {}).get('prompts') or []
    by_topic = {}
    for p in prompts:
        text = (p.get('text') or '').strip()
        if not text:
            continue
        by_topic.setdefault((p.get('topic') or 'Audit prompts').strip(), []).append(text)

    groups = created = 0
    for topic, texts in by_topic.items():
        title = ' '.join(w.capitalize() if w.islower() else w for w in topic.split())[:90] or 'Audit prompts'
        name, n = title[:100], 2
        while PromptGroup.objects.filter(group_id=name, domain=domain).exists():
            name = f"{title} ({n})"[:100]
            n += 1
        group = PromptGroup.objects.create(group_id=name, domain=domain, track_status='INIT',
                                           track_message=f'Seeded from audit #{audit.pk}')
        groups += 1
        for i, text in enumerate(texts):
            if Prompt.objects.filter(prompt=text, group=group).exists():
                continue
            Prompt.objects.create(prompt=text, group=group, type='primary' if i == 0 else 'secondary', track_status='INIT')
            created += 1
    return {'groups': groups, 'prompts': created}


def claim(audit, user):
    """Turn a finished audit into a tracked Domain in the user's organisation.

    Mirrors domains.views.create_analyzed_domain: no LLM work here — the
    profile the audit already extracted becomes the brand record, keyword
    seeding runs behind the response, and the audit is linked back as the
    Day-0 baseline (which also stops its public link from expiring).
    """
    from domains.models import Domain, DomainAccess
    from domains.views import domain_already_tracked

    if audit.status != 'DONE':
        raise AuditRefused('Only a finished audit can be claimed.')
    if audit.is_claimed:
        raise AuditRefused('This audit has already been claimed.', domain_id=audit.claimed_domain_id)
    organisation = getattr(user, 'organisation', None)
    if organisation is None:
        raise AuditRefused('Your account has no organisation to add the brand to.', status=403)

    profile = (audit.grounding or {}).get('profile') or {}
    competitors = [c.get('name') for c in (audit.competitors or []) if c.get('name')]

    with transaction.atomic():
        existing = domain_already_tracked(organisation, audit.website)
        if existing:
            raise AuditRefused(
                f"This domain is already tracked as '{existing.name}'.", domain_id=existing.pk,
            )
        domain = Domain.objects.create(
            name=audit.brand_name or audit.host,
            url=audit.website,
            organisation=organisation,
            country=COUNTRY_NAMES.get(audit.country, 'United States'),
            processing_status='COMP',
            short_description=(profile.get('description') or '')[:500] or None,
            target_audience=profile.get('audience') or None,
            offering_categories=list(profile.get('categories') or []) or None,
            regions_served=list(profile.get('regions') or []) or None,
            use_cases=list(profile.get('use_cases') or []) or None,
            buying_criteria=list(profile.get('buying_criteria') or []) or None,
            key_competitors=', '.join(competitors) or None,
        )
        try:
            DomainAccess.objects.create(domain=domain, user=user, granted_by=user)
        except Exception as exc:  # noqa: BLE001 - access row is a convenience
            logger.error('[Audit] could not create domain access for %s: %s', domain.pk, exc)

        audit.claimed_at = timezone.now()
        audit.claimed_by = user
        audit.claimed_domain = domain
        audit.expires_at = None
        audit.save(update_fields=['claimed_at', 'claimed_by', 'claimed_domain', 'expires_at', 'modified_at'])

        if getattr(settings, 'AUDIT_CLAIM_SEEDS_PROMPTS', True):
            try:
                seeded = seed_prompts_from_audit(audit, domain)
                logger.info('[Audit] claim of audit %s seeded %s groups / %s prompts on domain %s',
                            audit.pk, seeded['groups'], seeded['prompts'], domain.pk)
            except Exception as exc:  # noqa: BLE001 - a project without prompts is recoverable
                logger.error('[Audit] could not seed prompts for domain %s from audit %s: %s', domain.pk, audit.pk, exc)

    try:
        from domains.keyword_seeder import seed_keywords_in_background
        seed_keywords_in_background(domain.id)
    except Exception as exc:  # noqa: BLE001 - a brand without keywords is recoverable
        logger.error('[Audit] could not start keyword seeding for domain %s: %s', domain.pk, exc)
    try:
        from .notifications import alert_claimed
        alert_claimed(audit, domain, user)
    except Exception as exc:  # noqa: BLE001 - never let mail break a claim
        logger.warning('[Audit] claim alert failed for audit %s: %s', audit.pk, exc)
    return domain
