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
import { MisinformationDetailDialog } from "@/components/MisinformationDetailDialog";
import { MisinformationActionDialog } from "@/components/MisinformationActionDialog";
import { ConfigureDetectionDialog } from "@/components/ConfigureDetectionDialog";
import { StartScanDialog } from "@/components/StartScanDialog";
import { ContentComparisonDialog } from "@/components/ContentComparisonDialog";
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  Shield,
  Eye,
  FileText,
  Settings,
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
  Loader2
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
  const [actionDialogOpen, setActionDialogOpen] = useState(false);
  const [configureDialogOpen, setConfigureDialogOpen] = useState(false);
  const [startScanDialogOpen, setStartScanDialogOpen] = useState(false);
  const [comparisonDialogOpen, setComparisonDialogOpen] = useState(false);
  const [selectedCase, setSelectedCase] = useState<MisinformationAlert | null>(null);

  // Data state
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
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
    try {
      await apiClient.triggerMisinformationScan({ domain_id: selectedDomain.id });
      toast({
        title: "Scan Started",
        description: "Misinformation scan has been initiated. This may take a few minutes."
      });
      // Refresh data after a delay
      setTimeout(() => fetchData(), 5000);
    } catch (err: any) {
      toast({
        title: "Scan Failed",
        description: err.message || 'Failed to start scan',
        variant: "destructive"
      });
    } finally {
      setScanning(false);
    }
  };

  const handleUpdateAlertStatus = async (alertId: number, status: string) => {
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
    }
  };

  // Generate detection metrics from dashboard data
  // Summary Cards: Total Detected, Broken Links, Misinformation, Outdated Information
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

  const handleTakeAction = (misinformationCase: MisinformationAlert) => {
    setSelectedCase(misinformationCase);
    setActionDialogOpen(true);
  };

  const handleConfigureRules = () => {
    setConfigureDialogOpen(true);
  };

  const handleStartMonitoring = () => {
    handleTriggerScan();
  };

  // Show loading state
  if (loading && !dashboardData) {
    return <PageLoader />;
  }

  const handleExportReport = () => {
    toast({
      title: "Exporting Report",
      description: "Generating misinformation report...",
    });
  };

  return (
    <div className="p-8 space-y-8 bg-background animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Misinformation Alerts</h1>
          <p className="text-muted-foreground mt-2">
            Detect and correct AI hallucinations about your brand
          </p>
        </div>
        <div className="flex gap-3">
          <Button onClick={handleStartMonitoring} disabled={scanning || !selectedDomain}>
            {scanning ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Play className="h-4 w-4 mr-2" />
            )}
            {scanning ? 'Scanning...' : 'Start Scan'}
          </Button>
        </div>
      </div>

      {/* Detection Metrics - Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {detectionMetrics.map((metric) => {
          const IconComponent = metric.icon;
          return (
            <Card key={metric.name} className="transition-all duration-300 border border-border hover:border-primary">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {metric.name}
                </CardTitle>
                <div className={`p-2 rounded-lg bg-muted/50`}>
                  <IconComponent className={`h-4 w-4 ${metric.color}`} />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{metric.value}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  {metric.name === "Total Detected" && "All issues found"}
                  {metric.name === "Broken Links" && "Invalid citations"}
                  {metric.name === "Misinformation" && "Factual errors"}
                  {metric.name === "Outdated Info" && "Stale content"}
                </p>
              </CardContent>
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
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Active Misinformation Cases</CardTitle>
                  <CardDescription>
                    Detected inaccuracies requiring attention
                  </CardDescription>
                </div>
                <Button variant="outline" onClick={handleExportReport}>
                  <FileText className="h-4 w-4 mr-2" />
                  Export Report
                </Button>
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
                      <div className="flex gap-2 pt-3 border-t border-border">
                        <Button size="sm" onClick={() => handleViewDetails(item)}>
                          <Eye className="h-3 w-3 mr-1" />
                          View Details
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => handleTakeAction(item)}>
                          <Settings className="h-3 w-3 mr-1" />
                          Take Action
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
                              <h4 className="font-medium">{item.title}</h4>
                            </div>
                            <div className="flex items-center gap-3 text-sm text-muted-foreground mt-1">
                              <Badge variant="secondary">
                                {alertTypeLabels[item.alert_type] || item.alert_type}
                              </Badge>
                              {item.platform && (
                                <>
                                  <span>•</span>
                                  <span>{item.platform}</span>
                                </>
                              )}
                              <span>•</span>
                              <span>Resolved {item.resolved_at ? formatTimeAgo(item.resolved_at) : 'recently'}</span>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          {item.resolution_notes && (
                            <div className="text-right max-w-[200px]">
                              <p className="text-sm font-medium">Resolution Notes</p>
                              <p className="text-sm text-muted-foreground truncate">{item.resolution_notes}</p>
                            </div>
                          )}
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
    <MisinformationActionDialog
      open={actionDialogOpen}
      onOpenChange={setActionDialogOpen}
      misinformationCase={selectedCase}
    />
    <ConfigureDetectionDialog
      open={configureDialogOpen}
      onOpenChange={setConfigureDialogOpen}
    />
    <StartScanDialog
      open={startScanDialogOpen}
      onOpenChange={setStartScanDialogOpen}
    />
    <ContentComparisonDialog
      open={comparisonDialogOpen}
      onOpenChange={setComparisonDialogOpen}
    />
    </div>
  );
};

export default MisinformationAlerts;
