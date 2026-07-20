"""
Reconnect helpers for Google integrations.

Pure logic (no Django imports) so it can be unit-tested without a database.
"""


def preserved_provider_id(existing_provider_id, available, fetch_succeeded=True):
    """Decide whether a previously selected GA property / GSC site survives a reconnect.

    The OAuth callback writes its defaults on UPDATE as well as CREATE, so
    writing an empty provider_id unconditionally silently clears the user's
    selection every time they press "Connect" again on an already-connected
    domain. Both the hourly INIT scheduler and the daily rolling refresh skip
    any integration whose provider_id is empty, so tracking stops until somebody
    notices and re-picks the site.

    Keeping it blindly is also wrong: reconnecting with a DIFFERENT Google
    account must not leave a stale id pointing at a property the new token
    cannot read.

    Args:
        existing_provider_id: provider_id currently stored, or '' / None.
        available: list of {'id': ..., 'display_name': ...} dicts just fetched
            from Google, or None when the list could not be fetched.
        fetch_succeeded: False when the API call errored. On failure the
            selection is preserved rather than destroyed — a transient outage
            must not wipe configuration. The caller has already marked the
            integration disconnected with an error message, so the problem is
            still surfaced.

    Returns:
        The provider_id to persist: the existing one when it is still valid,
        otherwise '' (meaning "user must select").
    """
    if not existing_provider_id:
        return ''

    # Could not verify — keep what we have rather than destroy it.
    if not fetch_succeeded or available is None:
        return existing_provider_id

    for item in available:
        if isinstance(item, dict) and item.get('id') == existing_provider_id:
            return existing_provider_id

    # Verified against a real list and the selection is gone (account switched
    # or access revoked) — force a re-selection.
    return ''
