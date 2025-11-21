#!/usr/bin/env python3
"""
Script to process all competitors for a domain and generate AI insights.
Usage: python3 process_domain_competitors.py <domain_id>
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'llm_monitor.settings')
django.setup()

from competitors.models import Competitor
from domains.models import Domain
from competitors.views import process_competitor_single
from rest_framework.test import APIRequestFactory
from authentication.models import Account

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
        
        # Get or create a super admin user for API calls
        admin_user = Account.objects.filter(role='super_admin').first()
        if not admin_user:
            print("Warning: No super_admin user found. Creating a temporary one...")
            admin_user = Account.objects.create(
                email='temp@admin.com',
                role='super_admin',
                is_active=True
            )
        
        # Create API request factory
        factory = APIRequestFactory()
        
        # Process each competitor
        for comp in competitors:
            print(f"Processing competitor: {comp.name} (ID: {comp.id})")
            print(f"  Current status: {comp.track_status}")
            
            # Create a POST request
            request = factory.post(
                '/api/competitors/process-single/',
                {'competitor_id': comp.id, 'sync': True},
                format='json'
            )
            request.user = admin_user
            
            # Call the view function
            from rest_framework.response import Response
            response = process_competitor_single(request)
            
            comp.refresh_from_db()
            print(f"  New status: {comp.track_status}")
            
            if response.status_code == 200:
                data = response.data
                if data.get('success'):
                    print(f"  ✅ Success: {data.get('message', 'Completed')}")
                    if data.get('processed'):
                        print(f"     Processed: {data.get('processed')} prompts")
                else:
                    print(f"  ❌ Failed: {data.get('error', 'Unknown error')}")
            else:
                print(f"  ❌ Failed: Status {response.status_code}")
                if hasattr(response, 'data'):
                    print(f"     Error: {response.data.get('error', 'Unknown')}")
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
        print("Usage: python3 process_domain_competitors.py <domain_id>")
        print("Example: python3 process_domain_competitors.py 4")
        sys.exit(1)
    
    domain_id = int(sys.argv[1])
    process_domain_competitors(domain_id)

