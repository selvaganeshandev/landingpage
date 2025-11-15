import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { useToast } from "@/hooks/use-toast";
import { CreateReportDialog } from "@/components/CreateReportDialog";
import { ReportPreviewDialog } from "@/components/ReportPreviewDialog";
import { EditReportDialog } from "@/components/EditReportDialog";
import { GenerateNowDialog } from "@/components/GenerateNowDialog";
import { ScheduleReportDialog } from "@/components/ScheduleReportDialog";
import { apiClient } from "@/services/api";
import {
  FileText,
  Plus,
  Download,
  Calendar,
  Eye,
  Share2,
  Clock,
  Settings,
  Loader2
} from "lucide-react";

const Reports = () => {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [createReportDialogOpen, setCreateReportDialogOpen] = useState(false);
  const [previewDialogOpen, setPreviewDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [generateNowDialogOpen, setGenerateNowDialogOpen] = useState(false);
  const [scheduleDialogOpen, setScheduleDialogOpen] = useState(false);
  const [selectedReport, setSelectedReport] = useState<any>(null);

  // Fetch report templates
  const { data: templates = [], isLoading: templatesLoading } = useQuery({
    queryKey: ['reportTemplates'],
    queryFn: () => apiClient.getReportTemplates(),
  });

  // Fetch scheduled reports
  const { data: scheduledReports = [], isLoading: scheduledLoading } = useQuery({
    queryKey: ['scheduledReports'],
    queryFn: () => apiClient.getScheduledReports(),
  });

  // Fetch generated reports
  const { data: generatedReports = [], isLoading: generatedLoading } = useQuery({
    queryKey: ['generatedReports'],
    queryFn: () => apiClient.getGeneratedReports(),
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
    try {
      // Download all generated reports
      for (const report of generatedReports) {
        if (report.file_path) {
          const response = await apiClient.downloadReport(report.id);
          // Handle download (browser will handle file download)
        }
      }
      toast({
        title: "Downloading Reports",
        description: `Downloading ${generatedReports.length} reports...`,
      });
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to download reports",
        variant: "destructive",
      });
    }
  };

  const handleShareReport = () => {
    toast({
      title: "Share Report",
      description: "Opening sharing options...",
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

  const handleDeleteReport = async (reportId: number) => {
    if (confirm('Are you sure you want to delete this scheduled report?')) {
      deleteReportMutation.mutate(reportId);
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

  // Show loading state
  if (templatesLoading || scheduledLoading || generatedLoading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-screen">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-muted-foreground">Loading reports...</p>
        </div>
      </div>
    );
  }

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
          <Button variant="outline" onClick={handleManageTemplates}>
            <Settings className="h-4 w-4 mr-2" />
            Manage Templates
          </Button>
          <Button onClick={handleCreateReport}>
            <Plus className="h-4 w-4 mr-2" />
            Create Report
          </Button>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
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
      </div>

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
          <div className="space-y-4">
            {scheduledReports.map((report: any) => (
              <div key={report.id} className="p-4 rounded-lg border border-border hover:bg-accent/50 transition-colors">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h4 className="font-semibold">{report.name}</h4>
                      <Badge variant={report.status === "active" ? "default" : "secondary"}>
                        {report.status}
                      </Badge>
                      {report.template_name && (
                        <Badge variant="outline" className="text-xs">
                          {report.template_name}
                        </Badge>
                      )}
                    </div>
                    {report.description && (
                      <p className="text-sm text-muted-foreground mb-3">{report.description}</p>
                    )}
                    <div className="flex flex-wrap gap-4 text-sm">
                      <div className="flex items-center gap-2">
                        <Clock className="h-4 w-4 text-muted-foreground" />
                        <span className="text-muted-foreground">{formatSchedule(report)}</span>
                      </div>
                      {report.last_generated_at && (
                        <div className="flex items-center gap-2">
                          <Calendar className="h-4 w-4 text-muted-foreground" />
                          <span className="text-muted-foreground">
                            Last: {formatRelativeTime(report.last_generated_at)}
                          </span>
                        </div>
                      )}
                      {report.next_run_at && (
                        <div className="flex items-center gap-2">
                          <Calendar className="h-4 w-4 text-muted-foreground" />
                          <span className="text-muted-foreground">
                            Next: {new Date(report.next_run_at).toLocaleDateString()}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" onClick={() => handlePreview(report)}>
                      <Eye className="h-3 w-3 mr-1" />
                      Preview
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => handleEdit(report)}>
                      Edit
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => handleRunNow(report)}
                      disabled={report.status === 'paused'}
                    >
                      Run Now
                    </Button>
                  </div>
                </div>
                <div className="flex items-center gap-4 pt-3 border-t border-border">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">Formats:</span>
                    {report.formats && report.formats.map((fmt: string) => (
                      <Badge key={fmt} variant="outline" className="text-xs">
                        {fmt}
                      </Badge>
                    ))}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">
                      Recipients: {report.recipients?.length || 0}
                    </span>
                  </div>
                  <div className="ml-auto flex gap-2">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleToggleStatus(report)}
                    >
                      {report.status === 'active' ? 'Pause' : 'Resume'}
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDeleteReport(report.id)}
                    >
                      Delete
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Recent Reports */}
      <Card className="p-6">
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
              <div key={report.id} className="p-4 rounded-lg border border-border hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between mb-3">
                  <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                    <FileText className="h-5 w-5 text-primary" />
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
      </Card>

      {/* Templates */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-6">Report Templates</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {templates.map((template: any) => (
            <div key={template.id} className="p-4 rounded-lg border border-border hover:shadow-md transition-shadow">
              <div className="aspect-[4/3] rounded-lg bg-gradient-to-br from-primary/10 to-secondary/10 mb-4 flex items-center justify-center">
                <FileText className="h-12 w-12 text-muted-foreground" />
              </div>
              <h4 className="font-semibold mb-2">{template.name}</h4>
              <p className="text-sm text-muted-foreground mb-3">{template.description}</p>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs text-muted-foreground">
                  {template.sections?.length || 0} sections
                </span>
                <Button
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
                    status: "active"
                  })}
                >
                  <Eye className="h-3 w-3 mr-1" />
                  Preview
                </Button>
              </div>
              <Button
                className="w-full"
                size="sm"
                onClick={() => handleUseTemplate(template)}
              >
                Use Template
              </Button>
            </div>
          ))}
        </div>
      </Card>

      {/* API Access */}
      <Card className="p-6">
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
      </Card>

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
    </div>
  );
};

export default Reports;
