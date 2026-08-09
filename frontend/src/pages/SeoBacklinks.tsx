import { useState, useEffect, useCallback, useMemo } from "react";
import { apiClient } from "@/services/api";
import { useDomainStore } from "@/stores/domainStore";
import { useToast } from "@/hooks/use-toast";
import { Card, CardContent } from "@/components/ui/card";
import { MetricCard } from "@/components/MetricCard";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import {
  Loader2, Link2, ExternalLink, Download, RefreshCw, AlertTriangle,
  Search, ShieldAlert, Globe, TrendingUp, Info,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Types — mirror seo_rankings/serializers_backlinks.py
// ---------------------------------------------------------------------------

interface Snapshot {
  id: number;
  status: string;
  is_truncated: boolean;
  error_message: string;
  rank: number;
  backlinks: number;
  backlinks_spam_score: number;
  broken_backlinks: number;
  broken_pages: number;
  crawled_pages: number;
  internal_links_count: number;
  external_links_count: number;
  referring_domains: number;
  referring_domains_nofollow: number;
  referring_main_domains: number;
  referring_ips: number;
  referring_subnets: number;
  referring_pages: number;
  referring_pages_nofollow: number;
  first_seen: string | null;
  referring_links_tld: Record<string, number>;
  referring_links_types: Record<string, number>;
  referring_links_attributes: Record<string, number>;
  referring_links_platform_types: Record<string, number>;
  referring_links_semantic_locations: Record<string, number>;
  referring_links_countries: Record<string, number>;
  stored_backlinks: number;
  dofollow_backlinks: number;
  completed_at: string | null;
  next_refresh_allowed_at: string | null;
}

interface BacklinkRow {
  id: number;
  domain_from: string;
  url_from: string;
  url_to: string;
  anchor: string;
  item_type: string;
  dofollow: boolean;
  is_new: boolean;
  is_lost: boolean;
  is_broken: boolean;
  rank: number;
  domain_from_rank: number;
  backlink_spam_score: number;
  domain_from_country: string;
  first_seen: string | null;
  last_seen: string | null;
  page_from_title: string;
}

interface AnchorRow { id: number; anchor: string; backlinks: number; referring_domains: number; }
interface RefDomainRow { id: number; domain_name: string; rank: number; backlinks: number; backlinks_spam_score: number; country: string; }
interface PageRow { id: number; page_url: string; backlinks: number; referring_domains: number; }

interface Overview {
  domain_id: number;
  domain_name: string;
  domain_url: string;
  is_fetching: boolean;
  snapshot: Snapshot | null;
  history: Array<{ point_date: string; backlinks: number; referring_domains: number }>;
  top_anchors: AnchorRow[];
  top_referring_domains: RefDomainRow[];
  top_pages: PageRow[];
  can_refresh: boolean;
  next_refresh_allowed_at: string | null;
  last_error: string | null;
}

interface ListResponse {
  count: number;
  page: number;
  page_size: number;
  total_backlinks: number;
  is_truncated: boolean;
  results: BacklinkRow[];
}

const fmt = (n: number | undefined | null) => (n ?? 0).toLocaleString();

const fmtDate = (iso: string | null) =>
  iso ? new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" }) : "—";

/** While a fetch is in flight the page polls; this is the gap between polls.
 *  A capped pull is ~10 sequential DataForSEO calls, so seconds, not minutes. */
const POLL_MS = 4000;

/** Spam score is 0-100 and only meaningful at the top end. Returned as a theme
 *  colour name so it can drive MetricCard's icon tint, which is how severity is
 *  signalled on every other metric surface. */
const spamTone = (score: number) =>
  score >= 60 ? "destructive" : score >= 30 ? "warning" : "primary";

/** Table cells still need the raw class rather than a colour name. */
const spamTextTone = (score: number) =>
  score >= 60 ? "text-destructive" : score >= 30 ? "text-warning" : "text-muted-foreground";

/** Breakdown dicts come back already aggregated from DataForSEO's summary
 *  call, so these bars cost nothing extra to render. */
const Breakdown = ({ title, data, limit = 6 }: {
  title: string; data: Record<string, number>; limit?: number;
}) => {
  const rows = useMemo(() => {
    const entries = Object.entries(data || {})
      .filter(([k]) => k !== "")
      .sort((a, b) => b[1] - a[1])
      .slice(0, limit);
    const max = entries.length ? entries[0][1] : 1;
    return entries.map(([k, v]) => ({ key: k, value: v, pct: max ? (v / max) * 100 : 0 }));
  }, [data, limit]);

  if (!rows.length) return null;

  return (
    <Card className="border border-border">
      <CardContent className="p-4">
        <p className="text-sm font-semibold mb-3">{title}</p>
        <div className="space-y-2.5">
          {rows.map((r) => (
            <div key={r.key}>
              <div className="flex justify-between text-xs mb-1 gap-2">
                <span className="truncate text-muted-foreground" title={r.key}>{r.key}</span>
                <span className="font-medium flex-shrink-0">{fmt(r.value)}</span>
              </div>
              <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                <div className="h-full rounded-full gradient-primary" style={{ width: `${Math.max(r.pct, 2)}%` }} />
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

export default function SeoBacklinks() {
  const { toast } = useToast();
  const { selectedDomain } = useDomainStore();
  const activeDomainId = selectedDomain ? String(selectedDomain.id) : "";

  const [overview, setOverview] = useState<Overview | null>(null);
  const [list, setList] = useState<ListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [listLoading, setListLoading] = useState(false);
  const [starting, setStarting] = useState(false);
  const [exporting, setExporting] = useState(false);

  // The monthly lock. Held separately from `overview` because it is also set
  // by a 429 on the refresh button, before any reload has happened.
  const [lockedUntil, setLockedUntil] = useState<string | null>(null);

  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [linkType, setLinkType] = useState("all");
  const [sort, setSort] = useState("rank");
  const [direction, setDirection] = useState("desc");

  const snapshot = overview?.snapshot ?? null;
  const isFetching = overview?.is_fetching ?? false;

  const loadOverview = useCallback(async () => {
    if (!activeDomainId) { setOverview(null); return; }
    try {
      const data = (await apiClient.getSeoBacklinks(activeDomainId)) as Overview;
      setOverview(data);
      setLockedUntil(data.can_refresh ? null : data.next_refresh_allowed_at);
      return data;
    } catch (err: any) {
      toast({
        title: "Could not load backlinks",
        description: err?.message || "Please try again.",
        variant: "destructive",
      });
      setOverview(null);
    }
  }, [activeDomainId, toast]);

  const loadList = useCallback(async () => {
    if (!activeDomainId) { setList(null); return; }
    setListLoading(true);
    try {
      setList((await apiClient.getSeoBacklinkList({
        domain_id: activeDomainId,
        page, search: debouncedSearch, link_type: linkType, sort, direction,
      })) as ListResponse);
    } catch (err: any) {
      toast({ title: "Could not load the backlink table", variant: "destructive" });
    } finally {
      setListLoading(false);
    }
  }, [activeDomainId, page, debouncedSearch, linkType, sort, direction, toast]);

  // Initial load per domain.
  useEffect(() => {
    setLoading(true);
    loadOverview().finally(() => setLoading(false));
  }, [loadOverview]);

  useEffect(() => {
    if (snapshot) loadList();
  }, [snapshot?.id, loadList]); // eslint-disable-line react-hooks/exhaustive-deps

  // Search debounce — the table filters server-side.
  useEffect(() => {
    const t = setTimeout(() => { setDebouncedSearch(search); setPage(1); }, 350);
    return () => clearTimeout(t);
  }, [search]);

  // Poll only while a pull is actually running.
  useEffect(() => {
    if (!isFetching) return;
    const t = setInterval(() => { loadOverview(); }, POLL_MS);
    return () => clearInterval(t);
  }, [isFetching, loadOverview]);

  const handleFetch = async () => {
    if (!activeDomainId) return;
    setStarting(true);
    try {
      await apiClient.fetchSeoBacklinks(activeDomainId);
      toast({
        title: "Fetching backlinks",
        description: "This takes a moment — the page updates when it finishes.",
      });
      await loadOverview();
    } catch (err: any) {
      // 429 is the monthly guard, not a failure. The backend sends the exact
      // date back so the alert never has to compute it.
      if (err?.status === 429) {
        const until = err?.data?.next_refresh_allowed_at ?? null;
        setLockedUntil(until);
        toast({
          title: "Already refreshed this month",
          description: `Backlinks can be refreshed once a month. Next refresh on ${fmtDate(until)}.`,
        });
      } else if (err?.status === 409) {
        toast({ title: "A fetch is already running for this project." });
        await loadOverview();
      } else {
        toast({
          title: "Could not start the fetch",
          description: err?.message || "Please try again.",
          variant: "destructive",
        });
      }
    } finally {
      setStarting(false);
    }
  };

  const handleExport = async () => {
    if (!activeDomainId) return;
    setExporting(true);
    try {
      const blob = await apiClient.exportSeoBacklinksCsv(activeDomainId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.setAttribute("download", `backlinks-${overview?.domain_name || "project"}.csv`);
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      toast({ title: "Export failed", variant: "destructive" });
    } finally {
      setExporting(false);
    }
  };

  const toggleSort = (field: string) => {
    if (sort === field) setDirection(direction === "desc" ? "asc" : "desc");
    else { setSort(field); setDirection("desc"); }
    setPage(1);
  };

  const totalPages = list ? Math.max(1, Math.ceil(list.count / list.page_size)) : 1;

  const header = (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 className="text-4xl font-bold tracking-tight">Backlinks</h1>
        <p className="text-muted-foreground mt-2">
          Who links to {overview?.domain_name || "this project"}, and how strong those links are
        </p>
      </div>
      {snapshot && (
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleExport} disabled={exporting}>
            {exporting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Download className="h-4 w-4 mr-2" />}
            Export
          </Button>
          <Button
            size="sm"
            onClick={handleFetch}
            disabled={starting || isFetching || !!lockedUntil}
            title={lockedUntil ? `Next refresh available on ${fmtDate(lockedUntil)}` : undefined}
          >
            {starting || isFetching
              ? <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              : <RefreshCw className="h-4 w-4 mr-2" />}
            Refresh
          </Button>
        </div>
      )}
    </div>
  );

  if (!activeDomainId) {
    return (
      <div className="p-8 space-y-8 bg-background animate-fade-in">
        {header}
        <div className="py-32 text-center text-muted-foreground">
          Select a project to see its backlink profile.
        </div>
      </div>
    );
  }

  if (loading && !overview) {
    return (
      <div className="p-8 space-y-8 bg-background animate-fade-in">
        {header}
        <div className="flex flex-col items-center justify-center py-32">
          <Loader2 className="h-10 w-10 animate-spin text-primary mb-4" />
          <span className="text-muted-foreground text-sm">Loading backlink profile…</span>
        </div>
      </div>
    );
  }

  // A pull in flight — the same view whether it was just started or was
  // already running when the page opened.
  if (isFetching) {
    return (
      <div className="p-8 space-y-8 bg-background animate-fade-in">
        {header}
        <Card className="border border-border">
          <CardContent className="flex flex-col items-center justify-center py-32 gap-3">
            <Loader2 className="h-10 w-10 animate-spin text-primary" />
            <h3 className="text-lg font-semibold">Pulling backlinks from DataForSEO</h3>
            <p className="text-sm text-muted-foreground max-w-md text-center">
              Fetching the profile summary, the referring domains, the anchor texts and the link
              list. This usually takes under a minute — the page updates on its own.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Never fetched.
  if (!snapshot) {
    return (
      <div className="p-8 space-y-8 bg-background animate-fade-in">
        {header}
        {overview?.last_error && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>The last fetch failed</AlertTitle>
            <AlertDescription>{overview.last_error}</AlertDescription>
          </Alert>
        )}
        <Card className="border border-border">
          <CardContent className="flex flex-col items-center justify-center text-center py-24 gap-4">
            <div className="rounded-full bg-muted/50 p-3">
              <Link2 className="h-6 w-6 text-muted-foreground" />
            </div>
            <div>
              <h3 className="text-lg font-semibold">No backlink data yet</h3>
              <p className="text-sm text-muted-foreground max-w-md mt-1">
                Backlinks are not tracked automatically. Pull the profile for this project when
                you need it — it can then be refreshed once a month.
              </p>
            </div>
            <Button onClick={handleFetch} disabled={starting}>
              {starting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Link2 className="h-4 w-4 mr-2" />}
              Fetch backlinks
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6 bg-background animate-fade-in">
      {header}

      <p className="text-sm text-muted-foreground">
        Last fetched {fmtDate(snapshot.completed_at)}
        {snapshot.first_seen && <> · first link seen {fmtDate(snapshot.first_seen)}</>}
      </p>

      {lockedUntil && (
        <Alert>
          <Info className="h-4 w-4" />
          <AlertTitle>Refreshed for this month</AlertTitle>
          <AlertDescription>
            Backlink data can be refreshed once a month. You can refresh this project again on{" "}
            <span className="font-semibold text-foreground">{fmtDate(lockedUntil)}</span>.
          </AlertDescription>
        </Alert>
      )}

      {snapshot.is_truncated ? (
        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Showing the strongest links</AlertTitle>
          <AlertDescription>
            This project has {fmt(snapshot.backlinks)} backlinks. The table below holds the{" "}
            {fmt(snapshot.stored_backlinks)} highest-ranked of them — the totals and breakdowns on
            this page still reflect the complete profile.
          </AlertDescription>
        </Alert>
      ) : snapshot.stored_backlinks < snapshot.backlinks ? (
        /* Not a cap — DataForSEO's profile total counts links it will not list
           individually, so these two numbers legitimately differ. Said plainly
           here because otherwise the tile and the table appear to contradict
           each other. */
        <Alert>
          <Info className="h-4 w-4" />
          <AlertTitle>Not every backlink can be listed individually</AlertTitle>
          <AlertDescription>
            The profile totals {fmt(snapshot.backlinks)} backlinks, of which{" "}
            {fmt(snapshot.stored_backlinks)} are available as individual records. The rest are
            counted in the totals and breakdowns above but cannot be itemised.
          </AlertDescription>
        </Alert>
      ) : null}

      {/* Headline metrics — the shared MetricCard, as on the dashboard. */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-6">
        <MetricCard
          title="Domain rank"
          value={fmt(snapshot.rank)}
          icon={<TrendingUp />}
          tooltip="DataForSEO's authority score for the whole domain, from 0 to 1000. It reflects the strength of everything linking to you, and moves slowly."
        />
        <MetricCard
          title="Backlinks"
          value={fmt(snapshot.backlinks)}
          icon={<Link2 />}
          tooltip="Every inbound link found across the profile, including several from the same site."
        />
        <MetricCard
          title="Referring domains"
          value={fmt(snapshot.referring_main_domains)}
          icon={<Globe />}
          tooltip="How many distinct websites link to you. Usually a better measure of reach than the raw backlink count."
        />
        <MetricCard
          title="Spam score"
          value={`${snapshot.backlinks_spam_score}%`}
          icon={<ShieldAlert />}
          iconColor={spamTone(snapshot.backlinks_spam_score)}
          tooltip="How much of the profile comes from low-quality sources, from 0 to 100. Only worth acting on at the high end."
        />
        <MetricCard
          title="Broken backlinks"
          value={fmt(snapshot.broken_backlinks)}
          icon={<AlertTriangle />}
          iconColor={snapshot.broken_backlinks > 0 ? "warning" : "primary"}
          tooltip="Links pointing at a page that no longer loads. Each one is earned authority being thrown away, and is usually fixable with a redirect."
        />
        <MetricCard
          title="Referring IPs"
          value={fmt(snapshot.referring_ips)}
          icon={<Globe />}
          tooltip={`Distinct IP addresses sending links, across ${fmt(snapshot.referring_subnets)} subnets. Many links from one IP often mean one network rather than genuine independent coverage.`}
        />
      </div>

      {/* Breakdowns — all six come free with the summary call. */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        <Breakdown title="Top referring TLDs" data={snapshot.referring_links_tld} />
        <Breakdown title="Link types" data={snapshot.referring_links_types} />
        <Breakdown title="Link attributes" data={snapshot.referring_links_attributes} />
        <Breakdown title="Platform types" data={snapshot.referring_links_platform_types} />
        <Breakdown title="Placement on page" data={snapshot.referring_links_semantic_locations} />
        <Breakdown title="Countries" data={snapshot.referring_links_countries} />
      </div>

      {/* Top anchors and referring domains */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <Card className="border border-border overflow-hidden">
          <div className="px-4 py-2.5 bg-muted/30 border-b border-border">
            <p className="text-sm font-semibold">Top anchor texts</p>
          </div>
          <CardContent className="p-0 max-h-[320px] overflow-auto">
            <Table className="table-fixed">
              <TableHeader className="sticky top-0 z-10 bg-card shadow-[inset_0_-1px_0_hsl(var(--border))]">
                <TableRow className="bg-card hover:bg-card border-0">
                  <TableHead className="text-xs font-semibold py-2">ANCHOR</TableHead>
                  <TableHead className="text-xs font-semibold py-2 text-center w-24">LINKS</TableHead>
                  <TableHead className="text-xs font-semibold py-2 text-center w-24">DOMAINS</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {overview!.top_anchors.map((a) => (
                  <TableRow key={a.id} className="hover:bg-muted/30">
                    <TableCell className="py-2 text-sm truncate" title={a.anchor}>
                      {a.anchor || <span className="text-muted-foreground italic">(no anchor)</span>}
                    </TableCell>
                    <TableCell className="py-2 text-sm text-center">{fmt(a.backlinks)}</TableCell>
                    <TableCell className="py-2 text-sm text-center">{fmt(a.referring_domains)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card className="border border-border overflow-hidden">
          <div className="px-4 py-2.5 bg-muted/30 border-b border-border">
            <p className="text-sm font-semibold">Top referring domains</p>
          </div>
          <CardContent className="p-0 max-h-[320px] overflow-auto">
            <Table className="table-fixed">
              <TableHeader className="sticky top-0 z-10 bg-card shadow-[inset_0_-1px_0_hsl(var(--border))]">
                <TableRow className="bg-card hover:bg-card border-0">
                  <TableHead className="text-xs font-semibold py-2">DOMAIN</TableHead>
                  <TableHead className="text-xs font-semibold py-2 text-center w-20">RANK</TableHead>
                  <TableHead className="text-xs font-semibold py-2 text-center w-24">LINKS</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {overview!.top_referring_domains.map((d) => (
                  <TableRow key={d.id} className="hover:bg-muted/30">
                    <TableCell className="py-2 text-sm truncate" title={d.domain_name}>
                      <a
                        href={`https://${d.domain_name}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="hover:text-primary hover:underline inline-flex items-center gap-1 min-w-0"
                      >
                        <span className="truncate">{d.domain_name}</span>
                        <ExternalLink className="h-2.5 w-2.5 flex-shrink-0" />
                      </a>
                    </TableCell>
                    <TableCell className="py-2 text-sm text-center">{fmt(d.rank)}</TableCell>
                    <TableCell className="py-2 text-sm text-center">{fmt(d.backlinks)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>

      {/* The backlink table */}
      <Card className="border border-border overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 bg-muted/30 border-b border-border">
          <div>
            <p className="text-sm font-semibold">All backlinks</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              {fmt(list?.count ?? 0)} shown
              {/* Always reconcile against the profile total — a bare "200" next
                  to a "275 backlinks" tile reads as a bug. */}
              {snapshot.stored_backlinks < snapshot.backlinks && (
                <> of {fmt(snapshot.backlinks)} total</>
              )}
              {" · "}{fmt(snapshot.dofollow_backlinks)} dofollow
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search domain, anchor or URL"
                className="h-8 pl-8 w-64 text-sm"
              />
            </div>
            <Select value={linkType} onValueChange={(v) => { setLinkType(v); setPage(1); }}>
              <SelectTrigger className="h-8 w-32 text-sm"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All links</SelectItem>
                <SelectItem value="dofollow">Dofollow</SelectItem>
                <SelectItem value="nofollow">Nofollow</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <CardContent className="p-0">
          {listLoading ? (
            <div className="flex items-center justify-center py-24">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
          ) : !list?.results.length ? (
            <div className="py-24 text-center text-sm text-muted-foreground">
              No backlinks match these filters.
            </div>
          ) : (
            <Table className="table-fixed">
              <TableHeader className="bg-card shadow-[inset_0_-1px_0_hsl(var(--border))]">
                <TableRow className="bg-card hover:bg-card border-0">
                  <TableHead className="text-xs font-semibold py-2">SOURCE</TableHead>
                  <TableHead className="text-xs font-semibold py-2">ANCHOR</TableHead>
                  <TableHead className="text-xs font-semibold py-2">TARGET</TableHead>
                  <TableHead
                    className="text-xs font-semibold py-2 text-center w-24 cursor-pointer select-none whitespace-nowrap"
                    onClick={() => toggleSort("domain_from_rank")}
                  >
                    DR {sort === "domain_from_rank" && (direction === "desc" ? "↓" : "↑")}
                  </TableHead>
                  <TableHead
                    className="text-xs font-semibold py-2 text-center w-24 cursor-pointer select-none whitespace-nowrap"
                    onClick={() => toggleSort("backlink_spam_score")}
                  >
                    SPAM {sort === "backlink_spam_score" && (direction === "desc" ? "↓" : "↑")}
                  </TableHead>
                  <TableHead className="text-xs font-semibold py-2 text-center w-28">TYPE</TableHead>
                  <TableHead
                    className="text-xs font-semibold py-2 text-center w-28 cursor-pointer select-none whitespace-nowrap"
                    onClick={() => toggleSort("first_seen")}
                  >
                    FIRST SEEN {sort === "first_seen" && (direction === "desc" ? "↓" : "↑")}
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {list.results.map((r) => (
                  <TableRow key={r.id} className="hover:bg-muted/30">
                    <TableCell className="py-2">
                      <div className="min-w-0">
                        <a
                          href={r.url_from}
                          target="_blank"
                          rel="noopener noreferrer"
                          title={r.url_from}
                          className="font-medium text-sm truncate flex items-center gap-1 min-w-0 hover:text-primary hover:underline"
                        >
                          <span className="truncate">{r.domain_from}</span>
                          <ExternalLink className="h-2.5 w-2.5 flex-shrink-0" />
                        </a>
                        {r.page_from_title && (
                          <p className="text-[11px] text-muted-foreground truncate" title={r.page_from_title}>
                            {r.page_from_title}
                          </p>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="py-2 text-sm truncate" title={r.anchor}>
                      {r.anchor || <span className="text-muted-foreground italic">
                        {r.item_type === "image" ? "(image link)" : "(no anchor)"}
                      </span>}
                    </TableCell>
                    <TableCell className="py-2 text-sm truncate" title={r.url_to}>
                      <a
                        href={r.url_to}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-muted-foreground hover:text-primary hover:underline"
                      >
                        {r.url_to.replace(/^https?:\/\/[^/]+/, "") || "/"}
                      </a>
                    </TableCell>
                    <TableCell className="py-2 text-sm text-center">{fmt(r.domain_from_rank)}</TableCell>
                    <TableCell className={cn("py-2 text-sm text-center", spamTextTone(r.backlink_spam_score))}>
                      {r.backlink_spam_score}%
                    </TableCell>
                    <TableCell className="py-2 text-center">
                      <div className="flex flex-wrap gap-1 justify-center">
                        <Badge variant={r.dofollow ? "default" : "secondary"} className="text-[10px] px-1.5 py-0">
                          {r.dofollow ? "follow" : "nofollow"}
                        </Badge>
                        {r.is_new && <Badge variant="outline" className="text-[10px] px-1.5 py-0">new</Badge>}
                        {r.is_broken && (
                          <Badge variant="destructive" className="text-[10px] px-1.5 py-0">broken</Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="py-2 text-sm text-center text-muted-foreground whitespace-nowrap">
                      {fmtDate(r.first_seen)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>

        {list && list.count > list.page_size && (
          <div className="flex items-center justify-between px-4 py-2.5 border-t border-border">
            <p className="text-xs text-muted-foreground">
              Page {list.page} of {totalPages}
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline" size="sm"
                disabled={page <= 1 || listLoading}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <Button
                variant="outline" size="sm"
                disabled={page >= totalPages || listLoading}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
