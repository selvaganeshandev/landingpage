"""
Link Validator Service
Validates URLs and checks for broken links.
"""
import logging
from typing import Tuple, Optional

import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

logger = logging.getLogger(__name__)


class LinkValidator:
    """
    Validates links and detects broken URLs.
    Uses HEAD requests for efficiency.
    """

    DEFAULT_TIMEOUT = 5  # Reduced from 10 for faster scanning

    # Status codes that indicate a broken link
    BROKEN_STATUS_CODES = {
        400, 401, 403, 404, 405, 410, 429,
        500, 501, 502, 503, 504
    }

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

            if status_code == 200:
                return True, status_code, None

            elif status_code in self.BROKEN_STATUS_CODES:
                error_msg = self._get_error_message(status_code)
                return False, status_code, error_msg

            elif 300 <= status_code < 400:
                # Redirect without final destination - might be OK
                return True, status_code, None

            else:
                return False, status_code, f"HTTP {status_code}"

        except Timeout:
            logger.warning(f"Timeout validating {url}")
            return False, 0, "Connection timeout"

        except ConnectionError as e:
            logger.warning(f"Connection error for {url}: {e}")
            return False, 0, "Connection failed"

        except RequestException as e:
            logger.error(f"Request error validating {url}: {e}")
            return False, 0, str(e)

        except Exception as e:
            logger.error(f"Unexpected error validating {url}: {e}")
            return False, 0, str(e)

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
