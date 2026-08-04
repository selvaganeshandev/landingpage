import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/services/api";
import { Loader2, Save, Building2, Landmark, ReceiptText } from "lucide-react";

/**
 * Everything the tax invoice prints that is not derived from usage: who is
 * issuing it, who is billed, the GST treatment, the numbering series and the
 * bank block. The billing figures come from the keyword data; this is the
 * letterhead.
 */

/* The Consignee / Buyer block is NOT here: those are properties of the
   organisation being billed, and live under Organization Settings >
   Invoice Details. This screen is only the issuing company's letterhead. */
type Settings = Record<string, any>;

const Field = ({ label, children, hint }: { label: string; children: React.ReactNode; hint?: string }) => (
  <div className="space-y-1.5">
    <Label className="text-sm">{label}</Label>
    {children}
    {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
  </div>
);

export default function InvoiceSettingsTab() {
  const { toast } = useToast();
  const [s, setS] = useState<Settings>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [signatureFile, setSignatureFile] = useState<File | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await apiClient.getInvoiceSettings() as any;
        setS(res.settings || {});
      } catch (e: any) {
        toast({ title: "Could not load invoice settings", description: e?.message, variant: "destructive" });
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const set = (k: string, v: any) => setS((p) => ({ ...p, [k]: v }));

  const save = async () => {
    setSaving(true);
    try {
      const res = await apiClient.saveInvoiceSettings(s, { logo: logoFile, signature: signatureFile }) as any;
      setS(res.settings || {});
      setLogoFile(null);
      setSignatureFile(null);
      toast({ title: "Invoice settings saved" });
    } catch (e: any) {
      toast({ title: "Could not save", description: e?.message, variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ── Seller ─────────────────────────────────────────────────────── */}
      <Card className="border border-border">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Building2 className="h-5 w-5" /> Your company
          </CardTitle>
          <CardDescription>Prints beside the logo at the top of the invoice.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Field label="Company name">
            <Input value={s.company_name || ""} onChange={(e) => set("company_name", e.target.value)} />
          </Field>
          <Field label="Address" hint="One line per line — the invoice keeps these breaks exactly.">
            <Textarea rows={3} value={s.company_address || ""} onChange={(e) => set("company_address", e.target.value)} />
          </Field>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Field label="GSTIN / UIN">
              <Input value={s.company_gstin || ""} onChange={(e) => set("company_gstin", e.target.value)} />
            </Field>
            <Field label="State name">
              <Input value={s.company_state_name || ""} onChange={(e) => set("company_state_name", e.target.value)} />
            </Field>
            <Field label="State code">
              <Input value={s.company_state_code || ""} onChange={(e) => set("company_state_code", e.target.value)} />
            </Field>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="E-mail">
              <Input value={s.company_email || ""} onChange={(e) => set("company_email", e.target.value)} />
            </Field>
            <Field label="Logo" hint={s.logo_url ? "A new file replaces the current logo." : "PNG or JPG."}>
              <div className="flex items-center gap-3">
                {s.logo_url && <img src={s.logo_url} alt="" className="h-9 border border-border rounded" />}
                <Input type="file" accept="image/*" onChange={(e) => setLogoFile(e.target.files?.[0] || null)} />
              </div>
            </Field>
          </div>
        </CardContent>
      </Card>

      {/* ── Numbering + tax ────────────────────────────────────────────── */}
      <Card className="border border-border">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <ReceiptText className="h-5 w-5" /> Numbering &amp; tax
          </CardTitle>
          <CardDescription>
            Invoice number prints as prefix / number / financial year — currently{" "}
            <span className="font-medium text-foreground">{s.invoice_number_preview || "—"}</span>.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Field label="Prefix"><Input value={s.invoice_prefix || ""} onChange={(e) => set("invoice_prefix", e.target.value)} /></Field>
            <Field label="Financial year" hint="e.g. 2025-26">
              <Input value={s.financial_year || ""} onChange={(e) => set("financial_year", e.target.value)} />
            </Field>
            <Field label="Next number"><Input type="number" min={1} value={s.next_number ?? 1} onChange={(e) => set("next_number", e.target.value)} /></Field>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Field label="HSN / SAC"><Input value={s.hsn_sac || ""} onChange={(e) => set("hsn_sac", e.target.value)} /></Field>
            <Field label="Tax type">
              <Select value={s.tax_type || "IGST"} onValueChange={(v) => set("tax_type", v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="IGST">IGST (inter-state)</SelectItem>
                  <SelectItem value="CGST_SGST">CGST + SGST (intra-state)</SelectItem>
                </SelectContent>
              </Select>
            </Field>
            <Field label="Tax rate %"><Input type="number" step="0.01" value={s.tax_rate ?? 18} onChange={(e) => set("tax_rate", e.target.value)} /></Field>
          </div>
        </CardContent>
      </Card>

      {/* ── Bank + signature ───────────────────────────────────────────── */}
      <Card className="border border-border">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Landmark className="h-5 w-5" /> Bank &amp; signature
          </CardTitle>
          <CardDescription>Prints in the block above the authorised signatory.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="A/c holder's name"><Input value={s.bank_account_name || ""} onChange={(e) => set("bank_account_name", e.target.value)} /></Field>
            <Field label="Bank name"><Input value={s.bank_name || ""} onChange={(e) => set("bank_name", e.target.value)} /></Field>
            <Field label="A/c number"><Input value={s.bank_account_number || ""} onChange={(e) => set("bank_account_number", e.target.value)} /></Field>
            <Field label="Branch & IFS code"><Input value={s.bank_branch_ifsc || ""} onChange={(e) => set("bank_branch_ifsc", e.target.value)} /></Field>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="Signature image" hint={s.signature_url ? "A new file replaces the current signature." : "Transparent PNG works best."}>
              <div className="flex items-center gap-3">
                {s.signature_url && <img src={s.signature_url} alt="" className="h-9 border border-border rounded" />}
                <Input type="file" accept="image/*" onChange={(e) => setSignatureFile(e.target.files?.[0] || null)} />
              </div>
            </Field>
            <Field label="Footer note"><Input value={s.footer_note || ""} onChange={(e) => set("footer_note", e.target.value)} /></Field>
          </div>
          <div className="grid grid-cols-1 gap-4">
            <Field
              label="Export / SEZ declaration"
              hint="Printed under the TAX INVOICE heading on non-India invoices only."
            >
              <Textarea
                rows={2}
                value={s.export_declaration || ""}
                onChange={(e) => set("export_declaration", e.target.value)}
              />
            </Field>
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button onClick={save} disabled={saving} className="gap-2 gradient-primary text-primary-foreground">
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          Save invoice settings
        </Button>
      </div>
    </div>
  );
}
