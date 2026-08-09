"""
DataForSEO Backlinks fetch worker.

Runs on the `seo` queue (engine-celery-seo). The backend never calls DataForSEO
itself — a full pull is 10+ sequential HTTP requests and would hold a gunicorn
worker for a minute or more. The backend creates a PEND snapshot, POSTs to the
engine, and polls the snapshot row for status.

Endpoints used (all `live`, no task_post/task_get polling):

    /v3/backlinks/summary/live            profile totals + six breakdowns
    /v3/backlinks/history/live            monthly trend, backfilled for years
    /v3/backlinks/backlinks/live          the individual links
    /v3/backlinks/referring_domains/live  linking domains, aggregated
    /v3/backlinks/anchors/live            anchor texts, aggregated
    /v3/backlinks/domain_pages/live       our pages, by links received

Pricing shapes this whole module. Every endpoint bills **$0.024 per request
plus $0.000036 per row**, max 1,000 rows per request, so pulling N rows costs:

    ceil(N / 1000) * 0.024 + N * 0.000036

Measured on havells.com (2026-08-09), an uncapped pull of ONE domain:

    backlinks         149,899 rows   150 requests   $9.00
    domain_pages       35,710 rows    36 requests   $2.15
    referring_domains   3,584 rows     4 requests   $0.23
    anchors             2,415 rows     3 requests   $0.16
    summary + history                  2 requests   $0.05
                                                   ------
                                                    $11.58

Against a shared prepaid balance that is five domains. Hence ROW_CAPS: the
summary counts are always the true totals (one cheap call), while the detail
tables keep only the highest-ranked rows and the snapshot is flagged
`is_truncated` so the UI says so rather than implying it holds everything.
"""
import logging
import math
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Dict, List, Optional, Tuple

import requests
from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

logger = logging.getLogger(__name__)

API_ROOT = "https://api.dataforseo.com/v3/backlinks"
SANDBOX_ROOT = "https://sandbox.dataforseo.com/v3/backlinks"

# DataForSEO's hard caps: rows per request, and `offset` before pagination has
# to switch to search_after_token.
MAX_ROWS_PER_REQUEST = 1000
MAX_OFFSET = 20000

# Published rate card, for pre-flight estimates only — the real figure is read
# back from each response's `cost` field.
COST_PER_REQUEST = 0.024
COST_PER_ROW = 0.000036

# Detail rows stored per snapshot. 1,000 keeps a full 45-project month near $13
# rather than $520. `backlinks` is the expensive one to raise — it is the only
# list that routinely runs to six figures.
DEFAULT_ROW_CAPS = {
    "backlinks": 1000,
    "referring_domains": 1000,
    "anchors": 1000,
    "domain_pages": 1000,
}

REQUEST_TIMEOUT = 120


class DataForSeoBacklinksError(RuntimeError):
    """API unreachable, misconfigured, or returned a non-success status."""


def row_caps() -> Dict[str, int]:
    caps = dict(DEFAULT_ROW_CAPS)
    caps.update(getattr(settings, "BACKLINK_ROW_CAPS", {}) or {})
    return caps


def _credentials(organisation=None) -> Tuple[str, str]:
    """Credentials for this fetch: the organisation's own, else the system pair.

    An organisation that supplies its own DataForSEO account in Organization
    Settings is billed on that account. Both halves must be present — a login
    with no password is a misconfiguration, and pairing it with the system
    password would silently bill the wrong account.
    """
    if organisation is not None:
        login = (getattr(organisation, "dataforseo_login", "") or "").strip()
        encrypted = getattr(organisation, "dataforseo_password_enc", None)
        if login and encrypted:
            try:
                from shared_models.crypto import decrypt_value
                password = decrypt_value(encrypted)
            except Exception:
                logger.exception(
                    "[BL] Could not decrypt the DataForSEO password for org %s — "
                    "falling back to the system account.", getattr(organisation, "id", "?"),
                )
                password = ""
            if password:
                return login, password
        if login and not encrypted:
            logger.warning(
                "[BL] Org %s has a DataForSEO login with no password — using the "
                "system account.", getattr(organisation, "id", "?"),
            )

    login = getattr(settings, "DATAFORSEO_LOGIN", None)
    password = getattr(settings, "DATAFORSEO_PASSWORD", None)
    if not login or not password:
        raise DataForSeoBacklinksError(
            "DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD are not configured. "
            "Set them in engine/.env, or give this organisation its own "
            "credentials in Organization Settings."
        )
    return login, password


def _root() -> str:
    return SANDBOX_ROOT if getattr(settings, "DATAFORSEO_USE_SANDBOX", False) else API_ROOT


def estimate_cost(row_count: int) -> float:
    """USD to pull `row_count` rows from a paginated Backlinks endpoint."""
    if row_count <= 0:
        return 0.0
    return math.ceil(row_count / MAX_ROWS_PER_REQUEST) * COST_PER_REQUEST + row_count * COST_PER_ROW


@dataclass
class FetchPlan:
    """What a pull will retrieve and cost, decided before anything is spent.

    `available` is what the domain actually has; `planned` is what the caps
    allow. They differ exactly when the snapshot is truncated.
    """
    available: Dict[str, int] = field(default_factory=dict)
    planned: Dict[str, int] = field(default_factory=dict)

    @property
    def is_truncated(self) -> bool:
        return any(self.planned[k] < self.available.get(k, 0) for k in self.planned)

    @property
    def estimated_cost(self) -> float:
        return round(sum(estimate_cost(n) for n in self.planned.values()), 4)


class BacklinksClient:
    """DataForSEO wrapper that tallies what it spends.

    One client per snapshot, so `cost` is the snapshot's true billed total
    rather than an estimate.
    """

    def __init__(self, organisation=None):
        self.auth = _credentials(organisation)
        self.cost = 0.0
        self.requests_made = 0

    def _post(self, endpoint: str, payload: dict) -> dict:
        url = f"{_root()}/{endpoint}/live"
        try:
            resp = requests.post(url, auth=self.auth, json=[payload], timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            body = resp.json()
        except requests.RequestException as exc:
            raise DataForSeoBacklinksError(f"{endpoint}: request failed — {exc}") from exc
        except ValueError as exc:
            raise DataForSeoBacklinksError(f"{endpoint}: response was not JSON") from exc

        self.requests_made += 1
        # Billed even when the task errors, so tally before checking status.
        self.cost += float(body.get("cost") or 0)

        if body.get("status_code") != 20000:
            raise DataForSeoBacklinksError(
                f"{endpoint}: {body.get('status_code')} {body.get('status_message')}"
            )
        task = (body.get("tasks") or [{}])[0]
        if task.get("status_code") != 20000:
            raise DataForSeoBacklinksError(
                f"{endpoint}: {task.get('status_code')} {task.get('status_message')}"
            )
        result = task.get("result") or []
        return result[0] if result else {}

    def summary(self, target: str, include_subdomains: bool = True) -> dict:
        return self._post("summary", {
            "target": target,
            "internal_list_limit": 10,
            "backlinks_status_type": "live",
            "include_subdomains": include_subdomains,
        })

    def history(self, target: str) -> List[dict]:
        return self._post("history", {"target": target}).get("items") or []

    def paginate(
        self,
        endpoint: str,
        target: str,
        limit: int,
        order_by: Optional[List[str]] = None,
        extra: Optional[dict] = None,
    ) -> List[dict]:
        """Page through `endpoint` until `limit` rows are collected.

        Uses `offset` up to MAX_OFFSET and `search_after_token` beyond it —
        DataForSEO rejects deep offsets, and the token is the only way to reach
        the tail of a large profile.
        """
        collected: List[dict] = []
        offset = 0
        token: Optional[str] = None

        while len(collected) < limit:
            page_size = min(MAX_ROWS_PER_REQUEST, limit - len(collected))
            payload = {"target": target, "limit": page_size, "backlinks_status_type": "live"}
            if order_by:
                payload["order_by"] = order_by
            if extra:
                payload.update(extra)
            if token:
                payload["search_after_token"] = token
            elif offset:
                payload["offset"] = offset

            result = self._post(endpoint, payload)
            items = result.get("items") or []
            collected.extend(items)

            if len(items) < page_size:
                break  # exhausted
            offset += len(items)
            token = result.get("search_after_token")
            if offset >= MAX_OFFSET and not token:
                logger.warning(
                    "[BL] %s: offset ceiling reached for %s with no search_after_token; "
                    "stopping at %d rows", endpoint, target, len(collected),
                )
                break

        return collected[:limit]


def plan_fetch(summary: dict, caps: Optional[Dict[str, int]] = None) -> FetchPlan:
    """Decide how many rows of each list to pull, from the summary's own counts."""
    caps = caps or row_caps()
    available = {
        "backlinks": int(summary.get("backlinks") or 0),
        "referring_domains": int(summary.get("referring_main_domains") or 0),
        # The summary carries no anchor count, so the cap doubles as the
        # estimate; the true count only emerges once the first page returns.
        "anchors": caps["anchors"],
        "domain_pages": int(summary.get("crawled_pages") or 0),
    }
    return FetchPlan(available=available, planned={k: min(v, caps[k]) for k, v in available.items()})


def _dt(value):
    """DataForSEO stamps look like '2025-10-03 18:32:06 +00:00'; blank is null."""
    if not value:
        return None
    return parse_datetime(value.replace(" +00:00", "+00:00"))


def _target_for(domain) -> str:
    raw = (domain.url or domain.name or "")
    return raw.replace("https://", "").replace("http://", "").strip("/").strip()


def _apply_summary(snapshot, summary: dict) -> None:
    for f in (
        "rank", "backlinks", "backlinks_spam_score", "broken_backlinks",
        "broken_pages", "crawled_pages", "internal_links_count",
        "external_links_count", "referring_domains", "referring_domains_nofollow",
        "referring_main_domains", "referring_main_domains_nofollow",
        "referring_ips", "referring_subnets", "referring_pages",
        "referring_pages_nofollow",
    ):
        setattr(snapshot, f, summary.get(f) or 0)
    for f in (
        "referring_links_tld", "referring_links_types", "referring_links_attributes",
        "referring_links_platform_types", "referring_links_semantic_locations",
        "referring_links_countries",
    ):
        setattr(snapshot, f, summary.get(f) or {})
    snapshot.first_seen = _dt(summary.get("first_seen"))
    snapshot.lost_date = _dt(summary.get("lost_date"))
    snapshot.target_info = summary.get("info") or {}


def _store_items(snapshot, rows: List[dict]) -> None:
    from shared_models.backlink_models import SeoBacklinkItem

    SeoBacklinkItem.objects.bulk_create([
        SeoBacklinkItem(
            snapshot=snapshot,
            domain_from=(r.get("domain_from") or "")[:255],
            url_from=r.get("url_from") or "",
            url_to=r.get("url_to") or "",
            tld_from=(r.get("tld_from") or "")[:63],
            anchor=r.get("anchor") or "",
            item_type=(r.get("item_type") or "")[:20],
            dofollow=bool(r.get("dofollow")),
            is_new=bool(r.get("is_new")),
            is_lost=bool(r.get("is_lost")),
            is_broken=bool(r.get("is_broken")),
            is_indirect_link=bool(r.get("is_indirect_link")),
            rank=r.get("rank") or 0,
            page_from_rank=r.get("page_from_rank") or 0,
            domain_from_rank=r.get("domain_from_rank") or 0,
            backlink_spam_score=r.get("backlink_spam_score") or 0,
            page_from_title=r.get("page_from_title") or "",
            page_from_language=(r.get("page_from_language") or "")[:16],
            page_from_external_links=r.get("page_from_external_links") or 0,
            page_from_internal_links=r.get("page_from_internal_links") or 0,
            domain_from_country=(r.get("domain_from_country") or "")[:8],
            domain_from_ip=(r.get("domain_from_ip") or "")[:45],
            domain_from_platform_type=r.get("domain_from_platform_type") or [],
            semantic_location=(r.get("semantic_location") or "")[:64],
            attributes=r.get("attributes") or [],
            url_to_status_code=r.get("url_to_status_code"),
            url_to_spam_score=r.get("url_to_spam_score") or 0,
            first_seen=_dt(r.get("first_seen")),
            last_seen=_dt(r.get("last_seen")),
            ranked_keywords_info=r.get("ranked_keywords_info") or {},
        )
        for r in rows
    ], batch_size=500)


def _store_referring_domains(snapshot, rows: List[dict]) -> None:
    from shared_models.backlink_models import SeoBacklinkReferringDomain

    SeoBacklinkReferringDomain.objects.bulk_create([
        SeoBacklinkReferringDomain(
            snapshot=snapshot,
            domain_name=(r.get("domain") or "")[:255],
            rank=r.get("rank") or 0,
            backlinks=r.get("backlinks") or 0,
            backlinks_spam_score=r.get("backlinks_spam_score") or 0,
            broken_backlinks=r.get("broken_backlinks") or 0,
            referring_pages=r.get("referring_pages") or 0,
            referring_domains=r.get("referring_domains") or 0,
            first_seen=_dt(r.get("first_seen")),
            lost_date=_dt(r.get("lost_date")),
            country=(r.get("country") or "")[:8],
            is_new=bool(r.get("is_new")),
            is_lost=bool(r.get("is_lost")),
        )
        for r in rows
    ], batch_size=500)


def _store_anchors(snapshot, rows: List[dict]) -> None:
    from shared_models.backlink_models import SeoBacklinkAnchor

    SeoBacklinkAnchor.objects.bulk_create([
        SeoBacklinkAnchor(
            snapshot=snapshot,
            anchor=r.get("anchor") or "",
            rank=r.get("rank") or 0,
            backlinks=r.get("backlinks") or 0,
            backlinks_spam_score=r.get("backlinks_spam_score") or 0,
            referring_domains=r.get("referring_domains") or 0,
            referring_main_domains=r.get("referring_main_domains") or 0,
            referring_pages=r.get("referring_pages") or 0,
            first_seen=_dt(r.get("first_seen")),
            lost_date=_dt(r.get("lost_date")),
        )
        for r in rows
    ], batch_size=500)


def _store_pages(snapshot, rows: List[dict]) -> None:
    """Store the target's own pages by links received.

    Unlike every other list endpoint, domain_pages nests its link metrics in a
    `page_summary` sub-object and names the URL `page`, not `url` — which is
    also why its order_by needs the dotted `page_summary.backlinks` path.
    """
    from shared_models.backlink_models import SeoBacklinkPage

    SeoBacklinkPage.objects.bulk_create([
        SeoBacklinkPage(
            snapshot=snapshot,
            page_url=r.get("page") or (r.get("meta") or {}).get("canonical") or "",
            rank=(r.get("page_summary") or {}).get("rank") or 0,
            backlinks=(r.get("page_summary") or {}).get("backlinks") or 0,
            referring_domains=(r.get("page_summary") or {}).get("referring_domains") or 0,
            referring_main_domains=(r.get("page_summary") or {}).get("referring_main_domains") or 0,
            referring_pages=(r.get("page_summary") or {}).get("referring_pages") or 0,
            status_code=r.get("status_code"),
            first_seen=_dt((r.get("page_summary") or {}).get("first_seen")),
        )
        for r in rows
    ], batch_size=500)


def _store_history(snapshot, rows: List[dict]) -> None:
    from shared_models.backlink_models import SeoBacklinkHistoryPoint

    points, seen = [], set()
    for r in rows:
        day = (r.get("date") or "")[:10]
        if not day or day in seen:
            continue
        seen.add(day)
        points.append(SeoBacklinkHistoryPoint(
            snapshot=snapshot,
            point_date=day,
            rank=r.get("rank") or 0,
            backlinks=r.get("backlinks") or 0,
            new_backlinks=r.get("new_backlinks") or 0,
            lost_backlinks=r.get("lost_backlinks") or 0,
            new_referring_domains=r.get("new_referring_domains") or 0,
            lost_referring_domains=r.get("lost_referring_domains") or 0,
            referring_domains=r.get("referring_domains") or 0,
            referring_main_domains=r.get("referring_main_domains") or 0,
            referring_pages=r.get("referring_pages") or 0,
            referring_ips=r.get("referring_ips") or 0,
            broken_backlinks=r.get("broken_backlinks") or 0,
            broken_pages=r.get("broken_pages") or 0,
        ))
    SeoBacklinkHistoryPoint.objects.bulk_create(points, batch_size=500)


def run_snapshot(snapshot_id: int) -> dict:
    """Fill in an already-created PEND snapshot. Blocking; ~10 requests capped.

    The snapshot row is created by the backend so the UI has something to poll
    the instant the button is pressed. This only ever moves it forward.
    """
    from shared_models.backlink_models import SeoBacklinkSnapshot
    from shared_models.models import Domain

    snapshot = SeoBacklinkSnapshot.objects.get(id=snapshot_id)
    if snapshot.status not in ('PEND', 'RUN'):
        logger.info("[BL] Snapshot %s already %s — nothing to do", snapshot_id, snapshot.status)
        return {'snapshot_id': snapshot_id, 'status': snapshot.status, 'skipped': True}

    domain = Domain.objects.get(id=snapshot.domain_id)
    target = _target_for(domain)
    if not target:
        snapshot.status = 'FAIL'
        snapshot.error_message = f"Domain {domain.id} has no usable URL"
        snapshot.completed_at = timezone.now()
        snapshot.save()
        return {'snapshot_id': snapshot_id, 'status': 'FAIL'}

    snapshot.status = 'RUN'
    snapshot.save(update_fields=['status'])

    # Bill the owning organisation's own DataForSEO account when it has one.
    organisation = None
    try:
        from shared_models.models import Organisation
        organisation = Organisation.objects.filter(id=domain.organisation_id).first()
    except Exception:
        logger.exception("[BL] Could not load the organisation for domain %s", domain.id)

    client = BacklinksClient(organisation)
    caps = row_caps()

    try:
        summary = client.summary(target)
        if not summary:
            raise DataForSeoBacklinksError(f"No backlink data available for {target}")
        _apply_summary(snapshot, summary)

        plan = plan_fetch(summary, caps)
        logger.info(
            "[BL] %s: available=%s planned=%s est=$%.3f",
            target, plan.available, plan.planned, plan.estimated_cost,
        )

        _store_history(snapshot, client.history(target))
        _store_items(snapshot, client.paginate(
            "backlinks", target, plan.planned["backlinks"],
            order_by=["rank,desc"], extra={"mode": "as_is"},
        ))
        _store_referring_domains(snapshot, client.paginate(
            "referring_domains", target, plan.planned["referring_domains"],
            order_by=["rank,desc"],
        ))
        _store_anchors(snapshot, client.paginate(
            "anchors", target, plan.planned["anchors"], order_by=["backlinks,desc"],
        ))
        _store_pages(snapshot, client.paginate(
            "domain_pages", target, plan.planned["domain_pages"],
            order_by=["page_summary.backlinks,desc"],
        ))

        snapshot.is_truncated = plan.is_truncated
        snapshot.status = 'DONE'
        snapshot.completed_at = timezone.now()
        snapshot.next_refresh_allowed_at = snapshot.completed_at + timedelta(
            days=getattr(settings, "BACKLINK_REFRESH_INTERVAL_DAYS", 30)
        )
        logger.info(
            "[BL] %s complete: %d backlinks stored, $%.4f spent over %d requests",
            target, plan.planned["backlinks"], client.cost, client.requests_made,
        )
    except Exception as exc:
        snapshot.status = 'FAIL'
        snapshot.error_message = str(exc)[:2000]
        snapshot.completed_at = timezone.now()
        # next_refresh_allowed_at stays null — a failed fetch must not lock the
        # project out for a month.
        logger.error("[BL] Fetch failed for %s: %s", target, exc, exc_info=True)
    finally:
        snapshot.api_cost = round(client.cost, 6)
        snapshot.api_requests = client.requests_made
        snapshot.save()

    return {
        'snapshot_id': snapshot_id,
        'status': snapshot.status,
        'cost': float(snapshot.api_cost),
        'requests': snapshot.api_requests,
        'truncated': snapshot.is_truncated,
    }
