import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { useToast } from "@/hooks/use-toast";
import { FileText, Calendar, Mail } from "lucide-react";

interface CreateReportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const reportSections = [
  { id: "overview", name: "Executive Overview", default: true },
  { id: "visibility", name: "Visibility Metrics", default: true },
  { id: "mentions", name: "Mention Analysis", default: true },
  { id: "sentiment", name: "Sentiment Breakdown", default: true },
  { id: "competitors", name: "Competitor Comparison", default: false },
  { id: "topics", name: "Topic Performance", default: false },
  { id: "content", name: "Content Gaps", default: false },
  { id: "multilingual", name: "Multilingual Data", default: false },
  { id: "trends", name: "Historical Trends", default: false },
];

export const CreateReportDialog = ({ open, onOpenChange }: CreateReportDialogProps) => {
  const { toast } = useToast();
  const [reportName, setReportName] = useState("");
  const [description, setDescription] = useState("");
  const [template, setTemplate] = useState("custom");
  const [format, setFormat] = useState("pdf");
  const [schedule, setSchedule] = useState("once");
  const [recipients, setRecipients] = useState("");
  const [selectedSections, setSelectedSections] = useState<Set<string>>(
    new Set(reportSections.filter(s => s.default).map(s => s.id))
  );

  const toggleSection = (id: string) => {
    const newSelected = new Set(selectedSections);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedSections(newSelected);
  };

  const handleGenerate = () => {
    if (!reportName.trim()) {
      toast({
        title: "Missing Report Name",
        description: "Please provide a name for your report.",
        variant: "destructive",
      });
      return;
    }

    if (selectedSections.size === 0) {
      toast({
        title: "No Sections Selected",
        description: "Please select at least one section for your report.",
        variant: "destructive",
      });
      return;
    }

    toast({
      title: "Generating Report",
      description: `"${reportName}" is being created with ${selectedSections.size} sections.`,
    });

    // Reset form
    setReportName("");
    setDescription("");
    setTemplate("custom");
    setSelectedSections(new Set(reportSections.filter(s => s.default).map(s => s.id)));
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-outfit text-2xl flex items-center gap-2">
            <FileText className="h-6 w-6 text-primary" />
            Create Custom Report
          </DialogTitle>
          <DialogDescription>
            Configure your report settings and select sections to include
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Report Name */}
          <div className="space-y-2">
            <Label htmlFor="reportName">Report Name*</Label>
            <Input
              id="reportName"
              placeholder="e.g., Q4 Performance Report"
              value={reportName}
              onChange={(e) => setReportName(e.target.value)}
              className="border-border/50"
            />
          </div>

          {/* Template */}
          <div className="space-y-2">
            <Label>Start From Template</Label>
            <Select value={template} onValueChange={setTemplate}>
              <SelectTrigger className="border-border/50">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="custom">Custom Report</SelectItem>
                <SelectItem value="executive">Executive Dashboard</SelectItem>
                <SelectItem value="detailed">Detailed Analytics</SelectItem>
                <SelectItem value="competitor">Competitor Focus</SelectItem>
                <SelectItem value="content">Content Strategy</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Description (Optional)</Label>
            <Textarea
              id="description"
              placeholder="Brief description of this report..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="border-border/50 min-h-[60px]"
            />
          </div>

          {/* Report Sections */}
          <div className="space-y-3">
            <Label>Report Sections ({selectedSections.size} selected)</Label>
            <div className="grid grid-cols-2 gap-3">
              {reportSections.map((section) => (
                <div
                  key={section.id}
                  className="flex items-center space-x-3 p-3 rounded-lg border border-border/50 hover:bg-accent/50 cursor-pointer"
                  onClick={() => toggleSection(section.id)}
                >
                  <Checkbox
                    checked={selectedSections.has(section.id)}
                    onCheckedChange={() => toggleSection(section.id)}
                  />
                  <Label className="cursor-pointer flex-1 font-normal">
                    {section.name}
                  </Label>
                </div>
              ))}
            </div>
          </div>

          {/* Format & Schedule */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Format</Label>
              <Select value={format} onValueChange={setFormat}>
                <SelectTrigger className="border-border/50">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="pdf">PDF</SelectItem>
                  <SelectItem value="excel">Excel</SelectItem>
                  <SelectItem value="powerpoint">PowerPoint</SelectItem>
                  <SelectItem value="csv">CSV Data</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Schedule</Label>
              <Select value={schedule} onValueChange={setSchedule}>
                <SelectTrigger className="border-border/50">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="once">Generate Once</SelectItem>
                  <SelectItem value="daily">Daily</SelectItem>
                  <SelectItem value="weekly">Weekly</SelectItem>
                  <SelectItem value="monthly">Monthly</SelectItem>
                  <SelectItem value="quarterly">Quarterly</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Recipients */}
          {schedule !== "once" && (
            <div className="space-y-2">
              <Label htmlFor="recipients">Email Recipients</Label>
              <Input
                id="recipients"
                type="email"
                placeholder="team@example.com, marketing@example.com"
                value={recipients}
                onChange={(e) => setRecipients(e.target.value)}
                className="border-border/50"
              />
              <p className="text-xs text-muted-foreground">
                Separate multiple emails with commas
              </p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleGenerate} className="gradient-primary">
            {schedule === "once" ? "Generate Report" : "Create & Schedule"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
