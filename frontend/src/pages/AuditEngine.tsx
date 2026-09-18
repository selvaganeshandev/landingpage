/**
 * Audit Engine — run a URL through the GEO audit and work the results as a
 * lead list. Sits at the top of Overview; admin/super_admin only (the backend
 * enforces the same rule).
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Download, ExternalLink, Eye, Link2, Loader2, Mail, MoreHorizontal, Play, RefreshCw, Search, Trash2, Zap, Info,
} from "lucide-react";
import { apiClient } from "@/services/api";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { MetricCard } from "@/components/MetricCard";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { GeoBadge, StatusBadge, saveBlob, timeAgo } from "@/components/audits/AuditBits";
import { AUDIT_COUNTRIES, type AuditConfig, type AuditListResponse, type AuditListRow } from "@/types/audit";

const POLL_MS = 10_000;

const SOURCE_LABEL: Record<string, string> = { manual: "Manual", landing: "Landing page", api: "API" };

export default function AuditEngine() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user } = useAuth();

  const [config, setConfig] = useState<AuditConfig | null>(null);
  const [configError, setConfigError] = useState<string | null>(null);
  const [data, setData] = useState<AuditListResponse | null>(null);
  const [loading, setLoading] = useState(true);

  // Run form
  const [url, setUrl] = useState("");
  const [country, setCountry] = useState("in");
  const [starting, setStarting] = useState(false);

  // Filters
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [source, setSource] = useState("all");
  const [claimed, setClaimed] = useState("all");
  const [page, setPage] = useState(1);

  const [deleting, setDeleting] = useState<AuditListRow | null>(null);

  useEffect(() => {
    apiClient.getAuditConfig()
      .then(setConfig)
      .catch((e: Error) => setConfigError(e.message));
  }, []);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search.trim()), 300);
    return () => clearTimeout(t);
  }, [search]);

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      setData(await apiClient.getAudits({
        page,
        page_size: 25,
        search: debouncedSearch || undefined,
        source: source === "all" ? "" : (source as AuditListRow["source"]),
        claimed: claimed === "all" ? "" : (claimed as "true" | "false"),
        ordering: "-created_at",
      }));
    } catch (e) {
      if (!silent) toast({ title: "Could not load audits", description: (e as Error).message, variant: "destructive" });
    } finally {
      if (!silent) setLoading(false);
    }
  }, [page, debouncedSearch, source, claimed, toast]);

  useEffect(() => { load(); }, [load]);

  // Keep live rows moving without a manual refresh.
  const hasLive = useMemo(() => (data?.results || []).some((r) => r.status === "INIT" || r.status === "PROC"), [data]);
  useEffect(() => {
    if (!hasLive) return;
    const t = setInterval(() => load(true), POLL_MS);
    return () => clearInterval(t);
  }, [hasLive, load]);

  const handleRun = async (force = false) => {
    if (!url.trim()) return;
    setStarting(true);
    try {
      const res = await apiClient.createAudit({ url: url.trim(), country, force });
      if (res.reused) {
        toast({
          title: `An audit of ${res.host} already ran recently`,
          description: "Opening the existing one. Use “Run anyway” to spend on a fresh audit.",
        });
      } else {
        toast({ title: `Auditing ${res.host}`, description: "About three minutes. You can leave this page." });
      }
      setUrl("");
      navigate(`/audits/${res.id}`);
    } catch (e) {
      const err = e as Error & { status?: number };
      toast({
        title: err.status === 429 ? "Daily audit limit reached" : err.status === 503 ? "Audit engine unavailable" : "Could not start the audit",
        description: err.message,
        variant: "destructive",
      });
    } finally {
      setStarting(false);
    }
  };

  const copyLink = async (row: AuditListRow) => {
    const link = `${window.location.origin}/audit/${row.public_token}`;
    try {
      await navigator.clipboard.writeText(link);
      toast({ title: "Public link copied", description: link });
    } catch {
      toast({ title: "Public link", description: link });
    }
  };

  const handlePdf = async (row: AuditListRow) => {
    try {
      saveBlob(await apiClient.downloadAuditPdf(row.id), `promptmaxx-audit-${row.host}.pdf`);
    } catch (e) {
      toast({ title: "Could not download the PDF", description: (e as Error).message, variant: "destructive" });
    }
  };

  const handleRerun = async (row: AuditListRow) => {
    try {
      await apiClient.rerunAudit(row.id);
      toast({ title: `Re-running ${row.host}`, description: "It resumes from the stage that failed." });
      load(true);
    } catch (e) {
      toast({ title: "Could not re-run", description: (e as Error).message, variant: "destructive" });
    }
  };

  const handleClaim = async (row: AuditListRow) => {
    try {
      const res = await apiClient.claimAudit(row.id);
      toast({ title: `${res.domain.name} added as a project`, description: "Keywords are being generated in the background." });
      load(true);
      // The project switcher reads the global domain store; refresh it so the
      // new project shows up without a page reload.
      try {
        const { useDomainStore } = await import("@/stores/domainStore");
        await useDomainStore.getState().loadDomains();
      } catch { /* the list page does not depend on the project list */ }
    } catch (e) {
      toast({ title: "Could not convert to project", description: (e as Error).message, variant: "destructive" });
    }
  };

  const handleDelete = async () => {
    if (!deleting) return;
    try {
      await apiClient.deleteAudit(deleting.id);
      toast({ title: `Deleted the audit of ${deleting.host}` });
      setDeleting(null);
      load(true);
    } catch (e) {
      toast({ title: "Could not delete", description: (e as Error).message, variant: "destructive" });
    }
  };

  const rows = useMemo(() => data?.results || [], [data]);
  const stats = useMemo(() => {
    const done = rows.filter((r) => r.status === "DONE");
    const claimedRows = rows.filter((r) => r.is_claimed);
    const avg = done.length ? Math.round(done.reduce((s, r) => s + (r.geo_score ?? 0), 0) / done.length) : null;
    const opens = rows.reduce((s, r) => s + r.opens, 0);
    return { total: data?.count ?? 0, claimed: claimedRows.length, avg, opens };
  }, [rows, data]);

  const canManage = config?.can_manage ?? (user?.role === "admin" || user?.role === "super_admin");

  const header = (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 className="text-4xl font-bold tracking-tight">
          Audit Engine
        </h1>
        <p className="text-muted-foreground mt-2">
          A URL goes in. A GEO audit comes out — public, shareable, no login. Every audit here is a lead.
        </p>
      </div>
      <Button variant="outline" size="sm" onClick={() => load()} disabled={loading}>
        {loading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <RefreshCw className="h-4 w-4 mr-2" />}
        Refresh
      </Button>
    </div>
  );

  if (configError) {
    return (
      <div className="p-8 space-y-6 bg-background animate-fade-in">
        {header}
        <Alert variant="destructive">
          <AlertTitle>Audit Engine is not available for your account</AlertTitle>
          <AlertDescription>{configError}</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6 bg-background animate-fade-in">
      {header}

      {config && !config.enabled && (
        <Alert>
          <Info className="h-4 w-4" />
          <AlertTitle>The audit engine is switched off on this server</AlertTitle>
          <AlertDescription>
            Existing audits are still readable below. Set <code className="text-xs">AUDIT_ENGINE_ENABLED=True</code> on the backend and engine to run new ones.
          </AlertDescription>
        </Alert>
      )}

      {/* ---- run an audit ---- */}
      <Card className="border border-border">
        <CardContent className="p-5">
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex-1 min-w-[240px]">
              <label className="text-sm font-medium">Run an audit</label>
              <div className="relative mt-1.5">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") handleRun(); }}
                  placeholder="Enter your website, e.g. yourdomain.com"
                  className="pl-9"
                  disabled={!canManage || starting || config?.enabled === false}
                />
              </div>
            </div>
            <div className="w-44">
              <label className="text-sm font-medium">Market</label>
              <Select value={country} onValueChange={setCountry}>
                <SelectTrigger className="mt-1.5"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {AUDIT_COUNTRIES.map((c) => <SelectItem key={c.code} value={c.code}>{c.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <Button onClick={() => handleRun()} disabled={!canManage || starting || !url.trim() || config?.enabled === false}>
              {starting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Zap className="h-4 w-4 mr-2" />}
              Generate audit
            </Button>
            <Button variant="ghost" onClick={() => handleRun(true)} disabled={!canManage || starting || !url.trim() || config?.enabled === false}
                    title="Skip the 24-hour repeat check and spend on a fresh audit">
              Run anyway
            </Button>
          </div>
          {config && (
            <p className="text-xs text-muted-foreground mt-3">
              GEO: {config.prompt_count} prompts × {config.engines.length} engine{config.engines.length === 1 ? "" : "s"} × 1 run
              {config.seo_enabled ? ` · SEO: ${config.keyword_count} keywords` : " · SEO: off"} · Output: public link for {config.public_ttl_days} days · ~3 min
            </p>
          )}
        </CardContent>
      </Card>

      {/* ---- metrics ---- */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard title="Audits" value={stats.total} icon={<Search />} tooltip="Every audit you can see, across all sources and states." />
        <MetricCard title="Became projects" value={stats.claimed} icon={<Zap />} tooltip="Audits on this page that were converted into a tracked project." />
        <MetricCard title="Avg GEO score" value={stats.avg ?? "—"} icon={<Play />} tooltip="Average GEO score of the finished audits on this page." />
        <MetricCard title="Report opens" value={stats.opens} icon={<Eye />} tooltip="How many times the public report links on this page were opened. Unclaimed and opened often = warm lead." />
      </div>

      {/* ---- filters ---- */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} placeholder="Search domain, brand or email" className="pl-9" />
        </div>
        <Select value={source} onValueChange={(v) => { setSource(v); setPage(1); }}>
          <SelectTrigger className="w-40"><SelectValue placeholder="Source" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All sources</SelectItem>
            <SelectItem value="landing">Landing page</SelectItem>
            <SelectItem value="manual">Manual</SelectItem>
            <SelectItem value="api">API</SelectItem>
          </SelectContent>
        </Select>
        <Select value={claimed} onValueChange={(v) => { setClaimed(v); setPage(1); }}>
          <SelectTrigger className="w-40"><SelectValue placeholder="Stage" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Any stage</SelectItem>
            <SelectItem value="false">Unclaimed</SelectItem>
            <SelectItem value="true">Became project</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* ---- leads table ---- */}
      <div className="rounded-lg border border-border overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Domain</TableHead>
              <TableHead>GEO</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Source</TableHead>
              <TableHead>Ran</TableHead>
              <TableHead className="text-right">Opens</TableHead>
              <TableHead>Emailed</TableHead>
              <TableHead>Claimed</TableHead>
              <TableHead className="w-10" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading && !data ? (
              <TableRow><TableCell colSpan={9} className="text-center py-10 text-muted-foreground"><Loader2 className="h-5 w-5 animate-spin inline" /></TableCell></TableRow>
            ) : rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center py-12 text-muted-foreground">
                  No audits yet. Enter a website above to run the first one.
                </TableCell>
              </TableRow>
            ) : rows.map((row) => (
              <TableRow key={row.id} className="cursor-pointer" onClick={() => navigate(`/audits/${row.id}`)}>
                <TableCell>
                  <p className="font-medium">{row.host}</p>
                  <p className="text-xs text-muted-foreground">
                    {[row.brand_name, row.industry, row.competitors.length ? `${row.competitors.length} competitors` : ""].filter(Boolean).join(" · ") || "profiling…"}
                    {row.requester_email && <> · {row.requester_email}</>}
                  </p>
                </TableCell>
                <TableCell><GeoBadge score={row.geo_score} stage={row.geo_stage} /></TableCell>
                <TableCell><StatusBadge status={row.status} stageLabel={row.stage_label} /></TableCell>
                <TableCell className="text-muted-foreground">{SOURCE_LABEL[row.source] || row.source}</TableCell>
                <TableCell className="text-muted-foreground" title={row.created_at}>{timeAgo(row.created_at)}</TableCell>
                <TableCell className="text-right tabular-nums">{row.opens}</TableCell>
                <TableCell>
                  {row.emailed_at ? (
                    <span
                      className="inline-flex items-center gap-1 text-xs text-emerald-600"
                      title={`Sent to ${(row.emailed_to || []).join(", ") || "the requester"}${row.email_count > 1 ? ` · ${row.email_count} times` : ""} · ${row.emailed_at}`}
                    >
                      <Mail className="h-3.5 w-3.5" />Sent {timeAgo(row.emailed_at)}
                      {row.email_count > 1 && <span className="text-muted-foreground">×{row.email_count}</span>}
                    </span>
                  ) : (
                    <span className="text-xs text-muted-foreground">Not sent</span>
                  )}
                </TableCell>
                <TableCell>
                  {row.is_claimed
                    ? <Badge variant="outline" className="text-emerald-600">Project → {row.claimed_domain_name}</Badge>
                    : <span className="text-muted-foreground">—</span>}
                </TableCell>
                <TableCell onClick={(e) => e.stopPropagation()}>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-8 w-8"><MoreHorizontal className="h-4 w-4" /></Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => navigate(`/audits/${row.id}`)}><Eye className="h-4 w-4 mr-2" />Open</DropdownMenuItem>
                      <DropdownMenuItem onClick={() => copyLink(row)} disabled={row.status !== "DONE"}><Link2 className="h-4 w-4 mr-2" />Copy public link</DropdownMenuItem>
                      <DropdownMenuItem onClick={() => window.open(`/audit/${row.public_token}`, "_blank")} disabled={row.status !== "DONE"}><ExternalLink className="h-4 w-4 mr-2" />Preview public report</DropdownMenuItem>
                      <DropdownMenuItem onClick={() => handlePdf(row)} disabled={row.status !== "DONE"}><Download className="h-4 w-4 mr-2" />Download PDF</DropdownMenuItem>
                      {canManage && (
                        <>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem onClick={() => handleRerun(row)} disabled={row.status !== "FAIL"}><RefreshCw className="h-4 w-4 mr-2" />Re-run</DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleClaim(row)} disabled={row.status !== "DONE" || row.is_claimed}><Zap className="h-4 w-4 mr-2" />Convert to project</DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem className="text-destructive" onClick={() => setDeleting(row)}><Trash2 className="h-4 w-4 mr-2" />Delete</DropdownMenuItem>
                        </>
                      )}
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {data && data.count > 25 && (
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>{data.count} audits</span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={!data.previous} onClick={() => setPage((p) => p - 1)}>Previous</Button>
            <Button variant="outline" size="sm" disabled={!data.next} onClick={() => setPage((p) => p + 1)}>Next</Button>
          </div>
        </div>
      )}

      <p className="text-xs text-muted-foreground">
        This list is your pipeline. Every visitor who ran an audit is here with their score, whether they came back, and whether they claimed it.
        Unclaimed + opened 5+ times = warm.
      </p>

      <AlertDialog open={!!deleting} onOpenChange={(o) => !o && setDeleting(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete the audit of {deleting?.host}?</AlertDialogTitle>
            <AlertDialogDescription>
              The public link stops working and the evidence rows are removed. A project created from it is not affected.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
