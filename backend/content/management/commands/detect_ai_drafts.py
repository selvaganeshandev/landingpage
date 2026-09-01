"""
Management command: detect_ai_drafts
Runs the AI-generated-text detector over drafts that have never been
scored. The Content Studio only scores a draft when someone clicks
"Detect AI", so most rows carry null until then. Same model, truncation
and fields as POST /content/detect-ai/ (content.ai_detection).

    python manage.py detect_ai_drafts --dry-run
    python manage.py detect_ai_drafts --domain-id 66
    python manage.py detect_ai_drafts --domain-id 66 --recheck   # rescore already-scored drafts too
"""
import logging
import time

from django.core.management.base import BaseCommand, CommandError

from content.ai_detection import (
    AIDetectionError,
    AIDetectionModelLoading,
    detect_ai_text,
    save_detection,
)
from content.models import GeneratedContent

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Score unscored drafts with the AI-generated-text detector'

    def add_arguments(self, parser):
        parser.add_argument('--domain-id', type=int, default=None,
                            help='Only drafts of this domain')
        parser.add_argument('--org-id', type=int, default=None,
                            help='Only drafts of this organisation')
        parser.add_argument('--limit', type=int, default=0,
                            help='Stop after N drafts (0 = no limit)')
        parser.add_argument('--recheck', action='store_true',
                            help='Also rescore drafts that already have a score')
        parser.add_argument('--sleep', type=float, default=1.0,
                            help='Seconds to wait between detector calls (HF rate limits)')
        parser.add_argument('--dry-run', action='store_true',
                            help='List the drafts that would be scored, change nothing')

    def handle(self, *args, **options):
        qs = (
            GeneratedContent.objects
            .exclude(content_html='')
            .exclude(status='planned')
            .order_by('id')
        )
        if not options['recheck']:
            qs = qs.filter(ai_detection_score__isnull=True)
        if options['domain_id']:
            qs = qs.filter(domain_id=options['domain_id'])
        if options['org_id']:
            qs = qs.filter(domain__organisation_id=options['org_id'])
        rows = list(qs[:options['limit']] if options['limit'] else qs)

        if not rows:
            self.stdout.write('No drafts to score.')
            return

        self.stdout.write(f'{len(rows)} draft(s) to score.')
        if options['dry_run']:
            for content in rows[:50]:
                self.stdout.write(
                    f'  #{content.id} domain={content.domain_id} {content.title[:70]!r}'
                )
            if len(rows) > 50:
                self.stdout.write(f'  ... and {len(rows) - 50} more')
            return

        scored = failed = 0
        for content in rows:
            try:
                result = self._detect_with_one_retry(content.content_html)
            except AIDetectionError as exc:
                if 'not configured' in str(exc):
                    raise CommandError(str(exc))
                failed += 1
                self.stderr.write(f'  #{content.id} {exc}')
                continue

            save_detection(content, result)
            scored += 1
            self.stdout.write(
                f"  #{content.id} {result['label']} ai={result['ai_score']:.1f} "
                f"human={result['human_score']:.1f}"
            )
            if options['sleep']:
                time.sleep(options['sleep'])

        self.stdout.write(f'Done: {scored} scored, {failed} failed.')

    @staticmethod
    def _detect_with_one_retry(html):
        try:
            return detect_ai_text(html)
        except AIDetectionModelLoading as exc:
            wait = min(float(exc.estimated_time or 20), 60.0)
            logger.info("Detector model loading; waiting %.0fs", wait)
            time.sleep(wait)
            return detect_ai_text(html)
