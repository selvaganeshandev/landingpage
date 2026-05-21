import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Plus, FolderOpen, TrendingUp, Eye, Edit, Sparkles, Loader2, Clock, CheckCircle, Download } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import {
  Breadcrumb,
  BreadcrumbList,
  BreadcrumbItem,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { apiClient } from "@/services/api";
import { useDomainStore } from "@/stores/domainStore";
import { useAuth } from "@/contexts/AuthContext";
import { AddPromptGroupDialog } from "@/components/AddPromptGroupDialog";
import { EditPromptGroupDialog } from "@/components/EditPromptGroupDialog";
import { GenerateVariantsDialog } from "@/components/GenerateVariantsDialog";
import { getActiveDomainIdNumber } from "@/utils/activeDomain";

const Prompts = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [generateDialogOpen, setGenerateDialogOpen] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState<any>(null);
  const [promptGroups, setPromptGroups] = useState<any[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [offset, setOffset] = useState(0);
  const limit = 20;
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [isInitialLoad, setIsInitialLoad] = useState(true);
  const [isExporting, setIsExporting] = useState(false);

  const { selectedDomain, setDomainSwitching } = useDomainStore();
  const { user } = useAuth();

  useEffect(() => {
    setPromptGroups([]);
    setOffset(0);
    setTotalCount(0);
    setIsInitialLoad(true);
    setDomainSwitching(true); // Show page loader
    void loadPromptGroups(0, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDomain?.id]);

  const loadPromptGroups = async (startOffset: number = offset, replace: boolean = false) => {
    try {
      // Only show full page loader on initial load, not on "Load More"
      if (replace) {
        setIsLoading(true);
      }
      // Use unified helper to get active domain ID (from localStorage, synced with server)
      const activeDomainId = selectedDomain?.id ?? getActiveDomainIdNumber(user);
      if (!activeDomainId) {
        if (replace) {
          setIsLoading(false);
        }
        if (isInitialLoad) {
          setDomainSwitching(false);
          setIsInitialLoad(false);
        }
        toast({ title: 'No domain selected', description: 'Please select a domain to view prompt groups.', variant: 'destructive' });
        return;
      }
      const response = await apiClient.getPromptGroups({
        domain_id: activeDomainId,
        limit,
        offset: startOffset,
      });
      setTotalCount(response.total_count || 0);
      if (replace) {
        setPromptGroups(response.groups || []);
      } else {
        // Use functional update to ensure we're using the latest state
        setPromptGroups(prevGroups => [...prevGroups, ...(response.groups || [])]);
      }
    } catch (error: any) {
      const errorMessage = error.message || "Failed to load prompt groups";
      // Only show error for actual errors, not empty data
      const isNetworkError = errorMessage.includes('fetch') || errorMessage.includes('network') || errorMessage.includes('Network');
      const isServerError = errorMessage.includes('500') || errorMessage.includes('503') || errorMessage.includes('502');

      // Only show error toast for actual errors, not for empty data (404 is normal for empty data)
      if (isNetworkError || isServerError || (!errorMessage.includes('404') && !errorMessage.includes('Not Found'))) {
        toast({
          title: "Error loading prompt groups",
          description: errorMessage,
          variant: "destructive",
        });
      }
      // For empty data, just set empty array without showing error
      if (replace) {
        setPromptGroups([]);
      }
    } finally {
      if (replace) {
        setIsLoading(false);
      }
      if (isInitialLoad) {
        setDomainSwitching(false);
        setIsInitialLoad(false);
      }
    }
  };

  const canLoadMore = promptGroups.length < totalCount;
  const handleLoadMore = async () => {
    setIsLoadingMore(true);
    try {
      // Calculate next offset using current offset value
      const nextOffset = offset + limit;
      setOffset(nextOffset);
      // Load more with the new offset
      await loadPromptGroups(nextOffset, false);
    } finally {
      setIsLoadingMore(false);
    }
  };

  const handleViewDetails = (groupId: number) => {
    navigate(`/prompts/${groupId}`);
  };

  const handleEditGroup = (group: typeof promptGroups[0]) => {
    setSelectedGroup(group);
    setEditDialogOpen(true);
  };

  const handleGenerateVariants = (group: typeof promptGroups[0]) => {
    setSelectedGroup(group);
    setGenerateDialogOpen(true);
  };

  const getStatusBadge = (trackStatus: string) => {
    const status = trackStatus?.toUpperCase();
    
    // COMP and FAIL show "Completed" with success/green color (like sentiment positive)
    if (status === 'COMP' || status === 'FAIL') {
      return (
        <Badge variant="secondary" className="bg-success/10 text-success border-success/20 hover:bg-success/10 hover:text-success">
          <CheckCircle className="h-3 w-3 mr-1" />
          Completed
        </Badge>
      );
    }
    
    // All other statuses (PROC, SCHD, INIT, etc.) show "Processing" with no color (muted)
    return (
      <Badge variant="secondary" className="bg-muted text-muted-foreground hover:bg-muted hover:text-muted-foreground">
        <Clock className="h-3 w-3 mr-1" />
        Processing
      </Badge>
    );
  };

  return (
    <div className="p-8 space-y-8 bg-background animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">
            Prompt Monitoring
          </h1>
          <p className="text-muted-foreground mt-2">
            Track and group prompts to monitor brand visibility
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            onClick={async () => {
              const activeDomainId = selectedDomain?.id ?? getActiveDomainIdNumber(user);
              if (!activeDomainId) {
                toast({ title: "No domain selected", description: "Please select a domain before exporting.", variant: "destructive" });
                return;
              }
              try {
                setIsExporting(true);
                toast({ title: "Exporting Report", description: "Your AI Prompt Data export is being generated..." });
                const safeName = (selectedDomain?.name || "domain").replace(/\s+/g, "_");
                const timestamp = new Date().toISOString().slice(0, 10).replace(/-/g, "");
                await apiClient.exportPromptsReport({
                  domain_id: activeDomainId,
                  filename: `${safeName}_AI_Prompt_Data_Export_${timestamp}.xlsx`,
                });
              } catch (e: any) {
                toast({ title: "Export Failed", description: e?.message || String(e), variant: "destructive" });
              } finally {
                setIsExporting(false);
              }
            }}
            disabled={isExporting}
          >
            <Download className="h-4 w-4 mr-2" />
            {isExporting ? "Exporting..." : "Export"}
          </Button>
          <Button onClick={() => setAddDialogOpen(true)} className="gradient-primary shadow-md shadow-primary/20">
            <Plus className="h-4 w-4 mr-2" />
            Add Prompt Group
          </Button>
        </div>
      </div>

      {/* Search and organize controls removed as per requirements */}

      <div className="grid gap-6">
        {promptGroups.length > 0 ? (
          <>
          {promptGroups.map((group) => (
          <Card key={group.id} className="p-6 transition-all duration-300 border border-border hover:border-primary backdrop-blur-sm bg-card/80">
            <div className="space-y-5">
              <div className="flex items-start justify-between">
                <div className="space-y-2 flex-1">
                  <div className="flex items-center gap-3">
                    <h3 className="text-xl font-semibold font-inter">{group.group_id}</h3>
                    {getStatusBadge(group.track_status)}
                  </div>
                  {group.primary_prompt && (
                    <p className="text-sm text-muted-foreground font-mono bg-gradient-to-br from-muted/30 to-muted/50 px-3 py-2 rounded-xl inline-block border border-border">
                      {group.primary_prompt}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-6">
                  <div className="text-right">
                    <p className="text-3xl font-bold font-inter">{group.total_mentions || 0}</p>
                    <p className="text-xs text-muted-foreground uppercase tracking-wider">mentions</p>
                  </div>
                  {group.visibility_growth !== undefined && group.visibility_growth !== null && (
                    <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-success/10 border border-success/20">
                      <TrendingUp className="h-4 w-4 text-success" />
                      <span className="text-sm font-semibold text-success">
                        {group.visibility_growth > 0 ? '+' : ''}{group.visibility_growth}%
                      </span>
                    </div>
                  )}
                </div>
              </div>

              <div className="space-y-3">
                <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
                  Prompt Variants ({group.secondary_prompts?.length || 0})
                </p>
                <div className="flex flex-wrap gap-2">
                  {(group.secondary_prompts || []).slice(0, 5).map((variant: string, idx: number) => (
                    <Badge
                      key={idx}
                      variant="secondary"
                      className="font-mono text-xs px-3 py-1.5"
                    >
                      {variant}
                    </Badge>
                  ))}
                  {(group.secondary_prompts?.length || 0) > 5 && (
                    <Badge
                      variant="outline"
                      className="font-mono text-xs px-3 py-1.5 cursor-pointer hover:bg-muted"
                      onClick={() => handleViewDetails(group.id)}
                    >
                      +{group.secondary_prompts.length - 5} more
                    </Badge>
                  )}
                </div>
              </div>

              <div className="flex gap-2 pt-3 border-t">
                <Button variant="outline" size="sm" onClick={() => handleViewDetails(group.id)} className="border border-border">
                  <Eye className="h-4 w-4 mr-1" />
                  View Details
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleEditGroup(group)} className="border border-border">
                  <Edit className="h-4 w-4 mr-1" />
                  Edit Group
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleGenerateVariants(group)} className="border border-border">
                  <Sparkles className="h-4 w-4 mr-1" />
                  Generate Variants
                </Button>
              </div>
            </div>
          </Card>
        ))}
        {canLoadMore && (
          <div className="flex justify-center">
            <Button type="button" variant="outline" onClick={handleLoadMore} disabled={isLoadingMore} className="border border-border">
              {isLoadingMore ? (<><Loader2 className="h-4 w-4 mr-2 animate-spin"/> Loading...</>) : 'Load More'}
            </Button>
          </div>
        )}
        </>
        ) : (
          <Card className="p-12 text-center">
            <FolderOpen className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Prompt Groups Found</h3>
            <p className="text-muted-foreground mb-4">
              Create your first prompt group to get started.
            </p>
            <Button onClick={() => setAddDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add Prompt Group
            </Button>
          </Card>
        )}
      </div>

      {/* Dialogs */}
      <AddPromptGroupDialog 
        open={addDialogOpen} 
        onOpenChange={setAddDialogOpen}
        onAdd={(group) => {
          // Reload the list to get fresh data with variants
          setOffset(0);
          void loadPromptGroups(0, true);
        }}
      />
      <EditPromptGroupDialog 
        open={editDialogOpen} 
        onOpenChange={setEditDialogOpen}
        promptGroup={selectedGroup}
        onEdit={(group) => {
          // Reload the list to get fresh data with variants
          setOffset(0);
          void loadPromptGroups(0, true);
        }}
      />
      <GenerateVariantsDialog
        open={generateDialogOpen}
        onOpenChange={setGenerateDialogOpen}
        promptGroup={selectedGroup}
        onAdd={async (variants) => {
          // Add variants to the selected group
          if (selectedGroup) {
            try {
              const detail = await apiClient.getPromptGroupDetail(selectedGroup.id);
              const currentVariants = detail.group.secondary_prompts || [];
              const updatedVariants = [...currentVariants, ...variants];
              
              await apiClient.updatePromptGroup(selectedGroup.id, {
                group_id: selectedGroup.group_id,
                domain_id: selectedGroup.domain_id,
                primary_prompt: detail.group.primary_prompt,
                secondary_prompts: updatedVariants,
              });

              // Reload the list to show updated variants
              setOffset(0);
              void loadPromptGroups(0, true);
            } catch (error: any) {
              toast({
                title: "Error",
                description: error.message || "Failed to add variants",
                variant: "destructive",
              });
            }
          }
        }}
      />
    </div>
  );
};

export default Prompts;
