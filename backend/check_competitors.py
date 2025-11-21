#!/usr/bin/env python3
"""
Script to check competitors in the database
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
print("Checking Competitors in Database")
print("=" * 60)

# Check all competitors
competitors = Competitor.objects.all()
print(f"\n📊 Total competitors in database: {competitors.count()}")

if competitors.count() > 0:
    print("\nCompetitors found:")
    for c in competitors:
        print(f"  - {c.name} (ID: {c.id})")
        print(f"    Domain: {c.domain.name} (ID: {c.domain.id})")
        print(f"    URL: {c.url}")
        print(f"    Created: {c.created_at}")
        print()
else:
    print("\n❌ No competitors found in database.")
    print("\nAvailable domains:")
    domains = Domain.objects.all()
    for d in domains:
        print(f"  - {d.name} (ID: {d.id})")

print("=" * 60)
