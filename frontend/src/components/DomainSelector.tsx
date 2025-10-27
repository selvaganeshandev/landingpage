import { useState, useEffect } from "react";
import { Check, Globe, Loader2 } from "lucide-react";
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
import { useToast } from "@/hooks/use-toast";

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

  // Load domains on component mount
  useEffect(() => {
    // Clear any cached data first
    clearDomainStore();
    // Then load fresh data
    loadDomains();
  }, [loadDomains, clearDomainStore]);

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
    }
  };

  if (isLoading && domains.length === 0) {
    return (
      <Button
        variant="outline"
        className="w-[200px] justify-between"
        disabled
      >
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        Loading domains...
      </Button>
    );
  }

  if (domains.length === 0) {
    return (
      <Button
        variant="outline"
        className="w-[200px] justify-between"
        disabled
      >
        <Globe className="mr-2 h-4 w-4" />
        No domain added
      </Button>
    );
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-[200px] justify-between"
        >
          <Globe className="mr-2 h-4 w-4" />
          {selectedDomain ? selectedDomain.name : "Select domain"}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[200px] p-0">
        <Command>
          <CommandInput placeholder="Search domains..." />
          <CommandList>
            <CommandEmpty>No domains found.</CommandEmpty>
            <CommandGroup heading="Your Domains">
              {domains.map((domain) => (
                <CommandItem
                  key={domain.id}
                  value={domain.name}
                  onSelect={() => handleDomainSelect(domain.id)}
                >
                  <Check
                    className={cn(
                      "mr-2 h-4 w-4",
                      selectedDomain?.id === domain.id ? "opacity-100" : "opacity-0"
                    )}
                  />
                  <div className="flex flex-col">
                    <span>{domain.name}</span>
                    <span className="text-xs text-muted-foreground">
                      {domain.total_mentions} mentions
                    </span>
                  </div>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
};
