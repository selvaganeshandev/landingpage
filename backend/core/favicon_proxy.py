"""Favicon resolution that can actually tell a real icon from a placeholder.

Google's favicon service answers an unknown host with a generic globe rather
than an error: HTTP 200, a valid 16x16 PNG, byte-identical every time
(726 bytes, md5 b8a0bf37...). That makes the "did this work?" question
unanswerable in the browser:

  * `<img>` fires `load`, not `error`, because the body IS a decodable image,
    so an onError fallback chain never runs.
  * The status cannot be read either — neither google.com/s2 nor
    t*.gstatic.com sends access-control-allow-origin, so fetch() gets an
    opaque response and canvas is tainted.
  * Size is not a signal: www.racold.com's REAL icon is 16x16, the same
    dimensions as the placeholder.

And no fixed www/non-www rule works, because different domains need opposite
choices:

    menolabs.com   www -> placeholder   bare -> real
    racold.com     www -> real          bare -> placeholder

The shards also disagree with each other — t1 served menolabs' www variant as
a real icon while t3 served the placeholder for the same URL — so whichever
shard the browser happened to hit decided what the user saw.

Server-side none of that applies: bytes and status are both readable. This
resolves the candidates once, keeps the first that is not the placeholder, and
caches the answer so the shard lottery is played once per host rather than on
every page load.
"""

import hashlib
import logging
import re
from urllib.parse import quote

import requests
from django.core.cache import cache
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

logger = logging.getLogger(__name__)

# The generic globe Google returns for a host it has no icon for. Identical on
# t0-t3, so matching it is reliable; verified 2026-07-31.
PLACEHOLDER_MD5 = 'b8a0bf372c762e966cc99ede8682bc71'
PLACEHOLDER_BYTES = 726

FAVICON_ENDPOINT = 'https://t1.gstatic.com/faviconV2'
CACHE_TTL = 60 * 60 * 24 * 30  # 30 days — icons change rarely
CACHE_TTL_MISS = 60 * 60 * 24  # retry unknown hosts sooner, they may gain one

# Hostname, nothing else. The host is only ever interpolated into Google's
# `url` parameter — we never fetch the caller's host ourselves — but keeping
# this strict stops anything odd reaching the query string.
_HOST_RE = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?'
                      r'(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$')

# Suffixes where the registrable domain is three labels, not two, so
# example.co.uk is not mistaken for a subdomain that should skip its www try.
MULTI_PART_SUFFIXES = (
    'co.uk', 'org.uk', 'ac.uk', 'gov.uk',
    'com.au', 'net.au', 'org.au',
    'co.in', 'net.in', 'org.in', 'bank.in', 'gov.in', 'ac.in',
    'co.nz', 'co.za', 'co.jp', 'com.br', 'com.sg', 'com.my',
)


def _normalise_host(raw):
    """Bare hostname from a URL or host string, or None if it isn't one."""
    if not raw:
        return None
    host = str(raw).strip().lower()
    host = re.sub(r'^[a-z]+://', '', host)
    host = host.split('/')[0].split('?')[0].split('#')[0]
    host = host.split('@')[-1].split(':')[0].rstrip('.')
    return host if _HOST_RE.match(host) else None


def _is_registrable(host):
    """True when the host has no subdomain of its own (example.com, iob.bank.in)."""
    if re.match(r'^[0-9.]+$', host):
        return False
    suffix = next((s for s in MULTI_PART_SUFFIXES if host.endswith('.' + s)), None)
    labels = host.count('.') + 1
    return labels == 3 if suffix else labels == 2


def _candidates(host):
    """Hosts to try, best guess first.

    A subdomain is tried only as given: "www" in front of one is a host nobody
    publishes. A registrable domain is tried both ways because, as above, the
    right answer differs per domain and cannot be predicted.
    """
    if host.startswith('www.'):
        return [host, host[4:]]
    if _is_registrable(host):
        return [host, 'www.' + host]
    return [host]


def _fetch(host, size):
    """Return icon bytes for `host`, or None if Google only has the placeholder."""
    url = (f'{FAVICON_ENDPOINT}?client=SOCIAL&type=FAVICON'
           f'&fallback_opts=TYPE,SIZE,URL&size={size}&url=https://{quote(host)}')
    try:
        resp = requests.get(url, timeout=8)
    except requests.RequestException as exc:
        logger.debug('favicon fetch failed for %s: %s', host, exc)
        return None
    if resp.status_code != 200 or not resp.content:
        return None
    body = resp.content
    # Match on the digest rather than the length alone: a real icon could
    # coincidentally be 726 bytes, and the check is cheap.
    if len(body) == PLACEHOLDER_BYTES and hashlib.md5(body).hexdigest() == PLACEHOLDER_MD5:
        return None
    return body


# HEAD as well as GET: caches and proxies in front of this will probe with
# HEAD, and a 405 there makes them treat the icon as unavailable.
@api_view(['GET', 'HEAD'])
@permission_classes([AllowAny])
def favicon(request):
    """GET /favicon/?domain=<host>&size=32 -> the real icon, or 404.

    Unauthenticated by necessity: this is consumed by <img src>, which cannot
    carry an Authorization header. It exposes nothing — the only thing it can
    fetch is Google's favicon endpoint for a hostname the caller already knows.
    """
    host = _normalise_host(request.query_params.get('domain'))
    if not host:
        return HttpResponse(status=400)

    try:
        size = min(max(int(request.query_params.get('size', 32)), 16), 128)
    except (TypeError, ValueError):
        size = 32

    cache_key = f'favicon:v1:{host}:{size}'
    cached = cache.get(cache_key)
    if cached is not None:
        if cached == b'':  # negative result, cached so we stop re-asking
            return HttpResponse(status=404)
        return _image_response(cached)

    for candidate in _candidates(host):
        body = _fetch(candidate, size)
        if body:
            cache.set(cache_key, body, CACHE_TTL)
            return _image_response(body)

    cache.set(cache_key, b'', CACHE_TTL_MISS)
    return HttpResponse(status=404)


def _image_response(body):
    resp = HttpResponse(body, content_type='image/png')
    # Long browser cache: the answer only changes when a site changes its icon,
    # and the whole point is to stop paying for this lookup repeatedly.
    resp['Cache-Control'] = 'public, max-age=604800'
    return resp
