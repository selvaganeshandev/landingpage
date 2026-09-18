"""
Web Crawler Service
Crawls URLs using the DataBlue scrape API for reliable scraping with anti-bot bypass.

Was ScrapingDog. That key is not configured in any environment, so every crawl
returned "SCRAPINGDOG_API_KEY not configured" and the page content needed for
misinformation comparison was never fetched — the failure was silent because the
error was recorded per-URL as an ordinary crawl failure. DataBlue is the scraper
this product already pays for, so the crawl now goes through the same account as
SERP tracking and link validation.

DataBlue returns rendered **markdown**, not raw HTML. `ContentParser` sniffs the
body and strips markdown to prose itself; it does NOT run BeautifulSoup, and it
must not be handed markdown expecting trafilatura to cope — trafilatura parses
HTML only and returns None for markdown, which is exactly what happened between
this migration and the fix. `metadata` also carries the origin's real HTTP
status, which is what makes 404s distinguishable from anti-bot blocks.
"""
import logging
import time
from typing import Optional, Tuple
from urllib.parse import urlparse, urlencode

import requests
import threading
from django.conf import settings

logger = logging.getLogger(__name__)

DEFAULT_SCRAPE_URL = "https://api.datablue.dev/v1/scrape"


def _scrape_payload(url: str, dynamic: bool, formats=None) -> dict:
    """Body for /v1/scrape. Extra keys only when asked for, so existing callers
    keep the exact request they had before."""
    payload = {"url": url}
    if dynamic:
        payload["dynamic"] = True
    if formats:
        payload["formats"] = list(formats)
    return payload


class WebCrawler:
    """
    Web crawler using the DataBlue scrape API.
    Provides reliable scraping with Cloudflare and anti-bot bypass.
    """

    # Default configuration
    DEFAULT_TIMEOUT = 30  # seconds (a rendered scrape can take longer than a plain GET)
    DEFAULT_MAX_RETRIES = 2
    DEFAULT_RATE_LIMIT = 60  # requests per minute

    def __init__(
        self,
        timeout: int = None,
        max_retries: int = None,
        rate_limit: int = None,
        use_dynamic: bool = False
    ):
        """
        Initialize the web crawler.

        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            rate_limit: Maximum requests per minute
            use_dynamic: Whether to use dynamic rendering (JavaScript execution)
        """
        self.api_key = getattr(settings, 'DATABLUE_API_KEY', None)
        self.api_url = getattr(settings, 'DATABLUE_SCRAPE_URL', DEFAULT_SCRAPE_URL)
        if not self.api_key:
            logger.warning("DATABLUE_API_KEY not configured - crawling will fail")

        self.timeout = timeout or getattr(
            settings, 'MISINFO_CRAWL_TIMEOUT', self.DEFAULT_TIMEOUT
        )
        self.max_retries = max_retries or getattr(
            settings, 'MISINFO_CRAWL_MAX_RETRIES', self.DEFAULT_MAX_RETRIES
        )
        self.rate_limit = rate_limit or getattr(
            settings, 'MISINFO_CRAWL_RATE_LIMIT', self.DEFAULT_RATE_LIMIT
        )
        self.use_dynamic = use_dynamic

        self._last_request_time = 0
        self._rate_lock = threading.Lock()
        self._request_count = 0

        # Create requests session
        self.session = requests.Session()

    def _rate_limit_wait(self):
        """
        Wait if necessary to respect rate limiting.
        """
        if self.rate_limit <= 0:
            return

        min_interval = 60.0 / self.rate_limit  # seconds between requests
        # The scan now crawls several URLs at once from one crawler instance;
        # without the lock every thread reads the same _last_request_time and
        # they all fire together, so the limit is enforced across threads.
        with self._rate_lock:
            elapsed = time.time() - self._last_request_time
            if elapsed < min_interval:
                sleep_time = min_interval - elapsed
                logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
                time.sleep(sleep_time)
            self._last_request_time = time.time()

    def crawl(self, url: str, dynamic: bool = None, formats: Optional[list] = None) -> Tuple[Optional[str], int, Optional[str]]:
        """
        Crawl a URL and return the page content using the DataBlue scrape API.

        Args:
            url: The URL to crawl
            dynamic: Override default dynamic rendering setting

        Returns:
            Tuple of (html_content, http_status_code, error_message)
            - html_content: Raw HTML or None if failed
            - http_status_code: HTTP status code or 0 if connection failed
            - error_message: Error message or None if successful
        """
        if not self.api_key:
            return None, 0, "DATABLUE_API_KEY not configured"

        # `dynamic` was accepted and then dropped: the payload only ever carried
        # the URL, so JavaScript rendering could not be turned on by any caller.
        # Sent only when asked for, so existing callers keep their behaviour.
        use_dynamic = self.use_dynamic if dynamic is None else dynamic

        for attempt in range(self.max_retries):
            try:
                self._rate_limit_wait()

                logger.debug(f"Crawling URL with DataBlue: {url}")

                response = self.session.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=_scrape_payload(url, use_dynamic, formats),
                    timeout=self.timeout,
                )

                status_code = response.status_code

                if status_code == 200:
                    return self._parse_scrape(url, response)

                elif status_code in (401, 403):
                    logger.error("DataBlue API key invalid or expired")
                    return None, status_code, "Invalid API key"

                elif status_code == 402:
                    logger.error("DataBlue API credits exhausted")
                    return None, status_code, "API credits exhausted"

                elif status_code == 429:
                    logger.warning("DataBlue rate limit exceeded")
                    if attempt < self.max_retries - 1:
                        time.sleep(5 * (attempt + 1))
                        continue
                    return None, status_code, "Rate limit exceeded"

                elif status_code >= 500:
                    logger.warning(f"DataBlue server error ({status_code}) for {url}")
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    return None, status_code, f"Server error: {status_code}"

                else:
                    logger.warning(f"Unexpected status {status_code} for {url}")
                    return None, status_code, f"HTTP {status_code}"

            except requests.Timeout:
                logger.warning(f"Timeout crawling {url}")
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
                logger.error(f"Error crawling {url}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None, 0, str(e)

        return None, 0, "Max retries exceeded"

    def _parse_scrape(self, url: str, response) -> Tuple[Optional[str], int, Optional[str]]:
        """Turn a 200 from /v1/scrape into (content, origin_status, error).

        DataBlue answers 200 with `success: true` even when the target is dead —
        it renders the site's 404 into markdown. The origin's real status lives
        at data.metadata.status_code, and that is what decides the outcome here.
        Returning the rendered error page as if it were content would feed a
        "page not found" body into the misinformation comparison.
        """
        try:
            payload = response.json()
        except ValueError:
            return None, 0, "DataBlue returned non-JSON"

        if not isinstance(payload, dict) or payload.get("success") is False:
            detail = (payload or {}).get("error") or (payload or {}).get("detail") or "scrape failed"
            logger.warning(f"DataBlue scrape failed for {url}: {detail}")
            return None, 0, str(detail)

        data = payload.get("data")
        if not isinstance(data, dict):
            data = payload
        metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}

        origin_status = metadata.get("status_code")
        try:
            origin_status = int(origin_status)
        except (TypeError, ValueError):
            origin_status = 0

        # 0 means DataBlue never reached the host; 'blocked' means it was turned
        # away. Neither yields usable page content.
        if data.get("status") == "blocked" or origin_status == 0:
            reason = data.get("empty_reason") or "blocked"
            return None, origin_status or 403, f"Blocked by origin ({reason})"

        if origin_status >= 400:
            logger.info(f"Origin returned {origin_status} for {url}")
            return None, origin_status, f"HTTP {origin_status}"

        # raw_html first: it is the whole document, and only the audit rescue
        # asks for it. Markdown stays the default for everyone else.
        content = data.get("raw_html") or data.get("markdown") or data.get("html") or data.get("content") or ""
        if not content.strip():
            return None, origin_status, "Empty page content"

        logger.info(f"Successfully crawled {url} ({len(content)} chars)")
        return content, origin_status, None

    def crawl_dynamic(self, url: str) -> Tuple[Optional[str], int, Optional[str]]:
        """
        Crawl a URL with JavaScript rendering enabled.
        Use this for pages that require JavaScript to load content.

        Args:
            url: The URL to crawl

        Returns:
            Tuple of (html_content, http_status_code, error_message)
        """
        return self.crawl(url, dynamic=True)

    def is_crawlable(self, url: str) -> bool:
        """
        Quick check if a URL is likely crawlable.
        Does a simple HEAD request (not through DataBlue, to save credits).

        Args:
            url: The URL to check

        Returns:
            True if URL seems crawlable
        """
        try:
            self._rate_limit_wait()

            response = self.session.head(
                url,
                timeout=10,
                allow_redirects=True,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )

            return response.status_code == 200

        except Exception as e:
            logger.debug(f"URL {url} not crawlable: {e}")
            return False

    def get_domain(self, url: str) -> str:
        """
        Extract domain from URL.

        Args:
            url: The URL

        Returns:
            Domain name
        """
        try:
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return ''
