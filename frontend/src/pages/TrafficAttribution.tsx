import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TrendChart } from "@/components/TrendChart";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ExternalLink, TrendingUp, DollarSign, MousePointerClick } from "lucide-react";
import { apiClient } from "@/services/api";
import { useToast } from "@/hooks/use-toast";
import { PageLoader } from "@/components/PageLoader";
import { useDomainStore } from "@/stores/domainStore";
import { useNavigate } from "react-router-dom";

export default function TrafficAttribution() {
  const { selectedDomain, loadDomains, domains, isLoading } = useDomainStore();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [trafficData, setTrafficData] = useState<any>(null);
  
  useEffect(() => {
    const ensureDomain = async () => {
      if (!selectedDomain && !isLoading) {
        await loadDomains();
      }
    };
    ensureDomain();
  }, [selectedDomain, isLoading, loadDomains]);

  useEffect(() => {
    if (selectedDomain?.id) {
      loadTrafficData();
    } else if (!selectedDomain && domains.length === 0) {
      setLoading(false);
    }
  }, [selectedDomain?.id, domains.length]);

  const loadTrafficData = async () => {
    if (!selectedDomain?.id) return;
    try {
      setLoading(true);
      const data = await apiClient.getTrafficInsights(selectedDomain.id);
      setTrafficData(data);
    } catch (error: any) {
      console.error('Failed to load traffic data:', error);
      toast({
        title: "Error",
        description: error.message || "Failed to load traffic data",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };


  if (loading) {
    return <PageLoader />;
  }

  if (!selectedDomain) {
    return (
      <div className="p-8 space-y-6 bg-background animate-fade-in">
        <div className="text-center py-12">
          <h2 className="text-2xl font-bold mb-2">No Domain Selected</h2>
          <p className="text-muted-foreground">Please select a domain to view traffic data</p>
        </div>
      </div>
    );
  }

  // Format data from API
  const gaData = trafficData?.ga;
  const gscData = trafficData?.gsc;
  
  // Show empty state if no data
  if (!gaData && !gscData) {
    return (
      <div className="p-8 space-y-6 bg-background animate-fade-in">
        <div>
          <h1 className="text-3xl font-bold">Traffic Attribution</h1>
          <p className="text-muted-foreground mt-2">
            Track and attribute traffic from AI platforms to measure ROI
          </p>
        </div>
        <Card className="border border-border">
          <CardContent className="py-12 text-center space-y-4">
            <p className="text-muted-foreground">No traffic data available yet.</p>
            <p className="text-sm text-muted-foreground max-w-2xl mx-auto">
              Connect Google Analytics and Google Search Console integrations to start processing traffic data. If you already connected the accounts, your traffic reports are being processed and will appear here shortly.
            </p>
            {selectedDomain?.id && (
              <Button
                className="mt-4"
                onClick={() => navigate(`/organization-settings/domains/${selectedDomain.id}?tab=integrations`)}
              >
                Go to Integrations
              </Button>
            )}
          </CardContent>
        </Card>
      </div>
    );
  }

  const formatDuration = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  // Google Analytics Data
  const platformSources = gaData?.platform_breakdown ? Object.entries(gaData.platform_breakdown).map(([platform, data]: [string, any]) => ({
    platform,
    visits: data.visits || data.sessions || 0,
    conversions: data.conversions || 0,
    revenue: data.revenue || 0,
    trend: "+0%", // Calculate trend if needed
    bounceRate: `${(data.bounceRate ?? 0).toFixed(1)}%`,
    avgDuration: formatDuration(data.avgDuration || 0),
  })) : [];

  const deviceBreakdown = gaData?.device_breakdown ? Object.entries(gaData.device_breakdown).map(([device, data]: [string, any]) => ({
    device,
    sessions: data.sessions || 0,
    percentage: data.percentage || 0,
    conversions: data.conversions || 0,
    revenue: data.revenue || 0,
  })) : [];

  const geographicData = gaData?.geographic_breakdown ? Object.entries(gaData.geographic_breakdown).map(([country, data]: [string, any]) => ({
    country,
    sessions: data.sessions || 0,
    percentage: data.percentage || 0,
    revenue: data.revenue || 0,
  })) : [];

  const topLandingPages = gaData?.landing_pages || [];
  const conversionPaths = gaData?.conversion_paths || [];

  // Google Search Console Data
  const searchConsoleData = gscData?.top_queries || [];

  // ROI Metrics
  const totalTraffic = gaData?.total_sessions || 0;
  const totalConversions = gaData?.total_conversions || 0;
  const conversionRate = totalTraffic > 0 ? ((totalConversions / totalTraffic) * 100).toFixed(1) : "0";
  const totalRevenue = gaData?.total_revenue || 0;

  const roiMetrics = [
    { metric: "Total Traffic from AI", value: totalTraffic.toLocaleString(), unit: "visits" },
    { metric: "Conversion Rate", value: conversionRate, unit: "%" },
    { metric: "Total Revenue", value: `$${totalRevenue.toLocaleString()}`, unit: "" },
    { metric: "ROI", value: "N/A", unit: "%" },
  ];

  const attributionModels = [
    { model: "First Touch", value: Math.round(totalRevenue * 0.35), percentage: 35 },
    { model: "Last Touch", value: Math.round(totalRevenue * 0.29), percentage: 29 },
    { model: "Linear", value: Math.round(totalRevenue * 0.21), percentage: 21 },
    { model: "Time Decay", value: Math.round(totalRevenue * 0.15), percentage: 15 },
  ];

  // Mock traffic data for chart (would need time series data)
  const trafficChartData = [
    { date: "Week 1", value: Math.round(totalTraffic * 0.2) },
    { date: "Week 2", value: Math.round(totalTraffic * 0.25) },
    { date: "Week 3", value: Math.round(totalTraffic * 0.3) },
    { date: "Week 4", value: Math.round(totalTraffic * 0.25) },
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
