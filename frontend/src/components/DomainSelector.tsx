import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Check, Globe, Loader2, ChevronsUpDown, AlertCircle, Search, Plus, Settings } from "lucide-react";
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
import { MODULES } from "@/types/auth";
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
  const { user, checkPermission } = useAuth();
  const navigate = useNavigate();

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
      // A failed domain has no data and never will, so selecting it is still
      // blocked. Domains that are merely processing ARE selectable: analysis
      // runs in the background and results arrive progressively, so the pages
      // are worth opening — a ProcessingBanner explains what is still running.
      if (domain.processing_status === 'FAIL') {
        toast({
          title: "Domain Processing Failed",
          description: `Processing failed: ${domain.track_message || 'Unknown error'}. Please try re-adding this domain.`,
          variant: "destructive",
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

  const canAddDomain = user?.role === 'admin' || user?.role === 'super_admin';

  // Same gate as the /organization-settings/domains/:id route. Team members
  // land on Integrations, matching the gear in Organization Settings.
  const canOpenSettings = checkPermission(MODULES.ORGANIZATION_SETTINGS, 'read');
  const openDomainSettings = (domainId: number) => {
    setOpen(false);
    navigate(`/organization-settings/domains/${domainId}${user?.role === 'user' ? '?tab=integrations' : ''}`);
  };

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
  // there is nothing to switch to. The gear beside it is their only route into
  // the project, which is why it lives here rather than in the footer: a client
  // has one project, so "settings" and "this project" are the same thing.
  if (user?.role === 'client' && domains.length === 1) {
    const only = domains[0];
    return (
      <div className="relative">
        <Button
          variant="outline"
          className="w-full justify-start pr-12 pointer-events-none"
          tabIndex={-1}
        >
          <Globe className="mr-2 h-4 w-4 flex-shrink-0" />
          <span className="text-left flex-1 truncate">{only.name}</span>
        </Button>
        {canOpenSettings && (
          <button
            type="button"
            onClick={() => openDomainSettings(only.id)}
            title="Project health report"
            aria-label={`Health report for ${only.name}`}
            className="absolute right-2 top-1/2 -translate-y-1/2 flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          >
            <Settings className="h-4 w-4" />
          </button>
        )}
      </div>
    );
  }

  const selectedFaviconUrl = selectedDomain ? getFaviconUrl(selectedDomain.url, 32) : null;

  // Footer counts. Processing and failed are surfaced only when non-zero, so a
  // healthy account shows a plain project count rather than two zeroes.
  const processingCount = domains.filter(
    (d) => d.processing_status && ['INIT', 'SCHD', 'PROC'].includes(d.processing_status),
  ).length;
  const failedCount = domains.filter((d) => d.processing_status === 'FAIL').length;
  const isSearching = query.trim().length > 0;

  const filtered = domains.filter((d) => {
    const q = query.trim().toLowerCase();
    if (!q) return true;
    return (d.name || "").toLowerCase().includes(q)
      || hostLabel(d.url).toLowerCase().includes(q);
  });

  // The current project sits in its own section above the rest, so it is found
  // without scanning the grid. It drops out when a search doesn't match it.
  const currentMatch = filtered.find((d) => d.id === selectedDomain?.id);
  const otherDomains = filtered.filter((d) => d.id !== selectedDomain?.id);

  const renderDomainCard = (domain: (typeof domains)[number]) => {
    const faviconUrl = getFaviconUrl(domain.url, 64);
    const isProcessing = domain.processing_status
      && ['INIT', 'SCHD', 'PROC'].includes(domain.processing_status);
    const isFailed = domain.processing_status === 'FAIL';
    // Processing domains stay selectable — the label and spinner
    // are the signal, not a lock. Only failed domains are barred.
    const isDisabled = isFailed;
    const isActive = selectedDomain?.id === domain.id;
    const processingLabel = domain.processing_status === 'INIT' ? 'Initializing...' :
                            domain.processing_status === 'SCHD' ? 'Scheduled...' :
                            domain.processing_status === 'PROC' ? 'Processing...' : 'Processing...';

    // The gear is a sibling of the select button, not a child — a button
    // nested in a button is invalid HTML and swallows clicks unpredictably.
    // It stays enabled on failed projects: settings is where they get fixed.
    return (
      <div key={domain.id} className="relative">
        <button
          type="button"
          disabled={isDisabled}
          onClick={() => handleDomainSelect(domain.id)}
          className={cn(
            "flex w-full items-center gap-3 rounded-lg border p-3 text-left transition-colors",
            canOpenSettings && "pr-12",
            isActive
              ? "border-primary/30 bg-primary/5"
              : "border-border hover:border-primary/40 hover:bg-accent/50",
            isDisabled && "opacity-60 cursor-not-allowed hover:border-border hover:bg-transparent",
          )}
        >
          {/* The icon fills the tile edge to edge — a 24px glyph
              floating in a 40px box was hard to pick out when
              scanning fifty projects by logo. Favicons are square,
              so object-cover fills without cropping. */}
          <div className="h-10 w-10 flex-shrink-0 rounded-md border border-border bg-muted flex items-center justify-center overflow-hidden">
            {faviconUrl ? (
              <img
                src={faviconUrl}
                alt=""
                className="h-full w-full object-cover"
                onError={(e) => handleFaviconError(e, domain.url, domain.name, 64)}
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

        {canOpenSettings && (
          <button
            type="button"
            onClick={() => openDomainSettings(domain.id)}
            title="Project settings"
            aria-label={`Settings for ${domain.name}`}
            className="absolute right-2 top-1/2 -translate-y-1/2 flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          >
            <Settings className="h-4 w-4" />
          </button>
        )}
      </div>
    );
  };

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
              <div className="space-y-5">
                {currentMatch && (
                  <section>
                    <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Current project
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {renderDomainCard(currentMatch)}
                    </div>
                  </section>
                )}
                {otherDomains.length > 0 && (
                  <section>
                    <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Other projects
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {otherDomains.map(renderDomainCard)}
                    </div>
                  </section>
                )}
              </div>
            )}
          </div>

          {/* Footer. Flush to the dialog edges: -mx-6 -mb-6 cancels
              DialogContent's p-6, and -mt-4 cancels its grid `gap-4` — without
              that the border floated below a band of empty dialog background
              rather than sitting on the list's bottom edge. rounded-b-lg keeps
              the tinted bar inside the dialog's own corner radius.

              Renders even when the user cannot add a domain, because the counts
              are the point: with fifty-odd projects, "how many are there" and
              "how many did my search match" are not answerable by eye. */}
          <div className="-mx-6 -mb-6 -mt-4 flex flex-wrap items-center justify-between gap-3 rounded-b-lg border-t border-border bg-muted/30 px-6 py-3">
            <p className="text-xs text-muted-foreground">
              {isSearching ? (
                <>
                  <span className="font-medium text-foreground">{filtered.length}</span>
                  {" of "}
                  <span className="font-medium text-foreground">{domains.length}</span>
                  {" projects match"}
                </>
              ) : (
                <>
                  <span className="font-medium text-foreground">{domains.length}</span>
                  {domains.length === 1 ? " project" : " projects"}
                </>
              )}
              {processingCount > 0 && (
                <span className="text-orange-500"> · {processingCount} processing</span>
              )}
              {failedCount > 0 && (
                <span className="text-destructive"> · {failedCount} failed</span>
              )}
            </p>
            {canAddDomain && (
              <Button
                size="sm"
                onClick={() => {
                  setOpen(false);
                  setAddDomainOpen(true);
                }}
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Domain
              </Button>
            )}
          </div>
        </DialogContent>
      </Dialog>

      <AddDomainDialog
        open={addDomainOpen}
        onOpenChange={setAddDomainOpen}
        // Selection and the hand-off to Prompts happen inside the dialog, so
        // both entry points behave the same.
      />
    </>
  );
};
