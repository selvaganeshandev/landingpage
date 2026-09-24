/**
 * Every number and link the page copy quotes, in one place.
 *
 * ENGINES / PROMPT_COUNT should match what the backend is configured to run
 * (AUDIT_ENGINES and AUDIT_PROMPT_COUNT in the backend .env) — the live panel
 * shows the engine's real counters regardless, but the static copy ("6 engines",
 * "24 questions") is only honest if these agree.
 */
export const ENGINES = ["ChatGPT", "Gemini", "Claude", "Perplexity", "Grok", "DeepSeek"] as const;
export const ENGINE_COUNT = ENGINES.length;
export const PROMPT_COUNT = 24;
export const MINUTES_LABEL = "2 minutes";
export const REPORT_TTL_DAYS = 30;

/**
 * Sub-path the app is served under (NEXT_PUBLIC_BASE_PATH, e.g. /pmx-landingpage).
 * Next prefixes <Link> and its assets itself, but not fetch, <a href> or
 * history.replaceState — every raw in-app path goes through this.
 */
export const BASE_PATH = (process.env.NEXT_PUBLIC_BASE_PATH || "").replace(/\/$/, "");
export const HOME_AUDIT_HREF = `${BASE_PATH}/#audit`;

export const CONTACT_URL =process.env.NEXT_PUBLIC_CONTACT_URL || "https://www.pivotroots.com/contact";
export const PRIVACY_URL = "https://www.pivotroots.com/privacy-policy";
export const TERMS_URL = "https://www.pivotroots.com/terms-and-conditions";
export const LOGO_URL = "https://www.pivotroots.com/images/logo_black.svg";
/** Cloudflare Turnstile site key (public). Empty = no human check on the form. */
export const TURNSTILE_SITE_KEY = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY || "";
export const SHOW_POWERED_BY =process.env.NEXT_PUBLIC_SHOW_POWERED_BY === "true";

/** The engine's platform labels, shortened for a 92px chip. */
export function engineLabel(platform: string): string {
  if (platform === "Google Gemini") return "Gemini";
  return platform;
}
