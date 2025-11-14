# How to Run Celery in LLM Monitor

## 📍 Important Note
**Celery is configured in the ENGINE, not the Backend.**

The backend is a simple Django REST API server that doesn't use Celery. All background processing (domain processing, prompt analytics) is handled by the **Engine** using Celery.

---

## 🏗️ Architecture Overview

```
┌─────────────────┐         ┌─────────────────┐
│    Backend      │         │     Engine      │
│  Django + DRF   │◄────────┤  Django + Celery│
│  Port: 8000     │  REST   │  Port: 8001     │
│  No Celery      │   API   │  Has Celery     │
└─────────────────┘         └────────┬────────┘
                                     │
                            ┌────────┴────────┐
                            │                 │
                      ┌─────▼─────┐    ┌─────▼─────┐
                      │  Celery   │    │   Redis   │
                      │  Worker   │    │  Broker   │
                      └───────────┘    └───────────┘
```

---

## 📋 Prerequisites

### 1. Install Redis (Celery Broker)

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

**Check Redis is running:**
```bash
redis-cli ping
# Should return: PONG
```

### 2. Verify Engine Dependencies
```bash
cd /home/hts-005/Documents/python/v3.12/llm-monitor/engine
pip list | grep celery
# Should show: celery 5.3.4

pip list | grep redis
# Should show: redis 5.0.1
```

If not installed:
```bash
pip install celery==5.3.4 redis==5.0.1
```

---

## 🚀 Running Celery (Engine)

### Step 1: Start the Backend (REST API)
```bash
cd /home/hts-005/Documents/python/v3.12/llm-monitor/backend
source /home/hts-005/Documents/python/v3.12/env/bin/activate
python manage.py runserver 0.0.0.0:8000
```

Keep this terminal open.

---

### Step 2: Start the Engine Django Server (Optional)
```bash
# New terminal
cd /home/hts-005/Documents/python/v3.12/llm-monitor/engine
source /home/hts-005/Documents/python/v3.12/env/bin/activate
python manage.py runserver 0.0.0.0:8001
```

Keep this terminal open.

---

### Step 3: Start Celery Worker (Engine)
```bash
# New terminal
cd /home/hts-005/Documents/python/v3.12/llm-monitor/engine
source /home/hts-005/Documents/python/v3.12/env/bin/activate

# Start Celery worker
celery -A llm_monitor_engine worker --loglevel=info
```

**Output should look like:**
```
 -------------- celery@hostname v5.3.4 (emerald-rush)
--- ***** ----- 
-- ******* ---- Linux-6.14.0-33-generic-x86_64-with-glibc2.35 2025-11-05
- *** --- * --- 
- ** ---------- [config]
- ** ---------- .> app:         llm_monitor_engine:0x7f8b4c0a0
- ** ---------- .> transport:   redis://localhost:6379//
- ** ---------- .> results:     disabled://
- *** --- * --- .> concurrency: 8 (prefork)
-- ******* ---- .> task events: OFF (enable -E to monitor)
--- ***** ----- 

[tasks]
  . core.processing_tasks.process_domain_task
  . core.processing_tasks.process_prompt_analytics_task
  . core.processing_tasks.process_prompt_analytics_scheduler
  . core.processing_tasks.scheduler_tick

[2025-11-05 10:00:00,000: INFO/MainProcess] Connected to redis://localhost:6379//
[2025-11-05 10:00:00,000: INFO/MainProcess] mingle: searching for neighbors
[2025-11-05 10:00:00,000: INFO/MainProcess] mingle: all alone
[2025-11-05 10:00:00,000: INFO/MainProcess] celery@hostname ready.
```

Keep this terminal open.

---

### Step 4: Start Celery Beat (Scheduler) - Optional
```bash
# New terminal
cd /home/hts-005/Documents/python/v3.12/llm-monitor/engine
source /home/hts-005/Documents/python/v3.12/env/bin/activate

# Start Celery beat scheduler
celery -A llm_monitor_engine beat --loglevel=info
```

**Output should look like:**
```
celery beat v5.3.4 (emerald-rush) is starting.
__    -    ... [config]
LocalTime -> 2025-11-05 10:00:00
Configuration ->
    . broker -> redis://localhost:6379//
    . loader -> celery.loaders.app.AppLoader
    . scheduler -> celery.beat.PersistentScheduler
    . db -> celerybeat-schedule
    . logfile -> [stderr]@%INFO
    . maxinterval -> 5.00 minutes (300s)
```

Keep this terminal open.

---

## 🔧 Celery Configuration

### Current Celery Tasks

**File:** `engine/core/processing_tasks.py`

1. **`process_domain_task(domain_id)`**
   - Processes a single domain
   - Scrapes keywords → Generates prompts → Groups prompts → Stores in DB
   
2. **`scheduler_tick()`**
   - Checks for domains in `INIT` status
   - Schedules them for processing
   - Respects `MAX_CONCURRENT_DOMAINS` limit

3. **`process_prompt_analytics_task(prompt_id)`**
   - Processes a single prompt with AI platforms (ChatGPT, Gemini, Perplexity)
   - Generates analytics records
   
4. **`process_prompt_analytics_scheduler()`**
   - Schedules prompt analytics processing for ready prompts

---

## 📊 Celery Settings

**File:** `engine/llm_monitor_engine/settings.py`

Add these settings if not present:
```python
# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True

# Task routing (optional)
CELERY_TASK_ROUTES = {
    'core.processing_tasks.process_domain_task': {'queue': 'domain_processing'},
    'core.processing_tasks.process_prompt_analytics_task': {'queue': 'prompt_analytics'},
}

# Celery Beat Schedule (optional)
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'schedule-domains-every-30-seconds': {
        'task': 'core.processing_tasks.scheduler_tick',
        'schedule': 30.0,  # Every 30 seconds
    },
    'schedule-prompt-analytics-every-minute': {
        'task': 'core.processing_tasks.process_prompt_analytics_scheduler',
        'schedule': 60.0,  # Every 60 seconds
    },
}

# Processing limits
MAX_CONCURRENT_DOMAINS = 10
MAX_CONCURRENT_PROMPTS = 50
```

---

## 🎯 Testing Celery

### 1. Manual Task Trigger (Python Shell)
```bash
cd /home/hts-005/Documents/python/v3.12/llm-monitor/engine
python manage.py shell
```

```python
from core.processing_tasks import process_domain_task, process_prompt_analytics_task

# Trigger domain processing
domain_id = 1
task = process_domain_task.delay(domain_id)
print(f"Task ID: {task.id}")

# Trigger prompt analytics
prompt_id = 1
task = process_prompt_analytics_task.delay(prompt_id)
print(f"Task ID: {task.id}")
```

### 2. Check Task Status
```python
from celery.result import AsyncResult

task_id = "your-task-id-here"
result = AsyncResult(task_id)
print(f"Status: {result.status}")
print(f"Result: {result.result}")
```

### 3. Monitor Redis Queue
```bash
redis-cli

# Check queue length
LLEN celery

# View pending tasks (first 10)
LRANGE celery 0 9
```

---

## 🔍 Monitoring Celery

### Flower (Web-based monitoring tool)

**Install Flower:**
```bash
pip install flower
```

**Start Flower:**
```bash
cd /home/hts-005/Documents/python/v3.12/llm-monitor/engine
celery -A llm_monitor_engine flower --port=5555
```

**Access:**
Open browser: http://localhost:5555

Features:
- Real-time task monitoring
- Worker status
- Task history
- Task statistics

---

## 🛑 Stopping Celery

### Stop Celery Worker
Press `Ctrl+C` in the worker terminal, or:
```bash
# Find process
ps aux | grep celery

# Kill gracefully
pkill -f "celery worker"

# Force kill if needed
pkill -9 -f "celery worker"
```

### Stop Celery Beat
Press `Ctrl+C` in the beat terminal, or:
```bash
pkill -f "celery beat"
```

---

## 🐛 Troubleshooting

### Problem 1: "Connection refused" error
**Cause:** Redis is not running

**Solution:**
```bash
sudo systemctl start redis
redis-cli ping  # Should return PONG
```

### Problem 2: Tasks not executing
**Cause:** Worker not running or not connected

**Check:**
```bash
# Check worker logs
celery -A llm_monitor_engine inspect active

# Check registered tasks
celery -A llm_monitor_engine inspect registered
```

### Problem 3: "No module named 'celery'"
**Cause:** Celery not installed in virtual environment

**Solution:**
```bash
source /home/hts-005/Documents/python/v3.12/env/bin/activate
pip install celery==5.3.4 redis==5.0.1
```

### Problem 4: "Cannot import name 'celery'"
**Cause:** Wrong directory or DJANGO_SETTINGS_MODULE not set

**Solution:**
```bash
cd /home/hts-005/Documents/python/v3.12/llm-monitor/engine
export DJANGO_SETTINGS_MODULE=llm_monitor_engine.settings
celery -A llm_monitor_engine worker --loglevel=info
```

### Problem 5: Tasks stuck in "PENDING"
**Cause:** Result backend misconfigured or worker crashed

**Solution:**
```bash
# Restart worker
pkill -f "celery worker"
celery -A llm_monitor_engine worker --loglevel=info

# Check Redis
redis-cli
> KEYS *
```

---

## 🚀 Production Deployment

### Using Supervisor (Recommended)

**Install Supervisor:**
```bash
sudo apt install supervisor
```

**Create Supervisor config:**
`/etc/supervisor/conf.d/llm-monitor-celery.conf`
```ini
[program:llm-monitor-celery-worker]
command=/home/hts-005/Documents/python/v3.12/env/bin/celery -A llm_monitor_engine worker --loglevel=info
directory=/home/hts-005/Documents/python/v3.12/llm-monitor/engine
user=hts-005
numprocs=1
stdout_logfile=/var/log/llm-monitor/celery-worker.log
stderr_logfile=/var/log/llm-monitor/celery-worker-error.log
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=600

[program:llm-monitor-celery-beat]
command=/home/hts-005/Documents/python/v3.12/env/bin/celery -A llm_monitor_engine beat --loglevel=info
directory=/home/hts-005/Documents/python/v3.12/llm-monitor/engine
user=hts-005
numprocs=1
stdout_logfile=/var/log/llm-monitor/celery-beat.log
stderr_logfile=/var/log/llm-monitor/celery-beat-error.log
autostart=true
autorestart=true
startsecs=10
```

**Create log directory:**
```bash
sudo mkdir -p /var/log/llm-monitor
sudo chown hts-005:hts-005 /var/log/llm-monitor
```

**Start services:**
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start llm-monitor-celery-worker
sudo supervisorctl start llm-monitor-celery-beat
```

**Check status:**
```bash
sudo supervisorctl status
```

---

## 📝 Quick Reference

### Start Everything (Development)
```bash
# Terminal 1: Redis (if not running as service)
redis-server

# Terminal 2: Backend
cd backend && python manage.py runserver 0.0.0.0:8000

# Terminal 3: Engine
cd engine && python manage.py runserver 0.0.0.0:8001

# Terminal 4: Celery Worker
cd engine && celery -A llm_monitor_engine worker -l info

# Terminal 5: Celery Beat (optional)
cd engine && celery -A llm_monitor_engine beat -l info
```

### Useful Commands
```bash
# Check Celery tasks
celery -A llm_monitor_engine inspect active
celery -A llm_monitor_engine inspect registered
celery -A llm_monitor_engine inspect stats

# Purge all tasks
celery -A llm_monitor_engine purge

# List scheduled tasks
celery -A llm_monitor_engine inspect scheduled
```

---

## 🎓 Summary

| Component | Location | Port | Purpose |
|-----------|----------|------|---------|
| **Backend** | `/backend` | 8000 | REST API (Django + DRF) |
| **Engine** | `/engine` | 8001 | Processing Engine (Django) |
| **Celery Worker** | `/engine` | - | Background task execution |
| **Celery Beat** | `/engine` | - | Periodic task scheduler |
| **Redis** | System | 6379 | Message broker |
| **Flower** | `/engine` | 5555 | Monitoring UI (optional) |

**Backend does NOT use Celery** - it's a simple REST API.  
**Engine uses Celery** - for background processing of domains and prompts.

---

## ✅ Checklist for First Run

- [ ] Redis installed and running
- [ ] Engine dependencies installed (`celery`, `redis`)
- [ ] Backend running on port 8000
- [ ] Engine running on port 8001 (optional)
- [ ] Celery worker started
- [ ] Celery beat started (optional, for scheduled tasks)
- [ ] Test task execution (via shell or API)
- [ ] Check logs for errors

---

For more information on Celery, visit: https://docs.celeryq.dev/

