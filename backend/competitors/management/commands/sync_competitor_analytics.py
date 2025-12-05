"""
Management command to sync competitor prompt analytics data.
This command processes PromptAnalytics records and creates/updates
CompetitorPromptAnalytics with accurate mention counts and citations.
"""
from django.core.management.base import BaseCommand
from competitors.utils import sync_competitor_prompt_analytics


class Command(BaseCommand):
    help = 'Sync competitor prompt analytics from PromptAnalytics data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--domain-id',
            type=int,
            help='Sync only for a specific domain ID',
        )
        parser.add_argument(
            '--prompt-id',
            type=int,
            help='Sync only for a specific prompt ID',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of records to process in each batch (default: 100)',
        )

    def handle(self, *args, **options):
        domain_id = options.get('domain_id')
        prompt_id = options.get('prompt_id')
        batch_size = options.get('batch_size')

        self.stdout.write(self.style.SUCCESS('Starting competitor analytics sync...'))

        if domain_id:
            self.stdout.write(f'Filtering by domain_id: {domain_id}')
        if prompt_id:
            self.stdout.write(f'Filtering by prompt_id: {prompt_id}')

        self.stdout.write(f'Batch size: {batch_size}')
        self.stdout.write('')

        # Run the sync
        stats = sync_competitor_prompt_analytics(
            domain_id=domain_id,
            prompt_id=prompt_id,
            batch_size=batch_size
        )

        # Display results
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Sync completed!'))
        self.stdout.write('')
        self.stdout.write(f'  Processed prompts: {stats["processed_prompts"]}')
        self.stdout.write(self.style.SUCCESS(f'  Created: {stats["created"]}'))
        self.stdout.write(self.style.SUCCESS(f'  Updated: {stats["updated"]}'))
        self.stdout.write(self.style.WARNING(f'  Skipped: {stats["skipped"]}'))

        if stats['errors'] > 0:
            self.stdout.write(self.style.ERROR(f'  Errors: {stats["errors"]}'))
        else:
            self.stdout.write(f'  Errors: {stats["errors"]}')

        self.stdout.write('')
