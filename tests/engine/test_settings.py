"""
Engine test settings use SQLite and avoid production runtime dependencies.
"""
from llm_monitor_engine.settings import *  # noqa: F401, F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
}


class _DisableMigrations:
    """Return None for every app to disable migrations."""

    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = _DisableMigrations()

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
