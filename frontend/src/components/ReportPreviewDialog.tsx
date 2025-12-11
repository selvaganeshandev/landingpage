import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card } from "@/components/ui/card";
import { FileText, Download, Share2, Loader2, TrendingUp, Smile, Meh, Frown, Link2, Activity, AlertCircle } from "lucide-react";
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
  AreaChart,
  Line,
  Bar,
  Pie,
  Area,
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
    // Check if this is a custom template with widgets
    if (report.template_type === 'custom' && report.grid_rows) {
      // Use backend API for custom templates with real data
      await handleDownloadCustomTemplatePdf();
    } else {
      // Use html2canvas for predefined templates (legacy)
      await handleDownloadHtmlPdf();
    }
  };

  const handleDownloadCustomTemplatePdf = async () => {
    if (!selectedDomain) {
      toast({
        title: "Error",
        description: "No domain selected",
        variant: "destructive",
      });
      return;
    }

    setDownloadingPdf(true);
    try {
      const token = localStorage.getItem('access_token');

      // Calculate date range (last 30 days by default)
      const endDate = new Date();
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - 30);

      const requestBody = {
        domain_id: selectedDomain.id,
        template_name: report.name,
        grid_rows: report.grid_rows,
        html_template: report.html_template,  // Send saved HTML template
        css_template: report.css_template,    // Send saved CSS
        start_date: startDate.toISOString().split('T')[0], // YYYY-MM-DD format
        end_date: endDate.toISOString().split('T')[0],
      };

      const response = await fetch('http://localhost:8000/reports/generate-custom-pdf/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Failed to generate PDF' }));
        throw new Error(errorData.error || 'Failed to generate PDF');
      }

      // Download the PDF
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${report.name}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast({
        title: "Success",
        description: "PDF with real data downloaded successfully",
      });
    } catch (error) {
      console.error('Error downloading PDF:', error);
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to download PDF",
        variant: "destructive",
      });
    } finally {
      setDownloadingPdf(false);
    }
  };

  const handleDownloadHtmlPdf = async () => {
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

  // Render widget preview - matching ReportBuilder
  const renderWidgetPreview = (widget: any) => {
    switch (widget.id) {
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

      case "competitors-table":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <div className="overflow-auto">
              <table className="w-full text-sm">
                <thead className="border-b">
                  <tr>
                    <th className="text-left py-2">Competitor</th>
                    <th className="text-right py-2">Mentions</th>
                    <th className="text-right py-2">Share</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b">
                    <td className="py-2">Competitor A</td>
                    <td className="text-right">234</td>
                    <td className="text-right">28%</td>
                  </tr>
                  <tr className="border-b">
                    <td className="py-2">Competitor B</td>
                    <td className="text-right">189</td>
                    <td className="text-right">23%</td>
                  </tr>
                  <tr>
                    <td className="py-2">Competitor C</td>
                    <td className="text-right">156</td>
                    <td className="text-right">19%</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </Card>
        );

      case "summary-text":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <div className="space-y-3 text-sm text-muted-foreground">
              <p>
                This month showed strong performance across all AI platforms with a 12.5% increase in
                total mentions compared to the previous period.
              </p>
              <p>
                Sentiment remains predominantly positive at 65%, with ChatGPT leading in mention volume
                at 120 mentions, followed by Claude at 95 mentions.
              </p>
              <p>
                Key topics driving visibility include AI Integration and Product Features, while
                maintaining a healthy 42% share of voice in the competitive landscape.
              </p>
            </div>
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

      // New Information Metrics
      case "engagement-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-violet-500/10 to-violet-500/5 border-violet-200">
            <p className="text-sm text-muted-foreground mb-2">Engagement Score</p>
            <p className="text-4xl font-bold text-violet-600">92.3</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              +8.1% improvement
            </p>
          </Card>
        );

      case "mention-rate-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-sky-500/10 to-sky-500/5 border-sky-200">
            <p className="text-sm text-muted-foreground mb-2">Mention Rate</p>
            <p className="text-4xl font-bold text-sky-600">67%</p>
            <p className="text-sm text-muted-foreground mt-2">Of total prompts</p>
          </Card>
        );

      case "mention-growth-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-teal-500/10 to-teal-500/5 border-teal-200">
            <p className="text-sm text-muted-foreground mb-2">Mention Growth</p>
            <p className="text-4xl font-bold text-teal-600">+24.5%</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              vs last month
            </p>
          </Card>
        );

      case "platform-coverage-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-pink-500/10 to-pink-500/5 border-pink-200">
            <p className="text-sm text-muted-foreground mb-2">Platform Coverage</p>
            <p className="text-4xl font-bold text-pink-600">5/5</p>
            <p className="text-sm text-muted-foreground mt-2">All platforms active</p>
          </Card>
        );

      case "citation-rate-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-indigo-500/10 to-indigo-500/5 border-indigo-200">
            <p className="text-sm text-muted-foreground mb-2">Citation Rate</p>
            <p className="text-4xl font-bold text-indigo-600">2.8</p>
            <p className="text-sm text-muted-foreground mt-2">Citations per mention</p>
          </Card>
        );

      case "citation-density-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-fuchsia-500/10 to-fuchsia-500/5 border-fuchsia-200">
            <p className="text-sm text-muted-foreground mb-2">Citation Density</p>
            <p className="text-4xl font-bold text-fuchsia-600">3.2</p>
            <p className="text-sm text-muted-foreground mt-2">Avg per response</p>
          </Card>
        );

      case "primary-sources-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-rose-500/10 to-rose-500/5 border-rose-200">
            <p className="text-sm text-muted-foreground mb-2">Primary Sources</p>
            <p className="text-4xl font-bold text-rose-600">156</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              +12 this month
            </p>
          </Card>
        );

      case "avg-sentiment-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-lime-500/10 to-lime-500/5 border-lime-200">
            <p className="text-sm text-muted-foreground mb-2">Average Sentiment Score</p>
            <p className="text-4xl font-bold text-lime-600">7.8/10</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <Smile className="h-4 w-4" />
              Highly positive
            </p>
          </Card>
        );

      case "sentiment-trend-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-emerald-500/10 to-emerald-500/5 border-emerald-200">
            <p className="text-sm text-muted-foreground mb-2">Sentiment Trend</p>
            <p className="text-4xl font-bold text-emerald-600">+0.4</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              Improving trend
            </p>
          </Card>
        );

      case "market-position-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-purple-500/10 to-purple-500/5 border-purple-200">
            <p className="text-sm text-muted-foreground mb-2">Market Position</p>
            <p className="text-4xl font-bold text-purple-600">#2</p>
            <p className="text-sm text-muted-foreground mt-2">Out of 8 competitors</p>
          </Card>
        );

      case "competitor-gap-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-orange-500/10 to-orange-500/5 border-orange-200">
            <p className="text-sm text-muted-foreground mb-2">Competitor Gap</p>
            <p className="text-4xl font-bold text-orange-600">-145</p>
            <p className="text-sm text-muted-foreground mt-2">Behind leader</p>
          </Card>
        );

      case "market-share-trend-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-amber-500/10 to-amber-500/5 border-amber-200">
            <p className="text-sm text-muted-foreground mb-2">Market Share Trend</p>
            <p className="text-4xl font-bold text-amber-600">+3.2%</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              Growing share
            </p>
          </Card>
        );

      case "health-score-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-cyan-500/10 to-cyan-500/5 border-cyan-200">
            <p className="text-sm text-muted-foreground mb-2">Health Score</p>
            <p className="text-4xl font-bold text-cyan-600">94/100</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <Activity className="h-4 w-4" />
              Excellent health
            </p>
          </Card>
        );

      case "content-quality-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-blue-500/10 to-blue-500/5 border-blue-200">
            <p className="text-sm text-muted-foreground mb-2">Content Quality Score</p>
            <p className="text-4xl font-bold text-blue-600">88/100</p>
            <p className="text-sm text-muted-foreground mt-2">High quality content</p>
          </Card>
        );

      case "topics-covered-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-indigo-500/10 to-indigo-500/5 border-indigo-200">
            <p className="text-sm text-muted-foreground mb-2">Topics Covered</p>
            <p className="text-4xl font-bold text-indigo-600">24</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              +6 new topics
            </p>
          </Card>
        );

      case "answer-coverage-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-violet-500/10 to-violet-500/5 border-violet-200">
            <p className="text-sm text-muted-foreground mb-2">Answer Coverage</p>
            <p className="text-4xl font-bold text-violet-600">78%</p>
            <p className="text-sm text-muted-foreground mt-2">Of all prompts</p>
          </Card>
        );

      case "active-alerts-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-red-500/10 to-red-500/5 border-red-200">
            <p className="text-sm text-muted-foreground mb-2">Active Alerts</p>
            <p className="text-4xl font-bold text-red-600">3</p>
            <p className="text-sm text-muted-foreground mt-2">Require attention</p>
          </Card>
        );

      case "critical-issues-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-red-500/10 to-red-500/5 border-red-200">
            <p className="text-sm text-muted-foreground mb-2">Critical Issues</p>
            <p className="text-4xl font-bold text-red-600">1</p>
            <p className="text-sm text-red-600 mt-2 flex items-center gap-1">
              <AlertCircle className="h-4 w-4" />
              High priority
            </p>
          </Card>
        );

      case "broken-links-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-yellow-500/10 to-yellow-500/5 border-yellow-200">
            <p className="text-sm text-muted-foreground mb-2">Broken Links</p>
            <p className="text-4xl font-bold text-yellow-600">7</p>
            <p className="text-sm text-muted-foreground mt-2">Need fixing</p>
          </Card>
        );

      case "misinformation-cases-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-orange-500/10 to-orange-500/5 border-orange-200">
            <p className="text-sm text-muted-foreground mb-2">Misinformation Cases</p>
            <p className="text-4xl font-bold text-orange-600">2</p>
            <p className="text-sm text-orange-600 mt-2 flex items-center gap-1">
              <AlertCircle className="h-4 w-4" />
              Under review
            </p>
          </Card>
        );

      case "mention-growth-percent-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-green-500/10 to-green-500/5 border-green-200">
            <p className="text-sm text-muted-foreground mb-2">Mention Growth %</p>
            <p className="text-4xl font-bold text-green-600">+24.5%</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              Strong growth
            </p>
          </Card>
        );

      case "visibility-trend-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-emerald-500/10 to-emerald-500/5 border-emerald-200">
            <p className="text-sm text-muted-foreground mb-2">Visibility Trend</p>
            <p className="text-4xl font-bold text-emerald-600">+6.3%</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              Improving visibility
            </p>
          </Card>
        );

      case "citation-growth-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-blue-500/10 to-blue-500/5 border-blue-200">
            <p className="text-sm text-muted-foreground mb-2">Citation Growth</p>
            <p className="text-4xl font-bold text-blue-600">+18.2%</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              More citations
            </p>
          </Card>
        );

      case "engagement-growth-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-violet-500/10 to-violet-500/5 border-violet-200">
            <p className="text-sm text-muted-foreground mb-2">Engagement Growth</p>
            <p className="text-4xl font-bold text-violet-600">+8.1%</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              Better engagement
            </p>
          </Card>
        );

      // Platform Metrics - Overview
      case "total-platforms-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-purple-500/10 to-purple-500/5 border-purple-200">
            <p className="text-sm text-muted-foreground mb-2">Total Platforms Tracked</p>
            <p className="text-4xl font-bold text-purple-600">5</p>
            <p className="text-sm text-muted-foreground mt-2">Active platforms</p>
          </Card>
        );

      case "total-platform-mentions-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-blue-500/10 to-blue-500/5 border-blue-200">
            <p className="text-sm text-muted-foreground mb-2">Total Platform Mentions</p>
            <p className="text-4xl font-bold text-blue-600">2,847</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              +15.3% across all platforms
            </p>
          </Card>
        );

      case "total-platform-citations-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-cyan-500/10 to-cyan-500/5 border-cyan-200">
            <p className="text-sm text-muted-foreground mb-2">Total Platform Citations</p>
            <p className="text-4xl font-bold text-cyan-600">1,264</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              +22.1% from last month
            </p>
          </Card>
        );

      // Platform Metrics - Performance Per Platform
      case "chatgpt-visibility-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-green-500/10 to-green-500/5 border-green-200">
            <p className="text-sm text-muted-foreground mb-2">ChatGPT Visibility</p>
            <p className="text-4xl font-bold text-green-600">89.2</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              Leading platform
            </p>
          </Card>
        );

      case "gemini-visibility-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-blue-500/10 to-blue-500/5 border-blue-200">
            <p className="text-sm text-muted-foreground mb-2">Gemini Visibility</p>
            <p className="text-4xl font-bold text-blue-600">82.7</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              Strong presence
            </p>
          </Card>
        );

      case "perplexity-visibility-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-purple-500/10 to-purple-500/5 border-purple-200">
            <p className="text-sm text-muted-foreground mb-2">Perplexity Visibility</p>
            <p className="text-4xl font-bold text-purple-600">78.5</p>
            <p className="text-sm text-muted-foreground mt-2">Good performance</p>
          </Card>
        );

      case "claude-visibility-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-orange-500/10 to-orange-500/5 border-orange-200">
            <p className="text-sm text-muted-foreground mb-2">Claude Visibility</p>
            <p className="text-4xl font-bold text-orange-600">85.3</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              +4.2% improvement
            </p>
          </Card>
        );

      case "grok-visibility-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-indigo-500/10 to-indigo-500/5 border-indigo-200">
            <p className="text-sm text-muted-foreground mb-2">Grok Visibility</p>
            <p className="text-4xl font-bold text-indigo-600">71.8</p>
            <p className="text-sm text-amber-600 mt-2 flex items-center gap-1">
              Growing platform
            </p>
          </Card>
        );

      // Platform Metrics - Mention & Citation
      case "top-performing-platform-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-green-500/10 to-green-500/5 border-green-200">
            <p className="text-sm text-muted-foreground mb-2">Top Performing Platform</p>
            <p className="text-4xl font-bold text-green-600">ChatGPT</p>
            <p className="text-sm text-muted-foreground mt-2">847 mentions</p>
          </Card>
        );

      case "platform-mention-distribution-chart":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <ResponsiveContainer width="100%" height={200}>
              <RechartsPieChart>
                <Pie
                  data={[
                    { name: 'ChatGPT', value: 35, color: '#10b981' },
                    { name: 'Claude', value: 25, color: '#f97316' },
                    { name: 'Gemini', value: 20, color: '#3b82f6' },
                    { name: 'Perplexity', value: 12, color: '#8b5cf6' },
                    { name: 'Grok', value: 8, color: '#6366f1' },
                  ]}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={(entry) => `${entry.name}: ${entry.value}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {[
                    { name: 'ChatGPT', value: 35, color: '#10b981' },
                    { name: 'Claude', value: 25, color: '#f97316' },
                    { name: 'Gemini', value: 20, color: '#3b82f6' },
                    { name: 'Perplexity', value: 12, color: '#8b5cf6' },
                    { name: 'Grok', value: 8, color: '#6366f1' },
                  ].map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </RechartsPieChart>
            </ResponsiveContainer>
          </Card>
        );

      case "platform-citation-distribution-chart":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <ResponsiveContainer width="100%" height={200}>
              <RechartsBarChart data={[
                { platform: 'ChatGPT', citations: 425 },
                { platform: 'Claude', citations: 318 },
                { platform: 'Gemini', citations: 267 },
                { platform: 'Perplexity', citations: 189 },
                { platform: 'Grok', citations: 65 },
              ]}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="platform" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="citations" fill="#3b82f6" />
              </RechartsBarChart>
            </ResponsiveContainer>
          </Card>
        );

      case "platform-mention-trends-chart":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <ResponsiveContainer width="100%" height={200}>
              <RechartsLineChart data={[
                { month: 'Jan', ChatGPT: 120, Claude: 85, Gemini: 75, Perplexity: 45, Grok: 25 },
                { month: 'Feb', ChatGPT: 140, Claude: 95, Gemini: 82, Perplexity: 52, Grok: 28 },
                { month: 'Mar', ChatGPT: 165, Claude: 110, Gemini: 95, Perplexity: 58, Grok: 32 },
                { month: 'Apr', ChatGPT: 182, Claude: 125, Gemini: 108, Perplexity: 65, Grok: 38 },
              ]}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="ChatGPT" stroke="#10b981" strokeWidth={2} />
                <Line type="monotone" dataKey="Claude" stroke="#f97316" strokeWidth={2} />
                <Line type="monotone" dataKey="Gemini" stroke="#3b82f6" strokeWidth={2} />
                <Line type="monotone" dataKey="Perplexity" stroke="#8b5cf6" strokeWidth={2} />
                <Line type="monotone" dataKey="Grok" stroke="#6366f1" strokeWidth={2} />
              </RechartsLineChart>
            </ResponsiveContainer>
          </Card>
        );

      // Platform Metrics - Position
      case "avg-position-by-platform-chart":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <ResponsiveContainer width="100%" height={200}>
              <RechartsBarChart data={[
                { platform: 'ChatGPT', position: 1.8 },
                { platform: 'Claude', position: 2.1 },
                { platform: 'Gemini', position: 2.4 },
                { platform: 'Perplexity', position: 2.8 },
                { platform: 'Grok', position: 3.2 },
              ]}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="platform" />
                <YAxis reversed />
                <Tooltip />
                <Bar dataKey="position" fill="#f59e0b" />
              </RechartsBarChart>
            </ResponsiveContainer>
          </Card>
        );

      case "best-platform-position-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-amber-500/10 to-amber-500/5 border-amber-200">
            <p className="text-sm text-muted-foreground mb-2">Best Platform Position</p>
            <p className="text-4xl font-bold text-amber-600">ChatGPT</p>
            <p className="text-sm text-muted-foreground mt-2">Avg position: 1.8</p>
          </Card>
        );

      case "platform-position-comparison-chart":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <ResponsiveContainer width="100%" height={200}>
              <RechartsLineChart data={[
                { month: 'Jan', ChatGPT: 2.2, Claude: 2.5, Gemini: 2.8, Perplexity: 3.2, Grok: 3.8 },
                { month: 'Feb', ChatGPT: 2.0, Claude: 2.3, Gemini: 2.6, Perplexity: 3.0, Grok: 3.5 },
                { month: 'Mar', ChatGPT: 1.9, Claude: 2.2, Gemini: 2.5, Perplexity: 2.9, Grok: 3.3 },
                { month: 'Apr', ChatGPT: 1.8, Claude: 2.1, Gemini: 2.4, Perplexity: 2.8, Grok: 3.2 },
              ]}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis reversed />
                <Tooltip />
                <Line type="monotone" dataKey="ChatGPT" stroke="#10b981" strokeWidth={2} />
                <Line type="monotone" dataKey="Claude" stroke="#f97316" strokeWidth={2} />
                <Line type="monotone" dataKey="Gemini" stroke="#3b82f6" strokeWidth={2} />
                <Line type="monotone" dataKey="Perplexity" stroke="#8b5cf6" strokeWidth={2} />
                <Line type="monotone" dataKey="Grok" stroke="#6366f1" strokeWidth={2} />
              </RechartsLineChart>
            </ResponsiveContainer>
          </Card>
        );

      // Platform Metrics - Sentiment
      case "platform-sentiment-breakdown-chart":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <ResponsiveContainer width="100%" height={200}>
              <RechartsBarChart data={[
                { platform: 'ChatGPT', Positive: 72, Neutral: 20, Negative: 8 },
                { platform: 'Claude', Positive: 68, Neutral: 24, Negative: 8 },
                { platform: 'Gemini', Positive: 65, Neutral: 27, Negative: 8 },
                { platform: 'Perplexity', Positive: 70, Neutral: 22, Negative: 8 },
                { platform: 'Grok', Positive: 62, Neutral: 28, Negative: 10 },
              ]}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="platform" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="Positive" stackId="a" fill="#10b981" />
                <Bar dataKey="Neutral" stackId="a" fill="#94a3b8" />
                <Bar dataKey="Negative" stackId="a" fill="#ef4444" />
              </RechartsBarChart>
            </ResponsiveContainer>
          </Card>
        );

      case "most-positive-platform-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-green-500/10 to-green-500/5 border-green-200">
            <p className="text-sm text-muted-foreground mb-2">Most Positive Platform</p>
            <p className="text-4xl font-bold text-green-600">ChatGPT</p>
            <p className="text-sm text-muted-foreground mt-2">72% positive sentiment</p>
          </Card>
        );

      case "platform-sentiment-trends-chart":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <ResponsiveContainer width="100%" height={200}>
              <RechartsLineChart data={[
                { month: 'Jan', ChatGPT: 68, Claude: 64, Gemini: 60, Perplexity: 66, Grok: 58 },
                { month: 'Feb', ChatGPT: 69, Claude: 65, Gemini: 62, Perplexity: 67, Grok: 59 },
                { month: 'Mar', ChatGPT: 70, Claude: 66, Gemini: 63, Perplexity: 68, Grok: 60 },
                { month: 'Apr', ChatGPT: 72, Claude: 68, Gemini: 65, Perplexity: 70, Grok: 62 },
              ]}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="ChatGPT" stroke="#10b981" strokeWidth={2} />
                <Line type="monotone" dataKey="Claude" stroke="#f97316" strokeWidth={2} />
                <Line type="monotone" dataKey="Gemini" stroke="#3b82f6" strokeWidth={2} />
                <Line type="monotone" dataKey="Perplexity" stroke="#8b5cf6" strokeWidth={2} />
                <Line type="monotone" dataKey="Grok" stroke="#6366f1" strokeWidth={2} />
              </RechartsLineChart>
            </ResponsiveContainer>
          </Card>
        );

      // Platform Metrics - Engagement
      case "platform-response-rate-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-violet-500/10 to-violet-500/5 border-violet-200">
            <p className="text-sm text-muted-foreground mb-2">Platform Response Rate</p>
            <p className="text-4xl font-bold text-violet-600">96.4%</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              High engagement
            </p>
          </Card>
        );

      case "platform-mention-rate-chart":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <ResponsiveContainer width="100%" height={200}>
              <RechartsBarChart data={[
                { platform: 'ChatGPT', rate: 84 },
                { platform: 'Claude', rate: 76 },
                { platform: 'Gemini', rate: 72 },
                { platform: 'Perplexity', rate: 68 },
                { platform: 'Grok', rate: 58 },
              ]}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="platform" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="rate" fill="#8b5cf6" />
              </RechartsBarChart>
            </ResponsiveContainer>
          </Card>
        );

      case "platform-growth-rate-chart":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <ResponsiveContainer width="100%" height={200}>
              <RechartsLineChart data={[
                { month: 'Jan', ChatGPT: 0, Claude: 0, Gemini: 0, Perplexity: 0, Grok: 0 },
                { month: 'Feb', ChatGPT: 16.7, Claude: 11.8, Gemini: 9.3, Perplexity: 15.6, Grok: 12.0 },
                { month: 'Mar', ChatGPT: 17.9, Claude: 15.8, Gemini: 15.9, Perplexity: 11.5, Grok: 14.3 },
                { month: 'Apr', ChatGPT: 10.3, Claude: 13.6, Gemini: 13.7, Perplexity: 12.1, Grok: 18.8 },
              ]}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="ChatGPT" stroke="#10b981" strokeWidth={2} />
                <Line type="monotone" dataKey="Claude" stroke="#f97316" strokeWidth={2} />
                <Line type="monotone" dataKey="Gemini" stroke="#3b82f6" strokeWidth={2} />
                <Line type="monotone" dataKey="Perplexity" stroke="#8b5cf6" strokeWidth={2} />
                <Line type="monotone" dataKey="Grok" stroke="#6366f1" strokeWidth={2} />
              </RechartsLineChart>
            </ResponsiveContainer>
          </Card>
        );

      // Platform Metrics - Comparative
      case "platform-share-of-voice-chart":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <ResponsiveContainer width="100%" height={200}>
              <RechartsBarChart data={[
                { platform: 'ChatGPT', share: 35 },
                { platform: 'Claude', share: 25 },
                { platform: 'Gemini', share: 20 },
                { platform: 'Perplexity', share: 12 },
                { platform: 'Grok', share: 8 },
              ]}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="platform" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="share" fill="#f97316" />
              </RechartsBarChart>
            </ResponsiveContainer>
          </Card>
        );

      case "platform-performance-matrix-chart":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <div className="overflow-auto">
              <table className="w-full text-sm">
                <thead className="border-b">
                  <tr>
                    <th className="text-left py-2">Platform</th>
                    <th className="text-right py-2">Visibility</th>
                    <th className="text-right py-2">Position</th>
                    <th className="text-right py-2">Sentiment</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b">
                    <td className="py-2">ChatGPT</td>
                    <td className="text-right">89.2</td>
                    <td className="text-right">1.8</td>
                    <td className="text-right text-green-600">72%</td>
                  </tr>
                  <tr className="border-b">
                    <td className="py-2">Claude</td>
                    <td className="text-right">85.3</td>
                    <td className="text-right">2.1</td>
                    <td className="text-right text-green-600">68%</td>
                  </tr>
                  <tr className="border-b">
                    <td className="py-2">Gemini</td>
                    <td className="text-right">82.7</td>
                    <td className="text-right">2.4</td>
                    <td className="text-right text-green-600">65%</td>
                  </tr>
                  <tr className="border-b">
                    <td className="py-2">Perplexity</td>
                    <td className="text-right">78.5</td>
                    <td className="text-right">2.8</td>
                    <td className="text-right text-green-600">70%</td>
                  </tr>
                  <tr>
                    <td className="py-2">Grok</td>
                    <td className="text-right">71.8</td>
                    <td className="text-right">3.2</td>
                    <td className="text-right text-green-600">62%</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </Card>
        );

      case "platform-citation-density-chart":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <ResponsiveContainer width="100%" height={200}>
              <RechartsBarChart data={[
                { platform: 'ChatGPT', density: 0.50 },
                { platform: 'Claude', density: 0.38 },
                { platform: 'Gemini', density: 0.32 },
                { platform: 'Perplexity', density: 0.22 },
                { platform: 'Grok', density: 0.08 },
              ]}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="platform" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="density" fill="#3b82f6" />
              </RechartsBarChart>
            </ResponsiveContainer>
          </Card>
        );

      // Platform Metrics - Health
      case "platform-health-score-chart":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <ResponsiveContainer width="100%" height={200}>
              <RechartsBarChart data={[
                { platform: 'ChatGPT', health: 92 },
                { platform: 'Claude', health: 88 },
                { platform: 'Gemini', health: 86 },
                { platform: 'Perplexity', health: 84 },
                { platform: 'Grok', health: 78 },
              ]}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="platform" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="health" fill="#14b8a6" />
              </RechartsBarChart>
            </ResponsiveContainer>
          </Card>
        );

      case "platform-coverage-quality-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-teal-500/10 to-teal-500/5 border-teal-200">
            <p className="text-sm text-muted-foreground mb-2">Platform Coverage Quality</p>
            <p className="text-4xl font-bold text-teal-600">85.7</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              High quality coverage
            </p>
          </Card>
        );

      case "platform-consistency-score-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-sky-500/10 to-sky-500/5 border-sky-200">
            <p className="text-sm text-muted-foreground mb-2">Platform Consistency Score</p>
            <p className="text-4xl font-bold text-sky-600">91.2</p>
            <p className="text-sm text-muted-foreground mt-2">Consistent performance</p>
          </Card>
        );

      // New Citations widgets
      case "unique-sources-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-cyan-500/10 to-cyan-500/5 border-cyan-200">
            <p className="text-sm text-muted-foreground mb-2">Unique Sources</p>
            <p className="text-4xl font-bold text-cyan-600">156</p>
            <p className="text-sm text-muted-foreground mt-2">Distinct citation URLs</p>
          </Card>
        );

      case "domain-citations-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-blue-500/10 to-blue-500/5 border-blue-200">
            <p className="text-sm text-muted-foreground mb-2">Domain Citations</p>
            <p className="text-4xl font-bold text-blue-600">89</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <Link2 className="h-4 w-4" />
              Links to your domain
            </p>
          </Card>
        );

      case "valid-links-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-green-500/10 to-green-500/5 border-green-200">
            <p className="text-sm text-muted-foreground mb-2">Valid Links</p>
            <p className="text-4xl font-bold text-green-600">328</p>
            <p className="text-sm text-muted-foreground mt-2">Successfully verified</p>
          </Card>
        );

      case "pending-citations-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-amber-500/10 to-amber-500/5 border-amber-200">
            <p className="text-sm text-muted-foreground mb-2">Pending Citations</p>
            <p className="text-4xl font-bold text-amber-600">14</p>
            <p className="text-sm text-muted-foreground mt-2">Awaiting verification</p>
          </Card>
        );

      // New Sentiment widgets
      case "competitor-comparison-chart":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <ResponsiveContainer width="100%" height={200}>
              <RechartsBarChart data={[
                { name: 'Your Brand', sentiment: 0.72 },
                { name: 'Competitor A', sentiment: 0.58 },
                { name: 'Competitor B', sentiment: 0.65 },
                { name: 'Competitor C', sentiment: 0.42 },
                { name: 'Competitor D', sentiment: 0.55 },
              ]}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="sentiment" fill="#8b5cf6" />
              </RechartsBarChart>
            </ResponsiveContainer>
          </Card>
        );

      // New Topics widgets
      case "topic-distribution-chart":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <ResponsiveContainer width="100%" height={200}>
              <RechartsPieChart>
                <Pie
                  data={[
                    { name: 'AI Integration', value: 35 },
                    { name: 'Product Features', value: 28 },
                    { name: 'Pricing', value: 18 },
                    { name: 'Support', value: 12 },
                    { name: 'Other', value: 7 },
                  ]}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={(entry) => `${entry.name}: ${entry.value}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  <Cell fill="#3b82f6" />
                  <Cell fill="#8b5cf6" />
                  <Cell fill="#f97316" />
                  <Cell fill="#10b981" />
                  <Cell fill="#94a3b8" />
                </Pie>
                <Tooltip />
              </RechartsPieChart>
            </ResponsiveContainer>
          </Card>
        );

      case "topic-trends-chart":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <ResponsiveContainer width="100%" height={200}>
              <RechartsLineChart data={[
                { month: 'Jan', 'AI Integration': 25, 'Product Features': 18, 'Pricing': 12 },
                { month: 'Feb', 'AI Integration': 28, 'Product Features': 20, 'Pricing': 14 },
                { month: 'Mar', 'AI Integration': 32, 'Product Features': 24, 'Pricing': 16 },
                { month: 'Apr', 'AI Integration': 35, 'Product Features': 28, 'Pricing': 18 },
              ]}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="AI Integration" stroke="#3b82f6" strokeWidth={2} />
                <Line type="monotone" dataKey="Product Features" stroke="#8b5cf6" strokeWidth={2} />
                <Line type="monotone" dataKey="Pricing" stroke="#f97316" strokeWidth={2} />
              </RechartsLineChart>
            </ResponsiveContainer>
          </Card>
        );

      // New Share of Voice widgets
      case "market-share-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-purple-500/10 to-purple-500/5 border-purple-200">
            <p className="text-sm text-muted-foreground mb-2">Market Share</p>
            <p className="text-4xl font-bold text-purple-600">42%</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              +5.2% growth
            </p>
          </Card>
        );

      case "dominance-score-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-indigo-500/10 to-indigo-500/5 border-indigo-200">
            <p className="text-sm text-muted-foreground mb-2">Dominance Score</p>
            <p className="text-4xl font-bold text-indigo-600">78.5</p>
            <p className="text-sm text-muted-foreground mt-2">Out of 100</p>
          </Card>
        );

      case "overall-market-share-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-violet-500/10 to-violet-500/5 border-violet-200">
            <p className="text-sm text-muted-foreground mb-2">Overall Market Share</p>
            <p className="text-4xl font-bold text-violet-600">42%</p>
            <p className="text-sm text-muted-foreground mt-2">Across all platforms</p>
          </Card>
        );

      case "share-of-voice-trends-chart":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <ResponsiveContainer width="100%" height={200}>
              <RechartsLineChart data={[
                { month: 'Jan', share: 37 },
                { month: 'Feb', share: 39 },
                { month: 'Mar', share: 40 },
                { month: 'Apr', share: 42 },
                { month: 'May', share: 41 },
                { month: 'Jun', share: 42 },
              ]}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="share" stroke="#8b5cf6" strokeWidth={2} />
              </RechartsLineChart>
            </ResponsiveContainer>
          </Card>
        );

      case "brand-positioning-matrix-chart":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <div className="overflow-auto">
              <table className="w-full text-sm">
                <thead className="border-b">
                  <tr>
                    <th className="text-left py-2">Brand</th>
                    <th className="text-right py-2">Mentions</th>
                    <th className="text-right py-2">Sentiment</th>
                    <th className="text-right py-2">Position</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b bg-blue-50">
                    <td className="py-2 font-semibold">Your Brand</td>
                    <td className="text-right">1,547</td>
                    <td className="text-right text-green-600">0.72</td>
                    <td className="text-right">#2</td>
                  </tr>
                  <tr className="border-b">
                    <td className="py-2">Competitor A</td>
                    <td className="text-right">1,892</td>
                    <td className="text-right text-green-600">0.58</td>
                    <td className="text-right">#1</td>
                  </tr>
                  <tr className="border-b">
                    <td className="py-2">Competitor B</td>
                    <td className="text-right">1,234</td>
                    <td className="text-right text-green-600">0.65</td>
                    <td className="text-right">#3</td>
                  </tr>
                  <tr>
                    <td className="py-2">Competitor C</td>
                    <td className="text-right">987</td>
                    <td className="text-right text-yellow-600">0.42</td>
                    <td className="text-right">#4</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </Card>
        );

      // New Historical Trends widgets
      case "visibility-growth-chart":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={[
                { month: 'Jan', visibility: 72 },
                { month: 'Feb', visibility: 76 },
                { month: 'Mar', visibility: 81 },
                { month: 'Apr', visibility: 84 },
                { month: 'May', visibility: 86 },
                { month: 'Jun', visibility: 87.5 },
              ]}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
                <Tooltip />
                <Area type="monotone" dataKey="visibility" stroke="#10b981" fill="#10b981" fillOpacity={0.3} />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        );

      case "mention-growth-chart":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <ResponsiveContainer width="100%" height={200}>
              <RechartsLineChart data={[
                { month: 'Jan', growth: 0 },
                { month: 'Feb', growth: 15.5 },
                { month: 'Mar', growth: 17.3 },
                { month: 'Apr', growth: 24.5 },
                { month: 'May', growth: 12.8 },
                { month: 'Jun', growth: 18.2 },
              ]}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="growth" stroke="#3b82f6" strokeWidth={2} />
              </RechartsLineChart>
            </ResponsiveContainer>
          </Card>
        );

      case "position-improvement-chart":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <ResponsiveContainer width="100%" height={200}>
              <RechartsLineChart data={[
                { month: 'Jan', position: 3.2 },
                { month: 'Feb', position: 2.9 },
                { month: 'Mar', position: 2.7 },
                { month: 'Apr', position: 2.4 },
                { month: 'May', position: 2.5 },
                { month: 'Jun', position: 2.4 },
              ]}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis reversed />
                <Tooltip />
                <Line type="monotone" dataKey="position" stroke="#f97316" strokeWidth={2} />
              </RechartsLineChart>
            </ResponsiveContainer>
          </Card>
        );

      case "market-share-gain-chart":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={[
                { month: 'Jan', share: 37 },
                { month: 'Feb', share: 39 },
                { month: 'Mar', share: 40 },
                { month: 'Apr', share: 42 },
                { month: 'May', share: 41 },
                { month: 'Jun', share: 42 },
              ]}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
                <Tooltip />
                <Area type="monotone" dataKey="share" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.3} />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        );

      case "visibility-score-progression-chart":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <ResponsiveContainer width="100%" height={200}>
              <RechartsLineChart data={[
                { month: 'Jan', score: 72 },
                { month: 'Feb', score: 76 },
                { month: 'Mar', score: 81 },
                { month: 'Apr', score: 84 },
                { month: 'May', score: 86 },
                { month: 'Jun', score: 87.5 },
              ]}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="score" stroke="#10b981" strokeWidth={2} />
              </RechartsLineChart>
            </ResponsiveContainer>
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
