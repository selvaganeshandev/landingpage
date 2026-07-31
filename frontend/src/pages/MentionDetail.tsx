import { useState, useEffect } from "react";
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
  ArrowLeft, 
  Copy, 
  ExternalLink, 
  TrendingUp,
  MessageSquare,
  Clock,
  Target,
  Share2,
  FileText,
  Loader2
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/services/api";
import DOMPurify from 'dompurify';
import { formatMessage, FORMATTED_MESSAGE_CLASSES } from "@/utils/textFormatter";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from "recharts";

const MentionDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState("overview");
  const [mention, setMention] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [relatedMentions, setRelatedMentions] = useState<any[]>([]);
  const [positionTrend, setPositionTrend] = useState<any[]>([]);
  const [allAnalytics, setAllAnalytics] = useState<any[]>([]);
  const [availablePlatforms, setAvailablePlatforms] = useState<string[]>([]);
  const [selectedPlatform, setSelectedPlatform] = useState<string>("all");

  const formatDateTime = (iso?: string) => {
    if (!iso) return '';
    try {
      const d = new Date(iso);
      return d.toLocaleString();
    } catch {
      return iso;
    }
  };

  useEffect(() => {
    if (id) {
      loadMentionDetail();
      loadRelatedMentions();
    }
  }, [id]);

  useEffect(() => {
    if (mention?.prompt_id) {
      setSelectedPlatform("all"); // Reset platform filter when mention changes
      loadPositionTrend(mention.prompt_id, mention);
    }
  }, [mention?.prompt_id, mention]);

  const loadMentionDetail = async () => {
    try {
      setIsLoading(true);
      const response = await apiClient.getMentionDetail(parseInt(id!));
      setMention(response);
    } catch (error: any) {
      toast({
        title: "Error loading mention",
        description: error.message || "Failed to load mention details",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const loadRelatedMentions = async () => {
    try {
      const response = await apiClient.getRelatedMentions(parseInt(id!));
      setRelatedMentions(response.related_mentions);
    } catch (error: any) {
      console.error("Failed to load related mentions:", error);
    }
  };

  const loadPositionTrend = async (promptId: number, currentMention?: any) => {
    try {
      if (!promptId) {
        console.log("No promptId provided");
        return;
      }
      
      // Fetch prompt detail which includes analytics
      const response = await apiClient.getPromptDetail(promptId);
      const analytics = response.prompt?.analytics || [];
      
      console.log("Prompt detail response:", response);
      console.log("Analytics count:", analytics.length);
      console.log("Analytics data:", analytics);
      console.log("Current mention:", currentMention);
      
      // Include current mention in the data if it's not already there
      const currentMentionData = currentMention ? {
        id: currentMention.id,
        platform: currentMention.platform,
        is_mention: currentMention.is_mention !== false, // Default to true if not specified
        position: currentMention.position,
        created_at: currentMention.created_at,
      } : null;
      
      // Combine analytics with current mention if not already included
      let allMentionData = [...analytics];
      if (currentMentionData && !analytics.find((a: any) => a.id === currentMentionData.id)) {
        allMentionData.push(currentMentionData);
      }
      
      // Filter only mentions with position data (position exists and is a valid number)
      const mentionAnalytics = allMentionData.filter((analytic: any) => {
        const hasMention = analytic.is_mention !== false; // Treat undefined/null as true
        const position = Number(analytic.position);
        const hasPosition = !isNaN(position) && position > 0;
        return hasMention && hasPosition;
      });
      
      console.log("Filtered mention analytics:", mentionAnalytics);
      console.log("Mention analytics count:", mentionAnalytics.length);
      
      // Store all analytics for filtering
      setAllAnalytics(mentionAnalytics);
      
      // Extract unique platforms
      const platforms = Array.from(new Set(mentionAnalytics.map((a: any) => a.platform).filter(Boolean))).sort();
      setAvailablePlatforms(platforms);
      
      // Process analytics as-is (without grouping by date)
      const processedTrends = mentionAnalytics.map((analytic: any) => ({
        date: new Date(analytic.created_at).toISOString().split('T')[0],
        datetime: analytic.created_at,
        position: Number(analytic.position),
        platform: analytic.platform || 'Unknown',
        mentions: 1,
      })).sort((a, b) => new Date(a.datetime).getTime() - new Date(b.datetime).getTime());
      
      console.log("Processed trends:", processedTrends);
      setPositionTrend(processedTrends);
    } catch (error: any) {
      console.error("Failed to load position trend:", error);
      setPositionTrend([]);
      setAllAnalytics([]);
      setAvailablePlatforms([]);
    }
  };

  const handleCopy = () => {
    if (mention?.full_ai_response) {
      navigator.clipboard.writeText(mention.full_ai_response);
      toast({
        title: "Copied to Clipboard",
        description: "AI response has been copied.",
      });
    }
  };

  const handleShare = () => {
    if (navigator.share) {
      navigator.share({
        title: `Mention on ${mention?.platform}`,
        text: mention?.prompt_text,
        url: window.location.href,
      });
    } else {
      navigator.clipboard.writeText(window.location.href);
      toast({
        title: "Link Copied",
        description: "Share link has been copied to clipboard.",
      });
    }
  };

  const handleExport = async () => {
    if (!mention) return;
    
    try {
      toast({
        title: "Exporting...",
        description: "Preparing Excel file with mention data...",
      });

      await apiClient.exportMentionDetailExcel(mention.id);
      
      toast({
        title: "Export Successful",
        description: "Mention data exported to Excel file successfully.",
      });
    } catch (error: any) {
      toast({
        title: "Export Failed",
        description: error.message || "Failed to export mention",
        variant: "destructive",
      });
    }
  };

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case "positive":
        return "bg-success text-success-foreground";
      case "neutral":
        return "bg-warning text-warning-foreground";
      case "negative":
        return "bg-destructive text-destructive-foreground";
      default:
        return "bg-muted";
    }
  };

  // Process position trend data - filter by selected platform
  const trendData: Array<{ date: string; datetime: string; mentions: number; position: number; platform: string }> = 
    positionTrend.length > 0
      ? (selectedPlatform === "all" 
          ? positionTrend 
          : positionTrend.filter((item: any) => item.platform === selectedPlatform))
      : [];

  // Debug logging - must be before conditional returns (React hooks rules)
  useEffect(() => {
    console.log("Trend data:", trendData);
    console.log("Position trend:", positionTrend);
    console.log("Selected platform:", selectedPlatform);
    console.log("Available platforms:", availablePlatforms);
  }, [positionTrend.length, selectedPlatform, availablePlatforms.length]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  if (!mention) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card className="p-8 text-center">
          <h2 className="text-2xl font-bold mb-4">Mention Not Found</h2>
          <p className="text-gray-600 mb-4">The mention you're looking for doesn't exist.</p>
          <Button onClick={() => navigate("/mentions")}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Mentions
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6 bg-background animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="outline"
            size="icon"
            onClick={() => navigate(-1)}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight font-inter">Mention Details</h1>
            <p className="text-muted-foreground mt-1">
              In-depth analysis of this brand mention
            </p>
          </div>
        </div>
        <div className="flex gap-3">
          {/* <Button variant="outline" onClick={handleShare}>
            <Share2 className="h-4 w-4 mr-2" />
            Share
          </Button> */}
          <Button variant="outline" onClick={handleExport}>
            <FileText className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Overview Card */}
          <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
            <div className="space-y-6">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 rounded-2xl gradient-primary shadow-glow flex items-center justify-center font-bold text-white text-2xl font-inter">
                    #{mention.position}
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant="outline" className="font-medium text-base">{mention.platform}</Badge>
                      <Badge className={getSentimentColor(mention.sentiment) + " border"}>
                        {mention.sentiment}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      <Clock className="h-3 w-3 inline mr-1" />
                      {mention.time_ago} • {formatDateTime(mention.created_at)}
                    </p>
                  </div>
                </div>
                <Button variant="outline" size="sm" onClick={handleCopy} className="border border-border">
                  <Copy className="h-3 w-3 mr-1" />
                  Copy
                </Button>
              </div>

              <div className="space-y-3">
                <div>
                  <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                    User Prompt
                  </h3>
                  {/* Same treatment as Main Prompt on the prompt detail page:
                      font-mono at the app's base size, not text-lg. This is a
                      short value being displayed, not long-form reading, and at
                      18px it outweighed the heading above it. */}
                  <p className="font-mono text-sm leading-relaxed break-words bg-muted/30 p-4 rounded-xl border border-border">
                    {mention.prompt_text}
                  </p>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                    Full AI Response
                  </h3>
                  <div className="bg-gradient-to-br from-muted/30 to-muted/50 p-6 rounded-xl border border-border backdrop-blur-sm">
                    <div
                      className={FORMATTED_MESSAGE_CLASSES}
                      dangerouslySetInnerHTML={{
                        __html: DOMPurify.sanitize(formatMessage(mention.full_ai_response || ''), {
                          ALLOWED_TAGS: ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'a', 'ul', 'ol', 'li', 'strong', 'b', 'em', 'i', 'blockquote', 'code', 'pre', 'br', 'div', 'span'],
                          ALLOWED_ATTR: ['href', 'target', 'rel', 'class', 'id']
                        })
                      }}
                    />
                  </div>
                </div>
              </div>

              <div className="space-y-4 pt-4 border-t">
                <div>
                  <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                    Citations ({mention.citations?.length || 0})
                  </h3>
                  {mention.citations && mention.citations.length > 0 ? (
                    <div className="space-y-2">
                      {mention.citations.map((citation, idx) => (
                        <div key={idx} className="p-3 bg-muted/20 rounded-lg border border-border/30">
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-semibold text-foreground mb-2">"{citation.text}"</p>
                              <a 
                                href={citation.url || citation.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs text-primary hover:underline flex items-center gap-1 mb-1"
                              >
                                <ExternalLink className="h-3 w-3" />
                                {citation.source || citation.source_name || "Source"}
                              </a>
                              <p className="text-xs text-muted-foreground">{citation.description}</p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">No citations available</p>
                  )}
                </div>
                <div className="flex gap-2 pt-2">
                  <Button variant="outline" size="sm" onClick={handleCopy} className="border border-border">
                    <Copy className="h-3 w-3 mr-1" />
                    Copy
                  </Button>
                  {/* <Button variant="outline" size="sm" asChild className="border border-border">
                    <a href={mention.domain_url} target="_blank" rel="noopener noreferrer">
                      <ExternalLink className="h-3 w-3 mr-1" />
                      View Full Details
                    </a>
                  </Button> */}
                </div>
              </div>
            </div>
          </Card>

          {/* Tabs Section */}
          <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="bg-muted/50 p-1 border border-border mb-6">
                <TabsTrigger value="overview" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">
                  Overview
                </TabsTrigger>
                <TabsTrigger value="analysis" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">
                  Analysis
                </TabsTrigger>
                <TabsTrigger value="competitors" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">
                  Competitors
                </TabsTrigger>
              </TabsList>

              <TabsContent value="overview" className="space-y-4">
                <div>
                  <h3 className="text-lg font-semibold mb-4 font-inter">Key Topics Mentioned</h3>
                  <div className="flex flex-wrap gap-2">
                    {mention.key_topics && mention.key_topics.length > 0 ? (
                      mention.key_topics.map((topic, idx) => (
                        <Badge key={idx} variant="outline" className="text-sm px-3 py-1">
                          {topic}
                        </Badge>
                      ))
                    ) : (
                      <p className="text-sm text-muted-foreground">No key topics identified</p>
                    )}
                  </div>
                </div>

                <div className="pt-4">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold font-inter">Position Trend</h3>
                    {availablePlatforms.length > 0 && (
                      <Select value={selectedPlatform} onValueChange={setSelectedPlatform}>
                        <SelectTrigger className="w-[180px] border border-border">
                          <SelectValue placeholder="Select platform" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Platforms</SelectItem>
                          {availablePlatforms.map((platform) => (
                            <SelectItem key={platform} value={platform}>
                              {platform}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  </div>
                  {trendData.length === 0 ? (
                    <div className="h-[250px] flex flex-col items-center justify-center text-sm text-muted-foreground border border-border rounded-md">
                      <p>No trend data available</p>
                      {positionTrend.length > 0 && selectedPlatform !== "all" && (
                        <p className="text-xs mt-2">Try selecting "All Platforms"</p>
                      )}
                      {positionTrend.length === 0 && (
                        <p className="text-xs mt-2">No analytics data found for this prompt</p>
                      )}
                    </div>
                  ) : (
                    <ResponsiveContainer width="100%" height={250}>
                      <LineChart data={trendData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                        <XAxis 
                          dataKey="date" 
                          stroke="hsl(var(--muted-foreground))" 
                          fontSize={12}
                          angle={-45}
                          textAnchor="end"
                          height={60}
                        />
                        <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} reversed />
                        <Tooltip 
                          contentStyle={{
                            backgroundColor: "hsl(var(--card))",
                            border: "1px solid hsl(var(--border))",
                            borderRadius: "var(--radius)",
                          }}
                          labelFormatter={(label) => {
                            const item = trendData.find(d => d.date === label);
                            return item ? `${item.date} (${item.platform})` : label;
                          }}
                          formatter={(value: any) => [value, "Position"]}
                        />
                        <Line 
                          type="monotone" 
                          dataKey="position" 
                          name="Position"
                          stroke="hsl(var(--primary))" 
                          strokeWidth={3}
                          dot={{ fill: "hsl(var(--primary))", r: 4 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  )}
                </div>
              </TabsContent>

              <TabsContent value="analysis" className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 rounded-xl bg-gradient-to-br from-primary/5 to-secondary/5 border border-border">
                    <div className="flex items-center gap-2 mb-2">
                      <MessageSquare className="h-4 w-4 text-primary" />
                      <p className="text-sm text-muted-foreground">Citations</p>
                    </div>
                    <p className="text-3xl font-bold font-inter">{mention.total_citations}</p>
                  </div>
                  <div className="p-4 rounded-xl bg-gradient-to-br from-success/5 to-success/10 border border-border">
                    <div className="flex items-center gap-2 mb-2">
                      <TrendingUp className="h-4 w-4 text-success" />
                      <p className="text-sm text-muted-foreground">Position Rank</p>
                    </div>
                    <p className="text-3xl font-bold font-inter">#{mention.position}</p>
                  </div>
                </div>

                <div className="p-5 rounded-xl border border-border bg-muted/30">
                  <h4 className="font-semibold mb-3 font-inter">Sentiment Analysis</h4>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    This mention shows {mention.sentiment} sentiment with a score of {mention.sentiment_score}. 
                    {mention.sentiment === 'positive' && ' The response highlights positive aspects and benefits.'}
                    {mention.sentiment === 'negative' && ' The response contains critical or unfavorable content.'}
                    {mention.sentiment === 'neutral' && ' The response maintains a balanced, factual tone.'}
                  </p>
                </div>
              </TabsContent>

              <TabsContent value="competitors" className="space-y-4">
                <div>
                  <h3 className="text-lg font-semibold mb-3 font-inter">Competitors Mentioned</h3>
                  <div className="flex flex-wrap gap-2 mb-6">
                    {mention.competitor_mentions && mention.competitor_mentions.length > 0 ? (
                      mention.competitor_mentions.map((competitor, idx) => (
                        <Badge key={idx} variant="secondary" className="text-sm px-3 py-1">
                          {competitor}
                        </Badge>
                      ))
                    ) : (
                      <p className="text-sm text-muted-foreground">No competitors mentioned</p>
                    )}
                  </div>
                </div>

                <div className="pt-6 border-t border-border">
                  <h3 className="text-lg font-semibold mb-3 font-inter">Related Mentions</h3>
                  <p className="text-sm text-muted-foreground mb-3">Same prompt on different platforms</p>
                  <div className="space-y-3">
                    {relatedMentions && relatedMentions.length > 0 ? (
                      relatedMentions
                        .filter((related) => {
                          // Filter: same prompt (same_group) but different platform
                          const isSamePrompt = related.relation_type === 'same_group' || related.prompt_text === mention.prompt_text;
                          const isDifferentPlatform = related.platform !== mention.platform;
                          return isSamePrompt && isDifferentPlatform;
                        })
                        .map((related, idx) => (
                          <div key={idx} className="p-4 rounded-xl border border-border hover:shadow-md transition-all bg-card/50">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-xl gradient-primary shadow-md flex items-center justify-center font-bold text-white font-inter">
                                  #{related.position}
                                </div>
                                <div>
                                  <Badge variant="outline" className="mb-1">{related.platform}</Badge>
                                  <p className="text-sm text-muted-foreground font-mono">{related.prompt_text}</p>
                                  <p className="text-xs text-muted-foreground">{related.time_ago}</p>
                                </div>
                              </div>
                              <Button 
                                variant="ghost" 
                                size="sm"
                                onClick={() => navigate(`/mentions/${related.id}`)}
                              >
                                View
                              </Button>
                            </div>
                          </div>
                        ))
                    ) : (
                      <p className="text-sm text-muted-foreground">No related mentions found for this prompt on other platforms</p>
                    )}
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Engagement Stats */}
          <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
            {/* Was "Engagement Metrics", leading with Views and Shares. Those
                columns are 0 on all 11,328 analytics rows — nothing writes
                them, and an AI answer has no views or shares to write. They
                promised audience data that cannot exist for this medium.
                Replaced with what this answer genuinely records. */}
            <h3 className="text-lg font-semibold mb-4 font-inter">Answer Metrics</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-border">
                <span className="text-sm text-muted-foreground">Brand mentions</span>
                {/* No invented fallback. This used to substitute the related-
                    mention count, or a bare 1, whenever the real value was 0 —
                    turning "not mentioned" into "mentioned once". */}
                <span className="text-lg font-bold font-inter">{mention.total_mentions ?? 0}</span>
              </div>
              <div className="flex items-center justify-between pb-3 border-b border-border">
                <span className="text-sm text-muted-foreground">Position in answer</span>
                <span className="text-lg font-bold font-inter">
                  {mention.position && mention.position > 0 ? mention.position : '—'}
                </span>
              </div>
              {/* The actionable number on this screen. Being named without
                  being cited means the model describes you from other people's
                  pages — mention 14980 names IOB twice across 21 sources, none
                  of them IOB's. That points at a concrete next step in a way a
                  lexicon sentiment score never did. */}
              <div className="flex items-center justify-between pb-3 border-b border-border">
                <span className="text-sm text-muted-foreground">Your sources cited</span>
                <span className="text-lg font-bold font-inter">
                  <span className={(mention.own_domain_citations ?? 0) > 0 ? 'text-success' : 'text-muted-foreground'}>
                    {mention.own_domain_citations ?? 0}
                  </span>
                  <span className="text-sm font-normal text-muted-foreground"> of {mention.citations_count ?? 0}</span>
                </span>
              </div>
              <div className="flex items-center justify-between">
                {/* "Other brands", not "competitors": the extractor also returns
                    regulators and aggregators (Cibil, Rbi), so the stronger
                    claim would not be honest. */}
                <span className="text-sm text-muted-foreground">Other brands named</span>
                <span className="text-lg font-bold font-inter">
                  {(mention.other_brands_named ?? mention.competitor_mentions ?? []).length}
                </span>
              </div>
            </div>
          </Card>

          {/* Quick Actions - Commented out */}
          {/* <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
            <h3 className="text-lg font-semibold mb-4 font-inter">Quick Actions</h3>
            <div className="space-y-2">
              <Button variant="outline" className="w-full justify-start border border-border">
                <Target className="h-4 w-4 mr-2" />
                Add to Report
              </Button>
              <Button variant="outline" className="w-full justify-start border border-border">
                <MessageSquare className="h-4 w-4 mr-2" />
                View Context
              </Button>
              <Button variant="outline" className="w-full justify-start border border-border">
                <TrendingUp className="h-4 w-4 mr-2" />
                Compare Similar
              </Button>
            </div>
          </Card> */}
        </div>
      </div>
    </div>
  );
};

export default MentionDetail;
