import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Bot, ExternalLink, TrendingUp, Target } from "lucide-react";

export default function AgentAnalytics() {
  const modelPerformance = [
    { model: "GPT-5", mentions: 145, citationRate: 78, avgPosition: 2.3, trend: "+12%" },
    { model: "Claude Opus", mentions: 132, citationRate: 82, avgPosition: 2.1, trend: "+8%" },
    { model: "Gemini Pro", mentions: 98, citationRate: 65, avgPosition: 3.2, trend: "+15%" },
    { model: "Perplexity", mentions: 87, citationRate: 91, avgPosition: 1.8, trend: "+5%" },
    { model: "ChatGPT", mentions: 76, citationRate: 58, avgPosition: 3.8, trend: "-3%" },
  ];

  const sourcePreferences = [
    { source: "Official Documentation", citations: 234, percentage: 32 },
    { source: "GitHub Repositories", citations: 189, percentage: 26 },
    { source: "Technical Blogs", citations: 156, percentage: 21 },
    { source: "Stack Overflow", citations: 98, percentage: 13 },
    { source: "Academic Papers", citations: 56, percentage: 8 },
  ];

  const behaviorPatterns = [
    {
      pattern: "Documentation-First Approach",
      models: ["Claude Opus", "GPT-5"],
      frequency: 85,
      description: "Prioritizes official documentation over community content",
    },
    {
      pattern: "Code Example Preference",
      models: ["Gemini Pro", "Perplexity"],
      frequency: 72,
      description: "Favors sources with practical code examples",
    },
    {
      pattern: "Recent Content Bias",
      models: ["GPT-5", "Gemini Pro"],
      frequency: 68,
      description: "Shows preference for content published within last 6 months",
    },
    {
      pattern: "Academic Citation Style",
      models: ["Claude Opus"],
      frequency: 45,
      description: "Includes more academic and research-focused sources",
    },
  ];

  const referralPathways = [
    { pathway: "Direct Citation → Website", conversions: 456, conversionRate: 12.3 },
    { pathway: "Summary → Learn More Link", conversions: 234, conversionRate: 8.7 },
    { pathway: "Code Example → Documentation", conversions: 189, conversionRate: 15.2 },
    { pathway: "Comparison → Product Page", conversions: 145, conversionRate: 9.4 },
  ];

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Agent Analytics</h1>
        <p className="text-muted-foreground mt-2">
          Deep intelligence on AI model behavior and source preferences
        </p>
      </div>

      <Tabs defaultValue="performance" className="space-y-6">
        <TabsList>
          <TabsTrigger value="performance">Model Performance</TabsTrigger>
          <TabsTrigger value="sources">Source Citations</TabsTrigger>
          <TabsTrigger value="behavior">Behavior Patterns</TabsTrigger>
          <TabsTrigger value="pathways">Referral Pathways</TabsTrigger>
        </TabsList>

        <TabsContent value="performance" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Model-Specific Performance Tracking</CardTitle>
              <CardDescription>Compare how different AI models reference your brand</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {modelPerformance.map((item, index) => (
                  <div key={index} className="p-4 border rounded-lg space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Bot className="h-5 w-5 text-primary" />
                        <div>
                          <div className="font-medium">{item.model}</div>
                          <div className="text-sm text-muted-foreground">
                            {item.mentions} mentions this month
                          </div>
                        </div>
                      </div>
                      <Badge variant={item.trend.startsWith("+") ? "default" : "secondary"}>
                        {item.trend}
                      </Badge>
                    </div>
                    <div className="grid grid-cols-3 gap-4 pt-2">
                      <div>
                        <div className="text-sm text-muted-foreground">Citation Rate</div>
                        <div className="text-lg font-bold">{item.citationRate}%</div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">Avg Position</div>
                        <div className="text-lg font-bold">{item.avgPosition}</div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">Trend</div>
                        <div className="text-lg font-bold">{item.trend}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="sources" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Source Citation Analysis</CardTitle>
              <CardDescription>Which sources AI models prefer when mentioning your brand</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {sourcePreferences.map((item, index) => (
                  <div key={index} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <ExternalLink className="h-4 w-4 text-muted-foreground" />
                        <span className="font-medium">{item.source}</span>
                      </div>
                      <span className="text-sm text-muted-foreground">
                        {item.citations} citations
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <Progress value={item.percentage} className="flex-1" />
                      <span className="text-sm font-medium min-w-[45px] text-right">
                        {item.percentage}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="behavior" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Agent Behavior Patterns</CardTitle>
              <CardDescription>Identified patterns in how AI models find and cite content</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {behaviorPatterns.map((item, index) => (
                  <div key={index} className="p-4 border rounded-lg space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="font-medium">{item.pattern}</div>
                      <div className="flex items-center gap-2">
                        <TrendingUp className="h-4 w-4 text-primary" />
                        <span className="font-bold">{item.frequency}%</span>
                      </div>
                    </div>
                    <p className="text-sm text-muted-foreground">{item.description}</p>
                    <div className="flex gap-2 flex-wrap">
                      {item.models.map((model, idx) => (
                        <Badge key={idx} variant="secondary">
                          {model}
                        </Badge>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="pathways" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Referral Pathway Optimization</CardTitle>
              <CardDescription>Track how users navigate from AI responses to your content</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {referralPathways.map((item, index) => (
                  <div key={index} className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <Target className="h-4 w-4 text-primary" />
                        <span className="font-medium">{item.pathway}</span>
                      </div>
                      <div className="text-sm text-muted-foreground mt-1">
                        {item.conversions} conversions this month
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-bold">{item.conversionRate}%</div>
                      <div className="text-xs text-muted-foreground">Conversion Rate</div>
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
