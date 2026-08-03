import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageLoader } from "@/components/PageLoader";
import { useToast } from "@/hooks/use-toast";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { 
  LineChart, 
  Line, 
  AreaChart,
  Area,
  BarChart,
  Bar,
  ComposedChart,
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Legend 
} from "recharts";
import { 
  Calendar,
  TrendingUp,
  TrendingDown,
  Target,
  FileText,
  Download
} from "lucide-react";
import { useEffect, useState, useMemo } from "react";
import { apiClient } from "@/services/api";
import { useAuth } from "@/contexts/AuthContext";
import { getActiveDomainId } from "@/utils/activeDomain";
import { downloadCsv } from "@/utils/exportCsv";
import { useDomainStore } from "@/stores/domainStore";

const HistoricalTrends = () => {
  const { toast } = useToast();
  const { user } = useAuth();
  const { selectedDomain } = useDomainStore();
  const [domainId, setDomainId] = useState<string | null>(null);
  const [months, setMonths] = useState<number>(12);
  const [trendsData, setTrendsData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Sync domainId from selectedDomain (Zustand store) or localStorage when domain changes
  useEffect(() => {
    if (!user) return;

    if (selectedDomain?.id) {
      const newDomainId = String(selectedDomain.id);
      if (newDomainId !== domainId) {
        setDomainId(newDomainId);
        return;
      }
    }

    const id = getActiveDomainId(user);
    if (id && id !== domainId) setDomainId(id);
  }, [user, selectedDomain?.id, domainId]);

  useEffect(() => {
    const load = async () => {
      if (!domainId) return;
      setIsLoading(true);
      try {
        const data = await apiClient.getHistoricalTrends({ domain_id: domainId, months });
        setTrendsData(data);
      } catch (e:any) {
        // Only show error if it's not a 404 (empty data is expected)
        const errorMessage = e?.message || String(e);
        const isNotFound = errorMessage.includes('404') || errorMessage.includes('Not Found');
        if (!isNotFound) {
          toast({ 
            title: 'Failed to load historical trends', 
            description: errorMessage, 
            variant: 'destructive' 
          });
        }
        // Set empty data structure on error
        setTrendsData({
          visibility_trend: [],
          platform_growth: [],
          competitor_comparison: [],
          seasonal_pattern: [],
          forecast: [],
          milestones: [],
          summary: {
            visibility_growth: 0,
            mention_growth: 0,
            position_improvement: 0,
            market_share_gain: 0
          }
        });
      } finally {
        setIsLoading(false);
      }
    };
    void load();
  }, [domainId, months]);

  const visibilityTrend = useMemo(() => {
    if (!trendsData?.visibility_trend) return [];
    return trendsData.visibility_trend.map((v:any) => ({
      month: v.month,
      score: v.visibility_score || 0,
      mentions: v.mentions || 0,
      avgPosition: v.avg_position || 0,
      sentiment: v.sentiment || 0,
    }));
  }, [trendsData]);

  const platformGrowth = useMemo(() => trendsData?.platform_growth || [], [trendsData]);
  const competitorComparison = useMemo(() => trendsData?.competitor_comparison || [], [trendsData]);
  const seasonalPattern = useMemo(() => trendsData?.seasonal_pattern || [], [trendsData]);
  const summary = useMemo(() => trendsData?.summary || { visibility_growth: 0, mention_growth: 0, position_improvement: 0, market_share_gain: 0 }, [trendsData]);
  
  // Forecast - get from API
  const forecast = useMemo(() => trendsData?.forecast || [], [trendsData]);
  
  // Milestones - get from API
  const milestones = useMemo(() => trendsData?.milestones || [], [trendsData]);

  // A trend needs two points. With one, every chart below draws a single dot
  // and every growth figure is 0% — indistinguishable from a genuinely flat
  // period, which is a different statement entirely.
  const periodCount = visibilityTrend.length;
  const hasComparablePeriods = periodCount >= 2;
  const latestPeriodLabel = periodCount > 0 ? visibilityTrend[periodCount - 1]?.month : null;

  const handleExportReport = () => {
    const exportRows: Record<string, string | number>[] = [];

    // Visibility trend rows
    visibilityTrend.forEach((v: any) => {
      exportRows.push({
        section: 'Visibility Trend',
        month: v.month,
        visibility_score: v.score,
        mentions: v.mentions,
        avg_position: v.avgPosition,
        sentiment: v.sentiment,
        chatgpt: '',
        claude: '',
        perplexity: '',
        gemini: '',
      });
    });

    // Platform growth rows
    platformGrowth.forEach((p: any) => {
      exportRows.push({
        section: 'Platform Growth',
        month: p.month,
        visibility_score: '',
        mentions: '',
        avg_position: '',
        sentiment: '',
        chatgpt: p.chatgpt || 0,
        claude: p.claude || 0,
        perplexity: p.perplexity || 0,
        gemini: p.gemini || 0,
      });
    });

    // Summary row
    exportRows.push({
      section: 'Summary',
      month: '',
      visibility_score: `${summary.visibility_growth}%`,
      mentions: `${summary.mention_growth}%`,
      avg_position: `${summary.position_improvement}%`,
      sentiment: `${summary.market_share_gain}%`,
      chatgpt: '',
      claude: '',
      perplexity: '',
      gemini: '',
    });

    const headers = [
      { key: 'section', label: 'Section' },
      { key: 'month', label: 'Month' },
      { key: 'visibility_score', label: 'Visibility Score' },
      { key: 'mentions', label: 'Mentions' },
      { key: 'avg_position', label: 'Avg Position' },
      { key: 'sentiment', label: 'Sentiment' },
      { key: 'chatgpt', label: 'ChatGPT' },
      { key: 'claude', label: 'Claude' },
      { key: 'perplexity', label: 'Perplexity' },
      { key: 'gemini', label: 'Gemini' },
    ];

    const today = new Date().toISOString().split('T')[0];
    downloadCsv(exportRows, headers, `historical_trends_${today}.csv`);

    toast({
      title: "Report Exported",
      description: "Your historical trends report has been downloaded.",
    });
  };

  if (isLoading) {
    return <PageLoader />;
  }

  // Check if we have any data
  const hasData = trendsData && (
    (trendsData.visibility_trend && trendsData.visibility_trend.length > 0) ||
    (trendsData.platform_growth && trendsData.platform_growth.length > 0)
  );

  if (!hasData) {
    return (
      <div className="p-8 space-y-8">
        <div className="flex items-center justify-between pb-4">
          <div>
            <h1 className="text-4xl font-bold tracking-tight">Historical Trends</h1>
            <p className="text-muted-foreground mt-2">
              Long-term performance tracking and forecasting
            </p>
          </div>
        </div>
        <Card className="p-12 border border-border">
          <div className="flex flex-col items-center justify-center text-center">
            <p className="text-muted-foreground text-lg mb-2">No historical trends data available</p>
            <p className="text-muted-foreground text-sm">
              Historical trends will appear here once you have sufficient data collected over time.
            </p>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8 bg-background animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Historical Trends</h1>
          <p className="text-muted-foreground mt-2">
            Long-term performance tracking and forecasting
          </p>
        </div>
        <div className="flex gap-3">
          <Select value={String(months)} onValueChange={(v) => setMonths(Number(v))}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Time Range" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="3">Last 3 Months</SelectItem>
              <SelectItem value="6">Last 6 Months</SelectItem>
              <SelectItem value="12">Last 12 Months</SelectItem>
              <SelectItem value="24">Last 24 Months</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={handleExportReport} className="gradient-primary shadow-md shadow-primary/20">
            <Download className="h-4 w-4 mr-2" />
            Export Report
          </Button>
        </div>
      </div>

      {/* Summary Cards
          Every card used to be hardcoded text-success with a rising arrow, so a
          decline rendered as "-12%" in green beside an up arrow. Direction now
          follows the value, and Position Improvement inverts because a lower
          average position is the better outcome. */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {[
          {
            label: "Visibility Growth",
            value: summary.visibility_growth,
            caption: "Over period",
            goodWhenPositive: true,
          },
          {
            label: "Mention Growth",
            value: summary.mention_growth,
            caption: "Over period",
            goodWhenPositive: true,
          },
          {
            label: "Position Improvement",
            value: summary.position_improvement,
            caption: "Lower average position is better",
            goodWhenPositive: true,
          },
          {
            label: "Market Share Gain",
            value: summary.market_share_gain,
            caption: "Over period",
            goodWhenPositive: true,
          },
        ].map((card) => {
          const rising = card.value > 0;
          const flat = card.value === 0;
          const good = card.goodWhenPositive ? rising : !rising;
          const tone = flat ? "text-muted-foreground" : good ? "text-success" : "text-destructive";
          return (
            <Card key={card.label} className="p-6 border border-border">
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">{card.label}</p>
                <h3 className={`text-2xl font-bold ${tone}`}>
                  {rising ? "+" : ""}{card.value}%
                </h3>
                <div className="flex items-center gap-2 text-xs">
                  {flat ? (
                    <span className="text-muted-foreground">
                      {hasComparablePeriods ? "No change over period" : "Not enough history to compare"}
                    </span>
                  ) : (
                    <>
                      {rising
                        ? <TrendingUp className={`h-3 w-3 ${tone}`} />
                        : <TrendingDown className={`h-3 w-3 ${tone}`} />}
                      <span className="text-muted-foreground">{card.caption}</span>
                    </>
                  )}
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      {/* A single data point is not a trend. Every chart below plots a series
          that needs at least two periods, so say so once rather than drawing
          five charts each showing one dot. */}
      {!hasComparablePeriods && (
        <Card className="p-6 border border-dashed border-border bg-card/70">
          <div className="flex gap-4 items-start">
            <div className="p-3 rounded-full bg-muted text-muted-foreground">
              <TrendingUp className="h-5 w-5" />
            </div>
            <div className="space-y-1">
              <h3 className="font-semibold">Not enough history yet</h3>
              <p className="text-sm text-muted-foreground">
                {periodCount === 0
                  ? "No metric snapshots have been recorded for this domain yet. Trends appear once tracking has run."
                  : `Only one period of data has been recorded so far${latestPeriodLabel ? ` (${latestPeriodLabel})` : ""}. Charts below will fill in as tracking continues — a trend needs at least two.`}
              </p>
            </div>
          </div>
        </Card>
      )}


      {/* Visibility Score Over Time */}
      <Card className="p-6 border border-border">
        <h3 className="text-lg font-semibold mb-6">Visibility Score Progression</h3>
        <ResponsiveContainer width="100%" height={350}>
          <ComposedChart data={visibilityTrend}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis dataKey="month" stroke="hsl(var(--muted-foreground))" fontSize={12} />
            <YAxis 
              yAxisId="left"
              stroke="hsl(var(--muted-foreground))" 
              fontSize={12}
              label={{ value: "Score / Mentions", angle: -90, position: "insideLeft" }}
            />
            <YAxis 
              yAxisId="right"
              orientation="right"
              stroke="hsl(var(--muted-foreground))" 
              fontSize={12}
              domain={[1, 2.5]}
              label={{ value: "Avg Position", angle: 90, position: "insideRight" }}
            />
            <Tooltip 
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "var(--radius)",
              }}
            />
            <Legend />
            <Area
              yAxisId="left"
              type="monotone"
              dataKey="mentions"
              fill="hsl(var(--primary))"
              fillOpacity={0.1}
              stroke="none"
            />
            <Line 
              yAxisId="left"
              type="monotone" 
              dataKey="score" 
              name="Visibility Score"
              stroke="hsl(var(--primary))" 
              strokeWidth={3}
              dot={{ fill: "hsl(var(--primary))", r: 4 }}
            />
            <Line 
              yAxisId="left"
              type="monotone" 
              dataKey="mentions" 
              name="Mentions"
              stroke="hsl(var(--secondary))" 
              strokeWidth={2}
              dot={{ fill: "hsl(var(--secondary))", r: 3 }}
            />
            <Line 
              yAxisId="right"
              type="monotone" 
              dataKey="avgPosition" 
              name="Avg Position"
              stroke="hsl(var(--chart-3))" 
              strokeWidth={2}
              dot={{ fill: "hsl(var(--chart-3))", r: 3 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </Card>

      {/* Platform Growth */}
      <Card className="p-6 border border-border">
        <h3 className="text-lg font-semibold mb-6">Platform Growth Trends</h3>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={platformGrowth}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis dataKey="month" stroke="hsl(var(--muted-foreground))" fontSize={12} />
            <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
            <Tooltip 
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "var(--radius)",
              }}
            />
            <Legend />
            <Area 
              type="monotone" 
              dataKey="chatgpt" 
              name="ChatGPT"
              stackId="1"
              stroke="hsl(var(--chart-1))" 
              fill="hsl(var(--chart-1))"
              fillOpacity={0.6}
            />
            <Area 
              type="monotone" 
              dataKey="claude" 
              name="Claude"
              stackId="1"
              stroke="hsl(var(--chart-2))" 
              fill="hsl(var(--chart-2))"
              fillOpacity={0.6}
            />
            <Area 
              type="monotone" 
              dataKey="perplexity" 
              name="Perplexity"
              stackId="1"
              stroke="hsl(var(--chart-3))" 
              fill="hsl(var(--chart-3))"
              fillOpacity={0.6}
            />
            <Area 
              type="monotone" 
              dataKey="gemini" 
              name="Gemini"
              stackId="1"
              stroke="hsl(var(--chart-4))" 
              fill="hsl(var(--chart-4))"
              fillOpacity={0.6}
            />
          </AreaChart>
        </ResponsiveContainer>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Competitor Comparison */}
        <Card className="p-6 border border-border">
          <h3 className="text-lg font-semibold mb-6">Competitive Performance</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={competitorComparison}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="month" stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <Tooltip 
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "var(--radius)",
                }}
              />
              <Legend />
              {competitorComparison.length > 0 && Object.keys(competitorComparison[0]).filter(k => k !== 'month').slice(0, 3).map((key, idx) => (
                <Line 
                  key={key}
                  type="monotone" 
                  dataKey={key} 
                  name={key.charAt(0).toUpperCase() + key.slice(1).replace(/([A-Z])/g, ' $1')}
                  stroke={idx === 0 ? "hsl(var(--primary))" : idx === 1 ? "hsl(var(--chart-2))" : "hsl(var(--chart-3))"} 
                  strokeWidth={idx === 0 ? 3 : 2}
                  dot={{ fill: idx === 0 ? "hsl(var(--primary))" : idx === 1 ? "hsl(var(--chart-2))" : "hsl(var(--chart-3))", r: idx === 0 ? 4 : 3 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </Card>

        {/* Seasonal Patterns */}
        <Card className="p-6 border border-border">
          <h3 className="text-lg font-semibold mb-6">Seasonal Patterns</h3>
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={seasonalPattern}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="month" stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <Tooltip 
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "var(--radius)",
                }}
              />
              <Legend />
              <Bar 
                dataKey="mentions" 
                name="2024 Mentions"
                fill="hsl(var(--primary))"
                radius={[8, 8, 0, 0]}
              />
              <Line 
                type="monotone" 
                dataKey="avgYear" 
                name="Historical Average"
                stroke="hsl(var(--chart-4))" 
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Forecast */}
      <Card className="p-6 border border-border">
        <h3 className="text-lg font-semibold mb-6">Performance Forecast</h3>
        {forecast && forecast.length > 0 ? (
          <>
            <ResponsiveContainer width="100%" height={300}>
              <ComposedChart data={forecast}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="month" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
                <Tooltip 
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "var(--radius)",
                  }}
                />
                <Legend />
                <Area
                  type="monotone"
                  dataKey="upper"
                  fill="hsl(var(--primary))"
                  fillOpacity={0.1}
                  stroke="none"
                />
                <Area
                  type="monotone"
                  dataKey="lower"
                  fill="hsl(var(--background))"
                  fillOpacity={1}
                  stroke="none"
                />
                <Line 
                  type="monotone" 
                  dataKey="actual" 
                  name="Actual"
                  stroke="hsl(var(--primary))" 
                  strokeWidth={3}
                  dot={{ fill: "hsl(var(--primary))", r: 4 }}
                />
                <Line 
                  type="monotone" 
                  dataKey="forecast" 
                  name="Forecast"
                  stroke="hsl(var(--primary))" 
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  dot={{ fill: "hsl(var(--primary))", r: 3 }}
                />
              </ComposedChart>
            </ResponsiveContainer>
            <p className="text-sm text-muted-foreground mt-4">
              *Shaded area represents 90% confidence interval
            </p>
          </>
        ) : (
          <div className="flex items-center justify-center h-64">
            <p className="text-sm text-muted-foreground">Forecast data not available yet.</p>
          </div>
        )}
      </Card>

      {/* Milestones */}
      <Card className="p-6 border border-border">
        <h3 className="text-lg font-semibold mb-6">Key Milestones</h3>
        <div className="space-y-4">
          {milestones && milestones.length > 0 ? (
            milestones.map((milestone: any, index: number) => (
              <div key={index} className="flex items-start gap-4 p-4 border border-border rounded-lg hover:border-primary transition-colors">
                <div className="flex-shrink-0 w-2 h-2 rounded-full bg-primary mt-2"></div>
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <h4 className="font-semibold text-sm">{milestone.title}</h4>
                    <span className="text-xs text-muted-foreground">
                      {new Date(milestone.date).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground">{milestone.description}</p>
                  <div className="mt-2">
                    <Badge variant="outline" className="text-xs">
                      {milestone.metric}: {milestone.value}
                    </Badge>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <p className="text-sm text-muted-foreground">No milestones available yet.</p>
          )}
        </div>
      </Card>
    </div>
  );
};

export default HistoricalTrends;
