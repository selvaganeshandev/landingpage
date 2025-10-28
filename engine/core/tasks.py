# Backward-compatibility shim for existing imports and persisted Celery beat entries
from .processing_tasks import (
    process_domain_task,
    scheduler_tick,
    process_prompt_analytics_task,
    process_prompt_analytics_scheduler,
)


