"""
Script to clean up SentimentAnalytics records with NULL or empty platform values.
Run with: python manage.py shell < cleanup_null_platforms.py
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'llm_monitor.settings')
django.setup()

from analytics.models import SentimentAnalytics

print("🧹 Cleaning up SentimentAnalytics records with NULL or empty platform...")

# Count records with NULL or empty platform
null_count = SentimentAnalytics.objects.filter(platform__isnull=True).count()
empty_count = SentimentAnalytics.objects.filter(platform='').count()
total_bad = null_count + empty_count

print(f"  Found {null_count} records with NULL platform")
print(f"  Found {empty_count} records with empty string platform")
print(f"  Total records to delete: {total_bad}")

if total_bad > 0:
    # Delete records with NULL platform
    deleted_null, _ = SentimentAnalytics.objects.filter(platform__isnull=True).delete()
    print(f"  ✓ Deleted {deleted_null} records with NULL platform")
    
    # Delete records with empty string platform
    deleted_empty, _ = SentimentAnalytics.objects.filter(platform='').delete()
    print(f"  ✓ Deleted {deleted_empty} records with empty string platform")
    
    print(f"\n✅ Cleanup complete! Deleted {deleted_null + deleted_empty} records total.")
else:
    print("\n✅ No records with NULL or empty platform found. Database is clean!")

# Verify cleanup
remaining_null = SentimentAnalytics.objects.filter(platform__isnull=True).count()
remaining_empty = SentimentAnalytics.objects.filter(platform='').count()

if remaining_null == 0 and remaining_empty == 0:
    print("✅ Verification: All NULL and empty platform records have been removed.")
else:
    print(f"⚠️  Warning: Still found {remaining_null} NULL and {remaining_empty} empty platform records.")

