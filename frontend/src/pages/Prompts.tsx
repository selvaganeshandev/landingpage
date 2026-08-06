import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Plus, TrendingUp, Eye, Edit, Sparkles, Loader2, Clock, CheckCircle, Download, Trash2, ArrowLeft } from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
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
import { PromptSourceChooser, type PromptSource } from "@/components/PromptSourceChooser";
import { SearchConsoleSeedPicker } from "@/components/SearchConsoleSeedPicker";
import { PromptUploadStep } from "@/components/PromptUploadStep";
import { PromptGenerationWizard } from "@/components/PromptGenerationWizard";
import { PromptReviewTable, GenerationProgress, type Candidate } from "@/components/PromptReviewTable";
import { useGenerationRun } from "@/hooks/useGenerationRun";
import { getActiveDomainIdNumber } from "@/utils/activeDomain";

const Prompts = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  // Which build-your-list panel the empty state is showing. "choose" is the
  // three cards; picking Upload swaps them for the upload panel in place.
  const [buildStep, setBuildStep] = useState<"choose" | "upload" | "wizard" | "gsc">("choose");
  const [isAccepting, setIsAccepting] = useState(false);
  // Lets a project that already has groups open the build panel — otherwise
  // the chooser and the review table are unreachable once prompts exist.
  const [forceBuildPanel, setForceBuildPanel] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [generateDialogOpen, setGenerateDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [groupToDelete, setGroupToDelete] = useState<any>(null);
  const [isDeleting, setIsDeleting] = useState(false);
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
  // Server-owned generation state, so it survives navigation and refreshes.
  const {
    run: genRun,
    start: startRun,
    accept: acceptRun,
    discard: discardRun,
    refresh: refreshRun,
  } = useGenerationRun(selectedDomain?.id);
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

  const handleDeleteGroup = (group: typeof promptGroups[0]) => {
    setGroupToDelete(group);
    setDeleteDialogOpen(true);
  };

  const confirmDeleteGroup = async () => {
    if (!groupToDelete) return;
    try {
      setIsDeleting(true);
      await apiClient.deletePromptGroup(groupToDelete.id);
      toast({
        title: "Prompt Group Deleted",
        description: `"${groupToDelete.group_id}" and its prompts have been deleted.`,
      });
      setDeleteDialogOpen(false);
      setGroupToDelete(null);
      // Reload the list from the start so counts/pagination stay correct
      setOffset(0);
      void loadPromptGroups(0, true);
    } catch (error: any) {
      toast({
        title: "Failed to delete",
        description: error?.message || String(error),
        variant: "destructive",
      });
    } finally {
      setIsDeleting(false);
    }
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
          {/* Only with groups to export — on an empty project the button can
              only ever produce an empty spreadsheet, which reads as a broken
              export rather than an empty one. */}
          {promptGroups.length > 0 && (
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
            className="border-border"
          >
            <Download className="h-4 w-4 mr-2" />
            {isExporting ? "Exporting..." : "Export"}
          </Button>
          )}
          {/* With groups already on the page the chooser is unreachable — it
              only renders in the empty state — so this is the way back into it.
              With no groups the chooser is already on screen, and the button
              stays the direct manual route rather than pointing at itself. */}
          {promptGroups.length > 0 ? (
            <Button
              onClick={() => {
                setBuildStep("choose");
                setForceBuildPanel(true);
              }}
              className="gradient-primary shadow-md shadow-primary/20"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Prompts
            </Button>
          ) : (
            <Button onClick={() => setAddDialogOpen(true)} className="gradient-primary shadow-md shadow-primary/20">
              <Plus className="h-4 w-4 mr-2" />
              Add Prompts Manually
            </Button>
          )}
        </div>
      </div>

      {/* Search and organize controls removed as per requirements */}

      {/* The chooser only renders in the empty state, so once a project has
          groups a live run would otherwise be invisible. This keeps it
          findable in both cases. */}
      {promptGroups.length > 0 && genRun && ["INIT", "PROC", "DONE"].includes(genRun.status) && (
        <Card className="p-4 mb-6 border-primary/30 bg-primary/5">
          <div className="flex flex-wrap items-center gap-3">
            <Sparkles className="h-4 w-4 text-primary shrink-0" />
            {genRun.status === "DONE" ? (
              <>
                <p className="text-sm flex-1">
                  <span className="font-medium">{genRun.candidate_count} prompts ready to review.</span>{" "}
                  <span className="text-muted-foreground">Nothing is tracked until you add them.</span>
                </p>
                <Button
                  size="sm"
                  className="gradient-primary"
                  onClick={() => setForceBuildPanel(true)}
                >
                  Review {genRun.candidate_count} prompts
                </Button>
              </>
            ) : (
              <p className="text-sm flex-1">
                <span className="font-medium">Generating prompts…</span>{" "}
                <span className="text-muted-foreground">
                  Step {genRun.stage_index || 1} of {genRun.stage_total} · {genRun.stage_label}
                </span>
              </p>
            )}
          </div>
        </Card>
      )}

      <div className="grid gap-6">
        {promptGroups.length > 0 && !forceBuildPanel ? (
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
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleDeleteGroup(group)}
                  className="border border-destructive/30 text-destructive hover:bg-destructive/10 hover:text-destructive ml-auto"
                >
                  <Trash2 className="h-4 w-4 mr-1" />
                  Delete
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
          <Card className="p-8 md:p-10">
            {/* Reached from the header button, so it needs a way back — without
                this the groups list is unreachable until a run completes.
                Leaving is safe at every step: the run lives on the server and
                the banner above returns the user to it. */}
            {forceBuildPanel && promptGroups.length > 0 && (
              <div className="mb-6">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setForceBuildPanel(false)}
                  className="text-muted-foreground hover:text-foreground -ml-2"
                >
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Back to prompt groups
                </Button>
              </div>
            )}

            {/* A live run outranks whatever step the user was on — it survives
                navigation, so the page must reflect it on arrival. */}
            {genRun && (genRun.status === "INIT" || genRun.status === "PROC") ? (
              <GenerationProgress
                stageLabel={genRun.stage_label}
                stageIndex={genRun.stage_index}
                stageTotal={genRun.stage_total}
                progress={genRun.progress}
              />
            ) : genRun && genRun.status === "DONE" && genRun.candidates ? (
              <PromptReviewTable
                candidates={genRun.candidates as Candidate[]}
                saving={isAccepting}
                onAccept={async (ids, edits) => {
                  try {
                    setIsAccepting(true);
                    const res: any = await acceptRun(ids, edits);
                    toast({
                      title: "Prompts added",
                      description: `${res?.prompts_created ?? ids.length} prompts in ${res?.groups_created ?? 0} groups. Tracking starts on the next run.`,
                    });
                    setBuildStep("choose");
                    setForceBuildPanel(false);
                    setOffset(0);
                    void loadPromptGroups(0, true);
                  } catch (e: any) {
                    toast({ title: "Could not add prompts", description: e?.message, variant: "destructive" });
                  } finally {
                    setIsAccepting(false);
                  }
                }}
                onDiscard={async () => {
                  await discardRun();
                  setBuildStep("choose");
                  setForceBuildPanel(false);
                }}
              />
            ) : genRun && genRun.status === "FAIL" ? (
              <div className="text-center py-14">
                <h3 className="font-semibold text-lg">Generation failed</h3>
                <p className="text-sm text-muted-foreground mt-1.5 max-w-md mx-auto">
                  {genRun.error || "Something went wrong while generating prompts."}
                </p>
                <Button
                  className="gradient-primary mt-5"
                  onClick={async () => {
                    await discardRun();
                    setBuildStep("wizard");
                  }}
                >
                  Try again
                </Button>
              </div>
            ) : buildStep === "choose" ? (
              <PromptSourceChooser
                onSelect={(source: PromptSource) => {
                  setBuildStep(
                    source === "upload" ? "upload" : source === "gsc" ? "gsc" : "wizard"
                  );
                }}
              />
            ) : buildStep === "gsc" ? (
              <SearchConsoleSeedPicker
                domainId={selectedDomain?.id}
                onBack={() => setBuildStep("choose")}
                onRunCreated={async () => {
                  // The run is created already DONE, so the existing active-run
                  // poll picks it up and renders the same review table the AI
                  // path uses.
                  await refreshRun();
                  setBuildStep("wizard");
                }}
              />
            ) : buildStep === "wizard" ? (
              <PromptGenerationWizard
                onBack={() => setBuildStep("choose")}
                onGenerate={async (config) => {
                  try {
                    await startRun(config);
                    toast({
                      title: "Generating prompts",
                      description: "This runs in the background — you can leave this page.",
                    });
                  } catch (e: any) {
                    toast({ title: "Could not start", description: e?.message, variant: "destructive" });
                  }
                }}
              />
            ) : (
              <div className="max-w-2xl mx-auto">
                <PromptUploadStep
                  onUpload={async (file) => {
                    const activeDomainId = selectedDomain?.id ?? getActiveDomainIdNumber(user);
                    if (!activeDomainId) throw new Error("Select a project first.");
                    const res: any = await apiClient.uploadPromptFile(activeDomainId, file);
                    // The upload returns a DONE run with candidates attached, so
                    // refreshing swaps this step for the same review table the
                    // AI path uses — no separate review screen to maintain.
                    await refreshRun();
                    toast({
                      title: "Prompts ready to review",
                      description: `${res?.candidate_count ?? 0} prompts grouped by theme. Nothing is tracked until you add them.`,
                    });
                  }}
                />
                <div className="flex justify-start mt-6">
                  <Button
                    variant="outline"
                    onClick={() => setBuildStep("choose")}
                    className="border-border"
                  >
                    <ArrowLeft className="h-4 w-4 mr-2" />
                    Back
                  </Button>
                </div>
              </div>
            )}
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
      <AlertDialog open={deleteDialogOpen} onOpenChange={(open) => { if (!isDeleting) setDeleteDialogOpen(open); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Prompt Group</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete{groupToDelete?.group_id ? ` "${groupToDelete.group_id}"` : " this prompt group"}?
              This will permanently remove the group, all its prompt variants, and their tracked analytics. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => { e.preventDefault(); void confirmDeleteGroup(); }}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? (<><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Deleting...</>) : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default Prompts;
