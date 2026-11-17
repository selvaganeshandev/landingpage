/**
 * The static sections below the hero, in page order. Copy lives here; the
 * numbers it quotes come from lib/site so they change in one place. Motion is
 * declared with markers (data-r, data-split, data-count, .tilt, .mag) and run
 * by MotionRoot.
 */
import type { CSSProperties } from "react";
import { CONTACT_URL, ENGINE_COUNT, MINUTES_LABEL, PDF_PREVIEW_PAGES, PROMPT_COUNT, REPORT_TTL_DAYS } from "@/lib/site";
import { Lines } from "./Split";

const d = (n: number) => ({ "--d": n }) as CSSProperties;
const iv = (n: number) => ({ "--i": n }) as CSSProperties;

/* Wordless card illustrations — decoration only. */
const MENTION_GRID = ["c", "c", "m", "c", "m", "x", "c", "m", "x", "c", "c", "m", "m", "x", "c", "x", "m", "c"];

export function WhatYouGet() {
  return (
    <section className="sec alt" id="whats-in-it">
      <div className="wrap">
        <span className="tag" data-r="">What&apos;s in it</span>
        <h2 data-split=""><Lines lines={["One audit.", "One honest answer."]} /></h2>
        <p className="sub" data-r="" style={d(2)}>
          Most &quot;AI visibility&quot; tools give you a number and ask you to trust it. Ours shows you the actual answers —
          every question, every engine, and who got recommended when it wasn&apos;t you.
        </p>
        <div className="bento">
          <div className="card big tilt" data-r="">
            <div className="sheen" />
            <div className="n">01</div>
            <h3>Are you mentioned?</h3>
            <p>{PROMPT_COUNT} questions your buyers actually ask, put to {ENGINE_COUNT} engines. For each one: who got named, in what order, and who didn&apos;t.</p>
            <ul><li>Engine-by-engine grid</li><li>Every question, every answer</li><li>Who they recommend instead, and why</li></ul>
            <div className="viz" aria-hidden="true">
              <div className="viz-grid">{MENTION_GRID.map((c, i) => <i key={i} className={c} style={iv(i)} />)}</div>
            </div>
          </div>
          <div className="card tilt" data-r="" style={d(1)}>
            <div className="sheen" />
            <div className="n">02</div>
            <h3>Are you the source?</h3>
            <p>Being named is a start. Being cited is what moves buyers. We show who controls the citations in your category.</p>
            <ul><li>Your site vs rivals vs third parties</li><li>The publishers shaping your answers</li><li>Claims the engines get wrong about you</li></ul>
            <div className="viz-bars" aria-hidden="true">
              <i className="you" style={{ "--w": "72%", "--i": 0 } as CSSProperties} />
              <i style={{ "--w": "54%", "--i": 1 } as CSSProperties} />
              <i style={{ "--w": "38%", "--i": 2 } as CSSProperties} />
            </div>
          </div>
          <div className="card dark tilt" data-r="" style={d(2)}>
            <div className="sheen" />
            <div className="n">03</div>
            <h3>The three fixes</h3>
            <p>Not a 40-page PDF. Three things, ranked by lift per hour of work, each with the projected score if you do it.</p>
            <ul><li>What to change, on which page</li><li>How many points it&apos;s worth</li><li>Roughly how long it takes</li></ul>
            <div className="fixes" aria-hidden="true"><span>#1<b>▲▲▲</b></span><span>#2<b>▲▲</b></span><span>#3<b>▲</b></span></div>
          </div>
        </div>
      </div>
    </section>
  );
}

/** Pinned on desktop: the section holds while the three steps light up in turn. */
export function HowItWorks() {
  return (
    <section className="how" id="how">
      <div className="pin">
        <div className="wrap">
          <div>
            <span className="tag inv" data-r="">How it works</span>
            <h2 data-split=""><Lines lines={["Two minutes.", "Three fields."]} /></h2>
            <div className="meter" data-r="" style={d(2)} aria-hidden="true">
              <b id="howN">1</b>/ 3<div className="meter-bar"><i id="howBar" /></div>
            </div>
          </div>
          <div className="steps">
            <div className="rail" aria-hidden="true"><i id="rail" /></div>
            <div className="step on">
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
                <p>Who mentioned you, who cited you, how you were described, and what the engines got wrong. Three fixes ranked by lift. Your report is live at a link you can forward to anyone, with a PDF preview to download — and the full report lands in your inbox.</p>
              </div>
              <div className="t">~20s</div>
            </div>
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

const SAMPLE_ENGINES = [
  { e: "ChatGPT", c: "ok", v: "cited 11/24" },
  { e: "Gemini", c: "ok", v: "cited 9/24" },
  { e: "Claude", c: "ok", v: "cited 8/24" },
  { e: "Perplexity", c: "bad", v: "cited 2/24" },
  { e: "Grok", c: "warn", v: "cited 6/24" },
  { e: "DeepSeek", c: "warn", v: "cited 5/24" },
];

export function Sample() {
  return (
    <section className="sec alt" id="sample">
      <div className="wrap">
        <div className="sample">
          <div>
            <span className="tag" data-r="">Sample report</span>
            <h2 data-split=""><Lines lines={["This is what", "\"present but not preferred\" looks like."]} /></h2>
            <p className="sub" data-r="" style={d(2)}>
              A retail bank, mentioned by five of six engines — and cited by two. On Perplexity, an aggregator gets cited four times
              more often. That&apos;s the gap between showing up and being the answer.
            </p>
            <div className="quote" data-r="left" style={d(3)}>Being mentioned is a start. <em>Being cited</em> is the business.</div>
          </div>
          {/* The report builds itself on reveal: tiles flip in, dots light up, numbers count. */}
          <div className="rep" data-reveal="">
            <div className="hd">
              <small>AI Visibility Audit · sample</small>
              <b>Retail Bank · India</b>
              <div className="nums">
                <div><div className="v acc" data-count="58">58</div><div className="l">SCORE · PREFERRED</div></div>
                <div><div className="v"><span data-count="5">5</span><span>/6</span></div><div className="l">ENGINES MENTION</div></div>
                <div><div className="v"><span data-count="2">2</span><span>/6</span></div><div className="l">ENGINES CITE</div></div>
              </div>
            </div>
            <div className="bd">
              <div className="eg">
                {SAMPLE_ENGINES.map((x, i) => <div key={x.e} className={x.c} style={iv(i)}><b>{x.e}</b><i>{x.v}</i></div>)}
              </div>
              <div className="cap">What buyers ask · {ENGINE_COUNT} engines</div>
              {SAMPLE_ROWS.map((r, ri) => (
                <div className="row" key={r.q}>
                  <span>{r.q}</span>
                  <span className="dots">{r.dots.map((x, i) => <i key={i} className={x} style={iv(ri * 6 + i)} />)}</span>
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
    <section className="sec alt" id="why">
      <div className="wrap">
        <span className="tag" data-r="">Why us</span>
        <h2 data-split=""><Lines lines={["We've been flying", "since before jetpacks."]} /></h2>
        <div className="g4">
          <div className="stat" data-r="">
            <div className="n" data-count={ENGINE_COUNT}>{ENGINE_COUNT}</div>
            <h3>Engines, queried directly</h3>
            <p>Not scraped, not sampled from someone else&apos;s dataset. We ask ChatGPT, Gemini, Claude, Perplexity, Grok and DeepSeek ourselves.</p>
          </div>
          <div className="stat" data-r="" style={d(1)}>
            <div className="n" data-count={PROMPT_COUNT}>{PROMPT_COUNT}</div>
            <h3>Real buyer questions</h3>
            <p>Not &quot;tell me about Brand X&quot;. The questions people actually type — comparisons, best-ofs, how-tos — written from your own site.</p>
          </div>
          <div className="stat" data-r="" style={d(2)}>
            <div className="n" data-count="3">3</div>
            <h3>Fields. That&apos;s the form.</h3>
            <p>Website, brand name, work email. Industry, products, geography and competitors we detect from your site.</p>
          </div>
          <div className="stat" data-r="" style={d(3)}>
            <div className="n" data-count="4">4</div>
            <h3>Offices, two countries</h3>
            <p>Mumbai, Bangalore, Gurgaon, Dubai. When the audit says &quot;fix this&quot;, there&apos;s a team that can.</p>
          </div>
        </div>
        <div className="ctas" data-r="">
          <a className="btn mag" href={ctaHref}>Get my free audit <span className="arr">→</span></a>
          <a className="btn ghost mag" href={CONTACT_URL}>Talk to us instead</a>
        </div>
      </div>
    </section>
  );
}

function Q({ q, open, children }: { q: string; open?: boolean; children: React.ReactNode }) {
  return (
    <details open={open}>
      <summary>{q}<span className="pm" aria-hidden="true" /></summary>
      <div className="ans"><p>{children}</p></div>
    </details>
  );
}

export function Faq() {
  return (
    <section className="sec" id="faq">
      <div className="wrap faq-grid">
        <div className="left">
          <span className="tag" data-r="">Questions</span>
          <h2 data-split=""><Lines lines={["Fair questions."]} /></h2>
        </div>
        <div className="faq" data-r="">
          <Q q="Is it actually free?" open>
            Yes. The score, the engine grid, the sample questions and the three fixes are free and stay at a public link for {REPORT_TTL_DAYS} days,
            with a {PDF_PREVIEW_PAGES}-page PDF preview you can download the moment it&apos;s done. The PivotRoots team emails the full report to your
            work email — all {PROMPT_COUNT} questions with every engine&apos;s answer, the citation breakdown, and your 90-day plan. Still free. No card, ever.
          </Q>
          <Q q={`Why only ${PROMPT_COUNT} questions and one run per engine?`}>
            Because that&apos;s what fits in {MINUTES_LABEL}. AI answers vary run to run, so a single run is an honest snapshot, not a statistic — and the
            report says so. Clients we work with get every question asked ten times, on a schedule, with confidence intervals. The free audit tells
            you whether that&apos;s worth a conversation.
          </Q>
          <Q q="What do you do with my domain and email?">
            We audit the domain, email you the report, and a PivotRoots strategist may follow up once to ask if the results were useful. That&apos;s it.
            No list-selling, no drip sequence. Unsubscribe in one click. <a href="https://www.pivotroots.com/privacy-policy">Privacy policy</a>.
          </Q>
          <Q q="Why do you need a work email?">
            Because that&apos;s where the full report is sent, so it should land with someone who can actually act on it. Any work address is fine —
            yours, your agency&apos;s, your group company&apos;s — just not a personal Gmail, Yahoo or Outlook inbox. We check the address can receive mail
            before the audit starts. No login, no password — just the address.
          </Q>
          <Q q="My site is huge. Will you read all of it?">
            We read your homepage, sitemap and the product pages that matter for the questions — enough to know what you sell and who you sell it to.
            Enterprise sites get the same {MINUTES_LABEL} audit; the full engagement goes deeper.
          </Q>
          <Q q="What about Google rankings?">
            This audit is about AI answers only — that&apos;s the question nobody&apos;s been able to answer for you until now. If you want the Google side too,
            it&apos;s part of the full engagement. And Google&apos;s AI Overviews aren&apos;t tracked yet: no API exists, so nobody can do it reliably. We&apos;d
            rather tell you that than fake it.
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

const FINAL_LINES = ["Your competitor", "might be running", "this right now."];
const HIGHLIGHT = /^(competitor|right|now\.)$/i;

/** The headline lights up word by word as it scrolls into view. */
export function FinalCta({ ctaHref = "#audit" }: { ctaHref?: string }) {
  return (
    <section className="final">
      <div className="orb" aria-hidden="true" />
      <div className="wrap">
        <h2 id="finalH">
          {FINAL_LINES.map((line, li) => (
            <span key={line}>
              {li > 0 && <br />}
              {line.split(" ").map((w, i) => (
                <span key={w}>{i > 0 && " "}<span className={`fw${HIGHLIGHT.test(w) ? " hl" : ""}`}>{w}</span></span>
              ))}
            </span>
          ))}
        </h2>
        <p className="sub">Two minutes. Six engines. One honest answer.</p>
        <a className="btn acc lg mag" href={ctaHref}>Get my free audit <span className="arr">→</span></a>
      </div>
    </section>
  );
}
