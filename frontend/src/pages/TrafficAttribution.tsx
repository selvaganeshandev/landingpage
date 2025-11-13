import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TrendChart } from "@/components/TrendChart";
import { Badge } from "@/components/ui/badge";
import { ExternalLink, TrendingUp, DollarSign, MousePointerClick } from "lucide-react";

export default function TrafficAttribution() {
  // Google Analytics Mock Data
  const trafficData = [
    { date: "Week 1", value: 1240 },
    { date: "Week 2", value: 1580 },
    { date: "Week 3", value: 1890 },
    { date: "Week 4", value: 2340 },
  ];

  const platformSources = [
    { platform: "ChatGPT", visits: 1245, conversions: 89, revenue: 4450, trend: "+23%", bounceRate: "45%", avgDuration: "3:24" },
    { platform: "Perplexity", visits: 987, conversions: 124, revenue: 6200, trend: "+45%", bounceRate: "32%", avgDuration: "4:15" },
    { platform: "Claude", visits: 756, conversions: 67, revenue: 3350, trend: "+18%", bounceRate: "38%", avgDuration: "3:45" },
    { platform: "Gemini", visits: 634, conversions: 45, revenue: 2250, trend: "+12%", bounceRate: "41%", avgDuration: "2:58" },
    { platform: "Other AI", visits: 423, conversions: 28, revenue: 1400, trend: "+8%", bounceRate: "52%", avgDuration: "2:15" },
  ];

  // Google Search Console Mock Data
  const searchConsoleData = [
    { query: "best project management tool", impressions: 15420, clicks: 1245, ctr: "8.1%", position: 3.2 },
    { query: "ai-powered productivity software", impressions: 12890, clicks: 987, ctr: "7.7%", position: 4.1 },
    { query: "team collaboration platform", impressions: 10230, clicks: 756, ctr: "7.4%", position: 5.3 },
    { query: "workflow automation tool", impressions: 8940, clicks: 634, ctr: "7.1%", position: 6.2 },
    { query: "project tracking software", impressions: 7650, clicks: 423, ctr: "5.5%", position: 8.7 },
  ];

  const deviceBreakdown = [
    { device: "Desktop", sessions: 2234, percentage: 55, conversions: 245, revenue: 14200 },
    { device: "Mobile", sessions: 1456, percentage: 36, conversions: 98, revenue: 5800 },
    { device: "Tablet", sessions: 365, percentage: 9, conversions: 10, revenue: 650 },
  ];

  const topLandingPages = [
    { page: "/product", sessions: 1845, bounceRate: "32%", avgDuration: "4:23", conversions: 156 },
    { page: "/pricing", sessions: 1234, bounceRate: "28%", avgDuration: "3:45", conversions: 134 },
    { page: "/features", sessions: 987, bounceRate: "41%", avgDuration: "3:12", conversions: 89 },
    { page: "/blog/ai-productivity", sessions: 756, bounceRate: "38%", avgDuration: "5:34", conversions: 67 },
    { page: "/", sessions: 543, bounceRate: "45%", avgDuration: "2:15", conversions: 45 },
  ];

  const geographicData = [
    { country: "United States", sessions: 1845, percentage: 45.6, revenue: 12400 },
    { country: "United Kingdom", sessions: 756, percentage: 18.7, revenue: 4800 },
    { country: "Canada", sessions: 523, percentage: 12.9, revenue: 3200 },
    { country: "Germany", sessions: 456, percentage: 11.3, revenue: 2900 },
    { country: "Others", sessions: 465, percentage: 11.5, revenue: 2350 },
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
    <div className="p-8 space-y-6 bg-background animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold">Traffic Attribution</h1>
        <p className="text-muted-foreground mt-2">
          Track and attribute traffic from AI platforms to measure ROI
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        {roiMetrics.map((item, index) => (
          <Card key={index} className="transition-all duration-300 border border-border hover:border-primary">
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
        <TabsList className="bg-muted/50 p-1 border border-border">
          <TabsTrigger value="sources" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">Traffic Sources</TabsTrigger>
          <TabsTrigger value="search" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">Search Console</TabsTrigger>
          <TabsTrigger value="devices" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">Devices & Geo</TabsTrigger>
          <TabsTrigger value="pages" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">Landing Pages</TabsTrigger>
          <TabsTrigger value="conversions" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">Conversion Paths</TabsTrigger>
          <TabsTrigger value="attribution" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">Attribution Models</TabsTrigger>
        </TabsList>

        <TabsContent value="sources" className="space-y-6">
          <Card className="border border-border">
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
                    <div className="grid grid-cols-5 gap-4">
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
                      <div>
                        <div className="text-sm text-muted-foreground">Bounce Rate</div>
                        <div className="text-lg font-bold">{item.bounceRate}</div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">Avg Duration</div>
                        <div className="text-lg font-bold">{item.avgDuration}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="search" className="space-y-6">
          <Card className="border border-border">
            <CardHeader>
              <CardTitle>Google Search Console Data</CardTitle>
              <CardDescription>Top search queries driving traffic from AI platforms</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {searchConsoleData.map((item, index) => (
                  <div key={index} className="p-4 border rounded-lg">
                    <div className="font-medium mb-3">{item.query}</div>
                    <div className="grid grid-cols-4 gap-4">
                      <div>
                        <div className="text-sm text-muted-foreground">Impressions</div>
                        <div className="text-lg font-bold">{item.impressions.toLocaleString()}</div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">Clicks</div>
                        <div className="text-lg font-bold">{item.clicks.toLocaleString()}</div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">CTR</div>
                        <div className="text-lg font-bold">{item.ctr}</div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">Avg Position</div>
                        <div className="text-lg font-bold">{item.position}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="devices" className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            <Card className="border border-border">
              <CardHeader>
                <CardTitle>Device Breakdown</CardTitle>
                <CardDescription>Sessions and conversions by device type</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {deviceBreakdown.map((item, index) => (
                    <div key={index} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-medium">{item.device}</span>
                        <span className="text-sm font-medium">{item.sessions.toLocaleString()} sessions</span>
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
                      <div className="grid grid-cols-2 gap-2 mt-2 text-sm text-muted-foreground">
                        <div>Conversions: {item.conversions}</div>
                        <div>Revenue: ${item.revenue.toLocaleString()}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card className="border border-border">
              <CardHeader>
                <CardTitle>Geographic Distribution</CardTitle>
                <CardDescription>Sessions and revenue by country</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {geographicData.map((item, index) => (
                    <div key={index} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-medium">{item.country}</span>
                        <span className="text-sm font-medium">{item.sessions.toLocaleString()} sessions</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="flex-1 bg-secondary rounded-full h-2">
                          <div
                            className="bg-primary h-2 rounded-full transition-all"
                            style={{ width: `${item.percentage}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium min-w-[45px] text-right">
                          {item.percentage.toFixed(1)}%
                        </span>
                      </div>
                      <div className="text-sm text-muted-foreground mt-2">
                        Revenue: ${item.revenue.toLocaleString()}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="pages" className="space-y-6">
          <Card className="border border-border">
            <CardHeader>
              <CardTitle>Top Landing Pages</CardTitle>
              <CardDescription>Performance metrics for top landing pages from AI traffic</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {topLandingPages.map((item, index) => (
                  <div key={index} className="p-4 border rounded-lg">
                    <div className="font-medium mb-3">{item.page}</div>
                    <div className="grid grid-cols-4 gap-4">
                      <div>
                        <div className="text-sm text-muted-foreground">Sessions</div>
                        <div className="text-lg font-bold">{item.sessions.toLocaleString()}</div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">Bounce Rate</div>
                        <div className="text-lg font-bold">{item.bounceRate}</div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">Avg Duration</div>
                        <div className="text-lg font-bold">{item.avgDuration}</div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">Conversions</div>
                        <div className="text-lg font-bold">{item.conversions}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="conversions" className="space-y-6">
          <Card className="border border-border">
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
          <Card className="border border-border">
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
      </Tabs>
    </div>
  );
}
