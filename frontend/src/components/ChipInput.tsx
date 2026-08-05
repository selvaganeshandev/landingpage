import { useState, type KeyboardEvent } from "react";
import { Input } from "@/components/ui/input";
import { X } from "lucide-react";

/**
 * Tag-style multi-value input.
 *
 * Most of the prompt wizard's brand facts are lists that arrive pre-filled
 * from the site crawl, so the interaction that matters is *removing* a wrong
 * guess and adding a missing one — not typing from scratch. Enter and comma
 * both commit, and backspace on an empty field removes the last chip.
 */

interface ChipInputProps {
  value: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
  /** Chips the crawl suggested; rendered muted until accepted. */
  disabled?: boolean;
}

export const ChipInput = ({
  value,
  onChange,
  placeholder = "Type and press Enter…",
  disabled = false,
}: ChipInputProps) => {
  const [draft, setDraft] = useState("");

  const commit = (raw: string) => {
    const next = raw.trim().replace(/,$/, "");
    if (!next) return;
    // Case-insensitive dedupe — "Rakhi" and "rakhi" are the same occasion.
    if (value.some((v) => v.toLowerCase() === next.toLowerCase())) {
      setDraft("");
      return;
    }
    onChange([...value, next]);
    setDraft("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      commit(draft);
      return;
    }
    if (e.key === "Backspace" && !draft && value.length) {
      onChange(value.slice(0, -1));
    }
  };

  return (
    <div
      className={`rounded-md border border-border bg-background px-2 py-2 ${
        disabled ? "opacity-60 pointer-events-none" : ""
      }`}
    >
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-2">
          {value.map((chip, i) => (
            <span
              key={`${chip}-${i}`}
              className="inline-flex items-center gap-1 rounded-md bg-primary/10 text-primary px-2 py-1 text-xs font-medium"
            >
              {chip}
              <button
                type="button"
                onClick={() => onChange(value.filter((_, idx) => idx !== i))}
                className="hover:text-destructive transition-colors"
                aria-label={`Remove ${chip}`}
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      )}

      <Input
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={() => commit(draft)}
        placeholder={value.length ? "Add another…" : placeholder}
        className="border-0 shadow-none focus-visible:ring-0 h-8 px-1 text-sm"
      />
    </div>
  );
};
