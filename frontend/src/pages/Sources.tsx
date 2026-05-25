import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/services/api";
import { useDomainStore } from "@/stores/domainStore";
import {
  Download,
  ExternalLink,
  Loader2,
  Search,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Filter,
  X,
  Link2,
  MessageSquare,
  TrendingUp,
  Smile,
  RefreshCw,
} from "lucide-react";
import { getFaviconUrl, handleFaviconError } from "@/utils/faviconHelper";

type SourceRow = {
  source_urls: string;
  prompt_text: string;
  model: string;
  avg_sentiment: number;
  avg_position: number;
  mentions: number;
  created: string;
};

const ROWS_PER_PAGE_OPTIONS = [10, 25, 50, 100];

// Color theme per AI model — keeps the table scannable when many platforms
// are in use. Unknown providers fall back to a neutral slate badge.
const MODEL_COLORS: Record<string, string> = {
  ChatGPT: "bg-emerald-50 text-emerald-700 border-emerald-200",
  Gemini: "bg-blue-50 text-blue-700 border-blue-200",
  Claude: "bg-violet-50 text-violet-700 border-violet-200",
  Perplexity: "bg-amber-50 text-amber-700 border-amber-200",
  Grok: "bg-rose-50 text-rose-700 border-rose-200",
  DeepSeek: "bg-cyan-50 text-cyan-700 border-cyan-200",
  AI: "bg-slate-50 text-slate-700 border-slate-200",
};

function modelChipClass(model: string): string {
  return MODEL_COLORS[model] || "bg-slate-50 text-slate-700 border-slate-200";
}

// Sentiment is stored 0..100 (the export scales -1..1 sentiment_score to that).
// >= 66 positive, 34..65 neutral, <= 33 negative.
function sentimentBucket(value: number): "positive" | "neutral" | "negative" {
  if (value >= 66) return "positive";
  if (value <= 33) return "negative";
  return "neutral";
}

function sentimentChipClass(value: number): string {
  const b = sentimentBucket(value);
  if (b === "positive") return "bg-emerald-50 text-emerald-700 border-emerald-200";
  if (b === "negative") return "bg-rose-50 text-rose-700 border-rose-200";
  return "bg-amber-50 text-amber-700 border-amber-200";
}

type SentimentFilter = "all" | "positive" | "neutral" | "negative";
type SortKey = "created_desc" | "mentions_desc" | "sentiment_desc" | "position_asc";

const Sources = () => {
  const { toast } = useToast();
  const { selectedDomain } = useDomainStore();
  const domainId = selectedDomain?.id;

  const [search, setSearch] = useState("");
  const [modelFilter, setModelFilter] = useState<string>("all");
  const [sentimentFilter, setSentimentFilter] = useState<SentimentFilter>("all");
  const [onlyWithSources, setOnlyWithSources] = useState<boolean>(false);
  const [onlyWithMentions, setOnlyWithMentions] = useState<boolean>(false);
  const [sortBy, setSortBy] = useState<SortKey>("created_desc");
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [exporting, setExporting] = useState(false);

  const { data, isLoading, isError, isFetching, refetch } = useQuery({
    queryKey: ["promptSourcesData", domainId],
    queryFn: async () => {
      const res = await apiClient.getPromptSourcesData(domainId!);
      return res as {
        domain_id: number;
        domain_name: string;
        columns: string[];
        rows: SourceRow[];
        total_rows: number;
      };
    },
    enabled: !!domainId,
  });

  const allRows: SourceRow[] = data?.rows || [];

  // Models present in the data — drives the Model dropdown options.
  const availableModels = useMemo(() => {
    const set = new Set<string>();
    for (const r of allRows) {
      if (r.model) set.add(r.model);
    }
    return Array.from(set).sort();
  }, [allRows]);

  // Apply all filters → then sort.
  const filteredRows = useMemo(() => {
    const q = search.trim().toLowerCase();
    let rows = allRows.filter((r) => {
      if (q) {
        const hit =
          r.prompt_text.toLowerCase().includes(q) ||
          r.source_urls.toLowerCase().includes(q) ||
          r.model.toLowerCase().includes(q);
        if (!hit) return false;
      }
      if (modelFilter !== "all" && r.model !== modelFilter) return false;
      if (sentimentFilter !== "all" && sentimentBucket(r.avg_sentiment) !== sentimentFilter) {
        return false;
      }
      if (onlyWithSources && (!r.source_urls || r.source_urls === "No sources available")) {
        return false;
      }
      if (onlyWithMentions && r.mentions <= 0) return false;
      return true;
    });

    rows = [...rows];
    if (sortBy === "mentions_desc") {
      rows.sort((a, b) => b.mentions - a.mentions);
    } else if (sortBy === "sentiment_desc") {
      rows.sort((a, b) => b.avg_sentiment - a.avg_sentiment);
    } else if (sortBy === "position_asc") {
      // Lower (closer to 1) = better. Treat 0 (unknown) as worst so it sinks.
      rows.sort((a, b) => {
        const av = a.avg_position > 0 ? a.avg_position : Number.POSITIVE_INFINITY;
        const bv = b.avg_position > 0 ? b.avg_position : Number.POSITIVE_INFINITY;
        return av - bv;
      });
    }
    // created_desc is backend default — no client sort needed.
    return rows;
  }, [allRows, search, modelFilter, sentimentFilter, onlyWithSources, onlyWithMentions, sortBy]);

  // Stats reflect the currently-filtered view so toggling a filter updates
  // the cards too — gives the user immediate feedback on what they sliced.
  const stats = useMemo(() => {
    const total = filteredRows.length;
    const withSources = filteredRows.filter(
      (r) => r.source_urls && r.source_urls !== "No sources available",
    ).length;
    const totalMentions = filteredRows.reduce((s, r) => s + (r.mentions || 0), 0);
    // Sentiment is meaningful only when the AI actually mentioned the brand.
    // Rows with mentions=0 stay at the DB default sentiment=0 → 50.0 after
    // scaling, which would drag the average toward neutral. Exclude them.
    const mentionedRows = filteredRows.filter((r) => r.mentions > 0);
    const sentimentSum = mentionedRows.reduce((s, r) => s + (r.avg_sentiment || 0), 0);
    const avgSentiment = mentionedRows.length > 0 ? sentimentSum / mentionedRows.length : 0;
    const hasSentiment = mentionedRows.length > 0;
    const activeModels = new Set(filteredRows.map((r) => r.model)).size;
    return { total, withSources, totalMentions, avgSentiment, hasSentiment, activeModels };
  }, [filteredRows]);

  const totalRows = filteredRows.length;
  const totalPages = Math.max(1, Math.ceil(totalRows / rowsPerPage));
  const pageRows = filteredRows.slice(page * rowsPerPage, (page + 1) * rowsPerPage);

  const activeFilterCount =
    (search.trim() ? 1 : 0) +
    (modelFilter !== "all" ? 1 : 0) +
    (sentimentFilter !== "all" ? 1 : 0) +
    (onlyWithSources ? 1 : 0) +
    (onlyWithMentions ? 1 : 0);

  const resetFilters = () => {
    setSearch("");
    setModelFilter("all");
    setSentimentFilter("all");
    setOnlyWithSources(false);
    setOnlyWithMentions(false);
    setSortBy("created_desc");
    setPage(0);
  };

  // Reset page when any filter changes (otherwise users land on an empty page).
  const onAnyFilterChange = () => setPage(0);

  const handleExport = async () => {
    if (!domainId) return;
    setExporting(true);
    try {
      await apiClient.exportPromptsReport({ domain_id: domainId });
      toast({ title: "Export started", description: "Your .xlsx download has begun." });
    } catch (err: any) {
      toast({
        title: "Export failed",
        description: err?.message || "Could not generate the export.",
        variant: "destructive",
      });
    } finally {
      setExporting(false);
    }
  };

  if (!domainId) {
    return (
      <div className="p-8">
        <h1 className="text-4xl font-bold tracking-tight">Sources</h1>
        <p className="text-muted-foreground mt-2">
          AI prompt data with source URLs, sentiment, position, and mentions per
          model.
        </p>
        <Card className="p-12 mt-8 text-center">
          <p className="text-muted-foreground">
            Please select a domain to view sources.
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
            <img
              src={getFaviconUrl(selectedDomain?.url || "", 64)}
              alt=""
              className="h-8 w-8 rounded"
              onError={(e) =>
                handleFaviconError(
                  e,
                  selectedDomain?.url || "",
                  selectedDomain?.name || "",
                  64,
                )
              }
            />
          </div>
          <div>
            <h1 className="text-4xl font-bold tracking-tight">Sources</h1>
            <p className="text-sm text-muted-foreground mt-1">
              AI Prompt Data Export &mdash; source URLs, sentiment, avg.
              position and mentions per prompt &times; model.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
            title="Refresh data"
          >
            <RefreshCw className={`h-4 w-4 ${isFetching ? "animate-spin" : ""}`} />
          </Button>
          <Button variant="outline" onClick={handleExport} disabled={exporting || !totalRows}>
            {exporting ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Download className="h-4 w-4 mr-2" />
            )}
            {exporting ? "Exporting..." : "Export"}
          </Button>
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          icon={<MessageSquare className="h-4 w-4" />}
          label="Prompt × Model"
          value={stats.total.toLocaleString()}
          sub={`${stats.activeModels} model${stats.activeModels === 1 ? "" : "s"} active`}
          tone="default"
        />
        <StatCard
          icon={<Link2 className="h-4 w-4" />}
          label="With Sources"
          value={stats.withSources.toLocaleString()}
          sub={
            stats.total > 0
              ? `${Math.round((stats.withSources / stats.total) * 100)}% of rows`
              : "0% of rows"
          }
          tone="info"
        />
        <StatCard
          icon={<Smile className="h-4 w-4" />}
          label="Avg Sentiment"
          value={stats.hasSentiment ? stats.avgSentiment.toFixed(1) : "—"}
          sub={
            !stats.hasSentiment
              ? "No mentions to score"
              : stats.avgSentiment >= 66
                ? "Positive across mentions"
                : stats.avgSentiment <= 33
                  ? "Negative across mentions"
                  : "Neutral across mentions"
          }
          tone={
            !stats.hasSentiment
              ? "default"
              : stats.avgSentiment >= 66
                ? "good"
                : stats.avgSentiment <= 33
                  ? "bad"
                  : "warn"
          }
        />
        <StatCard
          icon={<TrendingUp className="h-4 w-4" />}
          label="Total Mentions"
          value={stats.totalMentions.toLocaleString()}
          sub="Across filtered rows"
          tone="info"
        />
      </div>

      {/* Filter bar */}
      <Card className="p-4 space-y-3">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div className="flex items-center gap-2 text-sm font-medium">
            <Filter className="h-4 w-4 text-muted-foreground" />
            Filters
            {activeFilterCount > 0 && (
              <Badge variant="secondary" className="ml-1">
                {activeFilterCount} active
              </Badge>
            )}
          </div>
          {activeFilterCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={resetFilters}
              className="h-7 text-xs"
            >
              <X className="h-3 w-3 mr-1" />
              Reset
            </Button>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          {/* Search */}
          <div className="relative md:col-span-2">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search by prompt, model or source domain..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                onAnyFilterChange();
              }}
              className="pl-9"
            />
          </div>

          {/* Model filter */}
          <Select
            value={modelFilter}
            onValueChange={(v) => {
              setModelFilter(v);
              onAnyFilterChange();
            }}
          >
            <SelectTrigger>
              <SelectValue placeholder="All models" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All models</SelectItem>
              {availableModels.map((m) => (
                <SelectItem key={m} value={m}>
                  {m}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Sentiment filter */}
          <Select
            value={sentimentFilter}
            onValueChange={(v: SentimentFilter) => {
              setSentimentFilter(v);
              onAnyFilterChange();
            }}
          >
            <SelectTrigger>
              <SelectValue placeholder="All sentiments" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All sentiments</SelectItem>
              <SelectItem value="positive">Positive (&ge; 66)</SelectItem>
              <SelectItem value="neutral">Neutral (34&ndash;65)</SelectItem>
              <SelectItem value="negative">Negative (&le; 33)</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center justify-between gap-3 flex-wrap pt-1">
          <div className="flex items-center gap-6 flex-wrap">
            <label className="flex items-center gap-2 cursor-pointer text-sm">
              <Switch
                checked={onlyWithSources}
                onCheckedChange={(v) => {
                  setOnlyWithSources(v);
                  onAnyFilterChange();
                }}
              />
              <span>Only with sources</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer text-sm">
              <Switch
                checked={onlyWithMentions}
                onCheckedChange={(v) => {
                  setOnlyWithMentions(v);
                  onAnyFilterChange();
                }}
              />
              <span>Only with mentions</span>
            </label>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Sort by</span>
            <Select
              value={sortBy}
              onValueChange={(v: SortKey) => {
                setSortBy(v);
                onAnyFilterChange();
              }}
            >
              <SelectTrigger className="w-[180px] h-9">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="created_desc">Most recent</SelectItem>
                <SelectItem value="mentions_desc">Most mentions</SelectItem>
                <SelectItem value="sentiment_desc">Highest sentiment</SelectItem>
                <SelectItem value="position_asc">Best position</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </Card>

      {/* Table */}
      <Card className="overflow-hidden">
        {isLoading && (
          <div className="px-5 py-12 flex items-center justify-center">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground mr-2" />
            <span className="text-sm text-muted-foreground">Loading sources...</span>
          </div>
        )}

        {!isLoading && isError && (
          <div className="px-5 py-12 text-center text-sm text-destructive">
            Failed to load sources. Please try again.
          </div>
        )}

        {!isLoading && !isError && totalRows === 0 && (
          <div className="px-5 py-12 text-center text-sm text-muted-foreground">
            {allRows.length === 0
              ? "No published prompt analytics yet. Run prompts in the Prompt Monitoring page to populate this view."
              : "No rows match the current filters."}
          </div>
        )}

        {!isLoading && !isError && totalRows > 0 && (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b" style={{ backgroundColor: "#f6f9fe" }}>
                    <th className="px-4 py-3 text-left font-semibold text-xs whitespace-nowrap" style={{ minWidth: 320 }}>
                      Source URLs
                    </th>
                    <th className="px-4 py-3 text-left font-semibold text-xs" style={{ minWidth: 280 }}>
                      Prompt Text
                    </th>
                    <th className="px-4 py-3 text-left font-semibold text-xs whitespace-nowrap" style={{ minWidth: 110 }}>
                      Model
                    </th>
                    <th className="px-4 py-3 text-center font-semibold text-xs whitespace-nowrap" style={{ minWidth: 130 }}>
                      Avg Sentiment
                    </th>
                    <th className="px-4 py-3 text-center font-semibold text-xs whitespace-nowrap" style={{ minWidth: 110 }}>
                      Avg Position
                    </th>
                    <th className="px-4 py-3 text-center font-semibold text-xs whitespace-nowrap" style={{ minWidth: 100 }}>
                      Mentions
                    </th>
                    <th className="px-4 py-3 text-left font-semibold text-xs whitespace-nowrap" style={{ minWidth: 180 }}>
                      Created
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {pageRows.map((row, idx) => {
                    const bg = idx % 2 === 0 ? "#fff" : "#faf8ff";
                    const domains =
                      row.source_urls === "No sources available" || !row.source_urls
                        ? []
                        : row.source_urls
                            .split(",")
                            .map((d) => d.trim())
                            .filter(Boolean);
                    return (
                      <tr key={page * rowsPerPage + idx} className="border-b hover:bg-muted/10 transition-colors" style={{ backgroundColor: bg }}>
                        <td className="px-4 py-3 align-top">
                          {domains.length === 0 ? (
                            <span className="text-muted-foreground italic text-xs">
                              No sources available
                            </span>
                          ) : (
                            <div className="flex flex-wrap gap-1.5 max-w-[420px]">
                              {domains.slice(0, 6).map((d) => (
                                <a
                                  key={d}
                                  href={d.startsWith("http") ? d : `https://${d}`}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded border border-border bg-muted/30 text-xs text-primary hover:underline hover:bg-muted/50 transition-colors"
                                  title={d}
                                >
                                  {d}
                                  <ExternalLink className="h-3 w-3 opacity-60" />
                                </a>
                              ))}
                              {domains.length > 6 && (
                                <span
                                  className="inline-flex items-center px-2 py-0.5 rounded border border-border bg-muted/20 text-xs text-muted-foreground"
                                  title={domains.slice(6).join(", ")}
                                >
                                  +{domains.length - 6} more
                                </span>
                              )}
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-3 align-top text-sm">
                          <div className="max-w-[420px]" title={row.prompt_text}>
                            {row.prompt_text}
                          </div>
                        </td>
                        <td className="px-4 py-3 align-top whitespace-nowrap">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded border text-xs font-medium ${modelChipClass(row.model)}`}
                          >
                            {row.model || "—"}
                          </span>
                        </td>
                        <td className="px-4 py-3 align-top text-center whitespace-nowrap">
                          {row.mentions > 0 ? (
                            <span
                              className={`inline-flex items-center px-2 py-0.5 rounded border text-xs font-medium ${sentimentChipClass(row.avg_sentiment)}`}
                              title={`${sentimentBucket(row.avg_sentiment)} (${row.avg_sentiment.toFixed(1)})`}
                            >
                              {row.avg_sentiment.toFixed(1)}
                            </span>
                          ) : (
                            <span
                              className="text-muted-foreground text-xs"
                              title="Sentiment is only meaningful when the AI mentioned the brand"
                            >
                              —
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 align-top text-center whitespace-nowrap">
                          {row.avg_position > 0 ? (
                            <span className="inline-flex items-center px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 text-xs font-medium">
                              #{row.avg_position.toFixed(1)}
                            </span>
                          ) : (
                            <span className="text-muted-foreground text-xs">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3 align-top text-center whitespace-nowrap">
                          {row.mentions > 0 ? (
                            <span className="inline-flex items-center justify-center min-w-[28px] px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20 text-xs font-semibold">
                              {row.mentions}
                            </span>
                          ) : (
                            <span className="text-muted-foreground text-xs">0</span>
                          )}
                        </td>
                        <td className="px-4 py-3 align-top whitespace-nowrap text-muted-foreground text-xs">
                          {row.created}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-end gap-4 px-5 py-3 border-t text-sm text-muted-foreground">
              <span className="flex items-center gap-1">
                Rows per page:
                <select
                  value={rowsPerPage}
                  onChange={(e) => {
                    setRowsPerPage(Number(e.target.value));
                    setPage(0);
                  }}
                  className="ml-1 border rounded px-1 py-0.5 text-sm bg-white cursor-pointer"
                >
                  {ROWS_PER_PAGE_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              </span>
              <span>
                {page * rowsPerPage + 1}-
                {Math.min((page + 1) * rowsPerPage, totalRows)} of {totalRows}
              </span>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setPage(0)}
                  disabled={page === 0}
                  className="p-1 hover:bg-muted rounded disabled:opacity-30"
                >
                  <ChevronsLeft className="h-4 w-4" />
                </button>
                <button
                  onClick={() => setPage(Math.max(0, page - 1))}
                  disabled={page === 0}
                  className="p-1 hover:bg-muted rounded disabled:opacity-30"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <button
                  onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                  disabled={page >= totalPages - 1}
                  className="p-1 hover:bg-muted rounded disabled:opacity-30"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
                <button
                  onClick={() => setPage(totalPages - 1)}
                  disabled={page >= totalPages - 1}
                  className="p-1 hover:bg-muted rounded disabled:opacity-30"
                >
                  <ChevronsRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          </>
        )}
      </Card>
    </div>
  );
};

// ─── Stat card ──────────────────────────────────────────────────────────────

type StatTone = "default" | "info" | "good" | "warn" | "bad";

const TONE_CLASSES: Record<StatTone, { icon: string; value: string }> = {
  default: { icon: "bg-slate-100 text-slate-600", value: "text-foreground" },
  info: { icon: "bg-blue-50 text-blue-600", value: "text-foreground" },
  good: { icon: "bg-emerald-50 text-emerald-600", value: "text-emerald-700" },
  warn: { icon: "bg-amber-50 text-amber-600", value: "text-amber-700" },
  bad: { icon: "bg-rose-50 text-rose-600", value: "text-rose-700" },
};

function StatCard({
  icon,
  label,
  value,
  sub,
  tone = "default",
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub?: string;
  tone?: StatTone;
}) {
  const t = TONE_CLASSES[tone];
  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-xs text-muted-foreground uppercase tracking-wider">
            {label}
          </div>
          <div className={`text-2xl font-bold mt-1 ${t.value}`}>{value}</div>
          {sub && (
            <div className="text-xs text-muted-foreground mt-1 truncate">{sub}</div>
          )}
        </div>
        <div className={`p-2 rounded-lg flex-shrink-0 ${t.icon}`}>{icon}</div>
      </div>
    </Card>
  );
}

export default Sources;
