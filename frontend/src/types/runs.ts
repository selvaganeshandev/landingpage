/**
 * Runs — the evidence ledger behind every GEO number.
 *
 * One row per prompt × engine execution, written by the engine and read
 * (never written) by the app. Mirrors backend/prompts/views_runs.py.
 */

export interface RunRow {
  id: number;
  tracked_at: string;
  platform: string;
  region: string;
  prompt_id: number;
  prompt: string;
  group_id: number | null;
  group: string;
  is_mention: boolean;
  total_mentions: number;
  total_citations: number;
  position: number;
  sentiment_category: "positive" | "neutral" | "negative" | string;
  sentiment_score: number;
  citations: string[];
  competitors: string[];
  context_summary: string;
  /** Which repeat of this question this row is, inside the current window. */
  run_number: number | null;
  runs_for_prompt: number | null;
}

export interface RunsWindow {
  since: string;
  until: string;
  days: number;
}

export interface RunsListResponse {
  runs: RunRow[];
  total_count: number;
  limit: number;
  offset: number;
  window: RunsWindow;
}

export type ConfidenceLevel = "high" | "good" | "fair" | "low" | "none";

export interface RunsConfidence {
  level: ConfidenceLevel;
  marker: string;
  label: string;
}

export interface RunsGroupRow {
  id: number;
  label: string;
  runs: number;
}

export interface RunsPlatformRow {
  platform: string;
  runs: number;
  variants: number;
  mentioned: number;
  cited: number;
  mention_rate: number;
}

export interface RunsSummaryResponse {
  total_runs: number;
  variants: number;
  engines: number;
  avg_runs_per_variant: number;
  confidence: RunsConfidence;
  low_confidence_variants: number;
  mentioned_runs: number;
  cited_runs: number;
  mention_rate: number;
  citation_rate: number;
  avg_position: number | null;
  last_run_at: string | null;
  by_platform: RunsPlatformRow[];
  groups: RunsGroupRow[];
  /** Questions the engines answered inconsistently across repeats. */
  unstable_variants: number;
  window: RunsWindow;
}

export interface RunsFilters {
  domain_id: number;
  days?: number;
  platform?: string;
  group_id?: string;
  mention?: "any" | "yes" | "no";
  variance?: "any" | "only";
  cited?: "any" | "yes";
  search?: string;
  limit?: number;
  offset?: number;
}

/** How many runs a variant needs before its rate is worth quoting. */
export const CONFIDENCE_TONE: Record<ConfidenceLevel, string> = {
  high: "text-emerald-600",
  good: "text-emerald-600",
  fair: "text-amber-600",
  low: "text-destructive",
  none: "text-muted-foreground",
};
