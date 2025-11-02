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

const visibilityTrend = [
  { month: "Jan", score: 68, mentions: 145, avgPosition: 2.1, sentiment: 68 },
  { month: "Feb", score: 71, mentions: 158, avgPosition: 2.0, sentiment: 70 },
  { month: "Mar", score: 75, mentions: 172, avgPosition: 1.9, sentiment: 71 },
  { month: "Apr", score: 78, mentions: 184, avgPosition: 1.8, sentiment: 72 },
  { month: "May", score: 82, mentions: 193, avgPosition: 1.7, sentiment: 73 },
  { month: "Jun", score: 85, mentions: 205, avgPosition: 1.7, sentiment: 73 },
  { month: "Jul", score: 88, mentions: 212, avgPosition: 1.6, sentiment: 74 },
  { month: "Aug", score: 89, mentions: 218, avgPosition: 1.6, sentiment: 74 },
  { month: "Sep", score: 91, mentions: 219, avgPosition: 1.6, sentiment: 74 },
  { month: "Oct", score: 92, mentions: 221, avgPosition: 1.6, sentiment: 74 },
  { month: "Nov", score: 94, mentions: 221, avgPosition: 1.6, sentiment: 74 },
];

const platformGrowth = [
  { month: "Jan", chatgpt: 45, claude: 38, perplexity: 32, gemini: 20 },
  { month: "Feb", chatgpt: 48, claude: 41, perplexity: 35, gemini: 24 },
  { month: "Mar", chatgpt: 52, claude: 44, perplexity: 38, gemini: 28 },
  { month: "Apr", chatgpt: 56, claude: 47, perplexity: 41, gemini: 32 },
  { month: "May", chatgpt: 60, claude: 51, perplexity: 43, gemini: 35 },
  { month: "Jun", chatgpt: 65, claude: 54, perplexity: 45, gemini: 38 },
  { month: "Jul", chatgpt: 70, claude: 58, perplexity: 47, gemini: 41 },
  { month: "Aug", chatgpt: 75, claude: 61, perplexity: 49, gemini: 43 },
  { month: "Sep", chatgpt: 78, claude: 63, perplexity: 50, gemini: 45 },
  { month: "Oct", chatgpt: 82, claude: 64, perplexity: 51, gemini: 46 },
  { month: "Nov", chatgpt: 89, claude: 64, perplexity: 42, gemini: 26 },
];

const competitorComparison = [
  { month: "Jan", vegfit: 145, myprotein: 178, naked: 132 },
  { month: "Feb", vegfit: 158, myprotein: 182, naked: 135 },
  { month: "Mar", vegfit: 172, myprotein: 185, naked: 138 },
  { month: "Apr", vegfit: 184, myprotein: 188, naked: 140 },
  { month: "May", vegfit: 193, myprotein: 190, naked: 138 },
  { month: "Jun", vegfit: 205, myprotein: 191, naked: 135 },
  { month: "Jul", vegfit: 212, myprotein: 189, naked: 132 },
  { month: "Aug", vegfit: 218, myprotein: 188, naked: 128 },
  { month: "Sep", vegfit: 219, myprotein: 186, naked: 125 },
  { month: "Oct", vegfit: 221, myprotein: 187, naked: 123 },
  { month: "Nov", vegfit: 221, myprotein: 187, naked: 123 },
];

const seasonalPattern = [
  { month: "Jan", mentions: 145, avgYear: 152 },
  { month: "Feb", mentions: 158, avgYear: 148 },
  { month: "Mar", mentions: 172, avgYear: 165 },
  { month: "Apr", mentions: 184, avgYear: 178 },
  { month: "May", mentions: 193, avgYear: 188 },
  { month: "Jun", mentions: 205, avgYear: 195 },
  { month: "Jul", mentions: 212, avgYear: 202 },
  { month: "Aug", mentions: 218, avgYear: 210 },
  { month: "Sep", mentions: 219, avgYear: 215 },
  { month: "Oct", mentions: 221, avgYear: 218 },
  { month: "Nov", mentions: 221, avgYear: 220 },
  { month: "Dec", mentions: 0, avgYear: 210 },
];

const milestones = [
  { date: "Jan 2024", event: "Launched AI visibility tracking", impact: "Baseline established" },
  { date: "Mar 2024", event: "Crossed 170 monthly mentions", impact: "+18% growth" },
  { date: "Jun 2024", event: "Reached #1 position in ChatGPT", impact: "Market leader status" },
  { date: "Aug 2024", event: "Visibility score hit 90", impact: "+25% from baseline" },
  { date: "Oct 2024", event: "Achieved 42% market share", impact: "Category dominance" },
];

const forecast = [
  { month: "Nov", actual: 221, forecast: null, lower: null, upper: null },
  { month: "Dec", actual: null, forecast: 228, lower: 218, upper: 238 },
  { month: "Jan", actual: null, forecast: 235, lower: 222, upper: 248 },
  { month: "Feb", actual: null, forecast: 242, lower: 226, upper: 258 },
  { month: "Mar", actual: null, forecast: 248, lower: 229, upper: 267 },
];

const HistoricalTrends = () => {
  const { toast } = useToast();

  const handleExportReport = () => {
    toast({
      title: "Exporting Report",
      description: "Your historical trends report is being generated...",
    });
  };

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
          <Select defaultValue="12">
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
        <Card className="p-6 border border-border">
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground font-medium">Visibility Growth</p>
            <h3 className="text-3xl font-bold text-success">+38%</h3>
            <div className="flex items-center gap-2 text-sm">
              <TrendingUp className="h-4 w-4 text-success" />
              <span className="text-muted-foreground">Year over year</span>
            </div>
          </div>
        </Card>

        <Card className="p-6 border border-border">
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground font-medium">Mention Growth</p>
            <h3 className="text-3xl font-bold text-success">+52%</h3>
            <div className="flex items-center gap-2 text-sm">
              <TrendingUp className="h-4 w-4 text-success" />
              <span className="text-muted-foreground">Since January</span>
            </div>
          </div>
        </Card>

        <Card className="p-6 border border-border">
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground font-medium">Position Improvement</p>
            <h3 className="text-3xl font-bold text-success">-24%</h3>
            <div className="flex items-center gap-2 text-sm">
              <TrendingDown className="h-4 w-4 text-success" />
              <span className="text-muted-foreground">Lower is better</span>
            </div>
          </div>
        </Card>

        <Card className="p-6 border border-border">
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground font-medium">Market Share Gain</p>
            <h3 className="text-3xl font-bold text-success">+12%</h3>
            <div className="flex items-center gap-2 text-sm">
              <TrendingUp className="h-4 w-4 text-success" />
              <span className="text-muted-foreground">This year</span>
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
      </Card>

      {/* Milestones */}
      <Card className="p-6 border border-border">
        <h3 className="text-lg font-semibold mb-6">Key Milestones</h3>
        <div className="space-y-4">
          {milestones.map((milestone, idx) => (
            <div key={idx} className="flex items-start gap-4 pb-4 border-b border-border last:border-0 last:pb-0">
              <div className="w-20 h-20 rounded-lg bg-gradient-to-br from-primary to-secondary text-primary-foreground flex items-center justify-center flex-shrink-0">
                <Calendar className="h-8 w-8" />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <p className="font-semibold">{milestone.event}</p>
                  <Badge variant="secondary">{milestone.date}</Badge>
                </div>
                <p className="text-sm text-muted-foreground">{milestone.impact}</p>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
};

export default HistoricalTrends;
