"""
Web Crawler Service
Validates URLs via direct HTTP requests (no third-party scraping API needed).
Replaces the former ScrapingDog integration.
"""
import ipaddress
import logging
import socket
import time
from typing import Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Realistic browser User-Agent so most sites don't block HEAD/GET checks.
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_DEFAULT_HEADERS = {
    "User-Agent": _USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# ---------------------------------------------------------------------------
# SSRF guard
# ---------------------------------------------------------------------------
# The crawler fetches citation URLs that ultimately come from LLM output, so a
# crafted prompt (or a redirect on a legitimate URL) could point it at internal
# infrastructure — cloud metadata (169.254.169.254), localhost admin panels, the
# database host, private RFC1918 ranges. The old ScrapingDog integration fetched
# from a third-party network so this was impossible; direct server-side fetches
# reintroduce it. Every URL — including each redirect hop — is validated here
# before any connection is opened.
_ALLOWED_SCHEMES = {"http", "https"}
_MAX_REDIRECTS = 5
_DEFAULT_MAX_CONTENT_BYTES = 5 * 1024 * 1024  # 5 MB cap on a fetched body


class _UnsafeUrlError(requests.RequestException):
    """Raised when a URL (or a redirect target) resolves to a non-public host.

    Subclasses requests.RequestException so it flows through the crawler's
    existing except-chain, but callers catch it FIRST to distinguish a blocked
    target from an ordinary network failure.
    """


def _resolves_to_internal_ip(hostname: str) -> bool:
    """True only if ``hostname`` resolves and ANY resolved IP is internal.

    Internal = loopback, private (RFC1918), link-local (incl. the
    169.254.169.254 cloud-metadata address), reserved, multicast, or
    unspecified, for both IPv4 and IPv6.

    A host that CANNOT be resolved returns False here — a dead/nonexistent host
    is not an SSRF target (there is nothing internal to reach), so the request
    is allowed to proceed and fail naturally as a *broken* URL. Blocking it
    would mislabel every hallucinated/dead citation link as "blocked". An
    unparseable resolved address returns True (block) to fail safe.
    """
    try:
        infos = socket.getaddrinfo(hostname, None)
    except (socket.gaierror, UnicodeError, OSError):
        return False  # can't resolve → nothing internal to hit → not a block
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return True
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return True
    return False


def is_safe_url(url: str) -> bool:
    """SSRF guard: allow only http(s) URLs that do not resolve to an internal IP.

    A dead host (no DNS record) is considered safe to *attempt* — the connection
    simply fails and the caller records a broken URL. Only a host that resolves
    to private/internal space is blocked.

    Note: this resolves DNS to inspect the target IP. A determined attacker who
    controls DNS could still rebind between this check and the request the
    stdlib makes when connecting (TOCTOU). That is a much higher bar than the
    hole this closes (LLM-supplied internal URLs and redirects to them); pin the
    connection to the validated IP if that threat is in scope.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        return False
    host = parsed.hostname
    if not host:
        return False
    return not _resolves_to_internal_ip(host)


class WebCrawler:
    """
    Web crawler using direct HTTP requests.
    Validates whether a URL is reachable (valid, broken, blocked).
    """

    DEFAULT_TIMEOUT = 15        # seconds per request
    DEFAULT_MAX_RETRIES = 2
    DEFAULT_RATE_LIMIT = 60     # requests per minute

    def __init__(
        self,
        timeout: int = None,
        max_retries: int = None,
        rate_limit: int = None,
        use_dynamic: bool = False   # kept for API compatibility, unused
    ):
        self.timeout = timeout or getattr(
            settings, 'MISINFO_CRAWL_TIMEOUT', self.DEFAULT_TIMEOUT
        )
        self.max_retries = max_retries or getattr(
            settings, 'MISINFO_CRAWL_MAX_RETRIES', self.DEFAULT_MAX_RETRIES
        )
        self.rate_limit = rate_limit or getattr(
            settings, 'MISINFO_CRAWL_RATE_LIMIT', self.DEFAULT_RATE_LIMIT
        )
        self.max_content_bytes = getattr(
            settings, 'MISINFO_CRAWL_MAX_BYTES', _DEFAULT_MAX_CONTENT_BYTES
        )

        self._last_request_time = 0
        self.session = requests.Session()
        self.session.headers.update(_DEFAULT_HEADERS)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _rate_limit_wait(self):
        if self.rate_limit <= 0:
            return
        min_interval = 60.0 / self.rate_limit
        elapsed = time.time() - self._last_request_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_request_time = time.time()

    def _classify_status(self, status_code: int) -> Tuple[Optional[str], Optional[str]]:
        """
        Return (crawl_status_hint, error_message) from an HTTP status code.
        crawl_status_hint: 'success', 'failed', 'blocked', or None (caller decides).
        """
        if status_code == 0:
            return 'failed', 'Connection failed or timeout'
        if status_code == 200:
            return 'success', None
        if status_code == 403:
            return 'blocked', 'Access forbidden (403)'
        if status_code == 404:
            return 'failed', 'Page not found (404)'
        if status_code == 410:
            return 'failed', 'Page gone (410)'
        if status_code >= 500:
            return 'failed', f'Server error ({status_code})'
        if status_code >= 400:
            return 'failed', f'HTTP {status_code}'
        return 'success', None

    def _guarded_request(self, method: str, url: str, stream: bool = False) -> requests.Response:
        """Issue an HTTP request, validating the URL and every redirect hop.

        Redirects are followed manually (``allow_redirects=False``) so each hop
        is re-checked by the SSRF guard — otherwise a public URL could redirect
        into private space. Raises ``_UnsafeUrlError`` if any hop is unsafe or
        the redirect chain is too long. The returned response is NOT consumed;
        the caller reads or closes it.
        """
        current = url
        for _ in range(_MAX_REDIRECTS + 1):
            if not is_safe_url(current):
                raise _UnsafeUrlError(f"blocked non-public URL: {current}")
            resp = self.session.request(
                method,
                current,
                timeout=self.timeout,
                allow_redirects=False,
                stream=stream,
            )
            if resp.is_redirect or resp.is_permanent_redirect:
                location = resp.headers.get("Location")
                resp.close()
                if not location:
                    return resp
                current = urljoin(current, location)
                continue
            return resp
        raise _UnsafeUrlError(f"too many redirects: {url}")

    def _read_capped(self, resp: requests.Response) -> str:
        """Read a response body up to ``self.max_content_bytes``, then decode.

        Streams so a hostile or oversized page cannot exhaust memory.
        """
        chunks = []
        total = 0
        try:
            for chunk in resp.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                chunks.append(chunk)
                total += len(chunk)
                if total >= self.max_content_bytes:
                    logger.warning(
                        f"Body exceeded {self.max_content_bytes} bytes; truncating: {resp.url}"
                    )
                    break
        finally:
            resp.close()
        encoding = resp.encoding or 'utf-8'
        try:
            return b"".join(chunks).decode(encoding, errors='replace')
        except (LookupError, TypeError):
            return b"".join(chunks).decode('utf-8', errors='replace')

    # ------------------------------------------------------------------
    # Public API (same signature as old ScrapingDog-based crawler)
    # ------------------------------------------------------------------

    def crawl(self, url: str, dynamic: bool = None) -> Tuple[Optional[str], int, Optional[str]]:
        """
        Validate a URL and optionally fetch its HTML content.

        Strategy:
          1. Try a HEAD request first (fast, saves bandwidth).
          2. If the site returns 405 Method Not Allowed, fall back to GET.
          3. On success (2xx), do a GET to fetch page content.

        Returns:
            Tuple of (html_content, http_status_code, error_message)
            - html_content: Page HTML or None
            - http_status_code: Final HTTP status code, or 0 on connection failure
            - error_message: Error string or None on success
        """
        # ---- SSRF guard: reject non-public targets before any network call ----
        if not is_safe_url(url):
            logger.warning(f"Blocked unsafe crawl target (SSRF guard): {url}")
            return None, 0, "Blocked: URL is not a public http(s) address"

        for attempt in range(self.max_retries):
            try:
                self._rate_limit_wait()

                # ---- Step 1: HEAD to check if URL is alive ----
                try:
                    head_resp = self._guarded_request("HEAD", url)
                    status_code = head_resp.status_code
                    head_resp.close()
                except _UnsafeUrlError as e:
                    logger.warning(f"Blocked unsafe redirect crawling {url}: {e}")
                    return None, 0, "Blocked: redirect to a non-public address"
                except requests.RequestException:
                    status_code = 405  # treat as "HEAD not supported"

                # ---- Step 2: Fall back to GET if HEAD not supported ----
                if status_code == 405:
                    try:
                        get_resp = self._guarded_request("GET", url, stream=True)
                        status_code = get_resp.status_code
                        get_resp.close()  # only the status is needed here
                    except _UnsafeUrlError as e:
                        logger.warning(f"Blocked unsafe redirect crawling {url}: {e}")
                        return None, 0, "Blocked: redirect to a non-public address"

                # ---- Step 3: Non-2xx → classify and return without body ----
                if status_code != 200:
                    hint, error = self._classify_status(status_code)
                    logger.info(f"URL check [{status_code}]: {url}")
                    return None, status_code, error

                # ---- Step 4: Fetch body (size-capped) for content comparison ----
                logger.info(f"Fetching content: {url}")
                try:
                    get_resp = self._guarded_request("GET", url, stream=True)
                except _UnsafeUrlError as e:
                    logger.warning(f"Blocked unsafe redirect crawling {url}: {e}")
                    return None, 0, "Blocked: redirect to a non-public address"
                html = self._read_capped(get_resp)
                return html, 200, None

            except requests.Timeout:
                logger.warning(f"Timeout crawling {url} (attempt {attempt + 1})")
                if attempt < self.max_retries - 1:
                    continue
                return None, 0, "Connection timeout"

            except requests.ConnectionError as e:
                logger.error(f"Connection error crawling {url}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None, 0, "Connection failed"

            except Exception as e:
                logger.error(f"Unexpected error crawling {url}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None, 0, str(e)

        return None, 0, "Max retries exceeded"

    def crawl_dynamic(self, url: str) -> Tuple[Optional[str], int, Optional[str]]:
        """Alias kept for API compatibility."""
        return self.crawl(url)

    def is_crawlable(self, url: str) -> bool:
        """Quick HEAD-based reachability check (SSRF-guarded)."""
        if not is_safe_url(url):
            logger.debug(f"URL {url} blocked by SSRF guard")
            return False
        try:
            self._rate_limit_wait()
            resp = self._guarded_request("HEAD", url)
            code = resp.status_code
            resp.close()
            return code < 400
        except Exception as e:
            logger.debug(f"URL {url} not crawlable: {e}")
            return False

    def get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            return urlparse(url).netloc
        except Exception:
            return ''
