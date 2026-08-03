"""
Fetch Google search volume for tracked keywords from DataForSEO.

    # what would it cost, without spending anything
    python manage.py fetch_keyword_volume --dry-run

    # backfill every keyword that has no volume yet
    python manage.py fetch_keyword_volume

    # one domain, or a cautious first slice
    python manage.py fetch_keyword_volume --domain 90
    python manage.py fetch_keyword_volume --limit 50

    # re-fetch keywords that already have figures (monthly refresh)
    python manage.py fetch_keyword_volume --refresh

By default only keywords with no volume row are fetched, so re-running is
cheap and safe: a run with nothing new to do makes zero API calls.

Billing is per request, not per keyword — 1,000 keywords cost the same $0.09 as
one — so always prefer a single wide run over many narrow ones.
"""
from django.core.management.base import BaseCommand

from core.volume_processor import sync_keyword_volume


class Command(BaseCommand):
    help = 'Fetch keyword search volume from DataForSEO into SeoKeywordVolume'

    def add_arguments(self, parser):
        parser.add_argument('--domain', type=int, help='Restrict to one domain id')
        parser.add_argument('--limit', type=int, help='Consider at most N keywords')
        parser.add_argument(
            '--refresh', action='store_true',
            help='Include keywords that already have volume (re-fetches everything)',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Report batches and estimated cost without calling the API',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        result = sync_keyword_volume(
            domain_id=options.get('domain'),
            only_missing=not options['refresh'],
            dry_run=dry_run,
            limit=options.get('limit'),
        )

        self.stdout.write(f"Keywords considered : {result['keywords_considered']}")
        self.stdout.write(f"API requests        : {result['requests']}")
        self.stdout.write(f"Estimated cost      : ${result['estimated_cost']:.2f}")

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run — no API calls made, nothing written'))
            return

        self.stdout.write(f"Volume written      : {result['updated']}")
        self.stdout.write(f"No data at Google   : {result['no_data']}")

        if result['failed_batches']:
            self.stdout.write(self.style.ERROR(
                f"Failed batches      : {result['failed_batches']} "
                "(re-run to retry — successful keywords are skipped)"
            ))
        elif result['requests']:
            self.stdout.write(self.style.SUCCESS('Done.'))
        else:
            self.stdout.write(self.style.SUCCESS('Nothing to fetch — every keyword already has volume.'))
