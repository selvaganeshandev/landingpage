import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import { 
  Bell,
  Plus,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Settings,
  Mail,
  MessageSquare,
  Smartphone
} from "lucide-react";

const activeAlerts = [
  {
    id: 1,
    type: "visibility_drop",
    severity: "high",
    title: "Visibility Drop Detected",
    message: "ChatGPT visibility decreased by 12% in the last 24 hours",
    platform: "ChatGPT",
    timestamp: "2 hours ago",
    metric: -12,
    status: "active"
  },
  {
    id: 2,
    type: "sentiment_negative",
    severity: "medium",
    title: "Negative Sentiment Spike",
    message: "Negative sentiment increased to 8% for 'taste' related mentions",
    platform: "Multiple",
    timestamp: "5 hours ago",
    metric: 8,
    status: "active"
  },
  {
    id: 3,
    type: "competitor_surge",
    severity: "medium",
    title: "Competitor Mention Surge",
    message: "MyProtein mentions increased by 25% in Perplexity",
    platform: "Perplexity",
    timestamp: "8 hours ago",
    metric: 25,
    status: "investigating"
  },
  {
    id: 4,
    type: "anomaly",
    severity: "high",
    title: "Unusual Activity Pattern",
    message: "Mention volume 3x above normal in weight loss category",
    platform: "Claude",
    timestamp: "12 hours ago",
    metric: 300,
    status: "active"
  },
];

const resolvedAlerts = [
  {
    id: 5,
    type: "visibility_recovery",
    severity: "low",
    title: "Visibility Recovered",
    message: "Gemini visibility returned to normal levels",
    platform: "Gemini",
    timestamp: "1 day ago",
    resolvedAt: "8 hours ago",
    status: "resolved"
  },
  {
    id: 6,
    type: "sentiment_improved",
    severity: "low",
    title: "Sentiment Improvement",
    message: "Positive sentiment recovered to 75%",
    platform: "Multiple",
    timestamp: "2 days ago",
    resolvedAt: "1 day ago",
    status: "resolved"
  },
];

const alertRules = [
  {
    id: 1,
    name: "Visibility Drop Alert",
    description: "Trigger when visibility score drops by more than 10% in 24 hours",
    enabled: true,
    channels: ["email", "slack"],
    conditions: "Visibility < -10% in 24h"
  },
  {
    id: 2,
    name: "Negative Sentiment Spike",
    description: "Alert when negative sentiment exceeds 10%",
    enabled: true,
    channels: ["email"],
    conditions: "Negative sentiment > 10%"
  },
  {
    id: 3,
    name: "Competitor Movement",
    description: "Monitor significant competitor mention changes",
    enabled: true,
    channels: ["slack"],
    conditions: "Competitor mentions +/- 20%"
  },
  {
    id: 4,
    name: "Position Loss",
    description: "Alert when average position drops below 2.0",
    enabled: false,
    channels: ["email"],
    conditions: "Avg position > 2.0"
  },
  {
    id: 5,
    name: "New Platform Detection",
    description: "Notify when brand appears on new AI platform",
    enabled: true,
    channels: ["email", "slack", "sms"],
    conditions: "New platform mention detected"
  },
  {
    id: 6,
    name: "Anomaly Detection",
    description: "AI-powered unusual pattern detection",
    enabled: true,
    channels: ["email", "slack"],
    conditions: "Statistical anomaly detected"
  },
];

const getSeverityColor = (severity: string) => {
  switch (severity) {
    case "high":
      return "bg-destructive text-destructive-foreground";
    case "medium":
      return "bg-warning text-warning-foreground";
    case "low":
      return "bg-success text-success-foreground";
    default:
      return "bg-muted";
  }
};

const getStatusColor = (status: string) => {
  switch (status) {
    case "active":
      return "text-destructive";
    case "investigating":
      return "text-warning";
    case "resolved":
      return "text-success";
    default:
      return "text-muted-foreground";
  }
};

const Alerts = () => {
  const { toast } = useToast();

  const handleConfigure = () => {
    toast({
      title: "Opening Configuration",
      description: "Loading alert settings...",
    });
  };

  const handleNewAlertRule = () => {
    toast({
      title: "Create Alert Rule",
      description: "Opening alert rule builder...",
    });
  };

  const handleInvestigate = () => {
    toast({
      title: "Investigating",
      description: "Opening detailed alert analysis...",
    });
  };

  const handleMarkResolved = () => {
    toast({
      title: "Alert Resolved",
      description: "Alert has been marked as resolved.",
    });
  };

  const handleEdit = () => {
    toast({
      title: "Edit Rule",
      description: "Opening alert rule editor...",
    });
  };

  const handleUpdateEmail = () => {
    toast({
      title: "Updating Email",
      description: "Email address updated successfully.",
    });
  };

  const handleConfigureSlack = () => {
    toast({
      title: "Configure Slack",
      description: "Opening Slack integration settings...",
    });
  };

  const handleConnectSMS = () => {
    toast({
      title: "Connect SMS",
      description: "Setting up SMS notifications...",
    });
  };

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Real-Time Alerts</h1>
          <p className="text-muted-foreground mt-2">
            Stay informed with instant notifications
          </p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={handleConfigure}>
            <Settings className="h-4 w-4 mr-2" />
            Configure
          </Button>
          <Button onClick={handleNewAlertRule}>
            <Plus className="h-4 w-4 mr-2" />
            New Alert Rule
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="p-6">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-muted-foreground font-medium">Active Alerts</p>
            <Bell className="h-5 w-5 text-destructive" />
          </div>
          <h3 className="text-3xl font-bold text-destructive">4</h3>
          <p className="text-xs text-muted-foreground mt-1">Require attention</p>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-muted-foreground font-medium">High Priority</p>
            <AlertTriangle className="h-5 w-5 text-destructive" />
          </div>
          <h3 className="text-3xl font-bold text-destructive">2</h3>
          <p className="text-xs text-muted-foreground mt-1">Critical issues</p>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-muted-foreground font-medium">Resolved Today</p>
            <CheckCircle2 className="h-5 w-5 text-success" />
          </div>
          <h3 className="text-3xl font-bold text-success">6</h3>
          <p className="text-xs text-muted-foreground mt-1">Issues fixed</p>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-muted-foreground font-medium">Avg Response</p>
            <Clock className="h-5 w-5 text-muted-foreground" />
          </div>
          <h3 className="text-3xl font-bold">2.4h</h3>
          <p className="text-xs text-muted-foreground mt-1">Response time</p>
        </Card>
      </div>

      {/* Alerts List */}
      <Tabs defaultValue="active" className="space-y-6">
        <TabsList>
          <TabsTrigger value="active">Active Alerts ({activeAlerts.length})</TabsTrigger>
          <TabsTrigger value="resolved">Resolved ({resolvedAlerts.length})</TabsTrigger>
          <TabsTrigger value="rules">Alert Rules ({alertRules.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="active" className="space-y-4">
          {activeAlerts.map((alert) => (
            <Card key={alert.id} className="p-6 hover:shadow-lg transition-shadow">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-start gap-4 flex-1">
                  <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${getSeverityColor(alert.severity)}`}>
                    <Bell className="h-6 w-6" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="font-semibold text-lg">{alert.title}</h3>
                      <Badge className={getSeverityColor(alert.severity)}>
                        {alert.severity}
                      </Badge>
                      <Badge variant="outline">{alert.platform}</Badge>
                    </div>
                    <p className="text-muted-foreground mb-3">{alert.message}</p>
                    <div className="flex items-center gap-4 text-sm">
                      <span className="text-muted-foreground">{alert.timestamp}</span>
                      <span className={`font-medium ${getStatusColor(alert.status)}`}>
                        Status: {alert.status}
                      </span>
                      {alert.metric && (
                        <span className="flex items-center gap-1">
                          {alert.metric > 0 ? (
                            <TrendingUp className="h-4 w-4 text-destructive" />
                          ) : (
                            <TrendingDown className="h-4 w-4 text-destructive" />
                          )}
                          <span className="font-medium">{Math.abs(alert.metric)}%</span>
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={handleInvestigate}>Investigate</Button>
                  <Button size="sm" onClick={handleMarkResolved}>Mark Resolved</Button>
                </div>
              </div>
            </Card>
          ))}
        </TabsContent>

        <TabsContent value="resolved" className="space-y-4">
          {resolvedAlerts.map((alert) => (
            <Card key={alert.id} className="p-6 opacity-75">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-lg bg-success/10 flex items-center justify-center">
                  <CheckCircle2 className="h-6 w-6 text-success" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="font-semibold">{alert.title}</h3>
                    <Badge variant="outline">{alert.platform}</Badge>
                    <Badge className="bg-success text-success-foreground">Resolved</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground mb-2">{alert.message}</p>
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <span>Triggered: {alert.timestamp}</span>
                    <span>Resolved: {alert.resolvedAt}</span>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </TabsContent>

        <TabsContent value="rules" className="space-y-4">
          <Card className="p-6">
            <div className="space-y-6">
              {alertRules.map((rule) => (
                <div key={rule.id} className="flex items-start justify-between p-4 rounded-lg border border-border">
                  <div className="flex items-start gap-4 flex-1">
                    <Switch checked={rule.enabled} />
                    <div className="flex-1">
                      <h4 className="font-semibold mb-1">{rule.name}</h4>
                      <p className="text-sm text-muted-foreground mb-3">{rule.description}</p>
                      <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground">Conditions:</span>
                          <Badge variant="secondary" className="text-xs font-mono">
                            {rule.conditions}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground">Channels:</span>
                          {rule.channels.includes("email") && <Mail className="h-4 w-4 text-muted-foreground" />}
                          {rule.channels.includes("slack") && <MessageSquare className="h-4 w-4 text-muted-foreground" />}
                          {rule.channels.includes("sms") && <Smartphone className="h-4 w-4 text-muted-foreground" />}
                        </div>
                      </div>
                    </div>
                  </div>
                  <Button variant="outline" size="sm" onClick={handleEdit}>Edit</Button>
                </div>
              ))}
            </div>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Notification Channels */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-6">Notification Channels</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-4 rounded-lg border border-border">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <Mail className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h4 className="font-semibold">Email</h4>
                <p className="text-xs text-success">Connected</p>
              </div>
            </div>
            <Input placeholder="team@vegfitpro.com" className="mb-2" />
            <Button variant="outline" size="sm" className="w-full" onClick={handleUpdateEmail}>Update Email</Button>
          </div>

          <div className="p-4 rounded-lg border border-border">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <MessageSquare className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h4 className="font-semibold">Slack</h4>
                <p className="text-xs text-success">Connected</p>
              </div>
            </div>
            <p className="text-sm text-muted-foreground mb-2">#ai-monitoring</p>
            <Button variant="outline" size="sm" className="w-full" onClick={handleConfigureSlack}>Configure Slack</Button>
          </div>

          <div className="p-4 rounded-lg border border-border">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center">
                <Smartphone className="h-5 w-5 text-muted-foreground" />
              </div>
              <div>
                <h4 className="font-semibold">SMS</h4>
                <p className="text-xs text-muted-foreground">Not connected</p>
              </div>
            </div>
            <Input placeholder="+1 (555) 000-0000" className="mb-2" />
            <Button variant="outline" size="sm" className="w-full" onClick={handleConnectSMS}>Connect SMS</Button>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default Alerts;
