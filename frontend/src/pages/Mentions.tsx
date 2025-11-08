import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Search, Filter, ExternalLink, Copy, Loader2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { apiClient } from "@/services/api";
import { useDomainStore } from "@/stores/domainStore";
import { useAuth } from "@/contexts/AuthContext";
import { getActiveDomainIdNumber } from "@/utils/activeDomain";
import DOMPurify from 'dompurify';

interface Mention {
  id: number;
  rank: number;
  mention_text_short: string;
  mention_text_long: string;
  description: string;
  platform: string;
  sentiment: string;
  sentiment_score: number;
  total_mentions: number;
  total_citations: number;
  position: number;
  timestamp: string;
  time_ago: string;
  domain_name: string;
  domain_url: string;
  group_id: string;
  track_status: string;
  type: string;
  citations: Array<{
    id: number;
    text: string;
    source: string;
    url: string;
    description: string;
  }>;
  citations_count: number;
  views: number;
  shares: number;
  engagement_score: number;
  competitor_mentions: string[];
  key_topics: string[];
  // Additional fields from API response
  prompt_text?: string;
  full_ai_response?: string;
  context_summary?: string;
  created_at?: string;
  modified_at?: string;
}

const Mentions = () => {
  const navigate = useNavigate();
  const [selectedPlatform, setSelectedPlatform] = useState("all");
  const [selectedSentiment, setSelectedSentiment] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [mentions, setMentions] = useState<Mention[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [offset, setOffset] = useState(0);
  const limit = 20;
  const [isLoading, setIsLoading] = useState(true);
  const [availablePlatforms, setAvailablePlatforms] = useState<string[]>(["ChatGPT", "Google Gemini", "Perplexity"]);
  const [availableSentiments, setAvailableSentiments] = useState<string[]>(["Positive", "Negative", "Neutral"]);
  const { toast } = useToast();

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

  const { selectedDomain } = useDomainStore();
  const { user } = useAuth();

  // Load mentions data
  useEffect(() => {
    // reset pagination when filters/domain change
    setMentions([]);
    setOffset(0);
    setTotalCount(0);
    void loadMentions(0, true);
    void loadFilters();
  }, [selectedPlatform, selectedSentiment, searchQuery, selectedDomain?.id]);

  const loadMentions = async (startOffset: number = offset, replace: boolean = false) => {
    try {
      setIsLoading(true);
      // Use unified helper to get active domain ID (from localStorage, synced with server)
      const activeDomainId = selectedDomain?.id ?? getActiveDomainIdNumber(user);
      const response = await apiClient.getMentions({
        search: searchQuery || undefined,
        platform: selectedPlatform !== "all" ? selectedPlatform : undefined,
        sentiment: selectedSentiment !== "all" ? selectedSentiment : undefined,
        domain_id: activeDomainId || undefined,
        limit,
        offset: startOffset,
      });
      setTotalCount(response.total_count || 0);
      if (replace) {
        setMentions(response.mentions || []);
      } else {
        // Use functional update to ensure we're using the latest state
        setMentions(prevMentions => [...prevMentions, ...(response.mentions || [])]);
      }
    } catch (error: any) {
      console.error('Mentions: API error', error);
      toast({
        title: "Error loading mentions",
        description: error.message || "Failed to load mentions",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const canLoadMore = mentions.length < totalCount;
  const handleLoadMore = async () => {
    // Calculate next offset using current offset value
    const nextOffset = offset + limit;
    setOffset(nextOffset);
    // Load more with the new offset
    await loadMentions(nextOffset, false);
  };

  const loadFilters = async () => {
    try {
      // Use predefined platforms and sentiments instead of API
      // const response = await apiClient.getMentionFilters();
      // setAvailablePlatforms(response.platforms.map(p => p.name));
      // setAvailableSentiments(response.sentiments.map(s => s.name));
    } catch (error: any) {
      console.error("Failed to load filters:", error);
    }
  };

  // Filter mentions based on selected platform and sentiment
  const filteredMentions = mentions.filter((mention) => {
    const platformMatch = selectedPlatform === "all" || mention.platform === selectedPlatform;
    const sentimentMatch = selectedSentiment === "all" || mention.sentiment.toLowerCase() === selectedSentiment.toLowerCase();
    return platformMatch && sentimentMatch;
  });

  const handleExport = async () => {
    try {
      const response = await apiClient.exportMentions({
        platform: selectedPlatform !== "all" ? selectedPlatform : undefined,
        sentiment: selectedSentiment !== "all" ? selectedSentiment : undefined,
        format: "csv"
      });
      
      toast({
        title: "Export Complete",
        description: `Exported ${response.count} mentions successfully.`,
      });
    } catch (error: any) {
      toast({
        title: "Export Failed",
        description: error.message || "Failed to export mentions",
        variant: "destructive",
      });
    }
  };

  const handleMoreFilters = () => {
    toast({
      title: "Advanced Filters",
      description: "Opening advanced filter options...",
    });
  };

  const handleCopy = (snippet: string) => {
    navigator.clipboard.writeText(snippet);
    toast({
      title: "Copied to Clipboard",
      description: "Mention snippet has been copied.",
    });
  };

  const handleViewFull = (mentionId: number) => {
    navigate(`/mentions/${mentionId}`);
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

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between pb-4">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Real-Time Mention Tracking</h1>
          <p className="text-muted-foreground mt-2">
            Monitor brand mentions and citations across AI platforms
          </p>
        </div>
        <Button onClick={handleExport} className="gradient-primary shadow-md shadow-primary/20">
          Export Mentions
        </Button>
      </div>

      {/* Platform Tabs */}
      <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
        <Tabs value={selectedPlatform} onValueChange={setSelectedPlatform}>
          <div className="flex items-center justify-between mb-6">
            <TabsList className="bg-muted/50 p-1 border border-border">
              <TabsTrigger value="all" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">All Platforms</TabsTrigger>
              {availablePlatforms.map(platform => (
                <TabsTrigger 
                  key={platform} 
                  value={platform} 
                  className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white"
                >
                  {platform}
                </TabsTrigger>
              ))}
            </TabsList>
            <Button variant="outline" onClick={handleMoreFilters} className="border border-border">
              <Filter className="h-4 w-4 mr-2" />
              More Filters
            </Button>
          </div>

          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input 
                placeholder="Search mentions..." 
                className="pl-10" 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <Select value={selectedSentiment} onValueChange={setSelectedSentiment}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Sentiment" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Sentiments</SelectItem>
                {availableSentiments.map(sentiment => (
                  <SelectItem key={sentiment} value={sentiment}>
                    {sentiment}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </Tabs>
      </Card>

      <div className="grid gap-6">
        {isLoading ? (
          <Card className="p-12 text-center shadow-elegant border border-border backdrop-blur-sm bg-card/80">
            <div className="flex flex-col items-center gap-4">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              <div>
                <h3 className="text-lg font-semibold mb-2 font-outfit">Loading mentions...</h3>
                <p className="text-muted-foreground">
                  Please wait while we fetch your mentions
                </p>
              </div>
            </div>
          </Card>
        ) : filteredMentions.length === 0 ? (
          <Card className="p-12 text-center shadow-elegant border border-border backdrop-blur-sm bg-card/80">
            <div className="flex flex-col items-center gap-4">
              <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center">
                <Search className="h-8 w-8 text-muted-foreground" />
              </div>
              <div>
                <h3 className="text-lg font-semibold mb-2 font-outfit">No mentions found</h3>
                <p className="text-muted-foreground">
                  Try adjusting your filters to see more results
                </p>
              </div>
            </div>
          </Card>
        ) : (
          <>
          {filteredMentions.map((mention) => (
          <Card key={mention.id} className="p-6 transition-all duration-300 border border-border hover:border-primary backdrop-blur-sm bg-card/80">
            <div className="space-y-5">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-14 h-14 rounded-2xl gradient-primary shadow-glow flex items-center justify-center font-bold text-white text-lg font-outfit">
                    #{mention.position}
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant="outline" className="font-medium">{mention.platform}</Badge>
                      <Badge className={getSentimentColor(mention.sentiment)}>
                        {mention.sentiment}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground font-mono">
                      {mention.prompt_text || mention.mention_text_long || mention.mention_text_short || 'No prompt text available'}
                    </p>
                  </div>
                </div>
                <span className="text-xs text-muted-foreground">{mention.time_ago}</span>
              </div>

              <div className="bg-gradient-to-br from-muted/30 to-muted/50 rounded-xl p-5 border border-border backdrop-blur-sm">
                <div 
                  className="text-sm leading-relaxed prose prose-sm max-w-none [&_h1]:font-semibold [&_h1]:text-lg [&_h1]:mt-4 [&_h1]:mb-2 [&_h1]:text-foreground [&_h2]:font-semibold [&_h2]:text-base [&_h2]:mt-4 [&_h2]:mb-2 [&_h2]:text-foreground [&_h3]:font-semibold [&_h3]:text-sm [&_h3]:mt-4 [&_h3]:mb-2 [&_h3]:text-foreground [&_a]:text-primary [&_a]:underline [&_a]:hover:no-underline [&_strong]:font-semibold [&_strong]:text-foreground [&_b]:font-semibold [&_b]:text-foreground"
                  dangerouslySetInnerHTML={{
                    __html: DOMPurify.sanitize(processContent(mention.description || mention.context_summary || 'No description available'), {
                      ALLOWED_TAGS: ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'a', 'ul', 'ol', 'li', 'strong', 'b', 'em', 'i', 'blockquote', 'code', 'pre', 'br', 'div', 'span'],
                      ALLOWED_ATTR: ['href', 'target', 'rel', 'class', 'id']
                    })
                  }}
                />
              </div>

              <div className="space-y-3 pt-3 border-t">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground font-medium">Citations ({mention.citations_count}):</span>
                </div>
                {mention.citations && mention.citations.length > 0 && (
                  <div className="space-y-2">
                    {mention.citations.map((citation, idx) => (
                      <div key={idx} className="p-3 bg-muted/20 rounded-lg border border-border/30">
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium mb-1">"{citation.text}"</p>
                            <a 
                              href={citation.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-primary hover:underline flex items-center gap-1"
                            >
                              <ExternalLink className="h-3 w-3" />
                              {citation.source}
                            </a>
                            <p className="text-xs text-muted-foreground mt-1">{citation.description}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                <div className="flex gap-2 pt-2">
                  <Button variant="outline" size="sm" onClick={() => handleCopy(mention.description)} className="border border-border">
                    <Copy className="h-3 w-3 mr-1" />
                    Copy
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => handleViewFull(mention.id)} className="border border-border">
                    <ExternalLink className="h-3 w-3 mr-1" />
                    View Full Details
                  </Button>
                </div>
              </div>
            </div>
          </Card>
          ))}
          {canLoadMore && (
            <div className="flex justify-center">
              <Button variant="outline" onClick={handleLoadMore} disabled={isLoading} className="border border-border">
                {isLoading ? (<><Loader2 className="h-4 w-4 mr-2 animate-spin"/> Loading...</>) : 'Load More'}
              </Button>
            </div>
          )}
          </>
        )}
      </div>
    </div>
  );
};

export default Mentions;
