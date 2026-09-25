/**
 * Server-side only: can this address's domain receive mail at all?
 *
 * The full report is emailed, so an address whose domain has no mail server
 * is refused before an audit is spent on it. Checks the domain's MX records;
 * a "null MX" (RFC 7505, exchange ".") means the domain accepts no mail.
 * Only a definite "no such domain / no MX" fails — a DNS timeout or server
 * error lets the visitor through rather than blocking them on our hiccup.
 */
import "server-only";
import { resolveMx } from "node:dns/promises";

const DEFINITE_MISS = new Set(["ENOTFOUND", "ENODATA", "NXDOMAIN"]);

export async function canReceiveMail(email: string): Promise<boolean> {
  const domain = email.split("@")[1]?.trim().toLowerCase();
  if (!domain) return false;
  try {
    const mx = await Promise.race([
      resolveMx(domain),
      new Promise<never>((_, reject) => setTimeout(() => reject(Object.assign(new Error("timeout"), { code: "ETIMEOUT" })), 5000)),
    ]);
    return mx.some((r) => r.exchange && r.exchange !== ".");
  } catch (e) {
    return !DEFINITE_MISS.has((e as { code?: string }).code || "");
  }
}
