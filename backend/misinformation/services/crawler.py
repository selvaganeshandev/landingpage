"""
Web Crawler Service
Crawls URLs using ScrapingDog API for reliable scraping with anti-bot bypass.
"""
import logging
import time
from typing import Optional, Tuple
from urllib.parse import urlparse, urlencode

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class WebCrawler:
    """
    Web crawler using ScrapingDog API.
    Provides reliable scraping with Cloudflare and anti-bot bypass.
    """

    # ScrapingDog API endpoint
    API_URL = "https://api.scrapingdog.com/scrape"

    # Default configuration
    DEFAULT_TIMEOUT = 30  # seconds (ScrapingDog may take longer)
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
        self.api_key = getattr(settings, 'SCRAPINGDOG_API_KEY', None)
        if not self.api_key:
            logger.warning("SCRAPINGDOG_API_KEY not configured - crawling will fail")

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
        elapsed = time.time() - self._last_request_time

        if elapsed < min_interval:
            sleep_time = min_interval - elapsed
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)

        self._last_request_time = time.time()

    def crawl(self, url: str, dynamic: bool = None) -> Tuple[Optional[str], int, Optional[str]]:
        """
        Crawl a URL and return the HTML content using ScrapingDog API.

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
            return None, 0, "SCRAPINGDOG_API_KEY not configured"

        use_dynamic = dynamic if dynamic is not None else self.use_dynamic

        for attempt in range(self.max_retries):
            try:
                self._rate_limit_wait()

                # Build ScrapingDog API parameters
                params = {
                    "api_key": self.api_key,
                    "url": url,
                    "dynamic": "true" if use_dynamic else "false"
                }

                logger.debug(f"Crawling URL with ScrapingDog: {url} (dynamic={use_dynamic})")

                response = self.session.get(
                    self.API_URL,
                    params=params,
                    timeout=self.timeout
                )

                status_code = response.status_code

                # Check for successful response
                if status_code == 200:
                    html = response.text

                    # Check if ScrapingDog returned an error in the response
                    if html.startswith('{"error"'):
                        try:
                            error_data = response.json()
                            error_msg = error_data.get('error', 'Unknown ScrapingDog error')
                            logger.warning(f"ScrapingDog error for {url}: {error_msg}")
                            return None, 0, error_msg
                        except Exception:
                            pass

                    logger.info(f"Successfully crawled {url} ({len(html)} chars)")
                    return html, 200, None

                elif status_code == 401:
                    logger.error("ScrapingDog API key invalid or expired")
                    return None, status_code, "Invalid API key"

                elif status_code == 402:
                    logger.error("ScrapingDog API credits exhausted")
                    return None, status_code, "API credits exhausted"

                elif status_code == 404:
                    logger.info(f"Page not found (404): {url}")
                    return None, 404, "Page not found"

                elif status_code == 429:
                    logger.warning("ScrapingDog rate limit exceeded")
                    if attempt < self.max_retries - 1:
                        time.sleep(5 * (attempt + 1))
                        continue
                    return None, status_code, "Rate limit exceeded"

                elif status_code >= 500:
                    logger.warning(f"ScrapingDog server error ({status_code}) for {url}")
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
        Does a simple HEAD request (not through ScrapingDog to save credits).

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
