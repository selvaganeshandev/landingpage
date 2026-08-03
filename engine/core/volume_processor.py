"""
Populates SeoKeywordVolume from DataForSEO.

Two entry points, both landing in :func:`sync_keyword_volume`:

* the ``fetch_keyword_volume`` management command — one-off backfills and
  manual runs;
* the ``sync_keyword_volume_task`` Celery task on beat — picks up keywords
  added since the last run, so a newly added brand gets volume without anyone
  asking for it.

The unit of work is a batch, never a single keyword, because DataForSEO bills
per request rather than per keyword (see dataforseo_volume). Fetching one
keyword on its own costs the same $0.09 as fetching a thousand, so the sweeper
deliberately waits for keywords to accumulate rather than firing per insert.
"""
import logging
from typing import Optional

from django.db import transaction
from django.utils import timezone

from core.dataforseo_volume import (
    COST_PER_REQUEST,
    MAX_KEYWORDS_PER_REQUEST,
    DataForSeoError,
    fetch_search_volume,
    location_code_for,
)
from shared_models.seo_models import SeoKeywordRank, SeoKeywordVolume

logger = logging.getLogger(__name__)


def _chunks(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def sync_keyword_volume(
    domain_id: Optional[int] = None,
    only_missing: bool = True,
    dry_run: bool = False,
    limit: Optional[int] = None,
) -> dict:
    """Fetch and store search volume for tracked keywords.

    Args:
        domain_id: restrict to one domain; None means every domain.
        only_missing: skip keywords that already have a volume row. This is
            what makes the beat task cheap — a sweep with nothing new to do
            makes zero requests and costs nothing.
        dry_run: report the batches and estimated cost without calling the API.
        limit: cap how many keywords are considered, for cautious first runs.

    Returns a summary dict.
    """
    qs = SeoKeywordRank.objects.select_related('keyword')
    if domain_id:
        qs = qs.filter(domain_id=domain_id)
    if only_missing:
        # A keyword is "done" once it has a volume row — including a row
        # recorded as no-data, so dead terms aren't re-requested every sweep.
        done_ids = SeoKeywordVolume.objects.values_list('seo_keyword_rank_id', flat=True)
        qs = qs.exclude(id__in=done_ids)

    rows = list(qs)
    if limit:
        rows = rows[:limit]

    # Group by (location, language): one request can only carry a single pair.
    groups: dict = {}
    for row in rows:
        text = (row.keyword.keyword or '').strip() if row.keyword_id else ''
        if not text:
            continue
        key = (location_code_for(row.isocode), (row.language_code or 'en').strip() or 'en')
        groups.setdefault(key, []).append((text, row))

    batches = []
    for (loc, lang), entries in groups.items():
        # De-duplicate within a batch: the same keyword text can be tracked by
        # several domains, and sending it twice wastes a slot in the 1,000 cap.
        by_text: dict = {}
        for text, row in entries:
            by_text.setdefault(text.lower(), []).append((text, row))
        unique_texts = [v[0][0] for v in by_text.values()]
        for chunk in _chunks(unique_texts, MAX_KEYWORDS_PER_REQUEST):
            batches.append((loc, lang, chunk, by_text))

    summary = {
        'keywords_considered': len(rows),
        'requests': len(batches),
        'estimated_cost': round(len(batches) * COST_PER_REQUEST, 2),
        'updated': 0,
        'no_data': 0,
        'failed_batches': 0,
    }

    if dry_run or not batches:
        return summary

    for loc, lang, chunk, by_text in batches:
        try:
            results = fetch_search_volume(chunk, location_code=loc, language_code=lang)
        except DataForSeoError as exc:
            # One bad batch must not abandon the rest — the others are already
            # paid for or still worth fetching.
            logger.error("Volume batch failed (location=%s language=%s, %d keywords): %s",
                         loc, lang, len(chunk), exc)
            summary['failed_batches'] += 1
            continue

        for text_lower, parsed in results.items():
            for _text, row in by_text.get(text_lower, []):
                _write(row, parsed, summary)

    return summary


def _write(row: SeoKeywordRank, parsed: dict, summary: dict) -> None:
    """Persist one keyword's figures. Idempotent — safe to re-run."""
    no_data = parsed.get('no_data')
    with transaction.atomic():
        SeoKeywordVolume.objects.update_or_create(
            seo_keyword_rank_id=row.id,
            defaults={
                'average_volume': parsed['average_volume'],
                'top_volume': parsed['top_volume'],
                'low_volume': parsed['low_volume'],
                'comp_level': parsed['comp_level'],
                'comp_index': parsed['comp_index'],
                'month_wise_volume': parsed['month_wise_volume'],
                'month_labels': parsed['month_labels'],
                # 'none' records that Google has no figure, which is different
                # from 'new' (never asked). Both leave the UI showing nothing,
                # but only 'new' is worth spending another request on.
                'status': 'none' if no_data else 'done',
                'modified_at': timezone.now(),
            },
        )
        # Mirror the headline number onto the keyword row, which is what the
        # rankings table, exports and reports already read.
        SeoKeywordRank.objects.filter(id=row.id).update(
            search_volume=None if no_data else parsed['average_volume']
        )

    if no_data:
        summary['no_data'] += 1
    else:
        summary['updated'] += 1
