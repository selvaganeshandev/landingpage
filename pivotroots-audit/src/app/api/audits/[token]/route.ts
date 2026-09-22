/**
 * GET /api/audits/<token> — progress while it runs, the report once it is DONE.
 * Relays the backend's public status endpoint (404 = unknown or expired link).
 */
import type { NextRequest } from "next/server";
import { API_URL, TOKEN_RE, forwardHeaders, relayJson, unavailable } from "@/lib/backend";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest, ctx: { params: Promise<{ token: string }> }) {
  const { token } = await ctx.params;
  if (!TOKEN_RE.test(token)) return Response.json({ error: "This audit link has expired or never existed." }, { status: 404 });
  let upstream: Response;
  try {
    upstream = await fetch(`${API_URL}/audits/public/${encodeURIComponent(token)}/`, {
      headers: forwardHeaders(req),
      cache: "no-store",
      signal: AbortSignal.timeout(20_000),
    });
  } catch {
    return unavailable();
  }
  return relayJson(upstream);
}
