from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings


class Command(BaseCommand):
    help = 'Reset database by dropping and recreating schema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reset without confirmation',
        )

    def handle(self, *args, **options):
        if not options['force']:
            confirm = input('This will DROP ALL DATA. Are you sure? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write('Operation cancelled.')
                return

        with connection.cursor() as cursor:
            try:
                # Drop all tables
                cursor.execute("DROP SCHEMA public CASCADE;")
                cursor.execute("CREATE SCHEMA public;")
                cursor.execute("GRANT ALL ON SCHEMA public TO postgres;")
                cursor.execute("GRANT ALL ON SCHEMA public TO public;")
                
                self.stdout.write(
                    self.style.SUCCESS('Database reset successfully!')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error resetting database: {str(e)}')
                )
