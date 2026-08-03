import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient } from "@/services/api";
import { useDomainStore } from "@/stores/domainStore";
import { useSidebar } from "@/contexts/SidebarContext";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/hooks/use-toast";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Search,
  Download,
  RefreshCw,
  Trash2,
  Columns,
  List,
  LayoutGrid,
  Monitor,
  Smartphone,
  Star,
  TrendingUp,
  TrendingDown,
  Info,
  Tag,
  ExternalLink,
  BarChart3,
  ArrowRight,
  X,
  Plus,
  SearchX,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Upload,
  FileUp,
  ArrowLeft,
  ArrowUp,
  ArrowDown,
  ArrowUpDown,
} from "lucide-react";

// Types matching the backend SeoKeywordRankSerializer
interface SeoKeyword {
  id: number;
  keyword: number;
  keyword_text: string;
  domain: number;
  domain_name: string;
  domain_url: string;
  platform: string;
  rank_now: number;
  top_rank: number | null;
  rank_since_start: number;
  day_val: number;
  day_mark: string;
  week_val: number;
  week_mark: string;
  half_month_val: number;
  half_month_mark: string;
  month_val: number;
  month_mark: string;
  status_from_start: string;
  featured_snippet: boolean;
  knowledge_panel: boolean;
  ads: boolean;
  review: boolean;
  total_rating: string;
  total_review: string;
  snippets_details: Record<string, any>;
  keyword_snippet: Record<string, any>;
  gsc_clicks: number;
  gsc_impressions: number;
  site_url: string;
  target_url: string;
  search_results: string;
  search_volume: number | null;
  region: string;
  isocode: string;
  language_code: string;
  auto_call_status: string;
  auto_refresh_count: number;
  last_ranked_date: string | null;
  cannibalisation: any[];
  tags: string[];
  favour: number;
  created_at: string;
  modified_at: string;
}

interface OverviewData {
  today: any;
  yesterday: any;
  best: any;
  comparison: Array<{ status: string; today: number; yesterday: number; best: number }>;
}

type SortKey = "rank" | "volume" | "best" | "clicks" | "impressions";

// Columns where a SMALLER number is better, so the first click sorts ascending.
// Everything else (volume, clicks, impressions) leads with the biggest number.
const ASCENDING_FIRST: SortKey[] = ["rank", "best"];

// Clicks and impressions come from Search Console, which finalises data on a
// ~2-3 day lag — so the sync reads 7 complete days ending 3 days back rather
// than the last 7 calendar days. Surfaced as a header tooltip because a bare
// "CLKS 174" invites the reader to assume it means all-time, or today.
const GSC_WINDOW_HINT = "Search Console data from the last 7 days";

// Helper: format keyword for UI display
function mapKeywordForUI(kw: SeoKeyword) {
  return {
    id: kw.id,
    keyword: kw.keyword_text,
    url: kw.site_url || kw.domain_url || '',
    rank: kw.rank_now > 0 && kw.rank_now <= 100 ? kw.rank_now : null,
    rankDisplay: kw.rank_now === 0 ? 'NR' : kw.rank_now > 100 ? `>${100}` : undefined,
    volume: kw.search_volume,
    best: kw.top_rank,
    clicks: kw.gsc_clicks,
    impressions: kw.gsc_impressions,
    change1d: kw.day_mark !== '-' ? { value: Math.abs(kw.day_val), direction: kw.day_mark } : null,
    change7d: kw.week_mark !== '-' ? { value: Math.abs(kw.week_val), direction: kw.week_mark } : null,
    change15d: kw.half_month_mark !== '-' ? { value: Math.abs(kw.half_month_val), direction: kw.half_month_mark } : null,
    serp: kw.featured_snippet || kw.knowledge_panel || kw.ads ? 'Yes' : null,
    tags: kw.tags || [],
    favour: kw.favour || 0,
    date: kw.last_ranked_date ? new Date(kw.last_ranked_date).toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' }) : '-',
    timeAgo: kw.last_ranked_date ? getTimeAgo(new Date(kw.last_ranked_date)) : '',
    country: kw.isocode?.toUpperCase() || 'US',
    region: kw.region || '',
    platform: kw.platform,
    autoCallStatus: kw.auto_call_status,
  };
}

function getTimeAgo(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  if (diffHours < 1) return 'just now';
  if (diffHours < 24) return `${diffHours} hours ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays} days ago`;
}

interface ColumnVisibility {
  volume: boolean;
  best: boolean;
  clicks: boolean;
  impressions: boolean;
  "1d": boolean;
  "7d": boolean;
  "15d": boolean;
  serp: boolean;
  tags: boolean;
  date: boolean;
}

const SeoRankings = () => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const [rankFilter, setRankFilter] = useState<"all" | "top3" | "top10" | "top50" | "nr">("all");
  // Sortable columns. `null` key = the API's own ordering, which is the default
  // so the table looks unchanged until the user asks for a sort.
  const [sortKey, setSortKey] = useState<SortKey | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [viewMode, setViewMode] = useState<"list" | "grid">("list");
  const [showOverview, setShowOverview] = useState(true);
  const [selectedKeywords, setSelectedKeywords] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshProgress, setRefreshProgress] = useState(0);
  const [refreshCompleted, setRefreshCompleted] = useState(0);
  const [refreshTotal, setRefreshTotal] = useState(0);
  const [seoKeywords, setSeoKeywords] = useState<ReturnType<typeof mapKeywordForUI>[]>([]);
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [gridTagPages, setGridTagPages] = useState<Record<string, number>>({});
  // Selectable page size. Was a fixed 10, which meant a domain with 200
  // keywords took twenty clicks to review.
  const [keywordsPerPage, setKeywordsPerPage] = useState(25);
  const KEYWORDS_PER_PAGE = keywordsPerPage;
  const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const activeDomainRef = useRef<string>("");

  // Tag dialog state — tagKeywordIds tracks which keywords the tag dialog
  // operates on, kept separate from the table-checkbox selectedKeywords so
  // that opening the inline "ADD" tag editor doesn't clear the user's row
  // selection (mirrors how RankMaxx passes IDs directly to ManageTagFullPage).
  const [tagDialogOpen, setTagDialogOpen] = useState(false);
  const [tagInput, setTagInput] = useState("");
  const [pendingTags, setPendingTags] = useState<string[]>([]);
  const [allDomainTags, setAllDomainTags] = useState<string[]>([]);
  const [tagLoading, setTagLoading] = useState(false);
  const [tagKeywordIds, setTagKeywordIds] = useState<number[]>([]);

  // Delete dialog state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);

  // Import dialog state
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [importLoading, setImportLoading] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importKeywordsText, setImportKeywordsText] = useState("");
  const [importPlatform, setImportPlatform] = useState("desktop");
  const [importRegion, setImportRegion] = useState("google.com");
  const [importIsocode, setImportIsocode] = useState("us");
  const [importLanguageCode, setImportLanguageCode] = useState("en");
  const [importResult, setImportResult] = useState<{
    success: boolean;
    keyword_created_count: number;
    keyword_skipped_count: number;
    seo_created_count: number;
    seo_skipped_count: number;
    total_processed: number;
  } | null>(null);

  // Add Keyword dialog state (RankMax-style)
  const [addKeywordDialogOpen, setAddKeywordDialogOpen] = useState(false);
  const [addKeywordLoading, setAddKeywordLoading] = useState(false);
  const [addKeywordText, setAddKeywordText] = useState("");
  const [addKeywordInputMode, setAddKeywordInputMode] = useState<"text" | "csv">("text");
  const [addKeywordFile, setAddKeywordFile] = useState<File | null>(null);
  const [addKeywordUrlSlug, setAddKeywordUrlSlug] = useState("");
  const [addKeywordRegion, setAddKeywordRegion] = useState("google.com");
  const [addKeywordLanguage, setAddKeywordLanguage] = useState("en");
  const [addKeywordPlatform, setAddKeywordPlatform] = useState("desktop");
  const [addKeywordTagsEnabled, setAddKeywordTagsEnabled] = useState(true);
  const [addKeywordTagInput, setAddKeywordTagInput] = useState("");
  const [addKeywordTags, setAddKeywordTags] = useState<string[]>([]);
  const [addKeywordResult, setAddKeywordResult] = useState<{
    success: boolean;
    seo_created_count: number;
    seo_skipped_count: number;
    total_processed: number;
  } | null>(null);

  const { toast } = useToast();
  const { user } = useAuth();

  // Use the domain store (same source as the sidebar DomainSelector)
  const { isOpen: sidebarOpen } = useSidebar();
  const { selectedDomain } = useDomainStore();
  const activeDomainId = selectedDomain ? String(selectedDomain.id) : "";
  activeDomainRef.current = activeDomainId;

  // Stop polling helper
  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  }, []);

  // Start polling refresh status via /seo/refresh-status/ endpoint
  const pollCountRef = useRef(0);
  const lastCompletedRef = useRef(-1);
  const staleCountRef = useRef(0);
  const MAX_POLL_ATTEMPTS = 2160; // 2160 * 5s = 3 hours max (supports 3000+ keywords)
  const MAX_STALE_POLLS = 6; // 6 * 5s = 30s with no progress → consider stale

  const resetRefreshState = useCallback(() => {
    setRefreshing(false);
    setRefreshProgress(0);
    setRefreshCompleted(0);
    setRefreshTotal(0);
  }, []);

  const startRefreshPolling = useCallback((domainId: string) => {
    // Prevent duplicate polling
    if (pollIntervalRef.current) return;
    setRefreshing(true);
    pollCountRef.current = 0;
    lastCompletedRef.current = -1;
    staleCountRef.current = 0;

    pollIntervalRef.current = setInterval(async () => {
      pollCountRef.current += 1;

      // Safety: stop polling after max attempts
      if (pollCountRef.current > MAX_POLL_ATTEMPTS) {
        stopPolling();
        resetRefreshState();
        return;
      }

      try {
        const statusRes = await apiClient.getSeoRefreshStatus(domainId) as {
          refreshing: boolean; total: number; completed: number; progress: number; status: string;
          running?: number; succeeded?: number; failed?: number; error?: string | null;
        };

        setRefreshTotal(statusRes.total);
        setRefreshCompleted(statusRes.completed);
        setRefreshProgress(statusRes.progress);

        // SERP-service failure (e.g. ScrapingDog/DataBlue rejected every
        // request — invalid key, billing limit, provider down). Stop polling
        // and surface the message instead of silently showing "completed".
        if (statusRes.status === 'error') {
          stopPolling();
          toast({
            title: "Refresh failed",
            description: statusRes.error || "SERP service is currently unavailable. Please try again after some time.",
            variant: "destructive",
          });
          resetRefreshState();
          return;
        }

        // Detect stale refresh: only count as stale when no keywords are actively running
        // Each keyword can take 30s+ (10 paginated API calls), so don't treat as stale
        // while the backend still has keywords in 'busy'/'avail' status
        const hasRunningKeywords = (statusRes.running ?? 0) > 0 || statusRes.refreshing;
        if (statusRes.completed === lastCompletedRef.current && !hasRunningKeywords) {
          staleCountRef.current += 1;
        } else {
          if (statusRes.completed !== lastCompletedRef.current) {
            lastCompletedRef.current = statusRes.completed;
          }
          staleCountRef.current = 0;
        }

        // If no progress for MAX_STALE_POLLS consecutive checks, treat as stale
        if (staleCountRef.current >= MAX_STALE_POLLS) {
          stopPolling();
          resetRefreshState();
          return;
        }

        if (!statusRes.refreshing || statusRes.status === 'done') {
          // Refresh complete — stop polling, fetch final data
          stopPolling();
          setRefreshProgress(100);

          const [keywordsRes, overviewRes] = await Promise.all([
            apiClient.getSeoKeywords({ domain_id: domainId }) as Promise<SeoKeyword[]>,
            apiClient.getSeoDomainOverview(domainId) as Promise<OverviewData>,
          ]);
          setSeoKeywords((keywordsRes || []).map(mapKeywordForUI));
          setOverview(overviewRes || null);

          // Hide progress bar after brief delay
          setTimeout(() => resetRefreshState(), 2000);
        }
      } catch {
        // Keep polling on transient network errors
      }
    }, 5000);
  }, [stopPolling, resetRefreshState, toast]);

  // Cleanup polling on unmount or domain change
  useEffect(() => {
    return () => {
      stopPolling();
      resetRefreshState();
    };
  }, [stopPolling, resetRefreshState, activeDomainId]);

  // Fetch SEO data — also detects active refresh on page load/reload
  const fetchSeoData = useCallback(async () => {
    if (!activeDomainId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const [keywordsRes, overviewRes] = await Promise.all([
        apiClient.getSeoKeywords({ domain_id: activeDomainId }) as Promise<SeoKeyword[]>,
        apiClient.getSeoDomainOverview(activeDomainId) as Promise<OverviewData>,
      ]);
      setSeoKeywords((keywordsRes || []).map(mapKeywordForUI));
      setOverview(overviewRes || null);

      // Check the refresh-status endpoint to see if a refresh is actually in progress.
      // Do two checks 5s apart to verify progress is actually moving (not stale state).
      if (!pollIntervalRef.current) {
        try {
          const firstCheck = await apiClient.getSeoRefreshStatus(activeDomainId) as {
            refreshing: boolean; total: number; completed: number; progress: number; status: string;
          };
          if (firstCheck.refreshing && firstCheck.status !== 'done') {
            // If already partially complete (completed > 0), it's likely real
            if (firstCheck.completed > 0) {
              setRefreshTotal(firstCheck.total);
              setRefreshCompleted(firstCheck.completed);
              setRefreshProgress(firstCheck.progress);
              startRefreshPolling(activeDomainId);
            } else {
              // completed === 0: could be stale. Wait 5s and re-check
              await new Promise(r => setTimeout(r, 5000));
              // Bail if domain changed while waiting
              if (activeDomainRef.current !== activeDomainId) return;
              const secondCheck = await apiClient.getSeoRefreshStatus(activeDomainId) as {
                refreshing: boolean; total: number; completed: number; progress: number; status: string;
              };
              if (secondCheck.refreshing && secondCheck.status !== 'done' &&
                  (secondCheck.completed > firstCheck.completed || secondCheck.progress > firstCheck.progress)) {
                setRefreshTotal(secondCheck.total);
                setRefreshCompleted(secondCheck.completed);
                setRefreshProgress(secondCheck.progress);
                startRefreshPolling(activeDomainId);
              }
              // If no progress between checks → stale, don't start polling
            }
          }
        } catch {
          // No active refresh or endpoint error — ignore
        }
      }
    } catch (err) {
      console.error("Failed to fetch SEO data:", err);
    } finally {
      setLoading(false);
    }
  }, [activeDomainId, startRefreshPolling]);

  useEffect(() => {
    fetchSeoData();
  }, [fetchSeoData]);

  const handleRefresh = async () => {
    if (!activeDomainId || refreshing) return;
    setRefreshing(true);
    setRefreshProgress(0);
    setRefreshCompleted(0);
    setRefreshTotal(0);
    try {
      await apiClient.triggerSeoRanking({ domain_id: Number(activeDomainId) });
      startRefreshPolling(activeDomainId);
    } catch (err) {
      console.error("Failed to trigger ranking:", err);
      setRefreshing(false);
    }
  };

  // ---------- Favourite Toggle ----------
  const handleToggleFavourite = async (kwId: number, currentFavour: number) => {
    const newValue = currentFavour ? 0 : 1;
    try {
      await apiClient.toggleSeoKeywordFavourite({ id: kwId, value: newValue });
      setSeoKeywords(prev =>
        prev.map(kw => kw.id === kwId ? { ...kw, favour: newValue } : kw)
      );
    } catch {
      toast({ title: "Error", description: "Failed to update favourite status", variant: "destructive" });
    }
  };

  // ---------- Delete ----------
  const handleOpenDelete = () => {
    if (selectedKeywords.length === 0) {
      toast({ title: "No selection", description: "Select at least one keyword to delete" });
      return;
    }
    setDeleteDialogOpen(true);
  };

  const handleConfirmDelete = async () => {
    setDeleteLoading(true);
    try {
      await apiClient.bulkDeleteSeoKeywords(selectedKeywords);
      setSeoKeywords(prev => prev.filter(kw => !selectedKeywords.includes(kw.id)));
      setSelectedKeywords([]);
      setDeleteDialogOpen(false);
      toast({ title: "Deleted", description: `${selectedKeywords.length} keyword(s) deleted successfully` });
    } catch {
      toast({ title: "Error", description: "Failed to delete keywords", variant: "destructive" });
    } finally {
      setDeleteLoading(false);
    }
  };

  // ---------- Tag Management ----------
  const handleOpenTagDialog = async () => {
    if (selectedKeywords.length === 0) {
      toast({ title: "No selection", description: "Select at least one keyword to add tags" });
      return;
    }
    const ids = [...selectedKeywords];
    setTagKeywordIds(ids);
    setTagDialogOpen(true);
    setPendingTags([]);
    setTagInput("");
    // Fetch existing tags for the domain
    try {
      const res = await apiClient.getSeoKeywordTags(activeDomainId, ids) as {
        all_tags: string[]; common_tags: string[];
      };
      setAllDomainTags(res.all_tags || []);
      setPendingTags(res.common_tags || []);
    } catch {
      setAllDomainTags([]);
    }
  };

  // Validate & commit a single tag string into pendingTags.
  // Returns the updated pendingTags array (needed by handleSaveTags to
  // capture the value synchronously before the async save).
  const commitTag = (raw: string, currentTags: string[]): string[] => {
    const tag = raw.trim().toLowerCase();
    if (!tag) return currentTags;
    if (!/^[a-zA-Z0-9\s-]+$/.test(tag)) {
      toast({ title: "Invalid tag", description: "Tags can only contain letters, numbers, spaces and hyphens" });
      return currentTags;
    }
    if (currentTags.length >= 20) {
      toast({ title: "Limit reached", description: "Maximum 20 tags per keyword" });
      return currentTags;
    }
    if (currentTags.includes(tag)) return currentTags;
    return [...currentTags, tag];
  };

  const handleAddTag = () => {
    const updated = commitTag(tagInput, pendingTags);
    if (updated !== pendingTags) setPendingTags(updated);
    setTagInput("");
  };

  const handleRemovePendingTag = (tag: string) => {
    setPendingTags(prev => prev.filter(t => t !== tag));
  };

  const handleSaveTags = async () => {
    setTagLoading(true);

    // Auto-commit whatever is still in the input field so the user
    // doesn't lose typed text when clicking "Save Tags" without
    // pressing Enter first (mirrors RankMaxx handleInputBlur behaviour).
    let finalTags = [...pendingTags];
    if (tagInput.trim()) {
      finalTags = commitTag(tagInput, finalTags);
      setTagInput("");
      setPendingTags(finalTags);
    }

    const idsToSave = [...tagKeywordIds];
    const tagsToSave = [...finalTags];
    const bulkMode: 'merge' | 'replace' =
      idsToSave.length > 1 ? 'merge' : 'replace';

    try {
      await apiClient.updateSeoKeywordTags({
        ids: idsToSave,
        tags: tagsToSave,
        mode: bulkMode,
      });

      setTagDialogOpen(false);
      setTagKeywordIds([]);
      toast({ title: "Tags updated", description: `Tags applied to ${idsToSave.length} keyword(s)` });

      // Re-fetch keywords from backend so the UI is always in sync with the
      // database (mirrors RankMaxx grid-view behaviour which does a full
      // tableUpdate after every tag save).
      if (activeDomainId) {
        try {
          const keywordsRes = await apiClient.getSeoKeywords({ domain_id: activeDomainId }) as SeoKeyword[];
          setSeoKeywords((keywordsRes || []).map(mapKeywordForUI));
        } catch {
          // Fall back to optimistic local update if re-fetch fails
          setSeoKeywords(prev =>
            prev.map(kw => {
              if (!idsToSave.includes(kw.id)) return kw;
              if (bulkMode === 'replace') {
                return { ...kw, tags: [...tagsToSave] };
              }
              const existing = kw.tags || [];
              return { ...kw, tags: Array.from(new Set([...existing, ...tagsToSave])) };
            })
          );
        }
      }
    } catch {
      toast({ title: "Error", description: "Failed to update tags", variant: "destructive" });
    } finally {
      setTagLoading(false);
    }
  };

  // ---------- Inline Tag Add (from TAGS column "ADD" click) ----------
  const handleInlineTagOpen = async (kwId: number) => {
    setTagKeywordIds([kwId]);
    setTagDialogOpen(true);
    setPendingTags([]);
    setTagInput("");
    // Load tags for the single keyword
    try {
      const res = await apiClient.getSeoKeywordTags(activeDomainId, [kwId]) as {
        all_tags: string[]; common_tags: string[];
      };
      setAllDomainTags(res.all_tags || []);
      // For a single keyword, load its existing tags
      const kw = seoKeywords.find(k => k.id === kwId);
      setPendingTags(kw?.tags || []);
    } catch {
      setAllDomainTags([]);
    }
  };

  // ---------- Group Tag Open (Grid View group card header) ----------
  const handleGroupTagOpen = async (kwIds: number[]) => {
    if (kwIds.length === 0) return;
    setTagKeywordIds(kwIds);
    setTagDialogOpen(true);
    setPendingTags([]);
    setTagInput("");
    try {
      const res = await apiClient.getSeoKeywordTags(activeDomainId, kwIds) as {
        all_tags: string[]; common_tags: string[];
      };
      setAllDomainTags(res.all_tags || []);
      setPendingTags(res.common_tags || []);
    } catch {
      setAllDomainTags([]);
    }
  };

  // Filter keywords by search + rank-range filter (from the Comparison card).
  // `kw.rank` holds the live position when it's 1-100, otherwise null
  // (rank 0 / not-ranked / >100). Top buckets reuse that; "nr" = no rank.
  const matchesRankFilter = (kw: typeof seoKeywords[number]) => {
    switch (rankFilter) {
      case "top3": return kw.rank != null && kw.rank <= 3;
      case "top10": return kw.rank != null && kw.rank <= 10;
      case "top50": return kw.rank != null && kw.rank <= 50;
      case "nr": return kw.rank == null;
      default: return true;
    }
  };
  const matchesSearch = (kw: typeof seoKeywords[number]) =>
    kw.keyword.toLowerCase().includes(searchQuery.toLowerCase());

  // Sorting is applied to the FILTERED list rather than to the current page, so
  // "best rank" means best across all 290 keywords, not just the 25 on screen.
  // Export and select-all read the same list, so they stay in step.
  //
  // Unranked keywords (rank == null) and keywords with no volume (NA) always
  // sink to the bottom in BOTH directions — they carry no value to compare, so
  // letting them lead an ascending sort would bury the rows the user wants.
  const sortedKeywords = (() => {
    const rows = seoKeywords.filter(kw => matchesSearch(kw) && matchesRankFilter(kw));
    if (!sortKey) return rows;

    const valueOf = (kw: typeof seoKeywords[number]) => {
      switch (sortKey) {
        case "rank": return kw.rank;
        case "volume": return kw.volume;
        case "best": return kw.best;
        case "clicks": return kw.clicks;
        case "impressions": return kw.impressions;
        default: return null;
      }
    };

    return [...rows].sort((a, b) => {
      const av = valueOf(a);
      const bv = valueOf(b);
      const aMissing = av == null;
      const bMissing = bv == null;
      if (aMissing && bMissing) return 0;
      if (aMissing) return 1;
      if (bMissing) return -1;
      return sortDir === "asc" ? Number(av) - Number(bv) : Number(bv) - Number(av);
    });
  })();

  const filteredKeywords = sortedKeywords;

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      // Third click clears the sort and restores the API's ordering.
      if (sortDir === "asc") setSortDir("desc");
      else { setSortKey(null); setSortDir("asc"); }
    } else {
      setSortKey(key);
      setSortDir(ASCENDING_FIRST.includes(key) ? "asc" : "desc");
    }
    setCurrentPage(1);
  };

  const SortableHead = ({ label, sortId, className, hint }: {
    label: string;
    sortId: SortKey;
    className?: string;
    /** Optional tooltip explaining what the column measures. */
    hint?: string;
  }) => {
    const button = (
      <button
        type="button"
        onClick={() => handleSort(sortId)}
        className="inline-flex items-center gap-1 mx-auto hover:text-foreground transition-colors"
        aria-label={`Sort by ${label}${hint ? `. ${hint}` : ""}`}
      >
        {label}
        {sortKey === sortId ? (
          sortDir === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
        ) : (
          <ArrowUpDown className="h-3 w-3 opacity-40" />
        )}
      </button>
    );

    return (
      <TableHead className={className}>
        {hint ? (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>{button}</TooltipTrigger>
              <TooltipContent side="top" className="text-xs">{hint}</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        ) : button}
      </TableHead>
    );
  };

  // Toggle a rank-range filter from the Comparison card and jump to the
  // keyword list so the user immediately sees the filtered data. Clicking
  // the already-active bucket clears the filter.
  const handleRankFilter = (filter: typeof rankFilter) => {
    setRankFilter((prev) => (prev === filter ? "all" : filter));
    if (typeof document !== "undefined") {
      requestAnimationFrame(() => {
        document.getElementById("seo-keywords-section")?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      });
    }
  };

  // Pagination
  const totalPages = Math.ceil(filteredKeywords.length / KEYWORDS_PER_PAGE);
  const paginatedKeywords = filteredKeywords.slice(
    (currentPage - 1) * KEYWORDS_PER_PAGE,
    currentPage * KEYWORDS_PER_PAGE
  );

  // Reset page when search or rank filter changes
  useEffect(() => {
    setCurrentPage(1);
    setGridTagPages({});
  }, [searchQuery, rankFilter, keywordsPerPage]);

  // Column visibility state
  const [visibleColumns, setVisibleColumns] = useState<ColumnVisibility>({
    volume: true,
    best: true,
    clicks: true,
    impressions: true,
    "1d": true,
    "7d": true,
    "15d": true,
    // SERP reads featured_snippet, knowledge_panel and ads — all three are unset
    // on every one of the 3,140 keyword rows, because the SERP provider returns
    // organic results only. Defaulted off and dropped from the column picker
    // below, so it cannot be switched on to reveal a column of dashes. The
    // field and its rendering stay in place for when the data arrives.
    serp: false,
    tags: true,
    date: true,
  });
  const [tempVisibleColumns, setTempVisibleColumns] = useState<ColumnVisibility>({ ...visibleColumns });
  const [columnPopoverOpen, setColumnPopoverOpen] = useState(false);

  const toggleKeywordSelection = (id: number) => {
    const kw = seoKeywords.find((k) => k.id === id);
    if (kw?.favour) return;
    setSelectedKeywords((prev) =>
      prev.includes(id) ? prev.filter((k) => k !== id) : [...prev, id]
    );
  };

  const toggleAllKeywords = () => {
    const selectableIds = filteredKeywords.filter((k) => !k.favour).map((k) => k.id);
    const allSelected = selectableIds.length > 0 && selectableIds.every((id) => selectedKeywords.includes(id));
    if (allSelected) {
      setSelectedKeywords([]);
    } else {
      setSelectedKeywords(selectableIds);
    }
  };

  const toggleGroupKeywords = (groupKeywordIds: number[]) => {
    const selectableIds = groupKeywordIds.filter((id) => {
      const kw = seoKeywords.find((k) => k.id === id);
      return !kw?.favour;
    });
    const allSelected = selectableIds.length > 0 && selectableIds.every((id) => selectedKeywords.includes(id));
    if (allSelected) {
      setSelectedKeywords((prev) => prev.filter((id) => !selectableIds.includes(id)));
    } else {
      setSelectedKeywords((prev) => [...new Set([...prev, ...selectableIds])]);
    }
  };

  // ---------- Export Helpers ----------
  // Quote a value for CSV
  const quoteCsv = (val: any) => {
    if (val === null || val === undefined) return '';
    const str = String(val);
    // escape double quotes
    return `"${str.replace(/"/g, '""')}"`;
  };

  // computeCompetition was removed. It bucketed search volume into Low/Med/High
  // and exported the result in a column headed "Comp", so a reader saw two
  // columns — Volume and Competition — that were the same number twice, one of
  // them relabelled as a metric the provider does not supply.


  const generateKeywordCsv = () => {
    const headers = [
      '#',
      'Keyword',
      'Rank',
      'Best rank',
      '1d',
      '7d',
      '15d',
      'Clicks',
      'Impressions',
      'Search volume',
      // Named for what it is: the page that ranks, not a target the user set.
      // target_url is unset on all 3,140 rows; site_url is what the scrape
      // returns and is populated wherever a rank exists.
      'Ranking URL',
      'Region',
      'Tags',
      'Last ranked',
    ];

    const rows = filteredKeywords.map((kw, idx) => {
      const change1d = kw.change1d ? kw.change1d.value : '-';
      const change7d = kw.change7d ? kw.change7d.value : '-';
      const change15d = kw.change15d ? kw.change15d.value : '-';
      return [
        idx + 1,
        kw.keyword,
        kw.rankDisplay || kw.rank || '',
        kw.best || '',
        change1d,
        change7d,
        change15d,
        kw.clicks ?? '',
        kw.impressions ?? '',
        kw.volume ?? '',
        kw.url || '',
        kw.region || '',
        Array.isArray(kw.tags) ? kw.tags.join('; ') : (kw.tags || ''),
        kw.date || '',
      ];
    });

    const allRows = [headers, ...rows];
    return allRows
      .map((r) => r.map(quoteCsv).join(','))
      .join('\n');
  };

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };

  const handleExportCsv = () => {
    const csv = generateKeywordCsv();
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    downloadBlob(blob, `seo_keywords_${Date.now()}.csv`);
  };

  const handleExportTxt = () => {
    const content = filteredKeywords.map((kw) => kw.keyword).join('\n');
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8;' });
    downloadBlob(blob, `seo_keywords_${Date.now()}.txt`);
  };

  const handleExportPdf = async () => {
    if (!activeDomainId) {
      toast({ title: "No domain", description: "Please select a domain first" });
      return;
    }
    setExporting(true);
    try {
      const blob = await apiClient.exportSeoKeywordsPdf(Number(activeDomainId));
      downloadBlob(blob, `seo_keywords_${Date.now()}.pdf`);
    } catch {
      toast({ title: "Export failed", description: "Could not generate PDF. Please try again.", variant: "destructive" });
    } finally {
      setExporting(false);
    }
  };

  // ---------- Import Keywords ----------
  const handleImportKeywords = async () => {
    if (!activeDomainId) return;
    setImportLoading(true);
    setImportResult(null);

    try {
      let result: any;

      if (importFile) {
        // CSV file upload
        const formData = new FormData();
        formData.append('domain_id', activeDomainId);
        formData.append('file', importFile);
        formData.append('platform', importPlatform);
        formData.append('region', importRegion);
        formData.append('isocode', importIsocode);
        formData.append('language_code', importLanguageCode);
        result = await apiClient.importSeoKeywords(formData);
      } else if (importKeywordsText.trim()) {
        // Text input — split by newlines/commas
        const keywords = importKeywordsText
          .split(/[\n,]+/)
          .map(k => k.trim())
          .filter(k => k.length > 0);

        if (keywords.length === 0) {
          toast({ title: "No keywords", description: "Enter at least one keyword", variant: "destructive" });
          setImportLoading(false);
          return;
        }

        result = await apiClient.importSeoKeywords({
          domain_id: Number(activeDomainId),
          keywords,
          platform: importPlatform,
          region: importRegion,
          isocode: importIsocode,
          language_code: importLanguageCode,
        });
      } else {
        toast({ title: "No input", description: "Upload a CSV file or enter keywords", variant: "destructive" });
        setImportLoading(false);
        return;
      }

      setImportResult(result);
      toast({
        title: "Import complete",
        description: `${result.seo_created_count} keyword(s) added to SEO tracking`,
      });

      // Refresh keyword list
      const [keywordsRes, overviewRes] = await Promise.all([
        apiClient.getSeoKeywords({ domain_id: activeDomainId }) as Promise<SeoKeyword[]>,
        apiClient.getSeoDomainOverview(activeDomainId) as Promise<OverviewData>,
      ]);
      setSeoKeywords((keywordsRes || []).map(mapKeywordForUI));
      setOverview(overviewRes || null);
    } catch (err: any) {
      toast({
        title: "Import failed",
        description: err?.message || "Could not import keywords. Please try again.",
        variant: "destructive",
      });
    } finally {
      setImportLoading(false);
    }
  };

  const resetImportDialog = () => {
    setImportFile(null);
    setImportKeywordsText("");
    setImportPlatform("desktop");
    setImportRegion("google.com");
    setImportIsocode("us");
    setImportLanguageCode("en");
    setImportResult(null);
  };

  // ---------- Add Keyword (RankMax-style) ----------
  const resetAddKeywordDialog = () => {
    setAddKeywordText("");
    setAddKeywordInputMode("text");
    setAddKeywordFile(null);
    setAddKeywordUrlSlug("");
    setAddKeywordRegion("google.com");
    setAddKeywordLanguage("en");
    setAddKeywordPlatform("desktop");
    setAddKeywordTagsEnabled(true);
    setAddKeywordTagInput("");
    setAddKeywordTags([]);
    setAddKeywordResult(null);
  };

  const handleAddKeywordTagKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if ((e.key === 'Enter' || e.key === ',') && addKeywordTagInput.trim()) {
      e.preventDefault();
      const tag = addKeywordTagInput.trim().toLowerCase();
      if (!addKeywordTags.includes(tag)) {
        setAddKeywordTags(prev => [...prev, tag]);
      }
      setAddKeywordTagInput("");
    }
  };

  const handleAddKeywordSubmit = async () => {
    if (!activeDomainId) return;
    setAddKeywordLoading(true);
    setAddKeywordResult(null);

    try {
      let result: any;

      if (addKeywordInputMode === "csv" && addKeywordFile) {
        const formData = new FormData();
        formData.append('domain_id', activeDomainId);
        formData.append('file', addKeywordFile);
        formData.append('platform', addKeywordPlatform);
        formData.append('region', addKeywordRegion);
        formData.append('language_code', addKeywordLanguage);
        if (addKeywordUrlSlug.trim()) {
          formData.append('target_url', addKeywordUrlSlug.trim());
        }
        if (addKeywordTagsEnabled && addKeywordTags.length > 0) {
          formData.append('tags', JSON.stringify(addKeywordTags));
        }
        // Derive isocode from region
        const isocode = regionToIsocode(addKeywordRegion);
        formData.append('isocode', isocode);
        result = await apiClient.importSeoKeywords(formData);
      } else {
        // Text input — split by commas/newlines/Enter
        const keywords = addKeywordText
          .split(/[\n,]+/)
          .map(k => k.trim())
          .filter(k => k.length > 0);

        if (keywords.length === 0) {
          toast({ title: "No keywords", description: "Enter at least one keyword", variant: "destructive" });
          setAddKeywordLoading(false);
          return;
        }

        const isocode = regionToIsocode(addKeywordRegion);
        result = await apiClient.importSeoKeywords({
          domain_id: Number(activeDomainId),
          keywords,
          platform: addKeywordPlatform,
          region: addKeywordRegion,
          isocode,
          language_code: addKeywordLanguage,
          target_url: addKeywordUrlSlug.trim() || undefined,
          tags: addKeywordTagsEnabled && addKeywordTags.length > 0 ? addKeywordTags : undefined,
        });
      }

      setAddKeywordResult(result);
      toast({
        title: "Keywords added",
        description: `${result.seo_created_count} keyword(s) added to SEO tracking`,
      });

      // Refresh keyword list
      const [keywordsRes, overviewRes] = await Promise.all([
        apiClient.getSeoKeywords({ domain_id: activeDomainId }) as Promise<SeoKeyword[]>,
        apiClient.getSeoDomainOverview(activeDomainId) as Promise<OverviewData>,
      ]);
      setSeoKeywords((keywordsRes || []).map(mapKeywordForUI));
      setOverview(overviewRes || null);
    } catch (err: any) {
      toast({
        title: "Failed to add keywords",
        description: err?.message || "Could not add keywords. Please try again.",
        variant: "destructive",
      });
    } finally {
      setAddKeywordLoading(false);
    }
  };

  // Map region to ISO code
  const regionToIsocode = (region: string): string => {
    const regionMap: Record<string, string> = {
      'google.com': 'us', 'google.co.uk': 'gb', 'google.ca': 'ca', 'google.com.au': 'au',
      'google.co.in': 'in', 'google.de': 'de', 'google.fr': 'fr', 'google.es': 'es',
      'google.it': 'it', 'google.co.jp': 'jp', 'google.com.br': 'br', 'google.com.mx': 'mx',
      'google.nl': 'nl', 'google.pl': 'pl', 'google.se': 'se', 'google.com.sg': 'sg',
      'google.co.za': 'za', 'google.com.ng': 'ng', 'google.co.nz': 'nz', 'google.ie': 'ie',
      'google.at': 'at', 'google.be': 'be', 'google.ch': 'ch', 'google.dk': 'dk',
      'google.fi': 'fi', 'google.no': 'no', 'google.pt': 'pt', 'google.com.ar': 'ar',
      'google.cl': 'cl', 'google.co.il': 'il', 'google.com.ph': 'ph', 'google.com.pk': 'pk',
      'google.com.eg': 'eg', 'google.ae': 'ae', 'google.co.th': 'th', 'google.com.my': 'my',
      'google.co.id': 'id', 'google.com.vn': 'vn', 'google.co.kr': 'kr', 'google.com.tw': 'tw',
      'google.com.hk': 'hk', 'google.ru': 'ru', 'google.com.ua': 'ua', 'google.com.tr': 'tr',
      'google.com.sa': 'sa', 'google.co.ke': 'ke',
    };
    return regionMap[region] || 'us';
  };

  const formatVolume = (volume: number | null) => {
    if (volume === null) return "NA";
    if (volume >= 1000) return `${(volume / 1000).toFixed(1)}K`;
    return volume.toString();
  };

  // Apply column visibility changes
  const handleApplyColumns = () => {
    setVisibleColumns({ ...tempVisibleColumns });
    setColumnPopoverOpen(false);
  };

  // Reset temp columns when popover opens
  const handleColumnPopoverOpenChange = (open: boolean) => {
    if (open) {
      setTempVisibleColumns({ ...visibleColumns });
    }
    setColumnPopoverOpen(open);
  };

  // Group keywords by tags for grid view
  const getTagGroups = (keywordsList: typeof filteredKeywords = filteredKeywords) => {
    const groups: Record<string, typeof filteredKeywords> = {};
    keywordsList.forEach((kw) => {
      if (kw.tags.length === 0) {
        if (!groups["No-tags"]) groups["No-tags"] = [];
        groups["No-tags"].push(kw);
      } else {
        kw.tags.forEach((tag) => {
          if (!groups[tag]) groups[tag] = [];
          groups[tag].push(kw);
        });
      }
    });
    return groups;
  };

  return (
    <div className="p-8 space-y-8 bg-background animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Keyword Rankings</h1>
          <p className="text-muted-foreground mt-2">
            Track your organic search rankings and keyword performance
          </p>
        </div>
        <Button className="gradient-primary shadow-md shadow-primary/20" onClick={() => navigate('/seo-rankings/add-keyword')} disabled={!activeDomainId}>
          <Plus className="h-4 w-4 mr-2" />
          Add Keyword
        </Button>
      </div>

      {loading && (
        <div className="flex flex-col items-center justify-center py-32">
          <Loader2 className="h-10 w-10 animate-spin text-primary mb-4" />
          <span className="text-muted-foreground text-sm">Loading SEO data...</span>
        </div>
      )}

      {!loading && !activeDomainId && (
        <Card className="p-8 text-center">
          <p className="text-muted-foreground">Please select an active domain to view SEO rankings.</p>
        </Card>
      )}

      {!loading && activeDomainId && (<>
      {/* Overview Section */}
      <Card className="shadow-elegant border border-border backdrop-blur-sm bg-card/80">
        <CardHeader className="flex flex-row items-center justify-between py-3 px-4">
          <CardTitle className="text-lg font-semibold">Overview</CardTitle>
          <div className="flex items-center gap-2">
            <Label htmlFor="hide-overview" className="text-sm text-muted-foreground">Hide</Label>
            <Switch id="hide-overview" checked={showOverview} onCheckedChange={setShowOverview} />
          </div>
        </CardHeader>
        {showOverview && (
          <CardContent className="pt-0 px-4 pb-4">
            {/* Overview Cards - Competitor Style */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">

              {/* Comparison Card */}
              <Card className="p-4 transition-all duration-300 backdrop-blur-sm bg-card/80 border border-border hover:border-primary">
                <div className="space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-base font-semibold font-inter">Comparison</h3>
                      <p className="text-sm text-muted-foreground">Ranking distribution</p>
                    </div>
                    <div className="w-10 h-10 rounded-lg shadow-glow flex items-center justify-center font-bold text-white text-sm font-inter bg-primary">
                      <BarChart3 className="h-5 w-5" />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    {([
                      { key: "top3" as const, label: "Top 3", value: overview?.today?.top_3_count ?? 0 },
                      { key: "top10" as const, label: "Top 10", value: overview?.today?.top_10_count ?? 0 },
                      { key: "top50" as const, label: "Top 50", value: overview?.today?.top_50_count ?? 0 },
                      { key: "nr" as const, label: "Not Ranked", value: overview?.today?.not_ranked_count ?? 0 },
                    ]).map(({ key, label, value }) => {
                      const active = rankFilter === key;
                      return (
                        <button
                          key={key}
                          type="button"
                          onClick={() => handleRankFilter(key)}
                          aria-pressed={active}
                          title={active ? `Showing only ${label} keywords — click to clear` : `Show only ${label} keywords`}
                          className={`p-2 rounded-lg border text-left transition-all cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary/50 ${
                            active
                              ? "bg-primary/10 border-primary ring-1 ring-primary"
                              : "bg-muted/30 border-border hover:border-primary"
                          }`}
                        >
                          <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">{label}</p>
                          <p className="text-lg font-bold font-inter">{value}</p>
                        </button>
                      );
                    })}
                  </div>

                  <div className="pt-2 border-t flex items-center justify-between">
                    {rankFilter === "all" ? (
                      <div className="flex items-center gap-2 text-sm">
                        <span className="text-muted-foreground">Best</span>
                        <span className="font-semibold">{overview?.today?.total_keywords ?? 0} keywords</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 text-sm">
                        <span className="text-muted-foreground">Filtered</span>
                        <span className="font-semibold">{filteredKeywords.length} keywords</span>
                        <button
                          type="button"
                          onClick={() => setRankFilter("all")}
                          className="text-xs text-primary hover:underline"
                        >
                          Clear
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </Card>

              {/* Device Card */}
              <Card className="p-4 transition-all duration-300 backdrop-blur-sm bg-card/80 border border-border hover:border-primary">
                <div className="space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-base font-semibold font-inter">Device</h3>
                      <p className="text-sm text-muted-foreground">Keywords by device</p>
                    </div>
                    <div className="w-10 h-10 rounded-lg shadow-glow flex items-center justify-center font-bold text-white text-sm font-inter bg-primary">
                      <Monitor className="h-5 w-5" />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div className="p-2 rounded-lg bg-muted/30 border border-border">
                      <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Desktop</p>
                      <p className="text-lg font-bold font-inter">{overview?.today?.desktop_count ?? 0}</p>
                    </div>
                    <div className="p-2 rounded-lg bg-muted/30 border border-border">
                      <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Mobile</p>
                      <p className="text-lg font-bold font-inter">{overview?.today?.mobile_count ?? 0}</p>
                    </div>
                    <div className="p-2 rounded-lg bg-muted/30 border border-border">
                      <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Tablet</p>
                      <p className="text-lg font-bold font-inter">0</p>
                    </div>
                    <div className="p-2 rounded-lg bg-muted/30 border border-border">
                      <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Total</p>
                      <p className="text-lg font-bold font-inter">{overview?.today?.total_keywords ?? 0}</p>
                    </div>
                  </div>

                  <div className="pt-2 border-t flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-muted-foreground">Tracking</span>
                      <span className="font-semibold">{overview?.today?.total_keywords ?? 0} keywords</span>
                    </div>
                  </div>
                </div>
              </Card>

              {/* Today's Performance Card */}
              <Card className="p-4 transition-all duration-300 backdrop-blur-sm bg-card/80 border border-border hover:border-primary">
                <div className="space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-base font-semibold font-inter">Performance</h3>
                      <p className="text-sm text-muted-foreground">Today's changes</p>
                    </div>
                    <div className="w-10 h-10 rounded-lg shadow-glow flex items-center justify-center font-bold text-white text-sm font-inter bg-primary">
                      <TrendingUp className="h-5 w-5" />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div className="p-2 rounded-lg bg-green-500/10 border border-green-500/20">
                      <p className="text-xs text-green-600 mb-1 uppercase tracking-wider">Improved</p>
                      <p className="text-lg font-bold font-inter text-green-600">{overview?.today?.improved_count ?? 0}</p>
                    </div>
                    <div className="p-2 rounded-lg bg-red-500/10 border border-red-500/20">
                      <p className="text-xs text-red-600 mb-1 uppercase tracking-wider">Declined</p>
                      <p className="text-lg font-bold font-inter text-red-600">{overview?.today?.declined_count ?? 0}</p>
                    </div>
                    <div className="p-2 rounded-lg bg-muted/30 border border-border">
                      <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">No Change</p>
                      <p className="text-lg font-bold font-inter">{overview?.today?.no_change_count ?? 0}</p>
                    </div>
                    <div className="p-2 rounded-lg bg-muted/30 border border-border">
                      <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">New</p>
                      <p className="text-lg font-bold font-inter">0</p>
                    </div>
                  </div>

                  <div className="pt-2 border-t flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-muted-foreground">Trend</span>
                      <div className="flex items-center gap-1">
                        {(overview?.today?.activity_level ?? 0) >= 0 ? (
                          <TrendingUp className="h-4 w-4 text-green-500" />
                        ) : (
                          <TrendingDown className="h-4 w-4 text-destructive" />
                        )}
                        <span className={`font-semibold ${(overview?.today?.activity_level ?? 0) >= 0 ? 'text-green-500' : 'text-destructive'}`}>
                          {overview?.today?.activity_level ?? 0}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </Card>

              {/* Rankmax Score Card */}
              <Card className="p-4 transition-all duration-300 backdrop-blur-sm bg-card/80 border border-border hover:border-primary">
                <div className="space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-base font-semibold font-inter">Rankmax Score</h3>
                      <p className="text-sm text-muted-foreground">Overall performance</p>
                    </div>
                    <div className={`w-10 h-10 rounded-lg shadow-glow flex items-center justify-center font-bold text-white text-base font-inter ${
                      (overview?.today?.score_meter ?? 0) >= 50 ? 'bg-green-500' : (overview?.today?.score_meter ?? 0) >= 20 ? 'bg-yellow-500' : 'bg-red-500'
                    }`}>
                      {Math.round(overview?.today?.score_meter ?? 0)}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div className="p-2 rounded-lg bg-muted/30 border border-border">
                      <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Current</p>
                      <p className="text-lg font-bold font-inter">{Math.round(overview?.today?.score_meter ?? 0)}</p>
                    </div>
                    <div className="p-2 rounded-lg bg-muted/30 border border-border">
                      <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Best</p>
                      <p className="text-lg font-bold font-inter">{Math.round(overview?.best?.score_meter ?? 0)}</p>
                    </div>
                    <div className="p-2 rounded-lg bg-muted/30 border border-border">
                      <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Top Score</p>
                      <p className="text-lg font-bold font-inter">{Math.round(overview?.today?.top_score ?? 0)}</p>
                    </div>
                    <div className={`p-2 rounded-lg ${(overview?.today?.score_meter ?? 0) >= 50 ? 'bg-green-500/10 border border-green-500/20' : 'bg-red-500/10 border border-red-500/20'}`}>
                      <p className={`text-xs mb-1 uppercase tracking-wider ${(overview?.today?.score_meter ?? 0) >= 50 ? 'text-green-600' : 'text-red-600'}`}>Status</p>
                      <p className={`text-lg font-bold font-inter ${(overview?.today?.score_meter ?? 0) >= 50 ? 'text-green-600' : 'text-red-600'}`}>
                        {(overview?.today?.score_meter ?? 0) >= 50 ? 'Good' : (overview?.today?.score_meter ?? 0) >= 20 ? 'Medium' : 'Low'}
                      </p>
                    </div>
                  </div>

                  <div className="pt-2 border-t flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-muted-foreground">Trend</span>
                      <div className="flex items-center gap-1">
                        {(overview?.today?.score_meter ?? 0) >= (overview?.yesterday?.score_meter ?? 0) ? (
                          <>
                            <TrendingUp className="h-4 w-4 text-green-500" />
                            <span className="font-semibold text-green-500">Rising</span>
                          </>
                        ) : (
                          <>
                            <TrendingDown className="h-4 w-4 text-destructive" />
                            <span className="font-semibold text-destructive">Dropping</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </Card>
            </div>

            {/* SERP Features and Google Search Ads are hidden until DataBlue
                supplies the data behind them. The SERP endpoint we query returns
                organic results only, so every figure in these two cards resolves
                to 0 or an empty list — and a card reading "0 placements" is read
                as "no ads are competing with you", which is a claim we cannot
                make from an absence of data.

                Held behind `false &&` rather than deleted: the markup is correct
                and still type-checks against the API shape, so it cannot rot
                while hidden. Flip to a real condition once the SERP response
                carries serp_features and ad placements. */}
            {false && (
              <>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
              {/* SERP Features Card */}
              <Card className="p-4 transition-all duration-300 backdrop-blur-sm bg-card/80 border border-border hover:border-primary">
                <div className="space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-base font-semibold font-inter">SERP Features</h3>
                      <p className="text-sm text-muted-foreground">Your search result ratings</p>
                    </div>
                    <div className="w-10 h-10 rounded-lg shadow-glow flex items-center justify-center font-bold text-white text-sm font-inter bg-yellow-500">
                      <Star className="h-5 w-5" />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between p-2 rounded-lg bg-muted/30 border border-border">
                      <div className="flex items-center gap-2">
                        {[1, 2, 3, 4, 5].map((_, i) => (
                          <Star
                            key={i}
                            className={`h-4 w-4 ${i < 2 ? "text-yellow-500 fill-yellow-500" : "text-muted-foreground/30"}`}
                          />
                        ))}
                        <span className="text-xs text-muted-foreground ml-2">(0-2 stars)</span>
                      </div>
                      <span className="text-lg font-bold font-inter">{overview?.today?.rating_0_2 ?? 0}</span>
                    </div>
                    <div className="flex items-center justify-between p-2 rounded-lg bg-muted/30 border border-border">
                      <div className="flex items-center gap-2">
                        {[1, 2, 3, 4, 5].map((_, i) => (
                          <Star
                            key={i}
                            className={`h-4 w-4 ${i < 4 ? "text-yellow-500 fill-yellow-500" : "text-muted-foreground/30"}`}
                          />
                        ))}
                        <span className="text-xs text-muted-foreground ml-2">(2-4 stars)</span>
                      </div>
                      <span className="text-lg font-bold font-inter">{overview?.today?.rating_2_4 ?? 0}</span>
                    </div>
                    <div className="flex items-center justify-between p-2 rounded-lg bg-muted/30 border border-border">
                      <div className="flex items-center gap-2">
                        {[1, 2, 3, 4, 5].map((_, i) => (
                          <Star key={i} className="h-4 w-4 text-yellow-500 fill-yellow-500" />
                        ))}
                        <span className="text-xs text-muted-foreground ml-2">(4-5 stars)</span>
                      </div>
                      <span className="text-lg font-bold font-inter">{overview?.today?.rating_4_5 ?? 0}</span>
                    </div>
                  </div>

                  <div className="pt-2 border-t flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-muted-foreground">Total Features</span>
                      <span className="font-semibold">{(overview?.today?.rating_0_2 ?? 0) + (overview?.today?.rating_2_4 ?? 0) + (overview?.today?.rating_4_5 ?? 0)}</span>
                    </div>
                  </div>
                </div>
              </Card>

              {/* Google Search Ads Card */}
              <Card className="p-4 transition-all duration-300 backdrop-blur-sm bg-card/80 border border-border hover:border-primary">
                <div className="space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-base font-semibold font-inter">Google Search Ads</h3>
                      <p className="text-sm text-muted-foreground">Ad placement comparison</p>
                    </div>
                    <div className="w-10 h-10 rounded-lg shadow-glow flex items-center justify-center font-bold text-white text-sm font-inter bg-blue-500">
                      <LayoutGrid className="h-5 w-5" />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between p-2 rounded-lg bg-muted/30 border border-border">
                      <span className="text-sm font-medium">Above & below the fold</span>
                      <div className="flex items-center gap-4">
                        <span className="text-xs text-muted-foreground">You: <span className="text-lg font-bold font-inter text-foreground">{overview?.today?.ads_you_above_below ?? 0}</span></span>
                        <span className="text-xs text-muted-foreground">Others: <span className="text-lg font-bold font-inter text-foreground">{overview?.today?.ads_others_above_below ?? 0}</span></span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between p-2 rounded-lg bg-muted/30 border border-border">
                      <span className="text-sm font-medium">Above the fold</span>
                      <div className="flex items-center gap-4">
                        <span className="text-xs text-muted-foreground">You: <span className="text-lg font-bold font-inter text-foreground">{overview?.today?.ads_you_above ?? 0}</span></span>
                        <span className="text-xs text-muted-foreground">Others: <span className="text-lg font-bold font-inter text-foreground">{overview?.today?.ads_others_above ?? 0}</span></span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between p-2 rounded-lg bg-muted/30 border border-border">
                      <span className="text-sm font-medium">Below the fold</span>
                      <div className="flex items-center gap-4">
                        <span className="text-xs text-muted-foreground">You: <span className="text-lg font-bold font-inter text-foreground">{overview?.today?.ads_you_below ?? 0}</span></span>
                        <span className="text-xs text-muted-foreground">Others: <span className="text-lg font-bold font-inter text-foreground">{overview?.today?.ads_others_below ?? 0}</span></span>
                      </div>
                    </div>
                  </div>

                  <div className="pt-2 border-t flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-muted-foreground">Your Ads</span>
                      <span className="font-semibold">{(overview?.today?.ads_you_above_below ?? 0) + (overview?.today?.ads_you_above ?? 0) + (overview?.today?.ads_you_below ?? 0)} placements</span>
                    </div>
                  </div>
                </div>
              </Card>
            </div>
              </>
            )}
          </CardContent>
        )}
      </Card>

      {/* Keywords Section */}
      <div id="seo-keywords-section" className="space-y-3 scroll-mt-4">
        <h2 className="text-xl font-semibold">Total keywords ({filteredKeywords.length})</h2>

        {/* Toolbar */}
        <Card className="shadow-elegant border border-border backdrop-blur-sm bg-card/80 p-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search keywords..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 w-[220px] bg-background"
                />
              </div>

              {/* Export Dropdown */}
              <DropdownMenu modal={false}>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" className="gap-2" disabled={exporting}>
                    {exporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                    {exporting ? 'Exporting...' : 'Export'}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start" className="w-56">
                  <DropdownMenuItem className="cursor-pointer" onClick={handleExportCsv} disabled={exporting}>
                    Export Project In .CSV
                  </DropdownMenuItem>
                  <DropdownMenuItem className="cursor-pointer" onClick={handleExportPdf} disabled={exporting}>
                    Export Project In .PDF
                  </DropdownMenuItem>
                  <DropdownMenuItem className="cursor-pointer" onClick={handleExportTxt} disabled={exporting}>
                    Export Keywords In .TXT
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>

              {/* Import Button - hidden, use Add Keyword page instead */}
            </div>

            <div className="flex items-center gap-2">
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="outline" size="icon" onClick={handleOpenTagDialog}>
                      <Tag className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>{selectedKeywords.length > 0 ? "Manage tags for selected keywords" : "Select keywords to add tags"}</TooltipContent>
                </Tooltip>
              </TooltipProvider>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="outline" size="icon" onClick={handleRefresh} disabled={refreshing || !activeDomainId}>
                      <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Refresh rankings</TooltipContent>
                </Tooltip>
              </TooltipProvider>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="outline" size="icon" onClick={handleOpenDelete}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>{selectedKeywords.length > 0 ? "Delete selected keywords" : "Select keywords to delete"}</TooltipContent>
                </Tooltip>
              </TooltipProvider>

              {/* Column Selection Popover - List view only */}
              {viewMode === "list" && (
              <Popover open={columnPopoverOpen} onOpenChange={handleColumnPopoverOpenChange}>
                <PopoverTrigger asChild>
                  <Button variant="outline" className="gap-2">
                    <Columns className="h-4 w-4" />
                    Column
                  </Button>
                </PopoverTrigger>
                <PopoverContent align="end" className="w-52 p-3 max-h-[420px] overflow-y-auto">
                  <div className="space-y-2.5">
                    {/* Always-on columns (Keyword, Rank) */}
                    {[
                      { label: "Keyword" },
                      { label: "Rank" },
                    ].map((col) => (
                      <div key={col.label} className="flex items-center gap-2">
                        <Checkbox checked={true} disabled className="opacity-60" />
                        <Label className="text-sm font-medium text-muted-foreground">{col.label}</Label>
                      </div>
                    ))}

                    {/* Toggleable columns */}
                    {(
                      [
                        { key: "volume", label: "Volume" },
                        { key: "best", label: "Best" },
                        { key: "clicks", label: "Clicks" },
                        { key: "impressions", label: "Impressions" },
                        { key: "1d", label: "1D" },
                        { key: "7d", label: "7d" },
                        { key: "15d", label: "15d" },
                        { key: "tags", label: "Tags" },
                        { key: "date", label: "Date" },
                      ] as { key: keyof ColumnVisibility; label: string }[]
                    ).map((col) => (
                      <div key={col.key} className="flex items-center gap-2">
                        <Checkbox
                          id={`col-${col.key}`}
                          checked={tempVisibleColumns[col.key]}
                          onCheckedChange={(checked) =>
                            setTempVisibleColumns((prev) => ({
                              ...prev,
                              [col.key]: !!checked,
                            }))
                          }
                        />
                        <Label htmlFor={`col-${col.key}`} className="text-sm font-medium cursor-pointer">
                          {col.label}
                        </Label>
                      </div>
                    ))}

                    <div className="border-t pt-2.5 mt-2.5">
                      <div className="flex items-center gap-2">
                        <Checkbox id="col-apply-all" />
                        <Label htmlFor="col-apply-all" className="text-sm text-muted-foreground cursor-pointer">
                          Apply to all project
                        </Label>
                      </div>
                    </div>

                    <Button
                      className="w-full gradient-primary shadow-md shadow-primary/20"
                      size="sm"
                      onClick={handleApplyColumns}
                    >
                      Apply
                    </Button>
                  </div>
                </PopoverContent>
              </Popover>
              )}

              <div className="flex items-center border border-border rounded-lg overflow-hidden">
                <Button
                  variant={viewMode === "list" ? "default" : "ghost"}
                  size="sm"
                  className={`rounded-none gap-1 ${viewMode === "list" ? "gradient-primary" : ""}`}
                  onClick={() => setViewMode("list")}
                >
                  <List className="h-4 w-4" />
                  List
                </Button>
                <Button
                  variant={viewMode === "grid" ? "default" : "ghost"}
                  size="sm"
                  className={`rounded-none gap-1 ${viewMode === "grid" ? "gradient-primary" : ""}`}
                  onClick={() => setViewMode("grid")}
                >
                  <LayoutGrid className="h-4 w-4" />
                  Grid
                </Button>
              </div>
            </div>
          </div>
        </Card>

        {/* Keywords Content - List or Grid View */}
        {viewMode === "list" ? (
          /* List View - Keywords Table */
          <Card className="shadow-elegant border border-border backdrop-blur-sm bg-card/80">
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/30 hover:bg-muted/30">
                    <TableHead className="w-10 py-2">
                      <Checkbox
                        checked={filteredKeywords.filter((k) => !k.favour).length > 0 && filteredKeywords.filter((k) => !k.favour).every((k) => selectedKeywords.includes(k.id))}
                        onCheckedChange={toggleAllKeywords}
                        disabled={filteredKeywords.filter((k) => !k.favour).length === 0}
                      />
                    </TableHead>
                    <TableHead className="w-20 text-xs font-semibold py-2">ACTIONS</TableHead>
                    <TableHead className="text-xs font-semibold py-2">KEYWORD</TableHead>
                    <SortableHead label="RANK" sortId="rank" className="text-center text-xs font-semibold py-2 w-14" />
                    {visibleColumns.volume && (
                      <SortableHead label="VOLUME" sortId="volume" className="text-center text-xs font-semibold py-2 w-16" />
                    )}
                    {visibleColumns.best && (
                      <SortableHead label="BEST" sortId="best" className="text-center text-xs font-semibold py-2 w-12" hint="Best rank this keyword has ever reached" />
                    )}
                    {visibleColumns.clicks && (
                      <SortableHead label="CLKS" sortId="clicks" className="text-center text-xs font-semibold py-2 w-12" hint={`Clicks — ${GSC_WINDOW_HINT}`} />
                    )}
                    {visibleColumns.impressions && (
                      <SortableHead label="IMPS" sortId="impressions" className="text-center text-xs font-semibold py-2 w-12" hint={`Impressions — ${GSC_WINDOW_HINT}`} />
                    )}
                    {visibleColumns["1d"] && (
                      <TableHead className="text-center text-xs font-semibold py-2 w-12">1D</TableHead>
                    )}
                    {visibleColumns["7d"] && (
                      <TableHead className="text-center text-xs font-semibold py-2 w-12">7D</TableHead>
                    )}
                    {visibleColumns["15d"] && (
                      <TableHead className="text-center text-xs font-semibold py-2 w-12">15D</TableHead>
                    )}
                    {visibleColumns.serp && (
                      <TableHead className="text-center text-xs font-semibold py-2 w-14">SERP</TableHead>
                    )}
                    {visibleColumns.tags && (
                      <TableHead className="text-center text-xs font-semibold py-2 w-16">TAGS</TableHead>
                    )}
                    {visibleColumns.date && (
                      <TableHead className="text-xs font-semibold py-2 w-20">DATE</TableHead>
                    )}
                    <TableHead className="w-8 py-2"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {paginatedKeywords.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={14} className="py-16 text-center">
                        <div className="flex flex-col items-center gap-3">
                          <SearchX className="h-12 w-12 text-muted-foreground/40" />
                          <div>
                            <p className="text-lg font-medium text-muted-foreground">No keywords found</p>
                            <p className="text-sm text-muted-foreground/60 mt-1">
                              {searchQuery
                                ? `No keywords matching "${searchQuery}"`
                                : 'Add keywords to start tracking your SEO rankings'}
                            </p>
                          </div>
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                  {paginatedKeywords.map((keyword) => (
                    <TableRow key={keyword.id} className="hover:bg-muted/30">
                      <TableCell className="py-3">
                        <Checkbox
                          checked={selectedKeywords.includes(keyword.id)}
                          onCheckedChange={() => toggleKeywordSelection(keyword.id)}
                          disabled={!!keyword.favour}
                        />
                      </TableCell>
                      <TableCell className="py-3">
                        {/* The G shortcut is hidden. It opened a live Google
                            search for the keyword, which shows today's SERP from
                            the viewer's own location and history — not the
                            ranking this row records, which was measured from a
                            configured region on a specific date. Two different
                            results side by side read as a discrepancy in our
                            data. */}
                        <div className="flex items-center gap-0">
                          {false && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-6 w-6"
                              onClick={() => window.open(`https://www.google.com/search?q=${encodeURIComponent(keyword.keyword)}`, '_blank')}
                            >
                              <span className="text-red-500 font-bold text-xs">G</span>
                            </Button>
                          )}
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-6 w-6"
                                  onClick={() => navigate(`/seo-rankings/${keyword.id}?tab=rank-history`)}
                                >
                                  <BarChart3 className="h-3.5 w-3.5 text-muted-foreground" />
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent>Rank History</TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-6 w-6"
                                  onClick={() => handleToggleFavourite(keyword.id, keyword.favour)}
                                >
                                  <Star className={`h-3.5 w-3.5 ${keyword.favour ? 'text-purple-500 fill-purple-500' : 'text-muted-foreground'}`} />
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent>{keyword.favour ? 'Mark as unfavourite' : 'Mark as favourite'}</TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        </div>
                      </TableCell>
                      <TableCell className="py-3">
                        <div className="flex items-center gap-2">
                          <img
                            src={`https://flagcdn.com/16x12/${keyword.country.toLowerCase()}.png`}
                            alt={keyword.country}
                            className="w-5 h-5 object-cover rounded-full shadow-sm flex-shrink-0"
                          />
                          <div className="min-w-0">
                            <p
                              className="font-medium text-sm truncate cursor-pointer hover:text-primary hover:underline"
                              onClick={() => navigate(`/seo-rankings/${keyword.id}`)}
                            >
                              {keyword.keyword}
                            </p>
                            {keyword.url ? (
                              <a
                                href={keyword.url.startsWith('http') ? keyword.url : `https://${keyword.url}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs text-muted-foreground flex items-center gap-1 truncate hover:text-primary hover:underline"
                              >
                                {keyword.url}
                                <ExternalLink className="h-2.5 w-2.5 flex-shrink-0" />
                              </a>
                            ) : (
                              <p className="text-xs text-muted-foreground flex items-center gap-1 truncate">
                                —
                              </p>
                            )}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="text-center py-3">
                        {keyword.rankDisplay ? (
                          <span className="text-muted-foreground text-sm">{keyword.rankDisplay}</span>
                        ) : (
                          <span className="font-semibold text-sm">{keyword.rank}</span>
                        )}
                      </TableCell>
                      {visibleColumns.volume && (
                        <TableCell className="text-center py-3">
                          <div className="flex items-center justify-center gap-0.5">
                            <span className="text-sm">{formatVolume(keyword.volume)}</span>
                          </div>
                        </TableCell>
                      )}
                      {visibleColumns.best && (
                        <TableCell className="text-center font-semibold py-3 text-sm">{keyword.best}</TableCell>
                      )}
                      {visibleColumns.clicks && (
                        <TableCell className="text-center py-3 text-sm">{keyword.clicks}</TableCell>
                      )}
                      {visibleColumns.impressions && (
                        <TableCell className="text-center py-3 text-sm">{keyword.impressions}</TableCell>
                      )}
                      {visibleColumns["1d"] && (
                        <TableCell className="text-center py-3">
                          {keyword.change1d ? (
                            <div className="flex items-center justify-center gap-0.5">
                              <span className={`text-sm ${keyword.change1d.direction === "down" ? "text-red-500 font-medium" : "text-green-500 font-medium"}`}>
                                {keyword.change1d.value}
                              </span>
                              {keyword.change1d.direction === "down" ? (
                                <TrendingDown className="h-3 w-3 text-red-500" />
                              ) : (
                                <TrendingUp className="h-3 w-3 text-green-500" />
                              )}
                            </div>
                          ) : (
                            <span className="text-muted-foreground text-sm">-</span>
                          )}
                        </TableCell>
                      )}
                      {visibleColumns["7d"] && (
                        <TableCell className="text-center py-3">
                          {keyword.change7d ? (
                            <div className="flex items-center justify-center gap-0.5">
                              <span className={`text-sm ${keyword.change7d.direction === "down" ? "text-red-500 font-medium" : "text-green-500 font-medium"}`}>
                                {keyword.change7d.value}
                              </span>
                              {keyword.change7d.direction === "down" ? (
                                <TrendingDown className="h-3 w-3 text-red-500" />
                              ) : (
                                <TrendingUp className="h-3 w-3 text-green-500" />
                              )}
                            </div>
                          ) : (
                            <span className="text-muted-foreground text-sm">-</span>
                          )}
                        </TableCell>
                      )}
                      {visibleColumns["15d"] && (
                        <TableCell className="text-center py-3">
                          {keyword.change15d ? (
                            <div className="flex items-center justify-center gap-0.5">
                              <span className={`text-sm ${keyword.change15d.direction === "down" ? "text-red-500 font-medium" : "text-green-500 font-medium"}`}>
                                {keyword.change15d.value}
                              </span>
                              {keyword.change15d.direction === "down" ? (
                                <TrendingDown className="h-3 w-3 text-red-500" />
                              ) : (
                                <TrendingUp className="h-3 w-3 text-green-500" />
                              )}
                            </div>
                          ) : (
                            <span className="text-muted-foreground text-sm">-</span>
                          )}
                        </TableCell>
                      )}
                      {visibleColumns.serp && (
                        <TableCell className="text-center py-3 text-sm">
                          {keyword.serp ? (
                            <span className="text-green-500 font-medium">{keyword.serp}</span>
                          ) : (
                            <span className="text-muted-foreground">NA</span>
                          )}
                        </TableCell>
                      )}
                      {visibleColumns.tags && (
                        <TableCell className="text-center py-3 text-sm">
                          {keyword.tags.length > 0 ? (
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <span
                                    className="inline-flex items-center gap-1 cursor-pointer hover:text-primary"
                                    onClick={() => handleInlineTagOpen(keyword.id)}
                                  >
                                    {keyword.tags.length}
                                    <Tag className="h-3 w-3 text-primary" />
                                  </span>
                                </TooltipTrigger>
                                <TooltipContent side="top" className="p-2 max-w-xs">
                                  <div className="flex flex-wrap gap-1 items-center">
                                    {keyword.tags.map((tag: string) => (
                                      <span key={tag} className="inline-block bg-muted text-foreground text-xs rounded px-1.5 py-0.5 capitalize">
                                        {tag}
                                      </span>
                                    ))}
                                    <span
                                      className="inline-block bg-primary/20 text-primary text-xs rounded px-1.5 py-0.5 cursor-pointer hover:bg-primary/30 font-medium"
                                      onClick={() => handleInlineTagOpen(keyword.id)}
                                    >
                                      ADD
                                    </span>
                                  </div>
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          ) : (
                            <span
                              className="text-xs text-primary font-medium cursor-pointer hover:underline"
                              onClick={() => handleInlineTagOpen(keyword.id)}
                            >
                              ADD
                            </span>
                          )}
                        </TableCell>
                      )}
                      {visibleColumns.date && (
                        <TableCell className="py-3">
                          <div>
                            <p className="text-xs text-muted-foreground whitespace-nowrap">{keyword.date}</p>
                            <p className="text-xs text-muted-foreground/60 whitespace-nowrap">{keyword.timeAgo}</p>
                          </div>
                        </TableCell>
                      )}
                      <TableCell className="py-3 w-8">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 rounded-full hover:bg-primary/10"
                          onClick={() => navigate(`/seo-rankings/${keyword.id}`)}
                        >
                          <ChevronRight className="h-4 w-4 text-primary" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {/* Pagination Controls. Rendered whenever there are rows, not only
                  past two pages — the page-size selector has to be reachable
                  even when everything already fits on one. */}
              {filteredKeywords.length > 0 && (
                <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-t border-border">
                  <div className="flex items-center gap-3">
                    <p className="text-sm text-muted-foreground">
                      Showing {(currentPage - 1) * KEYWORDS_PER_PAGE + 1}-{Math.min(currentPage * KEYWORDS_PER_PAGE, filteredKeywords.length)} of {filteredKeywords.length} keywords
                    </p>
                    <Select
                      value={String(keywordsPerPage)}
                      onValueChange={(v) => setKeywordsPerPage(Number(v))}
                    >
                      <SelectTrigger className="h-8 w-[110px] text-sm">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {PAGE_SIZE_OPTIONS.map((size) => (
                          <SelectItem key={size} value={String(size)}>
                            {size} per page
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(1)}
                      disabled={currentPage === 1}
                    >
                      First
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                      disabled={currentPage === 1}
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    {Array.from({ length: totalPages }, (_, i) => i + 1)
                      .filter(page => page === 1 || page === totalPages || Math.abs(page - currentPage) <= 2)
                      .reduce<(number | string)[]>((acc, page, idx, arr) => {
                        if (idx > 0 && page - (arr[idx - 1] as number) > 1) acc.push('...');
                        acc.push(page);
                        return acc;
                      }, [])
                      .map((item, idx) =>
                        item === '...' ? (
                          <span key={`ellipsis-${idx}`} className="px-2 text-muted-foreground">...</span>
                        ) : (
                          <Button
                            key={item}
                            variant={currentPage === item ? "default" : "outline"}
                            size="sm"
                            className="min-w-[32px]"
                            onClick={() => setCurrentPage(item as number)}
                          >
                            {item}
                          </Button>
                        )
                      )}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                      disabled={currentPage === totalPages}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(totalPages)}
                      disabled={currentPage === totalPages}
                    >
                      Last
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        ) : (
          /* Grid View - Keywords grouped by tags */
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {filteredKeywords.length === 0 && (
              <Card className="lg:col-span-2 shadow-elegant border border-border backdrop-blur-sm bg-card/80 p-12">
                <div className="flex flex-col items-center gap-3 text-center">
                  <SearchX className="h-12 w-12 text-muted-foreground/40" />
                  <div>
                    <p className="text-lg font-medium text-muted-foreground">No keywords found</p>
                    <p className="text-sm text-muted-foreground/60 mt-1">
                      {searchQuery
                        ? `No keywords matching "${searchQuery}"`
                        : 'Add keywords to start tracking your SEO rankings'}
                    </p>
                  </div>
                </div>
              </Card>
            )}
            {Object.entries(getTagGroups()).map(([tagName, keywords]) => {
              const tagPage = gridTagPages[tagName] || 1;
              const tagTotalPages = Math.ceil(keywords.length / KEYWORDS_PER_PAGE);
              const tagPaginatedKws = keywords.slice(
                (tagPage - 1) * KEYWORDS_PER_PAGE,
                tagPage * KEYWORDS_PER_PAGE
              );
              const setTagPage = (page: number | ((p: number) => number)) => {
                setGridTagPages(prev => ({
                  ...prev,
                  [tagName]: typeof page === 'function' ? page(prev[tagName] || 1) : page,
                }));
              };
              return (
              <Card key={tagName} className="shadow-elegant border border-border backdrop-blur-sm bg-card/80 overflow-hidden">
                {/* Grid Card Header */}
                <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-muted/20">
                  <div>
                    <h3 className="text-sm font-semibold">
                      Tag : <span className="text-foreground">{tagName}</span>
                    </h3>
                    <p className="text-xs text-muted-foreground">
                      Total keywords : <span className="font-medium">{keywords.length}</span>
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            variant="outline"
                            size="icon"
                            className="h-7 w-7"
                            onClick={() => {
                              // Use selected keywords within this group if any are checked,
                              // otherwise fall back to all keywords in the group (like RankMaxx).
                              const groupIds = keywords.map(kw => kw.id);
                              const selectedInGroup = groupIds.filter(id => selectedKeywords.includes(id));
                              handleGroupTagOpen(selectedInGroup.length > 0 ? selectedInGroup : groupIds);
                            }}
                          >
                            <Tag className="h-3.5 w-3.5" />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>Add tags to all keywords in this group</TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                    <span className="text-xs text-muted-foreground">Rankmax score</span>
                    <div className="w-8 h-8 rounded-full border-2 border-primary flex items-center justify-center">
                      <span className="text-xs font-bold text-primary">0</span>
                    </div>
                  </div>
                </div>

                {/* Grid Card Body - Mini Table */}
                <CardContent className="p-0 overflow-x-auto">
                  <Table className="min-w-[350px]">
                    <TableHeader>
                      <TableRow className="bg-muted/20 hover:bg-muted/20">
                        <TableHead className="w-8 py-3">
                          <Checkbox
                            checked={keywords.filter((kw) => !kw.favour).length > 0 && keywords.filter((kw) => !kw.favour).every((kw) => selectedKeywords.includes(kw.id))}
                            onCheckedChange={() => toggleGroupKeywords(keywords.map((kw) => kw.id))}
                            disabled={keywords.every((kw) => !!kw.favour)}
                          />
                        </TableHead>
                        <TableHead className="text-xs font-semibold py-3">KEYWORD</TableHead>
                        <SortableHead label="RANK" sortId="rank" className="text-center text-xs font-semibold py-3 w-14" />
                        <TableHead className="text-center text-xs font-semibold py-3 w-14">TAGS</TableHead>
                        <TableHead className="w-8 py-3"></TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {tagPaginatedKws.map((keyword) => (
                        <TableRow key={keyword.id} className="hover:bg-muted/30">
                          <TableCell className="py-3">
                            <Checkbox
                              checked={selectedKeywords.includes(keyword.id)}
                              onCheckedChange={() => toggleKeywordSelection(keyword.id)}
                              disabled={!!keyword.favour}
                            />
                          </TableCell>
                          <TableCell className="py-3">
                            <div className="flex items-center gap-1.5">
                              {/* Hidden — see the note on the main table. */}
                              {false && (
                                <div className="flex items-center gap-0 flex-shrink-0">
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-5 w-5"
                                    onClick={() => window.open(`https://www.google.com/search?q=${encodeURIComponent(keyword.keyword)}`, '_blank')}
                                  >
                                    <span className="text-red-500 font-bold text-[10px]">G</span>
                                  </Button>
                                </div>
                              )}
                              <img
                                src={`https://flagcdn.com/16x12/${keyword.country.toLowerCase()}.png`}
                                alt={keyword.country}
                                className="w-5 h-5 object-cover rounded-full shadow-sm flex-shrink-0"
                              />
                              <div className="min-w-0">
                                <p className="font-medium text-xs truncate">{keyword.keyword}</p>
                                {keyword.url ? (
                                  <a
                                    href={keyword.url.startsWith('http') ? keyword.url : `https://${keyword.url}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-[10px] text-muted-foreground flex items-center gap-0.5 truncate hover:text-primary hover:underline"
                                  >
                                    {keyword.url}
                                    <ExternalLink className="h-2 w-2 flex-shrink-0" />
                                  </a>
                                ) : (
                                  <p className="text-[10px] text-muted-foreground flex items-center gap-0.5 truncate">
                                    —
                                  </p>
                                )}
                              </div>
                            </div>
                          </TableCell>
                          <TableCell className="text-center py-3">
                            {keyword.rankDisplay ? (
                              <span className="text-muted-foreground text-xs">{keyword.rankDisplay}</span>
                            ) : (
                              <span className="font-semibold text-xs">{keyword.rank}</span>
                            )}
                          </TableCell>
                          <TableCell className="text-center py-3">
                            {keyword.tags.length > 0 ? (
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <span className="inline-flex items-center gap-1 cursor-pointer hover:text-primary">
                                      {keyword.tags.length}
                                      <Tag className="h-3 w-3 text-primary" />
                                    </span>
                                  </TooltipTrigger>
                                  <TooltipContent side="top" className="p-2 max-w-xs">
                                    <div className="flex flex-wrap gap-1 items-center">
                                      {keyword.tags.map((tag: string) => (
                                        <span key={tag} className="inline-block bg-muted text-foreground text-xs rounded px-1.5 py-0.5 capitalize">
                                          {tag}
                                        </span>
                                      ))}
                                      <span
                                        className="inline-block bg-primary/20 text-primary text-xs rounded px-1.5 py-0.5 cursor-pointer hover:bg-primary/30 font-medium"
                                        onClick={() => handleInlineTagOpen(keyword.id)}
                                      >
                                        ADD
                                      </span>
                                    </div>
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            ) : (
                              <span
                                className="text-xs text-primary font-medium cursor-pointer hover:underline"
                                onClick={() => handleInlineTagOpen(keyword.id)}
                              >
                                ADD
                              </span>
                            )}
                          </TableCell>
                          <TableCell className="py-3 w-8">
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-6 w-6"
                                    onClick={() => handleToggleFavourite(keyword.id, keyword.favour)}
                                  >
                                    <Star className={`h-3.5 w-3.5 ${keyword.favour ? 'text-purple-500 fill-purple-500' : 'text-muted-foreground'}`} />
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>{keyword.favour ? 'Mark as unfavourite' : 'Mark as favourite'}</TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  {/* Per-tag pagination */}
                  {tagTotalPages > 1 && (
                    <div className="flex items-center justify-between px-3 py-2 border-t border-border bg-muted/10">
                      <p className="text-xs text-muted-foreground">
                        {(tagPage - 1) * KEYWORDS_PER_PAGE + 1}-{Math.min(tagPage * KEYWORDS_PER_PAGE, keywords.length)} of {keywords.length}
                      </p>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-6 px-2 text-xs"
                          onClick={() => setTagPage(p => Math.max(1, p - 1))}
                          disabled={tagPage === 1}
                        >
                          <ChevronLeft className="h-3 w-3" />
                        </Button>
                        {Array.from({ length: tagTotalPages }, (_, i) => i + 1)
                          .filter(page => page === 1 || page === tagTotalPages || Math.abs(page - tagPage) <= 1)
                          .reduce<(number | string)[]>((acc, page, idx, arr) => {
                            if (idx > 0 && page - (arr[idx - 1] as number) > 1) acc.push('...');
                            acc.push(page);
                            return acc;
                          }, [])
                          .map((item, idx) =>
                            item === '...' ? (
                              <span key={`ellipsis-${idx}`} className="px-1 text-muted-foreground text-xs">...</span>
                            ) : (
                              <Button
                                key={item}
                                variant={tagPage === item ? "default" : "outline"}
                                size="sm"
                                className="h-6 w-6 px-0 text-xs"
                                onClick={() => setTagPage(item as number)}
                              >
                                {item}
                              </Button>
                            )
                          )}
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-6 px-2 text-xs"
                          onClick={() => setTagPage(p => Math.min(tagTotalPages, p + 1))}
                          disabled={tagPage === tagTotalPages}
                        >
                          <ChevronRight className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
              );
            })}
          </div>
        )}
      </div>

      </>)}

      {/* Refresh Progress Bar — fixed bottom, like RankMax */}
      {refreshing && (
        <div
          className="fixed bottom-0 right-0 z-50 bg-card border-t border-border shadow-lg pl-6 pr-24 py-3 transition-all duration-150"
          style={{ left: sidebarOpen ? '256px' : '64px' }}
        >
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <RefreshCw className="h-4 w-4 animate-spin text-primary" />
                <span className="text-sm font-medium">Refreshing...</span>
              </div>
              <span className="text-sm font-bold text-primary">
                {refreshCompleted}/{refreshTotal}
              </span>
            </div>
            <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-primary rounded-full"
                style={{
                  width: `${refreshProgress}%`,
                  transition: 'width 0.7s ease-in-out',
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Keywords</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete {selectedKeywords.length} keyword(s) and all their ranking history. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteLoading}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              disabled={deleteLoading}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteLoading ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin mr-2" />
                  Deleting...
                </>
              ) : (
                'Confirm Delete'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Tag Management Dialog */}
      <Dialog open={tagDialogOpen} onOpenChange={(open) => {
        setTagDialogOpen(open);
        if (!open) { setTagKeywordIds([]); setPendingTags([]); setTagInput(""); }
      }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Manage Tags</DialogTitle>
            <DialogDescription>
              You have selected {tagKeywordIds.length} keyword(s). Add or remove tags below.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* Tag Input */}
            <div className="flex gap-2">
              <Input
                placeholder="Type a tag and press Enter..."
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ',') {
                    e.preventDefault();
                    handleAddTag();
                  }
                }}
                onBlur={handleAddTag}
                className="flex-1"
              />
            </div>

            {/* Current Tags */}
            {pendingTags.length > 0 && (
              <div>
                <p className="text-xs text-muted-foreground mb-2 uppercase tracking-wider">Selected Tags</p>
                <div className="flex flex-wrap gap-1.5">
                  {pendingTags.map(tag => (
                    <Badge key={tag} variant="secondary" className="gap-1 px-2 py-1">
                      {tag}
                      <X
                        className="h-3 w-3 cursor-pointer hover:text-destructive"
                        onClick={() => handleRemovePendingTag(tag)}
                      />
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Available Tags from Domain */}
            {allDomainTags.length > 0 && (
              <div>
                <p className="text-xs text-muted-foreground mb-2 uppercase tracking-wider">Available Tags</p>
                <div className="flex flex-wrap gap-1.5">
                  {allDomainTags
                    .filter(tag => !pendingTags.includes(tag))
                    .map(tag => (
                      <Badge
                        key={tag}
                        variant="outline"
                        className="cursor-pointer hover:bg-primary/10 hover:border-primary px-2 py-1"
                        onClick={() => {
                          if (pendingTags.length < 20) {
                            setPendingTags(prev => [...prev, tag]);
                          }
                        }}
                      >
                        <Plus className="h-3 w-3 mr-1" />
                        {tag}
                      </Badge>
                    ))}
                </div>
              </div>
            )}

            <p className="text-xs text-muted-foreground">
              {pendingTags.length}/20 tags. Press Enter or comma to add. Only letters, numbers, spaces and hyphens allowed.
            </p>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setTagDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleSaveTags} disabled={tagLoading} className="gradient-primary">
              {tagLoading ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin mr-2" />
                  Saving...
                </>
              ) : (
                'Save Tags'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Import Keywords Dialog */}
      <Dialog open={importDialogOpen} onOpenChange={(open) => {
        setImportDialogOpen(open);
        if (!open) resetImportDialog();
      }}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Import Keywords</DialogTitle>
            <DialogDescription>
              Import keywords from a CSV file or paste them directly. Keywords will be added to SEO tracking for the current domain.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* CSV File Upload */}
            <div>
              <Label className="text-sm font-medium mb-2 block">Upload CSV File</Label>
              <div
                className="border-2 border-dashed border-border rounded-lg p-6 text-center cursor-pointer hover:border-primary/50 transition-colors"
                onClick={() => document.getElementById('import-csv-input')?.click()}
                onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); }}
                onDrop={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  const file = e.dataTransfer.files?.[0];
                  if (file && (file.name.endsWith('.csv') || file.name.endsWith('.txt'))) {
                    setImportFile(file);
                    setImportKeywordsText("");
                  }
                }}
              >
                <input
                  id="import-csv-input"
                  type="file"
                  accept=".csv,.txt"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                      setImportFile(file);
                      setImportKeywordsText("");
                    }
                  }}
                />
                {importFile ? (
                  <div className="flex items-center justify-center gap-2">
                    <FileUp className="h-5 w-5 text-primary" />
                    <span className="text-sm font-medium">{importFile.name}</span>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-5 w-5"
                      onClick={(e) => { e.stopPropagation(); setImportFile(null); }}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                ) : (
                  <div>
                    <Upload className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
                    <p className="text-sm text-muted-foreground">
                      Drag & drop a CSV/TXT file, or click to browse
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      CSV should have a "keyword" column, or one keyword per line
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* OR Divider */}
            <div className="flex items-center gap-3">
              <div className="flex-1 h-px bg-border" />
              <span className="text-xs text-muted-foreground uppercase">or paste keywords</span>
              <div className="flex-1 h-px bg-border" />
            </div>

            {/* Text Input */}
            <div>
              <textarea
                className="w-full min-h-[100px] rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-y"
                placeholder={"Enter keywords (one per line or comma-separated):\nbacklink management tool\nbacklink system\nlinkody alternative"}
                value={importKeywordsText}
                onChange={(e) => { setImportKeywordsText(e.target.value); setImportFile(null); }}
                disabled={!!importFile}
              />
            </div>

            {/* SEO Config */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs text-muted-foreground mb-1 block">Platform</Label>
                <select
                  className="w-full rounded-md border border-input bg-background px-3 py-3 text-sm"
                  value={importPlatform}
                  onChange={(e) => setImportPlatform(e.target.value)}
                >
                  <option value="desktop">Desktop</option>
                  <option value="mobile">Mobile</option>
                </select>
              </div>
              <div>
                <Label className="text-xs text-muted-foreground mb-1 block">Region</Label>
                <Input
                  value={importRegion}
                  onChange={(e) => setImportRegion(e.target.value)}
                  placeholder="google.com"
                  className="h-8 text-sm"
                />
              </div>
              <div>
                <Label className="text-xs text-muted-foreground mb-1 block">Country (ISO)</Label>
                <Input
                  value={importIsocode}
                  onChange={(e) => setImportIsocode(e.target.value)}
                  placeholder="us"
                  className="h-8 text-sm"
                />
              </div>
              <div>
                <Label className="text-xs text-muted-foreground mb-1 block">Language</Label>
                <Input
                  value={importLanguageCode}
                  onChange={(e) => setImportLanguageCode(e.target.value)}
                  placeholder="en"
                  className="h-8 text-sm"
                />
              </div>
            </div>

            {/* Import Result */}
            {importResult && (
              <div className="rounded-lg border border-border bg-muted/30 p-3 space-y-1">
                <p className="text-sm font-medium text-green-600">Import Successful</p>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-muted-foreground">
                  <span>Keywords created:</span>
                  <span className="font-medium text-foreground">{importResult.keyword_created_count}</span>
                  <span>Keywords existing:</span>
                  <span className="font-medium text-foreground">{importResult.keyword_skipped_count}</span>
                  <span>SEO tracking added:</span>
                  <span className="font-medium text-foreground">{importResult.seo_created_count}</span>
                  <span>Already tracked:</span>
                  <span className="font-medium text-foreground">{importResult.seo_skipped_count}</span>
                  <span>Total processed:</span>
                  <span className="font-medium text-foreground">{importResult.total_processed}</span>
                </div>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setImportDialogOpen(false)}>
              {importResult ? 'Close' : 'Cancel'}
            </Button>
            {!importResult && (
              <Button onClick={handleImportKeywords} disabled={importLoading || (!importFile && !importKeywordsText.trim())} className="gradient-primary">
                {importLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    Importing...
                  </>
                ) : (
                  <>
                    <Upload className="h-4 w-4 mr-2" />
                    Import Keywords
                  </>
                )}
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

    </div>
  );
};

export default SeoRankings;
