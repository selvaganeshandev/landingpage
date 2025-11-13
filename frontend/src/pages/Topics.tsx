import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/hooks/use-toast";
import { useContentGeneration } from "@/hooks/useContentGeneration";
import { 
  Brain,
  Plus,
  Search,
  TrendingUp,
  TrendingDown,
  Sparkles,
  FileText,
  Target
} from "lucide-react";
import { TopicDetailDialog } from "@/components/TopicDetailDialog";
import { TopicOptimizeDialog } from "@/components/TopicOptimizeDialog";
import { GenerateTopicsDialog } from "@/components/GenerateTopicsDialog";
import { AddTopicDialog } from "@/components/AddTopicDialog";
import { 
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Legend 
} from "recharts";

const topics = [
  {
    id: 1,
    name: "Muscle Building & Performance",
    keywords: ["muscle building", "post-workout", "athletic performance", "strength training"],
    mentions: 89,
    visibility: 92,
    sentiment: 78,
    trend: 15,
    platforms: ["ChatGPT", "Claude", "Perplexity"],
    color: "hsl(var(--chart-1))"
  },
  {
    id: 2,
    name: "Weight Loss & Nutrition",
    keywords: ["weight loss", "calorie control", "fat loss", "diet"],
    mentions: 67,
    visibility: 68,
    sentiment: 71,
    trend: 22,
    platforms: ["ChatGPT", "Gemini"],
    color: "hsl(var(--chart-2))"
  },
  {
    id: 3,
    name: "Ingredient Quality & Safety",
    keywords: ["organic", "clean ingredients", "non-GMO", "quality"],
    mentions: 54,
    visibility: 88,
    sentiment: 85,
    trend: 8,
    platforms: ["Claude", "Perplexity"],
    color: "hsl(var(--chart-3))"
  },
  {
    id: 4,
    name: "Taste & Mixability",
    keywords: ["taste", "flavor", "texture", "mixability"],
    mentions: 42,
    visibility: 75,
    sentiment: 72,
    trend: -3,
    platforms: ["ChatGPT", "Claude", "Gemini"],
    color: "hsl(var(--chart-4))"
  },
  {
    id: 5,
    name: "Price & Value",
    keywords: ["affordable", "price", "value", "budget"],
    mentions: 38,
    visibility: 65,
    sentiment: 64,
    trend: 5,
    platforms: ["Perplexity", "Gemini"],
    color: "hsl(var(--chart-5))"
  },
  {
    id: 6,
    name: "Sustainability & Ethics",
    keywords: ["sustainable", "eco-friendly", "ethical", "vegan"],
    mentions: 31,
    visibility: 82,
    sentiment: 88,
    trend: 18,
    platforms: ["Claude", "Perplexity"],
    color: "hsl(var(--success))"
  },
];

const topicDistribution = topics.map(t => ({
  name: t.name,
  value: t.mentions,
  color: t.color
}));

const topicTrends = [
  { month: "Jul", muscle: 75, weight: 52, ingredients: 48, taste: 41, price: 35, sustainability: 25 },
  { month: "Aug", muscle: 78, weight: 55, ingredients: 50, taste: 42, price: 36, sustainability: 27 },
  { month: "Sep", muscle: 82, weight: 58, ingredients: 51, taste: 42, price: 37, sustainability: 28 },
  { month: "Oct", muscle: 85, weight: 62, ingredients: 52, taste: 41, price: 38, sustainability: 29 },
  { month: "Nov", muscle: 89, weight: 67, ingredients: 54, taste: 42, price: 38, sustainability: 31 },
];

const promptSuggestions = [
  { prompt: "best vegan protein for muscle gain", relevance: 95, volume: "high", topics: ["Muscle Building", "Performance"] },
  { prompt: "plant-based protein for weight loss", relevance: 88, volume: "high", topics: ["Weight Loss", "Nutrition"] },
  { prompt: "organic vegan protein powder", relevance: 92, volume: "medium", topics: ["Ingredient Quality"] },
  { prompt: "affordable vegan protein", relevance: 78, volume: "medium", topics: ["Price & Value"] },
  { prompt: "sustainable plant protein brands", relevance: 85, volume: "medium", topics: ["Sustainability"] },
  { prompt: "best tasting vegan protein powder", relevance: 82, volume: "high", topics: ["Taste & Mixability"] },
];

const keywordPerformance = [
  { keyword: "vegan protein powder", mentions: 156, position: 1.2, visibility: 95 },
  { keyword: "plant-based protein", mentions: 124, position: 1.5, visibility: 91 },
  { keyword: "best vegan protein", mentions: 98, position: 1.4, visibility: 93 },
  { keyword: "organic protein powder", mentions: 67, position: 1.8, visibility: 86 },
  { keyword: "muscle building protein", mentions: 54, position: 1.6, visibility: 89 },
];

const Topics = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { navigateToContentGeneration } = useContentGeneration();
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [optimizeDialogOpen, setOptimizeDialogOpen] = useState(false);
  const [generateDialogOpen, setGenerateDialogOpen] = useState(false);
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [selectedTopic, setSelectedTopic] = useState<typeof topics[0] | null>(null);

  const handleGenerateTopics = () => {
    setGenerateDialogOpen(true);
  };

  const handleGenerateContent = (topic: typeof topics[0]) => {
    navigateToContentGeneration({
      topic: topic.name,
      keywords: topic.keywords,
      source: "Topic Analysis",
      priority: topic.trend > 10 ? "high" : "medium",
      articleType: "guide"
    });
  };

  const handleAddTopic = () => {
    setAddDialogOpen(true);
  };

  const handleViewDetails = (topic: typeof topics[0]) => {
    setSelectedTopic(topic);
    setDetailDialogOpen(true);
  };

  const handleOptimize = (topic: typeof topics[0]) => {
    setSelectedTopic(topic);
    setOptimizeDialogOpen(true);
  };

  const handleGenerateMore = () => {
    toast({
      title: "Generating Prompts",
      description: "AI is creating new prompt suggestions...",
    });
  };

  return (
    <div className="p-8 space-y-8 bg-background animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Topic-Based Tracking</h1>
          <p className="text-muted-foreground mt-2">
            Monitor performance across key topics and categories
          </p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={handleGenerateTopics}>
            <Sparkles className="h-4 w-4 mr-2" />
            Generate Topics
          </Button>
          <Button onClick={handleAddTopic} className="gradient-primary shadow-md shadow-primary/20">
            <Plus className="h-4 w-4 mr-2" />
            Add Topic
          </Button>
        </div>
      </div>

      {/* Search Bar */}
      <Card className="p-6 border border-border">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input placeholder="Search topics, keywords, or prompts..." className="pl-10" />
        </div>
      </Card>

      {/* Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="p-6 border border-border">
          <h3 className="text-lg font-semibold mb-6">Topic Distribution</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={topicDistribution}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={90}
                paddingAngle={2}
                dataKey="value"
              >
                {topicDistribution.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-6 lg:col-span-2">
          <h3 className="text-lg font-semibold mb-6">Topic Trends Over Time</h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={topicTrends}>
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
              <Line type="monotone" dataKey="muscle" name="Muscle Building" stroke="hsl(var(--chart-1))" strokeWidth={2} />
              <Line type="monotone" dataKey="weight" name="Weight Loss" stroke="hsl(var(--chart-2))" strokeWidth={2} />
              <Line type="monotone" dataKey="ingredients" name="Ingredients" stroke="hsl(var(--chart-3))" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Topics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {topics.map((topic) => (
          <Card key={topic.id} className="p-6 transition-all duration-300 border border-border hover:border-primary">
            <div className="space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-xl font-semibold mb-2">{topic.name}</h3>
                  <div className="flex flex-wrap gap-2 mb-3">
                    {topic.keywords.slice(0, 3).map((keyword) => (
                      <Badge key={keyword} variant="secondary" className="text-xs">
                        {keyword}
                      </Badge>
                    ))}
                    {topic.keywords.length > 3 && (
                      <Badge variant="secondary" className="text-xs">
                        +{topic.keywords.length - 3}
                      </Badge>
                    )}
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold" style={{ color: topic.color }}>{topic.mentions}</p>
                  <p className="text-xs text-muted-foreground">mentions</p>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Visibility</p>
                  <p className="text-lg font-bold">{topic.visibility}%</p>
                  <Progress value={topic.visibility} className="h-1 mt-1" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Sentiment</p>
                  <p className="text-lg font-bold">{topic.sentiment}%</p>
                  <Progress value={topic.sentiment} className="h-1 mt-1" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Trend</p>
                  <div className="flex items-center gap-1">
                    {topic.trend > 0 ? (
                      <TrendingUp className="h-4 w-4 text-success" />
                    ) : (
                      <TrendingDown className="h-4 w-4 text-destructive" />
                    )}
                    <p className={`text-lg font-bold ${topic.trend > 0 ? 'text-success' : 'text-destructive'}`}>
                      {topic.trend > 0 ? '+' : ''}{topic.trend}%
                    </p>
                  </div>
                </div>
              </div>

              <div className="pt-2 border-t border-border">
                <p className="text-xs text-muted-foreground mb-2">Active Platforms:</p>
                <div className="flex flex-wrap gap-2">
                  {topic.platforms.map((platform) => (
                    <Badge key={platform} variant="outline" className="text-xs">
                      {platform}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="flex gap-2">
                <Button 
                  size="sm" 
                  variant="default" 
                  onClick={() => handleGenerateContent(topic)}
                  className="gradient-primary"
                >
                  <Sparkles className="h-3 w-3 mr-1" />
                  Generate Content
                </Button>
                <Button size="sm" variant="outline" onClick={() => handleViewDetails(topic)}>View Details</Button>
                <Button size="sm" variant="outline" onClick={() => handleOptimize(topic)}>
                  <Target className="h-3 w-3 mr-1" />
                  Optimize
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* AI-Generated Prompt Suggestions */}
      <Card className="p-6 border border-border">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold">AI-Generated Prompt Suggestions</h3>
          <Button variant="outline" size="sm" onClick={handleGenerateMore}>
            <Sparkles className="h-3 w-3 mr-1" />
            Generate More
          </Button>
        </div>
        <div className="space-y-3">
          {promptSuggestions.map((suggestion, idx) => (
            <div key={idx} className="p-4 rounded-lg border border-border hover:bg-accent/50 transition-colors">
              <div className="flex items-start justify-between mb-2">
                <p className="font-mono text-sm font-medium flex-1">{suggestion.prompt}</p>
                <div className="flex items-center gap-3 ml-4">
                  <Badge variant={suggestion.volume === "high" ? "default" : "secondary"}>
                    {suggestion.volume} volume
                  </Badge>
                  <div className="text-right">
                    <p className="text-sm font-bold text-primary">{suggestion.relevance}%</p>
                    <p className="text-xs text-muted-foreground">relevance</p>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {suggestion.topics.map((topic) => (
                  <Badge key={topic} variant="outline" className="text-xs">
                    {topic}
                  </Badge>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Keyword Performance */}
      <Card className="p-6 border border-border">
        <h3 className="text-lg font-semibold mb-6">Top Keyword Performance</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={keywordPerformance} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis type="number" stroke="hsl(var(--muted-foreground))" fontSize={12} />
            <YAxis 
              dataKey="keyword" 
              type="category" 
              stroke="hsl(var(--muted-foreground))" 
              fontSize={12}
              width={150}
            />
            <Tooltip 
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "var(--radius)",
              }}
            />
            <Bar dataKey="mentions" fill="hsl(var(--primary))" radius={[0, 8, 8, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </Card>

      {/* Dialogs */}
      <TopicDetailDialog 
        open={detailDialogOpen}
        onOpenChange={setDetailDialogOpen}
        topic={selectedTopic}
      />
      <TopicOptimizeDialog
        open={optimizeDialogOpen}
        onOpenChange={setOptimizeDialogOpen}
        topic={selectedTopic}
      />
      <GenerateTopicsDialog
        open={generateDialogOpen}
        onOpenChange={setGenerateDialogOpen}
      />
      <AddTopicDialog
        open={addDialogOpen}
        onOpenChange={setAddDialogOpen}
      />
    </div>
  );
};

export default Topics;
