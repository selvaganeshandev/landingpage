import { useState, useEffect, useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
  Copy,
  Loader2,
  MessageSquare,
  GitBranch,
  Target,
  LinkIcon,
  AlertCircle,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/services/api";
import DOMPurify from 'dompurify';
import { PageLoader } from "@/components/PageLoader";
import { formatMessage, FORMATTED_MESSAGE_CLASSES } from "@/utils/textFormatter";
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
  const [isLoadingPrompts, setIsLoadingPrompts] = useState(false);
  const [selectedPlatform, setSelectedPlatform] = useState<string>("ChatGPT");
  const [selectedResponsePlatform, setSelectedResponsePlatform] = useState<string>("");
  const [platformResponses, setPlatformResponses] = useState<Record<string, string>>({});

  // Initial load - load everything once
  useEffect(() => {
    if (id) {
      loadPromptGroupDetail();
    }
  }, [id]);

  // When platform filter changes, only reload prompts
  useEffect(() => {
    if (id && promptGroup) {
      loadPrompts();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPlatform]);

  const loadPromptGroupDetail = async () => {
    try {
      setIsLoading(true);
      // Initial load without platform filter to get all data
      const response = await apiClient.getPromptGroupDetail(parseInt(id!));
      setPromptGroup(response.group);
      const promptsData = response.group?.prompts || [];
      setPrompts(promptsData);

      // Load full AI responses for each unique platform
      const platforms = new Set<string>();
      promptsData.forEach((p: any) => {
        if (p.platforms && Array.isArray(p.platforms)) {
          p.platforms.forEach((platform: string) => {
            if (platform) platforms.add(platform);
          });
        }
        if (p.platform) platforms.add(p.platform);
      });

      // Fetch full responses for each platform
      const responsesMap: Record<string, string> = {};

      // First, check if we have a primary response and which platform it belongs to
      const primaryPlatform = promptsData.find((p: any) => p.full_ai_response)?.platform ||
                             promptsData.find((p: any) => p.platforms?.[0])?.platforms?.[0];

      if (response.group?.primary_full_ai_response && primaryPlatform) {
        responsesMap[primaryPlatform] = response.group.primary_full_ai_response;
        console.log(`Using primary response for ${primaryPlatform}:`, {
          hasResponse: true,
          length: response.group.primary_full_ai_response.length
        });
      }

      // Fetch all platform responses in parallel for better performance
      const platformsToFetch = Array.from(platforms).filter(p => !responsesMap[p]);

      if (platformsToFetch.length > 0) {
        console.log(`Fetching responses for ${platformsToFetch.length} platforms in parallel:`, platformsToFetch);

        const platformPromises = platformsToFetch.map(async (platform) => {
          try {
            console.log(`Fetching response for ${platform}...`);
            const platformResponse = await apiClient.getPromptGroupDetail(parseInt(id!), { platform });

            // Try multiple sources for the response
            let platformFullResponse = null;

            if (platformResponse.group?.prompts?.[0]?.full_ai_response) {
              // First priority: prompt's own full_ai_response
              platformFullResponse = platformResponse.group.prompts[0].full_ai_response;
              console.log(`✓ Found response in prompt.full_ai_response for ${platform}`);
            } else if (platformResponse.group?.primary_full_ai_response) {
              // Second priority: group's primary_full_ai_response (when filtered by platform, this should be platform-specific)
              platformFullResponse = platformResponse.group.primary_full_ai_response;
              console.log(`✓ Found response in group.primary_full_ai_response for ${platform}`);
            }

            if (platformFullResponse) {
              console.log(`✓ Stored response for ${platform}, length: ${platformFullResponse.length}`);
              return { platform, response: platformFullResponse };
            } else {
              console.warn(`✗ No response found for ${platform}`);
              return { platform, response: null };
            }
          } catch (error) {
            console.error(`Failed to load response for ${platform}:`, error);
            return { platform, response: null };
          }
        });

        // Wait for all platforms to complete in parallel
        const results = await Promise.all(platformPromises);

        // Store all results in the map
        results.forEach(({ platform, response }) => {
          if (response) {
            responsesMap[platform] = response;
          }
        });
      }

      setPlatformResponses(responsesMap);

      // Debug: Log the full AI response availability
      console.log('Prompt Group Response:', {
        hasPrimaryFullAiResponse: !!response.group?.primary_full_ai_response,
        primaryFullAiResponseLength: response.group?.primary_full_ai_response?.length || 0,
        primaryFullAiResponsePreview: response.group?.primary_full_ai_response?.substring(0, 100) || 'N/A',
        totalPrompts: promptsData.length,
        platformResponses: Object.keys(responsesMap).map(platform => ({
          platform,
          hasResponse: !!responsesMap[platform],
          length: responsesMap[platform]?.length || 0
        }))
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

  const loadPrompts = async () => {
    try {
      setIsLoadingPrompts(true);
      // Load only prompts with platform filter
      const params = selectedPlatform ? { platform: selectedPlatform } : undefined;
      const response = await apiClient.getPromptGroupDetail(parseInt(id!), params);
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
      console.error('Error loading prompts:', error);
    } finally {
      setIsLoadingPrompts(false);
    }
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    toast({ title: "Copied to Clipboard", description: "Prompt has been copied." });
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

  // Get the full AI response for the selected platform
  const selectedFullAiResponse = useMemo(() => {
    if (!selectedResponsePlatform) {
      return promptGroup?.primary_full_ai_response || '';
    }

    // Find the prompt for the selected platform
    const platformPrompt = prompts.find((p: any) => {
      if (p.platforms && Array.isArray(p.platforms)) {
        return p.platforms.includes(selectedResponsePlatform);
      }
      return p.platform === selectedResponsePlatform;
    });

    return platformPrompt?.full_ai_response || promptGroup?.primary_full_ai_response || '';
  }, [selectedResponsePlatform, prompts, promptGroup]);

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

  // Set default response platform when data loads
  useEffect(() => {
    if (availablePlatforms.length > 0 && !selectedResponsePlatform) {
      const defaultPlatform = availablePlatforms.includes('ChatGPT')
        ? 'ChatGPT'
        : availablePlatforms[0];
      setSelectedResponsePlatform(defaultPlatform);
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
    return <PageLoader />;
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
    avgPosition: Math.round(t.avg_position || 0),
  }));

  const platformBreakdown = (promptGroup.platform_distribution || []).map((p: any) => ({
    platform: p.platform,
    mentions: p.count,
    avg_position: Math.round(p.avg_position || 0),
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
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-sm text-muted-foreground font-medium">Total Mentions</p>
              <h3 className="text-3xl font-bold mt-3">{promptGroup?.total_mentions || 0}</h3>
            </div>
            <div className="p-3 rounded-xl bg-primary/10">
              <MessageSquare className="h-6 w-6 text-primary" />
            </div>
          </div>
          {visibilityGrowth !== null ? (
            <div className="flex items-center gap-2 text-sm">
              <TrendingUp className="h-4 w-4 text-success" />
              <span className="text-success font-medium">+{visibilityGrowth}%</span>
              <span className="text-muted-foreground">vs last period</span>
            </div>
          ) : (
            <span className="text-sm text-muted-foreground">No historical data</span>
          )}
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-sm text-muted-foreground font-medium">Active Variants</p>
              <h3 className="text-3xl font-bold mt-3">{promptGroup?.active_variants || prompts?.length || 0}</h3>
            </div>
            <div className="p-3 rounded-xl bg-primary/10">
              <GitBranch className="h-6 w-6 text-primary" />
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Prompt variations tracked</span>
          </div>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-sm text-muted-foreground font-medium">Avg Position</p>
              <h3 className="text-3xl font-bold mt-3">{Math.round(promptGroup?.average_position || 0)}</h3>
            </div>
            <div className="p-3 rounded-xl bg-primary/10">
              <Target className="h-6 w-6 text-primary" />
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Across all platforms</span>
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
            {/* text-sm, not text-lg: this is a short value being displayed, not
                long-form reading content. At 18px it outweighed the "Main
                Prompt" heading above it. The AI response below stays at
                text-[15px] (FORMATTED_MESSAGE_CLASSES) because that IS prose. */}
            <p className="font-mono text-sm leading-relaxed break-words">{promptGroup?.primary_prompt || 'No main prompt available'}</p>
          </div>
        </div>
      </Card>

      {/* Full AI Response Section */}
      {availablePlatforms.length > 0 && (
        <Card className="p-6 shadow-elegant border-border/50 backdrop-blur-sm bg-card/80">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold font-inter">Full AI Response</h3>
              <Button variant="ghost" size="sm" onClick={() => handleCopy(selectedFullAiResponse || '')}>
                <Copy className="h-4 w-4 mr-1" />
                Copy
              </Button>
            </div>

            <Tabs value={selectedResponsePlatform} onValueChange={setSelectedResponsePlatform}>
              <TabsList className="bg-muted/50 p-1 border border-border mb-4">
                {availablePlatforms.map((platform) => (
                  <TabsTrigger
                    key={platform}
                    value={platform}
                    className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white"
                  >
                    {platform}
                  </TabsTrigger>
                ))}
              </TabsList>

              {availablePlatforms.map((platform) => {
                // Get the platform-specific response from our pre-loaded map
                const platformResponse = platformResponses[platform] || '';

                // Debug logging
                console.log(`Platform Tab: ${platform}`, {
                  hasResponse: !!platformResponse,
                  responseLength: platformResponse?.length || 0,
                  responsePreview: platformResponse?.substring(0, 100) || 'N/A'
                });

                return (
                  <TabsContent key={platform} value={platform} className="mt-0">
                    {platformResponse && platformResponse.trim() ? (
                      <div className="bg-gradient-to-br from-muted/30 to-muted/50 p-6 rounded-xl border border-border/50 backdrop-blur-sm">
                        <div
                          className={FORMATTED_MESSAGE_CLASSES}
                          dangerouslySetInnerHTML={{
                            __html: DOMPurify.sanitize(formatMessage(platformResponse), {
                              ALLOWED_TAGS: ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'a', 'ul', 'ol', 'li', 'strong', 'b', 'em', 'i', 'blockquote', 'code', 'pre', 'br', 'div', 'span', 'table', 'thead', 'tbody', 'tr', 'th', 'td'],
                              ALLOWED_ATTR: ['href', 'target', 'rel', 'class', 'id']
                            })
                          }}
                        />
                      </div>
                    ) : (
                      <div className="bg-gradient-to-br from-muted/30 to-muted/50 p-6 rounded-xl border border-border/50 backdrop-blur-sm text-center">
                        <p className="text-sm text-muted-foreground">No AI response available for {platform}</p>
                      </div>
                    )}
                  </TabsContent>
                );
              })}
            </Tabs>
          </div>
        </Card>
      )}

      {/* Missed Page URLs Section: URLs cited in the previous LLM run but
          absent from the latest one. Backend computes per (prompt, platform). */}
      {Array.isArray(promptGroup?.missed_urls) && promptGroup.missed_urls.length > 0 && (
        <Card className="p-6 shadow-elegant border-border/50 backdrop-blur-sm bg-card/80">
          <div className="space-y-4">
            <div className="flex items-start justify-between pb-4 border-b border-border/50">
              <div>
                <div className="flex items-center gap-2">
                  <AlertCircle className="h-5 w-5 text-amber-500" />
                  <h3 className="text-lg font-semibold font-inter">Missed Page URLs</h3>
                  <Badge variant="outline" className="ml-2">{promptGroup.missed_urls.length}</Badge>
                </div>
                <p className="text-sm text-muted-foreground mt-1">
                  Pages cited in the previous LLM response but missing from the latest one.
                </p>
              </div>
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>URL</TableHead>
                  <TableHead>Platform</TableHead>
                  <TableHead>Last Seen</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {promptGroup.missed_urls.map((m: any, idx: number) => (
                  <TableRow key={`${m.prompt_id}-${m.platform}-${idx}`}>
                    <TableCell>
                      <a
                        href={m.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 text-sm text-primary hover:underline break-all"
                      >
                        <LinkIcon className="h-3.5 w-3.5 shrink-0" />
                        <span className="break-all">{m.url}</span>
                      </a>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="capitalize">{m.platform}</Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {m.last_seen_at ? formatDate(m.last_seen_at) : '—'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </Card>
      )}

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
          {isLoadingPrompts ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <span className="ml-3 text-muted-foreground">Loading variants...</span>
            </div>
          ) : filteredVariants.length === 0 ? (
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
                              className={`text-sm flex-1 ${variant.latest_mention_id ? 'cursor-pointer hover:text-primary' : ''}`}
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
                  platformBreakdown.map((platform: any, idx: number) => {
                    const widthPercent = platform.mentions > 0 ? (platform.mentions / maxMentions) * 100 : 0;
                    return (
                      <div key={idx} className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium">{platform.platform}</span>
                          <span className="text-sm font-bold font-inter">{platform.mentions}</span>
                        </div>
                        <div className="h-2 bg-muted rounded-full overflow-hidden">
                          <div
                            className={`h-full transition-all duration-500 ${
                              idx === 0 ? 'bg-primary' :
                              idx === 1 ? 'bg-blue-500' :
                              idx === 2 ? 'bg-green-500' :
                              'bg-purple-500'
                            }`}
                            style={{ width: `${widthPercent}%` }}
                          />
                        </div>
                      </div>
                    );
                  })
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
