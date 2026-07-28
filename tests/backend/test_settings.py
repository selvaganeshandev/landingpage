"""
Test settings — uses a local SQLite database so tests can run without
access to the remote PostgreSQL server.
"""
from llm_monitor.settings import *  # noqa: F401, F403

# Do not require the runtime file-log directory during tests.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Load only the routes exercised by the backend test package. Production URL
# checks remain a separate `manage.py check` concern and may require optional
# report/export dependencies.
ROOT_URLCONF = "tests.backend.urls"

# Skip migrations entirely and create tables directly from models.
# This avoids SQLite incompatibilities with some PostgreSQL-specific migration steps.
class _DisableMigrations:
    """Return None for every app to disable migrations."""
    def __contains__(self, item):
        return True
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = _DisableMigrations()

# Speed up password hashing in tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
