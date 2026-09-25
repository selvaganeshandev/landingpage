/**
 * GET /api/audits/<token>/pdf — a preview of the finished report as a PDF.
 *
 * Fetches the backend's PDF and serves only its first PREVIEW_PAGES pages plus
 * a "locked" page: the full report goes out by email from the PivotRoots team.
 * The backend builds the PDF on request (a few seconds), answers 409 while the
 * audit is still running and 404 for an unknown or expired link; both relayed.
 */
import type { NextRequest } from "next/server";
import { API_URL, TOKEN_RE, forwardHeaders, relayJson, unavailable } from "@/lib/backend";
import { previewPdf } from "@/lib/pdf-preview";

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
  let preview: Uint8Array;
  try {
    preview = (await previewPdf(new Uint8Array(await upstream.arrayBuffer()))).bytes;
  } catch {
    // Never fall back to the full file: if the cut fails, the visitor gets
    // nothing rather than the whole report.
    return Response.json({ error: "We couldn't prepare the PDF preview. Please try again in a moment." }, { status: 502 });
  }
  return new Response(preview as BodyInit, {
    status: 200,
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": `attachment; filename="pivotroots-ai-visibility-audit-${host}-preview.pdf"`,
      "Content-Length": String(preview.byteLength),
      "Cache-Control": "private, no-store",
    },
  });
}
