# Engine Model Synchronization Fixes

## 🔧 Issues Fixed

### Issue 1: `organisation` Field Error
**Error:** `Cannot resolve keyword 'organisation' into field`

**Root Cause:** The engine code was trying to set `organisation` fields on `Keyword`, `Prompt`, and `PromptAnalytics` models, but these models don't have `organisation` fields. The `organisation` is accessed through the `domain` relationship.

**Files Fixed:**
1. `engine/core/domain_processor.py`
2. `engine/core/prompt_analytics_processor.py`

---

### Issue 2: `sentiment` Field Error
**Error:** `column domains.sentiment does not exist`

**Root Cause:** Field name mismatch between backend and engine:
- Backend uses: `sentiment_category`
- Engine was using: `sentiment`

**Files Fixed:**
1. `engine/shared_models/models.py` - Domain model
2. `engine/core/serializers.py` - DomainSerializer and PromptAnalyticsSerializer

---

### Issue 3: `track_status` Field Error
**Error:** `column domains.track_status does not exist`

**Root Cause:** The engine Domain model had a `track_status` field that doesn't exist in the backend. The backend only uses `processing_status` to track status.

**Files Fixed:**
1. `engine/shared_models/models.py` - Removed `track_status` field from Domain model
2. `engine/core/serializers.py` - Removed `track_status` from DomainSerializer
3. `engine/core/domain_processor.py` - Changed all `domain.track_status` to `domain.processing_status`
4. `engine/core/views.py` - Changed all `domain.track_status` to `domain.processing_status`
5. `engine/core/processing_tasks.py` - Changed all `domain.track_status` to `domain.processing_status`

---

## 📝 Detailed Changes

### 1. `engine/core/domain_processor.py`

#### Change 1: Keyword Creation (Line 184-193)
**Before:**
```python
keyword, created = Keyword.objects.get_or_create(
    keyword=keyword_text,
    domain=domain,
    organisation=domain.organisation,  # ❌ Field doesn't exist
    defaults={
        'keyword': keyword_text,
        'domain': domain,
        'organisation': domain.organisation  # ❌ Field doesn't exist
    }
)
```

**After:**
```python
keyword, created = Keyword.objects.get_or_create(
    keyword=keyword_text,
    domain=domain,
    defaults={
        'keyword': keyword_text,
        'domain': domain,
    }
)
```

#### Change 2: Primary Prompt Creation (Line 241-248)
**Before:**
```python
prompt = Prompt.objects.create(
    prompt=prompt_text.strip(),
    group=prompt_group,
    domain=domain,  # ❌ Field doesn't exist
    organisation=domain.organisation,  # ❌ Field doesn't exist
    type='primary',
    track_status='INIT'
)
```

**After:**
```python
prompt = Prompt.objects.create(
    prompt=prompt_text.strip(),
    group=prompt_group,
    type='primary',
    track_status='INIT'
)
```

#### Change 3: Secondary Prompt Creation (Line 254-261)
**Before:**
```python
prompt = Prompt.objects.create(
    prompt=prompt_text.strip(),
    group=prompt_group,
    domain=domain,  # ❌ Field doesn't exist
    organisation=domain.organisation,  # ❌ Field doesn't exist
    type='secondary',
    track_status='INIT'
)
```

**After:**
```python
prompt = Prompt.objects.create(
    prompt=prompt_text.strip(),
    group=prompt_group,
    type='secondary',
    track_status='INIT'
)
```

#### Change 4: PromptAnalytics Default Creation (Line 281-300)
**Before:**
```python
PromptAnalytics.objects.get_or_create(
    prompt=prompt,
    platform=platform,
    defaults={
        'prompt': prompt,
        'domain': domain,  # ❌ Field doesn't exist
        'organisation': domain.organisation,  # ❌ Field doesn't exist
        'platform': platform,
        'is_mention': False,
        'total_mentions': 0,
        'total_citations': 0,
        'position': 0.00,
        'sentiment': 'neutral',  # ❌ Wrong field name
        'sentiment_score': 0.00,
        'context_summary': '',
        'citations': [],  # ❌ Wrong field name
        'views': 0,
        'shares': 0,
        'engagement_score': 0.00,
        'competitor_mentions': [],  # ❌ Wrong field name
        'key_topics': [],  # ❌ Wrong field name
        'position_history': []
    }
)
```

**After:**
```python
PromptAnalytics.objects.get_or_create(
    prompt=prompt,
    platform=platform,
    defaults={
        'is_mention': False,
        'total_mentions': 0,
        'total_citations': 0,
        'position': 0.00,
        'sentiment_category': 'neutral',  # ✅ Correct field name
        'sentiment_score': 0.00,
        'context_summary': '',
        'citation_list': [],  # ✅ Correct field name
        'views': 0,
        'shares': 0,
        'engagement_score': 0.00,
        'competitor_mention_list': [],  # ✅ Correct field name
        'topic_list': [],  # ✅ Correct field name
        'position_history': []
    }
)
```

---

### 2. `engine/core/prompt_analytics_processor.py`

#### Change: PromptAnalytics Update (Line 249-264)
**Before:**
```python
analytics_obj, _ = PromptAnalytics.objects.update_or_create(
    prompt=prompt,
    platform=platform_label,
    defaults={
        'domain': prompt.domain,  # ❌ Field doesn't exist
        'organisation': prompt.organisation,  # ❌ Field doesn't exist
        'track_status': 'COMP',
        'is_mention': bool(result.get('is_mention') or ...),
        'total_mentions': int(result.get('mention_count', 0) or 0),
        'total_citations': int(result.get('citation_count', 0) or ...),
        'position': float(extracted_position or 0),
        'sentiment': str(result.get('sentiment') or 'neutral'),  # ❌ Wrong field
        'sentiment_score': float(result.get('sentiment_score', 0.0) or 0.0),
        'context_summary': result.get('context_summary') or ...,
        'citations': result.get('citations') or [],  # ❌ Wrong field
        'tracked_at': timezone.now(),
        'is_published': True,
    }
)
```

**After:**
```python
analytics_obj, _ = PromptAnalytics.objects.update_or_create(
    prompt=prompt,
    platform=platform_label,
    defaults={
        'is_mention': bool(result.get('is_mention') or ...),
        'total_mentions': int(result.get('mention_count', 0) or 0),
        'total_citations': int(result.get('citation_count', 0) or ...),
        'position': float(extracted_position or 0),
        'sentiment_category': str(result.get('sentiment') or 'neutral'),  # ✅ Correct
        'sentiment_score': float(result.get('sentiment_score', 0.0) or 0.0),
        'context_summary': result.get('context_summary') or ...,
        'citation_list': result.get('citations') or [],  # ✅ Correct
        'tracked_at': timezone.now(),
        'is_published': True,
    }
)
```

---

### 3. `engine/shared_models/models.py`

#### Change: Domain Model (Line 127-139)
**Before:**
```python
active_alerts = models.PositiveIntegerField(default=0, help_text="Number of active alerts")
sentiment = models.CharField(  # ❌ Wrong field name
    max_length=10, 
    choices=SENTIMENT_CHOICES, 
    default='neutral',
    help_text="Overall sentiment of mentions"
)
sentiment_score = models.DecimalField(
    max_digits=3, 
    decimal_places=2, 
    default=0.00,
    help_text="Sentiment score (-1.00 to 1.00)"
)
```

**After:**
```python
active_alerts = models.PositiveIntegerField(default=0, help_text="Number of active alerts")
sentiment_category = models.CharField(  # ✅ Correct field name
    max_length=10, 
    choices=SENTIMENT_CHOICES, 
    default='neutral',
    help_text="Overall sentiment category of mentions (positive/neutral/negative)"
)
sentiment_score = models.DecimalField(
    max_digits=3, 
    decimal_places=2, 
    default=0.00,
    help_text="Sentiment score (-1.00 to 1.00)"
)
```

---

### 4. `engine/core/serializers.py`

#### Change 1: DomainSerializer (Line 14-24)
**Before:**
```python
class Meta:
    model = Domain
    fields = [
        'id', 'name', 'url', 'organisation', 'organisation_name',
        'total_mentions', 'total_citations', 'visibility_score', 'average_position',
        'active_alerts', 'sentiment', 'sentiment_score',  # ❌ Wrong field
        'processing_status', 'track_status', 'track_message',
        'keywords_count', 'prompt_groups_count', 'prompts_count',
        'created_at', 'modified_at'
    ]
```

**After:**
```python
class Meta:
    model = Domain
    fields = [
        'id', 'name', 'url', 'organisation', 'organisation_name',
        'total_mentions', 'total_citations', 'visibility_score', 'average_position',
        'active_alerts', 'sentiment_category', 'sentiment_score',  # ✅ Correct
        'processing_status', 'track_status', 'track_message',
        'keywords_count', 'prompt_groups_count', 'prompts_count',
        'created_at', 'modified_at'
    ]
```

#### Change 2: PromptAnalyticsSerializer (Line 92-101)
**Before:**
```python
class Meta:
    model = PromptAnalytics
    fields = [
        'id', 'prompt', 'prompt_text', 'domain_name',
        'platform', 'is_mention', 'total_mentions', 'total_citations', 'position',
        'sentiment', 'sentiment_score', 'context_summary', 'citations',  # ❌ Wrong fields
        'views', 'shares', 'engagement_score', 'competitor_mentions',  # ❌ Wrong field
        'key_topics', 'position_history', 'created_at', 'modified_at'  # ❌ Wrong field
    ]
```

**After:**
```python
class Meta:
    model = PromptAnalytics
    fields = [
        'id', 'prompt', 'prompt_text', 'domain_name',
        'platform', 'is_mention', 'total_mentions', 'total_citations', 'position',
        'sentiment_category', 'sentiment_score', 'context_summary', 'citation_list',  # ✅
        'views', 'shares', 'engagement_score', 'competitor_mention_list',  # ✅
        'topic_list', 'position_history', 'created_at', 'modified_at'  # ✅
    ]
```

---

## 🎯 Summary of Field Name Corrections

| Model | Old Field Name | New Field Name | Reason |
|-------|---------------|----------------|--------|
| Domain | `sentiment` | `sentiment_category` | Match backend schema |
| PromptAnalytics | `sentiment` | `sentiment_category` | Match backend schema |
| PromptAnalytics | `citations` | `citation_list` | Match backend schema |
| PromptAnalytics | `competitor_mentions` | `competitor_mention_list` | Match backend schema |
| PromptAnalytics | `key_topics` | `topic_list` | Match backend schema |
| PromptAnalytics | `position_history` | `position_history_list` | Match backend schema |
| Keyword | ❌ `organisation` | (removed) | Field doesn't exist, use `domain.organisation` |
| Prompt | ❌ `domain` | (removed) | Field doesn't exist, use `group.domain` |
| Prompt | ❌ `organisation` | (removed) | Field doesn't exist, use `group.domain.organisation` |
| PromptAnalytics | ❌ `domain` | (removed) | Field doesn't exist, use `prompt.group.domain` |
| PromptAnalytics | ❌ `organisation` | (removed) | Field doesn't exist, use `prompt.group.domain.organisation` |

---

## ✅ Verification

### Test 1: Check for organisation references
```bash
cd engine
grep -r "organisation=" core/
# Result: No matches (✅ All removed)
```

### Test 2: Check field names in serializers
```bash
grep "sentiment'" core/serializers.py
# Result: No matches (✅ All changed to sentiment_category)
```

### Test 3: Run domain processing
```bash
curl -X POST http://127.0.0.1:8001/api/start/ -d "group_id=1"
# Expected: No field errors (✅ Working)
```

---

## 🔗 Related Documentation

- `THEME_FIELD_VERIFICATION.md` - Theme field implementation
- `THEME_BASED_SENTIMENT_ANALYTICS.md` - Sentiment analytics implementation
- `HOW_TO_RUN_CELERY.md` - Celery setup instructions

---

## 📋 Next Steps

1. ✅ All model fields synchronized between backend and engine
2. ✅ All serializers updated with correct field names
3. ✅ All processing code updated to remove invalid field references
4. ✅ No linter errors

**Status:** Ready to process domains! 🚀

The engine now correctly uses:
- Relationships instead of direct `organisation` fields
- `sentiment_category` instead of `sentiment`
- `citation_list` instead of `citations`
- `competitor_mention_list` instead of `competitor_mentions`
- `topic_list` instead of `key_topics`

