import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Card } from "@/components/ui/card";
import { apiClient } from "@/services/api";
import { useToast } from "@/hooks/use-toast";
import { ArrowLeft, Loader2, ExternalLink, Sparkles } from "lucide-react";
import { GoogleIcon } from "@/components/GoogleIcon";

interface Candidate {
  query: string;
  impressions: number;
  clicks: number;
  position: number;
  tier: number;
  tier_label: string;
}

interface SearchConsoleSeedPickerProps {
  domainId?: number;
  onBack: () => void;
  /** Called once a review-ready run exists, so the page can show it. */
  onRunCreated: () => void;
}

/** Selected by default. Enough to be worth tracking, small enough to review. */
const DEFAULT_SELECTION = 20;

const TIER_STYLES: Record<number, string> = {
  1: "bg-primary/10 text-primary border-primary/20",
  2: "bg-blue-500/10 text-blue-600 border-blue-500/20",
  3: "bg-muted text-muted-foreground border-border",
};

/**
 * Picks which Search Console queries become prompts.
 *
 * The list arrives already filtered: branded queries removed, because an
 * assistant asked about a brand by name will describe it regardless and that
 * measures nothing about discovery. What remains is ordered by whether an
 * answer would name any brand at all — a shortlist question surfaces vendors,
 * an explainer does not — and then by the impressions being lost at a weak
 * position, which is demand the brand is not currently winning.
 */
export const SearchConsoleSeedPicker = ({
  domainId,
  onBack,
  onRunCreated,
}: SearchConsoleSeedPickerProps) => {
  const { toast } = useToast();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [connected, setConnected] = useState(true);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [building, setBuilding] = useState(false);

  useEffect(() => {
    if (!domainId) return;
    let cancelled = false;

    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data: any = await apiClient.getSearchConsoleSeeds(domainId);
        if (cancelled) return;
        setConnected(Boolean(data?.connected));
        const rows: Candidate[] = data?.candidates || [];
        setCandidates(rows);
        setSelected(new Set(rows.slice(0, DEFAULT_SELECTION).map((c) => c.query)));
        if (data?.error) setError(data.error);
      } catch (e: any) {
        if (!cancelled) setError(e?.message || "Could not read Search Console.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [domainId]);

  const toggle = (query: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(query) ? next.delete(query) : next.add(query);
      return next;
    });
  };

  const handleBuild = async () => {
    if (!domainId || selected.size === 0) return;
    setBuilding(true);
    try {
      const result: any = await apiClient.createRunFromSearchConsole({
        domain_id: domainId,
        queries: Array.from(selected),
      });
      toast({
        title: "Prompts ready to review",
        description: `${result?.candidates_created ?? 0} prompts written from your search demand.`,
      });
      onRunCreated();
    } catch (e: any) {
      toast({
        title: "Could not build prompts",
        description: e?.data?.error || e?.message || "Please try again shortly.",
        variant: "destructive",
      });
    } finally {
      setBuilding(false);
    }
  };

  return (
    <div className="py-2">
      <Button variant="ghost" size="sm" onClick={onBack} className="mb-4 -ml-2">
        <ArrowLeft className="h-4 w-4 mr-2" />
        Back
      </Button>

      <div className="text-center mb-6">
        <h2 className="font-inter text-2xl font-bold tracking-tight">
          Prompts from your search demand
        </h2>
        <p className="text-muted-foreground mt-2 text-sm max-w-lg mx-auto">
          These are searches people already made — with your brand name filtered
          out, since those only find you because they knew you. Pick the ones
          worth tracking and we'll rewrite them as questions.
        </p>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-primary mb-3" />
          <p className="text-sm text-muted-foreground">Reading Search Console…</p>
        </div>
      ) : !connected ? (
        <Card className="p-8 text-center max-w-md mx-auto">
          <div className="w-12 h-12 rounded-full bg-blue-500/10 flex items-center justify-center mx-auto mb-4">
            <GoogleIcon className="h-6 w-6" />
          </div>
          <h3 className="font-semibold">Search Console isn't connected</h3>
          <p className="text-sm text-muted-foreground mt-2">
            Connect it for this project and we can build prompts from the
            searches people actually make.
          </p>
          {/* Organization Settings, not a dedicated integrations page — that
              is where the connect dialog actually lives. */}
          <Button className="mt-5" onClick={() => navigate("/organization-settings?tab=domains")}>
            Connect Search Console
            <ExternalLink className="h-4 w-4 ml-2" />
          </Button>
        </Card>
      ) : candidates.length === 0 ? (
        <Card className="p-8 text-center max-w-md mx-auto">
          {/* A failed request and an empty result are different outcomes and
              used to render identically — "no usable queries" over a message
              that was really a transport error. */}
          <h3 className="font-semibold">
            {error ? "Couldn't read Search Console" : "No usable queries yet"}
          </h3>
          <p className="text-sm text-muted-foreground mt-2">
            {error ||
              "Search Console has no non-branded searches for this project yet. Generate prompts with AI instead — this fills in as the site picks up impressions."}
          </p>
          <Button variant="outline" className="mt-5" onClick={onBack}>
            Choose another way
          </Button>
        </Card>
      ) : (
        <>
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm text-muted-foreground">
              <span className="font-medium text-foreground">{selected.size}</span> of{" "}
              {candidates.length} selected
            </p>
            <div className="flex gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelected(new Set(candidates.map((c) => c.query)))}
              >
                Select all
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setSelected(new Set())}>
                Clear
              </Button>
            </div>
          </div>

          <div className="border border-border rounded-lg divide-y divide-border max-h-[420px] overflow-y-auto">
            {candidates.map((c) => (
              <label
                key={c.query}
                className="flex items-center gap-3 p-3 cursor-pointer hover:bg-accent/40 transition-colors"
              >
                <Checkbox
                  checked={selected.has(c.query)}
                  onCheckedChange={() => toggle(c.query)}
                />
                <span className="flex-1 text-sm">{c.query}</span>
                <Badge variant="outline" className={`text-xs ${TIER_STYLES[c.tier] || ""}`}>
                  {c.tier_label}
                </Badge>
                <span className="text-xs text-muted-foreground w-28 text-right tabular-nums">
                  {c.impressions} impr · pos {c.position}
                </span>
              </label>
            ))}
          </div>

          <div className="flex justify-end mt-5">
            <Button
              onClick={handleBuild}
              disabled={selected.size === 0 || building}
              className="gradient-primary shadow-md shadow-primary/20"
            >
              {building ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Writing prompts…
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 mr-2" />
                  Build {selected.size} prompt{selected.size === 1 ? "" : "s"}
                </>
              )}
            </Button>
          </div>
        </>
      )}
    </div>
  );
};
