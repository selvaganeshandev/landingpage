"use client";

/**
 * Hero graphic: the six engines circling the brand. A buyer question types
 * out, each engine is "asked" in turn and lights up cited / mentioned /
 * absent. Decorative only (aria-hidden); the questions are the ones the page
 * copy already quotes. The server render shows one finished round, which is
 * also what reduced-motion visitors keep.
 */
import { useEffect, useState } from "react";
import { ENGINES } from "@/lib/site";

type Result = "" | "c" | "m" | "x";

const QUESTIONS: { q: string; d: Result[] }[] = [
  { q: "best savings account for students", d: ["c", "m", "c", "x", "m", "c"] },
  { q: "Best savings account for salaried professionals?", d: ["c", "c", "c", "m", "c", "m"] },
  { q: "which lender has the lowest processing fee", d: ["m", "c", "x", "m", "x", "c"] },
  { q: "Fastest credit card approval?", d: ["m", "x", "m", "x", "x", "x"] },
  { q: "Best gold loan rate per gram?", d: ["x", "x", "m", "x", "x", "x"] },
];

const R = 190; // ring radius in the 500×500 viewBox
const NODES = ENGINES.map((e, i) => {
  const a = (i / ENGINES.length) * Math.PI * 2 - Math.PI / 2;
  return { e, x: Math.cos(a) * R, y: Math.sin(a) * R };
});

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export function Orbit() {
  const [text, setText] = useState(QUESTIONS[1].q);
  const [results, setResults] = useState<Result[]>(QUESTIONS[1].d);
  const [asking, setAsking] = useState(-1);

  useEffect(() => {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let alive = true;
    (async () => {
      await sleep(1200);
      for (let qi = 0; alive; qi++) {
        const { q, d } = QUESTIONS[qi % QUESTIONS.length];
        setResults(Array(NODES.length).fill(""));
        for (let k = 1; k <= q.length && alive; k++) { setText(q.slice(0, k)); await sleep(28); }
        await sleep(350);
        for (let i = 0; i < NODES.length && alive; i++) {
          setAsking(i);
          await sleep(330);
          setResults((r) => r.map((v, j) => (j === i ? d[i] : v)));
        }
        setAsking(-1);
        await sleep(1800);
      }
    })();
    return () => { alive = false; };
  }, []);

  return (
    <div className="orbit" data-r="scale" style={{ "--d": 3 } as React.CSSProperties} aria-hidden="true">
      <div className="orbit-legend">
        <span><i className="c" />cited</span><span><i className="m" />mentioned</span><span><i className="x" />absent — rival cited instead</span>
      </div>
      <div className="ring">
        <svg viewBox="0 0 500 500">
          <circle className="track" cx="250" cy="250" r={R} />
          {NODES.map((n, i) => (
            <line key={n.e} className={`beam${asking === i ? " hot" : ""}`} x1="250" y1="250" x2={250 + n.x} y2={250 + n.y} />
          ))}
        </svg>
        {NODES.map((n, i) => (
          <div key={n.e} className="node" style={{ left: `${50 + (n.x / 500) * 100}%`, top: `${50 + (n.y / 500) * 100}%` }}>
            <div className="node-in">
              <div className="upright">
                <div className={`chip ${results[i]}${asking === i ? " ask" : ""}`}><i />{n.e}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="core">Your<br />brand<span>yourbrand.com</span></div>
      <div className="ask-q"><span>{text}</span><span className="car" /></div>
    </div>
  );
}
