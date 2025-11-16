import { useState } from "react";
import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/services/api";
import { useDomainStore } from "@/stores/domainStore";
import { X, Calendar, Clock } from "lucide-react";

interface ScheduleReportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const ScheduleReportDialog = ({ open, onOpenChange }: ScheduleReportDialogProps) => {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { selectedDomain } = useDomainStore();
  const activeDomainId = selectedDomain?.id;

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [template, setTemplate] = useState("1");
  const [schedule, setSchedule] = useState("weekly");
  const [scheduleTime, setScheduleTime] = useState("09:00");
  const [scheduleDay, setScheduleDay] = useState("0"); // Monday for weekly, 1st for monthly
  const [selectedFormats, setSelectedFormats] = useState<string[]>(["PDF"]);
  const [recipients, setRecipients] = useState<string[]>([]);
  const [newRecipient, setNewRecipient] = useState("");

  // Fetch report templates
  const { data: templates = [] } = useQuery({
    queryKey: ['reportTemplates'],
    queryFn: () => apiClient.getReportTemplates(),
  });

  // Create scheduled report mutation
  const createMutation = useMutation({
    mutationFn: (data: any) => apiClient.createScheduledReport(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scheduledReports'] });
      toast({
        title: "Report Scheduled",
        description: `"${name}" has been scheduled successfully.`,
      });
      resetForm();
      onOpenChange(false);
    },
    onError: (error: any) => {
      toast({
        title: "Error",
        description: error.message || "Failed to schedule report",
        variant: "destructive",
      });
    },
  });

  const resetForm = () => {
    setName("");
    setDescription("");
    setTemplate("1");
    setSchedule("weekly");
    setScheduleTime("09:00");
    setScheduleDay("0");
    setSelectedFormats(["PDF"]);
    setRecipients([]);
  };

  const handleSchedule = () => {
    if (!activeDomainId) {
      toast({
        title: "No Domain Selected",
        description: "Please select a domain first.",
        variant: "destructive",
      });
      return;
    }

    if (!name.trim()) {
      toast({
        title: "Missing Report Name",
        description: "Please provide a name for your report.",
        variant: "destructive",
      });
      return;
    }

    if (selectedFormats.length === 0) {
      toast({
        title: "No Format Selected",
        description: "Please select at least one output format.",
        variant: "destructive",
      });
      return;
    }

    // Prepare the data for API
    const [hours, minutes] = scheduleTime.split(':');
    const reportData = {
      domain: activeDomainId,
      name,
      description: description || "",
      template: parseInt(template),
      frequency: schedule,
      schedule_time: `${hours.padStart(2, '0')}:${minutes.padStart(2, '0')}:00`,
      schedule_day: schedule === 'weekly' || schedule === 'monthly' ? parseInt(scheduleDay) : null,
      sections: [], // Empty array for now, can be customized later
      formats: selectedFormats.map(f => f.toUpperCase()),
      recipients,
    };

    createMutation.mutate(reportData);
  };

  const toggleFormat = (format: string) => {
    setSelectedFormats(prev =>
      prev.includes(format)
        ? prev.filter(f => f !== format)
        : [...prev, format]
    );
  };

  const addRecipient = () => {
    if (newRecipient && !recipients.includes(newRecipient)) {
      setRecipients([...recipients, newRecipient]);
      setNewRecipient("");
    }
  };

  const removeRecipient = (email: string) => {
    setRecipients(recipients.filter(r => r !== email));
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Schedule New Report</DialogTitle>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Report Name */}
          <div className="space-y-2">
            <Label htmlFor="name">Report Name *</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Weekly Performance Report"
            />
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What does this report cover?"
              rows={3}
            />
          </div>

          {/* Template Selection */}
          <div className="space-y-2">
            <Label htmlFor="template">Report Template *</Label>
            <Select value={template} onValueChange={setTemplate}>
              <SelectTrigger>
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

          {/* Schedule Frequency */}
          <div className="space-y-2">
            <Label htmlFor="schedule">Schedule Frequency *</Label>
            <Select value={schedule} onValueChange={setSchedule}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="daily">Daily</SelectItem>
                <SelectItem value="weekly">Weekly</SelectItem>
                <SelectItem value="monthly">Monthly</SelectItem>
                <SelectItem value="quarterly">Quarterly</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Schedule Time and Day */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="scheduleTime">Time *</Label>
              <Input
                id="scheduleTime"
                type="time"
                value={scheduleTime}
                onChange={(e) => setScheduleTime(e.target.value)}
              />
            </div>

            {(schedule === "weekly" || schedule === "monthly") && (
              <div className="space-y-2">
                <Label htmlFor="scheduleDay">
                  {schedule === "weekly" ? "Day of Week *" : "Day of Month *"}
                </Label>
                <Select value={scheduleDay} onValueChange={setScheduleDay}>
                  <SelectTrigger>
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

          {/* Output Formats */}
          <div className="space-y-2">
            <Label>Output Formats *</Label>
            <div className="flex flex-wrap gap-2">
              {["PDF", "Excel", "PowerPoint", "Email"].map((format) => (
                <Badge
                  key={format}
                  variant={selectedFormats.includes(format) ? "default" : "outline"}
                  className="cursor-pointer"
                  onClick={() => toggleFormat(format)}
                >
                  {format}
                </Badge>
              ))}
            </div>
          </div>

          {/* Recipients */}
          <div className="space-y-2">
            <Label>Recipients (Optional)</Label>
            <div className="flex gap-2 mb-2">
              <Input
                value={newRecipient}
                onChange={(e) => setNewRecipient(e.target.value)}
                placeholder="Enter email address"
                onKeyPress={(e) => e.key === 'Enter' && addRecipient()}
              />
              <Button type="button" onClick={addRecipient}>Add</Button>
            </div>
            {recipients.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {recipients.map((email) => (
                  <Badge key={email} variant="secondary" className="pl-3 pr-1">
                    {email}
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-auto p-1 ml-1"
                      onClick={() => removeRecipient(email)}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </Badge>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No recipients added yet</p>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={createMutation.isPending}>
            Cancel
          </Button>
          <Button onClick={handleSchedule} disabled={createMutation.isPending}>
            {createMutation.isPending ? "Scheduling..." : "Schedule Report"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
