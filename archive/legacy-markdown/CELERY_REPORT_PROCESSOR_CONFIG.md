# Celery Configuration for Report Email Processor

## Overview

The report email processor uses Celery for asynchronous task processing. Celery Beat runs periodic tasks to check for due scheduled reports, and Celery Workers execute the actual report generation and email delivery.

## Architecture

```
Celery Beat (Scheduler)
  ↓ (every 15 seconds)
process_report_email_scheduler task
  ↓
ReportEmailProcessor.process_due_reports()
  ↓
For each due report:
  ├─ Create GeneratedReport
  ├─ Call Backend API (generate report file)
  └─ Send Email via Mailgun
```

## Configuration Files

### 1. Celery App Configuration

**File:** `engine/llm_monitor_engine/celery.py`

```python
from celery import Celery
import os

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'llm_monitor_engine.settings')

app = Celery('llm_monitor_engine')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

**File:** `engine/llm_monitor_engine/__init__.py`

```python
from .celery import app as celery_app

__all__ = ('celery_app',)
```

This ensures the Celery app is initialized when Django starts.

### 2. Celery Settings

**File:** `engine/llm_monitor_engine/settings.py`

#### Broker and Backend Configuration

```python
# Celery settings (for background processing)
# Use a dedicated Redis DB index for engine tasks (e.g., DB 5)
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/5')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/5')
CELERY_ACCEPT_CONTENT = [config('CELERY_ACCEPT_CONTENT', default='json')]
CELERY_TASK_SERIALIZER = config('CELERY_TASK_SERIALIZER', default='json')
CELERY_RESULT_SERIALIZER = config('CELERY_RESULT_SERIALIZER', default='json')
CELERY_TIMEZONE = TIME_ZONE

# Auto-expire task results after 1 day
CELERY_RESULT_EXPIRES = timedelta(days=config('CELERY_RESULT_EXPIRES_DAYS', default=1, cast=int))
```

**Key Points:**
- **Broker**: Redis database 5 (separate from other services)
- **Result Backend**: Same Redis database for task results
- **Serialization**: JSON format
- **Result Expiry**: 1 day (configurable)

#### Celery Beat Schedule

```python
CELERY_BEAT_SCHEDULE = {
    # ... other schedules ...
    
    'report-email-scheduler-every-15s': {
        'task': 'core.processing_tasks.process_report_email_scheduler',
        'schedule': config('CELERY_BEAT_SCHEDULE_REPORT_EMAIL', default=15.0, cast=float),
    },
}
```

**Configuration:**
- **Task Name**: `core.processing_tasks.process_report_email_scheduler`
- **Schedule**: Every 15 seconds (configurable via `CELERY_BEAT_SCHEDULE_REPORT_EMAIL`)
- **Purpose**: Checks for due scheduled reports and processes them

### 3. Celery Tasks

**File:** `engine/core/processing_tasks.py`

#### Periodic Scheduler Task

```python
@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_report_email_scheduler(self):
    """
    Periodic scheduler for report email delivery.
    Checks for due scheduled reports and sends them via email.
    Runs every 15 seconds (configurable via CELERY_BEAT_SCHEDULE_REPORT_EMAIL).
    """
    try:
        from .report_email_processor import ReportEmailProcessor
        
        processor = ReportEmailProcessor()
        result = processor.process_due_reports()
        
        logger.info(
            f"Report email scheduler tick completed: "
            f"processed={result['processed']}, "
            f"successful={result['successful']}, "
            f"failed={result['failed']}"
        )
        
        return result
    except Exception as e:
        logger.error(f"Error in report email scheduler: {str(e)}", exc_info=True)
        raise self.retry(exc=e, countdown=60)  # Retry after 60 seconds on error
```

**Task Configuration:**
- **`@shared_task`**: Makes task available across Django apps
- **`bind=True`**: Allows access to task instance (for retries)
- **`ignore_result=True`**: Don't store task results (saves Redis memory)
- **`max_retries=3`**: Maximum retry attempts on failure
- **Retry Logic**: Retries after 60 seconds on error

#### Manual Trigger Task

```python
@shared_task(bind=True, ignore_result=True, max_retries=3)
def process_single_report_email_task(self, scheduled_report_id: int):
    """
    Process a single scheduled report immediately (manual trigger).
    
    Args:
        scheduled_report_id: ID of scheduled report to process
    """
    from shared_models.models import ScheduledReport
    from .report_email_processor import ReportEmailProcessor
    
    try:
        scheduled_report = ScheduledReport.objects.get(id=scheduled_report_id)
        
        processor = ReportEmailProcessor()
        result = processor._process_single_scheduled_report(scheduled_report)
        
        logger.info(f"Processed scheduled report {scheduled_report_id}: {result['message']}")
        return result
    except ScheduledReport.DoesNotExist:
        logger.error(f"Scheduled report {scheduled_report_id} not found")
        return {'success': False, 'message': 'Scheduled report not found'}
    except Exception as e:
        logger.error(f"Error processing scheduled report {scheduled_report_id}: {e}", exc_info=True)
        raise self.retry(exc=e, countdown=60)
```

**Usage:**
- Can be triggered manually via API or Django shell
- Processes a single scheduled report immediately
- Useful for testing or on-demand processing

## Environment Variables

Add to `.env` file:

```bash
# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/5
CELERY_RESULT_BACKEND=redis://localhost:6379/5
CELERY_ACCEPT_CONTENT=json
CELERY_TASK_SERIALIZER=json
CELERY_RESULT_SERIALIZER=json
CELERY_RESULT_EXPIRES_DAYS=1

# Report Email Scheduler Frequency (in seconds)
CELERY_BEAT_SCHEDULE_REPORT_EMAIL=15.0
```

## Starting Celery Services

### 1. Start Celery Beat (Scheduler)

```bash
cd engine
celery -A llm_monitor_engine beat -l info
```

**What it does:**
- Runs periodic tasks according to `CELERY_BEAT_SCHEDULE`
- Triggers `process_report_email_scheduler` every 15 seconds
- Logs schedule execution

**Output:**
```
[INFO] Scheduler: Sending due task core.processing_tasks.process_report_email_scheduler
```

### 2. Start Celery Worker

```bash
cd engine
celery -A llm_monitor_engine worker -l info
```

**What it does:**
- Executes tasks sent by Celery Beat
- Processes report generation and email delivery
- Handles retries on failures

**Output:**
```
[INFO] Task core.processing_tasks.process_report_email_scheduler[xxx] received
[INFO] Report email scheduler tick completed: processed=2, successful=2, failed=0
```

### 3. Combined Command (Development)

```bash
cd engine
celery -A llm_monitor_engine worker --beat -l info
```

Runs both Beat and Worker in a single process (not recommended for production).

## Task Flow

### Automatic Processing Flow

```
1. Celery Beat triggers process_report_email_scheduler (every 15s)
   ↓
2. Task queued in Redis broker
   ↓
3. Celery Worker picks up task
   ↓
4. ReportEmailProcessor.process_due_reports() called
   ↓
5. For each due ScheduledReport:
   a. Create GeneratedReport record
   b. Call backend API to generate report file
   c. Send email with attachment
   d. Update next_run_at
   ↓
6. Task completes, result logged
```

### Manual Trigger Flow

```python
# Via Django shell or API
from engine.core.processing_tasks import process_single_report_email_task

# Trigger immediately
process_single_report_email_task.delay(scheduled_report_id=1)
```

## Monitoring

### Check Registered Tasks

```bash
celery -A llm_monitor_engine inspect registered
```

Should show:
```
core.processing_tasks.process_report_email_scheduler
core.processing_tasks.process_single_report_email_task
```

### Check Active Tasks

```bash
celery -A llm_monitor_engine inspect active
```

### Check Scheduled Tasks

```bash
celery -A llm_monitor_engine inspect scheduled
```

### View Task Results

```python
from celery.result import AsyncResult
from engine.llm_monitor_engine.celery import app

# Get task result
result = AsyncResult('task-id', app=app)
print(result.state)  # PENDING, SUCCESS, FAILURE, etc.
print(result.result)  # Task return value
```

## Configuration Options

### Adjust Schedule Frequency

**For Production (less frequent checks):**
```bash
# Check every 5 minutes
CELERY_BEAT_SCHEDULE_REPORT_EMAIL=300.0
```

**For Testing (more frequent checks):**
```bash
# Check every 5 seconds
CELERY_BEAT_SCHEDULE_REPORT_EMAIL=5.0
```

### Redis Database Selection

The engine uses Redis database 5 to avoid conflicts:
- Backend might use database 0
- Other services use different databases
- Change via `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`

### Task Retry Configuration

Modify in `processing_tasks.py`:
```python
@shared_task(bind=True, ignore_result=True, max_retries=5)  # Increase retries
def process_report_email_scheduler(self):
    # ...
    raise self.retry(exc=e, countdown=120)  # Increase retry delay
```

## Troubleshooting

### Tasks Not Running

1. **Check Celery Beat is running:**
   ```bash
   ps aux | grep celery
   ```

2. **Check Redis connection:**
   ```bash
   redis-cli -n 5 ping
   ```

3. **Check task registration:**
   ```bash
   celery -A llm_monitor_engine inspect registered | grep report
   ```

### Tasks Failing

1. **Check worker logs:**
   ```bash
   tail -f logs/engine.log | grep -i "report\|error"
   ```

2. **Check task state:**
   ```python
   from celery.result import AsyncResult
   result = AsyncResult('task-id')
   print(result.state, result.traceback)
   ```

### Schedule Not Working

1. **Verify Beat schedule:**
   ```python
   from django.conf import settings
   print(settings.CELERY_BEAT_SCHEDULE)
   ```

2. **Check Beat logs:**
   ```bash
   celery -A llm_monitor_engine beat -l debug
   ```

## Production Recommendations

1. **Use separate processes:**
   - Run Celery Beat as a systemd service
   - Run Celery Workers as separate processes/containers
   - Don't use `--beat` flag in production

2. **Monitor task execution:**
   - Set up monitoring (Flower, Prometheus)
   - Alert on task failures
   - Track processing metrics

3. **Optimize schedule:**
   - Increase interval for production (5-15 minutes)
   - Use cron-like schedules for specific times
   - Consider timezone-aware scheduling

4. **Resource management:**
   - Limit concurrent tasks per worker
   - Set task timeouts
   - Monitor Redis memory usage

## Example Systemd Service

**File:** `/etc/systemd/system/celery-beat-engine.service`

```ini
[Unit]
Description=Celery Beat for LLM Monitor Engine
After=network.target redis.service

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/llm-monitor/engine
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/celery -A llm_monitor_engine beat -l info
Restart=always

[Install]
WantedBy=multi-user.target
```

**File:** `/etc/systemd/system/celery-worker-engine.service`

```ini
[Unit]
Description=Celery Worker for LLM Monitor Engine
After=network.target redis.service

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/llm-monitor/engine
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/celery -A llm_monitor_engine worker -l info --concurrency=4
Restart=always

[Install]
WantedBy=multi-user.target
```

## Summary

The report email processor is configured as:

- **Scheduler**: Celery Beat runs `process_report_email_scheduler` every 15 seconds
- **Worker**: Celery Worker executes tasks asynchronously
- **Broker**: Redis database 5 for task queue
- **Tasks**: Two tasks - periodic scheduler and manual trigger
- **Retry**: Automatic retry on failures (3 attempts, 60s delay)
- **Logging**: Comprehensive logging for monitoring

This configuration ensures reliable, scalable report email delivery processing.

