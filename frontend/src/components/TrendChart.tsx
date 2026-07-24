import { useState } from "react";
import { Card } from "@/components/ui/card";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, Legend } from "recharts";
import { Info } from "lucide-react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

interface TrendMetrics {
  total_mentions?: number;
  mentions_change?: number | null;
  total_citations?: number;
  citations_change?: number | null;
  total_cited_pages?: number;
  cited_pages_change?: number | null;
  visibility_score?: number;
  visibility_change?: number | null;
  avg_position?: number;
  position_change?: number | null;
}

// AI-referred traffic aggregates from the GA4 AI-referral endpoint
// (/integrations/google/ai-referrals/). Shapes mirror the backend
// parse_ai_referral_response output.
interface AITrafficTotals {
  visits?: number;
  users?: number;
  conversions?: number;
  revenue?: number;
  pageViews?: number;
}
interface AIPlatformStat {
  visits?: number;
  users?: number;
  conversions?: number;
  avgDuration?: number;
  conversionRate?: number;
}
interface AITraffic {
  totals?: AITrafficTotals;
  platform_breakdown?: Record<string, AIPlatformStat>;
}

interface TrendChartProps {
  data?: Array<{ date: string; value?: number; mentions?: number; citations?: number; visibility?: number; [key: string]: number | string | undefined }>;
  metrics?: TrendMetrics;
  // Currently-selected window as a `days` string ("30" | "180" | "3650"), or
  // undefined when a custom date range is active (no button highlighted).
  timeRange?: string;
  onTimeRangeChange?: (days: string) => void;
  // Daily AI-referred traffic (sessions/users by date) — feeds the Visibility
  // vs Traffic correlation tab.
  aiTrafficDaily?: Array<{ date: string; sessions: number; users: number }> | null;
  // Your brand's share-of-voice percentage for the current window — feeds the
  // AI Visibility tab's third pill. Null when there's no share-of-voice reading.
  shareOfVoice?: number | null;
  // AI-referred traffic aggregates — feeds the AI Traffic tab. Null when GA isn't
  // connected or there were no AI referrals in the window.
  aiTraffic?: AITraffic | null;
  /** API's `trends_are_period`: true when `data` holds per-period activity,
   *  false when it holds running totals. Undefined for callers that don't
   *  supply it, which suppresses the caption rather than guessing. */
  isPeriodData?: boolean;
}

// Time-range presets wired to the existing `days` query param on the dashboard
// summary API — "All time" uses a wide window to capture the full history.
const TIME_RANGES: Array<{ label: string; value: string }> = [
  { label: "1M", value: "30" },
  { label: "6M", value: "180" },
  { label: "All time", value: "3650" },
];

// Compact number formatting for the pills (e.g. 7623 -> "7.6K").
const formatCompact = (n?: number): string => {
  if (n === undefined || n === null) return "-";
  if (Math.abs(n) >= 1000) return `${(n / 1000).toFixed(1).replace(/\.0$/, "")}K`;
  return String(n);
};

// Session duration in seconds -> "45s" / "2m 5s".
const formatDuration = (seconds?: number): string => {
  if (seconds === undefined || seconds === null) return "-";
  const s = Math.round(seconds);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return rem ? `${m}m ${rem}s` : `${m}m`;
};

// ---- Correlation helpers (Visibility vs Traffic tab) ----
const MONTH_INDEX: Record<string, number> = {
  Jan: 1, Feb: 2, Mar: 3, Apr: 4, May: 5, Jun: 6,
  Jul: 7, Aug: 8, Sep: 9, Oct: 10, Nov: 11, Dec: 12,
};

// The visibility series ("Oct 1") and the GA audience series ("1 Oct") format
// the same day in a different token order, so join on a normalized month-day
// key rather than the raw label.
const toDateKey = (label?: string): string | null => {
  if (!label) return null;
  let month: number | undefined;
  let day: number | undefined;
  for (const token of label.trim().split(/\s+/)) {
    if (MONTH_INDEX[token] !== undefined) month = MONTH_INDEX[token];
    else if (/^\d+$/.test(token)) day = parseInt(token, 10);
  }
  return month && day ? `${month}-${day}` : null;
};

const pearson = (pairs: Array<[number, number]>): number | null => {
  const n = pairs.length;
  if (n < 3) return null; // too few overlapping points to be meaningful
  let sx = 0, sy = 0, sxx = 0, syy = 0, sxy = 0;
  for (const [x, y] of pairs) {
    sx += x; sy += y; sxx += x * x; syy += y * y; sxy += x * y;
  }
  const denom = Math.sqrt((n * sxx - sx * sx) * (n * syy - sy * sy));
  if (denom === 0) return null;
  return (n * sxy - sx * sy) / denom;
};

const describeCorrelation = (r: number | null): string => {
  if (r === null) return "not enough overlap";
  const magnitude = Math.abs(r);
  const strength = magnitude >= 0.7 ? "strong" : magnitude >= 0.4 ? "moderate" : magnitude >= 0.2 ? "weak" : "negligible";
  const direction = r > 0 ? "positive" : r < 0 ? "negative" : "flat";
  return `${strength} ${direction}`;
};

interface PillProps {
  label: string;
  value?: number;
  /** Pre-formatted value (%, duration, correlation) — overrides formatCompact(value). */
  displayValue?: string;
  // Trend semantics:
  //   omitted (undefined) → no trend shown at all
  //   null                → "N/A" (metric has no prior-period comparison)
  //   number              → colored +-%
  change?: number | null;
  colorVar: string;
  /** Explanation shown on hover via styled UI Tooltip. */
  hint: string;
}

// Above this, a percentage stops informing and starts misleading — a jump from
// 8 to 3,700 is "+45,562%", which reads as a data error rather than as growth,
// when the real story is that tracking had barely started. Past this: "New".
const MAX_MEANINGFUL_CHANGE = 999;

const MetricPill = ({ label, value, displayValue, change, colorVar, hint }: PillProps) => {
  const showTrend = change !== undefined;
  const isNoData = change === null;
  const isUp = typeof change === "number" && change > 0;
  const isFlat = change === 0;
  const isNew = typeof change === "number" && change > MAX_MEANINGFUL_CHANGE;

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        <span className="h-2 w-2 rounded-full flex-shrink-0" style={{ backgroundColor: `hsl(var(--${colorVar}))` }} />
        <span>{label}</span>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <button type="button" className="inline-flex cursor-pointer text-muted-foreground opacity-50 hover:opacity-100 transition-opacity">
                <Info className="h-3 w-3 flex-shrink-0" />
              </button>
            </TooltipTrigger>
            <TooltipContent side="top" className="max-w-xs text-xs">
              {hint}
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
      <div className="flex items-baseline gap-1.5 flex-wrap">
        <span className="text-2xl font-bold tracking-tight text-foreground">{displayValue ?? formatCompact(value)}</span>
        {showTrend && (
          isNoData ? (
            <span className="text-xs text-muted-foreground">N/A</span>
          ) : isFlat ? (
            <span className="text-xs text-muted-foreground">0%</span>
          ) : isNew ? (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="text-xs font-semibold text-success cursor-default">New</span>
                </TooltipTrigger>
                <TooltipContent side="top" className="max-w-xs text-xs">
                  Grew from almost nothing in the previous period, so a percentage
                  would not be meaningful.
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          ) : (
            <span className={`text-xs font-semibold ${isUp ? "text-success" : "text-destructive"}`}>
              {isUp ? "+" : ""}{change}%
            </span>
          )
        )}
      </div>
    </div>
  );
};

type ChartTab = "main" | "aitraffic" | "visibility" | "correlation";

const CHART_TABS: Array<{ label: string; value: ChartTab }> = [
  { label: "Main Metrics", value: "main" },
  { label: "AI Traffic", value: "aitraffic" },
  { label: "AI Visibility", value: "visibility" },
  { label: "Visibility vs Traffic", value: "correlation" },
];

const TOOLTIP_STYLE = {
  backgroundColor: "hsl(var(--card))",
  border: "1px solid hsl(var(--border))",
  borderRadius: "var(--radius)",
} as const;

// Centered icon + message used by tabs that have no data yet.
const EmptyState = ({ title, subtitle }: { title: string; subtitle: string }) => (
  <div className="flex-1 min-h-[300px] flex flex-col items-center justify-center gap-3 text-muted-foreground">
    <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="opacity-40"><path d="M3 3v18h18" /><path d="m19 9-5 5-4-4-3 3" /></svg>
    <p className="text-sm font-medium">{title}</p>
    <p className="text-xs opacity-60">{subtitle}</p>
  </div>
);

export const TrendChart = ({ data = [], metrics, timeRange, onTimeRangeChange, aiTrafficDaily, shareOfVoice, aiTraffic, isPeriodData }: TrendChartProps) => {
  const [chartTab, setChartTab] = useState<ChartTab>("main");
  const hasCitationsSeries = data[0]?.citations !== undefined;
  const hasVisibilitySeries = data[0]?.visibility !== undefined;

  // ---- AI Traffic tab derived values ----
  const aiPlatformData = aiTraffic?.platform_breakdown
    ? Object.entries(aiTraffic.platform_breakdown)
        .map(([platform, pb]) => ({ platform, sessions: pb.visits ?? 0, users: pb.users ?? 0 }))
        .sort((a, b) => b.sessions - a.sessions)
    : [];
  const aiTotals = aiTraffic?.totals;
  const aiConvRate = aiTotals && (aiTotals.visits ?? 0) > 0
    ? ((aiTotals.conversions ?? 0) / (aiTotals.visits as number)) * 100
    : undefined;
  const aiEngagement = (() => {
    const pbs = aiTraffic?.platform_breakdown ? Object.values(aiTraffic.platform_breakdown) : [];
    let weight = 0;
    let weighted = 0;
    for (const pb of pbs) {
      const v = pb.visits ?? 0;
      weight += v;
      weighted += (pb.avgDuration ?? 0) * v;
    }
    return weight > 0 ? weighted / weight : undefined;
  })();

  // ---- Visibility vs Traffic (correlation) tab derived values ----
  const aiSessionsByDate = new Map<string, number>();
  for (const row of aiTrafficDaily ?? []) {
    const key = toDateKey(row.date);
    if (key) aiSessionsByDate.set(key, (aiSessionsByDate.get(key) ?? 0) + row.sessions);
  }
  const correlationData = data.map((d) => {
    const key = toDateKey(typeof d.date === "string" ? d.date : undefined);
    const sessions = key != null ? aiSessionsByDate.get(key) : undefined;
    return { date: d.date, visibility: d.visibility, sessions: sessions ?? null };
  });
  const correlationPairs = correlationData
    .filter((d) => typeof d.visibility === "number" && typeof d.sessions === "number")
    .map((d) => [d.visibility as number, d.sessions as number] as [number, number]);
  const correlationR = pearson(correlationPairs);
  const hasCorrelationSeries = correlationData.some((d) => d.sessions != null) && hasVisibilitySeries;
  const visibilityValues = correlationData.map((d) => d.visibility).filter((v): v is number => typeof v === "number");
  const avgVisibility = visibilityValues.length
    ? visibilityValues.reduce((a, b) => a + b, 0) / visibilityValues.length
    : undefined;
  const totalAiSessions = (aiTrafficDaily ?? []).reduce((a, r) => a + r.sessions, 0) || undefined;

  // Pills double as the chart's legend/summary, so they track the active tab:
  // each tab shows the metrics that match the series it plots. Values are
  // pulled from data the dashboard already fetches — no extra requests.
  const pills: PillProps[] = (() => {
    if (chartTab === "aitraffic") {
      return [
        { label: "AI Sessions", value: aiTotals?.visits, colorVar: "primary", hint: "Website sessions that arrived from AI platforms (ChatGPT, Gemini, Perplexity, Claude, Copilot…) in this period, from Google Analytics." },
        { label: "AI Users", value: aiTotals?.users, colorVar: "chart-2", hint: "Distinct users who reached your site from AI platforms in this period." },
        { label: "AI Conv. Rate", displayValue: aiConvRate !== undefined ? `${aiConvRate.toFixed(1)}%` : "-", colorVar: "chart-3", hint: "Share of AI-referred sessions that completed a conversion (conversions ÷ AI sessions) in this period." },
        { label: "Avg Engagement", displayValue: formatDuration(aiEngagement), colorVar: "secondary", hint: "Average session duration for AI-referred visits, weighted by sessions across AI platforms." },
      ];
    }
    if (chartTab === "visibility") {
      return [
        { label: "Visibility Score", value: metrics?.visibility_score, change: metrics?.visibility_change, colorVar: "secondary", hint: "Your AI Visibility score (0-100) for this period — how prominently your brand appears in AI answers. The percentage compares it with the previous period; N/A means no previous-period data." },
        // Avg Position: lower is better, so a signed +-% would read backwards
        // against the pill's up=good coloring — show the value without a delta.
        { label: "Avg Position", value: metrics?.avg_position, change: null, colorVar: "chart-2", hint: "Average rank of your brand when it appears in AI answers, across this period. Lower is better." },
        { label: "Share of Voice", value: shareOfVoice != null ? Math.round(shareOfVoice * 10) / 10 : undefined, change: null, colorVar: "chart-3", hint: "Your share of all brand mentions (yours plus tracked competitors') in AI answers for this period." },
      ];
    }
    if (chartTab === "correlation") {
      return [
        { label: "Avg Visibility", displayValue: avgVisibility !== undefined ? avgVisibility.toFixed(1) : "-", colorVar: "secondary", hint: "Average AI Visibility score across the period." },
        { label: "AI Sessions", value: totalAiSessions, colorVar: "primary", hint: "Total sessions arriving from AI platforms (ChatGPT, Gemini, Perplexity, Claude, Copilot…) over the period, from Google Analytics." },
        { label: "Correlation", displayValue: correlationR !== null ? `${correlationR.toFixed(2)} · ${describeCorrelation(correlationR)}` : "N/A", colorVar: "chart-3", hint: "Pearson correlation between the AI Visibility score and AI-referred sessions over matching dates. Ranges -1 to +1; a positive value means AI presence and AI-referred traffic tend to rise and fall together. Needs at least 3 overlapping dates." },
      ];
    }
    return [
      { label: "Mentions", value: metrics?.total_mentions, change: metrics?.mentions_change, colorVar: "primary", hint: "How many times your brand was mentioned in AI answers across your tracked prompts in this period. The percentage compares it with the previous period; N/A means there is no previous-period data to compare against." },
      { label: "Citations", value: metrics?.total_citations, change: metrics?.citations_change, colorVar: "chart-2", hint: "Every URL the AI cited in its answers during this period — the same total shown on the Citations page. Counts each citation, so one page cited several times counts more than once." },
      { label: "Cited Pages", value: metrics?.total_cited_pages, change: metrics?.cited_pages_change, colorVar: "chart-3", hint: "Distinct pages on your own domain that the AI cited in this period. Unlike Citations, each page is counted once no matter how often it was cited." },
    ];
  })();

  return (
    <Card className="p-6 h-full flex flex-col border border-border">
      {/* Top row: chart-type tabs (left) + time-range buttons (right) */}
      <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
        <div className="flex items-center gap-1 rounded-lg bg-muted/50 p-1">
          {CHART_TABS.map((tab) => (
            <button
              key={tab.value}
              type="button"
              onClick={() => setChartTab(tab.value)}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all ${
                chartTab === tab.value
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
        {onTimeRangeChange && (
          <div className="flex items-center gap-1 rounded-lg bg-muted/50 p-1">
            {TIME_RANGES.map((range) => (
              <button
                key={range.value}
                type="button"
                onClick={() => onTimeRangeChange(range.value)}
                className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all ${
                  timeRange === range.value
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {range.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Metric pills — double as the chart legend/summary, and track the active
          tab so the metrics shown always match the plotted series. Only shown
          when the dashboard supplies live metrics; other callers of TrendChart
          render exactly as before. */}
      {metrics && (
        <div className="flex items-center gap-12 mb-6 flex-wrap">
          {pills.map((pill) => (
            <MetricPill key={pill.label} {...pill} />
          ))}
        </div>
      )}

      {chartTab === "aitraffic" ? (
        aiPlatformData.length > 0 ? (
          <div className="flex-1 min-h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={aiPlatformData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="platform" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
                <RechartsTooltip contentStyle={TOOLTIP_STYLE} />
                <Legend />
                <Bar dataKey="sessions" name="AI Sessions" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                <Bar dataKey="users" name="AI Users" fill="hsl(var(--chart-2))" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <EmptyState
            title="No AI-referred traffic yet"
            subtitle="Connect Google Analytics to see sessions arriving from ChatGPT, Gemini, Perplexity and more."
          />
        )
      ) : chartTab === "correlation" ? (
        hasCorrelationSeries ? (
          <div className="flex-1 min-h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={correlationData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                <YAxis yAxisId="visibility" stroke="hsl(var(--secondary))" fontSize={12} domain={[0, 100]} />
                <YAxis yAxisId="sessions" orientation="right" stroke="hsl(var(--primary))" fontSize={12} />
                <RechartsTooltip contentStyle={TOOLTIP_STYLE} />
                <Legend />
                <Line
                  yAxisId="visibility"
                  type="monotone"
                  dataKey="visibility"
                  name="AI Visibility Score"
                  stroke="hsl(var(--secondary))"
                  strokeWidth={3}
                  dot={{ fill: "hsl(var(--secondary))", r: 4 }}
                  activeDot={{ r: 6 }}
                  connectNulls
                />
                <Line
                  yAxisId="sessions"
                  type="monotone"
                  dataKey="sessions"
                  name="AI-Referred Sessions"
                  stroke="hsl(var(--primary))"
                  strokeWidth={3}
                  dot={{ fill: "hsl(var(--primary))", r: 4 }}
                  activeDot={{ r: 6 }}
                  connectNulls
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <EmptyState
            title="Not enough data to compare"
            subtitle="Connect Google Analytics so we can chart AI Visibility against AI-referred traffic over time."
          />
        )
      ) : data.length === 0 ? (
        <EmptyState
          title="No trend data yet"
          subtitle="This chart fills in once your prompts have been tracked across AI platforms for the selected period."
        />
      ) : (
        /* Two nested boxes on purpose. ResponsiveContainer sizes itself to its
           parent, so any sibling in that same parent feeds its own height back
           into the measurement and the chart grows without bound on every
           re-measure. The inner `min-h-0` box therefore holds ONLY the chart,
           and the caption lives outside it. */
        <div className="flex-1 min-h-[300px] flex flex-col">
          <div className="flex-1 min-h-0">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis
                dataKey="date"
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
              />
              <YAxis
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
              />
              <RechartsTooltip contentStyle={TOOLTIP_STYLE} />
              <Legend />
              {/* AI Visibility tab — only the visibility score line */}
              {chartTab === "visibility" && hasVisibilitySeries && (
                <Line
                  type="monotone"
                  dataKey="visibility"
                  name="AI Visibility Score"
                  stroke="hsl(var(--secondary))"
                  strokeWidth={3}
                  dot={{ fill: "hsl(var(--secondary))", r: 4 }}
                  activeDot={{ r: 6 }}
                />
              )}
              {/* Main Metrics tab — Mentions + Citations + Cited Pages lines */}
              {chartTab === "main" && (
                <>
                  {data[0]?.value !== undefined && (
                    <Line
                      type="monotone"
                      dataKey="value"
                      name="Mentions"
                      stroke="hsl(var(--primary))"
                      strokeWidth={3}
                      dot={{ fill: "hsl(var(--primary))", r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                  )}
                  {data[0]?.mentions !== undefined && (
                    <Line
                      type="monotone"
                      dataKey="mentions"
                      name="Mentions"
                      stroke="hsl(var(--primary))"
                      strokeWidth={3}
                      dot={{ fill: "hsl(var(--primary))", r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                  )}
                  {hasCitationsSeries && (
                    <Line
                      type="monotone"
                      dataKey="citations"
                      name="Citations"
                      stroke="hsl(var(--chart-2))"
                      strokeWidth={3}
                      dot={{ fill: "hsl(var(--chart-2))", r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                  )}
                  {data[0]?.cited_pages !== undefined && (
                    <Line
                      type="monotone"
                      dataKey="cited_pages"
                      name="Cited Pages"
                      stroke="hsl(var(--chart-3))"
                      strokeWidth={3}
                      dot={{ fill: "hsl(var(--chart-3))", r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                  )}
                </>
              )}
            </LineChart>
          </ResponsiveContainer>
          </div>
          {/* Shown only while the API is still serving RUNNING TOTALS — i.e.
              snapshots written before the engine recorded per-period counts.
              Those totals can only climb, so a point reads "the total stood at X
              on this date", not "X happened on this date". Disappears by itself
              once the engine reprocesses and `trends_are_period` turns true. */}
          {isPeriodData === false && (
            <p className="mt-2 shrink-0 text-[11px] text-muted-foreground text-center">
              Running totals as at each date, not activity within the period.
            </p>
          )}
        </div>
      )}
    </Card>
  );
};
