import { useState, useEffect, useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { 
  ArrowLeft, 
  TrendingUp,
  Share2,
  FileText,
  Copy,
  Loader2
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/services/api";
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
  Legend
} from "recharts";

const PromptDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [promptGroup, setPromptGroup] = useState<any>(null);
  const [prompts, setPrompts] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedPlatform, setSelectedPlatform] = useState<string>("ChatGPT");

  useEffect(() => {
    if (id) {
      loadPromptGroupDetail();
    }
  }, [id, selectedPlatform]);

  const loadPromptGroupDetail = async () => {
    try {
      setIsLoading(true);
      // Include platform filter in API call
      const params = selectedPlatform ? { platform: selectedPlatform } : undefined;
      const response = await apiClient.getPromptGroupDetail(parseInt(id!), params);
      setPromptGroup(response.group);
      const promptsData = response.group?.prompts || [];
      setPrompts(promptsData);
      // Debug: Log prompts and their platforms
      console.log('Loaded prompts:', promptsData.length, 'for platform:', selectedPlatform);
      promptsData.forEach((p: any, idx: number) => {
        console.log(`Prompt ${idx + 1}:`, {
          id: p.id,
          text: p.prompt_text?.substring(0, 50),
          platforms: p.platforms,
          platform: p.platform,
          mentions: p.mentions_count
        });
      });
    } catch (error: any) {
      const errorMessage = error.message || "Failed to load prompt group details";
      // Only show error for actual errors, not empty data
      const isNetworkError = errorMessage.includes('fetch') || errorMessage.includes('network') || errorMessage.includes('Network');
      const isServerError = errorMessage.includes('500') || errorMessage.includes('503') || errorMessage.includes('502');
      
      // Only show error toast for actual errors, not for empty data (404 is normal for empty data)
      if (isNetworkError || isServerError || (!errorMessage.includes('404') && !errorMessage.includes('Not Found'))) {
        toast({ title: "Error loading prompt group", description: errorMessage, variant: "destructive" });
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    toast({ title: "Copied to Clipboard", description: "Prompt has been copied." });
  };

  const handleShare = () => {
    toast({ title: "Share Link Generated", description: "Prompt group link copied to clipboard." });
  };

  const handleExport = () => {
    toast({ title: "Exporting Report", description: "Prompt group report is being generated..." });
  };

  // Calculate trend metrics - avoid showing 100% unless there's historical data
  const visibilityGrowth = useMemo(() => {
    const growth = promptGroup?.visibility_growth;
    if (growth === null || growth === undefined) return null;
    
    // Check if we have historical data (multiple data points in trends)
    const trends = promptGroup?.mention_trends || [];
    const hasHistoricalData = trends.length > 1;
    
    // Only show growth if we have historical data, otherwise show null
    if (!hasHistoricalData && growth === 100) {
      return null;
    }
    
    return growth;
  }, [promptGroup]);

  // Show all variants - filtering is done on the backend via API call
  const filteredVariants = useMemo(() => {
    // Always show all prompts returned from API (backend already filters by platform)
    return prompts || [];
  }, [prompts]);

  // Get available platforms from variants - only include platforms that actually have data
  const availablePlatforms = useMemo(() => {
    const platforms = new Set<string>();
    prompts.forEach((p: any) => {
      // Add all platforms from the platforms array
      if (p.platforms && Array.isArray(p.platforms)) {
        p.platforms.forEach((platform: string) => {
          if (platform) platforms.add(platform);
        });
      }
      // Fallback to single platform field
      if (p.platform) platforms.add(p.platform);
    });
    return Array.from(platforms).sort();
  }, [prompts]);

  // Set default platform to ChatGPT if available, otherwise use first available platform
  useEffect(() => {
    if (availablePlatforms.length > 0) {
      // If current selection is not in available platforms, or if it's the initial "ChatGPT" default
      // but ChatGPT is not available, switch to the first available platform
      if (!availablePlatforms.includes(selectedPlatform)) {
        const defaultPlatform = availablePlatforms.includes('ChatGPT') ? 'ChatGPT' : availablePlatforms[0];
        setSelectedPlatform(defaultPlatform);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [availablePlatforms]);

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "N/A";
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    } catch {
      return dateString;
    }
  };

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment?.toLowerCase()) {
      case 'positive':
        return 'bg-success text-success-foreground';
      case 'negative':
        return 'bg-destructive text-destructive-foreground';
      default:
        return 'bg-warning text-warning-foreground';
    }
  };

  const getDominantSentiment = (sentiment: any) => {
    if (!sentiment) return 'neutral';
    const { positive = 0, neutral = 0, negative = 0 } = sentiment;
    
    // Find the maximum value
    const maxValue = Math.max(positive, neutral, negative);
    
    // If all are 0, default to neutral
    if (maxValue === 0) {
      return 'neutral';
    }
    
    // Return the sentiment with the highest percentage
    // If positive is highest and greater than negative, return positive
    if (positive === maxValue && positive > negative) return 'positive';
    // If negative is highest and greater than positive, return negative
    if (negative === maxValue && negative > positive) return 'negative';
    // Otherwise return neutral (neutral is highest, or there's a tie)
    return 'neutral';
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  if (!promptGroup) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card className="p-8 text-center">
          <h2 className="text-2xl font-bold mb-4">Prompt Group Not Found</h2>
          <p className="text-gray-600 mb-4">The prompt group you're looking for doesn't exist.</p>
          <Button onClick={() => navigate("/prompts")}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Prompts
          </Button>
        </Card>
      </div>
    );
  }

  const trendsData = (promptGroup.mention_trends || []).map((t: any) => ({
    month: t.date,
    mentions: t.mentions,
    avgPosition: t.avg_position,
  }));

  const platformBreakdown = (promptGroup.platform_distribution || []).map((p: any) => ({
    platform: p.platform,
    mentions: p.count,
    avg_position: p.avg_position,
  }));

  // Calculate max mentions for bar width calculation
  const maxMentions = platformBreakdown.length > 0 
    ? Math.max(...platformBreakdown.map((p: any) => p.mentions || 0))
    : 1;

  return (
    <div className="p-8 space-y-6 bg-background animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-border/50">
        <div className="flex items-center gap-4">
          <Button
            variant="outline"
            size="icon"
            onClick={() => navigate(-1)}
            className="border-border/50"
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight font-inter">{promptGroup?.group_id || 'N/A'}</h1>
            <p className="text-muted-foreground mt-1">
              {promptGroup?.theme || promptGroup?.primary_prompt || 'No description available'}
            </p>
          </div>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={handleShare} className="border-border/50">
            <Share2 className="h-4 w-4 mr-2" />
            Share
          </Button>
          <Button variant="outline" onClick={handleExport} className="border-border/50">
            <FileText className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="p-6 shadow-elegant border-border/50 backdrop-blur-sm bg-card/80">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground uppercase tracking-wider">Total Mentions</p>
            <p className="text-4xl font-bold font-inter">{promptGroup?.total_mentions || 0}</p>
            {visibilityGrowth !== null ? (
              <div className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-success" />
                <span className="text-sm font-semibold text-success">+{visibilityGrowth}%</span>
                <span className="text-sm text-muted-foreground">vs last month</span>
              </div>
            ) : (
              <span className="text-sm text-muted-foreground">No historical data available</span>
            )}
          </div>
        </Card>

        <Card className="p-6 shadow-elegant border-border/50 backdrop-blur-sm bg-card/80">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground uppercase tracking-wider">Active Variants</p>
            <p className="text-4xl font-bold font-inter">{promptGroup?.active_variants || prompts?.length || 0}</p>
            <p className="text-sm text-muted-foreground">Prompt variations being tracked</p>
          </div>
        </Card>

        <Card className="p-6 shadow-elegant border-border/50 backdrop-blur-sm bg-card/80">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground uppercase tracking-wider">Avg Position</p>
            <p className="text-4xl font-bold font-inter">{promptGroup?.average_position || 0}</p>
            <p className="text-sm text-muted-foreground">Across all platforms</p>
          </div>
        </Card>
      </div>

      {/* Main Prompt Trend - Full Width */}
      <Card className="p-6 shadow-elegant border-border/50 backdrop-blur-sm bg-card/80">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold font-inter">Main Prompt</h3>
            <Button variant="ghost" size="sm" onClick={() => handleCopy(promptGroup?.primary_prompt || '')}>
              <Copy className="h-4 w-4 mr-1" />
              Copy
            </Button>
          </div>
          <div className="p-4 rounded-xl bg-gradient-to-br from-primary/5 to-secondary/5 border border-border/50">
            <p className="font-mono text-lg">{promptGroup?.primary_prompt || 'No main prompt available'}</p>
          </div>
        </div>
      </Card>

      {/* Mention Volume Trend - Full Width */}
      <Card className="p-6 shadow-elegant border-border/50 backdrop-blur-sm bg-card/80">
        <div className="space-y-6">
          <div className="pb-4 border-b border-border/50">
            <h3 className="text-lg font-semibold font-inter">Mention Volume Trends</h3>
            <p className="text-sm text-muted-foreground mt-1">
              Track how mention frequency changes over time
            </p>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={trendsData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="month" stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <YAxis yAxisId="left" stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <YAxis yAxisId="right" orientation="right" stroke="hsl(var(--muted-foreground))" fontSize={12} reversed />
              <Tooltip contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "var(--radius)" }} />
              <Legend />
              <Line yAxisId="left" type="monotone" dataKey="mentions" name="Mentions" stroke="hsl(var(--primary))" strokeWidth={3} dot={{ fill: "hsl(var(--primary))", r: 4 }} />
              <Line yAxisId="right" type="monotone" dataKey="avgPosition" name="Avg Position" stroke="hsl(var(--chart-2))" strokeWidth={2} dot={{ fill: "hsl(var(--chart-2))", r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* Prompt Variants Section - New */}
      <Card className="p-6 shadow-elegant border-border/50 backdrop-blur-sm bg-card/80">
        <div className="space-y-6">
          <div className="flex items-center justify-between pb-4 border-b border-border/50">
            <div>
              <h3 className="text-lg font-semibold font-inter">Prompt Variants</h3>
              <p className="text-sm text-muted-foreground mt-1">
                Detailed performance metrics for each prompt variant
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Select value={selectedPlatform} onValueChange={setSelectedPlatform}>
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="Select Platform" />
                </SelectTrigger>
                <SelectContent>
                  {availablePlatforms.map((platform) => (
                    <SelectItem key={platform} value={platform}>
                      {platform}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Variants Table */}
          {filteredVariants.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No variants found for the selected platform.
            </div>
          ) : (
            <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Variant</TableHead>
                    <TableHead className="text-center">Mentions</TableHead>
                    <TableHead className="text-center">Citations</TableHead>
                    <TableHead className="text-center">Position</TableHead>
                    <TableHead className="text-center">Sentiment</TableHead>
                    <TableHead>Tracked Date</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredVariants.map((variant: any) => {
                    const dominantSentiment = getDominantSentiment(variant.sentiment);
                    return (
                    <TableRow key={variant.id}>
                        <TableCell>
                          <div className="flex items-start gap-2">
                            <p 
                              className={`text-sm max-w-xs truncate flex-1 ${variant.latest_mention_id ? 'cursor-pointer hover:text-primary' : ''}`}
                              onClick={() => {
                                if (variant.latest_mention_id) {
                                  navigate(`/mentions/${variant.latest_mention_id}`);
                                }
                              }}
                            >
                              {variant.prompt_text}
                            </p>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleCopy(variant.prompt_text);
                              }}
                              className="opacity-70 hover:opacity-100"
                            >
                              <Copy className="h-3 w-3" />
                            </Button>
                          </div>
                        </TableCell>
                        <TableCell className="text-center font-medium">
                          {variant.mentions_count || 0}
                        </TableCell>
                        <TableCell className="text-center font-medium">
                          {variant.citations_count || 0}
                        </TableCell>
                        <TableCell className="text-center">
                          {variant.latest_position > 0 ? (
                            <Badge variant="outline" className="font-bold">
                              #{variant.latest_position.toFixed(1)}
                            </Badge>
                          ) : (
                            <span className="text-muted-foreground">N/A</span>
                          )}
                        </TableCell>
                        <TableCell className="text-center">
                          <Badge className={getSentimentColor(dominantSentiment)}>
                            {dominantSentiment}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {formatDate(variant.last_tracked_at)}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
          )}
        </div>
      </Card>

      {/* Platform Distribution - Sidebar */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-3">
          <Card className="p-6 shadow-elegant border-border/50 backdrop-blur-sm bg-card/80">
            <div className="space-y-4">
              <h3 className="text-lg font-semibold font-inter pb-4 border-b border-border/50">Platform Distribution</h3>
              <div className="space-y-3">
                {platformBreakdown.length === 0 ? (
                  <div className="text-center py-4 text-muted-foreground">
                    No platform data available
                  </div>
                ) : (
                  platformBreakdown.map((platform: any, idx: number) => (
                    <div key={idx} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">{platform.platform}</span>
                        <span className="text-sm font-bold font-inter">{platform.mentions}</span>
                      </div>
                      <div className="h-2 bg-muted rounded-full overflow-hidden">
                        <div className={`h-full bg-chart-${(idx % 4) + 1} transition-all duration-500`} style={{ width: `${platform.mentions > 0 ? (platform.mentions / maxMentions) * 100 : 0}%` }} />
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Quick Actions - Commented Out */}
      {/* <Card className="p-6 shadow-elegant border-border/50 backdrop-blur-sm bg-card/80">
        <div className="space-y-3">
          <h3 className="text-lg font-semibold font-inter pb-4 border-b border-border/50">Quick Actions</h3>
          <Button variant="outline" className="w-full justify-start border-border/50">
            <Sparkles className="h-4 w-4 mr-2" />
            Generate More Variants
          </Button>
          <Button variant="outline" className="w-full justify-start border-border/50">
            <TrendingUp className="h-4 w-4 mr-2" />
            View All Mentions
          </Button>
        </div>
      </Card> */}
    </div>
  );
};

export default PromptDetail;
