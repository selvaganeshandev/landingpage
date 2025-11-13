import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/services/api";
import { Plus, Trash2, Globe, Mail, Shield, User, Crown, Settings, Link2, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ProjectAccessManager } from "@/components/ProjectAccessManager";

export default function OrganizationSettings() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user } = useAuth();

  // Organization state
  const [organization, setOrganization] = useState({
    id: 0,
    name: "",
    industry: "",
    team_count: 0,
    created_at: "",
    modified_at: "",
  });

  // Domains state
  const [domains, setDomains] = useState<Array<{
    id: number;
    name: string;
    url: string;
    organisation: number;
    total_mentions: number;
    total_citations: number;
    visibility_score: string;
    average_position: string;
    active_alerts: number;
    sentiment: string;
    sentiment_score: string;
    created_at: string;
    modified_at: string;
  }>>([]);

  const [newDomain, setNewDomain] = useState("");

  // Team members state
  const [teamMembers, setTeamMembers] = useState<Array<{
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
  }>>([]);
  const [invitations, setInvitations] = useState<Array<{
    id: string;
    email: string;
    role: 'admin' | 'user';
    status: 'pending' | 'accepted' | 'declined' | 'expired';
    invited_by: number;
    invited_by_email: string;
    expires_at: string;
    accepted_at?: string | null;
    created_at: string;
  }>>([]);

  // Loading states
  const [isLoading, setIsLoading] = useState(true);
  const [isUpdatingOrg, setIsUpdatingOrg] = useState(false);
  const [isAddingDomain, setIsAddingDomain] = useState(false);
  const [isUpdatingMember, setIsUpdatingMember] = useState<number | null>(null);
  // Confirm dialogs
  const [confirmDomainId, setConfirmDomainId] = useState<number | null>(null);
  const [confirmMemberId, setConfirmMemberId] = useState<number | null>(null);

  // Dialog states
  const [inviteDialogOpen, setInviteDialogOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<"admin" | "user">("user");
  const roleMeta: Record<"admin" | "user", { label: string; description: string }> = {
    user: { label: "User", description: "Can view and manage brand monitoring" },
    admin: { label: "Admin", description: "Full access including team management" },
  };
  const [addDomainDialogOpen, setAddDomainDialogOpen] = useState(false);

  // Project Access Manager states
  const [projectAccessDialogOpen, setProjectAccessDialogOpen] = useState(false);
  const [selectedMemberForAccess, setSelectedMemberForAccess] = useState<{
    id: number;
    name: string;
    email: string;
  } | null>(null);

  // Mock integrations data (keeping for now)
  const [integrations, setIntegrations] = useState([
    {
      id: "1",
      domainId: "1",
      domain: "acme.com",
      type: "google_analytics" as const,
      propertyId: "GA-123456789",
      connectedAt: "2024-01-20",
      status: "active" as const,
      lastSync: "2024-03-14T10:30:00Z"
    },
  ]);

  const [connectIntegrationDialog, setConnectIntegrationDialog] = useState(false);
  const [selectedDomainForIntegration, setSelectedDomainForIntegration] = useState("");
  const [integrationType, setIntegrationType] = useState<"google_analytics" | "search_console">("google_analytics");

  // Load data on component mount
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setIsLoading(true);
      await Promise.all([
        loadOrganization(),
        loadDomains(),
        loadTeamMembers(),
      ]);
    } catch (error) {
      toast({
        title: "Error loading data",
        description: "Failed to load organization data. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const loadOrganization = async () => {
    try {
      const data = await apiClient.getOrganization();
      setOrganization(data);
    } catch (error) {
      console.error("Error loading organization:", error);
    }
  };

  const loadDomains = async () => {
    try {
      const data = await apiClient.getDomains();
      setDomains(data.domains);
    } catch (error) {
      console.error("Error loading domains:", error);
    }
  };

  const loadTeamMembers = async () => {
    try {
      const data = await apiClient.getTeamMembers();
      // Exclude any super_admin accounts from team management UI
      const filtered = (data.members || []).filter((m: any) => m.role !== 'super_admin');
      setTeamMembers(filtered);
      setInvitations(data.invitations || []);
    } catch (error) {
      console.error("Error loading team members:", error);
    }
  };

  const handleAddDomain = async () => {
    if (!newDomain.trim()) {
      toast({
        title: "Domain required",
        description: "Please enter a domain name.",
        variant: "destructive",
      });
      return;
    }

    try {
      setIsAddingDomain(true);
      const domainName = newDomain.trim();
      const domainUrl = domainName.startsWith('http') ? domainName : `https://${domainName}`;

      const response = await apiClient.createDomain({
        name: domainName,
        url: domainUrl,
      });

      // Reload domains to get the updated list
      await loadDomains();
      setNewDomain("");
      setAddDomainDialogOpen(false);

      toast({
        title: "Domain added",
        description: `${domainName} has been added to your organization.`,
      });
    } catch (error: any) {
      toast({
        title: "Error adding domain",
        description: error.message || "Failed to add domain. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsAddingDomain(false);
    }
  };

  const handleRemoveDomainConfirmed = async (id: number) => {
    try {
      await apiClient.deleteDomain(id);

      // Reload domains to get the updated list
      await loadDomains();

      toast({
        title: "Domain removed",
        description: "The domain has been removed from your organization.",
      });
    } catch (error: any) {
      toast({
        title: "Error removing domain",
        description: error.message || "Failed to remove domain. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleUpdateOrgName = async () => {
    try {
      setIsUpdatingOrg(true);

      await apiClient.updateOrganization({
        name: organization.name,
        industry: organization.industry,
      });

      toast({
        title: "Organization updated",
        description: "Your organization details have been updated.",
      });
    } catch (error: any) {
      toast({
        title: "Error updating organization",
        description: error.message || "Failed to update organization. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsUpdatingOrg(false);
    }
  };

  const handleInviteMember = async () => {
    if (!inviteEmail.trim()) return;

    try {
      await apiClient.sendInvitation({
        email: inviteEmail.trim(),
        role: inviteRole,
      });

      setInviteEmail("");
      setInviteRole("user");
      setInviteDialogOpen(false);

      toast({
        title: "Invitation sent",
        description: `An invitation has been sent to ${inviteEmail.trim()}`,
      });
    } catch (error: any) {
      toast({
        title: "Error sending invitation",
        description: error.message || "Failed to send invitation. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleRemoveMemberConfirmed = async (id: number) => {
    try {
      await apiClient.removeTeamMember(id);

      // Reload team members to get the updated list
      await loadTeamMembers();

      toast({
        title: "Member removed",
        description: "Team member has been removed from the organization.",
      });
    } catch (error: any) {
      toast({
        title: "Error removing member",
        description: error.message || "Failed to remove team member. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleUpdateRole = async (id: number, newRole: "admin" | "user") => {
    try {
      setIsUpdatingMember(id);

      await apiClient.updateTeamMemberRole(id, newRole);

      // Reload team members to get the updated list
      await loadTeamMembers();

      toast({
        title: "Role updated",
        description: "Team member role has been updated.",
      });
    } catch (error: any) {
      toast({
        title: "Error updating role",
        description: error.message || "Failed to update team member role. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsUpdatingMember(null);
    }
  };

  const handleOpenProjectAccess = (member: any) => {
    const memberName = `${member.first_name} ${member.last_name}`.trim() || member.email.split('@')[0];
    setSelectedMemberForAccess({
      id: member.id,
      name: memberName,
      email: member.email
    });
    setProjectAccessDialogOpen(true);
  };

  const handleProjectAccessUpdated = () => {
    // Optionally reload team members or show a success message
    toast({
      title: "Project access updated",
      description: "Project access has been updated successfully.",
    });
  };

  const getRoleIcon = (role: "admin" | "user") => {
    return role === "admin" ? Crown : User;
  };

  const getRoleBadgeVariant = (role: "admin" | "user") => {
    return role === "admin" ? "default" : "secondary";
  };

  const handleConnectIntegration = () => {
    if (!selectedDomainForIntegration) {
      toast({
        title: "Domain required",
        description: "Please select a domain to connect the integration to.",
        variant: "destructive"
      });
      return;
    }

    // TODO: Connect to OAuth flow for GA/GSC
    const domain = domains.find(d => d.id === selectedDomainForIntegration);

    const newIntegration = integrationType === "google_analytics"
      ? {
        id: Date.now().toString(),
        domainId: selectedDomainForIntegration,
        domain: domain?.domain || "",
        type: "google_analytics" as const,
        propertyId: `GA-${Math.floor(Math.random() * 1000000000)}`,
        connectedAt: new Date().toISOString().split("T")[0],
        status: "active" as const,
        lastSync: new Date().toISOString()
      }
      : {
        id: Date.now().toString(),
        domainId: selectedDomainForIntegration,
        domain: domain?.domain || "",
        type: "search_console" as const,
        propertyUrl: `https://${domain?.domain}`,
        connectedAt: new Date().toISOString().split("T")[0],
        status: "active" as const,
        lastSync: new Date().toISOString()
      };

    setIntegrations([...integrations, newIntegration]);
    setConnectIntegrationDialog(false);
    setSelectedDomainForIntegration("");

    toast({
      title: "Integration connected",
      description: `${integrationType === "google_analytics" ? "Google Analytics" : "Search Console"} has been connected to ${domain?.domain}`,
    });
  };

  const handleDisconnectIntegration = (id: string) => {
    const integration = integrations.find(i => i.id === id);
    setIntegrations(integrations.filter(i => i.id !== id));
    toast({
      title: "Integration disconnected",
      description: `${integration?.type === "google_analytics" ? "Google Analytics" : "Search Console"} has been disconnected from ${integration?.domain}`,
    });
  };

  const getIntegrationsByDomain = (domainId: string) => {
    return integrations.filter(i => i.domainId === domainId);
  };

  if (isLoading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <div className="flex items-center gap-2">
          <Loader2 className="h-6 w-6 animate-spin" />
          <span>Loading organization data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6 bg-background animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold">Organization Settings</h1>
        <p className="text-muted-foreground mt-2">
          Manage your organization and domains
        </p>
      </div>

      <Card className="border border-border">
        <CardHeader>
          <CardTitle>Organization Details</CardTitle>
          <CardDescription>
            Update your organization information
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="org-name">Organization Name</Label>
            <div className="flex gap-2">
              <Input
                id="org-name"
                value={organization.name}
                onChange={(e) => setOrganization({ ...organization, name: e.target.value })}
              />
              <Button onClick={handleUpdateOrgName} disabled={isUpdatingOrg}>
                {isUpdatingOrg ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save"}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="border border-border">
        <CardHeader>
          <CardTitle>Domains</CardTitle>
          <CardDescription>
            Add and manage domains for your organization. All brand monitoring will be scoped to these domains.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Button onClick={() => setAddDomainDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add Domain
            </Button>
          </div>

          <Separator />

          <div className="space-y-3">
            {domains.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Globe className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p>No domains added yet</p>
              </div>
            ) : (
              domains.map((domain) => (
                <div
                  key={domain.id}
                  className="flex items-center justify-between p-3 border rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <Globe className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="font-medium capitalize">{domain.name}</p>
                      <p className="text-sm text-muted-foreground">{domain.url}</p>

                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setConfirmDomainId(domain.id)}
                  >
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      <Card className="border border-border">
        <CardHeader>
          <CardTitle>Integrations</CardTitle>
          <CardDescription>
            Connect Google Analytics and Search Console for each domain to track traffic attribution
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button onClick={() => setConnectIntegrationDialog(true)}>
            <Link2 className="h-4 w-4 mr-2" />
            Connect Integration
          </Button>

          <Separator />

          <div className="space-y-4">
            {/* {domains.map((domain) => {
              const domainIntegrations: any[] = [];
              return (
                <div key={domain.id} className="p-4 border rounded-lg space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Globe className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium">{domain.domain}</span>
                      <Badge variant={domain.verified ? "default" : "secondary"}>
                        {domain.verified ? "Verified" : "Pending"}
                      </Badge>
                    </div>
                  </div>

                  {domainIntegrations.length === 0 ? (
                    <div className="text-sm text-muted-foreground bg-muted/30 rounded p-3">
                      No integrations connected for this domain
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {domainIntegrations.map((integration) => (
                        <div
                          key={integration.id}
                          className="flex items-center justify-between p-3 bg-muted/30 rounded"
                        >
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-sm">
                                {integration.type === "google_analytics"
                                  ? "Google Analytics"
                                  : "Google Search Console"}
                              </span>
                              {integration.status === "active" ? (
                                <Badge variant="default" className="gap-1">
                                  <CheckCircle2 className="h-3 w-3" />
                                  Active
                                </Badge>
                              ) : (
                                <Badge variant="destructive" className="gap-1">
                                  <AlertCircle className="h-3 w-3" />
                                  Error
                                </Badge>
                              )}
                            </div>
                            <div className="text-xs text-muted-foreground mt-1">
                              {integration.type === "google_analytics"
                                ? `Property: ${integration.propertyId}`
                                : `URL: ${integration.propertyUrl}`}
                            </div>
                            <div className="text-xs text-muted-foreground">
                              Last sync: {new Date(integration.lastSync).toLocaleString()}
                            </div>
                            {integration.error && (
                              <div className="text-xs text-destructive mt-1">
                                Error: {integration.error}
                              </div>
                            )}
                          </div>
                          <div className="flex items-center gap-2">
                            {integration.status === "error" && (
                              <Button variant="outline" size="sm">
                                Reconnect
                              </Button>
                            )}
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleDisconnectIntegration(integration.id)}
                            >
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })} */}
            <div className="text-sm text-muted-foreground bg-muted/30 rounded p-3">
              No integrations connected for this domain
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="border border-border">
        <CardHeader>
          <CardTitle>Team Members</CardTitle>
          <CardDescription>
            Manage your organization's team members and their roles
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button onClick={() => setInviteDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Invite Member
          </Button>

          <Separator />

          {invitations.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-sm font-medium">Team Invitations</h4>
              {invitations.map((inv) => (
                <div
                  key={inv.id}
                  className="flex items-center justify-between p-4 border rounded-lg"
                >
                  <div className="flex items-center gap-4 flex-1">
                    <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                      <Mail className="h-5 w-5 text-primary" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <p className="font-medium">{inv.email}</p>
                        {inv.role === 'admin' ? (
                          <Badge variant="default" className="gap-1">
                            <Crown className="h-3 w-3" />
                            Admin
                          </Badge>
                        ) : (
                          <Badge variant="secondary">User</Badge>
                        )}
                        <Badge variant="secondary" className="gap-1">
                          {inv.status.charAt(0).toUpperCase() + inv.status.slice(1)}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground mt-1">
                        {inv.status === 'pending' ? (
                          <span>Expires {new Date(inv.expires_at).toLocaleDateString()}</span>
                        ) : inv.accepted_at ? (
                          <span>Accepted {new Date(inv.accepted_at).toLocaleDateString()}</span>
                        ) : (
                          <span>Created {new Date(inv.created_at).toLocaleDateString()}</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
              <Separator />
            </div>
          )}

          <div className="space-y-3">
            {teamMembers.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <User className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p>No team members yet</p>
              </div>
            ) : (
              teamMembers.map((member) => {
                const RoleIcon = getRoleIcon(member.role);
                const memberName = `${member.first_name} ${member.last_name}`.trim() || member.email.split('@')[0];
                return (
                  <div
                    key={member.id}
                    className="flex items-center justify-between p-4 border rounded-lg"
                  >
                    <div className="flex items-center gap-4 flex-1">
                      <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                        <User className="h-5 w-5 text-primary" />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <p className="font-medium capitalize">{memberName}</p>
                          {member.role === "admin" && (
                            <Badge variant="default" className="gap-1">
                              <Crown className="h-3 w-3" />
                              Admin
                            </Badge>
                          )}
                          {!member.is_active && (
                            <Badge variant="secondary" className="gap-1">
                              Inactive
                            </Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground mt-1">
                          <Mail className="h-3 w-3" />
                          {member.email}
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                          Joined {new Date(member.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="icon"
                          onClick={() => handleOpenProjectAccess(member)}
                          title="Manage Project Access"
                        >
                          <Globe className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="icon"
                          onClick={() => navigate(`/organization-settings/members/${member.id}`)}
                          title="Manage Module Permissions"
                        >
                          <Settings className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setConfirmMemberId(member.id)}
                          disabled={isUpdatingMember === member.id}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </CardContent>
      </Card>

      <Dialog open={inviteDialogOpen} onOpenChange={setInviteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Invite Team Member</DialogTitle>
            <DialogDescription>
              Send an invitation to join your organization
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="invite-email">Email Address</Label>
              <Input
                id="invite-email"
                type="email"
                placeholder="colleague@company.com"
                className="placeholder:text-muted-foreground placeholder:opacity-70"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="invite-role">Role</Label>
              <Select
                value={inviteRole}
                onValueChange={(value: "admin" | "user") => setInviteRole(value)}
              >
                <SelectTrigger id="invite-role">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="user">
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4" />
                      <span className="font-medium">User</span>
                    </div>
                  </SelectItem>
                  <SelectItem value="admin">
                    <div className="flex items-center gap-2">
                      <Crown className="h-4 w-4" />
                      <span className="font-medium">Admin</span>
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
              <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                {inviteRole === 'admin' ? (
                  <Crown className="h-3 w-3" />
                ) : (
                  <User className="h-3 w-3" />
                )}
                <span>{roleMeta[inviteRole].description}</span>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setInviteDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleInviteMember}>
              Send Invitation
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={connectIntegrationDialog} onOpenChange={setConnectIntegrationDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Connect Integration</DialogTitle>
            <DialogDescription>
              Connect Google Analytics or Search Console to a domain
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="integration-domain">Domain</Label>
              <Select
                value={selectedDomainForIntegration}
                onValueChange={setSelectedDomainForIntegration}
              >
                <SelectTrigger id="integration-domain">
                  <SelectValue placeholder="Select a domain" />
                </SelectTrigger>
                <SelectContent>
                  {domains.map((domain) => (
                    <SelectItem key={domain.id} value={domain.id}>
                      <div className="flex items-center gap-2">
                        <Globe className="h-4 w-4" />
                        {domain.domain}
                        {!domain.verified && (
                          <Badge variant="secondary" className="ml-2">Pending</Badge>
                        )}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="integration-type">Integration Type</Label>
              <Select
                value={integrationType}
                onValueChange={(value: "google_analytics" | "search_console") =>
                  setIntegrationType(value)
                }
              >
                <SelectTrigger id="integration-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="google_analytics">
                    <div className="flex items-center gap-2">
                      <Link2 className="h-4 w-4" />
                      <span className="font-medium">Google Analytics</span>
                    </div>
                  </SelectItem>
                  <SelectItem value="search_console">
                    <div className="flex items-center gap-2">
                      <Link2 className="h-4 w-4" />
                      <span className="font-medium">Google Search Console</span>
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
              <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                <Link2 className="h-3 w-3" />
                <span>
                  {integrationType === 'google_analytics' ? 'Track user behavior and conversions' : 'Monitor search performance and queries'}
                </span>
              </div>
            </div>
            <div className="bg-muted/50 p-3 rounded text-sm">
              <p className="font-medium mb-1">Next Steps:</p>
              <ol className="list-decimal list-inside space-y-1 text-muted-foreground">
                <li>You'll be redirected to Google to authenticate</li>
                <li>Select the property you want to connect</li>
                <li>Grant required permissions</li>
                <li>Data will start syncing automatically</li>
              </ol>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setConnectIntegrationDialog(false)}
            >
              Cancel
            </Button>
            <Button onClick={handleConnectIntegration}>
              Connect with Google
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={addDomainDialogOpen} onOpenChange={setAddDomainDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Domain</DialogTitle>
            <DialogDescription>
              Add a new domain to monitor for your organization
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="domain-name">Domain Name</Label>
              <Input
                id="domain-name"
                placeholder="example.com"
                value={newDomain}
                onChange={(e) => setNewDomain(e.target.value)}
                onKeyPress={(e) => e.key === "Enter" && handleAddDomain()}
              />
              <p className="text-xs text-muted-foreground">
                Enter the domain name without http:// or https://
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddDomainDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleAddDomain} disabled={isAddingDomain}>
              {isAddingDomain ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Plus className="h-4 w-4 mr-2" />}
              Add Domain
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Confirm Delete Domain */}
      <Dialog open={confirmDomainId !== null} onOpenChange={(open) => !open && setConfirmDomainId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove Domain</DialogTitle>
            <DialogDescription>
              Are you sure you want to remove this domain? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmDomainId(null)}>Cancel</Button>
            <Button
              variant="destructive"
              onClick={async () => {
                if (confirmDomainId !== null) {
                  await handleRemoveDomainConfirmed(confirmDomainId);
                  setConfirmDomainId(null);
                }
              }}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Confirm Remove Team Member */}
      <Dialog open={confirmMemberId !== null} onOpenChange={(open) => !open && setConfirmMemberId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove Team Member</DialogTitle>
            <DialogDescription>
              Are you sure you want to remove this member? The account will be deactivated.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmMemberId(null)}>Cancel</Button>
            <Button
              variant="destructive"
              onClick={async () => {
                if (confirmMemberId !== null) {
                  await handleRemoveMemberConfirmed(confirmMemberId);
                  setConfirmMemberId(null);
                }
              }}
            >
              Remove
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Project Access Manager */}
      {selectedMemberForAccess && (
        <ProjectAccessManager
          userId={selectedMemberForAccess.id}
          userName={selectedMemberForAccess.name}
          userEmail={selectedMemberForAccess.email}
          open={projectAccessDialogOpen}
          onOpenChange={setProjectAccessDialogOpen}
          onAccessUpdated={handleProjectAccessUpdated}
        />
      )}
    </div>
  );
}
