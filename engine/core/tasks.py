# Backward-compatibility shim for existing imports and persisted Celery beat entries
from .processing_tasks import (
    process_domain_task,
    scheduler_tick,
    process_prompt_analytics_task,
    process_prompt_analytics_scheduler,
    process_competitor_scheduler,
    process_single_competitor_task,
    process_seo_keyword_task,
    process_seo_domain_task,
)


