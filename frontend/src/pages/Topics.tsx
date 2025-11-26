import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/hooks/use-toast";
import { useContentGeneration } from "@/hooks/useContentGeneration";
import { useDomainStore } from "@/stores/domainStore";
import { apiClient } from "@/services/api";
import { PageLoader } from "@/components/PageLoader";
import {
  TrendingUp,
  TrendingDown,
  Sparkles,
  Target,
  Loader2
} from "lucide-react";
import { TopicDetailDialog } from "@/components/TopicDetailDialog";
import { TopicOptimizeDialog } from "@/components/TopicOptimizeDialog";
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

// Chart color palette
const CHART_COLORS = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
  "hsl(var(--chart-5))",
  "hsl(var(--success))"
];

interface Topic {
  id: number;
  name: string;
  keywords: string[];
  mentions: number;
  visibility: number;
  sentiment: number;
  trend: number;
  platforms: string[];
  color: string;
}

const Topics = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { navigateToContentGeneration } = useContentGeneration();
  const { selectedDomain } = useDomainStore();
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [optimizeDialogOpen, setOptimizeDialogOpen] = useState(false);
  const [selectedTopic, setSelectedTopic] = useState<Topic | null>(null);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [topicTrends, setTopicTrends] = useState<any[]>([]);
  const [topicDistributionData, setTopicDistributionData] = useState<any[]>([]);
  const [keywordPerformance, setKeywordPerformance] = useState<any[]>([]);
  const [promptSuggestions, setPromptSuggestions] = useState<any[]>([]);
  const [promptLoading, setPromptLoading] = useState(false);

  const handleGenerateContent = (topic: typeof topics[0]) => {
    navigateToContentGeneration({
      topic: topic.name,
      keywords: topic.keywords,
      source: "Topic Analysis",
      priority: topic.trend > 10 ? "high" : "medium",
      articleType: "guide"
    });
  };

  const handleViewDetails = (topic: typeof topics[0]) => {
    setSelectedTopic(topic);
    setDetailDialogOpen(true);
  };

  const handleOptimize = (topic: typeof topics[0]) => {
    setSelectedTopic(topic);
    setOptimizeDialogOpen(true);
  };


  const handleGenerateMore = async () => {
    if (!selectedDomain?.id) {
      toast({
        title: "No Domain Selected",
        description: "Please select a domain to generate prompt suggestions.",
        variant: "destructive"
      });
      return;
    }

    try {
      setPromptLoading(true);

      // Generate new prompts using ChatGPT via the API (with higher limit and generateNew=true)
      const promptsData: any = await apiClient.getTopicPromptSuggestions(selectedDomain.id, 12, true);
      const promptsArray = Array.isArray(promptsData) ? promptsData : (promptsData?.results || []);
      
      const suggestions = promptsArray.map((prompt: any) => ({
        prompt: prompt.prompt_text || prompt.prompt || "",
        topics: prompt.topic_name ? [prompt.topic_name] : ["General"],
        keyword: prompt.keyword || ""
      }));

      if (suggestions.length === 0) {
        toast({
          title: "No Suggestions Available",
          description: "No prompt suggestions generated. Make sure topics and keywords exist for this domain.",
          variant: "destructive"
        });
        return;
      }

      setPromptSuggestions(suggestions);
      
      toast({
        title: "Prompts Generated",
        description: `Generated ${suggestions.length} new AI-powered prompt suggestions.`,
      });
    } catch (err: any) {
      console.error("Error generating more prompts:", err);
      toast({
        title: "Error",
        description: err.message || "Failed to generate more prompts. Please try again.",
        variant: "destructive"
      });
    } finally {
      setPromptLoading(false);
    }
  };

  // Fetch topics data
  useEffect(() => {
    const fetchTopics = async () => {
      if (!selectedDomain?.id) {
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);

        // Fetch topics for the selected domain
        const topicsData: any = await apiClient.getTopicsByDomain(selectedDomain.id);
        const topicsArray = Array.isArray(topicsData) ? topicsData : (topicsData?.results || []);
        
        // Transform API data to match UI format
        const transformedTopics: Topic[] = topicsArray.map((topic: any, index: number) => {
          // Convert sentiment from -1 to 1 range to 0-100 percentage
          const sentimentScore = parseFloat(topic.sentiment_score || 0);
          const sentimentPercentage = ((sentimentScore + 1) / 2) * 100; // Normalize to 0-100
          
          return {
            id: topic.id,
            name: topic.name,
            keywords: topic.keyword_list || [],
            mentions: topic.total_mentions || 0,
            visibility: parseFloat(topic.visibility_score || 0),
            sentiment: Math.round(sentimentPercentage),
            trend: parseFloat(topic.trend_percentage || 0),
            platforms: topic.platform_list || [],
            color: CHART_COLORS[index % CHART_COLORS.length]
          };
        });

        setTopics(transformedTopics);

        // Fetch topic distribution using new dedicated endpoint
        try {
          const distributionData: any = await apiClient.getTopicDistribution(selectedDomain.id);
          const distributionArray = Array.isArray(distributionData) ? distributionData : (distributionData?.results || []);
          // Add colors to match the topics
          const distributionWithColors = distributionArray.map((item: any, index: number) => ({
            ...item,
            color: CHART_COLORS[index % CHART_COLORS.length]
          }));
          setTopicDistributionData(distributionWithColors);
        } catch (err) {
          console.error("Error fetching topic distribution:", err);
          setTopicDistributionData([]);
        }

        // Fetch topic trends (time-series data)
        if (transformedTopics.length > 0) {
          try {
            const trendsData: any = await apiClient.getTopicTrends(undefined, 90);
            // Ensure trendsData is an array
            const dataArray = Array.isArray(trendsData) ? trendsData : (trendsData?.results || []);
            
            // Group by date and aggregate by topic
            const trendsByDate = new Map<string, Map<number, number>>();
            
            dataArray.forEach((item: any) => {
              const date = new Date(item.timestamp);
              const monthKey = date.toLocaleDateString('en-US', { month: 'short' });
              
              if (!trendsByDate.has(monthKey)) {
                trendsByDate.set(monthKey, new Map());
              }
              
              const monthData = trendsByDate.get(monthKey)!;
              monthData.set(item.topic, item.total_mentions || 0);
            });
            
            // Transform to chart format - show top 3 topics
            const topTopics = transformedTopics.slice(0, 3);
            const chartData = Array.from(trendsByDate.entries()).map(([month, topicData]) => {
              const dataPoint: any = { month };
              topTopics.forEach((topic, idx) => {
                const key = `topic${idx + 1}`;
                dataPoint[key] = topicData.get(topic.id) || 0;
              });
              return dataPoint;
            });
            
            setTopicTrends(chartData);
          } catch (err) {
            console.error("Error fetching trends:", err);
            // Set empty array on error
            setTopicTrends([]);
          }

          // Fetch keyword performance using new dedicated endpoint
          try {
            const keywordData: any = await apiClient.getTopicKeywordPerformance(selectedDomain.id, 10);
            const keywordArray = Array.isArray(keywordData) ? keywordData : (keywordData?.results || []);
            // Format data for chart (already aggregated by backend)
            const formattedKeywords = keywordArray.map((item: any) => ({
              keyword: item.keyword,
              mentions: item.total_mentions || 0,
              position: item.avg_position || 0,
              visibility: item.visibility_score || 0
            }));
            setKeywordPerformance(formattedKeywords);
          } catch (err) {
            console.error("Error fetching keyword performance:", err);
            setKeywordPerformance([]);
          }

          // Fetch existing prompt suggestions from database (on load)
          try {
            const promptsData: any = await apiClient.getTopicPromptSuggestions(selectedDomain.id, 6, false);
            const promptsArray = Array.isArray(promptsData) ? promptsData : (promptsData?.results || []);
            const suggestions = promptsArray.map((prompt: any) => ({
              prompt: prompt.prompt_text || prompt.prompt || "",
              topics: prompt.topic_name ? [prompt.topic_name] : ["General"],
              keyword: prompt.keyword || ""
            }));
            setPromptSuggestions(suggestions);
          } catch (err: any) {
            console.error("Error fetching prompt suggestions:", err);
            setPromptSuggestions([]);
            // Don't show error toast here as it's not critical - just log it
          }
        }

      } catch (err: any) {
        console.error("Error fetching topics:", err);
        setError(err.message || "Failed to load topics");
        toast({
          title: "Error",
          description: "Failed to load topics. Please try again.",
          variant: "destructive"
        });
      } finally {
        setLoading(false);
      }
    };

    fetchTopics();
  }, [selectedDomain?.id, toast]);

  // Use topics directly (search removed)
  const filteredTopics = topics;

  // Show PageLoader while loading
  if (loading) {
    return <PageLoader />;
  }

  return (
    <div className="p-8 space-y-8 bg-background animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Topic-Based Tracking</h1>
          <p className="text-muted-foreground mt-2">
            Monitor performance across key topics and categories
          </p>
        </div>
        {/* Generate Topics and Add Topic buttons hidden as per requirements */}
      </div>

      {/* Error State */}
      {error && (
        <Card className="p-6 border-destructive">
          <p className="text-destructive">{error}</p>
        </Card>
      )}

      {/* No Domain Selected */}
      {!selectedDomain && (
        <Card className="p-6 border border-border">
          <p className="text-muted-foreground text-center">
            Please select a domain to view topics.
          </p>
        </Card>
      )}

      {/* No Topics */}
      {!error && selectedDomain && filteredTopics.length === 0 && (
        <Card className="p-6 border border-border">
          <p className="text-muted-foreground text-center">
            No topics found for this domain. Topics will be created automatically when domain processing completes.
          </p>
        </Card>
      )}

      {/* Content - Only show if has data */}
      {!error && filteredTopics.length > 0 && (
        <>

      {/* Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="p-6 border border-border">
          <h3 className="text-lg font-semibold mb-6">Topic Distribution</h3>
          {topicDistributionData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={topicDistributionData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {topicDistributionData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "var(--radius)",
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[250px] text-muted-foreground">
              <p>No distribution data available yet</p>
            </div>
          )}
        </Card>

        <Card className="p-6 lg:col-span-2">
          <h3 className="text-lg font-semibold mb-6">Topic Trends Over Time</h3>
          {topicTrends.length > 0 ? (
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
                {filteredTopics.slice(0, 3).map((topic, idx) => (
                  <Line 
                    key={topic.id}
                    type="monotone" 
                    dataKey={`topic${idx + 1}`} 
                    name={topic.name} 
                    stroke={topic.color} 
                    strokeWidth={2} 
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[250px] text-muted-foreground">
              <p>No trend data available yet</p>
            </div>
          )}
        </Card>
      </div>

      {/* Topics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {filteredTopics.map((topic) => (
          <Card key={topic.id} className="p-6 transition-all duration-300 border border-border hover:border-primary">
            <div className="space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-xl font-semibold mb-2">{topic.name}</h3>
                  <div className="flex flex-wrap gap-2 mb-3">
                    {topic.keywords && topic.keywords.length > 0 ? (
                      <>
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
                      </>
                    ) : (
                      <span className="text-xs text-muted-foreground italic">No keywords</span>
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
                  {topic.platforms && topic.platforms.length > 0 ? (
                    topic.platforms.map((platform) => (
                      <Badge key={platform} variant="outline" className="text-xs">
                        {platform}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-xs text-muted-foreground italic">No platform data available</span>
                  )}
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
                <Button 
                  size="sm" 
                  variant="outline" 
                  onClick={() => handleOptimize(topic)}
                >
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
          <Button 
            variant="outline" 
            size="sm" 
            onClick={handleGenerateMore}
            disabled={promptLoading || !selectedDomain?.id}
          >
            <Sparkles className="h-3 w-3 mr-1" />
            {promptLoading ? "Generating..." : "Generate More"}
          </Button>
        </div>
        <div className="relative min-h-[200px]">
          {promptLoading && (
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center rounded-lg bg-background/80 backdrop-blur-sm border border-dashed border-border">
              <Loader2 className="h-5 w-5 animate-spin text-primary mb-2" />
              <p className="text-sm text-muted-foreground">Generating fresh prompts…</p>
            </div>
          )}
          {promptSuggestions.length > 0 ? (
            <div className={`space-y-3 ${promptLoading ? "opacity-60 pointer-events-none" : ""}`}>
              {promptSuggestions.map((suggestion, idx) => (
                <div key={idx} className="p-4 rounded-lg border border-border hover:bg-accent/50 transition-colors">
                  <div className="flex items-start justify-between mb-2">
                    <p className="font-mono text-sm font-medium flex-1">{suggestion.prompt}</p>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    {suggestion.topics.map((topic) => (
                      <Badge key={topic} variant="outline" className="text-xs">
                        {topic}
                      </Badge>
                    ))}
                    {suggestion.keyword && (
                      <Badge variant="secondary" className="text-xs">
                        {suggestion.keyword}
                      </Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              <p>No prompt suggestions available yet</p>
            </div>
          )}
        </div>
      </Card>

      {/* Keyword Performance */}
      <Card className="p-6 border border-border">
        <h3 className="text-lg font-semibold mb-6">Top Keyword Performance</h3>
        {keywordPerformance.length > 0 ? (
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
        ) : (
          <div className="flex items-center justify-center h-[300px] text-muted-foreground">
            <p>No keyword performance data available yet</p>
          </div>
        )}
      </Card>
        </>
      )}

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
    </div>
  );
};

export default Topics;
