#!/usr/bin/env python3
"""
Script to process all competitors for a domain from engine context.
Usage: python3 process_domain.py <domain_id>
"""
import os
import sys
import django

# Setup Django for engine
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'llm_monitor_engine.settings')
django.setup()

from shared_models.models import Competitor, Domain
from core.competitor_processor import CompetitorProcessor

def process_domain_competitors(domain_id):
    """Process all competitors for a domain"""
    try:
        domain = Domain.objects.get(id=domain_id)
        print(f"Processing competitors for domain: {domain.name} (ID: {domain_id})")
        
        # Get all competitors for this domain
        competitors = Competitor.objects.filter(domain=domain)
        print(f"Found {competitors.count()} competitors\n")
        
        if competitors.count() == 0:
            print("No competitors found for this domain.")
            return
        
        # Initialize processor
        processor = CompetitorProcessor()
        
        # Process each competitor
        for comp in competitors:
            print(f"Processing competitor: {comp.name} (ID: {comp.id})")
            print(f"  Current status: {comp.track_status}")
            
            result = processor.process_competitor(comp)
            
            comp.refresh_from_db()
            print(f"  New status: {comp.track_status}")
            
            if result.get('scheduled') and result.get('status') == 'completed':
                print(f"  ✅ Success: Processed {result.get('processed', 0)} prompts")
                if result.get('failed', 0) > 0:
                    print(f"  ⚠️  Failed: {result.get('failed', 0)} prompts")
            else:
                print(f"  ❌ Failed: {result.get('error', 'Unknown error')}")
            print()
        
        print("✅ Processing complete! AI insights should now be generated.")
        print(f"\nCheck insights at: GET /competitors/competitive-insights?domain_id={domain_id}")
        
    except Domain.DoesNotExist:
        print(f"Error: Domain with ID {domain_id} not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 process_domain.py <domain_id>")
        print("Example: python3 process_domain.py 4")
        sys.exit(1)
    
    domain_id = int(sys.argv[1])
    process_domain_competitors(domain_id)

