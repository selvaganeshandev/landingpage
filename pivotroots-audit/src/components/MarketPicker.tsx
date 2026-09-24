"use client";

/**
 * Market picker for the audit form: which country's buyers the engines are
 * asked as. A listbox rather than a native <select> so each option can show
 * its code, cities and a "your location" marker in the page's own style.
 *
 * The panel is position:fixed and placed from the trigger's rect, because the
 * form clips its overflow (rounded corners) and would cut an absolute panel.
 */
import { useCallback, useEffect, useId, useRef, useState } from "react";
import { MARKETS } from "@/lib/site";

function Pin() {
  return (
    <svg width="12" height="14" viewBox="0 0 12 14" aria-hidden="true">
      <path d="M6 13.2S1 8.4 1 5.2a5 5 0 0 1 10 0c0 3.2-5 8-5 8Z" fill="currentColor" />
      <circle cx="6" cy="5.2" r="1.8" fill="#fff" />
    </svg>
  );
}

export function MarketPicker({ value, detected, onChange, disabled }: {
  value: string;
  /** Market guessed from the visitor's browser, "" if unknown. */
  detected: string;
  onChange: (code: string) => void;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [pos, setPos] = useState<{ top: number; left: number; width: number } | null>(null);
  const btn = useRef<HTMLButtonElement>(null);
  const list = useRef<HTMLUListElement>(null);
  const listId = useId();
  const current = MARKETS.find((m) => m.code === value) ?? MARKETS[0];

  // Hang the panel under the whole field (label, trigger and hint), aligned to
  // its left edge, kept on screen at narrow widths.
  const place = useCallback(() => {
    const field = btn.current?.closest(".field") ?? btn.current;
    const r = field?.getBoundingClientRect();
    if (!r) return;
    const width = Math.min(Math.max(320, r.width), window.innerWidth - 24);
    const left = Math.min(r.left, window.innerWidth - width - 12);
    setPos({ top: r.bottom + 10, left: Math.max(12, left), width });
  }, []);

  const openList = () => {
    if (disabled) return;
    place();
    setActive(Math.max(0, MARKETS.findIndex((m) => m.code === value)));
    setOpen(true);
  };
  const choose = (code: string) => {
    onChange(code);
    setOpen(false);
    btn.current?.focus();
  };

  useEffect(() => {
    if (!open) return;
    list.current?.focus();
    const close = (e: MouseEvent) => {
      if (!list.current?.contains(e.target as Node) && !btn.current?.contains(e.target as Node)) setOpen(false);
    };
    const shut = () => setOpen(false);
    document.addEventListener("mousedown", close);
    window.addEventListener("resize", shut);
    window.addEventListener("scroll", shut, true);
    return () => {
      document.removeEventListener("mousedown", close);
      window.removeEventListener("resize", shut);
      window.removeEventListener("scroll", shut, true);
    };
  }, [open]);

  const onListKey = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setActive((i) => (i + 1) % MARKETS.length); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((i) => (i - 1 + MARKETS.length) % MARKETS.length); }
    else if (e.key === "Home") { e.preventDefault(); setActive(0); }
    else if (e.key === "End") { e.preventDefault(); setActive(MARKETS.length - 1); }
    else if (e.key === "Enter" || e.key === " ") { e.preventDefault(); choose(MARKETS[active].code); }
    else if (e.key === "Escape" || e.key === "Tab") { setOpen(false); btn.current?.focus(); }
  };

  return (
    <>
      <button ref={btn} type="button" id="mkt" className="mk-trigger" disabled={disabled}
        aria-haspopup="listbox" aria-expanded={open} aria-controls={listId}
        onClick={() => (open ? setOpen(false) : openList())}
        onKeyDown={(e) => { if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); openList(); } }}>
        <span className="mk-code">{current.code.toUpperCase()}</span>
        <span className="mk-name">{current.name}</span>
        <svg className="mk-chev" width="12" height="8" viewBox="0 0 12 8" aria-hidden="true"><path d="M1 1l5 5 5-5" fill="none" stroke="currentColor" strokeWidth="2" /></svg>
      </button>

      {open && pos && (
        <ul ref={list} id={listId} role="listbox" tabIndex={-1} aria-label="Market" className="mk-list"
          aria-activedescendant={`${listId}-${MARKETS[active].code}`}
          style={{ top: pos.top, left: pos.left, width: pos.width }} onKeyDown={onListKey}>
          <li className="mk-head" role="presentation">Where do your buyers search?</li>
          {MARKETS.map((m, i) => (
            <li key={m.code} id={`${listId}-${m.code}`} role="option" aria-selected={m.code === value}
              className={`mk-opt${i === active ? " act" : ""}${m.code === value ? " sel" : ""}`}
              onMouseEnter={() => setActive(i)} onClick={() => choose(m.code)}>
              <span className="mk-code">{m.code.toUpperCase()}</span>
              <span className="mk-txt">
                <b>{m.name}</b>
                <small>{m.cities}</small>
              </span>
              {m.code === detected && <span className="mk-here"><Pin /> You&apos;re here</span>}
              {m.code === value && <span className="mk-tick" aria-hidden="true">✓</span>}
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

export { Pin };
