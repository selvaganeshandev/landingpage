/**
 * Runs — every execution, every engine, every repeat.
 *
 * The evidence behind every number in GEO monitoring: one row per prompt x
 * engine run, exactly as the engine recorded it. Read-only by design — this
 * page explains where the aggregates come from and lets a sceptical client
 * (or a support engineer) check them.
 *
 * Why confidence is on screen: AI answers are non-deterministic, so a single
 * run is an anecdote. The strip shows how many runs each variant averages and
 * how many variants are still too thin to quote.
 */
import { useEffect, useMemo, useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { PageLoader } from "@/components/PageLoader";
import { useDomainStore } from "@/stores/domainStore";
import { apiClient } from "@/services/api";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import { CONFIDENCE_TONE, type RunRow, type RunsListResponse, type RunsSummaryResponse } from "@/types/runs";
import { Activity, AlertTriangle, ChevronDown, ChevronRight, Download, Link2, RefreshCw, Search } from "lucide-react";

const PAGE_SIZE = 25;

const SENTIMENT_TONE: Record<string, string> = {
  positive: "text-emerald-600",
  negative: "text-destructive",
  neutral: "text-muted-foreground",
};

function fmtWhen(iso: string) {
  try {
    return new Date(iso).toLocaleString(undefined, { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso;
  }
}

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function Kpi({ label, value, sub, tone }: { label: string; value: React.ReactNode; sub?: React.ReactNode; tone?: string }) {
  return (
    <Card className="p-5 border border-border">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className={cn("mt-1 text-2xl font-bold tabular-nums", tone)}>{value}</p>
      {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
    </Card>
  );
}

/** The expanded row: what the engine actually saw in that one answer. */
function RunDetail({ run }: { run: RunRow }) {
  return (
    <TableRow className="bg-muted/30 hover:bg-muted/30">
      <TableCell colSpan={9} className="py-4">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">What the answer said</p>
            <p className="text-sm mt-1 leading-relaxed">{run.context_summary || "No summary recorded for this run."}</p>
          </div>
          <div className="space-y-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Cited URLs ({run.citations.length})</p>
              {run.citations.length ? (
                <ul className="mt-1 space-y-0.5">
                  {run.citations.slice(0, 8).map((u) => (
                    <li key={u} className="text-xs truncate" title={u}>
                      <Link2 className="inline h-3 w-3 mr-1 text-muted-foreground" />{u}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-muted-foreground mt-1">None — the engine answered without linking a source.</p>
              )}
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Competitors named</p>
              <p className="text-xs mt-1">{run.competitors.length ? run.competitors.join(" · ") : "None"}</p>
            </div>
          </div>
        </div>
      </TableCell>
    </TableRow>
  );
}

export default function Runs() {
  const { selectedDomain } = useDomainStore();
  const { toast } = useToast();

  const [summary, setSummary] = useState<RunsSummaryResponse | null>(null);
  const [data, setData] = useState<RunsListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [expanded, setExpanded] = useState<number | null>(null);

  const [days, setDays] = useState("30");
  const [platform, setPlatform] = useState("any");
  const [mention, setMention] = useState("any");
  const [group, setGroup] = useState("any");
  const [variance, setVariance] = useState(false);
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  const [page, setPage] = useState(0);

  useEffect(() => {
    const t = setTimeout(() => { setDebounced(search); setPage(0); }, 350);
    return () => clearTimeout(t);
  }, [search]);

  const filters = useMemo(() => ({
    domain_id: selectedDomain?.id,
    days: Number(days),
    platform,
    mention,
    group_id: group,
    variance: variance ? "only" : "any",
    search: debounced,
  }), [selectedDomain?.id, days, platform, mention, group, variance, debounced]);

  useEffect(() => {
    if (!selectedDomain?.id) return;
    let cancelled = false;
    setLoading(true);
    Promise.all([
      apiClient.getRunsSummary(filters),
      apiClient.getRuns({ ...filters, limit: PAGE_SIZE, offset: page * PAGE_SIZE }),
    ])
      .then(([s, rows]) => {
        if (cancelled) return;
        setSummary(s);
        setData(rows);
      })
      .catch((e) => {
        if (cancelled) return;
        toast({ title: "Could not load runs", description: (e as Error).message, variant: "destructive" });
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [filters, page, selectedDomain?.id, toast]);

  const exportCsv = async () => {
    if (!selectedDomain?.id) return;
    setExporting(true);
    try {
      saveBlob(await apiClient.downloadRunsCsv(filters), `promptmaxx-runs-${selectedDomain.name}.csv`);
    } catch (e) {
      toast({ title: "Could not export", description: (e as Error).message, variant: "destructive" });
    } finally {
      setExporting(false);
    }
  };

  if (!selectedDomain) {
    return (
      <div className="p-8">
        <h1 className="text-4xl font-bold tracking-tight">Runs</h1>
        <p className="text-muted-foreground mt-2">Select a project to see its run ledger.</p>
      </div>
    );
  }

  if (loading && !data) return <PageLoader />;

  const runs = data?.runs || [];
  const total = data?.total_count || 0;
  const lastPage = Math.max(0, Math.ceil(total / PAGE_SIZE) - 1);
  const platforms = summary?.by_platform.map((p) => p.platform) || [];

  return (
    <div className="p-8 space-y-6 bg-background animate-fade-in">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-4xl font-bold tracking-tight">Runs</h1>
          <p className="text-muted-foreground mt-2">
            Every execution, every engine, every repeat — the evidence behind every number in {selectedDomain.name}.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setPage(0)} disabled={loading}>
            <RefreshCw className={cn("h-4 w-4 mr-2", loading && "animate-spin")} />Refresh
          </Button>
          <Button variant="outline" size="sm" onClick={exportCsv} disabled={exporting || !total}>
            <Download className="h-4 w-4 mr-2" />{exporting ? "Exporting…" : "Export CSV"}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Kpi label="Total runs" value={(summary?.total_runs ?? 0).toLocaleString()}
             sub={`across ${summary?.variants ?? 0} prompts · ${summary?.engines ?? 0} engine${summary?.engines === 1 ? "" : "s"}`} />
        <Kpi label="Avg runs per prompt" value={summary?.avg_runs_per_variant ?? 0}
             tone={CONFIDENCE_TONE[summary?.confidence.level || "none"]}
             sub={`${summary?.confidence.marker || ""} ${summary?.confidence.label || ""}`} />
        <Kpi label="Mention rate" value={`${summary?.mention_rate ?? 0}%`}
             sub={`${(summary?.mentioned_runs ?? 0).toLocaleString()} of ${(summary?.total_runs ?? 0).toLocaleString()} runs named you`} />
        <Kpi label="Citation rate" value={`${summary?.citation_rate ?? 0}%`}
             sub={summary?.avg_position ? `avg position ${summary.avg_position} when named` : "runs that linked your site"} />
      </div>

      {(summary?.low_confidence_variants ?? 0) > 0 && (
        <Card className="p-4 border border-amber-500/30 bg-amber-500/5">
          <p className="text-sm">
            <b>{summary?.low_confidence_variants} prompts have fewer than 6 runs.</b>{" "}
            <span className="text-muted-foreground">
              AI answers vary between runs, so rates built on a handful of answers are directional. Run those prompts more often to firm them up.
            </span>
          </p>
        </Card>
      )}

      {(summary?.unstable_variants ?? 0) > 0 && (
        <Card className="p-4 border border-border">
          <p className="text-sm">
            <b>{summary?.unstable_variants} questions got different answers across repeats.</b>{" "}
            <span className="text-muted-foreground">
              The engine named you on some runs of the same question and not on others — use “Variance only” to read just those.
            </span>
          </p>
        </Card>
      )}

      {summary && summary.by_platform.length > 0 && (
        <Card className="p-5 border border-border">
          <p className="text-sm font-semibold mb-3">Runs by engine</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {summary.by_platform.map((p) => (
              <div key={p.platform} className="rounded-lg border border-border p-3">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-sm font-medium truncate" title={p.platform}>{p.platform}</span>
                  <span className="text-xs text-muted-foreground tabular-nums">{p.runs.toLocaleString()} runs</span>
                </div>
                <p className="mt-1 text-lg font-bold tabular-nums">{p.mention_rate}%</p>
                <p className="text-xs text-muted-foreground">named you · {p.cited} cited · {p.variants} prompts</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[240px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input className="pl-9" placeholder="Search the prompt text" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <Select value={days} onValueChange={(v) => { setDays(v); setPage(0); }}>
          <SelectTrigger className="w-[150px]"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="7">Last 7 days</SelectItem>
            <SelectItem value="30">Last 30 days</SelectItem>
            <SelectItem value="90">Last 90 days</SelectItem>
            <SelectItem value="365">Last 12 months</SelectItem>
          </SelectContent>
        </Select>
        <Select value={platform} onValueChange={(v) => { setPlatform(v); setPage(0); }}>
          <SelectTrigger className="w-[160px]"><SelectValue placeholder="All engines" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="any">All engines</SelectItem>
            {platforms.map((p) => <SelectItem key={p} value={p}>{p}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={group} onValueChange={(v) => { setGroup(v); setPage(0); }}>
          <SelectTrigger className="w-[170px]"><SelectValue placeholder="All groups" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="any">All groups</SelectItem>
            {(summary?.groups || []).map((g) => (
              <SelectItem key={g.id} value={String(g.id)}>{g.label || `Group ${g.id}`}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={mention} onValueChange={(v) => { setMention(v); setPage(0); }}>
          <SelectTrigger className="w-[160px]"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="any">Mention: any</SelectItem>
            <SelectItem value="yes">Mentioned you</SelectItem>
            <SelectItem value="no">Not mentioned</SelectItem>
          </SelectContent>
        </Select>
        <Button
          variant={variance ? "default" : "outline"}
          size="sm"
          onClick={() => { setVariance((v) => !v); setPage(0); }}
          title="Questions the engines answered inconsistently across repeats — where an average hides a coin flip"
        >
          <AlertTriangle className="h-4 w-4 mr-2" />Variance only
        </Button>
        <span className="text-xs text-muted-foreground">{total.toLocaleString()} runs</span>
      </div>

      <Card className="border border-border overflow-hidden">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-8" />
                <TableHead>When</TableHead>
                <TableHead>Prompt</TableHead>
                <TableHead className="whitespace-nowrap">Group</TableHead>
                <TableHead>Engine</TableHead>
                <TableHead className="whitespace-nowrap">Run</TableHead>
                <TableHead>Mention</TableHead>
                <TableHead className="text-right whitespace-nowrap">Position</TableHead>
                <TableHead className="text-right whitespace-nowrap">Cited</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {runs.length === 0 && (
                <TableRow>
                  <TableCell colSpan={9} className="text-center py-12 text-muted-foreground">
                    <Activity className="h-6 w-6 mx-auto mb-2 opacity-40" />
                    No runs in this window. Tracking writes a row here every time a prompt is asked.
                  </TableCell>
                </TableRow>
              )}
              {runs.map((run) => (
                <>
                  <TableRow key={run.id} className="cursor-pointer" onClick={() => setExpanded(expanded === run.id ? null : run.id)}>
                    <TableCell className="text-muted-foreground">
                      {expanded === run.id ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground whitespace-nowrap">{fmtWhen(run.tracked_at)}</TableCell>
                    <TableCell className="text-sm max-w-[340px]">
                      <span className="block truncate" title={run.prompt}>{run.prompt}</span>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground max-w-[140px] truncate" title={run.group}>{run.group || "—"}</TableCell>
                    <TableCell className="text-sm">{run.platform}</TableCell>
                    <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                      {run.run_number ? `${run.run_number}${run.runs_for_prompt ? ` of ${run.runs_for_prompt}` : ""}` : "—"}
                    </TableCell>
                    <TableCell>
                      {run.is_mention
                        ? <Badge variant="outline" className="text-emerald-600 border-emerald-500/30">mentioned</Badge>
                        : <span className="text-xs text-muted-foreground">not named</span>}
                      {run.is_mention && run.sentiment_category && (
                        <span className={cn("ml-2 text-[11px]", SENTIMENT_TONE[run.sentiment_category] || "")}>{run.sentiment_category}</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-sm">{run.is_mention && run.position ? run.position : "—"}</TableCell>
                    <TableCell className="text-right tabular-nums text-sm">{run.total_citations || "—"}</TableCell>
                  </TableRow>
                  {expanded === run.id && <RunDetail key={`${run.id}-detail`} run={run} />}
                </>
              ))}
            </TableBody>
          </Table>
        </div>
      </Card>

      {total > PAGE_SIZE && (
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">
            Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} of {total.toLocaleString()}
          </span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page === 0 || loading} onClick={() => setPage((p) => Math.max(0, p - 1))}>Previous</Button>
            <Button variant="outline" size="sm" disabled={page >= lastPage || loading} onClick={() => setPage((p) => p + 1)}>Next</Button>
          </div>
        </div>
      )}
    </div>
  );
}
