# Table Partitioning Guide for LLM Monitor

## What is Table Partitioning?

**Table partitioning** is a database technique that splits a large table into smaller, more manageable pieces called **partitions**, while still appearing as a single table to your application.

Think of it like organizing books in a library:
- **Without partitioning**: All books in one giant pile (hard to search, slow to manage)
- **With partitioning**: Books organized by year/month (easy to find, fast queries, can remove old data easily)

---

## Why Use Partitioning in LLM Monitor?

### Your Use Case: Time-Series Data

Your application stores **analytics data** that grows continuously over time:
- `PromptAnalytics` - Analytics records for every prompt/platform combination
- `CompetitorAnalytics` - Daily competitor tracking data
- `TopicAnalytics` - Daily topic performance data
- `SentimentAnalytics` - Sentiment data over time
- `ShareOfVoiceAnalytics` - Market share historical data
- `AlertNotifications` - Alert delivery history

### Problems Without Partitioning

```python
# After 1 year of operation:
PromptAnalytics.objects.count()
# → 10,000,000+ records! 😱

# Queries become SLOW:
PromptAnalytics.objects.filter(
    created_at__gte='2025-10-01',
    created_at__lt='2025-11-01'
)
# → Scans ALL 10 million rows even though you only need October data
```

### Benefits With Partitioning

```python
# Same query, but PostgreSQL only scans the October partition:
# → Scans only ~833,000 rows (1/12 of data)
# → 10-50x faster queries! 🚀

# Easy data management:
# Drop old data: DROP TABLE prompt_analytics_2024_01;  (instant!)
# Archive old data: Just detach and move partition
# Backup specific periods: Backup only recent partitions
```

---

## How Partitioning Works

### Concept

```
┌──────────────────────────────────────┐
│   prompt_analytics (Parent Table)    │
│   - Just a logical container         │
│   - No data stored here              │
└──────────────────────────────────────┘
               │
               ├─────────────────────────────────────────┐
               │                 │                       │
    ┌──────────▼─────────┐  ┌───▼──────────┐  ┌────────▼─────────┐
    │ prompt_analytics_  │  │ prompt_      │  │ prompt_analytics_│
    │    2025_01         │  │ analytics_   │  │    2025_03       │
    │                    │  │   2025_02    │  │                  │
    │ Jan 2025 data      │  │ Feb 2025     │  │ Mar 2025 data    │
    │ (830K rows)        │  │ data         │  │ (830K rows)      │
    └────────────────────┘  │ (830K rows)  │  └──────────────────┘
                            └──────────────┘
```

### Query Routing

```sql
-- Your query:
SELECT * FROM prompt_analytics 
WHERE created_at BETWEEN '2025-02-01' AND '2025-02-28';

-- PostgreSQL automatically knows to only scan:
SELECT * FROM prompt_analytics_2025_02;
-- ✅ Only scans February partition!
-- ❌ Skips January and March partitions
```

---

## Implementation for LLM Monitor

### 1. Which Tables to Partition?

Based on your models, partition these time-series tables:

| Table | Partition By | Reason | Expected Growth |
|-------|--------------|--------|-----------------|
| `prompt_analytics` | `created_at` (monthly) | High write volume, time-based queries | ~1M rows/month |
| `competitor_analytics` | `timestamp` (monthly) | Daily snapshots per competitor | ~100K rows/month |
| `topic_analytics` | `timestamp` (monthly) | Daily snapshots per topic | ~100K rows/month |
| `sentiment_analytics` | `timestamp` (monthly) | Historical sentiment tracking | ~50K rows/month |
| `share_of_voice_analytics` | `timestamp` (monthly) | Market share history | ~50K rows/month |
| `alert_notifications` | `sent_at` (monthly) | Notification logs | ~10K rows/month |

**Don't partition:**
- Small lookup tables (< 100K rows)
- Tables without clear partition key
- Tables with few time-range queries

---

### 2. Partition Strategy: Monthly Range Partitioning

**Why Monthly?**
- Good balance between partition count and data per partition
- Most queries are "last 30 days", "this month", etc.
- Easy to manage and maintain
- Can archive/drop old months easily

---

## Step-by-Step Implementation

### Method 1: PostgreSQL Native Partitioning (Recommended)

#### Step 1: Create SQL Migration File

```python
# backend/prompts/migrations/0005_partition_prompt_analytics.py

from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('prompts', '0004_rename_citations_promptanalytics_citation_list_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            -- Step 1: Rename existing table
            ALTER TABLE prompt_analytics RENAME TO prompt_analytics_old;
            
            -- Step 2: Create new partitioned table
            CREATE TABLE prompt_analytics (
                id SERIAL,
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
                CONSTRAINT prompt_analytics_pkey PRIMARY KEY (id, created_at),
                CONSTRAINT prompt_analytics_unique UNIQUE (prompt_id, platform, created_at)
            ) PARTITION BY RANGE (created_at);
            
            -- Step 3: Create partitions for current and future months
            -- October 2025
            CREATE TABLE prompt_analytics_2025_10 PARTITION OF prompt_analytics
                FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');
            
            -- November 2025
            CREATE TABLE prompt_analytics_2025_11 PARTITION OF prompt_analytics
                FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
            
            -- December 2025
            CREATE TABLE prompt_analytics_2025_12 PARTITION OF prompt_analytics
                FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');
            
            -- January 2026
            CREATE TABLE prompt_analytics_2026_01 PARTITION OF prompt_analytics
                FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
            
            -- Step 4: Copy data from old table to new partitioned table
            INSERT INTO prompt_analytics SELECT * FROM prompt_analytics_old;
            
            -- Step 5: Create indexes on partitions
            CREATE INDEX prompt_analytics_prompt_platform_idx 
                ON prompt_analytics (prompt_id, platform);
            CREATE INDEX prompt_analytics_platform_idx 
                ON prompt_analytics (platform, created_at);
            CREATE INDEX prompt_analytics_mention_idx 
                ON prompt_analytics (is_mention, created_at);
            
            -- Step 6: Create foreign key constraints
            ALTER TABLE prompt_analytics 
                ADD CONSTRAINT prompt_analytics_prompt_fk 
                FOREIGN KEY (prompt_id) REFERENCES prompts_prompt(id) 
                ON DELETE CASCADE;
            
            -- Step 7: Drop old table
            DROP TABLE prompt_analytics_old;
            """,
            reverse_sql="""
            -- Rollback: Convert back to non-partitioned table
            CREATE TABLE prompt_analytics_new AS SELECT * FROM prompt_analytics;
            DROP TABLE prompt_analytics;
            ALTER TABLE prompt_analytics_new RENAME TO prompt_analytics;
            """
        )
    ]
```

#### Step 2: Apply the Migration

```bash
python manage.py migrate prompts
```

---

### Method 2: Using django-postgres-partition (Easier)

#### Install Package

```bash
pip install django-postgres-partition
```

#### Update Model

```python
# backend/prompts/models.py

from postgres_partition.models import RangePartitionedModel
from postgres_partition.manager import PartitionedManager

class PromptAnalytics(RangePartitionedModel):
    objects = PartitionedManager()
    
    # ... all your existing fields ...
    
    class Meta:
        db_table = 'prompt_analytics'
        partition_key = 'created_at'  # Column to partition by
        partition_type = 'range'
        partition_interval = 'month'  # Create monthly partitions
        
        indexes = [
            models.Index(fields=['prompt', 'platform', 'created_at']),
            models.Index(fields=['prompt', 'is_mention', '-position']),
        ]

# Automatically creates partitions as needed!
```

#### Generate Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

---

## Automatic Partition Management

### Problem: Creating Future Partitions

You need to create partitions before data arrives, or inserts will fail!

### Solution 1: Scheduled Task (Recommended)

```python
# backend/prompts/management/commands/create_partitions.py

from django.core.management.base import BaseCommand
from django.db import connection
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Create partitions for next 3 months'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Get current date
            now = datetime.now()
            
            # Create partitions for next 3 months
            for i in range(3):
                month_start = (now + timedelta(days=30*i)).replace(day=1)
                month_end = (month_start + timedelta(days=32)).replace(day=1)
                
                table_name = f"prompt_analytics_{month_start.strftime('%Y_%m')}"
                
                sql = f"""
                CREATE TABLE IF NOT EXISTS {table_name}
                PARTITION OF prompt_analytics
                FOR VALUES FROM ('{month_start.strftime('%Y-%m-%d')}') 
                             TO ('{month_end.strftime('%Y-%m-%d')}');
                """
                
                try:
                    cursor.execute(sql)
                    self.stdout.write(
                        self.style.SUCCESS(f'Created partition: {table_name}')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'Partition exists: {table_name}')
                    )
```

#### Schedule with Cron or Celery

```python
# Run monthly via cron:
# 0 0 1 * * cd /path/to/project && python manage.py create_partitions

# Or with Celery Beat:
from celery import shared_task

@shared_task
def create_monthly_partitions():
    from django.core.management import call_command
    call_command('create_partitions')

# In celery.py:
app.conf.beat_schedule = {
    'create-partitions': {
        'task': 'prompts.tasks.create_monthly_partitions',
        'schedule': crontab(day_of_month=1, hour=0, minute=0),  # First of month
    },
}
```

---

### Solution 2: Default Partition (Fallback)

```sql
-- Create a default partition to catch any data outside defined ranges
CREATE TABLE prompt_analytics_default PARTITION OF prompt_analytics DEFAULT;
```

**Pros:** No failed inserts
**Cons:** Need to manually move data later

---

## Querying Partitioned Tables

### Good News: Transparent to Django ORM!

```python
# Your existing queries work exactly the same:
PromptAnalytics.objects.filter(
    created_at__gte='2025-10-01',
    created_at__lt='2025-11-01'
)
# PostgreSQL automatically uses only prompt_analytics_2025_10 partition!

# No code changes needed! 🎉
```

### Verify Partition Pruning

```python
# Check which partitions are scanned:
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        EXPLAIN ANALYZE
        SELECT * FROM prompt_analytics
        WHERE created_at >= '2025-10-01'
          AND created_at < '2025-11-01';
    """)
    print(cursor.fetchall())
```

**Expected output:**
```
Seq Scan on prompt_analytics_2025_10 (actual rows=830000...)
↑ Only scans October partition!
```

---

## Data Management

### Archive Old Data

```sql
-- Detach partition (keeps data but makes it independent)
ALTER TABLE prompt_analytics DETACH PARTITION prompt_analytics_2024_01;

-- Rename for archival
ALTER TABLE prompt_analytics_2024_01 RENAME TO prompt_analytics_2024_01_archive;

-- Compress and archive (optional)
pg_dump -t prompt_analytics_2024_01_archive > archive_2024_01.sql.gz
```

### Delete Old Data

```sql
-- Super fast! Just drops the partition
DROP TABLE prompt_analytics_2024_01;

-- vs. non-partitioned (very slow):
DELETE FROM prompt_analytics WHERE created_at < '2024-02-01';
-- Takes hours and causes table bloat
```

---

## Complete Implementation Plan

### Phase 1: Setup (Week 1)

1. **Choose tables to partition**
   ```bash
   # Priority order:
   1. prompt_analytics (highest volume)
   2. competitor_analytics
   3. topic_analytics
   4. sentiment_analytics
   5. share_of_voice_analytics
   ```

2. **Install package (optional)**
   ```bash
   pip install django-postgres-partition
   pip freeze > requirements.txt
   ```

3. **Create partitions for current + 3 future months**

### Phase 2: Migrate One Table (Week 2)

1. **Start with `prompt_analytics`** (most critical)
2. Create migration with rollback plan
3. Test on staging environment
4. Monitor query performance
5. Verify data integrity

### Phase 3: Migrate Remaining Tables (Week 3-4)

Apply same process to:
- competitor_analytics
- topic_analytics  
- sentiment_analytics
- share_of_voice_analytics
- alert_notifications

### Phase 4: Automation (Week 5)

1. Set up automatic partition creation
2. Configure monitoring/alerts
3. Document maintenance procedures
4. Create data retention policy

---

## Performance Expectations

### Before Partitioning
```python
# Query last 30 days from 10M rows
PromptAnalytics.objects.filter(
    created_at__gte=timezone.now() - timedelta(days=30)
)
# → 2-5 seconds ⏱️
# → Scans 10,000,000 rows 📊
```

### After Partitioning
```python
# Same query
PromptAnalytics.objects.filter(
    created_at__gte=timezone.now() - timedelta(days=30)
)
# → 0.1-0.3 seconds ⚡
# → Scans only ~830,000 rows (current month partition) 📊
# → 10-50x faster! 🚀
```

---

## Monitoring & Maintenance

### Check Partition Sizes

```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE tablename LIKE 'prompt_analytics_%'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

**Expected output:**
```
┌──────────────────────────────┬─────────┐
│ tablename                    │ size    │
├──────────────────────────────┼─────────┤
│ prompt_analytics_2025_10     │ 125 MB  │
│ prompt_analytics_2025_09     │ 118 MB  │
│ prompt_analytics_2025_08     │ 115 MB  │
└──────────────────────────────┴─────────┘
```

### List All Partitions

```sql
SELECT
    parent.relname AS parent_table,
    child.relname AS partition_name
FROM pg_inherits
JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
JOIN pg_class child ON pg_inherits.inhrelid = child.oid
WHERE parent.relname = 'prompt_analytics'
ORDER BY child.relname;
```

### Verify Partition Pruning

```sql
-- Should only access relevant partition
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM prompt_analytics
WHERE created_at >= '2025-10-01' AND created_at < '2025-11-01';
```

---

## Best Practices

### ✅ Do's

1. **Always create partitions in advance** (3-6 months ahead)
2. **Use monthly partitioning for analytics** (good balance)
3. **Include partition key in PRIMARY KEY** (`id, created_at`)
4. **Monitor partition sizes** (aim for 50-500 MB per partition)
5. **Archive/drop old partitions regularly** (data retention policy)
6. **Test migrations on staging first**
7. **Document partition management procedures**

### ❌ Don'ts

1. **Don't partition small tables** (< 100K rows)
2. **Don't create too many partitions** (avoid daily unless huge volume)
3. **Don't forget to create future partitions** (or use default partition)
4. **Don't partition without time-range queries** (no benefit)
5. **Don't delete partitions without backup** (always archive first)

---

## Troubleshooting

### Problem: Insert fails "no partition of relation found"

**Cause:** No partition exists for the data's timestamp

**Solution:**
```sql
-- Create missing partition
CREATE TABLE prompt_analytics_2026_02 PARTITION OF prompt_analytics
FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

-- Or create default partition
CREATE TABLE prompt_analytics_default PARTITION OF prompt_analytics DEFAULT;
```

### Problem: Slow queries after partitioning

**Cause:** Query doesn't use partition key in WHERE clause

**Solution:**
```python
# ❌ Bad: No partition pruning
PromptAnalytics.objects.filter(prompt_id=123)

# ✅ Good: Uses partition pruning
PromptAnalytics.objects.filter(
    prompt_id=123,
    created_at__gte='2025-10-01'  # ← Enables partition pruning
)
```

### Problem: Can't add foreign key to partitioned table

**Cause:** PostgreSQL limitation

**Solution:** Add foreign keys to individual partitions or use triggers

---

## Rollback Plan

If partitioning causes issues:

```sql
-- 1. Create regular table
CREATE TABLE prompt_analytics_new AS SELECT * FROM prompt_analytics;

-- 2. Drop partitioned table
DROP TABLE prompt_analytics CASCADE;

-- 3. Rename new table
ALTER TABLE prompt_analytics_new RENAME TO prompt_analytics;

-- 4. Recreate indexes and constraints
CREATE INDEX ... ;
```

---

## Summary

### What You Get

✅ **10-50x faster time-range queries**
✅ **Easy data archival/deletion** (drop old partitions instantly)
✅ **Better index performance** (smaller indexes per partition)
✅ **Parallel query execution** (PostgreSQL can scan partitions in parallel)
✅ **Simplified maintenance** (vacuum/analyze faster on small partitions)

### Cost

⚠️ **Initial setup time** (1-2 weeks for all tables)
⚠️ **Ongoing maintenance** (create new partitions monthly)
⚠️ **Slightly more complex queries** (must include partition key for pruning)

### Recommendation

**YES, implement partitioning for:**
- prompt_analytics
- competitor_analytics
- topic_analytics
- sentiment_analytics
- share_of_voice_analytics

**Start with `prompt_analytics` and expand once comfortable.**

---

**Last Updated:** November 3, 2025
**Status:** 📋 **PLANNING / READY TO IMPLEMENT**

