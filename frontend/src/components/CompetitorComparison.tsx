import { Card } from "@/components/ui/card";
import { TrendingUp, TrendingDown } from "lucide-react";

interface Competitor {
  name: string;
  url: string;
  mentions: number;
  shareOfVoice: number;
  /** Change in share-of-voice POINTS vs the last reading before this window.
   *  null when the brand has no earlier reading — no trend is not the same as
   *  a trend of zero, so it renders as nothing rather than "0%". */
  trend: number | null;
  /** This row is the viewing brand, not a competitor. */
  isYou: boolean;
}

export interface CompetitorComparisonProps {
  /** Every brand in the market — YOURS INCLUDED. The card is titled Share of
   *  Voice, so omitting your own row (as it did when it was fed the API's
   *  `competitors` list) left out the only figure the user came for. */
  competitors?: Array<{ name?: string; url?: string; mentions?: number; shareOfVoice?: number; trend?: number | null; isYou?: boolean; }>;
}

export const CompetitorComparison = ({ competitors = [] }: CompetitorComparisonProps) => {
  const list: Competitor[] = (competitors && competitors.length > 0 ? competitors.map((c, i) => ({
    name: c.name || `Competitor ${i+1}`,
    url: c.url || '',
    mentions: c.mentions ?? 0,
    shareOfVoice: c.shareOfVoice ?? 0,
    // Keep null distinct from 0 — `?? 0` here is what used to turn "unknown"
    // into a confident-looking 0%.
    trend: c.trend ?? null,
    isYou: Boolean(c.isYou),
  })) : [])
    // Ranked by share, so the badge is a real market position. It used to be the
    // array index, which numbered whatever order the API happened to return.
    .sort((a, b) => b.shareOfVoice - a.shareOfVoice);
  return (
    <Card className="p-6 h-full flex flex-col border border-border">
      <h3 className="text-lg font-semibold mb-4">Share of Voice</h3>
      <div className="space-y-4 flex-1">
        {list.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-muted-foreground text-center">No competitors found</p>
          </div>
        ) : (
          list.map((competitor, index) => (
          <div key={`${competitor.name}-${index}`} className={competitor.isYou ? "space-y-2 rounded-lg bg-primary/5 -mx-2 px-2 py-2" : "space-y-2"}>
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-secondary text-primary-foreground flex items-center justify-center font-bold text-sm flex-shrink-0">
                  {index + 1}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="font-medium truncate">
                    {competitor.name}
                    {competitor.isYou && (
                      <span className="ml-2 rounded-full bg-primary px-2 py-0.5 text-[10px] font-semibold text-primary-foreground align-middle">
                        You
                      </span>
                    )}
                  </p>
                  <p className="text-xs text-muted-foreground truncate">{competitor.url}</p>
                </div>
              </div>
              <div className="text-right flex-shrink-0">
                <p className="text-sm font-medium">{competitor.mentions} mentions</p>
                {competitor.trend !== null && (
                  <div
                    className={`flex items-center justify-end gap-1 text-xs ${
                      competitor.trend > 0
                        ? "text-success"
                        : competitor.trend < 0
                        ? "text-destructive"
                        : "text-muted-foreground"
                    }`}
                    title="Change in share of voice vs the previous reading"
                  >
                    {competitor.trend < 0 ? (
                      <TrendingDown className="h-3 w-3" />
                    ) : (
                      <TrendingUp className="h-3 w-3" />
                    )}
                    {competitor.trend > 0 ? "+" : ""}{competitor.trend} pts
                  </div>
                )}
              </div>
            </div>
            <div className="space-y-1">
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-primary to-secondary transition-all"
                  style={{ width: `${competitor.shareOfVoice}%` }}
                />
              </div>
              <p className="text-xs text-muted-foreground text-right">{competitor.shareOfVoice}% share of voice</p>
            </div>
          </div>
        ))
        )}
      </div>
    </Card>
  );
};
