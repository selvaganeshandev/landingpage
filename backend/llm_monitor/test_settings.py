"""
Test settings — uses a local SQLite database so tests can run without
access to the remote PostgreSQL server.
"""
from .settings import *  # noqa: F401, F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

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
