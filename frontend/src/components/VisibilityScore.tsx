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
 * Score bands calibrated to the visibility score's real distribution.
 *
 * The backend (`_calculate_visibility_score`) normalizes mentions, citations
 * and position against the MAXIMUM across ALL domains, so only the single
 * strongest domain approaches 90-100 and typical domains land far lower
 * (the backend's own comments cite ~22 as a common value). Semrush-style
 * fixed bands ("92 = Great") would therefore read "Poor" for healthy domains.
 * These thresholds skew accordingly so mid-tier domains read Average/Good.
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
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <button type="button" className="inline-flex cursor-pointer text-muted-foreground opacity-50 hover:opacity-100 transition-opacity">
                  <Info className="h-3.5 w-3.5" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="right" className="max-w-xs text-xs">
                Measures how frequently and prominently your brand appears in AI-generated answers across your tracked prompts (0 to 100).
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
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

        <div className="grid grid-cols-2 gap-4 pt-2">
          <div>
            <p className="text-sm text-muted-foreground">Total Mentions</p>
            <p className="text-2xl font-bold">{mentions}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Avg Position</p>
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
