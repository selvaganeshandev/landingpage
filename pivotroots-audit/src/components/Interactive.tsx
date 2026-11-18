"use client";

/**
 * The page's three small interactive pieces:
 *   QGrid           buyer questions × engines, filled cell by cell when on screen
 *   AskAgent        sample Ask Agent conversations, picked from three prompts
 *   ModuleDirectory every module in the platform, filterable by area
 * All content is illustrative; reduced-motion visitors get the finished state.
 */
import { useEffect, useRef, useState } from "react";
import { AREAS, MODULE_COUNT } from "@/lib/modules";
import { ENGINES } from "@/lib/site";

const reduced = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

type V = "c" | "m" | "x";
const ROWS: { q: string; v: V[] }[] = [
  { q: "Best savings account for students", v: ["c", "m", "c", "x", "m", "c"] },
  { q: "Lowest processing fee personal loan", v: ["m", "c", "x", "m", "x", "c"] },
  { q: "Fastest credit card approval", v: ["m", "x", "m", "x", "x", "x"] },
  { q: "Best gold loan rate per gram", v: ["x", "x", "m", "x", "x", "x"] },
];
const CELLS = ROWS.length * ENGINES.length;

export function QGrid() {
  // `filled` cells show their result, the cell at `filled` is being asked.
  const [filled, setFilled] = useState(CELLS);
  const [running, setRunning] = useState(false);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (reduced() || !root.current) return;
    const io = new IntersectionObserver(([e]) => setRunning(e.isIntersecting), { threshold: 0.4 });
    io.observe(root.current);
    return () => io.disconnect();
  }, []);
  useEffect(() => {
    if (!running) return;
    const t = setTimeout(() => setFilled((f) => (f >= CELLS ? 0 : f + 1)), filled >= CELLS ? 3500 : 300);
    return () => clearTimeout(t);
  }, [running, filled]);

  return (
    <div className="card" ref={root}>
      <div className="ch">Prompts × engines <em>{filled < CELLS ? "asking…" : "this week"}</em></div>
      <div className="qgrid">
        <div className="r th"><span>Buyer question</span>{ENGINES.map((e) => <i key={e}>{e.slice(0, 3)}</i>)}</div>
        {ROWS.map((row, ri) => (
          <div className="r" key={row.q}>
            <span>{row.q}</span>
            {row.v.map((v, ci) => {
              const n = ri * ENGINES.length + ci;
              return <i key={ci} className={`d${n < filled ? ` ${v}` : n === filled ? " ask" : ""}`} />;
            })}
          </div>
        ))}
      </div>
    </div>
  );
}

const CONVOS: { q: string; a: React.ReactNode }[] = [
  {
    q: "Why does Perplexity cite Rival A over us for “best savings account”?",
    a: <>Perplexity leans on <b>aggregator.com/best-of</b>, which lists Rival A first. Your rates page isn&apos;t cited on any of the 6 runs this week.
      <ul><li>Add a rate comparison table to your savings page</li><li>Get listed on the aggregator&apos;s best-of page</li></ul></>,
  },
  {
    q: "What changed in our share of voice this month?",
    a: <>Share of voice is up <b>9 points to 31%</b>. Most of the gain is on Gemini and ChatGPT for student-account questions. Rival A lost
      ground on Perplexity after your new FAQ page started being cited.</>,
  },
  {
    q: "Which three pages should we fix first?",
    a: <>Ranked by lift:<ul><li><b>/savings/rates</b> — cited by 0 of 6 engines, asked about most</li><li><b>/loans/gold</b> — engines quote an
      outdated rate</li><li><b>/cards/apply</b> — missing the approval-time facts engines look for</li></ul></>,
  },
];
const SHORT = ["Why does Perplexity cite Rival A over us?", "What changed in our share of voice this month?", "Which three pages should we fix first?"];

export function AskAgent() {
  const [cur, setCur] = useState(0);
  const [typing, setTyping] = useState(false);
  const pick = (i: number) => {
    setCur(i);
    if (reduced()) return;
    setTyping(true);
    setTimeout(() => setTyping(false), 900);
  };
  return (
    <>
      <div className="prompts rv" style={{ "--d": 1 } as React.CSSProperties}>
        {SHORT.map((s, i) => (
          <button key={s} type="button" className={i === cur ? "on" : ""} aria-pressed={i === cur} onClick={() => pick(i)}><span>›</span>{s}</button>
        ))}
      </div>
      <div className="chat rv" style={{ "--d": 2 } as React.CSSProperties}>
        <div className="chat-h"><i>AI</i>Ask Agent<em>sample conversation</em></div>
        <div className="chat-b" aria-live="polite">
          <div className="msg u">{CONVOS[cur].q}</div>
          <div className="msg a">{typing ? <span className="car" /> : CONVOS[cur].a}</div>
        </div>
        <div className="chat-in" aria-hidden="true"><span>Ask about your brand, rivals or engines…</span><b>↑</b></div>
      </div>
    </>
  );
}

export function ModuleDirectory() {
  const [area, setArea] = useState(-1);
  return (
    <>
      <div className="filters rv" role="group" aria-label="Filter modules by area">
        <button type="button" className={area < 0 ? "on" : ""} aria-pressed={area < 0} onClick={() => setArea(-1)}>All<em>{MODULE_COUNT}</em></button>
        {AREAS.map((a, i) => (
          <button key={a.key} type="button" className={area === i ? "on" : ""} aria-pressed={area === i} onClick={() => setArea(i)}>{a.name}<em>{a.mods.length}</em></button>
        ))}
      </div>
      <div className="dir">
        {AREAS.flatMap((a, i) => (area < 0 || area === i ? a.mods.map((m) => (
          <div className="mod" key={m.name}><em>{a.name}</em><b>{m.name}</b><p>{m.line}</p></div>
        )) : []))}
      </div>
    </>
  );
}
