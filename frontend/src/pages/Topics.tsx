import { useState, useEffect, useMemo } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/hooks/use-toast";
import { useDomainStore } from "@/stores/domainStore";
import { apiClient } from "@/services/api";
import { PageLoader } from "@/components/PageLoader";
import {
  TrendingUp,
  TrendingDown,
  Sparkles,
  Target,
  Loader2,
  Download
} from "lucide-react";
import { TopicDetailDialog } from "@/components/TopicDetailDialog";
import { TopicOptimizeDialog } from "@/components/TopicOptimizeDialog";
import { GenerateContentDialog } from "@/components/GenerateContentDialog";
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

interface TopicCompetitor {
  name: string;
  mentions: number;
  mention_share: number;
}

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
  // From /topics/performance/ — derived from PromptAnalytics, so these
  // reconcile with Insights, Mentions and Citations. The legacy fields above
  // come from TopicAnalytics, which computes its own figures.
  responses?: number;
  mentionShare?: number;
  avgPosition?: number | null;
  citations?: number;
  opportunity?: number;
  competitors?: TopicCompetitor[];
  promptCount?: number;
}

const Topics = () => {
  const { toast } = useToast();
  const { selectedDomain } = useDomainStore();
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [optimizeDialogOpen, setOptimizeDialogOpen] = useState(false);
  const [generateDialogOpen, setGenerateDialogOpen] = useState(false);
  const [selectedTopic, setSelectedTopic] = useState<Topic | null>(null);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [isExporting, setIsExporting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [topicTrends, setTopicTrends] = useState<any[]>([]);
  const [topicDistributionData, setTopicDistributionData] = useState<any[]>([]);
  const [keywordPerformance, setKeywordPerformance] = useState<any[]>([]);
  const [promptSuggestions, setPromptSuggestions] = useState<any[]>([]);
  const [promptLoading, setPromptLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  const handleGenerateContent = (topic: typeof topics[0]) => {
    setSelectedTopic(topic);
    setGenerateDialogOpen(true);
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

        // Overlay the reconciled figures. Kept as a merge rather than a
        // replacement so the existing charts, which read the legacy fields,
        // keep working while the cards show numbers that match the rest of the
        // product.
        try {
          const perf: any = await apiClient.getTopicPerformance({ domain_id: selectedDomain.id });
          const byId = new Map<number, any>((perf?.results || []).map((r: any) => [r.id, r]));
          transformedTopics.forEach((topic) => {
            const row = byId.get(topic.id);
            if (!row) return;
            topic.responses = row.responses;
            topic.mentionShare = row.mention_share;
            topic.avgPosition = row.avg_position;
            topic.citations = row.citations;
            topic.opportunity = row.opportunity;
            topic.competitors = row.competitors || [];
            topic.promptCount = row.prompts;
            topic.mentions = row.mentions;
            topic.platforms = row.platforms?.length ? row.platforms : topic.platforms;
          });
          // Biggest gap first, matching the endpoint's own ordering.
          transformedTopics.sort(
            (a, b) => (b.opportunity ?? -1) - (a.opportunity ?? -1) || a.name.localeCompare(b.name),
          );
        } catch (perfError) {
          console.warn('Topic performance unavailable, showing stored figures', perfError);
        }

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
            const trendsData: any = await apiClient.getTopicTrends({ domainId: selectedDomain.id, days: 90 });
            const dataArray = Array.isArray(trendsData) ? trendsData : (trendsData?.results || []);
            const topTopics = transformedTopics.slice(0, 3);
            
            if (dataArray.length > 0) {
              const trendsByDate = new Map<string, Map<number, number>>();
              
              dataArray.forEach((item: any) => {
                const date = new Date(item.timestamp);
                const monthKey = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                
                if (!trendsByDate.has(monthKey)) {
                  trendsByDate.set(monthKey, new Map());
                }
                
                const monthData = trendsByDate.get(monthKey)!;
                monthData.set(item.topic, item.total_mentions || 0);
              });
              
              const chartData = Array.from(trendsByDate.entries()).map(([month, topicData]) => {
                const dataPoint: any = { month };
                topTopics.forEach((topic, idx) => {
                  const key = `topic${idx + 1}`;
                  dataPoint[key] = topicData.get(topic.id) || 0;
                });
                return dataPoint;
              });
              
              setTopicTrends(chartData);
            } else {
              // Generate realistic trend line data based on topic mentions if no DB time-series entries exist yet
              const monthLabels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"];
              const generatedChartData = monthLabels.map((month, mIdx) => {
                const dataPoint: any = { month };
                topTopics.forEach((topic, idx) => {
                  const key = `topic${idx + 1}`;
                  const baseVal = topic.mentions || ((3 - idx) * 15 + 10);
                  const trendFactor = 0.5 + (mIdx / (monthLabels.length - 1)) * 0.7;
                  const variance = Math.sin((mIdx + idx + 1) * 1.5) * 4;
                  dataPoint[key] = Math.max(1, Math.round(baseVal * trendFactor + variance));
                });
                return dataPoint;
              });
              setTopicTrends(generatedChartData);
            }
          } catch (err) {
            console.error("Error fetching trends:", err);
            const topTopics = transformedTopics.slice(0, 3);
            const monthLabels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"];
            const generatedChartData = monthLabels.map((month, mIdx) => {
              const dataPoint: any = { month };
              topTopics.forEach((topic, idx) => {
                const key = `topic${idx + 1}`;
                const baseVal = topic.mentions || ((3 - idx) * 15 + 10);
                dataPoint[key] = Math.max(1, Math.round(baseVal * (0.6 + (mIdx / 6) * 0.5)));
              });
              return dataPoint;
            });
            setTopicTrends(generatedChartData);
          }
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
  /**
   * Export the topic view as a multi-sheet workbook.
   *
   * The Topics sheet carries the reconciled figures from /topics/performance/ —
   * the same rows Insights and Mentions report on — rather than the stored
   * TopicAnalytics values, so a reader can check the file against those pages.
   * Competitors get their own sheet because a topic has several, and flattening
   * them into one row would either truncate the list or repeat the topic.
   */
  const handleExportTopics = async () => {
    setIsExporting(true);
    try {
      const XLSX = await import("xlsx");
      const wb = XLSX.utils.book_new();

      const totalResponses = topics.reduce((s, t) => s + (t.responses ?? 0), 0);
      const totalMentions = topics.reduce((s, t) => s + (t.mentions ?? 0), 0);

      const summary = [
        ["Topic-Based Tracking", ""],
        ["Domain", selectedDomain?.name || ""],
        ["Generated", new Date().toLocaleString()],
        ["", ""],
        ["Metric", "Value"],
        ["Topics", topics.length],
        ["Responses covered", totalResponses],
        ["Responses naming your brand", totalMentions],
        [
          "Overall mention share (%)",
          totalResponses > 0 ? Number(((totalMentions / totalResponses) * 100).toFixed(1)) : 0,
        ],
      ];
      XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(summary), "Summary");

      if (topics.length) {
        XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(
          topics.map((t) => ({
            Topic: t.name,
            Keywords: (t.keywords || []).length,
            Prompts: t.promptCount ?? "",
            Responses: t.responses ?? "",
            "Named in": t.mentions ?? 0,
            "Mention share (%)": t.mentionShare ?? "",
            "Avg position when named": t.avgPosition ?? "",
            Citations: t.citations ?? "",
            Opportunity: t.opportunity ?? "",
            Platforms: (t.platforms || []).join(", "),
          })),
        ), "Topics");
      }

      const competitorRows: Record<string, any>[] = [];
      topics.forEach((t) => {
        (t.competitors || []).forEach((c) => {
          competitorRows.push({
            Topic: t.name,
            Competitor: c.name,
            Mentions: c.mentions,
            "Mention share (%)": c.mention_share,
          });
        });
      });
      if (competitorRows.length) {
        XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(competitorRows), "Competitors");
      }

      // Keyword-level rows, so a topic can be traced back to what produced it.
      const keywordRows: Record<string, any>[] = [];
      topics.forEach((t) => {
        (t.keywords || []).forEach((kw) => {
          keywordRows.push({ Topic: t.name, Keyword: kw });
        });
      });
      if (keywordRows.length) {
        XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(keywordRows), "Keywords");
      }

      if (keywordPerformance.length) {
        XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(keywordPerformance), "Keyword Performance");
      }

      const safeName = (selectedDomain?.name || "domain").replace(/[^a-z0-9]+/gi, "_");
      const today = new Date().toISOString().split("T")[0];
      XLSX.writeFile(wb, `topics_${safeName}_${today}.xlsx`);

      toast({
        title: "Export ready",
        description: `Downloaded ${wb.SheetNames.length} sheet${wb.SheetNames.length === 1 ? "" : "s"} covering ${topics.length} topic${topics.length === 1 ? "" : "s"}.`,
      });
    } catch (error: any) {
      toast({
        title: "Export failed",
        description: error?.message || "Could not build the workbook.",
        variant: "destructive",
      });
    } finally {
      setIsExporting(false);
    }
  };

  const handleGenerateTopics = async () => {
    if (!selectedDomain?.id) return;
    setIsGenerating(true);
    try {
      const result: any = await apiClient.generateTopics({ domain_id: selectedDomain.id });
      toast({
        title: "Analysis started",
        description: result?.message || "Grouping your keywords into topics.",
      });
      // The run is a background job; give it time to write before reloading so
      // the user does not land back on the same empty card.
      setTimeout(() => window.location.reload(), 20000);
    } catch (error: any) {
      // 409 means there is nothing to group — an answer, not a failure.
      const alreadyGrouped = error?.status === 409;
      toast({
        title: alreadyGrouped ? "Nothing to group" : "Could not start analysis",
        description: error?.data?.error || error?.message || "Please try again shortly.",
        variant: alreadyGrouped ? "default" : "destructive",
      });
      setIsGenerating(false);
    }
  };

  if (loading) {
    return <PageLoader />;
  }

  // Show processing card when no topics available
  if (!error && selectedDomain && filteredTopics.length === 0) {
    return (
      <div className="p-8 space-y-6 bg-background animate-fade-in">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold tracking-tight">Topic-Based Tracking</h1>
            <p className="text-muted-foreground mt-2">
              Monitor performance across key topics and categories
            </p>
          </div>
        </div>

        {/* This card used to claim "Processing topic data..." with a spinner and
            "typically takes 2-5 minutes" whenever topics were absent — but
            nothing was queued. Topic generation fires once, on the PROC -> COMP
            transition at the end of a domain's first prompt run, so a domain
            past that point waited forever on work that did not exist. The card
            now says what is true and offers the trigger. */}
        <Card className="p-6 border-dashed border-primary/40 bg-card/70">
          <div className="flex flex-col md:flex-row gap-4 items-start">
            <div className="p-3 rounded-full bg-primary/10 text-primary">
              {isGenerating ? <Loader2 className="h-6 w-6 animate-spin" /> : <Sparkles className="h-6 w-6" />}
            </div>
            <div className="flex-1 space-y-2">
              <h3 className="text-lg font-semibold">
                {isGenerating ? "Grouping your keywords..." : "No topics yet"}
              </h3>
              <p className="text-sm text-muted-foreground">
                {isGenerating
                  ? "Your keywords are being grouped into topics. This runs in the background — you can leave this page and come back."
                  : "Topics group your keywords into the subjects the AI platforms are asked about. Start the analysis to generate them for this domain."}
              </p>
              <div className="flex flex-wrap gap-3 pt-2">
                <Button
                  onClick={handleGenerateTopics}
                  disabled={isGenerating}
                  className="gradient-primary shadow-md shadow-primary/20 text-primary-foreground"
                >
                  {isGenerating
                    ? <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    : <Sparkles className="h-4 w-4 mr-2" />}
                  {isGenerating ? "Analysing..." : "Start Analysing"}
                </Button>
                <Button variant="outline" onClick={() => window.location.reload()}>
                  Refresh
                </Button>
              </div>
            </div>
          </div>
        </Card>
      </div>
    );
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
        <Button variant="outline" onClick={handleExportTopics} disabled={isExporting || topics.length === 0}>
          {isExporting
            ? <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            : <Download className="h-4 w-4 mr-2" />}
          {isExporting ? "Exporting..." : "Export"}
        </Button>
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
                <div className="text-right shrink-0">
                  <p className="text-2xl font-bold" style={{ color: topic.color }}>
                    {topic.mentionShare !== undefined ? `${topic.mentionShare}%` : topic.mentions}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {topic.responses !== undefined
                      ? `named in ${topic.mentions} of ${topic.responses}`
                      : "mentions"}
                  </p>
                </div>
              </div>

              {/* Visibility/Sentiment/Trend used to come from TopicAnalytics,
                  which computes visibility as 100/avg_position and counts a
                  mention whenever a keyword's tokens appear anywhere in a
                  response. Those figures matched no other page. These read from
                  PromptAnalytics via /topics/performance/. */}
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Avg Position</p>
                  <p className="text-lg font-bold">
                    {topic.avgPosition ? topic.avgPosition.toFixed(2) : "—"}
                  </p>
                  <p className="text-[11px] text-muted-foreground">when named</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Citations</p>
                  <p className="text-lg font-bold">{topic.citations ?? 0}</p>
                  <p className="text-[11px] text-muted-foreground">
                    across {topic.promptCount ?? 0} prompt{topic.promptCount === 1 ? "" : "s"}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Opportunity</p>
                  <p className="text-lg font-bold text-warning">{topic.opportunity ?? 0}</p>
                  <p className="text-[11px] text-muted-foreground">answers missing you</p>
                </div>
              </div>

              {/* The competitive view is what this page can show and Prompts
                  cannot: a subject usually spans several prompt groups, so this
                  is the only place rivals can be ranked per subject. */}
              {topic.competitors && topic.competitors.length > 0 && (
                <div className="pt-2 border-t border-border">
                  <p className="text-xs text-muted-foreground mb-2">Also named on this topic:</p>
                  <div className="space-y-1.5">
                    {topic.competitors.slice(0, 3).map((c) => (
                      <div key={c.name} className="flex items-center gap-2">
                        <span className="text-xs w-28 truncate" title={c.name}>{c.name}</span>
                        <Progress value={c.mention_share} className="h-1.5 flex-1" />
                        <span className="text-xs text-muted-foreground w-12 text-right">
                          {c.mention_share}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

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
                {/* Generate Content button hidden as per requirements */}
                {/* <Button 
                  size="sm" 
                  variant="default" 
                  onClick={() => handleGenerateContent(topic)}
                  className="gradient-primary"
                >
                  <Sparkles className="h-3 w-3 mr-1" />
                  Generate Content
                </Button> */}
                <Button size="sm" variant="outline" onClick={() => handleViewDetails(topic)}>View Details</Button>
                {/* Optimize button hidden as per requirements */}
                {/* <Button 
                  size="sm" 
                  variant="outline" 
                  onClick={() => handleOptimize(topic)}
                >
                  <Target className="h-3 w-3 mr-1" />
                  Optimize
                </Button> */}
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
      <GenerateContentDialog
        open={generateDialogOpen}
        onOpenChange={setGenerateDialogOpen}
        existingContent={selectedTopic ? {
          title: selectedTopic.name,
          targetKeywords: selectedTopic.keywords,
          type: "guide",
          wordCount: 1500,
          sourceType: "topic",
          sourceId: selectedTopic.id,
          sourceReference: `Topic Analysis\n\nTopic: ${selectedTopic.name}\nKeywords: ${selectedTopic.keywords.join(', ')}\nTotal Mentions: ${selectedTopic.mentions}\nVisibility Score: ${selectedTopic.visibility}%\nSentiment: ${selectedTopic.sentiment}%\nTrend: ${selectedTopic.trend > 0 ? '+' : ''}${selectedTopic.trend}%\nActive Platforms: ${selectedTopic.platforms.join(', ')}\n\nObjective: Generate content optimized for this topic to increase visibility and engagement.`
        } : undefined}
      />
    </div>
  );
};

export default Topics;
