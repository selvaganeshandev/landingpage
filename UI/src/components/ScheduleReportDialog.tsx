import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { X, Calendar, Clock } from "lucide-react";

interface ScheduleReportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSchedule: (report: any) => void;
}

export const ScheduleReportDialog = ({ open, onOpenChange, onSchedule }: ScheduleReportDialogProps) => {
  const { toast } = useToast();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [template, setTemplate] = useState("executive");
  const [schedule, setSchedule] = useState("weekly");
  const [selectedFormats, setSelectedFormats] = useState<string[]>(["PDF"]);
  const [recipients, setRecipients] = useState<string[]>([]);
  const [newRecipient, setNewRecipient] = useState("");

  const handleSchedule = () => {
    if (!name || recipients.length === 0) {
      toast({
        title: "Missing Information",
        description: "Please provide a report name and at least one recipient.",
        variant: "destructive",
      });
      return;
    }

    const newReport = {
      id: Date.now(),
      name,
      description,
      schedule: getScheduleLabel(schedule),
      format: selectedFormats,
      recipients,
      status: "active",
      lastGenerated: "Not yet run",
    };

    onSchedule(newReport);
    toast({
      title: "Report Scheduled",
      description: `${name} has been scheduled successfully.`,
    });
    
    // Reset form
    setName("");
    setDescription("");
    setTemplate("executive");
    setSchedule("weekly");
    setSelectedFormats(["PDF"]);
    setRecipients([]);
    onOpenChange(false);
  };

  const getScheduleLabel = (value: string) => {
    const labels: Record<string, string> = {
      daily: "Daily - 8 AM",
      weekly: "Weekly - Monday 9 AM",
      monthly: "Monthly - 1st of month",
      quarterly: "Quarterly",
    };
    return labels[value] || value;
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

          {/* Schedule Frequency */}
          <div className="space-y-2">
            <Label htmlFor="schedule">Schedule Frequency *</Label>
            <Select value={schedule} onValueChange={setSchedule}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="daily">
                  <div className="flex items-center gap-2">
                    <Clock className="h-4 w-4" />
                    Daily - 8 AM
                  </div>
                </SelectItem>
                <SelectItem value="weekly">
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4" />
                    Weekly - Monday 9 AM
                  </div>
                </SelectItem>
                <SelectItem value="monthly">
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4" />
                    Monthly - 1st of month
                  </div>
                </SelectItem>
                <SelectItem value="quarterly">
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4" />
                    Quarterly
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
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
            <Label>Recipients *</Label>
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
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSchedule}>
            Schedule Report
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
