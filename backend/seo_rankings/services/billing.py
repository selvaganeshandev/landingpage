"""
Keyword-based billing — rate card and per-project pricing.

The single source of truth for money in this application. Price is computed
here and travels to the client pre-computed; the UI sums the rows it is given
and does no arithmetic of its own (see BILLING_KEYWORD_CALCULATION.md §3.5).

Model B from the spec — a tiered slab. A project falls entirely into the
smallest slab that fits its tracked keyword count, and pays that slab's flat
price. Two distinct numbers per project, which must not be conflated:

    used keywords   how many keywords the project actually tracks
    keyword limit   the slab it lands in — the billable quantity

So 902 tracked keywords sit in the 1,000 slab and cost 3,599, exactly as the
reference billing screen shows.
"""
from dataclasses import dataclass
from typing import List, Optional

CURRENCY = "INR"

# The published plan matrix. Ordered ascending; the first slab that fits wins.
# `content_gap` is None on every tier but the first because the source rate
# card only states a figure there — not invented for the others.
PLANS = [
    {"keyword_limit": 300,  "price": 1499,  "tracking": "Daily", "ga_gsc": True,
     "all_features": True, "manual_refresh": 500,  "content_gap": 1000},
    {"keyword_limit": 750,  "price": 2499,  "tracking": "Daily", "ga_gsc": True,
     "all_features": True, "manual_refresh": 750,  "content_gap": None},
    {"keyword_limit": 1000, "price": 3599,  "tracking": "Daily", "ga_gsc": True,
     "all_features": True, "manual_refresh": 1000, "content_gap": None},
    {"keyword_limit": 3000, "price": 8999,  "tracking": "Daily", "ga_gsc": True,
     "all_features": True, "manual_refresh": 3000, "content_gap": None},
    {"keyword_limit": 5000, "price": 12999, "tracking": "Daily", "ga_gsc": True,
     "all_features": True, "manual_refresh": 5000, "content_gap": None},
    {"keyword_limit": 8000, "price": 16999, "tracking": "Daily", "ga_gsc": True,
     "all_features": True, "manual_refresh": 8000, "content_gap": None},
]

# Pricing only ever needs (limit, price); derived so the two cannot drift.
RATE_CARD = [(p["keyword_limit"], p["price"]) for p in PLANS]

# Above the largest slab there is no published price, so the top slab is
# charged and the overage flagged rather than silently invented. Nothing in the
# system is near it today (the largest project tracks 1,765 keywords).
TOP_SLAB, TOP_PRICE = RATE_CARD[-1]


@dataclass
class BillingRow:
    domain_id: int
    name: str
    url: str
    country: str
    used_keywords: int
    keyword_limit: int
    price: int
    currency: str = CURRENCY
    over_top_slab: bool = False
    # Only meaningful in the consolidated (all-organisations) view.
    organisation: str = ""

    def as_dict(self) -> dict:
        return {
            "domain_id": self.domain_id,
            "name": self.name,
            "url": self.url,
            "country": self.country,
            "used_keywords": self.used_keywords,
            "keyword_limit": self.keyword_limit,
            "price": self.price,
            "currency": self.currency,
            "over_top_slab": self.over_top_slab,
            "organisation": self.organisation,
        }


def slab_for(used_keywords: int):
    """Return (keyword_limit, price) for a tracked keyword count.

    A project tracking nothing is listed but not charged: it consumes no
    keywords, so it carries no slab and no price. It still appears in the
    tables at 0 / 0 rather than being hidden, so an admin can see the project
    exists and simply is not being billed for it yet.
    """
    quantity = max(0, int(used_keywords or 0))
    if quantity == 0:
        return 0, 0
    for limit, price in RATE_CARD:
        if quantity <= limit:
            return limit, price
    return TOP_SLAB, TOP_PRICE


def build_row(domain_id: int, name: str, url: str, country: str, used_keywords: int) -> BillingRow:
    limit, price = slab_for(used_keywords)
    return BillingRow(
        domain_id=domain_id,
        name=name or "",
        url=url or "",
        country=country or "",
        used_keywords=int(used_keywords or 0),
        keyword_limit=limit,
        price=price,
        over_top_slab=int(used_keywords or 0) > TOP_SLAB,
    )


def summarise(rows: List[BillingRow]) -> dict:
    """Totals for one region table.

    `total_projects` counts every project shown, including unbilled ones, so it
    matches the number of rows. `billable_projects` counts only those actually
    charged — the two differ whenever a project tracks no keywords.

    Prices are whole rupees, so the displayed total is always exactly the sum
    of the displayed rows — no rounding drift between row and footer.
    """
    return {
        "total_projects": len(rows),
        "billable_projects": sum(1 for r in rows if r.price > 0),
        "total_price": sum(r.price for r in rows),
        "currency": CURRENCY,
    }


# Region buckets. UAE is billed separately; everything else shares a table.
# Driven by data rather than an if/else so a third region is a list entry.
UAE_COUNTRIES = {"united arab emirates", "uae", "u.a.e."}


def region_key_for(country: Optional[str]) -> str:
    return "uae" if (country or "").strip().lower() in UAE_COUNTRIES else "row"


# `display_currency` is presentation only — the rate card, the stored price and
# every calculation stay in INR. UAE clients are invoiced in USD, so the screen
# leads with USD and keeps the INR figure alongside it; converting for display
# rather than storing a second price keeps one source of truth for money.
REGIONS = [
    {"key": "row", "label": "India & Other Regions", "display_currency": CURRENCY},
    {"key": "uae", "label": "UAE", "display_currency": "USD"},
]


# ---------------------------------------------------------------------------
# Amount in words — Indian numbering (lakh / crore), as the invoice prints it
# ---------------------------------------------------------------------------

_ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
         "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
         "Seventeen", "Eighteen", "Nineteen"]
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _two(n: int) -> str:
    if n < 20:
        return _ONES[n]
    return (_TENS[n // 10] + (" " + _ONES[n % 10] if n % 10 else "")).strip()


def _three(n: int) -> str:
    out = []
    if n >= 100:
        out.append(_ONES[n // 100] + " Hundred")
        n %= 100
    if n:
        out.append(_two(n))
    return " ".join(out)


def _int_words_western(n: int) -> str:
    """Thousand / Million / Billion grouping, for currencies other than INR."""
    if n == 0:
        return "Zero"
    parts, units = [], [(1_000_000_000, "Billion"), (1_000_000, "Million"), (1_000, "Thousand")]
    for size, name in units:
        chunk, n = divmod(n, size)
        if chunk:
            parts.append(_three(chunk) + " " + name)
    if n:
        parts.append(_three(n))
    return " ".join(parts)


def _int_words_indian(n: int) -> str:
    """Lakh / Crore grouping, as Indian invoices spell amounts."""
    if n == 0:
        return "Zero"
    parts = []
    crore, n = divmod(n, 10_000_000)
    lakh, n = divmod(n, 100_000)
    thousand, rest = divmod(n, 1_000)
    if crore:
        parts.append(_three(crore) + " Crore")
    if lakh:
        parts.append(_three(lakh) + " Lakh")
    if thousand:
        parts.append(_three(thousand) + " Thousand")
    if rest:
        parts.append(_three(rest))
    return " ".join(parts)


def amount_in_words(amount, currency: str = CURRENCY) -> str:
    """"INR One Lakh Six Thousand Two Hundred Only".

    INR uses lakh/crore grouping and whole rupees, since every rate-card price
    is an integer. Converted currencies can carry a fractional part, so cents
    are spelled when present.
    """
    currency = (currency or CURRENCY).upper()
    value = float(amount or 0)

    if currency == "INR":
        whole = int(round(value))
        return f"INR {_int_words_indian(whole)} Only"

    whole = int(value)
    cents = int(round((value - whole) * 100))
    if cents == 100:  # rounding pushed it to the next unit
        whole, cents = whole + 1, 0
    # Export invoices spell it out rather than using the ISO code.
    label = "US Dollar" if currency == "USD" else currency
    words = f"{label} {_int_words_western(whole)}"
    if cents:
        words += f" and Cents {_int_words_western(cents)}"
    return words + " Only"
