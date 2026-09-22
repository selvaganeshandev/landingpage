/**
 * The static sections below the hero, in page order. Copy lives here; the
 * numbers it quotes come from lib/site so they change in one place.
 */
import { CONTACT_URL, ENGINE_COUNT, MINUTES_LABEL, PROMPT_COUNT, REPORT_TTL_DAYS } from "@/lib/site";

export function WhatYouGet() {
  return (
    <section className="alt">
      <div className="wrap">
        <span className="tag">What&apos;s in it</span>
        <h2>One audit.<br />One honest answer.</h2>
        <p className="sub">
          Most &quot;AI visibility&quot; tools give you a number and ask you to trust it. Ours shows you the actual answers —
          every question, every engine, and who got recommended when it wasn&apos;t you.
        </p>
        <div className="grid g3">
          <div className="card">
            <div className="n">01</div>
            <h3>Are you mentioned?</h3>
            <p>{PROMPT_COUNT} questions your buyers actually ask, put to {ENGINE_COUNT} engines. For each one: who got named, in what order, and who didn&apos;t.</p>
            <ul><li>Engine-by-engine grid</li><li>Every question, every answer</li><li>Who they recommend instead, and why</li></ul>
          </div>
          <div className="card">
            <div className="n">02</div>
            <h3>Are you the source?</h3>
            <p>Being named is a start. Being cited is what moves buyers. We show who controls the citations in your category.</p>
            <ul><li>Your site vs rivals vs third parties</li><li>The publishers shaping your answers</li><li>Claims the engines get wrong about you</li></ul>
          </div>
          <div className="card dark">
            <div className="n">03</div>
            <h3>The three fixes</h3>
            <p>Not a 40-page PDF. Three things, ranked by lift per hour of work, each with the projected score if you do it.</p>
            <ul><li>What to change, on which page</li><li>How many points it&apos;s worth</li><li>Roughly how long it takes</li></ul>
          </div>
        </div>
      </div>
    </section>
  );
}

export function HowItWorks() {
  return (
    <section>
      <div className="wrap">
        <span className="tag">How it works</span>
        <h2>Two minutes.<br />Three fields.</h2>
        <div className="steps">
          <div className="step">
            <div className="k">1</div>
            <div>
              <h3>We read your site</h3>
              <p>Industry, products, who you sell to, and the four competitors that show up next to you. No questionnaire — we already know.</p>
            </div>
            <div className="t">~15s</div>
          </div>
          <div className="step">
            <div className="k">2</div>
            <div>
              <h3>We ask the engines what your buyers ask</h3>
              <p>
                {PROMPT_COUNT} real questions — &quot;best savings account for students&quot;, &quot;which lender has the lowest processing fee&quot; —
                each put to all {ENGINE_COUNT} engines. You watch the answers arrive.
              </p>
            </div>
            <div className="t">~90s</div>
          </div>
          <div className="step">
            <div className="k">3</div>
            <div>
              <h3>We score it and hand you the fixes</h3>
              <p>Who mentioned you, who cited you, how you were described, and what the engines got wrong. Three fixes ranked by lift. Your report is live at a link you can forward to anyone — and a PDF you can download.</p>
            </div>
            <div className="t">~20s</div>
          </div>
        </div>
      </div>
    </section>
  );
}

const SAMPLE_ROWS: { q: string; dots: ("c" | "m" | "x")[] }[] = [
  { q: "Best savings account for salaried professionals?", dots: ["c", "c", "c", "m", "c", "m"] },
  { q: "Fastest credit card approval?", dots: ["m", "x", "m", "x", "x", "x"] },
  { q: "Best gold loan rate per gram?", dots: ["x", "x", "m", "x", "x", "x"] },
];

export function Sample() {
  return (
    <section className="alt">
      <div className="wrap">
        <div className="sample">
          <div>
            <span className="tag">Sample report</span>
            <h2>This is what<br />&quot;present but not preferred&quot; looks like.</h2>
            <p className="sub">
              A retail bank, mentioned by five of six engines — and cited by two. On Perplexity, an aggregator gets cited four times
              more often. That&apos;s the gap between showing up and being the answer.
            </p>
            <div className="quote">Being mentioned is a start. <em>Being cited</em> is the business.</div>
          </div>
          <div className="rep">
            <div className="hd">
              <small>AI Visibility Audit · sample</small>
              <b>Retail Bank · India</b>
              <div className="nums">
                <div><div className="v acc">58</div><div className="l">SCORE · PREFERRED</div></div>
                <div><div className="v">5<span>/6</span></div><div className="l">ENGINES MENTION</div></div>
                <div><div className="v">2<span>/6</span></div><div className="l">ENGINES CITE</div></div>
              </div>
            </div>
            <div className="bd">
              <div className="eg">
                <div className="ok"><b>ChatGPT</b><i>cited 11/24</i></div>
                <div className="ok"><b>Gemini</b><i>cited 9/24</i></div>
                <div className="ok"><b>Claude</b><i>cited 8/24</i></div>
                <div className="bad"><b>Perplexity</b><i>cited 2/24</i></div>
                <div className="warn"><b>Grok</b><i>cited 6/24</i></div>
                <div className="warn"><b>DeepSeek</b><i>cited 5/24</i></div>
              </div>
              <div className="cap">What buyers ask · {ENGINE_COUNT} engines</div>
              {SAMPLE_ROWS.map((r) => (
                <div className="row" key={r.q}>
                  <span>{r.q}</span>
                  <span className="dots">{r.dots.map((d, i) => <i key={i} className={d} />)}</span>
                </div>
              ))}
              <div className="legend">● cited · ● mentioned · ● absent — rival cited instead</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function WhyUs({ ctaHref = "#audit" }: { ctaHref?: string }) {
  return (
    <section>
      <div className="wrap">
        <span className="tag">Why us</span>
        <h2>We&apos;ve been flying<br />since before jetpacks.</h2>
        <div className="grid g4">
          <div className="card">
            <div className="n">{ENGINE_COUNT}</div>
            <h3>Engines, queried directly</h3>
            <p>Not scraped, not sampled from someone else&apos;s dataset. We ask ChatGPT, Gemini, Claude, Perplexity, Grok and DeepSeek ourselves.</p>
          </div>
          <div className="card">
            <div className="n">{PROMPT_COUNT}</div>
            <h3>Real buyer questions</h3>
            <p>Not &quot;tell me about Brand X&quot;. The questions people actually type — comparisons, best-ofs, how-tos — written from your own site.</p>
          </div>
          <div className="card">
            <div className="n">3</div>
            <h3>Fields. That&apos;s the form.</h3>
            <p>Website, brand name, work email. Industry, products, geography and competitors we detect from your site.</p>
          </div>
          <div className="card">
            <div className="n">4</div>
            <h3>Offices, two countries</h3>
            <p>Mumbai, Bangalore, Gurgaon, Dubai. When the audit says &quot;fix this&quot;, there&apos;s a team that can.</p>
          </div>
        </div>
        <div className="ctas">
          <a className="btn" href={ctaHref}>Get my free audit →</a>
          <a className="btn ghost" href={CONTACT_URL}>Talk to us instead</a>
        </div>
      </div>
    </section>
  );
}

export function Faq() {
  return (
    <section className="alt">
      <div className="wrap">
        <span className="tag">Questions</span>
        <h2>Fair questions.</h2>
        <div className="faq">
          <details open>
            <summary>Is it actually free?</summary>
            <p>
              Yes. The score, the engine grid, the sample questions and the three fixes are free and stay at a public link for {REPORT_TTL_DAYS} days,
              with a PDF you can download the moment it&apos;s done. Enter a work email and we send the full version — all {PROMPT_COUNT} questions with
              every engine&apos;s answer, the citation breakdown, and the complete fix list. Still free. No card, ever.
            </p>
          </details>
          <details>
            <summary>Why only {PROMPT_COUNT} questions and one run per engine?</summary>
            <p>
              Because that&apos;s what fits in {MINUTES_LABEL}. AI answers vary run to run, so a single run is an honest snapshot, not a statistic — and the
              report says so. Clients we work with get every question asked ten times, on a schedule, with confidence intervals. The free audit tells
              you whether that&apos;s worth a conversation.
            </p>
          </details>
          <details>
            <summary>What do you do with my domain and email?</summary>
            <p>
              We audit the domain, email you the report, and a PivotRoots strategist may follow up once to ask if the results were useful. That&apos;s it.
              No list-selling, no drip sequence. Unsubscribe in one click. <a href="https://www.pivotroots.com/privacy-policy">Privacy policy</a>.
            </p>
          </details>
          <details>
            <summary>Why do you need a work email?</summary>
            <p>
              Two reasons. It has to be on the same domain as the website you enter, so a competitor can&apos;t run your audit and read your results. And it
              means the report lands with someone who can actually act on it. No login, no password — just the address.
            </p>
          </details>
          <details>
            <summary>My site is huge. Will you read all of it?</summary>
            <p>
              We read your homepage, sitemap and the product pages that matter for the questions — enough to know what you sell and who you sell it to.
              Enterprise sites get the same {MINUTES_LABEL} audit; the full engagement goes deeper.
            </p>
          </details>
          <details>
            <summary>What about Google rankings?</summary>
            <p>
              This audit is about AI answers only — that&apos;s the question nobody&apos;s been able to answer for you until now. If you want the Google side too,
              it&apos;s part of the full engagement. And Google&apos;s AI Overviews aren&apos;t tracked yet: no API exists, so nobody can do it reliably. We&apos;d
              rather tell you that than fake it.
            </p>
          </details>
          <details>
            <summary>I ran it and my score is bad. Now what?</summary>
            <p>
              Good — now you know. The three fixes are things your team can do this month. If you want the full plan, the sequencing, and someone to
              execute it, that&apos;s what we do. <a href={CONTACT_URL}>Talk to us.</a>
            </p>
          </details>
        </div>
      </div>
    </section>
  );
}

export function FinalCta({ ctaHref = "#audit" }: { ctaHref?: string }) {
  return (
    <section className="final">
      <div className="wrap">
        <h2>Your competitor<br />might be running<br />this right now.</h2>
        <p className="sub">Two minutes. Six engines. One honest answer.</p>
        <a className="btn acc lg" href={ctaHref}>Get my free audit →</a>
      </div>
    </section>
  );
}
