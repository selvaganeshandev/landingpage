/**
 * Consumer mailbox providers and throwaway-address services.
 *
 * The audit is a lead: it has to reach someone who can act on it, and the
 * same-domain rule is what stops a competitor running a brand's audit. A
 * personal address defeats both, so it is refused with a message that says
 * what to do instead — "use a work email" — rather than the generic
 * domain-mismatch line, which reads like a bug when you typed your own Gmail.
 *
 * Exact-match on the address's domain only. A provider whose domain is also a
 * real company's (zoho.com, proton.me's own staff) is deliberately left out:
 * refusing those would block that company's own employees from auditing their
 * own site, which is a worse failure than letting one personal address through.
 *
 * Add to INDIA / UAE rows as PivotRoots sees them in the leads table.
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
  // Apple
  "icloud.com", "me.com", "mac.com",
  // Other consumer providers
  "aol.com", "gmx.com", "gmx.net", "mail.com", "mail.ru", "yandex.com", "yandex.ru",
  "zohomail.com", "protonmail.com", "pm.me", "tutanota.com", "tuta.io",
  // India
  "rediffmail.com", "rediff.com", "indiatimes.com", "sify.com",
  // Asia-Pacific
  "qq.com", "163.com", "126.com", "sina.com", "naver.com", "daum.net", "hanmail.net",
  // Throwaway / disposable
  "mailinator.com", "yopmail.com", "guerrillamail.com", "sharklasers.com",
  "10minutemail.com", "temp-mail.org", "tempmail.com", "trashmail.com", "dispostable.com",
  "getnada.com", "maildrop.cc", "fakeinbox.com",
]);

/** The provider's domain when the address is a personal one, else "". */
export function freeEmailProvider(email: string): string {
  const domain = (email.split("@")[1] || "").trim().toLowerCase().replace(/^www\./, "");
  return FREE_EMAIL_DOMAINS.has(domain) ? domain : "";
}

/** What to tell someone who typed a personal address. */
export function workEmailMessage(provider: string): string {
  return `Use your work email, not a ${provider} address — the report goes to whoever can act on it.`;
}
