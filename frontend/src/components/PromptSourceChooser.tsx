import { Button } from "@/components/ui/button";
import { Sparkles, BarChart3, Upload, ArrowRight, AlertCircle } from "lucide-react";
import { GoogleIcon } from "@/components/GoogleIcon";

/**
 * Step 1 of Add Prompt Group — how the prompt list gets built.
 *
 * Three routes into the same review step: AI generation, real Search Console
 * demand, or a spreadsheet upload.
 * Presentation only; each card reports the chosen method upward and the dialog
 * decides what to render next.
 *
 * "From audit" is built but hidden behind SHOW_AUDIT: the GEO Audit Engine does
 * not exist yet, and a permanently locked card sitting between the two working
 * options read as a broken feature rather than a forthcoming one. The card is
 * kept rather than deleted so restoring it is a one-line change once audits
 * ship.
 */

export type PromptSource = "ai" | "audit" | "upload" | "gsc";

const SHOW_AUDIT = false;

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
          How would you like to add prompts?
        </h2>
        <p className="text-muted-foreground mt-2 text-sm max-w-md mx-auto">
          Let AI write them, or bring a list you already have. Either way you
          review everything before anything is tracked.
        </p>
      </div>

      <div
        className={`grid grid-cols-1 gap-4 ${
          SHOW_AUDIT ? "md:grid-cols-4" : "md:grid-cols-3"
        }`}
      >
        {/* ---------- Generate with AI ---------- */}
        <div className="group flex flex-col rounded-xl border border-border bg-card p-5 transition-all hover:border-primary/50 hover:shadow-lg hover:shadow-primary/5">
          <div className="h-11 w-11 rounded-xl gradient-primary flex items-center justify-center shadow-md shadow-primary/20">
            <Sparkles className="h-5 w-5 text-primary-foreground" />
          </div>

          <h3 className="font-semibold text-base mt-4">Generate with AI</h3>
          <p className="text-sm text-muted-foreground mt-1.5 leading-relaxed">
            Tell us about your brand — or pull the answers straight off your
            website — and we'll write the questions for you.
          </p>

          <div className="border-t border-border my-4" />

          <ul className="space-y-2 text-sm font-medium flex-1">
            <li>Ready in about a minute</li>
            <li>The questions buyers really ask, not ads for you</li>
            <li>Edit or drop any of them before they go live</li>
          </ul>

          <Button
            onClick={() => onSelect("ai")}
            className="gradient-primary shadow-md shadow-primary/20 w-full mt-5"
          >
            <Sparkles className="h-4 w-4 mr-2" />
            Generate with AI
          </Button>
        </div>

        {/* ---------- From Search Console ---------- */}
        <div className="group flex flex-col rounded-xl border border-border bg-card p-5 transition-all hover:border-primary/50 hover:shadow-lg hover:shadow-primary/5">
          <div className="h-11 w-11 rounded-xl bg-blue-500/10 flex items-center justify-center">
            <GoogleIcon className="h-5 w-5" />
          </div>

          <h3 className="font-semibold text-base mt-4">From Search Console</h3>
          <p className="text-sm text-muted-foreground mt-1.5 leading-relaxed">
            Build prompts from what people already searched to find you — real
            questions, not invented ones.
          </p>

          <div className="border-t border-border my-4" />

          <ul className="space-y-2 text-sm font-medium flex-1">
            <li>Your own Search Console demand</li>
            <li>Branded searches left out — they measure nothing</li>
            <li>Rewritten as the question people ask an assistant</li>
          </ul>

          <Button
            variant="outline"
            onClick={() => onSelect("gsc")}
            className="w-full mt-5"
          >
            <GoogleIcon className="h-4 w-4 mr-2" />
            Fetch from Search Console
          </Button>
        </div>

        {/* ---------- From audit (hidden until the audit engine ships) ---------- */}
        {SHOW_AUDIT && (
          <div
            className={`flex flex-col rounded-xl border border-border bg-card p-5 transition-all ${
              hasCompletedAudit
                ? "group hover:border-primary/50 hover:shadow-lg hover:shadow-primary/5"
                : ""
            }`}
          >
            <div
              className={`h-11 w-11 rounded-xl flex items-center justify-center ${
                hasCompletedAudit ? "bg-primary/10" : "bg-muted"
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
        )}

        {/* ---------- Upload CSV / Excel ---------- */}
        <div className="group flex flex-col rounded-xl border border-border bg-card p-5 transition-all hover:border-primary/50 hover:shadow-lg hover:shadow-primary/5">
          <div className="h-11 w-11 rounded-xl bg-success/10 flex items-center justify-center">
            <Upload className="h-5 w-5 text-success" />
          </div>

          <h3 className="font-semibold text-base mt-4">Upload your own</h3>
          <p className="text-sm text-muted-foreground mt-1.5 leading-relaxed">
            Already have a list somewhere? Bring it straight in from a
            spreadsheet.
          </p>

          <div className="border-t border-border my-4" />

          <ul className="space-y-2 text-sm font-medium flex-1">
            <li>Works with .csv, .xlsx and .xls</li>
            <li>Grab our template if you're unsure of the format</li>
            <li>Goes through the same review step</li>
          </ul>

          <Button
            variant="outline"
            onClick={() => onSelect("upload")}
            className="w-full mt-5 border-border"
          >
            <Upload className="h-4 w-4 mr-2" />
            Upload a file
          </Button>
        </div>
      </div>

      <p className="text-center text-xs text-muted-foreground mt-6 max-w-lg mx-auto leading-relaxed">
        Nothing is tracked until you've reviewed it and pressed add.
      </p>
    </div>
  );
};
