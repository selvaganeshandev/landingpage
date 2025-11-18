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

// Helper function to get favicon URL from domain URL
const getFaviconUrl = (url: string) => {
  try {
    const domain = new URL(url).hostname;
    return `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
  } catch {
    return null;
  }
};

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
    selectDefaultDomain,
    clearDomainStore
  } = useDomainStore();
  const { user } = useAuth();

  // Load domains on component mount
  useEffect(() => {
    clearDomainStore();
    loadDomains();
  }, [loadDomains, clearDomainStore]);

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

  // After domains load, restore last selected domain from server
  useEffect(() => {
    if (!user) return;
    if (domains.length === 0) return;
    
    const restoreDomain = async () => {
      // Load from server (primary source of truth)
      const { loadActiveDomainFromServer, updateActiveDomain } = await import('@/utils/activeDomain');
      const serverActiveDomainId = await loadActiveDomainFromServer(user.id);
      
      if (serverActiveDomainId) {
        const domainId = parseInt(serverActiveDomainId, 10);
        const exists = domains.find(d => d.id === domainId);
        if (exists) {
          // Sync both systems: set Zustand store and verify active_domain_id matches
          setSelectedDomain(exists);
          // Verify active_domain_id is in sync
          const currentActiveId = localStorage.getItem(`active_domain_id:${user.id}`);
          if (currentActiveId !== String(domainId)) {
            await updateActiveDomain(user.id, domainId, exists);
          }
          return;
        }
      }
      
      // If server has no active domain or domain doesn't exist, use first domain
      if (!serverActiveDomainId || serverActiveDomainId === null || serverActiveDomainId === '') {
        const firstDomain = domains[0];
        if (firstDomain) {
          // Update both systems: Zustand store and server
          setSelectedDomain(firstDomain);
          await updateActiveDomain(user.id, firstDomain.id, firstDomain);
        }
      } else if (!selectedDomain || !domains.find(d => d.id === selectedDomain.id)) {
        // Server has active domain but it doesn't exist in current domain list
        const firstDomain = domains[0];
        if (firstDomain) {
          setSelectedDomain(firstDomain);
          // Update server with first domain
          await updateActiveDomain(user.id, firstDomain.id, firstDomain);
        }
      }
    };
    
    void restoreDomain();
  }, [domains, user, setSelectedDomain, selectedDomain]);

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
      // Check if domain is still processing - don't allow selection
      if (domain.processing_status && ['INIT', 'SCHD', 'PROC'].includes(domain.processing_status)) {
        toast({
          title: "Domain Processing",
          description: "This domain is still being processed. Please wait until processing completes.",
          variant: "default",
        });
        return;
      }

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

  const selectedFaviconUrl = selectedDomain ? getFaviconUrl(selectedDomain.url) : null;

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
              onError={(e) => {
                e.currentTarget.style.display = 'none';
                e.currentTarget.nextElementSibling?.classList.remove('hidden');
              }}
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
              {domains.map((domain) => {
                const faviconUrl = getFaviconUrl(domain.url);
                const isProcessing = domain.processing_status && ['INIT', 'SCHD', 'PROC'].includes(domain.processing_status);
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
                      isProcessing && "opacity-60 cursor-not-allowed"
                    )}
                    disabled={isProcessing}
                  >
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      {faviconUrl ? (
                        <img
                          src={faviconUrl}
                          alt=""
                          className="h-4 w-4 flex-shrink-0 rounded"
                          onError={(e) => {
                            e.currentTarget.style.display = 'none';
                            e.currentTarget.nextElementSibling?.classList.remove('hidden');
                          }}
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
                        ) : (
                          <span className="text-xs text-muted-foreground">
                            {domain.total_mentions} mentions
                          </span>
                        )}
                      </div>
                    </div>
                    {isProcessing ? (
                      <AlertCircle className="h-4 w-4 flex-shrink-0 text-orange-500" />
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
