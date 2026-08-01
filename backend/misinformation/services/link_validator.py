"""
Link Validator Service
Validates URLs and checks for broken links.

Two-tier by design: a free HEAD request decides the common cases, and only the
verdicts a bot User-Agent cannot be trusted on are escalated to the DataBlue
scraper. See `datablue_scrape` for why those specific codes are the ones that
need a second opinion.
"""
import logging
from typing import Tuple, Optional

import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

from . import datablue_scrape

logger = logging.getLogger(__name__)


class LinkValidator:
    """
    Validates links and detects broken URLs.
    Uses HEAD requests for efficiency, with a scraper fallback for the codes a
    HEAD request cannot settle on its own.
    """

    DEFAULT_TIMEOUT = 5  # Reduced from 10 for faster scanning

    # Status codes that indicate a broken link.
    #
    # 403 and 429 deliberately are NOT here any more. They used to be, and they
    # are why bot-guarded sites (Cloudflare) and rate-limited hosts were being
    # recorded as broken links — 1,299 rows between them. Both now route to
    # INCONCLUSIVE_STATUS_CODES instead.
    BROKEN_STATUS_CODES = {
        400, 401, 404, 405, 410,
        500, 501, 502, 503, 504
    }

    # Codes where the origin is telling us about *our request*, not about the
    # page. A real browser usually gets through, so these escalate to DataBlue
    # rather than resolving here.
    INCONCLUSIVE_STATUS_CODES = {403, 429}

    # Status codes that need full GET to verify
    UNCERTAIN_STATUS_CODES = {405}  # Some servers don't allow HEAD

    def __init__(self, timeout: int = None):
        """
        Initialize the link validator.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; LinkValidator/1.0; +http://example.com/bot)',
            'Accept': '*/*',
        })

    def validate(self, url: str) -> Tuple[bool, int, Optional[str]]:
        """
        Validate a URL and check if it's accessible.

        Args:
            url: The URL to validate

        Returns:
            Tuple of (is_valid, http_status_code, error_message)
            - is_valid: True if link is working
            - http_status_code: HTTP status code or 0 if connection failed
            - error_message: Error message or None if valid
        """
        try:
            # First try HEAD request (more efficient)
            response = self.session.head(
                url,
                timeout=self.timeout,
                allow_redirects=True
            )

            status_code = response.status_code

            # Check if HEAD is not allowed, try GET
            if status_code in self.UNCERTAIN_STATUS_CODES:
                response = self.session.get(
                    url,
                    timeout=self.timeout,
                    allow_redirects=True,
                    stream=True  # Don't download body
                )
                status_code = response.status_code
                response.close()

            # Any 2xx/3xx is the origin serving us something. 202 in particular
            # used to fall through to the catch-all below and be recorded as
            # broken (95 rows) despite being a success code.
            if 200 <= status_code < 400:
                return True, status_code, None

            elif status_code in self.INCONCLUSIVE_STATUS_CODES:
                # We were turned away, not told the page is gone. Ask DataBlue.
                return self._escalate(
                    url,
                    fallback=(False, status_code, self._get_error_message(status_code)),
                    reason=f"HTTP {status_code}",
                )

            elif status_code in self.BROKEN_STATUS_CODES:
                error_msg = self._get_error_message(status_code)
                return False, status_code, error_msg

            else:
                return False, status_code, f"HTTP {status_code}"

        except Timeout:
            logger.warning(f"Timeout validating {url}")
            return self._escalate(url, fallback=(False, 0, "Connection timeout"), reason="timeout")

        except ConnectionError as e:
            logger.warning(f"Connection error for {url}: {e}")
            return self._escalate(url, fallback=(False, 0, "Connection failed"), reason="connection error")

        except RequestException as e:
            logger.error(f"Request error validating {url}: {e}")
            return False, 0, str(e)

        except Exception as e:
            logger.error(f"Unexpected error validating {url}: {e}")
            return False, 0, str(e)

    def _escalate(
        self,
        url: str,
        fallback: Tuple[bool, int, Optional[str]],
        reason: str,
    ) -> Tuple[bool, int, Optional[str]]:
        """Get a second opinion from DataBlue, keeping `fallback` if it can't help.

        `fallback` is what this method would have returned before the scraper
        existed. Preserving it on every inconclusive path is what makes turning
        the fallback off — or running without a valid key — a no-op rather than a
        behaviour change.
        """
        if not datablue_scrape.is_enabled():
            return fallback

        verdict, status_code, error = datablue_scrape.check_url(url)

        if verdict is datablue_scrape.INCONCLUSIVE:
            logger.debug(f"DataBlue could not settle {url} ({reason}): {error}")
            return fallback

        if verdict:
            logger.info(f"DataBlue cleared {url} after {reason} — page loads")
            return True, status_code or 200, None

        return False, status_code or fallback[1], error or fallback[2]

    def _get_error_message(self, status_code: int) -> str:
        """
        Get a human-readable error message for a status code.

        Args:
            status_code: HTTP status code

        Returns:
            Error message
        """
        messages = {
            400: "Bad request",
            401: "Unauthorized - authentication required",
            403: "Access forbidden",
            404: "Page not found",
            405: "Method not allowed",
            410: "Page permanently removed",
            429: "Too many requests",
            500: "Internal server error",
            501: "Not implemented",
            502: "Bad gateway",
            503: "Service unavailable",
            504: "Gateway timeout",
        }
        return messages.get(status_code, f"HTTP error {status_code}")

    def batch_validate(self, urls: list) -> dict:
        """
        Validate multiple URLs.

        Args:
            urls: List of URLs to validate

        Returns:
            Dict mapping URL to (is_valid, status_code, error_message)
        """
        results = {}
        for url in urls:
            results[url] = self.validate(url)
        return results

    def is_broken(self, url: str) -> bool:
        """
        Quick check if a URL is broken.

        Args:
            url: The URL to check

        Returns:
            True if link is broken
        """
        is_valid, _, _ = self.validate(url)
        return not is_valid

    def get_final_url(self, url: str) -> Tuple[str, int]:
        """
        Get the final URL after following redirects.

        Args:
            url: The URL to check

        Returns:
            Tuple of (final_url, status_code)
        """
        try:
            response = self.session.head(
                url,
                timeout=self.timeout,
                allow_redirects=True
            )
            return response.url, response.status_code
        except Exception:
            return url, 0
