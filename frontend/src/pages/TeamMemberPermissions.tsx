import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/services/api";
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
  Loader2,
  Calendar,
  SearchCheck,
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
      { id: "prompts", name: "Prompts", icon: Search, description: "Create and manage prompt groups" },
      { id: "mentions", name: "Mentions", icon: MessageSquare, description: "View and manage brand mentions" },
      { id: "citations", name: "Citations", icon: Link2, description: "View citation sources and references" },
      { id: "alerts", name: "Alerts", icon: Bell, description: "Configure and view alerts" },
    ]
  },
  {
    name: "Analytics",
    features: [
      { id: "sentiment_analysis", name: "Sentiment", icon: TrendingUp, description: "View sentiment trends and analysis" },
      { id: "topics", name: "Topics", icon: Brain, description: "Access topic analysis and trends" },
      { id: "share_of_voice", name: "Share of Voice", icon: BarChart3, description: "View competitive share of voice" },
      { id: "historical_trends", name: "Historical Trends", icon: BarChart3, description: "Access historical trend data" },
    ]
  },
  {
    name: "Strategy",
    features: [
      { id: "content_gaps", name: "Content Gaps", icon: Target, description: "Identify content opportunities" },
      { id: "competitors", name: "Competitors", icon: Users, description: "Manage competitor tracking" },
      { id: "content_planner", name: "Content Planner", icon: Calendar, description: "Plan and schedule content" },
    ]
  },
  {
    name: "Advanced",
    features: [
      { id: "traffic_attribution", name: "Traffic Attribution", icon: Link2, description: "Track traffic sources" },
      { id: "misinformation_alerts", name: "Misinformation Alerts", icon: AlertTriangle, description: "Monitor brand misinformation" },
    ]
  },
  {
    name: "SEO Monitoring",
    features: [
      { id: "keyword_rankings", name: "Keyword Rankings", icon: SearchCheck, description: "View keyword ranking positions and trends" },
      { id: "organic_reports", name: "Organic Reports", icon: FileText, description: "Generate and view organic search reports" },
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
      { id: "organization_settings", name: "Organization Settings", icon: Settings, description: "Manage organization settings" },
      { id: "team_management", name: "Team Management", icon: Users, description: "Manage team members and permissions" },
    ]
  }
];


export default function TeamMemberPermissions() {
  const { memberId } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user } = useAuth();
  
  // State management
  const [member, setMember] = useState<{
    id: number;
    email: string;
    first_name: string;
    last_name: string;
    role: 'admin' | 'user';
    organisation: number;
    organisation_name: string;
    is_active: boolean;
    created_at: string;
    modified_at: string;
  } | null>(null);
  
  const [permissions, setPermissions] = useState<Record<string, boolean>>({});
  const [userPermissions, setUserPermissions] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  
  // Load member data and permissions
  useEffect(() => {
    if (memberId) {
      loadMemberData();
    }
  }, [memberId]);
  
  const loadMemberData = async () => {
    try {
      setIsLoading(true);
      
      // Load team members to find the specific member
      const teamData = await apiClient.getTeamMembers();
      const foundMember = teamData.members.find(m => m.id === parseInt(memberId!));
      
      if (!foundMember) {
        toast({
          title: "Member not found",
          description: "The requested team member could not be found.",
          variant: "destructive",
        });
        navigate("/organization-settings");
        return;
      }
      
      setMember(foundMember);
      
      // Load user permissions
      const permissionsData = await apiClient.listUserPermissions(foundMember.id);
      setUserPermissions(permissionsData.permissions);
      
      // Initialize permissions state
      initializePermissions(permissionsData.permissions);
      
    } catch (error: any) {
      toast({
        title: "Error loading member data",
        description: error.message || "Failed to load member information.",
        variant: "destructive",
      });
      navigate("/organization-settings");
    } finally {
      setIsLoading(false);
    }
  };
  
  const initializePermissions = (userPerms: any[]) => {
    const allFeatureIds = featureCategories.flatMap(cat => 
      cat.features.map(f => f.id)
    );
    
    const permissionsMap: Record<string, boolean> = {};
    
    allFeatureIds.forEach(featureId => {
      const userPerm = userPerms.find(p => p.module === featureId);
      permissionsMap[featureId] = !!userPerm; // true if permission exists, false otherwise
    });
    
    setPermissions(permissionsMap);
  };

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

  const handleSavePermissions = async () => {
    if (!member) return;
    
    try {
      setIsSaving(true);
      
      // Get current permissions
      const currentPerms = userPermissions;
      const newPerms = permissions;
      
      // Find permissions to add and remove
      const permissionsToAdd: string[] = [];
      const permissionsToRemove: number[] = [];
      
      Object.keys(newPerms).forEach(module => {
        const hasPermission = newPerms[module];
        const existingPerm = currentPerms.find(p => p.module === module);
        
        if (hasPermission && !existingPerm) {
          permissionsToAdd.push(module);
        } else if (!hasPermission && existingPerm) {
          permissionsToRemove.push(existingPerm.id);
        }
      });
      
      // Remove permissions
      for (const permId of permissionsToRemove) {
        await apiClient.deletePermission(permId);
      }
      
      // Add new permissions
      if (permissionsToAdd.length > 0) {
        await apiClient.bulkAssignPermissions(permissionsToAdd.map(module => ({
          user: member.id,
          module,
          permission_level: 'read'
        })));
      }
      
      // Reload permissions to get updated data
      await loadMemberData();
      
      toast({
        title: "Permissions updated",
        description: `Permissions for ${member.first_name} ${member.last_name} have been updated successfully.`,
      });
      
    } catch (error: any) {
      toast({
        title: "Error updating permissions",
        description: error.message || "Failed to update permissions. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleGrantAll = async () => {
    if (!member) return;
    
    try {
      setIsSaving(true);
      
      const allFeatureIds = featureCategories.flatMap(cat => 
        cat.features.map(f => f.id)
      );
      
      await apiClient.grantAllPermissions(member.id);
      
      // Update local state
      setPermissions(Object.fromEntries(allFeatureIds.map(id => [id, true])));
      
      // Reload permissions
      await loadMemberData();
      
      toast({
        title: "All permissions granted",
        description: "All features have been enabled.",
      });
      
    } catch (error: any) {
      toast({
        title: "Error granting permissions",
        description: error.message || "Failed to grant all permissions. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleRevokeAll = async () => {
    if (!member) return;
    
    try {
      setIsSaving(true);
      
      const allFeatureIds = featureCategories.flatMap(cat => 
        cat.features.map(f => f.id)
      );
      
      await apiClient.revokeAllPermissions(member.id);
      
      // Update local state
      setPermissions(Object.fromEntries(allFeatureIds.map(id => [id, false])));
      
      // Reload permissions
      await loadMemberData();
      
      toast({
        title: "All permissions revoked",
        description: "All features have been disabled.",
      });
      
    } catch (error: any) {
      toast({
        title: "Error revoking permissions",
        description: error.message || "Failed to revoke all permissions. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <div className="flex items-center gap-2">
          <Loader2 className="h-6 w-6 animate-spin" />
          <span>Loading member permissions...</span>
        </div>
      </div>
    );
  }

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

  const memberName = `${member.first_name} ${member.last_name}`.trim() || member.email.split('@')[0];
  const enabledCount = Object.values(permissions).filter(Boolean).length;
  const totalCount = Object.keys(permissions).length;

  return (
    <div className="p-8 space-y-6 bg-background animate-fade-in">
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

      <Card className="border border-border">
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
                <User className="h-8 w-8 text-primary" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <CardTitle>{memberName}</CardTitle>
                  <Badge variant={member.role === "admin" ? "default" : "secondary"}>
                    {member.role}
                  </Badge>
                  {!member.is_active && (
                    <Badge variant="secondary">Inactive</Badge>
                  )}
                </div>
                <CardDescription className="flex items-center gap-2 mt-1">
                  <Mail className="h-3 w-3" />
                  {member.email}
                </CardDescription>
                <p className="text-xs text-muted-foreground mt-1">
                  Joined {new Date(member.created_at).toLocaleDateString()}
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

      <Card className="border border-border">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Feature Permissions</CardTitle>
              <CardDescription>
                Enable or disable access to specific features
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={handleRevokeAll} disabled={isSaving}>
                {isSaving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                Revoke All
              </Button>
              <Button variant="outline" size="sm" onClick={handleGrantAll} disabled={isSaving}>
                {isSaving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
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
        <Button variant="outline" onClick={() => navigate("/organization-settings")} disabled={isSaving}>
          Cancel
        </Button>
        <Button onClick={handleSavePermissions} disabled={isSaving}>
          {isSaving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
          Save Permissions
        </Button>
      </div>
    </div>
  );
}
