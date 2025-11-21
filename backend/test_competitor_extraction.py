"""
Test script for competitor extraction
Run this to manually test the competitor extraction service
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'llm_monitor.settings')
django.setup()

from competitors.services import CompetitorExtractionService
from domains.models import Domain


def test_competitor_extraction(domain_id=None):
    """
    Test competitor extraction for a domain

    Args:
        domain_id: Optional domain ID. If not provided, will test on first available domain
    """
    if domain_id:
        try:
            domain = Domain.objects.get(id=domain_id)
        except Domain.DoesNotExist:
            print(f"Domain with ID {domain_id} not found")
            return
    else:
        # Get first domain with COMP status
        domain = Domain.objects.filter(processing_status='COMP').first()
        if not domain:
            print("No completed domains found. Please process a domain first.")
            return

    print(f"\n{'='*60}")
    print(f"Testing Competitor Extraction")
    print(f"{'='*60}")
    print(f"Domain: {domain.name} (ID: {domain.id})")
    print(f"Status: {domain.processing_status}")
    print(f"{'='*60}\n")

    # Run extraction
    service = CompetitorExtractionService(domain)
    created_count, competitor_names = service.extract_and_create_competitors()

    print(f"\n{'='*60}")
    print(f"Results")
    print(f"{'='*60}")
    print(f"Created: {created_count} new competitors")
    if competitor_names:
        print(f"Competitors: {', '.join(competitor_names)}")
    print(f"{'='*60}\n")

    # Show all competitors for this domain
    from competitors.models import Competitor
    all_competitors = Competitor.objects.filter(domain=domain).order_by('-total_mentions')

    print(f"All Competitors for {domain.name}:")
    print(f"{'-'*60}")
    for comp in all_competitors:
        print(f"  • {comp.name}: {comp.total_mentions} mentions")
        print(f"    URL: {comp.url}")
        print(f"    Status: {comp.track_status}")
    print(f"{'-'*60}\n")


if __name__ == "__main__":
    import sys

    domain_id = None
    if len(sys.argv) > 1:
        try:
            domain_id = int(sys.argv[1])
        except ValueError:
            print("Invalid domain ID. Please provide a valid integer.")
            sys.exit(1)

    test_competitor_extraction(domain_id)
