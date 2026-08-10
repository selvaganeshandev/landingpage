"""
Content Parser Service

Extracts clean text from a fetched page body, whichever form the crawler
delivered it in.

trafilatura parses HTML and only HTML: given markdown it fails with "wrong data
type or not valid HTML" and returns None. The crawler was migrated from
ScrapingDog (raw HTML) to DataBlue (rendered markdown) without this file
changing, so from that point on 99% of fetches extracted nothing, and the
comparison step downstream — which is guarded on the text being non-empty —
silently stopped running while every URL still recorded as crawled.

So the body is now sniffed and routed: HTML keeps the trafilatura path
unchanged, markdown is reduced to prose here. The consumer only needs readable
sentences to compare an LLM claim against, not document structure.
"""
import logging
import re
from typing import Optional, Tuple
from datetime import datetime
import hashlib

import trafilatura
from trafilatura.settings import use_config

logger = logging.getLogger(__name__)

# Fenced code, images, links, emphasis, headings, quotes, bullets and table
# pipes — the syntax that carries no prose. Applied in order; links keep their
# anchor text because that text is often the only sentence on the line.
_MD_PATTERNS = [
    (re.compile(r'```.*?```', re.S), ' '),          # fenced code
    (re.compile(r'~~~.*?~~~', re.S), ' '),
    (re.compile(r'<!--.*?-->', re.S), ' '),         # html comments
    (re.compile(r'!\[[^\]]*\]\([^)]*\)'), ''),      # images, dropped entirely
    (re.compile(r'\[([^\]]*)\]\([^)]*\)'), r'\1'),  # links -> anchor text
    (re.compile(r'^\s{0,3}#{1,6}\s*', re.M), ''),   # heading markers
    (re.compile(r'^\s{0,3}>\s?', re.M), ''),        # blockquote markers
    (re.compile(r'^\s*[-*+]\s+', re.M), ''),        # bullets
    (re.compile(r'^\s*\d+\.\s+', re.M), ''),       # numbered lists
    (re.compile(r'^\s*\|?[\s:|-]{6,}\|?\s*$', re.M), ''),  # table rules
    (re.compile(r'[|]'), ' '),                     # table cell pipes
    (re.compile(r'(\*\*|__|\*|_|`)'), ''),          # emphasis and inline code
    (re.compile(r'^\s*[-*_]{3,}\s*$', re.M), ''),   # horizontal rules
]

# Matches the MIN_EXTRACTED_SIZE trafilatura is configured with below, so a
# markdown page and an HTML page have to clear the same bar to count as
# content. Below it the result is nav furniture, not prose.
MIN_EXTRACTED_SIZE = 100


def _looks_like_html(body: str) -> bool:
    """Is this an HTML document rather than markdown?

    Deliberately conservative: markdown routinely contains a stray inline tag,
    so a real tag near the start is required rather than any '<' anywhere.
    """
    head = body.lstrip()[:2000].lower()
    if head.startswith(('<!doctype', '<html', '<?xml')):
        return True
    return any(tag in head for tag in ('<html', '<body', '<head', '<div', '<article', '<main'))


def _markdown_to_text(body: str) -> str:
    """Reduce markdown to the prose inside it."""
    text = body
    for pattern, replacement in _MD_PATTERNS:
        text = pattern.sub(replacement, text)
    # Collapse the blank lines the substitutions leave behind, and drop lines
    # that were pure syntax and are now empty.
    lines = [line.strip() for line in text.splitlines()]
    return '\n'.join(line for line in lines if line).strip()


def _markdown_title(body: str) -> str:
    """A title for a page that has no <title> tag.

    Prefers the first heading. Many rendered pages open with the title as a
    plain line rather than a marked-up heading, so the first line of prose is
    the fallback — an approximate title beats an empty one in the UI.
    """
    lines = [line.strip() for line in body.splitlines()[:40]]
    for line in lines:
        if line.startswith('#'):
            heading = line.lstrip('#').strip()
            if heading:
                return heading
    for line in lines:
        if line and not line.startswith(('|', '-', '*', '>', '!')):
            return _markdown_to_text(line)[:200]
    return ""


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

        # DataBlue returns markdown; trafilatura would return None for it.
        if not _looks_like_html(html):
            return self._parse_markdown(html, url)

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

            # Extract metadata (trafilatura 2.0+ doesn't take url param)
            metadata = trafilatura.extract_metadata(html)

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

    def _parse_markdown(self, body: str, url: str = None) -> dict:
        """Markdown path: strip the syntax and keep the prose.

        No trafilatura call here — it is an HTML parser and markdown is exactly
        the input it rejects. Metadata is thinner than the HTML path can manage:
        markdown carries no <meta> tags, so there is no description and no
        publish date, and the title is the first heading. Those fields are
        reported empty rather than guessed.
        """
        text = _markdown_to_text(body)

        if len(text) < MIN_EXTRACTED_SIZE:
            logger.warning(
                "Markdown body from %s reduced to %d chars, below the %d minimum; "
                "treating as no content.", url, len(text), MIN_EXTRACTED_SIZE,
            )
            return self._empty_result()

        if len(text) > self.max_content_length:
            text = text[:self.max_content_length] + "..."

        return {
            'extracted_text': text,
            'page_title': _markdown_title(body)[:500],
            'meta_description': "",
            'publish_date': None,
            'content_hash': hashlib.sha256(text.encode()).hexdigest(),
        }

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
