/**
 * The seven pipeline stages, in the engine's order (Audit.STAGE_ORDER in
 * backend/audits/models.py). `key` must match the backend; the labels are this
 * page's voice. `detail` renders the engine's live counters for that stage.
 */
import { ENGINE_COUNT, PROMPT_COUNT } from "./site";

export type StageKey = "profile" | "crawl" | "prompts" | "engines" | "serp" | "score" | "publish";

export interface Stage {
  key: StageKey;
  title: string;
  /** What the card says before the engine has reported anything for it. */
  blurb: string;
  /** Live text from the engine's counters, or "" to keep the blurb. */
  detail: (d: Record<string, unknown>, seoEnabled: boolean) => string;
}

const n = (v: unknown): v is number => typeof v === "number";

export const STAGES: Stage[] = [
  {
    key: "profile",
    title: "Reading your site",
    blurb: "industry, products, rivals",
    detail: (d) =>
      n(d.competitors) ? `${d.competitors} rivals found` : d.source === "knowledge" ? "site unreadable · using public knowledge" : "",
  },
  {
    key: "crawl",
    title: "Checking your pages",
    blurb: "schema, bylines, dates",
    detail: (d) => (d.skipped ? "skipped" : d.error ? "site could not be read" : n(d.pages) ? `${d.pages} pages sampled` : ""),
  },
  {
    key: "prompts",
    title: "Writing questions",
    blurb: `${PROMPT_COUNT} things buyers ask`,
    detail: (d) => (n(d.count) ? `${d.count} questions written` : ""),
  },
  {
    key: "engines",
    title: `Asking ${ENGINE_COUNT} engines`,
    blurb: "every question, every engine",
    detail: (d) => (n(d.done) && n(d.total) ? `${d.done} / ${d.total} answers` : ""),
  },
  {
    key: "serp",
    title: "Checking Google",
    blurb: "where you rank today",
    detail: (d, seo) => (!seo || d.skipped ? "not in the free audit" : n(d.done) && n(d.total) ? `${d.done} / ${d.total} keywords` : ""),
  },
  {
    key: "score",
    title: "Scoring",
    blurb: "who mentions, who cites, who's framed how",
    detail: (d) => (n(d.geo_score) ? `AI visibility ${d.geo_score}` : ""),
  },
  {
    key: "publish",
    title: "Your report",
    blurb: "link + PDF",
    detail: () => "",
  },
];

export function stageIndex(key: string): number {
  return STAGES.findIndex((s) => s.key === key);
}
