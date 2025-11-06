import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
import { loadActiveDomain } from "@/utils/activeDomain";

const HistoricalTrends = () => {
  const { toast } = useToast();
  const { user } = useAuth();
  const [domainId, setDomainId] = useState<string | null>(null);
  const [months, setMonths] = useState<number>(12);
  const [trendsData, setTrendsData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!user) return;
    const id = loadActiveDomain(user.id);
    if (id) setDomainId(String(id));
  }, [user]);

  useEffect(() => {
    const load = async () => {
      if (!domainId) return;
      setIsLoading(true);
      try {
        const data = await apiClient.getHistoricalTrends({ domain_id: domainId, months });
        setTrendsData(data);
      } catch (e:any) {
        toast({ title: 'Failed to load historical trends', description: String(e.message||e), variant: 'destructive' });
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
  
  // Forecast - empty for now (can be computed later)
  const forecast = useMemo(() => [], []);

  const handleExportReport = () => {
    toast({
      title: "Exporting Report",
      description: "Your historical trends report is being generated...",
    });
  };

  if (isLoading) {
    return (
      <div className="p-8 space-y-8">
        <div className="flex items-center justify-center h-64">
          <p className="text-muted-foreground">Loading historical trends...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between pb-4">
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

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground font-medium">Visibility Growth</p>
            <h3 className="text-3xl font-bold text-success">{summary.visibility_growth >= 0 ? '+' : ''}{summary.visibility_growth}%</h3>
            <div className="flex items-center gap-2 text-sm">
              <TrendingUp className="h-4 w-4 text-success" />
              <span className="text-muted-foreground">Over period</span>
            </div>
          </div>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground font-medium">Mention Growth</p>
            <h3 className="text-3xl font-bold text-success">{summary.mention_growth >= 0 ? '+' : ''}{summary.mention_growth}%</h3>
            <div className="flex items-center gap-2 text-sm">
              <TrendingUp className="h-4 w-4 text-success" />
              <span className="text-muted-foreground">Over period</span>
            </div>
          </div>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground font-medium">Position Improvement</p>
            <h3 className="text-3xl font-bold text-success">{summary.position_improvement >= 0 ? '+' : ''}{summary.position_improvement}%</h3>
            <div className="flex items-center gap-2 text-sm">
              <TrendingDown className="h-4 w-4 text-success" />
              <span className="text-muted-foreground">Lower is better</span>
            </div>
          </div>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground font-medium">Market Share Gain</p>
            <h3 className="text-3xl font-bold text-success">{summary.market_share_gain >= 0 ? '+' : ''}{summary.market_share_gain}%</h3>
            <div className="flex items-center gap-2 text-sm">
              <TrendingUp className="h-4 w-4 text-success" />
              <span className="text-muted-foreground">Over period</span>
            </div>
          </div>
        </Card>
      </div>

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
          <p className="text-sm text-muted-foreground">No milestones available yet.</p>
        </div>
      </Card>
    </div>
  );
};

export default HistoricalTrends;
