"""
Billing endpoints — per-project keyword charges, split by region.

Super-admin only, enforced here as well as on the tab, so the data is
unreachable by URL for anyone else (BILLING_KEYWORD_CALCULATION.md §5.1).

Price is computed server-side by services/billing.py and sent pre-computed;
the client sums the rows it receives and does no pricing arithmetic.
"""
import logging
from datetime import datetime, timedelta
from io import BytesIO

from django.conf import settings
from django.db.models import Count, Min, Q
from django.utils import timezone
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from domains.models import Domain
from .models import SeoKeywordRank
from .services.billing import (
    CURRENCY,
    PLANS,
    REGIONS,
    build_row,
    region_key_for,
    summarise,
)

logger = logging.getLogger(__name__)


def _is_super_admin(user) -> bool:
    return getattr(user, "role", None) == "super_admin"


def billing_owner_emails():
    """Accounts that act as the billing operator for the platform."""
    return {
        e.strip().lower()
        for e in (getattr(settings, "BILLING_ALL_ORG_EMAILS", "") or "").split(",")
        if e.strip()
    }


def _can_view_all_orgs(user) -> bool:
    """Whether this account may see every organisation's charges.

    Driven by BILLING_ALL_ORG_EMAILS so the list is config, not code. Everyone
    else — including other super admins — stays scoped to their own
    organisation.
    """
    return (getattr(user, "email", "") or "").lower() in billing_owner_emails()


def _visible_organisations(user):
    """Organisations this account may report on, as [{id, name}]."""
    from domains.models import Domain

    if not _can_view_all_orgs(user):
        org = user.organisation
        return [{"id": org.id, "name": org.name}] if org else []

    rows = (
        Domain.objects.values("organisation_id", "organisation__name")
        .distinct()
        .order_by("organisation__name")
    )
    return [
        {"id": r["organisation_id"], "name": r["organisation__name"] or f"Org {r['organisation_id']}"}
        for r in rows
        if r["organisation_id"]
    ]


def _resolve_scope(request):
    """Work out which organisations this request covers.

    Returns (can_view_all, organisations, selected, org_ids) or None when the
    requested organisation is not one the caller may see. Shared by the summary
    and the export so the two can never report on different scopes.
    """
    user = request.user
    can_view_all = _can_view_all_orgs(user)
    organisations = _visible_organisations(user)

    # ?organisation=all | <id>. Anyone without the all-orgs grant is pinned to
    # their own organisation regardless of what they ask for.
    requested = (request.query_params.get("organisation") or "").strip().lower()
    if not can_view_all:
        return can_view_all, [], "own", None

    if requested and requested != "all":
        try:
            wanted = int(requested)
        except ValueError:
            return None
        if wanted not in {o["id"] for o in organisations}:
            return None
        return can_view_all, organisations, str(wanted), [wanted]

    # Always exactly one organisation, never a combined view. Billing figures
    # are only meaningful per account, and an invoice has to be addressed to a
    # single legal entity — a consolidated document has no buyer to name.
    # "all" is accepted and coerced rather than rejected so an old bookmark
    # still resolves to something sensible.
    if not organisations:
        return can_view_all, [], "own", None
    first = organisations[0]["id"]
    return can_view_all, organisations, str(first), [first]


def _billing_regions(user, organisation_ids=None, as_of=None):
    """Build the region tables for the requesting user's organisation.

    Every domain in the organisation appears, including those tracking no
    keywords yet — the rate card is priced "per project", so a project costs
    the entry slab whether or not keywords have been added. Scoping is by
    organisation, so each super admin sees only their own account.

    Counts come from one annotated query rather than a count per domain.
    """
    # `as_of` reconstructs a past month: count only keywords that existed by
    # then. Keywords deleted since are unrecoverable, so a historical invoice
    # can under-count — it reflects what the data still records.
    if as_of is None:
        domains = Domain.objects.annotate(used=Count("seo_keyword_ranks"))
    else:
        domains = Domain.objects.annotate(
            used=Count("seo_keyword_ranks", filter=Q(seo_keyword_ranks__created_at__lt=as_of))
        )
    if organisation_ids is None:
        domains = domains.filter(organisation=user.organisation)
    else:
        domains = domains.filter(organisation_id__in=organisation_ids)
    domains = domains.select_related("organisation").order_by("-used", "name")

    buckets = {r["key"]: [] for r in REGIONS}
    for d in domains:
        row = build_row(
            domain_id=d.id,
            name=d.name,
            url=d.url,
            country=d.country,
            used_keywords=d.used,
        )
        # Carried so a consolidated view can say which account a project is
        # under; ignored when viewing a single organisation.
        row.organisation = d.organisation.name if d.organisation else ""
        buckets.setdefault(region_key_for(row.country), []).append(row)

    return [
        {
            "key": region["key"],
            "label": region["label"],
            "projects": [r.as_dict() for r in buckets.get(region["key"], [])],
            **summarise(buckets.get(region["key"], [])),
        }
        for region in REGIONS
    ]


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def billing_summary(request):
    """Per-project billing rows grouped into region tables."""
    if not _is_super_admin(request.user):
        return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

    scope = _resolve_scope(request)
    if scope is None:
        return Response({"error": "Invalid organisation"}, status=status.HTTP_400_BAD_REQUEST)
    can_view_all, organisations, selected, org_ids = scope

    regions = _billing_regions(request.user, organisation_ids=org_ids)
    return Response({
        "currency": CURRENCY,
        "rate_card": PLANS,
        "regions": regions,
        # Across every region, so the header figure does not depend on which
        # table you happen to be looking at.
        "grand_total": sum(r["total_price"] for r in regions),
        "total_projects": sum(r["total_projects"] for r in regions),
        "can_view_all_orgs": can_view_all,
        "can_export": not can_view_all,
        "organisations": organisations if can_view_all else [],
        "selected_organisation": selected,
        "invoice_months": _invoice_months(request.user, organisation_ids=org_ids),
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def billing_export(request):
    """XLSX of every region — the whole account, not the visible table."""
    if not _is_super_admin(request.user):
        return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

    scope = _resolve_scope(request)
    if scope is None:
        return Response({"error": "Invalid organisation"}, status=status.HTTP_400_BAD_REQUEST)
    _can_view_all, _orgs, _selected, org_ids = scope

    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    regions = _billing_regions(request.user, organisation_ids=org_ids)

    wb = Workbook()
    wb.remove(wb.active)

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="6D28D9")
    total_font = Font(bold=True)

    for region in regions:
        # Excel forbids / \ ? * [ ] : in sheet names and caps them at 31 chars.
        title = region["label"].replace("&", "and")[:31]
        ws = wb.create_sheet(title=title)

        multi_org = len({p["organisation"] for p in region["projects"]}) > 1
        headers = ["#", "Project", "Domain", "Country"]
        if multi_org:
            headers.append("Organisation")
        headers += ["Used Keywords", "Keyword Limit", f"Price ({CURRENCY})"]
        ws.append(headers)
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")

        for i, p in enumerate(region["projects"], start=1):
            row = [i, p["name"], p["url"], p["country"]]
            if multi_org:
                row.append(p["organisation"])
            row += [p["used_keywords"], p["keyword_limit"], p["price"]]
            ws.append(row)

        ws.append([])
        total_row = ws.max_row + 1
        price_col = len(headers)
        ws.cell(row=total_row, column=1, value=f"Total — {region['billable_projects']} billable of {region['total_projects']} project(s)").font = total_font
        ws.cell(row=total_row, column=price_col, value=region["total_price"]).font = total_font

        widths = [6, 32, 40, 22] + ([26] if multi_org else []) + [16, 16, 16]
        for idx, width in enumerate(widths, start=1):
            ws.column_dimensions[chr(64 + idx)].width = width

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    response = HttpResponse(
        buf.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="promptmaxx_billing.xlsx"'
    return response


# ---------------------------------------------------------------------------
# Monthly invoices
# ---------------------------------------------------------------------------

def _month_bounds(month: str):
    """'YYYY-MM' -> (label, exclusive end datetime), or None if malformed.

    The end bound is the first instant of the following month, so the invoice
    covers everything that existed at any point up to the month's close.
    """
    try:
        start = datetime.strptime(month, "%Y-%m")
    except (TypeError, ValueError):
        return None
    start = timezone.make_aware(start) if timezone.is_naive(start) else start
    # First day of the next month.
    end = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    return start.strftime("%B %Y"), end


def _invoice_months(user, organisation_ids=None):
    """Months with billable history, newest first, as ['YYYY-MM', ...]."""
    qs = SeoKeywordRank.objects.all()
    if organisation_ids is None:
        qs = qs.filter(domain__organisation=user.organisation)
    else:
        qs = qs.filter(domain__organisation_id__in=organisation_ids)

    first = qs.aggregate(first=Min("created_at"))["first"]
    if not first:
        return []

    now = timezone.now()
    months, cursor = [], first.replace(day=1)
    while cursor <= now:
        months.append(cursor.strftime("%Y-%m"))
        cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
    return list(reversed(months))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def billing_invoice(request):
    """Monthly tax invoice PDF for ?month=YYYY-MM."""
    if not _is_super_admin(request.user):
        return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

    scope = _resolve_scope(request)
    if scope is None:
        return Response({"error": "Invalid organisation"}, status=status.HTTP_400_BAD_REQUEST)
    can_view_all, organisations, selected, org_ids = scope

    bounds = _month_bounds(request.query_params.get("month", ""))
    if bounds is None:
        return Response({"error": "month must be YYYY-MM"}, status=status.HTTP_400_BAD_REQUEST)
    period, end = bounds

    regions = _billing_regions(request.user, organisation_ids=org_ids, as_of=end)

    # One invoice per region: India & Other Regions and UAE are billed
    # separately. `region=all` still exists for a combined document.
    # Filtering happens before anything is totalled, so the itemised page 2
    # always reconciles with page 1's taxable value — a breakdown that does not
    # sum to its own total is worse than no breakdown.
    region_key = (request.query_params.get("region") or "").strip().lower()
    valid_keys = {r["key"] for r in REGIONS}
    if not region_key:
        region_key = REGIONS[0]["key"]
    if region_key not in valid_keys:
        # No combined option: one region is taxed and the other zero-rated, so
        # a single document cannot state a coherent tax treatment.
        return Response({"error": "Invalid region"}, status=status.HTTP_400_BAD_REQUEST)
    regions = [r for r in regions if r["key"] == region_key]

    subtotal = sum(r["total_price"] for r in regions)

    from .models_invoice import InvoiceSettings
    from .services.invoice_template import render_invoice_html
    from reports.services.weasyprint_pdf_generator import convert_html_to_pdf_weasyprint

    # Always the billing operator's letterhead: one company issues every
    # invoice, so a super admin downloading their own still gets the real
    # company block rather than an empty one attached to their account.
    from django.contrib.auth import get_user_model
    owner = (get_user_model().objects
             .filter(email__in=billing_owner_emails()).first()) or request.user
    cfg_obj, _ = InvoiceSettings.objects.get_or_create(user=owner)

    # Exports carry no GST: the supply is outside India, so no tax line, no
    # HSN/SAC summary and no tax in words. Domestic invoices are unchanged.
    is_export = bool(region_key and region_key not in ("", "all", "row"))
    if is_export:
        tax_rate, tax_amount, tax_label = 0.0, 0, ""
    else:
        tax_rate = float(cfg_obj.tax_rate or 0)
        tax_amount = round(subtotal * tax_rate / 100)
        tax_label = ("IGST" if cfg_obj.tax_type == InvoiceSettings.TAX_IGST else "CGST+SGST")
        tax_label = f"{tax_label}@{tax_rate:g}%"
    total = subtotal + tax_amount

    # Which organisation is being billed. In the consolidated view there is no
    # single buyer, so the invoice is addressed to the account as a whole.
    buyer_org_id = org_ids[0] if org_ids else request.user.organisation_id
    buyer_name = next(
        (o["name"] for o in organisations if o["id"] == buyer_org_id),
        request.user.organisation.name if request.user.organisation else "",
    )

    # The buyer block belongs to the organisation being invoiced, not to the
    # issuing user — it is edited under Organization Settings > Invoice Details.
    from authentication.models import Organisation
    org = Organisation.objects.filter(id=buyer_org_id).first()
    buyer = (org.invoice_party(region_key or "row") if org else
             {"name": buyer_name, "address": "", "gstin": "",
              "state_name": "", "state_code": ""})

    # Page 1 carries one consolidated charge — a GST invoice reads better with a
    # single service line than with dozens of brand rows. The per-brand detail
    # goes on page 2 as an itemised bill.
    items = [{
        "particulars": "Promptmaxx Subscription Payment",
        "sub": period,
        "amount": subtotal,
    }]

    # Export invoices are raised in USD. The rate is the one in force at the
    # close of the billing month — the time of supply — not the day the PDF is
    # downloaded, so reissuing an old invoice reproduces the original figures.
    currency, fx = CURRENCY, None
    if is_export:
        from .services.fx import FxUnavailable, get_rate
        rate_date = (end - timedelta(days=1)).date()  # last day of the month
        try:
            rate, source = get_rate("INR", "USD", rate_date)
        except FxUnavailable as exc:
            logger.error("Invoice FX unavailable: %s", exc)
            return Response(
                {"error": "Exchange rate unavailable for this period. Try again shortly."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        currency = "USD"
        fx = {
            "rate": rate,
            # Quoted the way people read it, to 2dp.
            "inverse": f"{(1 / float(rate)):,.2f}",
            "as_of": rate_date.strftime("%d-%b-%Y"),
            "source": source,
        }

    def media_path(f):
        # xhtml2pdf reads local paths; a URL would need a fetcher and would
        # fail silently, leaving the logo blank.
        try:
            return f.path if f else ""
        except (ValueError, NotImplementedError):
            return ""

    html = render_invoice_html(
        cfg={f: getattr(cfg_obj, f) for f in (
            "delivery_note", "payment_terms", "reference_no", "other_references",
            "buyers_order_no", "dispatch_doc_no", "dispatched_through", "destination",
            "terms_of_delivery", "bank_account_name", "bank_name",
            "bank_account_number", "bank_branch_ifsc", "footer_note")},
        seller={
            "name": cfg_obj.company_name,
            "address": cfg_obj.company_address,
            "gstin": cfg_obj.company_gstin,
            "state_name": cfg_obj.company_state_name,
            "state_code": cfg_obj.company_state_code,
            "email": cfg_obj.company_email,
        },
        buyer=buyer,
        consignee=buyer,
        invoice_no=cfg_obj.invoice_number(),
        invoice_date=end.strftime("%d-%b-%y"),
        items=items,
        subtotal=subtotal,
        tax_label=tax_label,
        tax_rate=tax_rate,
        tax_amount=tax_amount,
        total=total,
        hsn_sac=cfg_obj.hsn_sac,
        logo_src=media_path(cfg_obj.logo),
        signature_src=media_path(cfg_obj.signature),
        regions=regions,
        period=period,
        # Export / SEZ declaration belongs only on invoices raised outside
        # India; a domestic invoice carrying it would be wrong.
        title_note=cfg_obj.export_declaration if is_export else "",
        currency=currency,
        fx=fx,
    )

    # WeasyPrint, not xhtml2pdf: the approved layout uses rowspan,
    # border-collapse and percentage column widths, none of which xhtml2pdf
    # renders correctly.
    try:
        pdf = convert_html_to_pdf_weasyprint(html)
    except Exception as exc:
        logger.error("Invoice render failed: %s", exc, exc_info=True)
        return Response({"error": "Could not render the invoice"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    response = HttpResponse(pdf.getvalue(), content_type="application/pdf")
    month = request.query_params.get("month")
    response["Content-Disposition"] = f'attachment; filename="invoice_{month}.pdf"'
    return response
