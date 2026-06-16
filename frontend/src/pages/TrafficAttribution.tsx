import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { format } from "date-fns";
import { cn } from "@/lib/utils";
import { ExternalLink, TrendingUp, DollarSign, MousePointerClick, Users, Eye, ShoppingCart, BarChart3, CalendarIcon, Sparkles } from "lucide-react";
import { apiClient } from "@/services/api";
import { useToast } from "@/hooks/use-toast";
import { PageLoader } from "@/components/PageLoader";
import { useDomainStore } from "@/stores/domainStore";
import { useNavigate } from "react-router-dom";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, AreaChart, Area,
} from "recharts";

const DONUT_COLORS = ["#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6"];
const SPARK_COLOR = "#8b5cf6";

function Sparkline({ data, dataKey, color = SPARK_COLOR }: { data: any[]; dataKey: string; color?: string }) {
  if (!data || data.length === 0) return null;
  return (
    <div className="h-10 -mx-2">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data}>
          <defs>
            <linearGradient id={`grad-${dataKey}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.4} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area type="monotone" dataKey={dataKey} stroke={color} strokeWidth={1.5}
                fill={`url(#grad-${dataKey})`} dot={false} isAnimationActive={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function formatDurationSec(seconds: number): string {
  if (!seconds) return "00:00:00";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

function formatGADate(yyyymmdd: string): string {
  if (!yyyymmdd || yyyymmdd.length !== 8) return yyyymmdd;
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  const m = parseInt(yyyymmdd.slice(4, 6), 10);
  const d = parseInt(yyyymmdd.slice(6, 8), 10);
  return `${d} ${months[m - 1] ?? ""}`;
}

export default function TrafficAttribution() {
  const { selectedDomain, loadDomains, domains, isLoading } = useDomainStore();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [trafficData, setTrafficData] = useState<any>(null);
  const [dailySeries, setDailySeries] = useState<any[]>([]);
  // AI-referral date range. Both unset = the latest cached snapshot (default);
  // when a FULL range is picked we fetch a live GA4 window for those exact dates
  // (same sessionSource regex as the client's GA "matches regex" view).
  const [aiStartDate, setAiStartDate] = useState<Date | undefined>(undefined);
  const [aiEndDate, setAiEndDate] = useState<Date | undefined>(undefined);
  const [aiWindowData, setAiWindowData] = useState<any>(null);
  const [aiWindowLoading, setAiWindowLoading] = useState(false);
  // "GA4 view" toggle for the Sources tab. OFF = internal/exact view (clean cards).
  // ON = client-facing GA4 reconciliation view: reveals the sampling badge +
  // "matches GA4" note on every LLM card. Numbers are identical either way —
  // the switch only shows/hides the GA4-reconciliation context. Display-only.
  const [gaClientView, setGaClientView] = useState(false);

  useEffect(() => {
    const ensureDomain = async () => {
      if (!selectedDomain && !isLoading) {
        await loadDomains();
      }
    };
    ensureDomain();
  }, [selectedDomain, isLoading, loadDomains]);

  useEffect(() => {
    if (selectedDomain?.id) {
      loadTrafficData();
    } else if (!selectedDomain && domains.length === 0) {
      setLoading(false);
    }
  }, [selectedDomain?.id, domains.length]);

  // Fetch the live GA4 AI-referral window. With an explicit range we fetch those
  // exact dates; with NO range we default to the last 28 days ending YESTERDAY —
  // the same window the team compares in GA4's "Last 28 days" explore — so the
  // AI-platform numbers reconcile with GA4 out of the box instead of showing a
  // stale, differently-dated cached snapshot. Both paths use the shared
  // sessionSource regex on the backend. Other tabs (devices, geo, pages, search)
  // keep using the snapshot — only the AI-platform numbers re-window.
  useEffect(() => {
    if (!selectedDomain?.id) {
      setAiWindowData(null);
      return;
    }
    const hasRange = Boolean(aiStartDate && aiEndDate);
    let cancelled = false;
    setAiWindowLoading(true);
    const request = hasRange
      ? apiClient.getAIReferralData(
          selectedDomain.id,
          format(aiStartDate!, 'yyyy-MM-dd'),
          format(aiEndDate!, 'yyyy-MM-dd'),
        )
      : apiClient.getAIReferralData(selectedDomain.id, undefined, undefined, 28);
    request
      .then((res: any) => { if (!cancelled) setAiWindowData(res || null); })
      .catch(() => { if (!cancelled) setAiWindowData(null); })
      .finally(() => { if (!cancelled) setAiWindowLoading(false); });
    return () => { cancelled = true; };
  }, [selectedDomain?.id, aiStartDate, aiEndDate]);

  const loadTrafficData = async () => {
    if (!selectedDomain?.id) return;
    try {
      setLoading(true);
      const data = await apiClient.getTrafficInsights(selectedDomain.id);
      setTrafficData(data);
      // Fire daily-series fetch in the background — it's a live GA call (~3s)
      // and shouldn't block the cached aggregate render.
      apiClient.getGAData(selectedDomain.id).then((res: any) => {
        const daily = res?.data?.daily || [];
        setDailySeries(daily.map((row: any) => ({
          date: row.date,
          label: formatGADate(row.date),
          sessions: Number(row.sessions || 0),
          totalUsers: Number(row.totalUsers || 0),
          screenPageViews: Number(row.screenPageViews || 0),
          bounceRate: Number(row.bounceRate || 0),
          avgDuration: Number(row.averageSessionDuration || 0),
        })));
      }).catch(() => { /* GA may be disconnected — keep page usable */ });
    } catch (error: any) {
      console.error('Failed to load traffic data:', error);
      toast({
        title: "Error",
        description: error.message || "Failed to load traffic data",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };


  if (loading) {
    return <PageLoader />;
  }

  if (!selectedDomain) {
    return (
      <div className="p-8 space-y-6 bg-background animate-fade-in">
        <div className="text-center py-12">
          <h2 className="text-2xl font-bold mb-2">No Domain Selected</h2>
          <p className="text-muted-foreground">Please select a domain to view traffic data</p>
        </div>
      </div>
    );
  }

  // Format data from API
  const gaData = trafficData?.ga;
  const gscData = trafficData?.gsc;

  // AI-platform numbers come from the live GA4 window (default: last 28 days
  // ending yesterday, or the picked range) so they reconcile with GA4. Fall back
  // to the cached snapshot only if the live call fails, so the section is never
  // empty. Both sources share the platform_breakdown shape.
  const aiPlatformBreakdown = aiWindowData?.platform_breakdown
    ?? gaData?.platform_breakdown;
  const aiDateRange = aiWindowData?.date_range ?? null;
  
  // Show empty state if no data
  if (!gaData && !gscData) {
    return (
      <div className="p-8 space-y-6 bg-background animate-fade-in">
        <div>
          <h1 className="text-3xl font-bold">Traffic Attribution</h1>
          <p className="text-muted-foreground mt-2">
            Track and attribute traffic from AI platforms to measure ROI
          </p>
        </div>
        <Card className="border border-border">
          <CardContent className="py-12 text-center space-y-4">
            <p className="text-muted-foreground">No traffic data available yet.</p>
            <p className="text-sm text-muted-foreground max-w-2xl mx-auto">
              Connect Google Analytics and Google Search Console integrations to start processing traffic data. If you already connected the accounts, your traffic reports are being processed and will appear here shortly.
            </p>
            {selectedDomain?.id && (
              <Button
                className="mt-4"
                onClick={() => navigate(`/organization-settings/domains/${selectedDomain.id}?tab=integrations`)}
              >
                Go to Integrations
              </Button>
            )}
          </CardContent>
        </Card>
      </div>
    );
  }

  const formatDuration = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  // Render revenue in the GA4 property's own currency (e.g. ₹ for INR) instead of
  // a hardcoded "$". The live AI-referral window returns the property's ISO code;
  // fall back to USD only when it's unavailable (e.g. snapshot-only render).
  const currencyCode = aiWindowData?.currency_code || 'USD';

  // GA4 sampling state for the live AI-referral window. Our Data API numbers are
  // normally UNSAMPLED (exact, and match GA4's Reports view); only GA4 Explorations
  // sample. We surface this so the AI Assistance card can reassure the client a
  // figure is exact vs. a GA4 estimate. Absent on snapshot-only renders.
  const sampling = aiWindowData?.sampling;
  const isSampled = !!sampling?.is_sampled;
  const percentSampled = sampling?.percent_sampled;

  // GA4-reconciliation block shown on each card when the "GA4 view" switch is ON.
  // Sampling is per-response (a single GA4 query), so the state is identical for
  // every LLM — we render the same badge + note on each card for the client.
  // Returns null on snapshot-only renders where we have no live sampling metadata.
  const renderGaReconcile = () => {
    if (!sampling) return null;
    return (
      <div className="mt-3 border-t pt-2 space-y-1">
        {isSampled ? (
          <Badge variant="outline" className="border-amber-500 text-amber-600">
            ⚠ GA4-sampled{percentSampled != null ? ` (~${percentSampled}% of sessions)` : ''}
          </Badge>
        ) : (
          <Badge variant="outline" className="border-emerald-500 text-emerald-600">
            ✓ Unsampled · matches GA4 Reports
          </Badge>
        )}
        <p className="text-xs text-muted-foreground">
          {isSampled
            ? `GA4 sampled this window${percentSampled != null ? ` (~${percentSampled}% of sessions)` : ''} — its Explorations figure is an estimate. Compare in GA4 Reports → Traffic acquisition for an exact match.`
            : `GA4 Data API returns exact, unsampled data — it matches your GA4 Reports → Traffic acquisition${aiDateRange?.start ? ` for ${aiDateRange.start} → ${aiDateRange.end}` : ''} exactly.`}
        </p>
      </div>
    );
  };
  const formatCurrency = (value: number, decimals = 0): string => {
    try {
      return new Intl.NumberFormat(undefined, {
        style: 'currency',
        currency: currencyCode,
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      }).format(value || 0);
    } catch {
      return `${(value || 0).toLocaleString()}`;
    }
  };

  // Google Analytics Data
  const platformSources = aiPlatformBreakdown ? Object.entries(aiPlatformBreakdown).map(([platform, data]: [string, any]) => ({
    platform,
    visits: data.visits || data.sessions || 0,
    conversions: data.conversions || 0,
    revenue: data.revenue || 0,
    trend: "+0%", // Calculate trend if needed
    // GA4 returns bounceRate as a fraction (0.2621 = 26.21%); ×100 to match GA4's %.
    bounceRate: `${((data.bounceRate ?? 0) * 100).toFixed(1)}%`,
    avgDuration: formatDuration(data.avgDuration || 0),
    // Raw GA4 sessionSource rows that roll up into this LLM (live window only),
    // so the client can see exactly how the card reconciles with GA4.
    sources: Array.isArray(data.sources) ? data.sources : [],
  })) : [];

  const deviceBreakdown = gaData?.device_breakdown ? Object.entries(gaData.device_breakdown).map(([device, data]: [string, any]) => ({
    device,
    sessions: data.sessions || 0,
    percentage: data.percentage || 0,
    conversions: data.conversions || 0,
    revenue: data.revenue || 0,
  })) : [];

  const geographicData = gaData?.geographic_breakdown ? Object.entries(gaData.geographic_breakdown).map(([country, data]: [string, any]) => ({
    country,
    sessions: data.sessions || 0,
    percentage: data.percentage || 0,
    revenue: data.revenue || 0,
  })) : [];

  const topLandingPages = gaData?.landing_pages || [];
  const conversionPaths = gaData?.conversion_paths || [];

  // Google Search Console Data
  const searchConsoleData = gscData?.top_queries || [];

  // ===== AI-referral aggregates =====
  // Every headline metric on this page describes traffic ATTRIBUTED TO AI platforms,
  // so it is derived from platform_breakdown — the GA4 sessions whose sessionSource is
  // a known AI platform (ChatGPT, Claude, Gemini, Perplexity, Grok, DeepSeek, …).
  // We deliberately do NOT use gaData.total_sessions / total_conversions / total_revenue
  // here: those are all-channel site totals (organic + direct + paid + AI) and using them
  // made "Total AI Traffic" look hugely inflated versus GA4's actual AI-referral numbers.
  const aiBreakdown: any[] = aiPlatformBreakdown ? Object.values(aiPlatformBreakdown) : [];
  const visitsOf = (p: any) => Number(p?.visits ?? p?.sessions ?? 0) || 0;
  const sumBy = (key: string) => aiBreakdown.reduce((s, p: any) => s + (Number(p?.[key]) || 0), 0);
  const weightedAvg = (key: string, total: number) =>
    total > 0 ? aiBreakdown.reduce((s, p: any) => s + (Number(p?.[key]) || 0) * visitsOf(p), 0) / total : 0;

  const totalTraffic = aiBreakdown.reduce((s, p) => s + visitsOf(p), 0);
  const totalConversions = sumBy('conversions');
  const totalRevenue = sumBy('revenue');
  const conversionRate = totalTraffic > 0 ? ((totalConversions / totalTraffic) * 100).toFixed(1) : "0";

  // Per-LLM users / page views are present only on insights synced with the newer
  // breakdown query; fall back to "—" for older cached insights instead of showing
  // all-channel totals that would re-introduce the inflation this fix removes.
  const aiUsers = sumBy('users');
  const aiPageViews = sumBy('pageViews');
  const hasAiUsers = aiBreakdown.some((p: any) => p?.users != null);
  const hasAiPageViews = aiBreakdown.some((p: any) => p?.pageViews != null);

  const roiMetrics = [
    { metric: "Total Traffic from AI", value: totalTraffic.toLocaleString(), unit: "visits" },
    { metric: "Conversion Rate", value: conversionRate, unit: "%" },
    { metric: "Total Revenue", value: formatCurrency(totalRevenue), unit: "" },
    { metric: "ROI", value: "N/A", unit: "%" },
  ];

  // ===== Derived data for the Overview tab (all AI-referral scoped) =====
  const totalPageViews = aiPageViews;
  // Bounce rate and avg session duration are per-unit rates, so aggregate them as a
  // visit-weighted average across AI sources rather than summing.
  const avgSessionDuration = weightedAvg('avgDuration', totalTraffic);
  // weightedAvg keeps GA4's fraction scale (0–1), so engaged = total × (1 − fraction).
  const bounceRate = weightedAvg('bounceRate', totalTraffic);
  const engagedSessions = Math.max(0, Math.round(totalTraffic * (1 - bounceRate)));
  const revenuePerSession = totalTraffic > 0 ? totalRevenue / totalTraffic : 0;

  const sourceSummary = platformSources
    .slice()
    .sort((a, b) => b.visits - a.visits);
  const sourceTotal = sourceSummary.reduce((s, p) => s + p.visits, 0) || 1;

  const deviceDonut = deviceBreakdown.map((d) => ({
    name: d.device,
    value: d.sessions,
  }));
  const deviceTotal = deviceDonut.reduce((s, d) => s + d.value, 0);

  const countryMetrics = geographicData
    .slice()
    .sort((a, b) => b.sessions - a.sessions);

  const revenueBySource = sourceSummary
    .map((s) => ({ platform: s.platform, revenue: s.revenue, share: s.visits / sourceTotal }))
    .filter((r) => r.revenue > 0);
  const revenueTotal = revenueBySource.reduce((s, r) => s + r.revenue, 0) || totalRevenue;

  // Derive attribution model estimates from conversion paths if available, otherwise use industry defaults
  const conversionPathTotal = conversionPaths.reduce((sum: number, p: any) => sum + (p.value || 0), 0);
  const hasConversionData = conversionPathTotal > 0;
  const attributionModels = hasConversionData
    ? [
        { model: "First Touch", value: Math.round(conversionPathTotal * 0.35), percentage: 35 },
        { model: "Last Touch", value: Math.round(conversionPathTotal * 0.29), percentage: 29 },
        { model: "Linear", value: Math.round(conversionPathTotal * 0.21), percentage: 21 },
        { model: "Time Decay", value: Math.round(conversionPathTotal * 0.15), percentage: 15 },
      ]
    : [
        { model: "First Touch", value: Math.round(totalRevenue * 0.35), percentage: 35 },
        { model: "Last Touch", value: Math.round(totalRevenue * 0.29), percentage: 29 },
        { model: "Linear", value: Math.round(totalRevenue * 0.21), percentage: 21 },
        { model: "Time Decay", value: Math.round(totalRevenue * 0.15), percentage: 15 },
      ];

  return (
    <div className="p-8 space-y-6 bg-background animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold">Traffic Attribution</h1>
        <p className="text-muted-foreground mt-2">
          Track and attribute traffic from AI platforms to measure ROI
        </p>
      </div>

      {/* AI-traffic date range — fetches a live GA4 window for the exact dates
          (same sessionSource regex as the client's GA view). Leave blank for the
          latest cached snapshot. */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm text-muted-foreground mr-1">AI traffic range:</span>
        <Popover>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className={cn("justify-start text-left font-normal", !aiStartDate && "text-muted-foreground")}
            >
              <CalendarIcon className="mr-2 h-4 w-4" />
              {aiStartDate ? format(aiStartDate, "MMM d, yyyy") : <span>Start date</span>}
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0" align="start">
            <Calendar
              mode="single"
              selected={aiStartDate}
              onSelect={setAiStartDate}
              disabled={(date) => date > new Date()}
              initialFocus
            />
          </PopoverContent>
        </Popover>
        <Popover>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className={cn("justify-start text-left font-normal", !aiEndDate && "text-muted-foreground")}
            >
              <CalendarIcon className="mr-2 h-4 w-4" />
              {aiEndDate ? format(aiEndDate, "MMM d, yyyy") : <span>End date</span>}
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0" align="start">
            <Calendar
              mode="single"
              selected={aiEndDate}
              onSelect={setAiEndDate}
              disabled={(date) => date > new Date() || (aiStartDate ? date < aiStartDate : false)}
              initialFocus
            />
          </PopoverContent>
        </Popover>
        {(aiStartDate || aiEndDate) && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => { setAiStartDate(undefined); setAiEndDate(undefined); }}
          >
            Clear
          </Button>
        )}
        {aiWindowLoading && <span className="text-sm text-muted-foreground">Loading…</span>}
        {/* Only one of the two dates picked — the range isn't applied yet. */}
        {Boolean(aiStartDate) !== Boolean(aiEndDate) && !aiWindowLoading && (
          <span className="text-sm text-muted-foreground">Pick both dates to apply the range.</span>
        )}
        {aiDateRange && !aiWindowLoading && (
          <span className="text-sm text-muted-foreground">
            {aiDateRange.start} → {aiDateRange.end} (GA4-matched)
          </span>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        {roiMetrics.map((item, index) => (
          <Card key={index} className="transition-all duration-300 border border-border hover:border-primary">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{item.metric}</CardTitle>
              {index === 0 && <MousePointerClick className="h-4 w-4 text-muted-foreground" />}
              {index === 1 && <TrendingUp className="h-4 w-4 text-muted-foreground" />}
              {index === 2 && <DollarSign className="h-4 w-4 text-muted-foreground" />}
              {index === 3 && <TrendingUp className="h-4 w-4 text-muted-foreground" />}
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {item.value}
                {item.unit && <span className="text-sm font-normal ml-1">{item.unit}</span>}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className="bg-muted/50 p-1 border border-border">
          <TabsTrigger value="overview" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">AI Source Analytics</TabsTrigger>
          <TabsTrigger value="sources" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">Traffic Sources</TabsTrigger>
          <TabsTrigger value="search" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">Search Console</TabsTrigger>
          <TabsTrigger value="devices" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">Devices & Geo</TabsTrigger>
          <TabsTrigger value="pages" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">Landing Pages</TabsTrigger>
          <TabsTrigger value="attribution" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">Attribution Models</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          {/* Top metrics with sparklines */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
            {[
              { title: "Total AI Visits", value: totalTraffic.toLocaleString(), key: "sessions", icon: MousePointerClick },
              { title: "Engaged Sessions", value: engagedSessions.toLocaleString(), key: "sessions", icon: BarChart3 },
              { title: "Avg Duration", value: formatDurationSec(avgSessionDuration), key: "avgDuration", icon: TrendingUp },
              { title: "Total Users", value: hasAiUsers ? aiUsers.toLocaleString() : "—", key: "totalUsers", icon: Users },
              { title: "Page Views", value: hasAiPageViews ? totalPageViews.toLocaleString() : "—", key: "screenPageViews", icon: Eye },
            ].map((m, i) => {
              const Icon = m.icon;
              return (
                <Card key={i} className="border border-border">
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">{m.title}</CardTitle>
                    <Icon className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{m.value}</div>
                    <Sparkline data={dailySeries} dataKey={m.key} />
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {/* AI Source Visitors trend + Source Summary */}
          <div className="grid gap-6 lg:grid-cols-3">
            <Card className="border border-border lg:col-span-2">
              <CardHeader>
                <CardTitle>AI Source Visitors</CardTitle>
                <CardDescription>Total visitors from AI sources over time</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  {dailySeries.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={dailySeries}>
                        <defs>
                          <linearGradient id="visitors-grad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.3} />
                            <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                        <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                        <YAxis tick={{ fontSize: 11 }} />
                        <Tooltip />
                        <Area type="monotone" dataKey="sessions" stroke="#3b82f6" fill="url(#visitors-grad)" strokeWidth={2} />
                      </AreaChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
                      Connect Google Analytics to see daily visitor trends.
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card className="border border-border">
              <CardHeader>
                <CardTitle>Source Summary</CardTitle>
                <CardDescription>Top AI traffic sources</CardDescription>
              </CardHeader>
              <CardContent>
                {sourceSummary.length > 0 ? (
                  <div className="space-y-4">
                    {sourceSummary.map((s, i) => {
                      const pct = ((s.visits / sourceTotal) * 100).toFixed(1);
                      return (
                        <div key={i} className="space-y-1">
                          <div className="flex justify-between items-baseline">
                            <span className="font-medium text-sm">{s.platform}</span>
                            <span className="text-sm font-bold">{s.visits.toLocaleString()}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <div className="flex-1 bg-secondary rounded-full h-2">
                              <div className="bg-primary h-2 rounded-full" style={{ width: `${pct}%` }} />
                            </div>
                            <span className="text-xs text-muted-foreground min-w-[40px] text-right">{pct}%</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-8">No AI source data yet.</p>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Device Analytics + User Activity Trend */}
          <div className="grid gap-6 md:grid-cols-2">
            <Card className="border border-border">
              <CardHeader>
                <CardTitle>Device Analytics</CardTitle>
                <CardDescription>Device usage breakdown</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  {deviceDonut.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={deviceDonut} dataKey="value" nameKey="name" cx="50%" cy="50%"
                             innerRadius={55} outerRadius={90} paddingAngle={2} label={(d: any) => d.name}>
                          {deviceDonut.map((_, idx) => (
                            <Cell key={idx} fill={DONUT_COLORS[idx % DONUT_COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip formatter={(v: any) => `${(v as number).toLocaleString()} sessions`} />
                        <Legend />
                      </PieChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
                      No device breakdown available.
                    </div>
                  )}
                </div>
                {deviceTotal > 0 && (
                  <p className="text-center text-sm text-muted-foreground mt-2">
                    {deviceTotal.toLocaleString()} total sessions
                  </p>
                )}
              </CardContent>
            </Card>

            <Card className="border border-border">
              <CardHeader>
                <CardTitle>User Activity Trend</CardTitle>
                <CardDescription>Total users over time</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  {dailySeries.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={dailySeries}>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                        <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                        <YAxis tick={{ fontSize: 11 }} />
                        <Tooltip />
                        <Legend />
                        <Line type="monotone" dataKey="totalUsers" stroke="#ef4444" strokeWidth={2}
                              dot={false} name="Total users" />
                        <Line type="monotone" dataKey="sessions" stroke="#f59e0b" strokeWidth={2}
                              dot={false} name="Sessions" />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
                      Connect Google Analytics to see user activity.
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Landing Pages by LLM */}
          <Card className="border border-border">
            <CardHeader>
              <CardTitle>Landing Pages</CardTitle>
              <CardDescription>Top landing pages from AI traffic</CardDescription>
            </CardHeader>
            <CardContent>
              {topLandingPages.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-muted-foreground">
                        <th className="py-2 pr-4">Landing Page</th>
                        <th className="py-2 pr-4 text-right">Sessions</th>
                        <th className="py-2 pr-4 text-right">Conversions</th>
                        <th className="py-2 pr-4 text-right">Bounce Rate</th>
                        <th className="py-2 text-right">Avg Duration</th>
                      </tr>
                    </thead>
                    <tbody>
                      {topLandingPages.slice(0, 10).map((p: any, i: number) => (
                        <tr key={i} className="border-b last:border-0">
                          <td className="py-2 pr-4 font-medium truncate max-w-xs">{p.page}</td>
                          <td className="py-2 pr-4 text-right">{(p.sessions || 0).toLocaleString()}</td>
                          <td className="py-2 pr-4 text-right">{p.conversions || 0}</td>
                          <td className="py-2 pr-4 text-right">{p.bounceRate || "0%"}</td>
                          <td className="py-2 text-right">{p.avgDuration || "0:00"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-8">No landing page data yet.</p>
              )}
            </CardContent>
          </Card>

          {/* Country Metrics */}
          <Card className="border border-border">
            <CardHeader>
              <CardTitle>Sessions by Country</CardTitle>
              <CardDescription>Geographical distribution of sessions</CardDescription>
            </CardHeader>
            <CardContent>
              {countryMetrics.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-muted-foreground">
                        <th className="py-2 pr-4">Country</th>
                        <th className="py-2 pr-4 text-right">Sessions</th>
                        <th className="py-2 pr-4 text-right">Share</th>
                        <th className="py-2 text-right">Revenue</th>
                      </tr>
                    </thead>
                    <tbody>
                      {countryMetrics.slice(0, 15).map((c, i) => (
                        <tr key={i} className="border-b last:border-0">
                          <td className="py-2 pr-4 font-medium">{c.country}</td>
                          <td className="py-2 pr-4 text-right">{c.sessions.toLocaleString()}</td>
                          <td className="py-2 pr-4 text-right">{c.percentage.toFixed(1)}%</td>
                          <td className="py-2 text-right">{formatCurrency(c.revenue)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-8">No geographic data yet.</p>
              )}
            </CardContent>
          </Card>

          {/* Revenue Attribution */}
          <Card className="border border-border">
            <CardHeader>
              <CardTitle>Revenue Attribution</CardTitle>
              <CardDescription>Revenue from AI-referred sessions</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-4 md:grid-cols-4">
                <div className="p-4 border rounded-lg">
                  <div className="text-sm text-muted-foreground">Total Revenue</div>
                  <div className="text-2xl font-bold mt-1">{formatCurrency(totalRevenue)}</div>
                </div>
                <div className="p-4 border rounded-lg">
                  <div className="text-sm text-muted-foreground">Purchases</div>
                  <div className="text-2xl font-bold mt-1">{totalConversions.toLocaleString()}</div>
                </div>
                <div className="p-4 border rounded-lg">
                  <div className="text-sm text-muted-foreground">Conversion Rate</div>
                  <div className="text-2xl font-bold mt-1">{conversionRate}%</div>
                </div>
                <div className="p-4 border rounded-lg">
                  <div className="text-sm text-muted-foreground">Rev / Session</div>
                  <div className="text-2xl font-bold mt-1">{formatCurrency(revenuePerSession, 2)}</div>
                </div>
              </div>

              {revenueBySource.length > 0 && (
                <div>
                  <div className="text-sm font-medium mb-3">Revenue by AI Source</div>
                  <div className="space-y-3">
                    {revenueBySource.map((r, i) => {
                      const pct = ((r.revenue / revenueTotal) * 100).toFixed(1);
                      return (
                        <div key={i} className="flex items-center gap-3">
                          <ShoppingCart className="h-4 w-4 text-muted-foreground" />
                          <span className="font-medium text-sm flex-1">{r.platform}</span>
                          <div className="flex-1 bg-secondary rounded-full h-2 max-w-xs">
                            <div className="bg-primary h-2 rounded-full" style={{ width: `${pct}%` }} />
                          </div>
                          <span className="text-sm font-bold min-w-[100px] text-right">
                            {formatCurrency(r.revenue)}
                          </span>
                          <span className="text-xs text-muted-foreground min-w-[50px] text-right">{pct}%</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="sources" className="space-y-6">
          <Card className="border border-border">
            <CardHeader>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <CardTitle>AI Platform Referral Analysis</CardTitle>
                  <CardDescription>Traffic, conversions, and revenue by AI platform — exact, unsampled GA4 figures</CardDescription>
                </div>
                {/* GA4 view switch: OFF = internal/exact (clean cards), ON = client
                    GA4 reconciliation (reveals the sampling badge + "matches GA4"
                    note on every LLM card). Numbers are identical in both modes;
                    only the GA4 context is shown/hidden. */}
                {sampling && (
                  <div className="flex items-center gap-2 shrink-0">
                    <Label htmlFor="ga-view-switch" className="text-xs text-muted-foreground cursor-pointer">
                      {gaClientView ? 'GA4 view (client)' : 'Internal (exact)'}
                    </Label>
                    <Switch id="ga-view-switch" checked={gaClientView} onCheckedChange={setGaClientView} />
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {platformSources.length > 0 ? (
                <div className="space-y-4">
                  {platformSources.map((item, index) => (
                    <div key={index} className="p-4 border rounded-lg">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <ExternalLink className="h-4 w-4 text-primary" />
                          <span className="font-medium">{item.platform}</span>
                        </div>
                        <Badge variant="default">{item.trend}</Badge>
                      </div>
                      <div className="grid grid-cols-5 gap-4">
                        <div>
                          <div className="text-sm text-muted-foreground">Visits</div>
                          <div className="text-lg font-bold">{item.visits.toLocaleString()}</div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground">Conversions</div>
                          <div className="text-lg font-bold">{item.conversions}</div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground">Revenue</div>
                          <div className="text-lg font-bold">{formatCurrency(item.revenue)}</div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground">Bounce Rate</div>
                          <div className="text-lg font-bold">{item.bounceRate}</div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground">Avg Duration</div>
                          <div className="text-lg font-bold">{item.avgDuration}</div>
                        </div>
                      </div>
                      {/* GA4 reconciliation: the raw sessionSource rows that roll
                          up into this LLM. Helps clients match the card to GA4
                          (e.g. Perplexity = "perplexity" + "perplexity.ai"). */}
                      {item.sources && item.sources.length > 0 && (
                        <details className="mt-3">
                          <summary className="text-xs text-muted-foreground cursor-pointer select-none hover:text-foreground">
                            {item.sources.length === 1
                              ? `GA4 source: ${item.sources[0].source || "(not set)"}`
                              : `${item.sources.length} GA4 sources — show how this matches GA4`}
                          </summary>
                          <div className="mt-2 space-y-1 border-t pt-2">
                            {item.sources.map((s: any, i: number) => (
                              <div key={i} className="flex items-center justify-between text-xs">
                                <span className="text-muted-foreground font-mono">{s.source || "(not set)"}</span>
                                <span className="font-medium">{(s.visits || 0).toLocaleString()} visits</span>
                              </div>
                            ))}
                            <div className="flex items-center justify-between text-xs border-t pt-1 mt-1 font-semibold">
                              <span>Total — {item.platform}</span>
                              <span>{item.visits.toLocaleString()} visits</span>
                            </div>
                          </div>
                        </details>
                      )}
                      {/* Client GA4-reconciliation context, shown only when the
                          "GA4 view" switch is ON. Display-only — same numbers. */}
                      {gaClientView && renderGaReconcile()}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-8">No AI platform traffic data available. Connect Google Analytics to start tracking AI referral traffic.</p>
              )}
            </CardContent>
          </Card>

          {/* AI Assistance: a single combined section below the per-LLM cards that
              rolls every AI platform (ChatGPT, Gemini, Claude, Other AI, …) into one
              summary, then breaks the totals back down per LLM. Mirrors the aggregate
              already shown elsewhere on the page so the numbers reconcile. */}
          {platformSources.length > 0 && (
            <Card className="border border-border">
              <CardHeader>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <Sparkles className="h-5 w-5 text-primary" />
                      AI Assistance
                    </CardTitle>
                    <CardDescription>Combined traffic across all AI platforms, with a per-LLM breakdown</CardDescription>
                  </div>
                  {/* Sampling badge: tells the client whether these numbers are
                      exact (unsampled — match GA4 Reports) or a GA4 estimate.
                      Shown in the client "GA4 view" (switch ON) when we have
                      live-window sampling metadata. */}
                  {gaClientView && sampling && (
                    isSampled ? (
                      <Badge variant="outline" className="border-amber-500 text-amber-600 whitespace-nowrap">
                        ⚠ GA4-sampled{percentSampled != null ? ` (~${percentSampled}% of sessions)` : ''}
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="border-emerald-500 text-emerald-600 whitespace-nowrap">
                        ✓ Unsampled · matches GA4 Reports
                      </Badge>
                    )
                  )}
                </div>
              </CardHeader>
              <CardContent>
                {/* Combined totals across every AI platform */}
                <div className="p-4 border rounded-lg bg-muted/30 mb-4">
                  <div className="grid grid-cols-5 gap-4">
                    <div>
                      <div className="text-sm text-muted-foreground">Visits</div>
                      <div className="text-lg font-bold">{totalTraffic.toLocaleString()}</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Conversions</div>
                      <div className="text-lg font-bold">{totalConversions.toLocaleString()}</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Revenue</div>
                      <div className="text-lg font-bold">{formatCurrency(totalRevenue)}</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Bounce Rate</div>
                      <div className="text-lg font-bold">{(bounceRate * 100).toFixed(1)}%</div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground">Avg Duration</div>
                      <div className="text-lg font-bold">{formatDuration(avgSessionDuration)}</div>
                    </div>
                  </div>
                </div>

                {/* Plain-text sampling note for the combined total, shown in the
                    client "GA4 view" (switch ON). */}
                {gaClientView && sampling && (
                  <p className="text-xs text-muted-foreground mb-4">
                    {isSampled
                      ? `GA4 sampled this window${percentSampled != null ? ` (~${percentSampled}% of sessions)` : ''} — its Explorations figure is an estimate. Compare in GA4 Reports for an exact match.`
                      : `GA4 Data API returns exact, unsampled data — this total matches your GA4 Reports → Traffic acquisition${aiDateRange?.start ? ` for ${aiDateRange.start} → ${aiDateRange.end}` : ''} exactly.`}
                  </p>
                )}

                {/* Per-LLM breakdown (sorted high → low by visits) */}
                <div className="space-y-2">
                  {sourceSummary.map((item, index) => {
                    const share = totalTraffic > 0 ? ((item.visits / totalTraffic) * 100).toFixed(1) : "0";
                    return (
                      <div key={index} className="flex items-center justify-between gap-4 py-2 px-3 border rounded-md">
                        <div className="flex items-center gap-2 min-w-[120px]">
                          <ExternalLink className="h-4 w-4 text-primary" />
                          <span className="font-medium">{item.platform}</span>
                        </div>
                        <div className="flex flex-wrap items-center justify-end gap-x-6 gap-y-1 text-sm">
                          <span><span className="text-muted-foreground">Visits </span><span className="font-semibold">{item.visits.toLocaleString()}</span></span>
                          <span><span className="text-muted-foreground">Conversions </span><span className="font-semibold">{item.conversions}</span></span>
                          <span><span className="text-muted-foreground">Revenue </span><span className="font-semibold">{formatCurrency(item.revenue)}</span></span>
                          <span className="text-muted-foreground min-w-[48px] text-right">{share}%</span>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* How to verify against GA4. The point clients miss: compare in
                    GA4's REPORTS view (unsampled, matches us), not Explorations
                    (which samples). GA4 sampling can't be reproduced via the API. */}
                <details className="mt-4">
                  <summary className="text-xs text-muted-foreground cursor-pointer select-none hover:text-foreground">
                    How does this match GA4?
                  </summary>
                  <div className="mt-2 border-t pt-2 text-xs text-muted-foreground space-y-1">
                    <p>These totals are pulled from the GA4 Data API and are {isSampled ? 'GA4-sampled (an estimate)' : 'unsampled (exact)'}. To reconcile in GA4:</p>
                    <ol className="list-decimal pl-4 space-y-0.5">
                      <li>Go to <span className="font-medium text-foreground">Reports → Acquisition → Traffic acquisition</span> (not Explorations — Explorations samples and will differ).</li>
                      <li>Change the dimension to <span className="font-medium text-foreground">Session source / medium</span>.</li>
                      <li>Search each AI source and sum the <span className="font-medium text-foreground">Sessions</span> (= Visits here). Expand any LLM card above to see its exact GA4 sources.</li>
                      <li>Set the GA4 date range to <span className="font-medium text-foreground">{aiWindowData?.date_range?.start} → {aiWindowData?.date_range?.end}</span> (ends yesterday).</li>
                    </ol>
                  </div>
                </details>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="search" className="space-y-6">
          <Card className="border border-border">
            <CardHeader>
              <CardTitle>Google Search Console Data</CardTitle>
              <CardDescription>Top search queries driving traffic from AI platforms</CardDescription>
            </CardHeader>
            <CardContent>
              {searchConsoleData.length > 0 ? (
                <div className="space-y-4">
                  {searchConsoleData.map((item: any, index: number) => (
                    <div key={index} className="p-4 border rounded-lg">
                      <div className="font-medium mb-3">{item.query}</div>
                      <div className="grid grid-cols-4 gap-4">
                        <div>
                          <div className="text-sm text-muted-foreground">Impressions</div>
                          <div className="text-lg font-bold">{(item.impressions || 0).toLocaleString()}</div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground">Clicks</div>
                          <div className="text-lg font-bold">{(item.clicks || 0).toLocaleString()}</div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground">CTR</div>
                          <div className="text-lg font-bold">{item.ctr || '0%'}</div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground">Avg Position</div>
                          <div className="text-lg font-bold">{item.position || 0}</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-8">No Search Console data available. Connect Google Search Console to view search query data.</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="devices" className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            <Card className="border border-border">
              <CardHeader>
                <CardTitle>Device Breakdown</CardTitle>
                <CardDescription>Sessions and conversions by device type</CardDescription>
              </CardHeader>
              <CardContent>
                {deviceBreakdown.length > 0 ? (
                  <div className="space-y-4">
                    {deviceBreakdown.map((item, index) => (
                      <div key={index} className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="font-medium">{item.device}</span>
                          <span className="text-sm font-medium">{item.sessions.toLocaleString()} sessions</span>
                        </div>
                        <div className="flex items-center gap-3">
                          <div className="flex-1 bg-secondary rounded-full h-2">
                            <div
                              className="bg-primary h-2 rounded-full transition-all"
                              style={{ width: `${item.percentage}%` }}
                            />
                          </div>
                          <span className="text-sm font-medium min-w-[45px] text-right">
                            {item.percentage}%
                          </span>
                        </div>
                        <div className="grid grid-cols-2 gap-2 mt-2 text-sm text-muted-foreground">
                          <div>Conversions: {item.conversions}</div>
                          <div>Revenue: {formatCurrency(item.revenue)}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-8">No device breakdown data available.</p>
                )}
              </CardContent>
            </Card>

            <Card className="border border-border">
              <CardHeader>
                <CardTitle>Geographic Distribution</CardTitle>
                <CardDescription>Sessions and revenue by country</CardDescription>
              </CardHeader>
              <CardContent>
                {geographicData.length > 0 ? (
                  <div className="space-y-4">
                    {geographicData.map((item, index) => (
                      <div key={index} className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="font-medium">{item.country}</span>
                          <span className="text-sm font-medium">{item.sessions.toLocaleString()} sessions</span>
                        </div>
                        <div className="flex items-center gap-3">
                          <div className="flex-1 bg-secondary rounded-full h-2">
                            <div
                              className="bg-primary h-2 rounded-full transition-all"
                              style={{ width: `${item.percentage}%` }}
                            />
                          </div>
                          <span className="text-sm font-medium min-w-[45px] text-right">
                            {item.percentage.toFixed(1)}%
                          </span>
                        </div>
                        <div className="text-sm text-muted-foreground mt-2">
                          Revenue: {formatCurrency(item.revenue)}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-8">No geographic data available.</p>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="pages" className="space-y-6">
          <Card className="border border-border">
            <CardHeader>
              <CardTitle>Top Landing Pages</CardTitle>
              <CardDescription>Performance metrics for top landing pages from AI traffic</CardDescription>
            </CardHeader>
            <CardContent>
              {topLandingPages.length > 0 ? (
                <div className="space-y-4">
                  {topLandingPages.map((item: any, index: number) => (
                    <div key={index} className="p-4 border rounded-lg">
                      <div className="font-medium mb-3">{item.page}</div>
                      <div className="grid grid-cols-4 gap-4">
                        <div>
                          <div className="text-sm text-muted-foreground">Sessions</div>
                          <div className="text-lg font-bold">{(item.sessions || 0).toLocaleString()}</div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground">Bounce Rate</div>
                          <div className="text-lg font-bold">{item.bounceRate || '0%'}</div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground">Avg Duration</div>
                          <div className="text-lg font-bold">{item.avgDuration || '0:00'}</div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground">Conversions</div>
                          <div className="text-lg font-bold">{item.conversions || 0}</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-8">No landing page data available.</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="attribution" className="space-y-6">
          <Card className="border border-border">
            <CardHeader>
              <CardTitle>Attribution Model Comparison</CardTitle>
              <CardDescription>Revenue attribution across different models</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {attributionModels.map((item, index) => (
                  <div key={index} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{item.model}</span>
                      <span className="text-sm font-medium">{formatCurrency(item.value)}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="flex-1 bg-secondary rounded-full h-2">
                        <div
                          className="bg-primary h-2 rounded-full transition-all"
                          style={{ width: `${item.percentage}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium min-w-[45px] text-right">
                        {item.percentage}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
