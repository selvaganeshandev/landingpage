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
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
  CalendarIcon,
} from "lucide-react";
import { getFaviconUrl, handleFaviconError } from "@/utils/faviconHelper";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { format } from "date-fns";
import { cn } from "@/lib/utils";
import { InfoHint, MetricHint } from "@/components/InfoHint";

type SourceUrlGroup = {
  domain: string;
  urls: string[];
};

type SourceRow = {
  source_urls: string;
  source_url_groups?: SourceUrlGroup[];
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
  const [startDate, setStartDate] = useState<Date | undefined>(undefined);
  const [endDate, setEndDate] = useState<Date | undefined>(undefined);
  // Controlled so picking a start hands straight to the end picker, matching
  // Traffic Attribution. Uncontrolled popovers left the user to close one
  // calendar and hunt for the second field before the range would apply.
  const [startPickerOpen, setStartPickerOpen] = useState(false);
  const [endPickerOpen, setEndPickerOpen] = useState(false);
  // Row whose full source list is open in the dialog; null when closed.
  const [sourcesModal, setSourcesModal] = useState<{
    prompt: string;
    model: string;
    groups: SourceUrlGroup[];
  } | null>(null);

  const dateRangeReady =
    (!startDate && !endDate) ||
    (Boolean(startDate) && Boolean(endDate) && startDate! <= endDate!);
  const startStr = startDate ? format(startDate, "yyyy-MM-dd") : undefined;
  const endStr = endDate ? format(endDate, "yyyy-MM-dd") : undefined;

  const { data, isLoading, isError } = useQuery({
    queryKey: ["promptSourcesData", domainId, startStr, endStr],
    queryFn: async () => {
      const res = await apiClient.getPromptSourcesData(domainId!, {
        start_date: startStr,
        end_date: endStr,
      });
      return res as {
        domain_id: number;
        domain_name: string;
        columns: string[];
        rows: SourceRow[];
        total_rows: number;
      };
    },
    // Only fetch when domain is set and (no range selected, OR a complete valid range is selected)
    enabled: !!domainId && dateRangeReady,
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
        const fullUrls = Array.isArray(r.source_url_groups)
          ? r.source_url_groups.flatMap((g) => [g.domain, ...g.urls]).join(" ").toLowerCase()
          : "";
        const hit =
          r.prompt_text.toLowerCase().includes(q) ||
          r.source_urls.toLowerCase().includes(q) ||
          fullUrls.includes(q) ||
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
    if ((startDate && !endDate) || (!startDate && endDate)) {
      toast({
        title: "Incomplete date range",
        description: "Please pick both a start and end date, or clear both.",
        variant: "destructive",
      });
      return;
    }
    if (startDate && endDate && startDate > endDate) {
      toast({
        title: "Invalid date range",
        description: "Start date must be on or before end date.",
        variant: "destructive",
      });
      return;
    }
    setExporting(true);
    try {
      await apiClient.exportPromptsReport({
        domain_id: domainId,
        start_date: startStr,
        end_date: endStr,
      });
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
    // One provider for the page: every domain in the table is a tooltip trigger,
    // and mounting a provider per row would be needless work.
    <TooltipProvider delayDuration={200}>
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
        <div className="flex items-center gap-2 flex-wrap">
          <Popover open={startPickerOpen} onOpenChange={setStartPickerOpen}>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className={cn("justify-start text-left font-normal", !startDate && "text-muted-foreground")}
              >
                <CalendarIcon className="mr-2 h-4 w-4" />
                {startDate ? format(startDate, "MMM d, yyyy") : <span>Start date</span>}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="start">
              <Calendar
                mode="single"
                selected={startDate}
                onSelect={(date) => {
                  setStartDate(date);
                  setStartPickerOpen(false);
                  if (date) {
                    // Drop an end date that now precedes the start, rather than
                    // leaving an impossible range on screen.
                    if (endDate && endDate < date) setEndDate(undefined);
                    setEndPickerOpen(true);
                  }
                }}
                disabled={(date) => date > new Date()}
                initialFocus
              />
            </PopoverContent>
          </Popover>
          <Popover open={endPickerOpen} onOpenChange={setEndPickerOpen}>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className={cn("justify-start text-left font-normal", !endDate && "text-muted-foreground")}
              >
                <CalendarIcon className="mr-2 h-4 w-4" />
                {endDate ? format(endDate, "MMM d, yyyy") : <span>End date</span>}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="start">
              <Calendar
                mode="single"
                selected={endDate}
                defaultMonth={startDate}
                onSelect={(date) => {
                  setEndDate(date);
                  if (date) setEndPickerOpen(false);
                }}
                disabled={(date) => date > new Date() || (startDate ? date < startDate : false)}
                initialFocus
              />
            </PopoverContent>
          </Popover>
          {(startDate || endDate) && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setStartDate(undefined);
                setEndDate(undefined);
              }}
            >
              <X className="h-4 w-4" />
            </Button>
          )}
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
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <StatCard
          icon={<MessageSquare className="h-5 w-5" />}
          label="Prompt × Model"
          hint={
            <MetricHint
              title="Prompt × Model"
              plain="One row for every prompt you track, on every AI platform it was asked on. The same prompt across four models is four rows."
              formula="Counts the rows currently in view, so it follows your filters, search and date range rather than the whole dataset."
            />
          }
          value={stats.total.toLocaleString()}
          sub={`${stats.activeModels} model${stats.activeModels === 1 ? "" : "s"} active`}
          tone="default"
        />
        <StatCard
          icon={<Link2 className="h-5 w-5" />}
          label="With Sources"
          hint={
            <MetricHint
              title="With Sources"
              plain="How many of those answers cited anything at all. The rest asserted things about your market without showing where it came from."
              formula="Rows carrying at least one source URL, divided by the rows in view."
            />
          }
          value={stats.withSources.toLocaleString()}
          sub={
            stats.total > 0
              ? `${Math.round((stats.withSources / stats.total) * 100)}% of rows`
              : "0% of rows"
          }
          tone="info"
        />
        <StatCard
          icon={<Smile className="h-5 w-5" />}
          label="Avg Sentiment"
          hint={
            <MetricHint
              title="Avg Sentiment"
              plain="How positively the AI answers speak about your brand, on a 0–100 scale. Above 66 is positive, below 33 negative."
              formula="Averaged only over answers that actually mention your brand. Rows with no mention sit at the neutral default and would drag every score toward 50, so they are excluded — which is why this reads “—” when nothing was mentioned."
            />
          }
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
          icon={<TrendingUp className="h-5 w-5" />}
          label="Total Mentions"
          hint={
            <MetricHint
              title="Total Mentions"
              plain="How many times your brand was named across the answers in view."
              formula="Sums the per-row mention counts. One answer naming you three times contributes three."
            />
          }
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
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/30">
                    <TableHead className="py-2 px-3 whitespace-nowrap" style={{ minWidth: 320 }}>
                      Source URLs
                    </TableHead>
                    <TableHead className="py-2 px-3" style={{ minWidth: 280 }}>
                      Prompt Text
                    </TableHead>
                    <TableHead className="py-2 px-3 whitespace-nowrap" style={{ minWidth: 110 }}>
                      Model
                    </TableHead>
                    <TableHead className="py-2 px-3 text-center whitespace-nowrap" style={{ minWidth: 130 }}>
                      Avg Sentiment
                    </TableHead>
                    <TableHead className="py-2 px-3 text-center whitespace-nowrap" style={{ minWidth: 110 }}>
                      Avg Position
                    </TableHead>
                    <TableHead className="py-2 px-3 text-center whitespace-nowrap" style={{ minWidth: 100 }}>
                      Mentions
                    </TableHead>
                    <TableHead className="py-2 px-3 whitespace-nowrap" style={{ minWidth: 180 }}>
                      Created
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {pageRows.map((row, idx) => {
                    // Prefer the new grouped structure (domain + subpage URLs).
                    // Fall back to the legacy comma-separated domain string so
                    // older cached responses still render correctly.
                    const groups: SourceUrlGroup[] =
                      Array.isArray(row.source_url_groups) && row.source_url_groups.length > 0
                        ? row.source_url_groups
                        : row.source_urls && row.source_urls !== "No sources available"
                          ? row.source_urls
                              .split(",")
                              .map((d) => d.trim())
                              .filter(Boolean)
                              .map((d) => ({ domain: d, urls: [] }))
                          : [];
                    return (
                      <TableRow key={page * rowsPerPage + idx} className="hover:bg-muted/20 transition-colors">
                        <TableCell className="py-2 px-3 align-top">
                          {groups.length === 0 ? (
                            <span className="text-muted-foreground italic text-xs">
                              No sources available
                            </span>
                          ) : (
                            <div className="space-y-1.5 max-w-[460px]">
                              {/* Domain plus a page count only. Listing three
                                  URLs per domain made a single row taller than
                                  the screen on prompts citing ten sources; the
                                  URLs live in the hover tooltip and the dialog
                                  instead of pushing every other column down. */}
                              {groups.slice(0, 4).map((g) => {
                                const domainHref = g.urls[0] || (g.domain.startsWith("http") ? g.domain : `https://${g.domain}`);
                                return (
                                  <div key={g.domain} className="flex items-center gap-1.5">
                                    <img
                                      src={getFaviconUrl(g.domain, 32)}
                                      alt=""
                                      className="w-3.5 h-3.5 flex-shrink-0"
                                      onError={(e) => handleFaviconError(e, g.domain, "", 32)}
                                    />
                                    <Tooltip>
                                      <TooltipTrigger asChild>
                                        <a
                                          href={domainHref}
                                          target="_blank"
                                          rel="noreferrer"
                                          className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline truncate"
                                        >
                                          <span className="truncate">{g.domain}</span>
                                          {g.urls.length > 0 && (
                                            <span className="text-muted-foreground font-normal">({g.urls.length})</span>
                                          )}
                                          <ExternalLink className="h-3 w-3 opacity-60 flex-shrink-0" />
                                        </a>
                                      </TooltipTrigger>
                                      <TooltipContent side="right" className="max-w-lg">
                                        {g.urls.length === 0 ? (
                                          <p className="text-xs">{g.domain}</p>
                                        ) : (
                                          <>
                                            <p className="text-xs font-medium mb-1">
                                              {g.urls.length} page{g.urls.length === 1 ? "" : "s"} cited on {g.domain}
                                            </p>
                                            <ul className="space-y-0.5">
                                              {g.urls.slice(0, 10).map((u) => (
                                                <li key={u} className="text-[11px] leading-snug break-all opacity-90">
                                                  {u}
                                                </li>
                                              ))}
                                            </ul>
                                            {g.urls.length > 10 && (
                                              <p className="text-[11px] italic mt-1 opacity-75">
                                                +{g.urls.length - 10} more — open the full list below
                                              </p>
                                            )}
                                          </>
                                        )}
                                      </TooltipContent>
                                    </Tooltip>
                                  </div>
                                );
                              })}
                              {/* Opens every domain for this row, the first four
                                  included — the dialog is the only place the
                                  full list is readable. */}
                              <button
                                type="button"
                                onClick={() => setSourcesModal({ prompt: row.prompt_text, model: row.model, groups })}
                                className="inline-flex items-center px-2 py-0.5 rounded border border-border bg-muted/20 text-xs text-muted-foreground hover:border-primary hover:text-primary transition-colors"
                              >
                                {groups.length > 4
                                  ? `+${groups.length - 4} more domain${groups.length - 4 === 1 ? "" : "s"}`
                                  : "View all sources"}
                              </button>
                            </div>
                          )}
                        </TableCell>
                        <TableCell className="py-2 px-3 align-top text-sm">
                          <div className="max-w-[420px]" title={row.prompt_text}>
                            {row.prompt_text}
                          </div>
                        </TableCell>
                        <TableCell className="py-2 px-3 align-top whitespace-nowrap">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded border text-xs font-medium ${modelChipClass(row.model)}`}
                          >
                            {row.model || "—"}
                          </span>
                        </TableCell>
                        <TableCell className="py-2 px-3 align-top text-center whitespace-nowrap">
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
                        </TableCell>
                        <TableCell className="py-2 px-3 align-top text-center whitespace-nowrap">
                          {row.avg_position > 0 ? (
                            <span className="inline-flex items-center px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 text-xs font-medium">
                              #{row.avg_position.toFixed(1)}
                            </span>
                          ) : (
                            <span className="text-muted-foreground text-xs">—</span>
                          )}
                        </TableCell>
                        <TableCell className="py-2 px-3 align-top text-center whitespace-nowrap">
                          {row.mentions > 0 ? (
                            <span className="inline-flex items-center justify-center min-w-[28px] px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20 text-xs font-semibold">
                              {row.mentions}
                            </span>
                          ) : (
                            <span className="text-muted-foreground text-xs">0</span>
                          )}
                        </TableCell>
                        <TableCell className="py-2 px-3 align-top whitespace-nowrap text-muted-foreground text-xs">
                          {row.created}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
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

      {/* Every source for one prompt × model. The table can only show four
          domains and three pages each before it would dominate the row, so the
          rest live here rather than being unreachable. */}
      <Dialog open={!!sourcesModal} onOpenChange={(open) => !open && setSourcesModal(null)}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-lg">All Sources</DialogTitle>
            <DialogDescription className="text-sm">
              {sourcesModal
                ? `${sourcesModal.groups.length} domain${sourcesModal.groups.length === 1 ? "" : "s"} · ${sourcesModal.groups.reduce((n, g) => n + g.urls.length, 0)} page${sourcesModal.groups.reduce((n, g) => n + g.urls.length, 0) === 1 ? "" : "s"} cited by ${sourcesModal.model}`
                : ""}
            </DialogDescription>
          </DialogHeader>

          {sourcesModal && (
            <>
              <p className="text-sm text-muted-foreground border-l-2 border-border pl-3">
                {sourcesModal.prompt}
              </p>
              <div className="space-y-3">
                {sourcesModal.groups.map((g) => {
                  const domainHref = g.urls[0] || (g.domain.startsWith("http") ? g.domain : `https://${g.domain}`);
                  return (
                    <div key={g.domain} className="rounded-lg border border-border p-3">
                      <div className="flex items-center gap-2">
                        <img
                          src={getFaviconUrl(g.domain, 32)}
                          alt=""
                          className="w-4 h-4 flex-shrink-0"
                          onError={(e) => handleFaviconError(e, g.domain, "", 32)}
                        />
                        <a
                          href={domainHref}
                          target="_blank"
                          rel="noreferrer"
                          className="text-sm font-medium text-primary hover:underline inline-flex items-center gap-1"
                        >
                          {g.domain}
                          <ExternalLink className="h-3 w-3 opacity-60" />
                        </a>
                        {g.urls.length > 0 && (
                          <span className="text-xs text-muted-foreground ml-auto">
                            {g.urls.length} page{g.urls.length === 1 ? "" : "s"}
                          </span>
                        )}
                      </div>
                      {g.urls.length > 0 && (
                        <ul className="mt-2 space-y-1 pl-6">
                          {g.urls.map((u) => (
                            <li key={u}>
                              <a
                                href={u}
                                target="_blank"
                                rel="noreferrer"
                                className="text-xs text-muted-foreground hover:text-primary hover:underline break-all"
                              >
                                {u}
                              </a>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
    </TooltipProvider>
  );
};

// ─── Stat card ──────────────────────────────────────────────────────────────

type StatTone = "default" | "info" | "good" | "warn" | "bad";

// `plainIcon` is the bare glyph colour used by the shared card shape; `icon`
// (the tinted tile) is kept for any caller still wanting the old treatment.
const TONE_CLASSES: Record<StatTone, { icon: string; value: string; plainIcon: string }> = {
  default: { icon: "bg-slate-100 text-slate-600", value: "text-foreground", plainIcon: "text-muted-foreground" },
  info: { icon: "bg-blue-50 text-blue-600", value: "text-foreground", plainIcon: "text-primary" },
  good: { icon: "bg-emerald-50 text-emerald-600", value: "text-emerald-700", plainIcon: "text-emerald-600" },
  warn: { icon: "bg-amber-50 text-amber-600", value: "text-amber-700", plainIcon: "text-amber-600" },
  bad: { icon: "bg-rose-50 text-rose-600", value: "text-rose-700", plainIcon: "text-rose-600" },
};

/**
 * Same card shape as the metric cards on Citations and Insights: sentence-case
 * label, text-2xl figure, plain icon, text-xs subtext. This page previously
 * used an uppercase tracking-wider label and a tinted icon tile, which made it
 * read as a different product surface.
 */
function StatCard({
  icon,
  label,
  value,
  sub,
  hint,
  tone = "default",
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub?: string;
  hint?: React.ReactNode;
  tone?: StatTone;
}) {
  const t = TONE_CLASSES[tone];
  return (
    <Card className="p-6 border border-border">
      <div className="flex items-center justify-between">
        <div className="min-w-0">
          <p className="text-sm text-muted-foreground flex items-center gap-1.5">
            {label}
            {hint && <InfoHint>{hint}</InfoHint>}
          </p>
          <p className={`text-2xl font-bold mt-1 ${t.value}`}>{value}</p>
        </div>
        <div className={`flex-shrink-0 ${t.plainIcon}`}>{icon}</div>
      </div>
      {sub && <p className="text-xs text-muted-foreground mt-2 truncate">{sub}</p>}
    </Card>
  );
}

export default Sources;
