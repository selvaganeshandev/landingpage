import { useState } from "react";
import { Card } from "@/components/ui/card";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { TrendingUp, TrendingDown } from "lucide-react";

const defaultData = [
  { date: "Oct 1", mentions: 45, visibility: 72 },
  { date: "Oct 8", mentions: 52, visibility: 78 },
  { date: "Oct 15", mentions: 61, visibility: 82 },
  { date: "Oct 22", mentions: 58, visibility: 85 },
  { date: "Oct 29", mentions: 67, visibility: 88 },
  { date: "Nov 5", mentions: 73, visibility: 91 },
  { date: "Nov 12", mentions: 84, visibility: 94 },
];

interface TrendMetrics {
  total_mentions?: number;
  mentions_change?: number | null;
  total_citations?: number;
  citations_change?: number | null;
  total_cited_pages?: number;
  cited_pages_change?: number | null;
}

interface TrendChartProps {
  data?: Array<{ date: string; value?: number; mentions?: number; citations?: number; visibility?: number; [key: string]: number | string | undefined }>;
  metrics?: TrendMetrics;
  // Currently-selected window as a `days` string ("30" | "180" | "3650"), or
  // undefined when a custom date range is active (no button highlighted).
  timeRange?: string;
  onTimeRangeChange?: (days: string) => void;
  audienceData?: Array<{ date: string; sessions: number; users: number }> | null;
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

interface PillProps {
  label: string;
  value?: number;
  change?: number | null;
  colorVar: string;
}

const MetricPill = ({ label, value, change, colorVar }: PillProps) => {
  // Always show trend next to value:
  // • null / undefined  → "N/A" (no prior-period data)
  // • 0                → "0%"  (flat)
  // • non-zero number  → colored +-%
  const isNoData = change === undefined || change === null;
  const isUp = !isNoData && change > 0;
  const isFlat = !isNoData && change === 0;

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        <span className="h-2 w-2 rounded-full flex-shrink-0" style={{ backgroundColor: `hsl(var(--${colorVar}))` }} />
        <span>{label}</span>
        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="opacity-40 cursor-help flex-shrink-0"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
      </div>
      <div className="flex items-baseline gap-1.5 flex-wrap">
        <span className="text-2xl font-bold tracking-tight text-foreground">{formatCompact(value)}</span>
        {isNoData ? (
          <span className="text-xs text-muted-foreground">N/A</span>
        ) : isFlat ? (
          <span className="text-xs text-muted-foreground">0%</span>
        ) : (
          <span className={`text-xs font-semibold ${isUp ? "text-success" : "text-destructive"}`}>
            {isUp ? "+" : ""}{change}%
          </span>
        )}
      </div>
    </div>
  );
};

type ChartTab = "main" | "audience" | "visibility";

const CHART_TABS: Array<{ label: string; value: ChartTab }> = [
  { label: "Main Metrics", value: "main" },
  { label: "Monthly Audience", value: "audience" },
  { label: "AI Visibility", value: "visibility" },
];

export const TrendChart = ({ data = defaultData, metrics, timeRange, onTimeRangeChange, audienceData }: TrendChartProps) => {
  const [chartTab, setChartTab] = useState<ChartTab>("main");
  const hasCitationsSeries = data[0]?.citations !== undefined;
  const hasVisibilitySeries = data[0]?.visibility !== undefined;

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

      {/* Metric pills — double as the chart legend/summary (Feature B). Only
          shown when the dashboard supplies live metrics; other callers of
          TrendChart render exactly as before. */}
      {metrics && (
        <div className="flex items-center gap-12 mb-6 flex-wrap">
          <MetricPill label="Mentions" value={metrics.total_mentions} change={metrics.mentions_change} colorVar="primary" />
          <MetricPill label="Citations" value={metrics.total_citations} change={metrics.citations_change} colorVar="chart-2" />
          <MetricPill label="Cited Pages" value={metrics.total_cited_pages} change={metrics.cited_pages_change} colorVar="chart-3" />
        </div>
      )}

      {chartTab === "audience" ? (
        audienceData && audienceData.length > 0 ? (
          <div className="flex-1 min-h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={audienceData}>
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
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "var(--radius)",
                  }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="sessions"
                  name="Monthly Sessions"
                  stroke="hsl(var(--primary))"
                  strokeWidth={3}
                  dot={{ fill: "hsl(var(--primary))", r: 4 }}
                  activeDot={{ r: 6 }}
                />
                <Line
                  type="monotone"
                  dataKey="users"
                  name="Monthly Users"
                  stroke="hsl(var(--chart-2))"
                  strokeWidth={3}
                  dot={{ fill: "hsl(var(--chart-2))", r: 4 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          /* Monthly Audience tab — placeholder until audience data is wired */
          <div className="flex-1 min-h-[300px] flex flex-col items-center justify-center gap-3 text-muted-foreground">
            <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="opacity-40"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
            <p className="text-sm font-medium">Monthly Audience data coming soon</p>
            <p className="text-xs opacity-60">Connect your analytics integration to enable this view.</p>
          </div>
        )
      ) : (
        <div className="flex-1 min-h-[300px]">
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
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "var(--radius)",
                }}
              />
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
              {/* Main Metrics tab — Mentions + Citations lines */}
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
      )}
    </Card>
  );
};
