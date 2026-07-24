"""Laminar (lmnr) observability bootstrap for the engine.

Single entrypoint ``init_laminar()`` — safe to call from every process-start
hook (Django ``AppConfig.ready``, Celery ``worker_process_init``). It is
deliberately defensive so telemetry can never take the pipeline down:

  * runs only when ``ENABLE_LAMINAR`` is truthy AND a project API key is set,
  * initializes at most once per process (module-level singleton),
  * skips management commands that do no LLM work (``migrate`` etc.),
  * swallows any init/flush error and logs it — a broken exporter must not
    break request/task handling.

Enable at runtime via ``engine/.env``: ``ENABLE_LAMINAR=true`` (+ a valid
``LMNR_PROJECT_API_KEY``). Deploys ship with it ``false`` for a zero-risk
rollout; flip the flag and restart to turn tracing on, flip back to roll back.
"""
import logging
import os
import sys

logger = logging.getLogger(__name__)

_initialized = False

# Django management commands that must NOT spin up telemetry: they run no LLM
# work and often run in throwaway/CI processes. `manage.py <cmd>` puts the
# subcommand at sys.argv[1]; gunicorn/celery argv never match these.
SKIP_COMMANDS = {
    "migrate", "makemigrations", "collectstatic", "test", "flush",
    "showmigrations", "shell", "shell_plus", "createsuperuser", "dbshell",
    "check", "makemessages", "compilemessages",
}


def _truthy(value):
    return str(value or "").strip().lower() in ("1", "true", "yes", "on")


def _should_skip():
    return len(sys.argv) > 1 and sys.argv[1] in SKIP_COMMANDS


def init_laminar():
    """Initialize Laminar once for the current process (no-op if disabled)."""
    global _initialized
    if _initialized or _should_skip():
        return
    if not _truthy(os.getenv("ENABLE_LAMINAR")):
        logger.debug("Laminar telemetry disabled (ENABLE_LAMINAR not truthy)")
        return
    if not os.getenv("LMNR_PROJECT_API_KEY"):
        logger.warning("ENABLE_LAMINAR is on but LMNR_PROJECT_API_KEY is missing — skipping init")
        return
    try:
        from lmnr import Laminar

        # project_api_key is read from LMNR_PROJECT_API_KEY automatically.
        # base_url can point at a self-hosted instance via LMNR_BASE_URL.
        init_kwargs = {"metadata": {"environment": os.getenv("ENVIRONMENT", "dev")}}
        base_url = os.getenv("LMNR_BASE_URL")
        if base_url:
            init_kwargs["base_url"] = base_url
        Laminar.initialize(**init_kwargs)
        _initialized = True
        logger.info("Laminar telemetry initialized [env=%s]", os.getenv("ENVIRONMENT", "dev"))
    except Exception as exc:  # noqa: BLE001 — telemetry must never break startup
        logger.error("Failed to initialize Laminar: %s", exc)


def flush_laminar():
    """Force-flush pending spans. Call on worker/process shutdown so Celery
    prefork children don't drop their last batch of traces."""
    if not _initialized:
        return
    try:
        from lmnr import Laminar

        Laminar.flush()
    except Exception as exc:  # noqa: BLE001
        logger.error("Laminar flush failed: %s", exc)
