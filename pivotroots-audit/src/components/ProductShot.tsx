/**
 * The hero's product screenshot, drawn in HTML: the platform dashboard with the
 * app's real sidebar groups. Every figure is illustrative sample data and the
 * frame says so. MotionRoot adds .in when it scrolls into view (frame lands
 * flat, the line draws, the bars grow).
 */
import type { CSSProperties } from "react";
import { ENGINES } from "@/lib/site";

const w = (pct: number) => ({ "--w": `${pct}%` }) as CSSProperties;

const SIDE: [string, string[]][] = [
  ["Overview", ["Dashboard", "Ask Agent"]],
  ["GEO monitoring", ["Prompts", "Mentions", "Citations", "Sources", "Alerts"]],
  ["Analytics", ["Sentiment", "Share of Voice", "Competitors"]],
  ["SEO monitoring", ["Keywords", "Backlinks"]],
  ["Strategy", ["Content Gaps", "Content Planner"]],
];

const BY_ENGINE: { pct: number; v: "c" | "m" | "x"; you?: boolean }[] = [
  { pct: 78, v: "c" }, { pct: 70, v: "c" }, { pct: 52, v: "m" }, { pct: 64, v: "c", you: true }, { pct: 22, v: "x" }, { pct: 40, v: "m" },
];
const LABEL = { c: "cited", m: "mentioned", x: "absent" };

const LINE = "M0,128 L36,118 L72,120 L109,104 L145,96 L182,98 L218,82 L254,68 L291,60 L327,46 L364,38 L400,30";

export function ProductShot() {
  return (
    <div className="shot rv" data-io="" style={{ "--d": 5 } as CSSProperties} aria-label="Sample AI visibility dashboard" role="img">
      <div className="float f1" aria-hidden="true"><span className="ic">!</span><div><b>Wrong claim flagged</b><small>ChatGPT quoted an old fee</small></div></div>
      <div className="float f2" aria-hidden="true"><span className="ic">↑</span><div><b>+89% visits from AI</b><small>Traffic attribution</small></div></div>
      <div className="float f3" aria-hidden="true"><span className="ic">✓</span><div><b>Now cited on Perplexity</b><small>3 new citations this week</small></div></div>
      <div className="frame" aria-hidden="true">
        <div className="chrome"><i /><i /><i /><span>AI Visibility · yourbrand.com</span><em>sample data</em></div>
        <div className="app">
          <div className="side">
            {SIDE.map(([h, items], gi) => (
              <div key={h}>
                <h6>{h}</h6>
                {items.map((it, ii) => <span key={it} className={gi === 0 && ii === 0 ? "on" : ""}>{it}</span>)}
              </div>
            ))}
          </div>
          <div className="main">
            <div className="main-h"><b>Dashboard</b><span>Last 12 weeks · India</span></div>
            <div className="kpis">
              <div className="kpi acc"><span>Visibility score</span><b data-count="58">58</b><small>▲ 24 pts</small></div>
              <div className="kpi"><span>Engines citing you</span><b><em data-count="4">4</em>/{ENGINES.length}</b><small>▲ 2 since audit</small></div>
              <div className="kpi"><span>Share of voice</span><b><em data-count="31">31</em>%</b><small>▲ 9 pts</small></div>
              <div className="kpi"><span>Wrong claims open</span><b data-count="2">2</b><small>▼ from 7</small></div>
            </div>
            <div className="two">
              <div className="panel">
                <div className="ph">Visibility score <em>weekly</em></div>
                <svg className="chart" viewBox="0 0 400 150" preserveAspectRatio="none">
                  <defs><linearGradient id="shot-g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#CBDB2D" stopOpacity=".45" /><stop offset="1" stopColor="#CBDB2D" stopOpacity="0" /></linearGradient></defs>
                  <g className="grid"><line x1="0" y1="30" x2="400" y2="30" /><line x1="0" y1="75" x2="400" y2="75" /><line x1="0" y1="120" x2="400" y2="120" /></g>
                  <path className="area" d={`${LINE} L400,150 L0,150Z`} fill="url(#shot-g)" />
                  <path className="ln" d={LINE} />
                  <circle className="pt" cx="394" cy="31" r="6" />
                </svg>
              </div>
              <div className="panel">
                <div className="ph">This week, by engine</div>
                {ENGINES.map((e, i) => (
                  <div className="erow" key={e}>
                    <span>{e}</span>
                    <div className="track"><i className={BY_ENGINE[i].you ? "you" : ""} style={w(BY_ENGINE[i].pct)} /></div>
                    <span className={`pill ${BY_ENGINE[i].v}`}>{LABEL[BY_ENGINE[i].v]}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
