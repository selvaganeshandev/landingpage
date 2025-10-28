import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { 
  Users, 
  UserPlus, 
  Shield, 
  Edit, 
  Trash2, 
  Loader2,
  Search,
  Globe,
  X
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/services/api";

interface DomainAccess {
  id: number;
  user: {
    id: number;
    email: string;
    first_name: string;
    last_name: string;
  };
  access_level: 'viewer' | 'editor' | 'admin';
  granted_by: {
    id: number;
    email: string;
  };
  created_at: string;
}

interface AvailableUser {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: 'admin' | 'user';
}

interface ProjectAccessManagerProps {
  userId: number;
  userName: string;
  userEmail: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAccessUpdated?: () => void;
}

export const ProjectAccessManager = ({ 
  userId, 
  userName, 
  userEmail, 
  open, 
  onOpenChange,
  onAccessUpdated
}: ProjectAccessManagerProps) => {
  const { toast } = useToast();
  const [domains, setDomains] = useState<any[]>([]);
  const [userAccess, setUserAccess] = useState<{[domainId: number]: DomainAccess}>({});
  const [isLoading, setIsLoading] = useState(false);
  const [isUpdating, setIsUpdating] = useState<number | null>(null);

  useEffect(() => {
    if (open) {
      loadData();
    }
  }, [open, userId]);

  const loadData = async () => {
    try {
      setIsLoading(true);
      
      // Load all domains
      const domainsResponse = await apiClient.getDomains();
      setDomains(domainsResponse.domains);
      
      // Load user's access for each domain
      const accessMap: {[domainId: number]: DomainAccess} = {};
      for (const domain of domainsResponse.domains) {
        try {
          const accessResponse = await apiClient.getDomainAccess(domain.id);
          const userAccessItem = accessResponse.access_list.find(
            access => access.user.id === userId
          );
          if (userAccessItem) {
            accessMap[domain.id] = userAccessItem;
          }
        } catch (error) {
          // User doesn't have access to this domain
          console.log(`User ${userId} doesn't have access to domain ${domain.id}`);
        }
      }
      setUserAccess(accessMap);
      
    } catch (error: any) {
      toast({
        title: "Error loading data",
        description: error.message || "Failed to load project access data",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleAccess = async (domainId: number, enabled: boolean) => {
    try {
      setIsUpdating(domainId);
      
      if (enabled) {
        // Grant access with default 'viewer' level
        await apiClient.grantDomainAccess(domainId, {
          user_id: userId,
          access_level: 'viewer'
        });
        
        // Update local state
        const domain = domains.find(d => d.id === domainId);
        if (domain) {
          setUserAccess(prev => ({
            ...prev,
            [domainId]: {
              id: Date.now(), // Temporary ID
              user: { id: userId, email: userEmail, first_name: userName.split(' ')[0], last_name: userName.split(' ')[1] || '' },
              access_level: 'viewer',
              granted_by: { id: 0, email: '' },
              created_at: new Date().toISOString()
            }
          }));
        }
        
        toast({
          title: "Access granted",
          description: `${userName} now has viewer access to ${domain?.name}`,
        });
      } else {
        // Revoke access
        await apiClient.revokeDomainAccess(domainId, userId);
        
        // Update local state
        setUserAccess(prev => {
          const newAccess = { ...prev };
          delete newAccess[domainId];
          return newAccess;
        });
        
        const domain = domains.find(d => d.id === domainId);
        toast({
          title: "Access revoked",
          description: `${userName}'s access to ${domain?.name} has been revoked`,
        });
      }
      
      if (onAccessUpdated) {
        onAccessUpdated();
      }
      
    } catch (error: any) {
      toast({
        title: "Error updating access",
        description: error.message || "Failed to update project access",
        variant: "destructive",
      });
    } finally {
      setIsUpdating(null);
    }
  };

  const handleAccessLevelChange = async (domainId: number, newLevel: 'viewer' | 'editor' | 'admin') => {
    try {
      setIsUpdating(domainId);
      
      await apiClient.updateDomainAccess(domainId, userId, {
        access_level: newLevel
      });
      
      // Update local state
      setUserAccess(prev => ({
        ...prev,
        [domainId]: {
          ...prev[domainId],
          access_level: newLevel
        }
      }));
      
      const domain = domains.find(d => d.id === domainId);
      toast({
        title: "Access level updated",
        description: `${userName}'s access to ${domain?.name} changed to ${newLevel}`,
      });
      
      if (onAccessUpdated) {
        onAccessUpdated();
      }
      
    } catch (error: any) {
      toast({
        title: "Error updating access level",
        description: error.message || "Failed to update access level",
        variant: "destructive",
      });
    } finally {
      setIsUpdating(null);
    }
  };

  const getAccessLevelColor = (level: string) => {
    switch (level) {
      case 'admin': return 'bg-red-100 text-red-800 border-red-200';
      case 'editor': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'viewer': return 'bg-green-100 text-green-800 border-green-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            Project Access Management
          </DialogTitle>
          <DialogDescription>
            Manage project access for <strong>{userName}</strong> ({userEmail})
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          ) : (
            <div className="space-y-4">
              {domains.map((domain) => {
                const hasAccess = userAccess[domain.id];
                const isUpdatingThis = isUpdating === domain.id;
                
                return (
                  <div key={domain.id} className="border rounded-lg p-4 space-y-3">
                    {/* Project Name and Toggle */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Globe className="h-5 w-5 text-muted-foreground" />
                        <div>
                          <h3 className="font-semibold">{domain.name}</h3>
                          <p className="text-sm text-muted-foreground">{domain.url}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Switch
                          checked={!!hasAccess}
                          onCheckedChange={(enabled) => handleToggleAccess(domain.id, enabled)}
                          disabled={isUpdatingThis}
                        />
                        {isUpdatingThis && (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        )}
                      </div>
                    </div>

                    {/* Access Level Dropdown */}
                    {hasAccess && (
                      <div className="flex items-center gap-3 pl-8">
                        <Label className="text-sm font-medium">Access Level:</Label>
                        <Select
                          value={hasAccess.access_level}
                          onValueChange={(value: 'viewer' | 'editor' | 'admin') => 
                            handleAccessLevelChange(domain.id, value)
                          }
                          disabled={isUpdatingThis}
                        >
                          <SelectTrigger className="w-32">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="viewer">Viewer</SelectItem>
                            <SelectItem value="editor">Editor</SelectItem>
                            <SelectItem value="admin">Admin</SelectItem>
                          </SelectContent>
                        </Select>
                        <Badge className={getAccessLevelColor(hasAccess.access_level)}>
                          {hasAccess.access_level}
                        </Badge>
                      </div>
                    )}
                  </div>
                );
              })}
              
              {domains.length === 0 && (
                <div className="text-center py-8 text-muted-foreground">
                  No projects available for access management.
                </div>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

