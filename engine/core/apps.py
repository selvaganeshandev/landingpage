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
