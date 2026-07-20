"""
Helper functions for Google OAuth credentials.
This module provides engine-specific implementations that don't depend on backend models.
"""
import logging
from datetime import datetime, timezone as dt_timezone

from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

# Google OAuth scopes
SCOPES = [
    'https://www.googleapis.com/auth/analytics.readonly',  # GA4 Data API
    'https://www.googleapis.com/auth/webmasters.readonly',  # Search Console
]


def parse_stored_expiry(raw_expiry):
    """Parse the stored ISO expiry into the naive-UTC datetime google-auth expects.

    The expiry was always written to the credentials JSON but never read back, so
    google-auth saw expiry=None and considered the token valid forever - it never
    refreshed proactively and instead let calls fail.

    Returns None when absent or unparseable, which preserves that old behaviour
    rather than guessing.
    """
    if not raw_expiry:
        return None
    try:
        expiry = datetime.fromisoformat(raw_expiry)
    except (TypeError, ValueError):
        logger.warning(f"Unparseable stored token expiry: {raw_expiry!r}")
        return None
    # google-auth compares expiry against utcnow(), so it must be naive UTC.
    if expiry.tzinfo is not None:
        expiry = expiry.astimezone(dt_timezone.utc).replace(tzinfo=None)
    return expiry


def persist_refreshed_credentials(integration, credentials):
    """Write a newly refreshed access token back onto the integration.

    Without this the refreshed token is discarded when the process ends, so a
    fresh one is minted on every run and the stored token stays stale forever.
    The integration then survives only on its refresh token - and if a reconnect
    ever returns no new refresh token, auth dies with no path back.
    """
    try:
        creds_data = dict(integration.credentials or {})
        creds_data['token'] = credentials.token
        creds_data['expiry'] = credentials.expiry.isoformat() if credentials.expiry else None
        integration.credentials = creds_data
        integration.save(update_fields=['credentials'])
        logger.info(f"Refreshed and stored Google access token for integration {integration.id}")
    except Exception as e:
        # A failed write must not break the fetch - the in-memory credentials
        # are still usable for this run.
        logger.warning(f"Could not persist refreshed token for integration {integration.id}: {e}")


def get_credentials_from_integration(integration, persist=True):
    """Convert stored credentials back to Google Credentials object.

    Refreshes the access token when it has expired and, unless persist=False,
    stores the new token so later runs and other processes reuse it.
    """
    creds_data = integration.credentials
    if not creds_data:
        return None

    credentials = Credentials(
        token=creds_data.get('token'),
        refresh_token=creds_data.get('refresh_token'),
        token_uri=creds_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
        client_id=creds_data.get('client_id'),
        client_secret=creds_data.get('client_secret'),
        scopes=creds_data.get('scopes', SCOPES),
        expiry=parse_stored_expiry(creds_data.get('expiry')),
    )

    if persist and credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(GoogleAuthRequest())
            persist_refreshed_credentials(integration, credentials)
        except Exception as e:
            # Let the caller proceed and surface the real API error; a refresh
            # failure here usually means the grant was revoked.
            logger.warning(f"Token refresh failed for integration {integration.id}: {e}")

    return credentials
