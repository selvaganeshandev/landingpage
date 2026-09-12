"""
Rebuild today's sentiment snapshot for every domain from the mentions on file.

The Sentiment page reads SentimentAnalytics, which is only ever written when a
prompt group finishes processing. Two things left it empty for 40 of 74
production domains while the underlying sentiment sat fully scored in
PromptAnalytics:

  - the weekly sweep has been off since 2026-07-23, so nothing has been
    re-aggregated and 28 domains aged past the page's 30-day window; and
  - the writer skipped any group without a theme, so 12 domains whose uploaded
    prompts landed in one untitled group (Kotak Bank, Kia Motors, Shobha IVF
    ...) never had a row written at all.

This command calls the same writer the engine uses, once per (domain, theme),
so the rows it produces are exactly what a fresh processing run would produce.
It reads PromptAnalytics and writes SentimentAnalytics; it makes no AI calls
and spends no credits.

    python manage.py rebuild_sentiment_analytics --dry-run     # report only
    python manage.py rebuild_sentiment_analytics --domain 173  # one domain
    python manage.py rebuild_sentiment_analytics               # every domain

Rows are keyed on today's date, so re-running the command on the same day is
idempotent, and history for earlier dates is left exactly as recorded.
"""
from datetime import date

from django.core.management.base import BaseCommand
from django.db.models import Count, Q

from core.prompt_analytics_processor import (
    PromptAnalyticsProcessor,
    sentiment_theme_for,
)
from shared_models.models import Domain, PromptAnalytics, PromptGroup, SentimentAnalytics


class Command(BaseCommand):
    help = "Rebuild today's SentimentAnalytics rows from scored mentions already stored"

    def add_arguments(self, parser):
        parser.add_argument('--domain', type=int, help='Restrict to one domain id')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report what would be written without touching the database',
        )

    def handle(self, *args, **options):
        domain_filter = options.get('domain')
        dry_run = options.get('dry_run')
        today = date.today()

        domains = Domain.objects.all().order_by('id')
        if domain_filter:
            domains = domains.filter(id=domain_filter)
            if not domains.exists():
                self.stdout.write(self.style.WARNING(f'No domain with id {domain_filter}'))
                return

        # The processor's constructor builds LLM clients lazily and only needs
        # the concurrency figure; nothing in the sentiment writer calls out.
        processor = PromptAnalyticsProcessor(max_concurrent_prompts=1)

        written_domains = 0
        skipped_no_mentions = 0
        rows_before_total = SentimentAnalytics.objects.filter(snapshot_date=today).count()
        report = []

        for domain in domains:
            mentions = PromptAnalytics.objects.filter(
                prompt__group__domain=domain,
                prompt__track_status='COMP',
                is_mention=True,
                is_published=True,
            ).count()
            if mentions == 0:
                skipped_no_mentions += 1
                continue

            # One representative group per sentiment theme. The writer
            # aggregates across every group sharing that theme, so calling it
            # for one group of each is enough — and untitled groups all
            # resolve to the fallback theme, so one of those covers them all.
            seen = set()
            representatives = []
            for group in PromptGroup.objects.filter(domain=domain).order_by('id'):
                key = sentiment_theme_for(group)
                if key in seen:
                    continue
                seen.add(key)
                representatives.append(group)

            before = SentimentAnalytics.objects.filter(domain=domain, snapshot_date=today).count()

            if not dry_run:
                for group in representatives:
                    processor._update_sentiment_analytics_for_theme(group, None)

            after = SentimentAnalytics.objects.filter(domain=domain, snapshot_date=today).count()
            written_domains += 1
            report.append((domain.name, mentions, len(representatives), before, after))

        self.stdout.write('')
        self.stdout.write(f"{'domain':<28}{'mentions':>9}{'themes':>8}  {'rows today'}")
        self.stdout.write('-' * 62)
        for name, mentions, themes, before, after in report:
            rows = f'{before} -> {after}' if not dry_run else f'{before} (would write)'
            self.stdout.write(f'{name[:27]:<28}{mentions:>9}{themes:>8}  {rows}')

        self.stdout.write('')
        self.stdout.write(f'Domains with mentions        : {written_domains}')
        self.stdout.write(f'Skipped (no mentions)        : {skipped_no_mentions}')
        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run — nothing written'))
        else:
            rows_after_total = SentimentAnalytics.objects.filter(snapshot_date=today).count()
            self.stdout.write(
                f"Rows dated {today}       : {rows_before_total} -> {rows_after_total}"
            )
            self.stdout.write(self.style.SUCCESS('Done'))
