import { useState } from "react";
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

const CompetitorDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [timePeriod, setTimePeriod] = useState("30");
  const [activeTab, setActiveTab] = useState("overview");

  // Mock data
  const competitor = {
    id: id || "myprotein",
    name: "MyProtein",
    url: "myprotein.com",
    logo: "🏋️",
    mentions: 187,
    visibility: 85,
    sentiment: 68,
    avgPosition: 2.1,
    shareOfVoice: 35,
    trend: 8,
    description: "Leading sports nutrition brand offering protein supplements, vitamins, and fitness accessories."
  };

  const mentionTrend = [
    { month: "Jul", mentions: 178, position: 2.3 },
    { month: "Aug", mentions: 182, position: 2.2 },
    { month: "Sep", mentions: 185, position: 2.2 },
    { month: "Oct", mentions: 188, position: 2.1 },
    { month: "Nov", mentions: 190, position: 2.1 },
    { month: "Dec", mentions: 191, position: 2.1 },
    { month: "Jan", mentions: 189, position: 2.1 },
    { month: "Feb", mentions: 188, position: 2.1 },
    { month: "Mar", mentions: 186, position: 2.1 },
    { month: "Apr", mentions: 187, position: 2.1 },
  ];

  const platformBreakdown = [
    { platform: "ChatGPT", mentions: 72, percentage: 38.5 },
    { platform: "Claude", mentions: 58, percentage: 31.0 },
    { platform: "Perplexity", mentions: 35, percentage: 18.7 },
    { platform: "Gemini", mentions: 22, percentage: 11.8 },
  ];

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

  return (
    <div className="p-8 space-y-6 bg-background">
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
              <div className="w-16 h-16 rounded-2xl gradient-primary shadow-glow flex items-center justify-center text-3xl">
                {competitor.logo}
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
            <p className="text-4xl font-bold font-outfit">{competitor.mentions}</p>
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
            <p className="text-4xl font-bold font-outfit">{competitor.visibility}%</p>
            <Progress value={competitor.visibility} className="h-2" />
          </div>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary backdrop-blur-sm bg-card/80">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground uppercase tracking-wider">Avg Position</p>
            <p className="text-4xl font-bold font-outfit">{competitor.avgPosition}</p>
            <p className="text-sm text-muted-foreground">Across all platforms</p>
          </div>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary backdrop-blur-sm bg-card/80">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground uppercase tracking-wider">Share of Voice</p>
            <p className="text-4xl font-bold font-outfit">{competitor.shareOfVoice}%</p>
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
                <h3 className="text-lg font-semibold font-outfit">Mention Volume & Position Trends</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Track mention frequency and average position over time
                </p>
              </div>
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
            </div>
          </Card>

          {/* Platform Breakdown */}
          <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
            <div className="space-y-6">
              <div className="pb-4 border-b border-border">
                <h3 className="text-lg font-semibold font-outfit">Platform Distribution</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Mention breakdown across AI platforms
                </p>
              </div>
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
                        <p className="font-bold font-outfit">{platform.mentions}</p>
                        <p className="text-xs text-muted-foreground">{platform.percentage}%</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
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
                  <h3 className="text-lg font-semibold mb-3 font-outfit">About {competitor.name}</h3>
                  <p className="text-muted-foreground leading-relaxed">{competitor.description}</p>
                </div>
                <div className="pt-4">
                  <h3 className="text-lg font-semibold mb-4 font-outfit">Sentiment Distribution</h3>
                  <div className="grid grid-cols-3 gap-4">
                    {sentimentData.map((item) => (
                      <div key={item.name} className="p-4 rounded-xl border border-border bg-muted/30">
                        <p className="text-sm text-muted-foreground mb-2">{item.name}</p>
                        <p className="text-3xl font-bold font-outfit">{item.value}%</p>
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
                        <div className="w-10 h-10 rounded-xl gradient-primary shadow-md flex items-center justify-center font-bold text-white font-outfit">
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
                    <h4 className="font-semibold mb-3 font-outfit text-success flex items-center gap-2">
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
                    <h4 className="font-semibold mb-3 font-outfit text-warning flex items-center gap-2">
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
            <h3 className="text-lg font-semibold mb-4 font-outfit">Quick Stats</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-border">
                <span className="text-sm text-muted-foreground">Positive Sentiment</span>
                <span className="text-lg font-bold font-outfit text-success">{competitor.sentiment}%</span>
              </div>
              <div className="flex items-center justify-between pb-3 border-b border-border">
                <span className="text-sm text-muted-foreground">Market Rank</span>
                <span className="text-lg font-bold font-outfit">#2</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Growth Rate</span>
                <span className="text-lg font-bold font-outfit text-success">+{competitor.trend}%</span>
              </div>
            </div>
          </Card>

          {/* Quick Actions */}
          <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
            <h3 className="text-lg font-semibold mb-4 font-outfit">Quick Actions</h3>
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
