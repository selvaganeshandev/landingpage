import { Loader2 } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { Domain } from "@/stores/domainStore";

/**
 * Shown above a page's content while a domain is still being analysed.
 *
 * This replaces the previous behaviour, where ProcessingStateCard took over the
 * whole content area and the domain could not even be selected. Analysis runs
 * in the background and results land progressively, so locking the entire app
 * out of a domain for the duration hid data that was already there. The banner
 * keeps the explanation without taking the page away.
 */

// Mirrors ProcessingStateCard's mapping so both surfaces agree on progress.
const progressFor = (status?: string | null, message?: string | null): number => {
  if (status === 'INIT') return 10;
  if (status === 'SCHD') return 20;
  if (status === 'PROC') {
    if (!message) return 30;
    const m = message.toLowerCase();
    if (m.includes('keyword') || m.includes('scraping')) return 35;
    if (m.includes('prompt') && m.includes('generat')) return 45;
    if (m.includes('group') || m.includes('cluster')) return 55;
    if (m.includes('analytic')) return 60;
    return 40;
  }
  return 65;
};

export const ProcessingBanner = ({ domain }: { domain: Domain }) => {
  const progress = progressFor(domain.processing_status, domain.track_message);

  return (
    <div className="px-8 pt-6">
      <div className="rounded-lg border border-primary/30 bg-primary/5 p-4 space-y-3">
        <div className="flex items-start gap-3">
          <Loader2 className="h-5 w-5 text-primary animate-spin mt-0.5 flex-shrink-0" />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium">
              {domain.name} is still being analysed
            </p>
            <p className="text-sm text-muted-foreground">
              {/* The backend already writes a precise, human-readable status
                  here — e.g. "Prompts ready: 105 keywords and 10 groups.
                  Queuing for LLM analysis..." — so prefer it over a guess. */}
              {domain.track_message ||
                "Setting things up. Pages will fill in as results arrive."}
            </p>
          </div>
          <span className="text-sm font-medium tabular-nums text-primary flex-shrink-0">
            {progress}%
          </span>
        </div>
        <Progress value={progress} className="h-1.5" />
        <p className="text-xs text-muted-foreground">
          You can keep working — pages populate as each stage finishes, and this
          banner disappears once the analysis completes.
        </p>
      </div>
    </div>
  );
};

export default ProcessingBanner;
