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
/** Pages of the report PDF a visitor can download; the rest is emailed by the team. */
export const PDF_PREVIEW_PAGES = 4;

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
/**
 * Markets the audit can run for — the same list and codes as the app's audit
 * screen (frontend/src/types/audit.ts AUDIT_COUNTRIES). The code is sent as
 * `country`; prompts and rankings run as a buyer in that market.
 */
export const MARKETS = [
  { code: "in", name: "India", cities: "Mumbai · Delhi · Bangalore" },
  { code: "ae", name: "UAE", cities: "Dubai · Abu Dhabi" },
  { code: "us", name: "United States", cities: "New York · San Francisco" },
  { code: "gb", name: "United Kingdom", cities: "London · Manchester" },
  { code: "sg", name: "Singapore", cities: "Singapore" },
  { code: "au", name: "Australia", cities: "Sydney · Melbourne" },
  { code: "ca", name: "Canada", cities: "Toronto · Vancouver" },
  { code: "de", name: "Germany", cities: "Berlin · Munich" },
] as const;
export const DEFAULT_MARKET = "in";
export const isMarket = (c: string) => MARKETS.some((m) => m.code === c);

/**
 * Best guess at the visitor's market from the browser alone — time zone first,
 * then the region in their language settings. No permission prompt, no IP
 * lookup, nothing leaves the browser. Returns "" when it can't tell.
 */
export function detectMarket(): string {
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "";
    if (/^Asia\/(Kolkata|Calcutta)$/.test(tz)) return "in";
    if (tz === "Asia/Dubai") return "ae";
    if (tz === "Asia/Singapore") return "sg";
    if (/^(Europe\/London|Europe\/Belfast)$/.test(tz)) return "gb";
    if (/^(Europe\/Berlin|Europe\/Busingen)$/.test(tz)) return "de";
    if (tz.startsWith("Australia/")) return "au";
    if (/^America\/(Toronto|Vancouver|Edmonton|Winnipeg|Halifax|St_Johns|Regina|Montreal|Moncton|Whitehorse|Yellowknife|Iqaluit)$/.test(tz)) return "ca";
    if (/^(America\/(New_York|Chicago|Denver|Los_Angeles|Phoenix|Anchorage|Detroit|Boise|Indiana\/.+|Kentucky\/.+)|Pacific\/Honolulu)$/.test(tz)) return "us";
  } catch { /* no Intl — fall through */ }
  for (const lang of (typeof navigator !== "undefined" && navigator.languages) || []) {
    const region = lang.split("-")[1]?.toLowerCase();
    const code = region === "uk" ? "gb" : region;
    if (code && isMarket(code)) return code;
  }
  return "";
}

/** Cloudflare Turnstile site key (public). Empty = no human check on the form. */
export const TURNSTILE_SITE_KEY = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY || "";
export const SHOW_POWERED_BY =process.env.NEXT_PUBLIC_SHOW_POWERED_BY === "true";

/** The engine's platform labels, shortened for a 92px chip. */
export function engineLabel(platform: string): string {
  if (platform === "Google Gemini") return "Gemini";
  return platform;
}
