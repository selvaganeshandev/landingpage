import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TimeFilter } from "@/components/TimeFilter";
import { 
  ArrowLeft, 
  TrendingUp,
  TrendingDown,
  Building2,
  ExternalLink,
  Share2,
  FileText,
  Target,
  MessageSquare
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
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
import { apiClient } from "@/services/api";
import { useAuth } from "@/contexts/AuthContext";
import { getActiveDomainId } from "@/utils/activeDomain";
import { useDomainStore } from "@/stores/domainStore";

const CompetitorDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user } = useAuth();
  const { selectedDomain } = useDomainStore();
  const [timePeriod, setTimePeriod] = useState("30");
  const [activeTab, setActiveTab] = useState("overview");
  const [domainId, setDomainId] = useState<string | null>(null);
  const [competitor, setCompetitor] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [mentionTrend, setMentionTrend] = useState<any[]>([]);
  const [platformBreakdown, setPlatformBreakdown] = useState<any[]>([]);
  const [sentimentData, setSentimentData] = useState<any[]>([]);
  const [topMentions, setTopMentions] = useState<any[]>([]);

  // Sync domainId
  useEffect(() => {
    if (!user) return;
    if (selectedDomain?.id) {
      const newDomainId = String(selectedDomain.id);
      if (newDomainId !== domainId) {
        setDomainId(newDomainId);
        return;
      }
    }
    const serverActiveDomain = getActiveDomainId(user);
    const serverDomainId = serverActiveDomain || '';
    if (serverDomainId !== domainId) {
      setDomainId(serverDomainId);
    }
  }, [user, selectedDomain?.id, domainId]);

  // Load competitor data
  useEffect(() => {
    const loadCompetitorData = async () => {
      if (!domainId || !id) return;
      setIsLoading(true);
      try {
        // Get all competitors to find the one matching the URL slug
        const competitorsList = await apiClient.get(`/competitors/competitors/by_domain/?domain_id=${domainId}`);
        const competitors = Array.isArray(competitorsList) ? competitorsList : [];
        
        // Find competitor by URL (id is URL slug without .com)
        const foundCompetitor = competitors.find((c: any) => {
          const urlSlug = c.url?.replace(/^https?:\/\//, '').replace(/\.com$/, '').replace(/\./g, '');
          return urlSlug === id || c.url?.includes(id) || c.name?.toLowerCase().replace(/\s+/g, '') === id.toLowerCase();
        });
        
        if (!foundCompetitor) {
          toast({
            title: "Competitor not found",
            description: "The requested competitor could not be found.",
            variant: "destructive",
          });
          navigate('/competitors');
          return;
        }
        
        // Load competitor detail and analytics
        const competitorId = foundCompetitor.id;
        if (!competitorId) {
          toast({
            title: "Error",
            description: "Competitor ID not found.",
            variant: "destructive",
          });
          navigate('/competitors');
          return;
        }
        
        const [detail, analytics] = await Promise.all([
          apiClient.getCompetitorDetail(competitorId),
          apiClient.getEngineCompetitorAnalytics(competitorId).catch(() => null),
        ]);
        
        // Format competitor data
        const rawSentiment = Number(detail.sentiment_score || 0);
        const sentimentPercent = Math.round((rawSentiment + 1) * 50);
        
        setCompetitor({
          id: detail.id,
          name: detail.name || 'Unknown',
          url: detail.url || '',
          mentions: detail.total_mentions || 0,
          visibility: Math.round(Number(detail.visibility_score || 0)),
          sentiment: sentimentPercent,
          avgPosition: Number(detail.average_position || 0).toFixed(1),
          shareOfVoice: Math.round(Number(detail.share_of_voice_percentage || 0)),
          trend: Number(detail.trend_percentage || 0),
        });
        
        // Load analytics data if available
        if (analytics && Array.isArray(analytics)) {
          // Build mention trend from analytics
          const trendMap = new Map<string, { mentions: number; positions: number[] }>();
          analytics.forEach((a: any) => {
            const date = a.timestamp || a.created_at;
            const month = date ? new Date(date).toLocaleDateString('en-US', { month: 'short' }) : '';
            if (!trendMap.has(month)) {
              trendMap.set(month, { mentions: 0, positions: [] });
            }
            const entry = trendMap.get(month)!;
            entry.mentions += a.total_mentions || 0;
            if (a.position) entry.positions.push(a.position);
          });
          
          const trends = Array.from(trendMap.entries()).map(([month, data]) => ({
            month,
            mentions: data.mentions,
            position: data.positions.length > 0 ? (data.positions.reduce((a, b) => a + b, 0) / data.positions.length) : 0,
          })).sort((a, b) => a.month.localeCompare(b.month));
          
          setMentionTrend(trends);
        }
        
        // Load platform breakdown from competitor analytics
        if (analytics && Array.isArray(analytics)) {
          const platformMap = new Map<string, number>();
          analytics.forEach((a: any) => {
            const platform = a.platform || 'Overall';
            platformMap.set(platform, (platformMap.get(platform) || 0) + (a.total_mentions || 0));
          });
          
          const total = Array.from(platformMap.values()).reduce((a, b) => a + b, 0);
          const breakdown = Array.from(platformMap.entries()).map(([platform, mentions]) => ({
            platform,
            mentions,
            percentage: total > 0 ? Number(((mentions / total) * 100).toFixed(1)) : 0,
          }));
          
          setPlatformBreakdown(breakdown);
        }
        
        // Load sentiment data
        const sentimentMap = { positive: 0, neutral: 0, negative: 0 };
        if (analytics && Array.isArray(analytics)) {
          analytics.forEach((a: any) => {
            const score = Number(a.sentiment_score || 0);
            if (score > 0.33) sentimentMap.positive++;
            else if (score >= -0.33) sentimentMap.neutral++;
            else sentimentMap.negative++;
          });
        }
        
        const totalSentiment = sentimentMap.positive + sentimentMap.neutral + sentimentMap.negative;
        if (totalSentiment > 0) {
          setSentimentData([
            { name: "Positive", value: Math.round((sentimentMap.positive / totalSentiment) * 100), color: "hsl(var(--success))" },
            { name: "Neutral", value: Math.round((sentimentMap.neutral / totalSentiment) * 100), color: "hsl(var(--warning))" },
            { name: "Negative", value: Math.round((sentimentMap.negative / totalSentiment) * 100), color: "hsl(var(--destructive))" },
          ]);
        }
        
      } catch (error: any) {
        toast({
          title: "Error loading competitor",
          description: error.message || "Failed to load competitor details",
          variant: "destructive",
        });
        navigate('/competitors');
      } finally {
        setIsLoading(false);
      }
    };
    
    void loadCompetitorData();
  }, [domainId, id, navigate, toast]);

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

  if (isLoading) {
    return (
      <div className="p-8 space-y-6 bg-background animate-fade-in">
        <div className="flex items-center justify-center h-64">
          <p className="text-muted-foreground">Loading competitor details...</p>
        </div>
      </div>
    );
  }

  if (!competitor) {
    return (
      <div className="p-8 space-y-6 bg-background animate-fade-in">
        <div className="flex items-center justify-center h-64">
          <p className="text-muted-foreground">Competitor not found</p>
        </div>
      </div>
    );
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
              <div className="w-16 h-16 rounded-2xl gradient-primary shadow-glow flex items-center justify-center">
                <span className="text-2xl font-bold text-white font-inter">
                  {competitor.name.substring(0, 1).toUpperCase()}
                </span>
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
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary backdrop-blur-sm bg-card/80">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground uppercase tracking-wider">Total Mentions</p>
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
            <p className="text-sm text-muted-foreground uppercase tracking-wider">Visibility Score</p>
            <p className="text-4xl font-bold font-inter">{competitor.visibility}</p>
            <Progress value={competitor.visibility} className="h-2" />
          </div>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary backdrop-blur-sm bg-card/80">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground uppercase tracking-wider">Avg Position</p>
            <p className="text-4xl font-bold font-inter">{competitor.avgPosition}</p>
            <p className="text-sm text-muted-foreground">Across all platforms</p>
          </div>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary backdrop-blur-sm bg-card/80">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground uppercase tracking-wider">Share of Voice</p>
            <p className="text-4xl font-bold font-inter">{competitor.shareOfVoice}%</p>
            <p className="text-sm text-muted-foreground">Market share</p>
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
                  <p className="text-muted-foreground">No trend data available yet.</p>
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
                  <p className="text-muted-foreground">No platform data available yet.</p>
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
                  <p className="text-muted-foreground leading-relaxed">
                    Competitive analysis and performance metrics for {competitor.name}.
                  </p>
                </div>
                {sentimentData.length > 0 && (
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
                )}
              </TabsContent>

              <TabsContent value="mentions" className="space-y-3">
                {topMentions.length > 0 ? (
                  topMentions.map((mention, idx) => (
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
                  ))
                ) : (
                  <div className="flex items-center justify-center py-8">
                    <p className="text-muted-foreground">No mentions data available yet.</p>
                  </div>
                )}
              </TabsContent>

              <TabsContent value="swot" className="space-y-4">
                <div className="flex items-center justify-center py-8">
                  <p className="text-muted-foreground">SWOT analysis coming soon.</p>
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
                <span className="text-sm text-muted-foreground">Positive Sentiment</span>
                <span className="text-lg font-bold font-inter text-success">{competitor.sentiment}%</span>
              </div>
              <div className="flex items-center justify-between pb-3 border-b border-border">
                <span className="text-sm text-muted-foreground">Market Rank</span>
                <span className="text-lg font-bold font-inter">#2</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Growth Rate</span>
                <span className="text-lg font-bold font-inter text-success">+{competitor.trend}%</span>
              </div>
            </div>
          </Card>

          {/* Quick Actions */}
          <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
            <h3 className="text-lg font-semibold mb-4 font-inter">Quick Actions</h3>
            <div className="space-y-2">
              <Button variant="outline" className="w-full justify-start border border-border" asChild>
                <a href={`https://${competitor.url}`} target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="h-4 w-4 mr-2" />
                  Visit Website
                </a>
              </Button>
              <Button variant="outline" className="w-full justify-start border border-border">
                <MessageSquare className="h-4 w-4 mr-2" />
                View All Mentions
              </Button>
              <Button variant="outline" className="w-full justify-start border border-border">
                <Target className="h-4 w-4 mr-2" />
                Compare Metrics
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default CompetitorDetail;
