import { useState } from "react";
import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
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
import { apiClient } from "@/services/api";
import { useDomainStore } from "@/stores/domainStore";
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
  const queryClient = useQueryClient();
  const { selectedDomain } = useDomainStore();
  const activeDomainId = selectedDomain?.id;

  const [reportName, setReportName] = useState("");
  const [description, setDescription] = useState("");
  const [template, setTemplate] = useState("1"); // Default to first template
  const [format, setFormat] = useState("pdf");
  const [schedule, setSchedule] = useState("once");
  const [scheduleTime, setScheduleTime] = useState("09:00");
  const [scheduleDay, setScheduleDay] = useState("1"); // Monday for weekly, 1st for monthly
  const [recipients, setRecipients] = useState("");
  const [selectedSections, setSelectedSections] = useState<Set<string>>(
    new Set(reportSections.filter(s => s.default).map(s => s.id))
  );

  // Fetch report templates to get template IDs
  const { data: templates = [] } = useQuery({
    queryKey: ['reportTemplates'],
    queryFn: async () => {
      const result = await apiClient.getReportTemplates();
      return result as any[];
    },
  });

  // Create report mutation (handles both one-time and scheduled reports)
  const createMutation = useMutation({
    mutationFn: (data: any) => {
      // For one-time reports, use the generate_now endpoint
      if (data.frequency === 'once') {
        return apiClient.generateReport({
          domain_id: data.domain,
          template_id: data.template,
          sections: data.sections,
          format: data.formats[0], // Use first format for one-time generation
          data_period_days: 30, // Default to 30 days
        });
      }
      // For scheduled reports, use the scheduled endpoint
      return apiClient.createScheduledReport(data);
    },
    onSuccess: () => {
      // Invalidate both queries to refresh the lists
      queryClient.invalidateQueries({ queryKey: ['scheduledReports'] });
      queryClient.invalidateQueries({ queryKey: ['generatedReports'] });
      toast({
        title: schedule === 'once' ? "Report Generated" : "Report Scheduled",
        description: `"${reportName}" has been ${schedule === 'once' ? 'generated' : 'scheduled'} successfully.`,
      });
      resetForm();
      onOpenChange(false);
    },
    onError: (error: any) => {
      toast({
        title: "Error",
        description: error.message || `Failed to ${schedule === 'once' ? 'generate' : 'schedule'} report`,
        variant: "destructive",
      });
    },
  });

  const toggleSection = (id: string) => {
    const newSelected = new Set(selectedSections);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedSections(newSelected);
  };

  const resetForm = () => {
    setReportName("");
    setDescription("");
    setTemplate("1");
    setFormat("pdf");
    setSchedule("once");
    setScheduleTime("09:00");
    setScheduleDay("1");
    setRecipients("");
    setSelectedSections(new Set(reportSections.filter(s => s.default).map(s => s.id)));
  };

  const handleGenerate = () => {
    if (!activeDomainId) {
      toast({
        title: "No Domain Selected",
        description: "Please select a domain first.",
        variant: "destructive",
      });
      return;
    }

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

    // Prepare the data for API
    const [hours, minutes] = scheduleTime.split(':');
    const reportData = {
      domain: activeDomainId,
      name: reportName,
      description: description || "",
      template: parseInt(template),
      frequency: schedule,
      schedule_time: `${hours.padStart(2, '0')}:${minutes.padStart(2, '0')}:00`,
      schedule_day: schedule === 'weekly' || schedule === 'monthly' ? parseInt(scheduleDay) : null,
      sections: Array.from(selectedSections),
      formats: [format.toUpperCase()],
      recipients: recipients ? recipients.split(',').map(email => email.trim()).filter(Boolean) : [],
    };

    createMutation.mutate(reportData);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-inter text-2xl flex items-center gap-2">
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
              className="border border-border"
            />
          </div>

          {/* Template */}
          <div className="space-y-2">
            <Label>Report Template*</Label>
            <Select value={template} onValueChange={setTemplate}>
              <SelectTrigger className="border border-border">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {templates.map((tmpl: any) => (
                  <SelectItem key={tmpl.id} value={String(tmpl.id)}>
                    {tmpl.name}
                  </SelectItem>
                ))}
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
              className="border border-border min-h-[60px]"
            />
          </div>

          {/* Report Sections */}
          <div className="space-y-3">
            <Label>Report Sections ({selectedSections.size} selected)</Label>
            <div className="grid grid-cols-2 gap-3">
              {reportSections.map((section) => (
                <div
                  key={section.id}
                  className="flex items-center space-x-3 p-3 rounded-lg border border-border hover:bg-accent/50 cursor-pointer"
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
              <Label>Format*</Label>
              <Select value={format} onValueChange={setFormat}>
                <SelectTrigger className="border border-border">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="pdf">PDF</SelectItem>
                  <SelectItem value="excel">Excel</SelectItem>
                  <SelectItem value="powerpoint">PowerPoint</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Schedule*</Label>
              <Select value={schedule} onValueChange={setSchedule}>
                <SelectTrigger className="border border-border">
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

          {/* Schedule Time (for all except 'once') */}
          {schedule !== "once" && (
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="scheduleTime">Time</Label>
                <Input
                  id="scheduleTime"
                  type="time"
                  value={scheduleTime}
                  onChange={(e) => setScheduleTime(e.target.value)}
                  className="border border-border"
                />
              </div>

              {(schedule === "weekly" || schedule === "monthly") && (
                <div className="space-y-2">
                  <Label htmlFor="scheduleDay">
                    {schedule === "weekly" ? "Day of Week" : "Day of Month"}
                  </Label>
                  <Select value={scheduleDay} onValueChange={setScheduleDay}>
                    <SelectTrigger className="border border-border">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {schedule === "weekly" ? (
                        <>
                          <SelectItem value="0">Monday</SelectItem>
                          <SelectItem value="1">Tuesday</SelectItem>
                          <SelectItem value="2">Wednesday</SelectItem>
                          <SelectItem value="3">Thursday</SelectItem>
                          <SelectItem value="4">Friday</SelectItem>
                          <SelectItem value="5">Saturday</SelectItem>
                          <SelectItem value="6">Sunday</SelectItem>
                        </>
                      ) : (
                        Array.from({ length: 28 }, (_, i) => (
                          <SelectItem key={i + 1} value={String(i + 1)}>
                            {i + 1}
                          </SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>
          )}

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
                className="border border-border"
              />
              <p className="text-xs text-muted-foreground">
                Separate multiple emails with commas
              </p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={createMutation.isPending}>
            Cancel
          </Button>
          <Button onClick={handleGenerate} className="gradient-primary" disabled={createMutation.isPending}>
            {createMutation.isPending
              ? (schedule === "once" ? "Generating..." : "Creating...")
              : (schedule === "once" ? "Generate Report" : "Create & Schedule")
            }
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
