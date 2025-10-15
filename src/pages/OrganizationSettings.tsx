import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import { Plus, Trash2, Globe, Mail, Shield, User, Crown, Settings } from "lucide-react";
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

export default function OrganizationSettings() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [orgName, setOrgName] = useState("Acme Corp");
  const [domains, setDomains] = useState([
    { id: "1", domain: "acme.com", verified: true },
    { id: "2", domain: "acmecorp.com", verified: false },
  ]);
  const [newDomain, setNewDomain] = useState("");
  
  const [teamMembers, setTeamMembers] = useState([
    { 
      id: "1", 
      email: "john@acme.com", 
      name: "John Doe", 
      role: "admin" as const,
      joinedAt: "2024-01-15"
    },
    { 
      id: "2", 
      email: "sarah@acme.com", 
      name: "Sarah Smith", 
      role: "user" as const,
      joinedAt: "2024-02-20"
    },
    { 
      id: "3", 
      email: "mike@acme.com", 
      name: "Mike Johnson", 
      role: "user" as const,
      joinedAt: "2024-03-10"
    },
  ]);
  
  const [inviteDialogOpen, setInviteDialogOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<"admin" | "user">("user");

  const handleAddDomain = () => {
    if (!newDomain.trim()) return;

    // TODO: Connect to Supabase
    const domain = {
      id: Date.now().toString(),
      domain: newDomain.trim(),
      verified: false,
    };
    setDomains([...domains, domain]);
    setNewDomain("");
    toast({
      title: "Domain added",
      description: `${domain.domain} has been added to your organization.`,
    });
  };

  const handleRemoveDomain = (id: string) => {
    // TODO: Connect to Supabase
    setDomains(domains.filter(d => d.id !== id));
    toast({
      title: "Domain removed",
      description: "The domain has been removed from your organization.",
    });
  };

  const handleUpdateOrgName = () => {
    // TODO: Connect to Supabase
    toast({
      title: "Organization updated",
      description: "Your organization name has been updated.",
    });
  };

  const handleInviteMember = () => {
    if (!inviteEmail.trim()) return;

    // TODO: Connect to Supabase
    const newMember = {
      id: Date.now().toString(),
      email: inviteEmail.trim(),
      name: inviteEmail.split("@")[0],
      role: inviteRole,
      joinedAt: new Date().toISOString().split("T")[0],
    };
    
    setTeamMembers([...teamMembers, newMember]);
    setInviteEmail("");
    setInviteRole("user");
    setInviteDialogOpen(false);
    
    toast({
      title: "Invitation sent",
      description: `An invitation has been sent to ${newMember.email}`,
    });
  };

  const handleRemoveMember = (id: string) => {
    // TODO: Connect to Supabase
    const member = teamMembers.find(m => m.id === id);
    setTeamMembers(teamMembers.filter(m => m.id !== id));
    toast({
      title: "Member removed",
      description: `${member?.name} has been removed from the organization.`,
    });
  };

  const handleUpdateRole = (id: string, newRole: "admin" | "user") => {
    // TODO: Connect to Supabase
    setTeamMembers(teamMembers.map(m => 
      m.id === id ? { ...m, role: newRole } : m
    ));
    toast({
      title: "Role updated",
      description: "Team member role has been updated.",
    });
  };

  const getRoleIcon = (role: "admin" | "user") => {
    return role === "admin" ? Crown : User;
  };

  const getRoleBadgeVariant = (role: "admin" | "user") => {
    return role === "admin" ? "default" : "secondary";
  };

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Organization Settings</h1>
        <p className="text-muted-foreground mt-2">
          Manage your organization and domains
        </p>
      </div>

      <Card>
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
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
              />
              <Button onClick={handleUpdateOrgName}>Save</Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Domains</CardTitle>
          <CardDescription>
            Add and manage domains for your organization. All brand monitoring will be scoped to these domains.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Input
              placeholder="example.com"
              value={newDomain}
              onChange={(e) => setNewDomain(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && handleAddDomain()}
            />
            <Button onClick={handleAddDomain}>
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
                      <p className="font-medium">{domain.domain}</p>
                      <Badge variant={domain.verified ? "default" : "secondary"} className="mt-1">
                        {domain.verified ? "Verified" : "Pending"}
                      </Badge>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleRemoveDomain(domain.id)}
                  >
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
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

          <div className="space-y-3">
            {teamMembers.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <User className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p>No team members yet</p>
              </div>
            ) : (
              teamMembers.map((member) => {
                const RoleIcon = getRoleIcon(member.role);
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
                          <p className="font-medium">{member.name}</p>
                          {member.role === "admin" && (
                            <Badge variant="default" className="gap-1">
                              <Crown className="h-3 w-3" />
                              Admin
                            </Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground mt-1">
                          <Mail className="h-3 w-3" />
                          {member.email}
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                          Joined {new Date(member.joinedAt).toLocaleDateString()}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Select
                          value={member.role}
                          onValueChange={(value: "admin" | "user") =>
                            handleUpdateRole(member.id, value)
                          }
                        >
                          <SelectTrigger className="w-[120px]">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="admin">Admin</SelectItem>
                            <SelectItem value="user">User</SelectItem>
                          </SelectContent>
                        </Select>
                        <Button
                          variant="outline"
                          size="icon"
                          onClick={() => navigate(`/organization-settings/members/${member.id}`)}
                          title="Manage Permissions"
                        >
                          <Settings className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleRemoveMember(member.id)}
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
                      <div>
                        <p className="font-medium">User</p>
                        <p className="text-xs text-muted-foreground">
                          Can view and manage brand monitoring
                        </p>
                      </div>
                    </div>
                  </SelectItem>
                  <SelectItem value="admin">
                    <div className="flex items-center gap-2">
                      <Crown className="h-4 w-4" />
                      <div>
                        <p className="font-medium">Admin</p>
                        <p className="text-xs text-muted-foreground">
                          Full access including team management
                        </p>
                      </div>
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
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
    </div>
  );
}
