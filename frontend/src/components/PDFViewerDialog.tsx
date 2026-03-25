import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Download, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { API_BASE_URL } from "@/services/api";
import { useToast } from "@/hooks/use-toast";

interface PDFViewerDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  reportId: number | null;
  reportName: string;
}

export const PDFViewerDialog = ({ open, onOpenChange, reportId, reportName }: PDFViewerDialogProps) => {
  const [pdfUrl, setPdfUrl] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    if (open && reportId) {
      // Fetch the PDF with authentication
      const fetchPDF = async () => {
        setLoading(true);
        try {
          const token = localStorage.getItem('access_token');
          const response = await fetch(`${API_BASE_URL}/reports/generated/${reportId}/download/`, {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          });

          if (!response.ok) {
            throw new Error('Failed to fetch report');
          }

          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
          setPdfUrl(url);
        } catch (error) {
          console.error('Error fetching PDF:', error);
          toast({
            title: "Error",
            description: "Failed to load PDF report",
            variant: "destructive",
          });
        } finally {
          setLoading(false);
        }
      };

      fetchPDF();
    } else {
      // Clear PDF when dialog closes
      if (pdfUrl) {
        window.URL.revokeObjectURL(pdfUrl);
        setPdfUrl("");
      }
    }

    // Cleanup on unmount
    return () => {
      if (pdfUrl) {
        window.URL.revokeObjectURL(pdfUrl);
      }
    };
  }, [open, reportId]);

  const handleDownload = async () => {
    if (pdfUrl) {
      const a = document.createElement('a');
      a.href = pdfUrl;
      a.download = `${reportName}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl h-[90vh] flex flex-col p-0">
        <DialogHeader className="px-6 pt-6 pb-4 border-b">
          <div className="flex items-center justify-between">
            <DialogTitle>{reportName}</DialogTitle>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={handleDownload}>
                <Download className="h-4 w-4 mr-2" />
                Download
              </Button>
            </div>
          </div>
        </DialogHeader>

        <div className="flex-1 overflow-hidden bg-gray-100 flex items-center justify-center">
          {loading ? (
            <div className="flex flex-col items-center gap-4">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">Loading PDF...</p>
            </div>
          ) : pdfUrl ? (
            <iframe
              src={pdfUrl}
              className="w-full h-full border-0"
              title="PDF Viewer"
            />
          ) : (
            <p className="text-muted-foreground">No PDF to display</p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};
