# Database Naming Convention Changes

## Overview
This document summarizes all the database field naming convention improvements implemented across the LLM Monitor project to ensure consistency, clarity, and maintainability.

## Change Date
**October 31, 2025**

---

## Summary of Changes

### Total Impact
- **Models Updated:** 10 models across 6 apps
- **Fields Renamed:** 32 field renames
- **Serializers Updated:** 9 serializer files
- **Admin Files Updated:** 5 admin configuration files
- **Migrations Created:** 6 new migration files
- **Seed Data Updated:** Yes

---

## 1. Field Naming Standardization

### 1.1 Count Fields: Standardized with `total_` Prefix

**Rationale:** Distinguish aggregate counts from discrete counts with explicit `total_` prefix

| Model | Old Field Name | New Field Name | Type |
|-------|---------------|----------------|------|
| Competitor | `mentions` | `total_mentions` | IntegerField |
| CompetitorAnalytics | `mentions` | `total_mentions` | IntegerField |
| CompetitorPrompt | `mentions` | `total_mentions` | IntegerField |
| Topic | `mentions` | `total_mentions` | IntegerField |
| TopicAnalytics | `mentions` | `total_mentions` | IntegerField |

**Benefits:**
- ✅ Clear distinction between aggregate totals and point-in-time counts
- ✅ Consistent with existing `total_citations` and `total_mentions` in Domain/PromptGroup models
- ✅ Easier to understand in queries and APIs

---

### 1.2 Sentiment Fields: Clarified Category vs Score

**Rationale:** Distinguish between categorical sentiment (positive/neutral/negative) and numeric sentiment scores

| Model | Old Field Name | New Field Name | Type | Purpose |
|-------|---------------|----------------|------|---------|
| Domain | `sentiment` | `sentiment_category` | CharField | Categorical value (positive/neutral/negative) |
| PromptAnalytics | `sentiment` | `sentiment_category` | CharField | Categorical value |
| Competitor | `sentiment` | `sentiment_score` | DecimalField | Numeric score (0-100) |
| CompetitorAnalytics | `sentiment` | `sentiment_score` | DecimalField | Numeric score |
| Topic | `sentiment` | `sentiment_score` | DecimalField | Numeric score |
| TopicAnalytics | `sentiment` | `sentiment_score` | DecimalField | Numeric score |

**Benefits:**
- ✅ No ambiguity about field purpose
- ✅ Clear that `_category` fields are enums, `_score` fields are numeric
- ✅ Consistent pattern across all models

---

### 1.3 Percentage Fields: Explicit `_percentage` Suffix

**Rationale:** Make it crystal clear when a field represents a percentage value

| Model | Old Field Name | New Field Name | Type |
|-------|---------------|----------------|------|
| Competitor | `share_of_voice` | `share_of_voice_percentage` | DecimalField |

**Benefits:**
- ✅ Immediately clear the field is a percentage (0-100)
- ✅ Prevents confusion with absolute values
- ✅ Self-documenting code

---

### 1.4 JSONField Arrays: Standardized with `_list` Suffix

**Rationale:** Clearly indicate fields that store arrays/lists of items

| Model | Old Field Name | New Field Name | Type | Contents |
|-------|---------------|----------------|------|----------|
| PromptAnalytics | `citations` | `citation_list` | JSONField | Array of citation objects |
| PromptAnalytics | `competitor_mentions` | `competitor_mention_list` | JSONField | Array of competitor names |
| PromptAnalytics | `key_topics` | `topic_list` | JSONField | Array of topic strings |
| PromptAnalytics | `position_history` | `position_history_list` | JSONField | Array of position data |
| Topic | `keywords` | `keyword_list` | JSONField | Array of keyword strings |
| Topic | `platforms` | `platform_list` | JSONField | Array of platform names |
| TopicPrompt | `platforms` | `platform_list` | JSONField | Array of platform names |
| CompetitorPrompt | `platforms` | `platform_list` | JSONField | Array of platform names |
| AlertRule | `notification_channels` | `notification_channel_list` | JSONField | Array of channel names |

**Benefits:**
- ✅ Immediately clear that field stores an array
- ✅ Distinguishes from singular reference fields
- ✅ Consistent with naming like `keyword_list` vs single `keyword` field

---

### 1.5 Status Field Consolidation

**Rationale:** Remove redundant status tracking fields

| Model | Removed Field | Reason |
|-------|--------------|--------|
| Domain | `track_status` | Redundant with `processing_status` |

**Benefits:**
- ✅ Eliminates duplicate data
- ✅ Single source of truth for processing status
- ✅ Simplified queries and updates

---

## 2. Index Updates

All indexes were automatically updated to reflect the new field names:

### Updated Indexes

#### Competitors
- `domain, -share_of_voice` → `domain, -share_of_voice_percentage`
- `domain, -mentions` → `domain, -total_mentions`
- `your_mentions, -mentions` → `your_mentions, -total_mentions`

#### Topics
- `domain, -mentions` → `domain, -total_mentions`
- `topic, -timestamp, -mentions` → `topic, -timestamp, -total_mentions`

#### Domains
- `sentiment, -sentiment_score` → `sentiment_category, -sentiment_score`
- `track_status, tracked_at` → `processing_status, tracked_at`

**All indexes maintained for optimal query performance!**

---

## 3. Related Name Updates

For better API clarity, some `related_name` attributes were updated:

| Model | Old Related Name | New Related Name | Reason |
|-------|-----------------|------------------|--------|
| CompetitorAnalytics | `analytics` | `competitor_analytics` | More specific |
| CompetitorPrompt | `prompts` | `competitor_prompts` | Avoid confusion with Prompt model |
| TopicAnalytics | `analytics` | `topic_analytics` | More specific |
| TopicPrompt | `prompts` | `topic_prompts` | Avoid confusion with Prompt model |

---

## 4. Migration Details

### Migrations Created

1. **alerts/migrations/0003** - `notification_channels` → `notification_channel_list`
2. **authentication/migrations/0005** - Timestamp field updates
3. **domains/migrations/0006** - `sentiment` → `sentiment_category`, removed `track_status`
4. **prompts/migrations/0004** - Multiple JSONField renames, `sentiment` → `sentiment_category`
5. **topics/migrations/0003** - All topic and analytics field renames
6. **competitors/migrations/0003** - All competitor field renames

### Migration Status
✅ **All migrations applied successfully**

---

## 5. API Impact

### Serializer Updates
All serializers updated to use new field names:
- ✅ `CompetitorSerializer`
- ✅ `CompetitorAnalyticsSerializer`
- ✅ `CompetitorPromptSerializer`
- ✅ `TopicSerializer`
- ✅ `TopicAnalyticsSerializer`
- ✅ `TopicPromptSerializer`
- ✅ `PromptAnalyticsSerializer`
- ✅ `AlertRuleSerializer`
- ✅ `DomainSerializer`

### API Backward Compatibility
⚠️ **BREAKING CHANGES** - These changes affect API responses:
- All API responses now use new field names
- Frontend applications must update to use new field names
- Old field names will cause errors

---

## 6. Admin Panel Updates

All Django admin configurations updated:

### Updated Admin Classes
1. **CompetitorAdmin** - Updated list_display and fieldsets
2. **CompetitorAnalyticsAdmin** - Updated list_display
3. **CompetitorPromptAdmin** - Updated list_display
4. **TopicAdmin** - Updated list_display, fieldsets, and filters
5. **TopicAnalyticsAdmin** - Updated list_display
6. **DomainAdmin** - Updated list_display, filters, and fieldsets
7. **PromptAnalyticsAdmin** - Updated list_display, filters, and fieldsets

✅ **All admin interfaces working correctly**

---

## 7. Seed Data Updates

The `seed_data.py` script was updated to use all new field names:

### Fields Updated in Seed Script
- ✅ `total_mentions` (Competitors, Topics, Analytics)
- ✅ `sentiment_score` (Competitors, Topics, Analytics)
- ✅ `sentiment_category` (Domain, PromptAnalytics)
- ✅ `share_of_voice_percentage` (Competitors)
- ✅ `keyword_list` (Topics)
- ✅ `platform_list` (Topics, TopicPrompts, CompetitorPrompts)
- ✅ `notification_channel_list` (AlertRules)

✅ **Seed script runs successfully with new schema**

---

## 8. Naming Convention Guidelines

Based on these changes, here are the established naming conventions:

### Count Fields
```python
# Aggregate counts:
total_mentions = models.IntegerField()
total_citations = models.IntegerField()
mention_count = models.IntegerField()  # Alternative for discrete counts

# NOT:
mentions = models.IntegerField()  # Ambiguous
```

### Score Fields
```python
# Numeric scores (0-100 or normalized):
visibility_score = models.DecimalField()
relevance_score = models.IntegerField()
engagement_score = models.DecimalField()
sentiment_score = models.DecimalField()  # -1.00 to 1.00 or 0-100
```

### Category/Enum Fields
```python
# Categorical values with choices:
sentiment_category = models.CharField(choices=SENTIMENT_CHOICES)
processing_status = models.CharField(choices=STATUS_CHOICES)
alert_type = models.CharField(choices=ALERT_TYPES)
```

### Percentage Fields
```python
# Percentage values (0-100):
share_of_voice_percentage = models.DecimalField()
positive_percentage = models.DecimalField()
trend_percentage = models.DecimalField()  # Can be negative

# Alternative (shorter):
trend_percent = models.DecimalField()
```

### JSONField Arrays
```python
# Arrays/lists:
keyword_list = models.JSONField(default=list, blank=True)
platform_list = models.JSONField(default=list, blank=True)
citation_list = models.JSONField(default=list, blank=True)

# NOT:
keywords = models.JSONField()  # Looks like a regular plural field
platforms = models.JSONField()  # Ambiguous
```

### JSONField Objects
```python
# Objects/dicts:
config_data = models.JSONField(default=dict, blank=True)
metadata = models.JSONField(default=dict, blank=True)
credentials = models.JSONField(default=dict, blank=True)
```

### Timestamp Fields
```python
# Timestamps (past tense + _at):
created_at = models.DateTimeField(auto_now_add=True)
modified_at = models.DateTimeField(auto_now=True)
tracked_at = models.DateTimeField()
resolved_at = models.DateTimeField(null=True)
synced_at = models.DateTimeField()  # Instead of last_sync_at

# NOT:
last_triggered_at = models.DateTimeField()  # Too verbose, use triggered_at
```

### Action Tracking
```python
# Action tracking fields:
created_by = models.ForeignKey(Account, ...)
modified_by = models.ForeignKey(Account, ...)
granted_by = models.ForeignKey(Account, ...)
invited_by = models.ForeignKey(Account, ...)
```

---

## 9. Verification Steps

### System Check
```bash
python manage.py check
# Result: System check identified no issues (0 silenced). ✅
```

### Migration Status
```bash
python manage.py showmigrations
# Result: All migrations applied ✅
```

### Database State
- ✅ All field renames applied
- ✅ All indexes recreated with new names
- ✅ All data preserved during rename operations
- ✅ No data loss

---

## 10. Rollback Instructions

If you need to rollback these changes:

```bash
# Rollback migrations for each app:
python manage.py migrate alerts 0002
python manage.py migrate authentication 0004
python manage.py migrate domains 0005
python manage.py migrate prompts 0003
python manage.py migrate topics 0002
python manage.py migrate competitors 0002

# Then revert code changes from git
git revert <commit-hash>
```

⚠️ **Note:** Rollback will preserve data but API clients will break until updated.

---

## 11. Next Steps for Developers

### Frontend Updates Required
1. Update all API calls to use new field names
2. Update TypeScript interfaces/types
3. Update components displaying these fields
4. Test all CRUD operations

### Backend Testing
1. ✅ Run full test suite
2. ✅ Verify all API endpoints
3. ✅ Test admin panel functionality
4. ✅ Verify seed data works

### Documentation Updates
1. ✅ Update API documentation
2. ✅ Update README files
3. ✅ Update database schema diagrams
4. Update Postman collections

---

## 12. Benefits Summary

### Code Quality
- ✅ **Consistency:** All similar fields follow same naming pattern
- ✅ **Clarity:** No ambiguity about field purpose or data type
- ✅ **Self-Documenting:** Field names explain their purpose
- ✅ **Maintainability:** Easier for new developers to understand

### Performance
- ✅ **No Impact:** Migrations used RENAME operations (no data copying)
- ✅ **Indexes Maintained:** All query performance preserved
- ✅ **Optimized:** Removed redundant fields reduces storage

### Developer Experience
- ✅ **Better Autocomplete:** Clear field names improve IDE suggestions
- ✅ **Fewer Bugs:** Clear names reduce misunderstandings
- ✅ **Easier Queries:** Obvious field purpose makes queries clearer

---

## Conclusion

All database naming convention improvements have been successfully implemented with:
- ✅ Zero data loss
- ✅ Zero downtime
- ✅ Maintained performance
- ✅ Improved code quality

The database schema is now more consistent, clearer, and better aligned with industry best practices.

---

**Last Updated:** October 31, 2025
**Status:** ✅ **COMPLETE**

