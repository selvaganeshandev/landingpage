import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { X } from "lucide-react";

interface EditReportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  report: {
    id: number;
    name: string;
    description: string;
    schedule: string;
    format: string[];
    recipients: string[];
    status: string;
  } | null;
  onSave: (report: any) => void;
}

export const EditReportDialog = ({ open, onOpenChange, report, onSave }: EditReportDialogProps) => {
  const { toast } = useToast();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [schedule, setSchedule] = useState("");
  const [selectedFormats, setSelectedFormats] = useState<string[]>([]);
  const [recipients, setRecipients] = useState<string[]>([]);
  const [newRecipient, setNewRecipient] = useState("");
  const [status, setStatus] = useState("active");

  useEffect(() => {
    if (report) {
      setName(report.name);
      setDescription(report.description);
      setSchedule(report.schedule);
      setSelectedFormats(report.format);
      setRecipients(report.recipients);
      setStatus(report.status);
    }
  }, [report]);

  if (!report) return null;

  const handleSave = () => {
    const updatedReport = {
      ...report,
      name,
      description,
      schedule,
      format: selectedFormats,
      recipients,
      status,
    };

    onSave(updatedReport);
    toast({
      title: "Report Updated",
      description: "Your scheduled report has been updated successfully.",
    });
    onOpenChange(false);
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
          <DialogTitle>Edit Scheduled Report</DialogTitle>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Report Name */}
          <div className="space-y-2">
            <Label htmlFor="name">Report Name</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter report name"
            />
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe what this report covers"
              rows={3}
            />
          </div>

          {/* Schedule */}
          <div className="space-y-2">
            <Label htmlFor="schedule">Schedule</Label>
            <Select value={schedule} onValueChange={setSchedule}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Daily - 8 AM">Daily - 8 AM</SelectItem>
                <SelectItem value="Weekly - Monday 9 AM">Weekly - Monday 9 AM</SelectItem>
                <SelectItem value="Monthly - 1st of month">Monthly - 1st of month</SelectItem>
                <SelectItem value="Quarterly">Quarterly</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Status */}
          <div className="space-y-2">
            <Label htmlFor="status">Status</Label>
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="paused">Paused</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Output Formats */}
          <div className="space-y-2">
            <Label>Output Formats</Label>
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
            <Label>Recipients</Label>
            <div className="flex gap-2 mb-2">
              <Input
                value={newRecipient}
                onChange={(e) => setNewRecipient(e.target.value)}
                placeholder="Enter email address"
                onKeyPress={(e) => e.key === 'Enter' && addRecipient()}
              />
              <Button type="button" onClick={addRecipient}>Add</Button>
            </div>
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
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave}>
            Save Changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
