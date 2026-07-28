# Celery Configuration for LLM Monitor Engine

## Verification

All Celery configuration checks pass. The engine is ready to run Celery workers and Beat.

### Configuration Summary

- **Broker**: `redis://localhost:6379/5`
- **Result Backend**: `redis://localhost:6379/5`
- **Timezone**: UTC
- **Beat Schedule**: 4 scheduled tasks

### Registered Tasks

All required integration tasks are registered:
- ✓ `core.processing_tasks.process_integration_insights_scheduler`
- ✓ `core.processing_tasks.process_ga_insight_task`
- ✓ `core.processing_tasks.process_gsc_insight_task`

### Celery Beat Schedule

1. **domain-scheduler-tick-every-15s** (every 15 seconds)
   - Task: `core.processing_tasks.scheduler_tick`

2. **prompt-analytics-scheduler-every-15s** (every 15 seconds)
   - Task: `core.processing_tasks.process_prompt_analytics_scheduler`

3. **topic-analytics-scheduler-every-15s** (every 15 seconds)
   - Task: `core.processing_tasks.process_topic_analytics_scheduler`

4. **integration-insights-scheduler-every-hour** (every 15 seconds for testing)
   - Task: `core.processing_tasks.process_integration_insights_scheduler`
   - **Note**: Currently set to 15 seconds for testing. Change to 3600.0 for production.

## Starting Celery

### Option 1: Using the start script (Recommended)

```bash
cd /home/hts-005/Documents/python/v3.12/llm-monitor
./start-celery.sh
```

Choose option 3 to start both Worker and Beat in the background.

### Option 2: Manual start

**Terminal 1 - Celery Worker:**
```bash
cd /home/hts-005/Documents/python/v3.12/llm-monitor/engine
/home/hts-005/Documents/python/v3.12/env/bin/python -m celery -A llm_monitor_engine worker --loglevel=info
```

**Terminal 2 - Celery Beat:**
```bash
cd /home/hts-005/Documents/python/v3.12/llm-monitor/engine
/home/hts-005/Documents/python/v3.12/env/bin/python -m celery -A llm_monitor_engine beat --loglevel=info
```

### Option 3: Background processes

```bash
cd /home/hts-005/Documents/python/v3.12/llm-monitor/engine

# Start Worker
nohup /home/hts-005/Documents/python/v3.12/env/bin/python -m celery -A llm_monitor_engine worker --loglevel=info > /tmp/celery-worker.log 2>&1 &

# Start Beat
nohup /home/hts-005/Documents/python/v3.12/env/bin/python -m celery -A llm_monitor_engine beat --loglevel=info > /tmp/celery-beat.log 2>&1 &
```

## Verification Commands

### Check if Celery is running

```bash
ps aux | grep -E "celery.*worker|celery.*beat" | grep -v grep
```

### Check registered tasks (requires running worker)

```bash
cd /home/hts-005/Documents/python/v3.12/llm-monitor/engine
/home/hts-005/Documents/python/v3.12/env/bin/python -m celery -A llm_monitor_engine inspect registered
```

### Run verification script

```bash
cd /home/hts-005/Documents/python/v3.12/llm-monitor/engine
/home/hts-005/Documents/python/v3.12/env/bin/python verify_celery.py
```

## Troubleshooting

### Issue: "No nodes replied within time constraint"

**Cause**: Celery worker is not running.

**Solution**: Start the Celery worker first, then try the command again.

### Issue: Tasks not being processed

**Check**:
1. Is Redis running? `redis-cli -n 5 ping` should return `PONG`
2. Is the worker running? `ps aux | grep celery`
3. Are there INIT records? Check the database for `GATrafficInsight` and `GSCTrafficInsight` with `track_status='INIT'`
4. Check worker logs: `/tmp/celery-worker.log` or terminal output
5. Check Beat logs: `/tmp/celery-beat.log` or terminal output

### Issue: Scheduler not running

**Check**:
1. Is Celery Beat running? `ps aux | grep "celery.*beat"`
2. Check Beat logs for errors
3. Verify the schedule in `engine/llm_monitor_engine/settings.py`

## Configuration Files

- **Celery App**: `engine/llm_monitor_engine/celery.py`
- **Settings**: `engine/llm_monitor_engine/settings.py` (lines 168-201)
- **Tasks**: `engine/core/processing_tasks.py`
- **App Config**: `engine/core/apps.py` (ensures tasks are registered)

## Notes

- The integration insights scheduler runs every 15 seconds for testing
- Each scheduler run processes one GA insight and one GSC insight (if available)
- The scheduler uses database locking (`select_for_update`) to prevent race conditions
- Only active integrations with valid `provider_id` are processed

