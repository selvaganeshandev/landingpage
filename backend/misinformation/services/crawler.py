"""
Web Crawler Service
Crawls URLs with Cloudflare bypass support using cloudscraper.
"""
import logging
import time
from typing import Optional, Tuple
from urllib.parse import urlparse

import cloudscraper
from django.conf import settings

logger = logging.getLogger(__name__)


class WebCrawler:
    """
    Web crawler with Cloudflare bypass support.
    Uses cloudscraper for handling anti-bot protection.
    """

    # Default configuration
    DEFAULT_TIMEOUT = 30
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RATE_LIMIT = 10  # requests per minute
    DEFAULT_MAX_CONTENT_LENGTH = 50000  # 50KB of text

    # Common user agents for rotation
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]

    def __init__(
        self,
        timeout: int = None,
        max_retries: int = None,
        rate_limit: int = None
    ):
        """
        Initialize the web crawler.

        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            rate_limit: Maximum requests per minute
        """
        self.timeout = timeout or getattr(
            settings, 'MISINFO_CRAWL_TIMEOUT', self.DEFAULT_TIMEOUT
        )
        self.max_retries = max_retries or getattr(
            settings, 'MISINFO_CRAWL_MAX_RETRIES', self.DEFAULT_MAX_RETRIES
        )
        self.rate_limit = rate_limit or getattr(
            settings, 'MISINFO_CRAWL_RATE_LIMIT', self.DEFAULT_RATE_LIMIT
        )

        self._last_request_time = 0
        self._request_count = 0
        self._user_agent_index = 0

        # Create cloudscraper session
        self.scraper = self._create_scraper()

    def _create_scraper(self) -> cloudscraper.CloudScraper:
        """
        Create a cloudscraper session with browser emulation.

        Returns:
            CloudScraper instance
        """
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            },
            delay=10  # Delay for JavaScript challenge solving
        )
        return scraper

    def _get_next_user_agent(self) -> str:
        """
        Get the next user agent in rotation.

        Returns:
            User agent string
        """
        ua = self.USER_AGENTS[self._user_agent_index]
        self._user_agent_index = (self._user_agent_index + 1) % len(self.USER_AGENTS)
        return ua

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

    def crawl(self, url: str) -> Tuple[Optional[str], int, Optional[str]]:
        """
        Crawl a URL and return the HTML content.

        Args:
            url: The URL to crawl

        Returns:
            Tuple of (html_content, http_status_code, error_message)
            - html_content: Raw HTML or None if failed
            - http_status_code: HTTP status code or 0 if connection failed
            - error_message: Error message or None if successful
        """
        for attempt in range(self.max_retries):
            try:
                self._rate_limit_wait()

                # Update headers with rotated user agent
                headers = {
                    'User-Agent': self._get_next_user_agent(),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }

                logger.info(f"Crawling URL: {url} (attempt {attempt + 1}/{self.max_retries})")

                response = self.scraper.get(
                    url,
                    headers=headers,
                    timeout=self.timeout,
                    allow_redirects=True
                )

                status_code = response.status_code

                # Check for successful response
                if status_code == 200:
                    # Check content type
                    content_type = response.headers.get('Content-Type', '').lower()
                    if 'text/html' not in content_type and 'text/plain' not in content_type:
                        logger.warning(f"Non-HTML content type: {content_type} for {url}")
                        return None, status_code, f"Non-HTML content type: {content_type}"

                    html = response.text
                    logger.info(f"Successfully crawled {url} ({len(html)} chars)")
                    return html, status_code, None

                elif status_code == 403:
                    # Cloudflare or access denied
                    logger.warning(f"Access denied (403) for {url}")
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    return None, status_code, "Access denied - possibly blocked by firewall"

                elif status_code == 404:
                    logger.info(f"Page not found (404): {url}")
                    return None, status_code, "Page not found"

                elif status_code >= 500:
                    logger.warning(f"Server error ({status_code}) for {url}")
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    return None, status_code, f"Server error: {status_code}"

                else:
                    logger.warning(f"Unexpected status {status_code} for {url}")
                    return None, status_code, f"HTTP {status_code}"

            except cloudscraper.exceptions.CloudflareChallengeError as e:
                logger.warning(f"Cloudflare challenge failed for {url}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    self.scraper = self._create_scraper()  # Create new scraper
                    continue
                return None, 0, "Cloudflare challenge failed - site is protected"

            except Exception as e:
                logger.error(f"Error crawling {url}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None, 0, str(e)

        return None, 0, "Max retries exceeded"

    def is_crawlable(self, url: str) -> bool:
        """
        Quick check if a URL is likely crawlable.
        Does a HEAD request to check availability.

        Args:
            url: The URL to check

        Returns:
            True if URL seems crawlable
        """
        try:
            self._rate_limit_wait()

            response = self.scraper.head(
                url,
                timeout=10,
                allow_redirects=True
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
