# Competitor Processing System - Complete Guide

## 📋 **Overview**

The Competitor Processing System is a comprehensive solution for tracking how competitors appear in AI platform responses (ChatGPT, Claude, etc.). It automatically tests prompts, analyzes competitor mentions, and calculates Share of Voice metrics.

---

## 🏗️ **Architecture**

### **System Components**

```
┌─────────────────────────────────────────────────────────────────┐
│                    Competitor Processing Flow                    │
└─────────────────────────────────────────────────────────────────┘

1. CREATE COMPETITOR (API)
   ├─> Set track_status = 'INIT'
   └─> Stored in competitors table

2. CELERY SCHEDULER (Periodic Task)
   ├─> Picks INIT competitors
   ├─> Links all domain prompts
   └─> Creates CompetitorPromptAnalytics records

3. COMPETITOR PROCESSOR
   ├─> Sends prompts to ChatGPT
   ├─> Analyzes competitor mentions
   └─> Stores results in CompetitorPromptAnalytics

4. AGGREGATION
   ├─> Updates Competitor aggregate fields
   ├─> Creates CompetitorAnalytics snapshot
   └─> Calculates ShareOfVoiceAnalytics

5. RESULTS (API)
   └─> Frontend displays competitor insights
```

---

## 📊 **Database Models**

### **1. Competitor** (Main Model)

Stores competitor brands being tracked for a domain.

```python
class Competitor(models.Model):
    # Core fields
    domain = ForeignKey(Domain)
    name = CharField(max_length=255)
    url = URLField(max_length=500)
    
    # Tracking fields
    track_status = CharField(max_length=4, choices=STATUS_CHOICES, default='INIT')
    track_message = TextField(blank=True, null=True)
    tracked_at = DateTimeField(null=True, blank=True)
    
    # Aggregate analytics (updated after processing)
    total_mentions = IntegerField(default=0)
    visibility_score = DecimalField(max_digits=5, decimal_places=2, default=0.0)
    sentiment_score = DecimalField(max_digits=5, decimal_places=2, default=0.0)
    average_position = DecimalField(max_digits=5, decimal_places=2, default=0.0)
    share_of_voice_percentage = DecimalField(max_digits=5, decimal_places=2, default=0.0)
    trend_percentage = DecimalField(max_digits=6, decimal_places=2, default=0.0)
```

**Status Flow:**
```
INIT → SCHD → PROC → COMP (or FAIL)
```

- **INIT**: Competitor just created, ready to be processed
- **SCHD**: Scheduled for processing (prompts being linked)
- **PROC**: Processing competitor analytics
- **COMP**: Completed processing
- **FAIL**: Processing failed

---

### **2. CompetitorPromptAnalytics** (NEW - Core Analytics Model)

Links competitors to prompts and stores analytics for each competitor-prompt pair.

```python
class CompetitorPromptAnalytics(models.Model):
    # Relationships
    competitor = ForeignKey(Competitor)
    prompt = ForeignKey(Prompt)
    
    # Tracking fields
    track_status = CharField(max_length=4, default='INIT')
    track_message = TextField(blank=True, null=True)
    tracked_at = DateTimeField(null=True, blank=True)
    
    # Analytics data (populated after ChatGPT testing)
    is_mentioned = BooleanField(default=False)
    position = IntegerField(null=True, blank=True)  # Position in AI response
    mention_count = IntegerField(default=0)
    sentiment_category = CharField(max_length=50)  # positive/neutral/negative
    sentiment_score = DecimalField(max_digits=5, decimal_places=2, default=0.0)
    platform = CharField(max_length=100)  # 'ChatGPT', 'Claude', etc.
    response_text = TextField(blank=True, null=True)  # Full AI response
    citation_list = JSONField(default=list, blank=True)  # URLs/citations
```

**Key Features:**
- **Many-to-Many**: One competitor can be tested against many prompts
- **Historical**: Records remain even if prompts change
- **Detailed**: Stores full response for analysis

---

### **3. CompetitorAnalytics** (Historical Snapshots)

Time-series data for competitor performance.

```python
class CompetitorAnalytics(models.Model):
    competitor = ForeignKey(Competitor)
    platform = CharField(max_length=100)
    total_mentions = IntegerField(default=0)
    position = DecimalField(max_digits=5, decimal_places=2, default=0.0)
    sentiment_score = DecimalField(max_digits=5, decimal_places=2, default=0.0)
    timestamp = DateField()  # Daily snapshot
```

**Purpose:** Track trends over time (daily snapshots).

---

### **4. ShareOfVoiceAnalytics** (Market Share)

Calculates each player's share of total mentions.

```python
class ShareOfVoiceAnalytics(models.Model):
    domain = ForeignKey(Domain)
    competitor = ForeignKey(Competitor, null=True, blank=True)  # NULL = own brand
    platform = CharField(max_length=100, null=True, blank=True)  # NULL = overall
    share_percentage = DecimalField(max_digits=5, decimal_places=2, default=0.0)
    mention_count = IntegerField(default=0)
    market_position = IntegerField(null=True, blank=True)  # Rank (1 = leader)
    timestamp = DateField()
```

**Key Features:**
- **NULL competitor**: Represents your own brand
- **NULL platform**: Represents aggregated data across all platforms
- **Market position**: Automatic ranking by share_percentage

---

## 🔄 **Processing Flow**

### **Step 1: Create Competitor (API)**

```bash
POST /api/competitors/
{
    "domain": 1,
    "name": "Nike",
    "url": "https://www.nike.com"
}
```

**What Happens:**
1. Competitor created with `track_status='INIT'`
2. All aggregate fields set to 0
3. Ready for processing

---

### **Step 2: Link Prompts**

**Triggered by:** Celery Scheduler (`process_competitor_scheduler`)

**Process:**
```python
# 1. Find INIT competitors
competitor = Competitor.objects.filter(track_status='INIT').first()

# 2. Get all completed prompts for this domain
prompts = Prompt.objects.filter(
    domain=competitor.domain,
    track_status='COMP'
)

# 3. Create CompetitorPromptAnalytics records
for prompt in prompts:
    CompetitorPromptAnalytics.objects.get_or_create(
        competitor=competitor,
        prompt=prompt,
        defaults={
            'track_status': 'INIT',
            'platform': 'ChatGPT'
        }
    )
```

**Result:** Each prompt is now linked to the competitor and ready for testing.

---

### **Step 3: Process Each Prompt**

**For each CompetitorPromptAnalytics:**

```python
# 1. Send prompt to ChatGPT
response = chatgpt_client.query_chatgpt(prompt.prompt_text)

# 2. Analyze if competitor is mentioned
analysis = analyze_competitor_mention(
    response_text=response['content'],
    competitor_name=competitor.name,
    competitor_url=competitor.url
)

# 3. Store results
CompetitorPromptAnalytics.objects.update(
    is_mentioned=analysis['is_mentioned'],
    position=analysis['position'],
    mention_count=analysis['mention_count'],
    sentiment_category=analysis['sentiment_category'],
    sentiment_score=analysis['sentiment_score'],
    response_text=response['content'],
    citation_list=analysis['citations'],
    track_status='COMP'
)
```

**Analysis Logic:**

1. **is_mentioned**: Does response contain competitor name?
2. **position**: Where in the list does competitor appear? (e.g., "1. Nike" → position=1)
3. **mention_count**: How many times mentioned?
4. **sentiment_category**: positive/neutral/negative (keyword-based)
5. **sentiment_score**: Numeric score (-1 to 1)
6. **citations**: URLs or references mentioning competitor

---

### **Step 4: Aggregate Results**

**After all prompts processed:**

```python
# 1. Update Competitor aggregate fields
analytics_qs = CompetitorPromptAnalytics.objects.filter(
    competitor=competitor,
    track_status='COMP'
)

totals = analytics_qs.aggregate(
    total_mentions=Sum('mention_count'),
    avg_position=Avg('position'),
    avg_sentiment=Avg('sentiment_score'),
    mentioned_count=Count('id', filter=Q(is_mentioned=True))
)

competitor.total_mentions = totals['total_mentions']
competitor.average_position = totals['avg_position']
competitor.sentiment_score = totals['avg_sentiment']
competitor.visibility_score = calculate_visibility_score(...)
competitor.save()

# 2. Create CompetitorAnalytics snapshot
CompetitorAnalytics.objects.create(
    competitor=competitor,
    platform='ChatGPT',
    total_mentions=totals['total_mentions'],
    position=totals['avg_position'],
    sentiment_score=totals['avg_sentiment'],
    timestamp=date.today()
)

# 3. Calculate Share of Voice
update_share_of_voice(competitor)
```

---

## 📈 **Share of Voice Calculation**

### **Formula**

```python
# 1. Get own brand mentions
own_mentions = PromptAnalytics.objects.filter(
    prompt__domain=domain,
    prompt__track_status='COMP'
).aggregate(total=Sum('total_mentions'))['total']

# 2. Get all competitors' mentions
competitors_mentions = Competitor.objects.filter(
    domain=domain,
    track_status='COMP'
).aggregate(total=Sum('total_mentions'))['total']

# 3. Total market
total_market_mentions = own_mentions + competitors_mentions

# 4. Competitor's share
competitor_share = (competitor.total_mentions / total_market_mentions) * 100

# 5. Store in ShareOfVoiceAnalytics
ShareOfVoiceAnalytics.objects.update_or_create(
    domain=domain,
    competitor=competitor,
    platform='ChatGPT',
    timestamp=date.today(),
    defaults={
        'share_percentage': competitor_share,
        'mention_count': competitor.total_mentions,
        'market_position': None  # Calculated next
    }
)

# 6. Calculate market positions (ranks)
sov_records = ShareOfVoiceAnalytics.objects.filter(
    domain=domain,
    timestamp=date.today()
).order_by('-share_percentage')

for rank, sov in enumerate(sov_records, start=1):
    sov.market_position = rank
    sov.save()
```

### **Example Output**

| Brand | Mention Count | Share % | Market Position |
|-------|---------------|---------|-----------------|
| Your Brand | 150 | 37.5% | 1 (Leader) |
| Nike | 120 | 30.0% | 2 |
| Adidas | 80 | 20.0% | 3 |
| Puma | 50 | 12.5% | 4 |
| **Total** | **400** | **100%** | - |

---

## 🎯 **Visibility Score Calculation**

```python
def calculate_visibility_score(total_prompts, mentioned_count, avg_position):
    """
    Visibility Score = (Mention Rate) * (Position Weight) * 100
    
    - Mention Rate: How often competitor appears (0-1)
    - Position Weight: Higher weight for better positions (1/position)
    - Result: Score from 0-100
    """
    if total_prompts == 0:
        return 0.0
    
    mention_rate = mentioned_count / total_prompts
    position_weight = 1.0 / (avg_position if avg_position > 0 else 1.0)
    
    score = min(mention_rate * position_weight * 100, 100)
    return round(score, 2)
```

**Examples:**

| Mentioned | Total Prompts | Avg Position | Visibility Score |
|-----------|---------------|--------------|------------------|
| 50 | 100 | 1.0 | 50.0 (High) |
| 50 | 100 | 3.0 | 16.7 (Medium) |
| 10 | 100 | 1.0 | 10.0 (Low) |
| 10 | 100 | 10.0 | 1.0 (Very Low) |

---

## 🔧 **Celery Tasks**

### **1. Periodic Scheduler** (Every 5 minutes)

```python
@shared_task
def process_competitor_scheduler():
    """
    Picks one INIT competitor and processes it.
    """
    processor = CompetitorProcessor(max_concurrent_prompts=10)
    return processor.schedule_tick()
```

**Configuration** (`llm_monitor_engine/celery.py`):

```python
app.conf.beat_schedule = {
    'process-competitor-scheduler': {
        'task': 'core.tasks.process_competitor_scheduler',
        'schedule': 300.0,  # Every 5 minutes
    },
}
```

---

### **2. Manual Processing Task**

```python
@shared_task
def process_single_competitor_task(competitor_id):
    """
    Process a specific competitor on-demand.
    """
    competitor = Competitor.objects.get(id=competitor_id)
    processor = CompetitorProcessor(max_concurrent_prompts=10)
    
    # Reset to INIT so it gets picked up
    competitor.track_status = 'INIT'
    competitor.save()
    
    return processor.schedule_tick()
```

---

## 🌐 **API Endpoints**

### **Competitor Management**

#### **1. List Competitors**
```bash
GET /api/competitors/
```

**Response:**
```json
[
    {
        "id": 1,
        "domain": 1,
        "domain_name": "Adidas",
        "name": "Nike",
        "url": "https://www.nike.com",
        "track_status": "COMP",
        "track_message": "Completed at 2025-11-05 10:30:00",
        "tracked_at": "2025-11-05T10:30:00Z",
        "total_mentions": 120,
        "visibility_score": 45.5,
        "sentiment_score": 0.75,
        "average_position": 1.5,
        "share_of_voice_percentage": 30.0,
        "trend_percentage": 5.2,
        "created_at": "2025-11-01T12:00:00Z",
        "modified_at": "2025-11-05T10:30:00Z"
    }
]
```

---

#### **2. Create Competitor**
```bash
POST /api/competitors/
{
    "domain": 1,
    "name": "Nike",
    "url": "https://www.nike.com"
}
```

**Response:**
```json
{
    "id": 1,
    "domain": 1,
    "name": "Nike",
    "url": "https://www.nike.com",
    "track_status": "INIT",
    "total_mentions": 0,
    "visibility_score": 0.0,
    ...
}
```

**Note:** Competitor is auto-set to `track_status='INIT'` and will be picked up by the scheduler.

---

#### **3. Trigger Processing**
```bash
POST /api/competitors/{id}/process/
```

**Response:**
```json
{
    "message": "Processing started for competitor Nike",
    "competitor_id": 1,
    "track_status": "INIT"
}
```

---

#### **4. Get Detailed Analytics**
```bash
GET /api/competitors/{id}/analytics/
```

**Response:**
```json
{
    "competitor": {
        "id": 1,
        "name": "Nike",
        ...
    },
    "statistics": {
        "total_prompts_tested": 100,
        "times_mentioned": 50,
        "mention_rate": 50.0,
        "average_position": 1.5,
        "average_sentiment": 0.75,
        "total_mention_count": 120
    },
    "recent_prompts": [
        {
            "id": 1,
            "competitor_name": "Nike",
            "prompt_text": "What are the best running shoes?",
            "is_mentioned": true,
            "position": 1,
            "mention_count": 2,
            "sentiment_category": "positive",
            "sentiment_score": 0.8,
            ...
        }
    ]
}
```

---

### **Competitor-Prompt Analytics**

#### **1. Get All Analytics for a Competitor**
```bash
GET /api/competitor-prompt-analytics/by_competitor/?competitor_id=1
```

---

#### **2. Find Opportunity Gaps**
```bash
GET /api/competitor-prompt-analytics/gaps/?domain_id=1&competitor_id=1
```

**Returns:** Prompts where competitor is in top 5 but you're not mentioned (opportunities).

---

### **Share of Voice Analytics**

```bash
GET /api/analytics/share-of-voice/?domain_id=1
```

**Response:**
```json
{
    "domain_id": 1,
    "timestamp": "2025-11-05",
    "players": [
        {
            "name": "Adidas (Your Brand)",
            "competitor_id": null,
            "mention_count": 150,
            "share_percentage": 37.5,
            "market_position": 1
        },
        {
            "name": "Nike",
            "competitor_id": 1,
            "mention_count": 120,
            "share_percentage": 30.0,
            "market_position": 2
        },
        {
            "name": "Puma",
            "competitor_id": 2,
            "mention_count": 80,
            "share_percentage": 20.0,
            "market_position": 3
        }
    ]
}
```

---

## ⚙️ **Settings Configuration**

Add to `engine/llm_monitor_engine/settings.py`:

```python
# Competitor Processing Settings
MAX_CONCURRENT_COMPETITOR_PROMPTS = 10  # Process 10 prompts at a time
```

---

## 🚀 **Running the System**

### **1. Start Celery Worker**

```bash
cd /home/hts-005/Documents/python/v3.12/llm-monitor/engine
source /home/hts-005/Documents/python/v3.12/env/bin/activate
celery -A llm_monitor_engine worker --loglevel=info
```

---

### **2. Start Celery Beat (Scheduler)**

```bash
cd /home/hts-005/Documents/python/v3.12/llm-monitor/engine
source /home/hts-005/Documents/python/v3.12/env/bin/activate
celery -A llm_monitor_engine beat --loglevel=info
```

---

### **3. Quick Start Script**

```bash
#!/bin/bash
cd /home/hts-005/Documents/python/v3.12/llm-monitor/engine
source /home/hts-005/Documents/python/v3.12/env/bin/activate

# Start worker in background
celery -A llm_monitor_engine worker --loglevel=info &

# Start beat in background
celery -A llm_monitor_engine beat --loglevel=info &

echo "Celery worker and beat started!"
```

---

## 📊 **Monitoring**

### **Check Competitor Status**

```python
from shared_models.models import Competitor

# View all competitors and their status
for comp in Competitor.objects.all():
    print(f"{comp.name}: {comp.track_status} - {comp.track_message}")
```

### **Check Processing Progress**

```python
from shared_models.models import CompetitorPromptAnalytics

comp_id = 1

# Count by status
stats = CompetitorPromptAnalytics.objects.filter(
    competitor_id=comp_id
).values('track_status').annotate(count=Count('id'))

for stat in stats:
    print(f"{stat['track_status']}: {stat['count']}")
```

---

## 🔍 **Debugging**

### **Common Issues**

#### **1. Competitor Stuck in INIT**

**Cause:** Celery Beat not running or scheduler task not configured.

**Fix:**
```bash
# Check if Celery Beat is running
ps aux | grep "celery.*beat"

# Start Celery Beat
celery -A llm_monitor_engine beat --loglevel=info
```

---

#### **2. No Prompts Linked**

**Cause:** Domain has no completed prompts (`Prompt.track_status != 'COMP'`).

**Fix:**
```python
# Check domain prompts
from shared_models.models import Prompt
Prompt.objects.filter(domain_id=1, track_status='COMP').count()

# If 0, run domain processor first
from core.processing_tasks import process_domain_task
process_domain_task.delay(1)
```

---

#### **3. Processing Stuck in PROC**

**Cause:** Exception during processing or Celery worker crashed.

**Fix:**
```python
# Reset stuck competitors
Competitor.objects.filter(track_status='PROC').update(
    track_status='INIT',
    track_message='Reset after being stuck'
)
```

---

## 📈 **Performance**

### **Expected Processing Times**

| Prompts | Time per Prompt | Total Time |
|---------|-----------------|------------|
| 10 | 5 seconds | ~1 minute |
| 50 | 5 seconds | ~5 minutes |
| 100 | 5 seconds | ~10 minutes |

**Note:** Time depends on ChatGPT API response time.

---

## 🎯 **Use Cases**

### **1. Competitive Intelligence**

- Track how often competitors appear in AI responses
- Identify which prompts favor competitors
- Monitor sentiment towards competitors

### **2. Market Positioning**

- Calculate Share of Voice across competitors
- Track market position over time
- Identify emerging competitors

### **3. Opportunity Analysis**

- Find prompts where competitors dominate (gaps)
- Identify prompts to optimize
- Benchmark against competition

---

## 📝 **Summary**

✅ **Competitor Model**: Extended with tracking fields
✅ **CompetitorPromptAnalytics**: New model linking competitors to prompts
✅ **CompetitorProcessor**: Complete processing logic
✅ **Celery Tasks**: Automated scheduling and processing
✅ **API Endpoints**: Full CRUD + analytics
✅ **Share of Voice**: Automatic market share calculation
✅ **Documentation**: This comprehensive guide!

---

## 🚀 **Next Steps**

1. **Run migrations**: `python manage.py migrate`
2. **Start Celery**: Worker + Beat
3. **Create competitor**: Via API
4. **Wait for processing**: ~5 minutes
5. **View results**: Via analytics endpoint

**Your competitor tracking system is ready!** 🎉

