"""Trim the evidence behind old, unclaimed audits.

    manage.py cleanup_audits [--days 30] [--dry-run]

An unclaimed audit whose public link expired more than --days ago loses its
evidence rows (per-prompt answers, sampled pages, keyword ranks) and its cached
crawl/answers in `grounding`; the Audit row, headline scores and report JSON
stay, so the leads table and the public summary still work. Failed audits
older than the same window are deleted outright — they carry nothing anyone
comes back for.

Claimed audits are never touched: they are a project's Day-0 baseline.

Not scheduled anywhere by default. Run it from cron, or by hand.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from audits.models import Audit, AuditKeywordResult, AuditPageResult, AuditPromptResult


class Command(BaseCommand):
    help = 'Remove evidence rows from expired unclaimed audits and delete old failed ones.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30, help='Grace period after expiry (default 30)')
        parser.add_argument('--dry-run', action='store_true', help='Report what would change without changing it')

    def handle(self, *args, **options):
        days = max(0, int(options['days']))
        dry = bool(options['dry_run'])
        cutoff = timezone.now() - timedelta(days=days)

        expired = Audit.objects.filter(
            claimed_domain__isnull=True, status='DONE', expires_at__isnull=False, expires_at__lt=cutoff,
        ).filter(Q(prompt_results__isnull=False) | Q(page_results__isnull=False) | Q(keyword_results__isnull=False)).distinct()
        failed = Audit.objects.filter(claimed_domain__isnull=True, status='FAIL', created_at__lt=cutoff)

        trimmed = 0
        for audit in expired.iterator():
            n = (AuditPromptResult.objects.filter(audit=audit).count() + AuditPageResult.objects.filter(audit=audit).count()
                 + AuditKeywordResult.objects.filter(audit=audit).count())
            self.stdout.write(f"{'would trim' if dry else 'trimming'} audit {audit.pk} ({audit.host}): {n} evidence rows")
            if not dry:
                AuditPromptResult.objects.filter(audit=audit).delete()
                AuditPageResult.objects.filter(audit=audit).delete()
                AuditKeywordResult.objects.filter(audit=audit).delete()
                grounding = dict(audit.grounding or {})
                for key in ('prompts', 'crawl', 'keywords', 'narrative'):
                    grounding.pop(key, None)
                grounding['trimmed_at'] = timezone.now().isoformat()
                audit.grounding = grounding
                audit.save(update_fields=['grounding', 'modified_at'])
            trimmed += 1

        deleted = failed.count()
        for audit in failed.iterator():
            self.stdout.write(f"{'would delete' if dry else 'deleting'} failed audit {audit.pk} ({audit.host})")
        if not dry and deleted:
            failed.delete()

        self.stdout.write(self.style.SUCCESS(f"{'dry run: ' if dry else ''}{trimmed} audits trimmed, {deleted} failed audits deleted"))
