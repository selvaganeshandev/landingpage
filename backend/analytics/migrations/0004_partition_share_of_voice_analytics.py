"""
Migration to convert share_of_voice_analytics to a partitioned table.
"""

from django.db import migrations
from datetime import datetime
from dateutil.relativedelta import relativedelta


def create_partitioned_table(apps, schema_editor):
    """Convert share_of_voice_analytics to a partitioned table"""
    
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
            CREATE TABLE share_of_voice_analytics_{month_name} PARTITION OF share_of_voice_analytics
                FOR VALUES FROM ('{start_date}') TO ('{end_date}');
        """)
    
    sql = f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_class WHERE relname = 'share_of_voice_analytics' AND relkind = 'p'
            ) THEN
                ALTER TABLE share_of_voice_analytics RENAME TO share_of_voice_analytics_old;
                
                CREATE TABLE share_of_voice_analytics (
                    id INTEGER NOT NULL,
                    domain_id INTEGER NOT NULL,
                    competitor_id INTEGER,
                    platform VARCHAR(100),
                    share_of_voice_percentage DECIMAL(5, 2) NOT NULL DEFAULT 0,
                    mention_count INTEGER NOT NULL DEFAULT 0,
                    timestamp DATE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    PRIMARY KEY (id, timestamp)
                ) PARTITION BY RANGE (timestamp);
                
                CREATE SEQUENCE IF NOT EXISTS share_of_voice_analytics_id_seq;
                ALTER TABLE share_of_voice_analytics ALTER COLUMN id SET DEFAULT nextval('share_of_voice_analytics_id_seq');
                
                {''.join(partition_sqls)}
                
                IF EXISTS (SELECT 1 FROM share_of_voice_analytics_old LIMIT 1) THEN
                    INSERT INTO share_of_voice_analytics SELECT * FROM share_of_voice_analytics_old;
                END IF;
                
                CREATE INDEX share_of_voice_analytics_domain_timestamp_idx 
                    ON share_of_voice_analytics (domain_id, timestamp DESC);
                CREATE INDEX share_of_voice_analytics_competitor_timestamp_idx 
                    ON share_of_voice_analytics (competitor_id, timestamp DESC);
                CREATE INDEX share_of_voice_analytics_platform_idx
                    ON share_of_voice_analytics (platform, timestamp DESC);
                
                ALTER TABLE share_of_voice_analytics 
                    ADD CONSTRAINT share_of_voice_analytics_domain_fk 
                    FOREIGN KEY (domain_id) REFERENCES domains_domain(id) 
                    ON DELETE CASCADE;
                
                ALTER TABLE share_of_voice_analytics 
                    ADD CONSTRAINT share_of_voice_analytics_competitor_fk 
                    FOREIGN KEY (competitor_id) REFERENCES competitors_competitor(id) 
                    ON DELETE CASCADE;
                
                DROP TABLE IF EXISTS share_of_voice_analytics_old;
                
                RAISE NOTICE 'Converted share_of_voice_analytics to partitioned table successfully';
            ELSE
                RAISE NOTICE 'share_of_voice_analytics is already partitioned, skipping conversion';
            END IF;
        END $$;
    """
    
    schema_editor.execute(sql)


def reverse_partitioning(apps, schema_editor):
    """Reverse the partitioning"""
    
    sql = """
        CREATE TABLE share_of_voice_analytics_new AS SELECT * FROM share_of_voice_analytics;
        DROP TABLE share_of_voice_analytics CASCADE;
        ALTER TABLE share_of_voice_analytics_new RENAME TO share_of_voice_analytics;
        ALTER TABLE share_of_voice_analytics ADD PRIMARY KEY (id);
        
        CREATE SEQUENCE IF NOT EXISTS share_of_voice_analytics_id_seq;
        ALTER TABLE share_of_voice_analytics ALTER COLUMN id SET DEFAULT nextval('share_of_voice_analytics_id_seq');
        SELECT setval('share_of_voice_analytics_id_seq', COALESCE((SELECT MAX(id) FROM share_of_voice_analytics), 1));
        
        CREATE INDEX share_of_voice_analytics_domain_timestamp_idx 
            ON share_of_voice_analytics (domain_id, timestamp);
        CREATE INDEX share_of_voice_analytics_competitor_timestamp_idx 
            ON share_of_voice_analytics (competitor_id, timestamp);
        
        ALTER TABLE share_of_voice_analytics 
            ADD CONSTRAINT share_of_voice_analytics_domain_fk 
            FOREIGN KEY (domain_id) REFERENCES domains_domain(id) 
            ON DELETE CASCADE;
        
        ALTER TABLE share_of_voice_analytics 
            ADD CONSTRAINT share_of_voice_analytics_competitor_fk 
            FOREIGN KEY (competitor_id) REFERENCES competitors_competitor(id) 
            ON DELETE CASCADE;
    """
    
    schema_editor.execute(sql)


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0003_sentimentanalytics_sentiment_a_domain__508f7c_idx_and_more'),
    ]

    operations = [
        migrations.RunPython(
            create_partitioned_table,
            reverse_partitioning,
        ),
    ]

