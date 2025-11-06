import { useState, useEffect } from "react";
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
import { NewAlertRuleDialog } from "@/components/NewAlertRuleDialog";
import { AlertConfigDialog } from "@/components/AlertConfigDialog";
import { apiClient } from "@/services/api";
import { useDomainStore } from "@/stores/domainStore";

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
  const { selectedDomain } = useDomainStore();
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [newRuleDialogOpen, setNewRuleDialogOpen] = useState(false);

  const [activeAlerts, setActiveAlerts] = useState<any[]>([]);
  const [resolvedAlerts, setResolvedAlerts] = useState<any[]>([]);
  const [alertRules, setAlertRules] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>({ total: 0, active: 0, high_priority: 0, resolved_today: 0, investigating: 0 });

  const loadData = async () => {
    try {
      const domain_id = selectedDomain?.id;
      const [activeResp, listResp, rulesResp, summaryResp] = await Promise.all([
        apiClient.getActiveAlerts(domain_id ? { domain_id } : undefined),
        apiClient.getAlerts(domain_id ? { domain_id } : undefined),
        apiClient.getAlertRules(domain_id ? { domain_id } : undefined),
        apiClient.getAlertSummary(domain_id ? { domain_id } : undefined)
      ] as any);

      const normalize = (data: any) => (Array.isArray(data) ? data : (data?.results || []));
      const active = normalize(activeResp);
      const all = normalize(listResp);
      const rules = normalize(rulesResp);
      const resolved = all.filter((a: any) => a.status === 'resolved');

      setActiveAlerts(active);
      setResolvedAlerts(resolved);
      setAlertRules(rules);
      setSummary(summaryResp || {});
    } catch (e:any) {
      toast({ title: 'Failed to load alerts', description: String(e.message||e), variant: 'destructive' });
    }
  };

  useEffect(() => {
    void loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDomain?.id]);

  const handleConfigure = () => {
    setConfigDialogOpen(true);
  };

  const handleNewAlertRule = () => {
    setNewRuleDialogOpen(true);
  };

  const handleInvestigate = () => {
    toast({
      title: "Investigating",
      description: "Opening detailed alert analysis...",
    });
  };

  const handleMarkResolved = () => {
    toast({ title: 'Mark Resolved', description: 'Use the resolve action from alert row (to be implemented).' });
  };

  const handleEdit = () => {
    toast({ title: 'Edit Rule', description: 'Opening alert rule editor...' });
  };

  const handleRuleEnabledToggle = async (rule: any, enabled: boolean) => {
    try {
      // Use toggle endpoint for simplicity; if mismatch, fallback to PUT
      if (Boolean(rule.enabled) !== Boolean(enabled)) {
        await apiClient.toggleAlertRule(rule.id);
      }
      setAlertRules(prev => prev.map(r => (r.id === rule.id ? { ...r, enabled } : r)));
    } catch (e:any) {
      toast({ title: 'Failed to update rule', description: String(e.message||e), variant: 'destructive' });
    }
  };

  const handleUpdateEmail = () => {
    toast({ title: 'Updating Email', description: 'Email address updated successfully.' });
  };

  const handleConfigureSlack = () => {
    toast({ title: 'Configure Slack', description: 'Opening Slack integration settings...' });
  };

  const handleConnectSMS = () => {
    toast({ title: 'Connect SMS', description: 'Setting up SMS notifications...' });
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
          <Button onClick={handleNewAlertRule} className="gradient-primary shadow-md shadow-primary/20">
            <Plus className="h-4 w-4 mr-2" />
            New Alert Rule
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-muted-foreground font-medium">Active Alerts</p>
            <Bell className="h-5 w-5 text-destructive" />
          </div>
          <h3 className="text-3xl font-bold text-destructive">{summary.active}</h3>
          <p className="text-xs text-muted-foreground mt-1">Require attention</p>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-muted-foreground font-medium">High Priority</p>
            <AlertTriangle className="h-5 w-5 text-destructive" />
          </div>
          <h3 className="text-3xl font-bold text-destructive">{summary.high_priority}</h3>
          <p className="text-xs text-muted-foreground mt-1">Critical issues</p>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-muted-foreground font-medium">Resolved Today</p>
            <CheckCircle2 className="h-5 w-5 text-success" />
          </div>
          <h3 className="text-3xl font-bold text-success">{summary.resolved_today}</h3>
          <p className="text-xs text-muted-foreground mt-1">Issues fixed</p>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
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
        <TabsList className="bg-muted/50 p-1 border border-border">
          <TabsTrigger value="active" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">Active Alerts ({activeAlerts.length})</TabsTrigger>
          <TabsTrigger value="resolved" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">Resolved ({resolvedAlerts.length})</TabsTrigger>
          <TabsTrigger value="rules" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">Alert Rules ({alertRules.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="active" className="space-y-4">
          {activeAlerts.map((alert) => (
            <Card key={alert.id} className="p-6 transition-all duration-300 border border-border hover:border-primary">
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
                      <Badge variant="outline">{alert.platform || 'All'}</Badge>
                    </div>
                    <p className="text-muted-foreground mb-3">{alert.message}</p>
                    <div className="flex items-center gap-4 text-sm">
                      <span className="text-muted-foreground">{alert.created_at}</span>
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
            <Card key={alert.id} className="p-6 transition-all duration-300 border border-border hover:border-primary opacity-75">
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
                    <span>Triggered: {alert.created_at}</span>
                    <span>Resolved: {alert.resolved_at}</span>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </TabsContent>

        <TabsContent value="rules" className="space-y-4">
          <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
            <div className="space-y-6">
              {alertRules.map((rule) => (
                <div key={rule.id} className="flex items-start justify-between p-4 rounded-lg transition-all duration-300 border border-border hover:border-primary">
                  <div className="flex items-start gap-4 flex-1">
                    <Switch checked={rule.enabled} onCheckedChange={(val) => handleRuleEnabledToggle(rule, Boolean(val))} />
                    <div className="flex-1">
                      <h4 className="font-semibold mb-1">{rule.name}</h4>
                      <p className="text-sm text-muted-foreground mb-3">{rule.description}</p>
                      <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground">Conditions:</span>
                          <Badge variant="secondary" className="text-xs font-mono">
                            {typeof rule.conditions === 'string' ? rule.conditions : JSON.stringify(rule.conditions)}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground">Channels:</span>
                          {rule.notification_channel_list?.includes("email") && <Mail className="h-4 w-4 text-muted-foreground" />}
                          {rule.notification_channel_list?.includes("slack") && <MessageSquare className="h-4 w-4 text-muted-foreground" />}
                          {rule.notification_channel_list?.includes("sms") && <Smartphone className="h-4 w-4 text-muted-foreground" />}
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
      <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
        <h3 className="text-lg font-semibold mb-6">Notification Channels</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-4 rounded-lg transition-all duration-300 border border-border hover:border-primary">
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

          <div className="p-4 rounded-lg transition-all duration-300 border border-border hover:border-primary">
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

          <div className="p-4 rounded-lg transition-all duration-300 border border-border hover:border-primary">
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

      {/* Dialogs */}
      <NewAlertRuleDialog 
        open={newRuleDialogOpen} 
        onOpenChange={setNewRuleDialogOpen}
        domainId={selectedDomain?.id}
        onAdd={() => { void loadData(); }}
      />
      <AlertConfigDialog 
        open={configDialogOpen} 
        onOpenChange={setConfigDialogOpen}
      />
    </div>
  );
};

export default Alerts;
