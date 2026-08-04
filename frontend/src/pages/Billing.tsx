import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Download, ExternalLink, Loader2, AlertTriangle, CreditCard, Check, FileText } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/services/api";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

/**
 * Billing — per-project keyword charges, split into region tables.
 *
 * Price is computed server-side (seo_rankings/services/billing.py) and arrives
 * pre-computed; this component sums nothing and derives no prices. The totals
 * shown in each header come from the API and cover the whole region, not the
 * visible rows.
 */

interface BillingProject {
  domain_id: number;
  name: string;
  url: string;
  country: string;
  used_keywords: number;
  keyword_limit: number;
  price: number;
  currency: string;
  over_top_slab: boolean;
  organisation: string;
}

interface BillingRegion {
  key: string;
  label: string;
  projects: BillingProject[];
  total_projects: number;
  billable_projects: number;
  total_price: number;
  currency: string;
}

interface RatePlan {
  keyword_limit: number;
  price: number;
  tracking: string;
  ga_gsc: boolean;
  all_features: boolean;
  manual_refresh: number;
  content_gap: number | null;
}

interface BillingResponse {
  currency: string;
  rate_card: RatePlan[];
  regions: BillingRegion[];
  grand_total: number;
  total_projects: number;
  can_view_all_orgs: boolean;
  can_export: boolean;
  organisations: { id: number; name: string }[];
  selected_organisation: string;
  invoice_months: string[];
}

const inr = (n: number) => n.toLocaleString("en-IN");

/** "2026-07" -> "July 2026". Parsed as a plain Y/M so the label cannot shift a
 *  month across a timezone boundary the way new Date("2026-07") can. */
const monthLabel = (m: string) => {
  const [y, mo] = (m || "").split("-").map(Number);
  if (!y || !mo) return m;
  return new Date(y, mo - 1, 1).toLocaleDateString("en-US", { month: "long", year: "numeric" });
};

/** Strip scheme and www so a stored URL reads as a hostname. */
const hostOf = (url: string) =>
  (url || "").replace(/^https?:\/\//i, "").replace(/^www\./i, "").replace(/[/?#].*$/, "");

const yes = <Check className="h-3.5 w-3.5 text-emerald-600 mx-auto" />;

/** Feature rows of the rate card, in the order the published card lists them. */
const RATE_ROWS: { label: string; render: (t: RatePlan) => React.ReactNode }[] = [
  { label: "Tracking frequency", render: (t) => t.tracking },
  { label: "GA & GSC reports", render: (t) => (t.ga_gsc ? yes : "—") },
  { label: "All features (except competitor)", render: (t) => (t.all_features ? yes : "—") },
  { label: "Manual refresh", render: (t) => `${inr(t.manual_refresh)}/mo` },
  {
    label: "Content gap metrics",
    render: (t) => (t.content_gap == null
      ? <span className="text-muted-foreground">—</span>
      : inr(t.content_gap)),
  },
];

function RegionTable({ region, showOrg }: { region: BillingRegion; showOrg: boolean }) {
  return (
    <Card className="border border-border overflow-hidden">
      {/* The header renders even when the region is empty, so an unused region
          reads "0 projects / 0 INR" rather than vanishing from the page. */}
      <div className="flex flex-wrap items-start justify-between gap-3 px-4 py-2.5 bg-muted/30 border-b border-border">
        <div>
          <p className="text-sm">
            <span className="text-muted-foreground">Project Region: </span>
            <span className="font-semibold">{region.label}</span>
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">
            Total Projects: <span className="font-medium text-foreground">{region.total_projects}</span>
            {region.billable_projects !== region.total_projects && (
              <span> · {region.billable_projects} billable</span>
            )}
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs text-muted-foreground">Total Price (all rows)</p>
          <p className="text-lg font-bold text-primary">
            {inr(region.total_price)} <span className="text-sm">{region.currency}</span>
          </p>
        </div>
      </div>

      {/* Capped height with the header pinned — 55 projects would otherwise
          make the card metres tall and push the second region table far below
          the fold. Roughly six rows visible, then scroll. */}
      <CardContent className="p-0 max-h-[320px] overflow-auto">
        {region.projects.length === 0 ? (
          <div className="py-16 text-center text-sm text-muted-foreground">
            No billable projects in this region
          </div>
        ) : (
          <Table className="table-fixed">
            {/* Opaque, not bg-muted/20 — a translucent sticky header lets the
                rows scroll visibly through it. */}
            <TableHeader className="sticky top-0 z-10 bg-card shadow-[inset_0_-1px_0_hsl(var(--border))]">
              <TableRow className="bg-card hover:bg-card border-0">
                <TableHead className="text-xs font-semibold py-2 w-10 text-center">#</TableHead>
                <TableHead className="text-xs font-semibold py-2">PROJECT</TableHead>
                <TableHead className="text-center text-xs font-semibold py-2 w-28 whitespace-nowrap">USED KEYWORD</TableHead>
                <TableHead className="text-center text-xs font-semibold py-2 w-28 whitespace-nowrap">KEYWORD LIMIT</TableHead>
                <TableHead className="text-center text-xs font-semibold py-2 w-28 whitespace-nowrap">PRICE</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {region.projects.map((p, i) => (
                <TableRow
                  key={p.domain_id}
                  // Muted: no keywords tracked, so nothing is charged. Shown
                  // rather than hidden so the project is visibly present.
                  className={cn("hover:bg-muted/30", p.price === 0 && "text-muted-foreground")}
                >
                  <TableCell className="text-center py-2 text-sm text-muted-foreground">{i + 1}</TableCell>
                  <TableCell className="py-2">
                    <div className="min-w-0">
                      <p className="font-medium text-sm truncate" title={p.name}>{p.name}</p>
                      {showOrg && p.organisation && (
                        <p className="text-[11px] text-muted-foreground truncate" title={p.organisation}>
                          {p.organisation}
                        </p>
                      )}
                      <a
                        href={p.url?.startsWith("http") ? p.url : `https://${p.url}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        title={p.url}
                        className="text-xs text-muted-foreground flex items-center gap-1 min-w-0 hover:text-primary hover:underline"
                      >
                        <span className="truncate">{hostOf(p.url)}</span>
                        <ExternalLink className="h-2.5 w-2.5 flex-shrink-0" />
                      </a>
                    </div>
                  </TableCell>
                  {/* Highlighted — the metric the charge is derived from. */}
                  <TableCell className="text-center py-2 bg-primary/5">
                    <span className="text-sm font-medium">{inr(p.used_keywords)}</span>
                    {p.over_top_slab && (
                      <span title="Above the largest published slab — charged at the top slab">
                        <AlertTriangle className="inline h-3 w-3 ml-1 text-amber-500" />
                      </span>
                    )}
                  </TableCell>
                  <TableCell className="text-center py-2 text-sm">
                    {p.keyword_limit > 0 ? inr(p.keyword_limit) : "—"}
                  </TableCell>
                  <TableCell className="text-center py-2 text-sm">
                    {inr(p.price)} <span className="font-bold">{p.currency}</span>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

export default function Billing() {
  const { toast } = useToast();
  const [data, setData] = useState<BillingResponse | null>(null);
  const [loading, setLoading] = useState(true);
  // The spec's source app left a failed request stuck in a skeleton forever,
  // because the flag only cleared on success. Error is tracked separately.
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  // "all" | "<org id>". Ignored by the server for accounts without the
  // all-organisations grant, which are pinned to their own.
  // Empty until the first response tells us which organisation the server
  // resolved; sending "all" would only be coerced back to one anyway.
  const [org, setOrg] = useState<string>("");
  const [invoiceOpen, setInvoiceOpen] = useState(false);
  const [invoiceMonth, setInvoiceMonth] = useState<string>("");
  const [invoiceBusy, setInvoiceBusy] = useState(false);
  // Each region is invoiced separately — they are billed to different entities
  // — so the picker defaults to the first rather than a combined document.
  const [invoiceRegion, setInvoiceRegion] = useState<string>("");

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        setError(null);
        const res = await apiClient.getBillingSummary(org) as BillingResponse;
        setData(res);
        // Newest month first, so [0] is the current period.
        setInvoiceMonth((prev) => prev || res.invoice_months?.[0] || "");
        setInvoiceRegion((prev) => prev || res.regions?.[0]?.key || "");
        if (res.selected_organisation && res.selected_organisation !== "own") {
          setOrg((prev) => prev || res.selected_organisation);
        }
      } catch (e: any) {
        setError(e?.message || "Could not load billing data.");
      } finally {
        setLoading(false);
      }
    })();
  }, [org]);

  const handleInvoice = async () => {
    if (!invoiceMonth) return;
    setInvoiceBusy(true);
    try {
      await apiClient.downloadBillingInvoice(invoiceMonth, org, invoiceRegion);
      const label = data?.regions?.find((r) => r.key === invoiceRegion)?.label;
      toast({ title: `Invoice for ${monthLabel(invoiceMonth)} downloaded`,
              description: label ? `Region: ${label}` : undefined });
      setInvoiceOpen(false);
    } catch (e: any) {
      toast({ title: "Could not generate invoice", description: e?.message, variant: "destructive" });
    } finally {
      setInvoiceBusy(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      await apiClient.exportBilling(org);
      toast({ title: "Billing exported" });
    } catch (e: any) {
      toast({ title: "Export failed", description: e?.message, variant: "destructive" });
    } finally {
      setExporting(false);
    }
  };

  // Tiers that at least one billed project lands in, so the card ties back to
  // the tables above instead of being a static price list.
  const tiersInUse = new Set(
    (data?.regions ?? [])
      .flatMap((r) => r.projects)
      .filter((p) => p.price > 0)
      .map((p) => p.keyword_limit)
  );

  const header = (
    <div className="flex flex-wrap items-start justify-between gap-3 pb-4 border-b border-border/50">
      <div className="flex items-center gap-3">
        <div className="w-11 h-11 rounded-lg bg-primary/10 text-primary flex items-center justify-center flex-shrink-0">
          <CreditCard className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight font-inter">Billing</h1>
          <p className="text-muted-foreground mt-0.5 text-sm">
            Per-project charges based on tracked keywords
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        {/* Only rendered for accounts granted the consolidated view. */}
        {data?.can_view_all_orgs && (
          <Select value={org} onValueChange={setOrg}>
            <SelectTrigger className="h-9 w-[220px] text-sm">
              <SelectValue placeholder="Organization" />
            </SelectTrigger>
            <SelectContent>
              {/* No "all" option: billing figures are per account, and an
                  invoice must name one legal entity as the buyer. */}
              {(data?.organisations ?? []).map((o) => (
                <SelectItem key={o.id} value={String(o.id)}>{o.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
        <Button
          onClick={() => setInvoiceOpen(true)}
          disabled={loading || !!error || !(data?.invoice_months?.length)}
          className="gap-2 gradient-primary shadow-md shadow-primary/20 text-primary-foreground"
        >
          <FileText className="h-4 w-4" />
          Download Invoice
        </Button>
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="p-8 space-y-6 bg-background animate-fade-in">
        {header}
        <div className="flex items-center justify-center py-24">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 space-y-6 bg-background animate-fade-in">
        {header}
        <Card className="p-8 text-center border border-border">
          <AlertTriangle className="h-6 w-6 text-destructive mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">{error}</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-5 bg-background animate-fade-in">
      {header}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm text-muted-foreground">
            Charged per project on the keyword slab it falls into. Projects tracking
            no keywords are listed but not charged.
          </p>
          <p className="text-sm mt-1">
            <span className="text-muted-foreground">Grand total: </span>
            <span className="font-semibold">
              {inr(data?.grand_total ?? 0)} {data?.currency}
            </span>
            <span className="text-muted-foreground">
              {" "}across {(data?.regions ?? []).reduce((n, r) => n + r.billable_projects, 0)} billable
              of {data?.total_projects ?? 0} project(s)
            </span>
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {(data?.regions ?? []).map((region) => (
          <RegionTable key={region.key} region={region} showOrg={false} />
        ))}
      </div>

      {/* Rate card as a comparison matrix rather than a row of price chips —
          the plan differs on more than price, and the tiers a project actually
          lands in are highlighted so the charges above can be traced to it. */}
      {data?.rate_card?.length ? (
        <Card className="border border-border overflow-hidden">
          <div className="px-4 py-3 border-b border-border bg-muted/30">
            <p className="text-sm font-semibold">Rate card</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              A project pays the flat price of the smallest tier that fits its tracked
              keywords. Tiers in use by this account are highlighted.
            </p>
          </div>
          <CardContent className="p-0 overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/20 hover:bg-muted/20">
                  <TableHead className="text-xs font-semibold py-2.5 w-56 whitespace-nowrap">KEYWORDS</TableHead>
                  {data.rate_card.map((t) => (
                    <TableHead
                      key={t.keyword_limit}
                      className={cn(
                        "text-center text-xs font-semibold py-2.5 whitespace-nowrap",
                        tiersInUse.has(t.keyword_limit) && "bg-primary/10 text-primary"
                      )}
                    >
                      {inr(t.keyword_limit)} kwds
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {RATE_ROWS.map((row) => (
                  <TableRow key={row.label} className="hover:bg-muted/20">
                    <TableCell className="py-2.5 text-sm text-muted-foreground">{row.label}</TableCell>
                    {data.rate_card.map((t) => (
                      <TableCell
                        key={t.keyword_limit}
                        className={cn(
                          "text-center py-2.5 text-sm",
                          tiersInUse.has(t.keyword_limit) && "bg-primary/5"
                        )}
                      >
                        {row.render(t)}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
                <TableRow className="bg-muted/30 hover:bg-muted/30 border-t-2 border-border">
                  <TableCell className="py-3 text-sm font-semibold">Cost per project</TableCell>
                  {data.rate_card.map((t) => (
                    <TableCell
                      key={t.keyword_limit}
                      className={cn(
                        "text-center py-3 whitespace-nowrap",
                        tiersInUse.has(t.keyword_limit) && "bg-primary/10"
                      )}
                    >
                      <span className="text-sm font-bold">{inr(t.price)}</span>
                      <span className="text-xs font-semibold text-muted-foreground ml-1">{data.currency}</span>
                    </TableCell>
                  ))}
                </TableRow>
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ) : null}

      {/* Monthly invoice. Figures are rebuilt as of the chosen month's close,
          so an older period shows what was tracked then, not today's totals. */}
      <Dialog open={invoiceOpen} onOpenChange={setInvoiceOpen}>
        <DialogContent className="sm:max-w-[440px]">
          <DialogHeader>
            <DialogTitle>Generate invoice</DialogTitle>
            <DialogDescription>
              Pick a region and billing period. The invoice is raised against
              {" "}
              <span className="font-medium text-foreground">
                {(data?.organisations ?? []).find(
                  (o) => String(o.id) === org)?.name || "this organization"}
              </span>
              {" "}and is priced on the keywords tracked at the close of that month.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <label className="text-sm font-medium">Region</label>
              <Select value={invoiceRegion} onValueChange={setInvoiceRegion}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a region" />
                </SelectTrigger>
                <SelectContent>
                  {(data?.regions ?? []).map((r) => (
                    <SelectItem key={r.key} value={r.key}>
                      {r.label} ({r.billable_projects} billable)
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Billing period</label>
              <Select value={invoiceMonth} onValueChange={setInvoiceMonth}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a month" />
                </SelectTrigger>
                <SelectContent>
                  {(data?.invoice_months ?? []).map((m, i) => (
                    <SelectItem key={m} value={m}>
                      {monthLabel(m)}{i === 0 ? " (current)" : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setInvoiceOpen(false)} disabled={invoiceBusy}>
              Cancel
            </Button>
            <Button
              onClick={handleInvoice}
              disabled={invoiceBusy || !invoiceMonth || !invoiceRegion}
              className="gap-2 gradient-primary text-primary-foreground"
            >
              {invoiceBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
              Download PDF
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
