# Stuck Prompts Fix - Reset Utility

## 🐛 Problem

Prompts were getting stuck in **"SCHD" (Scheduled)** status and not progressing to completion.

### **Root Cause**

In `engine/core/prompt_analytics_processor.py`, the `schedule_tick()` method:
1. Marks prompts as "SCHD" (Scheduled)
2. Calls `self.process_single_prompt(prompt.id)` **synchronously**
3. If an error occurs or processing hangs, the prompt stays stuck in "SCHD"

---

## ✅ Solution

Created a **Reset Stuck Prompts** endpoint that automatically resets prompts (and groups) that have been stuck in "SCHD" status for too long.

---

## 📝 Implementation

### **New API Endpoint**

**URL:** `POST /api/prompts/reset-stuck/`

**Purpose:** Reset prompts and groups stuck in SCHD status

**Parameters:**
```json
{
  "timeout_minutes": 30  // Optional, defaults to 30 minutes
}
```

**Response:**
```json
{
  "success": true,
  "message": "Reset 5 stuck prompts and 1 stuck groups",
  "reset_prompts": 5,
  "reset_groups": 1,
  "timeout_minutes": 30
}
```

---

### **How It Works**

```python
@api_view(['POST'])
@permission_classes([AllowAny])
def reset_stuck_prompts(request):
    """Reset prompts that are stuck in SCHD status for more than N minutes."""
    
    # 1. Get timeout (default 30 minutes)
    timeout_minutes = int(request.data.get('timeout_minutes', 30))
    cutoff_time = timezone.now() - timedelta(minutes=timeout_minutes)
    
    # 2. Find stuck prompts (SCHD + not updated recently)
    stuck_prompts = Prompt.objects.filter(
        track_status='SCHD',
        modified_at__lt=cutoff_time
    )
    
    # 3. Reset to INIT so they can be reprocessed
    stuck_prompts.update(
        track_status='INIT',
        track_message='Reset from SCHD (stuck)',
        tracked_at=timezone.now()
    )
    
    # 4. Also reset stuck PromptGroups
    stuck_groups = PromptGroup.objects.filter(
        track_status='SCHD',
        modified_at__lt=cutoff_time
    )
    stuck_groups.update(
        track_status='INIT',
        track_message='Reset from SCHD (stuck)',
        tracked_at=timezone.now()
    )
```

---

## 🚀 Usage

### **Manual Reset via API**

Reset prompts stuck for more than 30 minutes (default):
```bash
curl -X POST http://127.0.0.1:8001/api/prompts/reset-stuck/
```

Reset prompts stuck for more than 10 minutes:
```bash
curl -X POST http://127.0.0.1:8001/api/prompts/reset-stuck/ \
  -H "Content-Type: application/json" \
  -d '{"timeout_minutes": 10}'
```

---

### **Check Stuck Prompts**

Query the database to see stuck prompts:
```python
from shared_models.models import Prompt, PromptGroup
from django.utils import timezone
from datetime import timedelta

# Find prompts stuck for more than 30 minutes
cutoff = timezone.now() - timedelta(minutes=30)

stuck_prompts = Prompt.objects.filter(
    track_status='SCHD',
    modified_at__lt=cutoff
)

print(f"Found {stuck_prompts.count()} stuck prompts:")
for p in stuck_prompts:
    print(f"  - Prompt {p.id}: {p.prompt[:50]}... (stuck since {p.modified_at})")
```

---

### **Check Processing Status**

View current status via API:
```bash
curl http://127.0.0.1:8001/api/status/
```

Response includes counts by status:
```json
{
  "success": true,
  "data": {
    "domain_counts": {
      "INIT": 0,
      "SCHD": 1,
      "PROC": 0,
      "COMP": 5,
      "FAIL": 0
    }
  }
}
```

---

## 🔍 Why Prompts Get Stuck

### **Common Causes**

1. **API Timeout**: ChatGPT/Gemini/Perplexity API takes too long and times out
2. **Network Error**: Connection lost during processing
3. **Exception Between Status Updates**: Error occurs after marking "SCHD" but before `process_single_prompt()` runs
4. **Celery Worker Crash**: Worker dies mid-processing
5. **Rate Limiting**: AI platform blocks requests temporarily

### **Status Flow**

```
INIT → SCHD → PROC → COMP ✅
              ↓
            (STUCK if error here)
```

**Problem Zone:** Between SCHD and PROC, if `process_single_prompt()` never runs or fails silently.

---

## 🛠️ Long-Term Solutions

### **1. Use Celery Task Instead of Direct Call**

**Current (Problematic):**
```python
# In schedule_tick()
self.process_single_prompt(prompt.id)  # ❌ Synchronous, no retry
```

**Better (Future Enhancement):**
```python
# In schedule_tick()
from .processing_tasks import process_prompt_analytics_task
process_prompt_analytics_task.delay(prompt.id)  # ✅ Async with retry
```

This would make processing asynchronous and add automatic retry logic.

---

### **2. Add Timeout to Processing**

Add a timeout to `process_single_prompt()`:
```python
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("Processing took too long")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(300)  # 5 minute timeout

try:
    self.process_single_prompt(prompt.id)
finally:
    signal.alarm(0)  # Disable alarm
```

---

### **3. Automatic Recovery in Celery Beat**

Add a periodic task to auto-reset stuck prompts:
```python
# In celerybeat_schedule
'reset-stuck-prompts': {
    'task': 'core.tasks.reset_stuck_prompts_task',
    'schedule': crontab(minute='*/15'),  # Every 15 minutes
},
```

---

### **4. Better Error Handling**

Wrap processing in comprehensive try-except:
```python
try:
    prompt.track_status = 'SCHD'
    prompt.save()
    
    result = self.process_single_prompt(prompt.id)
    
except Exception as e:
    logger.error(f"Error processing prompt {prompt.id}: {e}")
    prompt.track_status = 'INIT'  # Reset instead of leaving stuck
    prompt.track_message = f'Reset due to error: {str(e)}'
    prompt.save()
```

---

## 📊 Monitoring

### **Query Stuck Prompts Count**
```sql
SELECT COUNT(*) 
FROM prompts 
WHERE track_status = 'SCHD' 
  AND modified_at < NOW() - INTERVAL '30 minutes';
```

### **Check Oldest Stuck Prompt**
```sql
SELECT id, prompt, track_status, modified_at 
FROM prompts 
WHERE track_status = 'SCHD' 
ORDER BY modified_at ASC 
LIMIT 1;
```

### **Status Distribution**
```sql
SELECT track_status, COUNT(*) 
FROM prompts 
GROUP BY track_status;
```

---

## 🎯 Best Practices

1. **Regular Resets**: Run reset endpoint every 30 minutes via cron
2. **Monitor Logs**: Watch for errors in Celery worker logs
3. **Check Status API**: Use `/api/status/` to monitor processing
4. **Adjust Timeout**: If AI APIs are slow, increase timeout_minutes
5. **Scale Workers**: Add more Celery workers if processing is slow

---

## ✅ Quick Fix Steps

If you have stuck prompts right now:

1. **Reset them immediately:**
   ```bash
   curl -X POST http://127.0.0.1:8001/api/prompts/reset-stuck/ \
     -H "Content-Type: application/json" \
     -d '{"timeout_minutes": 5}'
   ```

2. **Check if they're processing:**
   ```bash
   curl http://127.0.0.1:8001/api/prompts/status/<DOMAIN_ID>/
   ```

3. **Restart Celery worker** (to clear any hung tasks):
   ```bash
   pkill -f "celery.*worker"
   cd engine
   celery -A llm_monitor_engine worker -l info &
   ```

4. **Restart Celery beat** (scheduler):
   ```bash
   pkill -f "celery.*beat"
   celery -A llm_monitor_engine beat -l info &
   ```

---

## 📁 Files Modified

1. **`engine/core/views.py`** - Added `reset_stuck_prompts()` endpoint
2. **`engine/core/urls.py`** - Added route `/api/prompts/reset-stuck/`

---

## 🚀 Result

You now have a tool to **automatically recover from stuck prompts** without manual database intervention! 🎉

**Next Steps:**
- Use this endpoint when prompts are stuck
- Consider implementing automatic periodic resets
- Monitor for patterns (which prompts/platforms get stuck most)
- Improve error handling in the processing pipeline

