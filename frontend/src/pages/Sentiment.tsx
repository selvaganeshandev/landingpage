import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TimeFilter } from "@/components/TimeFilter";
import { useToast } from "@/hooks/use-toast";
import { 
  TrendingUp, 
  TrendingDown, 
  Smile, 
  Meh, 
  Frown,
  ArrowUpRight,
  ArrowDownRight,
  FileText,
  RefreshCw
} from "lucide-react";
import { 
  LineChart, 
  Line, 
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Legend 
} from "recharts";
import { useEffect, useMemo, useState } from "react";
import { apiClient } from "@/services/api";
import { useAuth } from "@/contexts/AuthContext";
import { getActiveDomainId } from "@/utils/activeDomain";
import { useDomainStore } from "@/stores/domainStore";

type SentimentRow = { theme: string; positive_percentage: number; neutral_percentage: number; negative_percentage: number; mention_count: number; platform?: string | null; timestamp: string };

const COLORS = {
  positive: "hsl(var(--success))",
  neutral: "hsl(var(--warning))",
  negative: "hsl(var(--destructive))",
};

const Sentiment = () => {
  const { toast } = useToast();
  const { user } = useAuth();
  const { selectedDomain } = useDomainStore();
  const [timePeriod, setTimePeriod] = useState<string>("30");
  const [days, setDays] = useState<number>(30);
  const [domainId, setDomainId] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  // API data
  const [summary, setSummary] = useState<{ positive_percentage: number; neutral_percentage: number; negative_percentage: number; total_mentions: number } | null>(null);
  const [rows, setRows] = useState<SentimentRow[]>([]);
  const [competitorRows, setCompetitorRows] = useState<any[]>([]);

  // Sync domainId from selectedDomain (Zustand store) or localStorage when domain changes
  useEffect(() => {
    if (!user) return;
    
    // Priority 1: Use selectedDomain from Zustand store (most up-to-date when user changes domain)
    if (selectedDomain?.id) {
      const newDomainId = String(selectedDomain.id);
      if (newDomainId !== domainId) {
        setDomainId(newDomainId);
        return;
      }
    }
    
    // Priority 2: Fallback to localStorage (synced with server)
    const id = getActiveDomainId(user);
    if (id && id !== domainId) {
      setDomainId(id);
    }
  }, [user, selectedDomain?.id, domainId]);

  // Update days when timePeriod changes
  useEffect(() => {
    const daysMap: Record<string, number> = {
      '7': 7,
      '30': 30,
      '90': 90,
      '365': 365,
    };
    setDays(daysMap[timePeriod] || 30);
  }, [timePeriod]);

  useEffect(() => {
    const load = async () => {
      if (!domainId) return;
      setLoading(true);
      try {
        const [sum, list] = await Promise.all([
          apiClient.getSentimentSummary({ domain_id: domainId, days }),
          apiClient.getSentimentByDomain({ domain_id: domainId, days })
        ]);
        setSummary(sum as any);
        setRows(Array.isArray(list) ? list : []);
        // Optional: competitor sentiment (engine)
        try {
          const cp = await apiClient.getCompetitorPromptAnalyticsEngine({ domain_id: domainId });
          setCompetitorRows(Array.isArray(cp) ? cp : cp || []);
        } catch {
          setCompetitorRows([]);
        }
      } catch (e:any) {
        const errorMessage = String(e.message || e);
        // Only show error for actual errors, not empty data
        const isNetworkError = errorMessage.includes('fetch') || errorMessage.includes('network') || errorMessage.includes('Network');
        const isServerError = errorMessage.includes('500') || errorMessage.includes('503') || errorMessage.includes('502');
        
        // Only show error toast for actual errors, not for empty data (404 is normal for empty data)
        if (isNetworkError || isServerError || (!errorMessage.includes('404') && !errorMessage.includes('Not Found'))) {
          toast({ title: 'Failed to load sentiment', description: errorMessage, variant: 'destructive' });
        }
        // For empty data, set default empty values without showing error
        setSummary({ positive_percentage: 0, neutral_percentage: 0, negative_percentage: 0, total_mentions: 0 });
        setRows([]);
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [domainId, days]);

  const handleExportReport = () => {
    toast({
      title: "Exporting Report",
      description: "Your sentiment report is being generated...",
    });
  };

  const sentimentOverview = useMemo(() => ({
    positive: summary?.positive_percentage || 0,
    neutral: summary?.neutral_percentage || 0,
    negative: summary?.negative_percentage || 0,
    total_mentions: summary?.total_mentions || 0,
    positive_change: summary?.positive_change || 0,
    neutral_change: summary?.neutral_change || 0,
    negative_change: summary?.negative_change || 0,
  }), [summary]);

  const pieData = [
    { name: "Positive", value: sentimentOverview.positive, color: COLORS.positive },
    { name: "Neutral", value: sentimentOverview.neutral, color: COLORS.neutral },
    { name: "Negative", value: sentimentOverview.negative, color: COLORS.negative },
  ];

  // Build trend by date (weighted by mentions per day)
  const sentimentTrend = useMemo(() => {
    const byDate: Record<string, { posSum: number; neuSum: number; negSum: number; mentions: number }> = {};
    rows.forEach((r) => {
      const d = r.timestamp;
      if (!byDate[d]) byDate[d] = { posSum: 0, neuSum: 0, negSum: 0, mentions: 0 };
      byDate[d].posSum += Number(r.positive_percentage) * Number(r.mention_count);
      byDate[d].neuSum += Number(r.neutral_percentage) * Number(r.mention_count);
      byDate[d].negSum += Number(r.negative_percentage) * Number(r.mention_count);
      byDate[d].mentions += Number(r.mention_count);
    });
    return Object.entries(byDate).sort((a,b)=>a[0].localeCompare(b[0])).map(([date, v]) => ({
      date,
      positive: v.mentions ? +(v.posSum / v.mentions).toFixed(2) : 0,
      neutral: v.mentions ? +(v.neuSum / v.mentions).toFixed(2) : 0,
      negative: v.mentions ? +(v.negSum / v.mentions).toFixed(2) : 0,
    }));
  }, [rows]);

  // Thematic breakdown aggregated across period (weighted by mentions)
  const thematicSentiment = useMemo(() => {
    const map: Record<string, { positive: number; neutral: number; negative: number; mentions: number }> = {};
    rows.forEach((r) => {
      const key = r.theme || 'Unknown';
      if (!map[key]) map[key] = { positive: 0, neutral: 0, negative: 0, mentions: 0 };
      map[key].positive += Number(r.positive_percentage) * Number(r.mention_count);
      map[key].neutral += Number(r.neutral_percentage) * Number(r.mention_count);
      map[key].negative += Number(r.negative_percentage) * Number(r.mention_count);
      map[key].mentions += Number(r.mention_count);
    });
    return Object.entries(map).map(([theme, v]) => ({
      theme,
      positive: v.mentions ? +(v.positive / v.mentions).toFixed(2) : 0,
      neutral: v.mentions ? +(v.neutral / v.mentions).toFixed(2) : 0,
      negative: v.mentions ? +(v.negative / v.mentions).toFixed(2) : 0,
      mentions: v.mentions,
    })).sort((a,b)=>b.mentions - a.mentions);
  }, [rows]);

  // Platform breakdown
  const platformSentiment = useMemo(() => {
    const map: Record<string, { pos: number; neu: number; neg: number; mentions: number }> = {};
    rows.forEach((r) => {
      const key = r.platform || 'Overall';
      if (!map[key]) map[key] = { pos: 0, neu: 0, neg: 0, mentions: 0 };
      map[key].pos += Number(r.positive_percentage) * Number(r.mention_count);
      map[key].neu += Number(r.neutral_percentage) * Number(r.mention_count);
      map[key].neg += Number(r.negative_percentage) * Number(r.mention_count);
      map[key].mentions += Number(r.mention_count);
    });
    return Object.entries(map).map(([platform, v]) => ({
      platform,
      positive: v.mentions ? +(v.pos / v.mentions).toFixed(2) : 0,
      neutral: v.mentions ? +(v.neu / v.mentions).toFixed(2) : 0,
      negative: v.mentions ? +(v.neg / v.mentions).toFixed(2) : 0,
    }));
  }, [rows]);

  // Competitor sentiment from engine competitor prompt analytics (average sentiment_score -> categories pct approx)
  const competitorSentiment = useMemo(() => {
    if (!competitorRows || competitorRows.length === 0) return [] as any[];
    const map: Record<string, { name: string; pos: number; neu: number; neg: number; count: number }> = {};
    competitorRows.forEach((r:any) => {
      const key = r.competitor?.name || `Competitor ${r.competitor_id || ''}`;
      if (!map[key]) map[key] = { name: key, pos: 0, neu: 0, neg: 0, count: 0 };
      const cat = (r.sentiment_category || '').toLowerCase();
      if (cat === 'positive') map[key].pos += 1; else if (cat === 'negative') map[key].neg += 1; else map[key].neu += 1;
      map[key].count += 1;
    });
    return Object.values(map).map(v => ({
      name: v.name,
      positive: v.count ? +(v.pos * 100 / v.count).toFixed(2) : 0,
      neutral: v.count ? +(v.neu * 100 / v.count).toFixed(2) : 0,
      negative: v.count ? +(v.neg * 100 / v.count).toFixed(2) : 0,
    }));
  }, [competitorRows]);

  const handleRefresh = () => {
    if (domainId) {
      const load = async () => {
        setLoading(true);
        try {
          const [sum, list] = await Promise.all([
            apiClient.getSentimentSummary({ domain_id: domainId, days }),
            apiClient.getSentimentByDomain({ domain_id: domainId, days })
          ]);
          setSummary(sum as any);
          setRows(Array.isArray(list) ? list : []);
          toast({ title: 'Data refreshed', description: 'Sentiment data has been updated.' });
        } catch (e: any) {
          toast({ title: 'Failed to refresh', description: String(e.message || e), variant: 'destructive' });
        } finally {
          setLoading(false);
        }
      };
      void load();
    }
  };

  return (
    <div className="p-8 space-y-8 bg-background animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Sentiment Analysis</h1>
          <p className="text-muted-foreground mt-2">
            Deep dive into brand sentiment across AI platforms
          </p>
        </div>
        <div className="flex items-center gap-4">
          <TimeFilter selected={timePeriod} onSelect={setTimePeriod} />
          <Button 
            onClick={handleRefresh} 
            variant="outline"
            disabled={loading}
            className="border-border"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button onClick={handleExportReport} className="gradient-primary shadow-md shadow-primary/20">
            <FileText className="h-4 w-4 mr-2" />
            Export Sentiment Report
          </Button>
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="h-8 w-8 animate-spin text-primary" />
          <span className="ml-3 text-muted-foreground">Loading sentiment data...</span>
        </div>
      )}

      {!loading && (
        <>
      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-sm text-muted-foreground font-medium">Positive Sentiment</p>
              <h3 className="text-4xl font-bold text-success mt-2">{sentimentOverview.positive}%</h3>
            </div>
            <div className="p-3 rounded-xl bg-success/10">
              <Smile className="h-6 w-6 text-success" />
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm">
            {sentimentOverview.positive_change !== 0 ? (
              <>
                {sentimentOverview.positive_change > 0 ? (
                  <ArrowUpRight className="h-4 w-4 text-success" />
                ) : (
                  <ArrowDownRight className="h-4 w-4 text-muted-foreground" />
                )}
                <span className={`font-medium ${
                  sentimentOverview.positive_change > 0 ? 'text-success' : 'text-muted-foreground'
                }`}>
                  {sentimentOverview.positive_change > 0 ? '+' : ''}{sentimentOverview.positive_change.toFixed(1)}%
                </span>
                <span className="text-muted-foreground">vs last period</span>
              </>
            ) : (
              <span className="text-muted-foreground">No change vs last period</span>
            )}
          </div>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-sm text-muted-foreground font-medium">Neutral Sentiment</p>
              <h3 className="text-4xl font-bold text-warning mt-2">{sentimentOverview.neutral}%</h3>
            </div>
            <div className="p-3 rounded-xl bg-warning/10">
              <Meh className="h-6 w-6 text-warning" />
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm">
            {sentimentOverview.neutral_change !== 0 ? (
              <>
                {sentimentOverview.neutral_change > 0 ? (
                  <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <ArrowDownRight className="h-4 w-4 text-muted-foreground" />
                )}
                <span className="text-muted-foreground font-medium">
                  {sentimentOverview.neutral_change > 0 ? '+' : ''}{sentimentOverview.neutral_change.toFixed(1)}%
                </span>
                <span className="text-muted-foreground">vs last period</span>
              </>
            ) : (
              <span className="text-muted-foreground">No change vs last period</span>
            )}
          </div>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-sm text-muted-foreground font-medium">Negative Sentiment</p>
              <h3 className="text-4xl font-bold text-destructive mt-2">{sentimentOverview.negative}%</h3>
            </div>
            <div className="p-3 rounded-xl bg-destructive/10">
              <Frown className="h-6 w-6 text-destructive" />
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm">
            {sentimentOverview.negative_change !== 0 ? (
              <>
                {sentimentOverview.negative_change < 0 ? (
                  <ArrowDownRight className="h-4 w-4 text-success" />
                ) : (
                  <ArrowUpRight className="h-4 w-4 text-destructive" />
                )}
                <span className={`font-medium ${
                  sentimentOverview.negative_change < 0 ? 'text-success' : 'text-destructive'
                }`}>
                  {sentimentOverview.negative_change > 0 ? '+' : ''}{sentimentOverview.negative_change.toFixed(1)}%
                </span>
                <span className="text-muted-foreground">vs last period</span>
              </>
            ) : (
              <span className="text-muted-foreground">No change vs last period</span>
            )}
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sentiment Distribution */}
        <Card className="p-6 border border-border">
          <h3 className="text-lg font-semibold mb-4">Sentiment Distribution</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={90}
                paddingAngle={5}
                dataKey="value"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-2 mt-4">
            {pieData.map((item) => (
              <div key={item.name} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                  <span>{item.name}</span>
                </div>
                <span className="font-medium">{item.value}%</span>
              </div>
            ))}
          </div>
        </Card>

        {/* Sentiment Trends */}
        <Card className="p-6 lg:col-span-2">
          <h3 className="text-lg font-semibold mb-4">Sentiment Trends Over Time</h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={sentimentTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
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
                dataKey="positive" 
                stroke={COLORS.positive}
                strokeWidth={2}
                dot={{ fill: COLORS.positive, r: 3 }}
              />
              <Line 
                type="monotone" 
                dataKey="neutral" 
                stroke={COLORS.neutral}
                strokeWidth={2}
                dot={{ fill: COLORS.neutral, r: 3 }}
              />
              <Line 
                type="monotone" 
                dataKey="negative" 
                stroke={COLORS.negative}
                strokeWidth={2}
                dot={{ fill: COLORS.negative, r: 3 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Thematic Sentiment Breakdown */}
      <Card className="p-6 border border-border">
        <h3 className="text-lg font-semibold mb-6">Thematic Sentiment Breakdown</h3>
        <div className="space-y-6">
          {thematicSentiment.map((theme) => (
            <div key={theme.theme} className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <h4 className="font-medium">{theme.theme}</h4>
                  <Badge variant="secondary">{theme.mentions} mentions</Badge>
                </div>
                <div className="flex items-center gap-6 text-sm">
                  <span className="text-success font-medium">{theme.positive}%</span>
                  <span className="text-warning font-medium">{theme.neutral}%</span>
                  <span className="text-destructive font-medium">{theme.negative}%</span>
                </div>
              </div>
              <div className="flex gap-1 h-2 rounded-full overflow-hidden">
                <div 
                  className="bg-success" 
                  style={{ width: `${theme.positive}%` }}
                />
                <div 
                  className="bg-warning" 
                  style={{ width: `${theme.neutral}%` }}
                />
                <div 
                  className="bg-destructive" 
                  style={{ width: `${theme.negative}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Platform & Competitor Analysis */}
      <Tabs defaultValue="platform" className="space-y-6">
        <TabsList className="bg-muted/50 p-1 border border-border grid w-full max-w-md grid-cols-2">
          <TabsTrigger value="platform" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">By Platform</TabsTrigger>
          <TabsTrigger value="competitor" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">Competitor Comparison</TabsTrigger>
        </TabsList>

        <TabsContent value="platform" className="space-y-4">
          <Card className="p-6 border border-border">
            <h3 className="text-lg font-semibold mb-6">Platform Sentiment Breakdown</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={platformSentiment}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="platform" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
                <Tooltip 
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "var(--radius)",
                  }}
                />
                <Legend />
                <Bar dataKey="positive" stackId="a" fill={COLORS.positive} />
                <Bar dataKey="neutral" stackId="a" fill={COLORS.neutral} />
                <Bar dataKey="negative" stackId="a" fill={COLORS.negative} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </TabsContent>

        <TabsContent value="competitor" className="space-y-4">
          <Card className="p-6 border border-border">
            <h3 className="text-lg font-semibold mb-6">Competitive Sentiment Analysis</h3>
            <div className="space-y-6">
              {competitorSentiment.map((competitor, index) => (
                <div key={competitor.name} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm ${
                        index === 0 
                          ? "bg-gradient-to-br from-primary to-secondary text-primary-foreground"
                          : "bg-muted text-muted-foreground"
                      }`}>
                        {index + 1}
                      </div>
                      <h4 className="font-medium">{competitor.name}</h4>
                    </div>
                    <div className="flex items-center gap-6 text-sm">
                      <span className="text-success font-medium">{competitor.positive}%</span>
                      <span className="text-warning font-medium">{competitor.neutral}%</span>
                      <span className="text-destructive font-medium">{competitor.negative}%</span>
                    </div>
                  </div>
                  <div className="flex gap-1 h-3 rounded-full overflow-hidden">
                    <div 
                      className="bg-success" 
                      style={{ width: `${competitor.positive}%` }}
                    />
                    <div 
                      className="bg-warning" 
                      style={{ width: `${competitor.neutral}%` }}
                    />
                    <div 
                      className="bg-destructive" 
                      style={{ width: `${competitor.negative}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </TabsContent>
      </Tabs>
        </>
      )}
    </div>
  );
};

export default Sentiment;
