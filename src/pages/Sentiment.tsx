import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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

const sentimentOverview = {
  positive: 74,
  neutral: 21,
  negative: 5,
};

const sentimentTrend = [
  { date: "Oct 1", positive: 68, neutral: 25, negative: 7 },
  { date: "Oct 8", positive: 71, neutral: 23, negative: 6 },
  { date: "Oct 15", positive: 72, neutral: 22, negative: 6 },
  { date: "Oct 22", positive: 73, neutral: 22, negative: 5 },
  { date: "Oct 29", positive: 74, neutral: 21, negative: 5 },
  { date: "Nov 5", positive: 75, neutral: 20, negative: 5 },
  { date: "Nov 12", positive: 74, neutral: 21, negative: 5 },
];

const thematicSentiment = [
  { theme: "Product Quality", positive: 85, neutral: 12, negative: 3, mentions: 89 },
  { theme: "Taste & Flavor", positive: 78, neutral: 18, negative: 4, mentions: 72 },
  { theme: "Price & Value", positive: 65, neutral: 28, negative: 7, mentions: 58 },
  { theme: "Ingredient Quality", positive: 88, neutral: 10, negative: 2, mentions: 94 },
  { theme: "Mixability", positive: 71, neutral: 22, negative: 7, mentions: 45 },
  { theme: "Customer Service", positive: 82, neutral: 15, negative: 3, mentions: 31 },
];

const platformSentiment = [
  { platform: "ChatGPT", positive: 76, neutral: 20, negative: 4 },
  { platform: "Claude", positive: 73, neutral: 22, negative: 5 },
  { platform: "Perplexity", positive: 71, neutral: 23, negative: 6 },
  { platform: "Gemini", positive: 78, neutral: 18, negative: 4 },
];

const competitorSentiment = [
  { name: "VegFit Pro", positive: 74, neutral: 21, negative: 5 },
  { name: "MyProtein", positive: 68, neutral: 25, negative: 7 },
  { name: "Naked Nutrition", positive: 71, neutral: 23, negative: 6 },
];

const COLORS = {
  positive: "hsl(var(--success))",
  neutral: "hsl(var(--warning))",
  negative: "hsl(var(--destructive))",
};

const Sentiment = () => {
  const pieData = [
    { name: "Positive", value: sentimentOverview.positive, color: COLORS.positive },
    { name: "Neutral", value: sentimentOverview.neutral, color: COLORS.neutral },
    { name: "Negative", value: sentimentOverview.negative, color: COLORS.negative },
  ];

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Sentiment Analysis</h1>
          <p className="text-muted-foreground mt-2">
            Deep dive into brand sentiment across AI platforms
          </p>
        </div>
        <Button>
          <FileText className="h-4 w-4 mr-2" />
          Export Sentiment Report
        </Button>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="p-6">
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
            <ArrowUpRight className="h-4 w-4 text-success" />
            <span className="text-success font-medium">+3.2%</span>
            <span className="text-muted-foreground">vs last period</span>
          </div>
        </Card>

        <Card className="p-6">
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
            <ArrowDownRight className="h-4 w-4 text-muted-foreground" />
            <span className="text-muted-foreground font-medium">-1.8%</span>
            <span className="text-muted-foreground">vs last period</span>
          </div>
        </Card>

        <Card className="p-6">
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
            <ArrowDownRight className="h-4 w-4 text-success" />
            <span className="text-success font-medium">-1.4%</span>
            <span className="text-muted-foreground">vs last period</span>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sentiment Distribution */}
        <Card className="p-6">
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
      <Card className="p-6">
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
        <TabsList className="grid w-full max-w-md grid-cols-2">
          <TabsTrigger value="platform">By Platform</TabsTrigger>
          <TabsTrigger value="competitor">Competitor Comparison</TabsTrigger>
        </TabsList>

        <TabsContent value="platform" className="space-y-4">
          <Card className="p-6">
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
          <Card className="p-6">
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
    </div>
  );
};

export default Sentiment;
