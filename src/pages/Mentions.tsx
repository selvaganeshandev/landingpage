import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Search, Filter, ExternalLink, Copy } from "lucide-react";
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
  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Real-Time Mention Tracking</h1>
          <p className="text-muted-foreground mt-2">
            Monitor brand mentions and citations across AI platforms
          </p>
        </div>
        <Button>Export Mentions</Button>
      </div>

      <Card className="p-6">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input placeholder="Search mentions..." className="pl-10" />
          </div>
          <Select defaultValue="all">
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Platform" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Platforms</SelectItem>
              <SelectItem value="chatgpt">ChatGPT</SelectItem>
              <SelectItem value="claude">Claude</SelectItem>
              <SelectItem value="perplexity">Perplexity</SelectItem>
              <SelectItem value="gemini">Gemini</SelectItem>
            </SelectContent>
          </Select>
          <Select defaultValue="all">
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
          <Button variant="outline">
            <Filter className="h-4 w-4 mr-2" />
            More Filters
          </Button>
        </div>
      </Card>

      <div className="grid gap-6">
        {mentions.map((mention) => (
          <Card key={mention.id} className="p-6 hover:shadow-lg transition-shadow">
            <div className="space-y-4">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-primary to-secondary text-primary-foreground flex items-center justify-center font-bold">
                    #{mention.position}
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant="outline">{mention.platform}</Badge>
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

              <div className="bg-muted/50 rounded-lg p-4 border border-border">
                <p className="text-sm leading-relaxed">{mention.snippet}</p>
              </div>

              <div className="flex items-center justify-between pt-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">Sources:</span>
                  {mention.sources.map((source, idx) => (
                    <Badge key={idx} variant="secondary" className="text-xs">
                      {source}
                    </Badge>
                  ))}
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm">
                    <Copy className="h-3 w-3 mr-1" />
                    Copy
                  </Button>
                  <Button variant="outline" size="sm">
                    <ExternalLink className="h-3 w-3 mr-1" />
                    View Full
                  </Button>
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default Mentions;
