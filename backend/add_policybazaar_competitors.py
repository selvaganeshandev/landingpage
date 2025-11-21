#!/usr/bin/env python3
"""
Script to add competitors for policybazaar.com
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'llm_monitor.settings')
django.setup()

from competitors.models import Competitor
from domains.models import Domain

print("=" * 60)
print("Adding Competitors for PolicyBazaar.com")
print("=" * 60)

try:
    # Get policybazaar domain
    domain = Domain.objects.get(id=2)
    print(f"\n📍 Domain: {domain.name} (ID: {domain.id})")

    # Define competitors for PolicyBazaar
    competitors_data = [
        {
            'name': 'Acko',
            'url': 'https://www.acko.com/',
        },
        {
            'name': 'Digit Insurance',
            'url': 'https://www.godigit.com/',
        },
        {
            'name': 'HDFC Ergo',
            'url': 'https://www.hdfcergo.com/',
        },
    ]

    print(f"\n📊 Adding {len(competitors_data)} competitors...\n")

    created_count = 0
    for comp_data in competitors_data:
        competitor, created = Competitor.objects.get_or_create(
            domain=domain,
            name=comp_data['name'],
            defaults={
                'url': comp_data['url'],
                'track_status': 'INIT'
            }
        )

        if created:
            print(f"✅ Created: {competitor.name}")
            created_count += 1
        else:
            print(f"ℹ️  Already exists: {competitor.name}")

    print(f"\n🎉 Done! Created {created_count} new competitor(s)")
    print(f"💡 Total competitors for {domain.name}: {Competitor.objects.filter(domain=domain).count()}")

except Domain.DoesNotExist:
    print(f"\n❌ Domain with ID 2 not found")
    print("\nAvailable domains:")
    for d in Domain.objects.all():
        print(f"  - {d.name} (ID: {d.id})")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("=" * 60)
