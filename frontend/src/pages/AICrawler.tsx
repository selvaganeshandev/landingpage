import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { useToast } from "@/hooks/use-toast";
import { Search, Play, Clock, CheckCircle2, XCircle, Loader2 } from "lucide-react";

export default function AICrawler() {
  const { toast } = useToast();
  const [isRunning, setIsRunning] = useState(false);
  const [query, setQuery] = useState("");

  const handleStartCrawl = () => {
    if (!query.trim()) {
      toast({
        title: "Query Required",
        description: "Please enter a search query to crawl",
        variant: "destructive",
      });
      return;
    }

    setIsRunning(true);
    toast({
      title: "Crawl Started",
      description: `Crawling AI models for: "${query}"`,
    });

    setTimeout(() => {
      setIsRunning(false);
      toast({
        title: "Crawl Complete",
        description: "Results are now available in the Recent Crawls tab",
      });
    }, 3000);
  };

  const recentCrawls = [
    {
      query: "best project management tools",
      status: "completed",
      models: 5,
      mentions: 23,
      timestamp: "2 hours ago",
    },
    {
      query: "AI automation platforms comparison",
      status: "completed",
      models: 4,
      mentions: 18,
      timestamp: "5 hours ago",
    },
    {
      query: "enterprise collaboration software",
      status: "running",
      models: 3,
      mentions: 12,
      timestamp: "Just now",
    },
  ];

  const discoveredMentions = [
    {
      model: "GPT-5",
      query: "best project management tools",
      mention: "Among the top project management platforms, ProductName stands out for its...",
      cited: true,
      position: 2,
    },
    {
      model: "Claude Opus",
      query: "best project management tools",
      mention: "For project management, several tools are worth considering including ProductName...",
      cited: true,
      position: 3,
    },
    {
      model: "Gemini Pro",
      query: "AI automation platforms comparison",
      mention: "ProductName offers comprehensive automation features that integrate well...",
      cited: false,
      position: 5,
    },
  ];

  return (
    <div className="p-8 space-y-6 bg-background">
      <div>
        <h1 className="text-3xl font-bold">AI Crawler</h1>
        <p className="text-muted-foreground mt-2">
          Crawl and analyze AI model responses across multiple platforms
        </p>
      </div>

      <Tabs defaultValue="new-crawl" className="space-y-6">
        <TabsList>
          <TabsTrigger value="new-crawl">New Crawl</TabsTrigger>
          <TabsTrigger value="recent">Recent Crawls</TabsTrigger>
          <TabsTrigger value="discoveries">Discoveries</TabsTrigger>
        </TabsList>

        <TabsContent value="new-crawl" className="space-y-6">
          <Card className="border border-border">
            <CardHeader>
              <CardTitle>Configure Crawl</CardTitle>
              <CardDescription>Set up a new crawl to track brand mentions across AI models</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="query">Search Query</Label>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="query"
                      placeholder="e.g., best project management tools"
                      className="pl-9"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                    />
                  </div>
                  <Button onClick={handleStartCrawl} disabled={isRunning}>
                    {isRunning ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Running
                      </>
                    ) : (
                      <>
                        <Play className="mr-2 h-4 w-4" />
                        Start Crawl
                      </>
                    )}
                  </Button>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>AI Models to Crawl</Label>
                  <div className="space-y-3 pt-2">
                    {["GPT-5", "Claude Opus", "Gemini Pro", "Perplexity", "ChatGPT"].map((model) => (
                      <div key={model} className="flex items-center space-x-2">
                        <Checkbox id={model} defaultChecked />
                        <label htmlFor={model} className="text-sm font-medium cursor-pointer">
                          {model}
                        </label>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="crawl-depth">Crawl Depth</Label>
                    <Select defaultValue="standard">
                      <SelectTrigger id="crawl-depth">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="quick">Quick (1-2 queries)</SelectItem>
                        <SelectItem value="standard">Standard (3-5 queries)</SelectItem>
                        <SelectItem value="deep">Deep (10+ queries)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="frequency">Crawl Frequency</Label>
                    <Select defaultValue="daily">
                      <SelectTrigger id="frequency">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="realtime">Real-time</SelectItem>
                        <SelectItem value="hourly">Hourly</SelectItem>
                        <SelectItem value="daily">Daily</SelectItem>
                        <SelectItem value="weekly">Weekly</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="recent" className="space-y-6">
          <Card className="border border-border">
            <CardHeader>
              <CardTitle>Recent Crawls</CardTitle>
              <CardDescription>View status and results of recent crawl operations</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {recentCrawls.map((crawl, index) => (
                  <div key={index} className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{crawl.query}</span>
                        {crawl.status === "completed" ? (
                          <CheckCircle2 className="h-4 w-4 text-green-500" />
                        ) : crawl.status === "running" ? (
                          <Loader2 className="h-4 w-4 animate-spin text-primary" />
                        ) : (
                          <XCircle className="h-4 w-4 text-red-500" />
                        )}
                      </div>
                      <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                        <span>{crawl.models} models</span>
                        <span>•</span>
                        <span>{crawl.mentions} mentions</span>
                        <span>•</span>
                        <div className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {crawl.timestamp}
                        </div>
                      </div>
                    </div>
                    <Button variant="outline" size="sm">
                      View Results
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="discoveries" className="space-y-6">
          <Card className="border border-border">
            <CardHeader>
              <CardTitle>Content Discoveries</CardTitle>
              <CardDescription>New mentions and citations found during crawls</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {discoveredMentions.map((mention, index) => (
                  <div key={index} className="p-4 border rounded-lg space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary">{mention.model}</Badge>
                        <span className="text-sm text-muted-foreground">Position {mention.position}</span>
                      </div>
                      {mention.cited ? (
                        <Badge variant="default">
                          <CheckCircle2 className="h-3 w-3 mr-1" />
                          Cited
                        </Badge>
                      ) : (
                        <Badge variant="outline">Not Cited</Badge>
                      )}
                    </div>
                    <div className="text-sm">
                      <div className="text-muted-foreground mb-1">Query: {mention.query}</div>
                      <div className="italic">"{mention.mention}"</div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
