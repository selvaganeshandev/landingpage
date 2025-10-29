import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { Separator } from "@/components/ui/separator";
import { Input } from "@/components/ui/input";
import { Settings, Bell, Mail, MessageSquare } from "lucide-react";

interface ConfigureDetectionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ConfigureDetectionDialog({
  open,
  onOpenChange,
}: ConfigureDetectionDialogProps) {
  const { toast } = useToast();
  const [sensitivity, setSensitivity] = useState("medium");
  const [scanFrequency, setScanFrequency] = useState("hourly");
  const [priorityThreshold, setPriorityThreshold] = useState("medium");
  const [notificationChannel, setNotificationChannel] = useState("email-app");
  const [emailNotifications, setEmailNotifications] = useState(true);
  const [slackNotifications, setSlackNotifications] = useState(false);
  const [webhookNotifications, setWebhookNotifications] = useState(false);
  const [autoCorrection, setAutoCorrection] = useState(false);
  const [requireApproval, setRequireApproval] = useState(true);
  const [notificationEmail, setNotificationEmail] = useState("team@example.com");
  const [slackWebhook, setSlackWebhook] = useState("");

  const handleSave = () => {
    toast({
      title: "Settings saved",
      description: "Detection configuration has been updated successfully",
    });
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Configure Detection Settings
          </DialogTitle>
          <DialogDescription>
            Customize how misinformation is detected and how you're notified
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Detection Settings */}
          <div className="space-y-4">
            <h3 className="font-semibold">Detection Settings</h3>
            
            <div className="space-y-2">
              <Label htmlFor="sensitivity">Detection Sensitivity</Label>
              <Select value={sensitivity} onValueChange={setSensitivity}>
                <SelectTrigger id="sensitivity">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="high">High (All potential issues)</SelectItem>
                  <SelectItem value="medium">Medium (Likely issues)</SelectItem>
                  <SelectItem value="low">Low (Only confirmed issues)</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Higher sensitivity may result in more false positives but catches more potential issues
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="scan-frequency">Scan Frequency</Label>
              <Select value={scanFrequency} onValueChange={setScanFrequency}>
                <SelectTrigger id="scan-frequency">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="realtime">Real-time (Continuous)</SelectItem>
                  <SelectItem value="hourly">Every hour</SelectItem>
                  <SelectItem value="6hours">Every 6 hours</SelectItem>
                  <SelectItem value="daily">Daily</SelectItem>
                  <SelectItem value="weekly">Weekly</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                How often to scan AI platforms for new misinformation
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="priority-threshold">Alert Priority Threshold</Label>
              <Select value={priorityThreshold} onValueChange={setPriorityThreshold}>
                <SelectTrigger id="priority-threshold">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All severities</SelectItem>
                  <SelectItem value="medium">Medium and High only</SelectItem>
                  <SelectItem value="high">High only</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Only create alerts for issues above this severity level
              </p>
            </div>
          </div>

          <Separator />

          {/* Notification Settings */}
          <div className="space-y-4">
            <h3 className="font-semibold flex items-center gap-2">
              <Bell className="h-4 w-4" />
              Notification Settings
            </h3>
            
            <div className="flex items-center justify-between p-3 rounded-lg border">
              <div className="flex items-center gap-3">
                <Mail className="h-4 w-4 text-muted-foreground" />
                <div className="space-y-0.5">
                  <Label htmlFor="email-notif">Email Notifications</Label>
                  <p className="text-xs text-muted-foreground">
                    Receive alerts via email
                  </p>
                </div>
              </div>
              <Switch
                id="email-notif"
                checked={emailNotifications}
                onCheckedChange={setEmailNotifications}
              />
            </div>

            {emailNotifications && (
              <div className="ml-10 space-y-2">
                <Label htmlFor="email">Email Address</Label>
                <Input
                  id="email"
                  type="email"
                  value={notificationEmail}
                  onChange={(e) => setNotificationEmail(e.target.value)}
                  placeholder="team@example.com"
                />
              </div>
            )}

            <div className="flex items-center justify-between p-3 rounded-lg border">
              <div className="flex items-center gap-3">
                <MessageSquare className="h-4 w-4 text-muted-foreground" />
                <div className="space-y-0.5">
                  <Label htmlFor="slack-notif">Slack Integration</Label>
                  <p className="text-xs text-muted-foreground">
                    Send alerts to Slack channel
                  </p>
                </div>
              </div>
              <Switch
                id="slack-notif"
                checked={slackNotifications}
                onCheckedChange={setSlackNotifications}
              />
            </div>

            {slackNotifications && (
              <div className="ml-10 space-y-2">
                <Label htmlFor="slack-webhook">Slack Webhook URL</Label>
                <Input
                  id="slack-webhook"
                  value={slackWebhook}
                  onChange={(e) => setSlackWebhook(e.target.value)}
                  placeholder="https://hooks.slack.com/services/..."
                />
              </div>
            )}

            <div className="flex items-center justify-between p-3 rounded-lg border">
              <div className="flex items-center gap-3">
                <Settings className="h-4 w-4 text-muted-foreground" />
                <div className="space-y-0.5">
                  <Label htmlFor="webhook-notif">Webhook Integration</Label>
                  <p className="text-xs text-muted-foreground">
                    Send to custom webhook endpoint
                  </p>
                </div>
              </div>
              <Switch
                id="webhook-notif"
                checked={webhookNotifications}
                onCheckedChange={setWebhookNotifications}
              />
            </div>
          </div>

          <Separator />

          {/* Automation Settings */}
          <div className="space-y-4">
            <h3 className="font-semibold">Automation Settings</h3>
            
            <div className="flex items-center justify-between p-3 rounded-lg border">
              <div className="space-y-0.5">
                <Label htmlFor="auto-correction">Automatic Correction Submission</Label>
                <p className="text-xs text-muted-foreground">
                  Automatically submit corrections for detected issues
                </p>
              </div>
              <Switch
                id="auto-correction"
                checked={autoCorrection}
                onCheckedChange={setAutoCorrection}
              />
            </div>

            <div className="flex items-center justify-between p-3 rounded-lg border">
              <div className="space-y-0.5">
                <Label htmlFor="require-approval">Require Manual Approval</Label>
                <p className="text-xs text-muted-foreground">
                  Team must approve before submitting corrections
                </p>
              </div>
              <Switch
                id="require-approval"
                checked={requireApproval}
                onCheckedChange={setRequireApproval}
              />
            </div>
          </div>

          <Separator />

          {/* Advanced Options */}
          <div className="space-y-4 p-4 bg-muted rounded-lg">
            <h4 className="font-medium text-sm">Advanced Options</h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground mb-1">Batch Processing</p>
                <p className="font-medium">100 mentions per batch</p>
              </div>
              <div>
                <p className="text-muted-foreground mb-1">Retention Period</p>
                <p className="font-medium">90 days</p>
              </div>
              <div>
                <p className="text-muted-foreground mb-1">AI Confidence Threshold</p>
                <p className="font-medium">75%</p>
              </div>
              <div>
                <p className="text-muted-foreground mb-1">Max Alerts per Day</p>
                <p className="font-medium">50 alerts</p>
              </div>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave}>
            Save Configuration
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
