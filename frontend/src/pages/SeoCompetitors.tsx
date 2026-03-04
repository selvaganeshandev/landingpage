import { useState, useEffect, useRef, useCallback } from "react";
import { ExternalLink, Plus, Trash2, ChevronLeft, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { useDomainStore } from "@/stores/domainStore";
import { useToast } from "@/hooks/use-toast";
import apiClient from "@/services/api";

// ─── Illustrations ───────────────────────────────────────────────────────────

const RobotIllustration = () => (
  <svg viewBox="0 0 240 275" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-52 h-52 drop-shadow-xl">
    <circle cx="120" cy="8" r="7" fill="#a78bfa" />
    <rect x="117" y="13" width="6" height="20" rx="3" fill="#8b5cf6" />
    <circle cx="120" cy="108" r="82" fill="#7c3aed" />
    <circle cx="152" cy="62" r="11" fill="white" opacity="0.14" />
    <rect x="62" y="80" width="116" height="60" rx="18" fill="#1e1b4b" />
    <circle cx="93" cy="110" r="21" fill="white" />
    <circle cx="93" cy="110" r="10" fill="#1e1b4b" />
    <circle cx="88" cy="104" r="4" fill="white" opacity="0.8" />
    <circle cx="147" cy="110" r="21" fill="white" />
    <circle cx="147" cy="110" r="10" fill="#1e1b4b" />
    <circle cx="142" cy="104" r="4" fill="white" opacity="0.8" />
    <path d="M 93 145 Q 120 163 147 145" stroke="#f9a8d4" strokeWidth="4.5" fill="none" strokeLinecap="round" />
    <rect x="76" y="182" width="88" height="58" rx="20" fill="#6d28d9" />
    <rect x="26" y="192" width="54" height="42" rx="11" fill="#7c3aed" />
    <rect x="26" y="192" width="54" height="8" rx="6" fill="#8b5cf6" />
    <path d="M 80 202 Q 96 215 80 228" stroke="#5b21b6" strokeWidth="5" fill="none" strokeLinecap="round" />
  </svg>
);

// Animated card skeleton shown during analysis
const AnalyzingCard = ({ index }: { index: number }) => (
  <div
    className="rounded-xl border border-border bg-card p-5 space-y-3 animate-pulse"
    style={{ animationDelay: `${index * 0.15}s` }}
  >
    <div className="flex items-center gap-3">
      <div className="w-9 h-9 rounded-lg bg-muted" />
      <div className="flex-1 space-y-1.5">
        <div className="h-3 bg-muted rounded w-2/3" />
        <div className="h-2.5 bg-muted rounded w-1/2" />
      </div>
    </div>
    <div className="space-y-1.5">
      <div className="h-2 bg-muted rounded w-full" />
      <div className="h-2 bg-muted rounded w-3/4" />
    </div>
    <div className="flex gap-2">
      <div className="h-5 w-16 bg-muted rounded-full" />
      <div className="h-5 w-20 bg-muted rounded-full" />
    </div>
  </div>
);

// ─── Types ───────────────────────────────────────────────────────────────────

interface Candidate {
  domain: string;
  count: number;
  tracked: boolean;
}

interface CompProject {
  id: number;
  competitor_domain: string;
  keyword_count: number;
  ranked_us: number;
  ranked_them: number;
  created_at: string;
}

interface CompKeyword {
  id: number;
  keyword: string;
  our_rank: number;
  their_rank: number;
  our_url: string;
  their_url: string;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function RankBadge({ rank }: { rank: number }) {
  if (!rank || rank === 0) {
    return <span className="text-muted-foreground text-sm">–</span>;
  }
  const color =
    rank <= 3 ? "bg-emerald-500/10 text-emerald-600 border-emerald-300/40" :
    rank <= 10 ? "bg-blue-500/10 text-blue-600 border-blue-300/40" :
    rank <= 50 ? "bg-yellow-500/10 text-yellow-600 border-yellow-300/40" :
    "bg-muted text-muted-foreground border-border";
  return (
    <span className={`inline-flex items-center justify-center w-10 h-7 rounded text-xs font-bold border ${color}`}>
      {rank}
    </span>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

const SeoCompetitors = () => {
  const { selectedDomain } = useDomainStore();
  const { toast } = useToast();

  // View state: init | analyzing | selecting | direct | keywords
  const [view, setView] = useState<"init" | "analyzing" | "selecting" | "direct" | "keywords">("init");

  // Data
  const [analysisStatus, setAnalysisStatus] = useState<string>("INIT");
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [trackedCount, setTrackedCount] = useState(0);
  const [projects, setProjects] = useState<CompProject[]>([]);
  const [selectedProject, setSelectedProject] = useState<CompProject | null>(null);
  const [keywords, setKeywords] = useState<CompKeyword[]>([]);
  const [kwSearch, setKwSearch] = useState("");
  const [adding, setAdding] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const domainId = selectedDomain?.id;
  const faviconUrl = selectedDomain?.url
    ? `https://www.google.com/s2/favicons?domain=${selectedDomain.url}&sz=64`
    : null;

  // ── Load initial status on domain change ──────────────────────────────────
  const loadStatus = useCallback(async () => {
    if (!domainId) return;
    try {
      const data = await apiClient.getSeoCompetitorStatus(domainId);
      const st = data.status as string;
      setAnalysisStatus(st);

      if (st === "SCHD") {
        setView("analyzing");
      } else if (st === "COMP") {
        setCandidates(data.candidates || []);
        setTrackedCount(data.tracked_count || 0);
        // Also load projects
        await loadProjects();
        setView("selecting");
      } else if (st === "INIT") {
        // Check if there are existing projects (OVER state)
        await loadProjects();
      }
    } catch (_e) {
      // silently ignore
    }
  }, [domainId]);

  const loadProjects = useCallback(async () => {
    if (!domainId) return;
    try {
      const data = await apiClient.getSeoCompetitorProjects(domainId);
      const ps = data.projects || [];
      setProjects(ps);
      if (ps.length > 0 && analysisStatus !== "COMP") {
        setView("direct");
      }
    } catch (_e) {
      // silently ignore
    }
  }, [domainId, analysisStatus]);

  useEffect(() => {
    setView("init");
    setProjects([]);
    setCandidates([]);
    setAnalysisStatus("INIT");
    loadStatus();
  }, [domainId]);

  // ── Poll while analyzing ──────────────────────────────────────────────────
  useEffect(() => {
    if (view === "analyzing") {
      pollRef.current = setInterval(async () => {
        if (!domainId) return;
        try {
          const data = await apiClient.getSeoCompetitorStatus(domainId);
          const st = data.status as string;
          setAnalysisStatus(st);
          if (st === "COMP") {
            clearInterval(pollRef.current!);
            setCandidates(data.candidates || []);
            setTrackedCount(data.tracked_count || 0);
            await loadProjects();
            setView("selecting");
          } else if (st === "FAIL") {
            clearInterval(pollRef.current!);
            toast({ title: "Analysis failed", description: "Please try again.", variant: "destructive" });
            setView("init");
          }
        } catch (_e) {
          // keep polling
        }
      }, 3000);
    } else {
      if (pollRef.current) clearInterval(pollRef.current);
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [view, domainId]);

  // ── Handlers ─────────────────────────────────────────────────────────────

  const handleStartAnalysis = async () => {
    if (!domainId) return;
    setView("analyzing");
    setAnalysisStatus("SCHD");
    try {
      await apiClient.startSeoCompetitorAnalysis(domainId);
    } catch (_e) {
      toast({ title: "Error", description: "Could not start analysis.", variant: "destructive" });
      setView("init");
    }
  };

  const handleAddCompetitor = async (domain: string) => {
    if (!domainId || trackedCount >= 6) return;
    setAdding(domain);
    try {
      await apiClient.addSeoCompetitor(domainId, domain);
      setCandidates(prev =>
        prev.map(c => c.domain === domain ? { ...c, tracked: true } : c)
      );
      setTrackedCount(prev => prev + 1);
      await loadProjects();
      toast({ title: "Competitor added", description: domain });
    } catch (e: any) {
      toast({ title: "Error", description: e?.message || "Could not add competitor.", variant: "destructive" });
    } finally {
      setAdding(null);
    }
  };

  const handleDeleteCompetitor = async (project: CompProject) => {
    setDeletingId(project.id);
    try {
      await apiClient.deleteSeoCompetitor(project.id);
      setProjects(prev => prev.filter(p => p.id !== project.id));
      toast({ title: "Competitor removed", description: project.competitor_domain });
    } catch (_e) {
      toast({ title: "Error", description: "Could not remove competitor.", variant: "destructive" });
    } finally {
      setDeletingId(null);
    }
  };

  const handleViewKeywords = async (project: CompProject) => {
    setSelectedProject(project);
    setKeywords([]);
    setView("keywords");
    try {
      const data = await apiClient.getSeoCompetitorKeywords(project.id);
      setKeywords(data.keywords || []);
    } catch (_e) {
      toast({ title: "Error", description: "Could not load keywords.", variant: "destructive" });
    }
  };

  const handleDoneSelecting = () => {
    if (projects.length === 0) {
      toast({ title: "No competitors added", description: "Add at least one competitor first." });
      return;
    }
    setView("direct");
  };

  // ── Filtered keywords ────────────────────────────────────────────────────
  const filteredKws = keywords.filter(k =>
    !kwSearch || k.keyword.toLowerCase().includes(kwSearch.toLowerCase())
  );

  // ─────────────────────────────────────────────────────────────────────────
  // RENDER
  // ─────────────────────────────────────────────────────────────────────────

  const Header = () => (
    <div className="flex items-center gap-3">
      <div className="w-11 h-11 rounded-lg border border-border bg-muted flex items-center justify-center flex-shrink-0 overflow-hidden">
        {faviconUrl ? (
          <img
            src={faviconUrl}
            alt={selectedDomain?.name}
            className="w-7 h-7 object-contain"
            onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
          />
        ) : (
          <span className="text-xs font-bold text-muted-foreground">
            {selectedDomain?.name?.slice(0, 2).toUpperCase() ?? "—"}
          </span>
        )}
      </div>
      <div>
        <h1 className="text-xl font-bold leading-tight">Competitors Analysis</h1>
        {selectedDomain?.url ? (
          <a
            href={selectedDomain.url.startsWith("http") ? selectedDomain.url : `https://${selectedDomain.url}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-sm text-muted-foreground hover:text-primary transition-colors mt-0.5"
          >
            {selectedDomain.url}
            <ExternalLink className="w-3 h-3" />
          </a>
        ) : (
          <p className="text-sm text-muted-foreground mt-0.5">No domain selected</p>
        )}
      </div>
    </div>
  );

  // ── VIEW: INIT ────────────────────────────────────────────────────────────
  if (view === "init") {
    return (
      <div className="p-8 space-y-8 bg-background animate-fade-in">
        <Header />
        <div className="flex flex-col items-center justify-center min-h-[65vh] gap-8">
          <RobotIllustration />
          <div className="text-center space-y-3 max-w-md">
            <h2 className="text-2xl font-bold">Competitor AI</h2>
            <p className="text-muted-foreground leading-relaxed">
              Hey, this is PromptMaxxBot and I'm here to assist you with tracking your
              Competitors' SEO Progress.
            </p>
          </div>
          <Button
            className="gradient-primary shadow-md shadow-primary/20 px-10 h-11 text-base"
            onClick={handleStartAnalysis}
            disabled={!domainId}
          >
            Start Analysis
          </Button>
        </div>
      </div>
    );
  }

  // ── VIEW: ANALYZING ───────────────────────────────────────────────────────
  if (view === "analyzing") {
    return (
      <div className="p-8 space-y-8 bg-background animate-fade-in">
        <Header />
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
            <span className="text-sm font-medium text-muted-foreground">
              Analyzing competitors from your keyword SERP data…
            </span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[0, 1, 2, 3].map(i => <AnalyzingCard key={i} index={i} />)}
          </div>
          <p className="text-xs text-muted-foreground text-center pt-2">
            This typically takes 10–30 seconds. Results will appear automatically.
          </p>
        </div>
      </div>
    );
  }

  // ── VIEW: SELECTING (All Competitors) ─────────────────────────────────────
  if (view === "selecting") {
    return (
      <div className="p-8 space-y-6 bg-background animate-fade-in">
        <Header />

        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">All Competitors Found</h2>
            <p className="text-sm text-muted-foreground mt-0.5">
              Select up to 6 competitors to track.{" "}
              <span className="text-primary font-medium">{trackedCount}/6 selected</span>
            </p>
          </div>
          <Button
            className="gradient-primary shadow-md shadow-primary/20"
            onClick={handleDoneSelecting}
            disabled={projects.length === 0}
          >
            Done →
          </Button>
        </div>

        {candidates.length === 0 ? (
          <div className="text-center py-16 text-muted-foreground">
            <p>No competitors found. Run keyword rank tracking first to collect SERP data.</p>
            <Button variant="outline" className="mt-4" onClick={handleStartAnalysis}>
              Re-analyze
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
            {candidates.map(c => (
              <div
                key={c.domain}
                className={`rounded-xl border bg-card p-4 flex items-center justify-between gap-3 transition-all ${
                  c.tracked ? "border-primary/40 bg-primary/5" : "border-border"
                }`}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-8 h-8 rounded bg-muted flex items-center justify-center flex-shrink-0 overflow-hidden">
                    <img
                      src={`https://www.google.com/s2/favicons?domain=${c.domain}&sz=32`}
                      alt={c.domain}
                      className="w-5 h-5 object-contain"
                      onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                    />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate">{c.domain}</p>
                    <p className="text-xs text-muted-foreground">{c.count} keyword{c.count !== 1 ? "s" : ""}</p>
                  </div>
                </div>
                {c.tracked ? (
                  <Badge variant="secondary" className="text-xs text-primary border-primary/30 bg-primary/10 flex-shrink-0">
                    Added
                  </Badge>
                ) : (
                  <Button
                    size="sm"
                    variant="outline"
                    className="flex-shrink-0 h-7 px-2 text-xs"
                    disabled={trackedCount >= 6 || adding === c.domain}
                    onClick={() => handleAddCompetitor(c.domain)}
                  >
                    {adding === c.domain ? "…" : <><Plus className="w-3 h-3 mr-1" />Add</>}
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // ── VIEW: DIRECT COMPETITORS ──────────────────────────────────────────────
  if (view === "direct") {
    return (
      <div className="p-8 space-y-6 bg-background animate-fade-in">
        <Header />

        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">Direct Competitors</h2>
            <p className="text-sm text-muted-foreground mt-0.5">
              {projects.length}/6 competitors tracked
            </p>
          </div>
          <Button
            variant="outline"
            onClick={() => setView("selecting")}
            disabled={analysisStatus !== "COMP"}
          >
            <Plus className="w-4 h-4 mr-2" />
            Manage Competitors
          </Button>
        </div>

        {projects.length === 0 ? (
          <div className="text-center py-16 text-muted-foreground">
            <p>No competitors tracked yet.</p>
            <Button className="mt-4 gradient-primary shadow-md shadow-primary/20" onClick={handleStartAnalysis}>
              Start Analysis
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map(p => (
              <div key={p.id} className="rounded-xl border border-border bg-card p-5 space-y-4">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-9 h-9 rounded-lg bg-muted flex items-center justify-center flex-shrink-0 overflow-hidden">
                      <img
                        src={`https://www.google.com/s2/favicons?domain=${p.competitor_domain}&sz=32`}
                        alt={p.competitor_domain}
                        className="w-6 h-6 object-contain"
                        onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                      />
                    </div>
                    <div className="min-w-0">
                      <p className="font-semibold text-sm truncate">{p.competitor_domain}</p>
                      <a
                        href={`https://${p.competitor_domain}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-primary transition-colors"
                      >
                        {p.competitor_domain}
                        <ExternalLink className="w-2.5 h-2.5" />
                      </a>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 text-muted-foreground hover:text-destructive flex-shrink-0"
                    disabled={deletingId === p.id}
                    onClick={() => handleDeleteCompetitor(p)}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                </div>

                <div className="grid grid-cols-2 gap-2 text-center">
                  <div className="rounded-lg bg-muted/50 p-2">
                    <p className="text-lg font-bold text-primary">{p.keyword_count}</p>
                    <p className="text-xs text-muted-foreground">Keywords</p>
                  </div>
                  <div className="rounded-lg bg-muted/50 p-2">
                    <p className="text-lg font-bold">{p.ranked_them}</p>
                    <p className="text-xs text-muted-foreground">Their ranked</p>
                  </div>
                </div>

                <Button
                  className="w-full gradient-primary shadow-sm shadow-primary/20 h-9 text-sm"
                  onClick={() => handleViewKeywords(p)}
                >
                  View Keywords
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // ── VIEW: KEYWORDS COMPARISON ─────────────────────────────────────────────
  if (view === "keywords" && selectedProject) {
    return (
      <div className="p-8 space-y-6 bg-background animate-fade-in">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            className="gap-1.5 text-muted-foreground hover:text-foreground"
            onClick={() => setView("direct")}
          >
            <ChevronLeft className="w-4 h-4" />
            Back
          </Button>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center overflow-hidden">
              <img
                src={`https://www.google.com/s2/favicons?domain=${selectedProject.competitor_domain}&sz=32`}
                alt={selectedProject.competitor_domain}
                className="w-5 h-5 object-contain"
                onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
              />
            </div>
            <div>
              <h1 className="text-xl font-bold leading-tight">{selectedProject.competitor_domain}</h1>
              <p className="text-sm text-muted-foreground">Keyword rank comparison</p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Search keywords…"
              value={kwSearch}
              onChange={e => setKwSearch(e.target.value)}
              className="pl-9 h-9"
            />
          </div>
          <span className="text-sm text-muted-foreground">{filteredKws.length} keywords</span>
        </div>

        <div className="rounded-xl border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/40">
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Keyword</th>
                <th className="text-center px-4 py-3 font-medium text-muted-foreground">Our Rank</th>
                <th className="text-center px-4 py-3 font-medium text-muted-foreground">
                  <span className="flex items-center justify-center gap-1.5">
                    <img
                      src={`https://www.google.com/s2/favicons?domain=${selectedProject.competitor_domain}&sz=16`}
                      alt={selectedProject.competitor_domain}
                      className="w-3.5 h-3.5"
                      onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                    />
                    Their Rank
                  </span>
                </th>
                <th className="text-center px-4 py-3 font-medium text-muted-foreground">Diff</th>
              </tr>
            </thead>
            <tbody>
              {keywords.length === 0 && (
                <tr>
                  <td colSpan={4} className="text-center py-12 text-muted-foreground">
                    Loading keywords…
                  </td>
                </tr>
              )}
              {filteredKws.map((kw, i) => {
                const diff = kw.our_rank && kw.their_rank
                  ? kw.their_rank - kw.our_rank
                  : null;
                return (
                  <tr key={kw.id} className={`border-b border-border last:border-0 ${i % 2 === 0 ? "" : "bg-muted/20"}`}>
                    <td className="px-4 py-3">
                      <span className="font-medium">{kw.keyword}</span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <RankBadge rank={kw.our_rank} />
                    </td>
                    <td className="px-4 py-3 text-center">
                      <RankBadge rank={kw.their_rank} />
                    </td>
                    <td className="px-4 py-3 text-center">
                      {diff === null ? (
                        <span className="text-muted-foreground text-xs">–</span>
                      ) : diff > 0 ? (
                        <span className="text-emerald-600 text-xs font-medium">+{diff}</span>
                      ) : diff < 0 ? (
                        <span className="text-red-500 text-xs font-medium">{diff}</span>
                      ) : (
                        <span className="text-muted-foreground text-xs">=</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  return null;
};

export default SeoCompetitors;
