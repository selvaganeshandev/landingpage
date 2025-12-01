from django.apps import AppConfig


class MisinformationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'misinformation'
    verbose_name = 'Misinformation Detection'

    def ready(self):
        # Signals removed - misinformation processing now handled by engine
        # import misinformation.signals  # noqa: F401
        pass
