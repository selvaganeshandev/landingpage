"""
Test script to verify misinformation automation status
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'llm_monitor.settings')
django.setup()

from domains.models import Domain
from misinformation.models import MisinformationScan, CitationURL, MisinformationAlert
from prompts.models import Prompt, PromptAnalytics

def check_domain_status():
    """Check status of all domains"""
    print("=" * 80)
    print("DOMAIN STATUS CHECK")
    print("=" * 80)

    domains = Domain.objects.all().order_by('-created_at')

    for domain in domains:
        print(f"\n{'=' * 80}")
        print(f"Domain: {domain.name} (ID: {domain.id})")
        print(f"URL: {domain.url}")
        print(f"Processing Status: {domain.processing_status}")
        print(f"Misinformation Scan Status: {domain.misinformation_scan_status}")
        print(f"Last Scan: {domain.last_misinformation_scan_at}")

        # Count prompts
        prompt_count = Prompt.objects.filter(group__domain=domain).count()
        print(f"\nPrompts Generated: {prompt_count}")

        if prompt_count > 0:
            # Count completed analytics
            completed_analytics = PromptAnalytics.objects.filter(
                prompt__group__domain=domain,
                track_status='COMP'
            ).count()

            # Count analytics with mentions
            mention_analytics = PromptAnalytics.objects.filter(
                prompt__group__domain=domain,
                track_status='COMP',
                is_mention=True
            ).count()

            print(f"Completed Analytics: {completed_analytics}")
            print(f"Analytics with Brand Mentions: {mention_analytics}")

        # Count scans
        scan_count = MisinformationScan.objects.filter(domain=domain).count()
        print(f"\nMisinformation Scans: {scan_count}")

        if scan_count > 0:
            recent_scan = MisinformationScan.objects.filter(domain=domain).order_by('-created_at').first()
            print(f"  Latest Scan Status: {recent_scan.status}")
            print(f"  Started: {recent_scan.started_at}")
            print(f"  Completed: {recent_scan.completed_at}")
            print(f"  Prompts Scanned: {recent_scan.total_prompts_scanned}")
            print(f"  Citations Found: {recent_scan.total_citations_found}")
            print(f"  Alerts Generated: {recent_scan.total_alerts_generated}")

        # Count citations and alerts
        citation_count = CitationURL.objects.filter(domain=domain).count()
        alert_count = MisinformationAlert.objects.filter(domain=domain).count()

        print(f"\nTotal Citations: {citation_count}")
        print(f"Total Alerts: {alert_count}")

        # Determine if automation is working
        print(f"\n{'─' * 80}")
        if domain.processing_status == 'FAIL':
            print("❌ STATUS: Domain processing FAILED")
            print("   → Automation cannot run until domain processing succeeds")
        elif domain.processing_status == 'COMP':
            if mention_analytics > 0:
                print("✓ STATUS: Domain is ready for misinformation scanning")
                if scan_count > 0:
                    print("✓ AUTOMATION: Working! Scans have been triggered")
                else:
                    print("⚠ AUTOMATION: Ready but no scans run yet (may still be processing)")
            else:
                print("⚠ STATUS: Domain completed but no brand mentions found")
                print("   → Misinformation scans only trigger when brand is mentioned")
        else:
            print(f"⏳ STATUS: Domain processing in progress ({domain.processing_status})")
            print("   → Automation will run after processing completes")

    print(f"\n{'=' * 80}")
    print("\nAUTOMATION SUMMARY:")
    print("─" * 80)
    print("Misinformation scanning is automated via Django signals in:")
    print("  • backend/misinformation/signals.py")
    print("  • Triggers automatically when PromptAnalytics is saved")
    print("  • Conditions: track_status='COMP' AND is_mention=True")
    print("  • Runs in background thread (non-blocking)")
    print(f"{'=' * 80}\n")

if __name__ == '__main__':
    check_domain_status()
