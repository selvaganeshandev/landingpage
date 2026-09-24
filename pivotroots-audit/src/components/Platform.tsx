/**
 * "Beyond the audit" — what PivotRoots runs for clients after the free audit.
 * Ported from the PromptMaxx site's dashboard preview and feature cards, redrawn
 * in the PivotRoots palette. Every number here is illustrative sample data
 * (labelled as such on the page), never a real client's.
 */
import { CONTACT_URL, ENGINES, SHOW_POWERED_BY } from "@/lib/site";

const TREND = [22, 26, 25, 31, 34, 33, 39, 44, 47, 52, 55, 58];

const SOV = [
  { name: "yourbrand.com", pct: 31, you: true },
  { name: "Rival A", pct: 24 },
  { name: "Aggregator", pct: 19 },
  { name: "Rival B", pct: 12 },
];

const ENGINE_ROWS: { e: string; v: "c" | "m" | "x" }[] = ENGINES.map((e, i) => ({
  e,
  v: (["c", "c", "m", "c", "x", "m"] as const)[i % 6],
}));

function Dashboard() {
  return (
    <div className="dash" aria-label="Sample AI visibility dashboard">
      <div className="dash-chrome">
        <i /><i /><i />
        <span>AI Visibility · yourbrand.com</span>
        <em>sample data</em>
      </div>
      <div className="dash-body">
        <div className="dash-tiles">
          <div><span>Visibility score</span><b className="acc-ink">58</b><small className="up">▲ 24 in 12 weeks</small></div>
          <div><span>Engines citing you</span><b>4<small>/{ENGINES.length}</small></b><small className="up">▲ 2 since audit</small></div>
          <div><span>Share of voice</span><b>31%</b><small className="up">▲ 9 pts</small></div>
          <div><span>Wrong claims open</span><b>2</b><small className="down">▼ from 7</small></div>
        </div>
        <div className="dash-main">
          <div className="dash-card">
            <div className="dash-h">Visibility score · weekly</div>
            <div className="spark" role="img" aria-label="Score rising from 22 to 58 over 12 weeks">
              {TREND.map((v, i) => <i key={i} style={{ height: `${(v / 60) * 100}%` }} className={i === TREND.length - 1 ? "now" : ""} />)}
            </div>
            <div className="dash-foot"><span>Audit</span><span>Fixes shipped</span><span>Today</span></div>
          </div>
          <div className="dash-card">
            <div className="dash-h">Share of voice</div>
            {SOV.map((s) => (
              <div className="sov" key={s.name}>
                <span className={s.you ? "you" : ""}>{s.name}</span>
                <div className="track"><i style={{ width: `${s.pct * 3}%` }} className={s.you ? "you" : ""} /></div>
                <b>{s.pct}%</b>
              </div>
            ))}
            <div className="dash-h" style={{ marginTop: 16 }}>This week, by engine</div>
            <div className="eng">
              {ENGINE_ROWS.map((r) => <span key={r.e} className={r.v}>{r.e}</span>)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function Platform({ ctaHref = "#audit" }: { ctaHref?: string }) {
  return (
    <section id="platform" className="platform">
      <div className="wrap">
        <span className="tag acc">Beyond the free audit</span>
        <h2>The audit is a snapshot.<br />We keep watching.</h2>
        <p className="sub">
          For PivotRoots clients the same engine runs every week — more questions, every engine, every market — and our team turns what it
          finds into fixes that ship. This is what that looks like.
        </p>

        <Dashboard />

        <div className="grid g3 feats">
          <div className="feat">
            <div className="mock">
              <div className="mrow bad"><b>!</b><div><strong>Engine quoted the wrong price</strong><small>&quot;₹999/mo&quot; → actually ₹499/mo</small></div></div>
              <div className="mrow ok"><b>✓</b><div><strong>Flagged to your team</strong><small>source page + fix attached</small></div></div>
            </div>
            <h3>Catch AI getting you wrong</h3>
            <p>Wrong prices, retired products, a rival&apos;s feature pinned on you. We flag every claim the engines get wrong, with the page they took it from.</p>
          </div>
          <div className="feat">
            <div className="mock">
              <div className="mh">Sources the engines cite</div>
              <div className="src"><i className="c" />yourbrand.com/pricing<em>you</em></div>
              <div className="src"><i className="c" />yourbrand.com/compare<em>you</em></div>
              <div className="src"><i className="x" />aggregator.com/best-of<em>3rd party</em></div>
            </div>
            <h3>See who the engines trust</h3>
            <p>Being cited is what moves buyers. See which pages — yours, a rival&apos;s, a publisher&apos;s — the engines lean on for every question.</p>
          </div>
          <div className="feat">
            <div className="mock">
              <div className="mh">Share of voice · 12 weeks</div>
              <div className="sov"><span className="you">You</span><div className="track"><i className="you" style={{ width: "62%" }} /></div><b>31%</b></div>
              <div className="sov"><span>Rival A</span><div className="track"><i style={{ width: "48%" }} /></div><b>24%</b></div>
              <div className="sov"><span>Rival B</span><div className="track"><i style={{ width: "24%" }} /></div><b>12%</b></div>
            </div>
            <h3>Beat your competitors, not a benchmark</h3>
            <p>Your share of the answers against the four brands the engines name next to you — tracked week on week, question by question.</p>
          </div>
          <div className="feat">
            <div className="mock">
              <div className="mh">Visits from AI answers</div>
              <div className="big">+89%</div>
              <div className="kv"><span>ChatGPT</span><b>5,420</b></div>
              <div className="kv"><span>Perplexity</span><b>4,127</b></div>
              <div className="kv"><span>Gemini</span><b>3,300</b></div>
            </div>
            <h3>Know what AI sends you</h3>
            <p>Connect your analytics and see the visits, sign-ups and sales that start in an AI answer — and which engine sent them.</p>
          </div>
          <div className="feat">
            <div className="mock">
              <div className="mh">Content editor <span className="pill">Citable: 94</span></div>
              <div className="line" style={{ width: "100%" }} />
              <div className="line" style={{ width: "82%" }} />
              <div className="line acc" style={{ width: "64%" }} />
              <div className="chips"><span>Answer-first rewrite</span><span>FAQ schema</span><span>Link map</span></div>
            </div>
            <h3>Content built to be cited</h3>
            <p>Pages written the way engines quote them — direct answers, clean structure, the facts they need — scored before they go live.</p>
          </div>
          <div className="feat dark">
            <div className="mock">
              <div className="mh">Markets</div>
              <div className="mk">
                {["India", "UAE", "KSA", "UK", "US", "Singapore"].map((m, i) => (
                  <span key={m}><i className={["c", "c", "m", "c", "x", "c"][i]} />{m}</span>
                ))}
              </div>
            </div>
            <h3>Every market you sell in</h3>
            <p>Buyers in Mumbai and Dubai get different answers. We ask the engines as your buyers in each market, and track each one on its own.</p>
          </div>
        </div>

        <div className="ctas">
          <a className="btn" href={ctaHref}>Start with the free audit →</a>
          <a className="btn ghost" href={CONTACT_URL}>Talk to a PivotRoots strategist</a>
        </div>
        <p className="fine-print">
          Figures in this section are illustrative sample data, not a client&apos;s results.
          {SHOW_POWERED_BY && " Monitoring runs on the PromptMaxx AI visibility engine."}
        </p>
      </div>
    </section>
  );
}
