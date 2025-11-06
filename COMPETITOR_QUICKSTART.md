# Competitor Processing - Quick Start Guide

## 🚀 **Get Started in 5 Minutes**

---

## 1️⃣ **Verify Migrations**

```bash
cd /home/hts-005/Documents/python/v3.12/llm-monitor/backend
source /home/hts-005/Documents/python/v3.12/env/bin/activate
python manage.py migrate
```

**Expected Output:**
```
Operations to perform:
  Apply all migrations: competitors
Running migrations:
  Applying competitors.0002_competitorpromptanalytics_competitor_track_message_and_more... OK
```

---

## 2️⃣ **Start Celery (if not running)**

```bash
cd /home/hts-005/Documents/python/v3.12/llm-monitor/engine
source /home/hts-005/Documents/python/v3.12/env/bin/activate

# Terminal 1: Start Worker
celery -A llm_monitor_engine worker --loglevel=info &

# Terminal 2: Start Beat (Scheduler)
celery -A llm_monitor_engine beat --loglevel=info &
```

---

## 3️⃣ **Create Your First Competitor**

### **Option A: via API (curl)**

```bash
curl -X POST http://127.0.0.1:8000/api/competitors/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "domain": 1,
    "name": "Nike",
    "url": "https://www.nike.com"
  }'
```

### **Option B: via Django Shell**

```python
from competitors.models import Competitor
from domains.models import Domain

# Create competitor
competitor = Competitor.objects.create(
    domain=Domain.objects.get(id=1),
    name="Nike",
    url="https://www.nike.com"
    # track_status='INIT' is set automatically
)

print(f"Created competitor: {competitor.name} (ID: {competitor.id})")
```

---

## 4️⃣ **Monitor Processing**

### **Check Status**

```python
from competitors.models import Competitor

competitor = Competitor.objects.get(id=1)
print(f"Status: {competitor.track_status}")
print(f"Message: {competitor.track_message}")
```

**Status Flow:**
```
INIT → SCHD → PROC → COMP
(~5 minutes total)
```

---

## 5️⃣ **View Results**

### **Get Analytics**

```bash
curl http://127.0.0.1:8000/api/competitors/1/analytics/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### **Get Share of Voice**

```bash
curl http://127.0.0.1:8000/api/analytics/share-of-voice/?domain_id=1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 📊 **What Gets Processed?**

When you create a competitor:

1. **System links** all completed prompts from the domain
2. **Sends each prompt** to ChatGPT
3. **Analyzes** if/how competitor is mentioned
4. **Stores results** in `CompetitorPromptAnalytics`
5. **Aggregates** into competitor metrics
6. **Calculates** Share of Voice

---

## 🎯 **Key Metrics You'll See**

| Metric | Description |
|--------|-------------|
| **total_mentions** | How many times competitor appears |
| **average_position** | Average ranking in AI responses |
| **visibility_score** | Combined metric (0-100) |
| **sentiment_score** | How positively mentioned (-1 to 1) |
| **share_of_voice_percentage** | Market share vs. your brand |

---

## 🔍 **Debugging**

### **If Processing Doesn't Start:**

1. Check Celery is running:
```bash
ps aux | grep celery
```

2. Check Celery logs:
```bash
tail -f /path/to/celery.log
```

3. Manually trigger:
```bash
curl -X POST http://127.0.0.1:8000/api/competitors/1/process/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### **If No Prompts Linked:**

Make sure domain has completed prompts:

```python
from prompts.models import Prompt

# Check prompts
count = Prompt.objects.filter(
    domain_id=1,
    track_status='COMP'
).count()

print(f"Completed prompts: {count}")

# If 0, process domain first
from engine.core.processing_tasks import process_domain_task
process_domain_task.delay(1)
```

---

## 📖 **Full Documentation**

- **Complete Guide**: `COMPETITOR_PROCESSING_SYSTEM.md`
- **Implementation Details**: `COMPETITOR_IMPLEMENTATION_SUMMARY.md`
- **This Quick Start**: `COMPETITOR_QUICKSTART.md`

---

## ✅ **That's It!**

Your competitor tracking system is now running! 🎉

**Next Steps:**
- Add more competitors
- Review analytics
- Set up alerts (future enhancement)
- Export reports (future enhancement)

