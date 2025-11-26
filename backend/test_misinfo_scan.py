#!/usr/bin/env python
"""
Test script for misinformation scanning on Airbnb domain
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'llm_monitor.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from domains.models import Domain
from prompts.models import PromptAnalytics
from misinformation.models import MisinformationScan, CitationURL, MisinformationAlert
from misinformation.tasks import MisinformationScanner
from django.utils import timezone

def test_airbnb_scan():
    print("=" * 60)
    print("MISINFORMATION SCAN TEST - Airbnb US")
    print("=" * 60)

    # Find Airbnb domain
    try:
        domain = Domain.objects.get(name__icontains='airbnb')
        print(f"\n✓ Found domain: {domain.name} (ID: {domain.id})")
        print(f"  URL: {domain.url}")
        print(f"  Current scan status: {domain.misinformation_scan_status}")
    except Domain.DoesNotExist:
        print("✗ Airbnb domain not found!")
        return

    # Check prompt analytics
    pa_qs = PromptAnalytics.objects.filter(
        prompt__group__domain_id=domain.id,
        track_status='COMP',
        is_mention=True
    ).select_related('prompt', 'prompt__group')

    print(f"\n--- Prompt Analytics to scan: {pa_qs.count()} ---")

    for i, pa in enumerate(pa_qs[:3]):  # Show first 3
        print(f"\n  [{i+1}] PromptAnalytics ID: {pa.id}")
        print(f"      Prompt: {pa.prompt.prompt[:50]}...")
        print(f"      Context summary length: {len(pa.context_summary or '')}")
        print(f"      Citation list: {pa.citation_list}")

    if pa_qs.count() == 0:
        print("\n✗ No prompt analytics to scan!")
        return

    # Test URL extraction on first prompt analytics
    print("\n--- Testing URL Extraction ---")
    from misinformation.services import URLExtractor
    extractor = URLExtractor()

    first_pa = pa_qs.first()
    response_text = first_pa.context_summary or ""
    citation_list = first_pa.citation_list or []

    print(f"  Response text length: {len(response_text)}")
    print(f"  Citation list: {citation_list}")

    urls = extractor.extract_all(response_text, citation_list)
    print(f"  Extracted URLs: {len(urls)}")
    for url_data in urls[:5]:
        print(f"    - {url_data['url']}")

    # Test link validation on first URL
    if urls:
        print("\n--- Testing Link Validation ---")
        from misinformation.services import LinkValidator
        validator = LinkValidator()

        test_url = urls[0]['url']
        print(f"  Testing: {test_url}")
        is_valid, status_code, error = validator.validate(test_url)
        print(f"  Result: valid={is_valid}, status={status_code}, error={error}")

    # Test crawling
    if urls:
        print("\n--- Testing Web Crawling ---")
        from misinformation.services import WebCrawler
        crawler = WebCrawler()

        test_url = urls[0]['url']
        print(f"  Crawling: {test_url}")
        html, status, error = crawler.crawl(test_url)
        print(f"  Result: status={status}, error={error}, html_length={len(html or '')}")

        if html:
            print("\n--- Testing Content Parsing ---")
            from misinformation.services import ContentParser
            parser = ContentParser()

            parsed = parser.parse(html, test_url)
            print(f"  Title: {parsed['page_title'][:50]}..." if parsed['page_title'] else "  Title: None")
            print(f"  Text length: {len(parsed['extracted_text'])}")
            print(f"  Text preview: {parsed['extracted_text'][:100]}..." if parsed['extracted_text'] else "  Text: None")

    # Now run actual scan
    print("\n" + "=" * 60)
    print("RUNNING ACTUAL SCAN")
    print("=" * 60)

    # Clear any running scans first
    MisinformationScan.objects.filter(domain=domain, status='running').update(
        status='failed',
        error_message='Cleared for test',
        completed_at=timezone.now()
    )

    scanner = MisinformationScanner(domain.id)
    print(f"\nScanner initialized for domain: {scanner.domain.name}")

    try:
        print("\nStarting scan...")
        scan = scanner.run()

        print(f"\n✓ Scan completed!")
        print(f"  Scan ID: {scan.id}")
        print(f"  Status: {scan.status}")
        print(f"  Prompts scanned: {scan.total_prompts_scanned}")
        print(f"  Citations found: {scan.total_citations_found}")
        print(f"  Alerts generated: {scan.total_alerts_generated}")

        # Show alerts
        alerts = MisinformationAlert.objects.filter(scan=scan)
        if alerts.exists():
            print(f"\n--- Alerts Created ---")
            for alert in alerts:
                print(f"  - [{alert.severity}] {alert.alert_type}: {alert.explanation[:50]}...")

        # Update domain status
        domain.refresh_from_db()
        print(f"\nDomain scan status: {domain.misinformation_scan_status}")

    except Exception as e:
        print(f"\n✗ Scan failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_airbnb_scan()
