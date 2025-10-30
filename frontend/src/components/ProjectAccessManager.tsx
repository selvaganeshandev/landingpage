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
      
      // Load all domains (admin management scope)
      const domainsResponse = await apiClient.getDomains({ manage: true });
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
        // Grant access
        await apiClient.grantDomainAccess(domainId, {
          user_id: userId,
        });
        
        // Optimistically mark as having access
        setUserAccess(prev => ({
          ...prev,
          [domainId]: prev[domainId] || {
            id: Date.now(),
            user: { id: userId, email: userEmail, first_name: userName.split(' ')[0], last_name: userName.split(' ')[1] || '' },
            granted_by: { id: 0, email: '' },
            created_at: new Date().toISOString()
          }
        }));

        // Refresh access map for this domain from server to ensure accuracy
        try {
          const refreshed = await apiClient.getDomainAccess(domainId);
          const userAccessItem = refreshed.access_list.find(a => a.user.id === userId);
          if (userAccessItem) {
            setUserAccess(prev => ({ ...prev, [domainId]: userAccessItem }));
          }
          const domainObj = domains.find(d => d.id === domainId);
          const domainName = userAccessItem?.domain_name || domainObj?.name || String(domainId);
          toast({
            title: "Access granted",
            description: `${userName} now has access to ${domainName}`,
          });
        } catch (_) {
          const domainObj = domains.find(d => d.id === domainId);
          const domainName = domainObj?.name || String(domainId);
          toast({
            title: "Access granted",
            description: `${userName} now has access to ${domainName}`,
          });
        }
        
      } else {
        // Revoke access
        await apiClient.revokeDomainAccess(domainId, userId);
        
        // Refresh access map for this domain from server to ensure accuracy
        try {
          const refreshed = await apiClient.getDomainAccess(domainId);
          const userAccessItem = refreshed.access_list.find(a => a.user.id === userId);
          setUserAccess(prev => {
            const copy = { ...prev };
            if (userAccessItem) {
              copy[domainId] = userAccessItem;
            } else {
              delete copy[domainId];
            }
            return copy;
          });
        } catch (_) {
          // Optimistically remove access on failure to refresh
          setUserAccess(prev => {
            const copy = { ...prev };
            delete copy[domainId];
            return copy;
          });
        }
        
        const domainObj = domains.find(d => d.id === domainId);
        const domainName = domainObj?.name || String(domainId);
        toast({
          title: "Access revoked",
          description: `${userName}'s access to ${domainName} has been revoked`,
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

  // Access levels removed; toggles grant/revoke only

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

                    {/* Access levels UI removed */}
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

