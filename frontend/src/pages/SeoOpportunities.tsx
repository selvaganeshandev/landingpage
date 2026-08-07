import { useState, useEffect, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient } from "@/services/api";
import { useDomainStore } from "@/stores/domainStore";
import { useToast } from "@/hooks/use-toast";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { InfoHint, MetricHint } from "@/components/InfoHint";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Loader2,
  TrendingUp,
  TrendingDown,
  Minus,
  ExternalLink,
  SearchCheck,
  BarChart3,
  Trophy,
  EyeOff,
  Search,
  ChevronLeft,
  ChevronRight,
  Download,
  Plus,
} from "lucide-react";

type TrajectoryState = "climbing" | "slipping" | "volatile" | "stalled" | "new";

interface Trajectory {
  state: TrajectoryState;
  delta: number;
  volatility: number;
  points: number;
  sparkline: number[];
}

interface Difficulty {
  level: "LOW" | "MEDIUM" | "HIGH" | null;
  index: number | null;
  monthly_volume: number[];
  month_labels: string[];
}

interface OpportunityRow {
  id: number;
  keyword: string;
  rank_now: number;
  top_rank: number | null;
  search_volume: number;
  target_url: string;
  week_val: number;
  week_mark: string;
  month_val: number;
  month_mark: string;
  tags: string[];
  favour: number;
  trajectory: Trajectory;
  difficulty: Difficulty;
  opportunity: Opportunity;
}

/** Every row shares a hostname, so the path is the part worth reading. */
const urlPath = (url: string) => {
  try {
    const u = new URL(url);
    return u.pathname === "/" ? u.hostname : u.pathname + u.search;
  } catch {
    return url;
  }
};

interface Bucket {
  label: string;
  range: [number, number] | null;
  total: number;
  volume_at_stake: number;
  rows: OpportunityRow[];
}

interface Opportunity {
  estimated_clicks: number;
  winnability: number;
  score: number;
  target_position: number;
  reasons: string[];
  ctr_now: number;
  ctr_target: number;
}

interface OpportunitiesResponse {
  buckets: {
    striking_distance: Bucket;
    page_two: Bucket;
    slipping: Bucket;
  };
  scored_from: Record<string, number>;
  ctr_source: string;
  summary: {
    tracked: number;
    ranking: number;
    top_three: number;
    not_ranked: number;
    with_volume: number;
    crawled: number;
  };
  limit: number;
}

const formatVolume = (n: number) => {
  if (!n) return "—";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
};

const MoveIndicator = ({ mark, val }: { mark: string; val: number }) => {
  if (mark === "up") {
    return (
      <span className="inline-flex items-center gap-1 text-sm font-medium text-success">
        <TrendingUp className="h-3.5 w-3.5" />
        {val}
      </span>
    );
  }
  if (mark === "down") {
    return (
      <span className="inline-flex items-center gap-1 text-sm font-medium text-destructive">
        <TrendingDown className="h-3.5 w-3.5" />
        {val}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center text-muted-foreground">
      <Minus className="h-3.5 w-3.5" />
    </span>
  );
};

/**
 * Position sparkline. Rank is a golf score, so the y-axis is inverted:
 * a line that rises on screen means the keyword gained places.
 */
const Sparkline = ({ points }: { points: number[] }) => {
  if (points.length < 2) {
    return <span className="text-xs text-muted-foreground">—</span>;
  }

  const w = 64;
  const h = 20;
  const best = Math.min(...points);
  const worst = Math.max(...points);
  const span = worst - best || 1;

  const path = points
    .map((p, i) => {
      const x = (i / (points.length - 1)) * w;
      const y = ((p - best) / span) * (h - 2) + 1;
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <svg width={w} height={h} className="overflow-visible" aria-hidden="true">
      <path d={path} fill="none" stroke="currentColor" strokeWidth="1.5" opacity="0.7" />
    </svg>
  );
};

const TRAJECTORY_STYLE: Record<TrajectoryState, { label: string; className: string }> = {
  climbing: { label: "Climbing", className: "text-success" },
  slipping: { label: "Slipping", className: "text-destructive" },
  volatile: { label: "Volatile", className: "text-warning" },
  stalled: { label: "Stalled", className: "text-muted-foreground" },
  new: { label: "Too new", className: "text-muted-foreground" },
};

const TrajectoryCell = ({ trajectory }: { trajectory: Trajectory }) => {
  const style = TRAJECTORY_STYLE[trajectory.state] ?? TRAJECTORY_STYLE.new;
  const showDelta = trajectory.state === "climbing" || trajectory.state === "slipping";

  return (
    <div className={`flex items-center gap-2 ${style.className}`}>
      <Sparkline points={trajectory.sparkline} />
      <div className="leading-tight">
        <div className="text-xs font-medium">{style.label}</div>
        <div className="text-[11px] text-muted-foreground tabular-nums">
          {trajectory.state === "new"
            ? `${trajectory.points}d`
            : showDelta
            ? `${trajectory.delta > 0 ? "+" : ""}${trajectory.delta} places`
            : `±${trajectory.volatility}`}
        </div>
      </div>
    </div>
  );
};

const COMPETITION_STYLE: Record<string, string> = {
  LOW: "text-success",
  MEDIUM: "text-warning",
  HIGH: "text-destructive",
};

const CompetitionCell = ({ difficulty }: { difficulty: Difficulty }) => {
  if (!difficulty?.level) {
    return <span className="text-xs text-muted-foreground">—</span>;
  }
  const tone = COMPETITION_STYLE[difficulty.level] ?? "text-muted-foreground";
  return (
    <div className="leading-tight">
      <div className={`text-xs font-medium ${tone}`}>
        {difficulty.level.charAt(0) + difficulty.level.slice(1).toLowerCase()}
      </div>
      {difficulty.index !== null && (
        <div className="text-[11px] text-muted-foreground tabular-nums">
          {difficulty.index}/100
        </div>
      )}
    </div>
  );
};

const formatScore = (n: number) => {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
  if (n >= 100) return String(Math.round(n));
  return n.toFixed(n < 10 ? 1 : 0);
};

/**
 * The score is only useful if the reasons behind it are one hover away —
 * an unexplained ranking is not something an account manager can defend.
 */
const ScoreCell = ({
  opportunity,
  volume,
  position,
}: {
  opportunity: Opportunity;
  volume: number;
  position: number;
}) => (
  <Tooltip>
    <TooltipTrigger asChild>
      <div className="cursor-help">
        <div className="text-base font-bold tabular-nums text-primary">
          {formatScore(opportunity.score)}
        </div>
        <div className="text-[11px] text-muted-foreground tabular-nums">
          ~{formatScore(opportunity.estimated_clicks)} clicks
        </div>
      </div>
    </TooltipTrigger>
    <TooltipContent side="right" className="max-w-sm space-y-2">
      <p className="font-medium">
        Est. {Math.round(opportunity.estimated_clicks).toLocaleString()} more clicks/mo if this
        reaches #{opportunity.target_position}
      </p>

      {/* The arithmetic, spelled out — a number nobody can reconstruct is a
          number nobody should act on. */}
      <div className="text-xs space-y-1 border-t border-border/40 pt-1.5">
        <p className="opacity-70">How this is estimated</p>
        <p className="tabular-nums">
          {volume.toLocaleString()} searches/mo × ({opportunity.ctr_target}% at #
          {opportunity.target_position} − {opportunity.ctr_now}% at #{position}) ={" "}
          {Math.round(opportunity.estimated_clicks).toLocaleString()}
        </p>
        <p className="opacity-70">
          Those click-through rates are <strong>published industry averages</strong> by position,
          not measured for this site — Search Console data isn't stored per keyword, so there's
          nothing to calibrate against. Treat the figure as a way to compare keywords against each
          other, not as a traffic forecast.
        </p>
      </div>

      {opportunity.reasons.length > 0 && (
        <div className="text-xs border-t border-border/40 pt-1.5">
          <p className="opacity-70 mb-0.5">
            Winnability ×{opportunity.winnability}, because:
          </p>
          <ul className="space-y-0.5">
            {opportunity.reasons.map((r) => (
              <li key={r}>· {r}</li>
            ))}
          </ul>
        </div>
      )}
    </TooltipContent>
  </Tooltip>
);

/**
 * The three ways this page can legitimately have nothing to show. They are not
 * interchangeable: 37 of 50 domains track no SEO keywords at all, and telling
 * that user "no keywords in this bucket" leaves them with no idea what to do.
 */
const EmptyState = ({
  icon: Icon,
  title,
  children,
  action,
}: {
  icon: typeof SearchCheck;
  title: string;
  children: React.ReactNode;
  action?: { label: string; onClick: () => void };
}) => (
  <Card className="p-6 border border-border">
    <div className="flex flex-col items-center justify-center text-center py-16 gap-3">
      <div className="rounded-full bg-muted/50 p-3">
        <Icon className="h-6 w-6 text-muted-foreground" />
      </div>
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="text-sm text-muted-foreground max-w-md">{children}</p>
      {action && (
        <Button
          className="gradient-primary shadow-md shadow-primary/20 mt-2"
          onClick={action.onClick}
        >
          <Plus className="h-4 w-4 mr-2" />
          {action.label}
        </Button>
      )}
    </div>
  </Card>
);

/**
 * Per-bucket empty messages. A bucket can be empty while the page as a whole
 * has plenty of data, and that is not a problem to fix — it usually means the
 * keywords sit somewhere else. Each message says where they are instead.
 */
type Summary = { tracked: number; ranking: number; top_three: number; not_ranked: number };

const BUCKET_EMPTY: Record<
  "striking_distance" | "page_two" | "slipping",
  { title: string; hint: (s: Summary) => string }
> = {
  striking_distance: {
    title: "Nothing sitting in positions 4–10",
    hint: (s) =>
      `None of the ${s.ranking.toLocaleString()} ranking keywords are on page one below the top three.` +
      (s.top_three > 0
        ? ` ${s.top_three.toLocaleString()} already hold a top-three spot — those are won, not opportunities.`
        : " Check Page Two for the closest candidates."),
  },
  page_two: {
    title: "Nothing sitting in positions 11–20",
    hint: (s) =>
      `None of the ${s.ranking.toLocaleString()} ranking keywords are on page two. ` +
      `Keywords below position 20 are not shown here — the jump to page one is usually too far to call an opportunity.`,
  },
  slipping: {
    title: "Nothing has slipped",
    hint: () =>
      "No tracked keyword lost ground over the last week or month. That is the good outcome — this tab stays empty when positions are holding.",
  },
};

const PAGE_SIZE = 50;

/**
 * Page numbers to render: always first and last, plus a window around the
 * current page, with nulls standing in for the gaps. Keeps the control a fixed
 * width whether there are 3 pages or 16.
 */
const pageWindow = (current: number, total: number): (number | null)[] => {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);

  const pages = new Set<number>([1, total, current]);
  if (current - 1 > 1) pages.add(current - 1);
  if (current + 1 < total) pages.add(current + 1);

  const sorted = [...pages].sort((a, b) => a - b);
  const out: (number | null)[] = [];
  sorted.forEach((p, i) => {
    if (i > 0 && p - sorted[i - 1] > 1) out.push(null);
    out.push(p);
  });
  return out;
};

const OpportunityTable = ({
  bucket,
  emptyTitle,
  emptyHint,
  onOpen,
}: {
  bucket: Bucket;
  emptyTitle: string;
  emptyHint: string;
  onOpen: (id: number) => void;
}) => {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);

  // Search runs over the whole bucket, not the visible page — otherwise
  // "find me that keyword" would only work if you were already looking at it.
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return bucket.rows;
    return bucket.rows.filter(
      (r) =>
        r.keyword.toLowerCase().includes(q) ||
        r.target_url.toLowerCase().includes(q)
    );
  }, [bucket.rows, query]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount);
  const visible = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  // A new search should not leave you stranded on page 7 of 2 results.
  useEffect(() => setPage(1), [query, bucket.rows]);

  if (!bucket.rows.length) {
    return (
      <div className="py-16 text-center space-y-1">
        <p className="text-sm font-medium">{emptyTitle}</p>
        <p className="text-sm text-muted-foreground max-w-md mx-auto">{emptyHint}</p>
      </div>
    );
  }

  const first = (safePage - 1) * PAGE_SIZE + 1;
  const last = Math.min(safePage * PAGE_SIZE, filtered.length);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="relative w-full max-w-xs">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search keyword or URL…"
            className="pl-8"
          />
        </div>
        <span className="text-sm text-muted-foreground">
          <span className="font-medium text-foreground">{formatVolume(bucket.volume_at_stake)}</span>{" "}
          monthly searches across {bucket.total.toLocaleString()} keywords
        </span>
      </div>

      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          {filtered.length === 0
            ? "No matches"
            : `Showing ${first.toLocaleString()}–${last.toLocaleString()} of ${filtered.length.toLocaleString()}`}
          {query
            ? ` matching “${query}” (of ${bucket.total.toLocaleString()})`
            : " — ranked across all of them"}
        </span>
      </div>

      {/* Stated in the open rather than only inside a hover: the click figures
          are modelled, and anyone reading the column should know that. */}
      <p className="text-xs text-muted-foreground">
        Click figures are <span className="font-medium text-foreground">estimates</span> — search
        volume × the industry-average click-through rate for each position. No Search Console data
        is stored per keyword, so they aren't calibrated to this site. Use them to rank keywords
        against each other, not to forecast traffic. Hover any score for its workings.
      </p>

      <div className="rounded-md border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[90px]">
                <span className="flex items-center gap-1.5">
                  Score
                  <InfoHint>
                    <MetricHint
                      title="Opportunity Score"
                      plain="What this keyword is worth multiplied by how reachable it looks — the order to work in."
                      formula="Estimated extra monthly clicks (search volume × the CTR difference between the current and target position) × a winnability multiplier built from trajectory, advertiser competition and whether the page has held the target position before. Target is #3 from page one, #10 from page two. CTR values are published industry averages, not measured for this account."
                    />
                  </InfoHint>
                </span>
              </TableHead>
              <TableHead className="w-[80px]">Position</TableHead>
              <TableHead>Ranking Page</TableHead>
              <TableHead className="w-[110px] text-right">Volume</TableHead>
              <TableHead className="w-[170px]">
                <span className="flex items-center gap-1.5">
                  Trajectory
                  <InfoHint>
                    <MetricHint
                      title="Trajectory"
                      plain="Which way this keyword has been heading over the last 90 days, rather than where it sits today."
                      formula="Compares the average of the first and last 7 daily positions. A move of 2+ places reads as Climbing or Slipping; a standard deviation of 5+ reads as Volatile, since a keyword that swings wildly isn't really stalled. Fewer than 10 recorded days shows as Too new."
                    />
                  </InfoHint>
                </span>
              </TableHead>
              <TableHead className="w-[110px]">
                <span className="flex items-center gap-1.5">
                  Ad Competition
                  <InfoHint>
                    <MetricHint
                      title="Ad Competition"
                      plain="How contested this term is among advertisers — a rough proxy for how commercially valuable it is."
                      formula="Google Keyword Planner's competition value (LOW / MEDIUM / HIGH plus a 0-100 index). It measures paid-search bidding, NOT organic ranking difficulty — a LOW term can still be hard to rank for. Treat it as a hint, not a verdict."
                    />
                  </InfoHint>
                </span>
              </TableHead>
              <TableHead className="w-[80px]">30d</TableHead>
              <TableHead className="w-[80px] text-right">Best</TableHead>
              <TableHead className="w-[50px]" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {visible.map((row) => (
              <TableRow
                key={row.id}
                className="cursor-pointer transition-colors hover:bg-muted/50"
                onClick={() => onOpen(row.id)}
              >
                <TableCell>
                  <ScoreCell
                    opportunity={row.opportunity}
                    volume={row.search_volume}
                    position={row.rank_now}
                  />
                </TableCell>
                <TableCell>
                  <Badge variant="secondary" className="tabular-nums">
                    {row.rank_now}
                  </Badge>
                </TableCell>
                <TableCell>
                  {row.target_url ? (
                    <div className="font-medium truncate max-w-md" title={row.target_url}>
                      {urlPath(row.target_url)}
                    </div>
                  ) : (
                    <div className="font-medium text-muted-foreground">No page recorded</div>
                  )}
                  <div className="text-xs text-muted-foreground truncate max-w-md">
                    {row.keyword}
                  </div>
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatVolume(row.search_volume)}
                </TableCell>
                <TableCell>
                  <TrajectoryCell trajectory={row.trajectory} />
                </TableCell>
                <TableCell>
                  <CompetitionCell difficulty={row.difficulty} />
                </TableCell>
                <TableCell>
                  <MoveIndicator mark={row.month_mark} val={row.month_val} />
                </TableCell>
                <TableCell className="text-right tabular-nums text-muted-foreground">
                  {row.top_rank ?? "—"}
                </TableCell>
                <TableCell>
                  {row.target_url && (
                    <a
                      href={row.target_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      title="Open the ranking page"
                      className="inline-flex text-muted-foreground hover:text-primary transition-colors"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>

        {filtered.length === 0 && (
          <div className="py-16 text-center text-muted-foreground text-sm">
            Nothing matches “{query}” in this bucket.
          </div>
        )}
      </div>

      {pageCount > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground tabular-nums">
            Page {safePage} of {pageCount}
          </span>
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={safePage === 1}
            >
              <ChevronLeft className="h-4 w-4 mr-1" />
              Prev
            </Button>
            {pageWindow(safePage, pageCount).map((p, i) =>
              p === null ? (
                <span key={`gap-${i}`} className="px-2 text-muted-foreground">
                  …
                </span>
              ) : (
                <Button
                  key={p}
                  variant={p === safePage ? "default" : "outline"}
                  size="sm"
                  className={p === safePage ? "gradient-primary text-white" : ""}
                  onClick={() => setPage(p)}
                >
                  {p}
                </Button>
              )
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
              disabled={safePage === pageCount}
            >
              Next
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

export default function SeoOpportunities() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { selectedDomain } = useDomainStore();
  const activeDomainId = selectedDomain ? String(selectedDomain.id) : "";

  const [data, setData] = useState<OpportunitiesResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);

  const fetchData = useCallback(async () => {
    if (!activeDomainId) {
      setData(null);
      return;
    }
    setLoading(true);
    try {
      const res = await apiClient.getSeoOpportunities({ domain_id: activeDomainId });
      setData(res as OpportunitiesResponse);
    } catch (err: any) {
      toast({
        title: "Could not load opportunities",
        description: err?.message || "Please try again.",
        variant: "destructive",
      });
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [activeDomainId, toast]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Rows open the opportunity view, not the generic keyword detail: the two
  // show different things, and this page's rows are opportunities.
  const openKeyword = (id: number) => navigate(`/seo-opportunities/${id}`);

  const handleExport = async () => {
    if (!activeDomainId) return;
    setExporting(true);
    try {
      const blob = await apiClient.exportSeoOpportunitiesXlsx(activeDomainId);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      const now = new Date();
      const ts =
        now.getFullYear().toString() +
        String(now.getMonth() + 1).padStart(2, "0") +
        String(now.getDate()).padStart(2, "0") +
        "_" +
        String(now.getHours()).padStart(2, "0") +
        String(now.getMinutes()).padStart(2, "0");
      link.setAttribute(
        "download",
        `opportunities-${selectedDomain?.name || activeDomainId}-${ts}.xlsx`
      );
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast({ title: "Opportunities exported" });
    } catch {
      toast({ title: "Export failed", variant: "destructive" });
    } finally {
      setExporting(false);
    }
  };

  return (
    <TooltipProvider delayDuration={150}>
    <div className="p-8 space-y-8 bg-background animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Opportunities</h1>
          <p className="text-muted-foreground mt-2">
            Keywords closest to earning clicks, ranked by what each one is worth and how
            reachable it looks
          </p>
        </div>
        <Button
          variant="outline"
          onClick={handleExport}
          disabled={!activeDomainId || exporting}
        >
          {exporting ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <Download className="h-4 w-4 mr-2" />
          )}
          Export
        </Button>
      </div>

      {!activeDomainId && (
        <div className="py-32 text-center text-muted-foreground">
          Select a domain to see its opportunities.
        </div>
      )}

      {activeDomainId && loading && (
        <div className="flex flex-col items-center justify-center py-32">
          <Loader2 className="h-10 w-10 animate-spin text-primary mb-4" />
          <span className="text-muted-foreground text-sm">Loading opportunities...</span>
        </div>
      )}

      {/* Nothing tracked at all — by far the most common case (37 of 50
          domains). Showing four zero tiles and three empty tabs here would be
          noise; what this user needs is the reason and the next step. */}
      {activeDomainId && !loading && data && data.summary.tracked === 0 && (
        <EmptyState
          icon={SearchCheck}
          title="No keywords are being tracked yet"
          action={{
            label: "Add Keywords",
            onClick: () => navigate("/seo-rankings/add-keyword"),
          }}
        >
          Opportunities is built from daily rank tracking, and{" "}
          <span className="font-medium text-foreground">
            {selectedDomain?.name || "this domain"}
          </span>{" "}
          has no keywords set up. Add some and this page will fill in once the first crawl
          completes — usually within a day.
        </EmptyState>
      )}

      {/* Keywords exist but have never been crawled. */}
      {activeDomainId && !loading && data && data.summary.tracked > 0 &&
        data.summary.crawled === 0 && (
          <EmptyState icon={Loader2} title="Waiting for the first crawl">
            {data.summary.tracked.toLocaleString()} keyword
            {data.summary.tracked === 1 ? " is" : "s are"} set up but{" "}
            {data.summary.tracked === 1 ? "has" : "have"} not been checked yet. Positions
            appear here after the first ranking run, then build history daily.
          </EmptyState>
        )}

      {/* Crawled, but nothing ranks anywhere in the top 100. */}
      {activeDomainId && !loading && data && data.summary.crawled > 0 &&
        data.summary.ranking === 0 && (
          <EmptyState icon={EyeOff} title="Nothing is ranking yet">
            All {data.summary.tracked.toLocaleString()} tracked keyword
            {data.summary.tracked === 1 ? "" : "s"} have been checked, but none currently
            place in the top 100. Opportunities shows keywords already within reach of page
            one, so there is nothing to rank here until something starts placing.
          </EmptyState>
        )}

      {activeDomainId && !loading && data && data.summary.ranking > 0 && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {[
              {
                label: "Tracked",
                value: data.summary.tracked,
                icon: SearchCheck,
                tint: "text-primary",
                hint: `${data.summary.with_volume.toLocaleString()} with search volume`,
              },
              {
                label: "Ranking",
                value: data.summary.ranking,
                icon: BarChart3,
                tint: "text-secondary",
                hint: "Holding a position today",
              },
              {
                label: "In Top 3",
                value: data.summary.top_three,
                icon: Trophy,
                tint: "text-success",
                hint: "Positions earning most clicks",
              },
              {
                label: "Not Ranked",
                value: data.summary.not_ranked,
                icon: EyeOff,
                tint: "text-destructive",
                hint: "No position recorded",
              },
            ].map((tile) => (
              <Card key={tile.label} className="p-6 border border-border">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">{tile.label}</p>
                    <p className="text-2xl font-bold mt-1 tabular-nums">
                      {tile.value.toLocaleString()}
                    </p>
                  </div>
                  <tile.icon className={`h-5 w-5 ${tile.tint}`} />
                </div>
                <p className="text-xs text-muted-foreground mt-2">{tile.hint}</p>
              </Card>
            ))}
          </div>

          <Tabs defaultValue="striking_distance" className="space-y-6">
            <TabsList className="bg-muted/50 p-1 border border-border">
              {(
                [
                  ["striking_distance", "Striking Distance"],
                  ["page_two", "Page Two"],
                  ["slipping", "Slipping"],
                ] as const
              ).map(([key, label]) => (
                <TabsTrigger
                  key={key}
                  value={key}
                  className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white"
                >
                  {label}
                  <span className="ml-2 tabular-nums opacity-70">
                    {data.buckets[key].total.toLocaleString()}
                  </span>
                </TabsTrigger>
              ))}
            </TabsList>

            {(["striking_distance", "page_two", "slipping"] as const).map((key) => (
              <TabsContent key={key} value={key} className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  {data.buckets[key].label}
                </p>
                <OpportunityTable
                  bucket={data.buckets[key]}
                  emptyTitle={BUCKET_EMPTY[key].title}
                  emptyHint={BUCKET_EMPTY[key].hint(data.summary)}
                  onOpen={openKeyword}
                />
              </TabsContent>
            ))}
          </Tabs>
        </>
      )}
    </div>
    </TooltipProvider>
  );
}
