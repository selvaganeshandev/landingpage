import { Card } from "@/components/ui/card";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Info } from "lucide-react";

interface VisibilityScoreProps {
  brand: string;
  score: number;
  mentions: number;
  avgPosition?: number;
  sentiment: {
    positive: number;
    neutral: number;
    negative: number;
  };
}

/**
 * Score bands for the visibility gauge.
 *
 * The score is built from absolute RATES over the domain's own tracked prompts
 * (see `compute_visibility_score` in backend/analytics/views_dashboard.py):
 * mentions 40%, citations 30%, sentiment 20%, position 10%. Because every
 * component is bounded 0-1 by construction, the full 0-100 range is reachable
 * and these are ordinary fixed thresholds — no skew is needed.
 *
 * They previously WERE skewed, to compensate for an older formula that divided
 * by the MAX across all domains and pinned almost every domain into 11-29. That
 * normalization is gone; do not reintroduce compensating thresholds here.
 *
 * Tune here if the scoring distribution changes — this is the single source
 * of truth for the gauge's label logic and is pure frontend (no API change).
 */
const SCORE_BANDS = [
  { min: 70, label: "Great", description: "Frequently mentioned and often preferred by LLMs", color: "hsl(var(--success))" },
  { min: 50, label: "Good", description: "Regularly mentioned across AI platforms", color: "hsl(var(--primary))" },
  { min: 30, label: "Average", description: "Moderately visible in AI answers", color: "hsl(var(--warning))" },
  { min: 15, label: "Below Average", description: "Occasionally surfaced by LLMs", color: "hsl(var(--warning))" },
  { min: 0, label: "Poor", description: "Rarely mentioned in AI answers", color: "hsl(var(--destructive))" },
] as const;

const getBand = (score: number) =>
  SCORE_BANDS.find((band) => score >= band.min) ?? SCORE_BANDS[SCORE_BANDS.length - 1];

/** The card's shared info affordance, so every figure on it can explain what it
 *  counts and over what window without repeating the tooltip scaffolding. */
const InfoHint = ({ side = "top", children }: { side?: "top" | "right"; children: React.ReactNode }) => (
  <TooltipProvider>
    <Tooltip>
      <TooltipTrigger asChild>
        <button type="button" className="inline-flex cursor-pointer text-muted-foreground opacity-50 hover:opacity-100 transition-opacity">
          <Info className="h-3.5 w-3.5" />
        </button>
      </TooltipTrigger>
      <TooltipContent side={side} className="max-w-xs text-xs">
        {children}
      </TooltipContent>
    </Tooltip>
  </TooltipProvider>
);

// Semicircle arc geometry: path from (20,100) to (180,100) with radius 80.
const ARC_RADIUS = 80;
const ARC_LENGTH = Math.PI * ARC_RADIUS;
const ARC_PATH = `M 20 100 A ${ARC_RADIUS} ${ARC_RADIUS} 0 0 1 180 100`;

export const VisibilityScore = ({ brand, score, mentions, avgPosition = 0, sentiment }: VisibilityScoreProps) => {
  const clampedScore = Math.max(0, Math.min(100, Number(score) || 0));
  const band = getBand(clampedScore);
  const valueLength = (clampedScore / 100) * ARC_LENGTH;

  return (
    <Card className="p-6 h-full border border-border">
      <div className="space-y-4 h-full flex flex-col">
        <div className="flex items-center gap-1.5">
          <h3 className="text-lg font-semibold">AI Visibility</h3>
          {/* Names all four components and their weights. The previous text
              described only mentions and position, leaving half the score
              (citations + sentiment) unexplained — so a user whose score
              moved could not tell what had actually changed. */}
          <InfoHint side="right">
            <p className="font-medium mb-1">How your brand shows up in AI answers (0–100)</p>
            <p className="mb-1.5 text-muted-foreground">
              Measured across the prompts you track, as a share of the answers we checked.
            </p>
            <ul className="space-y-0.5">
              <li>• <strong>40%</strong> how often you're mentioned</li>
              <li>• <strong>30%</strong> how often your site is cited</li>
              <li>• <strong>20%</strong> how positively you're described</li>
              <li>• <strong>10%</strong> how early you appear in the answer</li>
            </ul>
          </InfoHint>
        </div>

        {/* AI Visibility Score gauge (semicircular arc) */}
        <div className="flex flex-col items-center">
          <div className="relative w-full max-w-[280px]">
            <svg viewBox="0 0 200 112" className="w-full" role="img" aria-label={`AI visibility score ${Math.round(clampedScore)} out of 100, ${band.label}`}>
              <path
                d={ARC_PATH}
                fill="none"
                stroke="hsl(var(--muted))"
                strokeWidth={14}
                strokeLinecap="round"
              />
              <path
                d={ARC_PATH}
                fill="none"
                stroke={band.color}
                strokeWidth={14}
                strokeLinecap="round"
                strokeDasharray={`${valueLength} ${ARC_LENGTH}`}
                className="transition-all duration-700 ease-out"
              />
            </svg>
            <div className="absolute inset-x-0 bottom-0 flex flex-col items-center">
              <span className="text-4xl font-bold text-primary leading-none">{Math.round(clampedScore)}</span>
              <span className="text-xs text-muted-foreground mt-1">out of 100</span>
            </div>
          </div>
          <p className="text-lg font-semibold mt-2" style={{ color: band.color }}>{band.label}</p>
          <p className="text-sm text-muted-foreground text-center">{band.description}</p>
        </div>

        {/* Maturity ladder — shows every stage so users see where they sit and what "better" looks like (P2). */}
        <div className="flex gap-1 pt-1" role="list" aria-label={`Visibility maturity stages, currently ${band.label}`}>
          {[...SCORE_BANDS].reverse().map((stage) => {
            const isCurrent = stage.label === band.label;
            return (
              <div key={stage.label} role="listitem" className="flex flex-1 flex-col items-center gap-1">
                <div
                  className="h-1.5 w-full rounded-full transition-colors"
                  style={{ backgroundColor: isCurrent ? band.color : "hsl(var(--muted))" }}
                />
                <span
                  className={`text-center text-[10px] leading-tight ${isCurrent ? "font-semibold text-foreground" : "text-muted-foreground"}`}
                >
                  {stage.label}
                </span>
              </div>
            );
          })}
        </div>

        <div className="grid grid-cols-2 gap-4 pt-2">
          <div>
            <div className="flex items-center gap-1.5">
              <p className="text-sm text-muted-foreground">Total Mentions</p>
              {/* This card has no time control of its own, so "this period"
                  meant nothing here — name the control that actually sets the
                  window instead. */}
              <InfoHint>
                Times your brand was named in AI answers across your tracked prompts. Covers the date range set at the top of the page — the last 30 days if you haven't chosen one.
              </InfoHint>
            </div>
            <p className="text-2xl font-bold">{mentions}</p>
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <p className="text-sm text-muted-foreground">Avg Position</p>
              <InfoHint>
                Average rank of your brand where it appears in an AI answer, over the same date range. Lower is better — position 1 means it was named first.
              </InfoHint>
            </div>
            <p className="text-2xl font-bold">{avgPosition > 0 ? avgPosition.toFixed(1) : '0'}</p>
          </div>
        </div>

        <div className="space-y-2 pt-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Sentiment</span>
          </div>
          <div className="flex gap-1 h-2 rounded-full overflow-hidden">
            <div
              className="bg-success"
              style={{ width: `${sentiment.positive}%` }}
            />
            <div
              className="bg-warning"
              style={{ width: `${sentiment.neutral}%` }}
            />
            <div
              className="bg-destructive"
              style={{ width: `${sentiment.negative}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>{sentiment.positive}% Positive</span>
            <span>{sentiment.neutral}% Neutral</span>
            <span>{sentiment.negative}% Negative</span>
          </div>
        </div>
      </div>
    </Card>
  );
};
