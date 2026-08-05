import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Loader2, Check, Trash2, Sparkles } from "lucide-react";

/**
 * Review step — nothing is tracked until the user accepts here.
 *
 * Grouped by cluster because that is what each accepted group becomes: one
 * PromptGroup, its best-scoring member the primary prompt and the rest
 * variants. Rows are editable in place since a near-miss prompt is usually
 * worth fixing rather than discarding.
 */

export interface Candidate {
  id: number;
  text: string;
  intent: string;
  intent_label: string;
  entity: string;
  is_branded: boolean;
  cluster_key: string;
  cluster_title: string;
  score_elicits_brands: number;
}

interface PromptReviewTableProps {
  candidates: Candidate[];
  saving?: boolean;
  onAccept: (acceptedIds: number[], edits: Record<string, string>) => void;
  onDiscard: () => void;
}

export const PromptReviewTable = ({
  candidates,
  saving = false,
  onAccept,
  onDiscard,
}: PromptReviewTableProps) => {
  const [selected, setSelected] = useState<Set<number>>(
    () => new Set(candidates.map((c) => c.id)),
  );
  const [edits, setEdits] = useState<Record<string, string>>({});

  const clusters = useMemo(() => {
    const map = new Map<string, Candidate[]>();
    candidates.forEach((c) => {
      const key = c.cluster_key || "general";
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(c);
    });
    return Array.from(map.entries());
  }, [candidates]);

  const toggle = (id: number) =>
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const allSelected = selected.size === candidates.length;

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
        <div>
          <h2 className="font-inter text-2xl font-bold tracking-tight">
            Review your prompts
          </h2>
          <p className="text-sm text-muted-foreground mt-1.5">
            {candidates.length} generated across {clusters.length} themes.
            Nothing is tracked until you add them.
          </p>
        </div>
        <button
          type="button"
          onClick={() =>
            setSelected(allSelected ? new Set() : new Set(candidates.map((c) => c.id)))
          }
          className="text-sm font-medium text-primary hover:underline underline-offset-2"
        >
          {allSelected ? "Deselect all" : "Select all"}
        </button>
      </div>

      <div className="space-y-5">
        {clusters.map(([key, rows]) => (
          <div key={key} className="rounded-xl border border-border overflow-hidden">
            <div className="bg-muted/40 px-4 py-2.5 border-b border-border flex items-center justify-between">
              <p className="text-sm font-semibold">{rows[0].cluster_title || key}</p>
              <Badge variant="secondary" className="text-[11px]">
                {rows.length} prompt{rows.length > 1 ? "s" : ""}
              </Badge>
            </div>

            <div className="divide-y divide-border">
              {rows.map((c, i) => (
                <div key={c.id} className="flex items-start gap-3 px-4 py-3">
                  <Checkbox
                    checked={selected.has(c.id)}
                    onCheckedChange={() => toggle(c.id)}
                    className="mt-2"
                  />
                  <div className="flex-1 min-w-0">
                    <Input
                      value={edits[c.id] ?? c.text}
                      onChange={(e) =>
                        setEdits((p) => ({ ...p, [c.id]: e.target.value }))
                      }
                      className="border-0 shadow-none focus-visible:ring-1 px-1 h-8 text-sm"
                    />
                    <div className="flex flex-wrap items-center gap-1.5 mt-1 px-1">
                      <Badge variant="outline" className="text-[10px] font-normal">
                        {c.intent_label || c.intent}
                      </Badge>
                      <Badge
                        variant="outline"
                        className={`text-[10px] font-normal ${
                          c.is_branded ? "text-primary border-primary/40" : ""
                        }`}
                      >
                        {c.is_branded ? "Branded" : "Unbranded"}
                      </Badge>
                      {i === 0 && (
                        <span className="text-[10px] text-muted-foreground">
                          Primary in this group
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="flex items-center gap-2 mt-6 pt-5 border-t border-border">
        <Button
          variant="outline"
          onClick={onDiscard}
          disabled={saving}
          className="border-border text-muted-foreground"
        >
          <Trash2 className="h-4 w-4 mr-2" />
          Discard
        </Button>
        <div className="ml-auto">
          <Button
            onClick={() => onAccept(Array.from(selected), edits)}
            disabled={saving || selected.size === 0}
            className="gradient-primary shadow-md shadow-primary/20"
          >
            {saving ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Adding…
              </>
            ) : (
              <>
                <Check className="h-4 w-4 mr-2" />
                Add {selected.size} prompt{selected.size === 1 ? "" : "s"}
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
};

/** Progress panel shown while the engine works through the six stages. */
export const GenerationProgress = ({
  stageLabel,
  stageIndex,
  stageTotal,
  progress,
}: {
  stageLabel: string;
  stageIndex: number;
  stageTotal: number;
  progress: number;
}) => (
  <div className="flex flex-col items-center justify-center py-16 text-center">
    <div className="h-12 w-12 rounded-xl gradient-primary flex items-center justify-center shadow-md shadow-primary/20">
      <Sparkles className="h-6 w-6 text-primary-foreground animate-pulse" />
    </div>
    <h3 className="font-semibold text-lg mt-4">Generating your prompts</h3>
    <p className="text-sm text-muted-foreground mt-1">
      Step {stageIndex || 1} of {stageTotal} · {stageLabel || "Starting…"}
    </p>
    <div className="w-full max-w-sm h-1.5 rounded-full bg-muted mt-5 overflow-hidden">
      <div
        className="h-full gradient-primary transition-all duration-500"
        style={{ width: `${Math.max(5, progress)}%` }}
      />
    </div>
    <p className="text-xs text-muted-foreground mt-4">
      This runs in the background — you can leave this page and come back.
    </p>
  </div>
);
