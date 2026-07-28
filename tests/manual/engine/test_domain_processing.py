"""
Test script for domain processing and metric snapshot creation
Run this to test domain processing and verify metric snapshots are created
"""
import os
import sys
import django
from pathlib import Path

# Setup Django
ENGINE_ROOT = Path(__file__).resolve().parents[3] / 'engine'
sys.path.insert(0, str(ENGINE_ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'llm_monitor_engine.settings')
django.setup()

from shared_models.models import Domain, PromptMetricSnapshot, PromptAnalytics, PromptGroup
from core.domain_processor import DomainProcessor
from core.prompt_analytics_processor import PromptAnalyticsProcessor
from django.utils import timezone
from datetime import date

def test_domain_processing(domain_id=None):
    """Test domain processing and verify metric snapshots are created"""
    print("=" * 80)
    print("TESTING DOMAIN PROCESSING AND METRIC SNAPSHOT CREATION")
    print("=" * 80)
    
    # Get or create a test domain
    if domain_id:
        try:
            domain = Domain.objects.get(id=domain_id)
            print(f"Using existing domain: {domain.name} (ID: {domain.id})")
        except Domain.DoesNotExist:
            print(f"Domain {domain_id} not found. Creating new domain...")
            domain = None
    else:
        # Find a domain to test with
        domain = Domain.objects.filter(processing_status='INIT').first()
        if not domain:
            domain = Domain.objects.first()
    
    if not domain:
        print("ERROR: No domain found. Please create a domain first.")
        return
    
    print(f"\nTesting with domain: {domain.name} (ID: {domain.id})")
    print(f"Current status: {domain.processing_status}")
    
    # Check existing metric snapshots
    initial_count = PromptMetricSnapshot.objects.count()
    print(f"\nInitial PromptMetricSnapshot count: {initial_count}")
    
    # Check existing analytics
    analytics_count = PromptAnalytics.objects.filter(
        prompt__group__domain=domain,
        prompt__track_status='COMP'
    ).count()
    print(f"Existing completed analytics for domain: {analytics_count}")
    
    if analytics_count == 0:
        print("\nNo completed analytics found. Processing domain first...")
        
        # Process domain
        processor = DomainProcessor()
        processor.process_domain(domain.id)
        
        # Wait a bit for processing
        import time
        print("Waiting for domain processing to complete...")
        time.sleep(5)
        
        # Refresh domain
        domain.refresh_from_db()
        print(f"Domain processing status: {domain.processing_status}")
        
        if domain.processing_status != 'COMP':
            print("WARNING: Domain processing may not be complete yet.")
    
    # Check analytics again
    analytics_count = PromptAnalytics.objects.filter(
        prompt__group__domain=domain,
        prompt__track_status='COMP'
    ).count()
    print(f"\nCompleted analytics for domain: {analytics_count}")
    
    if analytics_count == 0:
        print("ERROR: No completed analytics found. Cannot create metric snapshots.")
        return
    
    # Manually trigger metric snapshot creation
    print("\nManually triggering metric snapshot creation...")
    try:
        # Get all groups for this domain
        groups = PromptGroup.objects.filter(domain=domain, track_status='COMP')
        
        if not groups.exists():
            print("No completed groups found. Processing prompts first...")
            # Process prompts
            prompt_processor = PromptAnalyticsProcessor(max_concurrent_prompts=5)
            for group in groups:
                prompts = group.prompts.filter(track_status__in=['INIT', 'SCHD', 'PROC'])
                for prompt in prompts:
                    try:
                        result = prompt_processor.process_single_prompt(prompt.id)
                        print(f"Processed prompt {prompt.id}: {result.get('status', 'unknown')}")
                    except Exception as e:
                        print(f"Error processing prompt {prompt.id}: {str(e)}")
        
        # Trigger aggregation for each group
        prompt_processor = PromptAnalyticsProcessor(max_concurrent_prompts=5)
        for group in groups:
            print(f"\nAggregating group {group.id}...")
            try:
                prompt_processor._check_and_aggregate_group(group)
                print(f"Group {group.id} aggregated successfully")
            except Exception as e:
                print(f"Error aggregating group {group.id}: {str(e)}")
                import traceback
                traceback.print_exc()
        
        # Check final count
        final_count = PromptMetricSnapshot.objects.count()
        print(f"\nFinal PromptMetricSnapshot count: {final_count}")
        print(f"New snapshots created: {final_count - initial_count}")
        
        # Show some sample snapshots
        if final_count > initial_count:
            print("\nSample snapshots created:")
            snapshots = PromptMetricSnapshot.objects.filter(
                prompt__group__domain=domain
            ).order_by('-created_at')[:5]
            for snapshot in snapshots:
                print(f"  - Prompt {snapshot.prompt.id}, Platform: {snapshot.platform}, "
                      f"Date: {snapshot.snapshot_date}, Mentions: {snapshot.mentions}")
        else:
            print("\nWARNING: No new snapshots were created!")
            print("Check the logs/metric_snapshots.log file for details.")
        
    except Exception as e:
        print(f"ERROR during metric snapshot creation: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print(f"\nCheck logs/metric_snapshots.log for detailed logging")
    print(f"Check logs/engine.log for general engine logs")

if __name__ == '__main__':
    import sys
    domain_id = int(sys.argv[1]) if len(sys.argv) > 1 else None
    test_domain_processing(domain_id)

