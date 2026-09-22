"use client";

/**
 * Polls one audit until it is DONE or FAIL, and keeps a rolling feed of the
 * engine answers seen so far (the backend sends only the newest few each poll,
 * so the page remembers what scrolled past).
 */
import { useEffect, useRef, useState } from "react";
import { AuditApiError, getAudit, type LiveRow, type PublicAudit } from "./audit";

const POLL_MS = 2500;
const FEED_MAX = 6;

export interface AuditState {
  audit: PublicAudit | null;
  feed: LiveRow[];
  error: { status?: number; message: string } | null;
}

const rowKey = (r: LiveRow) => `${r.engine}|${r.prompt}|${r.at}`;

/**
 * `token` is set once per page life (null → the new audit, or fixed from the
 * URL), so state starts empty and is never reset here.
 */
export function useAudit(token: string | null): AuditState {
  const [audit, setAudit] = useState<PublicAudit | null>(null);
  const [feed, setFeed] = useState<LiveRow[]>([]);
  const [error, setError] = useState<AuditState["error"]>(null);
  const seen = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    seen.current = new Set();

    const tick = async () => {
      try {
        const a = await getAudit(token);
        if (cancelled) return;
        setAudit(a);
        setError(null);
        const fresh = (a.live || []).filter((r) => !seen.current.has(rowKey(r)));
        if (fresh.length) {
          fresh.forEach((r) => seen.current.add(rowKey(r)));
          // Backend order is newest-first; the feed shows newest on top.
          setFeed((prev) => [...fresh, ...prev].slice(0, FEED_MAX));
        }
        if (a.status === "INIT" || a.status === "PROC") timer = setTimeout(tick, POLL_MS);
      } catch (e) {
        if (cancelled) return;
        const err = e as AuditApiError;
        setError({ status: err.status, message: err.message || "We lost the connection. Retrying…" });
        // A 404 is final (expired / unknown); anything else is worth another try.
        if (err.status !== 404) timer = setTimeout(tick, POLL_MS * 2);
      }
    };
    tick();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [token]);

  return { audit, feed, error };
}
