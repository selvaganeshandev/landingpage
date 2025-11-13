import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Breadcrumb,
  BreadcrumbList,
  BreadcrumbItem,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
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
  Smartphone,
  Trash2
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

  // Delete confirmation dialogs
  const [deleteAlertDialogOpen, setDeleteAlertDialogOpen] = useState(false);
  const [deleteRuleDialogOpen, setDeleteRuleDialogOpen] = useState(false);
  const [itemToDelete, setItemToDelete] = useState<{ type: 'alert' | 'rule'; id: number } | null>(null);

  const [activeAlerts, setActiveAlerts] = useState<any[]>([]);
  const [resolvedAlerts, setResolvedAlerts] = useState<any[]>([]);
  const [alertRules, setAlertRules] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>({ total: 0, active: 0, high_priority: 0, resolved_today: 0, avg_response_time: null });
  const [loading, setLoading] = useState(false);
  
  // Email input state
  const [emailAddress, setEmailAddress] = useState<string>('');
  const [emailError, setEmailError] = useState<string>('');

  const loadData = async () => {
    setLoading(true);
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
      const summaryData = summaryResp || {};
      setSummary(summaryData);
      // Set email address from summary if available
      if (summaryData.email_address) {
        setEmailAddress(summaryData.email_address);
      }
    } catch (e: any) {
      // Only show error for actual errors, not empty data (404, empty arrays are normal)
      const errorMessage = String(e.message || e);
      const isNetworkError = errorMessage.includes('fetch') || errorMessage.includes('network') || errorMessage.includes('Network');
      const isServerError = errorMessage.includes('500') || errorMessage.includes('503') || errorMessage.includes('502');
      
      // Only show error toast for actual errors, not for empty data (404 is normal for empty data)
      if (isNetworkError || isServerError || (!errorMessage.includes('404') && !errorMessage.includes('Not Found'))) {
        toast({ 
          title: 'Failed to load alerts', 
          description: errorMessage, 
          variant: 'destructive' 
        });
      }
      // For empty data (404), just set empty arrays without showing error
      setActiveAlerts([]);
      setResolvedAlerts([]);
      setAlertRules([]);
      setSummary({ total: 0, active: 0, high_priority: 0, resolved_today: 0, avg_response_time: null });
    } finally {
      setLoading(false);
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

  const handleInvestigate = async (alertId: number) => {
    try {
      await apiClient.investigateAlert(alertId);
      toast({
        title: "Alert Under Investigation",
        description: "The alert has been marked as investigating.",
      });
      void loadData();
    } catch (e: any) {
      toast({
        title: 'Failed to update alert',
        description: String(e.message || e),
        variant: 'destructive'
      });
    }
  };

  const handleMarkResolved = async (alertId: number) => {
    try {
      await apiClient.resolveAlert(alertId);
      toast({
        title: "Alert Resolved",
        description: "The alert has been marked as resolved.",
      });
      void loadData();
    } catch (e: any) {
      toast({
        title: 'Failed to resolve alert',
        description: String(e.message || e),
        variant: 'destructive'
      });
    }
  };


  const handleDeleteAlert = (alertId: number) => {
    setItemToDelete({ type: 'alert', id: alertId });
    setDeleteAlertDialogOpen(true);
  };

  const handleDeleteRule = (ruleId: number) => {
    setItemToDelete({ type: 'rule', id: ruleId });
    setDeleteRuleDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (!itemToDelete) return;

    try {
      if (itemToDelete.type === 'alert') {
        await apiClient.deleteAlert(itemToDelete.id);
        toast({
          title: "Alert Deleted",
          description: "The alert has been deleted successfully.",
        });
      } else {
        await apiClient.deleteAlertRule(itemToDelete.id);
        toast({
          title: "Rule Deleted",
          description: "The alert rule has been deleted successfully.",
        });
      }
      setItemToDelete(null);
      setDeleteAlertDialogOpen(false);
      setDeleteRuleDialogOpen(false);
      void loadData();
    } catch (e: any) {
      toast({
        title: 'Failed to delete',
        description: String(e.message || e),
        variant: 'destructive'
      });
    }
  };

  const handleRuleEnabledToggle = async (rule: any, enabled: boolean) => {
    try {
      if (Boolean(rule.enabled) !== Boolean(enabled)) {
        await apiClient.toggleAlertRule(rule.id);
      }
      setAlertRules(prev => prev.map(r => (r.id === rule.id ? { ...r, enabled } : r)));
      toast({
        title: enabled ? "Rule Enabled" : "Rule Disabled",
        description: `Alert rule "${rule.name}" has been ${enabled ? 'enabled' : 'disabled'}.`,
      });
    } catch (e: any) {
      toast({ 
        title: 'Failed to update rule', 
        description: String(e.message || e), 
        variant: 'destructive' 
      });
      // Revert the toggle on error
      setAlertRules(prev => prev.map(r => (r.id === rule.id ? { ...r, enabled: !enabled } : r)));
    }
  };

  const validateEmail = (email: string): boolean => {
    if (!email || email.trim() === '') {
      setEmailError('Email address is required');
      return false;
    }
    
    // Basic email validation regex
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email.trim())) {
      setEmailError('Please enter a valid email address');
      return false;
    }
    
    // Check for common invalid patterns
    if (email.includes('..') || email.startsWith('.') || email.startsWith('@')) {
      setEmailError('Please enter a valid email address');
      return false;
    }
    
    setEmailError('');
    return true;
  };

  const handleEmailChange = (value: string) => {
    setEmailAddress(value);
    // Clear error when user starts typing
    if (emailError) {
      setEmailError('');
    }
  };

  const handleUpdateEmail = async () => {
    // Validate email
    if (!validateEmail(emailAddress)) {
      toast({
        title: 'Invalid Email',
        description: emailError || 'Please enter a valid email address',
        variant: 'destructive'
      });
      return;
    }

    if (!selectedDomain?.id) {
      toast({
        title: 'No Domain Selected',
        description: 'Please select a domain first',
        variant: 'destructive'
      });
      return;
    }

    try {
      await apiClient.updateEmailConfig({
        domain_id: selectedDomain.id,
        email_address: emailAddress.trim()
      });
      
      toast({
        title: 'Email Updated',
        description: `Email address updated to ${emailAddress.trim()}`,
      });
      
      // Clear error on success and reload data
      setEmailError('');
      void loadData();
    } catch (e: any) {
      toast({
        title: 'Failed to Update Email',
        description: String(e.message || e),
        variant: 'destructive'
      });
    }
  };

  const handleConfigureSlack = () => {
    toast({ title: 'Configure Slack', description: 'Opening Slack integration settings...' });
  };

  const handleConnectSMS = () => {
    toast({ title: 'Connect SMS', description: 'Setting up SMS notifications...' });
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return 'N/A';
    try {
      const date = new Date(dateString);
      return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateString;
    }
  };

  const formatCondition = (conditions: any) => {
    if (!conditions || typeof conditions !== 'object') {
      return typeof conditions === 'string' ? conditions : JSON.stringify(conditions);
    }

    const triggerType = conditions.trigger_type || '';
    const threshold = conditions.threshold_percent || 0;
    const timeWindow = conditions.time_window_hours || 24;

    // Map trigger types to display names
    const metricNames: { [key: string]: string } = {
      'visibility_drop': 'Visibility',
      'visibility_increase': 'Visibility',
      'sentiment_negative': 'Sentiment',
      'sentiment_positive': 'Sentiment',
      'position_drop': 'Position',
      'mention_spike': 'Mentions',
      'anomaly': 'Anomaly',
    };

    const metricName = metricNames[triggerType] || 'Metric';

    // Determine operator and threshold format
    let operator = '<';
    let thresholdDisplay = `-${threshold}%`;
    
    if (triggerType === 'visibility_increase' || triggerType === 'sentiment_positive' || triggerType === 'mention_spike') {
      operator = '>';
      thresholdDisplay = `${threshold}%`;
    } else if (triggerType === 'position_drop') {
      operator = '>';
      thresholdDisplay = `${threshold}%`;
    } else if (triggerType === 'anomaly') {
      operator = '>';
      thresholdDisplay = `${threshold}%`;
    }

    // Format time window
    let timeWindowDisplay = '';
    if (timeWindow < 24) {
      timeWindowDisplay = `${timeWindow}h`;
    } else if (timeWindow === 24) {
      timeWindowDisplay = '24h';
    } else if (timeWindow < 168) {
      timeWindowDisplay = `${Math.round(timeWindow / 24)}d`;
    } else {
      timeWindowDisplay = `${Math.round(timeWindow / 168)}w`;
    }

    return `${metricName} ${operator} ${thresholdDisplay} in ${timeWindowDisplay}`;
  };

  return (
    <div className="p-8 space-y-8 bg-background animate-fade-in">
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
          <h3 className="text-3xl font-bold text-destructive">{summary.active || 0}</h3>
          <p className="text-xs text-muted-foreground mt-1">Require attention</p>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-muted-foreground font-medium">High Priority</p>
            <AlertTriangle className="h-5 w-5 text-destructive" />
          </div>
          <h3 className="text-3xl font-bold text-destructive">{summary.high_priority || 0}</h3>
          <p className="text-xs text-muted-foreground mt-1">Critical issues</p>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-muted-foreground font-medium">Resolved Today</p>
            <CheckCircle2 className="h-5 w-5 text-success" />
          </div>
          <h3 className="text-3xl font-bold text-success">{summary.resolved_today || 0}</h3>
          <p className="text-xs text-muted-foreground mt-1">Issues fixed</p>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-muted-foreground font-medium">Avg Response</p>
            <Clock className="h-5 w-5 text-muted-foreground" />
          </div>
          <h3 className={`text-3xl font-bold ${summary.avg_response_time ? '' : 'text-muted-foreground opacity-50'}`}>
            {summary.avg_response_time ? `${summary.avg_response_time}h` : 'NA'}
          </h3>
          <p className="text-xs text-muted-foreground mt-1">Response time</p>
        </Card>
      </div>

      {/* Alerts List */}
      <Tabs defaultValue="active" className="space-y-6">
        <TabsList className="bg-muted/50 p-1 border border-border">
          <TabsTrigger value="active" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">
            Active Alerts ({activeAlerts.length})
          </TabsTrigger>
          <TabsTrigger value="resolved" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">
            Resolved ({resolvedAlerts.length})
          </TabsTrigger>
          <TabsTrigger value="rules" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">
            Alert Rules ({alertRules.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="active" className="space-y-4">
          {loading ? (
            <Card className="p-6 text-center">
              <p className="text-muted-foreground">Loading alerts...</p>
            </Card>
          ) : activeAlerts.length === 0 ? (
            <Card className="p-6 text-center">
              <Bell className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No active alerts</p>
            </Card>
          ) : (
            activeAlerts.map((alert) => (
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
                        <Badge variant="outline" className={getStatusColor(alert.status)}>
                          {alert.status}
                        </Badge>
                      </div>
                      <p className="text-muted-foreground mb-3">{alert.message}</p>
                      <div className="flex items-center gap-4 text-sm">
                        <span className="text-muted-foreground">
                          Created: {formatDate(alert.created_at)}
                        </span>
                        {alert.metric && (
                          <span className="flex items-center gap-1">
                            {alert.metric > 0 ? (
                              <TrendingUp className="h-4 w-4 text-destructive" />
                            ) : (
                              <TrendingDown className="h-4 w-4 text-destructive" />
                            )}
                            <span className="font-medium">{Math.abs(Number(alert.metric))}%</span>
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    {alert.status === 'active' && (
                      <>
                        <Button 
                          size="sm" 
                          variant="outline" 
                          onClick={() => handleInvestigate(alert.id)}
                        >
                          Investigate
                        </Button>
                        <Button 
                          size="sm" 
                          onClick={() => handleMarkResolved(alert.id)}
                        >
                          Mark Resolved
                        </Button>
                      </>
                    )}
                    <Button 
                      size="sm" 
                      variant="outline"
                      onClick={() => handleDeleteAlert(alert.id)}
                      className="text-destructive hover:text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </Card>
            ))
          )}
        </TabsContent>

        <TabsContent value="resolved" className="space-y-4">
          {loading ? (
            <Card className="p-6 text-center">
              <p className="text-muted-foreground">Loading alerts...</p>
            </Card>
          ) : resolvedAlerts.length === 0 ? (
            <Card className="p-6 text-center">
              <CheckCircle2 className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No resolved alerts</p>
            </Card>
          ) : (
            resolvedAlerts.map((alert) => (
              <Card key={alert.id} className="p-6 transition-all duration-300 border border-border hover:border-primary opacity-75">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4 flex-1">
                    <div className="w-12 h-12 rounded-lg bg-success/10 flex items-center justify-center">
                      <CheckCircle2 className="h-6 w-6 text-success" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="font-semibold">{alert.title}</h3>
                        <Badge variant="outline">{alert.platform || 'All'}</Badge>
                        <Badge className="bg-success text-success-foreground">Resolved</Badge>
                      </div>
                      <p className="text-sm text-muted-foreground mb-2">{alert.message}</p>
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span>Triggered: {formatDate(alert.created_at)}</span>
                        <span>Resolved: {formatDate(alert.resolved_at)}</span>
                      </div>
                    </div>
                  </div>
                  <Button 
                    size="sm" 
                    variant="outline"
                    onClick={() => handleDeleteAlert(alert.id)}
                    className="text-destructive hover:text-destructive"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </Card>
            ))
          )}
        </TabsContent>

        <TabsContent value="rules" className="space-y-4">
          <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
            {loading ? (
              <div className="text-center py-8">
                <p className="text-muted-foreground">Loading rules...</p>
              </div>
            ) : alertRules.length === 0 ? (
              <div className="text-center py-8">
                <Bell className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground mb-4">No alert rules configured</p>
                <Button onClick={handleNewAlertRule} className="gradient-primary">
                  <Plus className="h-4 w-4 mr-2" />
                  Create First Rule
                </Button>
              </div>
            ) : (
              <div className="space-y-6">
                {alertRules.map((rule) => (
                  <div key={rule.id} className="flex items-start justify-between p-4 rounded-lg transition-all duration-300 border border-border hover:border-primary">
                    <div className="flex items-start gap-4 flex-1">
                      <Switch 
                        checked={rule.enabled} 
                        onCheckedChange={(val) => handleRuleEnabledToggle(rule, Boolean(val))} 
                      />
                      <div className="flex-1">
                        <h4 className="font-semibold mb-1">{rule.name}</h4>
                        <p className="text-sm text-muted-foreground mb-3">{rule.description}</p>
                        <div className="flex items-center gap-4 flex-wrap">
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground">Conditions:</span>
                            <Badge className="text-xs font-mono bg-primary text-primary-foreground">
                              {formatCondition(rule.conditions)}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground">Channels:</span>
                            {rule.notification_channel_list?.includes("email") && (
                              <Mail className="h-4 w-4 text-muted-foreground" />
                            )}
                            {rule.notification_channel_list?.includes("slack") && (
                              <MessageSquare className="h-4 w-4 text-muted-foreground" />
                            )}
                            {rule.notification_channel_list?.includes("sms") && (
                              <Smartphone className="h-4 w-4 text-muted-foreground" />
                            )}
                          </div>
                          {rule.detection_count > 0 && (
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-muted-foreground">Detections:</span>
                              <Badge variant="outline" className="text-xs">
                                {rule.detection_count}
                              </Badge>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => handleDeleteRule(rule.id)}
                      className="text-destructive hover:text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
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
                <p className={`text-xs ${
                  summary.email_enabled && summary.email_address 
                    ? 'text-success' 
                    : 'text-muted-foreground'
                }`}>
                  {summary.email_enabled && summary.email_address 
                    ? 'Connected' 
                    : 'Not configured'}
                </p>
              </div>
            </div>
            <div className="space-y-1">
              <Input 
                type="email"
                placeholder="Enter email address" 
                className={`mb-2 ${emailError ? 'border-destructive' : ''}`}
                value={emailAddress}
                onChange={(e) => handleEmailChange(e.target.value)}
                onBlur={() => {
                  if (emailAddress) {
                    validateEmail(emailAddress);
                  }
                }}
              />
              {emailError && (
                <p className="text-xs text-destructive">{emailError}</p>
              )}
            </div>
            <Button 
              variant="outline" 
              size="sm" 
              className="w-full" 
              onClick={handleUpdateEmail}
              disabled={!emailAddress.trim()}
            >
              Update Email
            </Button>
          </div>

          <div className="p-4 rounded-lg transition-all duration-300 border border-border hover:border-primary opacity-50">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <MessageSquare className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h4 className="font-semibold">Slack</h4>
                <p className={`text-xs ${
                  summary.slack_enabled && summary.slack_webhook_url 
                    ? 'text-success' 
                    : 'text-muted-foreground'
                }`}>
                  {summary.slack_enabled && summary.slack_webhook_url 
                    ? 'Connected' 
                    : 'Coming Soon'}
                </p>
              </div>
            </div>
            <Input 
              placeholder="Enter Slack channel" 
              className="mb-2" 
              disabled
              defaultValue={summary.slack_channel || ''}
            />
            <Button variant="outline" size="sm" className="w-full" disabled onClick={handleConfigureSlack}>
              Configure Slack
            </Button>
          </div>

          <div className="p-4 rounded-lg transition-all duration-300 border border-border hover:border-primary opacity-50">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center">
                <Smartphone className="h-5 w-5 text-muted-foreground" />
              </div>
              <div>
                <h4 className="font-semibold">SMS</h4>
                <p className={`text-xs ${
                  summary.sms_enabled && summary.phone_number 
                    ? 'text-success' 
                    : 'text-muted-foreground'
                }`}>
                  {summary.sms_enabled && summary.phone_number 
                    ? 'Connected' 
                    : 'Coming Soon'}
                </p>
              </div>
            </div>
            <Input 
              placeholder="Enter phone number" 
              className="mb-2" 
              disabled
              defaultValue={summary.phone_number || ''}
            />
            <Button variant="outline" size="sm" className="w-full" disabled onClick={handleConnectSMS}>
              Connect SMS
            </Button>
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

      {/* Delete Confirmation Dialogs */}
      <AlertDialog open={deleteAlertDialogOpen} onOpenChange={setDeleteAlertDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Alert</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this alert? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete} className="bg-destructive text-destructive-foreground">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={deleteRuleDialogOpen} onOpenChange={setDeleteRuleDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Alert Rule</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this alert rule? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete} className="bg-destructive text-destructive-foreground">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default Alerts;
