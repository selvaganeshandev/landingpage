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


def _env(key, default=None):
    """Read a setting the way the rest of the app does — python-decouple's
    ``config()`` reads ``.env``. Those values are NOT exported to ``os.environ``
    under decouple, so ``os.getenv`` alone silently misses them (that was the
    original 'never initialized' bug). Falls back to ``os.environ`` if decouple
    isn't importable in some context."""
    try:
        from decouple import config
        return config(key, default=default)
    except Exception:
        return os.getenv(key, default)


def _should_skip():
    return len(sys.argv) > 1 and sys.argv[1] in SKIP_COMMANDS


def init_laminar():
    """Initialize Laminar once for the current process (no-op if disabled)."""
    global _initialized
    if _initialized or _should_skip():
        return
    if not _truthy(_env("ENABLE_LAMINAR", "false")):
        logger.debug("Laminar telemetry disabled (ENABLE_LAMINAR not truthy)")
        return
    api_key = _env("LMNR_PROJECT_API_KEY", "")
    if not api_key:
        logger.warning("ENABLE_LAMINAR is on but LMNR_PROJECT_API_KEY is missing — skipping init")
        return
    try:
        from lmnr import Laminar

        # Default instrument set (all providers). This requires opentelemetry
        # pinned to the 1.43 line — lmnr's bundled OpenAI instrumentor imports
        # opentelemetry._events, which 1.44 removed; the pins live in
        # engine/requirements.txt. Pass the key explicitly (decouple keeps it out
        # of os.environ). base_url -> self-hosted instance.
        init_kwargs = {
            "project_api_key": api_key,
            "metadata": {"environment": _env("ENVIRONMENT", "dev")},
        }
        base_url = _env("LMNR_BASE_URL", "")
        if base_url:
            init_kwargs["base_url"] = base_url
        Laminar.initialize(**init_kwargs)
        _initialized = True
        logger.info("Laminar telemetry initialized [env=%s]", _env("ENVIRONMENT", "dev"))
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


def _enabled():
    """Whether telemetry should be active for this process (checked at import
    time by the observe() decorator, so `lmnr` is only imported when on)."""
    return (
        _truthy(_env("ENABLE_LAMINAR", "false"))
        and bool(_env("LMNR_PROJECT_API_KEY", ""))
        and not _should_skip()
    )


def observe(**observe_kwargs):
    """Wrap a workflow entrypoint with Laminar's @observe when telemetry is
    enabled; a transparent pass-through otherwise.

    Because the decorator is applied at import time, the disabled path returns
    the original function WITHOUT importing lmnr — so processor modules stay
    importable and side-effect-free when ENABLE_LAMINAR is off.
    """
    def decorator(func):
        if not _enabled():
            return func
        try:
            from lmnr import observe as _lmnr_observe

            return _lmnr_observe(**observe_kwargs)(func)
        except Exception as exc:  # noqa: BLE001
            logger.error("Laminar observe wrap failed for %s: %s",
                         getattr(func, "__name__", func), exc)
            return func

    return decorator


def trace_metadata(**fields):
    """Attach tenant/provider metadata (organization_id, domain_id, provider,
    model, …) to the CURRENT trace. No-op unless Laminar is initialized. Drops
    None values so callers can pass optional fields freely."""
    if not _initialized:
        return
    try:
        from lmnr import Laminar

        clean = {k: v for k, v in fields.items() if v is not None}
        if clean:
            Laminar.set_trace_metadata(clean)
    except Exception as exc:  # noqa: BLE001
        logger.error("Laminar set_trace_metadata failed: %s", exc)
