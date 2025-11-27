"""
Helper functions for Google OAuth credentials.
This module provides engine-specific implementations that don't depend on backend models.
"""
from google.oauth2.credentials import Credentials

# Google OAuth scopes
SCOPES = [
    'https://www.googleapis.com/auth/analytics.readonly',  # GA4 Data API
    'https://www.googleapis.com/auth/webmasters.readonly',  # Search Console
]


def get_credentials_from_integration(integration):
    """Convert stored credentials back to Google Credentials object."""
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
    )

    return credentials

