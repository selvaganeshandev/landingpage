"use client";

/**
 * Page-wide motion, wired once after hydration so the sections can stay
 * server components that only carry markers:
 *
 *   [data-r] / [data-split]   reveal on scroll (.in)
 *   [data-count]              count up from 0 when revealed
 *   [data-tz]                 live office clock
 *   .tilt / .mag              card tilt and magnetic buttons (mouse only)
 *   #prog, .nav, .nav-links   scroll progress, shrink, active-section underline
 *   #how                      pinned three-step story (desktop)
 *   #finalH .fw               headline lights up word by word
 *   #dash, #wordmark          dashboard tilt-in, footer wordmark fill
 *   .faq details              smooth open/close
 *
 * Content is in the HTML regardless; the hidden starting states only apply
 * under html.js (set before paint in the layout), and reduced-motion visitors
 * get everything shown and still.
 */
import { useEffect } from "react";

const clamp = (v: number) => Math.min(1, Math.max(0, v));

export function MotionRoot() {
  useEffect(() => {
    const $$ = <T extends Element = HTMLElement>(s: string, r: ParentNode = document): T[] => Array.from(r.querySelectorAll<T>(s));
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    const fine = matchMedia("(hover: hover)").matches;
    const off: (() => void)[] = [];
    const on = <K extends keyof HTMLElementEventMap>(el: HTMLElement | Window, ev: K, fn: (e: HTMLElementEventMap[K]) => void, opts?: AddEventListenerOptions) => {
      el.addEventListener(ev, fn as EventListener, opts);
      off.push(() => el.removeEventListener(ev, fn as EventListener, opts));
    };

    /* counters */
    const count = (el: HTMLElement) => {
      const to = Number(el.dataset.count);
      if (reduce || !Number.isFinite(to)) { el.textContent = String(to); return; }
      const t0 = performance.now(), dur = 1400 + to * 6;
      const tick = (t: number) => {
        const p = Math.min(1, (t - t0) / dur);
        el.textContent = String(Math.round(to * (1 - Math.pow(1 - p, 3))));
        if (p < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    };
    // Counters still below the fold start at 0 so they don't jump on reveal.
    if (!reduce) $$("[data-count]").forEach((el) => { if (el.getBoundingClientRect().top > innerHeight) el.textContent = "0"; });

    /* reveal on scroll */
    const io = new IntersectionObserver((entries) => entries.forEach((e) => {
      if (!e.isIntersecting) return;
      const el = e.target as HTMLElement;
      el.classList.add("in");
      $$("[data-count]", el).forEach(count);
      if (el.dataset.count) count(el);
      io.unobserve(el);
    }), { threshold: 0.18, rootMargin: "0px 0px -6% 0px" });
    $$("[data-r],[data-split],[data-reveal]").forEach((el) => io.observe(el));
    off.push(() => io.disconnect());

    /* office clocks */
    const clocks = $$("[data-tz]");
    const tickClock = () => clocks.forEach((c) => {
      c.textContent = new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: c.dataset.tz }).format(new Date());
    });
    tickClock();
    const clockTimer = setInterval(tickClock, 15000);
    off.push(() => clearInterval(clockTimer));

    /* scroll-driven pieces */
    const nav = document.querySelector<HTMLElement>(".nav");
    const prog = document.getElementById("prog");
    const ind = document.querySelector<HTMLElement>(".nav-ind");
    const links = $$<HTMLAnchorElement>(".nav-links a");
    const secs = links.map((a) => document.getElementById(a.hash.slice(1)));
    const how = document.getElementById("how");
    const steps = how ? $$(".step", how) : [];
    const rail = document.getElementById("rail"), howBar = document.getElementById("howBar"), howN = document.getElementById("howN");
    const finalH = document.getElementById("finalH");
    const fws = finalH ? $$(".fw", finalH) : [];
    const dash = document.getElementById("dash");
    const wm = document.getElementById("wordmark");

    let raf = 0;
    const frame = () => {
      raf = 0;
      const y = scrollY, vh = innerHeight, H = document.documentElement.scrollHeight - vh;
      if (prog) prog.style.transform = `scaleX(${H > 0 ? y / H : 0})`;
      nav?.classList.toggle("scrolled", y > 40);

      let cur = -1;
      if (y > vh * 0.5) secs.forEach((s, i) => { if (s && s.getBoundingClientRect().top < vh * 0.4) cur = i; });
      links.forEach((a, i) => a.classList.toggle("on", i === cur));
      if (ind) {
        const a = links[cur];
        ind.style.opacity = a ? "1" : "0";
        if (a) { ind.style.width = `${a.offsetWidth - 24}px`; ind.style.transform = `translateX(${a.offsetLeft + 12}px)`; }
      }

      if (how && steps.length) {
        let p = 1, act = steps.length - 1;
        if (innerWidth > 980 && !reduce) {
          const r = how.getBoundingClientRect();
          p = clamp(-r.top / (how.offsetHeight - vh));
          act = Math.min(steps.length - 1, Math.floor(p * steps.length * 0.999));
        }
        steps.forEach((s, i) => { s.classList.toggle("on", innerWidth <= 980 || reduce || i === act); s.classList.toggle("done", i < act); });
        rail?.style.setProperty("--p", String(p));
        howBar?.style.setProperty("--p", String(p));
        if (howN) howN.textContent = String(act + 1);
      }

      if (finalH) {
        const fp = clamp((vh * 0.9 - finalH.getBoundingClientRect().top) / (vh * 0.6));
        const lit = reduce ? fws.length : Math.round(fp * fws.length);
        fws.forEach((w, i) => w.classList.toggle("lit", i < lit));
      }

      if (dash && !reduce) {
        const top = dash.getBoundingClientRect().top;
        dash.style.transform = `translateY(${(top - vh / 2) * -0.06}px) rotateX(${Math.max(0, Math.min(10, (top / vh) * 10))}deg)`;
      }

      if (wm) wm.style.setProperty("--fill", `${reduce ? 100 : clamp((vh - wm.getBoundingClientRect().top) / (vh * 0.5)) * 100}%`);
    };
    const schedule = () => { if (!raf) raf = requestAnimationFrame(frame); };
    on(window, "scroll", schedule, { passive: true });
    on(window, "resize", schedule);
    frame();
    off.push(() => cancelAnimationFrame(raf));

    /* hero cursor glow */
    const hero = document.querySelector<HTMLElement>(".hero"), glow = document.querySelector<HTMLElement>(".hero .glow");
    if (hero && glow && fine) on(hero, "pointermove", (e) => {
      const r = hero.getBoundingClientRect();
      glow.style.left = `${e.clientX - r.left}px`;
      glow.style.top = `${e.clientY - r.top}px`;
    });

    /* tilt cards, magnetic buttons */
    if (!reduce && fine) {
      $$(".tilt").forEach((c) => {
        on(c, "pointermove", (e) => {
          const r = c.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
          c.style.transform = `perspective(900px) rotateX(${(0.5 - y) * 6}deg) rotateY(${(x - 0.5) * 8}deg) translateY(-4px)`;
          c.style.setProperty("--mx", `${x * 100}%`);
          c.style.setProperty("--my", `${y * 100}%`);
        });
        on(c, "pointerleave", () => { c.style.transform = ""; });
      });
      $$(".mag").forEach((b) => {
        on(b, "pointermove", (e) => {
          const r = b.getBoundingClientRect();
          b.style.transform = `translate(${(e.clientX - r.left - r.width / 2) * 0.22}px,${(e.clientY - r.top - r.height / 2) * 0.3}px)`;
        });
        on(b, "pointerleave", () => { b.style.transform = ""; });
      });
    }

    /* FAQ: animate the answer's height instead of snapping */
    if (!reduce) $$<HTMLDetailsElement>(".faq details").forEach((d) => {
      const s = d.querySelector<HTMLElement>("summary"), a = d.querySelector<HTMLElement>(".ans");
      if (!s || !a) return;
      on(s, "click", (e) => {
        e.preventDefault();
        const ease = "cubic-bezier(.2,.8,.2,1)";
        if (d.open) {
          a.animate([{ height: `${a.scrollHeight}px`, opacity: 1 }, { height: "0px", opacity: 0 }], { duration: 380, easing: ease }).onfinish = () => { d.open = false; };
        } else {
          d.open = true;
          a.animate([{ height: "0px", opacity: 0 }, { height: `${a.scrollHeight}px`, opacity: 1 }], { duration: 450, easing: ease });
        }
      });
    });

    return () => off.forEach((f) => f());
  }, []);

  return null;
}
