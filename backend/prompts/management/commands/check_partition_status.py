"""
Management command to check the status of partitioned tables.

Usage:
    python manage.py check_partition_status
    python manage.py check_partition_status --table prompt_analytics
"""

from django.core.management.base import BaseCommand
from django.db import connection
from datetime import datetime


class Command(BaseCommand):
    help = 'Check status and statistics of partitioned tables'

    def add_arguments(self, parser):
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
            help='Specific table to check (default: all)'
        )

    def handle(self, *args, **options):
        table_filter = options['table']
        
        tables = [
            'prompt_analytics',
            'competitor_analytics',
            'topic_analytics',
            'sentiment_analytics',
            'share_of_voice_analytics',
        ]
        
        if table_filter != 'all':
            tables = [table_filter]
        
        self.stdout.write(
            self.style.SUCCESS('\n📊 Partition Status Report\n' + '='*60)
        )
        
        for table_name in tables:
            self.check_table_partitions(table_name)
        
        self.stdout.write('\n')

    def check_table_partitions(self, table_name):
        """Check partition status for a specific table"""
        
        self.stdout.write(f'\n\n📋 Table: {table_name}')
        self.stdout.write('-' * 60)
        
        with connection.cursor() as cursor:
            # Check if table is partitioned
            cursor.execute("""
                SELECT 
                    relkind = 'p' as is_partitioned
                FROM pg_class
                WHERE relname = %s;
            """, [table_name])
            
            result = cursor.fetchone()
            if not result:
                self.stdout.write(
                    self.style.ERROR(f'❌ Table {table_name} does not exist!')
                )
                return
            
            is_partitioned = result[0]
            
            if not is_partitioned:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Table is NOT partitioned')
                )
                return
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Table is partitioned')
            )
            
            # Get partition information
            cursor.execute("""
                SELECT
                    child.relname AS partition_name,
                    pg_get_expr(child.relpartbound, child.oid) AS partition_range,
                    pg_size_pretty(pg_total_relation_size(child.oid)) AS size,
                    (SELECT count(*) FROM ONLY child.relname) AS row_count
                FROM pg_inherits
                JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
                JOIN pg_class child ON pg_inherits.inhrelid = child.oid
                WHERE parent.relname = %s
                ORDER BY child.relname;
            """, [table_name])
            
            partitions = cursor.fetchall()
            
            if not partitions:
                self.stdout.write(
                    self.style.WARNING('\n⚠️  No partitions created yet!')
                )
                return
            
            self.stdout.write(f'\n📦 Total partitions: {len(partitions)}\n')
            
            # Display partition details
            total_size = 0
            for partition_name, partition_range, size, row_count in partitions:
                self.stdout.write(
                    f'  • {partition_name}\n'
                    f'    Range: {partition_range}\n'
                    f'    Size: {size}\n'
                )
                
            # Get total table size
            cursor.execute("""
                SELECT pg_size_pretty(pg_total_relation_size(%s));
            """, [table_name])
            
            total_size = cursor.fetchone()[0]
            self.stdout.write(f'\n💾 Total size: {total_size}')
            
            # Check for missing partitions (future months)
            current_month = datetime.now().strftime('%Y_%m')
            next_month = (datetime.now().replace(day=1) + 
                         __import__('datetime').timedelta(days=32)).strftime('%Y_%m')
            
            partition_names = [p[0] for p in partitions]
            
            warnings = []
            if f"{table_name}_{current_month}" not in partition_names:
                warnings.append(f'⚠️  Missing partition for current month ({current_month})')
            
            if f"{table_name}_{next_month}" not in partition_names:
                warnings.append(f'⚠️  Missing partition for next month ({next_month})')
            
            if warnings:
                self.stdout.write('\n' + '\n'.join(warnings))
                self.stdout.write(
                    self.style.WARNING(
                        '\n💡 Run: python manage.py create_partitions'
                    )
                )

    def test_partition_pruning(self, table_name):
        """Test if partition pruning is working"""
        
        self.stdout.write(f'\n\n🔍 Testing partition pruning for {table_name}...\n')
        
        with connection.cursor() as cursor:
            # Test query with date filter
            cursor.execute(f"""
                EXPLAIN (ANALYZE, BUFFERS)
                SELECT * FROM {table_name}
                WHERE created_at >= NOW() - INTERVAL '30 days'
                LIMIT 10;
            """)
            
            plan = cursor.fetchall()
            
            self.stdout.write('Query Plan:')
            for row in plan:
                self.stdout.write(f'  {row[0]}')

