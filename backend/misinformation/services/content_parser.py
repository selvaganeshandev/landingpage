"""
Content Parser Service
Extracts clean text content from HTML using trafilatura.
"""
import logging
from typing import Optional, Tuple
from datetime import datetime
import hashlib

import trafilatura
from trafilatura.settings import use_config

logger = logging.getLogger(__name__)


class ContentParser:
    """
    Parses HTML content and extracts clean text using trafilatura.
    """

    # Maximum content length to store
    MAX_CONTENT_LENGTH = 50000

    def __init__(self, max_content_length: int = None):
        """
        Initialize the content parser.

        Args:
            max_content_length: Maximum characters to extract
        """
        self.max_content_length = max_content_length or self.MAX_CONTENT_LENGTH

        # Configure trafilatura
        self.config = use_config()
        self.config.set("DEFAULT", "MIN_OUTPUT_SIZE", "100")
        self.config.set("DEFAULT", "MIN_EXTRACTED_SIZE", "100")

    def parse(self, html: str, url: str = None) -> dict:
        """
        Parse HTML and extract structured content.

        Args:
            html: Raw HTML content
            url: Optional URL for better extraction

        Returns:
            Dict with extracted content:
            {
                'extracted_text': str,
                'page_title': str,
                'meta_description': str,
                'publish_date': date or None,
                'content_hash': str
            }
        """
        if not html:
            return self._empty_result()

        try:
            # Extract main content
            extracted_text = trafilatura.extract(
                html,
                url=url,
                include_comments=False,
                include_tables=True,
                include_links=False,
                include_images=False,
                favor_precision=True,
                config=self.config
            )

            if not extracted_text:
                logger.warning(f"No text extracted from {url}")
                extracted_text = ""

            # Truncate if too long
            if len(extracted_text) > self.max_content_length:
                extracted_text = extracted_text[:self.max_content_length] + "..."

            # Extract metadata
            metadata = trafilatura.extract_metadata(html, url=url)

            page_title = ""
            meta_description = ""
            publish_date = None

            if metadata:
                page_title = metadata.title or ""
                meta_description = metadata.description or ""

                # Parse publish date
                if metadata.date:
                    try:
                        publish_date = datetime.strptime(
                            metadata.date, "%Y-%m-%d"
                        ).date()
                    except ValueError:
                        try:
                            # Try other formats
                            publish_date = datetime.fromisoformat(
                                metadata.date.replace('Z', '+00:00')
                            ).date()
                        except (ValueError, AttributeError):
                            publish_date = None

            # Generate content hash
            content_hash = ""
            if extracted_text:
                content_hash = hashlib.sha256(extracted_text.encode()).hexdigest()

            return {
                'extracted_text': extracted_text,
                'page_title': page_title[:500] if page_title else "",
                'meta_description': meta_description,
                'publish_date': publish_date,
                'content_hash': content_hash
            }

        except Exception as e:
            logger.error(f"Error parsing content from {url}: {e}")
            return self._empty_result()

    def _empty_result(self) -> dict:
        """
        Return an empty result structure.

        Returns:
            Empty result dict
        """
        return {
            'extracted_text': "",
            'page_title': "",
            'meta_description': "",
            'publish_date': None,
            'content_hash': ""
        }

    def extract_key_facts(self, text: str, limit: int = 10) -> list:
        """
        Extract key sentences/facts from text.
        Useful for comparison with LLM claims.

        Args:
            text: The text to extract from
            limit: Maximum number of facts to extract

        Returns:
            List of key sentences
        """
        if not text:
            return []

        # Simple sentence extraction
        # Split by common sentence endings
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)

        # Filter and clean sentences
        facts = []
        for sentence in sentences:
            sentence = sentence.strip()
            # Skip very short or very long sentences
            if 20 < len(sentence) < 500:
                facts.append(sentence)
                if len(facts) >= limit:
                    break

        return facts

    def get_content_summary(self, text: str, max_length: int = 500) -> str:
        """
        Get a brief summary of the content.

        Args:
            text: The text to summarize
            max_length: Maximum length of summary

        Returns:
            Content summary
        """
        if not text:
            return ""

        # Simple extraction of first paragraph or sentences
        paragraphs = text.split('\n\n')

        summary = ""
        for para in paragraphs:
            para = para.strip()
            if len(para) > 50:  # Skip very short paragraphs
                summary = para
                break

        if len(summary) > max_length:
            summary = summary[:max_length].rsplit(' ', 1)[0] + "..."

        return summary
