/**
 * Small shared pieces for the Audit Engine screens: the GEO score ring and
 * band badge and the six-stage progress strip. Formatting helpers live in
 * ./format so this file only exports components (fast refresh).
 */
import { useEffect, useState } from "react";
import { Loader2, Check, X, Minus } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import {
  AUDIT_STAGES, GEO_STAGE_LABELS,
  type AuditStage, type AuditStatus, type GeoStage,
} from "@/types/audit";

export { fmtDate, fmtDateTime, timeAgo, pct, saveBlob } from "./format";

/** Typical wall clock, for the "approx." half of the readout.
 *
 *  Measured after the engine stage was flattened onto one pool: 8 prompts x 3
 *  engines at AUDIT_MAX_CONCURRENT_CALLS=12 costs ~100s, plus ~90s of profile,
 *  crawl, scoring and publishing. Ranking 25 keywords adds another ~40s —
 *  measured at 4-23s per lookup, pooled — so an audit with the SERP stage on
 *  is meaningfully longer and gets its own figure rather than one average that
 *  is wrong for both.
 *
 *  A guide, not a promise: a large site or a slow provider pushes it out,
 *  which is what the "taking longer than usual" note is for. */
const TYPICAL_RUN_SECONDS = { geo: 4 * 60, withSeo: 5 * 60 };

function clock(seconds: number) {
  const s = Math.max(0, Math.floor(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

/**
 * How long this audit has been running, ticking once a second, against how
 * long one usually takes. Once it finishes it holds the final duration.
 *
 * The clock is derived from the row's own timestamps rather than from when
 * the page opened, so a reload — or a lead opening the link from their email
 * ten minutes later — still shows the truth.
 */
export function RunTimer({
  startedAt, finishedAt, running, seoEnabled = false,
}: {
  startedAt: string;
  finishedAt?: string | null;
  running: boolean;
  /** Ranking keywords on Google adds roughly a minute. */
  seoEnabled?: boolean;
}) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!running) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [running]);

  const start = new Date(startedAt).getTime();
  if (!Number.isFinite(start)) return null;
  const end = !running && finishedAt ? new Date(finishedAt).getTime() : now;
  const elapsed = (end - start) / 1000;

  if (!running) {
    return <span className="tabular-nums">Took {clock(elapsed)}</span>;
  }

  const typical = seoEnabled ? TYPICAL_RUN_SECONDS.withSeo : TYPICAL_RUN_SECONDS.geo;
  const overrunning = elapsed > typical * 1.5;
  return (
    <span className="tabular-nums">
      {clock(elapsed)}
      <span className="text-muted-foreground">
        {" "}of approx. {Math.round(typical / 60)} min
      </span>
      {overrunning && (
        <span className="text-amber-600"> · taking longer than usual</span>
      )}
    </span>
  );
}

export function geoTone(stage: GeoStage) {
  return stage ? GEO_STAGE_LABELS[stage].tone : "text-muted-foreground";
}

/** "58 · Preferred" as a compact inline badge for tables. */
export function GeoBadge({ score, stage }: { score: number | null; stage: GeoStage }) {
  if (score === null || !stage) return <span className="text-muted-foreground">—</span>;
  return (
    <span className="inline-flex items-center gap-2">
      <span className="text-base font-semibold tabular-nums">{score}</span>
      <Badge variant="outline" className={cn("font-medium", geoTone(stage))}>{GEO_STAGE_LABELS[stage].label}</Badge>
    </span>
  );
}

/** The big score ring on the report and detail headers. */
export function GeoRing({ score, stage, size = 128 }: { score: number | null; stage: GeoStage; size?: number }) {
  const value = score ?? 0;
  const r = (size - 12) / 2;
  const c = 2 * Math.PI * r;
  const tone = stage === "absent" ? "hsl(var(--destructive))"
    : stage === "present" ? "#d97706"
    : stage === "preferred" ? "hsl(var(--primary))"
    : stage === "default" ? "#059669" : "hsl(var(--muted-foreground))";
  return (
    <div className="relative flex-none" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} stroke="hsl(var(--muted))" strokeWidth="10" fill="none" />
        <circle
          cx={size / 2} cy={size / 2} r={r} stroke={tone} strokeWidth="10" fill="none" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - value / 100)}
          className="transition-all duration-700"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-4xl font-bold tabular-nums leading-none">{score ?? "—"}</span>
        <span className={cn("text-xs font-semibold uppercase tracking-wide mt-1", geoTone(stage))}>
          {stage ? GEO_STAGE_LABELS[stage].label : "not scored"}
        </span>
      </div>
    </div>
  );
}

/** Status pill for the leads table. */
export function StatusBadge({ status, stageLabel }: { status: AuditStatus; stageLabel?: string }) {
  if (status === "DONE") return <Badge className="bg-emerald-600 hover:bg-emerald-600">Published</Badge>;
  if (status === "FAIL") return <Badge variant="destructive">Failed</Badge>;
  return (
    <Badge variant="secondary" className="gap-1">
      <Loader2 className="h-3 w-3 animate-spin" />
      {status === "INIT" ? "Queued" : stageLabel || "Processing"}
    </Badge>
  );
}

/** The six stages with the current one live, as on the prototype's audit-run screen. */
export function StageStrip({
  status, stage, stageDetail, seoEnabled,
}: {
  status: AuditStatus;
  stage: AuditStage;
  stageDetail: Record<string, Record<string, unknown>>;
  seoEnabled: boolean;
}) {
  const currentIdx = AUDIT_STAGES.findIndex((s) => s.key === stage);
  const detailFor = (key: string) => {
    const d = stageDetail?.[key] || {};
    if (key === "serp" && (d.skipped || !seoEnabled)) return "skipped on this plan";
    // The engines stage counts answers (prompts × engines × runs), not engines — say so.
    if (key === "engines" && typeof d.done === "number" && typeof d.total === "number") return `${d.done} / ${d.total} answers`;
    if (typeof d.done === "number" && typeof d.total === "number") return `${d.done} / ${d.total}`;
    if (key === "profile" && d.source) return d.source === "site" ? "site read" : "from public knowledge";
    if (key === "crawl" && d.skipped) return "skipped";
    if (key === "crawl" && d.error) return "site could not be read";
    if (key === "crawl" && typeof d.pages === "number") {
      // A page that needed a rendering fetch is itself a finding: if our reader
      // could not see it, an AI crawler probably cannot either.
      const rescued = typeof d.pages_rescued === "number" ? d.pages_rescued : 0;
      return `${d.pages} pages sampled${rescued ? ` · ${rescued} needed rendering` : ""}`;
    }
    if (key === "prompts" && typeof d.count === "number") return `${d.count} prompts`;
    if (key === "score" && typeof d.geo_score === "number") return `GEO ${d.geo_score}`;
    return "";
  };
  return (
    <ol className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
      {AUDIT_STAGES.map((s, i) => {
        const done = status === "DONE" || i < currentIdx;
        const active = status !== "DONE" && status !== "FAIL" && i === currentIdx;
        const failed = status === "FAIL" && i === currentIdx;
        const skipped = (s.key === "serp" && (!seoEnabled || stageDetail?.serp?.skipped)) || (s.key === "crawl" && Boolean(stageDetail?.crawl?.skipped));
        return (
          <li
            key={s.key}
            className={cn(
              "rounded-lg border p-3 text-sm",
              active && "border-primary bg-primary/5",
              failed && "border-destructive bg-destructive/5",
              !active && !failed && "border-border",
            )}
          >
            <div className="flex items-center gap-2 font-medium">
              <span className={cn(
                "flex h-5 w-5 items-center justify-center rounded-full text-[11px]",
                done && !skipped && "bg-emerald-600 text-white",
                skipped && "bg-muted text-muted-foreground",
                active && "bg-primary text-primary-foreground",
                failed && "bg-destructive text-destructive-foreground",
                !done && !active && !failed && !skipped && "bg-muted text-muted-foreground",
              )}>
                {failed ? <X className="h-3 w-3" /> : skipped ? <Minus className="h-3 w-3" /> : done ? <Check className="h-3 w-3" /> : active ? <Loader2 className="h-3 w-3 animate-spin" /> : i + 1}
              </span>
              <span className="truncate" title={s.label}>{s.short}</span>
            </div>
            <p className="mt-1 text-xs text-muted-foreground min-h-[1rem]">{detailFor(s.key)}</p>
            {/* What this stage is for, while it is the one running. Shown only
                on the live stage so the strip stays scannable once it is done. */}
            {active && <p className="mt-1.5 text-xs leading-snug text-foreground/70">{s.does}</p>}
          </li>
        );
      })}
    </ol>
  );
}
