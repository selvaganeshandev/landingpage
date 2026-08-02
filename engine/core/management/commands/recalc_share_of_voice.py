"""
Recompute share of voice so each domain's players add up.

Shares were written one competitor at a time, each pass building its own market
denominator from Competitor.total_mentions while other competitors in the same
tick were still unprocessed. The rows therefore encode ratios against different
denominators and cannot be reconciled: 17 of 56 domains had a latest snapshot
that did not sum to 100% (Tata Motors 145.7%, one domain 880%), and 486 rows
carried 0% share beside a non-zero mention count.

CompetitorProcessor.recalculate_share_of_voice rewrites a whole domain from one
snapshot of the data. This command applies it to existing rows.

    python manage.py recalc_share_of_voice --dry-run     # report only
    python manage.py recalc_share_of_voice --domain 91   # one domain
    python manage.py recalc_share_of_voice               # every domain

Only the latest timestamp per domain is rewritten — that is what the Share of
Voice page reads. Historical snapshots are left as recorded; they are wrong in
the same way, but rewriting them would invent history against today's mention
counts rather than the counts of the day they describe.
"""
from django.core.management.base import BaseCommand
from django.db.models import Max

from core.competitor_processor import CompetitorProcessor
from shared_models.models import ShareOfVoiceAnalytics


class Command(BaseCommand):
    help = "Recompute share of voice against a single consistent denominator per domain"

    def add_arguments(self, parser):
        parser.add_argument('--domain', type=int, help='Restrict to one domain id')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report which domains are inconsistent without writing anything',
        )
        parser.add_argument(
            '--tolerance',
            type=float,
            default=1.0,
            help='Percentage points a domain may deviate from 100 before it counts as broken',
        )

    def handle(self, *args, **options):
        domain_filter = options.get('domain')
        dry_run = options.get('dry_run')
        tolerance = options.get('tolerance')

        domain_ids = sorted(set(
            ShareOfVoiceAnalytics.objects.values_list('domain_id', flat=True)
        ))
        if domain_filter:
            domain_ids = [d for d in domain_ids if d == domain_filter]
            if not domain_ids:
                self.stdout.write(self.style.WARNING(f'No share data for domain {domain_filter}'))
                return

        processor = CompetitorProcessor()
        broken_before = []
        fixed = 0
        skipped = 0

        for domain_id in domain_ids:
            latest = ShareOfVoiceAnalytics.objects.filter(
                domain_id=domain_id
            ).aggregate(m=Max('timestamp'))['m']
            if not latest:
                continue

            rows = ShareOfVoiceAnalytics.objects.filter(domain_id=domain_id, timestamp=latest)
            before = sum(float(r.share_percentage or 0) for r in rows)
            was_broken = abs(before - 100) > tolerance

            if was_broken:
                broken_before.append((domain_id, round(before, 1), rows.count()))

            if dry_run:
                continue

            result = processor.recalculate_share_of_voice(domain_id, timestamp=latest)
            if not result.get('updated'):
                # No mentions anywhere for this domain — leaving the rows alone
                # is more honest than writing zeros over whatever was recorded.
                skipped += 1
                continue

            after_rows = ShareOfVoiceAnalytics.objects.filter(domain_id=domain_id, timestamp=latest)
            after = sum(float(r.share_percentage or 0) for r in after_rows)
            fixed += 1

            if was_broken:
                self.stdout.write(
                    f'  domain {domain_id}: {before:.1f}% -> {after:.1f}% '
                    f'({after_rows.count()} players)'
                )

        self.stdout.write('')
        self.stdout.write(f'Domains with share data      : {len(domain_ids)}')
        self.stdout.write(
            f'Outside {tolerance}pt of 100% before  : {len(broken_before)}'
        )
        if dry_run:
            for domain_id, total, players in broken_before[:20]:
                self.stdout.write(f'  domain {domain_id}: {total}% across {players} players')
            self.stdout.write(self.style.WARNING('Dry run — nothing written'))
        else:
            self.stdout.write(f'Recalculated                 : {fixed}')
            self.stdout.write(f'Skipped (no mentions)        : {skipped}')
            self.stdout.write(self.style.SUCCESS('Done'))
