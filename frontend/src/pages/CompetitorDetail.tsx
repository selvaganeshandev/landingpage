import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TimeFilter } from "@/components/TimeFilter";
import { PageLoader } from "@/components/PageLoader";
import { ViewMentionsDialog } from "@/components/ViewMentionsDialog";
import { CompareMetricsDialog } from "@/components/CompareMetricsDialog";
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Building2,
  ExternalLink,
  Share2,
  FileText,
  Target,
  MessageSquare,
  ArrowLeftRight
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/services/api";
import { useAuth } from "@/contexts/AuthContext";
import { getActiveDomainId } from "@/utils/activeDomain";
import { useDomainStore } from "@/stores/domainStore";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  PieChart,
  Pie,
  Cell
} from "recharts";

const CompetitorDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user } = useAuth();
  const { selectedDomain } = useDomainStore();
  const [timePeriod, setTimePeriod] = useState("30");
  const [activeTab, setActiveTab] = useState("overview");
  const [isLoading, setIsLoading] = useState(true);
  const [competitor, setCompetitor] = useState<any>(null);
  const [domainId, setDomainId] = useState<string | null>(null);
  const [mentionTrend, setMentionTrend] = useState<any[]>([]);
  const [marketRank, setMarketRank] = useState<number | null>(null);
  const [viewMentionsDialogOpen, setViewMentionsDialogOpen] = useState(false);
  const [compareMetricsDialogOpen, setCompareMetricsDialogOpen] = useState(false);
  const [platformBreakdown, setPlatformBreakdown] = useState<any[]>([]);

  // Sync domainId from selectedDomain or localStorage
  useEffect(() => {
    if (!user) return;

    if (selectedDomain?.id) {
      const newDomainId = String(selectedDomain.id);
      if (newDomainId !== domainId) {
        setDomainId(newDomainId);
      }
    } else {
      const serverActiveDomain = getActiveDomainId(user);
      const serverDomainId = serverActiveDomain || '';
      if (serverDomainId !== domainId) {
        setDomainId(serverDomainId);
      }
    }
  }, [user, selectedDomain?.id, domainId]);

  // Fetch competitor data
  useEffect(() => {
    const fetchCompetitor = async () => {
      if (!id || !domainId) {
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      try {
        // Fetch competitor details, trend data, and all competitors in parallel
        const [data, snapshotData, allCompetitors] = await Promise.all([
          apiClient.getEngineCompetitorDetail(Number(id)),
          apiClient.getCompetitorMetricSnapshots({
            domain_id: domainId,
            competitor_id: id,
            days: Number(timePeriod)
          }),
          apiClient.getEngineCompetitors({ domain_id: domainId })
        ]);

        // Convert sentiment_score from -1 to 1 range to 0-100 percentage for display
        const rawSentiment = Number(data.sentiment_score || 0);
        const totalMentions = Number(data.total_mentions || 0);
        let sentimentPercent = 0;
        if (rawSentiment === -1 || (rawSentiment === 0 && totalMentions === 0)) {
          sentimentPercent = 0; // No data or unmentioned
        } else {
          sentimentPercent = Math.round((rawSentiment + 1) * 50);
        }

        setCompetitor({
          id: data.id,
          name: data.name || 'Unknown',
          url: data.url || data.domain_name || '',
          logo: data.name ? data.name.charAt(0).toUpperCase() : '?',
          mentions: data.total_mentions || 0,
          citations: data.total_citations || 0,
          visibility: Math.round(Number(data.visibility_score || 0)),
          sentiment: sentimentPercent,
          avgPosition: Number(data.average_position || 0),
          shareOfVoice: Math.round(Number(data.share_of_voice_percentage || 0)),
          trend: Number(data.trend_percentage || 0),
          description: data.description || `${data.name} - Competitor analysis and performance tracking.`,
        });

        // Process snapshot data for the trend chart
        const snapshots = Array.isArray(snapshotData) ? snapshotData : snapshotData?.results || [];
        if (snapshots.length > 0) {
          const trendData = snapshots.map((snap: any) => {
            const date = new Date(snap.timestamp || snap.created_at);
            const monthLabel = date.toLocaleDateString('en-US', { month: 'short' });

            return {
              month: monthLabel,
              mentions: Number(snap.total_mentions || 0),
              position: Number(snap.average_position || 0),
              date: date.getTime() // for sorting
            };
          });

          // Sort by date and remove duplicates (keep latest for each month)
          const sortedTrend = trendData
            .sort((a, b) => a.date - b.date)
            .reduce((acc: any[], curr) => {
              const existingIndex = acc.findIndex(item => item.month === curr.month);
              if (existingIndex >= 0) {
                // Replace with newer data for same month
                acc[existingIndex] = curr;
              } else {
                acc.push(curr);
              }
              return acc;
            }, [])
            .map(({ date, ...rest }) => rest); // Remove date field before setting

          setMentionTrend(sortedTrend);
        } else {
          setMentionTrend([]);
        }

        // Calculate platform breakdown from the latest snapshot
        if (snapshots.length > 0) {
          // Sort snapshots by timestamp (most recent first) to ensure we get the latest
          const sortedSnapshots = [...snapshots].sort((a: any, b: any) => {
            const dateA = new Date(a.timestamp || a.created_at || 0).getTime();
            const dateB = new Date(b.timestamp || b.created_at || 0).getTime();
            return dateB - dateA; // Descending order (newest first)
          });
          const latestSnapshot = sortedSnapshots[0]; // Most recent snapshot
          const platformMetrics = latestSnapshot.platform_metrics || [];

          if (Array.isArray(platformMetrics) && platformMetrics.length > 0) {
            // Calculate total mentions across all platforms
            const totalPlatformMentions = platformMetrics.reduce((sum: number, pm: any) => {
              return sum + (Number(pm.mentions) || 0);
            }, 0);

            // Build platform breakdown with percentages
            const breakdown = platformMetrics
              .filter((pm: any) => (Number(pm.mentions) || 0) > 0) // Only platforms with mentions
              .map((pm: any) => ({
                platform: pm.platform || 'Unknown',
                mentions: Number(pm.mentions) || 0,
                percentage: totalPlatformMentions > 0
                  ? Number(((Number(pm.mentions) / totalPlatformMentions) * 100).toFixed(1))
                  : 0
              }))
              .sort((a, b) => b.mentions - a.mentions); // Sort by mentions desc

            setPlatformBreakdown(breakdown);
          } else {
            setPlatformBreakdown([]);
          }
        } else {
          setPlatformBreakdown([]);
        }

        // Calculate market rank based on share of voice
        const competitors = Array.isArray(allCompetitors) ? allCompetitors : allCompetitors?.results || [];
        if (competitors.length > 0) {
          // Sort competitors by share of voice (descending) or mentions if share of voice is not available
          const sortedCompetitors = competitors
            .map((c: any) => ({
              id: c.id,
              shareOfVoice: Number(c.share_of_voice_percentage || 0),
              mentions: Number(c.total_mentions || 0)
            }))
            .sort((a, b) => {
              // Primary sort by share of voice, fallback to mentions
              if (b.shareOfVoice !== a.shareOfVoice) {
                return b.shareOfVoice - a.shareOfVoice;
              }
              return b.mentions - a.mentions;
            });

          // Find the rank (1-indexed)
          const rank = sortedCompetitors.findIndex(c => c.id === Number(id)) + 1;
          setMarketRank(rank > 0 ? rank : null);
        } else {
          setMarketRank(null);
        }
      } catch (error: any) {
        console.error('Failed to load competitor details:', error);
        toast({
          title: 'Failed to Load Competitor',
          description: error?.message || 'Could not fetch competitor details.',
          variant: 'destructive',
        });
      } finally {
        setIsLoading(false);
      }
    };

    fetchCompetitor();
  }, [id, domainId, timePeriod, toast]);

  const sentimentData = [
    { name: "Positive", value: 68, color: "hsl(var(--success))" },
    { name: "Neutral", value: 24, color: "hsl(var(--warning))" },
    { name: "Negative", value: 8, color: "hsl(var(--destructive))" },
  ];

  const topMentions = [
    { prompt: "best budget protein powder", position: 1, platform: "ChatGPT", sentiment: "positive" },
    { prompt: "affordable sports supplements", position: 2, platform: "Claude", sentiment: "positive" },
    { prompt: "protein powder comparison", position: 3, platform: "Perplexity", sentiment: "neutral" },
  ];

  const strengthsWeaknesses = {
    strengths: [
      "Competitive pricing and frequent promotions",
      "Wide product range across categories",
      "Strong brand recognition in fitness community",
      "Effective e-commerce and subscription model"
    ],
    weaknesses: [
      "Lower mention of ingredient quality vs premium brands",
      "Mixed reviews on taste and mixability",
      "Less emphasis on sustainability and clean labels",
      "Positioned more as budget option than premium"
    ]
  };

  const handleShare = () => {
    toast({
      title: "Share Link Generated",
      description: "Competitor profile link copied to clipboard.",
    });
  };

  const handleExport = () => {
    toast({
      title: "Exporting Report",
      description: "Comprehensive competitor report is being generated...",
    });
  };

  // Helper function to format URL with protocol
  const formatUrl = (url: string) => {
    if (!url) return '#';
    // Check if URL already has a protocol
    if (url.startsWith('http://') || url.startsWith('https://')) {
      return url;
    }
    // Add https:// if no protocol exists
    return `https://${url}`;
  };

  // Show loading state
  if (isLoading || !competitor) {
    return <PageLoader sidebarOpen />;
  }

  return (
    <div className="p-8 space-y-6 bg-background animate-fade-in">
      {/* Header */}
      <div className="space-y-4 pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="outline"
              size="icon"
              onClick={() => navigate(-1)}
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-2xl border-2 border-border shadow-lg flex items-center justify-center bg-card overflow-hidden">
                {competitor.url ? (
                  <img
                    src={`https://www.google.com/s2/favicons?domain=${competitor.url}&sz=64`}
                    alt={`${competitor.name} favicon`}
                    className="w-10 h-10 object-contain"
                    onError={(e) => {
                      e.currentTarget.style.display = 'none';
                      e.currentTarget.parentElement!.innerHTML = `<span class="text-3xl font-bold text-primary">${competitor.logo}</span>`;
                    }}
                  />
                ) : (
                  <span className="text-3xl font-bold text-primary">{competitor.logo}</span>
                )}
              </div>
              <div>
                <h1 className="text-4xl font-bold tracking-tight">{competitor.name}</h1>
                <p className="text-muted-foreground mt-2">{competitor.url}</p>
              </div>
            </div>
          </div>
          <div className="flex gap-3">
            <TimeFilter selected={timePeriod} onSelect={setTimePeriod} />
            <Button variant="outline" onClick={handleShare}>
              <Share2 className="h-4 w-4 mr-2" />
              Share
            </Button>
            <Button variant="outline" onClick={handleExport}>
              <FileText className="h-4 w-4 mr-2" />
              Export
            </Button>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-6">
        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary backdrop-blur-sm bg-card/80">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground uppercase tracking-wider">Mentions</p>
            <p className="text-4xl font-bold font-inter">{competitor.mentions}</p>
            <div className="flex items-center gap-2">
              {competitor.trend > 0 ? (
                <TrendingUp className="h-4 w-4 text-success" />
              ) : (
                <TrendingDown className="h-4 w-4 text-destructive" />
              )}
              <span className={`text-sm font-semibold ${competitor.trend > 0 ? 'text-success' : 'text-destructive'}`}>
                {competitor.trend > 0 ? '+' : ''}{competitor.trend}%
              </span>
            </div>
          </div>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary backdrop-blur-sm bg-card/80">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground uppercase tracking-wider">Citations</p>
            <p className="text-4xl font-bold font-inter">{competitor.citations || 0}</p>
            <p className="text-sm text-muted-foreground">Source references</p>
          </div>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary backdrop-blur-sm bg-card/80">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground uppercase tracking-wider">Share of Voice</p>
            <p className="text-4xl font-bold font-inter">{competitor.shareOfVoice}%</p>
            <p className="text-sm text-muted-foreground">Market share</p>
          </div>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary backdrop-blur-sm bg-card/80">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground uppercase tracking-wider">Avg Position</p>
            <p className="text-4xl font-bold font-inter">{competitor.avgPosition?.toFixed(1) || '0.0'}</p>
            <p className="text-sm text-muted-foreground">Across all platforms</p>
          </div>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary backdrop-blur-sm bg-card/80">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground uppercase tracking-wider">Visibility</p>
            <p className="text-4xl font-bold font-inter">{competitor.visibility}%</p>
            <Progress value={competitor.visibility} className="h-2" />
          </div>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary backdrop-blur-sm bg-card/80">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground uppercase tracking-wider">Sentiment</p>
            <p className="text-4xl font-bold font-inter">{competitor.sentiment}%</p>
            <Progress value={competitor.sentiment} className="h-2" />
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Mention Trends */}
          <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
            <div className="space-y-6">
              <div className="pb-4 border-b border-border">
                <h3 className="text-lg font-semibold font-inter">Mention Volume & Position Trends</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Track mention frequency and average position over time
                </p>
              </div>
              {mentionTrend.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={mentionTrend}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="month" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                    <YAxis yAxisId="left" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                    <YAxis yAxisId="right" orientation="right" stroke="hsl(var(--muted-foreground))" fontSize={12} reversed />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "hsl(var(--card))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "var(--radius)",
                      }}
                    />
                    <Legend />
                    <Line
                      yAxisId="left"
                      type="monotone"
                      dataKey="mentions"
                      name="Mentions"
                      stroke="hsl(var(--primary))"
                      strokeWidth={3}
                      dot={{ fill: "hsl(var(--primary))", r: 4 }}
                    />
                    <Line
                      yAxisId="right"
                      type="monotone"
                      dataKey="position"
                      name="Avg Position"
                      stroke="hsl(var(--chart-2))"
                      strokeWidth={2}
                      dot={{ fill: "hsl(var(--chart-2))", r: 3 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-[300px]">
                  <p className="text-sm text-muted-foreground">No trend data available for the selected period.</p>
                </div>
              )}
            </div>
          </Card>

          {/* Platform Breakdown */}
          <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
            <div className="space-y-6">
              <div className="pb-4 border-b border-border">
                <h3 className="text-lg font-semibold font-inter">Platform Distribution</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Mention breakdown across AI platforms
                </p>
              </div>
              {platformBreakdown.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <ResponsiveContainer width="100%" height={250}>
                    <PieChart>
                      <Pie
                        data={platformBreakdown}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ platform, percentage }) => `${platform} ${percentage}%`}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="mentions"
                      >
                        {platformBreakdown.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={`hsl(var(--chart-${index + 1}))`} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="space-y-3">
                    {platformBreakdown.map((platform, idx) => (
                      <div key={idx} className="flex items-center justify-between p-3 rounded-xl bg-muted/30 border border-border">
                        <div className="flex items-center gap-3">
                          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: `hsl(var(--chart-${idx + 1}))` }} />
                          <span className="font-medium">{platform.platform}</span>
                        </div>
                        <div className="text-right">
                          <p className="font-bold font-inter">{platform.mentions}</p>
                          <p className="text-xs text-muted-foreground">{platform.percentage}%</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center h-[250px]">
                  <div className="text-center space-y-2">
                    <MessageSquare className="h-12 w-12 mx-auto text-muted-foreground/30" />
                    <p className="text-sm text-muted-foreground">No platform data available</p>
                  </div>
                </div>
              )}
            </div>
          </Card>

          {/* Tabs Section */}
          <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="bg-muted/50 p-1 border border-border mb-6">
                <TabsTrigger value="overview" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">
                  Overview
                </TabsTrigger>
                <TabsTrigger value="mentions" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">
                  Top Mentions
                </TabsTrigger>
                <TabsTrigger value="swot" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">
                  SWOT Analysis
                </TabsTrigger>
              </TabsList>

              <TabsContent value="overview" className="space-y-4">
                <div>
                  <h3 className="text-lg font-semibold mb-3 font-inter">About {competitor.name}</h3>
                  <p className="text-muted-foreground leading-relaxed">{competitor.description}</p>
                </div>
                <div className="pt-4">
                  <h3 className="text-lg font-semibold mb-4 font-inter">Sentiment Distribution</h3>
                  <div className="grid grid-cols-3 gap-4">
                    {sentimentData.map((item) => (
                      <div key={item.name} className="p-4 rounded-xl border border-border bg-muted/30">
                        <p className="text-sm text-muted-foreground mb-2">{item.name}</p>
                        <p className="text-3xl font-bold font-inter">{item.value}%</p>
                        <Progress value={item.value} className="h-2 mt-2" />
                      </div>
                    ))}
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="mentions" className="space-y-3">
                {topMentions.map((mention, idx) => (
                  <div key={idx} className="p-4 rounded-xl border border-border hover:shadow-md transition-all bg-card/50">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl gradient-primary shadow-md flex items-center justify-center font-bold text-white font-inter">
                          #{mention.position}
                        </div>
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <Badge variant="outline">{mention.platform}</Badge>
                            <Badge variant="secondary">{mention.sentiment}</Badge>
                          </div>
                          <p className="text-sm font-mono text-muted-foreground">{mention.prompt}</p>
                        </div>
                      </div>
                      <Button variant="ghost" size="sm">
                        <ExternalLink className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </TabsContent>

              <TabsContent value="swot" className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-5 rounded-xl border border-success/20 bg-success/5">
                    <h4 className="font-semibold mb-3 font-inter text-success flex items-center gap-2">
                      <TrendingUp className="h-4 w-4" />
                      Strengths
                    </h4>
                    <ul className="space-y-2">
                      {strengthsWeaknesses.strengths.map((item, idx) => (
                        <li key={idx} className="text-sm flex items-start gap-2">
                          <span className="text-success mt-1">•</span>
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div className="p-5 rounded-xl border border-warning/20 bg-warning/5">
                    <h4 className="font-semibold mb-3 font-inter text-warning flex items-center gap-2">
                      <Target className="h-4 w-4" />
                      Weaknesses
                    </h4>
                    <ul className="space-y-2">
                      {strengthsWeaknesses.weaknesses.map((item, idx) => (
                        <li key={idx} className="text-sm flex items-start gap-2">
                          <span className="text-warning mt-1">•</span>
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Quick Stats */}
          <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
            <h3 className="text-lg font-semibold mb-4 font-inter">Quick Stats</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-border">
                <span className="text-sm text-muted-foreground">Sentiment Score</span>
                <span className={`text-lg font-bold font-inter ${
                  competitor.sentiment >= 60 ? 'text-success' :
                  competitor.sentiment >= 40 ? 'text-warning' :
                  'text-destructive'
                }`}>
                  {competitor.sentiment}%
                </span>
              </div>
              <div className="flex items-center justify-between pb-3 border-b border-border">
                <span className="text-sm text-muted-foreground">Market Rank</span>
                <span className="text-lg font-bold font-inter">
                  {marketRank ? `#${marketRank}` : 'N/A'}
                </span>
              </div>
              <div className="flex items-center justify-between pb-3 border-b border-border">
                <span className="text-sm text-muted-foreground">Total Citations</span>
                <span className="text-lg font-bold font-inter">{competitor.citations || 0}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Growth Trend</span>
                <span className={`text-lg font-bold font-inter ${
                  competitor.trend > 0 ? 'text-success' :
                  competitor.trend < 0 ? 'text-destructive' :
                  'text-muted-foreground'
                }`}>
                  {competitor.trend > 0 ? '+' : ''}{competitor.trend}%
                </span>
              </div>
            </div>
          </Card>

          {/* Quick Actions */}
          <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
            <h3 className="text-lg font-semibold mb-4 font-inter">Quick Actions</h3>
            <div className="space-y-2">
              <Button variant="outline" className="w-full justify-start border border-border" asChild>
                <a href={formatUrl(competitor.url)} target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="h-4 w-4 mr-2" />
                  Visit Website
                </a>
              </Button>
              <Button
                variant="outline"
                className="w-full justify-start border border-border"
                onClick={() => setViewMentionsDialogOpen(true)}
              >
                <MessageSquare className="h-4 w-4 mr-2" />
                View All Mentions
              </Button>
              <Button
                variant="outline"
                className="w-full justify-start border border-border"
                onClick={() => setCompareMetricsDialogOpen(true)}
              >
                <ArrowLeftRight className="h-4 w-4 mr-2" />
                Compare Metrics
              </Button>
            </div>
          </Card>
        </div>
      </div>

      {/* View Mentions Dialog */}
      <ViewMentionsDialog
        open={viewMentionsDialogOpen}
        onOpenChange={setViewMentionsDialogOpen}
        competitorId={Number(id)}
        competitorName={competitor.name}
        domainId={domainId || ''}
      />

      {/* Compare Metrics Dialog */}
      <CompareMetricsDialog
        open={compareMetricsDialogOpen}
        onOpenChange={setCompareMetricsDialogOpen}
        competitorId={Number(id)}
        competitorName={competitor.name}
        competitorUrl={competitor.url}
      />
    </div>
  );
};

export default CompetitorDetail;
