from django.apps import AppConfig


class CompetitorsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'competitors'

    def ready(self):
        """Import signal handlers when the app is ready"""
        import competitors.signals  # noqa
