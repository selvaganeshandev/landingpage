"""JWT authentication that also enforces account lifecycle status.

A signed JWT stays cryptographically valid until it expires (8h access / 30d
refresh). Suspending or disabling an account must lock it out on the *next*
request, not whenever the token happens to expire — so every authenticated
request re-checks ``account_status`` against the live user row.
"""

from __future__ import annotations

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed


class StatusCheckingJWTAuthentication(JWTAuthentication):
    """JWTAuthentication that rejects tokens for non-active accounts.

    DRF already loads the user row to build ``request.user``, so the status check
    reads a field that is normally already in memory — no extra query.
    """

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if getattr(user, "account_status", "active") != "active":
            raise AuthenticationFailed(
                "Account is suspended or disabled.",
                code="account_inactive",
            )
        return user
