/**
 * Personal mailboxes the audit form refuses: Google, Yahoo and Microsoft only.
 *
 * The audit is a lead and the full report is emailed, so it should reach a
 * work inbox. Every other address is accepted — including company emails on a
 * different domain from the website (agencies, group companies), so there is
 * no same-domain rule. Exact-match on the address's domain.
 */
const FREE_EMAIL_DOMAINS = new Set([
  // Google
  "gmail.com", "googlemail.com",
  // Yahoo, incl. the country mailboxes common in India and the UK
  "yahoo.com", "yahoo.co.in", "yahoo.in", "yahoo.co.uk", "yahoo.ca", "yahoo.com.au",
  "yahoo.fr", "yahoo.de", "yahoo.es", "yahoo.it", "yahoo.co.jp", "ymail.com", "rocketmail.com",
  // Microsoft
  "hotmail.com", "hotmail.co.uk", "hotmail.co.in", "hotmail.fr", "outlook.com", "outlook.in",
  "live.com", "live.co.uk", "msn.com",
]);

/** The provider's domain when the address is a personal one, else "". */
export function freeEmailProvider(email: string): string {
  const domain = (email.split("@")[1] || "").trim().toLowerCase().replace(/^www\./, "");
  return FREE_EMAIL_DOMAINS.has(domain) ? domain : "";
}

/** What to tell someone who typed a personal address. */
export function workEmailMessage(provider: string): string {
  const article = /^[aeiou]/i.test(provider) ? "an" : "a";
  return `Use your work email, not ${article} ${provider} address — the report goes to whoever can act on it.`;
}
