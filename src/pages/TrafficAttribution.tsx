import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TrendChart } from "@/components/TrendChart";
import { Badge } from "@/components/ui/badge";
import { ExternalLink, TrendingUp, DollarSign, MousePointerClick } from "lucide-react";

export default function TrafficAttribution() {
  const trafficData = [
    { date: "Week 1", value: 1240 },
    { date: "Week 2", value: 1580 },
    { date: "Week 3", value: 1890 },
    { date: "Week 4", value: 2340 },
  ];

  const platformSources = [
    { platform: "ChatGPT", visits: 1245, conversions: 89, revenue: 4450, trend: "+23%" },
    { platform: "Perplexity", visits: 987, conversions: 124, revenue: 6200, trend: "+45%" },
    { platform: "Claude", visits: 756, conversions: 67, revenue: 3350, trend: "+18%" },
    { platform: "Gemini", visits: 634, conversions: 45, revenue: 2250, trend: "+12%" },
    { platform: "Other AI", visits: 423, conversions: 28, revenue: 1400, trend: "+8%" },
  ];

  const conversionPaths = [
    {
      path: "AI Response → Landing Page → Sign Up",
      conversions: 156,
      value: 7800,
      avgTime: "2.3 min",
    },
    {
      path: "AI Response → Product Page → Purchase",
      conversions: 89,
      value: 8900,
      avgTime: "4.1 min",
    },
    {
      path: "AI Response → Blog → Newsletter",
      conversions: 134,
      value: 2680,
      avgTime: "3.5 min",
    },
    {
      path: "AI Response → Pricing → Contact Sales",
      conversions: 45,
      value: 13500,
      avgTime: "5.2 min",
    },
  ];

  const attributionModels = [
    { model: "First Touch", value: 15230, percentage: 35 },
    { model: "Last Touch", value: 12890, percentage: 29 },
    { model: "Linear", value: 8950, percentage: 21 },
    { model: "Time Decay", value: 6540, percentage: 15 },
  ];

  const roiMetrics = [
    { metric: "Total Traffic from AI", value: "4,045", unit: "visits" },
    { metric: "Conversion Rate", value: "8.7", unit: "%" },
    { metric: "Total Revenue", value: "$25,650", unit: "" },
    { metric: "ROI", value: "425", unit: "%" },
  ];

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Traffic Attribution</h1>
        <p className="text-muted-foreground mt-2">
          Track and attribute traffic from AI platforms to measure ROI
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        {roiMetrics.map((item, index) => (
          <Card key={index}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{item.metric}</CardTitle>
              {index === 0 && <MousePointerClick className="h-4 w-4 text-muted-foreground" />}
              {index === 1 && <TrendingUp className="h-4 w-4 text-muted-foreground" />}
              {index === 2 && <DollarSign className="h-4 w-4 text-muted-foreground" />}
              {index === 3 && <TrendingUp className="h-4 w-4 text-muted-foreground" />}
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {item.value}
                {item.unit && <span className="text-sm font-normal ml-1">{item.unit}</span>}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Tabs defaultValue="sources" className="space-y-6">
        <TabsList>
          <TabsTrigger value="sources">Traffic Sources</TabsTrigger>
          <TabsTrigger value="conversions">Conversion Paths</TabsTrigger>
          <TabsTrigger value="attribution">Attribution Models</TabsTrigger>
          <TabsTrigger value="trends">Trends</TabsTrigger>
        </TabsList>

        <TabsContent value="sources" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>AI Platform Referral Analysis</CardTitle>
              <CardDescription>Traffic, conversions, and revenue by AI platform</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {platformSources.map((item, index) => (
                  <div key={index} className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <ExternalLink className="h-4 w-4 text-primary" />
                        <span className="font-medium">{item.platform}</span>
                      </div>
                      <Badge variant="default">{item.trend}</Badge>
                    </div>
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <div className="text-sm text-muted-foreground">Visits</div>
                        <div className="text-lg font-bold">{item.visits.toLocaleString()}</div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">Conversions</div>
                        <div className="text-lg font-bold">{item.conversions}</div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">Revenue</div>
                        <div className="text-lg font-bold">${item.revenue.toLocaleString()}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="conversions" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Conversion Attribution Paths</CardTitle>
              <CardDescription>Most common user journeys from AI platforms</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {conversionPaths.map((item, index) => (
                  <div key={index} className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex-1">
                      <div className="font-medium mb-2">{item.path}</div>
                      <div className="flex gap-4 text-sm text-muted-foreground">
                        <span>{item.conversions} conversions</span>
                        <span>•</span>
                        <span>Avg. time: {item.avgTime}</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xl font-bold">${item.value.toLocaleString()}</div>
                      <div className="text-xs text-muted-foreground">Total Value</div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="attribution" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Attribution Model Comparison</CardTitle>
              <CardDescription>Revenue attribution across different models</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {attributionModels.map((item, index) => (
                  <div key={index} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{item.model}</span>
                      <span className="text-sm font-medium">${item.value.toLocaleString()}</span>
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

        <TabsContent value="trends" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Traffic Trend Analysis</CardTitle>
              <CardDescription>AI-driven traffic growth over time</CardDescription>
            </CardHeader>
            <CardContent>
              <TrendChart data={trafficData} />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
