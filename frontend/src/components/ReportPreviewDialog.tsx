import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { FileText, Download, Share2, Loader2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { ExecutiveDashboardTemplate } from "@/components/report-templates/ExecutiveDashboardTemplate";
import { DetailedAnalyticsTemplate } from "@/components/report-templates/DetailedAnalyticsTemplate";
import { CompetitorFocusTemplate } from "@/components/report-templates/CompetitorFocusTemplate";
import { ContentStrategyTemplate } from "@/components/report-templates/ContentStrategyTemplate";
import { useEffect, useState, useRef } from "react";
import html2canvas from "html2canvas";
import jsPDF from "jspdf";

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
  } | null;
}

export const ReportPreviewDialog = ({ open, onOpenChange, report }: ReportPreviewDialogProps) => {
  const { toast } = useToast();
  const [reportData, setReportData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const reportContentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open && report) {
      console.log('[ReportPreviewDialog] Report object:', report);

      // Get domain ID - it might be in different fields
      const domainId = report.domain || (report as any).domain_id;

      console.log('[ReportPreviewDialog] Domain ID:', domainId);

      if (!domainId) {
        console.warn('[ReportPreviewDialog] No domain ID found in report');
        setReportData(null);
        return;
      }

      // Fetch report data from the backend
      const fetchReportData = async () => {
        setLoading(true);
        try {
          const token = localStorage.getItem('access_token');
          const url = `http://localhost:8000/analytics/dashboard/summary/?domain_id=${domainId}&days=30`;
          console.log('[ReportPreviewDialog] Fetching from:', url);

          const response = await fetch(url, {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          });

          if (!response.ok) {
            throw new Error('Failed to fetch report data');
          }

          const data = await response.json();
          console.log('[ReportPreviewDialog] Fetched report data:', data);
          console.log('[ReportPreviewDialog] Metrics:', data?.metrics);
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
      <div className="space-y-8">
        <div className="border-b pb-6">
          <h2 className="text-2xl font-bold mb-2">{report.name}</h2>
          <p className="text-muted-foreground">Generated on {new Date().toLocaleDateString()}</p>
        </div>
        <div>
          <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Executive Summary
          </h3>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="p-4 border rounded-lg">
              <p className="text-sm text-muted-foreground mb-1">Visibility Score</p>
              <p className="text-2xl font-bold">87.5%</p>
              <Badge variant="default" className="mt-2">+5.2%</Badge>
            </div>
            <div className="p-4 border rounded-lg">
              <p className="text-sm text-muted-foreground mb-1">Total Mentions</p>
              <p className="text-2xl font-bold">1,247</p>
              <Badge variant="default" className="mt-2">+12.3%</Badge>
            </div>
            <div className="p-4 border rounded-lg">
              <p className="text-sm text-muted-foreground mb-1">Sentiment</p>
              <p className="text-2xl font-bold">Positive</p>
              <Badge variant="default" className="mt-2">92% positive</Badge>
            </div>
          </div>
        </div>
        <div>
          <h3 className="text-xl font-semibold mb-4">Performance Trends</h3>
          <div className="aspect-video border rounded-lg bg-muted/30 flex items-center justify-center">
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

        <ScrollArea className="flex-1 border rounded-lg">
          <div ref={reportContentRef} className="bg-background">
            {renderTemplate()}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
};
