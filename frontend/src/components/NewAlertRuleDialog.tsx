import { useEffect, useState } from "react";
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
  /** Pass an existing rule to edit it; omit to create a new one. */
  rule?: any | null;
}

import { apiClient } from "@/services/api";

export const NewAlertRuleDialog = ({ open, onOpenChange, onAdd, domainId, rule }: NewAlertRuleDialogProps) => {
  const { toast } = useToast();
  const isEdit = Boolean(rule?.id);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [triggerType, setTriggerType] = useState("");
  const [threshold, setThreshold] = useState("");
  const [channels, setChannels] = useState<string[]>([]);

  // Load the rule being edited each time the dialog opens, and clear the form
  // when opening for a new rule — otherwise the previous rule's values would
  // persist and silently become the starting point for the next one.
  useEffect(() => {
    if (!open) return;
    if (rule) {
      setName(rule.name || "");
      setDescription(rule.description || "");
      setTriggerType(rule.conditions?.trigger_type || "");
      setThreshold(
        rule.conditions?.threshold_percent !== undefined && rule.conditions?.threshold_percent !== null
          ? String(rule.conditions.threshold_percent)
          : "",
      );
      setChannels(rule.notification_channel_list || []);
    } else {
      setName("");
      setDescription("");
      setTriggerType("");
      setThreshold("");
      setChannels([]);
    }
  }, [open, rule]);

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
        // Preserve the window an existing rule was created with rather than
        // silently resetting it to the weekly default on every edit.
        time_window_hours: rule?.conditions?.time_window_hours ?? 168,
      },
      notification_channel_list: channels,
      // Editing must not flip a disabled rule back on.
      enabled: isEdit ? Boolean(rule?.enabled) : true,
      ...(domainId ? { domain: domainId } : {}),
    } as any;

    try {
      const saved = isEdit
        ? await apiClient.updateAlertRule(rule.id, payload)
        : await apiClient.createAlertRule(payload);
      if (onAdd) onAdd(saved);
      toast({
        title: isEdit ? "Alert Rule Updated" : "Alert Rule Created",
        description: `"${name}" has been ${isEdit ? "updated" : "created"} successfully.`,
      });
      onOpenChange(false);
    } catch (e:any) {
      toast({
        title: isEdit ? 'Failed to update rule' : 'Failed to create rule',
        description: String(e.message||e),
        variant: 'destructive',
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-inter text-2xl">{isEdit ? "Edit Alert Rule" : "Create New Alert Rule"}</DialogTitle>
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
              </SelectContent>
            </Select>
          </div>

          {/* Threshold */}
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

              <div className="flex items-center space-x-3 p-3 rounded-lg border border-border opacity-50">
                <Checkbox
                  id="slack"
                  checked={false}
                  disabled={true}
                />
                <div className="flex items-center gap-2 flex-1">
                  <MessageSquare className="h-4 w-4 text-muted-foreground" />
                  <Label htmlFor="slack" className="cursor-not-allowed flex-1 font-normal text-muted-foreground">
                    Slack Notifications (Coming Soon)
                  </Label>
                </div>
              </div>

              <div className="flex items-center space-x-3 p-3 rounded-lg border border-border opacity-50">
                <Checkbox
                  id="sms"
                  checked={false}
                  disabled={true}
                />
                <div className="flex items-center gap-2 flex-1">
                  <Smartphone className="h-4 w-4 text-muted-foreground" />
                  <Label htmlFor="sms" className="cursor-not-allowed flex-1 font-normal text-muted-foreground">
                    SMS Notifications (Coming Soon)
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
            {isEdit ? "Save Changes" : "Create Alert Rule"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
