"use client";

/**
 * The dark panel under the form: the seven stages as the engine walks them,
 * the answers arriving, then the score and the PDF.
 */
import { useEffect, useState } from "react";
import Link from "next/link";
import { pdfUrl, reportPath, scoreSummary, type LiveRow, type PublicAudit } from "@/lib/audit";
import { STAGES, stageIndex } from "@/lib/stages";
import { CONTACT_URL, REPORT_TTL_DAYS, engineLabel } from "@/lib/site";
import type { AuditState } from "@/lib/useAudit";

function useElapsed(startedAt: string | undefined, running: boolean) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!running) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [running]);
  if (!startedAt) return "";
  const s = Math.max(0, Math.floor((now - new Date(startedAt).getTime()) / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

function Stages({ audit }: { audit: PublicAudit | null }) {
  const status = audit?.status ?? "INIT";
  const current = audit ? stageIndex(audit.stage) : -1;
  const detail = audit?.stage_detail || {};
  const seo = !!audit?.seo_enabled;
  return (
    <ol className="stages" aria-label="Audit progress">
      {STAGES.map((s, i) => {
        const skipped = (s.key === "serp" && (!seo || !!detail.serp?.skipped)) || (s.key === "crawl" && !!detail.crawl?.skipped);
        const done = status === "DONE" || i < current;
        const active = (status === "INIT" || status === "PROC") && (i === current || (current < 0 && i === 0));
        const failed = status === "FAIL" && i === current;
        const cls = failed ? "fl" : skipped && !active ? "sk" : done ? "dn" : active ? "ac" : "";
        const text = s.detail(detail[s.key] || {}, seo) || s.blurb;
        return (
          <li key={s.key} className={cls} aria-current={active ? "step" : undefined}>
            <b>{s.title}</b>{text}
          </li>
        );
      })}
    </ol>
  );
}

function FeedRow({ r }: { r: LiveRow }) {
  const cls = r.result === "cited" ? "c" : r.result === "mentioned" ? "m" : "x";
  const txt = r.result === "cited" ? `cited${r.position ? ` #${r.position}` : ""}`
    : r.result === "mentioned" ? "mentioned, not cited"
    : r.instead ? `absent · ${r.instead} instead` : "absent";
  return (
    <div className="r">
      <span className="e" title={r.engine}>{engineLabel(r.engine)}</span>
      <span className="q" title={r.prompt}>{r.prompt}</span>
      <span className={`v ${cls}`}>{txt}</span>
    </div>
  );
}

function CountUp({ to }: { to: number }) {
  const [n, setN] = useState(0);
  useEffect(() => {
    let v = 0;
    const t = setInterval(() => { v = Math.min(to, v + 2); setN(v); if (v >= to) clearInterval(t); }, 28);
    return () => clearInterval(t);
  }, [to]);
  return <>{n}</>;
}

function ScoreBox({ audit, email }: { audit: PublicAudit; email: string }) {
  const s = scoreSummary(audit);
  const [copied, setCopied] = useState(false);
  const link = typeof window === "undefined" ? reportPath(audit.public_token) : `${window.location.origin}${reportPath(audit.public_token)}`;
  const copy = async () => {
    try { await navigator.clipboard.writeText(link); setCopied(true); setTimeout(() => setCopied(false), 2000); } catch { /* no clipboard: the URL is in the address bar */ }
  };
  const verdict = s.verdict || (
    `${audit.brand_name || audit.host} is ${s.stage.charAt(0) + s.stage.slice(1).toLowerCase()}. ` +
    `${s.mention} of ${s.total} engines mention you; ${s.cite} cite your site.` +
    (s.rivalInstead ? ` On ${s.rivalInstead} of ${s.questions} questions a rival was cited where you weren't.` : "")
  );
  return (
    <div className="scorebox">
      <div>
        <div className="lbl">AI Visibility Score</div>
        <div className="big"><CountUp to={s.score} /></div>
        <span className={`stage ${(audit.geo_stage || "present").toLowerCase()}`}>{s.stage}</span>
      </div>
      <div>
        <p>{verdict}</p>
        <div className="mini">
          <div><b>{s.mention}<small>/{s.total}</small></b><span>engines mention you</span></div>
          <div><b>{s.cite}<small>/{s.total}</small></b><span>engines cite your site</span></div>
          <div><b>{s.rivalInstead}<small>/{s.questions}</small></b><span>questions where a rival is cited instead</span></div>
          <div><b>{s.shareOfVoice == null ? "—" : `${s.shareOfVoice}%`}</b><span>your share of voice vs rivals</span></div>
        </div>
        <div className="claim">
          <a className="btn acc" href={pdfUrl(audit.public_token)} download>Download the PDF report ↓</a>
          <button type="button" className="btn ghost" onClick={copy}>{copied ? "Link copied ✓" : "Copy report link"}</button>
          <span className="note">
            Every question, every engine&apos;s answer, and the fix list. Free.
            {email ? <> The report is filed under <b>{email}</b>.</> : null} This link stays live for {REPORT_TTL_DAYS} days.
          </span>
        </div>
      </div>
    </div>
  );
}

export function LivePanel({ host, email, reused, state }: {
  host: string;
  email: string;
  reused: boolean;
  state: AuditState;
}) {
  const { audit, feed, error } = state;
  const status = audit?.status ?? "INIT";
  // No audit yet and an error = the link itself is bad (expired / unknown).
  const loadFailed = !audit && !!error;
  const running = !loadFailed && (status === "INIT" || status === "PROC");
  const elapsed = useElapsed(audit?.created_at, running);
  const progress = status === "DONE" ? 100 : audit?.progress ?? 2;
  const shownHost = audit?.host || host;

  return (
    <div className="live" id="live" aria-live="polite">
      <div className="top">
        <div>
          <div className="kicker">{status === "DONE" ? "Audited" : status === "FAIL" ? "Audit stopped" : "Auditing"}</div>
          <div className="dom">{shownHost}</div>
        </div>
        <div className="when">
          {status === "DONE" && audit
            ? <>Done{reused ? " · we audited this site in the last 24 hours, so here is that report" : ""} · <a href={pdfUrl(audit.public_token)} download>Download the PDF →</a></>
            : status === "FAIL"
            ? "Stopped"
            : <>{elapsed ? `Running ${elapsed} · ` : ""}you can leave this page open — it updates itself. Bookmark it to come back.</>}
        </div>
      </div>

      {!loadFailed && <div className="bar" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress}><i style={{ width: `${progress}%` }} /></div>}

      {!loadFailed && <Stages audit={audit} />}

      {running && (
        <div className="feed">
          {feed.length === 0
            ? <div className="empty">{audit?.stage === "engines" ? "First answers arriving…" : "Answers will appear here as the engines reply."}</div>
            : feed.map((r) => <FeedRow key={`${r.engine}|${r.prompt}|${r.at}`} r={r} />)}
        </div>
      )}

      {error && audit && running && <div className="failed" role="status"><b>Connection hiccup.</b> {error.message}</div>}
      {loadFailed && (
        <div className="failed" role="alert">
          <b>We couldn&apos;t load this audit.</b> {error?.message}
          <br />
          <Link className="btn ghost sm" href="/" style={{ color: "#fff", borderColor: "rgba(255,255,255,.35)" }}>Run a new audit</Link>
        </div>
      )}

      {status === "FAIL" && (
        <div className="failed" role="alert">
          <b>This audit could not be completed.</b> {audit?.error || "Please try again later."} If it keeps happening,{" "}
          <a href={CONTACT_URL} style={{ color: "#fff" }}>tell us</a> and we&apos;ll run it by hand.
          <br />
          <Link className="btn ghost sm" href="/" style={{ color: "#fff", borderColor: "rgba(255,255,255,.35)" }}>Try another site</Link>
        </div>
      )}

      {status === "DONE" && audit && <ScoreBox audit={audit} email={email} />}
    </div>
  );
}
