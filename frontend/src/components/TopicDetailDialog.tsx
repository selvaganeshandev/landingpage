import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card } from "@/components/ui/card";
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
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { TrendingUp, TrendingDown, MessageSquare, ThumbsUp, ThumbsDown } from "lucide-react";

interface TopicDetailDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  topic: {
    id: number;
    name: string;
    keywords: string[];
    mentions: number;
    visibility: number;
    sentiment: number;
    trend: number;
    platforms: string[];
    color: string;
  } | null;
}

const mentionTimeline = [
  { date: "Nov 1", mentions: 12, visibility: 88 },
  { date: "Nov 5", mentions: 15, visibility: 90 },
  { date: "Nov 10", mentions: 18, visibility: 91 },
  { date: "Nov 15", mentions: 22, visibility: 89 },
  { date: "Nov 20", mentions: 19, visibility: 92 },
  { date: "Nov 25", mentions: 24, visibility: 94 },
];

const platformBreakdown = [
  { platform: "ChatGPT", mentions: 45, color: "hsl(var(--chart-1))" },
  { platform: "Claude", mentions: 28, color: "hsl(var(--chart-2))" },
  { platform: "Perplexity", mentions: 16, color: "hsl(var(--chart-3))" },
];

const keywordVariations = [
  { keyword: "muscle building", mentions: 34, position: 1.2, visibility: 95 },
  { keyword: "post-workout", mentions: 28, position: 1.5, visibility: 91 },
  { keyword: "athletic performance", mentions: 18, position: 1.8, visibility: 87 },
  { keyword: "strength training", mentions: 9, position: 2.1, visibility: 83 },
];

const sentimentBreakdown = [
  { name: "Positive", value: 78, color: "hsl(var(--success))" },
  { name: "Neutral", value: 18, color: "hsl(var(--muted))" },
  { name: "Negative", value: 4, color: "hsl(var(--destructive))" },
];

const relatedPrompts = [
  { prompt: "best vegan protein for muscle gain", mentions: 18, relevance: 95 },
  { prompt: "plant-based protein for athletes", mentions: 15, relevance: 92 },
  { prompt: "post-workout vegan protein", mentions: 12, relevance: 89 },
  { prompt: "muscle building plant protein", mentions: 8, relevance: 87 },
];

export const TopicDetailDialog = ({ open, onOpenChange, topic }: TopicDetailDialogProps) => {
  if (!topic) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-outfit text-2xl">{topic.name}</DialogTitle>
          <DialogDescription>
            Comprehensive analysis and performance metrics for this topic
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-4 gap-4">
            <Card className="p-4 border border-border">
              <div className="flex items-center justify-between mb-2">
                <MessageSquare className="h-5 w-5 text-muted-foreground" />
                <div className="flex items-center gap-1">
                  {topic.trend > 0 ? (
                    <TrendingUp className="h-4 w-4 text-success" />
                  ) : (
                    <TrendingDown className="h-4 w-4 text-destructive" />
                  )}
                  <span className={`text-xs font-medium ${topic.trend > 0 ? 'text-success' : 'text-destructive'}`}>
                    {topic.trend > 0 ? '+' : ''}{topic.trend}%
                  </span>
                </div>
              </div>
              <p className="text-2xl font-bold" style={{ color: topic.color }}>{topic.mentions}</p>
              <p className="text-xs text-muted-foreground">Total Mentions</p>
            </Card>

            <Card className="p-4 border border-border">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-muted-foreground">Visibility</span>
              </div>
              <p className="text-2xl font-bold">{topic.visibility}%</p>
              <Progress value={topic.visibility} className="h-1.5 mt-2" />
            </Card>

            <Card className="p-4 border border-border">
              <div className="flex items-center justify-between mb-2">
                <ThumbsUp className="h-5 w-5 text-success" />
              </div>
              <p className="text-2xl font-bold text-success">{topic.sentiment}%</p>
              <p className="text-xs text-muted-foreground">Positive Sentiment</p>
            </Card>

            <Card className="p-4 border border-border">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-muted-foreground">Platforms</span>
              </div>
              <p className="text-2xl font-bold">{topic.platforms.length}</p>
              <p className="text-xs text-muted-foreground">Active Platforms</p>
            </Card>
          </div>

          <Tabs defaultValue="timeline" className="space-y-6">
            <TabsList className="grid w-full grid-cols-5">
              <TabsTrigger value="timeline">Timeline</TabsTrigger>
              <TabsTrigger value="platforms">Platforms</TabsTrigger>
              <TabsTrigger value="keywords">Keywords</TabsTrigger>
              <TabsTrigger value="sentiment">Sentiment</TabsTrigger>
              <TabsTrigger value="prompts">Related Prompts</TabsTrigger>
            </TabsList>

            {/* Mention Timeline */}
            <TabsContent value="timeline" className="space-y-4">
              <Card className="p-6 border border-border">
                <h4 className="font-semibold mb-4">Mention Trend (Last 30 Days)</h4>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={mentionTimeline}>
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
                    <Line 
                      type="monotone" 
                      dataKey="mentions" 
                      stroke={topic.color} 
                      strokeWidth={3}
                      dot={{ fill: topic.color, r: 4 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </Card>
            </TabsContent>

            {/* Platform Breakdown */}
            <TabsContent value="platforms" className="space-y-4">
              <div className="grid grid-cols-2 gap-6">
                <Card className="p-6 border border-border">
                  <h4 className="font-semibold mb-4">Platform Distribution</h4>
                  <ResponsiveContainer width="100%" height={250}>
                    <PieChart>
                      <Pie
                        data={platformBreakdown}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={90}
                        paddingAngle={2}
                        dataKey="mentions"
                      >
                        {platformBreakdown.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </Card>

                <Card className="p-6 border border-border">
                  <h4 className="font-semibold mb-4">Mentions by Platform</h4>
                  <div className="space-y-4 mt-8">
                    {platformBreakdown.map((platform) => (
                      <div key={platform.platform}>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium">{platform.platform}</span>
                          <span className="text-sm font-bold">{platform.mentions}</span>
                        </div>
                        <Progress 
                          value={(platform.mentions / topic.mentions) * 100} 
                          className="h-2"
                        />
                      </div>
                    ))}
                  </div>
                </Card>
              </div>
            </TabsContent>

            {/* Keyword Variations */}
            <TabsContent value="keywords" className="space-y-4">
              <Card className="p-6 border border-border">
                <h4 className="font-semibold mb-4">Keyword Performance</h4>
                <div className="space-y-4">
                  {keywordVariations.map((kw) => (
                    <div key={kw.keyword} className="p-4 rounded-lg border border-border">
                      <div className="flex items-center justify-between mb-3">
                        <Badge variant="secondary" className="font-mono">{kw.keyword}</Badge>
                        <span className="text-sm font-bold">{kw.mentions} mentions</span>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <p className="text-xs text-muted-foreground mb-1">Avg Position</p>
                          <p className="text-lg font-bold">{kw.position}</p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground mb-1">Visibility</p>
                          <p className="text-lg font-bold">{kw.visibility}%</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </TabsContent>

            {/* Sentiment Breakdown */}
            <TabsContent value="sentiment" className="space-y-4">
              <div className="grid grid-cols-2 gap-6">
                <Card className="p-6 border border-border">
                  <h4 className="font-semibold mb-4">Sentiment Distribution</h4>
                  <ResponsiveContainer width="100%" height={250}>
                    <PieChart>
                      <Pie
                        data={sentimentBreakdown}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={90}
                        paddingAngle={2}
                        dataKey="value"
                        label
                      >
                        {sentimentBreakdown.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </Card>

                <Card className="p-6 border border-border">
                  <h4 className="font-semibold mb-4">Sentiment Breakdown</h4>
                  <div className="space-y-6 mt-8">
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 rounded-lg bg-success/10 flex items-center justify-center">
                        <ThumbsUp className="h-6 w-6 text-success" />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium">Positive</p>
                        <p className="text-2xl font-bold text-success">{sentimentBreakdown[0].value}%</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 rounded-lg bg-muted flex items-center justify-center">
                        <MessageSquare className="h-6 w-6 text-muted-foreground" />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium">Neutral</p>
                        <p className="text-2xl font-bold">{sentimentBreakdown[1].value}%</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 rounded-lg bg-destructive/10 flex items-center justify-center">
                        <ThumbsDown className="h-6 w-6 text-destructive" />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium">Negative</p>
                        <p className="text-2xl font-bold text-destructive">{sentimentBreakdown[2].value}%</p>
                      </div>
                    </div>
                  </div>
                </Card>
              </div>
            </TabsContent>

            {/* Related Prompts */}
            <TabsContent value="prompts" className="space-y-4">
              <Card className="p-6 border border-border">
                <h4 className="font-semibold mb-4">Related Prompts ({relatedPrompts.length})</h4>
                <div className="space-y-3">
                  {relatedPrompts.map((prompt, idx) => (
                    <div key={idx} className="p-4 rounded-lg border border-border hover:bg-accent/50 transition-colors">
                      <div className="flex items-center justify-between mb-2">
                        <p className="font-mono text-sm flex-1">{prompt.prompt}</p>
                        <div className="flex items-center gap-4 ml-4">
                          <div className="text-right">
                            <p className="text-xs text-muted-foreground">Relevance</p>
                            <p className="text-sm font-bold text-primary">{prompt.relevance}%</p>
                          </div>
                          <div className="text-right">
                            <p className="text-xs text-muted-foreground">Mentions</p>
                            <p className="text-sm font-bold">{prompt.mentions}</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </DialogContent>
    </Dialog>
  );
};
