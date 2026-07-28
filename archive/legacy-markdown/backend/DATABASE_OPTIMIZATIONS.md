# Database Optimization Recommendations for LLM Monitor

## Overview
This document outlines critical database optimizations needed for scalability, performance, and reliability.

---

## 1. **Missing Indexes for High-Frequency Queries**

### **A. Authentication & Access Control**
```python
# backend/authentication/models.py

class Account(AbstractUser):
    # Add these to Meta:
    indexes = [
        models.Index(fields=['organisation', 'role', 'is_active']),  # Team queries
        models.Index(fields=['email']),  # Already unique, but explicit index
        models.Index(fields=['organisation', 'created_at']),  # User timeline
    ]

class UserPermission(models.Model):
    # Add these to Meta:
    indexes = [
        models.Index(fields=['user', 'module']),  # Permission checks (critical!)
        models.Index(fields=['granted_by', 'created_at']),  # Audit logs
    ]

class TeamInvitation(models.Model):
    # Add these to Meta:
    indexes = [
        models.Index(fields=['email', 'status']),  # Check pending invites
        models.Index(fields=['organisation', 'status', 'created_at']),  # Org invites
        models.Index(fields=['expires_at']),  # Cleanup expired invites
    ]
```

### **B. Domain & Core Models**
```python
# backend/domains/models.py

class Domain(models.Model):
    indexes = [
        models.Index(fields=['organisation', 'processing_status']),  # Org domain list
        models.Index(fields=['organisation', '-visibility_score']),  # Top domains
        models.Index(fields=['track_status', 'tracked_at']),  # Processing queue
        models.Index(fields=['sentiment', '-sentiment_score']),  # Sentiment filtering
    ]

class DomainAccess(models.Model):
    # Add composite index:
    indexes = [
        models.Index(fields=['user', 'domain']),  # Already unique, good
        models.Index(fields=['granted_by', 'created_at']),  # Audit
    ]
```

### **C. Prompts & Analytics**
```python
# backend/prompts/models.py

class PromptGroup(models.Model):
    indexes = [
        models.Index(fields=['domain', 'is_published']),  # Published groups
        models.Index(fields=['domain', 'track_status']),  # Processing status
        models.Index(fields=['domain', '-total_mentions']),  # Top groups
    ]

class Prompt(models.Model):
    indexes = [
        models.Index(fields=['group', 'track_status']),  # Group processing
        models.Index(fields=['group', 'type']),  # Primary/secondary
        models.Index(fields=['tracked_at']),  # Recently tracked
    ]

class PromptAnalytics(models.Model):
    indexes = [
        models.Index(fields=['prompt', 'platform', 'created_at']),  # Time-series queries
        models.Index(fields=['prompt', 'is_mention', '-position']),  # Mention analysis
        models.Index(fields=['platform', 'is_mention', 'created_at']),  # Platform trends
        models.Index(fields=['prompt', '-sentiment_score']),  # Sentiment analysis
    ]
    # Note: Already has unique(prompt, platform) which creates an index
```

### **D. Keywords**
```python
# backend/keywords/models.py

class Keyword(models.Model):
    indexes = [
        models.Index(fields=['domain', 'keyword']),  # Domain keywords lookup
        models.Index(fields=['domain', 'created_at']),  # Timeline
        # Consider full-text search index for keyword field:
        # GinIndex(fields=['keyword'], opclasses=['gin_trgm_ops'])  # Requires pg_trgm
    ]
```

---

## 2. **New Tables - Missing Indexes**

### **A. Alerts System**
```python
# backend/alerts/models.py

class Alert(models.Model):
    # CRITICAL: Add these indexes
    indexes = [
        models.Index(fields=['domain', 'status', '-created_at']),  # Already exists ✓
        models.Index(fields=['status', 'severity']),  # Already exists ✓
        models.Index(fields=['type', 'created_at']),  # Already exists ✓
        # ADD THESE:
        models.Index(fields=['created_by', '-created_at']),  # User's alerts
        models.Index(fields=['domain', 'type', 'status']),  # Filtered alerts
        models.Index(fields=['resolved_at']),  # Resolution time analysis
    ]

class AlertRule(models.Model):
    indexes = [
        models.Index(fields=['domain', 'enabled']),  # Already exists ✓
        # ADD THESE:
        models.Index(fields=['enabled', 'last_triggered_at']),  # Active rule monitoring
        models.Index(fields=['domain', '-detection_count']),  # Most triggered rules
    ]

class AlertNotification(models.Model):
    indexes = [
        models.Index(fields=['alert', 'sent_at']),  # Already exists ✓
        models.Index(fields=['status', 'sent_at']),  # Already exists ✓
        # ADD THESE:
        models.Index(fields=['channel', 'status']),  # Channel success rates
        models.Index(fields=['recipient', '-sent_at']),  # User notification history
    ]
```

### **B. Competitors**
```python
# backend/competitors/models.py

class Competitor(models.Model):
    indexes = [
        models.Index(fields=['domain']),  # Already exists ✓
        # ADD THESE:
        models.Index(fields=['domain', '-share_of_voice']),  # Market leaders
        models.Index(fields=['domain', '-visibility_score']),  # Visibility ranking
        models.Index(fields=['domain', '-mentions']),  # Most mentioned
        models.Index(fields=['domain', 'created_at']),  # Tracking timeline
    ]

class CompetitorAnalytics(models.Model):
    indexes = [
        models.Index(fields=['competitor', 'timestamp']),  # Already exists ✓
        models.Index(fields=['platform', 'timestamp']),  # Already exists ✓
        # ADD THESE:
        models.Index(fields=['competitor', 'platform', '-timestamp']),  # Platform trends
        models.Index(fields=['timestamp', '-mentions']),  # Daily top competitors
    ]

class CompetitorPrompt(models.Model):
    indexes = [
        models.Index(fields=['competitor', '-mentions']),  # Already exists ✓
        # ADD THESE:
        models.Index(fields=['competitor', '-position']),  # Top positions
        models.Index(fields=['your_mentions', '-mentions']),  # Gap analysis (CRITICAL!)
        models.Index(fields=['competitor', 'created_at']),  # Tracking timeline
    ]
```

### **C. Topics**
```python
# backend/topics/models.py

class Topic(models.Model):
    indexes = [
        models.Index(fields=['domain', '-mentions']),  # Already exists ✓
        # ADD THESE:
        models.Index(fields=['domain', '-visibility_score']),  # Top topics
        models.Index(fields=['domain', '-trend_percentage']),  # Trending topics
        models.Index(fields=['domain', 'created_at']),  # Topic timeline
    ]
    # JSONB field optimization:
    # GinIndex(fields=['keywords'])  # Fast keyword array lookups

class TopicAnalytics(models.Model):
    indexes = [
        models.Index(fields=['topic', 'timestamp']),  # Already exists ✓
        # ADD THESE:
        models.Index(fields=['topic', '-timestamp', '-mentions']),  # Recent top data
        models.Index(fields=['timestamp']),  # Date range queries
    ]

class TopicPrompt(models.Model):
    indexes = [
        models.Index(fields=['topic', '-relevance_score']),  # Already exists ✓
        # ADD THESE:
        models.Index(fields=['search_volume', '-relevance_score']),  # High-value prompts
        models.Index(fields=['topic', 'search_volume']),  # Filter by volume
    ]
```

### **D. Analytics (Sentiment & SOV)**
```python
# backend/analytics/models.py

class SentimentAnalytics(models.Model):
    indexes = [
        models.Index(fields=['domain', 'timestamp']),  # Already exists ✓
        models.Index(fields=['theme', 'timestamp']),  # Already exists ✓
        # ADD THESE:
        models.Index(fields=['domain', 'platform', 'timestamp']),  # Platform sentiment
        models.Index(fields=['domain', 'theme', '-negative_percentage']),  # Problem themes
        models.Index(fields=['timestamp', '-mention_count']),  # Popular themes by date
    ]

class ShareOfVoiceAnalytics(models.Model):
    indexes = [
        models.Index(fields=['domain', 'timestamp']),  # Already exists ✓
        models.Index(fields=['competitor', 'timestamp']),  # Already exists ✓
        # ADD THESE:
        models.Index(fields=['domain', 'platform', 'timestamp']),  # Platform SOV
        models.Index(fields=['timestamp', '-share_percentage']),  # Market leaders
        models.Index(fields=['domain', 'competitor', 'platform', 'timestamp']),  # Full drill-down
        models.Index(fields=['market_position', 'timestamp']),  # Ranking changes
    ]
```

### **E. Integrations**
```python
# backend/integrations/models.py

class Integration(models.Model):
    indexes = [
        models.Index(fields=['domain', 'type']),  # Already exists ✓
        models.Index(fields=['status', 'last_sync_at']),  # Already exists ✓
        # ADD THESE:
        models.Index(fields=['domain', 'status']),  # Domain integration health
        models.Index(fields=['type', 'status']),  # Integration type health
        models.Index(fields=['last_sync_at']),  # Sync monitoring
    ]
```

---

## 3. **Table Partitioning for Time-Series Data**

For large-scale time-series data, implement table partitioning:

### **Tables to Partition**
```sql
-- Monthly partitioning for analytics tables
CREATE TABLE prompt_analytics PARTITION BY RANGE (created_at);
CREATE TABLE competitor_analytics PARTITION BY RANGE (timestamp);
CREATE TABLE topic_analytics PARTITION BY RANGE (timestamp);
CREATE TABLE sentiment_analytics PARTITION BY RANGE (timestamp);
CREATE TABLE share_of_voice_analytics PARTITION BY RANGE (timestamp);
CREATE TABLE alert_notifications PARTITION BY RANGE (sent_at);

-- Example: Create partitions for 2025
CREATE TABLE prompt_analytics_2025_01 PARTITION OF prompt_analytics
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE prompt_analytics_2025_02 PARTITION OF prompt_analytics
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
-- ... and so on
```

### **Django Implementation**
```python
# Use django-postgres-partition or implement manual partitioning
# https://github.com/chrisglass/django-postgres-partition

class PromptAnalytics(models.Model):
    # ... fields ...
    
    class Meta:
        # PostgreSQL-specific
        db_table = 'prompt_analytics'
        # Add partition configuration
```

---

## 4. **JSONB Field Optimization**

### **GIN Indexes for JSONB Fields**
```python
from django.contrib.postgres.indexes import GinIndex

class AlertRule(models.Model):
    conditions = models.JSONField(default=dict)
    notification_channels = models.JSONField(default=list)
    
    class Meta:
        indexes = [
            GinIndex(fields=['conditions']),  # Fast JSON queries
            GinIndex(fields=['notification_channels']),
        ]

class Topic(models.Model):
    keywords = models.JSONField(default=list)
    platforms = models.JSONField(default=list)
    
    class Meta:
        indexes = [
            GinIndex(fields=['keywords']),  # Fast array contains queries
            GinIndex(fields=['platforms']),
        ]

class CompetitorPrompt(models.Model):
    platforms = models.JSONField(default=list)
    
    class Meta:
        indexes = [
            GinIndex(fields=['platforms']),
        ]
```

---

## 5. **Data Retention & Archival**

### **Retention Policies**
```python
# Add retention fields to time-series models

class PromptAnalytics(models.Model):
    # ... existing fields ...
    archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['archived', 'created_at']),  # Active data queries
        ]

# Management command: archive_old_analytics.py
from django.core.management.base import BaseCommand
from datetime import timedelta
from django.utils import timezone

class Command(BaseCommand):
    def handle(self, *args, **options):
        cutoff_date = timezone.now() - timedelta(days=365)
        
        # Archive old analytics (keep last 12 months active)
        PromptAnalytics.objects.filter(
            created_at__lt=cutoff_date,
            archived=False
        ).update(archived=True, archived_at=timezone.now())
```

---

## 6. **Query Optimization Strategies**

### **A. Use select_related() for Foreign Keys**
```python
# Bad (N+1 queries)
alerts = Alert.objects.filter(domain__organisation=org)
for alert in alerts:
    print(alert.domain.name)  # Hits DB each time

# Good (1 query with JOIN)
alerts = Alert.objects.select_related('domain', 'created_by').filter(
    domain__organisation=org
)
```

### **B. Use prefetch_related() for Reverse Relations**
```python
# Bad (N+1 queries)
domains = Domain.objects.filter(organisation=org)
for domain in domains:
    print(domain.alerts.count())  # Hits DB each time

# Good (2 queries total)
domains = Domain.objects.prefetch_related('alerts').filter(organisation=org)
```

### **C. Database-Level Aggregations**
```python
from django.db.models import Count, Avg, Sum

# Instead of Python loops, use DB aggregation
domain_stats = Domain.objects.filter(organisation=org).aggregate(
    total_mentions=Sum('total_mentions'),
    avg_visibility=Avg('visibility_score'),
    alert_count=Count('alerts')
)
```

---

## 7. **Connection Pooling**

### **Add pgBouncer for Connection Pooling**
```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
        'CONN_MAX_AGE': 600,  # Connection persistence (10 min)
        'OPTIONS': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000',  # 30 second query timeout
        },
    }
}

# Add connection pooling middleware (optional)
# pip install django-db-connection-pool
```

---

## 8. **Caching Strategy**

### **Redis Caching for Hot Data**
```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Cache expensive queries
from django.core.cache import cache

def get_domain_stats(domain_id):
    cache_key = f'domain_stats_{domain_id}'
    stats = cache.get(cache_key)
    
    if stats is None:
        stats = Domain.objects.get(id=domain_id).get_stats()
        cache.set(cache_key, stats, 300)  # Cache for 5 minutes
    
    return stats
```

---

## 9. **Database Monitoring**

### **Enable Query Logging for Slow Queries**
```python
# settings.py (development only)
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',  # Log all SQL queries
        },
    },
}

# PostgreSQL slow query log
# postgresql.conf:
# log_min_duration_statement = 1000  # Log queries > 1 second
```

### **Add django-silk for Query Profiling**
```bash
pip install django-silk

# settings.py
INSTALLED_APPS += ['silk']
MIDDLEWARE += ['silk.middleware.SilkyMiddleware']

# urls.py
urlpatterns += [path('silk/', include('silk.urls', namespace='silk'))]
```

---

## 10. **Materialized Views for Complex Analytics**

### **Create Materialized Views for Dashboard Stats**
```sql
-- PostgreSQL materialized view for domain summary
CREATE MATERIALIZED VIEW domain_summary_mv AS
SELECT 
    d.id,
    d.name,
    d.organisation_id,
    COUNT(DISTINCT pa.id) as total_analytics,
    AVG(pa.position) as avg_position,
    COUNT(DISTINCT CASE WHEN pa.is_mention THEN pa.id END) as mention_count,
    AVG(pa.sentiment_score) as avg_sentiment
FROM domains d
LEFT JOIN prompt_groups pg ON pg.domain_id = d.id
LEFT JOIN prompts p ON p.group_id = pg.id
LEFT JOIN prompt_analytics pa ON pa.prompt_id = p.id
GROUP BY d.id, d.name, d.organisation_id;

CREATE UNIQUE INDEX ON domain_summary_mv (id);

-- Refresh periodically (add to cron or Celery beat)
REFRESH MATERIALIZED VIEW CONCURRENTLY domain_summary_mv;
```

---

## 11. **Full-Text Search Optimization**

### **Add PostgreSQL Full-Text Search**
```python
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank

class Prompt(models.Model):
    # ... existing fields ...
    search_vector = models.GeneratedField(
        expression=SearchVector('prompt'),
        output_field=models.TextField(),
        db_persist=True
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['search_vector']),  # GIN index for FTS
        ]

# Usage:
query = SearchQuery('machine learning')
prompts = Prompt.objects.annotate(
    rank=SearchRank('search_vector', query)
).filter(search_vector=query).order_by('-rank')
```

---

## 12. **Implementation Priority**

### **Phase 1: Critical (Immediate)**
1. ✅ Add `UserPermission` index on `(user, module)` - security/performance critical
2. ✅ Add `PromptAnalytics` composite indexes for time-series queries
3. ✅ Add `CompetitorPrompt` gap analysis index
4. ✅ Enable `CONN_MAX_AGE` for connection persistence

### **Phase 2: High Priority (Week 1)**
1. ✅ Add GIN indexes for all JSONB fields
2. ✅ Implement query optimization (select_related/prefetch_related)
3. ✅ Add caching for hot data (Redis)
4. ✅ Enable slow query logging

### **Phase 3: Medium Priority (Month 1)**
1. ⏳ Implement table partitioning for analytics tables
2. ⏳ Add materialized views for dashboard stats
3. ⏳ Set up pgBouncer connection pooling
4. ⏳ Implement data archival strategy

### **Phase 4: Long-term (Quarter 1)**
1. ⏳ Full-text search optimization
2. ⏳ Read replicas for reporting queries
3. ⏳ Automated partition management
4. ⏳ Advanced monitoring and alerting

---

## Summary

**Estimated Performance Improvements:**
- **Query Speed**: 50-80% faster for common queries
- **Concurrent Users**: 3-5x capacity increase
- **Database Size**: 30-50% reduction with archival
- **Response Time**: < 100ms for most API calls

**Next Steps:**
1. Run migration to add missing indexes
2. Update model Meta classes
3. Test query performance before/after
4. Monitor slow query log
5. Implement caching strategy

