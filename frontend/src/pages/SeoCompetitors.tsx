import { useState, useEffect, useRef, useCallback } from "react";
import { ExternalLink, Plus, Trash2, ChevronLeft, Search, ChevronRight, RefreshCw, MoreVertical, X, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import Lottie from "lottie-react";
import CompLottie from "@/assets/animations/compLottie.json";

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

/* ─── Rank badge ──────────────────────────────────────────────────────────── */
function RankBadge({ rank }: { rank: number }) {
  if (!rank || rank === 0)
    return <span className="text-muted-foreground text-sm">-</span>;
  const color =
    rank <= 3 ? "bg-emerald-500/10 text-emerald-600 border-emerald-300/40" :
    rank <= 10 ? "bg-blue-500/10 text-blue-600 border-blue-300/40" :
    rank <= 50 ? "bg-yellow-500/10 text-yellow-600 border-yellow-300/40" :
    "bg-muted text-muted-foreground border-border";
  return (
    <span className={`inline-flex items-center justify-center min-w-[2.5rem] h-7 rounded text-xs font-bold border ${color}`}>
      {rank}
    </span>
  );
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
    catch { toast({ title: "Error", description: "Could not start analysis.", variant: "destructive" }); setView("init"); }
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

  /* ── Shared header (like RankMax competitor_header.js) ───────────────────── */
  const Header = ({ title, subtitle, extra }: { title?: string; subtitle?: string; extra?: React.ReactNode }) => (
    <div className="flex items-center justify-between flex-wrap gap-3">
      <div className="flex items-center gap-3">
        <div className="w-12 h-12 rounded-lg border border-border bg-white flex items-center justify-center flex-shrink-0 overflow-hidden p-1">
          {selectedDomain?.url ? (
            <img src={favUrl(selectedDomain.url)} alt="" className="w-8 h-8 object-contain rounded"
              onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
          ) : (
            <span className="text-xs font-bold text-muted-foreground">
              {selectedDomain?.name?.slice(0, 2).toUpperCase() ?? "—"}
            </span>
          )}
        </div>
        <div>
          <h1 className="text-xl font-bold leading-tight">{title || "Competitors Analysis"}</h1>
          <p className="text-sm text-muted-foreground mt-0.5 leading-snug">
            {subtitle || selectedDomain?.name || ""}
          </p>
        </div>
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
    const showCards = view === "analyzing";

    const cardData = [
      { label: "Analyzing your keywords", bg: "#fffec4" },
      { label: "Finding the competitors", bg: "#ffc4e7" },
      { label: "Filtering the competitors", bg: "#c4fff9" },
      { label: "Collecting information", bg: "#ffd6c4" },
    ];

    /* Progress bar: each bar runs 10s, sequential (0s, 10s, 20s, 30s delays) */
    const ProgressBar = ({ index, active }: { index: number; active: boolean }) => (
      <div className="w-full rounded-full overflow-hidden" style={{ height: 6, background: "#f2e9ff", position: "relative", bottom: 4 }}>
        {active ? (
          <div className="rounded-full" style={{
            height: 6, background: "rgb(137, 89, 207)", width: 0,
            animation: "comp-pb 10s linear forwards",
            animationDelay: `${index * 10}s`,
          }} />
        ) : (
          <div className="rounded-full" style={{ height: 6, background: "rgb(137, 89, 207)", width: "100%" }} />
        )}
      </div>
    );

    /* Button: matches RankMax state machine exactly */
    const ActionButton = () => {
      if (isRunning) {
        return (
          <Button className="gradient-primary shadow-md shadow-primary/20 h-10 min-w-[140px]" disabled>
            <Loader2 className="w-4 h-4 animate-spin" />
          </Button>
        );
      }
      if (isReady) {
        return (
          <Button className="gradient-primary shadow-md shadow-primary/20 h-10 min-w-[140px]" onClick={handleViewAnalysis}>
            View Analysis
          </Button>
        );
      }
      if (analysisStatus === "FAIL") {
        return (
          <Button className="gradient-primary shadow-md shadow-primary/20 h-10 min-w-[140px]" onClick={handleStartAnalysis}>
            Reanalysis
          </Button>
        );
      }
      return (
        <Button className="gradient-primary shadow-md shadow-primary/20 h-10 min-w-[140px]"
          onClick={handleStartAnalysis} disabled={!domainId}>
          Start Analysis
        </Button>
      );
    };

    return (
      <div className="p-6 sm:p-8 bg-background animate-fade-in">
        <Header />
        <div className="flex flex-col items-center justify-center pt-4">

          {/* Cards + Robot layout (cards only visible during analysis) */}
          <div className="flex items-center justify-center w-full max-w-3xl">

            {/* Left cards */}
            {showCards && (
              <div className="hidden md:flex flex-col flex-shrink-0" style={{ width: 176 }}>
                <div style={{ marginBottom: 100 }}>
                  <div className="w-full flex items-center justify-center text-center rounded-md px-3 font-bold text-sm leading-7"
                    style={{ background: cardData[0].bg, color: "#34234f", height: 80 }}>
                    {cardData[0].label}
                  </div>
                  <ProgressBar index={0} active={isRunning} />
                </div>
                <div>
                  <div className="w-full flex items-center justify-center text-center rounded-md px-3 font-bold text-sm leading-7"
                    style={{ background: cardData[1].bg, color: "#34234f", height: 80 }}>
                    {cardData[1].label}
                  </div>
                  <ProgressBar index={1} active={isRunning} />
                </div>
              </div>
            )}

            {/* Robot center — Lottie animation (same as RankMax) */}
            <div className="flex-shrink-0 mx-2 sm:mx-6" style={{ width: showCards ? 220 : 280 }}>
              <Lottie animationData={CompLottie} loop />
            </div>

            {/* Right cards */}
            {showCards && (
              <div className="hidden md:flex flex-col flex-shrink-0" style={{ width: 176 }}>
                <div style={{ marginBottom: 100, marginTop: 30 }}>
                  <div className="w-full flex items-center justify-center text-center rounded-md px-3 font-bold text-sm leading-7"
                    style={{ background: cardData[2].bg, color: "#34234f", height: 80 }}>
                    {cardData[2].label}
                  </div>
                  <ProgressBar index={2} active={isRunning} />
                </div>
                <div style={{ marginLeft: -25 }}>
                  <div className="w-full flex items-center justify-center text-center rounded-md px-3 font-bold text-sm leading-7"
                    style={{ background: cardData[3].bg, color: "#34234f", height: 80 }}>
                    {cardData[3].label}
                  </div>
                  <ProgressBar index={3} active={isRunning} />
                </div>
              </div>
            )}
          </div>

          {/* Mobile: show cards in grid */}
          {showCards && (
            <div className="grid grid-cols-2 gap-3 w-full max-w-sm mt-4 md:hidden">
              {cardData.map((c, i) => (
                <div key={i}>
                  <div className="flex items-center justify-center text-center rounded-md px-2 font-bold text-xs leading-5"
                    style={{ background: c.bg, color: "#34234f", height: 60 }}>
                    {c.label}
                  </div>
                  <div className="w-full rounded-full overflow-hidden" style={{ height: 4, background: "#f2e9ff" }}>
                    <div className="rounded-full" style={{
                      height: 4, background: "rgb(137, 89, 207)", width: 0,
                      animation: isRunning ? "comp-pb 10s linear forwards" : "none",
                      animationDelay: `${i * 10}s`,
                      ...(isRunning ? {} : { width: "100%" }),
                    }} />
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Bottom: title + status text + button */}
          <div className="text-center mt-6 space-y-2">
            <h2 className="text-xl font-bold">Competitor AI</h2>
            <p className="text-sm text-muted-foreground max-w-md leading-relaxed">
              {showCards && totalKeywords > 0 ? (
                <><span className="text-primary font-semibold">{totalKeywords}</span>/{totalKeywords} keywords match identified and <span className="text-primary font-semibold">{uniqueDomains}</span> domains tracked</>
              ) : showCards ? (
                "Analyzing your keywords and finding competitors…"
              ) : (
                "Hey, this is PromptMaxxBot and I'm here to assist you with tracking your Competitors' SEO Progress."
              )}
            </p>
            <div className="pt-2 flex justify-center">
              <ActionButton />
            </div>
          </div>
        </div>
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
        <div className="p-6 sm:p-8 pb-32">
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
                <div key={c.domain}
                  className={`rounded-md border p-4 flex items-center gap-3 transition-all
                    ${c.tracked ? "bg-primary/5 border-primary/20" : "bg-card border-border"}`}>
                  {/* Favicon */}
                  <div className="w-9 h-9 rounded border border-border bg-white flex items-center justify-center flex-shrink-0 overflow-hidden p-0.5">
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
                        className="text-xs font-medium text-red-500 hover:text-red-600 bg-red-50 hover:bg-red-100 rounded px-2.5 py-1.5 transition-colors flex items-center gap-1">
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
                </div>
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
      <div className="p-6 sm:p-8 space-y-5 bg-background animate-fade-in">
        <Header
          title="Direct Competitors"
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

        {projects.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-[50vh] gap-4">
            <p className="text-muted-foreground">No competitor project found</p>
            <p className="text-sm text-muted-foreground">Looks like you haven't added a project yet.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map(p => (
              <div key={p.id} className="rounded-lg border-2 border-primary/20 bg-card p-4 hover:border-primary/40 hover:shadow-sm transition-all">
                <div className="flex items-start gap-3">
                  {/* Favicon */}
                  <div className="w-10 h-10 rounded border border-border bg-white flex items-center justify-center flex-shrink-0 overflow-hidden p-0.5">
                    <img src={favUrl(p.competitor_domain)} alt="" className="w-7 h-7 rounded object-contain"
                      onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
                  </div>
                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <button onClick={() => handleViewKeywords(p)} className="hover:underline">
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
              </div>
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
      <div className="p-6 sm:p-8 space-y-5 bg-background animate-fade-in">
        {/* Header — like RankMax: back arrow + "Competitors Analysis" + "Domain vs Competitor" */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" className="h-9 w-9 rounded-full border border-border flex-shrink-0"
              onClick={() => setView("direct")}>
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <div>
              <h1 className="text-xl font-bold leading-tight">Competitors Analysis</h1>
              <p className="text-sm text-muted-foreground mt-0.5">
                {selectedDomain?.name || "Your site"} <span className="text-primary font-semibold">vs</span> {projectName(selectedProject.competitor_domain)}
              </p>
            </div>
          </div>
          <Button size="sm" className="gradient-primary gap-1.5"
            onClick={() => { if (analysisStatus === "COMP") setView("selecting"); else handleStartAnalysis(); }}>
            <Plus className="w-4 h-4" /> Add Competitor
          </Button>
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
        <div className="rounded-lg border border-border overflow-x-auto">
          <table className="w-full text-sm min-w-[900px]">
            <thead>
              <tr className="border-b border-border bg-muted/30 text-xs uppercase tracking-wider">
                <th className="text-left px-4 py-3 font-semibold text-muted-foreground">Keyword</th>
                <th className="text-center px-3 py-3 font-semibold text-muted-foreground w-24">My Rank</th>
                <th className="text-center px-3 py-3 font-semibold text-muted-foreground w-32">Competitor Rank</th>
                <th className="text-center px-3 py-3 font-semibold text-muted-foreground w-20">Best</th>
                <th className="text-center px-3 py-3 font-semibold text-muted-foreground w-20">SERP</th>
                <th className="text-center px-3 py-3 font-semibold text-muted-foreground w-20">Volume</th>
                <th className="text-right px-4 py-3 font-semibold text-muted-foreground w-32">Date</th>
              </tr>
            </thead>
            <tbody>
              {keywords.length === 0 && (
                <tr><td colSpan={7} className="text-center py-12 text-muted-foreground">Loading keywords...</td></tr>
              )}
              {filteredKws.map((kw, i) => (
                <tr key={kw.id} className={`border-b border-border last:border-0 ${i % 2 ? "bg-muted/10" : ""}`}>
                  <td className="px-4 py-3">
                    <span className="font-medium">{kw.keyword}</span>
                    {kw.our_url && (
                      <a href={kw.our_url} target="_blank" rel="noopener noreferrer"
                        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-primary mt-0.5 truncate max-w-[280px]">
                        {new URL(kw.our_url).pathname}
                        <ExternalLink className="w-2.5 h-2.5 flex-shrink-0" />
                      </a>
                    )}
                  </td>
                  <td className="px-3 py-3 text-center"><RankBadge rank={kw.our_rank} /></td>
                  <td className="px-3 py-3 text-center">
                    <span className={kw.their_rank > 0 ? "inline-flex items-center justify-center min-w-[2.5rem] h-7 rounded text-xs font-bold bg-pink-50 text-pink-700 border border-pink-200" : ""}>
                      {kw.their_rank > 0 ? kw.their_rank : <span className="text-muted-foreground text-sm">-</span>}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-center">
                    {kw.best_rank > 0 ? (
                      <span className="text-xs font-bold">{kw.best_rank}</span>
                    ) : (
                      <span className="text-muted-foreground text-xs">-</span>
                    )}
                  </td>
                  <td className="px-3 py-3 text-center">
                    <span className={`text-xs ${serpLabel(kw) !== "NA" ? "font-semibold text-primary" : "text-muted-foreground"}`}>
                      {serpLabel(kw)}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-center">
                    {kw.search_volume != null && kw.search_volume > 0 ? (
                      <span className="text-xs font-semibold">{kw.search_volume.toLocaleString()}</span>
                    ) : (
                      <span className="text-muted-foreground text-xs">-</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="text-xs font-medium">{formatDate(kw.last_ranked_date)}</div>
                    <div className="text-[10px] text-muted-foreground">{timeAgo(kw.last_ranked_date)}</div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  return null;
};

export default SeoCompetitors;
