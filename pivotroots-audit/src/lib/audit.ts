/**
 * What the page knows about an audit, and how it talks to the backend.
 *
 * All calls go through this app's own /api/audits route handlers, which proxy
 * to the PromptMaxx backend's public audit endpoints (backend/audits/views.py).
 * Shapes mirror PublicAuditSerializer; only the fields this page reads are typed.
 */
import { BASE_PATH } from "./site";

export type AuditStatus = "INIT" | "PROC" | "DONE" | "FAIL";
export type GeoStage = "absent" | "present" | "preferred" | "default" | "";

export interface LiveRow {
  engine: string;
  prompt: string;
  result: "cited" | "mentioned" | "absent";
  position: number | null;
  instead: string;
  at: string;
}

export interface EngineSummary {
  platform: string;
  asked: number;
  answered: number;
  mentioned: number;
  cited: number;
  preferred: boolean;
}

export interface PublicAudit {
  public_token: string;
  host: string;
  brand_name: string;
  industry: string;
  seo_enabled: boolean;
  status: AuditStatus;
  stage: string;
  stage_index: number;
  stage_total: number;
  stage_label: string;
  progress: number;
  stage_detail: Record<string, Record<string, unknown>>;
  live?: LiveRow[];
  error: string;
  geo_score: number | null;
  geo_stage: GeoStage;
  appearances: number;
  cited_runs: number;
  total_runs: number;
  engines_preferred: number;
  engines_total: number;
  share_of_voice: string | number | null;
  report: {
    geo?: {
      engines?: EngineSummary[];
      evidence?: { prompt_text: string; cited_instead: string[]; engines: Record<string, string> }[];
    };
    summary?: { headline?: string; key_findings?: string[] };
    quick_wins?: unknown[];
  } | null;
  expires_at: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface CreateResponse {
  id: number;
  host: string;
  status: AuditStatus;
  reused: boolean;
  public_token: string;
  error?: string;
}

export class AuditApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function parse<T>(res: Response): Promise<T> {
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg =
      res.status === 429 ? data.error || "We've hit today's audit limit. Please try again tomorrow."
      : res.status === 503 ? "The audit engine is taking a break. Please try again in a few minutes."
      : res.status === 404 ? "This audit link has expired or never existed."
      : data.error || "Something went wrong. Please try again.";
    throw new AuditApiError(res.status, msg);
  }
  return data as T;
}

export async function createAudit(input: {
  url: string; email: string; brand_name: string; country?: string; campaign?: string; turnstile_token?: string;
}) {
  const res = await fetch(`${BASE_PATH}/api/audits`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return parse<CreateResponse>(res);
}

export async function getAudit(token: string) {
  const res = await fetch(`${BASE_PATH}/api/audits/${encodeURIComponent(token)}`, { cache: "no-store" });
  return parse<PublicAudit>(res);
}

export function pdfUrl(token: string) {
  return `${BASE_PATH}/api/audits/${encodeURIComponent(token)}/pdf`;
}

export function reportPath(token: string) {
  return `${BASE_PATH}/audit/${encodeURIComponent(token)}`;
}

/* ---- form helpers (same rules as the original page) ---- */

export const cleanDomain = (v: string) =>
  v.trim().toLowerCase().replace(/^https?:\/\//, "").replace(/^www\./, "").replace(/\/.*$/, "");

export const titleCase = (d: string) =>
  d.split(".")[0].replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export const isDomain = (d: string) => /^[a-z0-9.-]+\.[a-z]{2,}$/i.test(d);
export const isEmail = (e: string) => /^[^\s@]+@[^\s@]+\.[a-z]{2,}$/i.test(e);

/* ---- numbers for the score panel, from the finished report ---- */

export function scoreSummary(a: PublicAudit) {
  const engines = a.report?.geo?.engines ?? [];
  const evidence = a.report?.geo?.evidence ?? [];
  const total = a.engines_total || engines.length;
  const sov = a.share_of_voice == null ? null : Math.round(Number(a.share_of_voice));
  return {
    score: a.geo_score ?? 0,
    stage: (a.geo_stage || "present").toUpperCase(),
    mention: engines.filter((e) => e.mentioned > 0).length,
    cite: engines.filter((e) => e.cited > 0).length,
    total,
    rivalInstead: evidence.filter((e) => (e.cited_instead || []).length > 0).length,
    questions: evidence.length,
    shareOfVoice: sov,
    verdict: a.report?.summary?.headline || "",
  };
}
