/**
 * The home page below the hero: why it matters, the platform (four feature
 * rows), Ask Agent, SEO + tech, how the free audit works, every module, FAQ
 * and the closing call to action. Module names come from lib/modules.ts, which
 * mirrors the app's sidebar. Mock figures are illustrative sample data.
 */
import type { CSSProperties, ReactNode } from "react";
import { AREAS, MODULE_COUNT } from "@/lib/modules";
import { CONTACT_URL, ENGINES, MINUTES_LABEL, PDF_PREVIEW_PAGES, PROMPT_COUNT, REPORT_TTL_DAYS, SHOW_POWERED_BY } from "@/lib/site";
import { AskAgent, ModuleDirectory, QGrid } from "./Interactive";

const d = (n: number) => ({ "--d": n }) as CSSProperties;
const w = (pct: number) => ({ "--w": `${pct}%` }) as CSSProperties;

function Head({ eyebrow, title, sub, center = true, dark = false }: { eyebrow: string; title: ReactNode; sub?: ReactNode; center?: boolean; dark?: boolean }) {
  return (
    <div className={`sec-h${center ? " c" : ""} rv`}>
      <span className={`eyebrow${dark ? " dark" : ""}`}>{eyebrow}</span>
      <h2>{title}</h2>
      {sub && <p>{sub}</p>}
    </div>
  );
}

export function Trust() {
  return (
    <div className="trust">
      <div className="wrap">
        <p>Answers tracked across</p>
        <div className="engines">
          {ENGINES.map((e) => <span key={e}>{e}</span>)}
          <span className="soon">Google AI Overviews · soon</span>
        </div>
      </div>
    </div>
  );
}

export function Shift() {
  return (
    <section className="sec" id="why">
      <div className="wrap">
        <Head eyebrow="Why it matters now" title="Buyers ask AI first. Most brands can't see the answer."
          sub="Rankings, traffic and ad dashboards don't show what an AI engine tells your buyer. We do — question by question, engine by engine." />
        <div className="shift">
          <div className="scard rv"><span className="n">01</span><h3>One answer, a short list</h3><p>An AI answer names a handful of brands. If you&apos;re not in it, you&apos;re not in the consideration set.</p></div>
          <div className="scard rv" style={d(1)}><span className="n">02</span><h3>Being cited moves buyers</h3><p>Being mentioned is a start. Being the source the engine links to is what wins the click and the trust.</p></div>
          <div className="scard rv" style={d(2)}><span className="n">03</span><h3>AI gets things wrong</h3><p>Old prices, retired products, a rival&apos;s feature pinned on you — repeated to every buyer who asks.</p></div>
        </div>
        <div className="stats rv">
          <div><b data-count={MODULE_COUNT}>{MODULE_COUNT}</b><span>modules in one platform</span></div>
          <div><b data-count={ENGINES.length}>{ENGINES.length}</b><span>AI engines tracked</span></div>
          <div><b>GEO + SEO</b><span>AI answers and Google, together</span></div>
          <div><b data-count="4">4</b><span>offices · India &amp; UAE</span></div>
        </div>
      </div>
    </section>
  );
}

function Mods({ items }: { items: [string, string][] }) {
  return <ul className="mods">{items.map(([b, s]) => <li key={b}><div><b>{b}</b><small>{s}</small></div></li>)}</ul>;
}

function Row({ flip, tag, title, text, mods, children }: { flip?: boolean; tag: string; title: string; text: string; mods: [string, string][]; children: ReactNode }) {
  return (
    <div className={`frow${flip ? " flip" : ""}`}>
      <div className="ftext rv">
        <span className="tag">{tag}</span>
        <h3>{title}</h3>
        <p>{text}</p>
        <Mods items={mods} />
      </div>
      <div className="fvis rv" data-io="" style={d(1)}>{children}</div>
    </div>
  );
}

export function Product() {
  return (
    <section className="sec" id="product" style={{ paddingTop: 20 }}>
      <div className="wrap">
        <Head eyebrow="The platform" title="See it, understand it, protect it, grow it."
          sub="Everything PivotRoots clients use after the free audit — the same engine, running every week, across every engine and market." />

        <Row tag="01 · GEO monitoring" title="Every answer, on every engine, every week."
          text="Track the questions your buyers actually ask and read what each engine said — who it named, in what order, and which pages it cited."
          mods={[["Prompts", "The buyer questions you track"], ["Runs", "Every answer, engine by engine"], ["Mentions", "Each time you're named, in context"],
            ["Citations", "The links engines attach"], ["Sources", "The domains engines trust"], ["Alerts", "Drops and rival jumps, flagged"]]}>
          <QGrid />
          <div className="card mini-stats"><div><b>144</b><span>answers read</span></div><div><b>38</b><span>mentions</span></div><div><b>21</b><span>citations</span></div><div><b>9</b><span>sources</span></div></div>
        </Row>

        <Row flip tag="02 · Analytics & competitors" title="Know where you win — and who's beating you."
          text="Your share of the answers against the brands engines name next to you, how they describe you, and how it moves week on week."
          mods={[["Share of Voice", "Your share of the answers"], ["Competitors", "Head to head, question by question"], ["Sentiment", "Positive, neutral or negative"],
            ["Topics", "Themes you own, and the ones you miss"], ["Historical Trends", "Every metric, week on week"], ["Dashboard", "The whole picture on one screen"]]}>
          <div className="card">
            <div className="ch">Share of voice <em>12 weeks</em></div>
            {[["You", 31, true], ["Rival A", 24], ["Aggregator", 19], ["Rival B", 12]].map(([n, p, you]) => (
              <div className="sov" key={n as string}><span className={you ? "you" : ""}>{n}</span><div className="track"><i className={you ? "you" : ""} style={w((p as number) * 2)} /></div><b>{p}%</b></div>
            ))}
          </div>
          <div className="card">
            <div className="ch">Sentiment <em>how engines describe you</em></div>
            <div className="sent"><i className="p" style={w(62)} /><i className="n" style={w(28)} /><i className="x" style={w(10)} /></div>
            <div className="legend"><span className="pos">62% positive</span><span>28% neutral</span><span className="neg">10% negative</span></div>
            <div className="ch" style={{ marginTop: 16 }}>Topics</div>
            <div className="chips"><span>Savings rates ✓</span><span>Student accounts ✓</span><span>Gold loans — missing</span><span>Forex — missing</span></div>
          </div>
        </Row>

        <Row tag="03 · Protect & prove" title="Catch AI getting you wrong. Prove what AI sends you."
          text="Every wrong claim, with the page the engine took it from — and the visits that start in an AI answer, by engine. In every language your buyers ask in."
          mods={[["Misinformation", "Wrong claims, with their source"], ["Traffic Attribution", "Visits that start in AI answers"], ["Multilingual", "Answers tracked per language"]]}>
          <div className="card">
            <div className="ch">Misinformation</div>
            <div className="alert bad"><span className="ic">!</span><div><b>ChatGPT quoted the wrong fee</b><small>&ldquo;₹999 processing fee&rdquo; → actually ₹499 · source: an old blog post</small></div></div>
            <div className="alert ok"><span className="ic">✓</span><div><b>Fixed and re-checked</b><small>Gemini and ChatGPT now quote ₹499</small></div></div>
          </div>
          <div className="card">
            <div className="ch">Visits from AI answers <em>vs last quarter</em></div>
            <div className="bignum">+<span data-count="89">89</span>%</div>
            <div className="kv" style={{ marginTop: 12 }}><span>ChatGPT</span><b>5,420</b></div>
            <div className="kv"><span>Perplexity</span><b>4,127</b></div>
            <div className="kv"><span>Gemini</span><b>3,300</b></div>
          </div>
        </Row>

        <Row flip tag="04 · Strategy & content" title="Turn every gap into content that gets cited."
          text="See the questions engines answer without you and the topics rivals rank for — then plan, draft and score the pages that close the gap."
          mods={[["GEO Content Gaps", "Questions answered without you"], ["SEO Content Gaps", "Topics rivals rank for, clicks at stake"],
            ["Content Planner", "A calendar with an AI drafting wizard"], ["Content Editor", "Write and score before you publish"]]}>
          <div className="card">
            <div className="ch">Content gaps <em>ranked by lift</em></div>
            {[["GEO", "Which bank has no forex markup?", "Answered without you on 5 engines"], ["SEO", "student account documents", "~1,900 extra clicks / month"],
              ["GEO", "Is a gold loan safe?", "A rival is cited on 4 engines"]].map(([t, q, s]) => (
              <div className="gap" key={q}><i>{t}</i><div><b>{q}</b><small>{s}</small></div></div>
            ))}
          </div>
          <div className="card editor">
            <div className="ch">Content editor <span className="score">Citable score 94</span></div>
            <div className="line" style={{ width: "100%" }} /><div className="line" style={{ width: "86%" }} /><div className="line p" style={{ width: "62%" }} /><div className="line" style={{ width: "74%" }} />
            <div className="chips" style={{ marginTop: 14 }}><span>Answer-first intro</span><span>FAQ block</span><span>Comparison table</span></div>
          </div>
        </Row>
      </div>
    </section>
  );
}

export function Agent() {
  return (
    <section className="sec darksec" id="agent">
      <div className="wrap agent">
        <div>
          <Head center={false} dark eyebrow="Ask Agent" title="Ask your AI visibility data anything."
            sub="No dashboards to dig through. Ask in plain English and get an answer from your own tracking data — with the fix, not just the number." />
        </div>
        <div className="agent-r"><AskAgent /></div>
      </div>
    </section>
  );
}

export function Seo() {
  return (
    <section className="sec" id="seo">
      <div className="wrap">
        <Head eyebrow="SEO monitoring · Tech · Reports" title="AI answers and Google search, in one place."
          sub="The same platform tracks your organic search — keywords, rivals, links and site health — so GEO and SEO work from one plan." />
        <div className="bento">
          <div className="bx s4 rv">
            <h3>Keywords &amp; Opportunities</h3><p>Rankings for the keywords that bring business, and the ones close to page one — ranked by the lift they&apos;d bring.</p>
            <div className="viz kw">
              <div className="r th"><span>Keyword</span><span>Pos.</span><span>Change</span><span>Opportunity</span></div>
              {([["savings account interest rate", 3, 2, ""], ["zero balance account", 7, 4, "page 1"], ["personal loan eligibility", 11, -1, "near page 1"],
                ["gold loan per gram", 14, 6, "near page 1"]] as [string, number, number, string][]).map(([k, p, c, o]) => (
                <div className="r" key={k}><span>{k}</span><b>#{p}</b><span className={c >= 0 ? "up" : "dn"}>{c >= 0 ? "▲" : "▼"} {Math.abs(c)}</span>{o ? <span className="opp">{o}</span> : <span />}</div>
              ))}
            </div>
          </div>
          <div className="bx s2 ink rv" style={d(1)}>
            <h3>Tech Health Analysis</h3><p>A graded health check of your site, exportable for your dev team.</p>
            <div className="viz grade"><b>B+</b><ul><li>Graded checks</li><li>Clear priorities</li><li>Export to share</li></ul></div>
          </div>
          <div className="bx s2 rv">
            <h3>SEO Share of Voice</h3><p>Your share of organic search against your rivals.</p>
            <div className="viz">
              <div className="sov"><span className="you">You</span><div className="track"><i className="you" style={w(54)} /></div><b>18%</b></div>
              <div className="sov"><span>Rival A</span><div className="track"><i style={w(72)} /></div><b>24%</b></div>
            </div>
          </div>
          <div className="bx s2 rv" style={d(1)}>
            <h3>SEO Competitors</h3><p>Who outranks you, and on which keywords.</p>
            <div className="viz chips"><span>Rival A · 142 kw</span><span>Rival B · 96 kw</span><span>Aggregator · 61 kw</span></div>
          </div>
          <div className="bx s2 rv" style={d(2)}>
            <h3>Backlinks</h3><p>Your link profile, with links won and lost.</p>
            <div className="viz bl">{[30, 42, 38, 55, 61, 80].map((h, i) => <i key={i} className={i === 5 ? "w" : ""} style={{ "--h": `${h}%` } as CSSProperties} />)}</div>
          </div>
          <div className="bx s3 rv">
            <h3>Audit Engine</h3><p>Full AI visibility audits on demand — for your brand, a new market, or a prospect. The free audit is one slice of it.</p>
            <div className="viz chips"><span>{PROMPT_COUNT} buyer questions</span><span>{ENGINES.length} engines</span><span>Score + 3 fixes</span><span>PDF report</span></div>
          </div>
          <div className="bx s3 rv" style={d(1)}>
            <h3>GEO &amp; Organic Reports</h3><p>Shareable reports for your team and leadership, AI and SEO side by side.</p>
            <div className="viz doc"><div><i /><i /><i className="p" /><i /><span>GEO report</span></div><div><i /><i className="p" /><i /><i /><span>Organic report</span></div></div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function HowFree() {
  return (
    <section className="sec band" id="how">
      <div className="wrap">
        <Head eyebrow="Start free" title="Two minutes. Three fields. One honest answer."
          sub="The free audit runs a slice of the platform on your brand, so you can see where you stand before you talk to anyone." />
        <div className="steps">
          <div className="step rv"><div className="k"><b>1</b><span>~15s</span></div><h3>We read your site</h3><p>Industry, products, who you sell to, and the four competitors that show up next to you. No questionnaire — we already know.</p></div>
          <div className="step rv" style={d(1)}><div className="k"><b>2</b><span>~90s</span></div><h3>We ask the engines what your buyers ask</h3><p>{PROMPT_COUNT} real questions, each put to all {ENGINES.length} engines. You watch the answers arrive.</p></div>
          <div className="step rv" style={d(2)}><div className="k"><b>3</b><span>~20s</span></div><h3>We score it and hand you the fixes</h3><p>Who mentioned you, who cited you, what they got wrong. Three fixes ranked by lift, a {PDF_PREVIEW_PAGES}-page PDF preview, and the full report in your inbox.</p></div>
        </div>
        <div className="sample rv">
          <div>
            <span className="eyebrow dark">Sample report</span>
            <h3>This is what &ldquo;present but not preferred&rdquo; looks like.</h3>
            <p>A retail bank, mentioned by five of six engines — and cited by two. Being mentioned is a start. Being cited is the business.</p>
          </div>
          <div className="snums">
            <div><b data-count="58">58</b><span>score · preferred</span></div>
            <div><b>5<small>/6</small></b><span>engines mention</span></div>
            <div><b>2<small>/6</small></b><span>engines cite</span></div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function Modules() {
  return (
    <section className="sec" id="modules">
      <div className="wrap">
        <Head center={false} eyebrow="Everything inside" title={`${MODULE_COUNT} modules. One login.`}
          sub={`Filter by area to see what each part of the platform does — ${AREAS.length} areas in all. Your plan includes the modules your team needs.`} />
        <ModuleDirectory />
        <p className="fine-print rv">
          Figures on this page are illustrative sample data, not a client&apos;s results.
          {SHOW_POWERED_BY && " The platform runs on the PromptMaxx AI visibility engine."}
        </p>
      </div>
    </section>
  );
}

function Q({ q, children, open }: { q: string; children: ReactNode; open?: boolean }) {
  return <details open={open}><summary>{q}</summary><p>{children}</p></details>;
}

export function Faq() {
  return (
    <section className="sec" id="faq" style={{ paddingTop: 20 }}>
      <div className="wrap faq">
        <Head center={false} eyebrow="Questions" title="Fair questions." sub={<>Anything else? <a href={CONTACT_URL}>Talk to a strategist.</a></>} />
        <div className="rv">
          <Q q="Is the audit actually free?" open>
            Yes. The score, the engine grid, the sample questions and the three fixes are free and stay at a public link for {REPORT_TTL_DAYS} days,
            with a {PDF_PREVIEW_PAGES}-page PDF preview you can download the moment it&apos;s done. The PivotRoots team emails the full report to your
            work email — all {PROMPT_COUNT} questions with every engine&apos;s answer, the citation breakdown, and your 90-day plan. Still free. No card, ever.
          </Q>
          <Q q="What's the difference between the audit and the platform?">
            The audit is one run: {PROMPT_COUNT} questions, one pass per engine, in {MINUTES_LABEL} — an honest snapshot. The platform runs every week,
            with every question asked repeatedly across every engine and market, plus SEO, content and reporting — and the PivotRoots team turning
            what it finds into fixes.
          </Q>
          <Q q={`Why only ${PROMPT_COUNT} questions and one run per engine?`}>
            Because that&apos;s what fits in {MINUTES_LABEL}. AI answers vary run to run, so a single run is an honest snapshot, not a statistic — and the
            report says so. Clients we work with get every question asked ten times, on a schedule, with confidence intervals.
          </Q>
          <Q q="What do you do with my domain and email?">
            We audit the domain, email you the report, and a PivotRoots strategist may follow up once to ask if the results were useful. That&apos;s it.
            No list-selling, no drip sequence. Unsubscribe in one click. <a href="https://www.pivotroots.com/privacy-policy">Privacy policy</a>.
          </Q>
          <Q q="Why do you need a work email?">
            Because that&apos;s where the full report is sent, so it should land with someone who can act on it. Any work address is fine — yours, your
            agency&apos;s, your group company&apos;s — just not a personal Gmail, Yahoo or Outlook inbox. No login, no password — just the address.
          </Q>
          <Q q="What about Google rankings?">
            The free audit covers AI answers only. Google rankings, backlinks and site health are part of the platform&apos;s SEO monitoring. And
            Google&apos;s AI Overviews aren&apos;t tracked yet: no API exists, so nobody can do it reliably. We&apos;d rather tell you that than fake it.
          </Q>
          <Q q="I ran it and my score is bad. Now what?">
            Good — now you know. The three fixes are things your team can do this month. If you want the full plan, the sequencing, and someone to
            execute it, that&apos;s what we do. <a href={CONTACT_URL}>Talk to us.</a>
          </Q>
        </div>
      </div>
    </section>
  );
}

export function FinalCta({ ctaHref = "#audit" }: { ctaHref?: string }) {
  return (
    <section className="final darksec">
      <span className="eyebrow dark">Free · {MINUTES_LABEL} · {ENGINES.length} engines</span>
      <h2>Your competitor <em>might be running this</em> right now.</h2>
      <p>See what AI tells your buyers — before they decide.</p>
      <div className="final-ctas">
        <a className="btn btn-pear btn-lg" href={ctaHref}>Get my free audit <span className="arr">→</span></a>
        <a className="btn btn-ghost-dark btn-lg" href={CONTACT_URL}>Talk to a strategist</a>
      </div>
      <div className="ticks"><span>No card</span><span>No login</span><span>Full report by email</span></div>
    </section>
  );
}
