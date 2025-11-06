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
import { Mail, MessageSquare, Smartphone } from "lucide-react";

interface NewAlertRuleDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAdd?: (rule: any) => void;
  domainId?: number | string;
}

import { apiClient } from "@/services/api";

export const NewAlertRuleDialog = ({ open, onOpenChange, onAdd, domainId }: NewAlertRuleDialogProps) => {
  const { toast } = useToast();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [triggerType, setTriggerType] = useState("");
  const [threshold, setThreshold] = useState("");
  const [timeWindow, setTimeWindow] = useState("24");
  const [channels, setChannels] = useState<string[]>([]);

  const handleChannelToggle = (channel: string) => {
    setChannels(prev =>
      prev.includes(channel)
        ? prev.filter(c => c !== channel)
        : [...prev, channel]
    );
  };

  const handleSubmit = async () => {
    if (!name.trim() || !triggerType || !threshold) {
      toast({
        title: "Missing Information",
        description: "Please fill in all required fields.",
        variant: "destructive",
      });
      return;
    }

    if (channels.length === 0) {
      toast({
        title: "No Notification Channels",
        description: "Please select at least one notification channel.",
        variant: "destructive",
      });
      return;
    }

    const payload = {
      name: name.trim(),
      description: description.trim(),
      conditions: {
        trigger_type: triggerType,
        threshold_percent: Number(threshold),
        time_window_hours: Number(timeWindow),
      },
      notification_channel_list: channels,
      enabled: true,
      ...(domainId ? { domain: domainId } : {}),
    } as any;

    try {
      const created = await apiClient.createAlertRule(payload);
      if (onAdd) onAdd(created);
      toast({ title: "Alert Rule Created", description: `"${name}" has been created successfully.` });
      // Reset form
      setName("");
      setDescription("");
      setTriggerType("");
      setThreshold("");
      setTimeWindow("24");
      setChannels([]);
      onOpenChange(false);
    } catch (e:any) {
      toast({ title: 'Failed to create rule', description: String(e.message||e), variant: 'destructive' });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-outfit text-2xl">Create New Alert Rule</DialogTitle>
          <DialogDescription>
            Configure conditions and notifications for monitoring your brand visibility
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Rule Name */}
          <div className="space-y-2">
            <Label htmlFor="name">Rule Name*</Label>
            <Input
              id="name"
              placeholder="e.g., Visibility Drop Alert"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="border border-border"
            />
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              placeholder="Describe when this alert should trigger..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="border border-border min-h-[80px]"
            />
          </div>

          {/* Trigger Type */}
          <div className="space-y-2">
            <Label htmlFor="trigger">Trigger Condition*</Label>
            <Select value={triggerType} onValueChange={setTriggerType}>
              <SelectTrigger className="border border-border">
                <SelectValue placeholder="Select trigger type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="visibility_drop">Visibility Score Drop</SelectItem>
                <SelectItem value="visibility_increase">Visibility Score Increase</SelectItem>
                <SelectItem value="sentiment_negative">Negative Sentiment Spike</SelectItem>
                <SelectItem value="sentiment_positive">Positive Sentiment Increase</SelectItem>
                <SelectItem value="competitor_surge">Competitor Mention Surge</SelectItem>
                <SelectItem value="position_drop">Position Drop</SelectItem>
                <SelectItem value="mention_spike">Mention Volume Spike</SelectItem>
                <SelectItem value="anomaly">Anomaly Detection</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Threshold */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="threshold">Threshold Value*</Label>
              <div className="flex gap-2 items-center">
                <Input
                  id="threshold"
                  type="number"
                  placeholder="e.g., 10"
                  value={threshold}
                  onChange={(e) => setThreshold(e.target.value)}
                  className="border border-border"
                />
                <span className="text-muted-foreground">%</span>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="timeWindow">Time Window</Label>
              <Select value={timeWindow} onValueChange={setTimeWindow}>
                <SelectTrigger className="border border-border">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">1 hour</SelectItem>
                  <SelectItem value="6">6 hours</SelectItem>
                  <SelectItem value="12">12 hours</SelectItem>
                  <SelectItem value="24">24 hours</SelectItem>
                  <SelectItem value="48">48 hours</SelectItem>
                  <SelectItem value="168">7 days</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Notification Channels */}
          <div className="space-y-3">
            <Label>Notification Channels*</Label>
            <div className="space-y-3">
              <div className="flex items-center space-x-3 p-3 rounded-lg border border-border">
                <Checkbox
                  id="email"
                  checked={channels.includes("email")}
                  onCheckedChange={() => handleChannelToggle("email")}
                />
                <div className="flex items-center gap-2 flex-1">
                  <Mail className="h-4 w-4 text-primary" />
                  <Label htmlFor="email" className="cursor-pointer flex-1 font-normal">
                    Email Notifications
                  </Label>
                </div>
              </div>

              <div className="flex items-center space-x-3 p-3 rounded-lg border border-border">
                <Checkbox
                  id="slack"
                  checked={channels.includes("slack")}
                  onCheckedChange={() => handleChannelToggle("slack")}
                />
                <div className="flex items-center gap-2 flex-1">
                  <MessageSquare className="h-4 w-4 text-primary" />
                  <Label htmlFor="slack" className="cursor-pointer flex-1 font-normal">
                    Slack Notifications
                  </Label>
                </div>
              </div>

              <div className="flex items-center space-x-3 p-3 rounded-lg border border-border">
                <Checkbox
                  id="sms"
                  checked={channels.includes("sms")}
                  onCheckedChange={() => handleChannelToggle("sms")}
                />
                <div className="flex items-center gap-2 flex-1">
                  <Smartphone className="h-4 w-4 text-primary" />
                  <Label htmlFor="sms" className="cursor-pointer flex-1 font-normal">
                    SMS Notifications
                  </Label>
                </div>
              </div>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} className="gradient-primary">
            Create Alert Rule
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
