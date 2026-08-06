import { useState, useEffect, useCallback } from "react";
import { Check, Globe, Loader2, ChevronsUpDown, AlertCircle, Search, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { AddDomainDialog } from "@/components/AddDomainDialog";
import { cn } from "@/lib/utils";
import { useDomainStore } from "@/stores/domainStore";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/hooks/use-toast";
import { getFaviconUrl, handleFaviconError } from "@/utils/faviconHelper";

/** Bare host for the dropdown subtext: no scheme, no "www.", no trailing slash. */
const hostLabel = (url?: string | null): string => {
  if (!url) return "";
  return String(url)
    .replace(/^https?:\/\//i, "")
    .replace(/^www\./i, "")
    .replace(/\/+$/, "");
};

export const DomainSelector = () => {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [addDomainOpen, setAddDomainOpen] = useState(false);
  const { toast } = useToast();
  
  const {
    domains,
    selectedDomain,
    isLoading,
    error,
    loadDomains,
    setSelectedDomain,
    setDomainSwitching
  } = useDomainStore();
  const { user } = useAuth();

  // Clear stale domains if they don't belong to current user's organization
  useEffect(() => {
    if (user && domains.length > 0) {
      const hasMismatch = domains.some(d => d.organisation !== user.organisation);
      if (hasMismatch) {
        const { clearDomainStore } = useDomainStore.getState();
        clearDomainStore();
        localStorage.removeItem('domain-store');
      }
    }
  }, [user, domains]);

  // Load domains on component mount
  useEffect(() => {
    loadDomains();
  }, [loadDomains]);

  // Poll for domain status updates every 10 seconds if there are processing domains
  useEffect(() => {
    const hasProcessingDomains = domains.some(d =>
      d.processing_status && ['INIT', 'SCHD', 'PROC'].includes(d.processing_status)
    );

    if (!hasProcessingDomains) return;

    const interval = setInterval(() => {
      loadDomains();
    }, 10000); // Poll every 10 seconds

    return () => clearInterval(interval);
  }, [domains, loadDomains]);

  // If currently selected domain is processing, switch to first completed domain
  useEffect(() => {
    if (!selectedDomain || !user) return;

    const isCurrentDomainProcessing = selectedDomain.processing_status &&
      ['INIT', 'SCHD', 'PROC'].includes(selectedDomain.processing_status);

    if (isCurrentDomainProcessing) {
      // Find first completed domain
      const firstCompletedDomain = domains.find(d =>
        d.id !== selectedDomain.id && (!d.processing_status || d.processing_status === 'COMP')
      );

      if (firstCompletedDomain) {
        // Switch to completed domain
        (async () => {
          const { updateActiveDomain } = await import('@/utils/activeDomain');
          await updateActiveDomain(user.id, firstCompletedDomain.id, firstCompletedDomain);
          setSelectedDomain(firstCompletedDomain);
        })();
      }
    }
  }, [selectedDomain, domains, user, setSelectedDomain]);

  // Sync selected domain to server after domains load (only if not already synced)
  useEffect(() => {
    if (!user || !selectedDomain || domains.length === 0) return;

    const syncToServer = async () => {
      // Load from server to check if it's in sync
      const { loadActiveDomainFromServer, updateActiveDomain } = await import('@/utils/activeDomain');
      const serverActiveDomainId = await loadActiveDomainFromServer(user.id);

      // If server value doesn't match current selection, update server
      if (serverActiveDomainId !== String(selectedDomain.id)) {
        await updateActiveDomain(user.id, selectedDomain.id, selectedDomain);
      }
    };

    void syncToServer();
  }, [domains, user, selectedDomain]);

  // Clients with exactly one assigned domain: auto-select it so their dashboards
  // load without ever touching a switcher.
  useEffect(() => {
    if (user?.role === 'client' && domains.length === 1 && !selectedDomain) {
      setSelectedDomain(domains[0]);
    }
  }, [user, domains, selectedDomain, setSelectedDomain]);

  // Show error if domain loading failed
  useEffect(() => {
    if (error) {
      toast({
        title: "Error loading domains",
        description: error,
        variant: "destructive",
      });
    }
  }, [error, toast]);

  useEffect(() => {
    if (!open) setQuery("");
  }, [open]);

  const handleDomainSelect = async (domainId: number) => {
    const domain = domains.find(d => d.id === domainId);
    if (domain) {
      // Check if domain is still processing or failed - don't allow selection
      if (domain.processing_status && ['INIT', 'SCHD', 'PROC', 'FAIL'].includes(domain.processing_status)) {

        const isFailed = domain.processing_status === 'FAIL';
        toast({
          title: isFailed ? "Domain Processing Failed" : "Domain Processing",
          description: isFailed
            ? `Processing failed: ${domain.track_message || 'Unknown error'}. Please try re-adding this domain.`
            : "This domain is still being processed. Please wait until processing completes.",
          variant: isFailed ? "destructive" : "default",
        });
        return;
      }

      // Start domain switching - show page loader
      setDomainSwitching(true);
      setOpen(false);

      if (user) {
        // Update both Zustand store and server/localStorage in one call
        // This ensures both systems stay in sync
        const { updateActiveDomain } = await import('@/utils/activeDomain');
        const success = await updateActiveDomain(user.id, domainId, domain);
        if (success) {
          // Only update Zustand store if server sync succeeded
          // (updateActiveDomain already updates it, but this ensures it's set)
          setSelectedDomain(domain);
        } else {
          // If server sync failed, revert to server value
          const { loadActiveDomainFromServer } = await import('@/utils/activeDomain');
          const serverActiveDomainId = await loadActiveDomainFromServer(user.id);
          if (serverActiveDomainId) {
            const serverDomainId = parseInt(serverActiveDomainId, 10);
            const serverDomain = domains.find(d => d.id === serverDomainId);
            if (serverDomain) {
              setSelectedDomain(serverDomain);
            }
          }
        }
      } else {
        // If no user, just update Zustand store (shouldn't happen in normal flow)
        setSelectedDomain(domain);
      }

      // Hide page loader after data has had time to load (1 second)
      setTimeout(() => {
        setDomainSwitching(false);
      }, 1000);
    }
  };

  // The same wizard the Domains tab opens — switch to whatever it creates so
  // the user lands on the brand they just added. The wizard has already
  // refreshed the domain store by the time this runs.
  const handleDomainAdded = async (domain: any) => {
    if (!domain) return;
    if (user) {
      const { updateActiveDomain } = await import('@/utils/activeDomain');
      await updateActiveDomain(user.id, domain.id, domain);
    }
    setSelectedDomain(domain);
  };

  const canAddDomain = user?.role === 'admin' || user?.role === 'super_admin';

  if (isLoading && domains.length === 0) {
    return (
      <Button
        variant="outline"
        className="w-full justify-start"
        disabled
      >
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        <span className="text-left flex-1">Loading domains...</span>
      </Button>
    );
  }

  if (domains.length === 0) {
    return (
      <Button
        variant="outline"
        className="w-full justify-start"
        disabled
      >
        <Globe className="mr-2 h-4 w-4 flex-shrink-0" />
        <span className="text-left flex-1">No domain added</span>
      </Button>
    );
  }

  // Clients with a single domain get a static label instead of a switcher —
  // there is nothing to switch to.
  if (user?.role === 'client' && domains.length === 1) {
    const only = domains[0];
    return (
      <Button variant="outline" className="w-full justify-start" disabled>
        <Globe className="mr-2 h-4 w-4 flex-shrink-0" />
        <span className="text-left flex-1 truncate">{only.name}</span>
      </Button>
    );
  }

  const selectedFaviconUrl = selectedDomain ? getFaviconUrl(selectedDomain.url, 32) : null;

  const filtered = domains.filter((d) => {
    const q = query.trim().toLowerCase();
    if (!q) return true;
    return (d.name || "").toLowerCase().includes(q)
      || hostLabel(d.url).toLowerCase().includes(q);
  });

  return (
    <>
      {/* Trigger. The stacked chevrons read as "switch between", which is what
          this does — a single caret implies a dropdown will open below it. */}
      <Button
        variant="outline"
        onClick={() => setOpen(true)}
        aria-haspopup="dialog"
        className="w-full justify-start gap-2 h-11"
      >
        {selectedFaviconUrl ? (
          <img
            src={selectedFaviconUrl}
            alt=""
            className="h-5 w-5 flex-shrink-0 rounded"
            onError={(e) => handleFaviconError(e, selectedDomain?.url || '', selectedDomain?.name, 32)}
          />
        ) : null}
        <Globe className={cn("h-5 w-5 flex-shrink-0", selectedFaviconUrl && "hidden")} />
        <span className="text-left flex-1 truncate font-medium">
          {selectedDomain ? selectedDomain.name : "Select project"}
        </span>
        <ChevronsUpDown className="h-4 w-4 flex-shrink-0 opacity-60" />
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-[760px]">
          <DialogHeader>
            <DialogTitle>Switch project</DialogTitle>
          </DialogHeader>

          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search projects"
              className="pl-9"
              autoFocus
            />
          </div>

          <div className="max-h-[55vh] overflow-y-auto -mx-1 px-1">
            {filtered.length === 0 ? (
              <p className="py-10 text-center text-sm text-muted-foreground">
                No projects match that search
              </p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {filtered.map((domain) => {
                  const faviconUrl = getFaviconUrl(domain.url, 32);
                  const isProcessing = domain.processing_status
                    && ['INIT', 'SCHD', 'PROC'].includes(domain.processing_status);
                  const isFailed = domain.processing_status === 'FAIL';
                  const isDisabled = isProcessing || isFailed;
                  const isActive = selectedDomain?.id === domain.id;
                  const processingLabel = domain.processing_status === 'INIT' ? 'Initializing...' :
                                          domain.processing_status === 'SCHD' ? 'Scheduled...' :
                                          domain.processing_status === 'PROC' ? 'Processing...' : 'Processing...';

                  return (
                    <button
                      key={domain.id}
                      type="button"
                      disabled={isDisabled}
                      onClick={() => handleDomainSelect(domain.id)}
                      className={cn(
                        "flex items-center gap-3 rounded-lg border p-3 text-left transition-colors",
                        isActive
                          ? "border-primary/30 bg-primary/5"
                          : "border-border hover:border-primary/40 hover:bg-accent/50",
                        isDisabled && "opacity-60 cursor-not-allowed hover:border-border hover:bg-transparent",
                      )}
                    >
                      <div className="h-10 w-10 flex-shrink-0 rounded-md border border-border bg-muted flex items-center justify-center overflow-hidden">
                        {faviconUrl ? (
                          <img
                            src={faviconUrl}
                            alt=""
                            className="h-6 w-6 object-contain"
                            onError={(e) => handleFaviconError(e, domain.url, domain.name, 32)}
                          />
                        ) : (
                          <Globe className="h-5 w-5 text-muted-foreground" />
                        )}
                      </div>

                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-semibold">{domain.name}</p>
                        {isProcessing ? (
                          <span className="text-xs text-orange-500 flex items-center gap-1">
                            <Loader2 className="h-3 w-3 animate-spin" />
                            {processingLabel}
                          </span>
                        ) : isFailed ? (
                          <span className="text-xs text-red-500 flex items-center gap-1">
                            <AlertCircle className="h-3 w-3" />
                            Failed
                          </span>
                        ) : (
                          // The host, not a mention count: `total_mentions` is a
                          // denormalized column that drifts, and the host is what
                          // actually tells two similarly named projects apart.
                          <p className="truncate text-xs text-muted-foreground">
                            {hostLabel(domain.url) || " "}
                          </p>
                        )}
                      </div>

                      {isActive && <Check className="h-4 w-4 flex-shrink-0 text-primary" />}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {canAddDomain && (
            <div className="flex justify-end pt-2">
              <Button
                onClick={() => {
                  setOpen(false);
                  setAddDomainOpen(true);
                }}
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Domain
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <AddDomainDialog
        open={addDomainOpen}
        onOpenChange={setAddDomainOpen}
        onDomainAdded={handleDomainAdded}
      />
    </>
  );
};
