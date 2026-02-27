import { useState, useEffect, useCallback } from "react";
import { apiClient } from "@/services/api";
import { useDomainStore } from "@/stores/domainStore";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
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
  ChevronRight,
  BarChart3,
  ArrowRight,
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
  created_at: string;
  modified_at: string;
}

interface OverviewData {
  today: any;
  yesterday: any;
  best: any;
  comparison: Array<{ status: string; today: number; yesterday: number; best: number }>;
}

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
    tags: [] as string[],
    date: kw.last_ranked_date ? new Date(kw.last_ranked_date).toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' }) : '-',
    timeAgo: kw.last_ranked_date ? getTimeAgo(new Date(kw.last_ranked_date)) : '',
    country: kw.isocode?.toUpperCase() || 'US',
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
  const [searchQuery, setSearchQuery] = useState("");
  const [viewMode, setViewMode] = useState<"list" | "grid">("list");
  const [showOverview, setShowOverview] = useState(true);
  const [selectedKeywords, setSelectedKeywords] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [seoKeywords, setSeoKeywords] = useState<ReturnType<typeof mapKeywordForUI>[]>([]);
  const [overview, setOverview] = useState<OverviewData | null>(null);

  // Use the domain store (same source as the sidebar DomainSelector)
  const { selectedDomain } = useDomainStore();
  const activeDomainId = selectedDomain ? String(selectedDomain.id) : "";

  // Fetch SEO data when domain is available
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
    } catch (err) {
      console.error("Failed to fetch SEO data:", err);
    } finally {
      setLoading(false);
    }
  }, [activeDomainId]);

  useEffect(() => {
    fetchSeoData();
  }, [fetchSeoData]);

  const handleRefresh = async () => {
    if (!activeDomainId || refreshing) return;
    setRefreshing(true);
    try {
      await apiClient.triggerSeoRanking({ domain_id: Number(activeDomainId) });
      // Poll for results every 5s (engine processes async via Celery)
      let attempts = 0;
      const maxAttempts = 24; // up to 2 minutes
      const poll = setInterval(async () => {
        attempts++;
        try {
          const [keywordsRes, overviewRes] = await Promise.all([
            apiClient.getSeoKeywords({ domain_id: activeDomainId }) as Promise<SeoKeyword[]>,
            apiClient.getSeoDomainOverview(activeDomainId) as Promise<OverviewData>,
          ]);
          setSeoKeywords((keywordsRes || []).map(mapKeywordForUI));
          setOverview(overviewRes || null);

          // Stop polling once we have overview data or all keywords are processed
          const allDone = (keywordsRes || []).every(
            (kw: SeoKeyword) => kw.auto_call_status === 'done' || kw.auto_call_status === 'fail'
          );
          if ((overviewRes?.today && allDone) || attempts >= maxAttempts) {
            clearInterval(poll);
            setRefreshing(false);
          }
        } catch {
          // Keep polling on error
          if (attempts >= maxAttempts) {
            clearInterval(poll);
            setRefreshing(false);
          }
        }
      }, 5000);
    } catch (err) {
      console.error("Failed to trigger ranking:", err);
      setRefreshing(false);
    }
  };

  // Filter keywords by search
  const filteredKeywords = seoKeywords.filter(kw =>
    kw.keyword.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Column visibility state
  const [visibleColumns, setVisibleColumns] = useState<ColumnVisibility>({
    volume: true,
    best: true,
    clicks: true,
    impressions: true,
    "1d": true,
    "7d": true,
    "15d": true,
    serp: true,
    tags: true,
    date: true,
  });
  const [tempVisibleColumns, setTempVisibleColumns] = useState<ColumnVisibility>({ ...visibleColumns });
  const [columnPopoverOpen, setColumnPopoverOpen] = useState(false);

  const toggleKeywordSelection = (id: number) => {
    setSelectedKeywords((prev) =>
      prev.includes(id) ? prev.filter((k) => k !== id) : [...prev, id]
    );
  };

  const toggleAllKeywords = () => {
    if (selectedKeywords.length === filteredKeywords.length) {
      setSelectedKeywords([]);
    } else {
      setSelectedKeywords(filteredKeywords.map((k) => k.id));
    }
  };

  const toggleGroupKeywords = (groupKeywordIds: number[]) => {
    const allSelected = groupKeywordIds.every((id) => selectedKeywords.includes(id));
    if (allSelected) {
      setSelectedKeywords((prev) => prev.filter((id) => !groupKeywordIds.includes(id)));
    } else {
      setSelectedKeywords((prev) => [...new Set([...prev, ...groupKeywordIds])]);
    }
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
  const getTagGroups = () => {
    const groups: Record<string, typeof filteredKeywords> = {};
    filteredKeywords.forEach((kw) => {
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
        <Button className="gradient-primary shadow-md shadow-primary/20" onClick={handleRefresh} disabled={refreshing || !activeDomainId}>
          <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
          {refreshing ? 'Refreshing...' : 'Refresh Data'}
        </Button>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground mr-2" />
          <span className="text-muted-foreground">Loading SEO data...</span>
        </div>
      )}

      {!loading && !activeDomainId && (
        <Card className="p-8 text-center">
          <p className="text-muted-foreground">Please select an active domain to view SEO rankings.</p>
        </Card>
      )}

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
                    <div className="p-2 rounded-lg bg-muted/30 border border-border">
                      <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Top 3</p>
                      <p className="text-lg font-bold font-inter">{overview?.today?.top_3_count ?? 0}</p>
                    </div>
                    <div className="p-2 rounded-lg bg-muted/30 border border-border">
                      <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Top 10</p>
                      <p className="text-lg font-bold font-inter">{overview?.today?.top_10_count ?? 0}</p>
                    </div>
                    <div className="p-2 rounded-lg bg-muted/30 border border-border">
                      <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Top 50</p>
                      <p className="text-lg font-bold font-inter">{overview?.today?.top_50_count ?? 0}</p>
                    </div>
                    <div className="p-2 rounded-lg bg-muted/30 border border-border">
                      <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Not Ranked</p>
                      <p className="text-lg font-bold font-inter">{overview?.today?.not_ranked_count ?? 0}</p>
                    </div>
                  </div>

                  <div className="pt-2 border-t flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-muted-foreground">Best</span>
                      <span className="font-semibold">{overview?.today?.total_keywords ?? 0} keywords</span>
                    </div>
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

            {/* Second Row - SERP Features & Google Ads */}
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
                      <span className="text-lg font-bold font-inter">3</span>
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
                      <span className="text-lg font-bold font-inter">0</span>
                    </div>
                    <div className="flex items-center justify-between p-2 rounded-lg bg-muted/30 border border-border">
                      <div className="flex items-center gap-2">
                        {[1, 2, 3, 4, 5].map((_, i) => (
                          <Star key={i} className="h-4 w-4 text-yellow-500 fill-yellow-500" />
                        ))}
                        <span className="text-xs text-muted-foreground ml-2">(4-5 stars)</span>
                      </div>
                      <span className="text-lg font-bold font-inter">0</span>
                    </div>
                  </div>

                  <div className="pt-2 border-t flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-muted-foreground">Total Features</span>
                      <span className="font-semibold">3</span>
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
                        <span className="text-xs text-muted-foreground">You: <span className="text-lg font-bold font-inter text-foreground">0</span></span>
                        <span className="text-xs text-muted-foreground">Others: <span className="text-lg font-bold font-inter text-foreground">0</span></span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between p-2 rounded-lg bg-muted/30 border border-border">
                      <span className="text-sm font-medium">Above the fold</span>
                      <div className="flex items-center gap-4">
                        <span className="text-xs text-muted-foreground">You: <span className="text-lg font-bold font-inter text-foreground">0</span></span>
                        <span className="text-xs text-muted-foreground">Others: <span className="text-lg font-bold font-inter text-foreground">0</span></span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between p-2 rounded-lg bg-muted/30 border border-border">
                      <span className="text-sm font-medium">Below the fold</span>
                      <div className="flex items-center gap-4">
                        <span className="text-xs text-muted-foreground">You: <span className="text-lg font-bold font-inter text-foreground">0</span></span>
                        <span className="text-xs text-muted-foreground">Others: <span className="text-lg font-bold font-inter text-foreground">0</span></span>
                      </div>
                    </div>
                  </div>

                  <div className="pt-2 border-t flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-muted-foreground">Your Ads</span>
                      <span className="font-semibold">0 placements</span>
                    </div>
                  </div>
                </div>
              </Card>
            </div>
          </CardContent>
        )}
      </Card>

      {/* Keywords Section */}
      <div className="space-y-3">
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
                  <Button variant="outline" className="gap-2">
                    <Download className="h-4 w-4" />
                    Export
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start" className="w-56">
                  <DropdownMenuItem className="cursor-pointer">
                    Export Project In .CSV
                  </DropdownMenuItem>
                  <DropdownMenuItem className="cursor-pointer">
                    Export Project In .PDF
                  </DropdownMenuItem>
                  <DropdownMenuItem className="cursor-pointer">
                    Export Keywords In .TXT
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            <div className="flex items-center gap-2">
              <Button variant="outline" size="icon">
                <Tag className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="icon">
                <RefreshCw className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="icon">
                <Trash2 className="h-4 w-4" />
              </Button>

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
                        { key: "serp", label: "SERP" },
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
                        checked={selectedKeywords.length === filteredKeywords.length}
                        onCheckedChange={toggleAllKeywords}
                      />
                    </TableHead>
                    <TableHead className="w-20 text-xs font-semibold py-2">ACTIONS</TableHead>
                    <TableHead className="text-xs font-semibold py-2">KEYWORD</TableHead>
                    <TableHead className="text-center text-xs font-semibold py-2 w-14">RANK</TableHead>
                    {visibleColumns.volume && (
                      <TableHead className="text-center text-xs font-semibold py-2 w-16">VOLUME</TableHead>
                    )}
                    {visibleColumns.best && (
                      <TableHead className="text-center text-xs font-semibold py-2 w-12">BEST</TableHead>
                    )}
                    {visibleColumns.clicks && (
                      <TableHead className="text-center text-xs font-semibold py-2 w-12">CLKS</TableHead>
                    )}
                    {visibleColumns.impressions && (
                      <TableHead className="text-center text-xs font-semibold py-2 w-12">IMPS</TableHead>
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
                  {filteredKeywords.map((keyword) => (
                    <TableRow key={keyword.id} className="hover:bg-muted/30">
                      <TableCell className="py-1.5">
                        <Checkbox
                          checked={selectedKeywords.includes(keyword.id)}
                          onCheckedChange={() => toggleKeywordSelection(keyword.id)}
                        />
                      </TableCell>
                      <TableCell className="py-1.5">
                        <div className="flex items-center gap-0">
                          <Button variant="ghost" size="icon" className="h-6 w-6">
                            <span className="text-red-500 font-bold text-xs">G</span>
                          </Button>
                          <Button variant="ghost" size="icon" className="h-6 w-6">
                            <BarChart3 className="h-3.5 w-3.5 text-muted-foreground" />
                          </Button>
                          <Button variant="ghost" size="icon" className="h-6 w-6">
                            <Star className="h-3.5 w-3.5 text-muted-foreground" />
                          </Button>
                        </div>
                      </TableCell>
                      <TableCell className="py-1.5">
                        <div className="flex items-center gap-2">
                          <img
                            src={`https://flagcdn.com/16x12/${keyword.country.toLowerCase()}.png`}
                            alt={keyword.country}
                            className="w-4 h-3 object-cover rounded-sm shadow-sm flex-shrink-0"
                          />
                          <div className="min-w-0">
                            <p className="font-medium text-sm truncate">{keyword.keyword}</p>
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
                      <TableCell className="text-center py-1.5">
                        {keyword.rankDisplay ? (
                          <span className="text-muted-foreground text-sm">{keyword.rankDisplay}</span>
                        ) : (
                          <span className="font-semibold text-sm">{keyword.rank}</span>
                        )}
                      </TableCell>
                      {visibleColumns.volume && (
                        <TableCell className="text-center py-1.5">
                          <div className="flex items-center justify-center gap-0.5">
                            <span className="text-sm">{formatVolume(keyword.volume)}</span>
                          </div>
                        </TableCell>
                      )}
                      {visibleColumns.best && (
                        <TableCell className="text-center font-semibold py-1.5 text-sm">{keyword.best}</TableCell>
                      )}
                      {visibleColumns.clicks && (
                        <TableCell className="text-center py-1.5 text-sm">{keyword.clicks}</TableCell>
                      )}
                      {visibleColumns.impressions && (
                        <TableCell className="text-center py-1.5 text-sm">{keyword.impressions}</TableCell>
                      )}
                      {visibleColumns["1d"] && (
                        <TableCell className="text-center py-1.5">
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
                        <TableCell className="text-center py-1.5">
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
                        <TableCell className="text-center py-1.5">
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
                        <TableCell className="text-center py-1.5 text-sm">
                          {keyword.serp ? (
                            <span className="text-green-500 font-medium">{keyword.serp}</span>
                          ) : (
                            <span className="text-muted-foreground">NA</span>
                          )}
                        </TableCell>
                      )}
                      {visibleColumns.tags && (
                        <TableCell className="text-center py-1.5 text-sm">
                          {keyword.tags.length > 0 ? (
                            <span className="inline-flex items-center gap-1">
                              {keyword.tags.length}
                              <Tag className="h-3 w-3 text-primary" />
                            </span>
                          ) : (
                            <span className="text-xs text-primary font-medium cursor-pointer hover:underline">ADD</span>
                          )}
                        </TableCell>
                      )}
                      {visibleColumns.date && (
                        <TableCell className="py-1.5">
                          <div>
                            <p className="text-xs text-muted-foreground whitespace-nowrap">{keyword.date}</p>
                            <p className="text-xs text-muted-foreground/60 whitespace-nowrap">{keyword.timeAgo}</p>
                          </div>
                        </TableCell>
                      )}
                      <TableCell className="py-1.5">
                        <Button variant="ghost" size="icon" className="h-6 w-6">
                          <ChevronRight className="h-3.5 w-3.5" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        ) : (
          /* Grid View - Keywords grouped by tags */
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {Object.entries(getTagGroups()).map(([tagName, keywords]) => (
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
                        <TableHead className="w-8 py-1.5">
                          <Checkbox
                            checked={keywords.every((kw) => selectedKeywords.includes(kw.id))}
                            onCheckedChange={() => toggleGroupKeywords(keywords.map((kw) => kw.id))}
                          />
                        </TableHead>
                        <TableHead className="text-xs font-semibold py-1.5">KEYWORD</TableHead>
                        <TableHead className="text-center text-xs font-semibold py-1.5 w-14">RANK</TableHead>
                        <TableHead className="w-8 py-1.5"></TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {keywords.map((keyword) => (
                        <TableRow key={keyword.id} className="hover:bg-muted/30">
                          <TableCell className="py-1.5">
                            <Checkbox
                              checked={selectedKeywords.includes(keyword.id)}
                              onCheckedChange={() => toggleKeywordSelection(keyword.id)}
                            />
                          </TableCell>
                          <TableCell className="py-1.5">
                            <div className="flex items-center gap-1.5">
                              <div className="flex items-center gap-0 flex-shrink-0">
                                <Button variant="ghost" size="icon" className="h-5 w-5">
                                  <span className="text-red-500 font-bold text-[10px]">G</span>
                                </Button>
                                <Button variant="ghost" size="icon" className="h-5 w-5">
                                  <BarChart3 className="h-3 w-3 text-muted-foreground" />
                                </Button>
                              </div>
                              <img
                                src={`https://flagcdn.com/16x12/${keyword.country.toLowerCase()}.png`}
                                alt={keyword.country}
                                className="w-4 h-3 object-cover rounded-sm shadow-sm flex-shrink-0"
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
                          <TableCell className="text-center py-1.5">
                            {keyword.rankDisplay ? (
                              <span className="text-muted-foreground text-xs">{keyword.rankDisplay}</span>
                            ) : (
                              <span className="font-semibold text-xs">{keyword.rank}</span>
                            )}
                          </TableCell>
                          <TableCell className="py-1.5">
                            <Button variant="ghost" size="icon" className="h-5 w-5 text-primary">
                              <ChevronRight className="h-3.5 w-3.5" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default SeoRankings;
