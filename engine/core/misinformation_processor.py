"""
Misinformation Processing Module
Handles misinformation detection and citation scanning in the engine.
"""
import logging
import re
import threading
from datetime import date
from typing import Optional, List
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.apps import apps

from shared_models.models import Domain, PromptAnalytics

from .misinformation_services import (
    URLExtractor,
    WebCrawler,
    ContentParser,
    LinkValidator,
    ContentComparator,
)
from .telemetry import observe, trace_metadata

logger = logging.getLogger(__name__)


# Scan tunables. All read from settings so production can turn a knob
# without a deploy; the defaults are the values measured to matter.
#
# A scan is one crawl plus one model call per cited URL, done strictly one
# after another. On production that meant UPES University (78 answers,
# ~1,000 distinct citations) had run for 4.5 hours with 913 URLs still to go,
# and earlier domains took 9-43 hours. Four things bring that to minutes:
#   MISINFO_MAX_URLS_PER_ANSWER  answers cite ~17 URLs; the first few are what
#                                the model relied on, the tail is padding.
#   MISINFO_RECRAWL_HOURS        a source checked this week does not need
#                                checking again on the next run.
#   MISINFO_SKIP_IF_BRAND_ABSENT a page that never names the brand has nothing
#                                to be wrong about it, so the model call —
#                                the slow, paid step — is skipped.
#   MISINFO_SCAN_CONCURRENCY     every (answer, URL) pair in the scan is queued
#                                to one pool. Two answers often cite the same
#                                page, so work on a given URL is serialised with
#                                a per-URL lock — different URLs run in parallel,
#                                the same URL never does, and the second caller
#                                finds it already crawled and skips.
MISINFO_MAX_URLS_PER_ANSWER = int(getattr(settings, 'MISINFO_MAX_URLS_PER_ANSWER', 10))
MISINFO_RECRAWL_HOURS = int(getattr(settings, 'MISINFO_RECRAWL_HOURS', 168))
MISINFO_SKIP_IF_BRAND_ABSENT = bool(getattr(settings, 'MISINFO_SKIP_IF_BRAND_ABSENT', True))
MISINFO_SCAN_CONCURRENCY = int(getattr(settings, 'MISINFO_SCAN_CONCURRENCY', 8))

# Words that are part of many brand names and prove nothing on their own.
_GENERIC_BRAND_WORDS = frozenset((
    'the', 'and', 'of', 'ltd', 'limited', 'inc', 'llc', 'pvt', 'private', 'co',
    'company', 'group', 'india', 'bank', 'university', 'hospital', 'insurance',
    'motors', 'services', 'solutions', 'technologies', 'international', 'global',
))


class MisinformationProcessor:
    """
    Processes misinformation scans for domains.
    Similar to CompetitorProcessor, this handles the processing logic in the engine.
    """

    def __init__(self):
        """Initialize the processor with services."""
        # Initialize services
        self.url_extractor = URLExtractor()
        self.crawler = WebCrawler()
        self.content_parser = ContentParser()
        self.link_validator = LinkValidator()
        self.comparator = ContentComparator()

    @observe(name="misinformation.process_domain", ignore_inputs=["self"])
    def process_domain(self, domain_id: int, prompt_analytics_ids: List[int] = None,
                       own_links_only: bool = False):
        """
        Process misinformation scan for a domain.

        Args:
            domain_id: ID of the domain to scan
            prompt_analytics_ids: Optional list of specific prompt analytics to scan
            own_links_only: Visit only citations pointing at the domain's own
                site. Sent by the Citations page's "Validate Citations" button,
                which asks whether links AI sent to this brand still work —
                a question that does not exist for aws.amazon.com. Automatic
                scans leave it off: misinformation detection is precisely about
                what third-party pages say.

        Returns:
            MisinformationScan instance
        """
        # Get models from shared_models (read-only models pointing to backend tables)
        from shared_models.models import (
            MisinformationScan,
            CitationURL,
            CitationContent,
            CitationMention,
            MisinformationAlert,
            MisinformationAnalytics
        )

        domain = Domain.objects.get(id=domain_id)

        # Attach tenant attribution to the Laminar trace (no-op when off).
        trace_metadata(
            trace_type="misinformation",
            organization_id=getattr(domain, 'organisation_id', None),
            domain_id=domain_id,
        )

        # Bind the comparator to this domain's organisation so it uses the org's
        # BYOK OpenAI key (with .env fallback).
        self.comparator = ContentComparator(org_id=getattr(domain, 'organisation_id', None))

        # Create scan record
        scan = MisinformationScan.objects.create(
            domain=domain,
            status='running',
            started_at=timezone.now()
        )

        # Update domain status to scanning
        with transaction.atomic():
            domain_fresh = Domain.objects.select_for_update().get(id=domain_id)
            domain_fresh.misinformation_scan_status = 'SCANNING'
            domain_fresh.save(update_fields=['misinformation_scan_status'])

        try:
            # Get prompt analytics to scan
            if prompt_analytics_ids:
                prompt_analytics_qs = PromptAnalytics.objects.filter(
                    id__in=prompt_analytics_ids,
                    prompt__group__domain_id=domain_id,
                    track_status='COMP'  # Only completed analytics
                )
            else:
                prompt_analytics_qs = PromptAnalytics.objects.filter(
                    prompt__group__domain_id=domain_id,
                    track_status='COMP',
                    is_mention=True  # Only where brand is mentioned
                ).select_related('prompt', 'prompt__group')

            total = prompt_analytics_qs.count()
            logger.info(f"Starting misinformation scan for domain {domain.name}, {total} prompt analytics to scan")

            # Counters
            prompts_scanned = 0
            citations_found = 0
            alerts_generated = 0

            # Gather every (answer, URL) pair up front, then push them all through
            # one pool. Doing answers one at a time — even with the URLs inside
            # each answer in parallel — left most workers idle, since an answer
            # cites only a handful of pages.
            work = []
            for pa in prompt_analytics_qs:
                try:
                    urls = self._urls_for(pa, domain, own_links_only)
                except Exception as e:
                    logger.error(f"Error extracting URLs for prompt analytics {pa.id}: {e}")
                    continue
                prompts_scanned += 1
                citations_found += len(urls)
                for position, url_data in enumerate(urls, start=1):
                    work.append((pa, position, url_data))

            self._url_locks = {}
            self._url_locks_guard = threading.Lock()

            def _one(item):
                pa, position, url_data = item
                key = url_data['url'].strip().lower()
                with self._url_locks_guard:
                    lock = self._url_locks.setdefault(key, threading.Lock())
                try:
                    with lock:
                        return self._process_url(
                            pa, url_data, position, domain,
                            CitationURL, CitationContent, CitationMention, MisinformationAlert, scan
                        )
                except Exception as e:
                    logger.error(f"Error processing URL {url_data['url']}: {e}")
                    return False
                finally:
                    # Each worker thread holds its own DB connection; hand it
                    # back rather than letting it idle until the thread dies.
                    from django.db import connection
                    connection.close()

            workers = max(1, min(MISINFO_SCAN_CONCURRENCY, len(work)))
            logger.info(f"Scanning {len(work)} URL(s) across {prompts_scanned} answer(s) with {workers} worker(s)")
            if workers == 1:
                for item in work:
                    if _one(item):
                        alerts_generated += 1
            else:
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=workers, thread_name_prefix='misinfo') as pool:
                    for created in pool.map(_one, work):
                        if created:
                            alerts_generated += 1

            # Update scan record
            scan.status = 'completed'
            scan.completed_at = timezone.now()
            scan.total_prompts_scanned = prompts_scanned
            scan.total_citations_found = citations_found
            scan.total_alerts_generated = alerts_generated
            scan.save()

            # Update domain status based on results
            with transaction.atomic():
                domain_fresh = Domain.objects.select_for_update().get(id=domain_id)
                if alerts_generated > 0:
                    domain_fresh.misinformation_scan_status = 'SCANNED'
                else:
                    domain_fresh.misinformation_scan_status = 'NO_ISSUES'
                domain_fresh.last_misinformation_scan_at = timezone.now()
                domain_fresh.save(update_fields=['misinformation_scan_status', 'last_misinformation_scan_at'])

            # Update daily analytics
            self._update_daily_analytics(domain, MisinformationAlert, MisinformationAnalytics)

            logger.info(
                f"Scan completed: {prompts_scanned} prompts, "
                f"{citations_found} citations, {alerts_generated} alerts"
            )

            return scan

        except Exception as e:
            logger.error(f"Scan failed: {e}")
            scan.status = 'failed'
            scan.error_message = str(e)
            scan.completed_at = timezone.now()
            scan.save()

            # Reset domain status on failure
            with transaction.atomic():
                domain_fresh = Domain.objects.select_for_update().get(id=domain_id)
                domain_fresh.misinformation_scan_status = 'READY'
                domain_fresh.save(update_fields=['misinformation_scan_status'])
            raise

    def _urls_for(self, pa: PromptAnalytics, domain: Domain, own_links_only: bool = False) -> list:
        """The URLs to check for one answer, after the own-site filter and the
        per-answer cap. Shared by the scan loop and _process_prompt_analytics."""
        response_text = pa.context_summary or ""
        citation_list = pa.citation_list or []
        urls = self.url_extractor.extract_all(response_text, citation_list)
        if own_links_only:
            urls = [u for u in urls if self._is_own_site_url(u['url'], domain)]
        if MISINFO_MAX_URLS_PER_ANSWER > 0 and len(urls) > MISINFO_MAX_URLS_PER_ANSWER:
            logger.info(
                f"Prompt analytics {pa.id}: {len(urls)} URLs, checking the first "
                f"{MISINFO_MAX_URLS_PER_ANSWER} (MISINFO_MAX_URLS_PER_ANSWER)"
            )
            urls = urls[:MISINFO_MAX_URLS_PER_ANSWER]
        if urls:
            logger.info(f"Found {len(urls)} URLs in prompt analytics {pa.id}")
        return urls

    def _process_prompt_analytics(
        self, pa: PromptAnalytics, domain: Domain,
        CitationURL, CitationContent, CitationMention, MisinformationAlert, scan,
        own_links_only: bool = False
    ) -> dict:
        """
        Process a single prompt analytics record.

        Args:
            pa: PromptAnalytics instance
            domain: Domain instance
            CitationURL, CitationContent, CitationMention, MisinformationAlert: Model classes
            scan: MisinformationScan instance

        Returns:
            Dict with 'citations' and 'alerts' counts
        """
        urls = self._urls_for(pa, domain, own_links_only)
        if not urls:
            logger.debug(f"No URLs found in prompt analytics {pa.id}")
            return {'citations': 0, 'alerts': 0}
        citations_count = len(urls)
        alerts_count = 0

        def _one(position, url_data):
            try:
                return self._process_url(
                    pa, url_data, position, domain,
                    CitationURL, CitationContent, CitationMention, MisinformationAlert, scan
                )
            except Exception as e:
                logger.error(f"Error processing URL {url_data['url']}: {e}")
                return False
            finally:
                # Each worker thread gets its own DB connection; return it to
                # the pool rather than letting it idle until the thread dies.
                from django.db import connection
                connection.close()

        workers = max(1, min(MISINFO_SCAN_CONCURRENCY, len(urls)))
        if workers == 1:
            for position, url_data in enumerate(urls, start=1):
                if _one(position, url_data):
                    alerts_count += 1
        else:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=workers, thread_name_prefix='misinfo') as pool:
                for created in pool.map(lambda pu: _one(*pu), enumerate(urls, start=1)):
                    if created:
                        alerts_count += 1

        return {'citations': citations_count, 'alerts': alerts_count}

    def _process_url(
        self, pa: PromptAnalytics, url_data: dict, position: int, domain: Domain,
        CitationURL, CitationContent, CitationMention, MisinformationAlert, scan
    ) -> bool:
        """
        Process a single URL: crawl, parse, and compare.
        Only creates alerts for brand-related URLs.

        Args:
            pa: PromptAnalytics instance
            url_data: Dict with 'url' and 'url_hash'
            position: Position of this URL in the response (1-indexed)
            domain: Domain instance
            CitationURL, CitationContent, CitationMention, MisinformationAlert: Model classes
            scan: MisinformationScan instance

        Returns:
            True if an alert was created, False otherwise
        """
        url = url_data['url']
        url_hash = url_data['url_hash']

        # Check if this URL is related to our brand
        is_brand_url = self._is_brand_related_url(url, domain)

        # Check if URL already exists for this prompt analytics
        citation_url, created = CitationURL.objects.get_or_create(
            domain=domain,
            prompt_analytics=pa,
            url_hash=url_hash,
            defaults={
                'url': url,
                'crawl_status': 'pending'
            }
        )

        # Always create a CitationMention record to track this occurrence
        context_snippet = self._extract_context_snippet(pa.context_summary or "", url)

        CitationMention.objects.get_or_create(
            citation_url=citation_url,
            prompt_analytics=pa,
            defaults={
                'domain': domain,
                'context_snippet': context_snippet,
                'position_in_response': position,
                'is_primary_source': position == 1,  # First citation is primary
            }
        )

        if not created and citation_url.crawl_status == 'success':
            # URL already processed successfully, check if content is fresh
            if citation_url.last_crawled_at:
                # Skip if crawled recently (MISINFO_RECRAWL_HOURS, default a week)
                age = timezone.now() - citation_url.last_crawled_at
                if age.total_seconds() < MISINFO_RECRAWL_HOURS * 3600:
                    logger.debug(f"Skipping recently crawled URL: {url}")
                    return False

        # Validate link first
        is_valid, status_code, error = self.link_validator.validate(url)

        if not is_valid:
            citation_url.crawl_status = 'failed'
            citation_url.http_status_code = status_code
            citation_url.crawl_error = error
            citation_url.is_crawlable = False
            citation_url.save()

            # Only create broken link alert for actual broken links (404, 410)
            if is_brand_url and status_code in (404, 410):
                self._create_alert(
                    pa=pa,
                    citation_url=citation_url,
                    alert_type='broken_link',
                    severity='low',
                    llm_claim=f"Citation URL: {url}",
                    source_content="",
                    explanation=f"Broken link: {error}",
                    domain=domain,
                    scan=scan,
                    MisinformationAlert=MisinformationAlert
                )
                return True
            return False

        # The link is alive — the validator just proved it. Record that verdict
        # NOW, before any content work, because these two questions are separate:
        #
        #   "does this link work?"        -> the validator, and only the validator
        #   "what does the page say?"     -> the scrape below, for misinformation
        #
        # They used to be conflated: a validated-alive URL whose *content* could
        # not be scraped was written back as crawl_status='failed', so the
        # Citations page reported working links as broken. With the scraper key
        # unset that hit every single URL.
        citation_url.crawl_status = 'success'
        citation_url.http_status_code = status_code
        citation_url.crawl_error = None
        citation_url.is_crawlable = True
        citation_url.last_crawled_at = timezone.now()
        citation_url.save()

        # Fetch the page text. This feeds the misinformation comparison only —
        # its outcome must not change the link status set above.
        #
        # Social/video platforms and binary files are skipped here rather than at
        # extraction time: their links still need validating (done above), but
        # scraping a YouTube watch page or a PDF for prose to compare against an
        # LLM claim yields nothing and costs a credit per URL.
        if not self.url_extractor.is_content_scrapable(url):
            logger.debug(f"Validated but not scraping content for {url}")
            return False

        html, http_status, crawl_error = self.crawler.crawl(url)

        if not html:
            # One exception: if the scraper reports a definitive gone-status from
            # the origin, that is better evidence than a HEAD that may have been
            # served a cached or soft response.
            if http_status in (404, 410):
                citation_url.crawl_status = 'failed'
                citation_url.http_status_code = http_status
                citation_url.crawl_error = crawl_error
                citation_url.is_crawlable = False
                citation_url.save()
            else:
                # Content unavailable, link still fine. Note why the text is
                # missing without disturbing the verdict.
                citation_url.crawl_error = f'Content unavailable: {crawl_error}'
                citation_url.save(update_fields=['crawl_error'])

            # Only create broken link alert for brand-related URLs
            if is_brand_url and http_status in (404, 410):
                self._create_alert(
                    pa=pa,
                    citation_url=citation_url,
                    alert_type='broken_link',
                    severity='low',
                    llm_claim=f"Citation URL: {url}",
                    source_content="",
                    explanation=f"Page not found (HTTP {http_status})",
                    domain=domain,
                    scan=scan,
                    MisinformationAlert=MisinformationAlert
                )
                return True
            return False

        # Parse content
        parsed = self.content_parser.parse(html, url)

        # Update or create citation content
        CitationContent.objects.update_or_create(
            citation_url=citation_url,
            defaults={
                'raw_html': html[:100000] if html else "",  # Limit HTML storage
                'extracted_text': parsed['extracted_text'],
                'page_title': parsed['page_title'],
                'meta_description': parsed['meta_description'],
                'publish_date': parsed['publish_date'],
                'content_hash': parsed['content_hash']
            }
        )

        # crawl_status stays the LINK's health and is deliberately not touched
        # by the extraction outcome — see the note above where it is set. A
        # reachable page whose body yields no prose is still a working link,
        # and marking it otherwise would drop it out of the Valid count on the
        # Citations page, which is the bug that note records fixing.
        #
        # The extraction outcome is carried by extracted_text being empty, and
        # logged here so a silent parser failure is visible in the worker log
        # rather than only as an absence of alerts.
        extracted = parsed['extracted_text']
        if not extracted:
            logger.warning(
                "No readable text extracted from %s (body %d chars) — "
                "misinformation comparison skipped for this URL.",
                url, len(html or ''),
            )
        citation_url.crawl_status = 'success'
        citation_url.last_crawled_at = timezone.now()
        citation_url.crawl_error = None
        citation_url.save()

        # Compare LLM claims against source content
        alert_created = False
        if extracted:
            if MISINFO_SKIP_IF_BRAND_ABSENT and not self._mentions_brand(extracted, domain):
                logger.info(f"Source never names the brand, comparison skipped: {url}")
                return False
            alert_created = self._compare_content(
                pa, citation_url, extracted, url, domain, MisinformationAlert, scan
            )

        return alert_created

    def _mentions_brand(self, text: str, domain: Domain) -> bool:
        """Does this page mention the brand at all?

        A page that never names the brand cannot carry misinformation about it,
        and the comparison model call is the slow, paid step of the scan — so
        it is only made when there is something to compare. Matches the full
        name, the site's host label ("upes" for upes.ac.in), or any
        distinctive word of the name; generic words ("university", "bank")
        do not count on their own. Errs towards checking: anything ambiguous
        returns True.
        """
        t = (text or '').lower()
        if not t:
            return False
        name = (domain.name or '').strip().lower()
        if name and name in t:
            return True
        host = self._bare_host(domain.url or '')
        label = host.split('.')[0] if host else ''
        if label and len(label) >= 3 and label in t:
            return True
        words = [w for w in re.findall(r'[a-z0-9]+', name) if len(w) >= 3 and w not in _GENERIC_BRAND_WORDS]
        if not words:
            return True   # nothing distinctive to test against; do not skip
        return any(w in t for w in words)

    @staticmethod
    def _bare_host(url: str) -> str:
        h = (url or '').strip().lower()
        h = re.sub(r'^[a-z]+://', '', h).split('/')[0].split('@')[-1].split(':')[0]
        return h[4:] if h.startswith('www.') else h

    def _is_own_site_url(self, url: str, domain: Domain) -> bool:
        """True only when the URL is on the brand's own host (or a subdomain)."""
        from urllib.parse import urlparse

        def host_of(value: str) -> str:
            value = (value or '').strip().lower()
            if value and not value.startswith(('http://', 'https://')):
                value = f'https://{value}'
            host = urlparse(value).netloc
            return host[4:] if host.startswith('www.') else host

        brand = host_of(getattr(domain, 'url', ''))
        cited = host_of(url)
        if not brand or not cited:
            return False
        return cited == brand or cited.endswith(f'.{brand}')

    def _is_brand_related_url(self, url: str, domain: Domain) -> bool:
        """
        Check if URL is related to the brand.

        Args:
            url: URL to check
            domain: Domain instance

        Returns:
            True if URL is related to the brand
        """
        from urllib.parse import urlparse

        parsed_url = urlparse(url)
        url_domain = parsed_url.netloc.lower().replace('www.', '')

        # Check if URL is from the brand's own domain
        brand_domain = urlparse(domain.url).netloc.lower().replace('www.', '')

        if brand_domain in url_domain or url_domain in brand_domain:
            return True

        # Check if brand name appears in the URL path
        if domain.name.lower() in url.lower():
            return True

        return False

    def _extract_context_snippet(self, text: str, url: str, window: int = 200) -> str:
        """
        Extract a snippet of text around where the URL might appear.

        Args:
            text: Full response text
            url: URL to find context for
            window: Number of characters on each side of URL

        Returns:
            Context snippet string
        """
        if not text:
            return ""

        # Try to find the URL in text
        url_pos = text.find(url)
        if url_pos == -1:
            # URL not found directly, try domain only
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            url_pos = text.find(domain)

        if url_pos == -1:
            # If still not found, return first 400 chars as general context
            return text[:400] if len(text) > 400 else text

        # Extract window around the URL
        start = max(0, url_pos - window)
        end = min(len(text), url_pos + len(url) + window)

        snippet = text[start:end]

        # Add ellipsis if truncated
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."

        return snippet

    def _compare_content(
        self,
        pa: PromptAnalytics,
        citation_url,
        source_content: str,
        source_url: str,
        domain: Domain,
        MisinformationAlert,
        scan
    ) -> bool:
        """
        Compare LLM claims against source content.
        Only creates alerts for brand-related issues.

        Args:
            pa: PromptAnalytics instance
            citation_url: CitationURL instance
            source_content: Extracted text from source
            source_url: URL of the source
            domain: Domain instance
            MisinformationAlert: Model class
            scan: MisinformationScan instance

        Returns:
            True if an alert was created, False otherwise
        """
        # Get LLM response text
        llm_response = pa.context_summary or ""

        if not llm_response:
            return False

        # Extract brand-specific claims only
        claims = self.comparator.extract_brand_claims(llm_response, domain.name)

        # If no brand-specific claims found, skip comparison for this URL
        if not claims:
            logger.debug(f"No brand-specific claims found in response for {source_url}, skipping comparison")
            return False

        # Only compare brand-related claims
        alert_created = False
        for claim in claims:
            result = self.comparator.compare(
                llm_claim=claim,
                source_content=source_content,
                source_url=source_url,
                brand_name=domain.name,
                brand_url=domain.url
            )

            if result.has_issue:
                self._create_alert(
                    pa=pa,
                    citation_url=citation_url,
                    alert_type=result.alert_type,
                    severity=result.severity,
                    llm_claim=result.llm_claim,
                    source_content=result.source_content,
                    explanation=result.explanation,
                    domain=domain,
                    scan=scan,
                    MisinformationAlert=MisinformationAlert
                )
                alert_created = True

        return alert_created

    def _create_alert(
        self,
        pa: PromptAnalytics,
        citation_url: Optional,
        alert_type: str,
        severity: str,
        llm_claim: str,
        source_content: str,
        explanation: str,
        domain: Domain,
        scan,
        MisinformationAlert
    ) -> bool:
        """
        Create a misinformation alert.

        Args:
            pa: PromptAnalytics instance
            citation_url: CitationURL instance (optional)
            alert_type: Type of alert
            severity: Severity level
            llm_claim: The LLM's claim
            source_content: Content from source
            explanation: Explanation of the issue
            domain: Domain instance
            scan: MisinformationScan instance
            MisinformationAlert: Model class

        Returns:
            True if alert was created, False if duplicate
        """
        # Check for duplicate alerts - same citation URL
        existing = MisinformationAlert.objects.filter(
            domain=domain,
            prompt_analytics=pa,
            citation_url=citation_url,
            alert_type=alert_type,
            status__in=['new', 'reviewed']
        ).first()

        if existing:
            logger.debug(f"Duplicate alert skipped for {alert_type} (same citation URL)")
            return False

        # Also check for duplicate claims
        claim_prefix = llm_claim[:100] if llm_claim else ""
        if claim_prefix:
            existing_claim = MisinformationAlert.objects.filter(
                domain=domain,
                prompt_analytics=pa,
                alert_type=alert_type,
                llm_claim__startswith=claim_prefix,
                status__in=['new', 'reviewed']
            ).first()

            if existing_claim:
                logger.debug(f"Duplicate alert skipped for {alert_type} (same claim already exists)")
                return False

        MisinformationAlert.objects.create(
            domain=domain,
            prompt=pa.prompt,
            prompt_analytics=pa,
            citation_url=citation_url,
            scan=scan,
            alert_type=alert_type,
            severity=severity,
            llm_claim=llm_claim,
            source_content=source_content,
            explanation=explanation,
            status='new'
        )

        logger.info(f"Created {severity} {alert_type} alert for domain {domain.name}")
        return True

    def _update_daily_analytics(self, domain: Domain, MisinformationAlert, MisinformationAnalytics):
        """
        Update daily misinformation analytics.

        Args:
            domain: Domain instance
            MisinformationAlert: Model class
            MisinformationAnalytics: Model class
        """
        today = date.today()

        # Count alerts by type and severity
        alerts_today = MisinformationAlert.objects.filter(
            domain=domain,
            created_at__date=today
        )

        total = alerts_today.count()
        broken_links = alerts_today.filter(alert_type='broken_link').count()
        misinformation = alerts_today.filter(alert_type='misinformation').count()
        outdated = alerts_today.filter(alert_type='outdated').count()

        by_severity = {
            'low': alerts_today.filter(severity='low').count(),
            'medium': alerts_today.filter(severity='medium').count(),
            'high': alerts_today.filter(severity='high').count(),
            'critical': alerts_today.filter(severity='critical').count(),
        }

        MisinformationAnalytics.objects.update_or_create(
            domain=domain,
            date=today,
            defaults={
                'total_detected': total,
                'broken_links_count': broken_links,
                'misinformation_count': misinformation,
                'outdated_count': outdated,
                'by_severity': by_severity
            }
        )

