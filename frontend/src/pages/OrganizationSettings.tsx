import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DataForSeoCredentialsCard } from "@/components/DataForSeoCredentialsCard";
import Clients from "@/pages/Clients";
import InvoiceDetailsTab from "@/components/InvoiceDetailsTab";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/contexts/AuthContext";
import { MODULES } from "@/types/auth";
import { apiClient } from "@/services/api";
import ServiceApiKeysCard from "@/components/ServiceApiKeysCard";
import { Plus, Trash2, Globe, Mail, Shield, ShieldCheck, User, Crown, Settings, Link2, CheckCircle2, AlertCircle, Loader2, X, Check, ChevronDown, Upload, Sparkles, ChevronRight, ChevronLeft, Search, Activity, Key, Eye, EyeOff, Pencil, Copy, RefreshCw, Wallet } from "lucide-react";
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
import { AddDomainDialog } from "@/components/AddDomainDialog";
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
  const { user, checkPermission } = useAuth();
  const isTeamMember = user?.role === 'user';
  const hasTeamManagement = isTeamMember && checkPermission(MODULES.TEAM_MANAGEMENT, 'read');

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

  const [newDomainKeywords, setNewDomainKeywords] = useState<string[]>([]);
  const [keywordInput, setKeywordInput] = useState("");




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
  const [isTabLoading, setIsTabLoading] = useState(false);
  const [loadedTabs, setLoadedTabs] = useState<Set<string>>(new Set(["domains"]));
  const [isUpdatingOrg, setIsUpdatingOrg] = useState(false);
  const [isUpdatingMember, setIsUpdatingMember] = useState<number | null>(null);
  // Confirm dialogs
  const [confirmDomainId, setConfirmDomainId] = useState<number | null>(null);
  const [confirmMemberId, setConfirmMemberId] = useState<number | null>(null);
  const [confirmInvitationId, setConfirmInvitationId] = useState<string | null>(null);

  // Dialog states
  const [inviteDialogOpen, setInviteDialogOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<"admin" | "user" | "client">("user");
  const [inviteDomainId, setInviteDomainId] = useState<string>("");
  const roleMeta: Record<"admin" | "user" | "client", { label: string; description: string }> = {
    user: { label: "User", description: "Can view and manage brand monitoring" },
    admin: { label: "Admin", description: "Full access including team management" },
    client: { label: "Client", description: "Read-only access to one assigned domain" },
  };
  const [addDomainDialogOpen, setAddDomainDialogOpen] = useState(false);
  const [addKeywordsDialogOpen, setAddKeywordsDialogOpen] = useState(false);
  const [selectedDomainForKeywords, setSelectedDomainForKeywords] = useState<number | null>(null);
  const [newKeywordsInput, setNewKeywordsInput] = useState("");
  const [newKeywordsList, setNewKeywordsList] = useState<string[]>([]);
  const [isAddingKeywords, setIsAddingKeywords] = useState(false);

  // Team members search and pagination
  const [teamSearchQuery, setTeamSearchQuery] = useState("");
  const [teamSearchForced, setTeamSearchForced] = useState(false);
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

  // API Keys state
  const PROVIDERS = [
    // One key covers ChatGPT, Claude and Perplexity — all three share a
    // transport, so their individual vendor keys are never consulted. The id
    // stays 'openrouter' because it is what the API returns.
    // The label names the transport: customers paste an OpenRouter key here, so
    // calling it anything else left them guessing which key to get. This
    // replaces an earlier label that deliberately kept the transport unnamed.
    // Still no docsUrl — it is not rendered for any provider anyway.
    { id: 'openrouter', label: 'OpenRouter API (ChatGPT, Claude, Perplexity)', color: '#6d28d9' },
    { id: 'openai',     label: 'OpenAI (ChatGPT)',   color: '#10a37f', docsUrl: 'https://platform.openai.com/api-keys' },
    { id: 'gemini',     label: 'Google Gemini',       color: '#4285F4', docsUrl: 'https://aistudio.google.com/app/apikey' },
    { id: 'perplexity', label: 'Perplexity',          color: '#20808D', docsUrl: 'https://www.perplexity.ai/settings/api' },
    { id: 'anthropic',  label: 'Anthropic (Claude)',  color: '#D4A04A', docsUrl: 'https://console.anthropic.com/settings/keys' },
    { id: 'xai',        label: 'xAI (Grok)',          color: '#1DA1F2', docsUrl: 'https://console.x.ai/' },
    { id: 'deepseek',   label: 'DeepSeek',            color: '#7C4DFF', docsUrl: 'https://platform.deepseek.com/api_keys' },
  ] as const;

  type ProviderId = typeof PROVIDERS[number]['id'];

  // Token consumption, shown beneath the provider cards. Grouped by model
  // rather than by key because six of the seven models bill to one OpenRouter
  // credential — a per-key view would be a single undifferentiated line.
  const [tokenUsage, setTokenUsage] = useState<{
    summary?: { calls: number; total_tokens: number; input_tokens: number; output_tokens: number;
                cached_tokens: number; cost: number | null; failed: number;
                byok_calls: number; unpriced_calls: number };
    by_model?: Array<{ model_name: string; provider: string; calls: number;
                       total_tokens: number; cost: number | null; priced: boolean; failed: number }>;
    by_feature?: Array<{ feature: string; calls: number; total_tokens: number; cost: number | null }>;
    coverage_note?: string;
  } | null>(null);
  const [tokenUsageDays, setTokenUsageDays] = useState(30);
  const [loadingTokenUsage, setLoadingTokenUsage] = useState(false);

  // OpenRouter credit balance, shown against the OpenRouter API card. Kept
  // separate from apiKeys because it comes from a different endpoint and its
  // absence must not make the card look broken.
  const [openRouterBalance, setOpenRouterBalance] = useState<{
    configured: boolean;
    balance: number | null;
    total_credits?: number;
    total_usage?: number;
    error?: string;
  } | null>(null);

  const [apiKeys, setApiKeys] = useState<Record<ProviderId, {
    configured: boolean;
    preview: string | null;
    enabled: boolean;
    status: string;
  }>>({} as any);

  const [keyInputs, setKeyInputs] = useState<Record<ProviderId, string>>(
    Object.fromEntries(PROVIDERS.map(p => [p.id, ''])) as any
  );
  const [showKey, setShowKey] = useState<Record<ProviderId, boolean>>(
    Object.fromEntries(PROVIDERS.map(p => [p.id, false])) as any
  );
  const [savingKey, setSavingKey] = useState<ProviderId | null>(null);
  const [editingKey, setEditingKey] = useState<Record<ProviderId, boolean>>(
    Object.fromEntries(PROVIDERS.map(p => [p.id, false])) as any
  );
  const [copiedProvider, setCopiedProvider] = useState<ProviderId | null>(null);
  // Transient plaintext keys fetched on demand from the reveal endpoint.
  // Never preloaded; cleared automatically after REVEAL_TIMEOUT_MS.
  const [revealedKeys, setRevealedKeys] = useState<Record<ProviderId, string | null>>(
    Object.fromEntries(PROVIDERS.map(p => [p.id, null])) as any
  );
  const [revealingKey, setRevealingKey] = useState<ProviderId | null>(null);
  const REVEAL_TIMEOUT_MS = 30000; // auto-hide a revealed key after 30s

  // ===== Content Generation key (Claude, Strategy pipeline only) =====
  const [contentKey, setContentKey] = useState<{
    configured: boolean;
    preview: string | null;
    status: string;
    admin_key_configured: boolean;
    admin_key_preview: string | null;
    admin_key_status: string;
  }>({
    configured: false, preview: null, status: 'NOT_CONFIGURED',
    admin_key_configured: false, admin_key_preview: null, admin_key_status: 'NOT_CONFIGURED',
  });
  const [contentKeyInput, setContentKeyInput] = useState('');
  const [showContentKey, setShowContentKey] = useState(false);
  const [editingContentKey, setEditingContentKey] = useState(false);
  const [savingContentKey, setSavingContentKey] = useState(false);
  const [revealedContentKey, setRevealedContentKey] = useState<string | null>(null);
  const [revealingContentKey, setRevealingContentKey] = useState(false);
  const [contentKeyCopied, setContentKeyCopied] = useState(false);
  // Admin (usage-reporting) key states
  const [adminKeyInput, setAdminKeyInput] = useState('');
  const [showAdminKey, setShowAdminKey] = useState(false);
  const [editingAdminKey, setEditingAdminKey] = useState(false);
  const [savingAdminKey, setSavingAdminKey] = useState(false);
  const [revealedAdminKey, setRevealedAdminKey] = useState<string | null>(null);
  const [revealingAdminKey, setRevealingAdminKey] = useState(false);
  const [adminKeyCopied, setAdminKeyCopied] = useState(false);
  const [contentUsage, setContentUsage] = useState<any>(null);
  const [loadingContentUsage, setLoadingContentUsage] = useState(false);

  // Fetch the decrypted key for a provider on demand. Returns null on failure.
  const fetchPlaintextKey = async (provider: ProviderId): Promise<string | null> => {
    try {
      const data = await apiClient.revealApiKey(provider);
      return data?.api_key ?? null;
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to retrieve API key. Please try again.', variant: 'destructive' });
      return null;
    }
  };

  const handleRevealApiKey = async (provider: ProviderId) => {
    setRevealingKey(provider);
    const key = await fetchPlaintextKey(provider);
    setRevealingKey(null);
    if (!key) return;
    setRevealedKeys(prev => ({ ...prev, [provider]: key }));
    // Auto-clear so the plaintext doesn't linger in memory/UI indefinitely.
    window.setTimeout(() => {
      setRevealedKeys(prev => ({ ...prev, [provider]: null }));
    }, REVEAL_TIMEOUT_MS);
  };

  const handleHideApiKey = (provider: ProviderId) => {
    setRevealedKeys(prev => ({ ...prev, [provider]: null }));
  };

  const handleCopyApiKey = async (provider: ProviderId) => {
    setRevealingKey(provider);
    const key = await fetchPlaintextKey(provider);
    setRevealingKey(null);
    if (!key) return;
    await navigator.clipboard.writeText(key);
    setCopiedProvider(provider);
    // Plaintext is only held by the clipboard now — nothing retained in state.
    setTimeout(() => setCopiedProvider(null), 2000);
  };

  const handleEditApiKey = (provider: ProviderId) => {
    setEditingKey(prev => ({ ...prev, [provider]: true }));
    setRevealedKeys(prev => ({ ...prev, [provider]: null }));
    setKeyInputs(prev => ({ ...prev, [provider]: '' }));
  };

  // ----- Content Generation key handlers -----
  const loadContentKey = async () => {
    try {
      const data: any = await apiClient.getContentKey();
      setContentKey(data);
    } catch (error) {
      console.error('Error loading content generation key:', error);
    }
  };

  const loadContentKeyUsage = async () => {
    try {
      setLoadingContentUsage(true);
      const data: any = await apiClient.getContentKeyUsage();
      setContentUsage(data);
    } catch (error) {
      console.error('Error loading content generation usage:', error);
    } finally {
      setLoadingContentUsage(false);
    }
  };

  const handleSaveContentKey = async () => {
    const key = contentKeyInput.trim();
    if (!key) {
      toast({ title: 'API key required', description: 'Enter a Claude API key to configure content generation.', variant: 'destructive' });
      return;
    }
    setSavingContentKey(true);
    try {
      const res: any = await apiClient.updateContentKey({ api_key: key });
      setContentKey(res);
      setContentKeyInput('');
      setEditingContentKey(false);
      setShowContentKey(false);
      await loadContentKeyUsage();
      toast({ title: 'Content generation key saved', description: 'Your Claude content key has been validated and stored.' });
    } catch (error: any) {
      toast({ title: 'Error', description: error?.message || 'Failed to save the content generation key.', variant: 'destructive' });
    } finally {
      setSavingContentKey(false);
    }
  };

  // DELETE clears BOTH the content-generation and admin keys in one operation.
  const handleDeleteContentKey = async () => {
    setSavingContentKey(true);
    try {
      const res: any = await apiClient.deleteContentKey();
      setContentKey(res);
      setContentKeyInput('');
      setEditingContentKey(false);
      setRevealedContentKey(null);
      setAdminKeyInput('');
      setEditingAdminKey(false);
      setRevealedAdminKey(null);
      await loadContentKeyUsage();
      toast({ title: 'Keys removed', description: 'Content generation and admin keys were removed.' });
    } catch (error: any) {
      toast({ title: 'Error', description: 'Failed to remove the keys.', variant: 'destructive' });
    } finally {
      setSavingContentKey(false);
    }
  };

  const fetchContentPlaintextKey = async (): Promise<string | null> => {
    try {
      const data = await apiClient.revealContentKey();
      return data?.api_key ?? null;
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to retrieve the content generation key.', variant: 'destructive' });
      return null;
    }
  };

  const handleRevealContentKey = async () => {
    setRevealingContentKey(true);
    const key = await fetchContentPlaintextKey();
    setRevealingContentKey(false);
    if (!key) return;
    setRevealedContentKey(key);
    window.setTimeout(() => setRevealedContentKey(null), REVEAL_TIMEOUT_MS);
  };

  const handleCopyContentKey = async () => {
    setRevealingContentKey(true);
    const key = await fetchContentPlaintextKey();
    setRevealingContentKey(false);
    if (!key) return;
    await navigator.clipboard.writeText(key);
    setContentKeyCopied(true);
    setTimeout(() => setContentKeyCopied(false), 2000);
  };

  const handleEditContentKey = () => {
    setEditingContentKey(true);
    setRevealedContentKey(null);
    setContentKeyInput('');
  };

  // ----- Admin (usage-reporting) key handlers -----
  const handleSaveAdminKey = async () => {
    const key = adminKeyInput.trim();
    if (!key) {
      toast({ title: 'Admin key required', description: 'Enter an Anthropic Admin key (sk-ant-admin…).', variant: 'destructive' });
      return;
    }
    setSavingAdminKey(true);
    try {
      const res: any = await apiClient.updateContentKey({ admin_api_key: key });
      setContentKey(res);
      setAdminKeyInput('');
      setEditingAdminKey(false);
      setShowAdminKey(false);
      await loadContentKeyUsage();
      toast({ title: 'Admin key saved', description: 'Your Anthropic Admin key has been validated and stored.' });
    } catch (error: any) {
      toast({ title: 'Error', description: error?.message || 'Failed to save the admin key.', variant: 'destructive' });
    } finally {
      setSavingAdminKey(false);
    }
  };

  const fetchAdminPlaintextKey = async (): Promise<string | null> => {
    try {
      const data = await apiClient.revealAdminKey();
      return data?.api_key ?? null;
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to retrieve the admin key.', variant: 'destructive' });
      return null;
    }
  };

  const handleRevealAdminKey = async () => {
    setRevealingAdminKey(true);
    const key = await fetchAdminPlaintextKey();
    setRevealingAdminKey(false);
    if (!key) return;
    setRevealedAdminKey(key);
    window.setTimeout(() => setRevealedAdminKey(null), REVEAL_TIMEOUT_MS);
  };

  const handleCopyAdminKey = async () => {
    setRevealingAdminKey(true);
    const key = await fetchAdminPlaintextKey();
    setRevealingAdminKey(false);
    if (!key) return;
    await navigator.clipboard.writeText(key);
    setAdminKeyCopied(true);
    setTimeout(() => setAdminKeyCopied(false), 2000);
  };

  const handleEditAdminKey = () => {
    setEditingAdminKey(true);
    setRevealedAdminKey(null);
    setAdminKeyInput('');
  };

  // Format an ISO timestamp as a short "x minutes ago" relative string.
  const formatRelativeTime = (iso: string | null | undefined): string => {
    if (!iso) return 'Never';
    const then = new Date(iso).getTime();
    if (Number.isNaN(then)) return 'Never';
    const diffSec = Math.max(0, Math.floor((Date.now() - then) / 1000));
    if (diffSec < 60) return 'Just now';
    const mins = Math.floor(diffSec / 60);
    if (mins < 60) return `${mins} minute${mins === 1 ? '' : 's'} ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`;
    const days = Math.floor(hours / 24);
    return `${days} day${days === 1 ? '' : 's'} ago`;
  };

  const formatTokens = (n: number | null | undefined): string =>
    (n ?? 0).toLocaleString();


  // Load only organization + default tab (domains) on mount
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        setIsLoading(true);
        await Promise.all([
          loadOrganization(),
          loadDomains(),
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
    loadInitialData();
  }, []);

  // Lazy-load tab data on first switch
  const handleTabChange = async (tab: string) => {
    setSelectedTab(tab);
    if (loadedTabs.has(tab)) return;

    setIsTabLoading(true);
    try {
      if (tab === "team") {
        await loadTeamMembers();
      } else if (tab === "api-keys") {
        await loadApiKeys();
      } else if (tab === "content-key") {
        await Promise.all([loadContentKey(), loadContentKeyUsage()]);
      } else if (tab === "profile") {
        // Profile uses organization (already loaded) + user (from auth context)
      }
      setLoadedTabs(prev => new Set(prev).add(tab));
    } catch (error) {
      toast({
        title: "Error loading data",
        description: "Failed to load tab data. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsTabLoading(false);
    }
  };

  // Poll for domain updates when there are processing domains
  useEffect(() => {
    if (selectedTab !== "domains") return;

    const hasProcessingDomains = domains.some(d =>
      d.processing_status && ['INIT', 'SCHD', 'PROC'].includes(d.processing_status)
    );

    if (!hasProcessingDomains) return;

    const interval = setInterval(async () => {
      try {
        const totalPages = domainPage;
        const params: any = { page: '1', page_size: String(totalPages * DOMAINS_PAGE_SIZE) };
        if (domainSearchQuery.trim()) params.search = domainSearchQuery.trim();
        const data = await apiClient.getDomains(params);
        setDomains(data.domains);
        setDomainTotalCount(data.total_count ?? data.domains.length);
      } catch (error) {
        console.error("Error polling domains:", error);
      }
    }, 10000);

    return () => clearInterval(interval);
  }, [domains, selectedTab]);

  // Initialize profile data from user
  useEffect(() => {
    if (user) {
      setProfileData({
        first_name: user.first_name || "",
        last_name: user.last_name || "",
      });
    }
  }, [user]);

  const loadOrganization = async () => {
    try {
      const data = await apiClient.getOrganization();
      setOrganization(data);
      // Populate API keys state if present in response
      if (data.api_keys) {
        setApiKeys(data.api_keys);
      }
    } catch (error) {
      console.error("Error loading organization:", error);
    }
  };

  const loadApiKeys = async () => {
    try {
      const data = await apiClient.getOrganization();
      if (data.api_keys) setApiKeys(data.api_keys);
    } catch (error) {
      console.error("Error loading API keys:", error);
    }
    // Fetched separately and never allowed to fail the keys load — the card
    // must still render its status if the balance lookup is unreachable.
    try {
      setOpenRouterBalance(await apiClient.getOpenRouterBalance() as any);
    } catch (error) {
      console.error("Error loading OpenRouter balance:", error);
      setOpenRouterBalance(null);
    }
  };

  const handleSaveApiKey = async (provider: ProviderId) => {
    const newKey = keyInputs[provider].trim();
    if (!newKey) return;
    setSavingKey(provider);
    try {
      await apiClient.updateOrganization({ [`${provider}_api_key`]: newKey });
      setKeyInputs(prev => ({ ...prev, [provider]: '' }));
      await loadApiKeys();
      toast({ title: 'API key saved', description: `${PROVIDERS.find(p => p.id === provider)?.label} key updated successfully.` });
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to save API key. Please try again.', variant: 'destructive' });
    } finally {
      setSavingKey(null);
    }
  };


  const loadDomains = async (page: number = 1, append: boolean = false, search: string = "") => {
    try {
      const params: any = { page: String(page), page_size: String(DOMAINS_PAGE_SIZE) };
      if (search.trim()) {
        params.search = search.trim();
      }
      const data = await apiClient.getDomains(params);
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
      await loadDomains(domainPage + 1, true, domainSearchQuery);
    } finally {
      setIsLoadingMoreDomains(false);
    }
  };

  // Debounced server-side domain search - triggers after 3+ chars or when cleared
  const [domainSearchInitialized, setDomainSearchInitialized] = useState(false);
  useEffect(() => {
    if (!domainSearchInitialized) {
      setDomainSearchInitialized(true);
      return;
    }
    const trimmed = domainSearchQuery.trim();
    // Only search when 3+ characters typed, or when search is cleared (reload all)
    if (trimmed.length > 0 && trimmed.length < 3) return;
    const timer = setTimeout(() => {
      setDomainPage(1);
      loadDomains(1, false, domainSearchQuery);
    }, 400);
    return () => clearTimeout(timer);
  }, [domainSearchQuery]);

  const loadTokenUsage = async (days: number) => {
    setLoadingTokenUsage(true);
    try {
      const res = (await apiClient.getTokenUsage({ days })) as { status?: string; data?: unknown };
      setTokenUsage(res?.status === "success" ? (res.data as typeof tokenUsage) : null);
    } catch {
      // Consumption is informational — a failure here must not disturb the
      // key-management screen it sits beneath.
      setTokenUsage(null);
    } finally {
      setLoadingTokenUsage(false);
    }
  };

  useEffect(() => {
    loadTokenUsage(tokenUsageDays);
  }, [tokenUsageDays]);

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
    if (inviteRole === 'client' && !inviteDomainId) {
      toast({
        title: "Domain required",
        description: "Select the domain this client should see.",
        variant: "destructive",
      });
      return;
    }

    try {
      await apiClient.sendInvitation({
        email: inviteEmail.trim(),
        role: inviteRole,
        ...(inviteRole === 'client' ? { domain: Number(inviteDomainId) } : {}),
      });

      setInviteEmail("");
      setInviteRole("user");
      setInviteDomainId("");
      setInviteDialogOpen(false);

      toast({
        title: "Invitation sent",
        description: `An invitation has been sent to ${inviteEmail.trim()}`,
      });

      // Refresh team members and invitations list
      await loadTeamMembers();
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

      <Tabs value={selectedTab} onValueChange={handleTabChange} className="space-y-6">
        <div className="flex items-center justify-between">
          <TabsList className="bg-muted/50 p-1 border border-border">
            <TabsTrigger value="domains" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">All Domains</TabsTrigger>
            {(!isTeamMember || hasTeamManagement) && (
              <TabsTrigger value="team" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">Team Members</TabsTrigger>
            )}
            {/* Clients moved here from its own sidebar entry — it is org
                administration, and it sits next to Team Members because both
                are about who can log in. Same permission as this page. */}
            {!isTeamMember && (
              <TabsTrigger value="clients" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">Clients</TabsTrigger>
            )}
            {/* This organisation's registered particulars for its tax invoices. */}
            {!isTeamMember && (
              <TabsTrigger value="invoice-details" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">Invoice Details</TabsTrigger>
            )}
            {user?.role === 'super_admin' && (
              <TabsTrigger value="api-keys" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">
                <Key className="h-3.5 w-3.5 mr-1.5" />API Keys
              </TabsTrigger>
            )}
            {(user?.role === 'super_admin' || user?.role === 'admin') && (
              <TabsTrigger value="access-keys" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">
                <Key className="h-3.5 w-3.5 mr-1.5" />Get your API key
              </TabsTrigger>
            )}
            {/* Hidden: neither key on this tab is used any more. Content
                generation runs on the system OPENROUTER_API_KEY — a stored
                sk-ant key is ignored by the sk-or- prefix check — and the
                Anthropic usage API the Admin key queries reports zero, because
                Claude traffic now bills through OpenRouter. The tab and its
                endpoints are left in place for when a usage source exists
                again. */}
            {false && user?.role === 'super_admin' && (
              <TabsTrigger value="content-key" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">
                <Sparkles className="h-3.5 w-3.5 mr-1.5" />Content Generation api key
              </TabsTrigger>
            )}
          </TabsList>

          <div className="flex gap-2">
            {selectedTab === "domains" && !isTeamMember && (
              <Button onClick={() => setAddDomainDialogOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Domain
              </Button>
            )}
            {selectedTab === "team" && (!isTeamMember || hasTeamManagement) && (
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
                    onKeyDown={(e) => { if (e.key === 'Enter') { setDomainPage(1); loadDomains(1, false, domainSearchQuery); } }}
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
                <p>{domainSearchQuery.trim() ? "No domains found" : "No domains added yet"}</p>
              </div>
            ) : (
              domains.map((domain) => {
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
                      {/* Health Score Display - First (hidden for team members) */}
                      {!isTeamMember && (
                        domain.latest_health_score !== undefined && domain.latest_health_score !== null ? (
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
                        ) : null
                      )}

                      {/* Status Badge - Second (hidden for team members) */}
                      {!isTeamMember && isProcessing && (
                        <Badge variant="outline" className="gap-1.5 border-orange-500 text-orange-600 bg-orange-50 px-3 py-1">
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          {getStatusLabel()}
                        </Badge>
                      )}
                      {!isTeamMember && isFailed && (
                        <Badge variant="outline" className="gap-1.5 border-red-500 text-red-600 bg-red-50 px-3 py-1">
                          <AlertCircle className="h-3.5 w-3.5" />
                          Failed
                        </Badge>
                      )}
                      {!isTeamMember && isCompleted && (
                        <Badge variant="outline" className="gap-1.5 border-green-500 text-green-600 bg-green-50 px-3 py-1">
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          Ready
                        </Badge>
                      )}

                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => navigate(`/organization-settings/domains/${domain.id}${isTeamMember ? '?tab=integrations' : ''}`)}
                        title="Domain Settings"
                      >
                        <Settings className="h-4 w-4" />
                      </Button>

                      {!isTeamMember && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setConfirmDomainId(domain.id)}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      )}
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
          {isTabLoading ? (
            <div className="flex items-center justify-center py-20">
              <div className="flex items-center gap-3">
                <Loader2 className="h-6 w-6 animate-spin text-primary" />
                <span className="text-muted-foreground">Loading team members...</span>
              </div>
            </div>
          ) : (
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
                    onChange={(e) => { setTeamSearchQuery(e.target.value); setTeamSearchForced(false); setTeamVisibleCount(TEAM_PAGE_SIZE); }}
                    onKeyDown={(e) => { if (e.key === 'Enter') { setTeamSearchForced(true); setTeamVisibleCount(TEAM_PAGE_SIZE); } }}
                    className="pl-9"
                  />
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {invitations.filter((inv) => {
                if (!teamSearchQuery.trim() || (teamSearchQuery.trim().length < 3 && !teamSearchForced)) return true;
                return inv.email.toLowerCase().includes(teamSearchQuery.toLowerCase());
              }).length > 0 && (
            <div className="space-y-3">
              <h4 className="text-sm font-medium">Team Invitations</h4>
              {invitations.filter((inv) => {
                if (!teamSearchQuery.trim() || (teamSearchQuery.trim().length < 3 && !teamSearchForced)) return true;
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
                  {!isTeamMember && (
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
                  )}
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
                if (!teamSearchQuery.trim() || (teamSearchQuery.trim().length < 3 && !teamSearchForced)) return true;
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
                      {!isTeamMember && (
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
                      )}
                    </div>
                  </div>
                );
              })
              )}
            </div>
          {(() => {
            const filteredCount = teamMembers.filter((member) => {
              if (!teamSearchQuery.trim() || (teamSearchQuery.trim().length < 3 && !teamSearchForced)) return true;
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
          )}
        </TabsContent>

        {/* ─────────── CLIENTS TAB ─────────── */}
        {!isTeamMember && (
          <TabsContent value="clients" className="space-y-6">
            <Clients embedded />
          </TabsContent>
        )}

        {/* ─────────── INVOICE DETAILS TAB ─────────── */}
        {!isTeamMember && (
          <TabsContent value="invoice-details" className="space-y-6">
            <InvoiceDetailsTab />
          </TabsContent>
        )}

        {/* ─────────── ACCESS KEYS TAB (service API keys) ─────────── */}
        {(user?.role === 'super_admin' || user?.role === 'admin') && (
          <TabsContent value="access-keys" className="space-y-6">
            <ServiceApiKeysCard />
          </TabsContent>
        )}

        {/* ─────────── API KEYS TAB ─────────── */}
        {user?.role === 'super_admin' && (
          <TabsContent value="api-keys" className="space-y-6">
            <Card className="border border-border">
              <CardHeader>
                <CardTitle>LLM Provider API Keys</CardTitle>
                <CardDescription>
                  Add your own API keys for each AI provider. Keys are encrypted at rest.
                  Leave a field empty to use the system-level key (if configured).
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Only providers the server says it will actually read.
                      The rest authenticate through OpenRouter or are disabled
                      platforms, so a key stored for them would never be used. */}
                  {PROVIDERS.filter((p) => apiKeys?.[p.id]).map((provider) => {
                    const info = apiKeys[provider.id as ProviderId];
                    const status = info?.status ?? 'NOT_CONFIGURED';
                    const configured = info?.configured ?? false;
                    const preview = info?.preview ?? null;
                    const inputVal = keyInputs[provider.id as ProviderId] ?? '';
                    const visible = showKey[provider.id as ProviderId] ?? false;
                    const isSaving = savingKey === provider.id;
                    const isEditing = editingKey[provider.id as ProviderId] ?? false;
                    const revealed = revealedKeys[provider.id as ProviderId] ?? null;
                    const isRevealing = revealingKey === provider.id;

                    const statusConfig: Record<string, { label: string; className: string }> = {
                      CONNECTED:        { label: 'Connected',         className: 'bg-emerald-500/15 text-emerald-500 border-emerald-500/30' },
                      NOT_CONFIGURED:   { label: 'Not Configured',     className: 'bg-muted text-muted-foreground border-border' },
                      DISABLED:         { label: 'Disabled',           className: 'bg-orange-500/15 text-orange-400 border-orange-500/30' },
                      INVALID_KEY:      { label: 'Invalid Key',        className: 'bg-red-500/15 text-red-400 border-red-500/30' },
                      RATE_LIMITED:     { label: 'Rate Limited',       className: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30' },
                      OUT_OF_CREDITS:   { label: 'Out of Credits',     className: 'bg-red-500/15 text-red-400 border-red-500/30' },
                      MODEL_UNAVAILABLE:{ label: 'Model Unavailable',  className: 'bg-red-500/15 text-red-400 border-red-500/30' },
                      ERROR:            { label: 'Error',              className: 'bg-red-500/15 text-red-400 border-red-500/30' },
                    };
                    const sc = statusConfig[status] ?? statusConfig['NOT_CONFIGURED'];

                    return (
                      <Card key={provider.id} className="border border-border relative overflow-hidden bg-muted/10">
                        {/* Colour accent bar */}
                        <div className="absolute top-0 left-0 right-0 h-0.5" style={{ background: provider.color }} />

                        <CardHeader className="pb-3">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: `${provider.color}20` }}>
                                <Key className="h-4 w-4" style={{ color: provider.color }} />
                              </div>
                              <div>
                                <CardTitle className="text-base">{provider.label}</CardTitle>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <Badge variant="outline" className={`gap-1.5 px-2.5 py-0.5 font-medium ${sc.className}`}>
                                {sc.label}
                              </Badge>
                            </div>
                          </div>
                        </CardHeader>

                        <CardContent className="space-y-3">
                          {/* Free to read, and the number that decides whether a
                              prompt run can go ahead at all. Only OpenRouter
                              exposes one — the other providers here bill through
                              it or are disabled. */}
                          {provider.id === 'openrouter' && openRouterBalance?.balance != null && (
                            <div className="flex items-center gap-2 text-sm">
                              <Wallet className="h-3.5 w-3.5 text-muted-foreground" />
                              <span className="text-muted-foreground">Balance</span>
                              <span className="font-semibold">
                                ${openRouterBalance.balance.toFixed(2)}
                              </span>
                              {openRouterBalance.total_usage != null && (
                                <span className="text-xs text-muted-foreground">
                                  · ${openRouterBalance.total_usage.toFixed(2)} used of $
                                  {openRouterBalance.total_credits?.toFixed(2)}
                                </span>
                              )}
                            </div>
                          )}
                          {provider.id === 'openrouter' && openRouterBalance?.error && (
                            <p className="text-xs text-muted-foreground">
                              Balance unavailable: {openRouterBalance.error}
                            </p>
                          )}

                          {/* ── Key preview row (shown when configured and NOT editing) ── */}
                          {configured && !isEditing && (
                            <div className="flex items-center justify-between rounded-md border border-border bg-muted/30 px-3 py-2">
                              <div className="flex items-center gap-2 min-w-0">
                                <Key className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                                <span className="font-mono text-sm text-foreground truncate">
                                  {revealed ?? preview ?? '••••••••••••••••'}
                                </span>
                              </div>
                              <div className="flex items-center gap-1 shrink-0 ml-2">
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  className="h-8 px-2.5 gap-1.5 text-muted-foreground hover:text-foreground"
                                  disabled={isRevealing}
                                  onClick={() => revealed ? handleHideApiKey(provider.id as ProviderId) : handleRevealApiKey(provider.id as ProviderId)}
                                >
                                  {isRevealing ? (
                                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                  ) : revealed ? (
                                    <EyeOff className="h-3.5 w-3.5" />
                                  ) : (
                                    <Eye className="h-3.5 w-3.5" />
                                  )}
                                  <span className="text-xs font-medium">{revealed ? 'Hide' : 'Reveal'}</span>
                                </Button>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  className="h-8 px-2.5 gap-1.5 text-muted-foreground hover:text-foreground"
                                  disabled={isRevealing}
                                  onClick={() => handleCopyApiKey(provider.id as ProviderId)}
                                >
                                  {copiedProvider === provider.id ? (
                                    <>
                                      <Check className="h-3.5 w-3.5 text-emerald-500" />
                                      <span className="text-xs text-emerald-500 font-medium">Copied</span>
                                    </>
                                  ) : (
                                    <>
                                      <Copy className="h-3.5 w-3.5" />
                                      <span className="text-xs font-medium">Copy</span>
                                    </>
                                  )}
                                </Button>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  className="h-8 px-2.5 gap-1.5 text-muted-foreground hover:text-foreground"
                                  disabled={isRevealing}
                                  onClick={() => handleEditApiKey(provider.id as ProviderId)}
                                >
                                  <Pencil className="h-3.5 w-3.5" />
                                  <span className="text-xs font-medium">Edit</span>
                                </Button>
                              </div>
                            </div>
                          )}

                          {/* ── Input row (shown when NOT configured OR when editing) ── */}
                          {(!configured || isEditing) && (
                            <div className="flex gap-2">
                              <div className="relative flex-1">
                                <Input
                                  type={visible ? 'text' : 'password'}
                                  placeholder={configured ? 'Enter new key to replace…' : 'Paste your API key…'}
                                  value={inputVal}
                                  autoFocus={isEditing}
                                  onChange={e => setKeyInputs(prev => ({ ...prev, [provider.id]: e.target.value }))}
                                  className="pr-10 font-mono text-sm"
                                  onKeyDown={e => { if (e.key === 'Enter') handleSaveApiKey(provider.id as ProviderId); }}
                                />
                                <button
                                  type="button"
                                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                  onClick={() => setShowKey(prev => ({ ...prev, [provider.id]: !visible }))}
                                >
                                  {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                                </button>
                              </div>
                              <Button
                                size="sm"
                                disabled={!inputVal.trim() || isSaving}
                                onClick={async () => {
                                  await handleSaveApiKey(provider.id as ProviderId);
                                  setEditingKey(prev => ({ ...prev, [provider.id]: false }));
                                }}
                                className="gap-1.5"
                              >
                                {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
                                Save
                              </Button>
                              {isEditing && (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => {
                                    setEditingKey(prev => ({ ...prev, [provider.id]: false }));
                                    setKeyInputs(prev => ({ ...prev, [provider.id]: '' }));
                                    setShowKey(prev => ({ ...prev, [provider.id]: false }));
                                  }}
                                >
                                  Cancel
                                </Button>
                              )}
                            </div>
                          )}

                        </CardContent>
                      </Card>
                    );
                  })}
                </div>
              </CardContent>
            </Card>

            {/* Not an LLM provider, so it sits in its own card rather than the
                grid above — different auth shape, and a different bill. */}
            <DataForSeoCredentialsCard />

            {/* Token consumption per LLM. Grouped by model, not by key: six of
                the seven models bill to the single OpenRouter credential, so a
                per-key view would collapse to one undifferentiated line. */}
            <Card className="border border-border">
              <CardHeader>
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1.5">
                    <CardTitle>Token Consumption</CardTitle>
                    <CardDescription>
                      Tokens and cost per model for this organisation.
                    </CardDescription>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {[7, 30, 90].map((d) => (
                      <Button
                        key={d}
                        size="sm"
                        variant={tokenUsageDays === d ? "default" : "outline"}
                        onClick={() => setTokenUsageDays(d)}
                        disabled={loadingTokenUsage}
                      >
                        {d}d
                      </Button>
                    ))}
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => loadTokenUsage(tokenUsageDays)}
                      disabled={loadingTokenUsage}
                    >
                      {loadingTokenUsage ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <RefreshCw className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-5">
                {loadingTokenUsage && !tokenUsage ? (
                  <div className="flex items-center justify-center py-10">
                    <Loader2 className="h-6 w-6 animate-spin text-primary" />
                  </div>
                ) : !tokenUsage || !tokenUsage.summary?.calls ? (
                  <p className="text-sm text-muted-foreground py-6 text-center">
                    No recorded usage in the last {tokenUsageDays} days.
                  </p>
                ) : (
                  <>
                    {/* Headline figures */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      {[
                        { label: "Calls", value: tokenUsage.summary.calls.toLocaleString() },
                        { label: "Total tokens", value: tokenUsage.summary.total_tokens.toLocaleString() },
                        {
                          label: "Cost",
                          value:
                            tokenUsage.summary.cost === null
                              ? "Not priced"
                              : "$" + tokenUsage.summary.cost.toFixed(4),
                        },
                        { label: "Failed", value: tokenUsage.summary.failed.toLocaleString() },
                      ].map((stat) => (
                        <div key={stat.label} className="rounded-lg border bg-muted/30 p-3">
                          <div className="text-xs text-muted-foreground">{stat.label}</div>
                          <div className="text-xl font-semibold tabular-nums mt-0.5">{stat.value}</div>
                        </div>
                      ))}
                    </div>

                    {/* Per-model breakdown — the point of the module */}
                    <div className="rounded-lg border overflow-hidden">
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead className="bg-muted/50">
                            <tr className="text-left">
                              <th className="px-3 py-2 font-medium">Model</th>
                              <th className="px-3 py-2 font-medium text-right">Calls</th>
                              <th className="px-3 py-2 font-medium text-right">Tokens</th>
                              <th className="px-3 py-2 font-medium text-right">Cost</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(tokenUsage.by_model || []).map((m) => (
                              <tr key={m.provider + "-" + m.model_name} className="border-t">
                                <td className="px-3 py-2">
                                  <div className="font-medium break-all">{m.model_name}</div>
                                  <div className="text-xs text-muted-foreground">{m.provider}</div>
                                </td>
                                <td className="px-3 py-2 text-right tabular-nums">{m.calls.toLocaleString()}</td>
                                <td className="px-3 py-2 text-right tabular-nums">{m.total_tokens.toLocaleString()}</td>
                                <td className="px-3 py-2 text-right tabular-nums">
                                  {/* Gemini reports tokens but no price, so it
                                      shows a quota label rather than $0.00 —
                                      which would read as free when it is in
                                      fact the tightest limit we have. */}
                                  {!m.priced ? (
                                    <span className="text-muted-foreground text-xs">Quota-based</span>
                                  ) : m.cost === null ? (
                                    <span className="text-muted-foreground text-xs">&mdash;</span>
                                  ) : (
                                    "$" + m.cost.toFixed(4)
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>

                    {/* Per-feature, so it is clear which part of the product spends */}
                    {(tokenUsage.by_feature || []).length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        {(tokenUsage.by_feature || []).map((f) => (
                          <span
                            key={f.feature}
                            className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs"
                          >
                            <span className="font-medium">{f.feature}</span>
                            <span className="text-muted-foreground tabular-nums">
                              {f.total_tokens.toLocaleString()}
                            </span>
                          </span>
                        ))}
                      </div>
                    )}

                    {tokenUsage.coverage_note && (
                      <p className="text-xs text-muted-foreground">{tokenUsage.coverage_note}</p>
                    )}
                  </>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        )}

        {false && user?.role === 'super_admin' && (
          <TabsContent value="content-key" className="space-y-6">
            {(() => {
              const status = contentKey.status ?? 'NOT_CONFIGURED';
              const statusConfig: Record<string, { label: string; className: string }> = {
                CONNECTED:      { label: 'Connected',      className: 'bg-emerald-500/15 text-emerald-500 border-emerald-500/30' },
                NOT_CONFIGURED: { label: 'Not Configured', className: 'bg-muted text-muted-foreground border-border' },
                INVALID_KEY:    { label: 'Invalid Key',    className: 'bg-red-500/15 text-red-400 border-red-500/30' },
                RATE_LIMITED:   { label: 'Rate Limited',   className: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30' },
                OUT_OF_CREDITS: { label: 'Out of Credits', className: 'bg-red-500/15 text-red-400 border-red-500/30' },
                ERROR:          { label: 'Error',          className: 'bg-red-500/15 text-red-400 border-red-500/30' },
              };
              const sc = statusConfig[status] ?? statusConfig['NOT_CONFIGURED'];
              const usageSource = contentUsage?.source;
              const outOfCredits = contentUsage?.status === 'OUT_OF_CREDITS';
              const today = contentUsage?.today ?? { input_tokens: 0, output_tokens: 0, total_tokens: 0, estimated_cost_usd: 0 };
              const month = contentUsage?.month ?? { input_tokens: 0, output_tokens: 0, total_tokens: 0, estimated_cost_usd: 0 };
              const fmtUsd = (n: number | null | undefined) => `$${Number(n ?? 0).toFixed(4)}`;
              const adminStatus = outOfCredits ? 'OUT_OF_CREDITS' : (contentKey.admin_key_status ?? 'NOT_CONFIGURED');
              const adminSc = statusConfig[adminStatus] ?? statusConfig['NOT_CONFIGURED'];

              return (
                <>
                  {/* ── API key card ── */}
                  <Card className="border border-border relative overflow-hidden bg-muted/10">
                    <div className="absolute top-0 left-0 right-0 h-0.5" style={{ background: '#D4A04A' }} />
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: '#D4A04A20' }}>
                            <Sparkles className="h-4 w-4" style={{ color: '#D4A04A' }} />
                          </div>
                          <div>
                            <CardTitle className="text-base">Content Generation Key (Claude)</CardTitle>
                            <CardDescription className="text-xs">
                              Powers article writing, humanising, and refurbishing in the Strategy pipeline.
                            </CardDescription>
                          </div>
                        </div>
                        <Badge variant="outline" className={`gap-1.5 px-2.5 py-0.5 font-medium ${sc.className}`}>
                          {sc.label}
                        </Badge>
                      </div>
                    </CardHeader>

                    <CardContent className="space-y-3">
                      {/* Key preview row (configured & not editing) */}
                      {contentKey.configured && !editingContentKey && (
                        <div className="space-y-2">
                          <div className="flex items-center justify-between rounded-md border border-border bg-muted/30 px-3 py-2">
                            <div className="flex items-center gap-2 min-w-0">
                              <Key className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                              <span className="font-mono text-sm text-foreground truncate">
                                {revealedContentKey ?? contentKey.preview ?? '••••••••••••••••'}
                              </span>
                            </div>
                            <div className="flex items-center gap-1 shrink-0 ml-2">
                              <Button
                                size="sm" variant="ghost"
                                className="h-8 px-2.5 gap-1.5 text-muted-foreground hover:text-foreground"
                                disabled={revealingContentKey}
                                onClick={() => revealedContentKey ? setRevealedContentKey(null) : handleRevealContentKey()}
                              >
                                {revealingContentKey ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : revealedContentKey ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                                <span className="text-xs font-medium">{revealedContentKey ? 'Hide' : 'Reveal'}</span>
                              </Button>
                              <Button
                                size="sm" variant="ghost"
                                className="h-8 px-2.5 gap-1.5 text-muted-foreground hover:text-foreground"
                                disabled={revealingContentKey}
                                onClick={handleCopyContentKey}
                              >
                                {contentKeyCopied ? (
                                  <><Check className="h-3.5 w-3.5 text-emerald-500" /><span className="text-xs text-emerald-500 font-medium">Copied</span></>
                                ) : (
                                  <><Copy className="h-3.5 w-3.5" /><span className="text-xs font-medium">Copy</span></>
                                )}
                              </Button>
                              <Button
                                size="sm" variant="ghost"
                                className="h-8 px-2.5 gap-1.5 text-muted-foreground hover:text-foreground"
                                disabled={revealingContentKey}
                                onClick={handleEditContentKey}
                              >
                                <Pencil className="h-3.5 w-3.5" /><span className="text-xs font-medium">Edit</span>
                              </Button>
                              <Button
                                size="sm" variant="ghost"
                                className="h-8 px-2.5 gap-1.5 text-red-400 hover:text-red-300"
                                disabled={savingContentKey}
                                onClick={handleDeleteContentKey}
                              >
                                <Trash2 className="h-3.5 w-3.5" /><span className="text-xs font-medium">Delete</span>
                              </Button>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Edit / create form */}
                      {(!contentKey.configured || editingContentKey) && (
                        <div className="space-y-3">
                          <div className="space-y-1.5">
                            <Label className="text-xs">Claude API Key</Label>
                            <div className="relative">
                              <Input
                                type={showContentKey ? 'text' : 'password'}
                                placeholder={contentKey.configured ? 'Enter new key to replace…' : 'sk-ant-api…'}
                                value={contentKeyInput}
                                autoFocus={editingContentKey}
                                onChange={e => setContentKeyInput(e.target.value)}
                                className="pr-10 font-mono text-sm"
                              />
                              <button
                                type="button"
                                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                onClick={() => setShowContentKey(v => !v)}
                              >
                                {showContentKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                              </button>
                            </div>
                          </div>
                          <div className="flex gap-2">
                            <Button size="sm" disabled={savingContentKey} onClick={handleSaveContentKey} className="gap-1.5">
                              {savingContentKey ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
                              Save
                            </Button>
                            {editingContentKey && (
                              <Button
                                size="sm" variant="ghost"
                                onClick={() => {
                                  setEditingContentKey(false);
                                  setContentKeyInput('');
                                  setShowContentKey(false);
                                }}
                              >
                                Cancel
                              </Button>
                            )}
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  {/* ── Admin (usage-reporting) key card ── */}
                  <Card className="border border-border relative overflow-hidden bg-muted/10">
                    <div className="absolute top-0 left-0 right-0 h-0.5" style={{ background: '#D4A04A' }} />
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: '#D4A04A20' }}>
                            <Activity className="h-4 w-4" style={{ color: '#D4A04A' }} />
                          </div>
                          <div>
                            <CardTitle className="text-base">Usage Reporting Key (Admin)</CardTitle>
                            <CardDescription className="text-xs">
                              Fetches live token usage and cost directly from Anthropic. Does not generate content.
                            </CardDescription>
                          </div>
                        </div>
                        <Badge variant="outline" className={`gap-1.5 px-2.5 py-0.5 font-medium ${adminSc.className}`}>
                          {adminSc.label}
                        </Badge>
                      </div>
                    </CardHeader>

                    <CardContent className="space-y-3">
                      {contentKey.admin_key_configured && !editingAdminKey && (
                        <div className="flex items-center justify-between rounded-md border border-border bg-muted/30 px-3 py-2">
                          <div className="flex items-center gap-2 min-w-0">
                            <Key className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                            <span className="font-mono text-sm text-foreground truncate">
                              {revealedAdminKey ?? contentKey.admin_key_preview ?? '••••••••••••••••'}
                            </span>
                          </div>
                          <div className="flex items-center gap-1 shrink-0 ml-2">
                            <Button
                              size="sm" variant="ghost"
                              className="h-8 px-2.5 gap-1.5 text-muted-foreground hover:text-foreground"
                              disabled={revealingAdminKey}
                              onClick={() => revealedAdminKey ? setRevealedAdminKey(null) : handleRevealAdminKey()}
                            >
                              {revealingAdminKey ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : revealedAdminKey ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                              <span className="text-xs font-medium">{revealedAdminKey ? 'Hide' : 'Reveal'}</span>
                            </Button>
                            <Button
                              size="sm" variant="ghost"
                              className="h-8 px-2.5 gap-1.5 text-muted-foreground hover:text-foreground"
                              disabled={revealingAdminKey}
                              onClick={handleCopyAdminKey}
                            >
                              {adminKeyCopied ? (
                                <><Check className="h-3.5 w-3.5 text-emerald-500" /><span className="text-xs text-emerald-500 font-medium">Copied</span></>
                              ) : (
                                <><Copy className="h-3.5 w-3.5" /><span className="text-xs font-medium">Copy</span></>
                              )}
                            </Button>
                            <Button
                              size="sm" variant="ghost"
                              className="h-8 px-2.5 gap-1.5 text-muted-foreground hover:text-foreground"
                              disabled={revealingAdminKey}
                              onClick={handleEditAdminKey}
                            >
                              <Pencil className="h-3.5 w-3.5" /><span className="text-xs font-medium">Edit</span>
                            </Button>
                            <Button
                              size="sm" variant="ghost"
                              className="h-8 px-2.5 gap-1.5 text-red-400 hover:text-red-300"
                              disabled={savingContentKey}
                              onClick={handleDeleteContentKey}
                            >
                              <Trash2 className="h-3.5 w-3.5" /><span className="text-xs font-medium">Delete</span>
                            </Button>
                          </div>
                        </div>
                      )}

                      {(!contentKey.admin_key_configured || editingAdminKey) && (
                        <div className="space-y-3">
                          <div className="space-y-1.5">
                            <Label className="text-xs">Anthropic Admin Key</Label>
                            <div className="relative">
                              <Input
                                type={showAdminKey ? 'text' : 'password'}
                                placeholder={contentKey.admin_key_configured ? 'Enter new key to replace…' : 'sk-ant-admin…'}
                                value={adminKeyInput}
                                autoFocus={editingAdminKey}
                                onChange={e => setAdminKeyInput(e.target.value)}
                                className="pr-10 font-mono text-sm"
                              />
                              <button
                                type="button"
                                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                onClick={() => setShowAdminKey(v => !v)}
                              >
                                {showAdminKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                              </button>
                            </div>
                          </div>
                          <div className="flex gap-2">
                            <Button size="sm" disabled={savingAdminKey} onClick={handleSaveAdminKey} className="gap-1.5">
                              {savingAdminKey ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
                              Save
                            </Button>
                            {editingAdminKey && (
                              <Button
                                size="sm" variant="ghost"
                                onClick={() => { setEditingAdminKey(false); setAdminKeyInput(''); setShowAdminKey(false); }}
                              >
                                Cancel
                              </Button>
                            )}
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  {/* ── Usage dashboard ── */}
                  <Card className="border border-border">
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <div>
                          <CardTitle className="flex items-center gap-2">
                            <Activity className="h-4 w-4" />Token Usage
                            {usageSource === 'anthropic_api' && !outOfCredits && (
                              <Badge variant="outline" className="gap-1.5 px-2 py-0 text-[11px] bg-emerald-500/15 text-emerald-500 border-emerald-500/30">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />Live
                              </Badge>
                            )}
                          </CardTitle>
                          <CardDescription>Live token usage &amp; estimated cost from Anthropic.</CardDescription>
                        </div>
                        <div className="flex items-center gap-2">
                          {usageSource === 'anthropic_api' && !outOfCredits && (
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-8 px-2 gap-1.5 text-muted-foreground hover:text-foreground"
                              disabled={loadingContentUsage}
                              onClick={loadContentKeyUsage}
                            >
                              <RefreshCw className={`h-3.5 w-3.5 ${loadingContentUsage ? 'animate-spin' : ''}`} />
                              <span className="text-xs font-medium">Sync Now</span>
                            </Button>
                          )}
                          {loadingContentUsage && usageSource !== 'anthropic_api' && (
                            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                          )}
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {(!usageSource || usageSource === 'not_configured') ? (
                        <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/10 p-4 text-sm text-yellow-600 dark:text-yellow-400">
                          Configure an Admin API Key above to enable live usage reporting.
                        </div>
                      ) : outOfCredits ? (
                        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm font-medium text-red-500">
                          Anthropic credits exhausted. Recharge your account to resume generation.
                        </div>
                      ) : usageSource === 'error' ? (
                        <div className="rounded-lg border border-orange-500/30 bg-orange-500/10 p-4 text-sm text-orange-500">
                          Could not reach Anthropic. Check your Admin Key and try again.
                        </div>
                      ) : (
                        <>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {/* Today's Usage */}
                            <div className="rounded-lg border border-border bg-muted/10 p-4">
                              <h4 className="text-sm font-semibold mb-3">Today's Usage</h4>
                              <div className="space-y-2 text-sm">
                                <div className="flex justify-between"><span className="text-muted-foreground">Input Tokens</span><span className="font-medium">{formatTokens(today.input_tokens)}</span></div>
                                <div className="flex justify-between"><span className="text-muted-foreground">Output Tokens</span><span className="font-medium">{formatTokens(today.output_tokens)}</span></div>
                                <div className="flex justify-between"><span className="text-muted-foreground">Total Tokens</span><span className="font-medium">{formatTokens(today.total_tokens)}</span></div>
                                {today.caching_savings_usd > 0 && (
                                  <div className="flex justify-between text-xs text-muted-foreground">
                                    <span>Prompt Caching Savings</span>
                                    <span className="text-emerald-500 font-medium">
                                      {fmtUsd(today.caching_savings_usd)} ({today.caching_savings_pct}%)
                                    </span>
                                  </div>
                                )}
                                <Separator className="my-1" />
                                <div className="flex justify-between"><span className="text-muted-foreground">Estimated Cost</span><span className="font-semibold text-emerald-500">{fmtUsd(today.estimated_cost_usd)}</span></div>
                              </div>
                            </div>

                            {/* This Month */}
                            <div className="rounded-lg border border-border bg-muted/10 p-4">
                              <h4 className="text-sm font-semibold mb-3">This Month</h4>
                              <div className="space-y-2 text-sm">
                                <div className="flex justify-between"><span className="text-muted-foreground">Input Tokens</span><span className="font-medium">{formatTokens(month.input_tokens)}</span></div>
                                <div className="flex justify-between"><span className="text-muted-foreground">Output Tokens</span><span className="font-medium">{formatTokens(month.output_tokens)}</span></div>
                                <div className="flex justify-between"><span className="text-muted-foreground">Total Tokens</span><span className="font-medium">{formatTokens(month.total_tokens)}</span></div>
                                {month.caching_savings_usd > 0 && (
                                  <div className="flex justify-between text-xs text-muted-foreground">
                                    <span>Prompt Caching Savings</span>
                                    <span className="text-emerald-500 font-medium">
                                      {fmtUsd(month.caching_savings_usd)} ({month.caching_savings_pct}%)
                                    </span>
                                  </div>
                                )}
                                <Separator className="my-1" />
                                <div className="flex justify-between"><span className="text-muted-foreground">Estimated Cost</span><span className="font-semibold text-emerald-500">{fmtUsd(month.estimated_cost_usd)}</span></div>
                              </div>
                            </div>
                          </div>

                          <div className="flex flex-wrap items-center gap-x-6 gap-y-1 text-xs text-muted-foreground pt-1">
                            <span>Last synced: {formatRelativeTime(contentUsage?.last_synced)}</span>
                          </div>
                        </>
                      )}
                    </CardContent>
                  </Card>
                </>
              );
            })()}
          </TabsContent>
        )}

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
                onValueChange={(value: "admin" | "user" | "client") => setInviteRole(value)}
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
                  {/* Only admins may hand out Admin or Client. A regular user can
                      invite peers, but creating an admin is privilege escalation and
                      creating a client grants domain access — both admin decisions.
                      The backend enforces this too; hiding the options here keeps a
                      user from picking something that would only come back a 403. */}
                  {!isTeamMember && (
                    <>
                      <SelectItem value="admin">
                        <div className="flex items-center gap-2">
                          <Crown className="h-4 w-4" />
                          <span className="font-medium">Admin</span>
                        </div>
                      </SelectItem>
                      <SelectItem value="client">
                        <div className="flex items-center gap-2">
                          <ShieldCheck className="h-4 w-4" />
                          <span className="font-medium">Client</span>
                        </div>
                      </SelectItem>
                    </>
                  )}
                </SelectContent>
              </Select>
              <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                {inviteRole === 'admin' ? (
                  <Crown className="h-3 w-3" />
                ) : inviteRole === 'client' ? (
                  <ShieldCheck className="h-3 w-3" />
                ) : (
                  <User className="h-3 w-3" />
                )}
                <span>{roleMeta[inviteRole].description}</span>
              </div>
            </div>
            {inviteRole === 'client' && (
              <div className="space-y-2">
                <Label htmlFor="invite-domain">Domain (client sees only this)</Label>
                <Select value={inviteDomainId} onValueChange={setInviteDomainId}>
                  <SelectTrigger id="invite-domain">
                    <SelectValue placeholder="Select a domain" />
                  </SelectTrigger>
                  <SelectContent>
                    {domains.map((domain) => (
                      <SelectItem key={domain.id} value={String(domain.id)}>
                        {domain.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
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

      <AddDomainDialog
        open={addDomainDialogOpen}
        onOpenChange={setAddDomainDialogOpen}
        onDomainAdded={() => loadDomains()}
      />

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
