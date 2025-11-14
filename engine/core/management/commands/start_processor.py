from django.core.management.base import BaseCommand
from core.domain_processor import DomainProcessor


class Command(BaseCommand):
    help = 'Start the domain processing engine'

    def add_arguments(self, parser):
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run as daemon process',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting domain processing engine...')
        )
        
        processor = DomainProcessor()
        
        if options['daemon']:
            self.stdout.write(
                self.style.WARNING('Running as daemon process...')
            )
        
        try:
            processor.start_processing_loop()
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.SUCCESS('Domain processing engine stopped.')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error in processing engine: {str(e)}')
            )
