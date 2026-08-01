"""
URL Extraction Service
Extracts URLs from LLM response text and citation lists.
"""
import re
import hashlib
from typing import List, Set
from urllib.parse import urlparse


class URLExtractor:
    """
    Extracts and validates URLs from text and JSON citation lists.
    """

    # URL regex pattern - matches http, https, and www URLs
    URL_PATTERN = re.compile(
        r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s\]\)"\'>]*|'
        r'www\.(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s\]\)"\'>]*',
        re.IGNORECASE
    )

    # Common file extensions to exclude (images, documents, etc.)
    EXCLUDED_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.ico',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.zip', '.rar', '.tar', '.gz', '.7z',
        '.mp3', '.mp4', '.avi', '.mov', '.wmv',
        '.css', '.js', '.json', '.xml', '.woff', '.woff2', '.ttf', '.eot'
    }

    # Domains to skip (social media, known non-content pages)
    SKIP_DOMAINS = {
        'twitter.com', 'x.com', 'facebook.com', 'instagram.com',
        'linkedin.com', 'youtube.com', 'tiktok.com', 'pinterest.com',
        'reddit.com', 'discord.com', 'slack.com', 'whatsapp.com',
        'mailto:', 'tel:', 'javascript:'
    }

    def __init__(self):
        self.extracted_urls: Set[str] = set()

    def extract_from_text(self, text: str) -> List[str]:
        """
        Extract URLs from plain text.

        Args:
            text: The text to extract URLs from

        Returns:
            List of unique, validated URLs
        """
        if not text:
            return []

        urls = self.URL_PATTERN.findall(text)
        validated = []

        for url in urls:
            normalized = self._normalize_url(url)
            if normalized and self._is_valid_url(normalized):
                validated.append(normalized)

        return list(set(validated))

    def extract_from_citations(self, citation_list: list) -> List[str]:
        """
        Extract URLs from a citation list (JSON array).

        Every URL here is taken as-is: the platform explicitly cited it, and the
        Citations page displays it, so the scan must be able to report a status
        for it. Passing these through _is_valid_url would silently drop whole
        categories — YouTube, LinkedIn, Reddit, every PDF — leaving them stuck on
        the pending clock forever with no way to resolve them. On xberra tagger
        that was 84 citations, almost all YouTube.

        Whether a URL is worth scraping *text* from is a separate question,
        answered by is_content_scrapable().

        Args:
            citation_list: List of citation objects, each may have 'url', 'source', or 'link' field

        Returns:
            List of unique URLs
        """
        if not citation_list or not isinstance(citation_list, list):
            return []

        urls = []

        for citation in citation_list:
            if isinstance(citation, dict):
                # Try common field names for URLs
                for field in ['url', 'source', 'link', 'href', 'uri']:
                    url = citation.get(field)
                    if url and isinstance(url, str):
                        normalized = self._normalize_url(url)
                        if normalized and self._is_well_formed(normalized):
                            urls.append(normalized)
                            break

                # Also extract from 'text' field if it contains URLs
                text = citation.get('text', '')
                if text:
                    urls.extend(self.extract_from_text(text))

            elif isinstance(citation, str):
                # Citation might be a plain URL string
                normalized = self._normalize_url(citation)
                if normalized and self._is_well_formed(normalized):
                    urls.append(normalized)
                else:
                    # Or it might be text containing URLs
                    urls.extend(self.extract_from_text(citation))

        return list(set(urls))

    def extract_all(self, response_text: str, citation_list: list = None) -> List[dict]:
        """
        Extract all URLs from both response text and citation list.

        Args:
            response_text: The LLM response text
            citation_list: Optional list of citations

        Returns:
            List of dicts with 'url' and 'url_hash' keys
        """
        all_urls = set()

        # Extract from response text
        text_urls = self.extract_from_text(response_text)
        all_urls.update(text_urls)

        # Extract from citation list
        if citation_list:
            citation_urls = self.extract_from_citations(citation_list)
            all_urls.update(citation_urls)

        # Create result with hashes
        result = []
        for url in all_urls:
            result.append({
                'url': url,
                'url_hash': self._generate_hash(url)
            })

        return result

    def _normalize_url(self, url: str) -> str:
        """
        Normalize a URL for consistency.

        Args:
            url: The URL to normalize

        Returns:
            Normalized URL or empty string if invalid
        """
        if not url:
            return ''

        url = url.strip()

        # Add scheme if missing
        if url.startswith('www.'):
            url = 'https://' + url

        # Remove trailing punctuation that might have been captured
        url = url.rstrip('.,;:!?\'"')

        # Remove fragment
        if '#' in url:
            url = url.split('#')[0]

        # Remove trailing slash for consistency
        url = url.rstrip('/')

        return url

    def _is_well_formed(self, url: str) -> bool:
        """Structural check only: an http(s) URL with a host.

        No opinion on what the URL points at. Used for cited URLs, where the
        only reason to reject is that the string cannot be fetched at all —
        e.g. the truncated "https://bizfinx." that an LLM occasionally emits.
        """
        if not url:
            return False
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ('http', 'https'):
                return False
            host = parsed.netloc or ''
            # A host must contain a dot and not end on one; "bizfinx." fails both.
            return bool(host) and '.' in host and not host.endswith('.')
        except Exception:
            return False

    def is_content_scrapable(self, url: str) -> bool:
        """
        Whether this URL is worth fetching page *text* from.

        False for social/video platforms and for binary files. Scraping a
        YouTube watch page or a PDF for prose to compare against an LLM claim
        produces nothing useful, which is what SKIP_DOMAINS and
        EXCLUDED_EXTENSIONS were written for.

        This is deliberately NOT the same question as "should we check whether
        this link works". Every cited URL deserves that check — a dead YouTube
        link in an AI answer about your brand matters just as much as a dead
        article — so link validation must not consult this method.
        """
        if not url:
            return False
        try:
            parsed = urlparse(url)
            domain = (parsed.netloc or '').lower()
            if any(skip in domain for skip in self.SKIP_DOMAINS):
                return False
            path_lower = (parsed.path or '').lower()
            if any(path_lower.endswith(ext) for ext in self.EXCLUDED_EXTENSIONS):
                return False
            return True
        except Exception:
            return False

    def _is_valid_url(self, url: str) -> bool:
        """
        Check if a URL is valid and should be processed.

        Args:
            url: The URL to validate

        Returns:
            True if valid and should be processed
        """
        if not url:
            return False

        try:
            parsed = urlparse(url)

            # Must have scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                return False

            # Must be http or https
            if parsed.scheme not in ('http', 'https'):
                return False

            # Check for excluded domains
            domain = parsed.netloc.lower()
            for skip_domain in self.SKIP_DOMAINS:
                if skip_domain in domain:
                    return False

            # Check for excluded file extensions
            path_lower = parsed.path.lower()
            for ext in self.EXCLUDED_EXTENSIONS:
                if path_lower.endswith(ext):
                    return False

            # URL seems valid
            return True

        except Exception:
            return False

    def _generate_hash(self, url: str) -> str:
        """
        Generate a SHA256 hash for a URL.

        Args:
            url: The URL to hash

        Returns:
            SHA256 hash as hex string
        """
        return hashlib.sha256(url.encode()).hexdigest()
