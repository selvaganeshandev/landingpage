"use client";

/**
 * "Run a free AI visibility audit" — the landing page's lead capture.
 *
 * POSTs the URL to the backend's public /audits/ endpoint and sends the
 * visitor to the app's public report page, which shows live progress and then
 * the report. The backend applies the repeat window and daily caps; the two
 * error codes a visitor can actually hit (429, 503) get plain-language copy.
 *
 * Both hosts are build-time env vars with production defaults, so a build
 * without NEXT_PUBLIC_* still points at the live stack — never at localhost.
 */
import { useState } from "react";
import { ArrowRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

const API_URL = (process.env.NEXT_PUBLIC_API_URL || "https://promtmaxxservice.rankmax.io").replace(/\/$/, "");
const APP_URL = (process.env.NEXT_PUBLIC_APP_URL || "https://app.promptmaxx.co").replace(/\/$/, "");

const MARKETS: { code: string; label: string }[] = [
  { code: "in", label: "India" },
  { code: "ae", label: "UAE" },
  { code: "us", label: "USA" },
  { code: "gb", label: "UK" },
  { code: "sg", label: "Singapore" },
  { code: "au", label: "Australia" },
];

const inputClass =
  "h-12 w-full rounded-full border border-gray-200 bg-white px-5 text-base text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary";

export function AuditForm() {
  const [url, setUrl] = useState("");
  const [email, setEmail] = useState("");
  const [country, setCountry] = useState("in");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const site = url.trim();
    if (!site) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/audits/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: site, country, email: email.trim() }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        if (res.status === 429) setError(data.error || "We've hit today's audit limit. Please try again tomorrow.");
        else if (res.status === 503) setError("The audit engine is taking a break. Please try again in a few minutes.");
        else setError(data.error || "Enter a valid website address, e.g. example.com.");
        return;
      }
      window.location.assign(`${APP_URL}/audit/${data.public_token}`);
    } catch {
      setError("We couldn't reach the audit engine. Check your connection and try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="max-w-3xl mx-auto" aria-label="Run a free AI visibility audit">
      <div className="flex flex-col sm:flex-row gap-3">
        <input
          type="text"
          inputMode="url"
          autoComplete="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Enter your website, e.g. yourdomain.com"
          className={`${inputClass} flex-[2]`}
          disabled={busy}
          required
          aria-label="Website"
        />
        <select
          value={country}
          onChange={(e) => setCountry(e.target.value)}
          className={`${inputClass} sm:w-40`}
          disabled={busy}
          aria-label="Market"
        >
          {MARKETS.map((m) => (
            <option key={m.code} value={m.code}>{m.label}</option>
          ))}
        </select>
        <Button
          type="submit"
          disabled={busy || !url.trim()}
          className="bg-primary text-white hover:bg-primary/90 rounded-full h-12 !px-8 text-base font-medium cursor-pointer"
        >
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
          <span>{busy ? "Starting…" : "Get my free audit"}</span>
          {!busy && <ArrowRight className="w-4 h-4" />}
        </Button>
      </div>
      <div className="mt-3 flex flex-col sm:flex-row items-center gap-3">
        <input
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Email (optional — we'll send you the link when it's ready)"
          className={`${inputClass} h-10 text-sm flex-1`}
          disabled={busy}
          aria-label="Email"
        />
      </div>
      <p className="mt-3 text-center text-xs text-gray-500">
        Buyer prompts asked on the AI engines, scored 0–100, with the three quick wins that move it. About 3 minutes. No card, no login.
      </p>
      {error && (
        <p role="alert" className="mt-3 text-center text-sm text-red-600">{error}</p>
      )}
    </form>
  );
}
