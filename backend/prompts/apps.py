from django.apps import AppConfig


class PromptsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'prompts'

    def ready(self):
        """Import signal handlers when the app is ready"""
        import prompts.signals  # noqa
