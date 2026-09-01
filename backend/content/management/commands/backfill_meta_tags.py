"""
Management command: backfill_meta_tags
Fills meta_title / meta_description on generated drafts that have none.

Every generation path already produces them (ClaudeContentGenerator
.generate_meta_tags), so gaps come from drafts older than that feature or
from a generation-time failure the generator swallowed - it logs
"Meta tag generation failed" and returns empty strings. One small model
call per draft, billed to the draft's organisation key like generation.

    python manage.py backfill_meta_tags --dry-run
    python manage.py backfill_meta_tags --domain-id 66
    python manage.py backfill_meta_tags --org-id 3 --limit 50
"""
import logging
import time

from django.core.management.base import BaseCommand
from django.db.models import Q

from content.claude_content_generator import ClaudeContentGenerator
from content.models import GeneratedContent

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate missing meta_title / meta_description for existing drafts'

    def add_arguments(self, parser):
        parser.add_argument('--domain-id', type=int, default=None,
                            help='Only drafts of this domain')
        parser.add_argument('--org-id', type=int, default=None,
                            help='Only drafts of this organisation')
        parser.add_argument('--limit', type=int, default=0,
                            help='Stop after N drafts (0 = no limit)')
        parser.add_argument('--sleep', type=float, default=0.5,
                            help='Seconds to wait between model calls')
        parser.add_argument('--dry-run', action='store_true',
                            help='List the drafts that would be filled, change nothing')

    def handle(self, *args, **options):
        qs = (
            GeneratedContent.objects
            .filter(
                Q(meta_title='') | Q(meta_title__isnull=True)
                | Q(meta_description='') | Q(meta_description__isnull=True)
            )
            .exclude(content_html='')
            .exclude(status='planned')
            .select_related('domain')
            .order_by('id')
        )
        if options['domain_id']:
            qs = qs.filter(domain_id=options['domain_id'])
        if options['org_id']:
            qs = qs.filter(domain__organisation_id=options['org_id'])
        rows = list(qs[:options['limit']] if options['limit'] else qs)

        if not rows:
            self.stdout.write('No drafts with missing meta tags.')
            return

        self.stdout.write(f'{len(rows)} draft(s) missing meta tags.')
        if options['dry_run']:
            for content in rows[:50]:
                self.stdout.write(
                    f'  #{content.id} domain={content.domain_id} {content.title[:70]!r}'
                )
            if len(rows) > 50:
                self.stdout.write(f'  ... and {len(rows) - 50} more')
            return

        generators = {}
        filled = failed = skipped = 0
        for content in rows:
            org_id = content.domain.organisation_id
            if org_id not in generators:
                try:
                    generators[org_id] = ClaudeContentGenerator(org_id=org_id)
                except Exception as exc:
                    self.stderr.write(
                        f'org {org_id}: cannot build generator ({exc}); skipping its drafts'
                    )
                    generators[org_id] = None
            generator = generators[org_id]
            if generator is None:
                skipped += 1
                continue

            meta = generator.generate_meta_tags(
                title=content.title,
                content_html=content.content_html,
                keywords=content.keywords or '',
            )
            if not (meta.get('meta_title') or meta.get('meta_description')):
                failed += 1
                self.stderr.write(
                    f'  #{content.id} no meta returned - see the "Meta tag generation '
                    f'failed" warning in the backend log'
                )
                continue

            if not content.meta_title:
                content.meta_title = meta['meta_title']
            if not content.meta_description:
                content.meta_description = meta['meta_description']
            # modified_at deliberately not bumped: a backfill is not an edit
            # and should not reorder anyone's content list.
            content.save(update_fields=['meta_title', 'meta_description'])
            filled += 1
            self.stdout.write(f'  #{content.id} {content.meta_title[:70]!r}')
            if options['sleep']:
                time.sleep(options['sleep'])

        self.stdout.write(
            f'Done: {filled} filled, {failed} failed, {skipped} skipped (no generator).'
        )
