"""
Foreign-exchange rates for export invoices.

Export invoices are raised in USD while the rate card is in INR, so the amounts
have to be converted at the rate in force at the time of supply — the close of
the billing month, not the day the PDF happens to be downloaded. Using today's
rate on an old invoice is materially wrong: INR/USD moved 4.7% between February
and August 2026, which would misstate a February invoice by that much.

Once fetched, a rate is stored in FxRate and never fetched again for that date,
so reissuing an invoice reproduces the original figures exactly and a download
still works when the upstream API is unreachable.

Primary source: fawazahmed0/currency-api — open source (MIT), served free from
jsDelivr with no key, and the only free option offering date-pinned historical
rates. Fallback: open.er-api.com, which serves only the latest rate, so it is
used solely when no historical value can be obtained.
"""
import logging
from datetime import date as date_cls
from decimal import Decimal, InvalidOperation

import requests

logger = logging.getLogger(__name__)

# Date-pinned; @{date} returns that day's published rates.
_PRIMARY = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{date}/v1/currencies/{base}.json"
# Same data, different CDN — jsDelivr occasionally rate-limits.
_PRIMARY_ALT = "https://{date}.currency-api.pages.dev/v1/currencies/{base}.json"
# Latest only; no historical endpoint on the free tier.
_FALLBACK = "https://open.er-api.com/v6/latest/{base}"

_TIMEOUT = 12


class FxUnavailable(RuntimeError):
    """No rate could be obtained and none is cached."""


def _fetch_dated(base: str, quote: str, as_of: date_cls):
    """Rate published for a specific date, or None."""
    for template in (_PRIMARY, _PRIMARY_ALT):
        url = template.format(date=as_of.isoformat(), base=base.lower())
        try:
            resp = requests.get(url, timeout=_TIMEOUT)
            if resp.status_code != 200:
                continue
            payload = resp.json()
            value = (payload.get(base.lower()) or {}).get(quote.lower())
            if value:
                return Decimal(str(value)), f"currency-api@{as_of.isoformat()}"
        except (requests.RequestException, ValueError, InvalidOperation) as exc:
            logger.warning("FX lookup failed at %s: %s", url, exc)
    return None


def _fetch_latest(base: str, quote: str):
    """Today's rate, as a last resort."""
    try:
        resp = requests.get(_FALLBACK.format(base=base.upper()), timeout=_TIMEOUT)
        if resp.status_code == 200:
            payload = resp.json()
            value = (payload.get("rates") or {}).get(quote.upper())
            if value:
                return Decimal(str(value)), "open.er-api.com (latest)"
    except (requests.RequestException, ValueError, InvalidOperation) as exc:
        logger.warning("FX fallback failed: %s", exc)
    return None


def get_rate(base: str, quote: str, as_of: date_cls):
    """1 `base` expressed in `quote`, as at `as_of`.

    Returns (Decimal rate, source label). Cached permanently on first success.
    Raises FxUnavailable only when nothing is cached and every source fails —
    the caller should then refuse to produce the invoice rather than invent a
    conversion.
    """
    from ..models_invoice import FxRate

    base, quote = base.upper(), quote.upper()
    if base == quote:
        return Decimal("1"), "identity"

    cached = FxRate.objects.filter(base=base, quote=quote, as_of=as_of).first()
    if cached:
        return cached.rate, cached.source

    found = _fetch_dated(base, quote, as_of)
    if found is None:
        found = _fetch_latest(base, quote)
        if found is not None:
            # Flagged so it is obvious this is not the historical rate.
            found = (found[0], found[1] + " — historical unavailable")

    if found is None:
        # A neighbouring day is close enough to be defensible and far better
        # than failing outright; markets do not move much over a weekend.
        for delta in (1, 2, 3):
            for candidate in (as_of.toordinal() - delta,):
                alt = date_cls.fromordinal(candidate)
                near = _fetch_dated(base, quote, alt)
                if near:
                    found = (near[0], near[1] + f" (nearest to {as_of.isoformat()})")
                    break
            if found:
                break

    if found is None:
        raise FxUnavailable(
            f"No {base}->{quote} rate available for {as_of.isoformat()}"
        )

    rate, source = found
    FxRate.objects.update_or_create(
        base=base, quote=quote, as_of=as_of,
        defaults={"rate": rate, "source": source},
    )
    return rate, source
