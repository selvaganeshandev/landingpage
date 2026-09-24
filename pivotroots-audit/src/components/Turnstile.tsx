"use client";

/**
 * Cloudflare Turnstile widget. Loads Cloudflare's script once, renders the
 * widget explicitly and reports the token (null when it expires or errors).
 * Tokens are single-use: bump `resetKey` after a submit so a retry gets a
 * fresh one. The token is verified server-side in /api/audits.
 */
import { useEffect, useRef } from "react";

interface TurnstileApi {
  render: (el: HTMLElement, opts: Record<string, unknown>) => string;
  reset: (id: string) => void;
  remove: (id: string) => void;
}
declare global {
  interface Window { turnstile?: TurnstileApi }
}

const SCRIPT_SRC = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
let scriptPromise: Promise<void> | null = null;

function loadScript(): Promise<void> {
  if (window.turnstile) return Promise.resolve();
  if (!scriptPromise) {
    scriptPromise = new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = SCRIPT_SRC;
      s.async = true;
      s.onload = () => resolve();
      s.onerror = () => { scriptPromise = null; reject(new Error("turnstile script failed")); };
      document.head.appendChild(s);
    });
  }
  return scriptPromise;
}

export function Turnstile({ siteKey, onToken, resetKey }: { siteKey: string; onToken: (t: string | null) => void; resetKey: number }) {
  const el = useRef<HTMLDivElement>(null);
  const id = useRef<string | null>(null);
  const cb = useRef(onToken);
  useEffect(() => { cb.current = onToken; }, [onToken]);

  useEffect(() => {
    let gone = false;
    loadScript().then(() => {
      if (gone || !el.current || !window.turnstile || id.current) return;
      id.current = window.turnstile.render(el.current, {
        sitekey: siteKey,
        theme: "light",
        size: "flexible",
        callback: (t: string) => cb.current(t),
        "expired-callback": () => cb.current(null),
        "error-callback": () => cb.current(null),
      });
    }).catch(() => cb.current(null));
    return () => {
      gone = true;
      if (id.current && window.turnstile) window.turnstile.remove(id.current);
      id.current = null;
    };
  }, [siteKey]);

  useEffect(() => {
    if (resetKey && id.current && window.turnstile) {
      window.turnstile.reset(id.current);
      cb.current(null);
    }
  }, [resetKey]);

  return <div ref={el} className="captcha-box" />;
}
