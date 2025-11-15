import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { FileText, Download, Share2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { ExecutiveDashboardTemplate } from "@/components/report-templates/ExecutiveDashboardTemplate";
import { DetailedAnalyticsTemplate } from "@/components/report-templates/DetailedAnalyticsTemplate";
import { CompetitorFocusTemplate } from "@/components/report-templates/CompetitorFocusTemplate";
import { ContentStrategyTemplate } from "@/components/report-templates/ContentStrategyTemplate";

interface ReportPreviewDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  report: {
    id: number;
    name: string;
    description: string;
    format: string[];
  } | null;
}

export const ReportPreviewDialog = ({ open, onOpenChange, report }: ReportPreviewDialogProps) => {
  const { toast } = useToast();

  if (!report) return null;

  const handleDownload = (format: string) => {
    toast({
      title: "Downloading Report",
      description: `Downloading ${report.name} as ${format}...`,
    });
  };

  const handleShare = () => {
    toast({
      title: "Share Report",
      description: "Opening sharing options...",
    });
  };

  // Determine which template to render based on report name
  const renderTemplate = () => {
    const reportNameLower = report.name.toLowerCase();

    if (reportNameLower.includes('executive')) {
      return <ExecutiveDashboardTemplate />;
    } else if (reportNameLower.includes('detailed') || reportNameLower.includes('analytics')) {
      return <DetailedAnalyticsTemplate />;
    } else if (reportNameLower.includes('competitor')) {
      return <CompetitorFocusTemplate />;
    } else if (reportNameLower.includes('content') || reportNameLower.includes('strategy')) {
      return <ContentStrategyTemplate />;
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
              {report.format.map((fmt) => (
                <Button key={fmt} size="sm" variant="outline" onClick={() => handleDownload(fmt)}>
                  <Download className="h-3 w-3 mr-1" />
                  {fmt}
                </Button>
              ))}
              <Button size="sm" variant="outline" onClick={handleShare}>
                <Share2 className="h-3 w-3 mr-1" />
                Share
              </Button>
            </div>
          </div>
        </DialogHeader>

        <ScrollArea className="flex-1 border rounded-lg">
          <div className="p-8 bg-background">
            {renderTemplate()}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
};
