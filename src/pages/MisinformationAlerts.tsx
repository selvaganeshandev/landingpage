import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import { MisinformationDetailDialog } from "@/components/MisinformationDetailDialog";
import { MisinformationActionDialog } from "@/components/MisinformationActionDialog";
import { 
  AlertTriangle, 
  CheckCircle, 
  Clock, 
  Shield, 
  Eye,
  FileText,
  Settings,
  Search,
  Filter,
  TrendingUp,
  AlertCircle,
  XCircle,
  MessageSquare,
  ExternalLink,
  Play
} from "lucide-react";

const activeMisinformation = [
  {
    id: 1,
    title: "Incorrect Product Ingredients Listed",
    description: "AI models citing outdated ingredient list from 2022 formulation",
    severity: "high",
    platform: "ChatGPT",
    detectedAt: "2 hours ago",
    mentions: 24,
    status: "investigating",
    impact: "Product Information",
    correctInfo: "Current ingredient list includes updated plant-based formula",
    incorrectInfo: "Lists dairy-based ingredients that were removed in 2023"
  },
  {
    id: 2,
    title: "Wrong Company Founding Date",
    description: "Multiple AI platforms reporting incorrect founding year",
    severity: "medium",
    platform: "Perplexity",
    detectedAt: "5 hours ago",
    mentions: 12,
    status: "correcting",
    impact: "Company History",
    correctInfo: "Founded in 2018",
    incorrectInfo: "Founded in 2015"
  },
  {
    id: 3,
    title: "Misattributed CEO Quote",
    description: "Quote from competitor CEO attributed to our leadership",
    severity: "high",
    platform: "Claude",
    detectedAt: "1 day ago",
    mentions: 8,
    status: "escalated",
    impact: "Brand Reputation",
    correctInfo: "Quote belongs to CompetitorCo CEO",
    incorrectInfo: "Incorrectly attributed to our CEO"
  },
  {
    id: 4,
    title: "Pricing Information Outdated",
    description: "Old pricing from 2023 being referenced instead of current rates",
    severity: "medium",
    platform: "Gemini",
    detectedAt: "1 day ago",
    mentions: 18,
    status: "monitoring",
    impact: "Pricing & Sales",
    correctInfo: "Current pricing: $49/month",
    incorrectInfo: "Stating $39/month (2023 pricing)"
  }
];

const resolvedCases = [
  {
    id: 1,
    title: "Incorrect Certification Claims",
    platform: "ChatGPT",
    resolvedAt: "3 days ago",
    resolutionTime: "2 days",
    mentions: 31,
    status: "verified"
  },
  {
    id: 2,
    title: "Wrong Market Position Data",
    platform: "Perplexity",
    resolvedAt: "1 week ago",
    resolutionTime: "4 days",
    mentions: 15,
    status: "verified"
  },
  {
    id: 3,
    title: "Outdated Product Features",
    platform: "Multiple",
    resolvedAt: "2 weeks ago",
    resolutionTime: "1 week",
    mentions: 42,
    status: "verified"
  }
];

const detectionMetrics = [
  { name: "Total Detected", value: "47", change: "+12%", trend: "up" as const },
  { name: "Active Cases", value: "12", change: "-5%", trend: "down" as const },
  { name: "Avg. Response Time", value: "3.2 days", change: "-18%", trend: "down" as const },
  { name: "Verified Corrections", value: "35", change: "+23%", trend: "up" as const }
];

const monitoringRules = [
  {
    id: 1,
    name: "Product Information Accuracy",
    description: "Monitors for incorrect product specs, ingredients, or features",
    status: "active",
    detections: 15,
    lastTriggered: "2 hours ago"
  },
  {
    id: 2,
    name: "Company Data Verification",
    description: "Checks founding date, location, team size, and company facts",
    status: "active",
    detections: 8,
    lastTriggered: "5 hours ago"
  },
  {
    id: 3,
    name: "Pricing & Plans Monitor",
    description: "Ensures current pricing and plan details are cited correctly",
    status: "active",
    detections: 12,
    lastTriggered: "1 day ago"
  },
  {
    id: 4,
    name: "Leadership & Quotes",
    description: "Verifies attribution of statements and executive information",
    status: "paused",
    detections: 4,
    lastTriggered: "3 days ago"
  }
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
    case "investigating":
      return "text-warning";
    case "correcting":
      return "text-primary";
    case "escalated":
      return "text-destructive";
    case "monitoring":
      return "text-muted-foreground";
    case "verified":
      return "text-success";
    default:
      return "text-muted-foreground";
  }
};

const getStatusIcon = (status: string) => {
  switch (status) {
    case "investigating":
      return Search;
    case "correcting":
      return Settings;
    case "escalated":
      return AlertTriangle;
    case "monitoring":
      return Eye;
    case "verified":
      return CheckCircle;
    default:
      return Clock;
  }
};

const MisinformationAlerts = () => {
  const { toast } = useToast();
  const [selectedTab, setSelectedTab] = useState("active");
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [actionDialogOpen, setActionDialogOpen] = useState(false);
  const [selectedCase, setSelectedCase] = useState<typeof activeMisinformation[0] | null>(null);

  const handleViewDetails = (misinformationCase: typeof activeMisinformation[0]) => {
    setSelectedCase(misinformationCase);
    setDetailDialogOpen(true);
  };

  const handleTakeAction = (misinformationCase: typeof activeMisinformation[0]) => {
    setSelectedCase(misinformationCase);
    setActionDialogOpen(true);
  };

  const handleConfigureRules = () => {
    toast({
      title: "Configure Detection Rules",
      description: "Opening rule configuration panel...",
    });
  };

  const handleExportReport = () => {
    toast({
      title: "Exporting Report",
      description: "Generating misinformation report...",
    });
  };

  const handleStartMonitoring = () => {
    toast({
      title: "Starting Monitoring",
      description: "Initiating new monitoring scan...",
    });
  };

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Misinformation Alerts</h1>
          <p className="text-muted-foreground mt-2">
            Detect and correct AI hallucinations about your brand
          </p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={handleConfigureRules}>
            <Settings className="h-4 w-4 mr-2" />
            Configure Rules
          </Button>
          <Button onClick={handleStartMonitoring}>
            <Play className="h-4 w-4 mr-2" />
            Start Scan
          </Button>
        </div>
      </div>

      {/* Detection Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {detectionMetrics.map((metric) => (
          <Card key={metric.name}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                {metric.name}
              </CardTitle>
              <Shield className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metric.value}</div>
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <TrendingUp className={`h-3 w-3 ${metric.trend === 'up' ? 'text-success' : 'text-destructive'}`} />
                <span className={metric.trend === 'up' ? 'text-success' : 'text-destructive'}>
                  {metric.change}
                </span>
                <span>from last month</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Main Content Tabs */}
      <Tabs value={selectedTab} onValueChange={setSelectedTab}>
        <TabsList>
          <TabsTrigger value="active">
            <AlertCircle className="h-4 w-4 mr-2" />
            Active Cases ({activeMisinformation.length})
          </TabsTrigger>
          <TabsTrigger value="resolved">
            <CheckCircle className="h-4 w-4 mr-2" />
            Resolved ({resolvedCases.length})
          </TabsTrigger>
          <TabsTrigger value="monitoring">
            <Shield className="h-4 w-4 mr-2" />
            Monitoring Rules
          </TabsTrigger>
        </TabsList>

        {/* Active Cases Tab */}
        <TabsContent value="active" className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Active Misinformation Cases</CardTitle>
                  <CardDescription>
                    Detected inaccuracies requiring attention
                  </CardDescription>
                </div>
                <Button variant="outline" onClick={handleExportReport}>
                  <FileText className="h-4 w-4 mr-2" />
                  Export Report
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {activeMisinformation.map((item) => {
                const StatusIcon = getStatusIcon(item.status);
                return (
                  <div
                    key={item.id}
                    className="p-4 rounded-lg border border-border hover:bg-accent/50 transition-colors"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h4 className="font-semibold">{item.title}</h4>
                          <Badge className={getSeverityColor(item.severity)}>
                            {item.severity}
                          </Badge>
                          <Badge variant="outline" className={getStatusColor(item.status)}>
                            <StatusIcon className="h-3 w-3 mr-1" />
                            {item.status}
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground mb-3">
                          {item.description}
                        </p>
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div className="space-y-2">
                            <div className="flex items-center gap-2">
                              <span className="text-muted-foreground">Platform:</span>
                              <Badge variant="secondary">{item.platform}</Badge>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-muted-foreground">Impact:</span>
                              <span className="font-medium">{item.impact}</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-muted-foreground">Detected:</span>
                              <span>{item.detectedAt}</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <MessageSquare className="h-3 w-3 text-muted-foreground" />
                              <span>{item.mentions} mentions affected</span>
                            </div>
                          </div>
                          <div className="space-y-2">
                            <div className="p-2 bg-destructive/10 rounded">
                              <p className="text-xs font-medium mb-1 text-destructive flex items-center gap-1">
                                <XCircle className="h-3 w-3" />
                                Incorrect Information:
                              </p>
                              <p className="text-xs">{item.incorrectInfo}</p>
                            </div>
                            <div className="p-2 bg-success/10 rounded">
                              <p className="text-xs font-medium mb-1 text-success flex items-center gap-1">
                                <CheckCircle className="h-3 w-3" />
                                Correct Information:
                              </p>
                              <p className="text-xs">{item.correctInfo}</p>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="flex gap-2 pt-3 border-t border-border">
                      <Button size="sm" onClick={() => handleViewDetails(item)}>
                        <Eye className="h-3 w-3 mr-1" />
                        View Details
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => handleTakeAction(item)}>
                        <Settings className="h-3 w-3 mr-1" />
                        Take Action
                      </Button>
                      <Button size="sm" variant="ghost">
                        <ExternalLink className="h-3 w-3 mr-1" />
                        View Source
                      </Button>
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Resolved Cases Tab */}
        <TabsContent value="resolved" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Resolved Cases</CardTitle>
              <CardDescription>
                Successfully corrected misinformation
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {resolvedCases.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center justify-between p-4 rounded-lg border border-border"
                  >
                    <div className="flex items-center gap-4">
                      <div className="h-10 w-10 rounded-lg bg-success/10 flex items-center justify-center">
                        <CheckCircle className="h-5 w-5 text-success" />
                      </div>
                      <div>
                        <h4 className="font-medium">{item.title}</h4>
                        <div className="flex items-center gap-3 text-sm text-muted-foreground mt-1">
                          <Badge variant="secondary">{item.platform}</Badge>
                          <span>•</span>
                          <span>{item.mentions} mentions corrected</span>
                          <span>•</span>
                          <span>Resolved {item.resolvedAt}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <p className="text-sm font-medium">Resolution Time</p>
                        <p className="text-sm text-muted-foreground">{item.resolutionTime}</p>
                      </div>
                      <Button size="sm" variant="outline" onClick={() => {
                        const fullCase = activeMisinformation.find(c => c.id === item.id);
                        if (fullCase) handleViewDetails(fullCase);
                      }}>
                        View Details
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Monitoring Rules Tab */}
        <TabsContent value="monitoring" className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Automated Monitoring Rules</CardTitle>
                  <CardDescription>
                    Configure what to monitor and how to detect issues
                  </CardDescription>
                </div>
                <Button onClick={handleConfigureRules}>
                  <Settings className="h-4 w-4 mr-2" />
                  Add Rule
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {monitoringRules.map((rule) => (
                <div
                  key={rule.id}
                  className="p-4 rounded-lg border border-border hover:bg-accent/50 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h4 className="font-semibold">{rule.name}</h4>
                        <Badge variant={rule.status === "active" ? "default" : "secondary"}>
                          {rule.status}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground mb-3">
                        {rule.description}
                      </p>
                      <div className="flex items-center gap-4 text-sm">
                        <div className="flex items-center gap-2">
                          <AlertCircle className="h-4 w-4 text-muted-foreground" />
                          <span>{rule.detections} detections</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Clock className="h-4 w-4 text-muted-foreground" />
                          <span>Last triggered {rule.lastTriggered}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline">
                        Edit
                      </Button>
                      <Button size="sm" variant="ghost">
                        {rule.status === "active" ? "Pause" : "Activate"}
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Detection Configuration */}
          <Card>
            <CardHeader>
              <CardTitle>Detection Settings</CardTitle>
              <CardDescription>
                Configure sensitivity and notification preferences
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Detection Sensitivity</label>
                  <select className="w-full p-2 border rounded-lg">
                    <option>High (All potential issues)</option>
                    <option>Medium (Likely issues)</option>
                    <option>Low (Only confirmed issues)</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Scan Frequency</label>
                  <select className="w-full p-2 border rounded-lg">
                    <option>Real-time</option>
                    <option>Every hour</option>
                    <option>Every 6 hours</option>
                    <option>Daily</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Alert Priority Threshold</label>
                  <select className="w-full p-2 border rounded-lg">
                    <option>All severities</option>
                    <option>Medium and High only</option>
                    <option>High only</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Notification Channel</label>
                  <select className="w-full p-2 border rounded-lg">
                    <option>Email + In-app</option>
                    <option>Email only</option>
                    <option>In-app only</option>
                    <option>Slack integration</option>
                  </select>
                </div>
              </div>
              <Button>
                Save Settings
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Dialogs */}
      <MisinformationDetailDialog
        open={detailDialogOpen}
        onOpenChange={setDetailDialogOpen}
        misinformationCase={selectedCase}
      />
      <MisinformationActionDialog
        open={actionDialogOpen}
        onOpenChange={setActionDialogOpen}
        misinformationCase={selectedCase}
      />
    </div>
  );
};

export default MisinformationAlerts;
