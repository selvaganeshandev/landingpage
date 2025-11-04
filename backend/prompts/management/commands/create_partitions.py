"""
Management command to create database partitions for time-series tables.

Usage:
    python manage.py create_partitions
    python manage.py create_partitions --months 6
    python manage.py create_partitions --table prompt_analytics
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class Command(BaseCommand):
    help = 'Create monthly partitions for time-series analytics tables'

    def add_arguments(self, parser):
        parser.add_argument(
            '--months',
            type=int,
            default=3,
            help='Number of future months to create partitions for (default: 3)'
        )
        parser.add_argument(
            '--table',
            type=str,
            choices=[
                'prompt_analytics',
                'competitor_analytics',
                'topic_analytics',
                'sentiment_analytics',
                'share_of_voice_analytics',
                'all'
            ],
            default='all',
            help='Specific table to create partitions for (default: all)'
        )

    def handle(self, *args, **options):
        months_ahead = options['months']
        table_filter = options['table']
        
        # Define tables to partition
        tables = {
            'prompt_analytics': 'created_at',
            'competitor_analytics': 'timestamp',
            'topic_analytics': 'timestamp',
            'sentiment_analytics': 'timestamp',
            'share_of_voice_analytics': 'timestamp',
        }
        
        # Filter if specific table requested
        if table_filter != 'all':
            tables = {table_filter: tables[table_filter]}
        
        self.stdout.write(
            self.style.SUCCESS(f'\n🚀 Creating partitions for next {months_ahead} months...\n')
        )
        
        total_created = 0
        total_exists = 0
        
        for table_name, date_column in tables.items():
            created, exists = self.create_partitions_for_table(
                table_name, date_column, months_ahead
            )
            total_created += created
            total_exists += exists
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Summary:\n'
                f'  - Created: {total_created} new partitions\n'
                f'  - Already exist: {total_exists} partitions\n'
            )
        )

    def create_partitions_for_table(self, table_name, date_column, months_ahead):
        """Create partitions for a specific table"""
        
        self.stdout.write(f'\n📊 Processing table: {table_name}')
        
        created_count = 0
        exists_count = 0
        
        # Start from current month
        current_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Go back 1 month to ensure we have partition for any recent data
        start_date = current_date - relativedelta(months=1)
        
        with connection.cursor() as cursor:
            # Create partitions for past 1 month + next N months
            for i in range(months_ahead + 2):
                month_start = start_date + relativedelta(months=i)
                month_end = month_start + relativedelta(months=1)
                
                partition_name = f"{table_name}_{month_start.strftime('%Y_%m')}"
                
                # Check if partition already exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_tables
                        WHERE schemaname = 'public'
                        AND tablename = %s
                    );
                """, [partition_name])
                
                exists = cursor.fetchone()[0]
                
                if exists:
                    self.stdout.write(
                        self.style.WARNING(f'  ⚠ {partition_name} already exists')
                    )
                    exists_count += 1
                    continue
                
                # Create the partition
                try:
                    sql = f"""
                        CREATE TABLE {partition_name} PARTITION OF {table_name}
                        FOR VALUES FROM ('{month_start.strftime('%Y-%m-%d')}') 
                                     TO ('{month_end.strftime('%Y-%m-%d')}');
                    """
                    cursor.execute(sql)
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✓ Created {partition_name} '
                            f'({month_start.strftime("%b %Y")})'
                        )
                    )
                    created_count += 1
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ Failed to create {partition_name}: {str(e)}')
                    )
        
        return created_count, exists_count

    def list_existing_partitions(self, table_name):
        """List all existing partitions for a table"""
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    child.relname AS partition_name,
                    pg_size_pretty(pg_total_relation_size(child.oid)) AS size
                FROM pg_inherits
                JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
                JOIN pg_class child ON pg_inherits.inhrelid = child.oid
                WHERE parent.relname = %s
                ORDER BY child.relname;
            """, [table_name])
            
            partitions = cursor.fetchall()
            
            if partitions:
                self.stdout.write(f'\n  Existing partitions for {table_name}:')
                for partition_name, size in partitions:
                    self.stdout.write(f'    - {partition_name} ({size})')
            else:
                self.stdout.write(f'  No partitions found for {table_name}')

