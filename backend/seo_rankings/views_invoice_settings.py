"""
Invoice settings API — read and update the letterhead behind the tax invoice.

Super admin only, matching the billing endpoints it feeds. Multipart is
accepted so the logo and signature can be uploaded in the same request as the
text fields.
"""
import logging

from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models_invoice import InvoiceSettings
from .views_billing import _can_view_all_orgs, _is_super_admin

logger = logging.getLogger(__name__)

# Plain text/number fields the client may set.
EDITABLE_FIELDS = [
    "company_name", "company_address", "company_gstin", "company_state_name",
    "company_state_code", "company_email",
    "invoice_prefix", "financial_year", "next_number",
    "hsn_sac", "tax_type", "tax_rate",
    "bank_account_name", "bank_name", "bank_account_number", "bank_branch_ifsc",
    "footer_note", "export_declaration",
    "delivery_note", "payment_terms", "reference_no", "other_references",
    "buyers_order_no", "dispatch_doc_no", "dispatched_through", "destination",
    "terms_of_delivery",
]

NUMERIC_FIELDS = {"next_number", "tax_rate"}


def _serialize(settings_obj, request):
    def url(f):
        if not f:
            return ""
        try:
            return request.build_absolute_uri(f.url)
        except ValueError:
            return ""

    data = {f: getattr(settings_obj, f) for f in EDITABLE_FIELDS}
    data["tax_rate"] = float(settings_obj.tax_rate or 0)
    data["logo_url"] = url(settings_obj.logo)
    data["signature_url"] = url(settings_obj.signature)
    data["buyers"] = settings_obj.buyers or {}
    data["invoice_number_preview"] = settings_obj.invoice_number()
    return data


@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def invoice_settings(request):
    # The letterhead belongs to whoever issues invoices for the platform, not
    # to every super admin — one company issues them all. Gated on the same
    # BILLING_ALL_ORG_EMAILS list as the consolidated billing view.
    if not (_is_super_admin(request.user) and _can_view_all_orgs(request.user)):
        return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

    obj, _ = InvoiceSettings.objects.get_or_create(user=request.user)

    if request.method == "GET":
        return Response({"settings": _serialize(obj, request)})

    for field in EDITABLE_FIELDS:
        if field not in request.data:
            continue
        value = request.data.get(field)
        if field in NUMERIC_FIELDS:
            try:
                value = int(value) if field == "next_number" else float(value)
            except (TypeError, ValueError):
                return Response({"error": f"{field} must be a number"},
                                status=status.HTTP_400_BAD_REQUEST)
        setattr(obj, field, value)

    # buyers arrives as a JSON string because the request is multipart.
    if "buyers" in request.data:
        import json
        raw = request.data.get("buyers")
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
        except (TypeError, ValueError):
            return Response({"error": "buyers must be valid JSON"},
                            status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(parsed, dict):
            return Response({"error": "buyers must be an object"},
                            status=status.HTTP_400_BAD_REQUEST)
        obj.buyers = parsed

    for field in ("logo", "signature"):
        if field in request.FILES:
            setattr(obj, field, request.FILES[field])
        # An explicit empty string clears the existing image.
        elif request.data.get(f"clear_{field}") in ("1", "true", "True"):
            setattr(obj, field, None)

    obj.save()
    return Response({"settings": _serialize(obj, request)})
