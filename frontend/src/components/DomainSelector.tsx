import { useState, useEffect, useCallback } from "react";
import { Check, Globe, Loader2, ChevronDown, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { useDomainStore } from "@/stores/domainStore";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/hooks/use-toast";
import { getFaviconUrl, handleFaviconError } from "@/utils/faviconHelper";

export const DomainSelector = () => {
  const [open, setOpen] = useState(false);
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

  // Load domains on component mount
  useEffect(() => {
    // Don't clear the store - preserve the selected domain to prevent flash
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

  const selectedFaviconUrl = selectedDomain ? getFaviconUrl(selectedDomain.url, 32) : null;

  // Sort domains to put the selected domain first
  const sortedDomains = [...domains].sort((a, b) => {
    // Selected domain always comes first
    if (selectedDomain?.id === a.id) return -1;
    if (selectedDomain?.id === b.id) return 1;
    // Then sort by name
    return a.name.localeCompare(b.name);
  });

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full justify-start gap-2"
        >
          {selectedFaviconUrl ? (
            <img
              src={selectedFaviconUrl}
              alt=""
              className="h-4 w-4 flex-shrink-0 rounded"
              onError={(e) => handleFaviconError(e, selectedDomain?.url || '', selectedDomain?.name, 32)}
            />
          ) : null}
          <Globe className={cn("h-4 w-4 flex-shrink-0", selectedFaviconUrl && "hidden")} />
          <span className="text-left flex-1 truncate">
            {selectedDomain ? selectedDomain.name : "Select domain"}
          </span>
          <ChevronDown className="h-4 w-4 flex-shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[var(--radix-popover-trigger-width)] p-0">
        <Command>
          <CommandInput placeholder="Search domains..." />
          <CommandList>
            <CommandEmpty>No domains found.</CommandEmpty>
            <CommandGroup heading="Your Domains">
              {sortedDomains.map((domain) => {
                const faviconUrl = getFaviconUrl(domain.url, 32);
                const isProcessing = domain.processing_status && ['INIT', 'SCHD', 'PROC'].includes(domain.processing_status);
                const isFailed = domain.processing_status === 'FAIL';
                const isDisabled = isProcessing || isFailed;
                const processingLabel = domain.processing_status === 'INIT' ? 'Initializing...' :
                                       domain.processing_status === 'SCHD' ? 'Scheduled...' :
                                       domain.processing_status === 'PROC' ? 'Processing...' : 'Processing...';

                return (
                  <CommandItem
                    key={domain.id}
                    value={domain.name}
                    onSelect={() => handleDomainSelect(domain.id)}
                    className={cn(
                      "flex items-center justify-between gap-2",
                      isDisabled && "opacity-60 cursor-not-allowed"
                    )}
                    disabled={isDisabled}
                  >
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      {faviconUrl ? (
                        <img
                          src={faviconUrl}
                          alt=""
                          className="h-4 w-4 flex-shrink-0 rounded"
                          onError={(e) => handleFaviconError(e, domain.url, domain.name, 32)}
                        />
                      ) : null}
                      <Globe className={cn("h-4 w-4 flex-shrink-0", faviconUrl && "hidden")} />
                      <div className="flex flex-col flex-1 min-w-0">
                        <span className="truncate">{domain.name}</span>
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
                          <span className="text-xs text-muted-foreground">
                            {domain.total_mentions} mentions
                          </span>
                        )}
                      </div>
                    </div>
                    {isProcessing ? (
                      <AlertCircle className="h-4 w-4 flex-shrink-0 text-orange-500" />
                    ) : isFailed ? (
                      <AlertCircle className="h-4 w-4 flex-shrink-0 text-red-500" />
                    ) : (
                      <Check
                        className={cn(
                          "h-4 w-4 flex-shrink-0",
                          selectedDomain?.id === domain.id ? "opacity-100" : "opacity-0"
                        )}
                      />
                    )}
                  </CommandItem>
                );
              })}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
};
