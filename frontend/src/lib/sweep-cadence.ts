import type { Domain } from "@/stores/domainStore";

/**
 * Sweep cadence — the vocabulary behind Organization Settings › Schedules.
 *
 * The full sweep re-runs every prompt of a project across every AI platform the
 * engine has enabled, so its cost scales with the whole corpus. `sweep_cadence`
 * on the domain decides how often each project is included; this module is the
 * frontend's copy of the rules the engine applies in
 * core/processing_tasks.schedule_weekly_prompt_batches.
 *
 * The day counts MUST match SWEEP_CADENCE_DAYS in that task. They are 14 and 28
 * rather than 15 and 30 because the sweep only runs on the weekly cron: a
 * project due on day 15 would wait for the day-21 run and drift to a 21-day
 * cadence. The labels stay "15 days" / "30 days" because that is how a client
 * thinks about it.
 *
 * Only what the Schedules list renders is exported. The rest is module-private
 * on purpose: an exported helper with no consumer invites a second, divergent
 * copy of the same rule somewhere else.
 */

export type Cadence = "weekly" | "biweekly" | "monthly" | "off";

export interface CadenceOption {
  value: Cadence;
  /** Long form, for the select. */
  label: string;
  /** Short form, for table cells and chips. */
  short: string;
  /** Days between sweeps. null means never. */
  days: number | null;
  /** Sweeps in a 28-day month, used for load arithmetic. */
  runsPerMonth: number;
}

export const CADENCE_OPTIONS: CadenceOption[] = [
  { value: "weekly", label: "Weekly", short: "Weekly", days: 7, runsPerMonth: 4 },
  { value: "biweekly", label: "Every 15 days", short: "15 days", days: 14, runsPerMonth: 2 },
  { value: "monthly", label: "Every 30 days", short: "30 days", days: 28, runsPerMonth: 1 },
  { value: "off", label: "Off — no sweep", short: "Off", days: null, runsPerMonth: 0 },
];

/** A project saved before the field existed comes back without it. The engine
 *  reads a missing value as weekly too, so the row shows what will happen. */
export const cadenceOf = (domain: Pick<Domain, "sweep_cadence">): Cadence =>
  domain.sweep_cadence ?? "weekly";

/** The option row for a cadence - exported so a screen can print its label
 *  without keeping a second copy of the mapping. */
export const optionFor = (cadence: Cadence): CadenceOption =>
  CADENCE_OPTIONS.find((o) => o.value === cadence) ?? CADENCE_OPTIONS[0];

/** LLM calls one sweep of this project costs: every prompt on every platform. */
const callsPerSweep = (domain: Domain, platformCount: number): number =>
  (domain.prompt_count ?? 0) * platformCount;

/**
 * What one call to each platform costs, in OpenRouter credits (1 credit = $1).
 *
 * Rates read from https://openrouter.ai/api/v1/models on 2026-09-17. Output
 * sizes are the MEASURED median of this product's own stored answers (7,609
 * rows in PromptAnalyticsRun), not a vendor estimate — ChatGPT's figure adds
 * ~1,600 hidden reasoning tokens, which gpt-5-mini bills as output. `search` is
 * the per-call web charge: both the ChatGPT and Claude paths ground their
 * answers, and that is billed on top of tokens.
 *
 * Keyed by the platform names the API reports, so a platform this org has never
 * queried contributes nothing. An unknown name falls back to the ChatGPT rate
 * rather than to zero — under-stating a bill is the worse failure.
 */
const CALL_COST: Record<string, number> = {
  // input$/M, output$/M, out tokens, search
  ChatGPT: 0.000106 + 0.011330 + 0.010,          // gpt-5-mini,        5,665 tok
  Claude: 0.001275 + 0.028800 + 0.020,           // claude-sonnet-4.5, 1,920 tok
  "Google Gemini": 0.000128 + 0.009118,          // gemini-2.5-flash,  3,647 tok
  Perplexity: 0.000425 + 0.001382 + 0.005,       // sonar,             1,382 tok
};
const FALLBACK_CALL_COST = 0.0214;

/** The platforms a run fans out to when the caller does not know which are
 *  enabled. Track Prompts is triggered from Organization Settings, which does
 *  not load the per-project platform list, and production has all four on — so
 *  this is the honest default for an estimate shown before the run starts. */
export const ALL_PLATFORMS = ["ChatGPT", "Claude", "Google Gemini", "Perplexity"];

/**
 * Rough dollar cost of re-running `promptCount` prompts across `platforms`.
 *
 * Shown in the Track Prompts confirmation so the cost is known BEFORE the run,
 * not discovered afterwards. Uses the same CALL_COST table as the Schedules
 * screen, so the two can never quote different numbers for the same work.
 *
 * An estimate, not a quote: CALL_COST is built from measured median output
 * sizes and the provider rates of a given day, so a long-answering prompt costs
 * more than this and a short one less.
 */
export const estimateRunCost = (
  promptCount: number,
  platforms: string[] = ALL_PLATFORMS,
): number =>
  Math.max(0, promptCount || 0) *
  platforms.reduce((sum, p) => sum + (CALL_COST[p] ?? FALLBACK_CALL_COST), 0);

/** Credits one sweep of this project costs: every prompt, on every platform. */
export const creditsPerSweep = (domain: Domain, platforms: string[]): number =>
  (domain.prompt_count ?? 0) *
  platforms.reduce((sum, p) => sum + (CALL_COST[p] ?? FALLBACK_CALL_COST), 0);

/**
 * What this project costs in a 28-day month: one sweep, times how many sweeps
 * its cadence gets. A cadence of "off" has no runs, so it costs nothing —
 * which is the honest answer rather than a blank.
 */
export const creditsPerMonth = (domain: Domain, platforms: string[]): number =>
  creditsPerSweep(domain, platforms) * optionFor(cadenceOf(domain)).runsPerMonth;

/**
 * LLM calls this project costs in a 28-day month.
 *
 * The card header prints the org-wide total from this, and it MUST include the
 * platform count: leaving it out reported a quarter of the real volume.
 */
export const callsPerMonth = (domain: Domain, platformCount: number): number =>
  callsPerSweep(domain, platformCount) * optionFor(cadenceOf(domain)).runsPerMonth;

/**
 * The last time this project's prompts actually ran.
 *
 * `last_swept_at` is written by the sweep and is the right answer once one has
 * run. It is NULL on every project today because the column is new, and
 * counting from NULL made every row say the same thing. `tracked_at` is the
 * fallback: the domain stamps it whenever its prompts finish, from a sweep OR
 * from Track Prompts, and it matches the newest PromptAnalytics row exactly —
 * checked across the corpus.
 */
const lastSweptAt = (domain: Domain): Date | null => {
  const raw = domain.last_swept_at || domain.tracked_at;
  if (!raw) return null;
  const at = new Date(raw);
  return Number.isNaN(at.getTime()) ? null : at;
};

/**
 * When this project is next due: last run + its cadence. Nothing else.
 *
 * Deliberately NOT rounded up to the weekly cron. The cron is when the sweep
 * can fire, but rounding to it collapsed every overdue project onto the same
 * Sunday — 71 rows all reading "in 3 days", which answers nothing. A client on
 * 15 days swept today should read "in 14 days". The sweep still fires on the
 * Sunday on or after this date.
 */
const nextSweepAt = (domain: Domain): Date | null => {
  const { days } = optionFor(cadenceOf(domain));
  if (days === null) return null;
  const from = lastSweptAt(domain);
  if (!from) return new Date(0); // never run - due as soon as sweeps do
  return new Date(from.getTime() + days * 86_400_000);
};

export interface NextSweep {
  /** Short form for a table cell. */
  label: string;
  /** The line underneath: why that is the answer. */
  detail: string;
}

/**
 * What to show for "next sweep", given whether the engine will run one at all.
 *
 * "Paused" is reserved for the cadence being set to Off — the one state where
 * there genuinely is no next sweep to count down to. The server-side kill
 * switch is a different thing: the schedule still stands and the countdown is
 * still the answer to "when is this client next re-queried", so it keeps the
 * number and says the run is held in the line underneath. Collapsing both into
 * "Paused" hid the days from every project on the page.
 */
export const describeNextSweep = (
  domain: Domain,
  sweepsEnabled: boolean,
): NextSweep => {
  if (cadenceOf(domain) === "off") {
    return { label: "Paused", detail: "Sweep is off for this project" };
  }
  const run = nextSweepAt(domain);
  if (run === null) {
    return { label: "Paused", detail: "Sweep is off for this project" };
  }
  const swept = lastSweptAt(domain);
  if (!swept) {
    return { label: "Not swept yet", detail: "Runs on the first sweep" };
  }

  const days = Math.ceil((run.getTime() - Date.now()) / 86_400_000);
  const date = run.toLocaleDateString(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
  const label =
    days <= 0 ? "Due now" : days === 1 ? "Tomorrow" : `in ${days} days`;
  const why = !sweepsEnabled
    ? "held — sweeps are off server-side"
    : `last run ${swept.toLocaleDateString(undefined, { day: "numeric", month: "short" })}`;
  return { label, detail: `${date} · ${why}` };
};
