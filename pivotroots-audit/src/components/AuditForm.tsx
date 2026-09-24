"use client";

/**
 * The three fields. Validates like the original page (domain shape, brand
 * length, email on the site's domain), suggests a brand name from the domain
 * until the visitor types their own, and prefills from email-blast links:
 * ?d=<domain>&e=<email>&b=<brand>.
 */
import { useState } from "react";
import { cleanDomain, emailMatchesDomain, isDomain, isEmail, titleCase } from "@/lib/audit";
import { freeEmailProvider, workEmailMessage } from "@/lib/free-email";
import { TURNSTILE_SITE_KEY } from "@/lib/site";
import { Turnstile } from "./Turnstile";

export interface FormValues {
  domain: string;
  brand: string;
  email: string;
  /** Cloudflare Turnstile token; "" when the human check is not configured. */
  captcha: string;
}

const EMAIL_HINT = "Your work email, on your website's domain — no Gmail or Yahoo. That's how we know it's really you.";

export function AuditForm({ busy, serverError, onSubmit, prefill, captchaReset = 0 }: {
  /** From the email-blast link: ?d=<domain>&e=<email>&b=<brand>. */
  prefill: { d: string; e: string; b: string };
  busy: boolean;
  serverError: string | null;
  onSubmit: (v: FormValues) => void;
  /** Bumped by the parent after each submit: Turnstile tokens are single-use. */
  captchaReset?: number;
}) {
  const [dom, setDom] = useState(() => prefill.d);
  const [brand, setBrand] = useState(() => prefill.b);
  const [brandTouched, setBrandTouched] = useState(() => !!prefill.b);
  const [em, setEm] = useState(() => prefill.e);
  const [captcha, setCaptcha] = useState<string | null>(null);
  const [errs, setErrs] = useState<Partial<Record<keyof FormValues, string>>>({});

  const onDom = (v: string) => {
    setDom(v);
    setErrs((e) => ({ ...e, domain: undefined }));
    if (!brandTouched) { const d = cleanDomain(v); setBrand(d ? titleCase(d) : ""); }
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const d = cleanDomain(dom), b = brand.trim(), m = em.trim().toLowerCase();
    const next: typeof errs = {};
    if (!isDomain(d)) next.domain = "Enter your website, like yourbrand.com";
    if (b.length < 2) next.brand = "Tell us what to call you";
    if (!isEmail(m)) next.email = "Enter a valid email address";
    else {
      // Name the provider before the domain rule: "use an email on acme.com"
      // reads like a bug to someone who just typed their own Gmail.
      const provider = freeEmailProvider(m);
      if (provider) next.email = workEmailMessage(provider);
      else if (!next.domain && !emailMatchesDomain(m, d)) next.email = `Use an email on ${d} — that's how we know it's really you.`;
    }
    if (TURNSTILE_SITE_KEY && !captcha) next.captcha = "Tick the box below to show you're human.";
    setErrs(next);
    if (Object.keys(next).length) {
      const first = (["domain", "brand", "email"] as const).find((k) => next[k]);
      if (first) document.getElementById(first === "domain" ? "dom" : first === "brand" ? "brand" : "em")?.focus();
      return;
    }
    onSubmit({ domain: d, brand: b, email: m, captcha: captcha || "" });
  };

  return (
    <form className="form" onSubmit={submit} noValidate aria-label="Run a free AI visibility audit">
      <div className="row">
        <div className={`field${errs.domain ? " err" : ""}`}>
          <label htmlFor="dom">Website</label>
          <div className="in">
            <span className="pre">https://</span>
            <input id="dom" type="text" inputMode="url" autoComplete="url" placeholder="yourbrand.com" value={dom}
              onChange={(e) => onDom(e.target.value)} disabled={busy} required />
          </div>
          <div className="hint">{errs.domain || ""}</div>
        </div>
        <div className={`field${errs.brand ? " err" : ""}`}>
          <label htmlFor="brand">Brand name</label>
          <div className="in">
            <input id="brand" type="text" autoComplete="organization" placeholder="Your Brand" value={brand}
              onChange={(e) => { setBrand(e.target.value); setBrandTouched(!!e.target.value); setErrs((x) => ({ ...x, brand: undefined })); }}
              disabled={busy} required />
          </div>
          <div className="hint">{errs.brand || ""}</div>
        </div>
      </div>
      <div className="row last">
        <div className={`field${errs.email ? " err" : ""}`}>
          <label htmlFor="em">Work email</label>
          <div className="in">
            <input id="em" type="email" autoComplete="email" placeholder="you@yourbrand.com" value={em}
              onChange={(e) => { setEm(e.target.value); setErrs((x) => ({ ...x, email: undefined })); }} disabled={busy} required />
          </div>
          <div className="hint">{errs.email || EMAIL_HINT}</div>
        </div>
        <div className="go">
          <button className="btn acc" type="submit" disabled={busy}>{busy ? "Starting…" : "Get my free audit →"}</button>
        </div>
      </div>
      {TURNSTILE_SITE_KEY && (
        <div className={`captcha${errs.captcha ? " err" : ""}`}>
          <Turnstile siteKey={TURNSTILE_SITE_KEY} resetKey={captchaReset}
            onToken={(t) => { setCaptcha(t); if (t) setErrs((x) => ({ ...x, captcha: undefined })); }} />
          {errs.captcha && <div className="hint">{errs.captcha}</div>}
        </div>
      )}
      {serverError && <div className="msg" role="alert">{serverError}</div>}
    </form>
  );
}
