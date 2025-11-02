import { useState, useEffect } from "react";
import { Check, Globe, Loader2, ChevronDown } from "lucide-react";
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

  // After domains load, restore last selected domain for this user
  useEffect(() => {
    if (!user) return;
    if (domains.length === 0) return;
    const key = `selected_domain_user_${user.id}`;
    const savedId = parseInt(localStorage.getItem(key) || '', 10);
    const exists = domains.find(d => d.id === savedId);
    if (exists) {
      setSelectedDomain(exists);
    } else {
      // if current selected not in list, pick first
      if (!selectedDomain || !domains.find(d => d.id === selectedDomain.id)) {
        setSelectedDomain(domains[0]);
        localStorage.setItem(key, String(domains[0].id));
      }
    }
  }, [domains, user, setSelectedDomain]);

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

  const handleDomainSelect = (domainId: number) => {
    const domain = domains.find(d => d.id === domainId);
    if (domain) {
      setSelectedDomain(domain);
      setOpen(false);
      if (user) {
        localStorage.setItem(`selected_domain_user_${user.id}`, String(domain.id));
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
                return (
                  <CommandItem
                    key={domain.id}
                    value={domain.name}
                    onSelect={() => handleDomainSelect(domain.id)}
                    className="flex items-center justify-between gap-2"
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
                        <span className="text-xs text-muted-foreground">
                          {domain.total_mentions} mentions
                        </span>
                      </div>
                    </div>
                    <Check
                      className={cn(
                        "h-4 w-4 flex-shrink-0",
                        selectedDomain?.id === domain.id ? "opacity-100" : "opacity-0"
                      )}
                    />
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
