import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TrendChart } from "@/components/TrendChart";
import { Badge } from "@/components/ui/badge";
import { ArrowUpRight, ArrowDownRight, TrendingUp, Search, Sparkles } from "lucide-react";

export default function PromptInsights() {
  const volumeData = [
    { date: "Jan 1", value: 245 },
    { date: "Jan 8", value: 289 },
    { date: "Jan 15", value: 412 },
    { date: "Jan 22", value: 378 },
    { date: "Jan 29", value: 523 },
    { date: "Feb 5", value: 601 },
  ];

  const emergingQueries = [
    { query: "AI agent orchestration best practices", volume: 1250, growth: 145, trend: "up" },
    { query: "GPT-5 vs Claude comparison", volume: 890, growth: 98, trend: "up" },
    { query: "automated testing for LLM apps", volume: 756, growth: 67, trend: "up" },
    { query: "RAG architecture patterns", volume: 645, growth: -12, trend: "down" },
    { query: "prompt engineering certification", volume: 534, growth: 234, trend: "up" },
  ];

  const searchIntents = [
    { intent: "Informational", percentage: 45, queries: 2340 },
    { intent: "Navigational", percentage: 28, queries: 1456 },
    { intent: "Transactional", percentage: 18, queries: 936 },
    { intent: "Commercial", percentage: 9, queries: 468 },
  ];

  const demandOpportunities = [
    { topic: "Multi-agent systems", score: 92, volume: 3450, competition: "low" },
    { topic: "LLM security practices", score: 88, volume: 2890, competition: "medium" },
    { topic: "Context window optimization", score: 85, volume: 2340, competition: "low" },
    { topic: "Agent monitoring tools", score: 79, volume: 1890, competition: "high" },
  ];

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Prompt Volume Insights</h1>
        <p className="text-muted-foreground mt-2">
          Understand trending queries and search volumes across AI platforms
        </p>
      </div>

      <Tabs defaultValue="trends" className="space-y-6">
        <TabsList>
          <TabsTrigger value="trends">Volume Trends</TabsTrigger>
          <TabsTrigger value="emerging">Emerging Queries</TabsTrigger>
          <TabsTrigger value="intent">Search Intent</TabsTrigger>
          <TabsTrigger value="opportunities">Demand Opportunities</TabsTrigger>
        </TabsList>

        <TabsContent value="trends" className="space-y-6">
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Prompt Volume</CardTitle>
                <Search className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">12,450</div>
                <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
                  <ArrowUpRight className="h-3 w-3 text-green-500" />
                  <span className="text-green-500">23.5%</span> from last month
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Avg. Daily Volume</CardTitle>
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">415</div>
                <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
                  <ArrowUpRight className="h-3 w-3 text-green-500" />
                  <span className="text-green-500">18.2%</span> from last month
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Emerging Queries</CardTitle>
                <Sparkles className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">47</div>
                <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
                  <ArrowUpRight className="h-3 w-3 text-green-500" />
                  <span className="text-green-500">31.0%</span> from last month
                </p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Prompt Volume Forecast</CardTitle>
              <CardDescription>30-day trend and prediction model</CardDescription>
            </CardHeader>
            <CardContent>
              <TrendChart data={volumeData} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="emerging" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Emerging Query Identification</CardTitle>
              <CardDescription>Queries with significant volume growth</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {emergingQueries.map((item, index) => (
                  <div key={index} className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex-1">
                      <div className="font-medium">{item.query}</div>
                      <div className="text-sm text-muted-foreground mt-1">
                        {item.volume.toLocaleString()} monthly searches
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      {item.trend === "up" ? (
                        <div className="flex items-center gap-1 text-green-500">
                          <ArrowUpRight className="h-4 w-4" />
                          <span className="font-medium">+{item.growth}%</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1 text-red-500">
                          <ArrowDownRight className="h-4 w-4" />
                          <span className="font-medium">{item.growth}%</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="intent" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Search Intent Analysis</CardTitle>
              <CardDescription>Classification of user query intentions</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {searchIntents.map((item, index) => (
                  <div key={index} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{item.intent}</span>
                      <span className="text-sm text-muted-foreground">
                        {item.queries.toLocaleString()} queries
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="flex-1 bg-secondary rounded-full h-2">
                        <div
                          className="bg-primary h-2 rounded-full transition-all"
                          style={{ width: `${item.percentage}%` }}
                        />
                      </div>
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

        <TabsContent value="opportunities" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Demand Opportunity Scoring</CardTitle>
              <CardDescription>High-value topics ranked by opportunity score</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {demandOpportunities.map((item, index) => (
                  <div key={index} className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex-1">
                      <div className="font-medium">{item.topic}</div>
                      <div className="text-sm text-muted-foreground mt-1">
                        {item.volume.toLocaleString()} monthly volume
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge
                        variant={
                          item.competition === "low"
                            ? "default"
                            : item.competition === "medium"
                            ? "secondary"
                            : "destructive"
                        }
                      >
                        {item.competition} competition
                      </Badge>
                      <div className="text-right">
                        <div className="text-2xl font-bold">{item.score}</div>
                        <div className="text-xs text-muted-foreground">Score</div>
                      </div>
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
