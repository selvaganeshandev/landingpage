"""
Release keywords trapped in fallback "General" topics so they can be grouped.

When the grouping model call failed, TopicProcessor used to drop every keyword
into one topic named "General" and stamp last_used_for_topic_generation on each
one. That made the failure permanent: the keywords were consumed, later runs
skipped them, and the domain kept a topic carrying no semantic grouping. 33 of
116 topics in production were created this way.

The fallback no longer does that. This command clears up what it already left
behind: it deletes the General topics and clears the timestamp on their
keywords, so the next topic run regroups them properly.

    python manage.py regroup_general_topics --dry-run    # report only
    python manage.py regroup_general_topics --domain 91  # one domain
    python manage.py regroup_general_topics              # all domains

Only topics named exactly "General" are touched, and only their TopicKeyword
links are removed — the Keyword rows themselves are kept, with the timestamp
cleared. A domain whose keywords are all released will show an empty Topics page
until the next run, which is accurate: it has no valid grouping right now.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from shared_models.models import Keyword, Topic, TopicKeyword


class Command(BaseCommand):
    help = 'Delete fallback "General" topics and free their keywords for regrouping'

    def add_arguments(self, parser):
        parser.add_argument('--domain', type=int, help='Restrict to one domain id')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report what would be released without writing anything',
        )

    def handle(self, *args, **options):
        domain_filter = options.get('domain')
        dry_run = options.get('dry_run')

        topics = Topic.objects.filter(name__iexact='general')
        if domain_filter:
            topics = topics.filter(domain_id=domain_filter)

        if not topics.exists():
            self.stdout.write(self.style.SUCCESS('No "General" topics found — nothing to do'))
            return

        total_topics = 0
        total_keywords = 0

        for topic in topics.select_related('domain'):
            keyword_ids = list(
                TopicKeyword.objects.filter(topic=topic).values_list('keyword_id', flat=True)
            )
            total_topics += 1
            total_keywords += len(keyword_ids)

            self.stdout.write(
                f'  domain {topic.domain_id} ({topic.domain.name[:24]}): '
                f'topic {topic.id} holds {len(keyword_ids)} keyword(s)'
            )

            if dry_run:
                continue

            with transaction.atomic():
                # Clear the stamp first: if the delete fails the keywords are
                # merely eligible again, which is harmless. The reverse order
                # could delete the topic and leave its keywords consumed with no
                # topic to show for them.
                Keyword.objects.filter(id__in=keyword_ids).update(
                    last_used_for_topic_generation=None
                )
                TopicKeyword.objects.filter(topic=topic).delete()
                topic.delete()

        self.stdout.write('')
        self.stdout.write(f'"General" topics found : {total_topics}')
        self.stdout.write(f'Keywords held by them  : {total_keywords}')

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run — nothing written'))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    'Released. The next topic run for each domain will regroup these keywords.'
                )
            )
