import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { useToast } from "@/hooks/use-toast";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { CreateReportDialog } from "@/components/CreateReportDialog";
import { ReportPreviewDialog } from "@/components/ReportPreviewDialog";
import { EditReportDialog } from "@/components/EditReportDialog";
import { GenerateNowDialog } from "@/components/GenerateNowDialog";
import { ScheduleReportDialog } from "@/components/ScheduleReportDialog";
import { PDFViewerDialog } from "@/components/PDFViewerDialog";
import { apiClient } from "@/services/api";
import { useDomainStore } from "@/stores/domainStore";
import {
  FileText,
  Plus,
  Download,
  Calendar,
  Eye,
  Share2,
  Settings,
  Loader2,
  Table,
  Presentation,
  Trash2
} from "lucide-react";
import { getFaviconUrl, handleFaviconError } from "@/utils/faviconHelper";

const Reports = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { selectedDomain } = useDomainStore();
  const [createReportDialogOpen, setCreateReportDialogOpen] = useState(false);
  const [previewDialogOpen, setPreviewDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [generateNowDialogOpen, setGenerateNowDialogOpen] = useState(false);
  const [scheduleDialogOpen, setScheduleDialogOpen] = useState(false);
  const [pdfViewerOpen, setPdfViewerOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedReport, setSelectedReport] = useState<any>(null);
  const [viewingReportId, setViewingReportId] = useState<number | null>(null);
  const [reportToDelete, setReportToDelete] = useState<number | null>(null);

  // Get domain ID for filtering
  const domainId = selectedDomain?.id;

  console.log('[Reports] Selected domain:', selectedDomain?.name, 'ID:', domainId);

  // Invalidate queries when domain changes
  useEffect(() => {
    if (domainId) {
      console.log('[Reports] Domain changed to', domainId, '- invalidating queries');
      queryClient.invalidateQueries({ queryKey: ['scheduledReports'] });
      queryClient.invalidateQueries({ queryKey: ['generatedReports'] });
    }
  }, [domainId, queryClient]);

  // Fetch report templates
  const { data: templates = [], isLoading: templatesLoading } = useQuery({
    queryKey: ['reportTemplates'],
    queryFn: () => apiClient.getReportTemplates(),
  });

  // Fetch scheduled reports (filtered by domain)
  const { data: scheduledReports = [], isLoading: scheduledLoading } = useQuery({
    queryKey: ['scheduledReports', domainId],
    queryFn: () => apiClient.getScheduledReports(domainId ? { domain_id: domainId } : {}),
    enabled: !!domainId,
  });

  // Fetch generated reports (filtered by domain)
  const { data: generatedReports = [], isLoading: generatedLoading } = useQuery({
    queryKey: ['generatedReports', domainId],
    queryFn: () => apiClient.getGeneratedReports(domainId ? { domain_id: domainId } : {}),
    enabled: !!domainId,
  });

  // Delete scheduled report mutation
  const deleteReportMutation = useMutation({
    mutationFn: (id: number) => apiClient.deleteScheduledReport(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scheduledReports'] });
      toast({
        title: "Report Deleted",
        description: "The scheduled report has been deleted successfully.",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Error",
        description: error.message || "Failed to delete report",
        variant: "destructive",
      });
    },
  });

  // Pause report mutation
  const pauseReportMutation = useMutation({
    mutationFn: (id: number) => apiClient.pauseScheduledReport(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scheduledReports'] });
      toast({
        title: "Report Paused",
        description: "The scheduled report has been paused.",
      });
    },
  });

  // Resume report mutation
  const resumeReportMutation = useMutation({
    mutationFn: (id: number) => apiClient.resumeScheduledReport(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scheduledReports'] });
      toast({
        title: "Report Resumed",
        description: "The scheduled report has been resumed.",
      });
    },
  });

  const handleManageTemplates = () => {
    toast({
      title: "Opening Template Manager",
      description: "Loading report template settings...",
    });
  };

  const handleCreateReport = () => {
    setCreateReportDialogOpen(true);
  };

  const handleGenerateNow = () => {
    setGenerateNowDialogOpen(true);
  };

  const handleScheduleReport = () => {
    setScheduleDialogOpen(true);
  };

  const handleAddScheduledReport = () => {
    // Invalidate queries to refresh the list
    queryClient.invalidateQueries({ queryKey: ['scheduledReports'] });
  };

  const handleUpdateReport = () => {
    // Invalidate queries to refresh the list
    queryClient.invalidateQueries({ queryKey: ['scheduledReports'] });
  };

  const handleDownloadAll = async () => {
    if (!domainId) {
      toast({
        title: "No Domain Selected",
        description: "Please select a domain first.",
        variant: "destructive",
      });
      return;
    }

    if (generatedReports.length === 0) {
      toast({
        title: "No Reports",
        description: "No generated reports available to download.",
        variant: "destructive",
      });
      return;
    }

    try {
      toast({
        title: "Preparing Download",
        description: "Creating ZIP file with all reports...",
      });

      // Get all report IDs for the current domain
      const reportIds = generatedReports.map((r: any) => r.id);
      await apiClient.downloadAllReports(reportIds, domainId);

      toast({
        title: "Download Started",
        description: "Your reports ZIP file is downloading.",
      });
    } catch (error: any) {
      toast({
        title: "Download Failed",
        description: error.message || "Failed to download reports. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleShareReport = () => {
    toast({
      title: "Coming Soon",
      description: "Report sharing feature will be available soon.",
    });
  };

  const handlePreview = (report: any) => {
    setSelectedReport(report);
    setPreviewDialogOpen(true);
  };

  const handleEdit = (report: any) => {
    setSelectedReport(report);
    setEditDialogOpen(true);
  };

  const handleRunNow = async (report: any) => {
    try {
      await apiClient.generateReport({
        domain_id: report.domain,
        template_id: report.template,
        sections: report.sections || [],
        format: report.formats?.[0] || 'PDF',
        data_period_days: 30,
      });

      queryClient.invalidateQueries({ queryKey: ['generatedReports'] });

      toast({
        title: "Report Generation Started",
        description: `Generating ${report.name}...`,
      });
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to generate report",
        variant: "destructive",
      });
    }
  };

  const handleView = (report: any) => {
    setSelectedReport(report);
    setPreviewDialogOpen(true);
  };

  const handleDownload = async (reportId: number) => {
    try {
      await apiClient.downloadReport(reportId);
      toast({
        title: "Downloading",
        description: "Report download started...",
      });
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to download report",
        variant: "destructive",
      });
    }
  };

  const handleUseTemplate = (template: any) => {
    // Open create dialog with pre-selected template
    setSelectedReport(template);
    setCreateReportDialogOpen(true);
  };

  const handleViewDocumentation = () => {
    toast({
      title: "Opening Documentation",
      description: "Loading API documentation...",
    });
  };

  const handleGenerateAPIKey = () => {
    toast({
      title: "Generating API Key",
      description: "Creating new API key...",
    });
  };

  const handleToggleStatus = async (report: any) => {
    if (report.status === 'active') {
      pauseReportMutation.mutate(report.id);
    } else {
      resumeReportMutation.mutate(report.id);
    }
  };

  const handleDeleteReport = (reportId: number) => {
    setReportToDelete(reportId);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = () => {
    if (reportToDelete) {
      deleteReportMutation.mutate(reportToDelete);
      setDeleteDialogOpen(false);
      setReportToDelete(null);
    }
  };

  // Helper function to format schedule display
  const formatSchedule = (report: any) => {
    const freq = report.frequency;
    const time = report.schedule_time;
    const day = report.schedule_day;

    if (freq === 'once') return 'One-time';
    if (freq === 'daily') return `Daily at ${time}`;
    if (freq === 'weekly') {
      const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
      return `Weekly on ${days[day]} at ${time}`;
    }
    if (freq === 'monthly') return `Monthly on day ${day} at ${time}`;
    if (freq === 'quarterly') return `Quarterly at ${time}`;
    return freq;
  };

  // Helper function to format file size
  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  // Helper function to format relative time
  const formatRelativeTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) return `${diffMins} minutes ago`;
    if (diffHours < 24) return `${diffHours} hours ago`;
    if (diffDays === 1) return '1 day ago';
    return `${diffDays} days ago`;
  };

  // Helper function to get format icon
  const getFormatIcon = (format: string) => {
    const formatLower = format?.toLowerCase() || '';
    if (formatLower.includes('pdf')) {
      return <FileText className="h-5 w-5 text-primary" />;
    } else if (formatLower.includes('excel') || formatLower.includes('xlsx') || formatLower.includes('xls')) {
      return <Table className="h-5 w-5 text-primary" />;
    } else if (formatLower.includes('powerpoint') || formatLower.includes('pptx') || formatLower.includes('ppt')) {
      return <Presentation className="h-5 w-5 text-primary" />;
    }
    return <FileText className="h-5 w-5 text-primary" />;
  };

  // Helper function to render template thumbnails
  const getTemplateThumbnail = (templateName: string) => {
    switch (templateName) {
      case 'Executive Dashboard':
        return (
          <div className="aspect-[4/3] rounded-lg bg-gradient-to-br from-blue-500/10 via-purple-500/10 to-pink-500/10 overflow-hidden relative">
            <div className="absolute inset-0 p-4">
              {/* Dashboard grid layout */}
              <div className="grid grid-cols-2 gap-2 h-full">
                {/* Top metric cards */}
                <div className="bg-white/80 dark:bg-gray-800/80 rounded p-2 flex flex-col justify-between">
                  <div className="h-1.5 w-8 bg-blue-500 rounded"></div>
                  <div className="space-y-1">
                    <div className="h-5 w-12 bg-blue-500/20 rounded"></div>
                    <div className="h-1 w-full bg-gray-300 dark:bg-gray-600 rounded"></div>
                  </div>
                </div>
                <div className="bg-white/80 dark:bg-gray-800/80 rounded p-2 flex flex-col justify-between">
                  <div className="h-1.5 w-8 bg-purple-500 rounded"></div>
                  <div className="space-y-1">
                    <div className="h-5 w-12 bg-purple-500/20 rounded"></div>
                    <div className="h-1 w-full bg-gray-300 dark:bg-gray-600 rounded"></div>
                  </div>
                </div>
                {/* Chart area */}
                <div className="col-span-2 bg-white/80 dark:bg-gray-800/80 rounded p-2">
                  <div className="flex items-end justify-between h-full gap-1">
                    <div className="w-full bg-gradient-to-t from-blue-500 to-blue-300 rounded-t" style={{ height: '60%' }}></div>
                    <div className="w-full bg-gradient-to-t from-purple-500 to-purple-300 rounded-t" style={{ height: '80%' }}></div>
                    <div className="w-full bg-gradient-to-t from-pink-500 to-pink-300 rounded-t" style={{ height: '45%' }}></div>
                    <div className="w-full bg-gradient-to-t from-blue-500 to-blue-300 rounded-t" style={{ height: '70%' }}></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        );

      case 'Detailed Analytics':
        return (
          <div className="aspect-[4/3] rounded-lg bg-gradient-to-br from-green-500/10 via-teal-500/10 to-cyan-500/10 overflow-hidden relative">
            <div className="absolute inset-0 p-4">
              <div className="space-y-2 h-full">
                {/* Header */}
                <div className="h-2 w-20 bg-green-500 rounded"></div>
                {/* Line chart */}
                <div className="bg-white/80 dark:bg-gray-800/80 rounded p-2 flex-1 relative">
                  <svg className="w-full h-full" viewBox="0 0 100 60" preserveAspectRatio="none">
                    <path
                      d="M 0 50 Q 10 45, 20 40 T 40 35 T 60 30 T 80 25 L 100 20"
                      fill="none"
                      stroke="rgb(34, 197, 94)"
                      strokeWidth="2"
                      vectorEffect="non-scaling-stroke"
                    />
                    <path
                      d="M 0 55 Q 10 52, 20 48 T 40 45 T 60 42 T 80 38 L 100 35"
                      fill="none"
                      stroke="rgb(20, 184, 166)"
                      strokeWidth="2"
                      vectorEffect="non-scaling-stroke"
                    />
                  </svg>
                </div>
                {/* Data rows */}
                <div className="space-y-1.5">
                  <div className="flex items-center gap-1">
                    <div className="h-1.5 w-1.5 bg-green-500 rounded-full"></div>
                    <div className="h-1.5 flex-1 bg-gray-300 dark:bg-gray-600 rounded"></div>
                    <div className="h-1.5 w-6 bg-green-500/30 rounded"></div>
                  </div>
                  <div className="flex items-center gap-1">
                    <div className="h-1.5 w-1.5 bg-teal-500 rounded-full"></div>
                    <div className="h-1.5 flex-1 bg-gray-300 dark:bg-gray-600 rounded"></div>
                    <div className="h-1.5 w-6 bg-teal-500/30 rounded"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        );

      case 'Competitor Focus':
        return (
          <div className="aspect-[4/3] rounded-lg bg-gradient-to-br from-orange-500/10 via-red-500/10 to-rose-500/10 overflow-hidden relative">
            <div className="absolute inset-0 p-4">
              <div className="h-full flex flex-col justify-between">
                {/* Title */}
                <div className="h-2 w-16 bg-orange-500 rounded"></div>
                {/* Comparison bars */}
                <div className="space-y-2 flex-1 flex flex-col justify-center">
                  {/* Bar 1 - You */}
                  <div className="space-y-0.5">
                    <div className="flex items-center justify-between">
                      <div className="h-1 w-8 bg-gray-400 dark:bg-gray-600 rounded"></div>
                      <div className="h-1 w-4 bg-orange-500/40 rounded"></div>
                    </div>
                    <div className="h-3 bg-gradient-to-r from-orange-500 to-orange-400 rounded" style={{ width: '85%' }}></div>
                  </div>
                  {/* Bar 2 - Competitor 1 */}
                  <div className="space-y-0.5">
                    <div className="flex items-center justify-between">
                      <div className="h-1 w-8 bg-gray-400 dark:bg-gray-600 rounded"></div>
                      <div className="h-1 w-4 bg-red-500/40 rounded"></div>
                    </div>
                    <div className="h-3 bg-gradient-to-r from-red-500 to-red-400 rounded" style={{ width: '65%' }}></div>
                  </div>
                  {/* Bar 3 - Competitor 2 */}
                  <div className="space-y-0.5">
                    <div className="flex items-center justify-between">
                      <div className="h-1 w-8 bg-gray-400 dark:bg-gray-600 rounded"></div>
                      <div className="h-1 w-4 bg-rose-500/40 rounded"></div>
                    </div>
                    <div className="h-3 bg-gradient-to-r from-rose-500 to-rose-400 rounded" style={{ width: '50%' }}></div>
                  </div>
                </div>
                {/* Legend */}
                <div className="flex gap-2">
                  <div className="flex items-center gap-1">
                    <div className="h-1.5 w-1.5 bg-orange-500 rounded-full"></div>
                    <div className="h-1 w-6 bg-gray-300 dark:bg-gray-600 rounded"></div>
                  </div>
                  <div className="flex items-center gap-1">
                    <div className="h-1.5 w-1.5 bg-red-500 rounded-full"></div>
                    <div className="h-1 w-6 bg-gray-300 dark:bg-gray-600 rounded"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        );

      case 'Content Strategy':
        return (
          <div className="aspect-[4/3] rounded-lg bg-gradient-to-br from-violet-500/10 via-indigo-500/10 to-blue-500/10 overflow-hidden relative">
            <div className="absolute inset-0 p-4">
              <div className="h-full flex flex-col gap-2">
                {/* Header */}
                <div className="h-2 w-16 bg-violet-500 rounded"></div>
                {/* Content cards */}
                <div className="grid grid-cols-2 gap-2 flex-1">
                  {/* Card 1 - Document with citation */}
                  <div className="bg-white/80 dark:bg-gray-800/80 rounded p-2 space-y-1">
                    <div className="flex items-center gap-1">
                      <div className="h-1.5 w-1.5 bg-violet-500 rounded-full"></div>
                      <div className="h-1 flex-1 bg-gray-300 dark:bg-gray-600 rounded"></div>
                    </div>
                    <div className="space-y-0.5">
                      <div className="h-0.5 w-full bg-gray-300 dark:bg-gray-600 rounded"></div>
                      <div className="h-0.5 w-3/4 bg-gray-300 dark:bg-gray-600 rounded"></div>
                      <div className="h-0.5 w-full bg-gray-300 dark:bg-gray-600 rounded"></div>
                    </div>
                    <div className="h-1 w-10 bg-violet-500/30 rounded"></div>
                  </div>
                  {/* Card 2 - Keyword cloud */}
                  <div className="bg-white/80 dark:bg-gray-800/80 rounded p-2 flex flex-wrap gap-1 content-start">
                    <div className="h-1.5 w-6 bg-indigo-500/40 rounded"></div>
                    <div className="h-1.5 w-8 bg-violet-500/40 rounded"></div>
                    <div className="h-1.5 w-5 bg-blue-500/40 rounded"></div>
                    <div className="h-1.5 w-7 bg-indigo-500/40 rounded"></div>
                    <div className="h-1.5 w-6 bg-violet-500/40 rounded"></div>
                    <div className="h-1.5 w-9 bg-blue-500/40 rounded"></div>
                  </div>
                  {/* Card 3 - Pie chart */}
                  <div className="bg-white/80 dark:bg-gray-800/80 rounded p-2 flex items-center justify-center">
                    <div className="relative w-12 h-12">
                      <svg className="w-full h-full transform -rotate-90" viewBox="0 0 32 32">
                        <circle r="16" cx="16" cy="16" fill="transparent" stroke="rgb(139, 92, 246)" strokeWidth="32" strokeDasharray="60 100" />
                        <circle r="16" cx="16" cy="16" fill="transparent" stroke="rgb(99, 102, 241)" strokeWidth="32" strokeDasharray="40 100" strokeDashoffset="-60" />
                      </svg>
                    </div>
                  </div>
                  {/* Card 4 - List with metrics */}
                  <div className="bg-white/80 dark:bg-gray-800/80 rounded p-2 space-y-1">
                    <div className="flex items-center justify-between">
                      <div className="h-1 w-8 bg-gray-300 dark:bg-gray-600 rounded"></div>
                      <div className="h-1 w-3 bg-indigo-500 rounded"></div>
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="h-1 w-10 bg-gray-300 dark:bg-gray-600 rounded"></div>
                      <div className="h-1 w-3 bg-violet-500 rounded"></div>
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="h-1 w-6 bg-gray-300 dark:bg-gray-600 rounded"></div>
                      <div className="h-1 w-3 bg-blue-500 rounded"></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        );

      default:
        return (
          <div className="aspect-[4/3] rounded-lg bg-gradient-to-br from-primary/10 to-secondary/10 flex items-center justify-center">
            <FileText className="h-12 w-12 text-muted-foreground" />
          </div>
        );
    }
  };

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Custom Reports</h1>
          <p className="text-muted-foreground mt-2">
            Generate and automate branded reports
          </p>
        </div>
        <div className="flex gap-3">
          <Button onClick={() => navigate('/reports/create-template')}>
            <Plus className="h-4 w-4 mr-2" />
            Create Template
          </Button>
        </div>
      </div>

      {/* Quick Actions - Hidden for now */}
      {/* <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Button variant="outline" className="h-24 flex flex-col gap-2" onClick={handleGenerateNow}>
          <FileText className="h-6 w-6" />
          <span className="font-medium">Generate Now</span>
        </Button>
        <Button variant="outline" className="h-24 flex flex-col gap-2" onClick={handleScheduleReport}>
          <Calendar className="h-6 w-6" />
          <span className="font-medium">Schedule Report</span>
        </Button>
        <Button variant="outline" className="h-24 flex flex-col gap-2" onClick={handleDownloadAll}>
          <Download className="h-6 w-6" />
          <span className="font-medium">Download All</span>
        </Button>
        <Button variant="outline" className="h-24 flex flex-col gap-2" onClick={handleShareReport}>
          <Share2 className="h-6 w-6" />
          <span className="font-medium">Share Report</span>
        </Button>
      </div> */}

      {/* Scheduled Reports */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-6">Scheduled Reports</h3>
        {scheduledReports.length === 0 ? (
          <div className="text-center py-12">
            <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <p className="text-muted-foreground mb-4">No scheduled reports yet</p>
            <Button onClick={handleScheduleReport}>
              <Plus className="h-4 w-4 mr-2" />
              Schedule Your First Report
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            {scheduledReports.map((report: any) => (
              <div key={report.id} className="p-4 rounded-lg border border-border hover:border-primary transition-all duration-300">
                <div className="flex items-center gap-4">
                  {/* Favicon */}
                  <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                    <img
                      src={getFaviconUrl(report.domain_url || selectedDomain?.url || '', 64)}
                      alt="Domain favicon"
                      className="h-6 w-6"
                      onError={(e) => handleFaviconError(e, report.domain_url || selectedDomain?.url || '', selectedDomain?.name || '', 64)}
                    />
                  </div>

                  {/* Report Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="font-medium text-sm truncate">{report.name}</h4>
                      {report.template_name && (
                        <Badge variant="outline" className="text-xs flex-shrink-0">
                          {report.template_name}
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                      <span>{formatSchedule(report)}</span>
                      {report.next_run_at && (
                        <span>Next: {new Date(report.next_run_at).toLocaleDateString()}</span>
                      )}
                      {report.formats && (
                        <span>Format: {report.formats.join(', ')}</span>
                      )}
                    </div>
                  </div>

                  {/* Status Badge */}
                  <Badge variant={report.status === "active" ? "default" : "secondary"} className="text-xs flex-shrink-0">
                    {report.status}
                  </Badge>

                  {/* Actions */}
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDeleteReport(report.id)}
                      className="text-destructive hover:text-destructive hover:bg-destructive/10"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Recent Reports - Hidden for now */}
      {/* <Card className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold">Recent Reports</h3>
          <Button variant="outline" size="sm">View All</Button>
        </div>
        {generatedReports.length === 0 ? (
          <div className="text-center py-12">
            <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <p className="text-muted-foreground mb-4">No generated reports yet</p>
            <Button onClick={handleGenerateNow}>
              <Plus className="h-4 w-4 mr-2" />
              Generate Your First Report
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {generatedReports.slice(0, 8).map((report: any) => (
              <div key={report.id} className="p-4 rounded-lg border border-border hover:border-primary transition-all duration-300">
                <div className="flex items-start justify-between mb-3">
                  <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                    {getFormatIcon(report.format)}
                  </div>
                  <Badge variant="secondary" className="text-xs">{report.format}</Badge>
                </div>
                <h4 className="font-medium text-sm mb-2 line-clamp-2">{report.name}</h4>
                <div className="space-y-1 text-xs text-muted-foreground mb-3">
                  <p>{formatRelativeTime(report.generated_at)}</p>
                  <p>
                    {report.page_count ? `${report.page_count} pages` : 'N/A'} •{' '}
                    {report.file_size ? formatFileSize(report.file_size) : 'N/A'}
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    className="flex-1"
                    onClick={() => handleView(report)}
                  >
                    <Eye className="h-3 w-3 mr-1" />
                    View
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="flex-1"
                    onClick={() => handleDownload(report.id)}
                    disabled={!report.file_path}
                  >
                    <Download className="h-3 w-3 mr-1" />
                    Download
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card> */}

      {/* Report Templates */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold">Report Templates</h3>
          <Button variant="outline" size="sm" onClick={() => navigate('/reports/create-template')}>
            <Plus className="h-4 w-4 mr-2" />
            Create Custom Template
          </Button>
        </div>
        {templatesLoading ? (
          <div className="text-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground mx-auto mb-4" />
            <p className="text-muted-foreground">Loading templates...</p>
          </div>
        ) : templates.length === 0 ? (
          <div className="text-center py-12">
            <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <p className="text-muted-foreground mb-4">No templates created yet</p>
            <Button onClick={() => navigate('/reports/create-template')}>
              <Plus className="h-4 w-4 mr-2" />
              Create Your First Template
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {templates.map((template: any) => (
              <div key={template.id} className="p-4 rounded-lg border border-border hover:border-primary transition-all duration-300">
                {getTemplateThumbnail(template.name)}
                <div className="mt-4 space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <h4 className="font-semibold text-sm">{template.name}</h4>
                    {template.template_type === 'custom' && (
                      <Badge variant="secondary" className="text-xs">Custom</Badge>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground line-clamp-2">{template.description}</p>
                  {template.template_type === 'custom' && template.grid_rows && (
                    <span className="text-xs text-muted-foreground">
                      {template.grid_rows.length} {template.grid_rows.length === 1 ? 'row' : 'rows'}
                    </span>
                  )}
                  {template.template_type === 'predefined' && template.sections && (
                    <span className="text-xs text-muted-foreground">
                      {template.sections.length} {template.sections.length === 1 ? 'section' : 'sections'}
                    </span>
                  )}
                </div>
                <div className="mt-4 flex gap-2">
                  <Button
                    className="flex-1"
                    size="sm"
                    variant="outline"
                    onClick={() => handlePreview({
                      id: template.id,
                      name: template.name,
                      description: template.description,
                      format: ["PDF"],
                      schedule: "",
                      lastGenerated: "",
                      recipients: [],
                      status: "active",
                      template_type: template.template_type,
                      grid_rows: template.grid_rows
                    })}
                  >
                    <Eye className="h-3 w-3 mr-1" />
                    Preview
                  </Button>
                  {template.template_type === 'custom' && (
                    <Button
                      className="flex-1"
                      size="sm"
                      onClick={() => navigate(`/reports/create-template?template_id=${template.id}`)}
                    >
                      <Settings className="h-3 w-3 mr-1" />
                      Edit
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* API Access - Commented out for now */}
      {/* <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">API Access</h3>
        <p className="text-sm text-muted-foreground mb-4">
          Integrate visibility data directly into your systems with our REST API
        </p>
        <div className="space-y-4">
          <div className="p-4 rounded-lg bg-muted/50">
            <p className="text-sm font-medium mb-2">API Endpoint</p>
            <code className="text-xs bg-background px-3 py-2 rounded block">
              https://api.aivis ibilitypro.com/v1/reports
            </code>
          </div>
          <div className="flex gap-3">
            <Button variant="outline" onClick={handleViewDocumentation}>
              <FileText className="h-4 w-4 mr-2" />
              View Documentation
            </Button>
            <Button variant="outline" onClick={handleGenerateAPIKey}>Generate API Key</Button>
          </div>
        </div>
      </Card> */}

      {/* Dialogs */}
      <CreateReportDialog
        open={createReportDialogOpen}
        onOpenChange={setCreateReportDialogOpen}
      />
      <ReportPreviewDialog
        open={previewDialogOpen}
        onOpenChange={setPreviewDialogOpen}
        report={selectedReport}
      />
      <EditReportDialog
        open={editDialogOpen}
        onOpenChange={setEditDialogOpen}
        report={selectedReport}
        onSave={handleUpdateReport}
      />
      <GenerateNowDialog
        open={generateNowDialogOpen}
        onOpenChange={setGenerateNowDialogOpen}
      />
      <ScheduleReportDialog
        open={scheduleDialogOpen}
        onOpenChange={setScheduleDialogOpen}
        onSchedule={handleAddScheduledReport}
      />
      <PDFViewerDialog
        open={pdfViewerOpen}
        onOpenChange={setPdfViewerOpen}
        reportId={viewingReportId}
        reportName={selectedReport?.name || "Report"}
      />

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title="Delete Scheduled Report"
        description="Are you sure you want to delete this scheduled report? This action cannot be undone."
        confirmText="Delete"
        onConfirm={confirmDelete}
        variant="destructive"
      />
    </div>
  );
};

export default Reports;
