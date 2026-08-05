import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Upload, FileSpreadsheet, X, Download, Loader2, CircleAlert } from "lucide-react";

/**
 * Upload step of Add Prompt Group.
 *
 * Sends the file to the backend, which parses it, themes the prompts with the
 * internal model, and returns a run in DONE with candidates attached — exactly
 * what AI generation produces. The caller then shows the same review table, so
 * an uploaded list and a generated one are indistinguishable from here on.
 *
 * Owns its own upload state rather than lifting it: the parent only needs to
 * know that a run now exists.
 */

interface PromptUploadStepProps {
  /** Uploads the file and resolves once the run exists. */
  onUpload: (file: File) => Promise<void>;
  onFileSelected?: (file: File | null) => void;
}

const ACCEPTED = ".csv,.xlsx,.xls";
const TEMPLATE_ROWS = [
  "prompt",
  "What is the best web scraping API for developers?",
  "How do I convert websites into structured JSON?",
  "Which tools handle JavaScript rendering well?",
];

export const PromptUploadStep = ({ onUpload, onFileSelected }: PromptUploadStepProps) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pick = (next: File | null) => {
    setFile(next);
    setError(null);
    onFileSelected?.(next);
  };

  const submit = async () => {
    if (!file || busy) return;
    setBusy(true);
    setError(null);
    try {
      await onUpload(file);
    } catch (e: any) {
      setError(e?.message || "That file could not be processed.");
    } finally {
      setBusy(false);
    }
  };

  /** A one-column CSV is the format least likely to be got wrong, and it opens
   *  in Excel and Sheets alike. Built inline so there is no asset to serve. */
  const downloadTemplate = () => {
    const blob = new Blob([TEMPLATE_ROWS.join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "prompt-template.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="py-2 space-y-5">
      <div>
        <h2 className="font-inter text-xl font-bold tracking-tight">
          Upload your prompt list
        </h2>
        <p className="text-muted-foreground mt-1.5 text-sm">
          Bring prompts from a spreadsheet. You'll review and edit everything
          before anything is tracked.
        </p>
      </div>

      {!file ? (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragging(false);
            pick(e.dataTransfer.files?.[0] ?? null);
          }}
          onClick={() => inputRef.current?.click()}
          className={`rounded-xl border-2 border-dashed p-10 text-center cursor-pointer transition-all ${
            isDragging
              ? "border-primary bg-primary/5"
              : "border-border hover:border-primary/50 hover:bg-muted/30"
          }`}
        >
          <div className="h-12 w-12 rounded-xl bg-success/10 flex items-center justify-center mx-auto">
            <Upload className="h-6 w-6 text-success" />
          </div>
          <p className="font-semibold mt-4">
            Drop your file here, or click to browse
          </p>
          <p className="text-sm text-muted-foreground mt-1">
            Supports .csv, .xlsx and .xls
          </p>

          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED}
            className="hidden"
            onChange={(e) => pick(e.target.files?.[0] ?? null)}
          />
        </div>
      ) : (
        <div className="rounded-xl border border-border bg-card p-4 flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-success/10 flex items-center justify-center shrink-0">
            <FileSpreadsheet className="h-5 w-5 text-success" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="font-medium text-sm truncate">{file.name}</p>
            <p className="text-xs text-muted-foreground">
              {(file.size / 1024).toFixed(1)} KB
            </p>
          </div>
          <button
            type="button"
            onClick={() => pick(null)}
            disabled={busy}
            className="text-muted-foreground hover:text-destructive transition-colors shrink-0 disabled:opacity-40"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3.5 flex gap-2.5">
          <CircleAlert className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
          <p className="text-xs text-foreground/80 leading-relaxed">{error}</p>
        </div>
      )}

      <div className="rounded-lg border border-border bg-muted/30 p-4 flex items-start gap-3">
        <Download className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
        <div className="flex-1">
          <p className="text-sm font-medium">Not sure about the format?</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            One prompt per row. Put them in the first column, or under a heading
            called "prompt".
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={downloadTemplate}
          className="border-border shrink-0"
        >
          Template
        </Button>
      </div>

      {/* Sits with the dropzone rather than in the wizard footer: the action
          belongs to the file, and the wait needs explaining where the file is. */}
      <div className="flex items-center justify-end gap-3">
        {busy && (
          <span className="text-xs text-muted-foreground">
            Reading the file and grouping prompts by theme…
          </span>
        )}
        <Button
          type="button"
          onClick={submit}
          disabled={!file || busy}
          className="gradient-primary"
        >
          {busy ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Processing…
            </>
          ) : (
            "Continue"
          )}
        </Button>
      </div>
    </div>
  );
};
