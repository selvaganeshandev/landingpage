import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageLoader } from "@/components/PageLoader";
import { useToast } from "@/hooks/use-toast";
import { 
  TrendingUp, 
  TrendingDown, 
  Smile, 
  Meh, 
  Frown,
  ArrowUpRight,
  ArrowDownRight,
  FileText
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
import { downloadCsv } from "@/utils/exportCsv";
import { InfoHint, MetricHint } from "@/components/InfoHint";

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
  const DAYS = 30;
  const [domainId, setDomainId] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  // API data
  // The *_change fields are returned by /sentiment/summary/ (percentage-point
  // deltas vs the previous 30 days) and are read below; they were missing from
  // this type, so every card's change line was an unchecked property access.
  const [summary, setSummary] = useState<{
    positive_percentage: number;
    neutral_percentage: number;
    negative_percentage: number;
    total_mentions: number;
    positive_change?: number;
    neutral_change?: number;
    negative_change?: number;
  } | null>(null);
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

  useEffect(() => {
    const load = async () => {
      if (!domainId) return;
      setLoading(true);
      try {
        const [sum, list] = await Promise.all([
          apiClient.getSentimentSummary({ domain_id: domainId, days: DAYS }),
          apiClient.getSentimentByDomain({ domain_id: domainId, days: DAYS })
        ]);
        setSummary(sum as any);
        setRows(Array.isArray(list) ? list : []);
        // Optional: competitor sentiment (engine)
        try {
          const cp = await apiClient.getCompetitorPromptAnalyticsEngine({ domain_id: domainId });
          // Ensure we always set an array
          const payload = cp as any;
          if (Array.isArray(payload)) {
            setCompetitorRows(payload);
          } else if (payload && typeof payload === 'object' && Array.isArray(payload.results)) {
            setCompetitorRows(payload.results);
          } else {
            setCompetitorRows([]);
          }
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
  }, [domainId]);

  const handleExportReport = () => {
    // Build rows from overview + thematic + platform data
    const exportRows: Record<string, string | number>[] = [];

    // Overview row
    exportRows.push({
      section: 'Overview',
      theme: '',
      platform: '',
      positive: sentimentOverview.positive,
      neutral: sentimentOverview.neutral,
      negative: sentimentOverview.negative,
      mentions: sentimentOverview.total_mentions,
    });

    // Thematic rows
    thematicSentiment.forEach(t => {
      exportRows.push({
        section: 'Theme',
        theme: t.theme,
        platform: '',
        positive: t.positive,
        neutral: t.neutral,
        negative: t.negative,
        mentions: t.mentions,
      });
    });

    // Platform rows
    platformSentiment.forEach(p => {
      exportRows.push({
        section: 'Platform',
        theme: '',
        platform: p.platform,
        positive: p.positive,
        neutral: p.neutral,
        negative: p.negative,
        mentions: 0,
      });
    });

    // Competitor rows
    competitorSentiment.forEach(c => {
      exportRows.push({
        section: 'Competitor',
        theme: '',
        platform: c.name,
        positive: c.positive,
        neutral: c.neutral,
        negative: c.negative,
        mentions: 0,
      });
    });

    const headers = [
      { key: 'section', label: 'Section' },
      { key: 'theme', label: 'Theme' },
      { key: 'platform', label: 'Platform / Competitor' },
      { key: 'positive', label: 'Positive %' },
      { key: 'neutral', label: 'Neutral %' },
      { key: 'negative', label: 'Negative %' },
      { key: 'mentions', label: 'Mentions' },
    ];

    const today = new Date().toISOString().split('T')[0];
    downloadCsv(exportRows, headers, `sentiment_report_${today}.csv`);

    toast({
      title: "Report Exported",
      description: "Your sentiment report has been downloaded.",
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
  // Now includes "You" (your brand) from summary data
  const competitorSentiment = useMemo(() => {
    const map: Record<string, { name: string; pos: number; neu: number; neg: number; count: number }> = {};

    // Your own bar is built from `summary`, not from competitorRows, so it must
    // not be gated on competitors existing. Returning early when the competitor
    // list was empty hid your own sentiment too, leaving the tab blank for any
    // domain with no competitors configured.
    if (summary && summary.total_mentions > 0) {
      map['You'] = {
        name: 'You',
        pos: Math.round((summary.positive_percentage / 100) * summary.total_mentions),
        neu: Math.round((summary.neutral_percentage / 100) * summary.total_mentions),
        neg: Math.round((summary.negative_percentage / 100) * summary.total_mentions),
        count: summary.total_mentions
      };
    }
    
    // Add competitors from competitorRows
    if (competitorRows && competitorRows.length > 0) {
      competitorRows.forEach((r:any) => {
        // Use competitor_name from serializer, fallback to competitor?.name or competitor_id
        const key = r.competitor_name || r.competitor?.name || `Competitor ${r.competitor_id || r.competitor || ''}`;
        if (!map[key]) map[key] = { name: key, pos: 0, neu: 0, neg: 0, count: 0 };
        const cat = (r.sentiment_category || '').toLowerCase();
        if (cat === 'positive') map[key].pos += 1; 
        else if (cat === 'negative') map[key].neg += 1; 
        else map[key].neu += 1;
        map[key].count += 1;
      });
    }
    
    if (Object.keys(map).length === 0) return [] as any[];

    return Object.values(map).map(v => ({
      name: v.name,
      positive: v.count ? +(v.pos * 100 / v.count).toFixed(1) : 0,
      neutral: v.count ? +(v.neu * 100 / v.count).toFixed(1) : 0,
      negative: v.count ? +(v.neg * 100 / v.count).toFixed(1) : 0,
      isYou: v.name === 'You'
    })).sort((a, b) => {
      // Sort "You" first, then by positive sentiment descending, then by name
      if (a.isYou && !b.isYou) return -1;
      if (!a.isYou && b.isYou) return 1;
      if (a.positive !== b.positive) return b.positive - a.positive;
      return a.name.localeCompare(b.name);
    });
  }, [competitorRows, summary]);

  if (loading) {
    return <PageLoader />;
  }

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
          <Button onClick={handleExportReport} className="gradient-primary shadow-md shadow-primary/20">
            <FileText className="h-4 w-4 mr-2" />
            Export Sentiment Report
          </Button>
        </div>
      </div>


      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="p-6 border border-border">
          <div className="flex items-center justify-between mb-2">
            <div>
              <p className="text-sm text-muted-foreground flex items-center gap-1.5">
                Positive Sentiment
                <InfoHint>
                  <MetricHint
                    title="Positive Sentiment"
                    plain="The share of brand mentions that read as favourable across all AI answers in the last 30 days."
                    formula="Each day\u2019s theme snapshot carries its own positive percentage; these are averaged weighted by that snapshot\u2019s mention count, so a day with 40 mentions counts forty times as much as a day with one."
                  />
                </InfoHint>
              </p>
              <h3 className="text-2xl font-bold text-success mt-1">{sentimentOverview.positive}%</h3>
            </div>
            <Smile className="h-5 w-5 text-success" />
          </div>
          <div className="flex items-center gap-2 text-xs">
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

        <Card className="p-6 border border-border">
          <div className="flex items-center justify-between mb-2">
            <div>
              <p className="text-sm text-muted-foreground flex items-center gap-1.5">
                Neutral Sentiment
                <InfoHint>
                  <MetricHint
                    title="Neutral Sentiment"
                    plain="Mentions that state facts about you without leaning positive or negative \u2014 usually listings and comparisons."
                    formula="Same mention-weighted average as the other two. Positive, neutral and negative always total 100%."
                  />
                </InfoHint>
              </p>
              <h3 className="text-2xl font-bold text-warning mt-1">{sentimentOverview.neutral}%</h3>
            </div>
            <Meh className="h-5 w-5 text-warning" />
          </div>
          <div className="flex items-center gap-2 text-xs">
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

        <Card className="p-6 border border-border">
          <div className="flex items-center justify-between mb-2">
            <div>
              <p className="text-sm text-muted-foreground flex items-center gap-1.5">
                Negative Sentiment
                <InfoHint>
                  <MetricHint
                    title="Negative Sentiment"
                    plain="Mentions that read as unfavourable. This is the number worth acting on \u2014 each one is an AI answer steering someone away."
                    formula="Same mention-weighted average. The change compares against the previous 30 days and is shown in percentage points, not a percentage of a percentage."
                  />
                </InfoHint>
              </p>
              <h3 className="text-2xl font-bold text-destructive mt-1">{sentimentOverview.negative}%</h3>
            </div>
            <Frown className="h-5 w-5 text-destructive" />
          </div>
          <div className="flex items-center gap-2 text-xs">
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
        {thematicSentiment.length === 0 ? (
          <p className="text-sm text-muted-foreground py-8 text-center">
            No sentiment recorded in the last 30 days.
          </p>
        ) : (
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
        )}
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
            {platformSentiment.length === 0 ? (
              <p className="text-sm text-muted-foreground py-12 text-center">
                No sentiment recorded in the last 30 days.
              </p>
            ) : (
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
            )}
          </Card>
        </TabsContent>

        <TabsContent value="competitor" className="space-y-4">
          <Card className="p-6 border border-border">
            <div className="flex items-center gap-1.5 mb-6">
              <h3 className="text-lg font-semibold">Competitive Sentiment Analysis</h3>
              <InfoHint>
                <MetricHint
                  title="Competitive Sentiment"
                  plain="How favourably the AI platforms speak about you compared with each tracked competitor."
                  formula="Your row is the mention-weighted sentiment shown in the cards above. Competitor rows count how many of their tracked responses were classified positive, neutral or negative. The two are computed from different sources, so read this as a directional comparison rather than an exact like-for-like ranking."
                />
              </InfoHint>
            </div>
            {competitorSentiment.length === 0 ? (
              <p className="text-sm text-muted-foreground py-8 text-center">
                No sentiment recorded in the last 30 days.
              </p>
            ) : (
            <div className="space-y-6">
              {competitorSentiment.map((competitor, index) => (
                <div key={competitor.name} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm ${
                        competitor.isYou || index === 0
                          ? "bg-gradient-to-br from-primary to-secondary text-primary-foreground"
                          : "bg-muted text-muted-foreground"
                      }`}>
                        {index + 1}
                      </div>
                      <div className="flex items-center gap-2">
                        <h4 className="font-medium">{competitor.name}</h4>
                        {competitor.isYou && (
                          <Badge variant="default" className="gradient-primary border-0 text-xs">You</Badge>
                        )}
                      </div>
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
            )}
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Sentiment;
