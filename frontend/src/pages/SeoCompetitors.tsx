import { useState, useEffect, useRef, useCallback } from "react";
import { ExternalLink, Plus, Trash2, ChevronLeft, Search, ChevronRight, RefreshCw, MoreVertical, X, Loader2, ArrowUp, ArrowDown, ArrowUpDown, Users, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useDomainStore } from "@/stores/domainStore";
import { useSidebar } from "@/contexts/SidebarContext";
import { useToast } from "@/hooks/use-toast";
import apiClient from "@/services/api";

/* ─── Progress bar keyframes (matches RankMax: 10s per bar, sequential) ──── */
if (typeof document !== "undefined" && !document.getElementById("comp-pb-style")) {
  const s = document.createElement("style");
  s.id = "comp-pb-style";
  s.textContent = `@keyframes comp-pb{0%{width:0}100%{width:100%}}`;
  document.head.appendChild(s);
}

/* ─── Helper: extract project name from domain ────────────────────────────── */
function projectName(domain: string): string {
  try {
    const parts = domain.replace(/^www\./, "").split(".");
    if (parts.length >= 2) {
      return parts[0].charAt(0).toUpperCase() + parts[0].slice(1);
    }
    return domain.charAt(0).toUpperCase() + domain.slice(1);
  } catch {
    return domain;
  }
}

/* ─── Helper: bare hostname ───────────────────────────────────────────────────
   Strips scheme, www and any path so a stored URL like
   "https://www.keralatourism.org/" reads as "keralatourism.org". */
function bareDomain(url?: string): string {
  return (url || "")
    .trim()
    .replace(/^https?:\/\//i, "")
    .replace(/^www\./i, "")
    .replace(/[/?#].*$/, "");
}

/* ─── Helper: favicon URL ─────────────────────────────────────────────────── */
function favUrl(domain: string, sz = 64): string {
  return `https://www.google.com/s2/favicons?sz=${sz}&domain_url=${domain}`;
}

/* ─── Types ───────────────────────────────────────────────────────────────── */
interface Candidate { domain: string; count: number; tracked: boolean }
interface CompProject {
  id: number; competitor_domain: string; keyword_count: number;
  ranked_us: number; ranked_them: number; created_at: string;
}
interface CompKeyword {
  id: number; keyword: string; our_rank: number; their_rank: number;
  our_url: string; their_url: string;
  best_rank: number; search_volume: number | null;
  last_ranked_date: string | null;
  featured_snippet: boolean; knowledge_panel: boolean; ads: boolean;
}

/* ─── Sorting ─────────────────────────────────────────────────────────────────
   Matches the primary keyword table: click cycles asc -> desc -> off, and the
   first click uses whichever direction is actually useful for that column —
   rank 1 is the best rank, so ranks open ascending, while volume and date open
   with the largest first. */
type CompSortKey = "keyword" | "their_rank" | "our_rank" | "best_rank" | "volume" | "date";
const COMP_ASCENDING_FIRST: CompSortKey[] = ["keyword", "their_rank", "our_rank", "best_rank"];

/* Page sizes, matching the primary keyword table. */
const KW_PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

/* ─── Rank cell ───────────────────────────────────────────────────────────────
   Plain number, exactly as the primary keyword table renders a rank. This was
   a coloured, bordered badge — the only place in the app that boxed a rank,
   which made the competitor column read as a tag rather than a position. */
function RankCell({ rank }: { rank: number }) {
  if (!rank || rank <= 0)
    return <span className="text-muted-foreground text-sm">-</span>;
  return <span className="font-semibold text-sm">{rank}</span>;
}

/* ═════════════════════════════════════════════════════════════════════════════
   MAIN COMPONENT
   ═════════════════════════════════════════════════════════════════════════════ */
const SeoCompetitors = () => {
  const { selectedDomain } = useDomainStore();
  const { isOpen: sidebarOpen } = useSidebar();
  const { toast } = useToast();

  // View state
  const [view, setView] = useState<"init" | "analyzing" | "selecting" | "direct" | "keywords">("init");
  const [pageLoading, setPageLoading] = useState(true);
  const [analysisStatus, setAnalysisStatus] = useState("INIT");
  const [totalKeywords, setTotalKeywords] = useState(0);
  const [uniqueDomains, setUniqueDomains] = useState(0);

  // Selecting view
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [compSearch, setCompSearch] = useState("");
  const [trackedCount, setTrackedCount] = useState(0);
  const [adding, setAdding] = useState<string | null>(null);
  const [finishing, setFinishing] = useState(false);

  // Manual competitor add
  const [manualOpen, setManualOpen] = useState(false);
  const [manualDomain, setManualDomain] = useState("");
  const [manualBusy, setManualBusy] = useState(false);

  // Direct competitors
  const [projects, setProjects] = useState<CompProject[]>([]);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  // Keywords view
  const [selectedProject, setSelectedProject] = useState<CompProject | null>(null);
  const [keywords, setKeywords] = useState<CompKeyword[]>([]);
  const [kwSearch, setKwSearch] = useState("");
  const [sortKey, setSortKey] = useState<CompSortKey | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [currentPage, setCurrentPage] = useState(1);
  const [kwPerPage, setKwPerPage] = useState(25);

  // Wait state (after analysis completes, show "View Analysis" before transitioning)
  const [waitReady, setWaitReady] = useState(false);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const domainId = selectedDomain?.id;

  /* ── Load status on domain change ───────────────────────────────────────── */
  const loadProjects = useCallback(async () => {
    if (!domainId) return [];
    try {
      const data = await apiClient.getSeoCompetitorProjects(domainId);
      const ps = data.projects || [];
      setProjects(ps);
      return ps;
    } catch { return []; }
  }, [domainId]);

  const loadStatus = useCallback(async () => {
    if (!domainId) { setPageLoading(false); return; }
    setPageLoading(true);
    try {
      const data = await apiClient.getSeoCompetitorStatus(domainId);
      const st = data.status as string;
      setAnalysisStatus(st);
      setTotalKeywords(data.total_keywords || 0);
      setUniqueDomains(data.unique_domains || 0);

      if (st === "SCHD") {
        setView("analyzing");
        return;
      }

      // Always load existing projects
      const ps = await loadProjects();

      if (st === "COMP") {
        setCandidates(data.candidates || []);
        setTrackedCount(data.tracked_count || 0);
        // If user already added competitors, show them directly
        if (ps.length > 0) {
          setView("direct");
        } else {
          setView("selecting");
        }
      } else {
        // INIT / FAIL / other — show direct if projects exist, otherwise init
        if (ps.length > 0) {
          setView("direct");
        }
        // else: view stays "init" (set by useEffect reset)
      }
    } catch { /* ignore */ } finally {
      setPageLoading(false);
    }
  }, [domainId, loadProjects]);

  useEffect(() => {
    setView("init"); setProjects([]); setCandidates([]);
    setAnalysisStatus("INIT"); setTotalKeywords(0); setWaitReady(false);
    loadStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [domainId]);

  /* ── Poll while analyzing ───────────────────────────────────────────────── */
  useEffect(() => {
    if (view === "analyzing") {
      pollRef.current = setInterval(async () => {
        if (!domainId) return;
        try {
          const data = await apiClient.getSeoCompetitorStatus(domainId);
          const st = data.status as string;
          setAnalysisStatus(st);
          setTotalKeywords(data.total_keywords || 0);
          setUniqueDomains(data.unique_domains || 0);
          if (st === "COMP") {
            clearInterval(pollRef.current!);
            setCandidates(data.candidates || []);
            setTrackedCount(data.tracked_count || 0);
            toast({ title: "Competitor AI analysis completed!" });
            // Show "View Analysis" button (like RankMax WAIT state)
            setWaitReady(true);
          } else if (st === "FAIL") {
            clearInterval(pollRef.current!);
            toast({ title: "Analysis failed", description: "Please try again.", variant: "destructive" });
            setView("init");
          }
        } catch { /* keep polling */ }
      }, 3000);
    } else if (pollRef.current) {
      clearInterval(pollRef.current);
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [view, domainId]);

  /* ── Handlers ───────────────────────────────────────────────────────────── */
  const handleStartAnalysis = async () => {
    if (!domainId) return;
    setView("analyzing"); setAnalysisStatus("SCHD"); setWaitReady(false);
    try { await apiClient.startSeoCompetitorAnalysis(domainId); }
    catch (e: any) {
      // Show what the server said. The generic "Could not start analysis" hid
      // the one failure the user can actually act on — no tracked keywords, so
      // there is nothing to find competitors in.
      const msg = e?.message || "Could not start analysis.";
      toast({
        title: /keyword/i.test(msg) ? "No keywords to analyse" : "Error",
        description: msg,
        variant: "destructive",
      });
      setView("init");
    }
  };

  const handleViewAnalysis = async () => {
    await loadProjects();
    setView("selecting");
  };

  const handleAddCompetitor = async (domain: string) => {
    if (!domainId || trackedCount >= 30) return;
    setAdding(domain);
    try {
      await apiClient.addSeoCompetitor(domainId, domain);
      setCandidates(prev => prev.map(c => c.domain === domain ? { ...c, tracked: true } : c));
      setTrackedCount(prev => prev + 1);
      await loadProjects();
    } catch (e: any) {
      toast({ title: "Error", description: e?.message || "Could not add.", variant: "destructive" });
    } finally { setAdding(null); }
  };

  const handleRemoveCandidate = async (domain: string) => {
    // Find the project for this domain and delete it
    const proj = projects.find(p => p.competitor_domain === domain);
    if (proj) {
      try {
        await apiClient.deleteSeoCompetitor(proj.id);
        setProjects(prev => prev.filter(p => p.id !== proj.id));
        setCandidates(prev => prev.map(c => c.domain === domain ? { ...c, tracked: false } : c));
        setTrackedCount(prev => Math.max(0, prev - 1));
      } catch {
        toast({ title: "Error", description: "Could not remove.", variant: "destructive" });
      }
    }
  };

  const handleRemoveCompetitor = async (project: CompProject) => {
    setDeletingId(project.id);
    try {
      await apiClient.deleteSeoCompetitor(project.id);
      setProjects(prev => prev.filter(p => p.id !== project.id));
      setCandidates(prev => prev.map(c => c.domain === project.competitor_domain ? { ...c, tracked: false } : c));
      setTrackedCount(prev => Math.max(0, prev - 1));
    } catch {
      toast({ title: "Error", description: "Could not remove competitor.", variant: "destructive" });
    } finally { setDeletingId(null); }
  };

  const handleFinish = () => {
    if (projects.length === 0) {
      toast({ title: "Please select at least one competitor" }); return;
    }
    setFinishing(true);
    setTimeout(() => { setView("direct"); setFinishing(false); }, 300);
  };

  const handleViewKeywords = async (project: CompProject) => {
    setSelectedProject(project); setKeywords([]); setKwSearch(""); setView("keywords");
    try {
      const data = await apiClient.getSeoCompetitorKeywords(project.id);
      setKeywords(data.keywords || []);
    } catch {
      toast({ title: "Error", description: "Could not load keywords.", variant: "destructive" });
    }
  };

  const handleAddManual = async () => {
    const raw = manualDomain.trim();
    if (!domainId || !raw || manualBusy) return;
    // Normalize "https://www.competitor.com/x" -> "competitor.com" (backend re-normalizes too).
    const dom = raw.replace(/^https?:\/\//i, "").replace(/^www\./i, "").split("/")[0].trim().toLowerCase();
    if (!dom || !dom.includes(".")) {
      toast({ title: "Invalid domain", description: "Enter a valid domain like competitor.com", variant: "destructive" });
      return;
    }
    if (trackedCount >= 30) {
      toast({ title: "Limit reached", description: "You can add up to 30 competitors per project.", variant: "destructive" });
      return;
    }
    if (projects.some(p => p.competitor_domain === dom)) {
      toast({ title: "Already added", description: `${dom} is already a competitor.` });
      return;
    }
    setManualBusy(true);
    try {
      await apiClient.addSeoCompetitor(domainId, dom);
      await loadProjects();
      setTrackedCount(prev => prev + 1);
      setCandidates(prev => prev.map(c => c.domain === dom ? { ...c, tracked: true } : c));
      toast({ title: "Competitor added", description: dom });
      setManualDomain("");
      setManualOpen(false);
    } catch (e: any) {
      toast({ title: "Error", description: e?.message || "Could not add competitor.", variant: "destructive" });
    } finally {
      setManualBusy(false);
    }
  };

  /* ── Filtered lists ─────────────────────────────────────────────────────── */
  const filteredCandidates = candidates.filter(c =>
    !compSearch || c.domain.toLowerCase().includes(compSearch.toLowerCase())
  );
  const filteredKws = keywords.filter(k =>
    !kwSearch || k.keyword.toLowerCase().includes(kwSearch.toLowerCase())
  );

  /* ── Sorting ────────────────────────────────────────────────────────────── */
  const handleSort = (key: CompSortKey) => {
    if (sortKey === key) {
      // Third click clears the sort and restores the API's ordering.
      if (sortDir === "asc") setSortDir("desc");
      else { setSortKey(null); setSortDir("asc"); }
    } else {
      setSortKey(key);
      setSortDir(COMP_ASCENDING_FIRST.includes(key) ? "asc" : "desc");
    }
  };

  const sortedKws = (() => {
    if (!sortKey) return filteredKws;

    // A rank of 0 means "not ranking", not "rank zero" — it has to sort as
    // absent, otherwise every keyword nobody ranks for floods the top of an
    // ascending sort and buries the actual positions.
    const valueOf = (kw: CompKeyword): number | string | null => {
      switch (sortKey) {
        case "keyword": return kw.keyword || "";
        case "their_rank": return kw.their_rank > 0 ? kw.their_rank : null;
        case "our_rank": return kw.our_rank > 0 ? kw.our_rank : null;
        case "best_rank": return kw.best_rank > 0 ? kw.best_rank : null;
        case "volume": return kw.search_volume != null && kw.search_volume > 0 ? kw.search_volume : null;
        case "date": return kw.last_ranked_date ? new Date(kw.last_ranked_date).getTime() : null;
        default: return null;
      }
    };

    return [...filteredKws].sort((a, b) => {
      const av = valueOf(a);
      const bv = valueOf(b);
      // Missing values stay at the bottom in both directions.
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      if (typeof av === "string" || typeof bv === "string") {
        const cmp = String(av).localeCompare(String(bv));
        return sortDir === "asc" ? cmp : -cmp;
      }
      return sortDir === "asc" ? Number(av) - Number(bv) : Number(bv) - Number(av);
    });
  })();

  /* ── Pagination ─────────────────────────────────────────────────────────── */
  const totalKwPages = Math.max(1, Math.ceil(sortedKws.length / kwPerPage));
  const pagedKws = sortedKws.slice((currentPage - 1) * kwPerPage, currentPage * kwPerPage);

  // Searching, sorting or resizing the page can leave you on a page that no
  // longer exists — snap back to the first one.
  useEffect(() => { setCurrentPage(1); }, [kwSearch, sortKey, sortDir, kwPerPage, selectedProject?.id]);

  const SortableCompHead = ({ label, sortId, className }: {
    label: string; sortId: CompSortKey; className?: string;
  }) => (
    <TableHead className={className}>
      <button
        type="button"
        onClick={() => handleSort(sortId)}
        className="inline-flex items-center gap-1 hover:text-foreground transition-colors"
        aria-label={`Sort by ${label}`}
      >
        {label}
        {sortKey === sortId ? (
          sortDir === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
        ) : (
          <ArrowUpDown className="h-3 w-3 opacity-40" />
        )}
      </button>
    </TableHead>
  );

  /* ── Shared header (like RankMax competitor_header.js) ───────────────────── */
  /* Matches every other SEO page: a text-4xl title over a muted line of
     description, actions on the right. The favicon tile and the domain name
     that used to sit here are already carried by the project switcher in the
     sidebar, so repeating them made this the only page in the section with a
     different masthead. */
  const Header = ({ title, subtitle, extra }: { title?: string; subtitle?: string; extra?: React.ReactNode }) => (
    <div className="flex items-start justify-between gap-4 flex-wrap">
      <div>
        <h1 className="text-4xl font-bold tracking-tight">{title || "Competitors"}</h1>
        <p className="text-muted-foreground mt-2">
          {subtitle || "Domains ranking alongside you for the keywords you track"}
        </p>
      </div>
      {extra && <div className="flex items-center gap-2.5 flex-wrap">{extra}</div>}
    </div>
  );

  /* ── Manual add dialog (shared across selecting + direct views) ──────────── */
  const manualDialog = (
    <Dialog open={manualOpen} onOpenChange={(o) => { if (!manualBusy) setManualOpen(o); }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add competitor manually</DialogTitle>
          <DialogDescription>
            Enter a competitor's domain to track it alongside auto-discovered competitors.
            Keyword comparison fills in on the next analysis / reanalysis.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2 py-2">
          <Label htmlFor="manual-comp-domain">Competitor domain</Label>
          <Input
            id="manual-comp-domain"
            placeholder="competitor.com"
            value={manualDomain}
            onChange={(e) => setManualDomain(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleAddManual(); }}
            autoFocus
          />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setManualOpen(false)} disabled={manualBusy}>
            Cancel
          </Button>
          <Button className="gradient-primary" onClick={handleAddManual} disabled={manualBusy || !manualDomain.trim()}>
            {manualBusy ? "Adding..." : "Add competitor"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );

  /* ═══════════════════════════════════════════════════════════════════════════
     PAGE LOADER — shown while initial loadStatus is in progress
     ═══════════════════════════════════════════════════════════════════════════ */
  if (pageLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-32">
        <Loader2 className="h-10 w-10 animate-spin text-primary mb-4" />
        <span className="text-muted-foreground text-sm">Loading competitors...</span>
      </div>
    );
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     SHARED VIEW: INIT + ANALYZING (matches RankMax single-page layout)
     RankMax keeps robot + cards + button on ONE page, button text changes.
     VOID/INIT: Robot + "Start Analysis"
     LOAD/SCHD: Robot + progress cards + spinner button
     WAIT/COMP: Robot + progress cards + "View Analysis"
     FAIL: Robot + "Reanalysis"
     ═══════════════════════════════════════════════════════════════════════════ */
  if (view === "init" || view === "analyzing") {
    const isRunning = view === "analyzing" && !waitReady;
    const isReady = waitReady;
    const showSteps = view === "analyzing";

    /* The RankMax robot animation and its four floating pastel cards are gone.
       They were the only illustration of their kind in the app, used fixed hex
       colours that ignored the theme, and positioned the cards with hand-tuned
       pixel margins. This is the same dashed-card empty state the Topics page
       uses for its "Start Analysing" flow. */
    const steps = [
      "Analysing your keywords",
      "Finding the competitors",
      "Filtering the competitors",
      "Collecting information",
    ];

    const heading = isReady
      ? "Analysis complete"
      : isRunning
      ? "Finding your competitors..."
      : analysisStatus === "FAIL"
      ? "Analysis failed"
      : "No competitor analysis yet";

    const blurb = isReady
      ? `${totalKeywords} keywords matched across ${uniqueDomains} domains. Open the list to choose which competitors to track.`
      : isRunning
      ? "We're scanning the search results for every keyword you track to find the domains ranking alongside you. This runs in the background — you can leave this page and come back."
      : analysisStatus === "FAIL"
      ? "The last run didn't finish. Starting it again will pick up from your current keyword list."
      : "Competitor AI scans the search results for the keywords you track and finds the domains ranking alongside you. Start the analysis to discover them for this domain.";

    return (
      <div className="p-8 space-y-8 bg-background animate-fade-in">
        <Header />

        <Card className="p-6 border-dashed border-primary/40 bg-card/70">
          <div className="flex flex-col md:flex-row gap-4 items-start">
            <div className="p-3 rounded-full bg-primary/10 text-primary shrink-0">
              {isRunning
                ? <Loader2 className="h-6 w-6 animate-spin" />
                : <Users className="h-6 w-6" />}
            </div>
            <div className="flex-1 space-y-2 min-w-0">
              <h3 className="text-lg font-semibold">{heading}</h3>
              <p className="text-sm text-muted-foreground">{blurb}</p>

              {/* Progress steps, shown only while a run is in flight. Each bar
                  fills over 10s in sequence — the same pacing as before, now in
                  theme colours instead of #f2e9ff / rgb(137,89,207). */}
              {showSteps && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 pt-3 max-w-2xl">
                  {steps.map((label, i) => (
                    <div key={label} className="space-y-1.5">
                      <p className="text-xs font-medium text-muted-foreground">{label}</p>
                      <div className="w-full rounded-full overflow-hidden bg-muted" style={{ height: 4 }}>
                        <div
                          className="rounded-full bg-primary h-full"
                          style={isRunning
                            ? { width: 0, animation: "comp-pb 10s linear forwards", animationDelay: `${i * 10}s` }
                            : { width: "100%" }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {showSteps && totalKeywords > 0 && (
                <p className="text-sm text-muted-foreground pt-1">
                  <span className="text-primary font-semibold">{totalKeywords}</span> keywords matched and{" "}
                  <span className="text-primary font-semibold">{uniqueDomains}</span> domains tracked
                </p>
              )}

              <div className="flex flex-wrap gap-3 pt-2">
                {isRunning ? (
                  <Button disabled className="gradient-primary shadow-md shadow-primary/20 text-primary-foreground">
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Analysing...
                  </Button>
                ) : isReady ? (
                  <Button onClick={handleViewAnalysis}
                    className="gradient-primary shadow-md shadow-primary/20 text-primary-foreground">
                    <Users className="h-4 w-4 mr-2" />
                    View Competitors
                  </Button>
                ) : (
                  <Button onClick={handleStartAnalysis} disabled={!domainId}
                    className="gradient-primary shadow-md shadow-primary/20 text-primary-foreground">
                    <Sparkles className="h-4 w-4 mr-2" />
                    {analysisStatus === "FAIL" ? "Retry Analysis" : "Start Analysis"}
                  </Button>
                )}
                {projects.length > 0 && !isRunning && (
                  <Button variant="outline" onClick={() => setView("direct")}>
                    View tracked competitors
                  </Button>
                )}
              </div>
            </div>
          </div>
        </Card>
      </div>
    );
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     VIEW: SELECTING — All Competitors (like RankMax top_competitors.js)
     3-column grid, favicon + name + domain + matching keyword + Add button
     Fixed footer with "Finish (X/6)"
     ═══════════════════════════════════════════════════════════════════════════ */
  if (view === "selecting") {
    return (
      <div className="bg-background animate-fade-in">
        <div className="p-8 pb-32">
          <Header />

          {/* Subheader: All Competitors + Search */}
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mt-6 mb-5">
            <div>
              <h2 className="text-lg font-bold">All Competitors</h2>
              <p className="text-sm text-muted-foreground mt-1 leading-relaxed">
                NOTE: The list displays top competitors from {candidates.length} results.
              </p>
            </div>
            <div className="flex items-center gap-2 w-full sm:w-auto flex-shrink-0">
              <div className="relative w-full sm:w-72">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input placeholder={`Search among ${candidates.length} competitors`}
                  value={compSearch} onChange={e => setCompSearch(e.target.value)} className="pl-9 h-9 text-sm" />
              </div>
              <Button size="sm" variant="outline" className="gap-1.5 h-9 flex-shrink-0"
                disabled={trackedCount >= 30}
                onClick={() => setManualOpen(true)}>
                <Plus className="w-4 h-4" /> Add manually
              </Button>
            </div>
          </div>

          {/* Competitor grid — 3 columns like RankMax */}
          {filteredCandidates.length === 0 ? (
            <div className="flex items-center justify-center h-[50vh]">
              <div className="text-center">
                <p className="text-muted-foreground">No matches found within {candidates.length} competitors!</p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {filteredCandidates.map(c => (
                <Card key={c.domain}
                  className={`p-4 flex items-center gap-3 transition-all hover:border-primary/40
                    ${c.tracked ? "bg-primary/5 border-primary/30" : "border-border"}`}>
                  {/* Favicon */}
                  <div className="w-9 h-9 rounded border border-border bg-muted flex items-center justify-center flex-shrink-0 overflow-hidden p-0.5">
                    <img src={favUrl(c.domain)} alt="" className="w-7 h-7 rounded object-contain"
                      onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
                  </div>
                  {/* Info */}
                  <div className="flex-1 min-w-0 mr-2">
                    <p className="font-semibold text-sm text-primary truncate leading-tight">
                      {projectName(c.domain)}
                    </p>
                    <a href={`http://${c.domain}`} target="_blank" rel="noopener noreferrer"
                      className="flex items-center gap-1 text-xs text-muted-foreground hover:text-primary mt-0.5 truncate">
                      {c.domain}
                      <ExternalLink className="w-2.5 h-2.5 flex-shrink-0" />
                    </a>
                    <p className="text-xs text-muted-foreground mt-2">Matching keyword</p>
                    <p className="text-sm font-bold leading-tight">{c.count}/{totalKeywords}</p>
                  </div>
                  {/* Action */}
                  <div className="flex-shrink-0">
                    {c.tracked ? (
                      <button onClick={() => handleRemoveCandidate(c.domain)}
                        className="text-xs font-medium text-destructive bg-destructive/10 hover:bg-destructive/20 rounded px-2.5 py-1.5 transition-colors flex items-center gap-1">
                        <X className="w-3 h-3" />
                      </button>
                    ) : (
                      <Button size="sm" className="gradient-primary h-8 px-4 text-xs font-semibold"
                        disabled={trackedCount >= 30 || adding === c.domain}
                        onClick={() => handleAddCompetitor(c.domain)}>
                        {adding === c.domain ? "..." : "Add"}
                      </Button>
                    )}
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* Fixed footer — respects sidebar width, sits below chat button z-index */}
        <div
          className="fixed bottom-0 right-0 bg-background border-t border-border px-6 sm:px-8 py-4 flex items-center justify-between z-40 transition-all duration-150"
          style={{ left: sidebarOpen ? 256 : 64 }}>
          <span className="text-sm text-muted-foreground">
            You can add not more than 30 competitors per project.
          </span>
          <div className="flex items-center gap-3 mr-16">
            {projects.length > 0 && (
              <Button variant="outline" size="sm" onClick={() => setView("direct")} className="px-4">
                Skip
              </Button>
            )}
            <Button
              className={trackedCount > 0 ? "gradient-primary px-5" : "px-5"}
              variant={trackedCount > 0 ? "default" : "outline"}
              onClick={handleFinish}
              disabled={finishing}>
              <span className="mr-1.5">Finish</span>({trackedCount}/30)
            </Button>
          </div>
        </div>
        {manualDialog}
      </div>
    );
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     VIEW: DIRECT COMPETITORS — project cards (like RankMax OVER state)
     ═══════════════════════════════════════════════════════════════════════════ */
  if (view === "direct") {
    return (
      <div className="p-8 space-y-8 bg-background animate-fade-in">
        <Header
          title="Direct Competitors"
          subtitle="Competitors confirmed for this project, and how many of your keywords each one also ranks for"
          extra={
            <>
              <Button variant="outline" size="sm" className="gap-1.5 text-xs"
                onClick={handleStartAnalysis}>
                <RefreshCw className="w-3.5 h-3.5" /> Reanalysis
              </Button>
              <Button variant="outline" size="sm" className="gap-1.5"
                disabled={projects.length >= 30}
                onClick={() => setManualOpen(true)}>
                <Plus className="w-4 h-4" /> Add manually
              </Button>
              <Button size="sm" className="gradient-primary gap-1.5"
                onClick={() => { if (analysisStatus === "COMP") setView("selecting"); else handleStartAnalysis(); }}>
                <Plus className="w-4 h-4" /> Add Competitor
              </Button>
            </>
          }
        />

        {/* Project cards use single-width border-border like every other card
            in the app. They were border-2 border-primary/20 — a double-weight
            purple outline used nowhere else. */}
        {projects.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-[50vh] gap-4">
            <p className="text-muted-foreground">No competitor project found</p>
            <p className="text-sm text-muted-foreground">Looks like you haven't added a project yet.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map(p => (
              <Card key={p.id} className="border-border p-4 hover:border-primary/40 hover:shadow-md transition-all">
                <div className="flex items-start gap-3">
                  {/* Favicon */}
                  <div className="w-10 h-10 rounded border border-border bg-muted flex items-center justify-center flex-shrink-0 overflow-hidden p-0.5">
                    <img src={favUrl(p.competitor_domain)} alt="" className="w-7 h-7 rounded object-contain"
                      onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
                  </div>
                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    {/* block, not the default inline-block — as an inline box
                        it sat on a text baseline and the line-height added
                        descender space under it, which is what separated the
                        name from the domain rather than the anchor's mt-0.5. */}
                    <button
                      onClick={() => handleViewKeywords(p)}
                      className="block w-full text-left hover:underline"
                    >
                      <p className="font-semibold text-sm text-primary truncate leading-tight">
                        {projectName(p.competitor_domain)}
                      </p>
                    </button>
                    <a href={`https://${p.competitor_domain}`} target="_blank" rel="noopener noreferrer"
                      className="flex items-center gap-1 text-xs text-muted-foreground hover:text-primary mt-0.5 truncate max-w-[180px]">
                      {p.competitor_domain}
                      <ExternalLink className="w-2.5 h-2.5 flex-shrink-0" />
                    </a>
                    <p className="text-xs text-muted-foreground mt-3">Matching keyword</p>
                    <p className="text-sm font-bold leading-tight">{p.ranked_them}/{p.keyword_count}</p>
                  </div>
                  {/* 3-dot menu */}
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-7 w-7 flex-shrink-0">
                        <MoreVertical className="w-4 h-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem className="text-destructive focus:text-destructive"
                        disabled={deletingId === p.id}
                        onClick={() => handleRemoveCompetitor(p)}>
                        <Trash2 className="w-3.5 h-3.5 mr-2" />Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>

                {/* View Keywords link — at bottom */}
                <div className="flex items-center justify-between mt-4 pt-3 border-t border-border">
                  <span className="text-xs text-muted-foreground">
                    {p.created_at ? `Last Updated: ${new Date(p.created_at).toLocaleDateString()}` : ""}
                  </span>
                  <button
                    onClick={() => handleViewKeywords(p)}
                    className="flex items-center gap-1 text-sm font-semibold text-primary hover:underline">
                    View Keywords
                    <span className="w-5 h-5 rounded-full bg-primary/10 flex items-center justify-center">
                      <ChevronRight className="w-3.5 h-3.5" />
                    </span>
                  </button>
                </div>
              </Card>
            ))}
          </div>
        )}
        {manualDialog}
      </div>
    );
  }

  /* ═══════════════════════════════════════════════════════════════════════════
     VIEW: KEYWORDS — comparison table
     ═══════════════════════════════════════════════════════════════════════════ */
  if (view === "keywords" && selectedProject) {
    const serpLabel = (kw: CompKeyword) => {
      const parts: string[] = [];
      if (kw.featured_snippet) parts.push("FS");
      if (kw.knowledge_panel) parts.push("KP");
      if (kw.ads) parts.push("Ads");
      return parts.length > 0 ? parts.join(", ") : "NA";
    };

    const formatDate = (d: string | null) => {
      if (!d) return "-";
      const dt = new Date(d);
      return dt.toLocaleDateString("en-US", { month: "short", day: "2-digit", year: "numeric" });
    };

    const timeAgo = (d: string | null) => {
      if (!d) return "";
      const diff = Date.now() - new Date(d).getTime();
      const hrs = Math.floor(diff / 3600000);
      if (hrs < 1) return "Just now";
      if (hrs < 24) return `${hrs} hours ago`;
      const days = Math.floor(hrs / 24);
      return `${days} day${days > 1 ? "s" : ""} ago`;
    };

    return (
      <div className="p-8 space-y-8 bg-background animate-fade-in">
        {/* Detail-view header, same as SeoOpportunityDetail and SeoKeywordDetail:
            icon-only back button inline to the left of the title, rule under the
            row. This is a view within Competitors, not a top-level page, so it
            deliberately does not use the text-4xl masthead. */}
        <div className="flex items-center justify-between pb-4 border-b border-border/50 flex-wrap gap-3">
          <div className="flex items-center gap-4 min-w-0">
            <Button variant="outline" size="icon" className="border-border/50 flex-shrink-0"
              onClick={() => setView("direct")}>
              <ChevronLeft className="w-4 h-4" />
            </Button>
            {/* The matchup is what this view is about; "Competitors Analysis"
                is the section it lives in, so it reads as the subtitle. */}
            <div>
              <h1 className="text-2xl font-bold tracking-tight">
                {selectedDomain?.name || "Your site"} <span className="text-primary">vs</span> {projectName(selectedProject.competitor_domain)}
              </h1>
              {/* The actual hostnames, so it is unambiguous which properties
                  are being compared — brand names alone can be shared across
                  several domains. */}
              <p className="text-sm text-muted-foreground mt-0.5">
                {bareDomain(selectedDomain?.url) || "your site"} vs {bareDomain(selectedProject.competitor_domain)}
              </p>
            </div>
          </div>
          {/* "Add Competitor" removed — this view is a head-to-head against one
              competitor, not a place to manage the list. Adding is still on the
              Direct Competitors screen behind the back arrow. */}
        </div>

        {/* Total keywords + Search */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <h3 className="text-base font-bold">Total keywords ({filteredKws.length})</h3>
          <div className="relative w-full sm:w-64 flex-shrink-0">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input placeholder="Search" value={kwSearch}
              onChange={e => setKwSearch(e.target.value)} className="pl-9 h-9" />
          </div>
        </div>

        {/* Table — all RankMax columns */}
        {/* Same shell, header treatment and row rhythm as the primary keyword
            table on /seo-rankings: shadcn Table, uppercase py-2 heads on
            bg-muted/30, py-3 body cells, hover instead of zebra striping. */}
        <Card className="shadow-elegant border border-border backdrop-blur-sm bg-card/80">
          <CardContent className="p-0 overflow-x-auto">
            {/* table-fixed makes the column widths below authoritative. Under
                the default auto layout a cell's max-width is only a hint, and
                `truncate` sets white-space: nowrap — so the browser widened the
                keyword column to fit the longest URL instead of clipping it,
                which is what starved the rank columns. */}
            <Table className="table-fixed">
              <TableHeader>
                {/* Competitor first, then your rank and your best beside it.
                    BEST is YOUR best-ever position — views.py reads it from
                    your own SeoKeywordRank.top_rank, not the competitor's — so
                    it is labelled MY BEST and grouped with MY RANK. */}
                {/* KEYWORD is pinned to a fixed width so it stops absorbing all
                    the slack — with no width it stretched and squeezed the rank
                    columns until "MY BEST" wrapped onto two lines. Every other
                    head is nowrap so a label can never break mid-column. */}
                <TableRow className="bg-muted/30 hover:bg-muted/30">
                  <SortableCompHead label="KEYWORD" sortId="keyword" className="text-xs font-semibold py-2 w-[340px]" />
                  <SortableCompHead label="COMPETITOR RANK" sortId="their_rank" className="text-center text-xs font-semibold py-2 w-36 whitespace-nowrap [&>button]:mx-auto" />
                  <SortableCompHead label="MY RANK" sortId="our_rank" className="text-center text-xs font-semibold py-2 w-24 whitespace-nowrap [&>button]:mx-auto" />
                  <SortableCompHead label="MY BEST" sortId="best_rank" className="text-center text-xs font-semibold py-2 w-24 whitespace-nowrap [&>button]:mx-auto" />
                  {/* SERP is not sortable: featured_snippet / knowledge_panel /
                      ads are False on every keyword in the system, so the column
                      reads "NA" throughout and sorting it does nothing. */}
                  <TableHead className="text-center text-xs font-semibold py-2 w-16 whitespace-nowrap">SERP</TableHead>
                  <SortableCompHead label="VOLUME" sortId="volume" className="text-center text-xs font-semibold py-2 w-20 whitespace-nowrap [&>button]:mx-auto" />
                  <SortableCompHead label="DATE" sortId="date" className="text-right text-xs font-semibold py-2 w-32 whitespace-nowrap [&>button]:ml-auto" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {keywords.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-16 text-muted-foreground">
                      Loading keywords...
                    </TableCell>
                  </TableRow>
                )}
                {pagedKws.map((kw) => (
                  <TableRow key={kw.id} className="hover:bg-muted/30">
                    <TableCell className="py-3 w-[340px] max-w-[340px]">
                      <div className="min-w-0">
                        <p className="font-medium text-sm truncate">{kw.keyword}</p>
                        {/* The competitor's ranking page — the useful URL in a
                            head-to-head view. This showed our_url, which is
                            blank on every keyword we don't currently rank for,
                            so the column was a column of em-dashes. */}
                        {kw.their_url ? (
                          <a href={kw.their_url} target="_blank" rel="noopener noreferrer"
                            title={kw.their_url}
                            className="text-xs text-muted-foreground flex items-center gap-1 min-w-0 hover:text-primary hover:underline">
                            {/* truncate needs its own element — the anchor is a
                                flex container, so text-overflow would not apply
                                to its anonymous text child. */}
                            <span className="truncate">{kw.their_url}</span>
                            <ExternalLink className="w-2.5 h-2.5 flex-shrink-0" />
                          </a>
                        ) : (
                          <p className="text-xs text-muted-foreground">—</p>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-center py-3"><RankCell rank={kw.their_rank} /></TableCell>
                    <TableCell className="text-center py-3"><RankCell rank={kw.our_rank} /></TableCell>
                    <TableCell className="text-center py-3"><RankCell rank={kw.best_rank} /></TableCell>
                    <TableCell className="text-center py-3">
                      <span className={`text-sm ${serpLabel(kw) !== "NA" ? "font-semibold text-primary" : "text-muted-foreground"}`}>
                        {serpLabel(kw)}
                      </span>
                    </TableCell>
                    <TableCell className="text-center py-3">
                      {kw.search_volume != null && kw.search_volume > 0 ? (
                        <span className="text-sm">{kw.search_volume.toLocaleString()}</span>
                      ) : (
                        <span className="text-muted-foreground text-sm">-</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right py-3">
                      <div className="text-xs font-medium">{formatDate(kw.last_ranked_date)}</div>
                      <div className="text-[10px] text-muted-foreground">{timeAgo(kw.last_ranked_date)}</div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            {/* Same footer as the primary keyword table. The page-size select
                only appears once there are more rows than the smallest option,
                since below that every choice shows the same rows. */}
            {sortedKws.length > 0 && (
              <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-t border-border">
                <p className="text-sm text-muted-foreground">
                  Showing {(currentPage - 1) * kwPerPage + 1}-{Math.min(currentPage * kwPerPage, sortedKws.length)} of {sortedKws.length} keywords
                </p>
                <div className="flex items-center gap-2">
                  {sortedKws.length > KW_PAGE_SIZE_OPTIONS[0] && (
                    <Select value={String(kwPerPage)} onValueChange={(v) => setKwPerPage(Number(v))}>
                      <SelectTrigger className="h-8 w-[120px] text-sm">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {KW_PAGE_SIZE_OPTIONS.map((size) => (
                          <SelectItem key={size} value={String(size)}>{size} per page</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                  <div className="flex items-center gap-1">
                    <Button variant="outline" size="sm" onClick={() => setCurrentPage(1)} disabled={currentPage === 1}>
                      First
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1}>
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    {Array.from({ length: totalKwPages }, (_, i) => i + 1)
                      .filter(page => page === 1 || page === totalKwPages || Math.abs(page - currentPage) <= 2)
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
                    <Button variant="outline" size="sm" onClick={() => setCurrentPage(p => Math.min(totalKwPages, p + 1))} disabled={currentPage === totalKwPages}>
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => setCurrentPage(totalKwPages)} disabled={currentPage === totalKwPages}>
                      Last
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    );
  }

  return null;
};

export default SeoCompetitors;
