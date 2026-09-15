/**
 * /audit/<token> — the shareable report. No login, no sidebar: this is what a
 * prospect opens from the landing page or a shared link.
 *
 * While the audit runs it shows the six-stage progress and polls; once DONE
 * it renders the same AuditReportView the admin previews in the app. "Claim
 * this audit" claims by token when the visitor is a signed-in admin, and
 * otherwise sends them through sign-in and back here.
 */
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Download, Link2, Loader2, Zap } from "lucide-react";
import { apiClient } from "@/services/api";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/hooks/use-toast";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { StageStrip, fmtDate } from "@/components/audits/AuditBits";
import { AuditReportView } from "@/components/audits/AuditReportView";
import type { PublicAudit as PublicAuditType } from "@/types/audit";

const POLL_MS = 5_000;

export default function PublicAudit() {
  const { token = "" } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user, isAuthenticated } = useAuth();
  const canClaim = isAuthenticated && (user?.role === "admin" || user?.role === "super_admin");

  const [audit, setAudit] = useState<PublicAuditType | null>(null);
  const [error, setError] = useState<{ status?: number; message: string } | null>(null);
  const [claiming, setClaiming] = useState(false);

  const load = useCallback(async () => {
    if (!token) return;
    try {
      setAudit(await apiClient.getPublicAudit(token));
      setError(null);
    } catch (e) {
      const err = e as Error & { status?: number };
      setError({ status: err.status, message: err.message });
    }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const live = audit?.status === "INIT" || audit?.status === "PROC";
  useEffect(() => {
    if (!live) return;
    const t = setInterval(load, POLL_MS);
    return () => clearInterval(t);
  }, [live, load]);

  useEffect(() => {
    document.title = audit?.brand_name ? `${audit.brand_name} — AI visibility audit · PromptMaxx` : "AI visibility audit · PromptMaxx";
    return () => { document.title = "PromptMaxx"; };
  }, [audit?.brand_name]);

  const share = async () => {
    const link = window.location.href;
    try {
      await navigator.clipboard.writeText(link);
      toast({ title: "Link copied", description: link });
    } catch {
      toast({ title: "Share this link", description: link });
    }
  };

  const claim = async () => {
    if (!audit) return;
    if (!canClaim) {
      navigate(`/signin?next=${encodeURIComponent(`/audit/${token}`)}`);
      return;
    }
    setClaiming(true);
    try {
      const res = await apiClient.claimAuditByToken(token);
      toast({ title: `${res.domain.name} is now a project`, description: "This audit is its Day-0 baseline. Keywords are being generated." });
      navigate(`/audits/${res.audit.id}`);
    } catch (e) {
      const err = e as Error & { status?: number; data?: { audit_id?: number; domain_id?: number } };
      if (err.data?.audit_id && err.data?.domain_id) {
        toast({ title: "Already a project", description: err.message });
        navigate(`/audits/${err.data.audit_id}`);
      } else {
        toast({ title: "Could not claim this audit", description: err.message, variant: "destructive" });
      }
    } finally {
      setClaiming(false);
    }
  };

  const shell = (children: React.ReactNode) => (
    <div className="min-h-screen bg-background text-foreground">
      <style>{`@media print { .no-print { display: none !important; } body { background: #fff; } }`}</style>
      <header className="no-print border-b border-border">
        <div className="mx-auto max-w-6xl px-6 py-3 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Link to="/" className="text-lg font-bold tracking-tight text-primary">PROMPTMAXX</Link>
            <span className="text-sm text-muted-foreground">· Free AI visibility audit</span>
          </div>
          <div className="flex items-center gap-2">
            {audit?.status === "DONE" && (
              <>
                <span className="hidden sm:inline text-xs text-muted-foreground mr-2">
                  Public link{audit.expires_at ? ` · expires ${fmtDate(audit.expires_at)}` : ""} · {audit.opens} open{audit.opens === 1 ? "" : "s"}
                </span>
                <Button variant="outline" size="sm" onClick={share}><Link2 className="h-4 w-4 mr-2" />Share</Button>
                <Button variant="outline" size="sm" asChild>
                  <a href={apiClient.publicAuditPdfUrl(token)} download={`promptmaxx-audit-${audit.host}.pdf`}><Download className="h-4 w-4 mr-2" />PDF</a>
                </Button>
                {audit.report?.crawl?.technical_issues && (
                  <Button variant="outline" size="sm" asChild>
                    <a href={apiClient.publicAuditIssuesCsvUrl(token)} download={`promptmaxx-issues-${audit.host}.csv`}><Download className="h-4 w-4 mr-2" />Issues CSV</a>
                  </Button>
                )}
                {!audit.is_claimed && (
                  <Button size="sm" onClick={claim} disabled={claiming}>
                    {claiming ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Zap className="h-4 w-4 mr-2" />}
                    Claim this audit
                  </Button>
                )}
              </>
            )}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
      <footer className="no-print border-t border-border">
        <div className="mx-auto max-w-6xl px-6 py-6 text-xs text-muted-foreground flex flex-wrap justify-between gap-2">
          <span>Generated by PromptMaxx · AI search visibility and content strategy</span>
          <Link to="/signin" className="hover:text-foreground">Sign in</Link>
        </div>
      </footer>
    </div>
  );

  if (error) {
    return shell(
      <div className="py-24 text-center">
        <h1 className="text-2xl font-bold">{error.status === 404 ? "This audit link is no longer available" : "Could not load this audit"}</h1>
        <p className="text-muted-foreground mt-2">
          {error.status === 404 ? "Public reports expire after a while unless they are claimed. Run a new audit to get a fresh one." : error.message}
        </p>
      </div>,
    );
  }
  if (!audit) {
    return shell(<div className="py-24 flex justify-center text-muted-foreground"><Loader2 className="h-6 w-6 animate-spin" /></div>);
  }

  if (audit.status === "FAIL") {
    return shell(
      <div className="py-24 text-center">
        <h1 className="text-2xl font-bold">We couldn't finish the audit of {audit.host}</h1>
        <p className="text-muted-foreground mt-2">{audit.error}</p>
      </div>,
    );
  }

  if (live) {
    const engines = audit.stage_detail?.engines as { done?: number; total?: number } | undefined;
    return shell(
      <div className="space-y-6">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">AI visibility audit</p>
          <h1 className="text-3xl font-bold tracking-tight mt-1">Auditing {audit.host}</h1>
          <p className="text-muted-foreground mt-1">Six stages · about three minutes · this page updates itself. If you left an email, we'll send you the link too.</p>
        </div>
        <div className="rounded-lg border border-border p-5 space-y-4">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">{audit.stage_label || "Queued"}{engines?.total ? ` · ${engines.done ?? 0} / ${engines.total} executions` : ""}</span>
            <span className="text-muted-foreground tabular-nums">{audit.progress}%</span>
          </div>
          <Progress value={audit.progress} className="h-2" />
          <StageStrip status={audit.status} stage={audit.stage} stageDetail={audit.stage_detail || {}} seoEnabled={false} />
        </div>
        {audit.brand_name && (
          <div className="rounded-lg border border-border p-5">
            <p className="text-sm font-semibold mb-2">Profile · detected</p>
            <dl className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div><dt className="text-xs text-muted-foreground">Brand</dt><dd className="font-medium">{audit.brand_name}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Industry</dt><dd className="font-medium">{audit.industry || "—"}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Stack</dt><dd className="font-medium">{audit.tech_stack.join(" · ") || "—"}</dd></div>
              <div><dt className="text-xs text-muted-foreground">Competitors</dt><dd className="font-medium">{audit.competitors.map((c) => c.name).join(" · ") || "—"}</dd></div>
            </dl>
          </div>
        )}
      </div>,
    );
  }

  return shell(
    <div className="space-y-10">
      <AuditReportView audit={audit} />
      {!audit.is_claimed && (
        <section className="no-print rounded-xl border border-primary/30 bg-primary/5 p-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="font-semibold">The full plan is one click away</p>
            <p className="text-sm text-muted-foreground mt-1">
              Every prompt re-run for confidence, more engines, Google rankings, and a sequenced plan with the projected score at each step.
              This audit becomes Day 0 of your project — nothing is recomputed.
            </p>
          </div>
          <Button onClick={claim} disabled={claiming}>
            {claiming ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Zap className="h-4 w-4 mr-2" />}
            Claim this audit →
          </Button>
        </section>
      )}
    </div>,
  );
}
