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
import { useAuth } from "@/contexts/AuthContext";
import { loadActiveDomain, loadActiveDomainFromServer } from "@/utils/activeDomain";
import { useDomainStore } from "@/stores/domainStore";

const Dashboard = () => {
  const { user } = useAuth();
  const { selectedDomain } = useDomainStore();
  const [timePeriod, setTimePeriod] = useState("30");
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState<any>(null);
  const [domainId, setDomainId] = useState<string>("");
  const { toast } = useToast();
  
  // Get domain name for display
  const domainNameRaw = selectedDomain?.name || "Domain name";
  const domainName = domainNameRaw
    ? domainNameRaw.charAt(0).toUpperCase() + domainNameRaw.slice(1)
    : "Domain name";

  // Sync domain_id from selectedDomain (Zustand store) or server when domain changes
  useEffect(() => {
    if (!user) return;
    
    const syncDomain = async () => {
      // Priority 1: Use selectedDomain from Zustand store (most up-to-date when user changes domain)
      if (selectedDomain?.id) {
        const newDomainId = String(selectedDomain.id);
        if (newDomainId !== domainId) {
          setDomainId(newDomainId);
          return;
        }
      }
      
      // Priority 2: Fallback to server (primary source of truth on initial load)
      const serverActiveDomain = await loadActiveDomainFromServer(user.id);
      const serverDomainId = serverActiveDomain || '';
      
      if (serverDomainId !== domainId) {
        setDomainId(serverDomainId);
      }
    };
    
    void syncDomain();
  }, [user, selectedDomain?.id, domainId]);

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
    if (!user) return;
    
    // Try to get from server first (primary source of truth)
    const serverActiveDomain = await loadActiveDomainFromServer(user.id);
    const currentDomainId = serverActiveDomain || domainId || loadActiveDomain(user.id) || '';
    
    if (!currentDomainId) {
      console.warn('Dashboard: No active domain for user', user.id);
      toast({ 
        title: "No Domain Selected", 
        description: "Please select a domain to view dashboard data.", 
        variant: "destructive" 
      });
      return;
    }
    
    try {
      setLoading(true);
      console.log('Dashboard: Fetching summary for domain:', currentDomainId, 'days:', timePeriod);
      const data = await api.getDashboardSummary({ domain_id: currentDomainId, days: Number(timePeriod) });
      console.log('Dashboard: API response received:', data);
      setSummary(data);
      // Only show success toast if there's actual data, not for empty data
      if (data && (data.total_mentions > 0 || data.total_citations > 0 || data.visibility_score !== 0)) {
        toast({ title: "Data Loaded", description: "Dashboard updated." });
      }
    } catch (e) {
      console.error('Dashboard: API error:', e);
      const errorMessage = e instanceof Error ? e.message : String(e);
      // Only show error for actual errors, not empty data
      const isNetworkError = errorMessage.includes('fetch') || errorMessage.includes('network') || errorMessage.includes('Network');
      const isServerError = errorMessage.includes('500') || errorMessage.includes('503') || errorMessage.includes('502');
      
      // Only show error toast for actual errors, not for empty data
      if (isNetworkError || isServerError || (!errorMessage.includes('404') && !errorMessage.includes('Not Found'))) {
        toast({ 
          title: "Failed to load dashboard", 
          description: errorMessage, 
          variant: "destructive" 
        });
      }
      // For empty data, set default empty summary
      setSummary({
        total_mentions: 0,
        total_citations: 0,
        visibility_score: 0,
        average_position: 0,
        sentiment_score: 0,
        mentions_change: null,
        citations_change: null,
        visibility_change: null,
        position_change: null,
        sentiment_change: null
      });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void fetchSummary();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, domainId, timePeriod, selectedDomain?.id]);

  return (
    <div className="p-8 space-y-8 bg-background animate-fade-in">
      <div className="space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-4xl font-bold tracking-tight">Insights</h1>
            <p className="text-muted-foreground mt-2">
              Overview of your domain's AI search visibility performance
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
          value={summary?.metrics?.total_mentions ?? "-"}
          change={summary?.metrics?.mentions_change ?? undefined}
          trend={summary?.metrics?.mentions_change && summary.metrics.mentions_change > 0 ? "up" : "down"}
          icon={<Eye className="h-6 w-6" />}
        />
        <MetricCard
          title="Total Citations"
          value={summary?.metrics?.total_citations ?? "-"}
          change={summary?.metrics?.citations_change ?? undefined}
          trend={summary?.metrics?.citations_change && summary.metrics.citations_change > 0 ? "up" : "down"}
          icon={<Link2 className="h-6 w-6" />}
        />
        <MetricCard
          title="Visibility Score"
          value={summary?.metrics?.visibility_score ?? "-"}
          change={summary?.metrics?.visibility_change ?? undefined}
          trend={summary?.metrics?.visibility_change && summary.metrics.visibility_change > 0 ? "up" : "down"}
          icon={<Target className="h-6 w-6" />}
        />
        <MetricCard
          title="Avg Position"
          value={summary?.metrics?.avg_position ?? "-"}
          change={summary?.metrics?.position_change ?? undefined}
          trend={summary?.metrics?.position_change && summary.metrics.position_change < 0 ? "up" : "down"}
          icon={<TrendingUp className="h-6 w-6" />}
        />
        <MetricCard
          title="Active Alerts"
          value={summary?.metrics?.active_alerts ?? "-"}
          icon={<Bell className="h-6 w-6" />}
        />
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 flex flex-col gap-6">
          <VisibilityScore
            brand={domainName}
            score={summary?.brand?.visibility_score ?? 0}
            mentions={summary?.brand?.total_mentions ?? 0}
            avgPosition={summary?.brand?.avg_position ?? 0}
            sentiment={{
              positive: Math.round(summary?.brand?.sentiment?.positive_percentage ?? 0),
              neutral: Math.round(summary?.brand?.sentiment?.neutral_percentage ?? 0),
              negative: Math.round(summary?.brand?.sentiment?.negative_percentage ?? 0),
            }}
          />
          <div className="flex-1">
            <TrendChart data={summary?.trends} />
          </div>
        </div>
        <div className="flex flex-col gap-6">
          <PlatformMentions data={
            Array.isArray(summary?.platforms)
              ? summary.platforms.map((p: any) => ({
                  platform: p.platform ?? 'Platform',
                  count: p.mention_count ?? 0,
                  avg_position: p.avg_position ?? 0,
                }))
              : undefined
          } />
          <CompetitorComparison competitors={
            summary?.share_of_voice?.competitors?.map((c: any) => ({
              name: c.name || `Competitor ${c.competitor_id}`,
              url: c.url || '',
              mentions: c.mention_count ?? 0,
              shareOfVoice: c.share_percentage ?? 0,
              trend: c.trend ?? 0,
            }))
          } />
        </div>
      </div>

      {/* Mentions Table */}
      <MentionTable mentions={summary?.recent_mentions} />
    </div>
  );
};

export default Dashboard;
