import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Search, Filter, ExternalLink, Copy } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const mentions = [
  {
    id: 1,
    platform: "ChatGPT",
    prompt: "best vegan protein powder for athletes",
    position: 1,
    sentiment: "positive",
    snippet: "VegFit Pro stands out as a top choice for athletes seeking plant-based protein. Its clean ingredient profile and superior amino acid blend make it ideal for post-workout recovery.",
    timestamp: "2 hours ago",
    url: "#",
    sources: ["vegfitpro.com", "healthline.com"],
  },
  {
    id: 2,
    platform: "Claude",
    prompt: "top vegan protein supplement for sports",
    position: 2,
    sentiment: "positive",
    snippet: "Among the leading vegan protein options, VegFit Pro offers excellent value with its high protein content and natural ingredients, making it a favorite among endurance athletes.",
    timestamp: "5 hours ago",
    url: "#",
    sources: ["vegfitpro.com"],
  },
  {
    id: 3,
    platform: "Perplexity",
    prompt: "affordable plant-based protein",
    position: 1,
    sentiment: "neutral",
    snippet: "VegFit Pro provides a cost-effective solution for plant-based protein supplementation. While slightly more expensive than some alternatives, users report good results.",
    timestamp: "8 hours ago",
    url: "#",
    sources: ["vegfitpro.com", "amazon.com"],
  },
  {
    id: 4,
    platform: "Grok",
    prompt: "best protein powder for vegans",
    position: 1,
    sentiment: "positive",
    snippet: "VegFit Pro is highly recommended for vegans looking for quality protein. The formula is clean, effective, and backed by positive user reviews.",
    timestamp: "10 hours ago",
    url: "#",
    sources: ["vegfitpro.com", "reddit.com"],
  },
  {
    id: 5,
    platform: "Gemini",
    prompt: "plant protein comparison",
    position: 3,
    sentiment: "neutral",
    snippet: "When comparing plant-based proteins, VegFit Pro ranks well for quality but comes at a premium price point compared to competitors.",
    timestamp: "12 hours ago",
    url: "#",
    sources: ["vegfitpro.com", "consumerreports.com"],
  },
  {
    id: 6,
    platform: "ChatGPT",
    prompt: "organic vegan protein powder",
    position: 2,
    sentiment: "positive",
    snippet: "For those seeking organic options, VegFit Pro delivers with certified organic ingredients and exceptional taste that doesn't compromise on nutrition.",
    timestamp: "14 hours ago",
    url: "#",
    sources: ["vegfitpro.com", "organicfacts.com"],
  },
  {
    id: 7,
    platform: "Grok",
    prompt: "vegan protein powder side effects",
    position: 2,
    sentiment: "neutral",
    snippet: "Users report minimal digestive issues with VegFit Pro compared to other brands, though individual results may vary based on dietary sensitivities.",
    timestamp: "16 hours ago",
    url: "#",
    sources: ["vegfitpro.com"],
  },
];

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

const Mentions = () => {
  const navigate = useNavigate();
  const [selectedPlatform, setSelectedPlatform] = useState("all");
  const [selectedSentiment, setSelectedSentiment] = useState("all");
  const { toast } = useToast();

  // Filter mentions based on selected platform and sentiment
  const filteredMentions = mentions.filter((mention) => {
    const platformMatch = selectedPlatform === "all" || mention.platform.toLowerCase() === selectedPlatform.toLowerCase();
    const sentimentMatch = selectedSentiment === "all" || mention.sentiment === selectedSentiment;
    return platformMatch && sentimentMatch;
  });

  const handleExport = () => {
    toast({
      title: "Exporting Mentions",
      description: "Your mentions data is being exported...",
    });
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

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between pb-4 border-b border-border/50">
        <div>
          <h1 className="text-4xl font-bold tracking-tight font-outfit">Real-Time Mention Tracking</h1>
          <p className="text-muted-foreground mt-2">
            Monitor brand mentions and citations across AI platforms
          </p>
        </div>
        <Button onClick={handleExport} className="gradient-primary shadow-md shadow-primary/20">Export Mentions</Button>
      </div>

      {/* Platform Tabs */}
      <Card className="p-6 shadow-elegant border-border/50 backdrop-blur-sm bg-card/80">
        <Tabs value={selectedPlatform} onValueChange={setSelectedPlatform}>
          <div className="flex items-center justify-between mb-6">
            <TabsList className="bg-muted/50 p-1 border border-border/50">
              <TabsTrigger value="all" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md">All Platforms</TabsTrigger>
              <TabsTrigger value="grok" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md">Grok</TabsTrigger>
              <TabsTrigger value="claude" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md">Claude</TabsTrigger>
              <TabsTrigger value="chatgpt" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md">ChatGPT</TabsTrigger>
              <TabsTrigger value="perplexity" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md">Perplexity</TabsTrigger>
              <TabsTrigger value="gemini" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md">Google Gemini</TabsTrigger>
            </TabsList>
            <Button variant="outline" onClick={handleMoreFilters} className="border-border/50">
              <Filter className="h-4 w-4 mr-2" />
              More Filters
            </Button>
          </div>

          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input placeholder="Search mentions..." className="pl-10" />
            </div>
            <Select value={selectedSentiment} onValueChange={setSelectedSentiment}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Sentiment" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Sentiments</SelectItem>
                <SelectItem value="positive">Positive</SelectItem>
                <SelectItem value="neutral">Neutral</SelectItem>
                <SelectItem value="negative">Negative</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </Tabs>
      </Card>

      <div className="grid gap-6">
        {filteredMentions.length === 0 ? (
          <Card className="p-12 text-center shadow-elegant border-border/50 backdrop-blur-sm bg-card/80">
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
          filteredMentions.map((mention) => (
          <Card key={mention.id} className="p-6 hover:shadow-elegant transition-all duration-300 hover:scale-[1.01] border-border/50 backdrop-blur-sm bg-card/80">
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
                      {mention.prompt}
                    </p>
                  </div>
                </div>
                <span className="text-xs text-muted-foreground">{mention.timestamp}</span>
              </div>

              <div className="bg-gradient-to-br from-muted/30 to-muted/50 rounded-xl p-5 border border-border/50 backdrop-blur-sm">
                <p className="text-sm leading-relaxed">{mention.snippet}</p>
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-border/50">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground font-medium">Sources:</span>
                  {mention.sources.map((source, idx) => (
                    <Badge key={idx} variant="secondary" className="text-xs font-medium">
                      {source}
                    </Badge>
                  ))}
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => handleCopy(mention.snippet)} className="border-border/50">
                    <Copy className="h-3 w-3 mr-1" />
                    Copy
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => handleViewFull(mention.id)} className="border-border/50">
                    <ExternalLink className="h-3 w-3 mr-1" />
                    View Details
                  </Button>
                </div>
              </div>
            </div>
          </Card>
          ))
        )}
      </div>
    </div>
  );
};

export default Mentions;
