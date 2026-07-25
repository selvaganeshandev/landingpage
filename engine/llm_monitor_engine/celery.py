import os
from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'llm_monitor_engine.settings')

app = Celery('llm_monitor_engine')


# --- Laminar telemetry: prefork-safe lifecycle ---
# Each Celery prefork child is a separate process, so it must initialize its
# OWN Laminar/OTel exporter (worker_process_init), and flush on the way out so
# a recycled/killed child doesn't drop its last batch of spans. No-op unless
# ENABLE_LAMINAR is set — see core/telemetry.py.
@worker_process_init.connect
def _laminar_worker_init(**_kwargs):
    from core.telemetry import init_laminar
    init_laminar()


@worker_process_shutdown.connect
def _laminar_worker_shutdown(**_kwargs):
    from core.telemetry import flush_laminar
    flush_laminar()

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
