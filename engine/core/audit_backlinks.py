"""Audit Engine — backlink authority via DataForSEO (one summary call per audit).

The links pointing at a site shape how much the engines trust and cite it.
This is the only part of the audit that needs a paid source: DataForSEO's
Backlinks Summary endpoint, ~$0.02-0.03 per call (one request, no rows).
It reuses the credentials and client of core.backlinks_processor, so the
account that pays for the product's backlink snapshots pays for this too.

    fetch_backlinks(host)   network; None when disabled, unconfigured or failed
    parse_backlinks(summary) pure; DataForSEO summary → the report block

The report block:

    authority_score      0-100 (DataForSEO rank is 0-1000; divided by 10)
    referring_domains    unique linking websites ("sites linking in")
    backlinks            all individual links
    dofollow_share       % of links passing authority
    broken_backlinks     links pointing at pages that no longer exist
    referring_ips / referring_pages / first_seen, for the detail view
    score                0-100 for the Website Health "Backlink authority" row

Off unless AUDIT_BACKLINKS_ENABLED is true; the audit never fails because of
it — a missing account or an API error reads as "not measured".
"""
import logging
import math
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

REFERRING_DOMAINS_FULL_CREDIT = 10_000   # log scale: 10 → 25, 100 → 50, 1,000 → 75, 10,000 → 100


def _int(v) -> int:
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def parse_backlinks(summary: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """DataForSEO /backlinks/summary result → report block. None when the summary is empty."""
    if not isinstance(summary, dict) or not summary:
        return None
    backlinks = _int(summary.get('backlinks'))
    referring = _int(summary.get('referring_main_domains') or summary.get('referring_domains'))
    rank = summary.get('rank')
    authority = round(min(1000, max(0, float(rank))) / 10) if isinstance(rank, (int, float)) else None
    # the live summary reports nofollow under referring_links_attributes; older shapes had a top-level count
    attrs = summary.get('referring_links_attributes') if isinstance(summary.get('referring_links_attributes'), dict) else {}
    nofollow = _int(summary.get('backlinks_nofollow') if summary.get('backlinks_nofollow') is not None else attrs.get('nofollow'))
    dofollow_share = round(100 * (backlinks - nofollow) / backlinks) if backlinks else None
    out = {
        'source': 'dataforseo',
        'authority_score': authority,
        'referring_domains': referring,
        'referring_domains_nofollow': _int(summary.get('referring_domains_nofollow')),
        'backlinks': backlinks,
        'backlinks_nofollow': nofollow,
        'dofollow_share': dofollow_share,
        'broken_backlinks': _int(summary.get('broken_backlinks')),
        'referring_ips': _int(summary.get('referring_ips')),
        'referring_pages': _int(summary.get('referring_pages')),
        'first_seen': (str(summary.get('first_seen'))[:10] if summary.get('first_seen') else None),
        'target': summary.get('target') or '',
    }
    # Health row: authority carries most of the weight, breadth of linking sites the rest.
    breadth = min(1.0, math.log10(referring + 1) / math.log10(REFERRING_DOMAINS_FULL_CREDIT + 1)) if referring else 0.0
    if authority is None:
        out['score'] = round(100 * breadth) if referring else None
    else:
        out['score'] = round(0.6 * authority + 40 * breadth)
    return out


def fetch_backlinks(host: str) -> Optional[Dict[str, Any]]:
    """One Backlinks Summary call for the root domain. Never raises."""
    try:
        from core.backlinks_processor import BacklinksClient
        client = BacklinksClient()
        summary = client.summary(host, include_subdomains=True)
        block = parse_backlinks(summary)
        if block is not None:
            block['cost_usd'] = round(client.cost, 4)
        logger.info('[AuditBacklinks] %s: %s referring domains, cost $%.4f', host, (block or {}).get('referring_domains'), client.cost)
        return block
    except Exception as exc:  # noqa: BLE001 - unconfigured account, API error, timeout
        logger.info('[AuditBacklinks] not measured for %s: %s', host, exc)
        return None
