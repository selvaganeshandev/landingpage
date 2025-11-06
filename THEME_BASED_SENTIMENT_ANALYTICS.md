# Theme-Based Sentiment Analytics Implementation

## Overview
This document describes the implementation of theme-based sentiment analytics that links `PromptGroup` and `SentimentAnalytics` models through extracted themes using NLP techniques.

## Implementation Summary

### 1. Model Changes

#### Backend & Engine: `PromptGroup` Model
**File**: `backend/prompts/models.py`, `engine/shared_models/models.py`

Added `theme` field to store extracted theme:
```python
theme = models.CharField(
    max_length=255,
    blank=True,
    null=True,
    help_text="Common theme extracted from prompts in this group using NLP"
)
```

**Migration**: `prompts/migrations/0002_promptgroup_theme.py`

---

### 2. Theme Extraction During PromptGroup Creation

#### File: `engine/core/domain_processor.py`

**New Method: `_extract_theme_from_group()`**
- Extracts a concise theme from the prompt group
- Uses the cluster title (derived from sentence transformers)
- Filters out stop words and extracts meaningful keywords
- Limits theme to 50 characters for clean categorization

**Logic Flow**:
```
Keywords → Prompts → SentenceTransformer Embeddings → KMeans Clustering
                                                              ↓
                                                        Group Title
                                                              ↓
                                                    Extract Theme (NLP)
                                                              ↓
                                               Store in PromptGroup.theme
```

**Updated Method: `_store_prompt_groups()`**
- Calls `_extract_theme_from_group()` for each group
- Stores theme in `PromptGroup.theme`
- Creates initial `SentimentAnalytics` record with zero values
- Links domain and theme for future aggregation

**Example Theme Extraction**:
```python
# Group Title: "best practices for keyword research"
# Extracted Theme: "Best Practices Keyword Research"

# Group Title: "what are the benefits of using our product"
# Extracted Theme: "Benefits Using Product"
```

---

### 3. Sentiment Analytics Aggregation

#### File: `engine/core/prompt_analytics_processor.py`

**New Method: `_update_sentiment_analytics_for_theme()`**
- Called after all prompts in a group are processed
- Aggregates sentiment data from all `PromptAnalytics` in the group
- Calculates percentages for positive/neutral/negative sentiment
- Updates or creates `SentimentAnalytics` record for today's date

**Updated Method: `_check_and_aggregate_group()`**
- Added call to `_update_sentiment_analytics_for_theme()`
- Executes after group aggregation is complete

**Aggregation Logic**:
```python
# Count sentiments from PromptAnalytics
positive_count = analytics.filter(sentiment_category='positive', is_mention=True).count()
neutral_count = analytics.filter(sentiment_category='neutral', is_mention=True).count()
negative_count = analytics.filter(sentiment_category='negative', is_mention=True).count()

# Calculate percentages
positive_pct = (positive_count / total) * 100
neutral_pct = (neutral_count / total) * 100
negative_pct = (negative_count / total) * 100

# Update SentimentAnalytics
SentimentAnalytics.objects.update_or_create(
    domain=domain,
    theme=group.theme,
    platform=None,  # Overall aggregation
    timestamp=date.today(),
    defaults={
        'positive_percentage': positive_pct,
        'neutral_percentage': neutral_pct,
        'negative_percentage': negative_pct,
        'mention_count': total
    }
)
```

---

## Data Flow

### Phase 1: Domain Processing (Initial Setup)
```
┌─────────────────────────┐
│  Domain Created         │
│  Status: SCHD           │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Scrape Keywords        │
│  (DataForSEO API)       │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Generate Prompts       │
│  (ChatGPT API)          │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  Group Prompts                      │
│  (SentenceTransformer + KMeans)     │
│  - Embed prompts                    │
│  - Cluster similar prompts          │
│  - Extract representative title     │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  Extract Theme from Group           │
│  _extract_theme_from_group()        │
│  - Parse group title                │
│  - Remove stop words                │
│  - Extract 2-4 key words            │
│  - Title case and limit to 50 chars│
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  Create PromptGroup                 │
│  - group_id: title                  │
│  - theme: extracted theme           │
│  - domain: FK to domain             │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  Create Initial SentimentAnalytics  │
│  - domain: FK to domain             │
│  - theme: from PromptGroup          │
│  - positive_percentage: 0.0         │
│  - neutral_percentage: 0.0          │
│  - negative_percentage: 0.0         │
│  - mention_count: 0                 │
│  - timestamp: today                 │
└─────────────────────────────────────┘
```

### Phase 2: Analytics Processing (After Prompt Analysis)
```
┌─────────────────────────┐
│  Prompt Analytics       │
│  Status: COMP           │
│  (All platforms done)   │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  Check Group Completion             │
│  _check_and_aggregate_group()       │
│  - All prompts in group complete?   │
└──────────┬──────────────────────────┘
           │ YES
           ▼
┌─────────────────────────────────────┐
│  Aggregate Group Totals             │
│  - total_mentions                   │
│  - total_citations                  │
│  - average_position                 │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  Update SentimentAnalytics          │
│  _update_sentiment_analytics_for_   │
│  theme()                            │
│  - Count: positive/neutral/negative │
│  - Calculate percentages            │
│  - Update record for theme + today  │
└─────────────────────────────────────┘
```

---

## Relationship Between Models

### Direct Relationships
```
Domain
    └── PromptGroup (FK: domain)
            ├── theme (CharField)
            └── Prompt (FK: group)
                    └── PromptAnalytics (FK: prompt)
                            ├── sentiment_category
                            ├── sentiment_score
                            └── is_mention

Domain
    └── SentimentAnalytics (FK: domain)
            ├── theme (CharField)
            ├── positive_percentage
            ├── neutral_percentage
            ├── negative_percentage
            ├── mention_count
            └── timestamp
```

### Conceptual Link
```
PromptGroup.theme ←→ SentimentAnalytics.theme
    (Same string value, linked by domain)
```

**Note**: There is NO foreign key between `PromptGroup` and `SentimentAnalytics`. They are linked conceptually through the `theme` field, which is a string value extracted from the prompt group.

---

## Example Scenario

### Step 1: PromptGroup Created
```python
PromptGroup.objects.create(
    group_id="Best Practices SEO Optimization",
    domain=acme_domain,
    theme="Best Practices SEO",  # ← Extracted theme
    track_status='INIT'
)
```

### Step 2: Initial SentimentAnalytics Created
```python
SentimentAnalytics.objects.create(
    domain=acme_domain,
    theme="Best Practices SEO",  # ← Same theme
    positive_percentage=0.0,
    neutral_percentage=0.0,
    negative_percentage=0.0,
    mention_count=0,
    timestamp=date.today()
)
```

### Step 3: Prompts Processed → PromptAnalytics Created
```python
# For each prompt in the group, across platforms:
PromptAnalytics.objects.create(
    prompt=prompt,
    platform='ChatGPT',
    sentiment_category='positive',
    sentiment_score=0.75,
    is_mention=True,
    is_published=True
)
```

### Step 4: Group Complete → SentimentAnalytics Updated
```python
# After all prompts processed:
# Positive: 7, Neutral: 2, Negative: 1, Total: 10

SentimentAnalytics.objects.update_or_create(
    domain=acme_domain,
    theme="Best Practices SEO",
    platform=None,
    timestamp=date.today(),
    defaults={
        'positive_percentage': 70.0,   # 7/10 * 100
        'neutral_percentage': 20.0,    # 2/10 * 100
        'negative_percentage': 10.0,   # 1/10 * 100
        'mention_count': 10
    }
)
```

---

## Key Features

### 1. Automatic Theme Extraction
- Uses NLP (sentence transformers + clustering) to group similar prompts
- Extracts meaningful theme from cluster representative
- No manual theme assignment needed

### 2. Initial Zero-Value Records
- `SentimentAnalytics` created immediately when `PromptGroup` is created
- Allows for tracking progress even before analytics are processed
- Frontend can show "0% analyzed" status

### 3. Incremental Updates
- `SentimentAnalytics` updated when group processing completes
- Uses `update_or_create` to handle both new and existing records
- Daily snapshots (keyed by `timestamp`)

### 4. Aggregation by Theme
- Multiple `PromptGroups` can have the same theme
- Each theme gets one `SentimentAnalytics` record per day
- Enables theme-based trend analysis over time

---

## Query Examples

### Get All Themes for a Domain
```python
themes = SentimentAnalytics.objects.filter(
    domain=domain
).values_list('theme', flat=True).distinct()
```

### Get Sentiment Timeline for a Theme
```python
sentiment_timeline = SentimentAnalytics.objects.filter(
    domain=domain,
    theme="Product Quality"
).order_by('timestamp')
```

### Get All PromptGroups for a Theme
```python
groups_for_theme = PromptGroup.objects.filter(
    domain=domain,
    theme="Product Quality"
)
```

### Get Latest Sentiment Summary for Domain
```python
latest_sentiments = SentimentAnalytics.objects.filter(
    domain=domain,
    timestamp=date.today()
).order_by('-mention_count')
```

---

## Configuration

### Theme Extraction Stop Words
Defined in `_extract_theme_from_group()`:
```python
stop_words = {
    'what', 'how', 'why', 'when', 'where', 'who',
    'the', 'is', 'are', 'a', 'an', 'for', 'to', 'of', 'in', 'on', 'at'
}
```

### Theme Length Limit
- Maximum 50 characters for clean display
- Truncates at word boundary if longer

### Sentiment Aggregation Filters
- Only counts `is_mention=True` records
- Only counts `is_published=True` records
- Groups by `sentiment_category` field

---

## Future Enhancements

### 1. Platform-Specific Sentiment
Currently aggregates across all platforms. Could be extended to create separate `SentimentAnalytics` records per platform:
```python
SentimentAnalytics.objects.update_or_create(
    domain=domain,
    theme=theme,
    platform='ChatGPT',  # ← Specific platform
    timestamp=today,
    defaults={...}
)
```

### 2. Advanced Theme Extraction
Could use more sophisticated NLP:
- Named Entity Recognition (NER)
- Topic modeling (LDA)
- BERT-based keyword extraction
- Multi-word expressions (MWE) detection

### 3. Theme Hierarchies
Could create parent-child theme relationships:
- "Product" → "Product Quality", "Product Features"
- "Customer Service" → "Response Time", "Satisfaction"

### 4. Historical Sentiment Trends
Track sentiment changes over time:
- Week-over-week comparison
- Month-over-month trends
- Seasonal patterns

---

## Testing Checklist

✅ Theme field added to PromptGroup model  
✅ Migration created and applied (backend & engine)  
✅ Theme extraction implemented in DomainProcessor  
✅ Initial SentimentAnalytics created with PromptGroup  
✅ Sentiment aggregation implemented in PromptAnalyticsProcessor  
✅ Update logic uses update_or_create for daily records  
✅ No linter errors  

---

## Deployment Notes

1. **Database Migration**: Run migrations on production database
   ```bash
   cd backend
   python manage.py migrate prompts
   ```

2. **Engine Restart**: Restart engine workers to load new code
   ```bash
   supervisorctl restart llm-monitor-engine
   ```

3. **Backfill Themes**: For existing PromptGroups without themes, run backfill script:
   ```python
   # TODO: Create backfill script if needed
   ```

---

## Conclusion

This implementation successfully links `PromptGroup` and `SentimentAnalytics` through NLP-extracted themes, enabling:
- Automatic theme categorization
- Sentiment tracking by theme
- Trend analysis over time
- Clean separation between raw data (PromptAnalytics) and aggregated insights (SentimentAnalytics)

All changes are backward compatible and preserve existing functionality.

