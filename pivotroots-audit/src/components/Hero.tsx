"use client";

/**
 * The hero owns the audit's lifecycle on the page: form → POST → live panel
 * polling the token → score + PDF. Starting an audit rewrites the address bar
 * to /audit/<token>, so a refresh (or the same link later) resumes the panel;
 * /audit/[token] renders this same component with `initialToken` set.
 */
import { useEffect, useRef, useState, type CSSProperties } from "react";
import { AuditApiError, createAudit, reportPath } from "@/lib/audit";
import { useAudit } from "@/lib/useAudit";
import { CONTACT_URL, ENGINES, MINUTES_LABEL } from "@/lib/site";
import { AuditForm, type FormValues } from "./AuditForm";
import { LivePanel } from "./LivePanel";
import { Orbit } from "./Orbit";
import { Word, Words } from "./Split";

const FLIP_WORDS = ["you", "your competitor", "someone else", "you"];

/** Rotating badge on the form's corner: "Free · AI engines · 2 minutes" around the engine count. */
function Stamp() {
  return (
    <div className="stamp" aria-hidden="true">
      <svg viewBox="0 0 120 120">
        <defs><path id="stamp-path" d="M60,60 m-46,0 a46,46 0 1,1 92,0 a46,46 0 1,1 -92,0" /></defs>
        <circle cx="60" cy="60" r="58" />
        <text><textPath href="#stamp-path">Free · AI engines · {MINUTES_LABEL} · Free ·</textPath></text>
      </svg>
      <b>{ENGINES.length}</b>
    </div>
  );
}

/**
 * The highlighted word rolls up like a slot reel and the Pear box resizes to
 * fit. The last word repeats the first, so the reel snaps back unseen.
 */
function HeadlineFlip() {
  const box = useRef<HTMLSpanElement>(null);
  const reel = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    const flip = box.current, track = reel.current;
    if (!flip || !track) return;
    const words = Array.from(track.children) as HTMLElement[];
    let i = 0, snap: number | undefined;
    const fit = () => { flip.style.width = `${words[i].scrollWidth + parseFloat(getComputedStyle(flip).paddingLeft) * 2}px`; };
    fit();
    document.fonts?.ready.then(fit);
    window.addEventListener("resize", fit);
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    const t = reduce ? undefined : setInterval(() => {
      i++;
      track.style.transform = `translateY(${-i * 1.04}em)`;
      fit();
      if (i === words.length - 1) snap = window.setTimeout(() => {
        track.style.transition = "none";
        i = 0;
        track.style.transform = "none";
        fit();
        void track.offsetHeight;
        track.style.transition = "";
      }, 750);
    }, 2200);
    return () => { clearInterval(t); clearTimeout(snap); window.removeEventListener("resize", fit); };
  }, []);
  return (
    <span className="flip" ref={box}>
      <span className="flip-track" ref={reel}>
        {FLIP_WORDS.map((w, i) => <span key={i} aria-hidden={i > 0 || undefined}>{w}</span>)}
      </span>
    </span>
  );
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
    const country = v.country;
    track("start", { domain: v.domain, brand: v.brand, email: v.email, market: country, campaign });
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
      <div className="bg" aria-hidden="true" />
      <div className="glow" aria-hidden="true" />
      <div className="wrap">
        <div className="hero-top">
          <div>
            <span className="tag acc" data-r=""><span className="pulse" aria-hidden="true" />New · AI Visibility Audit by PivotRoots</span>
            <h1 data-split="">
              <Words text="Is AI recommending" />{" "}
              {/* nowrap: the "?" rides along with the reel instead of dropping to its own line */}
              <span className="nb"><Word i={3}><HeadlineFlip /></Word><Word i={4}>?</Word></span>
            </h1>
            <p className="lead" data-r="" style={{ "--d": 4 } as CSSProperties}>
              Your customers stopped Googling and started asking. Enter your domain and we&apos;ll show you exactly what ChatGPT, Gemini, Claude,
              Perplexity, Grok and DeepSeek say — and who they recommend instead.
            </p>
          </div>
          <Orbit />
        </div>

        {!token && (
          <div className="form-wrap" data-r="" style={{ "--d": 5 } as CSSProperties}>
            <Stamp />
            <AuditForm busy={busy} serverError={serverError} onSubmit={start} captchaReset={captchaReset}
              prefill={{ d: params.d || "", e: params.e || "", b: params.b || "", m: params.m || "" }} />
          </div>
        )}

        {!token && (
          <div className="fine" data-r="" style={{ "--d": 6 } as CSSProperties}>
            <span><b>No card.</b> No login. Just a work email.</span>
            <span><b>{MINUTES_LABEL}.</b> Watch it run.</span>
            <span><b>Real answers,</b> not a score you have to trust.</span>
          </div>
        )}

        {token && (
          <div ref={panelRef}>
            <LivePanel host={host} email={email} reused={reused} state={state} />
          </div>
        )}
      </div>

      {!token && (
        <>
          <div className="marq" data-r="" style={{ "--d": 7 } as CSSProperties}>
            <div className="marq-t">
              {[0, 1].map((k) => [...ENGINES, "Google AI Overviews · soon"].map((e) => (
                <span key={`${k}${e}`} className={e.includes("soon") ? "soon" : ""} aria-hidden={k > 0 || undefined}>{e}</span>
              )))}
            </div>
          </div>
          <div className="wrap">
            <a className="alt-card" href={CONTACT_URL} data-r="">
              <span className="av" aria-hidden="true"><i>PR</i><i>AI</i><i>✦</i></span>
              <span className="txt"><b>Rather talk it through?</b> Speak to a PivotRoots strategist</span>
              <span className="ar" aria-hidden="true">→</span>
            </a>
          </div>
        </>
      )}
    </section>
  );
}
