import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Upload, FileSpreadsheet, X, Download } from "lucide-react";

/**
 * Upload step of Add Prompt Group — presentation only.
 *
 * Selecting a file records it in local state and shows the summary card; the
 * parse and the review table that follows are not built yet, so nothing is
 * sent anywhere. Kept as its own component so wiring it up later touches this
 * file and not the dialog.
 */

interface PromptUploadStepProps {
  onFileSelected?: (file: File | null) => void;
}

const ACCEPTED = ".csv,.xlsx,.xls";

export const PromptUploadStep = ({ onFileSelected }: PromptUploadStepProps) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const pick = (next: File | null) => {
    setFile(next);
    onFileSelected?.(next);
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
            className="text-muted-foreground hover:text-destructive transition-colors shrink-0"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      <div className="rounded-lg border border-border bg-muted/30 p-4 flex items-start gap-3">
        <Download className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
        <div className="flex-1">
          <p className="text-sm font-medium">Not sure about the format?</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            Download the template with every supported column filled in.
          </p>
        </div>
        <Button variant="outline" size="sm" className="border-border shrink-0">
          Template
        </Button>
      </div>
    </div>
  );
};
