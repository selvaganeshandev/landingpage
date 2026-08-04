import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/services/api";
import { Loader2, Save, ReceiptText, Globe2 } from "lucide-react";

/**
 * Invoice Details — this organisation's registered particulars.
 *
 * These print as the Consignee (Ship to) and Buyer (Bill to) blocks on its tax
 * invoices. They describe the organisation, so they live here rather than on
 * the invoicing user's profile: each organisation owns and maintains its own.
 *
 * The issuing company's letterhead (logo, GSTIN, bank, numbering) is a
 * different thing entirely and lives under Profile > Invoice Settings.
 */

const BASE = ["legal_name", "address", "gstin", "state_name", "state_code"] as const;
const FIELDS = [
  ...BASE.map((f) => `billing_${f}`),
  ...BASE.map((f) => `billing_alt_${f}`),
];

export default function InvoiceDetailsTab() {
  const { toast } = useToast();
  const [form, setForm] = useState<Record<string, string>>({});
  const [orgName, setOrgName] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const d = await apiClient.getOrganization() as any;
        setOrgName(d?.name || "");
        setForm(Object.fromEntries(FIELDS.map((f) => [f, d?.[f] || ""])));
      } catch (e: any) {
        toast({ title: "Could not load invoice details", description: e?.message, variant: "destructive" });
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const set = (k: string, v: string) => setForm((p) => ({ ...p, [k]: v }));

  const save = async () => {
    setSaving(true);
    try {
      await apiClient.updateOrganization(form);
      toast({ title: "Invoice details saved" });
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

  /* Two registered entities: the same organisation is frequently invoiced
     through a different company abroad, so each region gets its own block.
     `prefix` is "billing_" or "billing_alt_". */
  // A plain function, not a component. Declared inside the component body, a
  // component would be a NEW type on every render, so React would unmount and
  // remount these inputs on each keystroke and the field would lose focus.
  const block = (prefix: string, taxLabel: string) => (
    <CardContent className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <Label className="text-sm">Registered name</Label>
          <Input
            value={form[`${prefix}legal_name`] || ""}
            onChange={(e) => set(`${prefix}legal_name`, e.target.value)}
            placeholder={orgName}
          />
          <p className="text-xs text-muted-foreground">
            Falls back to {prefix === "billing_" ? `the organization name (${orgName})` : "the India block"} when blank.
          </p>
        </div>
        <div className="space-y-1.5">
          <Label className="text-sm">{taxLabel}</Label>
          <Input
            value={form[`${prefix}gstin`] || ""}
            onChange={(e) => set(`${prefix}gstin`, e.target.value)}
          />
        </div>
      </div>

      <div className="space-y-1.5">
        <Label className="text-sm">Registered address</Label>
        <Textarea
          rows={4}
          value={form[`${prefix}address`] || ""}
          onChange={(e) => set(`${prefix}address`, e.target.value)}
        />
        <p className="text-xs text-muted-foreground">
          One line per line — the invoice keeps these breaks exactly.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <Label className="text-sm">State / Emirate name</Label>
          <Input
            value={form[`${prefix}state_name`] || ""}
            onChange={(e) => set(`${prefix}state_name`, e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label className="text-sm">State code</Label>
          <Input
            value={form[`${prefix}state_code`] || ""}
            onChange={(e) => set(`${prefix}state_code`, e.target.value)}
            placeholder="e.g. 27"
          />
        </div>
      </div>
    </CardContent>
  );

  return (
    <div className="space-y-6">
      <Card className="border border-border">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <ReceiptText className="h-5 w-5" /> India &amp; Other Regions
          </CardTitle>
          <CardDescription>
            How <span className="font-medium text-foreground">{orgName}</span> appears as the
            Consignee and Buyer on invoices for the India region.
          </CardDescription>
        </CardHeader>
        {block("billing_", "GSTIN / UIN")}
      </Card>

      <Card className="border border-border">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Globe2 className="h-5 w-5" /> UAE &amp; other countries
          </CardTitle>
          <CardDescription>
            Used on invoices raised for the non-India region. Leave blank to reuse the
            India block above.
          </CardDescription>
        </CardHeader>
        {block("billing_alt_", "Tax registration (TRN / VAT)")}
      </Card>

      <div className="flex justify-end">
        <Button onClick={save} disabled={saving} className="gap-2 gradient-primary text-primary-foreground">
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          Save invoice details
        </Button>
      </div>
    </div>
  );
}
