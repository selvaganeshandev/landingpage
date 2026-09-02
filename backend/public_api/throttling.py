"""Per-credential rate limiting for the public /v1/ surface.

One bucket per service API key (falls back to the user id for JWT
callers). The limit lives in SERVICE_API_THROTTLE_RATE (default
120/min) so ops can tune it in .env without a deploy.

DRF answers an exceeded bucket with 429 + Retry-After on its own; the
views also emit X-RateLimit-Limit / -Remaining / -Reset on every
response, which is what Enque's proxy reads to pace itself.
"""
from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle


class ServiceKeyThrottle(SimpleRateThrottle):
    scope = 'service_api'

    def get_rate(self):
        return getattr(settings, 'SERVICE_API_THROTTLE_RATE', '120/min')

    def get_cache_key(self, request, view):
        auth = getattr(request, 'auth', None)
        if auth is not None and getattr(auth, 'pk', None) is not None:
            ident = f'key-{auth.pk}'
        elif request.user and request.user.is_authenticated:
            ident = f'user-{request.user.pk}'
        else:
            ident = self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': ident}

    def allow_request(self, request, view):
        allowed = super().allow_request(request, view)
        # Stash the bucket state so the view can emit rate headers.
        request.rate_limit = self.num_requests
        request.rate_remaining = max(0, self.num_requests - len(self.history)) if allowed else 0
        request.rate_reset_seconds = int(self.wait() or 0) if not allowed else int(self.duration)
        return allowed


def apply_rate_headers(request, response):
    """Copy the throttle bucket state onto the response, if a throttle ran."""
    limit = getattr(request, 'rate_limit', None)
    if limit is None:
        return response
    response['X-RateLimit-Limit'] = str(limit)
    response['X-RateLimit-Remaining'] = str(getattr(request, 'rate_remaining', 0))
    response['X-RateLimit-Reset'] = str(getattr(request, 'rate_reset_seconds', 0))
    return response
