import { useState, useEffect, useMemo } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  ArrowLeft,
  ArrowUp,
  ArrowDown,
  Minus,
  RefreshCw,
  Trash2,
  Plus,
  ExternalLink,
  Monitor,
  Smartphone,
  Globe,
  Star,
  Loader2,
  Settings2,
  ChevronRight,
  Calendar,
  Tag,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/services/api";
import { useDomainStore } from "@/stores/domainStore";
import { PageLoader } from "@/components/PageLoader";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from "recharts";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
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
  snippets_details: any;
  keyword_snippet: any;
  gsc_clicks: number;
  gsc_impressions: number;
  site_url: string;
  target_url: string;
  search_results: string;
  search_volume: number | null;
  region: string;
  isocode: string;
  language_code: string;
  tags: string[];
  favour: number;
  auto_call_status: string;
  last_ranked_date: string | null;
  created_at: string;
  modified_at: string;
}

interface RankHistoryPoint {
  id: number;
  rank_position: number;
  snapshot_date: string;
}

interface VolumeData {
  average_volume: number;
  top_volume: number;
  low_volume: number;
  comp_level: string;
  comp_index: string;
  month_wise_volume: number[];
  month_labels: string[];
}

interface Competitor {
  rn: number;
  dn: string;
  lk: string;
}

interface Note {
  id: number;
  title: string;
  notes: string;
  note_date: string;
  created_by_name: string;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Helper Components
// ---------------------------------------------------------------------------

function ChangeIndicator({ val, mark }: { val: number; mark: string }) {
  if (mark === "up") {
    return (
      <span className="inline-flex items-center gap-1 text-green-600 font-semibold">
        <ArrowUp className="h-3.5 w-3.5" />
        {val}
      </span>
    );
  }
  if (mark === "down") {
    return (
      <span className="inline-flex items-center gap-1 text-red-500 font-semibold">
        <ArrowDown className="h-3.5 w-3.5" />
        {val}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-muted-foreground">
      <Minus className="h-3.5 w-3.5" />
    </span>
  );
}

function RankDisplay({ rank }: { rank: number }) {
  if (!rank || rank === 0) {
    return <span className="text-3xl font-bold text-muted-foreground">&gt;100</span>;
  }
  return <span className="text-3xl font-bold">{rank}</span>;
}

// ---------------------------------------------------------------------------
// Rank History Chart Filters
// ---------------------------------------------------------------------------
const RANK_FILTER_OPTIONS = [
  { label: "Today", days: 1 },
  { label: "Week", days: 7 },
  { label: "Month", days: 30 },
  { label: "Quarter", days: 90 },
  { label: "Year", days: 365 },
];

const MORE_FILTER_OPTIONS = [
  { label: "Last Week", days: 7 },
  { label: "Last Month", days: 30 },
  { label: "Last Quarter", days: 90 },
  { label: "Last Year", days: 365 },
];

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------
const SeoKeywordDetail = () => {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { selectedDomain } = useDomainStore();

  // Core data
  const [kwData, setKwData] = useState<SeoKeyword | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  // "volume-history" is hidden (no volume data source) — an old bookmarked
  // ?tab=volume-history link would otherwise land on a tab with no trigger.
  const requestedTab = searchParams.get("tab");
  const [activeTab, setActiveTab] = useState(
    !requestedTab || requestedTab === "volume-history" ? "overview" : requestedTab
  );

  // Rank History
  const [rankHistory, setRankHistory] = useState<RankHistoryPoint[]>([]);
  const [rankDays, setRankDays] = useState(7);
  const [moreFilterActive, setMoreFilterActive] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  // Volume History
  const [volumeData, setVolumeData] = useState<VolumeData | null>(null);
  const [isLoadingVolume, setIsLoadingVolume] = useState(false);

  // Competitors
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [competitorAds, setCompetitorAds] = useState<any[]>([]);
  const [compType, setCompType] = useState("tp");
  const [isLoadingComp, setIsLoadingComp] = useState(false);

  // Notes
  const [notes, setNotes] = useState<Note[]>([]);
  const [noteDates, setNoteDates] = useState<string[]>([]);
  const [isLoadingNotes, setIsLoadingNotes] = useState(false);
  const [showNoteDialog, setShowNoteDialog] = useState(false);
  const [editingNote, setEditingNote] = useState<Note | null>(null);
  const [noteForm, setNoteForm] = useState({ title: "", notes: "", note_date: "" });

  // ---------------------------------------------------------------------------
  // Load keyword detail
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (id) loadKeywordDetail();
  }, [id]);

  // When the selected domain changes, check if this keyword still belongs to it.
  // If not, navigate back to the rankings list for the new domain.
  useEffect(() => {
    if (!selectedDomain || !kwData) return;
    if (kwData.domain !== selectedDomain.id) {
      navigate('/seo-rankings', { replace: true });
    }
  }, [selectedDomain, kwData, navigate]);

  const loadKeywordDetail = async () => {
    try {
      setIsLoading(true);
      const data = await apiClient.getSeoKeywordDetail(parseInt(id!)) as SeoKeyword;
      setKwData(data);
    } catch (error: any) {
      toast({ title: "Error", description: error.message || "Failed to load keyword", variant: "destructive" });
    } finally {
      setIsLoading(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Tab data loaders (lazy)
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (!kwData) return;
    if (activeTab === "rank-history") loadRankHistory();
    if (activeTab === "volume-history") loadVolumeHistory();
    if (activeTab === "competitors") loadCompetitors();
    if (activeTab === "notes") loadNotes();
  }, [activeTab, kwData]);

  useEffect(() => {
    if (activeTab === "rank-history" && kwData) loadRankHistory();
  }, [rankDays]);

  useEffect(() => {
    if (activeTab === "competitors" && kwData) loadCompetitors();
  }, [compType]);

  const loadRankHistory = async () => {
    try {
      setIsLoadingHistory(true);
      const data = await apiClient.getSeoRankHistory(parseInt(id!), rankDays) as RankHistoryPoint[];
      setRankHistory(data);
    } catch { /* empty */ } finally {
      setIsLoadingHistory(false);
    }
  };

  const loadVolumeHistory = async () => {
    try {
      setIsLoadingVolume(true);
      const data = await apiClient.getSeoKeywordVolume(parseInt(id!)) as VolumeData;
      setVolumeData(data);
    } catch { /* empty */ } finally {
      setIsLoadingVolume(false);
    }
  };

  const loadCompetitors = async () => {
    try {
      setIsLoadingComp(true);
      const data = await apiClient.getSeoKeywordCompetitors(parseInt(id!), compType) as any;
      setCompetitors(data.competitors || []);
      setCompetitorAds(data.ads || []);
    } catch { /* empty */ } finally {
      setIsLoadingComp(false);
    }
  };

  const loadNotes = async () => {
    try {
      setIsLoadingNotes(true);
      const data = await apiClient.getSeoKeywordNotes(parseInt(id!)) as any;
      setNotes(data.notes || []);
      setNoteDates(data.note_dates || []);
    } catch { /* empty */ } finally {
      setIsLoadingNotes(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Notes CRUD
  // ---------------------------------------------------------------------------
  const openNewNote = () => {
    setEditingNote(null);
    setNoteForm({ title: "", notes: "", note_date: new Date().toISOString().split("T")[0] });
    setShowNoteDialog(true);
  };

  const openEditNote = (note: Note) => {
    setEditingNote(note);
    setNoteForm({ title: note.title, notes: note.notes, note_date: note.note_date });
    setShowNoteDialog(true);
  };

  const handleSaveNote = async () => {
    if (!noteForm.title.trim() || !noteForm.notes.trim()) {
      toast({ title: "Validation", description: "Title and notes are required", variant: "destructive" });
      return;
    }
    try {
      if (editingNote) {
        await apiClient.updateSeoKeywordNote(parseInt(id!), editingNote.id, noteForm);
        toast({ title: "Note updated" });
      } else {
        await apiClient.createSeoKeywordNote(parseInt(id!), noteForm);
        toast({ title: "Note created" });
      }
      setShowNoteDialog(false);
      loadNotes();
    } catch (error: any) {
      toast({ title: "Error", description: error.message, variant: "destructive" });
    }
  };

  const handleDeleteNote = async (noteId: number) => {
    try {
      await apiClient.deleteSeoKeywordNote(parseInt(id!), noteId);
      toast({ title: "Note deleted" });
      loadNotes();
    } catch (error: any) {
      toast({ title: "Error", description: error.message, variant: "destructive" });
    }
  };

  const handleDeleteKeyword = async () => {
    if (!window.confirm("Are you sure you want to delete this keyword?")) return;
    try {
      await apiClient.deleteSeoKeyword(parseInt(id!));
      toast({ title: "Keyword deleted" });
      navigate("/seo-rankings", { replace: true });
    } catch (error: any) {
      toast({ title: "Error", description: error.message || "Failed to delete keyword", variant: "destructive" });
    }
  };

  // ---------------------------------------------------------------------------
  // Chart data
  // ---------------------------------------------------------------------------
  const rankChartData = useMemo(() => {
    return rankHistory.map((h) => ({
      date: new Date(h.snapshot_date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
      rank: h.rank_position === 0 ? 101 : h.rank_position,
      rawDate: h.snapshot_date,
    }));
  }, [rankHistory]);

  // Dynamic Y-axis range matching RankMax logic
  const rankYDomain = useMemo(() => {
    if (rankChartData.length === 0) return { min: 1, max: 101, ticks: [1, 30, 60, 101] };
    const ranks = rankChartData.map((d) => d.rank);
    let minVal = Math.min(...ranks);
    let maxVal = Math.max(...ranks);

    if (maxVal === minVal || (maxVal - minVal) < 6) {
      minVal -= 2;
      maxVal += 3;
    } else {
      const avg = (maxVal - minVal) / 4;
      minVal = minVal - avg;
    }

    minVal = Math.max(1, Math.floor(minVal));
    maxVal = Math.ceil(maxVal);

    // Generate ~5 evenly spaced ticks
    const step = Math.max(1, Math.round((maxVal - minVal) / 5));
    const ticks: number[] = [];
    for (let v = minVal; v <= maxVal; v += step) {
      ticks.push(Math.round(v));
    }
    if (ticks[ticks.length - 1] < maxVal) ticks.push(maxVal);

    return { min: minVal, max: maxVal, ticks };
  }, [rankChartData]);

  const volumeChartData = useMemo(() => {
    if (!volumeData?.month_wise_volume?.length) return [];
    return volumeData.month_wise_volume.map((vol, i) => ({
      month: volumeData.month_labels?.[i] || `Month ${i + 1}`,
      volume: vol,
    }));
  }, [volumeData]);

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "N/A";
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  };

  const timeAgo = (dateStr: string | null) => {
    if (!dateStr) return "N/A";
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const hours = Math.floor(diffMs / (1000 * 60 * 60));
    if (hours < 1) return "Just now";
    if (hours < 24) return `${hours} hours ago`;
    const days = Math.floor(hours / 24);
    return `${days} day${days > 1 ? "s" : ""} ago`;
  };

  const formatVolume = (vol: number) => {
    if (vol >= 1000000) return `${(vol / 1000000).toFixed(1)}M`;
    if (vol >= 1000) return `${(vol / 1000).toFixed(1)}K`;
    return String(vol);
  };

  const getRegionLabel = (region: string) => {
    const map: Record<string, string> = {
      "google.com": "United States",
      "google.co.in": "India",
      "google.co.uk": "United Kingdom",
      "google.com.au": "Australia",
      "google.ca": "Canada",
      "google.ae": "UAE",
    };
    return map[region] || region;
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  if (isLoading) return <PageLoader />;

  if (!kwData) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card className="p-8 text-center">
          <h2 className="text-2xl font-bold mb-4">Keyword Not Found</h2>
          <p className="text-muted-foreground mb-4">The keyword you're looking for doesn't exist.</p>
          <Button onClick={() => navigate("/seo-rankings")}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Rankings
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6 bg-background animate-fade-in">
      {/* ================================================================ */}
      {/* HEADER */}
      {/* ================================================================ */}
      <div className="flex items-center justify-between pb-4 border-b border-border/50">
        <div className="flex items-center gap-4">
          <Button variant="outline" size="icon" onClick={() => navigate("/seo-rankings")} className="border-border/50">
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold tracking-tight font-inter">{kwData.domain_name}</h1>
              {kwData.favour === 1 && <Star className="h-5 w-5 fill-yellow-400 text-yellow-400" />}
            </div>
            <p className="text-muted-foreground mt-0.5">{kwData.keyword_text}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={loadKeywordDetail} className="border-border/50">
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="icon" className="border-border/50 text-red-500 hover:text-red-700 hover:bg-red-50" onClick={handleDeleteKeyword}>
            <Trash2 className="h-4 w-4" />
          </Button>
          <Button size="sm" onClick={openNewNote} className="gradient-primary text-white">
            <Calendar className="h-4 w-4 mr-1" />
            Add Notes
          </Button>
        </div>
      </div>

      {/* ================================================================ */}
      {/* TABS */}
      {/* ================================================================ */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="bg-muted/50 p-1 border border-border">
          <TabsTrigger value="overview" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">
            Overview
          </TabsTrigger>
          <TabsTrigger value="rank-history" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">
            Rank History
          </TabsTrigger>
          {/* Volume History hidden: DataBlue's SERP API returns no search-volume
              data and no other volume provider is configured, so the tab could
              only ever render zeros. Restore this trigger (and the matching
              TabsContent) once a keyword-volume source is wired up. */}
          <TabsTrigger value="competitors" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">
            Competitors
          </TabsTrigger>
          <TabsTrigger value="notes" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">
            Notes {notes.length > 0 && `(${notes.length})`}
          </TabsTrigger>
        </TabsList>

        {/* ============================================================== */}
        {/* TAB 1: OVERVIEW */}
        {/* ============================================================== */}
        <TabsContent value="overview" className="space-y-6 mt-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left — Keyword Info */}
            <Card className="p-6 border border-border">
              <h3 className="text-lg font-semibold mb-4">Overview</h3>
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <ExternalLink className="h-4 w-4 text-muted-foreground shrink-0" />
                  <div>
                    <p className="text-xs text-muted-foreground">URL</p>
                    <p className="text-sm font-medium break-all">{kwData.site_url || kwData.target_url || kwData.domain_url}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <RefreshCw className="h-4 w-4 text-muted-foreground shrink-0" />
                  <div>
                    <p className="text-xs text-muted-foreground">Last update</p>
                    <p className="text-sm font-medium">{timeAgo(kwData.last_ranked_date)} ({formatDate(kwData.last_ranked_date)})</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {kwData.platform === "desktop" ? (
                    <Monitor className="h-4 w-4 text-muted-foreground shrink-0" />
                  ) : (
                    <Smartphone className="h-4 w-4 text-muted-foreground shrink-0" />
                  )}
                  <div>
                    <p className="text-xs text-muted-foreground">Platform</p>
                    <p className="text-sm font-medium capitalize">{kwData.platform}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Globe className="h-4 w-4 text-muted-foreground shrink-0" />
                  <div>
                    <p className="text-xs text-muted-foreground">Search engine</p>
                    <p className="text-sm font-medium">
                      Google{" "}
                      <a
                        href={`https://www.google.com/search?q=${encodeURIComponent(kwData.keyword_text)}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary text-xs hover:underline"
                      >
                        (View SERP)
                      </a>
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-lg shrink-0">
                    <img
                      src={`https://flagcdn.com/20x15/${kwData.isocode}.png`}
                      alt={kwData.isocode}
                      className="inline-block"
                      onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                    />
                  </span>
                  <div>
                    <p className="text-xs text-muted-foreground">Country</p>
                    <p className="text-sm font-medium">{getRegionLabel(kwData.region)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm text-muted-foreground shrink-0 w-4 text-center">A</span>
                  <div>
                    <p className="text-xs text-muted-foreground">Language</p>
                    <p className="text-sm font-medium">({kwData.language_code})</p>
                  </div>
                </div>
              </div>
            </Card>

            {/* Right — Rank Cards */}
            <div className="lg:col-span-2 space-y-6">
              {/* 4-box rank display */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card className="p-5 text-center border border-border">
                  <p className="text-xs text-muted-foreground mb-2 font-medium">Current</p>
                  <RankDisplay rank={kwData.rank_now} />
                </Card>
                <Card className="p-5 text-center border border-border">
                  <p className="text-xs text-muted-foreground mb-2 font-medium">Last</p>
                  <RankDisplay rank={kwData.rank_now + kwData.day_val * (kwData.day_mark === "up" ? 1 : kwData.day_mark === "down" ? -1 : 0)} />
                </Card>
                <Card className="p-5 text-center border border-border">
                  <p className="text-xs text-muted-foreground mb-2 font-medium">Change</p>
                  <div className="flex justify-center">
                    <ChangeIndicator val={kwData.day_val} mark={kwData.day_mark} />
                  </div>
                </Card>
                <Card className="p-5 text-center border border-border">
                  <p className="text-xs text-muted-foreground mb-2 font-medium">Best</p>
                  <RankDisplay rank={kwData.top_rank || 0} />
                </Card>
              </div>

              {/* Tags */}
              <Card className="p-5 border border-border">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-semibold">Tags</h4>
                  <Button variant="outline" size="sm" className="text-xs h-7">
                    <Plus className="h-3 w-3 mr-1" />
                    Add
                  </Button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {(kwData.tags || []).length > 0 ? (
                    kwData.tags.map((tag, i) => (
                      <Badge key={i} variant="secondary" className="text-xs">{tag}</Badge>
                    ))
                  ) : (
                    <span className="text-sm text-muted-foreground italic">No tags found on keyword</span>
                  )}
                </div>
              </Card>

              {/* Current Google SERP view */}
              <Card className="p-5 border border-border">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-semibold flex items-center gap-1">
                    Current Google SERP view of your website
                    <span className="text-muted-foreground text-xs cursor-pointer" title="Shows how your website appears in Google search results"><svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="inline-block align-[-1px] opacity-50" role="img"><title>Shows how your website appears in Google search results</title><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg></span>
                  </h4>
                  <a
                    href={`https://www.google.com/search?q=${encodeURIComponent(kwData.keyword_text)}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-primary hover:underline flex items-center gap-1"
                  >
                    View SERP <ChevronRight className="h-3.5 w-3.5" />
                  </a>
                </div>
                {kwData.snippets_details && kwData.snippets_details.title ? (
                  <div className="space-y-2 p-3 bg-muted/30 rounded-lg">
                    <p className="text-sm font-medium text-blue-600">{kwData.snippets_details.title}</p>
                    <p className="text-xs text-green-700">{kwData.site_url || kwData.domain_url}</p>
                    <p className="text-xs text-muted-foreground">{kwData.snippets_details.description}</p>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground italic">No snippet detail available</p>
                )}
              </Card>

              {/* SERP Features */}
              <Card className="p-5 border border-border">
                <h4 className="text-sm font-semibold mb-3">SERP Features</h4>
                <div className="flex flex-wrap gap-3">
                  {kwData.featured_snippet && <Badge className="bg-blue-100 text-blue-800 border-blue-200">Featured Snippet</Badge>}
                  {kwData.knowledge_panel && <Badge className="bg-purple-100 text-purple-800 border-purple-200">Knowledge Panel</Badge>}
                  {kwData.ads && <Badge className="bg-amber-100 text-amber-800 border-amber-200">Ads</Badge>}
                  {kwData.review && (
                    <Badge className="bg-green-100 text-green-800 border-green-200">
                      Reviews {kwData.total_rating !== "-" && `(${kwData.total_rating})`}
                    </Badge>
                  )}
                  {!kwData.featured_snippet && !kwData.knowledge_panel && !kwData.ads && !kwData.review && (
                    <span className="text-sm text-muted-foreground">NA</span>
                  )}
                </div>
              </Card>

              {/* Change summary */}
              <Card className="p-5 border border-border">
                <h4 className="text-sm font-semibold mb-3">Rank Changes</h4>
                <div className="grid grid-cols-4 gap-4 text-center">
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">1D</p>
                    <ChangeIndicator val={kwData.day_val} mark={kwData.day_mark} />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">7D</p>
                    <ChangeIndicator val={kwData.week_val} mark={kwData.week_mark} />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">15D</p>
                    <ChangeIndicator val={kwData.half_month_val} mark={kwData.half_month_mark} />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">30D</p>
                    <ChangeIndicator val={kwData.month_val} mark={kwData.month_mark} />
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </TabsContent>

        {/* ============================================================== */}
        {/* TAB 2: RANK HISTORY */}
        {/* ============================================================== */}
        <TabsContent value="rank-history" className="space-y-6 mt-6">
          <Card className="p-6 border border-border">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold">Rank History</h3>
              <div className="flex gap-2 flex-wrap">
                {RANK_FILTER_OPTIONS.map((opt) => (
                  <Button
                    key={opt.label}
                    variant={rankDays === opt.days && !moreFilterActive ? "default" : "outline"}
                    size="sm"
                    onClick={() => { setRankDays(opt.days); setMoreFilterActive(false); }}
                    className={rankDays === opt.days && !moreFilterActive ? "gradient-primary text-white" : ""}
                  >
                    {opt.label}
                  </Button>
                ))}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant={moreFilterActive ? "default" : "outline"}
                      size="sm"
                      className={moreFilterActive ? "gradient-primary text-white" : ""}
                    >
                      More
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    {MORE_FILTER_OPTIONS.map((opt) => (
                      <DropdownMenuItem
                        key={opt.label}
                        onClick={() => { setRankDays(opt.days); setMoreFilterActive(true); }}
                        className="cursor-pointer"
                      >
                        <Tag className="h-3.5 w-3.5 mr-2 text-primary" />
                        {opt.label}
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>

            {isLoadingHistory ? (
              <div className="flex items-center justify-center py-16">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
              </div>
            ) : rankChartData.length === 0 ? (
              <div className="text-center py-16 text-muted-foreground">
                No rank history data available for this period.
              </div>
            ) : (
              <div className="relative">
                <ResponsiveContainer width="100%" height={420}>
                  <LineChart data={rankChartData} margin={{ top: 10, right: 20, left: 15, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.4} />
                    <XAxis
                      dataKey="date"
                      stroke="hsl(var(--muted-foreground))"
                      fontSize={11}
                      tickLine={{ stroke: "hsl(var(--border))" }}
                      interval={rankChartData.length <= 15 ? 0 : Math.floor(rankChartData.length / 15)}
                      angle={rankChartData.length > 30 ? -45 : 0}
                      textAnchor={rankChartData.length > 30 ? "end" : "middle"}
                      height={rankChartData.length > 30 ? 60 : 30}
                    />
                    <YAxis
                      reversed
                      domain={[rankYDomain.min, rankYDomain.max]}
                      ticks={rankYDomain.ticks}
                      stroke="hsl(var(--muted-foreground))"
                      fontSize={11}
                      tickFormatter={(val: number) => (val > 100 ? ">30" : String(Math.round(val)))}
                      width={40}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "hsl(var(--card))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "var(--radius)",
                        boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
                      }}
                      formatter={(value: any) => [value > 100 ? ">30" : `#${value}`, "Google Rank"]}
                      labelStyle={{ fontWeight: 600, marginBottom: 4 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="rank"
                      name="Google Rank"
                      stroke="hsl(var(--primary))"
                      strokeWidth={2.5}
                      dot={{ fill: "hsl(var(--primary))", r: rankChartData.length > 45 ? 2 : rankChartData.length === 1 ? 5 : 3.5, strokeWidth: 0 }}
                      activeDot={{ r: 6, strokeWidth: 0 }}
                      connectNulls
                    />
                  </LineChart>
                </ResponsiveContainer>
                {/* Watermark text (like RankMax) */}
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none select-none">
                  <span className="text-6xl font-bold text-muted-foreground/10 tracking-widest">Promptmaxx</span>
                </div>
                {/* Legend (like RankMax) */}
                <div className="flex items-center justify-center gap-6 mt-2">
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: "hsl(var(--primary))" }} />
                    <span className="text-sm text-muted-foreground font-medium">Google Rank</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-sm bg-yellow-500" />
                    <span className="text-sm text-muted-foreground font-medium">Notes</span>
                  </div>
                </div>
                {/* Description text (like RankMax) */}
                <p className="text-xs text-muted-foreground text-center mt-4 max-w-2xl mx-auto">
                  This graphs shows the record of improvement and decline in the ranking of this keyword. It accurately depicts the fluctuation in the position of the keyword over a period.
                </p>
              </div>
            )}
          </Card>
        </TabsContent>

        {/* ============================================================== */}
        {/* TAB 3: VOLUME HISTORY */}
        {/* ============================================================== */}
        <TabsContent value="volume-history" className="space-y-6 mt-6">
          {isLoadingVolume ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : (
            <>
              {/* Volume summary cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card className="p-5 text-center border border-border">
                  <p className="text-xs text-muted-foreground mb-2 font-medium">Top <span className="cursor-pointer" title="Highest search volume in the past year"><svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="inline-block align-[-1px] opacity-50" role="img"><title>Highest search volume in the past year</title><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg></span></p>
                  <span className="text-3xl font-bold">{formatVolume(volumeData?.top_volume || 0)}</span>
                </Card>
                <Card className="p-5 text-center border border-border">
                  <p className="text-xs text-muted-foreground mb-2 font-medium">Average</p>
                  <span className="text-3xl font-bold">{formatVolume(volumeData?.average_volume || kwData.search_volume || 0)}</span>
                </Card>
                <Card className="p-5 text-center border border-border">
                  <p className="text-xs text-muted-foreground mb-2 font-medium">Low</p>
                  <span className="text-3xl font-bold">{formatVolume(volumeData?.low_volume || 0)}</span>
                </Card>
                <Card className="p-5 text-center border border-border">
                  <p className="text-xs text-muted-foreground mb-2 font-medium">Competition Level</p>
                  <span className="text-3xl font-bold">{volumeData?.comp_level && volumeData.comp_level !== "-" ? volumeData.comp_level : "NA"}</span>
                </Card>
              </div>

              {/* Monthly volume breakdown cards */}
              <Card className="p-6 border border-border">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold">Keyword Search Volume History <span className="text-muted-foreground text-xs cursor-pointer" title="Monthly search volume breakdown"><svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="inline-block align-[-1px] opacity-50" role="img"><title>Monthly search volume breakdown</title><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg></span></h3>
                  {volumeData?.top_volume ? (
                    <span className="text-sm text-muted-foreground">
                      Top volume <strong>{formatVolume(volumeData.top_volume)}</strong> (1 Year)
                    </span>
                  ) : null}
                </div>

                {/* Monthly breakdown cards row */}
                {volumeChartData.length > 0 && (
                  <div className="flex gap-0 mb-6 overflow-x-auto">
                    {volumeChartData.map((item, i) => (
                      <div
                        key={i}
                        className="flex-1 min-w-[80px] text-center py-3 px-2 border border-border/50 first:rounded-l-lg last:rounded-r-lg"
                      >
                        <p className="text-xs text-muted-foreground mb-1">{item.month}</p>
                        <p className="text-sm font-bold">{formatVolume(item.volume)}</p>
                      </div>
                    ))}
                    <div className="flex-1 min-w-[80px] text-center py-3 px-2 border border-border/50 rounded-r-lg bg-primary/5">
                      <p className="text-xs text-muted-foreground mb-1">Average</p>
                      <p className="text-sm font-bold">{formatVolume(volumeData?.average_volume || 0)}</p>
                    </div>
                  </div>
                )}

                {volumeChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={350}>
                    <AreaChart data={volumeChartData}>
                      <defs>
                        <linearGradient id="volumeGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0.05} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="month" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                      <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "hsl(var(--card))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "var(--radius)",
                        }}
                      />
                      <Area
                        type="monotone"
                        dataKey="volume"
                        stroke="hsl(var(--primary))"
                        strokeWidth={2}
                        fill="url(#volumeGradient)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="text-center py-16 text-muted-foreground">
                    No volume history data available.
                  </div>
                )}
              </Card>
            </>
          )}
        </TabsContent>

        {/* ============================================================== */}
        {/* TAB 4: COMPETITORS */}
        {/* ============================================================== */}
        <TabsContent value="competitors" className="space-y-6 mt-6">
          <Card className="p-6 border border-border">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold">Competitors</h3>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="icon" className="border-border/50">
                    <Settings2 className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  {[
                    { label: "Top 10", value: "tp" },
                    { label: "Before You", value: "bf" },
                    { label: "After You", value: "ar" },
                  ].map((opt) => (
                    <DropdownMenuItem
                      key={opt.value}
                      onClick={() => setCompType(opt.value)}
                      className={`cursor-pointer ${compType === opt.value ? "text-primary font-semibold" : ""}`}
                    >
                      <Tag className="h-3.5 w-3.5 mr-2 text-primary" />
                      {opt.label}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            {isLoadingComp ? (
              <div className="flex items-center justify-center py-16">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
              </div>
            ) : competitors.length === 0 ? (
              <div className="text-center py-16 text-muted-foreground">
                No competitor data available.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {competitors.map((comp, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-4 p-3 rounded-lg border border-border/50 hover:border-primary/30 transition-colors"
                  >
                    <span className="w-8 h-8 flex items-center justify-center rounded-full bg-muted text-sm font-bold shrink-0">
                      {comp.rn || i + 1}
                    </span>
                    <img
                      src={`https://icons.duckduckgo.com/ip3/${comp.dn}.ico`}
                      alt=""
                      className="w-5 h-5 rounded shrink-0"
                      onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{comp.dn}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Competitor Ads */}
          <Card className="p-6 border border-border">
            <h3 className="text-lg font-semibold mb-4">Competitor in Google Ads</h3>
            {competitorAds.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No Google Ads competitors available.
              </div>
            ) : (
              <div className="space-y-3">
                {competitorAds.map((ad, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-4 p-3 rounded-lg border border-border/50"
                  >
                    <img
                      src={`https://icons.duckduckgo.com/ip3/${ad.domain}.ico`}
                      alt=""
                      className="w-5 h-5 rounded"
                      onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                    />
                    <span className="text-sm font-medium flex-1">{ad.domain}</span>
                    {ad.position === "11" && <Badge variant="secondary">Top</Badge>}
                    {ad.position === "10" && <Badge variant="secondary">Top + Bottom</Badge>}
                    {ad.position === "01" && <Badge variant="secondary">Bottom</Badge>}
                    {ad.is_recent && <Badge className="bg-green-100 text-green-800 text-xs">New</Badge>}
                  </div>
                ))}
              </div>
            )}
          </Card>
        </TabsContent>

        {/* ============================================================== */}
        {/* TAB 5: NOTES */}
        {/* ============================================================== */}
        <TabsContent value="notes" className="space-y-6 mt-6">
          <Card className="p-6 border border-border">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold">Total Keyword Notes</h3>
              <Button size="sm" onClick={openNewNote} className="gradient-primary text-white">
                <Plus className="h-4 w-4 mr-1" />
                Add Notes
              </Button>
            </div>

            {isLoadingNotes ? (
              <div className="flex items-center justify-center py-16">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
              </div>
            ) : notes.length === 0 ? (
              <div className="text-center py-16">
                <div className="mx-auto w-16 h-16 mb-4 rounded-lg bg-muted flex items-center justify-center">
                  <svg className="h-8 w-8 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <p className="text-muted-foreground">No Keyword Notes Found</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Title</TableHead>
                    <TableHead>Notes</TableHead>
                    <TableHead className="text-center">View</TableHead>
                    <TableHead className="text-center">Delete</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {notes.map((note) => (
                    <TableRow key={note.id}>
                      <TableCell className="text-sm">{formatDate(note.note_date)}</TableCell>
                      <TableCell className="font-medium">{note.title}</TableCell>
                      <TableCell className="text-sm text-muted-foreground max-w-xs truncate">{note.notes}</TableCell>
                      <TableCell className="text-center">
                        <Button variant="ghost" size="sm" onClick={() => openEditNote(note)}>
                          View
                        </Button>
                      </TableCell>
                      <TableCell className="text-center">
                        <Button variant="ghost" size="sm" className="text-red-500 hover:text-red-700" onClick={() => handleDeleteNote(note.id)}>
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </Card>
        </TabsContent>
      </Tabs>

      {/* ================================================================ */}
      {/* NOTE DIALOG */}
      {/* ================================================================ */}
      <Dialog open={showNoteDialog} onOpenChange={setShowNoteDialog}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>{editingNote ? "Edit Note" : "Add Note"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label className="text-sm font-medium mb-1 block">Date</label>
              <Input
                type="date"
                value={noteForm.note_date}
                onChange={(e) => setNoteForm({ ...noteForm, note_date: e.target.value })}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">Title</label>
              <Input
                placeholder="Note title"
                value={noteForm.title}
                onChange={(e) => setNoteForm({ ...noteForm, title: e.target.value })}
                maxLength={100}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">Notes</label>
              <Textarea
                placeholder="Write your note..."
                value={noteForm.notes}
                onChange={(e) => setNoteForm({ ...noteForm, notes: e.target.value })}
                rows={5}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowNoteDialog(false)}>Cancel</Button>
            <Button onClick={handleSaveNote} className="gradient-primary text-white">
              {editingNote ? "Update" : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default SeoKeywordDetail;
