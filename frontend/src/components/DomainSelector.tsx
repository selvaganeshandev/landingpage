import { useState } from "react";
import { Check, Globe } from "lucide-react";
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

const mockDomains = [
  { id: "1", domain: "acme.com", verified: true },
  { id: "2", domain: "acmecorp.com", verified: false },
];

export const DomainSelector = () => {
  const [open, setOpen] = useState(false);
  const [selectedDomain, setSelectedDomain] = useState(mockDomains[0]);

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
          {selectedDomain.domain}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[200px] p-0">
        <Command>
          <CommandInput placeholder="Search domains..." />
          <CommandList>
            <CommandEmpty>No domains found.</CommandEmpty>
            <CommandGroup heading="Your Domains">
              {mockDomains.map((domain) => (
                <CommandItem
                  key={domain.id}
                  value={domain.domain}
                  onSelect={() => {
                    setSelectedDomain(domain);
                    setOpen(false);
                  }}
                >
                  <Check
                    className={cn(
                      "mr-2 h-4 w-4",
                      selectedDomain.id === domain.id ? "opacity-100" : "opacity-0"
                    )}
                  />
                  {domain.domain}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
};
