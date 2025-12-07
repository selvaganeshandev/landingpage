import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card } from "@/components/ui/card";
import { FileText, Download, Share2, Loader2, TrendingUp, Smile, Meh, Frown } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useDomainStore } from "@/stores/domainStore";
import { getFaviconUrl, handleFaviconError } from "@/utils/faviconHelper";
import { apiClient } from "@/services/api";
import { useQuery } from "@tanstack/react-query";
import { ExecutiveDashboardTemplate } from "@/components/report-templates/ExecutiveDashboardTemplate";
import { DetailedAnalyticsTemplate } from "@/components/report-templates/DetailedAnalyticsTemplate";
import { CompetitorFocusTemplate } from "@/components/report-templates/CompetitorFocusTemplate";
import { ContentStrategyTemplate } from "@/components/report-templates/ContentStrategyTemplate";
import { useEffect, useState, useRef } from "react";
import html2canvas from "html2canvas";
import jsPDF from "jspdf";
import {
  LineChart as RechartsLineChart,
  BarChart as RechartsBarChart,
  PieChart as RechartsPieChart,
  Line,
  Bar,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface ReportPreviewDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  report: {
    id: number;
    name: string;
    description: string;
    format: string[];
    domain?: number;
    data_period_start?: string;
    data_period_end?: string;
    template_type?: string;
    grid_rows?: any[];
  } | null;
}

// Dummy data for previews
const dummyLineData = [
  { month: "Jan", mentions: 45 },
  { month: "Feb", mentions: 52 },
  { month: "Mar", mentions: 61 },
  { month: "Apr", mentions: 58 },
  { month: "May", mentions: 70 },
  { month: "Jun", mentions: 85 },
];

const dummyBarData = [
  { platform: "ChatGPT", mentions: 120 },
  { platform: "Claude", mentions: 95 },
  { platform: "Gemini", mentions: 78 },
  { platform: "Perplexity", mentions: 65 },
];

const dummyPieData = [
  { name: "Positive", value: 65, color: "#22c55e" },
  { name: "Neutral", value: 25, color: "#94a3b8" },
  { name: "Negative", value: 10, color: "#ef4444" },
];

export const ReportPreviewDialog = ({ open, onOpenChange, report }: ReportPreviewDialogProps) => {
  const { toast } = useToast();
  const { selectedDomain } = useDomainStore();
  const [reportData, setReportData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const reportContentRef = useRef<HTMLDivElement>(null);

  // Fetch domain statistics - same as ReportBuilder
  const { data: domainStats, isLoading: isLoadingStats } = useQuery({
    queryKey: ['domainStats', selectedDomain?.id],
    queryFn: async () => {
      if (!selectedDomain?.id) return null;

      // Fetch prompts, prompt groups, and dashboard summary (for platforms)
      const [prompts, promptGroups, dashboardSummary] = await Promise.all([
        apiClient.getPrompts({ domain_id: selectedDomain.id }),
        apiClient.getPromptGroups({ domain_id: selectedDomain.id }),
        apiClient.getDashboardSummary({ domain_id: String(selectedDomain.id), days: 30 })
      ]);

      // Handle prompts response - could be array or paginated object
      const promptsData = Array.isArray(prompts) ? prompts : prompts?.results || prompts?.prompts || [];

      // Extract LLMs from dashboard summary platforms
      const llms = new Set<string>();
      if (Array.isArray(dashboardSummary?.platforms)) {
        dashboardSummary.platforms.forEach((platform: any) => {
          if (platform.platform) {
            llms.add(platform.platform);
          }
        });
      }

      // Handle prompt groups response - the API returns { total_count, groups }
      const groupsCount = Array.isArray(promptGroups)
        ? promptGroups.length
        : (promptGroups?.groups?.length || promptGroups?.results?.length || 0);

      return {
        totalPrompts: promptsData.length,
        totalPromptGroups: groupsCount,
        trackedLLMs: Array.from(llms),
        lastUpdated: new Date().toISOString()
      };
    },
    enabled: !!selectedDomain?.id && open,
    refetchOnMount: true,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });

  useEffect(() => {
    if (open && report) {
      console.log('[ReportPreviewDialog] Report object:', report);

      // Skip data fetching for custom templates - they use grid_rows
      if (report.template_type === 'custom') {
        setReportData(null);
        setLoading(false);
        return;
      }

      // Get domain ID - it might be in different fields
      const domainId = report.domain || (report as any).domain_id;

      console.log('[ReportPreviewDialog] Domain ID:', domainId);

      if (!domainId) {
        console.warn('[ReportPreviewDialog] No domain ID found in report');
        setReportData(null);
        return;
      }

      // Determine report type from name or template
      const reportNameLower = report.name.toLowerCase();
      const templateNameLower = ((report as any).template_name || '').toLowerCase();

      let reportType = 'Executive Dashboard'; // default
      if (reportNameLower.includes('competitor') || templateNameLower.includes('competitor')) {
        reportType = 'Competitor Focus';
      } else if (reportNameLower.includes('content') || reportNameLower.includes('strategy') ||
                 templateNameLower.includes('content') || templateNameLower.includes('strategy')) {
        reportType = 'Content Strategy';
      } else if (reportNameLower.includes('detailed') || reportNameLower.includes('analytics') ||
                 templateNameLower.includes('detailed') || templateNameLower.includes('analytics')) {
        reportType = 'Detailed Analytics';
      } else if (reportNameLower.includes('executive') || templateNameLower.includes('executive')) {
        reportType = 'Executive Dashboard';
      }

      console.log('[ReportPreviewDialog] Detected report type:', reportType);

      // Fetch report data from the backend using the new preview-data endpoint
      const fetchReportData = async () => {
        setLoading(true);
        try {
          const token = localStorage.getItem('access_token');
          const url = `http://localhost:8000/reports/preview-data/?domain_id=${domainId}&report_type=${encodeURIComponent(reportType)}&days=30`;
          console.log('[ReportPreviewDialog] Fetching from:', url);

          const response = await fetch(url, {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          });

          if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || 'Failed to fetch report data');
          }

          const data = await response.json();
          console.log('[ReportPreviewDialog] Fetched report data:', data);
          setReportData(data);
        } catch (error) {
          console.error('Error fetching report data:', error);
          toast({
            title: "Error",
            description: "Failed to load report data",
            variant: "destructive",
          });
        } finally {
          setLoading(false);
        }
      };

      fetchReportData();
    }
  }, [open, report]);

  if (!report) return null;

  const handleDownload = async (format: string) => {
    if (format.toLowerCase() === 'pdf') {
      await handleDownloadPdf();
    } else {
      toast({
        title: "Downloading Report",
        description: `Downloading ${report.name} as ${format}...`,
      });
    }
  };

  const handleDownloadPdf = async () => {
    if (!reportContentRef.current) {
      toast({
        title: "Error",
        description: "Report content not available",
        variant: "destructive",
      });
      return;
    }

    setDownloadingPdf(true);
    try {
      // Get the element
      const element = reportContentRef.current;

      // Find the inner content div (the one with max-w-[1200px])
      const innerContent = element.querySelector('[class*="max-w-"]') as HTMLElement;
      const targetElement = innerContent || element;

      // Get the dimensions
      const elementWidth = targetElement.scrollWidth;
      const elementHeight = targetElement.scrollHeight;

      // Create canvas from HTML with high quality
      const canvas = await html2canvas(targetElement, {
        scale: 2, // Higher quality
        useCORS: true,
        logging: false,
        width: elementWidth,
        height: elementHeight,
        windowWidth: elementWidth,
        windowHeight: elementHeight,
        backgroundColor: '#ffffff',
      });

      // Calculate PDF dimensions
      const pageWidth = 210; // A4 width in mm
      const pageHeight = 297; // A4 height in mm

      // Calculate image dimensions maintaining aspect ratio
      const imgWidth = 170; // Content width (leaving margins)
      const imgHeight = (canvas.height * imgWidth) / canvas.width;

      // Center the content horizontally
      const xOffset = (pageWidth - imgWidth) / 2;

      // Create PDF
      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'mm',
        format: 'a4',
      });

      // Add image to PDF - centered
      const imgData = canvas.toDataURL('image/png');

      // If content is too tall, split into multiple pages
      let heightLeft = imgHeight;
      let position = 0;

      pdf.addImage(imgData, 'PNG', xOffset, position, imgWidth, imgHeight);
      heightLeft -= pageHeight;

      while (heightLeft > 0) {
        position = heightLeft - imgHeight;
        pdf.addPage();
        pdf.addImage(imgData, 'PNG', xOffset, position, imgWidth, imgHeight);
        heightLeft -= pageHeight;
      }

      // Download the PDF
      pdf.save(`${report.name}.pdf`);

      toast({
        title: "Success",
        description: "PDF downloaded successfully",
      });
    } catch (error) {
      console.error('Error downloading PDF:', error);
      toast({
        title: "Error",
        description: "Failed to download PDF",
        variant: "destructive",
      });
    } finally {
      setDownloadingPdf(false);
    }
  };

  const handleShare = () => {
    toast({
      title: "Share Report",
      description: "Opening sharing options...",
    });
  };

  // Render widget preview - exactly matching ReportBuilder
  const renderWidgetPreview = (widget: any) => {
    switch (widget.id) {
      case "mentions-chart":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <ResponsiveContainer width="100%" height={200}>
              <RechartsLineChart data={dummyLineData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="mentions" stroke="#3b82f6" strokeWidth={2} />
              </RechartsLineChart>
            </ResponsiveContainer>
          </Card>
        );

      case "sentiment-chart":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <ResponsiveContainer width="100%" height={200}>
              <RechartsPieChart>
                <Pie
                  data={dummyPieData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={(entry) => `${entry.name}: ${entry.value}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {dummyPieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </RechartsPieChart>
            </ResponsiveContainer>
          </Card>
        );

      case "platform-chart":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <ResponsiveContainer width="100%" height={200}>
              <RechartsBarChart data={dummyBarData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="platform" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="mentions" fill="#8b5cf6" />
              </RechartsBarChart>
            </ResponsiveContainer>
          </Card>
        );

      case "total-prompts-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-indigo-500/10 to-indigo-500/5 border-indigo-200">
            <p className="text-sm text-muted-foreground mb-2">Total Prompts</p>
            <p className="text-4xl font-bold text-indigo-600">{domainStats?.totalPrompts || 0}</p>
            <p className="text-sm text-muted-foreground mt-2">Tracked prompts</p>
          </Card>
        );

      case "total-citations-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-blue-500/10 to-blue-500/5 border-blue-200">
            <p className="text-sm text-muted-foreground mb-2">Total Citations</p>
            <p className="text-4xl font-bold text-blue-600">342</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              +18.2% from last month
            </p>
          </Card>
        );

      case "total-mentions-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-cyan-500/10 to-cyan-500/5 border-cyan-200">
            <p className="text-sm text-muted-foreground mb-2">Total Mentions</p>
            <p className="text-4xl font-bold text-cyan-600">1,547</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              +24.5% from last month
            </p>
          </Card>
        );

      case "visibility-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-emerald-500/10 to-emerald-500/5 border-emerald-200">
            <p className="text-sm text-muted-foreground mb-2">Visibility Score</p>
            <p className="text-4xl font-bold text-emerald-600">87.5</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              +6.3% improvement
            </p>
          </Card>
        );

      case "avg-position-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-amber-500/10 to-amber-500/5 border-amber-200">
            <p className="text-sm text-muted-foreground mb-2">Avg Position</p>
            <p className="text-4xl font-bold text-amber-600">2.4</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              -0.3 (improved)
            </p>
          </Card>
        );

      case "positive-sentiment-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-green-500/10 to-green-500/5 border-green-200">
            <p className="text-sm text-muted-foreground mb-2">Positive Sentiment</p>
            <p className="text-4xl font-bold text-green-600">68%</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <Smile className="h-4 w-4" />
              Majority positive
            </p>
          </Card>
        );

      case "neutral-sentiment-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-slate-500/10 to-slate-500/5 border-slate-200">
            <p className="text-sm text-muted-foreground mb-2">Neutral Sentiment</p>
            <p className="text-4xl font-bold text-slate-600">24%</p>
            <p className="text-sm text-muted-foreground mt-2 flex items-center gap-1">
              <Meh className="h-4 w-4" />
              Balanced feedback
            </p>
          </Card>
        );

      case "negative-sentiment-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-red-500/10 to-red-500/5 border-red-200">
            <p className="text-sm text-muted-foreground mb-2">Negative Sentiment</p>
            <p className="text-4xl font-bold text-red-600">8%</p>
            <p className="text-sm text-red-600 mt-2 flex items-center gap-1">
              <Frown className="h-4 w-4" />
              Minimal negative
            </p>
          </Card>
        );

      case "mentions-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-blue-500/10 to-blue-500/5 border-blue-200">
            <p className="text-sm text-muted-foreground mb-2">Total Mentions</p>
            <p className="text-4xl font-bold text-blue-600">1,234</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              +12.5% from last month
            </p>
          </Card>
        );

      case "sentiment-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-green-500/10 to-green-500/5 border-green-200">
            <p className="text-sm text-muted-foreground mb-2">Sentiment Score</p>
            <p className="text-4xl font-bold text-green-600">8.4/10</p>
            <p className="text-sm text-muted-foreground mt-2">Mostly Positive</p>
          </Card>
        );

      case "competitors-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-purple-500/10 to-purple-500/5 border-purple-200">
            <p className="text-sm text-muted-foreground mb-2">Competitors Tracked</p>
            <p className="text-4xl font-bold text-purple-600">8</p>
            <p className="text-sm text-muted-foreground mt-2">Active monitoring</p>
          </Card>
        );

      case "share-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-orange-500/10 to-orange-500/5 border-orange-200">
            <p className="text-sm text-muted-foreground mb-2">Share of Voice</p>
            <p className="text-4xl font-bold text-orange-600">42%</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              +5% increase
            </p>
          </Card>
        );

      case "topics-table":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <div className="overflow-auto">
              <table className="w-full text-sm">
                <thead className="border-b">
                  <tr>
                    <th className="text-left py-2">Topic</th>
                    <th className="text-right py-2">Mentions</th>
                    <th className="text-right py-2">Trend</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b">
                    <td className="py-2">AI Integration</td>
                    <td className="text-right">145</td>
                    <td className="text-right text-green-600">↑ 12%</td>
                  </tr>
                  <tr className="border-b">
                    <td className="py-2">Product Features</td>
                    <td className="text-right">98</td>
                    <td className="text-right text-green-600">↑ 8%</td>
                  </tr>
                  <tr className="border-b">
                    <td className="py-2">Pricing</td>
                    <td className="text-right">76</td>
                    <td className="text-right text-red-600">↓ 3%</td>
                  </tr>
                  <tr>
                    <td className="py-2">Customer Support</td>
                    <td className="text-right">52</td>
                    <td className="text-right text-green-600">↑ 15%</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </Card>
        );

      // Default widget for any other type
      default:
        return (
          <Card className="p-6 bg-muted">
            <p className="text-sm text-muted-foreground">Preview not available</p>
          </Card>
        );
    }
  };

  // Render custom template grid layout
  const renderCustomTemplate = () => {
    if (!report.grid_rows || report.grid_rows.length === 0) {
      return (
        <div className="flex flex-col items-center justify-center py-12">
          <FileText className="h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-muted-foreground">No widgets in this template</p>
        </div>
      );
    }

    const getGridCols = (type: string) => {
      switch (type) {
        case 'single': return 'grid-cols-1';
        case 'double': return 'grid-cols-2';
        case 'triple': return 'grid-cols-3';
        case 'quad': return 'grid-cols-4';
        default: return 'grid-cols-1';
      }
    };

    return (
      <div className="space-y-6 p-8">
        {/* Brand Header */}
        {selectedDomain && (
          <div className="flex items-center gap-4 pb-6 border-b">
            <div className="w-16 h-16 rounded-lg overflow-hidden bg-primary/10 flex items-center justify-center">
              <img
                src={getFaviconUrl(selectedDomain.url, 64)}
                alt={selectedDomain.name}
                className="w-full h-full object-cover"
                onError={(e) => handleFaviconError(e, selectedDomain.url, selectedDomain.name, 64)}
              />
            </div>
            <div>
              <h2 className="text-2xl font-bold">{selectedDomain.name}</h2>
              <p className="text-sm text-muted-foreground">{selectedDomain.url}</p>
            </div>
          </div>
        )}

        {/* Template Header */}
        <div className="mb-8">
          <h2 className="text-3xl font-bold mb-2">{report.name}</h2>
          <p className="text-muted-foreground">{report.description}</p>
          <p className="text-sm text-muted-foreground mt-2">
            Generated on {new Date().toLocaleDateString()}
          </p>
        </div>

        {/* Grid Rows with Widgets */}
        {report.grid_rows.map((row: any, rowIndex: number) => (
          <div key={row.id || rowIndex} className={`grid ${getGridCols(row.type)} gap-4`}>
            {row.slots.map((widget: any, slotIndex: number) => (
              <div key={slotIndex}>
                {widget ? (
                  renderWidgetPreview(widget)
                ) : (
                  <div className="p-6 rounded-lg border border-dashed border-muted-foreground/20">
                    <p className="text-sm text-muted-foreground text-center">Empty slot</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        ))}
      </div>
    );
  };

  // Determine which template to render based on report name or template name
  const renderTemplate = () => {
    if (loading) {
      return (
        <div className="flex flex-col items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary mb-4" />
          <p className="text-muted-foreground">Loading report data...</p>
        </div>
      );
    }

    // Check if it's a custom template
    if (report.template_type === 'custom') {
      return renderCustomTemplate();
    }

    const reportNameLower = report.name.toLowerCase();
    const templateNameLower = ((report as any).template_name || '').toLowerCase();

    console.log('[ReportPreviewDialog] Report name:', reportNameLower);
    console.log('[ReportPreviewDialog] Template name:', templateNameLower);

    // Check both report name and template name
    if (reportNameLower.includes('executive') || templateNameLower.includes('executive')) {
      return <ExecutiveDashboardTemplate data={reportData} />;
    } else if (reportNameLower.includes('detailed') || reportNameLower.includes('analytics') ||
               templateNameLower.includes('detailed') || templateNameLower.includes('analytics')) {
      return <DetailedAnalyticsTemplate data={reportData} />;
    } else if (reportNameLower.includes('competitor') || templateNameLower.includes('competitor')) {
      return <CompetitorFocusTemplate data={reportData} />;
    } else if (reportNameLower.includes('content') || reportNameLower.includes('strategy') ||
               templateNameLower.includes('content') || templateNameLower.includes('strategy')) {
      return <ContentStrategyTemplate data={reportData} />;
    }

    // Default generic template for other reports
    return (
      <div className="space-y-8 p-8">
        <div className="mb-8">
          <h2 className="text-3xl font-bold mb-2">{report.name}</h2>
          <p className="text-muted-foreground">Generated on {new Date().toLocaleDateString()}</p>
        </div>
        <div>
          <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Executive Summary
          </h3>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="p-4 rounded-lg border bg-card">
              <p className="text-sm text-muted-foreground mb-1">Visibility Score</p>
              <p className="text-2xl font-bold">87.5%</p>
              <Badge variant="default" className="mt-2">+5.2%</Badge>
            </div>
            <div className="p-4 rounded-lg border bg-card">
              <p className="text-sm text-muted-foreground mb-1">Total Mentions</p>
              <p className="text-2xl font-bold">1,247</p>
              <Badge variant="default" className="mt-2">+12.3%</Badge>
            </div>
            <div className="p-4 rounded-lg border bg-card">
              <p className="text-sm text-muted-foreground mb-1">Sentiment</p>
              <p className="text-2xl font-bold">Positive</p>
              <Badge variant="default" className="mt-2">92% positive</Badge>
            </div>
          </div>
        </div>
        <div>
          <h3 className="text-xl font-semibold mb-4">Performance Trends</h3>
          <div className="aspect-video rounded-lg border bg-muted/30 flex items-center justify-center">
            <p className="text-muted-foreground">Chart Preview</p>
          </div>
        </div>
      </div>
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl h-[80vh] flex flex-col">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <div>
              <DialogTitle>{report.name}</DialogTitle>
              <p className="text-sm text-muted-foreground mt-1">{report.description}</p>
            </div>
            <div className="flex gap-2">
              {Array.isArray(report.format) ? (
                report.format.map((fmt) => (
                  <Button
                    key={fmt}
                    size="sm"
                    variant="outline"
                    onClick={() => handleDownload(fmt)}
                    disabled={downloadingPdf}
                  >
                    {downloadingPdf && fmt.toLowerCase() === 'pdf' ? (
                      <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                    ) : (
                      <Download className="h-3 w-3 mr-1" />
                    )}
                    {fmt}
                  </Button>
                ))
              ) : (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleDownload(report.format)}
                  disabled={downloadingPdf}
                >
                  {downloadingPdf && report.format.toLowerCase() === 'pdf' ? (
                    <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                  ) : (
                    <Download className="h-3 w-3 mr-1" />
                  )}
                  {report.format}
                </Button>
              )}
              <Button size="sm" variant="outline" onClick={handleShare}>
                <Share2 className="h-3 w-3 mr-1" />
                Share
              </Button>
            </div>
          </div>
        </DialogHeader>

        <ScrollArea className="flex-1">
          <div ref={reportContentRef} className="bg-background">
            {renderTemplate()}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
};
