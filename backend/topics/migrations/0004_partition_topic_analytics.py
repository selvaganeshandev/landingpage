"""
Migration to convert topic_analytics to a partitioned table.
"""

from django.db import migrations
from datetime import datetime
from dateutil.relativedelta import relativedelta


def create_partitioned_table(apps, schema_editor):
    """Convert topic_analytics to a partitioned table"""
    
    current_date = datetime.now().replace(day=1)
    
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
            CREATE TABLE topic_analytics_{month_name} PARTITION OF topic_analytics
                FOR VALUES FROM ('{start_date}') TO ('{end_date}');
        """)
    
    sql = f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_class WHERE relname = 'topic_analytics' AND relkind = 'p'
            ) THEN
                ALTER TABLE topic_analytics RENAME TO topic_analytics_old;
                
                CREATE TABLE topic_analytics (
                    id INTEGER NOT NULL,
                    topic_id INTEGER NOT NULL,
                    total_mentions INTEGER NOT NULL DEFAULT 0,
                    visibility_score DECIMAL(5, 2),
                    sentiment_score DECIMAL(5, 2),
                    timestamp DATE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    PRIMARY KEY (id, timestamp)
                ) PARTITION BY RANGE (timestamp);
                
                CREATE SEQUENCE IF NOT EXISTS topic_analytics_id_seq;
                ALTER TABLE topic_analytics ALTER COLUMN id SET DEFAULT nextval('topic_analytics_id_seq');
                
                {''.join(partition_sqls)}
                
                IF EXISTS (SELECT 1 FROM topic_analytics_old LIMIT 1) THEN
                    INSERT INTO topic_analytics SELECT * FROM topic_analytics_old;
                END IF;
                
                CREATE INDEX topic_analytics_topic_idx 
                    ON topic_analytics (topic_id, timestamp DESC, total_mentions DESC);
                CREATE INDEX topic_analytics_timestamp_idx
                    ON topic_analytics (timestamp DESC);
                
                ALTER TABLE topic_analytics 
                    ADD CONSTRAINT topic_analytics_topic_fk 
                    FOREIGN KEY (topic_id) REFERENCES topics_topic(id) 
                    ON DELETE CASCADE;
                
                DROP TABLE IF EXISTS topic_analytics_old;
                
                RAISE NOTICE 'Converted topic_analytics to partitioned table successfully';
            ELSE
                RAISE NOTICE 'topic_analytics is already partitioned, skipping conversion';
            END IF;
        END $$;
    """
    
    schema_editor.execute(sql)


def reverse_partitioning(apps, schema_editor):
    """Reverse the partitioning"""
    
    sql = """
        CREATE TABLE topic_analytics_new AS SELECT * FROM topic_analytics;
        DROP TABLE topic_analytics CASCADE;
        ALTER TABLE topic_analytics_new RENAME TO topic_analytics;
        ALTER TABLE topic_analytics ADD PRIMARY KEY (id);
        
        CREATE SEQUENCE IF NOT EXISTS topic_analytics_id_seq;
        ALTER TABLE topic_analytics ALTER COLUMN id SET DEFAULT nextval('topic_analytics_id_seq');
        SELECT setval('topic_analytics_id_seq', COALESCE((SELECT MAX(id) FROM topic_analytics), 1));
        
        CREATE INDEX topic_analytics_topic_idx 
            ON topic_analytics (topic_id, timestamp);
        
        ALTER TABLE topic_analytics 
            ADD CONSTRAINT topic_analytics_topic_fk 
            FOREIGN KEY (topic_id) REFERENCES topics_topic(id) 
            ON DELETE CASCADE;
    """
    
    schema_editor.execute(sql)


class Migration(migrations.Migration):

    dependencies = [
        ('topics', '0003_alter_topic_options_and_more'),
    ]

    operations = [
        migrations.RunPython(
            create_partitioned_table,
            reverse_partitioning,
        ),
    ]

