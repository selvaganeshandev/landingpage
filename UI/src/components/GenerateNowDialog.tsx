import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { useToast } from "@/hooks/use-toast";
import { FileText } from "lucide-react";

interface GenerateNowDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const availableSections = [
  { id: "executive", name: "Executive Summary", default: true },
  { id: "visibility", name: "Visibility Score", default: true },
  { id: "mentions", name: "Mentions Overview", default: true },
  { id: "sentiment", name: "Sentiment Analysis", default: true },
  { id: "competitors", name: "Competitor Comparison", default: false },
  { id: "trends", name: "Trend Analysis", default: false },
  { id: "gaps", name: "Content Gaps", default: false },
  { id: "recommendations", name: "Recommendations", default: true },
];

export const GenerateNowDialog = ({ open, onOpenChange }: GenerateNowDialogProps) => {
  const { toast } = useToast();
  const [template, setTemplate] = useState("executive");
  const [format, setFormat] = useState("pdf");
  const [selectedSections, setSelectedSections] = useState<string[]>(
    availableSections.filter(s => s.default).map(s => s.id)
  );

  const handleGenerate = () => {
    toast({
      title: "Generating Report",
      description: "Your report is being created. This may take a few moments...",
    });
    
    // Simulate report generation
    setTimeout(() => {
      toast({
        title: "Report Ready!",
        description: "Your report has been generated successfully.",
      });
      onOpenChange(false);
    }, 2000);
  };

  const toggleSection = (sectionId: string) => {
    setSelectedSections(prev =>
      prev.includes(sectionId)
        ? prev.filter(id => id !== sectionId)
        : [...prev, sectionId]
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Generate Report Now</DialogTitle>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Template Selection */}
          <div className="space-y-2">
            <Label htmlFor="template">Report Template</Label>
            <Select value={template} onValueChange={setTemplate}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="executive">Executive Dashboard</SelectItem>
                <SelectItem value="detailed">Detailed Analytics</SelectItem>
                <SelectItem value="competitor">Competitor Focus</SelectItem>
                <SelectItem value="content">Content Strategy</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Format Selection */}
          <div className="space-y-2">
            <Label>Output Format</Label>
            <div className="flex gap-2">
              {["PDF", "Excel", "PowerPoint"].map((fmt) => (
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

          {/* Section Selection */}
          <div className="space-y-2">
            <Label>Include Sections</Label>
            <div className="border rounded-lg p-4 space-y-3 max-h-64 overflow-y-auto">
              {availableSections.map((section) => (
                <div key={section.id} className="flex items-center space-x-2">
                  <Checkbox
                    id={section.id}
                    checked={selectedSections.includes(section.id)}
                    onCheckedChange={() => toggleSection(section.id)}
                  />
                  <label
                    htmlFor={section.id}
                    className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                  >
                    {section.name}
                  </label>
                </div>
              ))}
            </div>
            <p className="text-xs text-muted-foreground">
              {selectedSections.length} of {availableSections.length} sections selected
            </p>
          </div>

          {/* Preview Info */}
          <div className="p-4 border rounded-lg bg-muted/30">
            <div className="flex items-start gap-3">
              <FileText className="h-5 w-5 text-muted-foreground mt-0.5" />
              <div className="text-sm">
                <p className="font-medium mb-1">Report Preview</p>
                <p className="text-muted-foreground">
                  This report will include {selectedSections.length} sections based on your current visibility data.
                  Estimated pages: {Math.ceil(selectedSections.length * 2.5)}
                </p>
              </div>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleGenerate}>
            Generate Report
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
