import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  TrendingUp, 
  TrendingDown,
  Target,
  Award,
  FileText,
  ArrowUpRight,
  ArrowDownRight,
  Crown
} from "lucide-react";
import { 
  BarChart,
  Bar,
  LineChart,
  Line,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Legend,
  ScatterChart,
  Scatter,
  ZAxis,
  Cell
} from "recharts";

const overallShare = [
  { brand: "VegFit Pro", share: 42, mentions: 221, change: 15 },
  { brand: "MyProtein", share: 35, mentions: 187, change: 8 },
  { brand: "Naked Nutrition", share: 23, mentions: 123, change: -3 },
];

const platformShare = {
  "ChatGPT": [
    { brand: "VegFit Pro", share: 44 },
    { brand: "MyProtein", share: 34 },
    { brand: "Naked Nutrition", share: 22 },
  ],
  "Claude": [
    { brand: "VegFit Pro", share: 41 },
    { brand: "MyProtein", share: 36 },
    { brand: "Naked Nutrition", share: 23 },
  ],
  "Perplexity": [
    { brand: "VegFit Pro", share: 40 },
    { brand: "MyProtein", share: 38 },
    { brand: "Naked Nutrition", share: 22 },
  ],
  "Gemini": [
    { brand: "VegFit Pro", share: 43 },
    { brand: "MyProtein", share: 32 },
    { brand: "Naked Nutrition", share: 25 },
  ],
};

const shareHistory = [
  { month: "Jul", vegfit: 38, myprotein: 37, naked: 25 },
  { month: "Aug", vegfit: 39, myprotein: 36, naked: 25 },
  { month: "Sep", vegfit: 40, myprotein: 36, naked: 24 },
  { month: "Oct", vegfit: 42, myprotein: 35, naked: 23 },
  { month: "Nov", vegfit: 42, myprotein: 35, naked: 23 },
];

const positioningMatrix = [
  { brand: "VegFit Pro", visibility: 94, sentiment: 74, mentions: 221, color: "hsl(var(--primary))" },
  { brand: "MyProtein", visibility: 85, sentiment: 68, mentions: 187, color: "hsl(var(--chart-2))" },
  { brand: "Naked Nutrition", visibility: 78, sentiment: 71, mentions: 123, color: "hsl(var(--chart-3))" },
];

const competitiveStrength = [
  { category: "Visibility", vegfit: 94, myprotein: 85, naked: 78 },
  { category: "Sentiment", vegfit: 74, myprotein: 68, naked: 71 },
  { category: "Avg Position", vegfit: 88, myprotein: 75, naked: 70 },
  { category: "Mention Growth", vegfit: 85, myprotein: 72, naked: 65 },
  { category: "Topic Coverage", vegfit: 82, myprotein: 78, naked: 68 },
];

const opportunities = [
  { 
    prompt: "best protein powder for weight loss",
    avgMentions: 45,
    currentShare: 28,
    opportunity: "high",
    competitors: ["MyProtein (38%)", "Naked Nutrition (34%)"]
  },
  { 
    prompt: "affordable vegan protein",
    avgMentions: 38,
    currentShare: 35,
    opportunity: "medium",
    competitors: ["Naked Nutrition (42%)", "MyProtein (23%)"]
  },
  { 
    prompt: "organic plant protein powder",
    avgMentions: 32,
    currentShare: 15,
    opportunity: "high",
    competitors: ["Naked Nutrition (52%)", "MyProtein (33%)"]
  },
];

const ShareOfVoice = () => {
  const dominanceScore = 94;
  const marketPosition = 1;

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Share of Voice</h1>
          <p className="text-muted-foreground mt-2">
            Competitive benchmarking and market position analysis
          </p>
        </div>
        <Button>
          <FileText className="h-4 w-4 mr-2" />
          Export Market Report
        </Button>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="p-6">
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-sm text-muted-foreground font-medium">Market Share</p>
              <h3 className="text-4xl font-bold text-primary mt-2">42%</h3>
            </div>
            <div className="p-3 rounded-xl bg-gradient-to-br from-primary to-secondary text-primary-foreground">
              <Target className="h-6 w-6" />
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <ArrowUpRight className="h-4 w-4 text-success" />
            <span className="text-success font-medium">+15%</span>
            <span className="text-muted-foreground">vs last period</span>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-sm text-muted-foreground font-medium">Market Position</p>
              <h3 className="text-4xl font-bold text-primary mt-2">#{marketPosition}</h3>
            </div>
            <div className="p-3 rounded-xl bg-gradient-to-br from-primary to-secondary text-primary-foreground">
              <Crown className="h-6 w-6" />
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Market Leader</span>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-sm text-muted-foreground font-medium">Dominance Score</p>
              <h3 className="text-4xl font-bold text-primary mt-2">{dominanceScore}</h3>
            </div>
            <div className="p-3 rounded-xl bg-gradient-to-br from-primary to-secondary text-primary-foreground">
              <Award className="h-6 w-6" />
            </div>
          </div>
          <Progress value={dominanceScore} className="mt-2" />
        </Card>
      </div>

      {/* Market Share Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-6">Overall Market Share</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={overallShare} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis type="number" stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <YAxis 
                dataKey="brand" 
                type="category" 
                stroke="hsl(var(--muted-foreground))" 
                fontSize={12}
                width={120}
              />
              <Tooltip 
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "var(--radius)",
                }}
              />
              <Bar dataKey="share" radius={[0, 8, 8, 0]}>
                <Cell fill="hsl(var(--primary))" />
                <Cell fill="hsl(var(--chart-2))" />
                <Cell fill="hsl(var(--chart-3))" />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-6">Share of Voice Trends</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={shareHistory}>
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
        </Card>
      </div>

      {/* Competitive Positioning */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-6">Competitive Strength Radar</h3>
          <ResponsiveContainer width="100%" height={350}>
            <RadarChart data={competitiveStrength}>
              <PolarGrid stroke="hsl(var(--border))" />
              <PolarAngleAxis 
                dataKey="category" 
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
          <h3 className="text-lg font-semibold mb-6">Brand Positioning Matrix</h3>
          <ResponsiveContainer width="100%" height={350}>
            <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
              <CartesianGrid stroke="hsl(var(--border))" />
              <XAxis 
                type="number" 
                dataKey="visibility" 
                name="Visibility Score"
                domain={[70, 100]}
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
                label={{ value: "Visibility Score", position: "bottom", fill: "hsl(var(--muted-foreground))" }}
              />
              <YAxis 
                type="number" 
                dataKey="sentiment" 
                name="Sentiment %"
                domain={[60, 80]}
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
                label={{ value: "Sentiment %", angle: -90, position: "left", fill: "hsl(var(--muted-foreground))" }}
              />
              <ZAxis type="number" dataKey="mentions" range={[200, 1000]} />
              <Tooltip 
                cursor={{ strokeDasharray: "3 3" }}
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "var(--radius)",
                }}
              />
              <Scatter name="Brands" data={positioningMatrix}>
                {positioningMatrix.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
          <div className="mt-4 space-y-2">
            {positioningMatrix.map((brand) => (
              <div key={brand.brand} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: brand.color }} />
                  <span className="font-medium">{brand.brand}</span>
                </div>
                <span className="text-muted-foreground">{brand.mentions} mentions</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Platform-Specific Share */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-6">Platform-Specific Share of Voice</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {Object.entries(platformShare).map(([platform, data]) => (
            <div key={platform} className="space-y-4">
              <h4 className="font-medium text-center">{platform}</h4>
              <div className="space-y-3">
                {data.map((brand, idx) => (
                  <div key={brand.brand} className="space-y-1">
                    <div className="flex items-center justify-between text-sm">
                      <span className={idx === 0 ? "font-medium" : "text-muted-foreground"}>
                        {brand.brand}
                      </span>
                      <span className="font-bold">{brand.share}%</span>
                    </div>
                    <Progress value={brand.share} className="h-2" />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Market Opportunities */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-6">Market Opportunities</h3>
        <div className="space-y-4">
          {opportunities.map((opp) => (
            <div key={opp.prompt} className="p-4 rounded-lg border border-border hover:bg-accent/50 transition-colors">
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <p className="font-mono text-sm mb-2">{opp.prompt}</p>
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <span>{opp.avgMentions} avg mentions</span>
                    <span>Current share: {opp.currentShare}%</span>
                  </div>
                </div>
                <Badge 
                  variant={opp.opportunity === "high" ? "default" : "secondary"}
                  className={opp.opportunity === "high" ? "bg-warning text-warning-foreground" : ""}
                >
                  {opp.opportunity} opportunity
                </Badge>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">Leading competitors:</span>
                {opp.competitors.map((comp, idx) => (
                  <Badge key={idx} variant="outline" className="text-xs">
                    {comp}
                  </Badge>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
};

export default ShareOfVoice;
