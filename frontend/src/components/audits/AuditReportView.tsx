/**
 * The audit report body — what a prospect sees on the public link and what an
 * admin previews in the app. Renders `PublicAudit` (or anything with the same
 * fields) so the two routes cannot drift.
 *
 * Sections follow the prototype: headline tiles → per-engine table → prompt
 * evidence → who is named instead → who controls the citations →
 * Findable / Cited / Chosen measures → quick wins → methodology.
 */
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";
import {
  AUDIT_COUNTRIES, GAP_LABELS, GEO_STAGE_LABELS,
  type CwvRating, type EngineOutcome, type HealthPriority, type IssueSeverity, type PublicAudit, type ReportCrawl, type ReportMeasure,
} from "@/types/audit";
import { AlertTriangle, Check, Info, X } from "lucide-react";
import { GeoRing, fmtDate, pct } from "./AuditBits";

const OUTCOME: Record<EngineOutcome, { dot: string; label: string }> = {
  cited: { dot: "bg-emerald-500", label: "cited" },
  mentioned: { dot: "bg-amber-500", label: "mentioned" },
  absent: { dot: "bg-destructive", label: "absent" },
  failed: { dot: "bg-muted-foreground/40", label: "no answer" },
};

const PILLARS: { key: ReportMeasure["pillar"]; title: string; question: string }[] = [
  { key: "findable", title: "Findable", question: "Can the engines reach and read you" },
  { key: "cited", title: "Cited", question: "Are you the source the engines use" },
  { key: "chosen", title: "Chosen", question: "Are you the answer the engines give" },
];

function Tile({ label, value, sub }: { label: string; value: React.ReactNode; sub?: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border p-4">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-bold tabular-nums">{value}</p>
      {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
    </div>
  );
}

function HeatCell({ rate, sub, strong }: { rate: number | null; sub: string; strong?: boolean }) {
  const tone = rate === null ? "bg-muted text-muted-foreground"
    : rate >= 67 ? "bg-emerald-500/20 text-emerald-700"
    : rate >= 34 ? "bg-amber-500/20 text-amber-700"
    : "bg-destructive/10 text-destructive";
  return (
    <div className={cn("rounded-md py-2 px-1", tone, strong && "font-semibold")}>
      <span className="block text-sm tabular-nums">{rate === null ? "—" : `${rate}%`}</span>
      <span className="block text-[10px] opacity-70 tabular-nums">{sub}</span>
    </div>
  );
}

function Bar({ label, value, max, you }: { label: string; value: number; max: number; you?: boolean }) {
  return (
    <div>
      <div className="flex justify-between text-xs mb-1 gap-2">
        <span className={cn("truncate", you ? "font-semibold" : "text-muted-foreground")} title={label}>
          {label}{you && <span className="ml-1 text-primary">· you</span>}
        </span>
        <span className="font-medium tabular-nums">{value}</span>
      </div>
      <div className="h-1.5 rounded-full bg-muted overflow-hidden">
        <div className={cn("h-full rounded-full", you ? "gradient-primary" : "bg-muted-foreground/40")}
             style={{ width: `${max ? Math.max((100 * value) / max, 2) : 0}%` }} />
      </div>
    </div>
  );
}

const PRIORITY: Record<HealthPriority, { label: string; cls: string }> = {
  on_track: { label: "On track", cls: "bg-emerald-500/15 text-emerald-700 border-emerald-500/30" },
  important: { label: "Important", cls: "bg-amber-500/15 text-amber-700 border-amber-500/30" },
  critical: { label: "Critical", cls: "bg-destructive/10 text-destructive border-destructive/30" },
  not_measured: { label: "Not measured", cls: "bg-muted text-muted-foreground border-border" },
};
const SEVERITY: Record<IssueSeverity, { label: string; cls: string; Icon: typeof X }> = {
  critical: { label: "Critical", cls: "text-destructive", Icon: X },
  warning: { label: "Warning", cls: "text-amber-600", Icon: AlertTriangle },
  info: { label: "Info", cls: "text-muted-foreground", Icon: Info },
};
const CWV_RATING: Record<CwvRating, { label: string; cls: string }> = {
  good: { label: "Good", cls: "text-emerald-600" },
  needs_improvement: { label: "Needs improvement", cls: "text-amber-600" },
  poor: { label: "Poor", cls: "text-destructive" },
};
const scoreTone = (s: number | null | undefined) =>
  s === null || s === undefined ? "text-muted-foreground" : s >= 80 ? "text-emerald-600" : s >= 60 ? "text-amber-600" : "text-destructive";

/** Website Health scorecard: eight weighted categories → one site score. */
function HealthScorecard({ health }: { health: NonNullable<ReportCrawl["health"]> }) {
  return (
    <Card className="border border-border">
      <CardContent className="p-4">
        <div className="flex items-baseline justify-between gap-3">
          <p className="text-sm font-semibold">Website health scorecard</p>
          <p className="text-sm">
            <span className={cn("text-2xl font-bold tabular-nums", scoreTone(health.score))}>{health.score ?? "—"}</span>
            <span className="text-xs text-muted-foreground"> / 100</span>
          </p>
        </div>
        <p className="text-xs text-muted-foreground mb-3">Weighted across the categories below; unmeasured categories drop out of the weighting.</p>
        <ul className="space-y-2">
          {health.categories.map((c) => (
            <li key={c.key} className="grid grid-cols-[1fr_auto] items-center gap-x-3 gap-y-0.5">
              <div className="flex items-center justify-between gap-2 text-sm">
                <span className="font-medium">{c.label} <span className="text-[11px] text-muted-foreground font-normal">· {c.weight}%</span></span>
                <span className={cn("tabular-nums font-semibold", scoreTone(c.score))}>{c.score ?? "—"}</span>
              </div>
              <span className={cn("rounded-full border px-2 py-0.5 text-[10px] font-semibold whitespace-nowrap", PRIORITY[c.priority].cls)}>{PRIORITY[c.priority].label}</span>
              <div className="h-1.5 rounded-full bg-muted overflow-hidden col-span-2">
                <div className={cn("h-full rounded-full", c.score === null ? "bg-transparent" : c.score >= 80 ? "bg-emerald-500" : c.score >= 60 ? "bg-amber-500" : "bg-destructive")}
                     style={{ width: `${c.score ?? 0}%` }} />
              </div>
              <p className="text-[11px] text-muted-foreground col-span-2 truncate" title={c.detail}>{c.detail}</p>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

function CwvCard({ cwv }: { cwv: NonNullable<ReportCrawl["cwv"]> }) {
  const metric = (label: string, value: number | null, unit: string, rating?: CwvRating | null) => (
    <div className="rounded-lg border border-border p-3">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 text-xl font-bold tabular-nums">{value === null ? "—" : `${value}${unit}`}</p>
      <p className={cn("text-xs font-medium", rating ? CWV_RATING[rating].cls : "text-muted-foreground")}>{rating ? CWV_RATING[rating].label : "no data"}</p>
    </div>
  );
  return (
    <Card className="border border-border">
      <CardContent className="p-4">
        <div className="flex items-baseline justify-between gap-3">
          <p className="text-sm font-semibold">Core Web Vitals</p>
          <p className="text-xs text-muted-foreground">{cwv.source === "field" ? "real-user data (CrUX, p75)" : "lab data (Lighthouse)"} · mobile</p>
        </div>
        <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-3">
          {metric("LCP", cwv.lcp_ms, " ms", cwv.lcp_ms_rating)}
          {metric("CLS", cwv.cls, "", cwv.cls_rating)}
          {metric("INP", cwv.inp_ms, " ms", cwv.inp_ms_rating)}
          <div className="rounded-lg border border-border p-3">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">CWV score</p>
            <p className={cn("mt-1 text-xl font-bold tabular-nums", scoreTone(cwv.score))}>{cwv.score ?? "—"}</p>
            <p className="text-xs text-muted-foreground">
              {cwv.performance_score !== null ? `Lighthouse performance ${cwv.performance_score}` : "slow pages are crawled less often"}
              {cwv.mobile_friendly === false && <span className="text-destructive"> · not mobile-friendly</span>}
              {cwv.mobile_friendly === true && <span className="text-emerald-600"> · mobile-friendly</span>}
            </p>
          </div>
        </div>
        {cwv.pages && cwv.pages.length > 1 && (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-xs">
              <thead><tr className="text-muted-foreground"><th className="text-left font-medium py-1">Page</th><th className="text-right font-medium">LCP</th><th className="text-right font-medium">CLS</th><th className="text-right font-medium">INP</th><th className="text-right font-medium">Score</th></tr></thead>
              <tbody>
                {cwv.pages.map((p) => {
                  let path = p.url; try { path = new URL(p.url).pathname || "/"; } catch { /* keep */ }
                  return (
                    <tr key={p.url} className="border-t border-border">
                      <td className="py-1 max-w-[260px] truncate" title={p.url}>{path}</td>
                      <td className={cn("text-right tabular-nums", p.lcp_ms_rating ? CWV_RATING[p.lcp_ms_rating].cls : "")}>{p.lcp_ms ?? "—"}</td>
                      <td className={cn("text-right tabular-nums", p.cls_rating ? CWV_RATING[p.cls_rating].cls : "")}>{p.cls ?? "—"}</td>
                      <td className={cn("text-right tabular-nums", p.inp_ms_rating ? CWV_RATING[p.inp_ms_rating].cls : "")}>{p.inp_ms ?? "—"}</td>
                      <td className={cn("text-right tabular-nums font-semibold", scoreTone(p.score))}>{p.score ?? "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {cwv.site_score !== null && cwv.site_score !== undefined && <p className="text-[11px] text-muted-foreground mt-1">Average across the pages tested: {cwv.site_score}</p>}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function BacklinksCard({ b }: { b: NonNullable<ReportCrawl["backlinks"]> }) {
  const tile = (label: string, value: string, sub: string) => (
    <div className="rounded-lg border border-border p-3">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 text-xl font-bold tabular-nums">{value}</p>
      <p className="text-xs text-muted-foreground">{sub}</p>
    </div>
  );
  return (
    <Card className="border border-border">
      <CardContent className="p-4">
        <div className="flex items-baseline justify-between gap-3">
          <p className="text-sm font-semibold">Backlink authority</p>
          <p className="text-xs text-muted-foreground">third-party link index{b.first_seen ? ` · links since ${b.first_seen.slice(0, 4)}` : ""}</p>
        </div>
        <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-3">
          {tile("Authority score", b.authority_score === null ? "—" : `${b.authority_score}`, "how trusted the site is, 0-100")}
          {tile("Sites linking in", b.referring_domains.toLocaleString(), "unique websites that link to you")}
          {tile("Total backlinks", b.backlinks.toLocaleString(), b.dofollow_share !== null ? `${b.dofollow_share}% dofollow` : "all individual links")}
          {tile("Broken backlinks", b.broken_backlinks.toLocaleString(), "links to pages that no longer exist")}
        </div>
        <p className="text-xs text-muted-foreground mt-3">The links pointing at your site shape how much the engines trust and cite it. Broken backlinks are authority you already earned and can reclaim with a redirect.</p>
      </CardContent>
    </Card>
  );
}

const VERDICT: Record<string, { label: string; cls: string }> = {
  indexable: { label: "Indexable", cls: "text-emerald-600" },
  not_indexable: { label: "Not indexable", cls: "text-destructive" },
  canonicalised: { label: "Canonicalised elsewhere", cls: "text-amber-600" },
  redirected: { label: "Redirects", cls: "text-amber-600" },
  unknown: { label: "Could not check", cls: "text-muted-foreground" },
};

/** Indexability verdicts, security checks and sitemap health — the "can Google even see it" card. */
function IndexabilityCard({ crawl }: { crawl: ReportCrawl }) {
  const idx = crawl.indexability;
  const site = crawl.site || {};
  const sm = crawl.sitemap_health;
  const yesNo = (v: boolean | null | undefined, yes: string, no: string, unknown = "not checked") =>
    v === true ? <span className="text-emerald-600">{yes}</span> : v === false ? <span className="text-destructive">{no}</span> : <span className="text-muted-foreground">{unknown}</span>;
  return (
    <Card className="border border-border">
      <CardContent className="p-4">
        <p className="text-sm font-semibold mb-3">Indexability &amp; security</p>
        {idx && (
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mb-3">
            {(Object.keys(VERDICT) as (keyof typeof VERDICT)[]).map((k) => (
              <div key={k} className="rounded-lg border border-border p-2 text-center">
                <p className={cn("text-lg font-bold tabular-nums", VERDICT[k].cls)}>{idx[k as keyof typeof idx] ?? 0}</p>
                <p className="text-[10px] text-muted-foreground leading-tight">{VERDICT[k].label}</p>
              </div>
            ))}
          </div>
        )}
        <ul className="space-y-1.5 text-sm">
          <li className="flex justify-between gap-2"><span>http:// redirects to https://</span><span className="text-xs font-medium">{yesNo(site.http_redirects_to_https, "yes", "no — both versions reachable")}</span></li>
          <li className="flex justify-between gap-2"><span>HSTS header</span><span className="text-xs font-medium">{yesNo(site.hsts, "present", "missing", "unknown")}</span></li>
          <li className="flex justify-between gap-2"><span>SSL certificate</span><span className="text-xs font-medium">
            {site.ssl_error ? <span className="text-destructive">error on at least one page</span>
              : site.certificate ? <span className={site.certificate.days_left < 30 ? "text-destructive" : "text-emerald-600"}>expires {site.certificate.expires} ({site.certificate.days_left} days){site.certificate.issuer ? ` · ${site.certificate.issuer}` : ""}</span>
              : <span className="text-emerald-600">ok</span>}
          </span></li>
          {site.security_headers && (
            <li className="flex justify-between gap-2"><span>Security headers</span><span className="text-xs font-medium">
              {Object.values(site.security_headers).every(Boolean) ? <span className="text-emerald-600">all 4 present</span>
                : <span className="text-amber-600">{Object.values(site.security_headers).filter(Boolean).length} of 4 present</span>}
            </span></li>
          )}
          {(crawl.soft_404_pages ?? 0) > 0 && <li className="flex justify-between gap-2"><span>Soft 404 pages</span><span className="text-xs font-medium text-destructive">{crawl.soft_404_pages}</span></li>}
          {crawl.avg_html_kb !== null && crawl.avg_html_kb !== undefined && <li className="flex justify-between gap-2"><span>Average HTML weight</span><span className="text-xs font-medium">{crawl.avg_html_kb} KB{crawl.avg_scripts !== undefined ? ` · ${crawl.avg_scripts} scripts/page` : ""}</span></li>}
          {sm && sm.listed > 0 && (
            <li className="flex justify-between gap-2 border-t border-border pt-2 mt-2">
              <span>Sitemap health</span>
              <span className="text-xs font-medium text-right">
                {sm.listed.toLocaleString()} URLs listed · {sm.checked} checked ·{" "}
                <span className={sm.errors.length ? "text-destructive" : "text-emerald-600"}>{sm.errors.length} with problems</span>
                {sm.not_in_sitemap.length > 0 && <span className="text-muted-foreground"> · {sm.not_in_sitemap.length} crawled pages not listed</span>}
              </span>
            </li>
          )}
          {(crawl.redirect_chains ?? 0) > 0 && <li className="flex justify-between gap-2"><span>Redirect chains (2+ hops)</span><span className="text-xs font-medium text-amber-600">{crawl.redirect_chains} pages</span></li>}
          {(crawl.thin_pages ?? 0) > 0 && <li className="flex justify-between gap-2"><span>Thin content pages</span><span className="text-xs font-medium text-amber-600">{crawl.thin_pages}</span></li>}
          {crawl.duplicate_groups && crawl.duplicate_groups.length > 0 && (
            <li className="flex justify-between gap-2"><span>Near-duplicate page groups</span><span className="text-xs font-medium text-amber-600">{crawl.duplicate_groups.length} groups · {crawl.duplicate_groups.reduce((s, g) => s + g.length, 0)} pages</span></li>
          )}
          {crawl.hreflang_errors && crawl.hreflang_errors.length > 0 && <li className="flex justify-between gap-2"><span>hreflang errors</span><span className="text-xs font-medium text-amber-600">{crawl.hreflang_errors.length}</span></li>}
        </ul>
      </CardContent>
    </Card>
  );
}

function IssueHistory({ d }: { d: NonNullable<ReportCrawl["issue_delta"]> }) {
  const when = d.previous_completed_at ? fmtDate(d.previous_completed_at) : "the previous audit";
  return (
    <div className="mt-4 rounded-lg border border-border bg-muted/30 p-4">
      <p className="text-sm font-semibold">Since {when}</p>
      <p className="text-xs text-muted-foreground mb-2">
        {d.previous_total} issue types then · {d.current_total} now{d.previous_health !== null && d.previous_health !== undefined ? ` · health was ${d.previous_health}` : ""}
      </p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
        <div>
          <p className="text-xs font-semibold text-emerald-600 mb-1">Fixed ({d.fixed.length})</p>
          {d.fixed.length ? d.fixed.map((f) => <p key={f.key} className="text-xs">{f.label} <span className="text-muted-foreground">(was {f.was})</span></p>) : <p className="text-xs text-muted-foreground">—</p>}
        </div>
        <div>
          <p className="text-xs font-semibold text-destructive mb-1">New ({d.new.length})</p>
          {d.new.length ? d.new.map((f) => <p key={f.key} className="text-xs">{f.label} <span className="text-muted-foreground">({f.count})</span></p>) : <p className="text-xs text-muted-foreground">—</p>}
        </div>
        <div>
          <p className="text-xs font-semibold text-amber-600 mb-1">Changed ({d.changed.length})</p>
          {d.changed.length ? d.changed.map((f) => <p key={f.key} className="text-xs">{f.label} <span className="text-muted-foreground">{f.from} → {f.to}</span></p>) : <p className="text-xs text-muted-foreground">—</p>}
        </div>
      </div>
    </div>
  );
}

function LinkOpportunities({ ops, compact }: { ops: NonNullable<ReportCrawl["link_opportunities"]>; compact: boolean }) {
  const path = (u: string) => { try { return new URL(u).pathname || "/"; } catch { return u; } };
  const shown = compact ? ops.slice(0, 5) : ops;
  return (
    <div className="mt-4">
      <p className="text-sm font-semibold">Internal link opportunities</p>
      <p className="text-xs text-muted-foreground mb-2">Pages that talk about another page's topic but never link to it — add a contextual link.</p>
      <div className="overflow-x-auto rounded-lg border border-border">
        <Table>
          <TableHeader><TableRow><TableHead>Link from</TableHead><TableHead>To</TableHead><TableHead>Shared topic</TableHead></TableRow></TableHeader>
          <TableBody>
            {shown.map((o, i) => (
              <TableRow key={i}>
                <TableCell className="text-xs font-medium max-w-[280px] truncate" title={o.from}>{path(o.from)}</TableCell>
                <TableCell className="text-xs max-w-[280px] truncate" title={o.to}>{path(o.to)}</TableCell>
                <TableCell className="text-xs text-muted-foreground">{o.topic}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      {compact && ops.length > shown.length && <p className="text-xs text-muted-foreground mt-1">{ops.length - shown.length} more in the full report</p>}
    </div>
  );
}

function TechnicalIssues({ issues, compact }: { issues: NonNullable<ReportCrawl["technical_issues"]>; compact: boolean }) {
  const shown = compact ? issues.slice(0, 6) : issues;
  return (
    <div className="mt-4">
      <p className="text-sm font-semibold">Technical SEO issues</p>
      <p className="text-xs text-muted-foreground mb-2">
        {issues.filter((i) => i.severity === "critical").length} critical · {issues.filter((i) => i.severity === "warning").length} warnings · {issues.filter((i) => i.severity === "info").length} info — counted over the sampled pages · the CSV export lists every affected URL
      </p>
      {issues.length === 0 ? (
        <p className="text-sm text-emerald-600 flex items-center gap-1"><Check className="h-4 w-4" /> No on-page or technical issues found on the sampled pages.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Severity</TableHead><TableHead>Issue</TableHead><TableHead className="text-right">Pages</TableHead>
                <TableHead>Examples</TableHead><TableHead>Fix</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {shown.map((i) => {
                const s = SEVERITY[i.severity];
                return (
                  <TableRow key={i.key}>
                    <TableCell><span className={cn("inline-flex items-center gap-1 text-xs font-semibold", s.cls)}><s.Icon className="h-3.5 w-3.5" />{s.label}</span></TableCell>
                    <TableCell className="text-sm font-medium">{i.label}</TableCell>
                    <TableCell className="text-right tabular-nums text-sm">{i.count} / {i.of}</TableCell>
                    <TableCell className="text-xs text-muted-foreground max-w-[220px]">{i.examples.slice(0, 3).join(" · ")}</TableCell>
                    <TableCell className="text-xs max-w-[320px]">
                      <span className="font-medium">{i.action}.</span> <span className="text-muted-foreground">{i.fix}</span>
                      {i.snippet && <code className="mt-1 block rounded bg-muted px-1.5 py-1 text-[10px] leading-snug break-all">{i.snippet}</code>}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}
      {compact && issues.length > shown.length && <p className="text-xs text-muted-foreground mt-1">{issues.length - shown.length} more in the full report</p>}
    </div>
  );
}

function ContentPatterns({ patterns }: { patterns: NonNullable<ReportCrawl["content_patterns"]> }) {
  const tone = { present: "text-emerald-600", partial: "text-amber-600", missing: "text-destructive" } as const;
  const label = { present: "present", partial: "partly there", missing: "missing" } as const;
  return (
    <div className="mt-4">
      <p className="text-sm font-semibold">Winning content patterns</p>
      <p className="text-xs text-muted-foreground mb-2">The three page shapes AI engines cite most often, and whether your sampled pages use them.</p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {patterns.map((p) => (
          <div key={p.key} className="rounded-lg border border-border p-3">
            <p className="text-sm font-medium leading-snug">{p.title}</p>
            <p className={cn("text-xs font-semibold mt-1", tone[p.status])}>{label[p.status]} <span className="text-muted-foreground font-normal">· {p.evidence}</span></p>
            <p className="text-xs text-muted-foreground mt-2 leading-relaxed">{p.advice}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Small on-page flag list for one row of the page table. */
function PageFlags({ d }: { d: NonNullable<ReportCrawl["pages"][number]["details"]> }) {
  const flags: { text: string; bad: boolean }[] = [];
  if (d.noindex) flags.push({ text: "noindex", bad: true });
  if (d.status_code && d.status_code >= 400) flags.push({ text: `HTTP ${d.status_code}`, bad: true });
  if (d.title_length === 0) flags.push({ text: "no title", bad: true });
  if (d.description_length === 0) flags.push({ text: "no description", bad: false });
  if (d.h1_count === 0) flags.push({ text: "no H1", bad: false });
  if ((d.h1_count ?? 0) > 1) flags.push({ text: `${d.h1_count} H1s`, bad: false });
  if (d.canonical_status === "missing") flags.push({ text: "no canonical", bad: false });
  if (d.canonical_status === "mismatch") flags.push({ text: "canonical elsewhere", bad: false });
  if (d.mixed_content) flags.push({ text: "mixed content", bad: true });
  if (d.viewport === false) flags.push({ text: "no viewport", bad: false });
  if (d.redirects) flags.push({ text: `${d.redirects} redirect${d.redirects > 1 ? "s" : ""}`, bad: (d.redirects ?? 0) > 1 });
  if (d.index?.verdict === "not_indexable" && d.index.reason.startsWith("blocked")) flags.push({ text: "robots blocked", bad: true });
  if (d.x_robots && d.x_robots.toLowerCase().includes("noindex")) flags.push({ text: "X-Robots noindex", bad: true });
  if (d.thin) flags.push({ text: "thin", bad: false });
  if (d.title_issue) flags.push({ text: `title ${d.title_issue}`, bad: false });
  if (d.description_issue) flags.push({ text: `description ${d.description_issue}`, bad: false });
  if (d.json_ld_invalid) flags.push({ text: "invalid JSON-LD", bad: false });
  if (d.rich_result_blockers?.length) flags.push({ text: "schema incomplete", bad: false });
  if (d.heading_issues?.length) flags.push({ text: "headings", bad: false });
  if (d.has_params && d.canonical_status !== "ok") flags.push({ text: "param URL", bad: false });
  if (d.soft_404) flags.push({ text: "soft 404", bad: true });
  if (d.meta_refresh) flags.push({ text: "meta refresh", bad: false });
  if ((d.html_bytes ?? 0) > 300000) flags.push({ text: `${Math.round((d.html_bytes ?? 0) / 1000)} KB HTML`, bad: false });
  if (!flags.length) return <span className="text-xs text-emerald-600">clean</span>;
  return (
    <span className="flex flex-wrap gap-1">
      {flags.map((f) => (
        <span key={f.text} className={cn("rounded border px-1 py-px text-[10px]", f.bad ? "border-destructive/30 text-destructive" : "border-amber-500/30 text-amber-700")}>{f.text}</span>
      ))}
    </span>
  );
}

function CrawlSection({ crawl, compact, intro }: { crawl: ReportCrawl; compact: boolean; intro?: string }) {
  const pages = compact ? crawl.pages.slice(0, 8) : crawl.pages;
  const fmtPct = (v: number | null | undefined) => (v === null || v === undefined ? "—" : `${v}%`);
  const hasDetails = crawl.pages.some((p) => p.details && Object.keys(p.details).length > 0);
  return (
    <section>
      <h3 className="text-lg font-semibold">Website health</h3>
      <Intro text={intro} />
      <p className="text-sm text-muted-foreground">
        {crawl.pages_sampled} of your pages sampled{crawl.urls_discovered ? ` (${crawl.urls_discovered} discovered)` : ""} · what the engines can read, and how citable it is
      </p>

      {crawl.health && (
        <div className="mt-3 grid grid-cols-1 lg:grid-cols-2 gap-6">
          <HealthScorecard health={crawl.health} />
          <div className="space-y-6">
            {crawl.indexability ? <IndexabilityCard crawl={crawl} /> : null}
            {crawl.backlinks ? <BacklinksCard b={crawl.backlinks} /> : null}
            {crawl.cwv ? <CwvCard cwv={crawl.cwv} /> : null}
            {crawl.content_patterns && crawl.content_patterns.length > 0 && !crawl.cwv && !crawl.backlinks && !crawl.indexability && (
              <Card className="border border-border"><CardContent className="p-4 pt-0"><ContentPatterns patterns={crawl.content_patterns} /></CardContent></Card>
            )}
          </div>
        </div>
      )}

      <div className="mt-3 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="border border-border">
          <CardContent className="p-4">
            <p className="text-sm font-semibold mb-3">AI crawler access</p>
            <ul className="space-y-2 text-sm">
              {crawl.bots.map((b) => (
                <li key={b.bot} className="flex items-center justify-between gap-2">
                  <span><span className="font-medium">{b.bot}</span> <span className="text-muted-foreground">· {b.engine}</span></span>
                  <span className={cn("inline-flex items-center gap-1 text-xs font-medium", b.allowed ? "text-emerald-600" : "text-destructive")}>
                    {b.allowed ? <Check className="h-3.5 w-3.5" /> : <X className="h-3.5 w-3.5" />}{b.allowed ? "allowed" : "blocked"}
                  </span>
                </li>
              ))}
              <li className="flex items-center justify-between gap-2 border-t border-border pt-2 mt-2">
                <span className="font-medium">robots.txt</span>
                <span className="text-xs text-muted-foreground">{crawl.robots_present ? "present" : "none (everything allowed)"}</span>
              </li>
              <li className="flex items-center justify-between gap-2">
                <span className="font-medium">sitemap.xml</span>
                <span className={cn("text-xs font-medium", crawl.sitemap_present ? "text-emerald-600" : "text-destructive")}>
                  {crawl.sitemap_present ? (crawl.sitemap_children ? `present · index with ${crawl.sitemap_children} child sitemaps` : "present") : "not found"}
                </span>
              </li>
              {crawl.link_check && crawl.link_check.checked > 0 && (
                <li className="flex items-center justify-between gap-2">
                  <span className="font-medium">Internal links checked</span>
                  <span className={cn("text-xs font-medium", crawl.link_check.broken ? "text-destructive" : "text-emerald-600")}>
                    {crawl.link_check.broken ? `${crawl.link_check.broken} of ${crawl.link_check.checked} broken` : `${crawl.link_check.checked} checked · none broken`}
                  </span>
                </li>
              )}
              <li className="flex items-center justify-between gap-2">
                <span className="font-medium">llms.txt</span>
                <span className="text-xs text-muted-foreground">{crawl.llms_txt ? "present" : "not detected · optional"}</span>
              </li>
            </ul>
          </CardContent>
        </Card>

        <Card className="border border-border">
          <CardContent className="p-4">
            <p className="text-sm font-semibold mb-3">Content &amp; schema signals</p>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
              <div><dt className="text-xs text-muted-foreground">Schema coverage</dt><dd className="font-medium tabular-nums">{fmtPct(crawl.schema_coverage)} of pages</dd></div>
              <div><dt className="text-xs text-muted-foreground">Key schema types</dt><dd className="font-medium">{crawl.recommended_types_present.length ? crawl.recommended_types_present.join(", ") : "none"}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Pages with author bio</dt><dd className="font-medium tabular-nums">{fmtPct(crawl.author_share)}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Outbound citations / page</dt><dd className="font-medium tabular-nums">{crawl.avg_external_links ?? "—"}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Avg word count</dt><dd className="font-medium tabular-nums">{crawl.avg_word_count?.toLocaleString() ?? "—"}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Question headings / tables</dt><dd className="font-medium tabular-nums">{fmtPct(crawl.question_heading_share)} / {fmtPct(crawl.table_share)}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Dated pages older than 12 months</dt><dd className="font-medium tabular-nums">{crawl.dated_pages ? `${crawl.stale_pages} of ${crawl.dated_pages}` : "no dates found"}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Latest update seen</dt><dd className="font-medium">{crawl.freshest ?? "—"}</dd></div>
              {crawl.avg_internal_links !== undefined && (
                <div><dt className="text-xs text-muted-foreground">Internal links / page</dt><dd className="font-medium tabular-nums">{crawl.avg_internal_links}{crawl.descriptive_anchor_share !== null && crawl.descriptive_anchor_share !== undefined ? ` · ${crawl.descriptive_anchor_share}% descriptive anchors` : ""}</dd></div>
              )}
              {crawl.person_schema_share !== undefined && (
                <div><dt className="text-xs text-muted-foreground">Person schema / credentials</dt><dd className="font-medium tabular-nums">{fmtPct(crawl.person_schema_share)} / {fmtPct(crawl.credential_share)} of pages</dd></div>
              )}
              {crawl.schema_gaps && crawl.schema_gaps.length > 0 && (
                <div className="col-span-2"><dt className="text-xs text-muted-foreground">Schema fields missing</dt><dd className="text-xs">{crawl.schema_gaps.slice(0, 3).map((g) => `${g.gap} (${g.pages})`).join(" · ")}</dd></div>
              )}
            </dl>
          </CardContent>
        </Card>
      </div>

      {crawl.issue_delta && <IssueHistory d={crawl.issue_delta} />}
      {crawl.technical_issues && <TechnicalIssues issues={crawl.technical_issues} compact={compact} />}
      {crawl.link_opportunities && crawl.link_opportunities.length > 0 && <LinkOpportunities ops={crawl.link_opportunities} compact={compact} />}
      {crawl.content_patterns && crawl.content_patterns.length > 0 && (crawl.cwv || crawl.backlinks || crawl.indexability) && <ContentPatterns patterns={crawl.content_patterns} />}

      <div className="mt-4 overflow-x-auto rounded-lg border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Page</TableHead><TableHead className="text-right">Words</TableHead><TableHead>Schema</TableHead>
              <TableHead>Author</TableHead><TableHead className="text-right">Citations</TableHead><TableHead>Updated</TableHead>
              {hasDetails && <TableHead className="text-right">Int. links</TableHead>}
              {hasDetails && <TableHead className="text-right">Depth</TableHead>}
              {hasDetails && <TableHead>On-page</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {pages.map((p) => {
              let path = p.url;
              try { path = new URL(p.url).pathname || "/"; } catch { /* keep raw */ }
              return (
                <TableRow key={p.url}>
                  <TableCell className="max-w-[320px]">
                    <span className="block truncate font-medium" title={p.url}>{path}</span>
                    {!p.fetched && <span className="text-xs text-destructive">could not be read</span>}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{p.fetched ? p.word_count.toLocaleString() : "—"}</TableCell>
                  <TableCell className="text-xs text-muted-foreground max-w-[220px] truncate" title={p.schema_types.join(", ")}>{p.schema_types.join(", ") || (p.fetched ? "none" : "—")}</TableCell>
                  <TableCell className="text-xs">{p.author ? <span className="text-emerald-600">{p.author}</span> : <span className="text-muted-foreground">—</span>}</TableCell>
                  <TableCell className="text-right tabular-nums">{p.fetched ? p.external_links : "—"}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">{p.last_modified ?? "—"}</TableCell>
                  {hasDetails && <TableCell className="text-right tabular-nums">{p.details?.internal_links ?? "—"}</TableCell>}
                  {hasDetails && <TableCell className="text-right tabular-nums">{p.details?.depth ?? "—"}</TableCell>}
                  {hasDetails && <TableCell>{p.details && Object.keys(p.details).length ? <PageFlags d={p.details} /> : <span className="text-xs text-muted-foreground">—</span>}</TableCell>}
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
      {compact && crawl.pages.length > pages.length && (
        <p className="text-xs text-muted-foreground mt-2">{crawl.pages.length - pages.length} more pages in the full report</p>
      )}
    </section>
  );
}

/** One-paragraph intro under a section heading, when the executive summary wrote one. */
function Intro({ text }: { text?: string }) {
  if (!text) return null;
  return <p className="text-sm leading-relaxed mt-1 mb-2 border-l-2 border-primary/40 pl-3">{text}</p>;
}

function summarySentence(a: PublicAudit) {
  const r = a.report;
  if (!r) return "";
  const stage = a.geo_stage ? GEO_STAGE_LABELS[a.geo_stage].label : "unscored";
  const engines = r.geo.engines;
  const weakest = engines.filter((e) => e.answered).sort((x, y) => x.mention_rate - y.mention_rate)[0];
  const parts = [
    `${a.brand_name || a.host} is ${stage}: mentioned on ${a.appearances} of ${a.total_runs} answers and cited on ${a.cited_runs}.`,
  ];
  if (weakest && weakest.top_rival && weakest.top_rival_mentions > 0 && weakest.mention_rate < 1) {
    parts.push(`It is weakest on ${weakest.platform}, where ${weakest.top_rival} is named ${weakest.top_rival_mentions}× and ${a.brand_name || "the brand"} on ${Math.round(weakest.mention_rate * 100)}% of prompts.`);
  }
  if (r.seo && r.seo.keywords_total) {
    parts.push(`On Google it ranks top-10 for ${r.seo.top10} of ${r.seo.keywords_total} discovered keywords.`);
  }
  return parts.join(" ");
}

export function AuditReportView({ audit, compact = false }: { audit: PublicAudit; compact?: boolean }) {
  const r = audit.report;
  if (!r) return null;
  const country = AUDIT_COUNTRIES.find((c) => c.code === audit.country)?.name || audit.country.toUpperCase();
  const engines = r.geo.engines;
  const platforms = engines.map((e) => e.platform);
  // Top six by mentions, but the brand's own row is always shown so a low
  // share reads as "you are here", not as an omission.
  const sovTop = r.geo.share_of_voice.slice(0, 6);
  const you = r.geo.share_of_voice.find((s) => s.is_you);
  const sov = you && !sovTop.includes(you) ? [...sovTop.slice(0, 5), you] : sovTop;
  const sovMax = Math.max(1, ...sov.map((s) => s.mentions));
  const ctrl = r.geo.citation_control;
  const measuresBy = (p: ReportMeasure["pillar"]) => r.measures.filter((m) => m.pillar === p);
  const evidence = compact ? r.geo.evidence.slice(0, 6) : r.geo.evidence;

  return (
    <div className="space-y-8">
      {/* ---- header ---- */}
      <div className="flex flex-wrap items-start gap-6">
        <GeoRing score={audit.geo_score} stage={audit.geo_stage} />
        <div className="flex-1 min-w-[260px]">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            AI visibility audit · {fmtDate(audit.completed_at)}
          </p>
          <h2 className="text-3xl font-bold tracking-tight mt-1">{audit.brand_name || audit.host}</h2>
          <p className="text-sm text-muted-foreground mt-1">
            {audit.host}{audit.industry ? ` · ${audit.industry}` : ""} · {country}
            {audit.competitors.length > 0 && <> · vs {audit.competitors.map((c) => c.name).join(", ")}</>}
          </p>
          <p className="mt-3 text-sm leading-relaxed">{r.summary?.headline || summarySentence(audit)}</p>
        </div>
      </div>

      {/* ---- executive summary ---- */}
      {r.summary && r.summary.key_findings.length > 0 && (
        <section className="rounded-xl border border-border bg-muted/30 p-5">
          <div className="flex items-baseline justify-between gap-2">
            <h3 className="text-base font-semibold">Key findings</h3>
            <span className="text-[11px] text-muted-foreground">{r.summary.source === "llm" ? "written from the audit's numbers" : "computed from the audit's numbers"}</span>
          </div>
          <ol className="mt-2 space-y-1.5">
            {r.summary.key_findings.map((f, i) => (
              <li key={i} className="flex gap-3 text-sm">
                <span className="flex h-5 w-5 flex-none items-center justify-center rounded-full bg-primary/10 text-primary text-xs font-semibold">{i + 1}</span>
                <span className="leading-snug">{f}</span>
              </li>
            ))}
          </ol>
        </section>
      )}

      {/* ---- headline tiles ---- */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <Tile label="GEO score" value={audit.geo_score ?? "—"}
              sub={audit.geo_stage ? `${GEO_STAGE_LABELS[audit.geo_stage].label} · ${GEO_STAGE_LABELS[audit.geo_stage].range}` : ""} />
        <Tile label="AI appearances" value={`${audit.appearances} / ${audit.total_runs}`} sub="answers naming you" />
        <Tile label="Cited" value={`${audit.cited_runs} / ${audit.total_runs}`} sub="answers linking your site" />
        <Tile label="Share of voice" value={pct(audit.share_of_voice)} sub="of all brand mentions" />
        <Tile label="SEO visibility" value={audit.seo_visibility === null ? "—" : Number(audit.seo_visibility).toFixed(1)}
              sub={r.seo ? `top-10 on ${r.seo.top10} / ${r.seo.keywords_total}` : "not measured"} />
        <Tile label="Engines" value={`${audit.engines_preferred} / ${audit.engines_total}`} sub="prefer you (>50% of prompts)" />
      </div>

      {/* ---- per engine ---- */}
      <section>
        <h3 className="text-lg font-semibold">GEO audit</h3>
        <Intro text={r.summary?.sections?.geo} />
        <p className="text-sm text-muted-foreground">
          {r.config?.prompt_count ?? r.geo.evidence.length} buyer prompts, each asked {r.geo.runs_per_prompt && r.geo.runs_per_prompt > 1 ? `${r.geo.runs_per_prompt}×` : "once"} on {engines.length} engine{engines.length === 1 ? "" : "s"} · {r.geo.runs_answered} of {r.geo.runs_total} answers read
        </p>
        <div className="mt-3 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {engines.map((e) => (
            <div key={e.platform} className={cn("rounded-lg border p-3", e.preferred ? "border-emerald-600/40" : "border-border")}>
              <p className="font-medium text-sm">{e.platform}</p>
              <p className="text-xs text-muted-foreground mt-1">cited {e.cited}/{e.answered}{e.avg_position ? ` · avg pos ${e.avg_position}` : ""}</p>
              <p className="text-xs mt-1">
                {e.top_rival && e.top_rival_mentions > 0
                  ? <span className="text-muted-foreground">{e.top_rival} {e.top_rival_mentions}×</span>
                  : <span className="text-emerald-600">no rival named</span>}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* ---- prompt evidence ---- */}
      <section>
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h3 className="text-lg font-semibold">Prompt evidence{r.geo.gap_counts && (
            <span className="ml-3 text-sm font-normal text-muted-foreground">
              {(Object.keys(GAP_LABELS) as (keyof typeof GAP_LABELS)[]).filter((k) => r.geo.gap_counts?.[k]).map((k) => `${r.geo.gap_counts?.[k]} ${GAP_LABELS[k].label.toLowerCase()}`).join(" · ")}
            </span>
          )}</h3>
          <p className="text-xs text-muted-foreground flex items-center gap-3">
            {(Object.keys(OUTCOME) as EngineOutcome[]).map((k) => (
              <span key={k} className="inline-flex items-center gap-1">
                <span className={cn("h-2 w-2 rounded-full", OUTCOME[k].dot)} />{OUTCOME[k].label}
              </span>
            ))}
          </p>
        </div>
        <div className="mt-3 overflow-x-auto rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>What buyers ask</TableHead>
                <TableHead className="w-24">Stage</TableHead>
                {platforms.map((p) => <TableHead key={p} className="w-16 text-center text-xs">{p.replace("Google ", "")}</TableHead>)}
                <TableHead className="w-28">Top competitor</TableHead>
                <TableHead>Cited instead of you</TableHead>
                <TableHead className="w-28">Gap type</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {evidence.map((ev) => (
                <TableRow key={ev.prompt_index}>
                  <TableCell className="font-medium">{ev.prompt_text}</TableCell>
                  <TableCell className="capitalize text-muted-foreground">{ev.funnel_stage || "—"}</TableCell>
                  {platforms.map((p) => {
                    const o = ev.engines[p];
                    return (
                      <TableCell key={p} className="text-center">
                        <span title={o ? OUTCOME[o].label : "not asked"} className={cn("inline-block h-2.5 w-2.5 rounded-full", o ? OUTCOME[o].dot : "bg-muted")} />
                      </TableCell>
                    );
                  })}
                  <TableCell className="text-xs text-muted-foreground">{ev.top_competitor || "—"}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">{ev.cited_instead.join(" · ") || "—"}</TableCell>
                  <TableCell>
                    {ev.gap_type ? (
                      <span className={cn("text-xs font-medium", GAP_LABELS[ev.gap_type].tone)} title={GAP_LABELS[ev.gap_type].hint}>{GAP_LABELS[ev.gap_type].label}</span>
                    ) : "—"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        {compact && r.geo.evidence.length > evidence.length && (
          <p className="text-xs text-muted-foreground mt-2">{r.geo.evidence.length - evidence.length} more prompts in the full report</p>
        )}
      </section>

      {/* ---- who is named / who is cited ---- */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="border border-border">
          <CardContent className="p-4">
            <p className="text-sm font-semibold mb-3">Who the engines name instead</p>
            <div className="space-y-2.5">
              {sov.map((s) => <Bar key={s.name} label={s.name} value={s.mentions} max={sovMax} you={s.is_you} />)}
            </div>
          </CardContent>
        </Card>
        <Card className="border border-border">
          <CardContent className="p-4">
            <p className="text-sm font-semibold mb-3">Who controls the citations</p>
            <div className="flex h-3 rounded-full overflow-hidden bg-muted">
              <div className="gradient-primary" style={{ width: `${ctrl.owned}%` }} title={`Owned ${ctrl.owned}%`} />
              <div className="bg-amber-500" style={{ width: `${ctrl.competitor}%` }} title={`Competitor ${ctrl.competitor}%`} />
              <div className="bg-muted-foreground/40" style={{ width: `${ctrl.third_party}%` }} title={`Third party ${ctrl.third_party}%`} />
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Owned {ctrl.owned}% · Competitor {ctrl.competitor}% · Third party {ctrl.third_party}% · {ctrl.total_citations} citations
            </p>
            {ctrl.top_sources.length > 0 && (
              <p className="text-xs mt-3">
                <span className="text-muted-foreground">Top sources: </span>
                {ctrl.top_sources.slice(0, 5).map((s) => `${s.host} (${s.count})`).join(" · ")}
              </p>
            )}
          </CardContent>
        </Card>
      </div>


      {/* ---- funnel x engine heatmap ---- */}
      {r.geo.funnel && (
        <section>
          <h3 className="text-lg font-semibold">Funnel stage heatmap</h3>
          <p className="text-sm text-muted-foreground">How often you are named, by buyer stage and engine (% of answers)</p>
          <div className="mt-3 overflow-x-auto rounded-lg border border-border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-40">Stage</TableHead>
                  {r.geo.funnel.platforms.map((p) => <TableHead key={p} className="text-center">{p.replace("Google ", "")}</TableHead>)}
                  <TableHead className="text-center">All engines</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {r.geo.funnel.stages.map((stage) => {
                  const total = r.geo.funnel!.by_stage[stage];
                  return (
                    <TableRow key={stage}>
                      <TableCell>
                        <span className="font-medium">{r.geo.funnel!.labels[stage]}</span>
                        <span className="block text-xs text-muted-foreground">{total.prompts} prompt{total.prompts === 1 ? "" : "s"}</span>
                      </TableCell>
                      {r.geo.funnel!.platforms.map((p) => {
                        const cell = r.geo.funnel!.cells[stage][p];
                        return <TableCell key={p} className="text-center p-1"><HeatCell rate={cell.rate} sub={cell.asked ? `${cell.mentioned}/${cell.asked}` : "—"} /></TableCell>;
                      })}
                      <TableCell className="text-center p-1"><HeatCell rate={total.rate} sub={total.asked ? `${total.mentioned}/${total.asked}` : "—"} strong /></TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </section>
      )}

      {/* ---- competitor matrix ---- */}
      {r.geo.competitors && r.geo.competitors.rows.length > 1 && (
        <section>
          <h3 className="text-lg font-semibold">Competitor matrix</h3>
          <Intro text={r.summary?.sections?.competitors} />
          <p className="text-sm text-muted-foreground">Every brand the engines named across the prompts — how many prompts it ranks in, and its average order of mention (1 = named first)</p>
          <div className="mt-3 overflow-x-auto rounded-lg border border-border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Brand</TableHead><TableHead className="text-right">Prompts ranked</TableHead><TableHead className="text-right">Share</TableHead>
                  <TableHead className="text-right">Avg position</TableHead><TableHead className="text-center">TOFU</TableHead><TableHead className="text-center">MOFU</TableHead><TableHead className="text-center">BOFU</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {r.geo.competitors.rows.map((c) => (
                  <TableRow key={c.name} className={cn(c.is_you && "bg-primary/5")}>
                    <TableCell className="font-medium">{c.name}{c.is_you && <span className="ml-1 text-xs text-primary">· you</span>}</TableCell>
                    <TableCell className="text-right tabular-nums">{c.prompts_ranked} / {c.prompts_total}</TableCell>
                    <TableCell className="text-right tabular-nums">{c.share}%</TableCell>
                    <TableCell className="text-right tabular-nums">{c.avg_position ?? "—"}</TableCell>
                    {["top", "middle", "bottom"].map((s) => (
                      <TableCell key={s} className="text-center text-xs tabular-nums text-muted-foreground">
                        {c.stages[s]?.of ? `${c.stages[s].ranked}/${c.stages[s].of}` : "—"}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          {r.geo.competitors.callouts.length > 0 && (
            <div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-3">
              {r.geo.competitors.callouts.map((c) => (
                <div key={c.title} className="rounded-lg border border-border p-3 text-sm">
                  <p className="font-medium">💡 {c.title}</p>
                  <p className="text-xs text-muted-foreground mt-1">{c.text}</p>
                </div>
              ))}
            </div>
          )}
        </section>
      )}


      {/* ---- brand narrative ---- */}
      {r.narrative && r.narrative.available && (
        <section>
          <h3 className="text-lg font-semibold">Brand narrative</h3>
          <Intro text={r.summary?.sections?.narrative} />
          <p className="text-sm text-muted-foreground">
            Not whether the engines name {audit.brand_name || "you"} — how they describe it, and what they lead with · {r.narrative.answers_analysed} answers analysed
          </p>
          <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3">
            <Tile label="Dominant framing" value={<span className="text-lg">{r.narrative.dominant_framing || "—"}</span>}
                  sub={r.narrative.framing_share != null ? `in ${r.narrative.framing_share}% of answers` : ""} />
            <Tile label="Narrative consistency" value={r.narrative.consistency != null ? `${r.narrative.consistency}%` : "—"}
                  sub={`across ${r.narrative.engines_analysed?.length ?? 0} engine${(r.narrative.engines_analysed?.length ?? 0) === 1 ? "" : "s"}`} />
            <Tile label="Descriptors present" value={r.narrative.descriptors_present?.length ?? 0} sub="ways the engines describe you" />
            <Tile label="Missing from answers" value={r.narrative.descriptors_missing?.length ?? 0} sub="things your site says that no engine repeats" />
          </div>
          <div className="mt-4 grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="border border-border">
              <CardContent className="p-4">
                <p className="text-sm font-semibold mb-3">How the engines describe you</p>
                <div className="space-y-2.5">
                  {(r.narrative.descriptors_present || []).map((d) => (
                    <Bar key={d.descriptor} label={d.descriptor} value={d.share} max={100} />
                  ))}
                  {!(r.narrative.descriptors_present || []).length && <p className="text-xs text-muted-foreground">—</p>}
                </div>
                {(r.narrative.descriptors_missing || []).length > 0 && (
                  <div className="mt-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">Missing descriptors</p>
                    <div className="flex flex-wrap gap-1.5">
                      {r.narrative.descriptors_missing!.map((m) => <Badge key={m} variant="outline" className="text-destructive">{m}</Badge>)}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
            <Card className="border border-border">
              <CardContent className="p-4">
                <p className="text-sm font-semibold mb-3">Framing by engine</p>
                <Table>
                  <TableHeader>
                    <TableRow><TableHead>Engine</TableHead><TableHead>Leads with</TableHead><TableHead>Tone</TableHead><TableHead>Matches your site</TableHead></TableRow>
                  </TableHeader>
                  <TableBody>
                    {(r.narrative.by_engine || []).map((e) => (
                      <TableRow key={e.platform}>
                        <TableCell className="font-medium">{e.platform}</TableCell>
                        <TableCell>{e.leads_with || "—"}</TableCell>
                        <TableCell className={cn("capitalize", e.tone === "positive" ? "text-emerald-600" : e.tone === "neutral" ? "text-muted-foreground" : "text-amber-600")}>{e.tone}</TableCell>
                        <TableCell className={cn("capitalize", e.matches_profile === "yes" ? "text-emerald-600" : e.matches_profile === "no" ? "text-destructive" : "text-amber-600")}>{e.matches_profile}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                {r.narrative.narrative_gap && (
                  <p className="text-xs text-muted-foreground mt-3"><span className="font-semibold text-foreground">Narrative gap · </span>{r.narrative.narrative_gap}</p>
                )}
              </CardContent>
            </Card>
          </div>
          {(r.narrative.off_brand || []).length > 0 && (
            <div className="mt-4 rounded-lg border border-amber-500/40 bg-amber-500/5 p-4">
              <p className="text-sm font-semibold">Off-brand framings</p>
              <ul className="mt-2 space-y-2">
                {r.narrative.off_brand!.map((o, i) => (
                  <li key={i} className="text-sm">
                    <span className="font-medium">{o.platform}: </span>“{o.claim}”
                    {o.why && <span className="block text-xs text-muted-foreground mt-0.5">{o.why}</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      {/* ---- SEO (only when the stage ran) ---- */}
      {r.seo && r.seo.keywords_total > 0 && (
        <section>
          <h3 className="text-lg font-semibold">SEO audit</h3>
          <p className="text-sm text-muted-foreground">{r.seo.keywords_total} keywords discovered from the site · ranked today</p>
          <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3">
            <Tile label="Visibility index" value={r.seo.visibility ?? "—"} />
            <Tile label="Top 10" value={`${r.seo.top10} / ${r.seo.keywords_total}`} />
            <Tile label="Striking distance" value={r.seo.striking_distance} sub="positions 11–20" />
            <Tile label="Unranked" value={r.seo.keywords_total - r.seo.top10 - r.seo.striking_distance} />
          </div>
          <div className="mt-3 overflow-x-auto rounded-lg border border-border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Keyword</TableHead><TableHead className="text-right">Vol</TableHead>
                  <TableHead className="text-right">Pos</TableHead><TableHead>Outranked by</TableHead>
                  <TableHead className="text-right">GEO</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {r.seo.top_keywords.map((k) => (
                  <TableRow key={k.keyword}>
                    <TableCell className="font-medium">{k.keyword}</TableCell>
                    <TableCell className="text-right tabular-nums">{k.search_volume?.toLocaleString() ?? "—"}</TableCell>
                    <TableCell className="text-right tabular-nums">{k.position ?? "—"}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">{k.outranked_by.join(", ") || "—"}</TableCell>
                    <TableCell className="text-right tabular-nums">{k.geo_engines_mentioning === null ? "—" : `${k.geo_engines_mentioning}/${engines.length}`}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </section>
      )}

      {/* ---- Website health (crawl stage) ---- */}
      {r.crawl && r.crawl.pages_sampled > 0 && <CrawlSection crawl={r.crawl} compact={compact} intro={r.summary?.sections?.website} />}

      {/* ---- Findable / Cited / Chosen ---- */}
      <section>
        <h3 className="text-lg font-semibold">Findable · Cited · Chosen</h3>
        <div className="mt-3 grid grid-cols-1 lg:grid-cols-3 gap-4">
          {PILLARS.map((p) => {
            const score = r.pillars[p.key];
            return (
              <Card key={p.key} className="border border-border">
                <CardContent className="p-4">
                  <div className="flex items-baseline justify-between">
                    <p className="font-semibold">{p.title}</p>
                    <p className="text-2xl font-bold tabular-nums">{score ?? <span className="text-sm font-normal text-muted-foreground">not measured</span>}</p>
                  </div>
                  <p className="text-xs text-muted-foreground">{p.question}</p>
                  <ul className="mt-3 space-y-2">
                    {measuresBy(p.key).map((m) => (
                      <li key={m.key} className="flex items-center justify-between gap-2 text-sm">
                        <span className="min-w-0">
                          <span className="block truncate">{m.label}</span>
                          <span className="block text-xs text-muted-foreground truncate" title={m.evidence}>{m.value ?? m.evidence}</span>
                        </span>
                        <span className={cn("flex-none text-xs tabular-nums font-medium",
                          m.score === null ? "text-muted-foreground" : m.status === "pass" ? "text-emerald-600" : "text-destructive")}>
                          {m.score === null ? "—" : `${m.score} / ${m.target}`}
                        </span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>

      {/* ---- quick wins ---- */}
      {r.quick_wins.length > 0 && (
        <section>
          <h3 className="text-lg font-semibold">Quick wins</h3>
          <p className="text-sm text-muted-foreground">Ordered by projected lift. Each one is backed by a row above.</p>
          <ol className="mt-3 space-y-3">
            {r.quick_wins.map((w, i) => (
              <li key={w.title} className="flex gap-4 rounded-lg border border-border p-4">
                <span className="flex h-7 w-7 flex-none items-center justify-center rounded-full bg-primary/10 text-primary text-sm font-semibold">{i + 1}</span>
                <div className="flex-1 min-w-0">
                  <p className="font-medium">{w.title}</p>
                  <p className="text-sm text-muted-foreground mt-1">{w.why} ~{w.effort_hours} hours.</p>
                </div>
                <Badge variant="outline" className="h-fit text-emerald-600 whitespace-nowrap">+{w.projected_geo_lift} GEO pts</Badge>
              </li>
            ))}
          </ol>
        </section>
      )}


      {/* ---- visibility plan ---- */}
      {r.plan && r.plan.buckets.some((b) => b.items.length > 0) && (
        <section>
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h3 className="text-lg font-semibold">Visibility plan</h3>
            <p className="text-sm text-muted-foreground">
              Today <span className="font-semibold text-foreground tabular-nums">{r.plan.today}</span>
              {" → "}<span className="font-semibold text-emerald-600 tabular-nums">{r.plan.projected}</span> if the plan is executed
              {r.plan.status_quo_note ? ` · status quo ${r.plan.status_quo_note}` : ""}
            </p>
          </div>
          <Intro text={r.summary?.sections?.plan} />
          <p className="text-sm text-muted-foreground">Every gap's action, sequenced Now / Next / Later, with the score projected at each step.</p>
          <div className="mt-3 grid grid-cols-1 lg:grid-cols-3 gap-4">
            {r.plan.buckets.map((b) => (
              <Card key={b.key} className={cn("border border-border", b.key === "now" && "border-primary/40")}>
                <CardContent className="p-4">
                  <div className="flex items-baseline justify-between">
                    <p className="font-semibold">{b.label}</p>
                    <p className="text-sm tabular-nums"><span className="text-muted-foreground">{b.from}</span> → <span className="font-semibold">{b.to}</span></p>
                  </div>
                  <p className="text-xs text-muted-foreground">{b.subtitle} · {b.items.length} action{b.items.length === 1 ? "" : "s"} · ~{b.hours}h</p>
                  <ol className="mt-3 space-y-3">
                    {b.items.length === 0 && <li className="text-xs text-muted-foreground">Nothing scheduled here.</li>}
                    {b.items.map((it) => (
                      <li key={it.key} className="text-sm">
                        <div className="flex items-start justify-between gap-2">
                          <p className="font-medium leading-snug">{it.title}</p>
                          <Badge variant="outline" className="flex-none text-emerald-600 text-[11px]">+{it.projected_geo_lift}</Badge>
                        </div>
                        <p className="text-xs text-muted-foreground mt-0.5">{it.why}</p>
                        <p className="text-[11px] text-muted-foreground mt-0.5 capitalize">{it.owner} · ~{it.effort_hours}h</p>
                      </li>
                    ))}
                  </ol>
                </CardContent>
              </Card>
            ))}
          </div>
          {r.plan.unscheduled > 0 && <p className="text-xs text-muted-foreground mt-2">{r.plan.unscheduled} more actions beyond the 90-day horizon.</p>}
        </section>
      )}

      {/* ---- methodology ---- */}
      <section className="text-xs text-muted-foreground leading-relaxed border-t border-border pt-4">
        <p className="font-semibold text-foreground mb-1">Methodology</p>
        <p>
          {r.config?.prompt_count ?? r.geo.evidence.length} prompts were generated from {audit.host} and asked {r.geo.runs_per_prompt && r.geo.runs_per_prompt > 1 ? `${r.geo.runs_per_prompt} times` : "once"} each on {platforms.join(", ")}
          {audit.completed_at ? ` on ${fmtDate(audit.completed_at)}` : ""}.{r.geo.runs_per_prompt && r.geo.runs_per_prompt > 1
            ? ` With ${r.geo.runs_per_prompt} runs per engine, an engine counts as "cited" or "mentioned" on a prompt when at least half its runs were.`
            : " One run per engine means low statistical confidence by design — AI answers vary run to run; the product re-asks each prompt several times and reports rates, not single results."} The GEO score weights placement 35%, frequency 25%, sourcing 25% and framing 15%,
          the same formula used for tracked projects.{r.seo ? " SEO data from PromptMaxx's own SERP pipeline; keyword volume from DataForSEO." : " Google rankings were not measured in this audit."}
          {r.crawl && r.crawl.pages_sampled > 0 ? ` On-site signals come from a plain-HTTP sample of ${r.crawl.pages_sampled} pages (schema, bylines, outbound citations, dates); no rendering, no user data.` : ""}
          {" "}Google AI Overviews are not yet tracked.
        </p>
      </section>
    </div>
  );
}
