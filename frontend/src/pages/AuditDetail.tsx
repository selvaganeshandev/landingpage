/**
 * One audit: live six-stage progress while it runs, then the report preview
 * exactly as the public link shows it, with the admin actions beside it
 * (share, re-run, convert to project, delete) and the raw evidence underneath.
 */
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft, Bell, Download, ExternalLink, Link2, Loader2, RefreshCw, Trash2, Zap, AlertTriangle,
} from "lucide-react";
import { apiClient } from "@/services/api";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { RunTimer, StageStrip, StatusBadge, fmtDate, fmtDateTime, saveBlob } from "@/components/audits/AuditBits";
import { AuditReportView } from "@/components/audits/AuditReportView";
import type { AuditDetail as AuditDetailType, PublicAudit } from "@/types/audit";

const POLL_MS = 5_000;

/** The detail row carries everything the public serializer does, bar two fields
 *  the public view derives for itself: seo_enabled, which the detail row holds
 *  inside config, and landing_url, which only a public visitor needs. */
function asPublic(a: AuditDetailType): PublicAudit {
  return {
    ...a,
    report: a.report && "geo" in a.report ? a.report : null,
    stage_detail: a.stage_detail || {},
    seo_enabled: Boolean((a.config as { seo_enabled?: boolean })?.seo_enabled),
    landing_url: "",
  } as PublicAudit;
}

export default function AuditDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user } = useAuth();
  const canManage = user?.role === "admin" || user?.role === "super_admin";

  const [audit, setAudit] = useState<AuditDetailType | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"rerun" | "claim" | "delete" | "pdf" | "csv" | "email" | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      setAudit(await apiClient.getAudit(id));
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const live = audit?.status === "INIT" || audit?.status === "PROC";
  useEffect(() => {
    if (!live) return;
    const t = setInterval(load, POLL_MS);
    return () => clearInterval(t);
  }, [live, load]);

  const publicLink = audit ? `${window.location.origin}/audit/${audit.public_token}` : "";

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(publicLink);
      toast({ title: "Public link copied", description: publicLink });
    } catch {
      toast({ title: "Public link", description: publicLink });
    }
  };

  const downloadIssues = async () => {
    if (!audit) return;
    setBusy("csv");
    try {
      saveBlob(await apiClient.downloadAuditIssuesCsv(audit.id), `promptmaxx-issues-${audit.host}.csv`);
    } catch (e) {
      toast({ title: "Could not export the issues", description: (e as Error).message, variant: "destructive" });
    } finally {
      setBusy(null);
    }
  };

  const downloadPdf = async () => {
    if (!audit) return;
    setBusy("pdf");
    try {
      saveBlob(await apiClient.downloadAuditPdf(audit.id), `promptmaxx-audit-${audit.host}.pdf`);
    } catch (e) {
      toast({ title: "Could not download the PDF", description: (e as Error).message, variant: "destructive" });
    } finally {
      setBusy(null);
    }
  };

  const rerun = async () => {
    if (!audit) return;
    setBusy("rerun");
    try {
      await apiClient.rerunAudit(audit.id);
      toast({ title: "Re-running", description: "It resumes from the stage that failed." });
      await load();
    } catch (e) {
      toast({ title: "Could not re-run", description: (e as Error).message, variant: "destructive" });
    } finally {
      setBusy(null);
    }
  };

  /** The claim created a Domain server-side; the project switcher reads the
   *  global store, so refresh it or the new project only appears after a reload. */
  const refreshProjects = async () => {
    try {
      const { useDomainStore } = await import("@/stores/domainStore");
      await useDomainStore.getState().loadDomains();
    } catch { /* the audit page itself does not depend on the project list */ }
  };

  const claim = async () => {
    if (!audit) return;
    setBusy("claim");
    try {
      const res = await apiClient.claimAudit(audit.id);
      toast({ title: `${res.domain.name} added as a project`, description: "Keywords are being generated in the background." });
      await Promise.all([load(), refreshProjects()]);
    } catch (e) {
      toast({ title: "Could not convert to project", description: (e as Error).message, variant: "destructive" });
    } finally {
      setBusy(null);
    }
  };

  const remove = async () => {
    if (!audit) return;
    setBusy("delete");
    try {
      await apiClient.deleteAudit(audit.id);
      toast({ title: `Deleted the audit of ${audit.host}` });
      navigate("/audits");
    } catch (e) {
      toast({ title: "Could not delete", description: (e as Error).message, variant: "destructive" });
      setBusy(null);
    }
  };

  if (error) {
    return (
      <div className="p-8 space-y-6 bg-background animate-fade-in">
        <Link to="/audits" className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="h-4 w-4 mr-1" />Audit Engine</Link>
        <Alert variant="destructive"><AlertTitle>Could not load this audit</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>
      </div>
    );
  }
  if (!audit) {
    return <div className="p-8 flex items-center justify-center text-muted-foreground"><Loader2 className="h-6 w-6 animate-spin" /></div>;
  }

  const seoEnabled = Boolean((audit.config as { seo_enabled?: boolean })?.seo_enabled);
  const engineDetail = audit.stage_detail?.engines as { done?: number; total?: number } | undefined;

  return (
    <div className="p-8 space-y-6 bg-background animate-fade-in">
      <Link to="/audits" className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4 mr-1" />Audit Engine
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-4xl font-bold tracking-tight flex items-center gap-3">
            {live ? `Auditing ${audit.host}` : audit.brand_name || audit.host}
            <StatusBadge status={audit.status} stageLabel={audit.stage_label} />
          </h1>
          <p className="text-muted-foreground mt-2">
            {audit.host}{audit.industry ? ` · ${audit.industry}` : ""} · started {fmtDateTime(audit.created_at)}
            {audit.requested_by_email ? ` by ${audit.requested_by_email}` : audit.requester_email ? ` · ${audit.requester_email}` : ""}
            {" · "}{audit.source === "landing" ? "landing page" : audit.source}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {live && (audit.requester_email || audit.requested_by_email) && (
            <span className="inline-flex items-center h-9 px-3 rounded-md border border-border text-xs text-muted-foreground">
              <Bell className="h-3.5 w-3.5 mr-2" />
              We'll email {audit.requester_email || audit.requested_by_email} when it's ready
            </span>
          )}
          <Button variant="outline" size="sm" onClick={copyLink} disabled={audit.status !== "DONE"}>
            <Link2 className="h-4 w-4 mr-2" />Share link
          </Button>
          <Button variant="outline" size="sm" onClick={() => window.open(`/audit/${audit.public_token}`, "_blank")} disabled={audit.status !== "DONE"}>
            <ExternalLink className="h-4 w-4 mr-2" />Public report
          </Button>
          <Button variant="outline" size="sm" onClick={downloadPdf} disabled={audit.status !== "DONE" || busy !== null}>
            {busy === "pdf" ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Download className="h-4 w-4 mr-2" />}PDF
          </Button>
          {audit.report?.crawl?.technical_issues && (
            <Button variant="outline" size="sm" onClick={downloadIssues} disabled={audit.status !== "DONE" || busy !== null} title="Every technical SEO issue with its URLs, for the developer">
              {busy === "csv" ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Download className="h-4 w-4 mr-2" />}Issues CSV
            </Button>
          )}
          {canManage && audit.status === "FAIL" && (
            <Button size="sm" onClick={rerun} disabled={busy !== null}>
              {busy === "rerun" ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <RefreshCw className="h-4 w-4 mr-2" />}Re-run
            </Button>
          )}
          {canManage && audit.status === "DONE" && !audit.is_claimed && (
            <Button size="sm" onClick={claim} disabled={busy !== null}>
              {busy === "claim" ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Zap className="h-4 w-4 mr-2" />}Convert to project
            </Button>
          )}
          {audit.is_claimed && audit.claimed_domain && (
            <Badge variant="outline" className="text-emerald-600 h-9 px-3">Project → {audit.claimed_domain_name}</Badge>
          )}
          {canManage && (
            <Button variant="ghost" size="sm" className="text-destructive" onClick={() => setConfirmDelete(true)} disabled={busy !== null}>
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      {/* ---- progress ---- */}
      {(live || audit.status === "FAIL") && (
        <Card className="border border-border">
          <CardContent className="p-5 space-y-4">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">
                {audit.status === "FAIL" ? "Stopped" : `${audit.stage_label || "Queued"}${engineDetail?.total ? ` · ${engineDetail.done ?? 0} / ${engineDetail.total} executions` : ""}`}
              </span>
              <span className="flex items-center gap-3">
                {live && <RunTimer startedAt={audit.created_at} finishedAt={audit.completed_at} running seoEnabled={seoEnabled} />}
                <span className="text-muted-foreground tabular-nums">{audit.progress}%</span>
              </span>
            </div>
            <Progress value={audit.progress} className="h-2" />
            <StageStrip status={audit.status} stage={audit.stage} stageDetail={audit.stage_detail || {}} seoEnabled={seoEnabled} />
            {live && (
              <p className="text-xs text-muted-foreground">
                {seoEnabled ? "Seven stages" : "Six stages"} · this page updates itself.
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {audit.status === "FAIL" && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>The audit stopped at “{audit.stage_label || audit.stage}”</AlertTitle>
          <AlertDescription className="font-mono text-xs break-all">{audit.error}</AlertDescription>
        </Alert>
      )}

      {/* ---- profile while running ---- */}
      {live && audit.brand_name && (
        <Card className="border border-border">
          <CardContent className="p-5">
            <p className="text-sm font-semibold mb-2">Profile · detected</p>
            <dl className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div><dt className="text-xs text-muted-foreground">Brand</dt><dd className="font-medium">{audit.brand_name}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Industry</dt><dd className="font-medium">{audit.industry || "—"}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Stack</dt><dd className="font-medium">{audit.tech_stack.join(" · ") || "—"}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Competitors</dt><dd className="font-medium">{audit.competitors.map((c) => c.name).join(" · ") || "—"}</dd></div>
            </dl>
          </CardContent>
        </Card>
      )}

      {/* ---- report + evidence ---- */}
      {audit.status === "DONE" && (
        <Tabs defaultValue="report">
          <TabsList>
            <TabsTrigger value="report">Report preview</TabsTrigger>
            <TabsTrigger value="responses">Responses ({audit.prompt_results.length})</TabsTrigger>
            {audit.keyword_results.length > 0 && <TabsTrigger value="keywords">Keywords ({audit.keyword_results.length})</TabsTrigger>}
            {audit.page_results.length > 0 && <TabsTrigger value="pages">Pages ({audit.page_results.length})</TabsTrigger>}
          </TabsList>

          <TabsContent value="report" className="mt-4">
            <Card className="border border-border">
              <CardContent className="p-6">
                <p className="text-xs text-muted-foreground mb-4">
                  Public link · {audit.expires_at ? `expires ${fmtDate(audit.expires_at)}` : "never expires (claimed)"} · {audit.opens} open{audit.opens === 1 ? "" : "s"}
                </p>
                <AuditReportView audit={asPublic(audit)} />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="responses" className="mt-4">
            <div className="rounded-lg border border-border overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>#</TableHead><TableHead>Prompt</TableHead><TableHead>Engine</TableHead><TableHead>Run</TableHead>
                    <TableHead>Result</TableHead><TableHead>Pos</TableHead><TableHead>Sentiment</TableHead>
                    <TableHead>Named</TableHead><TableHead>Cited domains</TableHead><TableHead className="text-right">Latency</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {audit.prompt_results.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell className="text-muted-foreground">{r.prompt_index}</TableCell>
                      <TableCell className="max-w-[320px]">
                        <details>
                          <summary className="cursor-pointer font-medium">{r.prompt_text}</summary>
                          <pre className="mt-2 whitespace-pre-wrap text-xs text-muted-foreground max-h-72 overflow-auto">{r.response_text || r.error || "—"}</pre>
                        </details>
                      </TableCell>
                      <TableCell>{r.platform}</TableCell>
                      <TableCell className="tabular-nums text-muted-foreground">{r.run_index}</TableCell>
                      <TableCell>
                        {r.status !== "ok" ? <Badge variant="destructive">{r.status.replace("_", " ")}</Badge>
                          : r.is_cited ? <Badge className="bg-emerald-600 hover:bg-emerald-600">cited</Badge>
                          : r.is_mention ? <Badge variant="secondary">mentioned</Badge>
                          : <Badge variant="outline">absent</Badge>}
                      </TableCell>
                      <TableCell className="tabular-nums">{r.position ? Number(r.position).toFixed(0) : "—"}</TableCell>
                      <TableCell className="capitalize text-muted-foreground">{r.sentiment || "—"}</TableCell>
                      <TableCell className="text-xs text-muted-foreground max-w-[200px] truncate" title={r.rival_positions && Object.keys(r.rival_positions).length ? Object.entries(r.rival_positions).sort((a, b) => a[1] - b[1]).map(([n, p]) => `${p}. ${n}`).join("  ") : r.competitors_mentioned.join(", ")}>
                        {r.rival_positions && Object.keys(r.rival_positions).length
                          ? Object.entries(r.rival_positions).sort((a, b) => a[1] - b[1]).map(([n, p]) => `${p}. ${n}`).join("  ")
                          : r.competitors_mentioned.join(", ") || "—"}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground max-w-[200px] truncate" title={r.cited_domains.join(", ")}>{r.cited_domains.join(", ") || "—"}</TableCell>
                      <TableCell className="text-right tabular-nums text-muted-foreground">{r.latency_ms ? `${(r.latency_ms / 1000).toFixed(1)}s` : "—"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </TabsContent>

          <TabsContent value="keywords" className="mt-4">
            <div className="rounded-lg border border-border overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Keyword</TableHead><TableHead className="text-right">Volume</TableHead><TableHead className="text-right">Position</TableHead>
                    <TableHead>URL</TableHead><TableHead>Outranked by</TableHead><TableHead className="text-right">GEO engines</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {audit.keyword_results.map((k) => (
                    <TableRow key={k.id}>
                      <TableCell className="font-medium">{k.keyword}</TableCell>
                      <TableCell className="text-right tabular-nums">{k.search_volume?.toLocaleString() ?? "—"}</TableCell>
                      <TableCell className="text-right tabular-nums">{k.position ?? "—"}</TableCell>
                      <TableCell className="text-xs text-muted-foreground max-w-[240px] truncate" title={k.ranking_url}>{k.ranking_url || "—"}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">{k.outranked_by.join(", ") || "—"}</TableCell>
                      <TableCell className="text-right tabular-nums">{k.geo_engines_mentioning ?? "—"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </TabsContent>
          <TabsContent value="pages" className="mt-4">
            <div className="rounded-lg border border-border overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>URL</TableHead><TableHead>Title</TableHead><TableHead className="text-right">Words</TableHead>
                    <TableHead>Schema types</TableHead><TableHead>Author</TableHead><TableHead className="text-right">Outbound hosts</TableHead>
                    <TableHead className="text-right">Q-headings</TableHead><TableHead>Table</TableHead><TableHead>Updated</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {audit.page_results.map((p) => (
                    <TableRow key={p.id}>
                      <TableCell className="max-w-[260px]"><a href={p.url} target="_blank" rel="noreferrer" className="block truncate text-primary hover:underline" title={p.url}>{p.url}</a>{!p.fetched && <span className="block text-xs text-destructive">{p.error || "could not be read"}</span>}</TableCell>
                      <TableCell className="max-w-[220px] truncate" title={p.title}>{p.title || "—"}</TableCell>
                      <TableCell className="text-right tabular-nums">{p.fetched ? p.word_count.toLocaleString() : "—"}</TableCell>
                      <TableCell className="text-xs text-muted-foreground max-w-[200px] truncate" title={p.schema_types.join(", ")}>{p.schema_types.join(", ") || "—"}</TableCell>
                      <TableCell className="text-xs">{p.author || "—"}</TableCell>
                      <TableCell className="text-right tabular-nums">{p.external_links}</TableCell>
                      <TableCell className="text-right tabular-nums">{p.question_headings}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">{p.has_table ? "yes" : "—"}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">{p.last_modified ?? "—"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </TabsContent>
        </Tabs>
      )}

      <AlertDialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete the audit of {audit.host}?</AlertDialogTitle>
            <AlertDialogDescription>The public link stops working and the evidence rows are removed. A project created from it is not affected.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={remove} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

    </div>
  );
}
