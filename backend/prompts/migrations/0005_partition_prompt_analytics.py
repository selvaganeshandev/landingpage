"""
Migration to convert prompt_analytics to a partitioned table.

This migration:
1. Renames the existing table
2. Creates a new partitioned table with the same structure
3. Creates initial partitions (current month + 3 future months)
4. Copies data from the old table to the new partitioned table
5. Drops the old table

Note: This operation is safe and preserves all data.
"""

from django.db import migrations
from datetime import datetime
from dateutil.relativedelta import relativedelta


def create_partitioned_table(apps, schema_editor):
    """Convert prompt_analytics to a partitioned table"""
    
    # Get current date for creating initial partitions
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
    
    # Build partition creation SQL
    partition_sqls = []
    for month_name, start_date, end_date in months:
        partition_sqls.append(f"""
            CREATE TABLE prompt_analytics_{month_name} PARTITION OF prompt_analytics
                FOR VALUES FROM ('{start_date}') TO ('{end_date}');
        """)
    
    # Complete SQL for conversion
    sql = f"""
        -- Step 1: Check if table is already partitioned
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_class WHERE relname = 'prompt_analytics' AND relkind = 'p'
            ) THEN
                -- Step 2: Rename existing table
                ALTER TABLE prompt_analytics RENAME TO prompt_analytics_old;
                
                -- Step 3: Create new partitioned table
                CREATE TABLE prompt_analytics (
                    id INTEGER NOT NULL,
                    prompt_id INTEGER NOT NULL,
                    platform VARCHAR(100) NOT NULL,
                    is_mention BOOLEAN NOT NULL DEFAULT false,
                    position DECIMAL(5, 2),
                    total_mentions INTEGER NOT NULL DEFAULT 0,
                    total_citations INTEGER NOT NULL DEFAULT 0,
                    visibility_score DECIMAL(5, 2),
                    context_summary TEXT,
                    sentiment_category VARCHAR(20),
                    sentiment_score DECIMAL(5, 2),
                    citation_list JSONB DEFAULT '[]'::jsonb,
                    competitor_mention_list JSONB DEFAULT '[]'::jsonb,
                    topic_list JSONB DEFAULT '[]'::jsonb,
                    position_history_list JSONB DEFAULT '[]'::jsonb,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    modified_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    PRIMARY KEY (id, created_at)
                ) PARTITION BY RANGE (created_at);
                
                -- Step 4: Create sequence for id (if it doesn't exist)
                CREATE SEQUENCE IF NOT EXISTS prompt_analytics_id_seq;
                ALTER TABLE prompt_analytics ALTER COLUMN id SET DEFAULT nextval('prompt_analytics_id_seq');
                
                -- Step 5: Create initial partitions
                {''.join(partition_sqls)}
                
                -- Step 6: Copy data from old table (if it exists and has data)
                IF EXISTS (SELECT 1 FROM prompt_analytics_old LIMIT 1) THEN
                    INSERT INTO prompt_analytics SELECT * FROM prompt_analytics_old;
                END IF;
                
                -- Step 7: Create indexes on partitions
                CREATE INDEX prompt_analytics_prompt_platform_idx 
                    ON prompt_analytics (prompt_id, platform, created_at);
                CREATE INDEX prompt_analytics_platform_idx 
                    ON prompt_analytics (platform, created_at);
                CREATE INDEX prompt_analytics_mention_idx 
                    ON prompt_analytics (is_mention, created_at);
                CREATE INDEX prompt_analytics_sentiment_idx
                    ON prompt_analytics (sentiment_category, created_at);
                
                -- Step 8: Add foreign key constraint
                ALTER TABLE prompt_analytics 
                    ADD CONSTRAINT prompt_analytics_prompt_fk 
                    FOREIGN KEY (prompt_id) REFERENCES prompts_prompt(id) 
                    ON DELETE CASCADE;
                
                -- Step 9: Add unique constraint
                ALTER TABLE prompt_analytics
                    ADD CONSTRAINT prompt_analytics_unique 
                    UNIQUE (prompt_id, platform, created_at);
                
                -- Step 10: Drop old table
                DROP TABLE IF EXISTS prompt_analytics_old;
                
                RAISE NOTICE 'Converted prompt_analytics to partitioned table successfully';
            ELSE
                RAISE NOTICE 'prompt_analytics is already partitioned, skipping conversion';
            END IF;
        END $$;
    """
    
    schema_editor.execute(sql)


def reverse_partitioning(apps, schema_editor):
    """Reverse the partitioning (convert back to regular table)"""
    
    sql = """
        -- Create regular table from partitioned table
        CREATE TABLE prompt_analytics_new AS SELECT * FROM prompt_analytics;
        
        -- Drop partitioned table
        DROP TABLE prompt_analytics CASCADE;
        
        -- Rename new table
        ALTER TABLE prompt_analytics_new RENAME TO prompt_analytics;
        
        -- Recreate primary key
        ALTER TABLE prompt_analytics ADD PRIMARY KEY (id);
        
        -- Recreate sequence
        CREATE SEQUENCE IF NOT EXISTS prompt_analytics_id_seq;
        ALTER TABLE prompt_analytics ALTER COLUMN id SET DEFAULT nextval('prompt_analytics_id_seq');
        SELECT setval('prompt_analytics_id_seq', COALESCE((SELECT MAX(id) FROM prompt_analytics), 1));
        
        -- Recreate indexes
        CREATE INDEX prompt_analytics_prompt_platform_idx 
            ON prompt_analytics (prompt_id, platform);
        CREATE INDEX prompt_analytics_platform_idx 
            ON prompt_analytics (platform, created_at);
        CREATE INDEX prompt_analytics_mention_idx 
            ON prompt_analytics (is_mention, created_at);
        
        -- Recreate foreign key
        ALTER TABLE prompt_analytics 
            ADD CONSTRAINT prompt_analytics_prompt_fk 
            FOREIGN KEY (prompt_id) REFERENCES prompts_prompt(id) 
            ON DELETE CASCADE;
        
        -- Recreate unique constraint
        ALTER TABLE prompt_analytics
            ADD CONSTRAINT prompt_analytics_unique 
            UNIQUE (prompt_id, platform);
    """
    
    schema_editor.execute(sql)


class Migration(migrations.Migration):

    dependencies = [
        ('prompts', '0004_rename_citations_promptanalytics_citation_list_and_more'),
    ]

    operations = [
        migrations.RunPython(
            create_partitioned_table,
            reverse_partitioning,
        ),
    ]

