import { useEffect, useState } from "react";
import { MetricCard } from "@/components/MetricCard";
import { VisibilityScore } from "@/components/VisibilityScore";
import { PlatformMentions } from "@/components/PlatformMentions";
import { CompetitorComparison } from "@/components/CompetitorComparison";
import { MentionTable } from "@/components/MentionTable";
import { TrendChart } from "@/components/TrendChart";
import { TimeFilter } from "@/components/TimeFilter";
import { Eye, TrendingUp, Target, Bell, Link2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { api } from "@/services/api";

const Dashboard = () => {
  const [timePeriod, setTimePeriod] = useState("30");
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState<any>(null);
  const domainId = localStorage.getItem('active_domain_id') || '';
  const { toast } = useToast();

  const handleExportReport = () => {
    toast({
      title: "Exporting Report",
      description: "Your dashboard report is being generated...",
    });
  };

  const handleRefreshData = () => {
    void fetchSummary();
  };

  async function fetchSummary() {
    if (!domainId) return;
    try {
      setLoading(true);
      const data = await api.getDashboardSummary({ domain_id: domainId, days: Number(timePeriod) });
      setSummary(data);
      toast({ title: "Data Loaded", description: "Dashboard updated." });
    } catch (e) {
      toast({ title: "Failed to load dashboard", description: String(e), variant: "destructive" });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void fetchSummary();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [domainId, timePeriod]);

  return (
    <div className="p-8 space-y-8">
      <div className="space-y-4">
        <div className="flex items-start justify-between pb-4">
          <div>
            <h1 className="text-4xl font-bold tracking-tight">Dashboard</h1>
            <p className="text-muted-foreground mt-2">
              Overview of your brand's AI search visibility performance
            </p>
          </div>
          <div className="flex items-center gap-3">
            <TimeFilter selected={timePeriod} onSelect={setTimePeriod} />
            <Button variant="outline" onClick={handleExportReport}>Export Report</Button>
            <Button onClick={handleRefreshData} className="gradient-primary shadow-md shadow-primary/20">
              Refresh Data
            </Button>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        <MetricCard
          title="Total Mentions"
          value={summary?.mentions?.total ?? "-"}
          change={15.2}
          trend="up"
          icon={<Eye className="h-6 w-6" />}
        />
        <MetricCard
          title="Total Citations"
          value={summary?.mentions?.top_mentions?.reduce((acc: number, m: any) => acc + (m.total_citations ?? 0), 0) ?? "-"}
          change={23.4}
          trend="up"
          icon={<Link2 className="h-6 w-6" />}
        />
        <MetricCard
          title="Visibility Score"
          value={Math.max(0, Math.min(100, Math.round(((summary?.mentions?.avg_sentiment ?? 0) + 1) * 50))).toString()}
          change={8.5}
          trend="up"
          icon={<Target className="h-6 w-6" />}
        />
        <MetricCard
          title="Avg Position"
          value={summary?.mentions?.avg_position ?? "-"}
          change={-12.3}
          trend="up"
          icon={<TrendingUp className="h-6 w-6" />}
        />
        <MetricCard
          title="Active Alerts"
          value={summary?.alerts?.active ?? "-"}
          icon={<Bell className="h-6 w-6" />}
        />
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 flex flex-col gap-6">
          <VisibilityScore
            brand={"Brand"}
            score={Math.max(0, Math.min(100, Math.round(((summary?.mentions?.avg_sentiment ?? 0) + 1) * 50)))}
            mentions={summary?.mentions?.total ?? 0}
            sentiment={{
              positive: Math.round(summary?.sentiment?.positive_percentage ?? 0),
              neutral: Math.round(summary?.sentiment?.neutral_percentage ?? 0),
              negative: Math.round(summary?.sentiment?.negative_percentage ?? 0),
            }}
          />
          <div className="flex-1">
            <TrendChart />
          </div>
        </div>
        <div className="flex flex-col gap-6">
          <PlatformMentions data={
            Array.isArray(summary?.mentions?.by_platform)
              ? summary.mentions.by_platform.map((p: any) => ({
                  platform: p.platform ?? p.name ?? p.Platform ?? 'Platform',
                  count: p.count ?? 0,
                  avg_position: p.avg_position ?? 0,
                }))
              : undefined
          } />
          <CompetitorComparison competitors={
            summary?.share_of_voice_latest?.competitors?.map((c: any) => ({
              name: c.name || `Competitor ${c.competitor_id}`,
              url: '',
              mentions: c.mention_count ?? 0,
              shareOfVoice: c.share_percentage ?? 0,
              trend: 0,
            }))
          } />
        </div>
      </div>

      {/* Mentions Table */}
      <MentionTable />
    </div>
  );
};

export default Dashboard;
