import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/services/api";
import { Plus, Trash2, Globe, Mail, Shield, User, Crown, Settings, Link2, CheckCircle2, AlertCircle, Loader2, X, Check, ChevronDown, Upload, Sparkles, ChevronRight, ChevronLeft, Search, Activity } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import { cn } from "@/lib/utils";
import { ProjectAccessManager } from "@/components/ProjectAccessManager";
import { PageLoader } from "@/components/PageLoader";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import { getFaviconUrl, handleFaviconError } from "@/utils/faviconHelper";

export default function OrganizationSettings() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user } = useAuth();

  // Organization state
  const [organization, setOrganization] = useState({
    id: 0,
    name: "",
    industry: "",
    team_count: 0,
    created_at: "",
    modified_at: "",
  });

  // Domains state
  const [domains, setDomains] = useState<Array<{
    id: number;
    name: string;
    url: string;
    organisation: number;
    total_mentions: number;
    total_citations: number;
    visibility_score: string;
    average_position: string;
    active_alerts: number;
    sentiment: string;
    sentiment_score: string;
    created_at: string;
    modified_at: string;
    processing_status?: string;
    track_message?: string;
  }>>([]);

  const [newDomain, setNewDomain] = useState("");
  const [newBrandName, setNewBrandName] = useState("");
  const [newDomainCountry, setNewDomainCountry] = useState("us");
  const [newDomainKeywords, setNewDomainKeywords] = useState<string[]>([]);
  const [keywordInput, setKeywordInput] = useState("");
  const [isFetchingKeywords, setIsFetchingKeywords] = useState(false);

  // Wizard state
  const [wizardStep, setWizardStep] = useState(1);

  // Niche state
  const [suggestedNiches, setSuggestedNiches] = useState<string[]>([]);
  const [selectedNiches, setSelectedNiches] = useState<string[]>([]);
  const [isFetchingNiches, setIsFetchingNiches] = useState(false);

  // Semantic keyword state
  const [generatedKeywords, setGeneratedKeywords] = useState<any[]>([]);
  const [selectedKeywordIndices, setSelectedKeywordIndices] = useState<Set<number>>(new Set());
  const [isGeneratingKeywords, setIsGeneratingKeywords] = useState(false);
  const [keywordSearchQuery, setKeywordSearchQuery] = useState("");
  const [useManualKeywords, setUseManualKeywords] = useState(false);
  const [ignoreBrandKeywords, setIgnoreBrandKeywords] = useState(false);

  // Automated onboarding state
  const [isAutomatedOnboarding, setIsAutomatedOnboarding] = useState(false);
  const [onboardingProgress, setOnboardingProgress] = useState(0);
  const [createdDomainId, setCreatedDomainId] = useState<number | null>(null);

  // Topic-level selection state
  const [selectedTopics, setSelectedTopics] = useState<Set<string>>(new Set());

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
    "Preparing your brand monitoring dashboard"
  ];

  // Team members state
  const [teamMembers, setTeamMembers] = useState<Array<{
    id: number;
    email: string;
    first_name: string;
    last_name: string;
    role: 'admin' | 'user';
    organisation: number;
    organisation_name: string;
    is_active: boolean;
    created_at: string;
    modified_at: string;
  }>>([]);
  const [invitations, setInvitations] = useState<Array<{
    id: string;
    email: string;
    role: 'admin' | 'user';
    status: 'pending' | 'accepted' | 'declined' | 'expired';
    invited_by: number;
    invited_by_email: string;
    expires_at: string;
    accepted_at?: string | null;
    created_at: string;
  }>>([]);

  // Tab state
  const [selectedTab, setSelectedTab] = useState("domains");

  // Profile state
  const [profileData, setProfileData] = useState({
    first_name: "",
    last_name: "",
  });
  const [isUpdatingProfile, setIsUpdatingProfile] = useState(false);

  // Pagination state for domains
  const [domainPage, setDomainPage] = useState(1);
  const [domainTotalCount, setDomainTotalCount] = useState(0);
  const [isLoadingMoreDomains, setIsLoadingMoreDomains] = useState(false);
  const [domainSearchQuery, setDomainSearchQuery] = useState("");
  const DOMAINS_PAGE_SIZE = 20;

  // Loading states
  const [isLoading, setIsLoading] = useState(true);
  const [isUpdatingOrg, setIsUpdatingOrg] = useState(false);
  const [isAddingDomain, setIsAddingDomain] = useState(false);
  const [isUpdatingMember, setIsUpdatingMember] = useState<number | null>(null);
  // Confirm dialogs
  const [confirmDomainId, setConfirmDomainId] = useState<number | null>(null);
  const [confirmMemberId, setConfirmMemberId] = useState<number | null>(null);
  const [confirmInvitationId, setConfirmInvitationId] = useState<string | null>(null);

  // Dialog states
  const [inviteDialogOpen, setInviteDialogOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<"admin" | "user">("user");
  const roleMeta: Record<"admin" | "user", { label: string; description: string }> = {
    user: { label: "User", description: "Can view and manage brand monitoring" },
    admin: { label: "Admin", description: "Full access including team management" },
  };
  const [addDomainDialogOpen, setAddDomainDialogOpen] = useState(false);
  const [addKeywordsDialogOpen, setAddKeywordsDialogOpen] = useState(false);
  const [selectedDomainForKeywords, setSelectedDomainForKeywords] = useState<number | null>(null);
  const [newKeywordsInput, setNewKeywordsInput] = useState("");
  const [newKeywordsList, setNewKeywordsList] = useState<string[]>([]);
  const [isAddingKeywords, setIsAddingKeywords] = useState(false);
  const [countryDropdownOpen, setCountryDropdownOpen] = useState(false);

  // Team members search and pagination
  const [teamSearchQuery, setTeamSearchQuery] = useState("");
  const TEAM_PAGE_SIZE = 20;
  const [teamVisibleCount, setTeamVisibleCount] = useState(TEAM_PAGE_SIZE);

  // Project Access Manager states
  const [projectAccessDialogOpen, setProjectAccessDialogOpen] = useState(false);
  const [selectedMemberForAccess, setSelectedMemberForAccess] = useState<{
    id: number;
    name: string;
    email: string;
  } | null>(null);

  // Mock integrations data (keeping for now)
  const [integrations, setIntegrations] = useState([
    {
      id: "1",
      domainId: "1",
      domain: "acme.com",
      type: "google_analytics" as const,
      propertyId: "GA-123456789",
      connectedAt: "2024-01-20",
      status: "active" as const,
      lastSync: "2024-03-14T10:30:00Z"
    },
  ]);

  const [connectIntegrationDialog, setConnectIntegrationDialog] = useState(false);
  const [selectedDomainForIntegration, setSelectedDomainForIntegration] = useState("");
  const [integrationType, setIntegrationType] = useState<"google_analytics" | "search_console">("google_analytics");

  // Load data on component mount
  useEffect(() => {
    loadData();
  }, []);

  // Poll for domain updates when there are processing domains
  useEffect(() => {
    const hasProcessingDomains = domains.some(d =>
      d.processing_status && ['INIT', 'SCHD', 'PROC'].includes(d.processing_status)
    );

    if (!hasProcessingDomains) return;

    const interval = setInterval(async () => {
      // Reload all currently loaded pages during polling
      try {
        const totalPages = domainPage;
        const data = await apiClient.getDomains({ page: '1', page_size: String(totalPages * DOMAINS_PAGE_SIZE) });
        setDomains(data.domains);
        setDomainTotalCount(data.total_count ?? data.domains.length);
      } catch (error) {
        console.error("Error polling domains:", error);
      }
    }, 10000); // Poll every 10 seconds

    return () => clearInterval(interval);
  }, [domains]);

  // Cycle through progress messages during automated onboarding
  useEffect(() => {
    if (!isAutomatedOnboarding) return;

    const interval = setInterval(() => {
      setOnboardingProgress((prev) => {
        // Keep showing the last message until processing is complete
        if (prev < progressMessages.length - 1) {
          return prev + 1;
        }
        return prev;
      });
    }, 4500); // Change message every 4.5 seconds

    return () => clearInterval(interval);
  }, [isAutomatedOnboarding, progressMessages.length]);

  // Initialize profile data from user
  useEffect(() => {
    if (user) {
      setProfileData({
        first_name: user.first_name || "",
        last_name: user.last_name || "",
      });
    }
  }, [user]);

  const loadData = async () => {
    try {
      setIsLoading(true);
      await Promise.all([
        loadOrganization(),
        loadDomains(),
        loadTeamMembers(),
      ]);
    } catch (error) {
      toast({
        title: "Error loading data",
        description: "Failed to load organization data. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const loadOrganization = async () => {
    try {
      const data = await apiClient.getOrganization();
      setOrganization(data);
    } catch (error) {
      console.error("Error loading organization:", error);
    }
  };

  const loadDomains = async (page: number = 1, append: boolean = false) => {
    try {
      const data = await apiClient.getDomains({ page: String(page), page_size: String(DOMAINS_PAGE_SIZE) });
      if (append) {
        setDomains(prev => [...prev, ...data.domains]);
      } else {
        setDomains(data.domains);
      }
      setDomainTotalCount(data.total_count ?? data.domains.length);
      setDomainPage(page);
    } catch (error) {
      console.error("Error loading domains:", error);
    }
  };

  const loadMoreDomains = async () => {
    try {
      setIsLoadingMoreDomains(true);
      await loadDomains(domainPage + 1, true);
    } finally {
      setIsLoadingMoreDomains(false);
    }
  };

  const loadTeamMembers = async () => {
    try {
      const data = await apiClient.getTeamMembers();
      // Exclude any super_admin accounts from team management UI
      const filtered = (data.members || []).filter((m: any) => m.role !== 'super_admin');
      setTeamMembers(filtered);
      setInvitations(data.invitations || []);
    } catch (error) {
      console.error("Error loading team members:", error);
    }
  };

  const MAX_KEYWORD_LENGTH = 255;

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

  const selectedCountry = countries.find(c => c.value === newDomainCountry);

  const cleanDomainInput = (input: string): string => {
    if (!input.trim()) return input;

    try {
      // Remove everything after the first slash (including query params, fragments, etc.)
      let cleaned = input.trim();

      // Remove protocol if present (https:// or http://)
      cleaned = cleaned.replace(/^https?:\/\//i, '');

      // Remove www. prefix (optional - you can remove this line if you want to keep www)
      // cleaned = cleaned.replace(/^www\./i, '');

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

  const handleFetchBrandNiches = async () => {
    if (!newDomain.trim() && !newBrandName.trim()) {
      toast({
        title: "Domain or brand name required",
        description: "Please enter a domain name or brand name first.",
        variant: "destructive",
      });
      return;
    }

    try {
      setIsFetchingNiches(true);
      const response: any = await apiClient.fetchBrandNiches(
        newDomain.trim(),
        newBrandName.trim()
      );

      if (response.success && response.niches) {
        setSuggestedNiches(response.niches);
        setSelectedNiches([]); // Reset selected niches
      } else {
        toast({
          title: "Failed to fetch niches",
          description: "Could not retrieve brand niches. Please try again.",
          variant: "destructive",
        });
      }
    } catch (error: any) {
      toast({
        title: "Error fetching niches",
        description: error.message || "Failed to fetch brand niches from AI.",
        variant: "destructive",
      });
    } finally {
      setIsFetchingNiches(false);
    }
  };

  const handleToggleNiche = (niche: string) => {
    setSelectedNiches((prev) => {
      if (prev.includes(niche)) {
        return prev.filter((n) => n !== niche);
      } else {
        return [...prev, niche];
      }
    });
  };

  const handleGenerateKeywords = async () => {
    try {
      setIsGeneratingKeywords(true);
      setIsAutomatedOnboarding(true);
      setOnboardingProgress(0);

      // Track animation start time
      const animationStartTime = Date.now();
      const TOTAL_ANIMATION_DURATION = 10 * 4500; // 10 messages * 4.5 seconds each = 45 seconds

      // Find the selected country name
      const selectedCountryObj = countries.find(c => c.value === newDomainCountry);
      const countryName = selectedCountryObj ? selectedCountryObj.label : 'United States';

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
          console.error('Error fetching niches:', error);
          // Continue without niches
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
        // Keep all keywords unselected by default
        setSelectedKeywordIndices(new Set());

        // Calculate remaining animation time
        const elapsedTime = Date.now() - animationStartTime;
        const remainingTime = Math.max(0, TOTAL_ANIMATION_DURATION - elapsedTime);

        // Wait for remaining animation time before showing Step 2
        setTimeout(() => {
          setIsAutomatedOnboarding(false);
          setOnboardingProgress(0);
          setWizardStep(2);
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

  const handleToggleKeyword = (index: number) => {
    setSelectedKeywordIndices((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  const handleSelectAllKeywords = () => {
    const allIndices = new Set(generatedKeywords.map((_: any, index: number) => index));
    setSelectedKeywordIndices(allIndices);
  };

  const handleDeselectAllKeywords = () => {
    setSelectedKeywordIndices(new Set());
  };

  const handleAddKeyword = () => {
    const trimmedInput = keywordInput.trim();
    if (!trimmedInput) return;

    // Split by comma, normalize to lowercase, trim whitespace, validate length
    const newKeywords = trimmedInput
      .split(',')
      .map(k => k.trim().toLowerCase())
      .filter(k => {
        if (k.length === 0) return false;
        if (k.length > MAX_KEYWORD_LENGTH) {
          toast({
            title: "Keyword too long",
            description: `"${k}" exceeds ${MAX_KEYWORD_LENGTH} characters. Please shorten it.`,
            variant: "destructive",
          });
          return false;
        }
        return true;
      })
      .filter(k => !newDomainKeywords.includes(k)); // Remove duplicates

    if (newKeywords.length > 0) {
      setNewDomainKeywords([...newDomainKeywords, ...newKeywords]);
      setKeywordInput("");
    } else {
      // Check if all were duplicates or invalid
      const validKeywords = trimmedInput
        .split(',')
        .map(k => k.trim().toLowerCase())
        .filter(k => k.length > 0 && k.length <= MAX_KEYWORD_LENGTH);
      
      if (validKeywords.length > 0 && validKeywords.every(k => newDomainKeywords.includes(k))) {
        toast({
          title: "Duplicate keywords",
          description: "These keywords are already added.",
          variant: "default",
        });
      }
    }
  };

  const handleRemoveKeyword = (keyword: string) => {
    setNewDomainKeywords(newDomainKeywords.filter(k => k !== keyword));
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const fileName = file.name.toLowerCase();
    const isCSV = fileName.endsWith('.csv');
    const isXLSX = fileName.endsWith('.xlsx') || fileName.endsWith('.xls');

    if (!isCSV && !isXLSX) {
      toast({
        title: "Invalid file type",
        description: "Please upload a CSV or XLSX file.",
        variant: "destructive",
      });
      return;
    }

    try {
      let keywords: string[] = [];

      if (isCSV) {
        // Parse CSV file
        const text = await file.text();
        // Split by newlines
        const lines = text.split(/\r?\n/);
        for (const line of lines) {
          if (!line.trim()) continue;
          // Split by comma, handling quoted values
          const values: string[] = [];
          let current = '';
          let inQuotes = false;
          
          for (let i = 0; i < line.length; i++) {
            const char = line[i];
            if (char === '"') {
              inQuotes = !inQuotes;
            } else if (char === ',' && !inQuotes) {
              values.push(current.trim());
              current = '';
            } else {
              current += char;
            }
          }
          values.push(current.trim()); // Add last value
          
          // Process each value
          for (const value of values) {
            const cleaned = value.replace(/^"|"$/g, '').trim().toLowerCase();
            if (cleaned && cleaned.length <= MAX_KEYWORD_LENGTH) {
              keywords.push(cleaned);
            }
          }
        }
      } else if (isXLSX) {
        // Parse XLSX file
        try {
          // Dynamic import for xlsx library
          const XLSX = await import('xlsx');
          const arrayBuffer = await file.arrayBuffer();
          const workbook = XLSX.read(arrayBuffer, { type: 'array' });
          const firstSheetName = workbook.SheetNames[0];
          const worksheet = workbook.Sheets[firstSheetName];
          const data = XLSX.utils.sheet_to_json(worksheet, { header: 1, defval: '' });
          
          // Extract keywords from all cells
          for (const row of data) {
            if (Array.isArray(row)) {
              for (const cell of row) {
                if (cell && typeof cell === 'string') {
                  const cleaned = cell.trim().toLowerCase();
                  if (cleaned && cleaned.length <= MAX_KEYWORD_LENGTH) {
                    keywords.push(cleaned);
                  }
                } else if (typeof cell === 'number') {
                  const cleaned = String(cell).trim().toLowerCase();
                  if (cleaned && cleaned.length <= MAX_KEYWORD_LENGTH) {
                    keywords.push(cleaned);
                  }
                }
              }
            }
          }
        } catch (xlsxError: any) {
          toast({
            title: "XLSX parsing error",
            description: xlsxError?.message || "Failed to parse XLSX file. Please check the file format and try again.",
            variant: "destructive",
          });
          return;
        }
      }

      // Remove duplicates and empty values
      const uniqueKeywords = [...new Set(keywords.filter(k => k.length > 0))];
      
      // Check maximum limit (100 keywords per upload)
      const MAX_KEYWORDS_PER_UPLOAD = 100;
      if (uniqueKeywords.length > MAX_KEYWORDS_PER_UPLOAD) {
        toast({
          title: "Too many keywords",
          description: `File contains ${uniqueKeywords.length} keywords. Maximum ${MAX_KEYWORDS_PER_UPLOAD} keywords allowed per upload. Please split your file into smaller batches.`,
          variant: "destructive",
        });
        return;
      }
      
      // Filter out keywords that are already added
      const newKeywords = uniqueKeywords.filter(k => !newDomainKeywords.includes(k));

      if (newKeywords.length === 0) {
        toast({
          title: "No new keywords",
          description: "All keywords from the file are already added or the file is empty.",
          variant: "default",
        });
        return;
      }

      // Check if adding these keywords would exceed the total limit
      const totalAfterAdd = newDomainKeywords.length + newKeywords.length;
      if (totalAfterAdd > MAX_KEYWORDS_PER_UPLOAD) {
        const canAdd = MAX_KEYWORDS_PER_UPLOAD - newDomainKeywords.length;
        if (canAdd <= 0) {
          toast({
            title: "Keyword limit reached",
            description: `You have already added ${newDomainKeywords.length} keywords. Maximum ${MAX_KEYWORDS_PER_UPLOAD} keywords allowed. Please remove some keywords before adding more.`,
            variant: "destructive",
          });
          return;
        } else {
          // Add only what we can
          const keywordsToAdd = newKeywords.slice(0, canAdd);
          setNewDomainKeywords([...newDomainKeywords, ...keywordsToAdd]);
          toast({
            title: "Partial upload",
            description: `Added ${keywordsToAdd.length} keyword(s) from ${file.name}. You already have ${newDomainKeywords.length} keywords. Maximum ${MAX_KEYWORDS_PER_UPLOAD} keywords allowed.`,
            variant: "default",
          });
          return;
        }
      }

      // Add new keywords
      setNewDomainKeywords([...newDomainKeywords, ...newKeywords]);
      
      toast({
        title: "Keywords uploaded",
        description: `Added ${newKeywords.length} keyword(s) from ${file.name}`,
        variant: "default",
      });
    } catch (error: any) {
      toast({
        title: "Upload error",
        description: error.message || "Failed to process the file. Please try again.",
        variant: "destructive",
      });
    } finally {
      // Reset file input
      event.target.value = '';
    }
  };

  const handleOpenAddKeywordsDialog = (domainId: number) => {
    setSelectedDomainForKeywords(domainId);
    setNewKeywordsInput("");
    setNewKeywordsList([]);
    setAddKeywordsDialogOpen(true);
  };

  const handleAddKeywordToExisting = () => {
    const trimmedInput = newKeywordsInput.trim();
    if (!trimmedInput) return;

    // Split by comma, normalize to lowercase, trim whitespace, validate length
    const newKeywords = trimmedInput
      .split(',')
      .map(k => k.trim().toLowerCase())
      .filter(k => {
        if (k.length === 0) return false;
        if (k.length > MAX_KEYWORD_LENGTH) {
          toast({
            title: "Keyword too long",
            description: `"${k}" exceeds ${MAX_KEYWORD_LENGTH} characters. Please shorten it.`,
            variant: "destructive",
          });
          return false;
        }
        return true;
      })
      .filter(k => !newKeywordsList.includes(k)); // Remove duplicates

    if (newKeywords.length > 0) {
      setNewKeywordsList([...newKeywordsList, ...newKeywords]);
      setNewKeywordsInput("");
    } else {
      // Check if all were duplicates or invalid
      const validKeywords = trimmedInput
        .split(',')
        .map(k => k.trim().toLowerCase())
        .filter(k => k.length > 0 && k.length <= MAX_KEYWORD_LENGTH);
      
      if (validKeywords.length > 0 && validKeywords.every(k => newKeywordsList.includes(k))) {
        toast({
          title: "Duplicate keywords",
          description: "These keywords are already added.",
          variant: "default",
        });
      }
    }
  };

  const handleRemoveKeywordFromExisting = (keyword: string) => {
    setNewKeywordsList(newKeywordsList.filter(k => k !== keyword));
  };

  const handleFileUploadForExisting = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const fileName = file.name.toLowerCase();
    const isCSV = fileName.endsWith('.csv');
    const isXLSX = fileName.endsWith('.xlsx') || fileName.endsWith('.xls');

    if (!isCSV && !isXLSX) {
      toast({
        title: "Invalid file type",
        description: "Please upload a CSV or XLSX file.",
        variant: "destructive",
      });
      return;
    }

    try {
      let keywords: string[] = [];

      if (isCSV) {
        // Parse CSV file
        const text = await file.text();
        // Split by newlines
        const lines = text.split(/\r?\n/);
        for (const line of lines) {
          if (!line.trim()) continue;
          // Split by comma, handling quoted values
          const values: string[] = [];
          let current = '';
          let inQuotes = false;
          
          for (let i = 0; i < line.length; i++) {
            const char = line[i];
            if (char === '"') {
              inQuotes = !inQuotes;
            } else if (char === ',' && !inQuotes) {
              values.push(current.trim());
              current = '';
            } else {
              current += char;
            }
          }
          values.push(current.trim()); // Add last value
          
          // Process each value
          for (const value of values) {
            const cleaned = value.replace(/^"|"$/g, '').trim().toLowerCase();
            if (cleaned && cleaned.length <= MAX_KEYWORD_LENGTH) {
              keywords.push(cleaned);
            }
          }
        }
      } else if (isXLSX) {
        // Parse XLSX file
        try {
          // Dynamic import for xlsx library
          const XLSX = await import('xlsx');
          const arrayBuffer = await file.arrayBuffer();
          const workbook = XLSX.read(arrayBuffer, { type: 'array' });
          const firstSheetName = workbook.SheetNames[0];
          const worksheet = workbook.Sheets[firstSheetName];
          const data = XLSX.utils.sheet_to_json(worksheet, { header: 1, defval: '' });
          
          // Extract keywords from all cells
          for (const row of data) {
            if (Array.isArray(row)) {
              for (const cell of row) {
                if (cell && typeof cell === 'string') {
                  const cleaned = cell.trim().toLowerCase();
                  if (cleaned && cleaned.length <= MAX_KEYWORD_LENGTH) {
                    keywords.push(cleaned);
                  }
                } else if (typeof cell === 'number') {
                  const cleaned = String(cell).trim().toLowerCase();
                  if (cleaned && cleaned.length <= MAX_KEYWORD_LENGTH) {
                    keywords.push(cleaned);
                  }
                }
              }
            }
          }
        } catch (xlsxError: any) {
          toast({
            title: "XLSX parsing error",
            description: xlsxError?.message || "Failed to parse XLSX file. Please check the file format and try again.",
            variant: "destructive",
          });
          return;
        }
      }

      // Remove duplicates and empty values
      const uniqueKeywords = [...new Set(keywords.filter(k => k.length > 0))];
      
      // Check maximum limit (100 keywords per upload)
      const MAX_KEYWORDS_PER_UPLOAD = 100;
      if (uniqueKeywords.length > MAX_KEYWORDS_PER_UPLOAD) {
        toast({
          title: "Too many keywords",
          description: `File contains ${uniqueKeywords.length} keywords. Maximum ${MAX_KEYWORDS_PER_UPLOAD} keywords allowed per upload. Please split your file into smaller batches.`,
          variant: "destructive",
        });
        return;
      }
      
      // Filter out keywords that are already added
      const newKeywords = uniqueKeywords.filter(k => !newKeywordsList.includes(k));

      if (newKeywords.length === 0) {
        toast({
          title: "No new keywords",
          description: "All keywords from the file are already added or the file is empty.",
          variant: "default",
        });
        return;
      }

      // Check if adding these keywords would exceed the total limit
      const totalAfterAdd = newKeywordsList.length + newKeywords.length;
      if (totalAfterAdd > MAX_KEYWORDS_PER_UPLOAD) {
        const canAdd = MAX_KEYWORDS_PER_UPLOAD - newKeywordsList.length;
        if (canAdd <= 0) {
          toast({
            title: "Keyword limit reached",
            description: `You have already added ${newKeywordsList.length} keywords. Maximum ${MAX_KEYWORDS_PER_UPLOAD} keywords allowed. Please remove some keywords before adding more.`,
            variant: "destructive",
          });
          return;
        } else {
          // Add only what we can
          const keywordsToAdd = newKeywords.slice(0, canAdd);
          setNewKeywordsList([...newKeywordsList, ...keywordsToAdd]);
          toast({
            title: "Partial upload",
            description: `Added ${keywordsToAdd.length} keyword(s) from ${file.name}. You already have ${newKeywordsList.length} keywords. Maximum ${MAX_KEYWORDS_PER_UPLOAD} keywords allowed.`,
            variant: "default",
          });
          return;
        }
      }

      // Add new keywords
      setNewKeywordsList([...newKeywordsList, ...newKeywords]);
      
      toast({
        title: "Keywords uploaded",
        description: `Added ${newKeywords.length} keyword(s) from ${file.name}`,
        variant: "default",
      });
    } catch (error: any) {
      toast({
        title: "Upload error",
        description: error.message || "Failed to process the file. Please try again.",
        variant: "destructive",
      });
    } finally {
      // Reset file input
      event.target.value = '';
    }
  };

  const handleAddKeywordsToDomain = async () => {
    if (!selectedDomainForKeywords || newKeywordsList.length === 0) {
      toast({
        title: "Keywords required",
        description: "Please add at least one keyword.",
        variant: "destructive",
      });
      return;
    }

    try {
      setIsAddingKeywords(true);
      const domain = domains.find(d => d.id === selectedDomainForKeywords);
      
      // Add keywords one by one
      let successCount = 0;
      let errorCount = 0;
      
      for (const keywordText of newKeywordsList) {
        try {
          await apiClient.createKeyword({
            keyword: keywordText,
            domain: selectedDomainForKeywords,
          });
          successCount++;
        } catch (error: any) {
          errorCount++;
          console.error(`Failed to add keyword "${keywordText}":`, error);
        }
      }

      // Reload domains to get updated data
      await loadDomains();

      // Reset form
      setNewKeywordsInput("");
      setNewKeywordsList([]);
      setAddKeywordsDialogOpen(false);
      setSelectedDomainForKeywords(null);

      if (errorCount === 0) {
        toast({
          title: "Keywords added successfully!",
          description: `Added ${successCount} keyword(s) to ${domain?.name || 'domain'}.`,
        });
      } else {
        toast({
          title: "Partially successful",
          description: `Added ${successCount} keyword(s), ${errorCount} failed (may already exist).`,
          variant: "default",
        });
      }
    } catch (error: any) {
      toast({
        title: "Error adding keywords",
        description: error.message || "Failed to add keywords. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsAddingKeywords(false);
    }
  };

  const handleFetchKeywordsFromGSC = async () => {
    if (!newDomain.trim()) {
      toast({
        title: "Domain required",
        description: "Please enter a domain name first.",
        variant: "destructive",
      });
      return;
    }

    try {
      setIsFetchingKeywords(true);

      // TODO: Implement actual GSC API call
      // For now, show a message that this feature is coming soon
      toast({
        title: "Coming Soon",
        description: "Google Search Console integration is being set up. This feature will be available soon.",
      });

      // Placeholder for when GSC integration is ready:
      // const response = await apiClient.fetchKeywordsFromGSC({ domain: newDomain.trim() });
      // setNewDomainKeywords([...newDomainKeywords, ...response.keywords]);
    } catch (error: any) {
      toast({
        title: "Error fetching keywords",
        description: error.message || "Failed to fetch keywords from Google Search Console.",
        variant: "destructive",
      });
    } finally {
      setIsFetchingKeywords(false);
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

    // Validate at least 1 topic selected for AI mode
    if (!useManualKeywords && generatedKeywords.length > 0 && selectedTopics.size === 0) {
      toast({
        title: "No topics selected",
        description: "Please select at least one topic from the list.",
        variant: "destructive",
      });
      return;
    }

    try {
      setIsAddingDomain(true);
      // Don't show the animated loading modal in Step 2

      const domainName = newDomain.trim();

      // Call the automated onboarding endpoint
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
            const selectedKeywords = generatedKeywords.filter(kw =>
              selectedTopics.has(kw.topic || 'Other')
            );
            await apiClient.bulkCreateKeywords(createdDomainId, selectedKeywords);
          } catch (keywordError) {
            console.error('Failed to save selected keywords:', keywordError);
          }
        }

        // Reload domains to get the updated list
        await loadDomains();

        // Also update the global domain store so DomainSelector refreshes
        const { useDomainStore } = await import('@/stores/domainStore');
        await useDomainStore.getState().loadDomains();

        // Reset form and close modal
        setNewDomain("");
        setNewBrandName("");
        setNewDomainCountry("us");
        setSuggestedNiches([]);
        setSelectedNiches([]);
        setGeneratedKeywords([]);
        setSelectedKeywordIndices(new Set());
        setSelectedTopics(new Set());
        setKeywordSearchQuery("");
        setUseManualKeywords(false);
        setIgnoreBrandKeywords(false);
        setWizardStep(1);
        setAddDomainDialogOpen(false);

        toast({
          title: "Domain added successfully!",
          description: `${response.domain.name} has been created and is ready to use.`,
          duration: 5000,
        });
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
      setIsAddingDomain(false);
    }
  };

  const handleRemoveDomainConfirmed = async (id: number) => {
    try {
      await apiClient.deleteDomain(id);

      // Reload domains to get the updated list (both local state and global store)
      await loadDomains(); // Update local state for this page

      // Also update the global domain store so DomainSelector refreshes
      const { useDomainStore } = await import('@/stores/domainStore');
      await useDomainStore.getState().loadDomains();

      toast({
        title: "Domain removed",
        description: "The domain has been removed from your organization.",
      });
    } catch (error: any) {
      toast({
        title: "Error removing domain",
        description: error.message || "Failed to remove domain. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleUpdateOrgName = async () => {
    try {
      setIsUpdatingOrg(true);

      await apiClient.updateOrganization({
        name: organization.name,
        industry: organization.industry,
      });

      toast({
        title: "Organization updated",
        description: "Your organization details have been updated.",
      });
    } catch (error: any) {
      toast({
        title: "Error updating organization",
        description: error.message || "Failed to update organization. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsUpdatingOrg(false);
    }
  };

  const handleUpdateProfile = async () => {
    try {
      setIsUpdatingProfile(true);

      await apiClient.updateProfile({
        first_name: profileData.first_name,
        last_name: profileData.last_name,
      });

      toast({
        title: "Profile updated",
        description: "Your profile has been updated successfully.",
      });
    } catch (error: any) {
      toast({
        title: "Error updating profile",
        description: error.message || "Failed to update profile. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsUpdatingProfile(false);
    }
  };

  const handleSaveAllProfile = async () => {
    try {
      setIsUpdatingProfile(true);
      setIsUpdatingOrg(true);

      await Promise.all([
        apiClient.updateProfile({
          first_name: profileData.first_name,
          last_name: profileData.last_name,
        }),
        apiClient.updateOrganization({
          name: organization.name,
          industry: organization.industry,
        }),
      ]);

      toast({
        title: "Changes saved",
        description: "Your profile and organization details have been updated.",
      });
    } catch (error: any) {
      toast({
        title: "Error saving changes",
        description: error.message || "Failed to save changes. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsUpdatingProfile(false);
      setIsUpdatingOrg(false);
    }
  };

  const handleInviteMember = async () => {
    if (!inviteEmail.trim()) return;

    try {
      await apiClient.sendInvitation({
        email: inviteEmail.trim(),
        role: inviteRole,
      });

      setInviteEmail("");
      setInviteRole("user");
      setInviteDialogOpen(false);

      toast({
        title: "Invitation sent",
        description: `An invitation has been sent to ${inviteEmail.trim()}`,
      });
    } catch (error: any) {
      toast({
        title: "Error sending invitation",
        description: error.message || "Failed to send invitation. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleRemoveMemberConfirmed = async (id: number) => {
    try {
      await apiClient.removeTeamMember(id);

      // Reload team members to get the updated list
      await loadTeamMembers();

      toast({
        title: "Member removed",
        description: "Team member has been removed from the organization.",
      });
    } catch (error: any) {
      toast({
        title: "Error removing member",
        description: error.message || "Failed to remove team member. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleDeleteInvitation = async (invitationId: string) => {
    try {
      await apiClient.deleteInvitation(invitationId);
      await loadTeamMembers();
      toast({
        title: "Invitation deleted",
        description: "The invitation has been deleted successfully.",
      });
    } catch (error: any) {
      toast({
        title: "Error deleting invitation",
        description: error.message || "Failed to delete invitation. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleUpdateRole = async (id: number, newRole: "admin" | "user") => {
    try {
      setIsUpdatingMember(id);

      await apiClient.updateTeamMemberRole(id, newRole);

      // Reload team members to get the updated list
      await loadTeamMembers();

      toast({
        title: "Role updated",
        description: "Team member role has been updated.",
      });
    } catch (error: any) {
      toast({
        title: "Error updating role",
        description: error.message || "Failed to update team member role. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsUpdatingMember(null);
    }
  };

  const handleOpenProjectAccess = (member: any) => {
    const memberName = `${member.first_name} ${member.last_name}`.trim() || member.email.split('@')[0];
    setSelectedMemberForAccess({
      id: member.id,
      name: memberName,
      email: member.email
    });
    setProjectAccessDialogOpen(true);
  };

  const handleProjectAccessUpdated = () => {
    // Optionally reload team members or show a success message
    toast({
      title: "Project access updated",
      description: "Project access has been updated successfully.",
    });
  };

  const getRoleIcon = (role: "admin" | "user") => {
    return role === "admin" ? Crown : User;
  };

  const getRoleBadgeVariant = (role: "admin" | "user") => {
    return role === "admin" ? "default" : "secondary";
  };

  const handleConnectIntegration = () => {
    if (!selectedDomainForIntegration) {
      toast({
        title: "Domain required",
        description: "Please select a domain to connect the integration to.",
        variant: "destructive"
      });
      return;
    }

    // TODO: Connect to OAuth flow for GA/GSC
    const domain = domains.find(d => d.id === selectedDomainForIntegration);

    const newIntegration = integrationType === "google_analytics"
      ? {
        id: Date.now().toString(),
        domainId: selectedDomainForIntegration,
        domain: domain?.domain || "",
        type: "google_analytics" as const,
        propertyId: `GA-${Math.floor(Math.random() * 1000000000)}`,
        connectedAt: new Date().toISOString().split("T")[0],
        status: "active" as const,
        lastSync: new Date().toISOString()
      }
      : {
        id: Date.now().toString(),
        domainId: selectedDomainForIntegration,
        domain: domain?.domain || "",
        type: "search_console" as const,
        propertyUrl: `https://${domain?.domain}`,
        connectedAt: new Date().toISOString().split("T")[0],
        status: "active" as const,
        lastSync: new Date().toISOString()
      };

    setIntegrations([...integrations, newIntegration]);
    setConnectIntegrationDialog(false);
    setSelectedDomainForIntegration("");

    toast({
      title: "Integration connected",
      description: `${integrationType === "google_analytics" ? "Google Analytics" : "Search Console"} has been connected to ${domain?.domain}`,
    });
  };

  const handleDisconnectIntegration = (id: string) => {
    const integration = integrations.find(i => i.id === id);
    setIntegrations(integrations.filter(i => i.id !== id));
    toast({
      title: "Integration disconnected",
      description: `${integration?.type === "google_analytics" ? "Google Analytics" : "Search Console"} has been disconnected from ${integration?.domain}`,
    });
  };

  const getIntegrationsByDomain = (domainId: string) => {
    return integrations.filter(i => i.domainId === domainId);
  };

  if (isLoading) {
    return <PageLoader />;
  }

  return (
    <div className="p-8 space-y-6 bg-background animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Organization Settings</h1>
          <p className="text-muted-foreground mt-2">
            Manage your organization, domains, and team
          </p>
        </div>
      </div>

      <Tabs value={selectedTab} onValueChange={setSelectedTab} className="space-y-6">
        <div className="flex items-center justify-between">
          <TabsList className="bg-muted/50 p-1 border border-border">
            <TabsTrigger value="domains" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">All Domains</TabsTrigger>
            <TabsTrigger value="team" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">Team Members</TabsTrigger>
            <TabsTrigger value="profile" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">Profile</TabsTrigger>
          </TabsList>

          <div className="flex gap-2">
            {selectedTab === "domains" && (
              <Button onClick={() => setAddDomainDialogOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Domain
              </Button>
            )}
            {selectedTab === "team" && (
              <Button onClick={() => setInviteDialogOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Invite Member
              </Button>
            )}
          </div>
        </div>

        <TabsContent value="domains" className="space-y-6">
          <Card className="border border-border">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Domains ({domainTotalCount})</CardTitle>
                  <CardDescription>
                    Add and manage domains for your organization. All brand monitoring will be scoped to these domains.
                  </CardDescription>
                </div>
                <div className="relative w-64">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search domains..."
                    value={domainSearchQuery}
                    onChange={(e) => setDomainSearchQuery(e.target.value)}
                    className="pl-9"
                  />
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3">
            {domains.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Globe className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p>No domains added yet</p>
              </div>
            ) : (
              domains.filter((domain) => {
                if (!domainSearchQuery.trim()) return true;
                const query = domainSearchQuery.toLowerCase();
                return domain.name.toLowerCase().includes(query) || domain.url.toLowerCase().includes(query);
              }).map((domain) => {
                const isProcessing = domain.processing_status && ['INIT', 'SCHD', 'PROC'].includes(domain.processing_status);
                const isFailed = domain.processing_status === 'FAIL';
                const isCompleted = !domain.processing_status || domain.processing_status === 'COMP';

                const getStatusLabel = () => {
                  if (domain.processing_status === 'INIT') return 'Initializing';
                  if (domain.processing_status === 'SCHD') return 'Scheduled';
                  if (domain.processing_status === 'PROC') return 'Processing';
                  if (domain.processing_status === 'FAIL') return 'Failed';
                  return 'Ready';
                };

                return (
                  <div
                    key={domain.id}
                    className="flex items-center justify-between p-3 border rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <img
                        src={getFaviconUrl(domain.url, 32)}
                        alt={`${domain.name} favicon`}
                        className="h-5 w-5 rounded"
                        onError={(e) => handleFaviconError(e, domain.url, domain.name, 32)}
                      />
                      <Globe className="h-5 w-5 text-muted-foreground hidden" />
                      <div>
                        <p className="font-medium capitalize">{domain.name}</p>
                        <p className="text-sm text-muted-foreground">{domain.url}</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      {/* Health Score Display - First */}
                      {domain.latest_health_score !== undefined && domain.latest_health_score !== null ? (
                        <button
                          onClick={() => navigate(`/organization-settings/domains/${domain.id}?tab=health`)}
                          className="flex flex-col items-center justify-center px-2 py-1 hover:opacity-80 transition-opacity cursor-pointer"
                          title="View health check details"
                        >
                          <div className={`text-xl font-bold leading-none ${
                            domain.latest_health_grade_color === 'green' ? 'text-green-600' :
                            domain.latest_health_grade_color === 'blue' ? 'text-blue-600' :
                            domain.latest_health_grade_color === 'yellow' ? 'text-yellow-600' :
                            'text-red-600'
                          }`}>
                            {domain.latest_health_score}
                          </div>
                          <div className="text-[10px] text-muted-foreground uppercase tracking-wide">
                            Health
                          </div>
                        </button>
                      ) : !isProcessing ? (
                        <button
                          onClick={() => navigate(`/organization-settings/domains/${domain.id}?tab=health`)}
                          className="flex items-center gap-1 px-2 py-1 hover:opacity-80 transition-opacity cursor-pointer"
                          title="Run health check"
                        >
                          <Activity className="h-3.5 w-3.5 text-primary" />
                          <span className="text-primary font-medium text-xs">Run</span>
                        </button>
                      ) : null}

                      {/* Status Badge - Second */}
                      {isProcessing && (
                        <Badge variant="outline" className="gap-1.5 border-orange-500 text-orange-600 bg-orange-50 px-3 py-1">
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          {getStatusLabel()}
                        </Badge>
                      )}
                      {isFailed && (
                        <Badge variant="outline" className="gap-1.5 border-red-500 text-red-600 bg-red-50 px-3 py-1">
                          <AlertCircle className="h-3.5 w-3.5" />
                          Failed
                        </Badge>
                      )}
                      {isCompleted && (
                        <Badge variant="outline" className="gap-1.5 border-green-500 text-green-600 bg-green-50 px-3 py-1">
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          Ready
                        </Badge>
                      )}

                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => navigate(`/organization-settings/domains/${domain.id}`)}
                        title="Domain Settings"
                      >
                        <Settings className="h-4 w-4" />
                      </Button>

                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setConfirmDomainId(domain.id)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
          {domains.length < domainTotalCount && (
            <div className="flex justify-center pt-2">
              <Button
                onClick={loadMoreDomains}
                disabled={isLoadingMoreDomains}
              >
                {isLoadingMoreDomains ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Loading...
                  </>
                ) : (
                  'Load More'
                )}
              </Button>
            </div>
          )}
          </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="team" className="space-y-6">
          <Card className="border border-border">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Team Members ({teamMembers.length + invitations.length})</CardTitle>
                  <CardDescription>
                    Manage your organization's team members and their roles
                  </CardDescription>
                </div>
                <div className="relative w-64">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search members..."
                    value={teamSearchQuery}
                    onChange={(e) => { setTeamSearchQuery(e.target.value); setTeamVisibleCount(TEAM_PAGE_SIZE); }}
                    className="pl-9"
                  />
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {invitations.filter((inv) => {
                if (!teamSearchQuery.trim()) return true;
                return inv.email.toLowerCase().includes(teamSearchQuery.toLowerCase());
              }).length > 0 && (
            <div className="space-y-3">
              <h4 className="text-sm font-medium">Team Invitations</h4>
              {invitations.filter((inv) => {
                if (!teamSearchQuery.trim()) return true;
                return inv.email.toLowerCase().includes(teamSearchQuery.toLowerCase());
              }).map((inv) => (
                <div
                  key={inv.id}
                  className="flex items-center justify-between p-4 border rounded-lg"
                >
                  <div className="flex items-center gap-4 flex-1">
                    <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                      <Mail className="h-5 w-5 text-primary" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <p className="font-medium">{inv.email}</p>
                        {inv.role === 'admin' ? (
                          <Badge variant="default" className="gap-1">
                            <Crown className="h-3 w-3" />
                            Admin
                          </Badge>
                        ) : (
                          <Badge variant="secondary">User</Badge>
                        )}
                        <Badge variant="secondary" className="gap-1">
                          {inv.status.charAt(0).toUpperCase() + inv.status.slice(1)}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground mt-1">
                        {inv.status === 'pending' ? (
                          <span>Expires {new Date(inv.expires_at).toLocaleDateString()}</span>
                        ) : inv.accepted_at ? (
                          <span>Accepted {new Date(inv.accepted_at).toLocaleDateString()}</span>
                        ) : (
                          <span>Created {new Date(inv.created_at).toLocaleDateString()}</span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setConfirmInvitationId(inv.id)}
                      title="Delete Invitation"
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
              ))}
              <Separator />
            </div>
          )}

          <div className="space-y-3">
            {teamMembers.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <User className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p>No team members yet</p>
              </div>
            ) : (
              teamMembers.filter((member) => {
                if (!teamSearchQuery.trim()) return true;
                const query = teamSearchQuery.toLowerCase();
                const name = `${member.first_name} ${member.last_name}`.toLowerCase();
                return name.includes(query) || member.email.toLowerCase().includes(query);
              }).slice(0, teamVisibleCount).map((member) => {
                const RoleIcon = getRoleIcon(member.role);
                const memberName = `${member.first_name} ${member.last_name}`.trim() || member.email.split('@')[0];
                return (
                  <div
                    key={member.id}
                    className="flex items-center justify-between p-4 border rounded-lg"
                  >
                    <div className="flex items-center gap-4 flex-1">
                      <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                        <User className="h-5 w-5 text-primary" />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <p className="font-medium capitalize">{memberName}</p>
                          {member.role === "admin" && (
                            <Badge variant="default" className="gap-1">
                              <Crown className="h-3 w-3" />
                              Admin
                            </Badge>
                          )}
                          {!member.is_active && (
                            <Badge variant="secondary" className="gap-1">
                              Inactive
                            </Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground mt-1">
                          <Mail className="h-3 w-3" />
                          {member.email}
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                          Joined {new Date(member.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="icon"
                          onClick={() => handleOpenProjectAccess(member)}
                          title="Manage Project Access"
                        >
                          <Globe className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="icon"
                          onClick={() => navigate(`/organization-settings/members/${member.id}`)}
                          title="Manage Module Permissions"
                        >
                          <Settings className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setConfirmMemberId(member.id)}
                          disabled={isUpdatingMember === member.id}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    </div>
                  </div>
                );
              })
              )}
            </div>
          {(() => {
            const filteredCount = teamMembers.filter((member) => {
              if (!teamSearchQuery.trim()) return true;
              const query = teamSearchQuery.toLowerCase();
              const name = `${member.first_name} ${member.last_name}`.toLowerCase();
              return name.includes(query) || member.email.toLowerCase().includes(query);
            }).length;
            return teamVisibleCount < filteredCount ? (
              <div className="flex justify-center pt-2">
                <Button
                  onClick={() => setTeamVisibleCount(prev => prev + TEAM_PAGE_SIZE)}
                >
                  Load More
                </Button>
              </div>
            ) : null;
          })()}
          </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="profile" className="space-y-6">
          <Card className="border border-border">
            <CardHeader>
              <CardTitle>Profile Settings</CardTitle>
              <CardDescription>
                Update your personal information and organization details
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Personal Information</h3>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="first-name">First Name</Label>
                    <Input
                      id="first-name"
                      value={profileData.first_name}
                      onChange={(e) => setProfileData({ ...profileData, first_name: e.target.value })}
                      placeholder="Enter your first name"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="last-name">Last Name</Label>
                    <Input
                      id="last-name"
                      value={profileData.last_name}
                      onChange={(e) => setProfileData({ ...profileData, last_name: e.target.value })}
                      placeholder="Enter your last name"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    value={user?.email || ""}
                    disabled
                    className="bg-muted"
                  />
                  <p className="text-xs text-muted-foreground">Email cannot be changed</p>
                </div>
              </div>

              <Separator />

              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Organization</h3>
                <div className="space-y-2">
                  <Label htmlFor="org-name">Organization Name</Label>
                  <Input
                    id="org-name"
                    value={organization.name}
                    onChange={(e) => setOrganization({ ...organization, name: e.target.value })}
                  />
                </div>
              </div>

              <Separator />

              <div className="flex justify-end">
                <Button onClick={handleSaveAllProfile} disabled={isUpdatingProfile || isUpdatingOrg}>
                  {(isUpdatingProfile || isUpdatingOrg) ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                  Save Changes
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={inviteDialogOpen} onOpenChange={setInviteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Invite Team Member</DialogTitle>
            <DialogDescription>
              Send an invitation to join your organization
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="invite-email">Email Address</Label>
              <Input
                id="invite-email"
                type="email"
                placeholder="colleague@company.com"
                className="placeholder:text-muted-foreground placeholder:opacity-70"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="invite-role">Role</Label>
              <Select
                value={inviteRole}
                onValueChange={(value: "admin" | "user") => setInviteRole(value)}
              >
                <SelectTrigger id="invite-role">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="user">
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4" />
                      <span className="font-medium">User</span>
                    </div>
                  </SelectItem>
                  <SelectItem value="admin">
                    <div className="flex items-center gap-2">
                      <Crown className="h-4 w-4" />
                      <span className="font-medium">Admin</span>
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
              <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                {inviteRole === 'admin' ? (
                  <Crown className="h-3 w-3" />
                ) : (
                  <User className="h-3 w-3" />
                )}
                <span>{roleMeta[inviteRole].description}</span>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setInviteDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleInviteMember}>
              Send Invitation
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={connectIntegrationDialog} onOpenChange={setConnectIntegrationDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Connect Integration</DialogTitle>
            <DialogDescription>
              Connect Google Analytics or Search Console to a domain
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="integration-domain">Domain</Label>
              <Select
                value={selectedDomainForIntegration}
                onValueChange={setSelectedDomainForIntegration}
              >
                <SelectTrigger id="integration-domain">
                  <SelectValue placeholder="Select a domain" />
                </SelectTrigger>
                <SelectContent>
                  {domains.map((domain) => (
                    <SelectItem key={domain.id} value={domain.id}>
                      <div className="flex items-center gap-2">
                        <Globe className="h-4 w-4" />
                        {domain.domain}
                        {!domain.verified && (
                          <Badge variant="secondary" className="ml-2">Pending</Badge>
                        )}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="integration-type">Integration Type</Label>
              <Select
                value={integrationType}
                onValueChange={(value: "google_analytics" | "search_console") =>
                  setIntegrationType(value)
                }
              >
                <SelectTrigger id="integration-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="google_analytics">
                    <div className="flex items-center gap-2">
                      <Link2 className="h-4 w-4" />
                      <span className="font-medium">Google Analytics</span>
                    </div>
                  </SelectItem>
                  <SelectItem value="search_console">
                    <div className="flex items-center gap-2">
                      <Link2 className="h-4 w-4" />
                      <span className="font-medium">Google Search Console</span>
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
              <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                <Link2 className="h-3 w-3" />
                <span>
                  {integrationType === 'google_analytics' ? 'Track user behavior and conversions' : 'Monitor search performance and queries'}
                </span>
              </div>
            </div>
            <div className="bg-muted/50 p-3 rounded text-sm">
              <p className="font-medium mb-1">Next Steps:</p>
              <ol className="list-decimal list-inside space-y-1 text-muted-foreground">
                <li>You'll be redirected to Google to authenticate</li>
                <li>Select the property you want to connect</li>
                <li>Grant required permissions</li>
                <li>Data will start syncing automatically</li>
              </ol>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setConnectIntegrationDialog(false)}
            >
              Cancel
            </Button>
            <Button onClick={handleConnectIntegration}>
              Connect with Google
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={addDomainDialogOpen} onOpenChange={(open) => {
        setAddDomainDialogOpen(open);
        if (!open) {
          // Reset wizard on close
          setWizardStep(1);
          setNewDomain("");
          setNewBrandName("");
          setNewDomainCountry("us");
          setSuggestedNiches([]);
          setSelectedNiches([]);
          setGeneratedKeywords([]);
          setSelectedKeywordIndices(new Set());
          setKeywordSearchQuery("");
          setNewDomainKeywords([]);
          setKeywordInput("");
          setIgnoreBrandKeywords(false);
        }
      }}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          {isAutomatedOnboarding ? (
            // Loading Modal with Progress Messages
            <div className="py-10 px-8">
              <div className="flex flex-col items-center justify-center space-y-6">
                {/* Animated GIF - 50% smaller */}
                <div className="w-24 h-24 flex items-center justify-center">
                  <img
                    src={new URL('../assets/flask.gif', import.meta.url).href}
                    alt="Processing..."
                    className="w-full h-full object-contain"
                  />
                </div>

                {/* Progress Message */}
                <div className="text-center space-y-3">
                  <h3 className="text-xl font-semibold">
                    Setting up your brand monitoring...
                  </h3>
                  <p className="text-sm text-muted-foreground animate-pulse">
                    {progressMessages[onboardingProgress]}
                  </p>
                </div>

                {/* Progress Indicator */}
                <div className="w-full max-w-md space-y-2">
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>Step {onboardingProgress + 1} of {progressMessages.length}</span>
                    <span>{Math.round(((onboardingProgress + 1) / progressMessages.length) * 100)}%</span>
                  </div>
                  <div className="w-full bg-secondary rounded-full h-2">
                    <div
                      className="bg-primary h-2 rounded-full transition-all duration-500"
                      style={{ width: `${((onboardingProgress + 1) / progressMessages.length) * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  Add Domain {wizardStep === 1 && <Badge variant="outline">Step 1 of 2</Badge>}
                  {wizardStep === 2 && <Badge variant="outline">Step 2 of 2</Badge>}
                </DialogTitle>
                <DialogDescription>
                  {wizardStep === 1 && "Enter domain details and select industry niches"}
                  {wizardStep === 2 && "Select prompt intents to track for your brand"}
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-6 py-4">
            {/* Step 1: Domain Info & Niches */}
            {wizardStep === 1 && (
              <>
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

                {/* Industry Niches - Automated */}
                <div className="space-y-3 bg-muted/50 p-4 rounded-lg border border-muted">
                  <div className="flex items-start gap-2">
                    <Sparkles className="h-5 w-5 text-primary mt-0.5" />
                    <div className="space-y-2">
                      <Label className="text-base">AI-Powered Analysis</Label>
                      <p className="text-sm text-muted-foreground">
                        We'll automatically analyze your brand and identify relevant industry niches, prompts, competitors, and content opportunities.
                      </p>
                      <p className="text-xs text-muted-foreground italic">
                        Tip: Connect Google Search Console later for more accurate audience insights and prompt data.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Close Step 1 */}
              </>
            )}

            {/* Step 2: Generated Prompts */}
            {wizardStep === 2 && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  {!useManualKeywords ? (
                    <>
                      <div>
                        <h3 className="text-lg font-semibold">Generated Prompts</h3>
                        <div className="flex items-center gap-3 mt-1">
                          <p className="text-sm text-muted-foreground">
                            {generatedKeywords.length} prompts in {Object.keys(generatedKeywords.reduce((acc: any, kw: any) => {
                              const topic = kw.topic || 'Other';
                              acc[topic] = true;
                              return acc;
                            }, {})).length} topics
                          </p>
                          <Badge variant="default" className="gap-1.5">
                            {selectedTopics.size} topics selected
                          </Badge>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="flex items-center space-x-2 bg-muted/30 px-3 py-2 rounded-lg border border-border">
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
                      <p className="text-sm text-muted-foreground mt-1">
                        Enter prompts separated by commas
                      </p>
                    </div>
                  )}
                </div>

                {!useManualKeywords ? (
                  <>
                    {/* Search Input */}
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <Input
                        placeholder="Search prompts..."
                        value={keywordSearchQuery}
                        onChange={(e) => setKeywordSearchQuery(e.target.value)}
                        className="pl-9"
                      />
                    </div>

                    {/* Prompts Grouped by Topic */}
                    <div className="space-y-4 max-h-[500px] overflow-y-auto pr-2">
                      {Object.entries(
                        generatedKeywords
                          .map((keyword, index) => ({ keyword, index }))
                          .filter(({ keyword }) => {
                            const matchesSearch = keywordSearchQuery === "" ||
                              keyword.keyword.toLowerCase().includes(keywordSearchQuery.toLowerCase()) ||
                              (keyword.topic && keyword.topic.toLowerCase().includes(keywordSearchQuery.toLowerCase())) ||
                              (keyword.entity && keyword.entity.toLowerCase().includes(keywordSearchQuery.toLowerCase()));

                            const brandName = newBrandName || newDomain.replace(/^(https?:\/\/)?(www\.)?/, '').split('.')[0];
                            const containsBrandName = ignoreBrandKeywords && brandName &&
                              keyword.keyword.toLowerCase().includes(brandName.toLowerCase());

                            return matchesSearch && !containsBrandName;
                          })
                          .reduce((acc: any, { keyword, index }) => {
                            const topic = keyword.topic || 'Other';
                            if (!acc[topic]) acc[topic] = [];
                            acc[topic].push({ keyword, index });
                            return acc;
                          }, {})
                      ).map(([topic, items]: [string, any]) => {
                        const topicItems = items as Array<{ keyword: any; index: number }>;
                        const topicIndices = topicItems.map(item => item.index);
                        const selectedInTopic = topicIndices.filter((idx: number) =>
                          selectedKeywordIndices.has(idx)
                        ).length;

                        const isTopicSelected = selectedTopics.has(topic);

                        return (
                          <div
                            key={topic}
                            className={cn(
                              "rounded-lg bg-card cursor-pointer transition-all border border-border/30",
                              isTopicSelected && "border-primary"
                            )}
                            onClick={() => {
                              setSelectedTopics(prev => {
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
                            <div className="border-b border-border/40 p-4">
                              <div className="flex items-center gap-3">
                                <Checkbox
                                  checked={isTopicSelected}
                                  onCheckedChange={() => {
                                    setSelectedTopics(prev => {
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
                                  <p className="text-xs text-muted-foreground mt-1">
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
                                            {keyword.intent || 'N/A'}
                                          </span>
                                        </TableCell>
                                        <TableCell>
                                          <span className="text-sm text-muted-foreground">
                                            {keyword.entity || 'N/A'}
                                          </span>
                                        </TableCell>
                                        <TableCell>
                                          <Badge
                                            variant={
                                              keyword.volume_level === 'very-high' || keyword.volume_level === 'high'
                                                ? 'default'
                                                : 'secondary'
                                            }
                                            className="text-xs whitespace-nowrap"
                                          >
                                            {keyword.volume_level || 'N/A'}
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

                    <p className="text-xs text-muted-foreground">
                      Selected prompts will be saved when you create the domain. You can edit them later from domain settings.
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
                        <p className="text-xs text-muted-foreground mt-2">
                          Enter up to 10 prompts separated by commas. These will be added as primary prompts.
                        </p>
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>

          <DialogFooter className="gap-2 sticky bottom-0 bg-background border-t py-4 mt-auto">
            {wizardStep === 2 && (
              <>
                <Button
                  variant="outline"
                  onClick={() => setWizardStep(1)}
                >
                  <ChevronLeft className="h-4 w-4 mr-2" />
                  Back
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setUseManualKeywords(!useManualKeywords)}
                  className="mr-auto"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  {useManualKeywords ? "Use AI Prompts" : "Add Manually"}
                </Button>
              </>
            )}

            <Button
              variant="outline"
              onClick={() => setAddDomainDialogOpen(false)}
            >
              Cancel
            </Button>

            {wizardStep === 1 && (
              <Button
                onClick={handleGenerateKeywords}
                disabled={!newDomain.trim() || !newBrandName.trim() || isGeneratingKeywords}
              >
                {isGeneratingKeywords ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Generating Keywords...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4 mr-2" />
                    Generate Keywords
                  </>
                )}
              </Button>
            )}

            {wizardStep === 2 && (
              <Button onClick={handleAddDomain} disabled={isAddingDomain}>
                {isAddingDomain ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    Creating Domain...
                  </>
                ) : (
                  <>
                    <Plus className="h-4 w-4 mr-2" />
                    Create Domain
                  </>
                )}
              </Button>
            )}
          </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* Confirm Delete Domain */}
      <Dialog open={confirmDomainId !== null} onOpenChange={(open) => !open && setConfirmDomainId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove Domain</DialogTitle>
            <DialogDescription>
              Are you sure you want to remove this domain? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmDomainId(null)}>Cancel</Button>
            <Button
              variant="destructive"
              onClick={async () => {
                if (confirmDomainId !== null) {
                  await handleRemoveDomainConfirmed(confirmDomainId);
                  setConfirmDomainId(null);
                }
              }}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Confirm Remove Team Member */}
      <Dialog open={confirmMemberId !== null} onOpenChange={(open) => !open && setConfirmMemberId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove Team Member</DialogTitle>
            <DialogDescription>
              Are you sure you want to remove this member? The account will be deactivated.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmMemberId(null)}>Cancel</Button>
            <Button
              variant="destructive"
              onClick={async () => {
                if (confirmMemberId !== null) {
                  await handleRemoveMemberConfirmed(confirmMemberId);
                  setConfirmMemberId(null);
                }
              }}
            >
              Remove
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Confirm Delete Invitation */}
      <Dialog open={confirmInvitationId !== null} onOpenChange={(open) => !open && setConfirmInvitationId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Invitation</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this invitation? You will be able to send a new invitation to this email afterwards.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmInvitationId(null)}>Cancel</Button>
            <Button
              variant="destructive"
              onClick={async () => {
                if (confirmInvitationId !== null) {
                  await handleDeleteInvitation(confirmInvitationId);
                  setConfirmInvitationId(null);
                }
              }}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Keywords Dialog */}
      <Dialog open={addKeywordsDialogOpen} onOpenChange={setAddKeywordsDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Add Keywords</DialogTitle>
            <DialogDescription>
              Add additional keywords to {domains.find(d => d.id === selectedDomainForKeywords)?.name || 'this domain'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {/* Keywords Input */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="add-keywords-input">
                  Keywords <span className="text-destructive">*</span>
                </Label>
              </div>
              <div className="space-y-2">
                {/* Tag Input - styled like textarea */}
                <div
                  id="add-keywords-input"
                  className="flex flex-wrap gap-2 min-h-[100px] max-h-[300px] overflow-y-auto p-3 border border-input rounded-md bg-background text-sm ring-offset-background placeholder:text-muted-foreground focus-within:outline-none focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2"
                >
                  {newKeywordsList.map((keyword, index) => (
                    <Badge
                      key={index}
                      variant="default"
                      className="gap-1 pr-1 h-7"
                    >
                      {keyword}
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="h-4 w-4 p-0 hover:bg-background/20"
                        onClick={() => handleRemoveKeywordFromExisting(keyword)}
                      >
                        <X className="h-3 w-3" />
                      </Button>
                    </Badge>
                  ))}
                  <Input
                    type="text"
                    placeholder={newKeywordsList.length === 0 ? "Enter keywords and press Enter (e.g., seo, digital marketing)" : "Add more keywords..."}
                    value={newKeywordsInput}
                    onChange={(e) => setNewKeywordsInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === ",") {
                        e.preventDefault();
                        handleAddKeywordToExisting();
                      }
                    }}
                    className="flex-1 min-w-[200px] border-0 focus-visible:ring-0 focus-visible:ring-offset-0 p-0 h-7"
                  />
                  <input
                    type="file"
                    accept=".csv,.xlsx,.xls"
                    onChange={handleFileUploadForExisting}
                    className="hidden"
                    id="keyword-file-upload-existing"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 shrink-0"
                    onClick={() => document.getElementById('keyword-file-upload-existing')?.click()}
                    title="Upload keywords from CSV or XLSX"
                  >
                    <Upload className="h-4 w-4" />
                  </Button>
                </div>
                <div className="flex justify-between items-center">
                  <p className="text-xs text-muted-foreground">
                    💡 Type keywords and press Enter, or upload CSV/XLSX files. Max 100 keywords per upload. Each cell = one keyword.
                  </p>
                  {newKeywordsList.length > 0 && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setNewKeywordsList([]);
                        setNewKeywordsInput("");
                      }}
                      className="h-8 text-xs"
                    >
                      Clear all
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddKeywordsDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleAddKeywordsToDomain} disabled={isAddingKeywords || newKeywordsList.length === 0}>
              {isAddingKeywords ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Adding...
                </>
              ) : (
                <>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Keywords
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Project Access Manager */}
      {selectedMemberForAccess && (
        <ProjectAccessManager
          userId={selectedMemberForAccess.id}
          userName={selectedMemberForAccess.name}
          userEmail={selectedMemberForAccess.email}
          open={projectAccessDialogOpen}
          onOpenChange={setProjectAccessDialogOpen}
          onAccessUpdated={handleProjectAccessUpdated}
        />
      )}
    </div>
  );
}
