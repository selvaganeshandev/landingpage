import { useMemo, useState } from "react";
import {
  Card, CardContent, CardDescription, CardHeader, CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useDomainStore } from "@/stores/domainStore";
import {
  CADENCE_OPTIONS, cadenceOf, callsPerMonth, creditsPerSweep, describeNextSweep,
  optionFor, type Cadence,
} from "@/lib/sweep-cadence";
import { getFaviconUrl, handleFaviconError } from "@/utils/faviconHelper";
import { Globe, Search } from "lucide-react";

/**
 * Every project's sweep cadence, side by side.
 *
 * The full sweep re-runs every prompt of every project across every AI platform,
 * so its cost scales with the whole corpus. The corpus is long-tailed: a handful
 * of projects hold most of the prompts, and the tail does not move enough to be
 * worth four runs a month. This is where a client sets the cadence for all of
 * them at once; Overview > Schedules shows the same setting for one project in
 * more detail.
 *
 * Laid out as the All Domains tab is — same Card, same header, same bordered
 * rows, and the page does the scrolling — so the two tabs read as one product
 * rather than two. A panel with its own scrollbar inside a scrolling page traps
 * the wheel and hides how many projects there are.
 *
 * READ-ONLY on purpose, and not clickable either. The cadence is changed on the
 * project's own settings page (Organization Settings > a domain > Basic Info),
 * so one place owns the edit. This screen exists for the questions that need
 * every project side by side - what does each one cost, when does each next
 * run, where is the money going.
 *
 * The engine reads the same column in
 * core/processing_tasks.schedule_weekly_prompt_batches.
 */
export const DomainSweepCadence = () => {
  // Already loaded for the project switcher on every page, so reading it here
  // adds no request.
  const { domains, sweep } = useDomainStore();
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return domains;
    return domains.filter(
      (d) =>
        (d.name || "").toLowerCase().includes(q) ||
        (d.url || "").toLowerCase().includes(q),
    );
  }, [domains, query]);

  // LLM calls a month, so the effect of a change is visible in the unit that
  // actually costs money rather than as an abstract cadence label.
  //
  // A sweep queries every prompt on every enabled platform, so the platform
  // count belongs in this total. Leaving it out is what made this card report a
  // quarter of the real volume while Overview, which included it, reported the
  // full figure under the same words.
  const platformCount = sweep?.platforms.length ?? 0;
  const monthlyCalls = useMemo(
    () => domains.reduce((sum, d) => sum + callsPerMonth(d, platformCount), 0),
    [domains, platformCount],
  );

  /**
   * One block per cadence, in CADENCE_OPTIONS order: Weekly, 15 days, 30 days,
   * Off. Flat, the list answered "what is this project set to" one row at a
   * time; clustered it answers "how is the estate split, and what is each tier
   * costing me" at a glance - which is the question the schedule exists for.
   *
   * Empty tiers are dropped rather than shown as a zero: a heading with nothing
   * under it reads as a loading failure.
   */
  const clusters = useMemo(
    () =>
      CADENCE_OPTIONS.map((option) => {
        const members = filtered.filter((d) => cadenceOf(d) === option.value);
        return {
          option,
          members,
          prompts: members.reduce((s, d) => s + (d.prompt_count ?? 0), 0),
          creditsPerMonth: members.reduce(
            (s, d) =>
              s + creditsPerSweep(d, sweep?.platforms ?? []) * option.runsPerMonth,
            0,
          ),
        };
      }).filter((c) => c.members.length > 0),
    [filtered, sweep],
  );

  return (
    <Card className="border border-border">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Sweep cadence ({domains.length})</CardTitle>
            <CardDescription>
              The full sweep re-runs every prompt on every AI platform. Every project's
              schedule and what it costs, side by side — open a project to change it.
              {/* Hidden until the platform count arrives with the domain list, rather
                  than briefly showing a total that is 0x the real one. */}
              {platformCount > 0 && (
                <>
                  {" "}Currently ≈ {monthlyCalls.toLocaleString()} LLM calls per month
                  across {platformCount} platforms.
                </>
              )}
            </CardDescription>
          </div>
          <div className="relative w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search domains..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="pl-9"
            />
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="space-y-3">
          {filtered.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Globe className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p>{query.trim() ? "No domains found" : "No domains added yet"}</p>
            </div>
          ) : (
            clusters.map((cluster) => (
              <div key={cluster.option.value} className="space-y-3">
                {/* Sticky so the tier stays named while a long block scrolls. */}
                <div className="sticky top-0 z-10 flex items-center justify-between gap-3
                                bg-background/95 backdrop-blur py-2">
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-semibold">{cluster.option.label}</h4>
                    <Badge variant="secondary" className="font-normal">
                      {cluster.members.length}{" "}
                      {cluster.members.length === 1 ? "project" : "projects"}
                    </Badge>
                  </div>
                  <div className="text-xs text-muted-foreground tabular-nums">
                    {cluster.prompts.toLocaleString()} prompts
                    {platformCount > 0 && cluster.option.days !== null && (
                      <> · ≈ {cluster.creditsPerMonth.toFixed(2)} credits / month</>
                    )}
                    {cluster.option.days === null && <> · nothing scheduled</>}
                  </div>
                </div>

                {cluster.members.map((domain) => (
              <div
                key={domain.id}
                className="flex items-center justify-between p-3 border rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <img
                    src={getFaviconUrl(domain.url, 32)}
                    alt={`${domain.name} favicon`}
                    className="h-5 w-5 rounded"
                    onError={(e) => handleFaviconError(e, domain.url, domain.name, 32)}
                  />
                  <Globe className="h-5 w-5 text-muted-foreground hidden" />
                  <div>
                    <p className="font-medium capitalize">{domain.name}</p>
                    {/* The prompt count has its own column now. */}
                    <p className="text-sm text-muted-foreground">{domain.url}</p>
                  </div>
                </div>

                {/* Three figures only, beside the control they belong to:
                    how much there is to sweep, what one sweep costs, and when it
                    next runs. Group and per-call counts were here too and were
                    removed - a row that answers four questions answers none of
                    them at a glance. Hidden below lg so a narrow window keeps
                    the name and the dropdown, which are what the row is for. */}
                <div className="hidden lg:flex items-center gap-8 ml-auto mr-6 text-right">
                  <div className="w-20">
                    <div className="text-sm font-medium tabular-nums">
                      {(domain.prompt_count ?? 0).toLocaleString()}
                    </div>
                    <div className="text-xs text-muted-foreground">prompts</div>
                  </div>
                  <div className="w-24">
                    <div className="text-sm font-medium tabular-nums">
                      {platformCount > 0
                        ? creditsPerSweep(domain, sweep?.platforms ?? []).toFixed(2)
                        : "—"}
                    </div>
                    <div className="text-xs text-muted-foreground">credits / sweep</div>
                  </div>
                  <div className="w-24">
                    <div className="text-sm font-medium">
                      {describeNextSweep(domain, sweep?.enabled !== false).label}
                    </div>
                    <div className="text-xs text-muted-foreground">next sweep</div>
                  </div>
                </div>

                <div className="w-[170px] flex justify-end">
                  <Badge
                    variant={cadenceOf(domain) === "off" ? "secondary" : "outline"}
                    className="font-normal"
                  >
                    {optionFor(cadenceOf(domain)).label}
                  </Badge>
                </div>
              </div>
                ))}
              </div>
            ))
          )}
        </div>

        <p className="text-xs text-muted-foreground">
          Read-only. A project's schedule is changed on its own settings page, under
          Basic Info.
        </p>
      </CardContent>
    </Card>
  );
};
