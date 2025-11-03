"""
Migration to convert competitor_analytics to a partitioned table.
"""

from django.db import migrations
from datetime import datetime
from dateutil.relativedelta import relativedelta


def create_partitioned_table(apps, schema_editor):
    """Convert competitor_analytics to a partitioned table"""
    
    current_date = datetime.now().replace(day=1)
    
    # Create list of months to partition (current + 3 future)
    months = []
    for i in range(4):
        month_start = current_date + relativedelta(months=i)
        month_end = month_start + relativedelta(months=1)
        months.append((
            month_start.strftime('%Y_%m'),
            month_start.strftime('%Y-%m-%d'),
            month_end.strftime('%Y-%m-%d')
        ))
    
    partition_sqls = []
    for month_name, start_date, end_date in months:
        partition_sqls.append(f"""
            CREATE TABLE competitor_analytics_{month_name} PARTITION OF competitor_analytics
                FOR VALUES FROM ('{start_date}') TO ('{end_date}');
        """)
    
    sql = f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_class WHERE relname = 'competitor_analytics' AND relkind = 'p'
            ) THEN
                ALTER TABLE competitor_analytics RENAME TO competitor_analytics_old;
                
                CREATE TABLE competitor_analytics (
                    id INTEGER NOT NULL,
                    competitor_id INTEGER NOT NULL,
                    platform VARCHAR(100) NOT NULL,
                    total_mentions INTEGER NOT NULL DEFAULT 0,
                    position DECIMAL(5, 2),
                    sentiment_score DECIMAL(5, 2),
                    timestamp DATE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    PRIMARY KEY (id, timestamp)
                ) PARTITION BY RANGE (timestamp);
                
                CREATE SEQUENCE IF NOT EXISTS competitor_analytics_id_seq;
                ALTER TABLE competitor_analytics ALTER COLUMN id SET DEFAULT nextval('competitor_analytics_id_seq');
                
                {''.join(partition_sqls)}
                
                IF EXISTS (SELECT 1 FROM competitor_analytics_old LIMIT 1) THEN
                    INSERT INTO competitor_analytics SELECT * FROM competitor_analytics_old;
                END IF;
                
                CREATE INDEX competitor_analytics_competitor_idx 
                    ON competitor_analytics (competitor_id, timestamp);
                CREATE INDEX competitor_analytics_platform_idx 
                    ON competitor_analytics (platform, timestamp);
                CREATE INDEX competitor_analytics_timestamp_mentions_idx
                    ON competitor_analytics (timestamp DESC, total_mentions DESC);
                
                ALTER TABLE competitor_analytics 
                    ADD CONSTRAINT competitor_analytics_competitor_fk 
                    FOREIGN KEY (competitor_id) REFERENCES competitors_competitor(id) 
                    ON DELETE CASCADE;
                
                DROP TABLE IF EXISTS competitor_analytics_old;
                
                RAISE NOTICE 'Converted competitor_analytics to partitioned table successfully';
            ELSE
                RAISE NOTICE 'competitor_analytics is already partitioned, skipping conversion';
            END IF;
        END $$;
    """
    
    schema_editor.execute(sql)


def reverse_partitioning(apps, schema_editor):
    """Reverse the partitioning"""
    
    sql = """
        CREATE TABLE competitor_analytics_new AS SELECT * FROM competitor_analytics;
        DROP TABLE competitor_analytics CASCADE;
        ALTER TABLE competitor_analytics_new RENAME TO competitor_analytics;
        ALTER TABLE competitor_analytics ADD PRIMARY KEY (id);
        
        CREATE SEQUENCE IF NOT EXISTS competitor_analytics_id_seq;
        ALTER TABLE competitor_analytics ALTER COLUMN id SET DEFAULT nextval('competitor_analytics_id_seq');
        SELECT setval('competitor_analytics_id_seq', COALESCE((SELECT MAX(id) FROM competitor_analytics), 1));
        
        CREATE INDEX competitor_analytics_competitor_idx 
            ON competitor_analytics (competitor_id, timestamp);
        CREATE INDEX competitor_analytics_platform_idx 
            ON competitor_analytics (platform, timestamp);
        
        ALTER TABLE competitor_analytics 
            ADD CONSTRAINT competitor_analytics_competitor_fk 
            FOREIGN KEY (competitor_id) REFERENCES competitors_competitor(id) 
            ON DELETE CASCADE;
    """
    
    schema_editor.execute(sql)


class Migration(migrations.Migration):

    dependencies = [
        ('competitors', '0003_alter_competitor_options_and_more'),
    ]

    operations = [
        migrations.RunPython(
            create_partitioned_table,
            reverse_partitioning,
        ),
    ]

