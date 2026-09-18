/**
 * "What's new" — the release notes a user can open from the account menu.
 *
 * Static on purpose: a hand-written list is faster to read than a changelog
 * feed and never depends on a network call. Newest first; keep entries to one
 * line each so the dialog stays a glance, not a document.
 */
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Sparkles } from "lucide-react";

interface Release {
  date: string;      // "Sep 2026"
  title: string;
  items: string[];
}

const RELEASES: Release[] = [
  {
    date: "Sep 2026",
    title: "Audit Engine",
    items: [
      "Generate a GEO audit for any URL — a public, shareable report in about three minutes.",
      "Designed PDF: executive summary, engine cards, funnel heatmap, competitor matrix, 90-day plan.",
      "Website Health scorecard with technical SEO checks, indexability, broken links and an issues CSV export.",
      "Backlink authority and Core Web Vitals in the report (when enabled).",
      "Convert an audit into a tracked project in one click; warm-lead alerts when a report is opened.",
    ],
  },
  {
    date: "Sep 2026",
    title: "Schedule",
    items: [
      "Set how often each project is swept — weekly, every 15 days, every 30 days, or off.",
      "See the cost per sweep and per month before you commit to a cadence.",
      "A Schedule tab on every project: prompts, engines, cost per run and the next run date.",
    ],
  },
];

export function WhatsNewDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Sparkles className="h-4 w-4 text-primary" />What's new</DialogTitle>
          <DialogDescription>Recent changes to PromptMaxx.</DialogDescription>
        </DialogHeader>
        <div className="space-y-5 max-h-[60vh] overflow-y-auto pr-1">
          {RELEASES.map((r) => (
            <section key={r.date + r.title}>
              <div className="flex items-baseline justify-between gap-2">
                <h3 className="text-sm font-semibold">{r.title}</h3>
                <span className="text-xs text-muted-foreground">{r.date}</span>
              </div>
              <ul className="mt-1.5 space-y-1">
                {r.items.map((it) => (
                  <li key={it} className="flex gap-2 text-sm leading-snug">
                    <span className="mt-[7px] h-1.5 w-1.5 flex-none rounded-full bg-primary/60" />
                    <span>{it}</span>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
