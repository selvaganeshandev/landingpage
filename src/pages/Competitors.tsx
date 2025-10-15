import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TimeFilter } from "@/components/TimeFilter";
import { TopBrandsList } from "@/components/TopBrandsList";
import { CompetitorHeatmap } from "@/components/CompetitorHeatmap";
import { useToast } from "@/hooks/use-toast";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { 
  Users,
  Plus,
  TrendingUp,
  TrendingDown,
  Target,
  FileText,
  Eye,
  MessageSquare
} from "lucide-react";
import { 
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Legend,
  Cell
} from "recharts";

const competitors = [
  {
    id: 1,
    name: "VegFit Pro",
    url: "vegfitpro.com",
    mentions: 221,
    visibility: 94,
    sentiment: 74,
    avgPosition: 1.6,
    shareOfVoice: 42,
    trend: 15,
    color: "hsl(var(--primary))",
    isYou: true
  },
  {
    id: 2,
    name: "MyProtein",
    url: "myprotein.com",
    mentions: 187,
    visibility: 85,
    sentiment: 68,
    avgPosition: 2.1,
    shareOfVoice: 35,
    trend: 8,
    color: "hsl(var(--chart-2))",
    isYou: false
  },
  {
    id: 3,
    name: "Naked Nutrition",
    url: "nakednutrition.com",
    mentions: 123,
    visibility: 78,
    sentiment: 71,
    avgPosition: 2.3,
    shareOfVoice: 23,
    trend: -3,
    color: "hsl(var(--chart-3))",
    isYou: false
  },
];

const competitiveMetrics = [
  { metric: "Visibility", vegfit: 94, myprotein: 85, naked: 78 },
  { metric: "Sentiment", vegfit: 74, myprotein: 68, naked: 71 },
  { metric: "Position", vegfit: 88, myprotein: 75, naked: 70 },
  { metric: "Coverage", vegfit: 82, myprotein: 78, naked: 68 },
  { metric: "Growth", vegfit: 85, myprotein: 72, naked: 65 },
];

const mentionHistory = [
  { month: "Jul", vegfit: 145, myprotein: 178, naked: 132 },
  { month: "Aug", vegfit: 158, myprotein: 182, naked: 135 },
  { month: "Sep", vegfit: 172, myprotein: 185, naked: 138 },
  { month: "Oct", vegfit: 184, myprotein: 188, naked: 140 },
  { month: "Nov", vegfit: 193, myprotein: 190, naked: 138 },
  { month: "Dec", vegfit: 205, myprotein: 191, naked: 135 },
  { month: "Jan", vegfit: 212, myprotein: 189, naked: 132 },
  { month: "Feb", vegfit: 218, myprotein: 188, naked: 128 },
  { month: "Mar", vegfit: 219, myprotein: 186, naked: 125 },
  { month: "Apr", vegfit: 221, myprotein: 187, naked: 123 },
];

const platformComparison = {
  "ChatGPT": [
    { brand: "VegFit Pro", mentions: 89 },
    { brand: "MyProtein", mentions: 72 },
    { brand: "Naked Nutrition", mentions: 45 },
  ],
  "Claude": [
    { brand: "VegFit Pro", mentions: 64 },
    { brand: "MyProtein", mentions: 58 },
    { brand: "Naked Nutrition", mentions: 38 },
  ],
  "Perplexity": [
    { brand: "VegFit Pro", mentions: 42 },
    { brand: "MyProtein", mentions: 35 },
    { brand: "Naked Nutrition", mentions: 25 },
  ],
  "Gemini": [
    { brand: "VegFit Pro", mentions: 26 },
    { brand: "MyProtein", mentions: 22 },
    { brand: "Naked Nutrition", mentions: 15 },
  ],
};

const competitiveInsights = [
  {
    title: "Market Leadership Maintained",
    description: "VegFit Pro maintains #1 position with 42% market share, 7% ahead of nearest competitor",
    type: "success",
    impact: "high"
  },
  {
    title: "Sentiment Advantage",
    description: "6% higher positive sentiment than MyProtein, driven by ingredient quality mentions",
    type: "success",
    impact: "medium"
  },
  {
    title: "MyProtein Gaining Momentum",
    description: "MyProtein increased mentions by 8% this month, focused on pricing positioning",
    type: "warning",
    impact: "medium"
  },
  {
    title: "Opportunity in Weight Loss",
    description: "Naked Nutrition dominates weight loss category - opportunity to increase presence",
    type: "opportunity",
    impact: "high"
  },
];

const Competitors = () => {
  const [timePeriod, setTimePeriod] = useState("90");
  const [selectedTab, setSelectedTab] = useState("overview");
  const { toast } = useToast();

  const handleExportReport = () => {
    toast({
      title: "Exporting Report",
      description: "Your competitor analysis report is being generated...",
    });
  };

  const handleAddCompetitor = () => {
    toast({
      title: "Add Competitor",
      description: "Opening competitor setup dialog...",
    });
  };

  const heatmapData = [
    {
      competitor: "VegFit Pro",
      platforms: { Grok: 22.5, Claude: 20.0, ChatGPT: 28.5, Perplexity: 19.0, "Google Gemini": 10.0 },
      isYou: true
    },
    {
      competitor: "MyProtein",
      platforms: { Grok: 18.0, Claude: 22.0, ChatGPT: 24.0, Perplexity: 21.0, "Google Gemini": 15.0 },
    },
    {
      competitor: "Naked Nutrition",
      platforms: { Grok: 15.0, Claude: 18.0, ChatGPT: 20.0, Perplexity: 22.0, "Google Gemini": 25.0 },
    },
  ];

  const topBrands = [
    { name: "VegFit Pro", url: "vegfitpro.com", mentions: 221, percentage: 10.9, isYou: true },
    { name: "MyProtein", url: "myprotein.com", mentions: 187, percentage: 30.1 },
    { name: "Naked Nutrition", url: "nakednutrition.com", mentions: 123, percentage: 17.5 },
    { name: "Marketmuse", url: "marketmuse.com", mentions: 110, percentage: 11.1 },
    { name: "Clearscope", url: "clearscope.io", mentions: 109, percentage: 11.0 },
  ];

  return (
    <div className="p-8 space-y-6">
      {/* Header with Tabs */}
      <div className="space-y-4">
        <Tabs value={selectedTab} onValueChange={setSelectedTab} className="w-full">
          <TabsList className="bg-muted/50">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="prompts">Prompts</TabsTrigger>
            <TabsTrigger value="competitors">Competitors</TabsTrigger>
            <TabsTrigger value="answer-gap">Answer Gap</TabsTrigger>
          </TabsList>
        </Tabs>

        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Competitor Analysis</h1>
            <p className="text-muted-foreground mt-1">
              Compare your brand's AI visibility against competitors
            </p>
          </div>
          <div className="flex gap-3">
            <Button variant="outline" onClick={handleExportReport}>
              <FileText className="h-4 w-4 mr-2" />
              Export Report
            </Button>
            <Button onClick={handleAddCompetitor}>
              <Plus className="h-4 w-4 mr-2" />
              Add Competitor
            </Button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center justify-between">
          <TimeFilter selected={timePeriod} onSelect={setTimePeriod} />
          <Select defaultValue="all">
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="All Competitors" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Competitors</SelectItem>
              <SelectItem value="vegfit">VegFit Pro</SelectItem>
              <SelectItem value="myprotein">MyProtein</SelectItem>
              <SelectItem value="naked">Naked Nutrition</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Competitor Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {competitors.map((competitor, idx) => (
          <Card key={competitor.id} className={`p-6 ${competitor.isYou ? 'ring-2 ring-primary' : ''}`}>
            <div className="space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-xl font-semibold">{competitor.name}</h3>
                    {competitor.isYou && (
                      <Badge variant="default">You</Badge>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">{competitor.url}</p>
                </div>
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary to-secondary text-primary-foreground flex items-center justify-center font-bold">
                  #{idx + 1}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Mentions</p>
                  <p className="text-2xl font-bold">{competitor.mentions}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Share</p>
                  <p className="text-2xl font-bold">{competitor.shareOfVoice}%</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Visibility</p>
                  <p className="text-lg font-bold">{competitor.visibility}%</p>
                  <Progress value={competitor.visibility} className="h-1 mt-1" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Sentiment</p>
                  <p className="text-lg font-bold">{competitor.sentiment}%</p>
                  <Progress value={competitor.sentiment} className="h-1 mt-1" />
                </div>
              </div>

              <div className="pt-3 border-t border-border">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Trend</span>
                  <div className="flex items-center gap-1">
                    {competitor.trend > 0 ? (
                      <TrendingUp className="h-4 w-4 text-success" />
                    ) : (
                      <TrendingDown className="h-4 w-4 text-destructive" />
                    )}
                    <span className={`font-medium ${competitor.trend > 0 ? 'text-success' : 'text-destructive'}`}>
                      {competitor.trend > 0 ? '+' : ''}{competitor.trend}%
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Main Grid with Charts and Top Brands */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* Brand Visibility Over Time */}
          <Card className="p-6">
            <div className="space-y-4">
              <div>
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <TrendingUp className="h-5 w-5" />
                  Brand Visibility Over Time
                </h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Track how often each brand is mentioned by AI providers
                </p>
              </div>
              <ResponsiveContainer width="100%" height={350}>
                <LineChart data={mentionHistory}>
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
                  <Line 
                    type="monotone" 
                    dataKey="vegfit" 
                    name="VegFit Pro"
                    stroke="hsl(var(--primary))" 
                    strokeWidth={3}
                    dot={{ fill: "hsl(var(--primary))", r: 4 }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="myprotein" 
                    name="MyProtein"
                    stroke="hsl(var(--chart-2))" 
                    strokeWidth={2}
                    dot={{ fill: "hsl(var(--chart-2))", r: 3 }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="naked" 
                    name="Naked Nutrition"
                    stroke="hsl(var(--chart-3))" 
                    strokeWidth={2}
                    dot={{ fill: "hsl(var(--chart-3))", r: 3 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* Heatmap */}
          <CompetitorHeatmap 
            data={heatmapData} 
            platforms={["Grok", "Claude", "ChatGPT", "Perplexity", "Google Gemini"]} 
          />
        </div>

        {/* Top Brands Sidebar */}
        <div>
          <TopBrandsList brands={topBrands} totalMentions={989} />
        </div>
      </div>

      {/* Competitive Analysis */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-6">Competitive Strength Analysis</h3>
          <ResponsiveContainer width="100%" height={350}>
            <RadarChart data={competitiveMetrics}>
              <PolarGrid stroke="hsl(var(--border))" />
              <PolarAngleAxis 
                dataKey="metric" 
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
              />
              <PolarRadiusAxis angle={90} domain={[0, 100]} stroke="hsl(var(--muted-foreground))" />
              <Radar 
                name="VegFit Pro" 
                dataKey="vegfit" 
                stroke="hsl(var(--primary))" 
                fill="hsl(var(--primary))" 
                fillOpacity={0.3}
                strokeWidth={2}
              />
              <Radar 
                name="MyProtein" 
                dataKey="myprotein" 
                stroke="hsl(var(--chart-2))" 
                fill="hsl(var(--chart-2))" 
                fillOpacity={0.2}
              />
              <Radar 
                name="Naked Nutrition" 
                dataKey="naked" 
                stroke="hsl(var(--chart-3))" 
                fill="hsl(var(--chart-3))" 
                fillOpacity={0.2}
              />
              <Legend />
            </RadarChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-6">Competitive Intelligence</h3>
          <div className="space-y-3">
            {competitiveInsights.map((insight, idx) => (
              <div key={idx} className="p-4 rounded-lg border border-border">
                <div className="flex items-start gap-3">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                    insight.type === 'success' ? 'bg-success/10' :
                    insight.type === 'warning' ? 'bg-warning/10' :
                    'bg-primary/10'
                  }`}>
                    <Target className={`h-4 w-4 ${
                      insight.type === 'success' ? 'text-success' :
                      insight.type === 'warning' ? 'text-warning' :
                      'text-primary'
                    }`} />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="font-semibold text-sm">{insight.title}</h4>
                      <Badge variant={insight.impact === 'high' ? 'default' : 'secondary'} className="text-xs">
                        {insight.impact}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">{insight.description}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Platform Breakdown */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-6">Platform-Specific Competition</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {Object.entries(platformComparison).map(([platform, data]) => (
            <div key={platform} className="space-y-4">
              <h4 className="font-medium text-center">{platform}</h4>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={data}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis 
                    dataKey="brand" 
                    stroke="hsl(var(--muted-foreground))" 
                    fontSize={10}
                    angle={-45}
                    textAnchor="end"
                    height={80}
                  />
                  <YAxis stroke="hsl(var(--muted-foreground))" fontSize={10} />
                  <Tooltip />
                  <Bar dataKey="mentions" radius={[8, 8, 0, 0]}>
                    <Cell fill="hsl(var(--primary))" />
                    <Cell fill="hsl(var(--chart-2))" />
                    <Cell fill="hsl(var(--chart-3))" />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ))}
        </div>
      </Card>

      {/* Competitive Insights */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-6">Competitive Intelligence</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {competitiveInsights.map((insight, idx) => (
            <div key={idx} className="p-4 rounded-lg border border-border">
              <div className="flex items-start gap-3 mb-2">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                  insight.type === 'success' ? 'bg-success/10' :
                  insight.type === 'warning' ? 'bg-warning/10' :
                  'bg-primary/10'
                }`}>
                  <Target className={`h-4 w-4 ${
                    insight.type === 'success' ? 'text-success' :
                    insight.type === 'warning' ? 'text-warning' :
                    'text-primary'
                  }`} />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="font-semibold">{insight.title}</h4>
                    <Badge variant={insight.impact === 'high' ? 'default' : 'secondary'} className="text-xs">
                      {insight.impact} impact
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">{insight.description}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
};

export default Competitors;
