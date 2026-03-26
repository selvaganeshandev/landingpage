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
  const [searchQuery, setSearchQuery] = useState('');
  const [visibleCount, setVisibleCount] = useState(10);
  const PAGE_SIZE = 10;

  useEffect(() => {
    if (open) {
      setSearchQuery('');
      setVisibleCount(PAGE_SIZE);
      loadData();
    }
  }, [open, userId]);

  const loadData = async () => {
    try {
      setIsLoading(true);

      // Load domains and user access in parallel (single call each)
      const [domainsResponse, accessResponse] = await Promise.all([
        apiClient.getDomains({ manage: true, fields: 'minimal' }),
        apiClient.getUserDomainAccess(userId),
      ]);
      setDomains(domainsResponse.domains);
      setUserAccess(accessResponse.access_map || {});

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

        <div className="space-y-4 py-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          ) : (
            <>
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search domains..."
                  value={searchQuery}
                  onChange={(e) => { setSearchQuery(e.target.value); setVisibleCount(PAGE_SIZE); }}
                  className="pl-9"
                />
              </div>

              {/* Domain count */}
              {(() => {
                const query = searchQuery.toLowerCase();
                // Sort: domains with access first, then alphabetical
                const sorted = [...domains].sort((a, b) => {
                  const aHas = userAccess[a.id] ? 1 : 0;
                  const bHas = userAccess[b.id] ? 1 : 0;
                  if (aHas !== bHas) return bHas - aHas;
                  return (a.name || '').localeCompare(b.name || '');
                });
                const filtered = query
                  ? sorted.filter(d => d.name?.toLowerCase().includes(query) || d.url?.toLowerCase().includes(query))
                  : sorted;
                const visible = filtered.slice(0, visibleCount);
                const hasMore = visibleCount < filtered.length;

                return (
                  <div className="space-y-3">
                    <p className="text-xs text-muted-foreground">
                      Showing {visible.length} of {filtered.length} domains
                      {Object.keys(userAccess).length > 0 && ` (${Object.keys(userAccess).length} with access)`}
                    </p>

                    {visible.map((domain) => {
                      const hasAccess = userAccess[domain.id];
                      const isUpdatingThis = isUpdating === domain.id;

                      return (
                        <div key={domain.id} className="border rounded-lg p-3">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3 min-w-0">
                              <Globe className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                              <div className="min-w-0">
                                <h3 className="font-medium text-sm truncate">{domain.name}</h3>
                                <p className="text-xs text-muted-foreground truncate">{domain.url}</p>
                              </div>
                            </div>
                            <div className="flex items-center gap-2 flex-shrink-0">
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
                        </div>
                      );
                    })}

                    {hasMore && (
                      <Button
                        variant="outline"
                        className="w-full"
                        onClick={() => setVisibleCount(prev => prev + PAGE_SIZE)}
                      >
                        Load More ({filtered.length - visibleCount} remaining)
                      </Button>
                    )}

                    {filtered.length === 0 && (
                      <div className="text-center py-6 text-muted-foreground text-sm">
                        {searchQuery ? 'No domains match your search.' : 'No projects available.'}
                      </div>
                    )}
                  </div>
                );
              })()}
            </>
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

