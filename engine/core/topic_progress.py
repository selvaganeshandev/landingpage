"""Progress for a topic-grouping run, readable while the run is in flight.

Grouping is a Celery task that merges every batch in memory and writes topics
only at the very end, so nothing in the database moves for the whole run: a
domain with 812 keywords sat at 812 pending / 0 topics for thirteen minutes.
The page had no way to tell "running" from "never started", so a refresh threw
away the only record that a run existed — the React state — and offered to
start another one.

Progress lives in Redis rather than on Domain because it is transient, written
several times a minute, and worthless once the run is over. It expires on its
own; no migration, no rows to clean up.

Everything here degrades to a no-op if Redis is unreachable. Losing the
progress display is not a reason to fail a grouping run that is otherwise fine.
"""
import json
import logging
import time

from django.conf import settings

logger = logging.getLogger(__name__)

# Long enough to outlive a slow run and let the UI read the terminal state
# afterwards; short enough that stale runs disappear on their own.
TTL_SECONDS = 2 * 60 * 60

_client = None


def _redis():
    """The broker's Redis, reused. None when unavailable."""
    global _client
    if _client is not None:
        return _client
    try:
        import redis

        url = getattr(settings, 'CELERY_BROKER_URL', None) or getattr(
            settings, 'REDIS_URL', 'redis://localhost:6379/0')
        _client = redis.Redis.from_url(url, socket_timeout=2, socket_connect_timeout=2)
        _client.ping()
        return _client
    except Exception as exc:
        logger.warning('[TopicProgress] Redis unavailable, progress disabled: %s', exc)
        _client = None
        return None


def _key(domain_id) -> str:
    return f'topicgen:progress:{int(domain_id)}'


def write(domain_id, **fields) -> None:
    """Merge `fields` into this domain's progress record."""
    client = _redis()
    if client is None:
        return
    try:
        current = read(domain_id) or {}
        current.update(fields)
        current['updated_at'] = time.time()
        client.setex(_key(domain_id), TTL_SECONDS, json.dumps(current))
    except Exception as exc:
        logger.warning('[TopicProgress] write failed for domain %s: %s', domain_id, exc)


def read(domain_id):
    """The domain's progress record, or None."""
    client = _redis()
    if client is None:
        return None
    try:
        raw = client.get(_key(domain_id))
        return json.loads(raw) if raw else None
    except Exception as exc:
        logger.warning('[TopicProgress] read failed for domain %s: %s', domain_id, exc)
        return None


def start(domain_id, keyword_count, task_id=None) -> None:
    """Record that a run has been queued. total_batches is not known yet."""
    write(
        domain_id,
        state='running',
        stage='queued',
        keywords=int(keyword_count or 0),
        batches_done=0,
        batches_total=0,
        topics_created=0,
        task_id=task_id,
        started_at=time.time(),
        error=None,
    )


def finish(domain_id, topics_created=0) -> None:
    write(domain_id, state='done', stage='finished', topics_created=int(topics_created or 0))


def fail(domain_id, message) -> None:
    write(domain_id, state='failed', stage='failed', error=str(message)[:300])
