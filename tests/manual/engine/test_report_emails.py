"""
Test script to generate and send all 4 report types via email
Sends to: sarvanan@appkodes.com
"""
import os
import sys
import django
from datetime import datetime, timedelta
from pathlib import Path

# Setup Django
ENGINE_ROOT = Path(__file__).resolve().parents[3] / 'engine'
sys.path.insert(0, str(ENGINE_ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'llm_monitor_engine.settings')
django.setup()

from django.utils import timezone
from shared_models.models import ScheduledReport, ReportTemplate, Domain, Organisation, Account
from core.report_email_processor import ReportEmailProcessor


def test_all_report_types():
    """Create and send test emails for all 4 report types"""

    print("="*70)
    print("TESTING REPORT EMAIL SYSTEM - All 4 Report Types")
    print("="*70)
    print(f"Recipient: sarvanan@appkodes.com")
    print(f"Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    # Get first active domain and organization (you can change these IDs as needed)
    try:
        domain = Domain.objects.first()
        organisation = Organisation.objects.first()
        admin_user = Account.objects.filter(role__in=['admin', 'super_admin']).first()

        if not domain or not organisation:
            print("ERROR: No domain or organisation found in database")
            print("Please ensure you have at least one domain and organisation")
            return

        print(f"\nUsing Domain: {domain.name} (ID: {domain.id})")
        print(f"Using Organisation: {organisation.name} (ID: {organisation.id})")
        print(f"Created by: {admin_user.email if admin_user else 'System'}")
        print()

    except Exception as e:
        print(f"ERROR: Failed to get domain/organisation: {e}")
        return

    # Get all 4 report templates
    templates = ReportTemplate.objects.filter(is_active=True).order_by('id')

    if templates.count() < 4:
        print(f"WARNING: Only {templates.count()} templates found. Expected 4.")
        print("Run: python backend/seed_report_templates.py")
        return

    print(f"Found {templates.count()} report templates:")
    for template in templates:
        print(f"  - {template.name}")
    print()

    # Create scheduled reports for each template
    scheduled_reports = []
    recipient_email = "sarvanan@appkodes.com"

    for idx, template in enumerate(templates, 1):
        print(f"[{idx}/4] Creating scheduled report: {template.name}")

        # Delete any existing test reports for this template
        ScheduledReport.objects.filter(
            name__startswith=f"TEST - {template.name}",
            domain=domain
        ).delete()

        # Create new scheduled report
        scheduled_report = ScheduledReport.objects.create(
            organisation=organisation,
            domain=domain,
            name=f"TEST - {template.name} - {timezone.now().strftime('%Y%m%d_%H%M%S')}",
            description=f"Automated test report for {template.name} template",
            template=template,
            frequency='once',  # One-time report
            schedule_time=timezone.now().time(),
            schedule_day=timezone.now().day,
            formats=['PDF', 'Email'],  # Generate PDF and send email
            recipients=[recipient_email],
            sections=template.sections,
            status='active',
            next_run_at=timezone.now(),  # Run immediately
            created_by=admin_user
        )

        scheduled_reports.append(scheduled_report)
        print(f"  ✓ Created ScheduledReport ID: {scheduled_report.id}")

    print(f"\n{'='*70}")
    print(f"Created {len(scheduled_reports)} scheduled reports")
    print(f"{'='*70}\n")

    # Process reports and send emails
    print("Processing reports and sending emails...")
    print("-"*70)

    processor = ReportEmailProcessor()

    for idx, scheduled_report in enumerate(scheduled_reports, 1):
        template_name = scheduled_report.template.name
        print(f"\n[{idx}/4] Processing: {template_name}")
        print(f"  Report ID: {scheduled_report.id}")
        print(f"  Recipient: {recipient_email}")

        try:
            result = processor._process_single_scheduled_report(scheduled_report)

            if result['success']:
                print(f"  ✓ SUCCESS: {result['message']}")
            else:
                print(f"  ✗ FAILED: {result['message']}")

        except Exception as e:
            print(f"  ✗ ERROR: {str(e)}")

    print(f"\n{'='*70}")
    print("REPORT EMAIL TEST COMPLETED")
    print(f"{'='*70}")
    print(f"\n📧 Check inbox at: sarvanan@appkodes.com")
    print(f"You should receive 4 emails (one for each report type):")
    print(f"  1. Executive Dashboard")
    print(f"  2. Detailed Analytics")
    print(f"  3. Competitor Focus")
    print(f"  4. Content Strategy")
    print(f"\n{'='*70}\n")


if __name__ == '__main__':
    try:
        test_all_report_types()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
