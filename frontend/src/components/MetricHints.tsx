import { MetricHint } from "@/components/InfoHint";

/**
 * Explanations for the Insights headline metrics.
 *
 * Lives under components/ rather than lib/ on purpose: the repo's .gitignore
 * carries a Python-packaging `lib/` rule, which also matches frontend/src/lib/,
 * so anything added there is silently never committed and would go missing from
 * a build made off the repository.
 *
 * Kept in one place so the same metric never gets two different definitions on
 * two different cards. Each entry states what the number is, then how the
 * backend actually derives it — the formulas mirror
 * `backend/analytics/views_dashboard.py` (`_live_window_metrics`,
 * `compute_visibility_score`), so any change there must be reflected here.
 */

/** The control that sets the window for every date-scoped figure on the page. */
const WINDOW = "the date range at the top of the page (the last 30 days if you haven't picked one)";

export const METRIC_HINTS = {
  totalPrompts: (
    <MetricHint
      title="Questions we ask AI on your behalf"
      plain="The prompts you track. Each one is put to every enabled AI platform on a recurring run, and everything else on this page is measured from those answers."
      formula={
        <>
          A count of every prompt saved for this domain. This is a running total, so unlike the
          other cards it is <strong>not</strong> limited by the date range — picking a narrower
          window will not lower it. Choosing a single LLM narrows it to prompts that have run on
          that platform.
        </>
      }
    />
  ),

  totalCitations: (
    <MetricHint
      title="Source links the AI showed"
      plain="Every link an AI answer offered as a source — yours and everyone else's — across the prompts you track."
      formula={
        <>
          All citation links in the tracked answers over {WINDOW}, added up. Each link counts
          separately, so one page cited in five answers counts five times. For pages on{" "}
          <strong>your own</strong> domain only, switch the Distribution by LLM card to Cited Pages.
        </>
      }
    />
  ),

  totalMentions: (
    <MetricHint
      title="Times AI named your brand"
      plain="How often AI answers actually referred to your brand when responding to the prompts you track."
      formula={
        <>
          Brand mentions summed across every tracked answer in {WINDOW}. A single answer can
          mention you more than once, so this can exceed the number of answers checked.
        </>
      }
    />
  ),

  visibilityScore: (
    <MetricHint
      title="How prominently you show up in AI answers (0–100)"
      plain="One number combining how often AI mentions you, cites you, speaks well of you, and how early it names you."
      formula={
        <>
          A weighted blend of four rates measured over the answers checked in {WINDOW}:
          <ul className="mt-1 space-y-0.5">
            <li>• <strong>40%</strong> mention rate — answers that named you ÷ answers checked</li>
            <li>• <strong>30%</strong> citation rate — answers that linked your site ÷ answers checked</li>
            <li>• <strong>20%</strong> sentiment — average tone of those mentions, rescaled from −1…+1 to 0…1</li>
            <li>• <strong>10%</strong> prominence — position 1 scores full credit, position 10 or worse scores none</li>
          </ul>
          <p className="mt-1">
            No mentions means a score of 0. It is scored over the whole window at once, so it is
            not the average of the points on the trend chart.
          </p>
        </>
      }
    />
  ),

  avgPosition: (
    <MetricHint
      title="Where you land inside the answer — lower is better"
      plain="When AI does name your brand, how early it appears. Position 1 means you were named first, ahead of every other brand."
      formula={
        <>
          The average of your brand's rank across answers that mentioned you in {WINDOW}, weighted
          by how many times each answer mentioned you, then rounded. Answers that never mentioned
          you are excluded, so this describes prominence, not frequency — for frequency see Total
          Mentions.
        </>
      }
    />
  ),
} as const;
