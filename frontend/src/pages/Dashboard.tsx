import { useEffect, useState, useRef } from "react";
import { MetricCard } from "@/components/MetricCard";
import { VisibilityScore } from "@/components/VisibilityScore";
import { PlatformMentions } from "@/components/PlatformMentions";
import { CompetitorComparison } from "@/components/CompetitorComparison";
import { MentionTable } from "@/components/MentionTable";
import { TrendChart } from "@/components/TrendChart";
import { TimeFilter } from "@/components/TimeFilter";
import { MentionsByCountry } from "@/components/MentionsByCountry";
import { PageLoader } from "@/components/PageLoader";
import { Eye, TrendingUp, Target, Bell, Link2, FileText, Download, CalendarIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { api } from "@/services/api";
import { useAuth } from "@/contexts/AuthContext";
import { loadActiveDomain, loadActiveDomainFromServer, getActiveDomainId } from "@/utils/activeDomain";
import { useDomainStore } from "@/stores/domainStore";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { format } from "date-fns";
import { cn } from "@/lib/utils";

function formatGADate(yyyymmdd: string): string {
  if (!yyyymmdd || yyyymmdd.length !== 8) return yyyymmdd;
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  const m = parseInt(yyyymmdd.slice(4, 6), 10);
  const d = parseInt(yyyymmdd.slice(6, 8), 10);
  return `${d} ${months[m - 1] ?? ""}`;
}

const Dashboard = () => {
  const { user } = useAuth();
  const { selectedDomain } = useDomainStore();
  const [timePeriod, setTimePeriod] = useState("30");
  const [selectedLLM, setSelectedLLM] = useState("all");
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState<any>(null);
  const [domainId, setDomainId] = useState<string | null>(null);
  const [dailyAudience, setDailyAudience] = useState<any[] | null>(null);
  const { toast } = useToast();
  const hasMountedRef = useRef(false);

  // Use refs to track the current filters to prevent unnecessary re-fetches
  const currentDomainIdRef = useRef<string>("");
  const currentTimePeriodRef = useRef<string>("");
  const currentSelectedLLMRef = useRef<string>("");
  const currentStartDateRef = useRef<string>("");
  const currentEndDateRef = useRef<string>("");

  // LLM modules configuration
  const llmModules = [
    { value: "all", label: "All LLMs" },
    { value: "chatgpt", label: "ChatGPT" },
    { value: "gemini", label: "Gemini" },
    { value: "perplexity", label: "Perplexity" },
    { value: "claude", label: "Claude" },
    { value: "grok", label: "Grok" },
    { value: "deepseek", label: "DeepSeek" },
  ];
  
  // Get domain name for display
  const domainNameRaw = selectedDomain?.name || "Domain name";
  const domainName = domainNameRaw
    ? domainNameRaw.charAt(0).toUpperCase() + domainNameRaw.slice(1)
    : "Domain name";

  // Sync domainId from selectedDomain or localStorage
  useEffect(() => {
    if (!user) return;

    if (selectedDomain?.id) {
      const newDomainId = String(selectedDomain.id);
      if (newDomainId !== domainId) {
        setDomainId(newDomainId);
      }
    } else {
      const serverActiveDomain = getActiveDomainId(user);
      const serverDomainId = serverActiveDomain || '';
      if (serverDomainId !== domainId) {
        setDomainId(serverDomainId);
      }
    }
  }, [user, selectedDomain?.id, domainId]);

  const [exporting, setExporting] = useState(false);
  const [exportStartDate, setExportStartDate] = useState<Date | undefined>(undefined);
  const [exportEndDate, setExportEndDate] = useState<Date | undefined>(undefined);
  const [isStartOpen, setIsStartOpen] = useState(false);
  const [isEndOpen, setIsEndOpen] = useState(false);

  const handleSelectStartDate = (date: Date | undefined) => {
    setExportStartDate(date);
    setIsStartOpen(false);
    if (date) {
      if (exportEndDate && exportEndDate < date) {
        setExportEndDate(undefined);
      }
      setIsEndOpen(true);
    }
  };

  const handleSelectEndDate = (date: Date | undefined) => {
    setExportEndDate(date);
    setIsEndOpen(false);
  };

  const handleExportReport = async () => {
    const currentDomainId = selectedDomain?.id ? String(selectedDomain.id) : domainId || '';
    if (!currentDomainId) {
      toast({
        title: "No Domain Selected",
        description: "Please select a domain before exporting.",
        variant: "destructive",
      });
      return;
    }
    if ((exportStartDate && !exportEndDate) || (!exportStartDate && exportEndDate)) {
      toast({
        title: "Incomplete Date Range",
        description: "Please select both a start and end date, or clear both.",
        variant: "destructive",
      });
      return;
    }
    if (exportStartDate && exportEndDate && exportStartDate > exportEndDate) {
      toast({
        title: "Invalid Date Range",
        description: "Start date must be on or before end date.",
        variant: "destructive",
      });
      return;
    }
    try {
      setExporting(true);
      toast({
        title: "Exporting Report",
        description: "Your AI Visibility report is being generated...",
      });
      const safeName = (selectedDomain?.name || 'domain').replace(/\s+/g, '_');
      const timestamp = new Date().toISOString().slice(0, 10).replace(/-/g, '');
      const useRange = Boolean(exportStartDate && exportEndDate);
      await api.exportDashboardReport({
        domain_id: currentDomainId,
        // Only send `days` when no explicit range is chosen, so backend
        // falls back to its existing behavior unchanged.
        ...(useRange ? {} : { days: Number(timePeriod) }),
        llm_model: selectedLLM !== 'all' ? selectedLLM : undefined,
        ...(useRange ? { start_date: format(exportStartDate!, 'yyyy-MM-dd') } : {}),
        ...(useRange ? { end_date: format(exportEndDate!, 'yyyy-MM-dd') } : {}),
        filename: `${safeName}_AI_Visibility_${timestamp}.xlsx`,
      });
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : String(e);
      toast({
        title: "Export Failed",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setExporting(false);
    }
  };

  const handleRefreshData = () => {
    void fetchSummary(true);
  };

  // Time-range presets (1M / 6M / All time) drive the existing `days` window.
  // Selecting one clears any custom date range so the preset actually applies
  // (a complete range otherwise overrides `days` in fetchSummary).
  const handleTimeRangeChange = (days: string) => {
    setExportStartDate(undefined);
    setExportEndDate(undefined);
    setTimePeriod(days);
  };

  async function fetchSummary(forceRefresh = false) {
    if (!user) return;

    // Get domain ID - prefer selectedDomain from Zustand, fallback to server
    let currentDomainId = selectedDomain?.id ? String(selectedDomain.id) : '';

    if (!currentDomainId) {
      const serverActiveDomain = await loadActiveDomainFromServer(user.id);
      currentDomainId = serverActiveDomain || loadActiveDomain(user.id) || '';
    }

    if (!currentDomainId) {
      toast({
        title: "No Domain Selected",
        description: "Please select a domain to view dashboard data.",
        variant: "destructive"
      });
      return;
    }

    // A complete date range overrides the `days` window. A partial range
    // (only start OR only end) is treated as "not applied" to avoid sending
    // an ambiguous request — the user picks both, or neither.
    const useRange = Boolean(exportStartDate && exportEndDate);
    const startStr = useRange ? format(exportStartDate!, 'yyyy-MM-dd') : '';
    const endStr = useRange ? format(exportEndDate!, 'yyyy-MM-dd') : '';

    // Check if all parameters are the same - only skip if nothing has changed
    const domainChanged = currentDomainIdRef.current !== currentDomainId;
    const timePeriodChanged = currentTimePeriodRef.current !== timePeriod;
    const llmChanged = currentSelectedLLMRef.current !== selectedLLM;
    const startChanged = currentStartDateRef.current !== startStr;
    const endChanged = currentEndDateRef.current !== endStr;

    // If nothing has changed, don't re-fetch (unless explicitly forced via refresh button)
    if (!forceRefresh && !domainChanged && !timePeriodChanged && !llmChanged && !startChanged && !endChanged && summary) {
      return;
    }

    // Update refs to track current state
    currentDomainIdRef.current = currentDomainId;
    currentTimePeriodRef.current = timePeriod;
    currentSelectedLLMRef.current = selectedLLM;
    currentStartDateRef.current = startStr;
    currentEndDateRef.current = endStr;

    try {
      setLoading(true);
      const data = await api.getDashboardSummary({
        domain_id: currentDomainId,
        // Only send `days` when no explicit range is applied — the backend
        // falls back to its existing behavior unchanged.
        ...(useRange ? {} : { days: Number(timePeriod) }),
        llm_model: selectedLLM !== 'all' ? selectedLLM : undefined,
        ...(useRange ? { start_date: startStr, end_date: endStr } : {}),
      });
      setSummary(data);

      // Fetch GA daily traffic series for the Monthly Audience tab
      api.getGAData(Number(currentDomainId), startStr || undefined, endStr || undefined)
        .then((res: any) => {
          const daily = res?.data?.daily || [];
          if (daily.length > 0) {
            setDailyAudience(daily.map((row: any) => ({
              date: formatGADate(row.date),
              sessions: Number(row.sessions || 0),
              users: Number(row.totalUsers || 0),
            })));
          } else {
            setDailyAudience(null);
          }
        })
        .catch(() => {
          setDailyAudience(null);
        });
    } catch (e) {
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

  // Fetch summary when dependencies change. The date range is included as
  // a dependency so the cards (Total Mentions, Citations, Visibility,
  // Platform Distribution …) refetch the moment the user picks a range.
  // A partial range (only start or only end) is ignored — fetchSummary
  // only sends start_date/end_date when both are set.
  useEffect(() => {
    if (user && domainId) {
      void fetchSummary();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, domainId, timePeriod, selectedLLM, exportStartDate, exportEndDate]);

  // Show loading state whenever we're fetching data
  if (loading || !summary) {
    return <PageLoader />;
  }

  return (
    <div className="p-8 space-y-8 bg-background animate-fade-in">
      <div className="space-y-4">
        <div className="flex items-start justify-between">
          <div className="min-w-0 flex-1">
            <h1 className="text-4xl font-bold tracking-tight">Insights</h1>
            <p className="text-muted-foreground mt-2 whitespace-nowrap">
              {selectedDomain?.name
                ? `${domainName} • AI Visibility Overview`
                : "AI Visibility Overview"}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Select value={selectedLLM} onValueChange={setSelectedLLM}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Select LLM" />
              </SelectTrigger>
              <SelectContent>
                {llmModules.map((llm) => (
                  <SelectItem key={llm.value} value={llm.value}>
                    {llm.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {/* <TimeFilter selected={timePeriod} onSelect={setTimePeriod} /> */}
            <Popover open={isStartOpen} onOpenChange={setIsStartOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  className={cn(
                    "justify-start text-left font-normal",
                    !exportStartDate && "text-muted-foreground"
                  )}
                >
                  <CalendarIcon className="mr-2 h-4 w-4" />
                  {exportStartDate ? format(exportStartDate, "MMM d, yyyy") : <span>Start date</span>}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <Calendar
                  mode="single"
                  selected={exportStartDate}
                  onSelect={handleSelectStartDate}
                  disabled={(date) => date > new Date()}
                  initialFocus
                />
              </PopoverContent>
            </Popover>
            <Popover open={isEndOpen} onOpenChange={setIsEndOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  className={cn(
                    "justify-start text-left font-normal",
                    !exportEndDate && "text-muted-foreground"
                  )}
                >
                  <CalendarIcon className="mr-2 h-4 w-4" />
                  {exportEndDate ? format(exportEndDate, "MMM d, yyyy") : <span>End date</span>}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <Calendar
                  mode="single"
                  selected={exportEndDate}
                  onSelect={handleSelectEndDate}
                  disabled={(date) => date > new Date() || (exportStartDate ? date < exportStartDate : false)}
                  initialFocus
                />
              </PopoverContent>
            </Popover>
            {(exportStartDate || exportEndDate) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setExportStartDate(undefined);
                  setExportEndDate(undefined);
                  setIsStartOpen(false);
                  setIsEndOpen(false);
                }}
              >
                Clear
              </Button>
            )}
            <Button variant="outline" onClick={handleExportReport} disabled={exporting || loading}>
              <Download className="h-4 w-4 mr-2" />
              {exporting ? "Exporting..." : "Export Report"}
            </Button>
            <Button onClick={handleRefreshData} className="gradient-primary shadow-md shadow-primary/20" disabled={loading}>
              {loading ? "Loading..." : "Refresh Data"}
            </Button>
          </div>
        </div>
      </div>

      {/* ROW 1 — AI Visibility Gauge & Trend Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
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
        </div>
        <div className="lg:col-span-2">
          <TrendChart
            data={summary?.trends}
            metrics={summary?.metrics}
            timeRange={exportStartDate && exportEndDate ? undefined : timePeriod}
            onTimeRangeChange={handleTimeRangeChange}
            audienceData={dailyAudience}
            isPeriodData={summary?.trends_are_period}
          />
        </div>
      </div>

      {/* ROW 2 — Distribution by LLM & Mentions by Country */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <PlatformMentions data={
          Array.isArray(summary?.platforms)
            ? summary.platforms.map((p: any) => ({
                platform: p.platform ?? 'Platform',
                count: p.mention_count ?? 0,
                citations: p.cited_pages ?? 0,
                avg_position: p.avg_position ?? 0,
              }))
            : undefined
        } />
        <MentionsByCountry data={summary?.countries} />
      </div>

      {/* ROW 3 — Key Metrics (moved below the hero) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        <MetricCard
          title="Total Prompts"
          value={summary?.metrics?.total_prompts ?? "-"}
          icon={<FileText className="h-4 w-4" />}
          href="/prompts"
        />
        <MetricCard
          title="Total Citations"
          value={summary?.metrics?.total_citations ?? "-"}
          change={summary?.metrics?.citations_change ?? undefined}
          trend={summary?.metrics?.citations_change && summary.metrics.citations_change > 0 ? "up" : "down"}
          icon={<Link2 className="h-4 w-4" />}
          href="/citations"
        />
        <MetricCard
          title="Total Mentions"
          value={summary?.metrics?.total_mentions ?? "-"}
          change={summary?.metrics?.mentions_change ?? undefined}
          trend={summary?.metrics?.mentions_change && summary.metrics.mentions_change > 0 ? "up" : "down"}
          icon={<Eye className="h-4 w-4" />}
          href="/mentions"
        />
        <MetricCard
          title="Visibility Score"
          value={summary?.metrics?.visibility_score ?? "-"}
          change={summary?.metrics?.visibility_change ?? undefined}
          trend={summary?.metrics?.visibility_change && summary.metrics.visibility_change > 0 ? "up" : "down"}
          icon={<Target className="h-4 w-4" />}
        />
        <MetricCard
          title="Avg Position"
          value={summary?.metrics?.avg_position ?? "-"}
          change={summary?.metrics?.position_change ?? undefined}
          trend={summary?.metrics?.position_change && summary.metrics.position_change < 0 ? "up" : "down"}
          icon={<TrendingUp className="h-4 w-4" />}
        />
      </div>

      {/* ROW 4 — Competitive context (moved below, full width) */}
      <CompetitorComparison competitors={
        summary?.share_of_voice?.competitors?.map((c: any) => ({
          name: c.name || `Competitor ${c.competitor_id}`,
          url: c.url || '',
          mentions: c.mention_count ?? 0,
          shareOfVoice: c.share_percentage ?? 0,
          trend: c.trend ?? 0,
        }))
      } />

      {/* ROW 5 — Mentions Table */}
      <MentionTable mentions={summary?.recent_mentions} />
    </div>
  );
};

export default Dashboard;
