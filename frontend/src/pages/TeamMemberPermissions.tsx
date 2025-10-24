import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import { 
  ArrowLeft, 
  User, 
  Mail, 
  Shield,
  LayoutDashboard,
  MessageSquare,
  Search,
  Bell,
  TrendingUp,
  Brain,
  BarChart3,
  Target,
  Users,
  Globe,
  Sparkles,
  Network,
  Link2,
  AlertTriangle,
  FileText,
  Settings,
} from "lucide-react";

const featureCategories = [
  {
    name: "Overview",
    features: [
      { id: "dashboard", name: "Dashboard", icon: LayoutDashboard, description: "View main dashboard and analytics overview" },
    ]
  },
  {
    name: "Tracking",
    features: [
      { id: "mentions", name: "Mentions", icon: MessageSquare, description: "View and manage brand mentions" },
      { id: "prompts", name: "Prompts", icon: Search, description: "Create and manage prompt groups" },
      { id: "alerts", name: "Alerts", icon: Bell, description: "Configure and view alerts" },
    ]
  },
  {
    name: "Analytics",
    features: [
      { id: "sentiment", name: "Sentiment Analysis", icon: TrendingUp, description: "View sentiment trends and analysis" },
      { id: "topics", name: "Topics", icon: Brain, description: "Access topic analysis and trends" },
      { id: "share-of-voice", name: "Share of Voice", icon: BarChart3, description: "View competitive share of voice" },
      { id: "trends", name: "Historical Trends", icon: BarChart3, description: "Access historical trend data" },
    ]
  },
  {
    name: "Strategy",
    features: [
      { id: "content-gaps", name: "Content Gaps", icon: Target, description: "Identify content opportunities" },
      { id: "competitors", name: "Competitors", icon: Users, description: "Manage competitor tracking" },
    ]
  },
  {
    name: "Advanced",
    features: [
      { id: "multilingual", name: "Multilingual", icon: Globe, description: "Manage multilingual monitoring" },
      { id: "copilot", name: "AI Copilot", icon: Sparkles, description: "Access AI recommendations" },
      { id: "prompt-insights", name: "Prompt Insights", icon: TrendingUp, description: "Advanced prompt analytics" },
      { id: "agent-analytics", name: "Agent Analytics", icon: Network, description: "View agent performance metrics" },
      { id: "crawler", name: "AI Crawler", icon: Network, description: "Manage AI crawler settings" },
      { id: "traffic", name: "Traffic Attribution", icon: Link2, description: "Track traffic sources" },
      { id: "misinformation", name: "Misinformation Alerts", icon: AlertTriangle, description: "Monitor brand misinformation" },
    ]
  },
  {
    name: "Reporting",
    features: [
      { id: "reports", name: "Reports", icon: FileText, description: "Create and view reports" },
    ]
  },
  {
    name: "Administration",
    features: [
      { id: "org-settings", name: "Organization Settings", icon: Settings, description: "Manage organization settings" },
      { id: "team-management", name: "Team Management", icon: Users, description: "Manage team members and permissions" },
    ]
  }
];

// Mock team member data
const mockTeamMembers = [
  { 
    id: "1", 
    email: "john@acme.com", 
    name: "John Doe", 
    role: "admin",
    joinedAt: "2024-01-15"
  },
  { 
    id: "2", 
    email: "sarah@acme.com", 
    name: "Sarah Smith", 
    role: "user",
    joinedAt: "2024-02-20"
  },
  { 
    id: "3", 
    email: "mike@acme.com", 
    name: "Mike Johnson", 
    role: "user",
    joinedAt: "2024-03-10"
  },
];

export default function TeamMemberPermissions() {
  const { memberId } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const member = mockTeamMembers.find(m => m.id === memberId);
  
  // Initialize all permissions based on role
  const initializePermissions = () => {
    const allFeatureIds = featureCategories.flatMap(cat => 
      cat.features.map(f => f.id)
    );
    
    if (member?.role === "admin") {
      // Admins get all permissions by default
      return Object.fromEntries(allFeatureIds.map(id => [id, true]));
    } else {
      // Regular users get basic permissions
      return Object.fromEntries(allFeatureIds.map(id => [
        id, 
        ["dashboard", "mentions", "sentiment", "topics", "trends", "reports"].includes(id)
      ]));
    }
  };
  
  const [permissions, setPermissions] = useState(initializePermissions());

  if (!member) {
    return (
      <div className="p-8">
        <div className="max-w-2xl mx-auto text-center">
          <h1 className="text-2xl font-bold mb-4">Team Member Not Found</h1>
          <Button onClick={() => navigate("/organization-settings")}>
            Back to Organization Settings
          </Button>
        </div>
      </div>
    );
  }

  const handleTogglePermission = (featureId: string) => {
    setPermissions(prev => ({
      ...prev,
      [featureId]: !prev[featureId]
    }));
  };

  const handleSavePermissions = () => {
    // TODO: Connect to Supabase
    toast({
      title: "Permissions updated",
      description: `Permissions for ${member.name} have been updated successfully.`,
    });
  };

  const handleGrantAll = () => {
    const allFeatureIds = featureCategories.flatMap(cat => 
      cat.features.map(f => f.id)
    );
    setPermissions(Object.fromEntries(allFeatureIds.map(id => [id, true])));
    toast({
      title: "All permissions granted",
      description: "All features have been enabled.",
    });
  };

  const handleRevokeAll = () => {
    const allFeatureIds = featureCategories.flatMap(cat => 
      cat.features.map(f => f.id)
    );
    setPermissions(Object.fromEntries(allFeatureIds.map(id => [id, false])));
    toast({
      title: "All permissions revoked",
      description: "All features have been disabled.",
    });
  };

  const enabledCount = Object.values(permissions).filter(Boolean).length;
  const totalCount = Object.keys(permissions).length;

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center gap-4">
        <Button 
          variant="ghost" 
          size="icon"
          onClick={() => navigate("/organization-settings")}
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1">
          <h1 className="text-3xl font-bold">Member Permissions</h1>
          <p className="text-muted-foreground mt-2">
            Configure feature access for team members
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
                <User className="h-8 w-8 text-primary" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <CardTitle>{member.name}</CardTitle>
                  <Badge variant={member.role === "admin" ? "default" : "secondary"}>
                    {member.role}
                  </Badge>
                </div>
                <CardDescription className="flex items-center gap-2 mt-1">
                  <Mail className="h-3 w-3" />
                  {member.email}
                </CardDescription>
                <p className="text-xs text-muted-foreground mt-1">
                  Joined {new Date(member.joinedAt).toLocaleDateString()}
                </p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm font-medium">Access Level</p>
              <p className="text-2xl font-bold text-primary">
                {enabledCount}/{totalCount}
              </p>
              <p className="text-xs text-muted-foreground">features enabled</p>
            </div>
          </div>
        </CardHeader>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Feature Permissions</CardTitle>
              <CardDescription>
                Enable or disable access to specific features
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={handleRevokeAll}>
                Revoke All
              </Button>
              <Button variant="outline" size="sm" onClick={handleGrantAll}>
                Grant All
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {featureCategories.map((category, idx) => (
            <div key={category.name}>
              {idx > 0 && <Separator className="my-6" />}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <Shield className="h-5 w-5 text-primary" />
                  {category.name}
                </h3>
                <div className="space-y-3">
                  {category.features.map((feature) => {
                    const Icon = feature.icon;
                    return (
                      <div
                        key={feature.id}
                        className="flex items-center justify-between p-4 border rounded-lg hover:bg-accent/50 transition-colors"
                      >
                        <div className="flex items-center gap-3 flex-1">
                          <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                            <Icon className="h-5 w-5 text-primary" />
                          </div>
                          <div className="flex-1">
                            <Label
                              htmlFor={feature.id}
                              className="text-base font-medium cursor-pointer"
                            >
                              {feature.name}
                            </Label>
                            <p className="text-sm text-muted-foreground">
                              {feature.description}
                            </p>
                          </div>
                        </div>
                        <Switch
                          id={feature.id}
                          checked={permissions[feature.id]}
                          onCheckedChange={() => handleTogglePermission(feature.id)}
                        />
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={() => navigate("/organization-settings")}>
          Cancel
        </Button>
        <Button onClick={handleSavePermissions}>
          Save Permissions
        </Button>
      </div>
    </div>
  );
}
