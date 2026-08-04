"""
Invoice settings — everything the tax invoice prints that is not derived from
usage.

One row per issuing user, edited on Profile ▸ Invoice Settings. The billing
figures come from services/billing.py; this supplies the letterhead: who is
issuing, who is being billed, the GST treatment, the numbering series and the
bank block.

Buyer details live in `buyers`, keyed by organisation id, because the invoice
is raised against whichever organisation is being billed and each has its own
GSTIN and registered address. Keeping it here rather than on Organisation
means the whole invoice is configured in one screen, which is what the setting
is for.
"""
from django.conf import settings
from django.db import models


class InvoiceSettings(models.Model):
    TAX_IGST = "IGST"
    TAX_CGST_SGST = "CGST_SGST"
    TAX_TYPE_CHOICES = [
        (TAX_IGST, "IGST (inter-state)"),
        (TAX_CGST_SGST, "CGST + SGST (intra-state)"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="invoice_settings",
    )

    # ----- Seller (the block beside the logo) -----
    company_name = models.CharField(max_length=255, blank=True, default="")
    # Free text so the address can keep the exact line breaks it prints with.
    company_address = models.TextField(blank=True, default="")
    company_gstin = models.CharField(max_length=32, blank=True, default="")
    company_state_name = models.CharField(max_length=64, blank=True, default="")
    company_state_code = models.CharField(max_length=8, blank=True, default="")
    company_email = models.EmailField(blank=True, default="")
    logo = models.ImageField(upload_to="invoice/", blank=True, null=True)

    # ----- Numbering: prints as "{prefix}/{number:03d}/{financial_year}" -----
    invoice_prefix = models.CharField(max_length=16, blank=True, default="INV")
    financial_year = models.CharField(max_length=16, blank=True, default="")
    next_number = models.PositiveIntegerField(default=1)

    # ----- Tax -----
    hsn_sac = models.CharField(max_length=16, blank=True, default="")
    tax_type = models.CharField(max_length=16, choices=TAX_TYPE_CHOICES, default=TAX_IGST)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18)

    # ----- Bank block -----
    bank_account_name = models.CharField(max_length=255, blank=True, default="")
    bank_name = models.CharField(max_length=255, blank=True, default="")
    bank_account_number = models.CharField(max_length=64, blank=True, default="")
    bank_branch_ifsc = models.CharField(max_length=255, blank=True, default="")

    # ----- Signature block -----
    signature = models.ImageField(upload_to="invoice/", blank=True, null=True)
    footer_note = models.CharField(
        max_length=255, blank=True, default="This is a Computer Generated Invoice"
    )

    # Printed under the TAX INVOICE heading on non-India invoices only. Kept
    # editable because the exact wording is prescribed and occasionally revised.
    export_declaration = models.CharField(
        max_length=255, blank=True,
        default=("SUPPLY MEANT FOR EXPORT/SUPPLY TO SEZ UNIT OR SEZ DEVELOPER "
                 "FOR AUTHORISED OPERATIONS ON PAYMENT OF IGST"),
    )

    # ----- Optional header grid values (left blank on the reference) -----
    delivery_note = models.CharField(max_length=255, blank=True, default="")
    payment_terms = models.CharField(max_length=255, blank=True, default="")
    reference_no = models.CharField(max_length=255, blank=True, default="")
    other_references = models.CharField(max_length=255, blank=True, default="")
    buyers_order_no = models.CharField(max_length=255, blank=True, default="")
    dispatch_doc_no = models.CharField(max_length=255, blank=True, default="")
    dispatched_through = models.CharField(max_length=255, blank=True, default="")
    destination = models.CharField(max_length=255, blank=True, default="")
    terms_of_delivery = models.TextField(blank=True, default="")

    # {"<organisation_id>": {name, address, gstin, state_name, state_code}}
    buyers = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "invoice_settings"
        verbose_name = "Invoice Settings"
        verbose_name_plural = "Invoice Settings"

    def __str__(self):
        return f"Invoice settings for {self.user_id}"

    def buyer_for(self, organisation_id, fallback_name=""):
        """Buyer block for an organisation, falling back to just its name."""
        entry = (self.buyers or {}).get(str(organisation_id)) or {}
        return {
            "name": entry.get("name") or fallback_name,
            "address": entry.get("address", ""),
            "gstin": entry.get("gstin", ""),
            "state_name": entry.get("state_name", ""),
            "state_code": entry.get("state_code", ""),
        }

    def invoice_number(self):
        return f"{self.invoice_prefix}/{self.next_number:03d}/{self.financial_year}".rstrip("/")


class FxRate(models.Model):
    """A cached foreign-exchange rate for one day.

    Invoices must be reproducible: regenerating July's invoice next year has to
    produce the same total it did when it was issued. The rate is therefore
    looked up once for the billing month's close, stored here, and re-read on
    every subsequent render — the upstream API is never consulted again for a
    date already recorded. It also keeps invoices working when the API is down.
    """
    base = models.CharField(max_length=3)
    quote = models.CharField(max_length=3)
    as_of = models.DateField()
    # 1 unit of `base` expressed in `quote`, e.g. INR->USD is ~0.0105.
    rate = models.DecimalField(max_digits=18, decimal_places=8)
    source = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "fx_rates"
        unique_together = ("base", "quote", "as_of")
        indexes = [models.Index(fields=["base", "quote", "as_of"])]

    def __str__(self):
        return f"1 {self.base} = {self.rate} {self.quote} on {self.as_of}"
