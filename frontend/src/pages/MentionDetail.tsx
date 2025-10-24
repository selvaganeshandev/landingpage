import { useState } from "react";
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
  FileText
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
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

  // Mock data - in real app, fetch based on id
  const mention = {
    id: id || "1",
    platform: "ChatGPT",
    prompt: "best vegan protein powder for athletes",
    position: 1,
    sentiment: "positive",
    fullResponse: "VegFit Pro stands out as a top choice for athletes seeking plant-based protein. Its clean ingredient profile and superior amino acid blend make it ideal for post-workout recovery.\n\nKey Features:\n• 25g of plant-based protein per serving\n• Complete amino acid profile from pea and rice protein\n• Added BCAAs for muscle recovery\n• No artificial sweeteners or additives\n• Third-party tested for purity\n\nMany professional athletes have switched to VegFit Pro for its effectiveness and digestibility. The natural vanilla flavor is well-received, and it mixes smoothly with both water and plant-based milk.\n\nCompared to other options like MyProtein or Naked Nutrition, VegFit Pro offers superior protein quality and better ingredient transparency. While it's priced slightly higher, the quality justifies the cost for serious athletes.",
    timestamp: "2 hours ago",
    date: "2024-01-15 14:30:00",
    url: "https://chat.openai.com/share/abc123",
    sources: ["vegfitpro.com", "healthline.com", "examine.com"],
    competitorsMentioned: ["MyProtein", "Naked Nutrition"],
    keyTopics: ["protein quality", "athlete nutrition", "plant-based", "recovery", "amino acids"],
    detailedCitations: [
      {
        text: "VegFit Pro stands out as a top choice for athletes",
        sourceUrl: "https://vegfitpro.com/products/protein-powder",
        sourceName: "VegFit Pro Official Site",
        context: "Product page citing key benefits and features",
        timestamp: "Referenced 2 hours ago",
        reliability: "high"
      },
      {
        text: "clean ingredient profile and superior amino acid blend",
        sourceUrl: "https://healthline.com/nutrition/vegan-protein-powder",
        sourceName: "Healthline - Vegan Protein Review",
        context: "Third-party nutritional analysis and comparison",
        timestamp: "Referenced 2 hours ago",
        reliability: "high"
      },
      {
        text: "Third-party tested for purity",
        sourceUrl: "https://examine.com/supplements/protein-powder/",
        sourceName: "Examine.com Research",
        context: "Independent testing and verification data",
        timestamp: "Referenced 2 hours ago",
        reliability: "high"
      }
    ],
    citations: 3,
    userEngagement: {
      views: 1247,
      shares: 89,
      citations: 12
    }
  };

  const trendData = [
    { date: "Jan 10", mentions: 4, position: 2.1 },
    { date: "Jan 11", mentions: 6, position: 1.8 },
    { date: "Jan 12", mentions: 5, position: 1.9 },
    { date: "Jan 13", mentions: 8, position: 1.6 },
    { date: "Jan 14", mentions: 7, position: 1.5 },
    { date: "Jan 15", mentions: 9, position: 1.4 },
  ];

  const relatedMentions = [
    { platform: "Claude", position: 2, prompt: "top vegan protein for sports" },
    { platform: "Perplexity", position: 1, prompt: "affordable plant-based protein" },
    { platform: "Gemini", position: 3, prompt: "best protein powder reviews" },
  ];

  const handleCopy = () => {
    navigator.clipboard.writeText(mention.fullResponse);
    toast({
      title: "Copied to Clipboard",
      description: "Full response has been copied.",
    });
  };

  const handleShare = () => {
    toast({
      title: "Share Link Generated",
      description: "Mention link copied to clipboard.",
    });
  };

  const handleExport = () => {
    toast({
      title: "Exporting Report",
      description: "Detailed mention report is being generated...",
    });
  };

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case "positive":
        return "bg-success/10 text-success border-success/20";
      case "neutral":
        return "bg-warning/10 text-warning border-warning/20";
      case "negative":
        return "bg-destructive/10 text-destructive border-destructive/20";
      default:
        return "bg-muted";
    }
  };

  return (
    <div className="p-8 space-y-6">
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
            <h1 className="text-3xl font-bold tracking-tight font-outfit">Mention Details</h1>
            <p className="text-muted-foreground mt-1">
              In-depth analysis of this brand mention
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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Overview Card */}
          <Card className="p-6 shadow-elegant border-border/50 backdrop-blur-sm bg-card/80">
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
                      {mention.timestamp} • {mention.date}
                    </p>
                  </div>
                </div>
                <Button variant="outline" size="sm" onClick={handleCopy} className="border-border/50">
                  <Copy className="h-3 w-3 mr-1" />
                  Copy
                </Button>
              </div>

              <div className="space-y-3">
                <div>
                  <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                    User Prompt
                  </h3>
                  <p className="text-lg font-mono bg-muted/30 p-4 rounded-xl border border-border/50">
                    {mention.prompt}
                  </p>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                    Full AI Response
                  </h3>
                  <div className="bg-gradient-to-br from-muted/30 to-muted/50 p-6 rounded-xl border border-border/50 backdrop-blur-sm">
                    <p className="text-sm leading-relaxed whitespace-pre-line">{mention.fullResponse}</p>
                  </div>
                </div>
              </div>

              <div className="space-y-4 pt-4 border-t border-border/50">
                <div>
                  <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                    Citations & Sources ({mention.detailedCitations?.length || 0})
                  </h3>
                  {mention.detailedCitations && mention.detailedCitations.length > 0 ? (
                    <div className="space-y-3">
                      {mention.detailedCitations.map((citation, idx) => (
                        <div key={idx} className="p-4 bg-gradient-to-br from-muted/20 to-muted/30 rounded-lg border border-border/30">
                          <div className="flex items-start gap-3">
                            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                              <span className="text-sm font-bold text-primary">{idx + 1}</span>
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium mb-2 leading-relaxed">"{citation.text}"</p>
                              <div className="space-y-1">
                                <a 
                                  href={citation.sourceUrl}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-sm text-primary hover:underline flex items-center gap-1 font-medium"
                                >
                                  <ExternalLink className="h-3 w-3" />
                                  {citation.sourceName}
                                </a>
                                <p className="text-xs text-muted-foreground">{citation.context}</p>
                                <div className="flex items-center gap-2 mt-2">
                                  <Badge variant="outline" className="text-xs">
                                    {citation.reliability === "high" ? "High Reliability" : "Verified"}
                                  </Badge>
                                  <span className="text-xs text-muted-foreground">{citation.timestamp}</span>
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
                <Button variant="outline" size="sm" asChild className="border-border/50">
                  <a href={mention.url} target="_blank" rel="noopener noreferrer">
                    <ExternalLink className="h-3 w-3 mr-1" />
                    View Original AI Response
                  </a>
                </Button>
              </div>
            </div>
          </Card>

          {/* Tabs Section */}
          <Card className="p-6 shadow-elegant border-border/50 backdrop-blur-sm bg-card/80">
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="bg-muted/50 p-1 border border-border/50 mb-6">
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
                    {mention.keyTopics.map((topic, idx) => (
                      <Badge key={idx} variant="outline" className="text-sm px-3 py-1">
                        {topic}
                      </Badge>
                    ))}
                  </div>
                </div>

                <div className="pt-4">
                  <h3 className="text-lg font-semibold mb-4 font-outfit">Position Trend</h3>
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
                </div>
              </TabsContent>

              <TabsContent value="analysis" className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 rounded-xl bg-gradient-to-br from-primary/5 to-secondary/5 border border-border/50">
                    <div className="flex items-center gap-2 mb-2">
                      <MessageSquare className="h-4 w-4 text-primary" />
                      <p className="text-sm text-muted-foreground">Citations</p>
                    </div>
                    <p className="text-3xl font-bold font-outfit">{mention.citations}</p>
                  </div>
                  <div className="p-4 rounded-xl bg-gradient-to-br from-success/5 to-success/10 border border-border/50">
                    <div className="flex items-center gap-2 mb-2">
                      <TrendingUp className="h-4 w-4 text-success" />
                      <p className="text-sm text-muted-foreground">Position Rank</p>
                    </div>
                    <p className="text-3xl font-bold font-outfit">#{mention.position}</p>
                  </div>
                </div>

                <div className="p-5 rounded-xl border border-border/50 bg-muted/30">
                  <h4 className="font-semibold mb-3 font-outfit">Sentiment Analysis</h4>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    This mention shows strong positive sentiment towards VegFit Pro, highlighting key differentiators like ingredient quality, amino acid profile, and third-party testing. The response positions the brand as a premium option worth the investment.
                  </p>
                </div>
              </TabsContent>

              <TabsContent value="competitors" className="space-y-4">
                <div>
                  <h3 className="text-lg font-semibold mb-3 font-outfit">Competitors Mentioned</h3>
                  <div className="flex flex-wrap gap-2 mb-6">
                    {mention.competitorsMentioned.map((competitor, idx) => (
                      <Badge key={idx} variant="secondary" className="text-sm px-3 py-1">
                        {competitor}
                      </Badge>
                    ))}
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-semibold mb-3 font-outfit">Related Mentions</h3>
                  <div className="space-y-3">
                    {relatedMentions.map((related, idx) => (
                      <div key={idx} className="p-4 rounded-xl border border-border/50 hover:shadow-md transition-all bg-card/50">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-xl gradient-primary shadow-md flex items-center justify-center font-bold text-white font-outfit">
                              #{related.position}
                            </div>
                            <div>
                              <Badge variant="outline" className="mb-1">{related.platform}</Badge>
                              <p className="text-sm text-muted-foreground font-mono">{related.prompt}</p>
                            </div>
                          </div>
                          <Button variant="ghost" size="sm">View</Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Engagement Stats */}
          <Card className="p-6 shadow-elegant border-border/50 backdrop-blur-sm bg-card/80">
            <h3 className="text-lg font-semibold mb-4 font-outfit">Engagement Metrics</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-border/50">
                <span className="text-sm text-muted-foreground">Views</span>
                <span className="text-lg font-bold font-outfit">{mention.userEngagement.views.toLocaleString()}</span>
              </div>
              <div className="flex items-center justify-between pb-3 border-b border-border/50">
                <span className="text-sm text-muted-foreground">Shares</span>
                <span className="text-lg font-bold font-outfit">{mention.userEngagement.shares}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Citations</span>
                <span className="text-lg font-bold font-outfit">{mention.userEngagement.citations}</span>
              </div>
            </div>
          </Card>

          {/* Quick Actions */}
          <Card className="p-6 shadow-elegant border-border/50 backdrop-blur-sm bg-card/80">
            <h3 className="text-lg font-semibold mb-4 font-outfit">Quick Actions</h3>
            <div className="space-y-2">
              <Button variant="outline" className="w-full justify-start border-border/50">
                <Target className="h-4 w-4 mr-2" />
                Add to Report
              </Button>
              <Button variant="outline" className="w-full justify-start border-border/50">
                <MessageSquare className="h-4 w-4 mr-2" />
                View Context
              </Button>
              <Button variant="outline" className="w-full justify-start border-border/50">
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
