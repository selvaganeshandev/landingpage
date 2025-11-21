import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/services/api";
import { Plus, Trash2, Globe, Mail, Shield, User, Crown, Settings, Link2, CheckCircle2, AlertCircle, Loader2, X, Check, ChevronDown } from "lucide-react";
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
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { cn } from "@/lib/utils";
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
    processing_status?: string;
    track_message?: string;
  }>>([]);

  const [newDomain, setNewDomain] = useState("");
  const [newDomainCountry, setNewDomainCountry] = useState("us");
  const [newDomainKeywords, setNewDomainKeywords] = useState<string[]>([]);
  const [keywordInput, setKeywordInput] = useState("");
  const [isFetchingKeywords, setIsFetchingKeywords] = useState(false);

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
  const [addKeywordsDialogOpen, setAddKeywordsDialogOpen] = useState(false);
  const [selectedDomainForKeywords, setSelectedDomainForKeywords] = useState<number | null>(null);
  const [newKeywordsInput, setNewKeywordsInput] = useState("");
  const [newKeywordsList, setNewKeywordsList] = useState<string[]>([]);
  const [isAddingKeywords, setIsAddingKeywords] = useState(false);
  const [countryDropdownOpen, setCountryDropdownOpen] = useState(false);

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

  // Poll for domain updates when there are processing domains
  useEffect(() => {
    const hasProcessingDomains = domains.some(d =>
      d.processing_status && ['INIT', 'SCHD', 'PROC'].includes(d.processing_status)
    );

    if (!hasProcessingDomains) return;

    const interval = setInterval(() => {
      loadDomains();
    }, 10000); // Poll every 10 seconds

    return () => clearInterval(interval);
  }, [domains]);

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

  const MAX_KEYWORD_LENGTH = 255;

  // Country list for searchable dropdown
  const countries = [
    { value: "us", label: "United States" },
    { value: "gb", label: "United Kingdom" },
    { value: "ca", label: "Canada" },
    { value: "au", label: "Australia" },
    { value: "de", label: "Germany" },
    { value: "fr", label: "France" },
    { value: "es", label: "Spain" },
    { value: "it", label: "Italy" },
    { value: "jp", label: "Japan" },
    { value: "in", label: "India" },
    { value: "br", label: "Brazil" },
    { value: "mx", label: "Mexico" },
    { value: "nl", label: "Netherlands" },
    { value: "se", label: "Sweden" },
    { value: "no", label: "Norway" },
    { value: "dk", label: "Denmark" },
    { value: "fi", label: "Finland" },
    { value: "pl", label: "Poland" },
    { value: "be", label: "Belgium" },
    { value: "at", label: "Austria" },
    { value: "ch", label: "Switzerland" },
    { value: "ie", label: "Ireland" },
    { value: "nz", label: "New Zealand" },
    { value: "sg", label: "Singapore" },
  ];

  const selectedCountry = countries.find(c => c.value === newDomainCountry);

  const handleAddKeyword = () => {
    const trimmedInput = keywordInput.trim();
    if (!trimmedInput) return;

    // Split by comma, normalize to lowercase, trim whitespace, validate length
    const newKeywords = trimmedInput
      .split(',')
      .map(k => k.trim().toLowerCase())
      .filter(k => {
        if (k.length === 0) return false;
        if (k.length > MAX_KEYWORD_LENGTH) {
          toast({
            title: "Keyword too long",
            description: `"${k}" exceeds ${MAX_KEYWORD_LENGTH} characters. Please shorten it.`,
            variant: "destructive",
          });
          return false;
        }
        return true;
      })
      .filter(k => !newDomainKeywords.includes(k)); // Remove duplicates

    if (newKeywords.length > 0) {
      setNewDomainKeywords([...newDomainKeywords, ...newKeywords]);
      setKeywordInput("");
    } else if (trimmedInput.split(',').some(k => k.trim().toLowerCase().length > MAX_KEYWORD_LENGTH)) {
      // Already showed error for length, but check if all were duplicates
      const allDuplicates = trimmedInput
        .split(',')
        .map(k => k.trim().toLowerCase())
        .filter(k => k.length > 0 && k.length <= MAX_KEYWORD_LENGTH)
        .every(k => newDomainKeywords.includes(k));
      
      if (allDuplicates) {
        toast({
          title: "Duplicate keywords",
          description: "These keywords are already added.",
          variant: "default",
        });
      }
    }
  };

  const handleRemoveKeyword = (keyword: string) => {
    setNewDomainKeywords(newDomainKeywords.filter(k => k !== keyword));
  };

  const handleOpenAddKeywordsDialog = (domainId: number) => {
    setSelectedDomainForKeywords(domainId);
    setNewKeywordsInput("");
    setNewKeywordsList([]);
    setAddKeywordsDialogOpen(true);
  };

  const handleAddKeywordToExisting = () => {
    const trimmedInput = newKeywordsInput.trim();
    if (!trimmedInput) return;

    // Split by comma, normalize to lowercase, trim whitespace, validate length
    const newKeywords = trimmedInput
      .split(',')
      .map(k => k.trim().toLowerCase())
      .filter(k => {
        if (k.length === 0) return false;
        if (k.length > MAX_KEYWORD_LENGTH) {
          toast({
            title: "Keyword too long",
            description: `"${k}" exceeds ${MAX_KEYWORD_LENGTH} characters. Please shorten it.`,
            variant: "destructive",
          });
          return false;
        }
        return true;
      })
      .filter(k => !newKeywordsList.includes(k)); // Remove duplicates

    if (newKeywords.length > 0) {
      setNewKeywordsList([...newKeywordsList, ...newKeywords]);
      setNewKeywordsInput("");
    } else if (trimmedInput.split(',').some(k => k.trim().toLowerCase().length > MAX_KEYWORD_LENGTH)) {
      // Already showed error for length, but check if all were duplicates
      const allDuplicates = trimmedInput
        .split(',')
        .map(k => k.trim().toLowerCase())
        .filter(k => k.length > 0 && k.length <= MAX_KEYWORD_LENGTH)
        .every(k => newKeywordsList.includes(k));
      
      if (allDuplicates) {
        toast({
          title: "Duplicate keywords",
          description: "These keywords are already added.",
          variant: "default",
        });
      }
    }
  };

  const handleRemoveKeywordFromExisting = (keyword: string) => {
    setNewKeywordsList(newKeywordsList.filter(k => k !== keyword));
  };

  const handleAddKeywordsToDomain = async () => {
    if (!selectedDomainForKeywords || newKeywordsList.length === 0) {
      toast({
        title: "Keywords required",
        description: "Please add at least one keyword.",
        variant: "destructive",
      });
      return;
    }

    try {
      setIsAddingKeywords(true);
      const domain = domains.find(d => d.id === selectedDomainForKeywords);
      
      // Add keywords one by one
      let successCount = 0;
      let errorCount = 0;
      
      for (const keywordText of newKeywordsList) {
        try {
          await apiClient.createKeyword({
            keyword: keywordText,
            domain: selectedDomainForKeywords,
          });
          successCount++;
        } catch (error: any) {
          errorCount++;
          console.error(`Failed to add keyword "${keywordText}":`, error);
        }
      }

      // Reload domains to get updated data
      await loadDomains();

      // Reset form
      setNewKeywordsInput("");
      setNewKeywordsList([]);
      setAddKeywordsDialogOpen(false);
      setSelectedDomainForKeywords(null);

      if (errorCount === 0) {
        toast({
          title: "Keywords added successfully!",
          description: `Added ${successCount} keyword(s) to ${domain?.name || 'domain'}.`,
        });
      } else {
        toast({
          title: "Partially successful",
          description: `Added ${successCount} keyword(s), ${errorCount} failed (may already exist).`,
          variant: "default",
        });
      }
    } catch (error: any) {
      toast({
        title: "Error adding keywords",
        description: error.message || "Failed to add keywords. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsAddingKeywords(false);
    }
  };

  const handleFetchKeywordsFromGSC = async () => {
    if (!newDomain.trim()) {
      toast({
        title: "Domain required",
        description: "Please enter a domain name first.",
        variant: "destructive",
      });
      return;
    }

    try {
      setIsFetchingKeywords(true);

      // TODO: Implement actual GSC API call
      // For now, show a message that this feature is coming soon
      toast({
        title: "Coming Soon",
        description: "Google Search Console integration is being set up. This feature will be available soon.",
      });

      // Placeholder for when GSC integration is ready:
      // const response = await apiClient.fetchKeywordsFromGSC({ domain: newDomain.trim() });
      // setNewDomainKeywords([...newDomainKeywords, ...response.keywords]);
    } catch (error: any) {
      toast({
        title: "Error fetching keywords",
        description: error.message || "Failed to fetch keywords from Google Search Console.",
        variant: "destructive",
      });
    } finally {
      setIsFetchingKeywords(false);
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

    // Validate keywords are provided (mandatory)
    if (newDomainKeywords.length === 0) {
      toast({
        title: "Keywords required",
        description: "Please add at least one keyword before creating the domain. Keywords are mandatory.",
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
        country: newDomainCountry,
        keywords: newDomainKeywords.join(','), // Keywords are now mandatory, always send
      });

      // Reload domains to get the updated list (both local state and global store)
      await loadDomains(); // Update local state for this page

      // Also update the global domain store so DomainSelector refreshes
      const { useDomainStore } = await import('@/stores/domainStore');
      await useDomainStore.getState().loadDomains();

      // Reset form
      setNewDomain("");
      setNewDomainCountry("us");
      setNewDomainKeywords([]);
      setKeywordInput("");
      setAddDomainDialogOpen(false);

      toast({
        title: "Brand added successfully!",
        description: `${domainName} is now being processed. We'll notify you when it's ready.`,
        duration: 5000,
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

      // Reload domains to get the updated list (both local state and global store)
      await loadDomains(); // Update local state for this page

      // Also update the global domain store so DomainSelector refreshes
      const { useDomainStore } = await import('@/stores/domainStore');
      await useDomainStore.getState().loadDomains();

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
              domains.map((domain) => {
                const isProcessing = domain.processing_status && ['INIT', 'SCHD', 'PROC'].includes(domain.processing_status);
                const isFailed = domain.processing_status === 'FAIL';
                const isCompleted = !domain.processing_status || domain.processing_status === 'COMP';

                const getStatusLabel = () => {
                  if (domain.processing_status === 'INIT') return 'Initializing';
                  if (domain.processing_status === 'SCHD') return 'Scheduled';
                  if (domain.processing_status === 'PROC') return 'Processing';
                  if (domain.processing_status === 'FAIL') return 'Failed';
                  return 'Ready';
                };

                return (
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

                    <div className="flex items-center gap-2">
                      {/* Status Badge */}
                      {isProcessing && (
                        <Badge variant="outline" className="gap-1 border-orange-500 text-orange-600 bg-orange-50">
                          <Loader2 className="h-3 w-3 animate-spin" />
                          {getStatusLabel()}
                        </Badge>
                      )}
                      {isFailed && (
                        <Badge variant="outline" className="gap-1 border-red-500 text-red-600 bg-red-50">
                          <AlertCircle className="h-3 w-3" />
                          Failed
                        </Badge>
                      )}
                      {isCompleted && (
                        <Badge variant="outline" className="gap-1 border-green-500 text-green-600 bg-green-50">
                          <CheckCircle2 className="h-3 w-3" />
                          Ready
                        </Badge>
                      )}

                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleOpenAddKeywordsDialog(domain.id)}
                        className="gap-2"
                      >
                        <Plus className="h-4 w-4" />
                        Add Keywords
                      </Button>

                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setConfirmDomainId(domain.id)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </div>
                );
              })
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
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Add Domain</DialogTitle>
            <DialogDescription>
              Add a new domain to monitor for your organization
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {/* Domain Name */}
            <div className="space-y-2">
              <Label htmlFor="domain-name">Domain Name</Label>
              <Input
                id="domain-name"
                placeholder="example.com"
                value={newDomain}
                onChange={(e) => setNewDomain(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Enter the domain name without http:// or https://
              </p>
            </div>

            {/* Country Selector - Searchable */}
            <div className="space-y-2">
              <Label htmlFor="domain-country">Country</Label>
              <Popover open={countryDropdownOpen} onOpenChange={setCountryDropdownOpen}>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    role="combobox"
                    aria-expanded={countryDropdownOpen}
                    className="w-full justify-between"
                    id="domain-country"
                  >
                    {selectedCountry ? selectedCountry.label : "Select country..."}
                    <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-[var(--radix-popover-trigger-width)] p-0" align="start">
                  <Command>
                    <CommandInput placeholder="Search country..." />
                    <CommandList>
                      <CommandEmpty>No country found.</CommandEmpty>
                      <CommandGroup>
                        {countries.map((country) => (
                          <CommandItem
                            key={country.value}
                            value={country.label}
                            onSelect={() => {
                              setNewDomainCountry(country.value);
                              setCountryDropdownOpen(false);
                            }}
                          >
                            <Check
                              className={cn(
                                "mr-2 h-4 w-4",
                                newDomainCountry === country.value ? "opacity-100" : "opacity-0"
                              )}
                            />
                            {country.label}
                          </CommandItem>
                        ))}
                      </CommandGroup>
                    </CommandList>
                  </Command>
                </PopoverContent>
              </Popover>
              <p className="text-xs text-muted-foreground">
                Select the primary country for this brand
              </p>
            </div>

            {/* Keywords Input */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="domain-keywords">
                  Keywords <span className="text-destructive">*</span> (Required)
                </Label>
                <Button
                  type="button"
                  variant="default"
                  size="sm"
                  onClick={handleFetchKeywordsFromGSC}
                  disabled={isFetchingKeywords}
                  className="gap-2"
                >
                  {isFetchingKeywords ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                    </svg>
                  )}
                  Fetch from GSC
                </Button>
              </div>
              <div className="space-y-2">
                <Textarea
                  id="domain-keywords"
                  placeholder="Enter keywords separated by commas (e.g., seo, digital marketing)"
                  value={keywordInput}
                  onChange={(e) => setKeywordInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                      e.preventDefault();
                      handleAddKeyword();
                    }
                  }}
                  className="min-h-[100px]"
                />
                <div className="flex justify-end">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleAddKeyword}
                    disabled={!keywordInput.trim()}
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Add Keywords
                  </Button>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                💡 Tip: Add at least one keyword separated by commas. Click "Add Keywords" or press Ctrl+Enter/Cmd+Enter to add to the list. Keywords are normalized to lowercase and must be under 255 characters.
              </p>

              {/* Keyword Tags */}
              {newDomainKeywords.length > 0 && (
                <div className="space-y-2">
                  <div className="flex flex-wrap gap-2 p-3 border rounded-lg bg-muted/30 max-h-32 overflow-y-auto">
                    {newDomainKeywords.map((keyword, index) => (
                      <Badge
                        key={index}
                        variant="default"
                        className="gap-1 pr-1"
                      >
                        {keyword}
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="h-4 w-4 p-0 hover:bg-background/20"
                          onClick={() => handleRemoveKeyword(keyword)}
                        >
                          <X className="h-3 w-3" />
                        </Button>
                      </Badge>
                    ))}
                  </div>
                  <div className="flex justify-start">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setNewDomainKeywords([])}
                      className="h-8 text-xs"
                    >
                      Clear all
                    </Button>
                  </div>
                </div>
              )}
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

      {/* Add Keywords Dialog */}
      <Dialog open={addKeywordsDialogOpen} onOpenChange={setAddKeywordsDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Add Keywords</DialogTitle>
            <DialogDescription>
              Add additional keywords to {domains.find(d => d.id === selectedDomainForKeywords)?.name || 'this domain'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {/* Keywords Input */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="add-keywords-input">
                  Keywords <span className="text-destructive">*</span>
                </Label>
              </div>
              <Textarea
                id="add-keywords-input"
                placeholder="Enter keywords separated by commas (e.g., seo, digital marketing). Press Ctrl+Enter or Cmd+Enter to add."
                value={newKeywordsInput}
                onChange={(e) => setNewKeywordsInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                    e.preventDefault();
                    handleAddKeywordToExisting();
                  }
                }}
                className="min-h-[100px]"
              />
              <p className="text-xs text-muted-foreground">
                💡 Tip: Add keywords separated by commas. Press Ctrl+Enter or Cmd+Enter to add. Keywords are normalized to lowercase and must be under 255 characters.
              </p>

              {/* Keyword Tags */}
              {newKeywordsList.length > 0 && (
                <div className="space-y-2">
                  <div className="flex flex-wrap gap-2 p-3 border rounded-lg bg-muted/30 max-h-32 overflow-y-auto">
                    {newKeywordsList.map((keyword, index) => (
                      <Badge
                        key={index}
                        variant="default"
                        className="gap-1 pr-1"
                      >
                        {keyword}
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="h-4 w-4 p-0 hover:bg-background/20"
                          onClick={() => handleRemoveKeywordFromExisting(keyword)}
                        >
                          <X className="h-3 w-3" />
                        </Button>
                      </Badge>
                    ))}
                  </div>
                  <div className="flex justify-start">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setNewKeywordsList([])}
                      className="h-8 text-xs"
                    >
                      Clear all
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddKeywordsDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleAddKeywordsToDomain} disabled={isAddingKeywords || newKeywordsList.length === 0}>
              {isAddingKeywords ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Adding...
                </>
              ) : (
                <>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Keywords
                </>
              )}
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
