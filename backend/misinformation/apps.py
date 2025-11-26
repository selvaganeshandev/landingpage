from django.apps import AppConfig


class MisinformationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'misinformation'
    verbose_name = 'Misinformation Detection'

    def ready(self):
        # Import signals when app is ready
        import misinformation.signals  # noqa: F401
