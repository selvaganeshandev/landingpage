"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  ChevronLeft,
  ChevronRight,
  Check,
  ChevronDown,
  Loader2,
  Sparkles,
  Search,
  Plus,
  Building2,
  Users,
  Target,
  Eye,
  Shield,
  FileText,
  BarChart3,
  Briefcase,
  Megaphone,
  Code,
  Rocket,
  UserCircle,
} from "lucide-react";
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { apiClient } from "@/services/api";
import { useToast } from "@/hooks/use-toast";
import { User } from "@/types/auth";

interface OnboardingModalProps {
  onComplete: (domain: any) => void;
  user?: User | null;
}

// Industry options
const industries = [
  { id: "technology", name: "Technology & Software", icon: Code },
  { id: "ecommerce", name: "E-Commerce & Retail", icon: Briefcase },
  { id: "marketing", name: "Marketing & Advertising", icon: Megaphone },
  { id: "finance", name: "Finance & Banking", icon: BarChart3 },
  { id: "healthcare", name: "Healthcare & Medical", icon: Shield },
  { id: "education", name: "Education & Training", icon: FileText },
  { id: "saas", name: "SaaS & B2B Services", icon: Rocket },
  { id: "agency", name: "Agency & Consulting", icon: Users },
  { id: "other", name: "Other", icon: Building2 },
];

// Company size options
const companySizes = [
  { id: "1-10", name: "1-10", description: "Startup / Small team" },
  { id: "11-50", name: "11-50", description: "Growing company" },
  { id: "51-200", name: "51-200", description: "Mid-size company" },
  { id: "200+", name: "200+", description: "Enterprise" },
];

// User role options
const userRoles = [
  { id: "founder", name: "Founder / CEO", icon: Rocket },
  { id: "marketing", name: "Marketing Manager", icon: Megaphone },
  { id: "seo", name: "SEO Specialist", icon: Search },
  { id: "content", name: "Content Strategist", icon: FileText },
  { id: "agency", name: "Agency / Consultant", icon: Briefcase },
  { id: "other", name: "Other", icon: UserCircle },
];

// Goals options
const goalOptions = [
  {
    id: "brand_monitoring",
    name: "Monitor Brand Mentions",
    description: "Track how AI platforms mention your brand",
    icon: Eye,
  },
  {
    id: "competitor_tracking",
    name: "Track Competitors",
    description: "Compare your visibility against competitors",
    icon: Target,
  },
  {
    id: "misinformation",
    name: "Detect Misinformation",
    description: "Find and correct inaccurate AI responses",
    icon: Shield,
  },
  {
    id: "content_optimization",
    name: "Optimize Content",
    description: "Improve content for AI discovery",
    icon: FileText,
  },
  {
    id: "traffic_measurement",
    name: "Measure AI Traffic",
    description: "Track visitors coming from AI platforms",
    icon: BarChart3,
  },
  {
    id: "multi_brand",
    name: "Manage Multiple Brands",
    description: "Agency or multi-brand management",
    icon: Building2,
  },
];

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

// Progress messages for automated onboarding
const progressMessages = [
  "Analyzing your website structure and content",
  "Reviewing your most engaging content pieces",
  "Identifying your primary industry niches",
  "Examining common prompts across AI platforms",
  "Categorizing prompt patterns and user intent",
  "Evaluating LLM response quality",
  "Discovering your key competitors",
  "Identifying content gaps and opportunities",
  "Generating recommended content topics",
  "Preparing your brand monitoring dashboard",
];

export function OnboardingModal({ onComplete, user }: OnboardingModalProps) {
  const { toast } = useToast();

  // Check if user already has an organization (invited user)
  // If so, skip organization setup steps (1 & 2) and go directly to domain setup (step 3)
  const hasExistingOrganization = Boolean(user?.organisation && user?.organisation_name);

  // Total steps in the wizard - 4 for new users, 2 for invited users (skip org steps)
  const totalSteps = hasExistingOrganization ? 2 : 4;

  // Map displayed step to actual wizard step
  // For invited users: displayed step 1 = wizard step 3, displayed step 2 = wizard step 4
  const getActualStep = (displayedStep: number) => {
    if (hasExistingOrganization) {
      return displayedStep + 2; // 1->3, 2->4
    }
    return displayedStep;
  };

  // Wizard state - start at step 3 for invited users
  const [wizardStep, setWizardStep] = useState(hasExistingOrganization ? 3 : 1);
  const [isLoading, setIsLoading] = useState(false);

  // Step 1: Organization Info
  const [orgName, setOrgName] = useState("");
  const [industry, setIndustry] = useState("");
  const [companySize, setCompanySize] = useState("");
  const [userRole, setUserRole] = useState("");

  // Step 2: Goals
  const [selectedGoals, setSelectedGoals] = useState<Set<string>>(new Set());
  const [usingAIMonitoring, setUsingAIMonitoring] = useState<boolean | null>(null);

  // Step 3: Domain Info
  const [newDomain, setNewDomain] = useState("");
  const [newBrandName, setNewBrandName] = useState("");
  const [newDomainCountry, setNewDomainCountry] = useState("us");
  const [countryDropdownOpen, setCountryDropdownOpen] = useState(false);

  // Niche state
  const [suggestedNiches, setSuggestedNiches] = useState<string[]>([]);
  const [selectedNiches, setSelectedNiches] = useState<string[]>([]);

  // Step 4: Semantic keyword state
  const [generatedKeywords, setGeneratedKeywords] = useState<any[]>([]);
  const [selectedKeywordIndices, setSelectedKeywordIndices] = useState<Set<number>>(new Set());
  const [isGeneratingKeywords, setIsGeneratingKeywords] = useState(false);
  const [keywordSearchQuery, setKeywordSearchQuery] = useState("");
  const [useManualKeywords, setUseManualKeywords] = useState(false);
  const [ignoreBrandKeywords, setIgnoreBrandKeywords] = useState(false);
  const [keywordInput, setKeywordInput] = useState("");

  // Topic-level selection state
  const [selectedTopics, setSelectedTopics] = useState<Set<string>>(new Set());

  // Automated onboarding state
  const [isAutomatedOnboarding, setIsAutomatedOnboarding] = useState(false);
  const [onboardingProgress, setOnboardingProgress] = useState(0);

  const selectedCountry = countries.find((c) => c.value === newDomainCountry);

  // Progress message animation
  useEffect(() => {
    if (!isAutomatedOnboarding) return;

    const interval = setInterval(() => {
      setOnboardingProgress((prev) => {
        if (prev < progressMessages.length - 1) {
          return prev + 1;
        }
        return prev;
      });
    }, 4500);

    return () => clearInterval(interval);
  }, [isAutomatedOnboarding]);

  const cleanDomainInput = (input: string): string => {
    if (!input.trim()) return input;

    try {
      let cleaned = input.trim();
      cleaned = cleaned.replace(/^https?:\/\//i, "");
      const domainMatch = cleaned.match(/^([^\/\?#]+)/);
      if (domainMatch) {
        cleaned = domainMatch[1];
      }
      cleaned = cleaned.replace(/\/+$/, "");
      return cleaned;
    } catch (error) {
      return input;
    }
  };

  const handleToggleGoal = (goalId: string) => {
    setSelectedGoals((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(goalId)) {
        newSet.delete(goalId);
      } else {
        newSet.add(goalId);
      }
      return newSet;
    });
  };

  const canProceed = () => {
    switch (wizardStep) {
      case 1:
        return orgName.trim() && industry && companySize && userRole;
      case 2:
        return selectedGoals.size > 0;
      case 3:
        return newDomain.trim() && newBrandName.trim();
      case 4:
        return useManualKeywords || selectedTopics.size > 0;
      default:
        return true;
    }
  };

  const handleNext = async () => {
    if (wizardStep === 2) {
      // Save organization info before moving to domain step
      try {
        await apiClient.updateOrganization({
          name: orgName.trim(),
          industry: industry,
          company_size: companySize,
          user_role: userRole,
          goals: Array.from(selectedGoals),
          using_ai_monitoring: usingAIMonitoring,
        });
      } catch (error) {
        console.error("Failed to save organization info:", error);
        // Continue anyway - the org info is nice-to-have
      }
    }

    if (wizardStep < totalSteps) {
      setWizardStep(wizardStep + 1);
    }
  };

  const handleBack = () => {
    const minStep = hasExistingOrganization ? 3 : 1;
    if (wizardStep > minStep) {
      setWizardStep(wizardStep - 1);
    }
  };

  const handleGenerateKeywords = async () => {
    try {
      setIsGeneratingKeywords(true);
      setIsAutomatedOnboarding(true);
      setOnboardingProgress(0);

      const animationStartTime = Date.now();
      const TOTAL_ANIMATION_DURATION = 10 * 4500;

      const selectedCountryObj = countries.find((c) => c.value === newDomainCountry);
      const countryName = selectedCountryObj ? selectedCountryObj.label : "United States";

      // Step 1: Fetch niches if not already selected
      let nichesToUse = selectedNiches;
      if (nichesToUse.length === 0) {
        try {
          const nicheResponse: any = await apiClient.fetchBrandNiches(
            newDomain.trim(),
            newBrandName.trim()
          );
          if (nicheResponse.success && nicheResponse.niches) {
            nichesToUse = nicheResponse.niches;
            setSuggestedNiches(nicheResponse.niches);
            setSelectedNiches(nicheResponse.niches);
          }
        } catch (error) {
          console.error("Error fetching niches:", error);
        }
      }

      // Step 2: Generate semantic keywords
      const response: any = await apiClient.generateSemanticKeywords({
        domain_name: newDomain.trim(),
        brand_name: newBrandName.trim(),
        country: countryName,
        niches: nichesToUse,
        approx_keywords: 100,
      });

      if (response.success && response.keywords) {
        setGeneratedKeywords(response.keywords);
        setSelectedKeywordIndices(new Set());

        const elapsedTime = Date.now() - animationStartTime;
        const remainingTime = Math.max(0, TOTAL_ANIMATION_DURATION - elapsedTime);

        setTimeout(() => {
          setIsAutomatedOnboarding(false);
          setOnboardingProgress(0);
          setWizardStep(4);
        }, remainingTime);
      } else {
        throw new Error("Failed to generate keywords");
      }
    } catch (error: any) {
      setIsAutomatedOnboarding(false);
      setOnboardingProgress(0);
      toast({
        title: "Error generating keywords",
        description: error.message || "Failed to generate keywords from AI.",
        variant: "destructive",
      });
    } finally {
      setIsGeneratingKeywords(false);
    }
  };

  const handleAddDomain = async () => {
    if (!newDomain.trim()) {
      toast({
        title: "Domain required",
        description: "Please enter a domain name.",
        variant: "destructive",
      });
      return;
    }

    if (!useManualKeywords && generatedKeywords.length > 0 && selectedTopics.size === 0) {
      toast({
        title: "No topics selected",
        description: "Please select at least one topic from the list.",
        variant: "destructive",
      });
      return;
    }

    try {
      setIsLoading(true);

      const domainName = newDomain.trim();

      const response: any = await apiClient.automatedDomainOnboard({
        domain_name: domainName,
        brand_name: newBrandName.trim(),
        country: newDomainCountry,
        niches: selectedNiches.length > 0 ? selectedNiches : undefined,
      });

      if (response.success && response.domain) {
        const createdDomainId = response.domain.id;

        // Gather all keywords from selected topics
        if (createdDomainId && selectedTopics.size > 0) {
          try {
            const selectedKeywords = generatedKeywords.filter((kw) =>
              selectedTopics.has(kw.topic || "Other")
            );
            await apiClient.bulkCreateKeywords(createdDomainId, selectedKeywords);
          } catch (keywordError) {
            console.error("Failed to save selected keywords:", keywordError);
          }
        }

        toast({
          title: "Setup Complete!",
          description: `${response.domain.name} has been created. Welcome to PromptMaxx!`,
          duration: 5000,
        });

        onComplete(response.domain);
      } else {
        throw new Error(response.error || "Failed to create domain");
      }
    } catch (error: any) {
      let errorMessage = error.message || "Failed to add domain. Please try again.";
      if (error.message && error.message.includes("must make a unique set")) {
        errorMessage = `This domain already exists in your organization. Please use a different domain or delete the existing one first.`;
      }

      toast({
        title: "Error adding domain",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const renderStepContent = () => {
    switch (wizardStep) {
      case 1:
        return (
          <div className="space-y-6">
            {/* Organization Name */}
            <div className="space-y-2">
              <Label htmlFor="org-name">
                Organization Name <span className="text-red-500">*</span>
              </Label>
              <Input
                id="org-name"
                placeholder="Your company or organization name"
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                className="h-12"
              />
            </div>

            {/* Industry */}
            <div className="space-y-3">
              <Label>
                Industry <span className="text-red-500">*</span>
              </Label>
              <div className="grid grid-cols-3 gap-3">
                {industries.map((ind) => {
                  const Icon = ind.icon;
                  const isSelected = industry === ind.id;
                  return (
                    <div
                      key={ind.id}
                      onClick={() => setIndustry(ind.id)}
                      className={cn(
                        "relative p-4 rounded-xl border-2 cursor-pointer transition-all hover:shadow-md",
                        isSelected
                          ? "border-purple-500 bg-purple-50"
                          : "border-gray-200 bg-white hover:border-gray-300"
                      )}
                    >
                      {isSelected && (
                        <div className="absolute top-2 right-2 w-5 h-5 bg-purple-600 rounded-full flex items-center justify-center">
                          <Check className="w-3 h-3 text-white" />
                        </div>
                      )}
                      <Icon
                        className={cn(
                          "w-6 h-6 mb-2",
                          isSelected ? "text-purple-600" : "text-gray-500"
                        )}
                      />
                      <p className={cn("text-sm font-medium", isSelected && "text-purple-900")}>
                        {ind.name}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Company Size */}
            <div className="space-y-3">
              <Label>
                Company Size <span className="text-red-500">*</span>
              </Label>
              <div className="grid grid-cols-4 gap-3">
                {companySizes.map((size) => {
                  const isSelected = companySize === size.id;
                  return (
                    <div
                      key={size.id}
                      onClick={() => setCompanySize(size.id)}
                      className={cn(
                        "p-4 rounded-xl border-2 cursor-pointer transition-all text-center",
                        isSelected
                          ? "border-purple-500 bg-purple-50"
                          : "border-gray-200 bg-white hover:border-gray-300"
                      )}
                    >
                      <p className={cn("font-bold text-lg", isSelected && "text-purple-600")}>
                        {size.name}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">{size.description}</p>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* User Role */}
            <div className="space-y-3">
              <Label>
                Your Role <span className="text-red-500">*</span>
              </Label>
              <div className="grid grid-cols-3 gap-3">
                {userRoles.map((role) => {
                  const Icon = role.icon;
                  const isSelected = userRole === role.id;
                  return (
                    <div
                      key={role.id}
                      onClick={() => setUserRole(role.id)}
                      className={cn(
                        "flex items-center gap-3 p-3 rounded-xl border-2 cursor-pointer transition-all",
                        isSelected
                          ? "border-purple-500 bg-purple-50"
                          : "border-gray-200 bg-white hover:border-gray-300"
                      )}
                    >
                      <Icon
                        className={cn(
                          "w-5 h-5",
                          isSelected ? "text-purple-600" : "text-gray-500"
                        )}
                      />
                      <span className={cn("text-sm font-medium", isSelected && "text-purple-900")}>
                        {role.name}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        );

      case 2:
        return (
          <div className="space-y-6">
            {/* Goals */}
            <div className="space-y-3">
              <Label>
                What are your primary goals? <span className="text-red-500">*</span>
              </Label>
              <p className="text-sm text-gray-500">Select all that apply</p>
              <div className="grid grid-cols-2 gap-4">
                {goalOptions.map((goal) => {
                  const Icon = goal.icon;
                  const isSelected = selectedGoals.has(goal.id);
                  return (
                    <div
                      key={goal.id}
                      onClick={() => handleToggleGoal(goal.id)}
                      className={cn(
                        "relative p-4 rounded-xl border-2 cursor-pointer transition-all hover:shadow-md",
                        isSelected
                          ? "border-purple-500 bg-purple-50"
                          : "border-gray-200 bg-white hover:border-gray-300"
                      )}
                    >
                      {isSelected && (
                        <div className="absolute top-3 right-3 w-5 h-5 bg-purple-600 rounded-full flex items-center justify-center">
                          <Check className="w-3 h-3 text-white" />
                        </div>
                      )}
                      <div className="flex items-start gap-3">
                        <div
                          className={cn(
                            "w-10 h-10 rounded-lg flex items-center justify-center",
                            isSelected ? "bg-purple-100" : "bg-gray-100"
                          )}
                        >
                          <Icon
                            className={cn(
                              "w-5 h-5",
                              isSelected ? "text-purple-600" : "text-gray-500"
                            )}
                          />
                        </div>
                        <div className="flex-1">
                          <p
                            className={cn(
                              "font-medium",
                              isSelected ? "text-purple-900" : "text-gray-900"
                            )}
                          >
                            {goal.name}
                          </p>
                          <p className="text-xs text-gray-500 mt-1">{goal.description}</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Currently using AI monitoring */}
            <div className="space-y-3">
              <Label>Are you currently using any AI monitoring tools?</Label>
              <div className="flex gap-3">
                <Button
                  variant={usingAIMonitoring === true ? "default" : "outline"}
                  onClick={() => setUsingAIMonitoring(true)}
                  className={cn(
                    "flex-1",
                    usingAIMonitoring === true && "bg-purple-600 hover:bg-purple-700"
                  )}
                >
                  Yes, I am
                </Button>
                <Button
                  variant={usingAIMonitoring === false ? "default" : "outline"}
                  onClick={() => setUsingAIMonitoring(false)}
                  className={cn(
                    "flex-1",
                    usingAIMonitoring === false && "bg-purple-600 hover:bg-purple-700"
                  )}
                >
                  No, this is new
                </Button>
              </div>
            </div>
          </div>
        );

      case 3:
        return (
          <div className="space-y-6">
            {/* Domain URL */}
            <div className="space-y-2">
              <Label htmlFor="domain-url">
                Domain URL <span className="text-red-500">*</span>
              </Label>
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
                  const pastedText = e.clipboardData.getData("text");
                  const cleaned = cleanDomainInput(pastedText);
                  if (cleaned !== pastedText) {
                    e.preventDefault();
                    setNewDomain(cleaned);
                  }
                }}
                className="h-12"
              />
            </div>

            {/* Brand Name */}
            <div className="space-y-2">
              <Label htmlFor="brand-name">
                Brand Name <span className="text-red-500">*</span>
              </Label>
              <Input
                id="brand-name"
                placeholder="Enter official brand name (e.g., Acme Inc)"
                value={newBrandName}
                onChange={(e) => setNewBrandName(e.target.value)}
                className="h-12"
              />
            </div>

            {/* Country Selector - Searchable */}
            <div className="space-y-2">
              <Label htmlFor="domain-country">Target Country</Label>
              <Popover open={countryDropdownOpen} onOpenChange={setCountryDropdownOpen}>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    role="combobox"
                    aria-expanded={countryDropdownOpen}
                    className="w-full justify-between h-12"
                    id="domain-country"
                  >
                    {selectedCountry
                      ? selectedCountry.label
                      : "Select primary country for this brand"}
                    <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent
                  className="w-[var(--radix-popover-trigger-width)] p-0 z-[200]"
                  align="start"
                  sideOffset={4}
                >
                  <Command>
                    <CommandInput placeholder="Search country..." />
                    <CommandList className="max-h-[300px]">
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

            {/* AI-Powered Analysis Info */}
            <div className="space-y-3 bg-purple-50 p-4 rounded-lg border border-purple-100">
              <div className="flex items-start gap-2">
                <Sparkles className="h-5 w-5 text-purple-600 mt-0.5" />
                <div className="space-y-2">
                  <Label className="text-base">AI-Powered Analysis</Label>
                  <p className="text-sm text-gray-600">
                    We'll automatically analyze your brand and identify relevant industry niches,
                    prompts, competitors, and content opportunities.
                  </p>
                  <p className="text-xs text-gray-500 italic">
                    Tip: Connect Google Search Console later for more accurate audience insights
                    and prompt data.
                  </p>
                </div>
              </div>
            </div>
          </div>
        );

      case 4:
        return (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              {!useManualKeywords ? (
                <>
                  <div>
                    <h3 className="text-lg font-semibold">Generated Prompts</h3>
                    <div className="flex items-center gap-3 mt-1">
                      <p className="text-sm text-gray-500">
                        {generatedKeywords.length} prompts in{" "}
                        {
                          Object.keys(
                            generatedKeywords.reduce((acc: any, kw: any) => {
                              const topic = kw.topic || "Other";
                              acc[topic] = true;
                              return acc;
                            }, {})
                          ).length
                        }{" "}
                        topics
                      </p>
                      <Badge variant="default" className="gap-1.5 bg-purple-600">
                        {selectedTopics.size} topics selected
                      </Badge>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="flex items-center space-x-2 bg-gray-100 px-3 py-2 rounded-lg border border-gray-200">
                      <Checkbox
                        id="ignoreBrandKeywords"
                        checked={ignoreBrandKeywords}
                        onCheckedChange={(checked) => setIgnoreBrandKeywords(checked as boolean)}
                      />
                      <label
                        htmlFor="ignoreBrandKeywords"
                        className="text-sm font-medium leading-none cursor-pointer"
                      >
                        Ignore Brand Prompts
                      </label>
                    </div>
                  </div>
                </>
              ) : (
                <div>
                  <h3 className="text-lg font-semibold">Manual Prompts</h3>
                  <p className="text-sm text-gray-500 mt-1">Enter prompts separated by commas</p>
                </div>
              )}
            </div>

            {!useManualKeywords ? (
              <>
                {/* Search Input */}
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <Input
                    placeholder="Search prompts..."
                    value={keywordSearchQuery}
                    onChange={(e) => setKeywordSearchQuery(e.target.value)}
                    className="pl-9"
                  />
                </div>

                {/* Prompts Grouped by Topic */}
                <div className="space-y-4 max-h-[350px] overflow-y-auto pr-2">
                  {Object.entries(
                    generatedKeywords
                      .map((keyword, index) => ({ keyword, index }))
                      .filter(({ keyword }) => {
                        const matchesSearch =
                          keywordSearchQuery === "" ||
                          keyword.keyword
                            .toLowerCase()
                            .includes(keywordSearchQuery.toLowerCase()) ||
                          (keyword.topic &&
                            keyword.topic
                              .toLowerCase()
                              .includes(keywordSearchQuery.toLowerCase())) ||
                          (keyword.entity &&
                            keyword.entity
                              .toLowerCase()
                              .includes(keywordSearchQuery.toLowerCase()));

                        const brandName =
                          newBrandName ||
                          newDomain.replace(/^(https?:\/\/)?(www\.)?/, "").split(".")[0];
                        const containsBrandName =
                          ignoreBrandKeywords &&
                          brandName &&
                          keyword.keyword.toLowerCase().includes(brandName.toLowerCase());

                        return matchesSearch && !containsBrandName;
                      })
                      .reduce((acc: any, { keyword, index }) => {
                        const topic = keyword.topic || "Other";
                        if (!acc[topic]) acc[topic] = [];
                        acc[topic].push({ keyword, index });
                        return acc;
                      }, {})
                  ).map(([topic, items]: [string, any]) => {
                    const topicItems = items as Array<{ keyword: any; index: number }>;
                    const isTopicSelected = selectedTopics.has(topic);

                    return (
                      <div
                        key={topic}
                        className={cn(
                          "rounded-lg bg-white cursor-pointer transition-all border",
                          isTopicSelected ? "border-purple-500" : "border-gray-200"
                        )}
                        onClick={() => {
                          setSelectedTopics((prev) => {
                            const newSet = new Set(prev);
                            if (newSet.has(topic)) {
                              newSet.delete(topic);
                            } else {
                              newSet.add(topic);
                            }
                            return newSet;
                          });
                        }}
                      >
                        <div className="border-b border-gray-100 p-4">
                          <div className="flex items-center gap-3">
                            <Checkbox
                              checked={isTopicSelected}
                              onCheckedChange={() => {
                                setSelectedTopics((prev) => {
                                  const newSet = new Set(prev);
                                  if (newSet.has(topic)) {
                                    newSet.delete(topic);
                                  } else {
                                    newSet.add(topic);
                                  }
                                  return newSet;
                                });
                              }}
                              onClick={(e) => e.stopPropagation()}
                            />
                            <div className="flex-1">
                              <h4 className="font-semibold">Topic: {topic}</h4>
                              <p className="text-xs text-gray-500 mt-1">
                                {topicItems.length} prompts in this topic
                              </p>
                            </div>
                          </div>
                        </div>
                        <div className="p-2">
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead className="w-[250px]">Prompt Intent</TableHead>
                                <TableHead className="w-[130px]">Intent</TableHead>
                                <TableHead className="w-[130px]">Entity</TableHead>
                                <TableHead className="w-[120px]">Volume</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {topicItems.map(({ keyword, index }) => {
                                return (
                                  <TableRow key={index}>
                                    <TableCell className="font-medium">{keyword.keyword}</TableCell>
                                    <TableCell>
                                      <span className="text-sm capitalize">
                                        {keyword.intent || "N/A"}
                                      </span>
                                    </TableCell>
                                    <TableCell>
                                      <span className="text-sm text-gray-500">
                                        {keyword.entity || "N/A"}
                                      </span>
                                    </TableCell>
                                    <TableCell>
                                      <Badge
                                        variant={
                                          keyword.volume_level === "very-high" ||
                                          keyword.volume_level === "high"
                                            ? "default"
                                            : "secondary"
                                        }
                                        className="text-xs whitespace-nowrap"
                                      >
                                        {keyword.volume_level || "N/A"}
                                      </Badge>
                                    </TableCell>
                                  </TableRow>
                                );
                              })}
                            </TableBody>
                          </Table>
                        </div>
                      </div>
                    );
                  })}
                </div>

                <p className="text-xs text-gray-500">
                  Selected prompts will be saved when you create the domain. You can edit them
                  later from domain settings.
                </p>
              </>
            ) : (
              <>
                {/* Manual Prompt Input */}
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="manualKeywords">Prompts (comma separated, max 10)</Label>
                    <Textarea
                      id="manualKeywords"
                      placeholder="how to build mobile apps, app design tips, iOS development tutorial..."
                      value={keywordInput}
                      onChange={(e) => setKeywordInput(e.target.value)}
                      className="min-h-[200px] mt-2"
                    />
                    <p className="text-xs text-gray-500 mt-2">
                      Enter up to 10 prompts separated by commas. These will be added as primary
                      prompts.
                    </p>
                  </div>
                </div>
              </>
            )}
          </div>
        );

      default:
        return null;
    }
  };

  const getStepTitle = () => {
    switch (wizardStep) {
      case 1:
        return "Tell us about your organization";
      case 2:
        return "What are your goals?";
      case 3:
        return "Add your first domain";
      case 4:
        return "Select prompt intents";
      default:
        return "";
    }
  };

  const getStepDescription = () => {
    switch (wizardStep) {
      case 1:
        return "This helps us personalize your AI visibility experience";
      case 2:
        return "Select what you want to achieve with PromptMaxx";
      case 3:
        return "Enter your domain details and we'll analyze your brand";
      case 4:
        return "Choose the prompts you want to track for your brand";
      default:
        return "";
    }
  };

  // Get displayed step number for invited users (1-2) vs regular users (1-4)
  const getDisplayedStep = () => {
    if (hasExistingOrganization) {
      return wizardStep - 2; // 3->1, 4->2
    }
    return wizardStep;
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center overflow-hidden">
      {/* Purple gradient background */}
      <div className="absolute inset-0 bg-gradient-to-br from-purple-600 via-purple-500 to-indigo-600" />

      {/* Content card */}
      <div className="relative w-full max-w-4xl mx-4 bg-white rounded-3xl shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
        {isAutomatedOnboarding ? (
          // Loading Modal with Progress Messages
          <div className="py-16 px-8">
            <div className="flex flex-col items-center justify-center space-y-6">
              {/* Animated GIF */}
              <div className="w-24 h-24 flex items-center justify-center">
                <img
                  src={new URL("../assets/flask.gif", import.meta.url).href}
                  alt="Processing..."
                  className="w-full h-full object-contain"
                />
              </div>

              {/* Progress Message */}
              <div className="text-center space-y-3">
                <h3 className="text-xl font-semibold text-gray-900">
                  Setting up your brand monitoring...
                </h3>
                <p className="text-sm text-gray-500 animate-pulse">
                  {progressMessages[onboardingProgress]}
                </p>
              </div>

              {/* Progress Indicator */}
              <div className="w-full max-w-md space-y-2">
                <div className="flex justify-between text-xs text-gray-500">
                  <span>
                    Step {onboardingProgress + 1} of {progressMessages.length}
                  </span>
                  <span>
                    {Math.round(((onboardingProgress + 1) / progressMessages.length) * 100)}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-purple-600 h-2 rounded-full transition-all duration-500"
                    style={{
                      width: `${((onboardingProgress + 1) / progressMessages.length) * 100}%`,
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
        ) : (
          <>
            {/* Header */}
            <div className="p-6 border-b border-gray-100">
              <div className="flex items-center gap-2">
                <Badge variant="secondary" className="text-purple-600 bg-purple-100">
                  Onboarding
                </Badge>
                <Badge variant="outline">Step {getDisplayedStep()} of {totalSteps}</Badge>
              </div>
              <h1 className="text-2xl font-bold text-gray-900 mt-3">{getStepTitle()}</h1>
              <p className="text-gray-500 mt-1">{getStepDescription()}</p>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">{renderStepContent()}</div>

            {/* Footer */}
            <div className="p-6 border-t border-gray-100">
              {/* Progress dots */}
              <div className="flex justify-center gap-2 mb-4">
                {Array.from({ length: totalSteps }).map((_, i) => {
                  const displayedStep = getDisplayedStep();
                  return (
                    <div
                      key={i}
                      className={cn(
                        "h-2 rounded-full transition-all",
                        i + 1 === displayedStep
                          ? "bg-purple-600 w-8"
                          : i + 1 < displayedStep
                          ? "bg-purple-600 w-2"
                          : "bg-gray-200 w-2"
                      )}
                    />
                  );
                })}
              </div>

              <div className="flex items-center gap-3">
                {/* Show Back button only if not at the first step (considering invited users start at step 3) */}
                {((hasExistingOrganization && wizardStep > 3) || (!hasExistingOrganization && wizardStep > 1)) && (
                  <Button variant="outline" onClick={handleBack}>
                    <ChevronLeft className="h-4 w-4 mr-2" />
                    Back
                  </Button>
                )}

                {wizardStep === 4 && (
                  <Button
                    variant="outline"
                    onClick={() => setUseManualKeywords(!useManualKeywords)}
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    {useManualKeywords ? "Use AI Prompts" : "Add Manually"}
                  </Button>
                )}

                <div className="flex-1" />

                {wizardStep < 3 && (
                  <Button
                    onClick={handleNext}
                    disabled={!canProceed()}
                    className="bg-purple-600 hover:bg-purple-700"
                  >
                    Continue
                    <ChevronRight className="h-4 w-4 ml-2" />
                  </Button>
                )}

                {wizardStep === 3 && (
                  <Button
                    onClick={handleGenerateKeywords}
                    disabled={!canProceed() || isGeneratingKeywords}
                    className="bg-purple-600 hover:bg-purple-700"
                  >
                    {isGeneratingKeywords ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Generating...
                      </>
                    ) : (
                      <>
                        <Sparkles className="h-4 w-4 mr-2" />
                        Generate Keywords
                        <ChevronRight className="h-4 w-4 ml-2" />
                      </>
                    )}
                  </Button>
                )}

                {wizardStep === 4 && (
                  <Button
                    onClick={handleAddDomain}
                    disabled={isLoading || !canProceed()}
                    className="bg-purple-600 hover:bg-purple-700"
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        Creating...
                      </>
                    ) : (
                      <>
                        Complete Setup
                        <ChevronRight className="h-4 w-4 ml-2" />
                      </>
                    )}
                  </Button>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
