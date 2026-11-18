"use client";

/**
 * Page-wide motion, wired once after hydration so the sections can stay
 * server components that only carry markers:
 *
 *   .rv               fades up when it scrolls into view (.in)
 *   [data-io]         gets .in on view without the fade (charts inside draw)
 *   [data-count]      counts up from 0 when its section is revealed
 *   [data-tz]         live office clock
 *   #nav              hairline border once the page scrolls
 *
 * Content is in the HTML regardless; hidden starting states only apply under
 * html.js (set before paint in the layout), and reduced-motion visitors get
 * everything shown and still.
 */
import { useEffect } from "react";

export function MotionRoot() {
  useEffect(() => {
    const $$ = (s: string, r: ParentNode = document) => Array.from(r.querySelectorAll<HTMLElement>(s));
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

    const count = (el: HTMLElement) => {
      const to = Number(el.dataset.count);
      if (reduce || !Number.isFinite(to)) { el.textContent = String(to); return; }
      const t0 = performance.now(), dur = 1200 + to * 6;
      const tick = (t: number) => {
        const p = Math.min(1, (t - t0) / dur);
        el.textContent = String(Math.round(to * (1 - Math.pow(1 - p, 3))));
        if (p < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    };
    // Counters still below the fold start at 0 so they don't jump on reveal.
    if (!reduce) $$("[data-count]").forEach((el) => { if (el.getBoundingClientRect().top > innerHeight) el.textContent = "0"; });

    const io = new IntersectionObserver((entries) => entries.forEach((e) => {
      if (!e.isIntersecting) return;
      const el = e.target as HTMLElement;
      el.classList.add("in");
      $$("[data-count]", el).forEach((c) => { if (!c.dataset.done) { c.dataset.done = "1"; count(c); } });
      io.unobserve(el);
    }), { threshold: 0.15, rootMargin: "0px 0px -5% 0px" });
    $$(".rv,[data-io]").forEach((el) => io.observe(el));

    const clocks = $$("[data-tz]");
    const tickClock = () => clocks.forEach((c) => {
      c.textContent = new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: c.dataset.tz }).format(new Date());
    });
    tickClock();
    const clockTimer = setInterval(tickClock, 15000);

    const nav = document.getElementById("nav");
    const onScroll = () => nav?.classList.toggle("scrolled", scrollY > 10);
    onScroll();
    addEventListener("scroll", onScroll, { passive: true });

    return () => { io.disconnect(); clearInterval(clockTimer); removeEventListener("scroll", onScroll); };
  }, []);

  return null;
}
