import { Button } from "@/components/ui/button";
import { Sparkles, BarChart3, Upload, ArrowRight, AlertCircle } from "lucide-react";

/**
 * Step 1 of Add Prompt Group — how the prompt list gets built.
 *
 * Three routes into the same review step: AI generation, a completed GEO
 * audit, or a spreadsheet upload. Presentation only; each card just reports
 * the chosen method upward and the dialog decides what to render next.
 *
 * "From audit" is rendered locked because the GEO Audit Engine does not exist
 * yet. It is shown rather than hidden so the path is discoverable and the
 * prerequisite is explicit — the same reason the reference design keeps it
 * visible with a callout instead of dropping the card.
 */

export type PromptSource = "ai" | "audit" | "upload";

interface PromptSourceChooserProps {
  onSelect: (source: PromptSource) => void;
  /** Flips the audit card out of its locked state once audits exist. */
  hasCompletedAudit?: boolean;
  onGoToAudit?: () => void;
}

export const PromptSourceChooser = ({
  onSelect,
  hasCompletedAudit = false,
  onGoToAudit,
}: PromptSourceChooserProps) => {
  return (
    <div className="py-2">
      <div className="text-center mb-8">
        <h2 className="font-inter text-2xl font-bold tracking-tight">
          How do you want to build your list?
        </h2>
        <p className="text-muted-foreground mt-2 text-sm max-w-md mx-auto">
          AI-generated, from a completed audit, or upload your own list — same
          review step afterward.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* ---------- Generate with AI ---------- */}
        <div className="group flex flex-col rounded-xl border border-border bg-card p-5 transition-all hover:border-primary/50 hover:shadow-lg hover:shadow-primary/5">
          <div className="h-11 w-11 rounded-xl gradient-primary flex items-center justify-center shadow-md shadow-primary/20">
            <Sparkles className="h-5 w-5 text-primary-foreground" />
          </div>

          <h3 className="font-semibold text-base mt-4">Generate with AI</h3>
          <p className="text-sm text-muted-foreground mt-1.5 leading-relaxed">
            Describe your goals and let AI build a targeted prompt list from
            scratch.
          </p>

          <div className="border-t border-border my-4" />

          <ul className="space-y-2 text-sm font-medium flex-1">
            <li>No prior audit needed</li>
            <li>Control funnel mix and tone</li>
            <li>Best for new topics or fresh angles</li>
          </ul>

          <Button
            onClick={() => onSelect("ai")}
            className="gradient-primary shadow-md shadow-primary/20 w-full mt-5"
          >
            <Sparkles className="h-4 w-4 mr-2" />
            Generate with AI
          </Button>
        </div>

        {/* ---------- From audit ---------- */}
        <div
          className={`flex flex-col rounded-xl border border-border bg-card p-5 transition-all ${
            hasCompletedAudit
              ? "group hover:border-primary/50 hover:shadow-lg hover:shadow-primary/5"
              : ""
          }`}
        >
          <div
            className={`h-11 w-11 rounded-xl flex items-center justify-center ${
              hasCompletedAudit
                ? "bg-primary/10"
                : "bg-muted"
            }`}
          >
            <BarChart3
              className={`h-5 w-5 ${
                hasCompletedAudit ? "text-primary" : "text-muted-foreground"
              }`}
            />
          </div>

          <h3
            className={`font-semibold text-base mt-4 ${
              hasCompletedAudit ? "" : "text-muted-foreground"
            }`}
          >
            From audit
          </h3>
          <p className="text-sm text-muted-foreground mt-1.5 leading-relaxed">
            {hasCompletedAudit
              ? "Build the list from prompts your latest GEO audit already tested."
              : "No completed audits yet. Run one first."}
          </p>

          {hasCompletedAudit ? (
            <>
              <div className="border-t border-border my-4" />
              <ul className="space-y-2 text-sm font-medium flex-1">
                <li>Grounded in real results</li>
                <li>Prioritises competitor gaps</li>
                <li>Same review table as AI and Upload</li>
              </ul>
              <Button
                variant="outline"
                onClick={() => onSelect("audit")}
                className="w-full mt-5 border-border"
              >
                Use audit results
              </Button>
            </>
          ) : (
            <div className="mt-4 flex-1 flex flex-col">
              <div className="rounded-lg border border-warning/30 bg-warning/5 p-3.5 flex-1">
                <div className="flex gap-2.5">
                  <AlertCircle className="h-4 w-4 text-warning shrink-0 mt-0.5" />
                  <p className="text-xs text-foreground/80 leading-relaxed">
                    Run a GEO Audit first to unlock this mode. Audits test your
                    brand across 100+ AI prompts and reveal where competitors
                    are winning.
                  </p>
                </div>

                <button
                  type="button"
                  onClick={onGoToAudit}
                  className="mt-3 flex items-center gap-1.5 text-xs font-semibold text-warning hover:underline underline-offset-2"
                >
                  Go to GEO Audit Engine
                  <ArrowRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* ---------- Upload CSV / Excel ---------- */}
        <div className="group flex flex-col rounded-xl border border-border bg-card p-5 transition-all hover:border-primary/50 hover:shadow-lg hover:shadow-primary/5">
          <div className="h-11 w-11 rounded-xl bg-success/10 flex items-center justify-center">
            <Upload className="h-5 w-5 text-success" />
          </div>

          <h3 className="font-semibold text-base mt-4">Upload CSV / Excel</h3>
          <p className="text-sm text-muted-foreground mt-1.5 leading-relaxed">
            Bring your own prompt list from a spreadsheet or existing workflow.
          </p>

          <div className="border-t border-border my-4" />

          <ul className="space-y-2 text-sm font-medium flex-1">
            <li>Supports .csv, .xlsx, .xls</li>
            <li>Template with all columns included</li>
            <li>Same review table as AI and Audit</li>
          </ul>

          <Button
            variant="outline"
            onClick={() => onSelect("upload")}
            className="w-full mt-5 border-border"
          >
            <Upload className="h-4 w-4 mr-2" />
            Upload file
          </Button>
        </div>
      </div>

      <p className="text-center text-xs text-muted-foreground mt-6 max-w-lg mx-auto leading-relaxed">
        You can run AI first, then audit (or the reverse), upload your own list,
        or add prompts manually in review.
      </p>
    </div>
  );
};
