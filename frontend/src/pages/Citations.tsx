import { useState, useRef, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageLoader } from "@/components/PageLoader";
import { ProcessingStateCard } from "@/components/ProcessingStateCard";
import { useDomainStore } from "@/stores/domainStore";
import { isDomainProcessing, isMisinformationProcessing } from "@/utils/processingStatus";
import { apiClient } from "@/services/api";
import { useToast } from "@/hooks/use-toast";
import {
  Link2,
  ExternalLink,
  Search,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Clock,
  Globe,
  Building2,
  ArrowUpRight,
  FileText,
  RefreshCw,
  Loader2,
  LinkIcon,
  TrendingUp,
  ShieldCheck,
  Download,
} from "lucide-react";
import { getFaviconUrl, handleFaviconError } from "@/utils/faviconHelper";
import { InfoHint, MetricHint } from "@/components/InfoHint";

const Citations = () => {
  const { selectedDomain } = useDomainStore();
  const { toast } = useToast();
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [sourceTypeFilter, setSourceTypeFilter] = useState<string>("all");
  const [platformFilter, setPlatformFilter] = useState<string>("all");
  const [currentPage, setCurrentPage] = useState(1);
  const [activeTab, setActiveTab] = useState("all");
  const [paginationDirection, setPaginationDirection] = useState<'next' | 'prev' | null>(null);
  const [isPaginationLoading, setIsPaginationLoading] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const pageSize = 10; // Reduced from 20 for faster loading

  // Ref to track table container position
  const tableContainerRef = useRef<HTMLDivElement>(null);
  const savedScrollPosition = useRef<number>(0);

  const domainId = selectedDomain?.id?.toString() || "";

  // Prevent scroll on page change
  useEffect(() => {
    if (isPaginationLoading) {
      // Save current scroll position
      savedScrollPosition.current = window.scrollY;
    } else if (savedScrollPosition.current > 0) {
      // Restore scroll position after loading
      window.scrollTo(0, savedScrollPosition.current);
      savedScrollPosition.current = 0;
    }
  }, [isPaginationLoading]);

  // Fetch dashboard data
  const { data: dashboardData, isLoading: dashboardLoading, refetch: refetchDashboard } = useQuery({
    queryKey: ["citationsDashboard", domainId],
    queryFn: () => apiClient.getCitationsDashboard({ domain_id: domainId }),
    enabled: !!domainId,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
    refetchOnWindowFocus: false, // Prevent refetch on window focus
    // While a validation is running, poll so the counts and the button state
    // advance on their own. The scan is a background job, so without this the
    // page would keep showing whatever was true when it was opened — including
    // after a refresh, since the cache is keyed only on the domain.
    refetchInterval: (data: any) => (data?.validation?.state === 'running' ? 10000 : false),
  });

  // Fetch citations list
  const { data: citationsData, isLoading: citationsLoading, isFetching: citationsFetching, refetch: refetchCitations } = useQuery({
    queryKey: ["citations", domainId, statusFilter, sourceTypeFilter, platformFilter, searchQuery, currentPage, activeTab],
    queryFn: () => {
      // Map activeTab to server-side source_type filter
      let effectiveSourceType = sourceTypeFilter !== "all" ? sourceTypeFilter : undefined;
      if (activeTab === "your_domain") effectiveSourceType = "your_domain";
      else if (activeTab === "third_party") effectiveSourceType = "third_party";

      return apiClient.getCitations({
        domain_id: domainId,
        status: statusFilter !== "all" ? statusFilter : undefined,
        source_type: effectiveSourceType,
        platform: platformFilter !== "all" ? platformFilter : undefined,
        search: searchQuery || undefined,
        page: currentPage,
        page_size: pageSize,
      });
    },
    enabled: !!domainId,
    staleTime: 2 * 60 * 1000, // Cache for 2 minutes
    refetchOnWindowFocus: false, // Prevent refetch on window focus
    keepPreviousData: true, // Keep previous data while fetching new page
    // Slower than the dashboard poll: the table is heavier to rebuild and the
    // per-row clocks matter less than the headline counts while a run is live.
    refetchInterval: (dashboardData as any)?.validation?.state === 'running' ? 20000 : false,
  });

  // Fetch citations by source
  const { data: sourceData, refetch: refetchSource } = useQuery({
    queryKey: ["citationsBySource", domainId],
    queryFn: () => apiClient.getCitationsBySource({ domain_id: domainId, limit: 10 }),
    enabled: !!domainId,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
    refetchOnWindowFocus: false, // Prevent refetch on window focus
  });

  // Reset loading state when data finishes loading
  useEffect(() => {
    if (!citationsFetching && isPaginationLoading) {
      // Small delay to ensure smooth transition
      const timer = setTimeout(() => {
        setIsPaginationLoading(false);
        setPaginationDirection(null);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [citationsFetching, isPaginationLoading]);

  // A previous `handleExport` lived here that only fired a "your report is being
  // generated" toast and generated nothing. It was wired to no button, so it
  // never misled anyone — the real implementation is further down.

  const handleRefresh = async () => {
    await Promise.all([refetchDashboard(), refetchCitations(), refetchSource()]);
    toast({
      title: "Data refreshed",
      description: "Citations data has been updated.",
    });
  };

  if (!selectedDomain) {
    return (
      <div className="p-8 flex flex-col items-center justify-center min-h-[400px] bg-background animate-fade-in">
        <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-4">
          <Link2 className="h-8 w-8 text-muted-foreground" />
        </div>
        <h2 className="text-xl font-semibold mb-2">No Domain Selected</h2>
        <p className="text-muted-foreground text-center max-w-md">
          Please select a domain from the dropdown to view citation analytics.
        </p>
      </div>
    );
  }

  if (dashboardLoading) {
    return <PageLoader />;
  }

  // Show ProcessingStateCard when:
  // 1. Domain is processing prompts (INIT, SCHD, PROC)
  // 2. Misinformation is still processing (READY or SCANNING)
  // Otherwise (misinformation is done - SCANNED/NO_ISSUES, or not started), show page with empty data
  const isPromptProcessing = selectedDomain?.processing_status && 
    ['INIT', 'SCHD', 'PROC'].includes(selectedDomain.processing_status);
  const isMisinfoStillProcessing = isMisinformationProcessing(selectedDomain);
  
  if (isPromptProcessing || isMisinfoStillProcessing) {
    return <ProcessingStateCard domain={selectedDomain!} />;
  }

  const summary = dashboardData?.summary || {
    total_citations: 0,
    unique_sources: 0,
    your_domain_citations: 0,
    competitor_citations: 0,
    citation_rate: 0,
    avg_citations_per_response: 0,
    broken_links: 0,
    new_sources_7d: 0,
  };

  const statusBreakdown = dashboardData?.status_breakdown || {};
  const validation = dashboardData?.validation;
  const platformBreakdown = dashboardData?.platform_breakdown || {};
  const topSources = sourceData?.results || dashboardData?.top_domains || [];
  const citations = citationsData?.results || [];
  const totalCitations = citationsData?.total || 0;
  const totalPages = Math.ceil(totalCitations / pageSize);

  // Three states from the server, never inferred from row counts: rows start
  // landing seconds into a run, so "some rows exist" would read as finished
  // while most URLs were still queued.
  const validationState: string = validation?.state || 'never';
  const isValidationRunning = validationState === 'running' || isValidating;
  const alreadyValidated = validationState === 'validated';
  const validationProgress =
    validation?.total ? `${validation.checked ?? 0} of ${validation.total}` : '';

  const handleExport = async () => {
    if (!domainId) return;
    setIsExporting(true);
    try {
      toast({ title: "Preparing export", description: "Building your citations workbook…" });
      await apiClient.exportCitationsExcel({
        domain_id: domainId,
        domain_name: selectedDomain?.name,
      });
      toast({ title: "Export ready", description: "Your citations workbook has been downloaded." });
    } catch (error: any) {
      toast({
        title: "Export failed",
        description: error?.message || "Could not build the export.",
        variant: "destructive",
      });
    } finally {
      setIsExporting(false);
    }
  };

  const handleValidate = async () => {
    if (!domainId) return;
    setIsValidating(true);
    try {
      const result: any = await apiClient.validateCitations({ domain_id: domainId });
      toast({
        title: "Validation started",
        description: result?.message || "Checking each cited URL now.",
      });
      // Refetch straight away so `validation.state` flips to 'running' and the
      // polling above takes over from here.
      refetchDashboard();
    } catch (error: any) {
      // 409 is the expected "already done" path, not a failure — say so plainly
      // instead of showing a generic error.
      const detail = error?.data?.error || error?.message || "Could not start validation.";
      const isAlreadyValidated = error?.status === 409;
      toast({
        title: isAlreadyValidated ? "Already validated" : "Validation failed",
        description: detail,
        variant: isAlreadyValidated ? "default" : "destructive",
      });
    } finally {
      setIsValidating(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "valid":
        return <CheckCircle2 className="h-4 w-4 text-success" />;
      case "broken":
        return <XCircle className="h-4 w-4 text-destructive" />;
      case "blocked":
        return <AlertCircle className="h-4 w-4 text-warning" />;
      case "pending":
        return <Clock className="h-4 w-4 text-muted-foreground" />;
      default:
        return <AlertCircle className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const formatDate = (date: string) => {
    return new Date(date).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const truncateUrl = (url: string, maxLength: number = 60) => {
    if (url.length <= maxLength) return url;
    return url.substring(0, maxLength) + "...";
  };

  // Server-side filtering via activeTab → source_type param (no client-side filter needed)
  const filteredCitations = citations;

  return (
    <div className="p-8 space-y-8 bg-background animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Citations</h1>
          <p className="text-muted-foreground mt-2">
            Track and analyze source citations across AI platforms
          </p>
        </div>
        {/* Validation is normally automatic, but it only fires once — on the
            transition into COMP at the end of a domain's first prompt run. A
            domain that missed that event has no other way to clear its pending
            citations, which is what this button is for. It refuses to re-run
            on an already-validated domain rather than re-billing the crawl. */}
        <div className="flex items-center gap-3">
          {/* Outline, matching the export buttons on Mentions and Prompts —
              the primary gradient is reserved for the action that starts work. */}
          <Button variant="outline" onClick={handleExport} disabled={isExporting}>
            {isExporting
              ? <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              : <Download className="h-4 w-4 mr-2" />}
            {isExporting ? "Exporting..." : "Export Citations"}
          </Button>
          <Button
            className="gradient-primary shadow-md shadow-primary/20 text-primary-foreground"
            onClick={handleValidate}
            disabled={isValidationRunning || alreadyValidated}
            title={
              isValidationRunning
                ? `Validation in progress${validationProgress ? ` — ${validationProgress} checked` : ""}`
                : alreadyValidated
                  ? "These citations have already been validated"
                  : "Check every cited URL and mark it valid or broken"
            }
          >
            {isValidationRunning
              ? <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              : <ShieldCheck className="h-4 w-4 mr-2" />}
            {isValidationRunning
              ? "Validating..."
              : alreadyValidated
                ? "Citations Validated"
                : "Validate Citations"}
          </Button>
        </div>
      </div>

      {/* Overview Cards
          Same card shape as the Secondary Metrics row below: a compact
          text-2xl figure with a plain icon. The two rows used to differ
          (text-4xl and a padded icon tile up here), which made the top row
          noticeably taller and the grid look misaligned. */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="p-6 border border-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground flex items-center gap-1.5">
                Total Citations
                <InfoHint>
                  <MetricHint
                    title="Total Citations"
                    plain="Every source link the AI platforms attached to an answer about you — your own pages and everyone else's."
                    formula="Counts each URL in every completed response, all-time. The same URL cited in five answers counts five times; use Unique Sources for distinct websites."
                  />
                </InfoHint>
              </p>
              <p className="text-2xl font-bold mt-1">{summary.total_citations}</p>
            </div>
            <Link2 className="h-5 w-5 text-primary" />
          </div>
          {/* Green with a rising arrow only when something actually rose.
              At 0 this read "+0 new this week" in success green, which framed
              a flat week as growth. */}
          {summary.new_sources_7d > 0 ? (
            <p className="text-xs text-muted-foreground mt-2 flex items-center gap-1">
              <ArrowUpRight className="h-3 w-3 text-success" />
              <span className="text-success font-medium">+{summary.new_sources_7d}</span>
              new this week
            </p>
          ) : (
            <p className="text-xs text-muted-foreground mt-2">No new sources this week</p>
          )}
        </Card>

        <Card className="p-6 border border-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground flex items-center gap-1.5">
                Unique Sources
                <InfoHint>
                  <MetricHint
                    title="Unique Sources"
                    plain="How many different websites the AI platforms draw on when they talk about your market."
                    formula="Distinct hostnames across all cited URLs. Ten pages from one site count as one source."
                  />
                </InfoHint>
              </p>
              <p className="text-2xl font-bold mt-1">{summary.unique_sources}</p>
            </div>
            <Globe className="h-5 w-5 text-secondary" />
          </div>
          <p className="text-xs text-muted-foreground mt-2">Distinct domains cited</p>
        </Card>

        <Card className="p-6 border border-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground flex items-center gap-1.5">
                Your Domain
                <InfoHint>
                  <MetricHint
                    title="Your Domain"
                    plain="Citations that point at your own website — the ones you directly control and can improve."
                    formula="Cited URLs containing your registered domain. Everything else counts as third-party."
                  />
                </InfoHint>
              </p>
              <p className="text-2xl font-bold text-success mt-1">{summary.your_domain_citations}</p>
            </div>
            <Building2 className="h-5 w-5 text-success" />
          </div>
          <p className="text-xs text-muted-foreground mt-2">Citations to your website</p>
        </Card>

        <Card className="p-6 border border-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground flex items-center gap-1.5">
                Broken Links
                <InfoHint>
                  <MetricHint
                    title="Broken Links"
                    plain="Cited pages that no longer load. If one of these is yours, an AI answer is sending readers to a dead page."
                    formula="Crawled citations that returned an HTTP error (400 or above) or that the crawler could not fetch at all."
                  />
                </InfoHint>
              </p>
              <p className="text-2xl font-bold text-destructive mt-1">{summary.broken_links}</p>
            </div>
            <XCircle className="h-5 w-5 text-destructive" />
          </div>
          <p className="text-xs text-muted-foreground mt-2">Need attention</p>
        </Card>
      </div>

      {/* Secondary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="p-6 border border-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground flex items-center gap-1.5">
                Citation Rate
                <InfoHint>
                  <MetricHint
                    title="Citation Rate"
                    plain="How often the AI platforms bother to show their sources at all. A low rate means most answers about you are unsourced assertions."
                    formula="Completed responses carrying at least one citation ÷ all completed responses, as a percentage."
                  />
                </InfoHint>
              </p>
              <p className="text-2xl font-bold mt-1">{summary.citation_rate}%</p>
            </div>
            <TrendingUp className="h-5 w-5 text-muted-foreground" />
          </div>
          <p className="text-xs text-muted-foreground mt-2">Of responses include citations</p>
        </Card>

        <Card className="p-6 border border-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground flex items-center gap-1.5">
                Avg Citations/Response
                <InfoHint>
                  <MetricHint
                    title="Avg Citations/Response"
                    plain="How many sources a typical answer leans on. Higher means more competition for the reader's attention inside a single answer."
                    formula="Total citations ÷ all completed responses — responses with no citations are included in the divisor, so this sits below the per-cited-answer average."
                  />
                </InfoHint>
              </p>
              <p className="text-2xl font-bold mt-1">{summary.avg_citations_per_response}</p>
            </div>
            <LinkIcon className="h-5 w-5 text-muted-foreground" />
          </div>
          <p className="text-xs text-muted-foreground mt-2">Average per AI response</p>
        </Card>

        <Card className="p-6 border border-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground flex items-center gap-1.5">
                Valid Links
                <InfoHint>
                  <MetricHint
                    title="Valid Links"
                    plain="Cited pages confirmed to be live and reachable."
                    formula="Crawled citations the crawler fetched successfully with an HTTP status below 400."
                  />
                </InfoHint>
              </p>
              <p className="text-2xl font-bold text-success mt-1">{statusBreakdown.valid || 0}</p>
            </div>
            <CheckCircle2 className="h-5 w-5 text-success" />
          </div>
          <p className="text-xs text-muted-foreground mt-2">Working citations</p>
        </Card>

        <Card className="p-6 border border-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground flex items-center gap-1.5">
                Pending
                <InfoHint>
                  <MetricHint
                    title="Pending"
                    plain="Citations we have collected but not yet visited, so their live/broken status is still unknown."
                    formula="Total citations minus the ones the crawler has already checked. This falls as validation catches up."
                  />
                </InfoHint>
              </p>
              <p className="text-2xl font-bold text-warning mt-1">{statusBreakdown.pending || 0}</p>
            </div>
            <Clock className="h-5 w-5 text-warning" />
          </div>
          <p className="text-xs text-muted-foreground mt-2">Awaiting validation</p>
        </Card>
      </div>

      {/* Platform & Sources */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Citations by Platform */}
        <Card className="p-6 border border-border">
          <h3 className="text-lg font-semibold mb-4">Citations by Platform</h3>
          <div className="space-y-4">
            {Object.entries(platformBreakdown).length > 0 ? (
              Object.entries(platformBreakdown).map(([platform, count]: [string, any]) => {
                const total = Object.values(platformBreakdown).reduce((a: any, b: any) => a + b, 0) as number;
                const percentage = total > 0 ? Math.round((count / total) * 100) : 0;
                return (
                  <div key={platform} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium capitalize">{platform}</span>
                      <span className="text-sm text-muted-foreground">{count} ({percentage}%)</span>
                    </div>
                    <div className="h-2 rounded-full overflow-hidden bg-muted">
                      <div
                        className="h-full bg-primary rounded-full transition-all duration-500"
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="text-center py-8">
                <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mx-auto mb-3">
                  <Globe className="h-6 w-6 text-muted-foreground" />
                </div>
                <p className="text-muted-foreground text-sm">No platform data available</p>
              </div>
            )}
          </div>
        </Card>

        {/* Top Cited Sources */}
        <Card className="p-6 border border-border">
          <h3 className="text-lg font-semibold mb-4">Top Cited Sources</h3>
          <div className="space-y-3">
            {topSources.length > 0 ? (
              topSources.slice(0, 5).map((source: any, index: number) => (
                <div key={source.source_domain || source.domain} className="flex items-center justify-between p-3 rounded-lg bg-muted/30 border border-border/50">
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm ${
                      index === 0
                        ? "bg-gradient-to-br from-primary to-secondary text-primary-foreground"
                        : "bg-muted text-muted-foreground"
                    }`}>
                      {index + 1}
                    </div>
                    <img
                      src={getFaviconUrl(source.source_domain || source.domain, 32)}
                      alt=""
                      className="w-4 h-4"
                      onError={(e) => handleFaviconError(e, source.source_domain || source.domain, '', 32)}
                    />
                    <div className="flex flex-col">
                      <span className="text-sm truncate max-w-[160px] font-medium">{source.source_domain || source.domain}</span>
                      {source.platforms && source.platforms.length > 0 && (
                        <span className="text-xs text-muted-foreground">{source.platforms.join(', ')}</span>
                      )}
                    </div>
                  </div>
                  <div className="text-right">
                    <Badge variant="secondary">{source.mention_count || source.count}</Badge>
                    {source.valid_count !== undefined && (
                      <div className="text-xs text-muted-foreground mt-1">
                        {source.valid_count} valid
                      </div>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-8">
                <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mx-auto mb-3">
                  <Globe className="h-6 w-6 text-muted-foreground" />
                </div>
                <p className="text-muted-foreground text-sm">No sources data available</p>
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Citations Table */}
      <Card className="p-6 border border-border">
        <Tabs value={activeTab} onValueChange={(v) => { setActiveTab(v); setCurrentPage(1); }} className="w-full">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-6">
            <TabsList className="bg-muted/50 p-1 border border-border">
              <TabsTrigger value="all" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">
                All Citations
              </TabsTrigger>
              <TabsTrigger value="your_domain" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">
                Your Domain
              </TabsTrigger>
              <TabsTrigger value="third_party" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">
                Third Party
              </TabsTrigger>
            </TabsList>

            <div className="flex flex-wrap items-center gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search URLs..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 w-[200px]"
                />
              </div>

              <Select value={statusFilter} onValueChange={(val) => { setStatusFilter(val); setCurrentPage(1); }}>
                <SelectTrigger className="w-[130px]">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="valid">Valid</SelectItem>
                  <SelectItem value="broken">Broken</SelectItem>
                  <SelectItem value="blocked">Blocked</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                </SelectContent>
              </Select>

              <Select value={platformFilter} onValueChange={(val) => { setPlatformFilter(val); setCurrentPage(1); }}>
                <SelectTrigger className="w-[130px]">
                  <SelectValue placeholder="Platform" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Platforms</SelectItem>
                  <SelectItem value="chatgpt">ChatGPT</SelectItem>
                  <SelectItem value="claude">Claude</SelectItem>
                  <SelectItem value="gemini">Gemini</SelectItem>
                  <SelectItem value="perplexity">Perplexity</SelectItem>
                  <SelectItem value="grok">Grok</SelectItem>
                  <SelectItem value="deepseek">DeepSeek</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <TabsContent value={activeTab} ref={tableContainerRef}>
            <CitationsTable
              citations={filteredCitations}
              isLoading={citationsLoading}
              getStatusIcon={getStatusIcon}
              formatDate={formatDate}
              truncateUrl={truncateUrl}
            />

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-6">
                <p className="text-sm text-muted-foreground">
                  Showing {(currentPage - 1) * pageSize + 1} to{" "}
                  {Math.min(currentPage * pageSize, totalCitations)} of {totalCitations} citations
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setPaginationDirection('prev');
                      setIsPaginationLoading(true);
                      setCurrentPage((p) => Math.max(1, p - 1));
                    }}
                    disabled={currentPage === 1 || isPaginationLoading}
                  >
                    {isPaginationLoading && paginationDirection === 'prev' ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : null}
                    Previous
                  </Button>
                  <span className="text-sm text-muted-foreground">
                    {isPaginationLoading ? (
                      <span className="flex items-center gap-2">
                        <Loader2 className="h-3 w-3 animate-spin" />
                        Loading...
                      </span>
                    ) : (
                      `Page ${currentPage} of ${totalPages}`
                    )}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setPaginationDirection('next');
                      setIsPaginationLoading(true);
                      setCurrentPage((p) => Math.min(totalPages, p + 1));
                    }}
                    disabled={currentPage === totalPages || isPaginationLoading}
                  >
                    {isPaginationLoading && paginationDirection === 'next' ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : null}
                    Next
                  </Button>
                </div>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </Card>
    </div>
  );
};

// Citations Table Component
const CitationsTable = ({
  citations,
  isLoading,
  getStatusIcon,
  formatDate,
  truncateUrl,
}: {
  citations: any[];
  isLoading: boolean;
  getStatusIcon: (status: string) => JSX.Element;
  formatDate: (date: string) => string;
  truncateUrl: (url: string, maxLength?: number) => string;
}) => {
  const tableRef = useRef<HTMLDivElement>(null);
  const [tableHeight, setTableHeight] = useState<number>(0);

  // Measure actual table height after render
  useEffect(() => {
    if (tableRef.current && !isLoading) {
      setTableHeight(tableRef.current.offsetHeight);
    }
  }, [citations, isLoading]);

  if (isLoading) {
    return (
      <div
        className="rounded-lg border border-border overflow-hidden flex flex-col items-center justify-center"
        style={{ height: tableHeight > 0 ? `${tableHeight}px` : '650px' }}
      >
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground mb-4" />
        <p className="text-muted-foreground">Loading citations...</p>
      </div>
    );
  }

  if (citations.length === 0) {
    return (
      <div className="rounded-lg border border-border overflow-hidden flex flex-col items-center justify-center" style={{ height: '650px' }}>
        <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-4">
          <Link2 className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold mb-2">No citations found</h3>
        <p className="text-muted-foreground">Try adjusting your filters to see more results</p>
      </div>
    );
  }

  return (
    <div ref={tableRef} className="rounded-lg border border-border overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow className="bg-muted/30">
            <TableHead className="w-[40px] py-2 px-2">Status</TableHead>
            <TableHead className="py-2 px-2">Source URL</TableHead>
            <TableHead className="py-2 px-2">Domain</TableHead>
            <TableHead className="text-center py-2 px-2">Mentions</TableHead>
            <TableHead className="py-2 px-2">Platform</TableHead>
            <TableHead className="py-2 px-2">Last Mentioned</TableHead>
            <TableHead className="w-[50px] py-2 px-2"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {citations.map((citation: any, index: number) => (
            <TableRow key={`${citation.url}-${citation.prompt_analytics_id}-${index}`} className="hover:bg-muted/20 transition-colors">
              <TableCell className="py-2 px-2">{getStatusIcon(citation.display_status)}</TableCell>
              <TableCell className="py-2 px-2">
                <div className="flex flex-col gap-0.5">
                  <div className="flex items-center gap-1.5">
                    <img
                      src={getFaviconUrl(citation.source_domain, 32)}
                      alt=""
                      className="w-4 h-4 flex-shrink-0"
                      onError={(e) => handleFaviconError(e, citation.source_domain, '', 32)}
                    />
                    <span className="text-sm" title={citation.url}>
                      {truncateUrl(citation.url, 50)}
                    </span>
                  </div>
                  {citation.context_snippet && (
                    <p className="text-xs text-muted-foreground line-clamp-1 max-w-[400px]" title={citation.context_snippet}>
                      {citation.context_snippet}
                    </p>
                  )}
                </div>
              </TableCell>
              <TableCell className="py-2 px-2">
                <span className="text-sm text-muted-foreground">{citation.source_domain}</span>
              </TableCell>
              <TableCell className="text-center py-2 px-2">
                <Badge variant="secondary">
                  {/* ?? not ||: the API always sends a real count, but `|| 1`
                      would turn a genuine 0 into a fabricated 1. */}
                  {citation.mention_count ?? 0}
                </Badge>
              </TableCell>
              <TableCell className="py-2 px-2">
                {citation.platform && (
                  <Badge variant="outline" className="capitalize font-medium">
                    {citation.platform}
                  </Badge>
                )}
              </TableCell>
              <TableCell className="text-sm text-muted-foreground py-2 px-2">
                {formatDate(citation.last_mentioned_at || citation.created_at)}
              </TableCell>
              <TableCell className="py-2 px-2">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => window.open(citation.url, "_blank")}
                  className="h-8 w-8 hover:bg-primary/10"
                >
                  <ExternalLink className="h-4 w-4" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
};

export default Citations;
