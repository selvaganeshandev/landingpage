/**
 * POST /api/audits — start an audit.
 *
 * Body: { url, email, brand_name?, country?, campaign? }. Re-validates what the
 * form already checked (the endpoint is reachable without the form), then
 * POSTs to the backend's public /audits/ and relays its answer: 201 new,
 * 200 reused (same host audited inside the repeat window), 400/429/503 refused.
 */
import type { NextRequest } from "next/server";
import { API_URL, DEFAULT_COUNTRY, forwardHeaders, relayJson, unavailable } from "@/lib/backend";
import { cleanDomain, emailMatchesDomain, isDomain, isEmail } from "@/lib/audit";

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
  const country = (String(body.country ?? "") || DEFAULT_COUNTRY).toLowerCase().slice(0, 2);

  if (!isDomain(domain)) return Response.json({ error: "Enter your website, like yourbrand.com" }, { status: 400 });
  if (!isEmail(email)) return Response.json({ error: "Enter a valid work email address." }, { status: 400 });
  if (!emailMatchesDomain(email, domain)) {
    return Response.json({ error: `Use an email on ${domain} — that's how we know it's really you.` }, { status: 400 });
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
