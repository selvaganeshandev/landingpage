import { useState, useEffect, useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { apiClient } from "@/services/api";
import { useToast } from "@/hooks/use-toast";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Loader2,
  ArrowLeft,
  ExternalLink,
  Lightbulb,
  Layers,
  Calculator,
} from "lucide-react";

interface Sibling {
  id: number;
  keyword: string;
  rank_now: number;
  search_volume: number;
}

interface Detail {
  keyword: {
    id: number;
    keyword: string;
    rank_now: number;
    top_rank: number | null;
    search_volume: number;
    target_url: string;
    trajectory: { state: string; delta: number; volatility: number; points: number };
    difficulty: { level: string | null; index: number | null };
    opportunity: {
      score: number;
      estimated_clicks: number;
      winnability: number;
      target_position: number;
      reasons: string[];
      ctr_now: number;
      ctr_target: number;
    };
  };
  siblings: Sibling[];
  sibling_volume: number;
  action: { headline: string; detail: string };
}

const fmt = (n: number) => n.toLocaleString();
const fmtVol = (n: number) => {
  if (!n) return "—";
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return String(n);
};

export default function SeoOpportunityDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [data, setData] = useState<Detail | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      setData((await apiClient.getSeoOpportunityDetail(id)) as Detail);
    } catch (err: any) {
      toast({
        title: "Could not load this opportunity",
        description: err?.message || "Please try again.",
        variant: "destructive",
      });
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [id, toast]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="p-8 flex flex-col items-center justify-center py-32">
        <Loader2 className="h-10 w-10 animate-spin text-primary mb-4" />
        <span className="text-muted-foreground text-sm">Loading opportunity...</span>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="p-8 space-y-8 bg-background animate-fade-in">
        <Button
          variant="outline"
          size="icon"
          className="border-border/50"
          onClick={() => navigate("/seo-opportunities")}
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="py-32 text-center text-muted-foreground">
          This opportunity could not be found.
        </div>
      </div>
    );
  }

  const { keyword: kw, siblings, sibling_volume, action } = data;
  const o = kw.opportunity;

  return (
    <div className="p-8 space-y-8 bg-background animate-fade-in">
      {/* Matches the header on SeoKeywordDetail and CompetitorDetail: an
          icon-only back button inline to the left of the title, and a rule
          under the row. A full-width text button above a text-4xl title made
          this read as a top-level page rather than a detail view. */}
      <div className="flex items-center justify-between pb-4 border-b border-border/50">
        <div className="flex items-center gap-4 min-w-0">
          <Button
            variant="outline"
            size="icon"
            className="border-border/50 flex-shrink-0"
            onClick={() => navigate("/seo-opportunities")}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="min-w-0">
            <h1 className="text-2xl font-bold tracking-tight font-inter truncate">
              {kw.keyword}
            </h1>
            <p className="text-muted-foreground mt-0.5 flex items-center gap-2 flex-wrap text-sm">
              <Badge variant="secondary" className="tabular-nums">
                #{kw.rank_now}
              </Badge>
              <span>{fmt(kw.search_volume)} searches/mo</span>
              {kw.top_rank ? <span>· best ever #{kw.top_rank}</span> : null}
            </p>
          </div>
        </div>
      </div>

      {/* 1 — what to do. The reason this page exists rather than a number. */}
      <Card className="p-6 border border-border">
        <div className="flex items-start gap-3">
          <div className="rounded-full bg-primary/10 p-2 flex-shrink-0">
            <Lightbulb className="h-5 w-5 text-primary" />
          </div>
          <div className="min-w-0">
            <p className="text-sm text-muted-foreground">Recommended action</p>
            <h2 className="text-lg font-semibold mt-0.5">{action.headline}</h2>
            <p className="text-sm text-muted-foreground mt-1.5 max-w-3xl">{action.detail}</p>
          </div>
        </div>
      </Card>

      {/* 2 — the score, shown as arithmetic rather than asserted. */}
      <Card className="p-6 border border-border space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Calculator className="h-4 w-4 text-secondary" />
            <h2 className="text-lg font-semibold">How this scores {fmt(Math.round(o.score))}</h2>
          </div>
          <Badge variant="secondary" className="tabular-nums">
            target #{o.target_position}
          </Badge>
        </div>

        <div className="rounded-lg bg-muted/40 border border-border p-4 space-y-1.5">
          <p className="text-sm text-muted-foreground">Estimated extra clicks per month</p>
          <p className="text-sm tabular-nums">
            {fmt(kw.search_volume)} searches × ({o.ctr_target}% at #{o.target_position} −{" "}
            {o.ctr_now}% at #{kw.rank_now}) ={" "}
            <span className="font-semibold text-foreground">
              {fmt(Math.round(o.estimated_clicks))}
            </span>
          </p>
          <p className="text-xs text-muted-foreground pt-1">
            Those click-through rates are published industry averages by position, not measured
            for this site — no Search Console data is stored per keyword. Use the figure to
            compare keywords, not to forecast traffic.
          </p>
        </div>

        <div>
          <p className="text-sm text-muted-foreground mb-2">
            Winnability ×{o.winnability} — {fmt(Math.round(o.estimated_clicks))} ×{" "}
            {o.winnability} = {fmt(Math.round(o.score))}
          </p>
          <ul className="space-y-1.5">
            {o.reasons.map((r) => (
              <li key={r} className="text-sm flex items-start gap-2">
                <span className="text-primary mt-0.5">·</span>
                <span>{r}</span>
              </li>
            ))}
            {o.reasons.length === 0 && (
              <li className="text-sm text-muted-foreground">
                No adjusting factors — scored on estimated value alone.
              </li>
            )}
          </ul>
        </div>
      </Card>

      {/* 3 — the page-level view. Nothing else in the product shows this. */}
      <Card className="p-6 border border-border space-y-4">
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-primary" />
          <h2 className="text-lg font-semibold">The page behind this keyword</h2>
        </div>

        {kw.target_url ? (
          <a
            href={kw.target_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline break-all"
          >
            {kw.target_url}
            <ExternalLink className="h-3.5 w-3.5 flex-shrink-0" />
          </a>
        ) : (
          <p className="text-sm text-muted-foreground">No ranking page recorded.</p>
        )}

        {siblings.length > 0 ? (
          <>
            <p className="text-sm text-muted-foreground">
              This one URL also ranks for{" "}
              <span className="font-medium text-foreground">{siblings.length}</span> other tracked
              keyword{siblings.length === 1 ? "" : "s"}, worth{" "}
              <span className="font-medium text-foreground">{fmt(sibling_volume)}</span> searches a
              month between them. Work done here lands on all of them at once.
            </p>

            <div className="rounded-md border border-border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[90px]">Position</TableHead>
                    <TableHead>Keyword</TableHead>
                    <TableHead className="w-[120px] text-right">Volume</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {siblings.map((s) => (
                    <TableRow
                      key={s.id}
                      className="cursor-pointer transition-colors hover:bg-muted/50"
                      onClick={() => navigate(`/seo-opportunities/${s.id}`)}
                    >
                      <TableCell>
                        <Badge variant="secondary" className="tabular-nums">
                          {s.rank_now === 0 ? "—" : s.rank_now}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-medium">{s.keyword}</TableCell>
                      <TableCell className="text-right tabular-nums">
                        {fmtVol(s.search_volume)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </>
        ) : (
          <p className="text-sm text-muted-foreground">
            No other tracked keyword ranks through this URL, so any work here affects this keyword
            alone.
          </p>
        )}
      </Card>
    </div>
  );
}
