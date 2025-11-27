import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'llm_monitor_engine.settings')

app = Celery('llm_monitor_engine')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
# This will discover tasks in tasks.py files by default
# We also explicitly import processing_tasks in core.apps.CoreConfig.ready()
app.autodiscover_tasks()

# Note: Explicit import of core.processing_tasks is done in core.apps.CoreConfig.ready()
# to ensure Django apps are loaded before importing models


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
