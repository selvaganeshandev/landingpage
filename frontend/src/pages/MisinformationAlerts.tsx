import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import { useDomainStore } from "@/stores/domainStore";
import { apiClient } from "@/services/api";
import { PageLoader } from "@/components/PageLoader";
import { NoPromptsYet } from "@/components/NoPromptsYet";
import { InfoHint, MetricHint } from "@/components/InfoHint";
import { ProcessingStateCard } from "@/components/ProcessingStateCard";
import { MisinformationDetailDialog } from "@/components/MisinformationDetailDialog";
import { isDomainProcessing } from "@/utils/processingStatus";
import { ConfigureDetectionDialog } from "@/components/ConfigureDetectionDialog";
import { ContentComparisonDialog } from "@/components/ContentComparisonDialog";
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  Shield,
  Eye,
  FileText,
  Search,
  Filter,
  TrendingUp,
  AlertCircle,
  XCircle,
  MessageSquare,
  ExternalLink,
  Play,
  LinkIcon,
  RefreshCw,
  Loader2,
  Info,
  Globe,
  FileSearch,
  Zap,
  CheckCircle2,
  Download
} from "lucide-react";

// Types for API responses
interface MisinformationAlert {
  id: number;
  alert_type: 'misinformation' | 'broken_link' | 'outdated';
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'new' | 'reviewed' | 'resolved' | 'dismissed';
  llm_claim: string;
  source_content?: string;
  explanation?: string;
  created_at: string;
  reviewed_at?: string;
  citation_url?: {
    url: string;
    crawl_status: string;
  };
  prompt?: {
    id: number;
    prompt_text: string;
  };
}

interface DashboardData {
  total_detected: number;
  broken_links: number;
  misinformation: number;
  outdated_content: number;
  active_cases: number;
  resolved_cases: number;
  avg_response_time_hours: number;
  trends: {
    total_detected_change: number;
    active_cases_change: number;
    response_time_change: number;
    resolved_change: number;
  };
  scan_status: 'NOT_READY' | 'READY' | 'SCANNING' | 'SCANNED' | 'NO_ISSUES';
  /** True while a scan row is genuinely running (last 24h). The status field
   *  alone cannot tell "queued" from "running for hours" — see the backend. */
  scan_running?: boolean;
  last_scan_at: string | null;
}


// Helper to format time ago
const formatTimeAgo = (dateString: string) => {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffHours / 24);

  if (diffDays > 0) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  if (diffHours > 0) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  return 'Just now';
};

// Map alert types to display labels
const alertTypeLabels: Record<string, string> = {
  misinformation: 'Misinformation',
  broken_link: 'Broken Link',
  outdated: 'Outdated Information'
};

// Map alert types to icons
const getAlertTypeIcon = (alertType: string) => {
  switch (alertType) {
    case 'broken_link':
      return LinkIcon;
    case 'outdated_content':
      return Clock;
    case 'missing_citation':
      return FileText;
    default:
      return AlertTriangle;
  }
};

const getSeverityColor = (severity: string) => {
  switch (severity) {
    case "critical":
      return "bg-destructive text-destructive-foreground";
    case "high":
      return "bg-destructive/80 text-destructive-foreground";
    case "medium":
      return "bg-warning text-warning-foreground";
    case "low":
      return "bg-success text-success-foreground";
    default:
      return "bg-muted";
  }
};

const getStatusColor = (status: string) => {
  switch (status) {
    case "new":
      return "text-warning";
    case "reviewed":
      return "text-primary";
    case "resolved":
      return "text-success";
    case "dismissed":
      return "text-muted-foreground";
    default:
      return "text-muted-foreground";
  }
};

const getStatusIcon = (status: string) => {
  switch (status) {
    case "new":
      return AlertCircle;
    case "reviewed":
      return Eye;
    case "resolved":
      return CheckCircle;
    case "dismissed":
      return XCircle;
    default:
      return Clock;
  }
};

const MisinformationAlerts = () => {
  const { toast } = useToast();
  const { selectedDomain } = useDomainStore();

  // UI state
  const [selectedTab, setSelectedTab] = useState("active");
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [configureDialogOpen, setConfigureDialogOpen] = useState(false);
  const [comparisonDialogOpen, setComparisonDialogOpen] = useState(false);
  const [selectedCase, setSelectedCase] = useState<MisinformationAlert | null>(null);

  // Data state
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [updatingAlertId, setUpdatingAlertId] = useState<number | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [activeAlerts, setActiveAlerts] = useState<MisinformationAlert[]>([]);
  const [resolvedAlerts, setResolvedAlerts] = useState<MisinformationAlert[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Fetch data when domain changes
  useEffect(() => {
    if (selectedDomain?.id) {
      fetchData();
    }
  }, [selectedDomain?.id]);

  const fetchData = async () => {
    if (!selectedDomain?.id) return;

    setLoading(true);
    setError(null);

    try {
      // Fetch dashboard data and alerts in parallel
      // Status values: new, reviewed (active), resolved, dismissed (closed)
      const [dashboardRes, activeRes, resolvedRes] = await Promise.all([
        apiClient.getMisinformationDashboard({ domain_id: String(selectedDomain.id), days: 30 }),
        apiClient.getMisinformationAlerts({
          domain_id: String(selectedDomain.id),
          status: 'new,reviewed'
        }),
        apiClient.getMisinformationAlerts({
          domain_id: String(selectedDomain.id),
          status: 'resolved,dismissed'
        })
      ]);

      setDashboardData(dashboardRes as DashboardData);
      setActiveAlerts((activeRes as any).results || []);
      setResolvedAlerts((resolvedRes as any).results || []);

      // Reset scanning state based on backend status
      const status = (dashboardRes as DashboardData).scan_status;
      if (status && status !== 'SCANNING') {
        setScanning(false);
      }
    } catch (err: any) {
      console.error('Error fetching misinformation data:', err);
      setError(err.message || 'Failed to load misinformation data');
      toast({
        title: "Error loading data",
        description: err.message || 'Failed to load misinformation data',
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleTriggerScan = async () => {
    if (!selectedDomain?.id) return;

    setScanning(true);
    // Show toast immediately when user clicks
    toast({
      title: "Scan Started",
      description: "Misinformation scan has been initiated. This may take a few minutes."
    });

    try {
      await apiClient.triggerMisinformationScan({ domain_id: selectedDomain.id });
      // Refresh data after a delay to get updated scan_status
      setTimeout(() => fetchData(), 5000);
      // Keep scanning=true until fetchData updates scan_status from backend
    } catch (err: any) {
      toast({
        title: "Scan Failed",
        description: err.message || 'Failed to start scan',
        variant: "destructive"
      });
      setScanning(false); // Only reset on error
    }
  };

  const handleUpdateAlertStatus = async (alertId: number, status: string) => {
    setUpdatingAlertId(alertId);
    try {
      await apiClient.updateMisinformationAlert(alertId, { status });
      toast({
        title: "Status Updated",
        description: `Alert status changed to ${status}`
      });
      fetchData(); // Refresh the list
    } catch (err: any) {
      toast({
        title: "Update Failed",
        description: err.message || 'Failed to update alert status',
        variant: "destructive"
      });
    } finally {
      setUpdatingAlertId(null);
    }
  };

  // Generate detection metrics from dashboard data
  // Summary Cards: Total Detected, Broken Links, Misinformation, Outdated Information
  // Written against what the scanner actually flags, so the cards can be read
  // without opening the code that produced them.
  const METRIC_HINTS: Record<string, { plain: string; formula: string }> = {
    "Total Detected": {
      plain: "Every issue the scan has raised about your brand across all AI platforms.",
      formula: "Broken links, misinformation and outdated info combined, all-time rather than for the current window. Alerts stay counted here after they are resolved.",
    },
    "Broken Links": {
      plain: "AI answers citing a page that no longer loads — a reader following that link reaches nothing.",
      formula: "Raised when a cited URL on your own domain returns 404 or 410. Sites that merely refuse our crawler (403) are not counted, since the page is usually fine for a real visitor.",
    },
    "Misinformation": {
      plain: "Cases where an AI answer states something your own cited page does not support.",
      formula: "The cited page is fetched and its text compared against the claim in the answer. A mismatch on a fact the source should confirm is raised here, with both texts kept for review.",
    },
    "Outdated Info": {
      plain: "Answers repeating details your site has since changed — old pricing, discontinued products, superseded figures.",
      formula: "Raised when the cited page still exists but its current content contradicts what the answer says, in a way that reads as staleness rather than error.",
    },
  };

  const defaultMetrics = [
    { name: "Total Detected", value: "0", icon: AlertTriangle, color: "text-destructive" },
    { name: "Broken Links", value: "0", icon: LinkIcon, color: "text-warning" },
    { name: "Misinformation", value: "0", icon: AlertCircle, color: "text-destructive" },
    { name: "Outdated Info", value: "0", icon: Clock, color: "text-muted-foreground" }
  ];

  const detectionMetrics = dashboardData ? [
    {
      name: "Total Detected",
      value: String(dashboardData.total_detected || 0),
      icon: AlertTriangle,
      color: "text-destructive"
    },
    {
      name: "Broken Links",
      value: String(dashboardData.broken_links || 0),
      icon: LinkIcon,
      color: "text-warning"
    },
    {
      name: "Misinformation",
      value: String(dashboardData.misinformation || 0),
      icon: AlertCircle,
      color: "text-destructive"
    },
    {
      name: "Outdated Info",
      value: String(dashboardData.outdated_content || 0),
      icon: Clock,
      color: "text-muted-foreground"
    }
  ] : defaultMetrics;

  const handleViewDetails = (misinformationCase: MisinformationAlert) => {
    setSelectedCase(misinformationCase);
    setDetailDialogOpen(true);
  };

  const handleConfigureRules = () => {
    setConfigureDialogOpen(true);
  };

  const handleStartMonitoring = () => {
    handleTriggerScan();
  };
  /**
   * Export the alert set as a multi-sheet workbook.
   *
   * Replaces a handler that raised a "Generating misinformation report..." toast
   * and produced no file — and which was attached to no button, so it would have
   * misled the first time anyone wired it up.
   */
  const handleExportReport = async () => {
    setIsExporting(true);
    try {
      const XLSX = await import("xlsx");
      const wb = XLSX.utils.book_new();

      const summary = [
        ["Misinformation Alerts", ""],
        ["Domain", selectedDomain?.name || ""],
        ["Generated", new Date().toLocaleString()],
        ["", ""],
        ["Metric", "Count"],
        ["Total detected", dashboardData?.total_detected ?? 0],
        ["Broken links", dashboardData?.broken_links ?? 0],
        ["Misinformation", dashboardData?.misinformation ?? 0],
        ["Outdated info", dashboardData?.outdated_content ?? 0],
        ["", ""],
        ["Active cases", activeAlerts.length],
        ["Resolved cases", resolvedAlerts.length],
      ];
      if ((dashboardData as any)?.by_severity) {
        summary.push(["", ""], ["Severity (active)", "Count"]);
        Object.entries((dashboardData as any).by_severity).forEach(([level, count]) => {
          summary.push([level, count as number]);
        });
      }
      XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(summary), "Summary");

      // Both tabs share a shape, so one mapper keeps the two sheets identical
      // in structure and comparable side by side.
      const toRow = (a: any) => ({
        ID: a.id,
        Type: a.alert_type,
        Severity: a.severity,
        Status: a.status,
        Platform: a.platform || "",
        "AI claim": a.llm_claim || "",
        "Source says": a.source_content || "",
        Explanation: a.explanation || "",
        "Source URL": a.citation_url?.url || a.source_url || "",
        Prompt: a.prompt_text || a.prompt?.prompt || "",
        Detected: a.created_at || "",
        Reviewed: a.reviewed_at || "",
      });

      if (activeAlerts.length) {
        XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(activeAlerts.map(toRow)), "Active Alerts");
      }
      if (resolvedAlerts.length) {
        XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(resolvedAlerts.map(toRow)), "Resolved");
      }

      const all = [...activeAlerts, ...resolvedAlerts];
      if (all.length) {
        const byType: Record<string, { type: string; total: number; low: number; medium: number; high: number; critical: number }> = {};
        all.forEach((a: any) => {
          const key = a.alert_type || "unknown";
          byType[key] = byType[key] || { type: key, total: 0, low: 0, medium: 0, high: 0, critical: 0 };
          byType[key].total += 1;
          const sev = (a.severity || "low") as "low" | "medium" | "high" | "critical";
          if (sev in byType[key]) byType[key][sev] += 1;
        });
        XLSX.utils.book_append_sheet(
          wb,
          XLSX.utils.json_to_sheet(Object.values(byType).map((r) => ({
            Type: r.type,
            Total: r.total,
            Low: r.low,
            Medium: r.medium,
            High: r.high,
            Critical: r.critical,
          }))),
          "By Type",
        );
      }

      const safeName = (selectedDomain?.name || "domain").replace(/[^a-z0-9]+/gi, "_");
      const today = new Date().toISOString().split("T")[0];
      XLSX.writeFile(wb, `misinformation_${safeName}_${today}.xlsx`);

      toast({
        title: "Export ready",
        description: `Downloaded ${wb.SheetNames.length} sheet${wb.SheetNames.length === 1 ? "" : "s"}.`,
      });
    } catch (error: any) {
      toast({
        title: "Export failed",
        description: error?.message || "Could not build the workbook.",
        variant: "destructive",
      });
    } finally {
      setIsExporting(false);
    }
  };


  // Show loading state
  if (loading && !dashboardData) {
    return <PageLoader />;
  }

  // Only the domain's own prompt processing hides the page. A misinformation
  // scan in progress is shown as a banner over the results so far (below):
  // the scan crawls every cited URL and has run for a working day on
  // production, and hiding a page of real alerts behind "1-3 minutes" for
  // that long is what clients reported as "still processing".
  if (isDomainProcessing(selectedDomain)) {
    return <ProcessingStateCard domain={selectedDomain!} />;
  }
  const scanInProgress =
    scanning ||
    dashboardData?.scan_running === true ||
    dashboardData?.scan_status === 'SCANNING';


  // The scan compares cited pages against what AI answers claim; with no prompts
  // there are no answers and no citations, so there is nothing to scan.
  if (selectedDomain?.prompt_count === 0) {
    return <NoPromptsYet what="Misinformation is detected by checking what AI answers claim about you" />;
  }

  // Misinformation scan runs automatically after prompt processing
  // No manual "Start Scan" needed - just show appropriate message if not ready
  if (dashboardData?.scan_status === 'NOT_READY' && !scanning) {
    return (
      <div className="p-8 space-y-6 bg-background animate-fade-in">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold tracking-tight">Misinformation Alerts</h1>
              <p className="text-muted-foreground mt-2">
                Detect and correct AI hallucinations about your brand
              </p>
            </div>
          </div>
        </div>

        <Card className="p-8 border border-border">
          <div className="flex flex-col items-center text-center space-y-6 max-w-2xl mx-auto">
            <div className="p-4 rounded-full bg-muted/50">
              <Info className="h-12 w-12 text-primary" />
            </div>
            <div className="space-y-2">
              <h2 className="text-2xl font-bold">Awaiting Prompt Analytics</h2>
              <p className="text-muted-foreground">
                Misinformation detection will automatically start once your prompt analytics are complete. The system will scan all citations and links to detect misinformation, broken links, and outdated content about your brand.
              </p>
            </div>

            <p className="text-sm text-muted-foreground">
              Automatic scanning begins after prompt processing completes.
            </p>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8 bg-background animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Misinformation Alerts</h1>
          <p className="text-muted-foreground mt-2">
            Detect and correct AI hallucinations about your brand
          </p>
          {scanInProgress && (
            <p className="mt-2 inline-flex items-center gap-2 rounded-md border border-amber-300 bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-800 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-200">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Misinformation scan in progress — it checks every source the AI cited and can take several hours. Alerts below are what it has found so far.
            </p>
          )}
        </div>
        {/* Export only. A Run Scan button was added here and removed: the scan
            fires automatically when a domain finishes processing, and the
            Validate Citations button on the Citations page already covers the
            manual case for the crawl this depends on. handleTriggerScan is left
            in place for the NOT_READY empty state below, which does offer it. */}
        <Button variant="outline" onClick={handleExportReport} disabled={isExporting}>
          {isExporting
            ? <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            : <Download className="h-4 w-4 mr-2" />}
          {isExporting ? "Exporting..." : "Export"}
        </Button>
      </div>

      {/* Detection Metrics - Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {detectionMetrics.map((metric) => {
          const IconComponent = metric.icon;
          return (
            /* Shared metric-card shape: p-6, text-2xl figure, plain icon,
               text-xs subtext — the same as Citations, Sources, Sentiment and
               Share of Voice. These were text-3xl inside a tinted icon tile,
               which made the row taller than every other page's. */
            <Card key={metric.name} className="p-6 border border-border">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground flex items-center gap-1.5">
                    {metric.name}
                    <InfoHint>
                      <MetricHint
                        title={metric.name}
                        plain={METRIC_HINTS[metric.name]?.plain || ""}
                        formula={METRIC_HINTS[metric.name]?.formula || ""}
                      />
                    </InfoHint>
                  </p>
                  <p className={`text-2xl font-bold mt-1 ${metric.color}`}>{metric.value}</p>
                </div>
                <IconComponent className={`h-5 w-5 ${metric.color}`} />
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                {metric.name === "Total Detected" && "All issues found"}
                {metric.name === "Broken Links" && "Invalid citations"}
                {metric.name === "Misinformation" && "Factual errors"}
                {metric.name === "Outdated Info" && "Stale content"}
              </p>
            </Card>
          );
        })}
      </div>

      {/* Main Content Tabs */}
      <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
        <Tabs value={selectedTab} onValueChange={setSelectedTab}>
          <div className="mb-6">
            <TabsList className="bg-muted/50 p-1 border border-border">
              <TabsTrigger value="active" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">
                <AlertCircle className="h-4 w-4 mr-2" />
                Active Cases ({activeAlerts.length})
              </TabsTrigger>
              <TabsTrigger value="resolved" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">
                <CheckCircle className="h-4 w-4 mr-2" />
                Resolved ({resolvedAlerts.length})
              </TabsTrigger>
            </TabsList>
          </div>

        {/* Active Cases Tab */}
        <TabsContent value="active" className="space-y-6">
          <Card className="border border-border">
            <CardHeader>
              <div>
                <CardTitle>Active Misinformation Cases</CardTitle>
                <CardDescription>
                  Detected inaccuracies requiring attention
                </CardDescription>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {activeAlerts.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Shield className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p className="text-lg font-medium">No active cases</p>
                  <p className="text-sm">Start a scan to detect misinformation issues</p>
                </div>
              ) : (
                activeAlerts.map((item) => {
                  const StatusIcon = getStatusIcon(item.status);
                  const AlertTypeIcon = getAlertTypeIcon(item.alert_type);
                  const sourceUrl = item.citation_url?.url;
                  return (
                    <div
                      key={item.id}
                      className="p-4 rounded-lg transition-all duration-300 border border-border hover:border-primary"
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <AlertTypeIcon className="h-4 w-4 text-muted-foreground" />
                            <h4 className="font-semibold">
                              {alertTypeLabels[item.alert_type] || item.alert_type}
                            </h4>
                            <Badge className={getSeverityColor(item.severity)}>
                              {item.severity}
                            </Badge>
                            <Badge variant="outline" className={getStatusColor(item.status)}>
                              <StatusIcon className="h-3 w-3 mr-1" />
                              {item.status}
                            </Badge>
                          </div>
                          {item.explanation && (
                            <p className="text-sm text-muted-foreground mb-3">
                              {item.explanation}
                            </p>
                          )}
                          <div className="grid grid-cols-2 gap-4 text-sm">
                            <div className="space-y-2">
                              <div className="flex items-center gap-2">
                                <span className="text-muted-foreground">Detected:</span>
                                <span>{formatTimeAgo(item.created_at)}</span>
                              </div>
                              {sourceUrl && (
                                <div className="flex items-center gap-2">
                                  <ExternalLink className="h-3 w-3 text-muted-foreground" />
                                  <a
                                    href={sourceUrl}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-primary hover:underline truncate max-w-[200px]"
                                  >
                                    {sourceUrl}
                                  </a>
                                </div>
                              )}
                              {item.prompt && (
                                <div className="flex items-center gap-2">
                                  <span className="text-muted-foreground">Prompt:</span>
                                  <span className="truncate max-w-[200px]">{item.prompt.prompt_text}</span>
                                </div>
                              )}
                            </div>
                            <div className="space-y-2">
                              {item.llm_claim && (
                                <div className="p-2 bg-destructive/10 rounded">
                                  <p className="text-xs font-medium mb-1 text-destructive flex items-center gap-1">
                                    <XCircle className="h-3 w-3" />
                                    LLM Claim:
                                  </p>
                                  <p className="text-xs line-clamp-3">{item.llm_claim}</p>
                                </div>
                              )}
                              {item.source_content && (
                                <div className="p-2 bg-success/10 rounded">
                                  <p className="text-xs font-medium mb-1 text-success flex items-center gap-1">
                                    <CheckCircle className="h-3 w-3" />
                                    Source Content:
                                  </p>
                                  <p className="text-xs line-clamp-3">{item.source_content}</p>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                      {/* Resolve and Investigate were missing entirely, which is
                          why every alert in the database sits at status 'new'
                          and the Resolved tab can never populate — the handler
                          existed but nothing called it. */}
                      <div className="flex gap-2 pt-3 border-t border-border flex-wrap">
                        <Button size="sm" onClick={() => handleViewDetails(item)}>
                          <Eye className="h-3 w-3 mr-1" />
                          View Details
                        </Button>
                        {sourceUrl && (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => window.open(sourceUrl, '_blank')}
                          >
                            <ExternalLink className="h-3 w-3 mr-1" />
                            View Source
                          </Button>
                        )}
                        <div className="ml-auto flex gap-2">
                          {item.status !== 'reviewed' && (
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={updatingAlertId === item.id}
                              onClick={() => handleUpdateAlertStatus(item.id, 'reviewed')}
                            >
                              {updatingAlertId === item.id
                                ? <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                : <Search className="h-3 w-3 mr-1" />}
                              Mark Reviewed
                            </Button>
                          )}
                          <Button
                            size="sm"
                            variant="outline"
                            className="text-success hover:text-success"
                            disabled={updatingAlertId === item.id}
                            onClick={() => handleUpdateAlertStatus(item.id, 'resolved')}
                          >
                            {updatingAlertId === item.id
                              ? <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                              : <CheckCircle2 className="h-3 w-3 mr-1" />}
                            Resolve
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="text-muted-foreground"
                            disabled={updatingAlertId === item.id}
                            onClick={() => handleUpdateAlertStatus(item.id, 'dismissed')}
                          >
                            Dismiss
                          </Button>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Resolved Cases Tab */}
        <TabsContent value="resolved" className="space-y-6">
          <Card className="border border-border">
            <CardHeader>
              <CardTitle>Resolved Cases</CardTitle>
              <CardDescription>
                Successfully corrected misinformation
              </CardDescription>
            </CardHeader>
            <CardContent>
              {resolvedAlerts.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <CheckCircle className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p className="text-lg font-medium">No resolved cases yet</p>
                  <p className="text-sm">Resolved cases will appear here</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {resolvedAlerts.map((item) => {
                    const AlertTypeIcon = getAlertTypeIcon(item.alert_type);
                    return (
                      <div
                        key={item.id}
                        className="flex items-center justify-between p-4 rounded-lg transition-all duration-300 border border-border hover:border-primary"
                      >
                        <div className="flex items-center gap-4">
                          <div className="h-10 w-10 rounded-lg bg-success/10 flex items-center justify-center">
                            <CheckCircle className="h-5 w-5 text-success" />
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <AlertTypeIcon className="h-4 w-4 text-muted-foreground" />
                              <h4 className="font-medium">{alertTypeLabels[item.alert_type] || item.alert_type}</h4>
                            </div>
                            <div className="flex items-center gap-3 text-sm text-muted-foreground mt-1">
                              <Badge variant="secondary" className={item.status === 'resolved' ? 'bg-success/20 text-success' : ''}>
                                {item.status}
                              </Badge>
                              <span>•</span>
                              <span>Resolved {item.reviewed_at ? formatTimeAgo(item.reviewed_at) : 'recently'}</span>
                            </div>
                            {item.explanation && (
                              <p className="text-xs text-muted-foreground mt-1 line-clamp-1">
                                {item.explanation}
                              </p>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          <Button size="sm" variant="outline" onClick={() => handleViewDetails(item)}>
                            View Details
                          </Button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </Card>

    {/* Dialogs */}
    <MisinformationDetailDialog
      open={detailDialogOpen}
      onOpenChange={setDetailDialogOpen}
      misinformationCase={selectedCase}
    />
    {/* How It Works - Information Card */}
      <Card className="border border-border bg-muted/30">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Info className="h-4 w-4 text-primary" />
            How Misinformation Detection Works
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-sm">
            <div className="space-y-2">
              <div className="flex items-center gap-2 font-medium">
                <Globe className="h-4 w-4 text-blue-500" />
                <span>1. Citation Crawling</span>
              </div>
              <p className="text-muted-foreground text-xs">
                We extract all URLs cited in AI responses about your brand and crawl each page to get the actual content.
              </p>
            </div>
            <div className="space-y-2">
              <div className="flex items-center gap-2 font-medium">
                <FileSearch className="h-4 w-4 text-purple-500" />
                <span>2. Content Comparison</span>
              </div>
              <p className="text-muted-foreground text-xs">
                AI compares what the LLM claimed about your brand against the actual source content to find discrepancies.
              </p>
            </div>
            <div className="space-y-2">
              <div className="flex items-center gap-2 font-medium">
                <Zap className="h-4 w-4 text-orange-500" />
                <span>3. Issue Detection</span>
              </div>
              <p className="text-muted-foreground text-xs">
                Flags broken links (404/410), misinformation (factual errors), and outdated info (old prices, discontinued products).
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

    <ConfigureDetectionDialog
      open={configureDialogOpen}
      onOpenChange={setConfigureDialogOpen}
    />
    <ContentComparisonDialog
      open={comparisonDialogOpen}
      onOpenChange={setComparisonDialogOpen}
    />
    </div>
  );
};

export default MisinformationAlerts;
