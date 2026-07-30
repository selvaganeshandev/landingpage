import { useState } from "react";
import { Card } from "@/components/ui/card";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, Legend } from "recharts";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { InfoHint } from "@/components/InfoHint";

interface TrendMetrics {
  total_mentions?: number;
  mentions_change?: number | null;
  // Every URL the AI cited, whoever owns it. Kept for the Citations page and
  // as the denominator of citation_share — no longer a headline pill here,
  // because on a brand dashboard it read as the brand's own number.
  total_citations?: number;
  citations_change?: number | null;
  // Times THIS domain was cited. The brand-scoped figure, and the same measure
  // the trend line has always plotted.
  total_brand_citations?: number;
  brand_citations_change?: number | null;
  // Percent of all cited URLs that were this domain's. Delta is in points.
  citation_share?: number;
  citation_share_change?: number | null;
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
  data?: Array<{ date: string; date_iso?: string; period_start_iso?: string; value?: number; mentions?: number; citations?: number; visibility?: number; [key: string]: number | string | undefined }>;
  metrics?: TrendMetrics;
  // Currently-selected window as a `days` string ("30" | "180" | "3650"), or
  // undefined when a custom date range is active (no button highlighted).
  timeRange?: string;
  onTimeRangeChange?: (days: string) => void;
  // Daily AI-referred traffic (sessions/users by date) — feeds the Visibility
  // vs Traffic correlation tab.
  aiTrafficDaily?: Array<{ date: string; dateIso?: string; sessions: number; users: number }> | null;
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
  /** Whether the domain's Google Analytics integration is connected+active.
   *  Only `false` means "not connected" — undefined/null = unknown (still
   *  loading), so we never wrongly prompt a connected user to connect. */
  gaConnected?: boolean | null;
  /** The AI-referral (platform breakdown) fetch failed — e.g. GA4 hit its
   *  per-property hourly quota (429). Distinguishes "rate-limited" from
   *  "genuinely no AI traffic" in the empty state. */
  aiTrafficError?: boolean;
  /** The AI-referral timeseries fetch (correlation) failed, same idea. */
  aiTrafficDailyError?: boolean;
  /** API's `window.is_all_time`: the window was widened to cover the domain's
   *  entire history, so no previous period exists to compare against. The pills
   *  then hide the change outright instead of printing N/A for a comparison
   *  that could never have been made. */
  isAllTime?: boolean;
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
// The two series are joined on ISO dates supplied by the API, not on the
// year-less display labels ("Jul 28") they used to be matched on — those
// collided across years on any window longer than twelve months.

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
  /**
   * Unit for `change`. Defaults to "%". Metrics that are THEMSELVES a
   * percentage pass " pts": a share going 0.04 -> 0.20 is "+0.16 pts", whereas
   * rendering it as a percent-of-a-percent would print "+400%".
   */
  changeUnit?: string;
  colorVar: string;
  /** Explanation shown on hover via styled UI Tooltip. */
  hint: string;
}

// Above this, a percentage stops informing and starts misleading — a jump from
// 8 to 3,700 is "+45,562%", which reads as a data error rather than as growth,
// when the real story is that tracking had barely started. Past this: "New".
const MAX_MEANINGFUL_CHANGE = 999;

const MetricPill = ({ label, value, displayValue, change, changeUnit = "%", colorVar, hint }: PillProps) => {
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
        <InfoHint iconClassName="h-3 w-3">{hint}</InfoHint>
      </div>
      <div className="flex items-baseline gap-1.5 flex-wrap">
        <span className="text-2xl font-bold tracking-tight text-foreground">{displayValue ?? formatCompact(value)}</span>
        {showTrend && (
          isNoData ? (
            <span className="text-xs text-muted-foreground">N/A</span>
          ) : isFlat ? (
            <span className="text-xs text-muted-foreground">0{changeUnit}</span>
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
              {isUp ? "+" : ""}{change}{changeUnit}
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

export const TrendChart = ({ data = [], metrics, timeRange, onTimeRangeChange, aiTrafficDaily, shareOfVoice, aiTraffic, isPeriodData, gaConnected, aiTrafficError, aiTrafficDailyError, isAllTime }: TrendChartProps) => {
  const [chartTab, setChartTab] = useState<ChartTab>("main");

  // "Period before all time" is not a thing. Passing undefined (rather than
  // null) hides the comparison entirely — see PillProps for the semantics.
  const periodChange = (value?: number | null) => (isAllTime ? undefined : value);
  // Check every point, not just the first. A period whose visibility could not
  // be put on the current scale carries no `visibility` key at all, so testing
  // data[0] alone would hide the whole series whenever the earliest point
  // happened to be one of those.
  const hasCitationsSeries = data.some((d) => d.citations !== undefined);
  // Same rule as citations above, deliberately. This used to test data[0]
  // alone, so a series whose first point lacked the field hid a line that
  // every later point could have drawn.
  const hasCitedPagesSeries = data.some((d) => d.cited_pages !== undefined);
  const hasVisibilitySeries = data.some((d) => d.visibility !== undefined);

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
  //
  // Each trend point closes a PERIOD, not a day. Matching GA sessions on the
  // closing day alone threw away every other day's traffic: on one domain the
  // chart drew 3,089 sessions while the period totals were 16,388. So every GA
  // day is attributed to the period that contains it — the same way the backend
  // buckets analytics rows — and a point's sessions then cover exactly the span
  // its visibility describes.
  //
  // Matching is on ISO dates. The display labels carry no year, so "Jul 28"
  // from two different years used to collide on a window longer than a year.
  const correlationData = data.map((d, i) => {
    const periodEnd = typeof d.date_iso === "string" ? d.date_iso : undefined;
    const periodStart = typeof d.period_start_iso === "string" ? d.period_start_iso : undefined;
    let sessions: number | null = null;
    if (periodEnd && periodStart && aiTrafficDaily?.length) {
      let sum = 0;
      let matched = false;
      for (const row of aiTrafficDaily) {
        if (!row.dateIso) continue;
        if (row.dateIso >= periodStart && row.dateIso <= periodEnd) {
          sum += row.sessions;
          matched = true;
        }
      }
      if (matched) sessions = sum;
    }
    return { date: d.date, visibility: d.visibility, sessions };
  });
  const correlationPairs = correlationData
    .filter((d) => typeof d.visibility === "number" && typeof d.sessions === "number")
    .map((d) => [d.visibility as number, d.sessions as number] as [number, number]);
  const correlationR = pearson(correlationPairs);
  const hasCorrelationSeries = correlationData.some((d) => d.sessions != null) && hasVisibilitySeries;
  // NOTE: there is deliberately no "average of the plotted points" here.
  // Visibility is a rate, so the unweighted mean of per-period rates is not the
  // rate over the whole window: a period with one answer would count as much as
  // a period with 155. This pill previously did exactly that and reported ~17
  // beside the same metric's true 29.18 on the tab next door. The window figure
  // comes from the API, which pools the periods' own inputs.
  const totalAiSessions = (aiTrafficDaily ?? []).reduce((a, r) => a + r.sessions, 0) || undefined;

  // Pills double as the chart's legend/summary, so they track the active tab:
  // each tab shows the metrics that match the series it plots. Values are
  // pulled from data the dashboard already fetches — no extra requests.
  const pills: PillProps[] = (() => {
    if (chartTab === "aitraffic") {
      return [
        { label: "AI Sessions", value: aiTotals?.visits, colorVar: "primary", hint: "Website sessions that arrived from AI platforms (ChatGPT, Gemini, Perplexity, Claude, Copilot…) in this period, from Google Analytics." },
        { label: "AI Users", value: aiTotals?.users, colorVar: "chart-2", hint: "Distinct users who reached your site from AI platforms in this period." },
        // The raw numerator behind AI Conv. Rate. Shown next to it so a
        // surprising rate can be read against the count it came from — a high
        // percentage off 3 conversions means something different from the same
        // percentage off 300.
        { label: "AI Conversions", value: aiTotals?.conversions, colorVar: "chart-4", hint: "Key events (conversions) completed during AI-referred sessions in this period, straight from Google Analytics. Which events count is set by the key events you marked in your GA4 property, so a low-bar event like a page view will inflate this. GA4 counts events, not sessions, so one session firing two key events counts twice." },
        { label: "AI Conv. Rate", displayValue: aiConvRate !== undefined ? `${aiConvRate.toFixed(1)}%` : "-", colorVar: "chart-3", hint: "Share of AI-referred sessions that completed a conversion (conversions ÷ AI sessions) in this period." },
      ];
    }
    if (chartTab === "visibility") {
      return [
        { label: "Visibility Score", value: metrics?.visibility_score, change: periodChange(metrics?.visibility_change), colorVar: "secondary", hint: "Your AI Visibility score (0-100) for this window — how prominently your brand appears in AI answers. Each point on the line scores its own period; this figure scores the whole window at once, so a period with more answers counts for more. It will not equal a plain average of the points. The percentage compares it with the previous period; N/A means no previous-period data." },
        // Avg Position: lower is better, so a signed +-% would read backwards
        // against the pill's up=good coloring — show the value without a delta.
        { label: "Avg Position", value: metrics?.avg_position, change: null, colorVar: "chart-2", hint: "Average rank of your brand when it appears in AI answers, across this period. Lower is better." },
        // Google Analytics, unlike the three pills beside it — it measures what
        // AI-referred visitors did on the site, not how the AI answers read. It
        // shows "-" whenever GA is not connected, since nothing else on this tab
        // depends on GA.
        { label: "Avg Engagement", displayValue: formatDuration(aiEngagement), colorVar: "chart-4", hint: "Average session duration for visits that arrived from AI platforms, weighted by sessions across those platforms. From Google Analytics — shows '-' when GA is not connected." },
        { label: "Share of Voice", value: shareOfVoice != null ? Math.round(shareOfVoice * 10) / 10 : undefined, change: null, colorVar: "chart-3", hint: "Your share of all brand mentions (yours plus tracked competitors') in AI answers for this period." },
      ];
    }
    if (chartTab === "correlation") {
      return [
        { label: "Visibility Score", value: metrics?.visibility_score, colorVar: "secondary", hint: "Your AI Visibility score (0-100) for this window — the same figure shown on the AI Visibility tab and on the gauge. Scored over every answer in the window at once, so periods with more answers count for more. It is not the average of the plotted points." },
        { label: "AI Sessions", value: totalAiSessions, colorVar: "primary", hint: "Total sessions arriving from AI platforms (ChatGPT, Gemini, Perplexity, Claude, Copilot…) over the period, from Google Analytics." },
        {
          label: "Correlation",
          displayValue: correlationR !== null ? `${correlationR.toFixed(2)} · ${describeCorrelation(correlationR)}` : "N/A",
          colorVar: "chart-3",
          hint: correlationR !== null
            ? `Does your AI visibility move together with the traffic AI sends you? Each point below is one period: its visibility score, paired with every Google Analytics session that arrived from an AI platform during that same period. We run a Pearson correlation across those ${correlationPairs.length} pairs. The result runs from -1 to +1 — near +1 they rise and fall together, near 0 there is no relationship, near -1 one rises as the other falls. It shows association, not cause: traffic can move for reasons that have nothing to do with AI answers.`
            : `Not enough paired periods yet. This compares each period's visibility score against the AI-referred sessions Google Analytics recorded in that same period, and needs at least 3 periods that have both. Right now ${correlationPairs.length} qualify — periods whose visibility could not be scored on the current formula, or where no GA data exists, are left out.`,
        },
      ];
    }
    return [
      { label: "Mentions", value: metrics?.total_mentions, change: periodChange(metrics?.mentions_change), colorVar: "primary", hint: "How many times your brand was mentioned in AI answers across your tracked prompts in this period. The percentage compares it with the previous period; N/A means there is no previous-period data to compare against." },
      // Was "Citations" showing total_citations — every URL in every answer,
      // overwhelmingly other people's sites. It sat beside a trend line plotting
      // this domain's own citations, so the card showed two numbers orders of
      // magnitude apart under one word. This is now the brand-scoped figure the
      // line has always drawn, and the old total moved into Citation Share.
      { label: "Your Citations", value: metrics?.total_brand_citations, change: periodChange(metrics?.brand_citations_change), colorVar: "chart-2", hint: "How many times AI answers linked to a page on your own domain in this period. Counts each link, so one page cited several times counts more than once — Cited Pages counts those same links once per page. The 'Sources Cited' line below plots every source in the answers, yours and everyone else's, so it is a much larger number." },
      { label: "Cited Pages", value: metrics?.total_cited_pages, change: periodChange(metrics?.cited_pages_change), colorVar: "chart-3", hint: "Distinct pages on your own domain that the AI cited in this period. Unlike Your Citations, each page is counted once no matter how often it was cited." },
      {
        label: "Citation Share",
        displayValue: metrics?.citation_share !== undefined ? `${metrics.citation_share.toFixed(2)}%` : "-",
        // Points, not percent-of-percent: a share moving 0.04 -> 0.20 is
        // "+0.16 pts", never "+400%".
        change: periodChange(metrics?.citation_share_change),
        changeUnit: " pts",
        colorVar: "chart-4",
        hint: `Of every source AI cited in this period, the share that was your domain${
          metrics?.total_brand_citations !== undefined && metrics?.total_citations !== undefined
            ? ` — your domain was cited ${metrics.total_brand_citations.toLocaleString()} time(s) out of ${metrics.total_citations.toLocaleString()} sources cited across all answers`
            : ""
        }. This is the number that says whether AI treats you as a source worth quoting.`,
      },
    ];
  })();

  // Empty-state copy for the GA-dependent tabs. Critically, only prompt to
  // "Connect Google Analytics" when we KNOW GA is disconnected (gaConnected ===
  // false). If GA is connected but the fetch failed, it's almost always GA4's
  // per-property hourly quota (429) — say so, don't imply it's disconnected.
  const RATE_LIMIT_SUBTITLE = "Google Analytics is temporarily rate-limited for this property (GA4 caps how many reports a property can run per hour). It usually clears within an hour — try again shortly.";
  const aiTrafficEmpty = gaConnected === false
    ? { title: "Connect Google Analytics", subtitle: "Connect GA to see sessions arriving from ChatGPT, Gemini, Perplexity, Claude and more." }
    : aiTrafficError
      ? { title: "Couldn't load AI traffic", subtitle: RATE_LIMIT_SUBTITLE }
      : { title: "No AI-referred traffic in this period", subtitle: "No sessions arrived from AI platforms in the selected window. Try a wider time range." };
  const correlationEmpty = gaConnected === false
    ? { title: "Connect Google Analytics", subtitle: "Connect GA so we can chart AI Visibility against AI-referred traffic over time." }
    : aiTrafficDailyError
      ? { title: "Couldn't load AI traffic", subtitle: RATE_LIMIT_SUBTITLE }
      : { title: "Not enough overlapping data", subtitle: "We need AI-referred traffic and visibility on the same dates to chart the correlation. Try a wider time range." };

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
          <EmptyState title={aiTrafficEmpty.title} subtitle={aiTrafficEmpty.subtitle} />
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
          <EmptyState title={correlationEmpty.title} subtitle={correlationEmpty.subtitle} />
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
                      // ALL citations in the answers, not the domain's own:
                      // snapshots store period_citations as the full count
                      // (Tata Motors plots 1199 while only 8 of its own pages
                      // were cited). Named for what it plots, so it can never
                      // be read as the brand's own figure again.
                      name="Sources Cited"
                      stroke="hsl(var(--chart-2))"
                      strokeWidth={3}
                      dot={{ fill: "hsl(var(--chart-2))", r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                  )}
                  {hasCitedPagesSeries && (
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
