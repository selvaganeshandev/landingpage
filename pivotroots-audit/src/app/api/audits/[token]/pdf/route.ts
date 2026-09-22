/**
 * GET /api/audits/<token>/pdf — the finished report as a PDF download.
 *
 * Streams the backend's PDF through under a PivotRoots filename. The backend
 * builds the PDF on request (a few seconds), answers 409 while the audit is
 * still running and 404 for an unknown or expired link; both are relayed.
 */
import type { NextRequest } from "next/server";
import { API_URL, TOKEN_RE, forwardHeaders, relayJson, unavailable } from "@/lib/backend";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest, ctx: { params: Promise<{ token: string }> }) {
  const { token } = await ctx.params;
  if (!TOKEN_RE.test(token)) return Response.json({ error: "This audit link has expired or never existed." }, { status: 404 });
  let upstream: Response;
  try {
    upstream = await fetch(`${API_URL}/audits/public/${encodeURIComponent(token)}/pdf/`, {
      headers: forwardHeaders(req, { Accept: "application/pdf, application/json" }),
      cache: "no-store",
      signal: AbortSignal.timeout(120_000),
    });
  } catch {
    return unavailable();
  }
  if (!upstream.ok || !(upstream.headers.get("content-type") || "").includes("application/pdf")) {
    return relayJson(upstream);
  }
  // The backend names the file after the host: promptmaxx-audit-<host>.pdf.
  const host = (upstream.headers.get("content-disposition") || "").match(/promptmaxx-audit-([^"]+)\.pdf/)?.[1] || "report";
  return new Response(upstream.body, {
    status: 200,
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": `attachment; filename="pivotroots-ai-visibility-audit-${host}.pdf"`,
      "Cache-Control": "private, no-store",
      ...(upstream.headers.get("content-length") ? { "Content-Length": upstream.headers.get("content-length")! } : {}),
    },
  });
}
