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
  Sparkles
} from "lucide-react";
import { TopicDetailDialog } from "@/components/TopicDetailDialog";
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
  const [selectedTopic, setSelectedTopic] = useState<Topic | null>(null);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [topicTrends, setTopicTrends] = useState<any[]>([]);
  const [keywordPerformance, setKeywordPerformance] = useState<any[]>([]);
  const [promptSuggestions, setPromptSuggestions] = useState<any[]>([]);

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


  const handleGenerateMore = async () => {
    if (!selectedDomain?.id || topics.length === 0) {
      toast({
        title: "No Topics Available",
        description: "Please create topics first to generate prompt suggestions.",
        variant: "destructive"
      });
      return;
    }

    try {
      setLoading(true);
      
      // Fetch more prompts from different topics
      const allPrompts: any[] = [];
      for (const topic of topics.slice(0, 3)) { // Get from top 3 topics
        try {
          const promptsData = await apiClient.getTopicPrompts({ topic_id: topic.id });
          // Ensure promptsData is an array
          const dataArray = Array.isArray(promptsData) ? promptsData : (promptsData?.results || []);
          allPrompts.push(...dataArray.map((prompt: any) => ({
            prompt: prompt.prompt_text,
            relevance: prompt.relevance_score || 0,
            volume: prompt.search_volume || "medium",
            topics: [topic.name]
          })));
        } catch (err) {
          console.error(`Error fetching prompts for topic ${topic.id}:`, err);
        }
      }

      // Sort by relevance and get top 10
      const topPrompts = allPrompts
        .sort((a, b) => b.relevance - a.relevance)
        .slice(0, 10);

      setPromptSuggestions(topPrompts);
      
      toast({
        title: "Prompts Updated",
        description: `Generated ${topPrompts.length} new prompt suggestions.`,
      });
    } catch (err) {
      console.error("Error generating more prompts:", err);
      toast({
        title: "Error",
        description: "Failed to generate more prompts. Please try again.",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
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
        const topicsData = await apiClient.getTopicsByDomain(selectedDomain.id);
        
        // Transform API data to match UI format
        const transformedTopics: Topic[] = topicsData.map((topic: any, index: number) => {
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

        // Fetch topic trends (time-series data)
        if (transformedTopics.length > 0) {
          try {
            const trendsData = await apiClient.getTopicTrends(undefined, 90);
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

          // Fetch keyword performance (aggregate from all topics)
          try {
            const allKeywordData: any[] = [];
            for (const topic of transformedTopics.slice(0, 5)) { // Limit to first 5 topics
              try {
                const keywordData = await apiClient.getTopicKeywordAnalytics(topic.id);
                // Ensure keywordData is an array
                const dataArray = Array.isArray(keywordData) ? keywordData : (keywordData?.results || []);
                allKeywordData.push(...dataArray);
              } catch (err) {
                console.error(`Error fetching keywords for topic ${topic.id}:`, err);
              }
            }
            
            // Aggregate and sort by mentions
            const keywordMap = new Map<string, any>();
            allKeywordData.forEach((item: any) => {
              const keyword = item.keyword;
              if (!keywordMap.has(keyword)) {
                keywordMap.set(keyword, {
                  keyword,
                  mentions: 0,
                  position: 0,
                  visibility: 0
                });
              }
              const existing = keywordMap.get(keyword)!;
              existing.mentions += item.mentions || 0;
            });
            
            const sortedKeywords = Array.from(keywordMap.values())
              .sort((a, b) => b.mentions - a.mentions)
              .slice(0, 10)
              .map(item => ({
                ...item,
                position: item.position || 0,
                visibility: item.visibility || 0
              }));
            
            setKeywordPerformance(sortedKeywords);
          } catch (err) {
            console.error("Error fetching keyword performance:", err);
          }

          // Fetch prompt suggestions
          try {
            const promptsData = await apiClient.getTopicPrompts({ topic_id: transformedTopics[0]?.id });
            // Ensure promptsData is an array (handle both direct array and paginated response)
            const dataArray = Array.isArray(promptsData) ? promptsData : (promptsData?.results || []);
            const suggestions = dataArray.slice(0, 6).map((prompt: any) => ({
              prompt: prompt.prompt_text,
              relevance: prompt.relevance_score || 0,
              volume: prompt.search_volume || "medium",
              topics: [prompt.topic_name || "General"]
            }));
            setPromptSuggestions(suggestions);
          } catch (err) {
            console.error("Error fetching prompt suggestions:", err);
            setPromptSuggestions([]);
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

  // Topic distribution for pie chart
  const topicDistribution = useMemo(() => {
    return filteredTopics.map((t, index) => ({
      name: t.name,
      value: t.mentions,
      color: t.color
    }));
  }, [filteredTopics]);

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
                {/* Optimize button hidden as per requirements */}
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
            disabled={loading || promptSuggestions.length === 0}
          >
            <Sparkles className="h-3 w-3 mr-1" />
            Generate More
          </Button>
        </div>
        {promptSuggestions.length > 0 ? (
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
        ) : (
          <div className="flex items-center justify-center h-[200px] text-muted-foreground">
            <p>No prompt suggestions available yet</p>
          </div>
        )}
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
    </div>
  );
};

export default Topics;
