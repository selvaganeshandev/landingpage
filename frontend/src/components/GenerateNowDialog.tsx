import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { useDomainStore } from "@/stores/domainStore";
import { apiClient } from "@/services/api";
import { FileText, Loader2, Download } from "lucide-react";
import { getFaviconUrl, handleFaviconError } from "@/utils/faviconHelper";

interface GenerateNowDialogProps{
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const GenerateNowDialog = ({ open, onOpenChange }: GenerateNowDialogProps) => {
  const { toast } = useToast();
  const { selectedDomain } = useDomainStore();
  const [templateId, setTemplateId] = useState<string>("");
  const [format, setFormat] = useState("pdf");
  const [isGenerating, setIsGenerating] = useState(false);

  // Fetch report templates
  const { data: templates = [], isLoading: templatesLoading } = useQuery({
    queryKey: ['reportTemplates'],
    queryFn: () => apiClient.getReportTemplates(),
  });

  const selectedTemplate = templates.find((t: any) => t.id.toString() === templateId);

  const handleGenerate = async () => {
    if (!selectedDomain) {
      toast({
        title: "No Domain Selected",
        description: "Please select a domain first.",
        variant: "destructive",
      });
      return;
    }

    if (!templateId) {
      toast({
        title: "No Template Selected",
        description: "Please select a report template.",
        variant: "destructive",
      });
      return;
    }

    setIsGenerating(true);

    try {
      toast({
        title: "Generating Report",
        description: "Your report is being created. This may take a few moments...",
      });

      // Call the API to generate the report
      const response = await apiClient.generateReport({
        domain_id: selectedDomain.id,
        template_id: parseInt(templateId),
        sections: selectedTemplate?.sections || [],
        format: format.toUpperCase(),
        data_period_days: 30,
      });

      // If we got a file path, download it
      if (response.id) {
        toast({
          title: "Report Generated!",
          description: "Downloading your report...",
        });

        // Download the generated report
        await apiClient.downloadReport(response.id);
      }

      onOpenChange(false);
    } catch (error: any) {
      console.error('Error generating report:', error);
      toast({
        title: "Error",
        description: error.message || "Failed to generate report. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Generate Report Now</DialogTitle>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Domain Info */}
          {selectedDomain && (
            <div className="p-3 border rounded-lg bg-muted/30">
              <div className="flex items-center gap-3">
                <img
                  src={getFaviconUrl(selectedDomain.url, 64)}
                  alt="Domain favicon"
                  className="h-6 w-6"
                  onError={(e) => handleFaviconError(e, selectedDomain.url, selectedDomain.name, 64)}
                />
                <div>
                  <p className="font-medium text-sm">{selectedDomain.name}</p>
                  <p className="text-xs text-muted-foreground">{selectedDomain.url}</p>
                </div>
              </div>
            </div>
          )}

          {/* Template Selection */}
          <div className="space-y-2">
            <Label htmlFor="template">Report Template</Label>
            {templatesLoading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading templates...
              </div>
            ) : (
              <Select value={templateId} onValueChange={setTemplateId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a template" />
                </SelectTrigger>
                <SelectContent>
                  {templates.map((template: any) => (
                    <SelectItem key={template.id} value={template.id.toString()}>
                      {template.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
            {selectedTemplate && (
              <p className="text-xs text-muted-foreground">
                {selectedTemplate.description}
              </p>
            )}
          </div>

          {/* Format Selection */}
          <div className="space-y-2">
            <Label>Output Format</Label>
            <div className="flex gap-2">
              {["PDF"].map((fmt) => (
                <Badge
                  key={fmt}
                  variant={format === fmt.toLowerCase() ? "default" : "outline"}
                  className="cursor-pointer"
                  onClick={() => setFormat(fmt.toLowerCase())}
                >
                  {fmt}
                </Badge>
              ))}
            </div>
          </div>

          {/* Preview Info */}
          {selectedTemplate && (
            <div className="p-4 border rounded-lg bg-muted/30">
              <div className="flex items-start gap-3">
                <FileText className="h-5 w-5 text-muted-foreground mt-0.5" />
                <div className="text-sm">
                  <p className="font-medium mb-1">Report Preview</p>
                  <p className="text-muted-foreground">
                    This report will include {selectedTemplate.sections?.length || 0} sections
                    based on data from the last 30 days.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isGenerating}>
            Cancel
          </Button>
          <Button onClick={handleGenerate} disabled={isGenerating || !templateId || !selectedDomain}>
            {isGenerating ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Download className="h-4 w-4 mr-2" />
                Generate & Download
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
