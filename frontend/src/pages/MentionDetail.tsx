import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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

  const formatDateTime = (iso?: string) => {
    if (!iso) return '';
    try {
      const d = new Date(iso);
      return d.toLocaleString();
    } catch {
      return iso;
    }
  };

  // Function to process content and convert markdown-like syntax to HTML
  const processContent = (content: string) => {
    if (!content) return '';
    
    let processedContent = content;
    
    // Replace ### with <h3> tags
    processedContent = processedContent.replace(/^###\s*(.+)$/gm, '<h3>$1</h3>');
    
    // Replace **text** with <strong>text</strong> for bold
    processedContent = processedContent.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Convert markdown links [text](url) to HTML links first
    processedContent = processedContent.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
    
    // Convert standalone URLs to clickable links
    const urlRegex = /(https?:\/\/[^\s<>"{}|\\^`\[\]]+)/g;
    processedContent = processedContent.replace(urlRegex, (match, url) => {
      // Check if this URL is already inside an HTML tag
      if (processedContent.includes(`href="${url}"`) || processedContent.includes(`href='${url}'`)) {
        return match; // Don't process if already in an href attribute
      }
      return `<a href="${url}" target="_blank" rel="noopener noreferrer">${url}</a>`;
    });
    
    // Also handle www. links
    const wwwRegex = /(www\.[^\s<>"{}|\\^`\[\]]+)/g;
    processedContent = processedContent.replace(wwwRegex, (match, url) => {
      // Check if this www. URL is already inside an HTML tag
      if (processedContent.includes(`href="https://${url}"`) || processedContent.includes(`href='https://${url}'`)) {
        return match; // Don't process if already in an href attribute
      }
      return `<a href="https://${url}" target="_blank" rel="noopener noreferrer">${url}</a>`;
    });
    
    // Convert line breaks to <br> tags
    processedContent = processedContent.replace(/\n/g, '<br>');
    
    return processedContent;
  };

  useEffect(() => {
    if (id) {
      loadMentionDetail();
      loadRelatedMentions();
    }
  }, [id]);

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

  const handleExport = () => {
    if (!mention) return;
    
    const exportData = {
      mention_id: mention.id,
      platform: mention.platform,
      sentiment: mention.sentiment,
      sentiment_score: mention.sentiment_score,
      prompt_text: mention.prompt_text,
      full_ai_response: mention.full_ai_response,
      total_mentions: mention.total_mentions,
      total_citations: mention.total_citations,
      position: mention.position,
      created_at: mention.created_at,
      domain_name: mention.domain_name,
      citations: mention.citations || [],
      key_topics: mention.key_topics || []
    };
    
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `mention-${mention.id}-${mention.platform.toLowerCase()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    toast({
      title: "Export Successful",
      description: "Mention data has been exported.",
    });
  };

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case "positive":
        return "bg-green-100 text-green-800";
      case "negative":
        return "bg-red-100 text-red-800";
      case "neutral":
        return "bg-gray-100 text-gray-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

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

  const trendData: Array<{ date: string; mentions: number; position: number }> = [];

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-4">
        <div className="flex items-center gap-4">
          <Button
            variant="outline"
            size="icon"
            onClick={() => navigate(-1)}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight font-outfit">Mention Details</h1>
            <p className="text-muted-foreground mt-1">
              In-depth analysis of this brand mention
            </p>
          </div>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={handleShare}>
            <Share2 className="h-4 w-4 mr-2" />
            Share
          </Button>
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
                  <div className="w-16 h-16 rounded-2xl gradient-primary shadow-glow flex items-center justify-center font-bold text-white text-2xl font-outfit">
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
                  <p className="text-lg font-mono bg-muted/30 p-4 rounded-xl border border-border">
                    {mention.prompt_text}
                  </p>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                    Full AI Response
                  </h3>
                  <div className="bg-gradient-to-br from-muted/30 to-muted/50 p-6 rounded-xl border border-border backdrop-blur-sm">
                    <div 
                      className="text-sm leading-relaxed prose prose-sm max-w-none [&_h1]:font-semibold [&_h1]:text-lg [&_h1]:mt-4 [&_h1]:mb-2 [&_h1]:text-foreground [&_h2]:font-semibold [&_h2]:text-base [&_h2]:mt-4 [&_h2]:mb-2 [&_h2]:text-foreground [&_h3]:font-semibold [&_h3]:text-sm [&_h3]:mt-4 [&_h3]:mb-2 [&_h3]:text-foreground [&_a]:text-primary [&_a]:underline [&_a]:hover:no-underline [&_strong]:font-semibold [&_strong]:text-foreground [&_b]:font-semibold [&_b]:text-foreground"
                      dangerouslySetInnerHTML={{
                        __html: DOMPurify.sanitize(processContent(mention.full_ai_response || ''), {
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
                    Citations & Sources ({mention.citations?.length || 0})
                  </h3>
                  {mention.citations && mention.citations.length > 0 ? (
                    <div className="space-y-3">
                      {mention.citations.map((citation, idx) => (
                        <div key={idx} className="p-4 bg-gradient-to-br from-muted/20 to-muted/30 rounded-lg border border-border/30">
                          <div className="flex items-start gap-3">
                            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                              <span className="text-sm font-bold text-primary">{idx + 1}</span>
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium mb-2 leading-relaxed">"{citation.text}"</p>
                              <div className="space-y-1">
                                {citation.url && (
                                  <a 
                                    href={citation.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-sm text-primary hover:underline flex items-center gap-1 font-medium"
                                  >
                                    <ExternalLink className="h-3 w-3" />
                                    {citation.source || citation.source_name || "Source"}
                                  </a>
                                )}
                                {citation.description && (
                                  <p className="text-xs text-muted-foreground">{citation.description}</p>
                                )}
                                <div className="flex items-center gap-2 mt-2">
                                  <Badge variant="outline" className="text-xs">
                                    {citation.reliability || "Verified"}
                                  </Badge>
                                  <span className="text-xs text-muted-foreground">{citation.referenced_at ? formatDateTime(citation.referenced_at) : "Recently referenced"}</span>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">No detailed citations available</p>
                  )}
                </div>
                <Button variant="outline" size="sm" asChild className="border border-border">
                  <a href={mention.url} target="_blank" rel="noopener noreferrer">
                    <ExternalLink className="h-3 w-3 mr-1" />
                    View Original AI Response
                  </a>
                </Button>
              </div>
            </div>
          </Card>

          {/* Tabs Section */}
          <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="bg-muted/50 p-1 border border-border mb-6">
                <TabsTrigger value="overview" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md">
                  Overview
                </TabsTrigger>
                <TabsTrigger value="analysis" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md">
                  Analysis
                </TabsTrigger>
                <TabsTrigger value="competitors" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md">
                  Competitors
                </TabsTrigger>
              </TabsList>

              <TabsContent value="overview" className="space-y-4">
                <div>
                  <h3 className="text-lg font-semibold mb-4 font-outfit">Key Topics Mentioned</h3>
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
                  <h3 className="text-lg font-semibold mb-4 font-outfit">Position Trend</h3>
                  {trendData.length === 0 ? (
                    <div className="h-[250px] flex items-center justify-center text-sm text-muted-foreground border border-border rounded-md">
                      No trend data available
                    </div>
                  ) : (
                    <ResponsiveContainer width="100%" height={250}>
                      <LineChart data={trendData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                        <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                        <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} reversed />
                        <Tooltip 
                          contentStyle={{
                            backgroundColor: "hsl(var(--card))",
                            border: "1px solid hsl(var(--border))",
                            borderRadius: "var(--radius)",
                          }}
                        />
                        <Line 
                          type="monotone" 
                          dataKey="position" 
                          name="Avg Position"
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
                    <p className="text-3xl font-bold font-outfit">{mention.total_citations}</p>
                  </div>
                  <div className="p-4 rounded-xl bg-gradient-to-br from-success/5 to-success/10 border border-border">
                    <div className="flex items-center gap-2 mb-2">
                      <TrendingUp className="h-4 w-4 text-success" />
                      <p className="text-sm text-muted-foreground">Position Rank</p>
                    </div>
                    <p className="text-3xl font-bold font-outfit">#{mention.position}</p>
                  </div>
                </div>

                <div className="p-5 rounded-xl border border-border bg-muted/30">
                  <h4 className="font-semibold mb-3 font-outfit">Sentiment Analysis</h4>
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
                  <h3 className="text-lg font-semibold mb-3 font-outfit">Competitors Mentioned</h3>
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

                <div>
                  <h3 className="text-lg font-semibold mb-3 font-outfit">Related Mentions</h3>
                  <div className="space-y-3">
                    {relatedMentions && relatedMentions.length > 0 ? (
                      relatedMentions.map((related, idx) => (
                        <div key={idx} className="p-4 rounded-xl border border-border hover:shadow-md transition-all bg-card/50">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <div className="w-10 h-10 rounded-xl gradient-primary shadow-md flex items-center justify-center font-bold text-white font-outfit">
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
                      <p className="text-sm text-muted-foreground">No related mentions found</p>
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
            <h3 className="text-lg font-semibold mb-4 font-outfit">Engagement Metrics</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-border">
                <span className="text-sm text-muted-foreground">Views</span>
                <span className="text-lg font-bold font-outfit">{mention.views ? mention.views.toLocaleString() : '0'}</span>
              </div>
              <div className="flex items-center justify-between pb-3 border-b border-border">
                <span className="text-sm text-muted-foreground">Shares</span>
                <span className="text-lg font-bold font-outfit">{mention.shares || '0'}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Citations</span>
                <span className="text-lg font-bold font-outfit">{mention.total_citations || '0'}</span>
              </div>
            </div>
          </Card>

          {/* Quick Actions */}
          <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
            <h3 className="text-lg font-semibold mb-4 font-outfit">Quick Actions</h3>
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
          </Card>
        </div>
      </div>
    </div>
  );
};

export default MentionDetail;
