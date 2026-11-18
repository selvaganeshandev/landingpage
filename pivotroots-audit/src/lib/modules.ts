/**
 * What is inside the platform, by area — the same modules, names and grouping
 * as the app's own sidebar (frontend/src/stores/navigationStore.ts). The page
 * lists only modules that exist there; keep the two in step.
 */
export interface Mod { name: string; line: string }
export interface Area { key: string; name: string; mods: Mod[] }

export const AREAS: Area[] = [
  {
    key: "overview", name: "Overview", mods: [
      { name: "Dashboard", line: "Your visibility score, trends and open issues on one screen." },
      { name: "Ask Agent", line: "Ask about your AI visibility in plain English. Answers come from your own data." },
    ],
  },
  {
    key: "geo", name: "GEO monitoring", mods: [
      { name: "Prompts", line: "The buyer questions you track, run on every engine." },
      { name: "Runs", line: "Every answer, engine by engine: what it said and who it named." },
      { name: "Mentions", line: "Each time an engine names your brand, in context." },
      { name: "Citations", line: "The links the engines attach to their answers." },
      { name: "Sources", line: "The domains and pages the engines trust in your category." },
      { name: "Alerts", line: "A heads-up when your visibility drops or a rival jumps." },
    ],
  },
  {
    key: "analytics", name: "Analytics", mods: [
      { name: "Sentiment", line: "How the engines describe you: positive, neutral or negative." },
      { name: "Topics", line: "The themes you own, and the ones where answers miss you." },
      { name: "Share of Voice", line: "Your share of the answers against your competitors." },
      { name: "Historical Trends", line: "Week-on-week movement on every metric." },
      { name: "Competitors", line: "Head to head with the brands the engines name next to you." },
    ],
  },
  {
    key: "protect", name: "Protect & prove", mods: [
      { name: "Misinformation", line: "Wrong claims the engines make about you, with the page they took it from." },
      { name: "Traffic Attribution", line: "The visits that start in an AI answer, and which engine sent them." },
      { name: "Multilingual", line: "Answers tracked in each language your buyers ask in." },
    ],
  },
  {
    key: "seo", name: "SEO monitoring", mods: [
      { name: "Keywords", line: "Rankings for the keywords that bring you business." },
      { name: "Opportunities", line: "Keywords close to page one, ranked by the lift they'd bring." },
      { name: "SEO Share of Voice", line: "Your share of organic search against your rivals." },
      { name: "SEO Competitors", line: "Who outranks you, and on which keywords." },
      { name: "Backlinks", line: "Your link profile, with links won and lost." },
    ],
  },
  {
    key: "strategy", name: "Strategy & content", mods: [
      { name: "GEO Content Gaps", line: "Questions the engines answer without you, and what to publish." },
      { name: "SEO Content Gaps", line: "Topics rivals rank for and you don't, with the clicks at stake." },
      { name: "Content Planner", line: "A content calendar with an AI wizard to draft each piece." },
      { name: "Content Editor", line: "Write and score pages before they go live." },
    ],
  },
  {
    key: "audit", name: "Audit & reports", mods: [
      { name: "Audit Engine", line: "Full AI visibility audits on demand. The free audit is one slice of it." },
      { name: "Tech Health Analysis", line: "A graded health check of your site, exportable." },
      { name: "GEO Reports", line: "Shareable AI visibility reports for your team and leadership." },
      { name: "Organic Reports", line: "SEO reporting, in the same place." },
    ],
  },
];

export const MODULE_COUNT = AREAS.reduce((n, a) => n + a.mods.length, 0);
