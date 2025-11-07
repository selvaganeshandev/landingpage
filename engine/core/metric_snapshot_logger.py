"""
Dedicated logger for metric snapshot creation debugging
Logs to a separate file for easier tracking
"""
import logging
import os
from datetime import datetime
from pathlib import Path

# Create logs directory if it doesn't exist
LOG_DIR = Path(__file__).parent.parent.parent.parent / 'logs'
LOG_DIR.mkdir(exist_ok=True)

# Create a dedicated log file for metric snapshots
LOG_FILE = LOG_DIR / 'metric_snapshots.log'

# Configure logger
logger = logging.getLogger('metric_snapshots')
logger.setLevel(logging.DEBUG)

# Remove existing handlers to avoid duplicates
logger.handlers = []

# Create file handler
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setLevel(logging.DEBUG)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

def log_snapshot_creation_start(analytics_count, snapshot_date, period_type):
    """Log the start of snapshot creation"""
    logger.info("=" * 80)
    logger.info(f"STARTING PROMPT METRIC SNAPSHOT CREATION")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"Analytics count: {analytics_count}")
    logger.info(f"Snapshot date: {snapshot_date}")
    logger.info(f"Period type: {period_type}")
    logger.info("=" * 80)

def log_table_check(exists, count=None, error=None):
    """Log table existence check"""
    if error:
        logger.error(f"TABLE CHECK FAILED: {str(error)}")
        logger.exception(error)
    elif exists:
        logger.info(f"TABLE CHECK: PromptMetricSnapshot table exists, current count: {count}")
    else:
        logger.warning("TABLE CHECK: PromptMetricSnapshot table does not exist or cannot be accessed")

def log_analytics_filtering(total_count, with_platform_count, sample_platforms=None):
    """Log analytics filtering results"""
    logger.info(f"ANALYTICS FILTERING:")
    logger.info(f"  Total analytics: {total_count}")
    logger.info(f"  With platform: {with_platform_count}")
    if sample_platforms:
        logger.info(f"  Sample platforms: {sample_platforms}")

def log_prompts_processing(prompts_count, prompts_list=None):
    """Log prompts being processed"""
    logger.info(f"PROCESSING PROMPTS:")
    logger.info(f"  Total prompts: {prompts_count}")
    if prompts_list:
        logger.info(f"  Prompt IDs: {prompts_list[:20]}")  # Log first 20

def log_platform_processing(prompt_id, platform, platform_analytics_count):
    """Log platform processing for a prompt"""
    logger.debug(f"  Processing prompt {prompt_id}, platform {platform}, analytics: {platform_analytics_count}")

def log_snapshot_creation(prompt_id, platform, snapshot_date, created, metrics):
    """Log successful snapshot creation"""
    action = "CREATED" if created else "UPDATED"
    logger.info(f"  ✓ {action} snapshot for prompt {prompt_id}, platform {platform}, date {snapshot_date}")
    logger.info(f"    Metrics: mentions={metrics.get('mentions', 0)}, "
                f"citations={metrics.get('citations', 0)}, "
                f"visibility={metrics.get('visibility_score', 0)}, "
                f"position={metrics.get('average_position', 0)}")

def log_snapshot_error(prompt_id, platform, error):
    """Log snapshot creation error"""
    logger.error(f"  ✗ ERROR creating snapshot for prompt {prompt_id}, platform {platform}: {str(error)}")
    logger.exception(error)

def log_snapshot_creation_complete(created_count, updated_count, total_prompts):
    """Log completion of snapshot creation"""
    logger.info("=" * 80)
    logger.info(f"COMPLETED PROMPT METRIC SNAPSHOT CREATION")
    logger.info(f"  Created: {created_count}")
    logger.info(f"  Updated: {updated_count}")
    logger.info(f"  Total prompts processed: {total_prompts}")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info("=" * 80)

def log_method_call(method_name, **kwargs):
    """Log method call with parameters"""
    logger.info(f"METHOD CALL: {method_name}")
    for key, value in kwargs.items():
        logger.info(f"  {key}: {value}")

def log_database_query(query_description, result_count=None, error=None):
    """Log database query execution"""
    if error:
        logger.error(f"QUERY FAILED: {query_description}")
        logger.error(f"  Error: {str(error)}")
    else:
        logger.debug(f"QUERY: {query_description}")
        if result_count is not None:
            logger.debug(f"  Result count: {result_count}")

