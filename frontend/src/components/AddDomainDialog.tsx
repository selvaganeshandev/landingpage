import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { AlertTriangle, Check, ChevronDown, Loader2, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { apiClient } from "@/services/api";
import { useToast } from "@/hooks/use-toast";

interface AddDomainDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Fired after the domain is created, with the created domain. */
  onDomainAdded?: (domain: any) => void;
}

// Country list for searchable dropdown (sorted alphabetically)
const countries = [
  { value: "af", label: "Afghanistan" },
  { value: "al", label: "Albania" },
  { value: "dz", label: "Algeria" },
  { value: "ar", label: "Argentina" },
  { value: "am", label: "Armenia" },
  { value: "au", label: "Australia" },
  { value: "at", label: "Austria" },
  { value: "az", label: "Azerbaijan" },
  { value: "bh", label: "Bahrain" },
  { value: "bd", label: "Bangladesh" },
  { value: "by", label: "Belarus" },
  { value: "be", label: "Belgium" },
  { value: "bo", label: "Bolivia" },
  { value: "ba", label: "Bosnia and Herzegovina" },
  { value: "br", label: "Brazil" },
  { value: "bn", label: "Brunei" },
  { value: "bg", label: "Bulgaria" },
  { value: "kh", label: "Cambodia" },
  { value: "ca", label: "Canada" },
  { value: "cl", label: "Chile" },
  { value: "cn", label: "China" },
  { value: "co", label: "Colombia" },
  { value: "cr", label: "Costa Rica" },
  { value: "hr", label: "Croatia" },
  { value: "cy", label: "Cyprus" },
  { value: "cz", label: "Czech Republic" },
  { value: "dk", label: "Denmark" },
  { value: "do", label: "Dominican Republic" },
  { value: "ec", label: "Ecuador" },
  { value: "eg", label: "Egypt" },
  { value: "sv", label: "El Salvador" },
  { value: "ee", label: "Estonia" },
  { value: "et", label: "Ethiopia" },
  { value: "fi", label: "Finland" },
  { value: "fr", label: "France" },
  { value: "ge", label: "Georgia" },
  { value: "de", label: "Germany" },
  { value: "gh", label: "Ghana" },
  { value: "gr", label: "Greece" },
  { value: "gt", label: "Guatemala" },
  { value: "hk", label: "Hong Kong" },
  { value: "hu", label: "Hungary" },
  { value: "is", label: "Iceland" },
  { value: "in", label: "India" },
  { value: "id", label: "Indonesia" },
  { value: "ir", label: "Iran" },
  { value: "iq", label: "Iraq" },
  { value: "ie", label: "Ireland" },
  { value: "il", label: "Israel" },
  { value: "it", label: "Italy" },
  { value: "jm", label: "Jamaica" },
  { value: "jp", label: "Japan" },
  { value: "jo", label: "Jordan" },
  { value: "kz", label: "Kazakhstan" },
  { value: "ke", label: "Kenya" },
  { value: "kw", label: "Kuwait" },
  { value: "lv", label: "Latvia" },
  { value: "lb", label: "Lebanon" },
  { value: "ly", label: "Libya" },
  { value: "lt", label: "Lithuania" },
  { value: "lu", label: "Luxembourg" },
  { value: "my", label: "Malaysia" },
  { value: "mv", label: "Maldives" },
  { value: "mt", label: "Malta" },
  { value: "mu", label: "Mauritius" },
  { value: "mx", label: "Mexico" },
  { value: "md", label: "Moldova" },
  { value: "mn", label: "Mongolia" },
  { value: "me", label: "Montenegro" },
  { value: "ma", label: "Morocco" },
  { value: "mm", label: "Myanmar" },
  { value: "np", label: "Nepal" },
  { value: "nl", label: "Netherlands" },
  { value: "nz", label: "New Zealand" },
  { value: "ng", label: "Nigeria" },
  { value: "mk", label: "North Macedonia" },
  { value: "no", label: "Norway" },
  { value: "om", label: "Oman" },
  { value: "pk", label: "Pakistan" },
  { value: "pa", label: "Panama" },
  { value: "py", label: "Paraguay" },
  { value: "pe", label: "Peru" },
  { value: "ph", label: "Philippines" },
  { value: "pl", label: "Poland" },
  { value: "pt", label: "Portugal" },
  { value: "pr", label: "Puerto Rico" },
  { value: "qa", label: "Qatar" },
  { value: "ro", label: "Romania" },
  { value: "ru", label: "Russia" },
  { value: "sa", label: "Saudi Arabia" },
  { value: "rs", label: "Serbia" },
  { value: "sg", label: "Singapore" },
  { value: "sk", label: "Slovakia" },
  { value: "si", label: "Slovenia" },
  { value: "za", label: "South Africa" },
  { value: "kr", label: "South Korea" },
  { value: "es", label: "Spain" },
  { value: "lk", label: "Sri Lanka" },
  { value: "se", label: "Sweden" },
  { value: "ch", label: "Switzerland" },
  { value: "tw", label: "Taiwan" },
  { value: "tz", label: "Tanzania" },
  { value: "th", label: "Thailand" },
  { value: "tn", label: "Tunisia" },
  { value: "tr", label: "Turkey" },
  { value: "ua", label: "Ukraine" },
  { value: "ae", label: "United Arab Emirates" },
  { value: "gb", label: "United Kingdom" },
  { value: "us", label: "United States" },
  { value: "uy", label: "Uruguay" },
  { value: "uz", label: "Uzbekistan" },
  { value: "ve", label: "Venezuela" },
  { value: "vn", label: "Vietnam" },
  { value: "ye", label: "Yemen" },
  { value: "zm", label: "Zambia" },
  { value: "zw", label: "Zimbabwe" },
];

/** What the analysis is doing, in the order it does it. */
const ANALYSIS_STEPS = [
  "Fetching your website",
  "Reading your page content",
  "Extracting your brand details",
  "Setting up your brand",
];

// The analysis really is one request, so these are paced rather than reported.
// The last analysis step never self-completes — it only ticks over when the
// response actually lands, so the checklist can't finish ahead of the work.
const STEP_PACE_MS = 4000;

/**
 * The "Add Domain" wizard: enter the brand, watch its site get read, done.
 *
 * There used to be a second step that generated ~50 AI prompts before a domain
 * could exist, behind a 45-second scripted progress animation. That made every
 * project pay the GEO setup cost even when it was only ever going to be tracked
 * for SEO. Prompts are now added on demand from the Prompts page; onboarding
 * just reads the site (the same crawl + extraction the generation wizard's
 * "Autofill from my site" uses) and saves what it finds.
 */
export function AddDomainDialog({ open, onOpenChange, onDomainAdded }: AddDomainDialogProps) {
  const { toast } = useToast();

  const [newDomain, setNewDomain] = useState("");
  const [newBrandName, setNewBrandName] = useState("");
  const [newDomainCountry, setNewDomainCountry] = useState("us");
  const [countryDropdownOpen, setCountryDropdownOpen] = useState(false);

  const [isRunning, setIsRunning] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [warning, setWarning] = useState<string | null>(null);
  // Steps 0-2 are paced by this timer; it never advances past the last
  // analysis step, which only the response can complete.
  const paceRef = useRef<number | null>(null);

  const stopPacing = () => {
    if (paceRef.current !== null) {
      window.clearInterval(paceRef.current);
      paceRef.current = null;
    }
  };

  useEffect(() => stopPacing, []);

  const resetAll = () => {
    stopPacing();
    setNewDomain("");
    setNewBrandName("");
    setNewDomainCountry("us");
    setIsRunning(false);
    setStepIndex(0);
    setWarning(null);
  };

  const selectedCountry = countries.find(c => c.value === newDomainCountry);

  const cleanDomainInput = (input: string): string => {
    if (!input.trim()) return input;

    try {
      // Remove everything after the first slash (including query params, fragments, etc.)
      let cleaned = input.trim();

      // Remove protocol if present (https:// or http://)
      cleaned = cleaned.replace(/^https?:\/\//i, '');

      // Extract only the domain part (everything before first slash, question mark, or hash)
      const domainMatch = cleaned.match(/^([^\/\?#]+)/);
      if (domainMatch) {
        cleaned = domainMatch[1];
      }

      // Remove trailing slash if present
      cleaned = cleaned.replace(/\/+$/, '');

      return cleaned;
    } catch (error) {
      // If parsing fails, return original input
      return input;
    }
  };

  const handleAnalyzeAndAdd = async () => {
    const domainName = cleanDomainInput(newDomain).trim();
    const brandName = newBrandName.trim();

    if (!domainName || !brandName) {
      toast({
        title: "Domain and brand name required",
        description: "Enter the website and the official brand name to continue.",
        variant: "destructive",
      });
      return;
    }

    setIsRunning(true);
    setWarning(null);
    setStepIndex(0);

    stopPacing();
    paceRef.current = window.setInterval(() => {
      // Hold on the last analysis step until the request returns.
      setStepIndex((prev) => (prev < ANALYSIS_STEPS.length - 2 ? prev + 1 : prev));
    }, STEP_PACE_MS);

    try {
      const analysis: any = await apiClient.analyzeBrandSite({
        domain_name: domainName,
        brand_name: brandName,
      });

      stopPacing();
      if (analysis?.warning) setWarning(analysis.warning);
      setStepIndex(ANALYSIS_STEPS.length - 1);

      const created: any = await apiClient.createAnalyzedDomain({
        domain_name: domainName,
        brand_name: brandName,
        country: newDomainCountry,
        fields: analysis?.fields || {},
      });

      if (!created?.success || !created?.domain) {
        throw new Error(created?.error || "Failed to create the brand.");
      }

      // Refresh the global domain store so every switcher sees the new brand
      const { useDomainStore } = await import('@/stores/domainStore');
      await useDomainStore.getState().loadDomains();

      setStepIndex(ANALYSIS_STEPS.length);

      toast({
        title: "Brand added",
        description: analysis?.warning
          ? `${created.domain.name} is ready. We couldn't read the site, so review its details in Domain Settings.`
          : `${created.domain.name} is ready to use.`,
        duration: 5000,
      });

      onDomainAdded?.(created.domain);
      resetAll();
      onOpenChange(false);
    } catch (error: any) {
      stopPacing();
      setIsRunning(false);
      setStepIndex(0);

      let description = error?.message || "Failed to add the brand. Please try again.";
      if (description.includes("must make a unique set") || description.includes("already exists")) {
        description = "This domain already exists in your organization.";
      }

      toast({
        title: "Couldn't add the brand",
        description,
        variant: "destructive",
      });
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        // Closing mid-analysis would abandon a brand halfway through creation.
        if (!next && isRunning) return;
        onOpenChange(next);
        if (!next) resetAll();
      }}
    >
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Add Domain</DialogTitle>
          <DialogDescription>
            {isRunning
              ? "Reading your website and setting the brand up"
              : "We'll read your website and fill in the brand details for you"}
          </DialogDescription>
        </DialogHeader>

        {isRunning ? (
          <div className="py-6 space-y-5">
            <p className="text-sm text-muted-foreground">
              Analyzing <span className="font-medium text-foreground">{cleanDomainInput(newDomain)}</span>
            </p>

            <ul className="space-y-3">
              {ANALYSIS_STEPS.map((label, index) => {
                const done = index < stepIndex;
                const active = index === stepIndex;

                return (
                  <li
                    key={label}
                    className={cn(
                      "flex items-center gap-3 text-sm transition-colors",
                      done && "text-foreground",
                      active && "text-foreground font-medium",
                      !done && !active && "text-muted-foreground/60",
                    )}
                  >
                    <span className="flex h-6 w-6 items-center justify-center">
                      {done ? (
                        <Check className="h-4 w-4 text-primary" />
                      ) : active ? (
                        <Loader2 className="h-4 w-4 animate-spin text-primary" />
                      ) : (
                        <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/40" />
                      )}
                    </span>
                    {label}
                  </li>
                );
              })}
            </ul>

            {warning && (
              <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-200">
                <AlertTriangle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                <span>{warning}</span>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-6 py-4">
            {/* Domain URL */}
            <div className="space-y-2">
              <Label htmlFor="domain-url">Domain URL <span className="text-destructive">*</span></Label>
              <Input
                id="domain-url"
                placeholder="example.com (without http:// or https://)"
                value={newDomain}
                onChange={(e) => setNewDomain(e.target.value)}
                onBlur={(e) => {
                  const cleaned = cleanDomainInput(e.target.value);
                  if (cleaned !== e.target.value) {
                    setNewDomain(cleaned);
                  }
                }}
                onPaste={(e) => {
                  const pastedText = e.clipboardData.getData('text');
                  const cleaned = cleanDomainInput(pastedText);
                  if (cleaned !== pastedText) {
                    e.preventDefault();
                    setNewDomain(cleaned);
                  }
                }}
              />
            </div>

            {/* Brand Name */}
            <div className="space-y-2">
              <Label htmlFor="brand-name">Brand Name <span className="text-destructive">*</span></Label>
              <Input
                id="brand-name"
                placeholder="Enter official brand name (e.g., Acme Inc)"
                value={newBrandName}
                onChange={(e) => setNewBrandName(e.target.value)}
              />
            </div>

            {/* Country Selector - Searchable */}
            <div className="space-y-2">
              <Label htmlFor="domain-country">Country</Label>
              <Popover open={countryDropdownOpen} onOpenChange={setCountryDropdownOpen}>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    role="combobox"
                    aria-expanded={countryDropdownOpen}
                    className="w-full justify-between"
                    id="domain-country"
                  >
                    {selectedCountry ? selectedCountry.label : "Select primary country for this brand"}
                    <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-[var(--radix-popover-trigger-width)] p-0" align="start">
                  <Command>
                    <CommandInput placeholder="Search country..." />
                    <CommandList>
                      <CommandEmpty>No country found.</CommandEmpty>
                      <CommandGroup>
                        {countries.map((country) => (
                          <CommandItem
                            key={country.value}
                            value={country.label}
                            onSelect={() => {
                              setNewDomainCountry(country.value);
                              setCountryDropdownOpen(false);
                            }}
                          >
                            <Check
                              className={cn(
                                "mr-2 h-4 w-4",
                                newDomainCountry === country.value ? "opacity-100" : "opacity-0"
                              )}
                            />
                            {country.label}
                          </CommandItem>
                        ))}
                      </CommandGroup>
                    </CommandList>
                  </Command>
                </PopoverContent>
              </Popover>
            </div>

            {/* What the analysis will do */}
            <div className="space-y-3 bg-muted/50 p-4 rounded-lg border border-muted">
              <div className="flex items-start gap-2">
                <Sparkles className="h-5 w-5 text-primary mt-0.5" />
                <div className="space-y-2">
                  <Label className="text-base">Quick site analysis</Label>
                  <p className="text-sm text-muted-foreground">
                    We'll read your website and pull out what your brand does, who it
                    sells to, its niches and its competitors. Takes a few seconds.
                  </p>
                  <p className="text-xs text-muted-foreground italic">
                    Tracking prompts in AI answers? Add them any time from the Prompts page.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        <DialogFooter className="gap-2">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isRunning}
          >
            Cancel
          </Button>
          <Button
            onClick={handleAnalyzeAndAdd}
            disabled={!newDomain.trim() || !newBrandName.trim() || isRunning}
          >
            {isRunning ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4 mr-2" />
                Analyze &amp; Add Brand
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
