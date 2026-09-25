/**
 * POST /api/audits — start an audit.
 *
 * Body: { url, email, brand_name?, country?, campaign?, turnstile_token? }. Re-validates what the
 * form already checked (the endpoint is reachable without the form), then
 * POSTs to the backend's public /audits/ and relays its answer: 201 new,
 * 200 reused (same host audited inside the repeat window), 400/429/503 refused.
 */
import type { NextRequest } from "next/server";
import { API_URL, DEFAULT_COUNTRY, forwardHeaders, relayJson, unavailable, verifyHuman, visitorIp } from "@/lib/backend";
import { cleanDomain, isDomain, isEmail } from "@/lib/audit";
import { freeEmailProvider, workEmailMessage } from "@/lib/free-email";
import { isMarket } from "@/lib/site";
import { canReceiveMail } from "@/lib/email-check";

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return Response.json({ error: "Send a JSON body." }, { status: 400 });
  }

  const domain = cleanDomain(String(body.url ?? ""));
  const email = String(body.email ?? "").trim().toLowerCase();
  const brand = String(body.brand_name ?? "").trim().slice(0, 255);
  // Only the markets the form offers; anything else falls back to the default
  // rather than running an audit for a market the page never promised.
  const asked = String(body.country ?? "").toLowerCase().slice(0, 2);
  const country = isMarket(asked) ? asked : DEFAULT_COUNTRY;

  if (!isDomain(domain)) return Response.json({ error: "Enter your website, like yourbrand.com" }, { status: 400 });
  if (!isEmail(email)) return Response.json({ error: "Enter a valid work email address." }, { status: 400 });
  const freeProvider = freeEmailProvider(email);
  if (freeProvider) return Response.json({ error: workEmailMessage(freeProvider) }, { status: 400 });
  // The full report is emailed: refuse an address whose domain takes no mail.
  if (!(await canReceiveMail(email))) {
    return Response.json({
      error: `We can't deliver email to ${email.split("@")[1]} — the full report is sent by email, so check the address and try again.`,
    }, { status: 400 });
  }
  // Last check before anything reaches the backend, so a failed human check
  // never costs an audit or counts against the visitor's daily cap.
  if (!(await verifyHuman(String(body.turnstile_token ?? ""), visitorIp(req)))) {
    return Response.json({ error: "We couldn't confirm you're human. Tick the check box and try again." }, { status: 400 });
  }

  let upstream: Response;
  try {
    upstream = await fetch(`${API_URL}/audits/`, {
      method: "POST",
      headers: forwardHeaders(req, { "Content-Type": "application/json" }),
      body: JSON.stringify({ url: domain, email, brand_name: brand, country }),
      cache: "no-store",
      signal: AbortSignal.timeout(20_000),
    });
  } catch {
    return unavailable();
  }
  return relayJson(upstream);
}
