"use client";

/**
 * The hero owns the audit's lifecycle on the page: form → POST → live panel
 * polling the token → score + PDF. Starting an audit rewrites the address bar
 * to /audit/<token>, so a refresh (or the same link later) resumes the panel;
 * /audit/[token] renders this same component with `initialToken` set.
 */
import { useEffect, useRef, useState } from "react";
import { AuditApiError, createAudit, reportPath } from "@/lib/audit";
import { useAudit } from "@/lib/useAudit";
import { CONTACT_URL, ENGINES, MINUTES_LABEL } from "@/lib/site";
import { AuditForm, type FormValues } from "./AuditForm";
import { LivePanel } from "./LivePanel";

const FLIP_WORDS = ["you", "your competitor", "someone else", "you"];

function HeadlineFlip() {
  const [i, setI] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setI((n) => (n + 1) % FLIP_WORDS.length), 2200);
    return () => clearInterval(t);
  }, []);
  return <span className="flip">{FLIP_WORDS[i]}</span>;
}

function track(ev: string, data: Record<string, unknown>) {
  const w = window as unknown as { dataLayer?: Record<string, unknown>[] };
  (w.dataLayer = w.dataLayer || []).push({ event: `audit_${ev}`, ...data });
}

/** Email-blast links carry ?d=<domain>&e=<email>&b=<brand>&c=<campaign>&m=<market>. */
export interface HeroParams {
  d?: string;
  e?: string;
  b?: string;
  c?: string;
  m?: string;
}

export function Hero({ initialToken = null, params = {} }: { initialToken?: string | null; params?: HeroParams }) {
  const [token, setToken] = useState<string | null>(initialToken);
  const [host, setHost] = useState("");
  const [email, setEmail] = useState("");
  const [reused, setReused] = useState(false);
  const [busy, setBusy] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [captchaReset, setCaptchaReset] = useState(0);
  const panelRef = useRef<HTMLDivElement>(null);
  const state = useAudit(token);

  // Fire "complete" once, when the poll first reports DONE.
  const completed = useRef(false);
  useEffect(() => {
    if (state.audit?.status === "DONE" && !completed.current) {
      completed.current = true;
      track("complete", { domain: state.audit.host, score: state.audit.geo_score, stage: state.audit.geo_stage });
    }
  }, [state.audit]);

  const start = async (v: FormValues) => {
    setBusy(true);
    setServerError(null);
    const campaign = params.c || "default";
    const country = (params.m || "").toLowerCase().slice(0, 2) || undefined;
    track("start", { domain: v.domain, brand: v.brand, email: v.email, campaign });
    try {
      const r = await createAudit({ url: v.domain, email: v.email, brand_name: v.brand, country, campaign, turnstile_token: v.captcha });
      setHost(r.host || v.domain);
      setEmail(v.email);
      setReused(!!r.reused);
      setToken(r.public_token);
      window.history.replaceState(null, "", reportPath(r.public_token));
      requestAnimationFrame(() => panelRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
    } catch (e) {
      const err = e as AuditApiError;
      setServerError(err.message || "We couldn't reach the audit engine. Check your connection and try again.");
      track("refused", { domain: v.domain, status: err.status });
      // The token was spent on this attempt; a retry needs a fresh one.
      setCaptchaReset((n) => n + 1);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="hero" id="audit">
      <div className="wrap">
        <div className="stamp"><div>Free<br /><b>{ENGINES.length}</b>AI engines<br />{MINUTES_LABEL}</div></div>
        <span className="tag acc"><span className="pulse" aria-hidden="true" />New · AI Visibility Audit by PivotRoots</span>
        <h1>Is AI recommending <HeadlineFlip />?</h1>
        <p className="lead">
          Your customers stopped Googling and started asking. Enter your domain and we&apos;ll show you exactly what ChatGPT, Gemini, Claude,
          Perplexity, Grok and DeepSeek say — and who they recommend instead.
        </p>

        {!token && (
          <AuditForm busy={busy} serverError={serverError} onSubmit={start} captchaReset={captchaReset}
            prefill={{ d: params.d || "", e: params.e || "", b: params.b || "" }} />
        )}

        {!token && (
          <>
            <div className="fine">
              <span><b>No card.</b> No login. Just a work email.</span>
              <span><b>{MINUTES_LABEL}.</b> Watch it run.</span>
              <span><b>Real answers,</b> not a score you have to trust.</span>
            </div>
            <div className="engines">
              {ENGINES.map((e) => <span key={e}>{e}</span>)}
              <span className="soon">Google AI Overviews · soon</span>
            </div>
            <a className="alt-cta" href={CONTACT_URL}>Rather talk it through? Speak to a PivotRoots strategist →</a>
          </>
        )}

        {token && (
          <div ref={panelRef}>
            <LivePanel host={host} email={email} reused={reused} state={state} />
          </div>
        )}
      </div>
    </section>
  );
}
