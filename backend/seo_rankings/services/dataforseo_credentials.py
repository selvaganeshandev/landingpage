"""
Where DataForSEO credentials come from.

Two sources, in order:

  1. The organisation's own credentials, set in Organization Settings → API Keys.
  2. The system-level pair in .env (DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD).

Same "leave it empty to use the system key" contract the LLM provider keys
already use, so an organisation that supplies its own account is billed on that
account, and everyone else falls back to ours.

Both halves must be present for an organisation's credentials to count — a
login with no password is a misconfiguration, and silently pairing it with the
system password would bill the wrong account.
"""
import logging
from typing import Optional, Tuple

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Free endpoint (cost 0.0) that returns the account's balance and rate limits.
# Doubles as credential validation: if it authenticates, the pair is good.
USER_DATA_URL = "https://api.dataforseo.com/v3/appendix/user_data"

PROBE_TIMEOUT = 20


def system_credentials() -> Tuple[str, str]:
    return (
        getattr(settings, "DATAFORSEO_LOGIN", None) or '',
        getattr(settings, "DATAFORSEO_PASSWORD", None) or '',
    )


def credentials_for(organisation) -> Tuple[str, str, str]:
    """Return (login, password, source) for an organisation.

    `source` is 'organisation' or 'system', so callers and the UI can say which
    account a spend will land on rather than leaving it ambiguous.
    """
    login = (getattr(organisation, 'dataforseo_login', '') or '').strip()
    password = getattr(organisation, 'dataforseo_password', '') or ''
    if login and password:
        return login, password, 'organisation'

    if login and not password:
        logger.warning(
            "Organisation %s has a DataForSEO login with no password — falling "
            "back to the system account.", getattr(organisation, 'id', '?'),
        )

    sys_login, sys_password = system_credentials()
    return sys_login, sys_password, 'system'


def probe(login: str, password: str) -> dict:
    """Validate a credential pair and read its balance. Never raises.

    Returns {'valid': bool, 'balance': float|None, 'login': str, 'error': str}.
    The call is free, so this can run on every save and on the settings page
    without adding to the bill.
    """
    if not login or not password:
        return {'valid': False, 'balance': None, 'login': login, 'error': 'Login and password are both required.'}

    try:
        resp = requests.get(USER_DATA_URL, auth=(login, password), timeout=PROBE_TIMEOUT)
    except requests.RequestException as exc:
        # A network problem is not a bad credential — say so rather than
        # telling the user their password is wrong.
        return {'valid': False, 'balance': None, 'login': login,
                'error': f'Could not reach DataForSEO: {exc}'}

    if resp.status_code == 401:
        return {'valid': False, 'balance': None, 'login': login,
                'error': 'DataForSEO rejected these credentials.'}

    try:
        body = resp.json()
    except ValueError:
        return {'valid': False, 'balance': None, 'login': login,
                'error': 'DataForSEO returned an unreadable response.'}

    if body.get('status_code') != 20000:
        return {'valid': False, 'balance': None, 'login': login,
                'error': body.get('status_message') or 'DataForSEO rejected the request.'}

    result = ((body.get('tasks') or [{}])[0].get('result') or [{}])[0]
    money = result.get('money') or {}
    return {
        'valid': True,
        'balance': money.get('balance'),
        'login': result.get('login') or login,
        'error': '',
    }
