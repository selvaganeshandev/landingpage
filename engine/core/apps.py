from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    
    def ready(self):
        # Import tasks to ensure they're registered with Celery
        try:
            import core.processing_tasks  # noqa
        except ImportError:
            pass
        # Boot Laminar telemetry for the engine's Django process (runserver /
        # any non-worker entrypoint). Celery workers init separately via the
        # worker_process_init signal in llm_monitor_engine/celery.py.
        from core.telemetry import init_laminar
        init_laminar()
