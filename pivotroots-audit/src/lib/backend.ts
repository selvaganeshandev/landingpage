/**
 * Server-side only: how the route handlers reach the PromptMaxx backend.
 *
 * The browser never sees AUDIT_API_URL. The visitor's IP is forwarded so the
 * backend's per-IP daily cap (AUDIT_PER_IP_DAILY) still counts visitors, not
 * this server — the backend reads the first hop of X-Forwarded-For. If the host
 * running this app does not set X-Forwarded-For / X-Real-IP, every visitor
 * shares one cap; deploy behind a proxy that does (nginx, Vercel, Cloudflare).
 */
import "server-only";
import type { NextRequest } from "next/server";

// No fallback on purpose: a test build must never quietly start audits on
// production. Set AUDIT_API_URL in .env.local (local stack) or the host's env.
export const API_URL = (process.env.AUDIT_API_URL || "").replace(/\/$/, "");
if (!API_URL) throw new Error("AUDIT_API_URL is not set — see pivotroots-audit/.env.example");
export const DEFAULT_COUNTRY = (process.env.AUDIT_DEFAULT_COUNTRY || "in").toLowerCase().slice(0, 2);

export const TOKEN_RE = /^[A-Za-z0-9_-]{8,64}$/;

export function visitorIp(req: NextRequest): string {
  const fwd = req.headers.get("x-forwarded-for") || "";
  const first = fwd.split(",")[0].trim();
  return first || req.headers.get("x-real-ip") || "";
}

export function forwardHeaders(req: NextRequest, extra: Record<string, string> = {}): HeadersInit {
  const ip = visitorIp(req);
  return {
    Accept: "application/json",
    "User-Agent": "pivotroots-audit-lp",
    ...(ip ? { "X-Forwarded-For": ip } : {}),
    ...extra,
  };
}

/** Pass the backend's JSON body and status straight through. */
export async function relayJson(upstream: Response): Promise<Response> {
  const text = await upstream.text();
  return new Response(text || "{}", {
    status: upstream.status,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}

export function unavailable(): Response {
  return Response.json({ error: "The audit engine is unavailable right now." }, { status: 503, headers: { "Cache-Control": "no-store" } });
}
