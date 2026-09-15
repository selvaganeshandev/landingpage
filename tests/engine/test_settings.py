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


# The engine's shared_models mirrors of backend-owned tables are `managed =
# False` (the backend's migrations create them on the shared DB). The test
# database is built from models, not migrations, so unmanaged models would get
# no table at all. Flip them to managed for the duration of the test run so the
# processors that write those tables (e.g. the Audit Engine) can be exercised.
from django.test.runner import DiscoverRunner  # noqa: E402


class UnmanagedModelTestRunner(DiscoverRunner):
    # Flipped in setup_databases, not setup_test_environment: mirror models
    # that live outside models.py (audit_models, seo_models) are only
    # registered once a test module imports them, which happens during
    # build_suite — after setup_test_environment but before setup_databases.
    def setup_databases(self, **kwargs):
        from django.apps import apps
        self._unmanaged = [m for m in apps.get_models() if not m._meta.managed]
        for model in self._unmanaged:
            model._meta.managed = True
        return super().setup_databases(**kwargs)

    def teardown_databases(self, old_config, **kwargs):
        super().teardown_databases(old_config, **kwargs)
        for model in getattr(self, '_unmanaged', []):
            model._meta.managed = False


TEST_RUNNER = 'tests.engine.test_settings.UnmanagedModelTestRunner'
