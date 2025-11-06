# Competitor Processing Flow - Complete Guide

## 📋 **Overview**

Competitor processing uses **`competitor_prompt_analytics`** table (NOT `competitor_prompts`). Here's the complete flow:

---

## 🔄 **Complete Processing Flow**

### **Step 1: Create Competitor**

```bash
POST /api/competitors/
{
  "domain": 1,
  "name": "Nike",
  "url": "https://www.nike.com"
}
```

**Result:**
- Creates `Competitor` record in `competitors` table
- Sets `track_status = 'INIT'`

---

### **Step 2: Trigger Processing**

```bash
POST /api/competitors/process-single/
{
  "competitor_id": 1
}
```

**What Happens:**

#### **2.1: Link Prompts to Competitor**

**Method:** `_link_prompts_to_competitor(competitor)`

```python
# Find all prompts with completed analytics for this domain
prompts_with_analytics = Prompt.objects.filter(
    group__domain_id=competitor.domain.id,
    analytics__track_status='COMP'
).distinct()

# For each prompt, create CompetitorPromptAnalytics record
for prompt in prompts_with_analytics:
    CompetitorPromptAnalytics.objects.get_or_create(
        competitor=competitor,
        prompt=prompt,
        defaults={
            'track_status': 'INIT',
            'track_message': 'Ready for processing',
            'platform': 'ChatGPT'
        }
    )
```

**Result:**
- Creates records in **`competitor_prompt_analytics`** table
- Links each prompt with completed analytics to the competitor
- Each record has `track_status = 'INIT'`

**Table Used:** `competitor_prompt_analytics`

---

#### **2.2: Process Each Competitor-Prompt Pair**

**Method:** `_process_competitor_prompts(competitor)`

For each `CompetitorPromptAnalytics` with `track_status='INIT'`:

```python
# Get existing PromptAnalytics for this prompt
prompt_analytics = PromptAnalytics.objects.filter(
    prompt=comp_prompt.prompt,
    track_status='COMP'
).order_by('-tracked_at').first()

# Use existing context_summary (no new API calls!)
response_text = prompt_analytics.context_summary

# Analyze competitor mentions in the response
analytics = analyze_competitor_mention(
    response_text=response_text,
    competitor_name=competitor.name,
    competitor_url=competitor.url
)

# Update CompetitorPromptAnalytics
CompetitorPromptAnalytics.objects.update(
    track_status='COMP',
    is_mentioned=analytics['is_mentioned'],
    position=analytics['position'],
    mention_count=analytics['mention_count'],
    sentiment_category=analytics['sentiment_category'],
    sentiment_score=analytics['sentiment_score'],
    response_text=response_text,
    citation_list=prompt_analytics.citation_list,
    platform=prompt_analytics.platform
)
```

**Result:**
- Updates **`competitor_prompt_analytics`** records
- Extracts competitor mentions from existing `PromptAnalytics.context_summary`
- No new API calls (reuses existing data)
- Sets `track_status = 'COMP'` for each record

**Table Used:** `competitor_prompt_analytics`

---

#### **2.3: Aggregate Analytics**

**Method:** `_aggregate_competitor_analytics(competitor)`

```python
# Get all completed CompetitorPromptAnalytics
analytics_qs = CompetitorPromptAnalytics.objects.filter(
    competitor=competitor,
    track_status='COMP'
)

# Calculate aggregates
total_mentions = analytics_qs.aggregate(Sum('mention_count'))['mention_count__sum'] or 0
avg_position = analytics_qs.aggregate(Avg('position'))['position__avg'] or 0
avg_sentiment = analytics_qs.aggregate(Avg('sentiment_score'))['sentiment_score__avg'] or 0

# Update Competitor record
Competitor.objects.update(
    total_mentions=total_mentions,
    average_position=avg_position,
    sentiment_score=avg_sentiment,
    visibility_score=calculate_visibility(...),
    share_of_voice_percentage=calculate_sov(...)
)
```

**Result:**
- Updates **`competitors`** table with aggregated metrics
- Creates **`competitor_analytics`** records (time-series data)
- Creates **`share_of_voice_analytics`** records (market share)

**Tables Used:** 
- `competitors` (aggregated metrics)
- `competitor_analytics` (historical records)
- `share_of_voice_analytics` (market share)

---

## 📊 **Tables Used in Processing**

### **1. `competitor_prompt_analytics`** ⭐ **PRIMARY TABLE**

**Purpose:** Links competitors to prompts and stores analytics for each pair

**Structure:**
```sql
competitor_prompt_analytics
├── id
├── competitor_id (FK to competitors)
├── prompt_id (FK to prompts)
├── track_status (INIT → SCHD → PROC → COMP)
├── is_mentioned (boolean)
├── position (integer)
├── mention_count (integer)
├── sentiment_category (string)
├── sentiment_score (decimal)
├── platform (string)
├── response_text (text)
├── citation_list (JSON)
└── timestamps
```

**Usage:**
- Created in `_link_prompts_to_competitor()`
- Updated in `_process_single_competitor_prompt()`
- Queried in `_aggregate_competitor_analytics()`

---

### **2. `competitors`** ⭐ **AGGREGATE METRICS**

**Purpose:** Stores aggregated analytics per competitor

**Structure:**
```sql
competitors
├── id
├── domain_id (FK)
├── name
├── url
├── track_status (INIT → SCHD → PROC → COMP)
├── total_mentions (aggregated)
├── average_position (aggregated)
├── sentiment_score (aggregated)
├── visibility_score (calculated)
├── share_of_voice_percentage (calculated)
└── timestamps
```

**Usage:**
- Updated in `_aggregate_competitor_analytics()`
- Stores final aggregated results

---

### **3. `competitor_analytics`** 📈 **TIME-SERIES DATA**

**Purpose:** Historical records for trend analysis

**Structure:**
```sql
competitor_analytics
├── id
├── competitor_id (FK)
├── platform
├── total_mentions
├── position
├── sentiment_score
├── timestamp (date)
└── created_at
```

**Usage:**
- Created in `_aggregate_competitor_analytics()`
- One record per day/platform
- Used for trend analysis

---

### **4. `share_of_voice_analytics`** 📊 **MARKET SHARE**

**Purpose:** Market share calculations

**Structure:**
```sql
share_of_voice_analytics
├── id
├── domain_id (FK)
├── competitor_id (FK, nullable)
├── platform
├── share_percentage
├── mention_count
├── market_position (rank)
├── timestamp (date)
└── created_at
```

**Usage:**
- Created in `_update_share_of_voice()`
- One record per competitor/domain/date
- `competitor_id = NULL` means own brand

---

## 🔄 **Status Flow**

### **Competitor Status:**
```
INIT → SCHD → PROC → COMP (or FAIL)
```

### **CompetitorPromptAnalytics Status:**
```
INIT → SCHD → PROC → COMP (or FAIL)
```

---

## 📝 **Code Flow**

### **1. API Endpoint Called**
```python
POST /api/competitors/process-single/
{"competitor_id": 1}
```

### **2. View Handler**
```python
# engine/core/views.py
start_single_competitor_processing()
  ↓
processor = CompetitorProcessor()
  ↓
processor._link_prompts_to_competitor(competitor)
  ↓
processor._process_competitor_prompts(competitor)
  ↓
processor._aggregate_competitor_analytics(competitor)
```

### **3. Processing Methods**

#### **`_link_prompts_to_competitor()`**
- Queries `Prompt` with `analytics__track_status='COMP'`
- Creates `CompetitorPromptAnalytics` records
- **Table:** `competitor_prompt_analytics`

#### **`_process_competitor_prompts()`**
- Gets `CompetitorPromptAnalytics` with `track_status='INIT'`
- For each, calls `_process_single_competitor_prompt()`
- **Table:** `competitor_prompt_analytics`

#### **`_process_single_competitor_prompt()`**
- Gets `PromptAnalytics.context_summary`
- Analyzes competitor mentions
- Updates `CompetitorPromptAnalytics`
- **Table:** `competitor_prompt_analytics`

#### **`_aggregate_competitor_analytics()`**
- Queries `CompetitorPromptAnalytics` with `track_status='COMP'`
- Calculates aggregates
- Updates `Competitor`
- Creates `CompetitorAnalytics` and `ShareOfVoiceAnalytics`
- **Tables:** `competitors`, `competitor_analytics`, `share_of_voice_analytics`

---

## 🎯 **Key Points**

1. ✅ **Uses `competitor_prompt_analytics` table** (NOT `competitor_prompts`)
2. ✅ **Reuses existing `PromptAnalytics.context_summary`** (no new API calls)
3. ✅ **Links prompts automatically** from domain with completed analytics
4. ✅ **Processes synchronously** by default (no Celery required)
5. ✅ **Aggregates results** into `Competitor`, `CompetitorAnalytics`, and `ShareOfVoiceAnalytics`

---

## 📊 **Data Flow Diagram**

```
Competitor Created (INIT)
    ↓
Link Prompts
    ↓
Create CompetitorPromptAnalytics records
    ↓
For each CompetitorPromptAnalytics:
    Get PromptAnalytics.context_summary
    Analyze competitor mentions
    Update CompetitorPromptAnalytics
    ↓
Aggregate Results:
    Update Competitor (total_mentions, avg_position, etc.)
    Create CompetitorAnalytics (time-series)
    Create ShareOfVoiceAnalytics (market share)
    ↓
Competitor Status = COMP
```

---

## ✅ **Summary**

**Competitor processing uses:**
- ✅ `competitor_prompt_analytics` table (primary)
- ✅ `competitors` table (aggregates)
- ✅ `competitor_analytics` table (time-series)
- ✅ `share_of_voice_analytics` table (market share)

**Does NOT use:**
- ❌ `competitor_prompts` table (DEPRECATED)

**The flow is:**
1. Link prompts → Create `CompetitorPromptAnalytics` records
2. Process each → Extract from `PromptAnalytics.context_summary`
3. Aggregate → Update `Competitor` and create analytics records

