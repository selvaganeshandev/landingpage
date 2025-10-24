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
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import { Mail, MessageSquare, Smartphone, Bell, Clock } from "lucide-react";

interface AlertConfigDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const AlertConfigDialog = ({ open, onOpenChange }: AlertConfigDialogProps) => {
  const { toast } = useToast();
  
  // General Settings
  const [alertsEnabled, setAlertsEnabled] = useState(true);
  const [quietHoursEnabled, setQuietHoursEnabled] = useState(false);
  const [quietHoursStart, setQuietHoursStart] = useState("22:00");
  const [quietHoursEnd, setQuietHoursEnd] = useState("08:00");
  const [digestFrequency, setDigestFrequency] = useState("daily");

  // Email Settings
  const [emailEnabled, setEmailEnabled] = useState(true);
  const [emailAddress, setEmailAddress] = useState("team@vegfitpro.com");

  // Slack Settings
  const [slackEnabled, setSlackEnabled] = useState(true);
  const [slackChannel, setSlackChannel] = useState("#ai-monitoring");
  const [slackWebhook, setSlackWebhook] = useState("");

  // SMS Settings
  const [smsEnabled, setSmsEnabled] = useState(false);
  const [phoneNumber, setPhoneNumber] = useState("");

  const handleSave = () => {
    toast({
      title: "Settings Saved",
      description: "Your alert configuration has been updated successfully.",
    });
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-outfit text-2xl">Alert Configuration</DialogTitle>
          <DialogDescription>
            Manage your alert preferences and notification channels
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="general" className="py-4">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="general">General</TabsTrigger>
            <TabsTrigger value="email">Email</TabsTrigger>
            <TabsTrigger value="slack">Slack</TabsTrigger>
            <TabsTrigger value="sms">SMS</TabsTrigger>
          </TabsList>

          {/* General Settings */}
          <TabsContent value="general" className="space-y-6 mt-6">
            <div className="flex items-center justify-between p-4 rounded-lg border border-border/50">
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <Bell className="h-4 w-4 text-primary" />
                  <Label className="text-base">Enable All Alerts</Label>
                </div>
                <p className="text-sm text-muted-foreground">
                  Master switch for all alert notifications
                </p>
              </div>
              <Switch
                checked={alertsEnabled}
                onCheckedChange={setAlertsEnabled}
              />
            </div>

            <div className="space-y-4 p-4 rounded-lg border border-border/50">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <Clock className="h-4 w-4 text-primary" />
                    <Label className="text-base">Quiet Hours</Label>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Pause non-critical alerts during specific hours
                  </p>
                </div>
                <Switch
                  checked={quietHoursEnabled}
                  onCheckedChange={setQuietHoursEnabled}
                />
              </div>

              {quietHoursEnabled && (
                <div className="grid grid-cols-2 gap-4 pt-4">
                  <div className="space-y-2">
                    <Label htmlFor="start">Start Time</Label>
                    <Input
                      id="start"
                      type="time"
                      value={quietHoursStart}
                      onChange={(e) => setQuietHoursStart(e.target.value)}
                      className="border-border/50"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="end">End Time</Label>
                    <Input
                      id="end"
                      type="time"
                      value={quietHoursEnd}
                      onChange={(e) => setQuietHoursEnd(e.target.value)}
                      className="border-border/50"
                    />
                  </div>
                </div>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="digest">Alert Digest Frequency</Label>
              <Select value={digestFrequency} onValueChange={setDigestFrequency}>
                <SelectTrigger className="border-border/50">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="realtime">Real-time (No digest)</SelectItem>
                  <SelectItem value="hourly">Hourly Summary</SelectItem>
                  <SelectItem value="daily">Daily Summary</SelectItem>
                  <SelectItem value="weekly">Weekly Summary</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Combine multiple alerts into a single notification
              </p>
            </div>
          </TabsContent>

          {/* Email Settings */}
          <TabsContent value="email" className="space-y-6 mt-6">
            <div className="flex items-center justify-between p-4 rounded-lg border border-border/50">
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <Mail className="h-4 w-4 text-primary" />
                  <Label className="text-base">Email Notifications</Label>
                </div>
                <p className="text-sm text-muted-foreground">
                  Receive alerts via email
                </p>
              </div>
              <Switch
                checked={emailEnabled}
                onCheckedChange={setEmailEnabled}
              />
            </div>

            {emailEnabled && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="emailAddress">Email Address</Label>
                  <Input
                    id="emailAddress"
                    type="email"
                    placeholder="team@example.com"
                    value={emailAddress}
                    onChange={(e) => setEmailAddress(e.target.value)}
                    className="border-border/50"
                  />
                  <p className="text-xs text-muted-foreground">
                    Primary email address for receiving alerts
                  </p>
                </div>

                <div className="p-4 rounded-lg bg-muted/30 border border-border/50">
                  <p className="text-sm font-medium mb-2">Email Format</p>
                  <p className="text-xs text-muted-foreground">
                    Alerts will be sent with detailed information including severity, affected metrics, and recommended actions.
                  </p>
                </div>
              </div>
            )}
          </TabsContent>

          {/* Slack Settings */}
          <TabsContent value="slack" className="space-y-6 mt-6">
            <div className="flex items-center justify-between p-4 rounded-lg border border-border/50">
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <MessageSquare className="h-4 w-4 text-primary" />
                  <Label className="text-base">Slack Notifications</Label>
                </div>
                <p className="text-sm text-muted-foreground">
                  Post alerts to your Slack workspace
                </p>
              </div>
              <Switch
                checked={slackEnabled}
                onCheckedChange={setSlackEnabled}
              />
            </div>

            {slackEnabled && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="slackChannel">Slack Channel</Label>
                  <Input
                    id="slackChannel"
                    placeholder="#ai-monitoring"
                    value={slackChannel}
                    onChange={(e) => setSlackChannel(e.target.value)}
                    className="border-border/50"
                  />
                  <p className="text-xs text-muted-foreground">
                    Channel where alerts will be posted
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="slackWebhook">Webhook URL</Label>
                  <Input
                    id="slackWebhook"
                    type="password"
                    placeholder="https://hooks.slack.com/services/..."
                    value={slackWebhook}
                    onChange={(e) => setSlackWebhook(e.target.value)}
                    className="border-border/50"
                  />
                  <p className="text-xs text-muted-foreground">
                    Get your webhook URL from Slack's Incoming Webhooks integration
                  </p>
                </div>

                <Button variant="outline" size="sm">
                  Test Slack Connection
                </Button>
              </div>
            )}
          </TabsContent>

          {/* SMS Settings */}
          <TabsContent value="sms" className="space-y-6 mt-6">
            <div className="flex items-center justify-between p-4 rounded-lg border border-border/50">
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <Smartphone className="h-4 w-4 text-primary" />
                  <Label className="text-base">SMS Notifications</Label>
                </div>
                <p className="text-sm text-muted-foreground">
                  Receive critical alerts via text message
                </p>
              </div>
              <Switch
                checked={smsEnabled}
                onCheckedChange={setSmsEnabled}
              />
            </div>

            {smsEnabled && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="phoneNumber">Phone Number</Label>
                  <Input
                    id="phoneNumber"
                    type="tel"
                    placeholder="+1 (555) 000-0000"
                    value={phoneNumber}
                    onChange={(e) => setPhoneNumber(e.target.value)}
                    className="border-border/50"
                  />
                  <p className="text-xs text-muted-foreground">
                    Include country code (e.g., +1 for US)
                  </p>
                </div>

                <div className="p-4 rounded-lg bg-warning/10 border border-warning/20">
                  <p className="text-sm font-medium text-warning mb-2">High Priority Only</p>
                  <p className="text-xs text-muted-foreground">
                    SMS notifications are only sent for high-severity alerts to avoid message overload.
                  </p>
                </div>

                <Button variant="outline" size="sm">
                  Send Test SMS
                </Button>
              </div>
            )}
          </TabsContent>
        </Tabs>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave} className="gradient-primary">
            Save Configuration
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
