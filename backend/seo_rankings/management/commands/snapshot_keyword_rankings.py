"""
Management command: snapshot_keyword_rankings

Creates daily SeoRankHistory entries from current SeoKeywordRank.rank_now values.
Run via cron or scheduler:  python manage.py snapshot_keyword_rankings
"""
import logging
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from seo_rankings.models import SeoKeywordRank, SeoRankHistory

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Snapshot current keyword rankings into SeoRankHistory for all domains'

    def add_arguments(self, parser):
        parser.add_argument(
            '--domain-id',
            type=int,
            default=None,
            help='Snapshot only a specific domain (default: all domains)',
        )

    def handle(self, *args, **options):
        today = date.today()
        domain_id = options.get('domain_id')

        qs = SeoKeywordRank.objects.filter(
            rank_now__gt=0,  # Only snapshot ranked keywords
        )
        if domain_id:
            qs = qs.filter(domain_id=domain_id)

        keywords = list(qs.values_list('id', 'rank_now'))

        if not keywords:
            self.stdout.write('No ranked keywords found. Nothing to snapshot.')
            return

        # Filter out keywords that already have a snapshot for today
        existing = set(
            SeoRankHistory.objects.filter(
                seo_keyword_rank_id__in=[k[0] for k in keywords],
                snapshot_date=today,
            ).values_list('seo_keyword_rank_id', flat=True)
        )

        to_create = [
            SeoRankHistory(
                seo_keyword_rank_id=kw_id,
                rank_position=rank_now,
                snapshot_date=today,
            )
            for kw_id, rank_now in keywords
            if kw_id not in existing
        ]

        if not to_create:
            self.stdout.write(f'All {len(keywords)} keywords already have snapshots for {today}.')
            return

        with transaction.atomic():
            SeoRankHistory.objects.bulk_create(to_create, ignore_conflicts=True)

        self.stdout.write(self.style.SUCCESS(
            f'Created {len(to_create)} rank snapshots for {today} '
            f'({len(existing)} already existed).'
        ))
