import { useRef } from "react";
import { Bold, Italic, Heading2, List, ListOrdered } from "lucide-react";

/**
 * A lightweight, dependency-free rich text field.
 *
 * It lets the user format their text visually (bold, italic, a heading, and
 * bullet / numbered lists) via a small toolbar over a contentEditable area.
 * On every edit it reports back the *plain text* (via `innerText`) so callers
 * that feed the value to an API or an AI prompt receive clean, tag-free text —
 * the formatting is a writing aid for the human, never sent downstream.
 *
 * Intentionally uncontrolled: the editor owns its DOM. To clear/reset it, give
 * it a `key` that changes (e.g. tied to a dialog's open state) so React
 * remounts a fresh, empty editor.
 */
interface RichTextAreaProps {
  /** Called with the plain-text content on every edit. */
  onChange: (plainText: string) => void;
  placeholder?: string;
  /** Minimum editor height in px (default 90). */
  minHeight?: number;
  className?: string;
}

export function RichTextArea({
  onChange,
  placeholder = "",
  minHeight = 90,
  className = "",
}: RichTextAreaProps) {
  const editorRef = useRef<HTMLDivElement>(null);

  const emit = () => {
    const el = editorRef.current;
    if (!el) return;
    // innerText collapses all formatting to clean, line-separated plain text:
    // headings and list items become their own lines, bold/italic become their
    // words. That is exactly what should reach an API or AI prompt.
    onChange((el.innerText || "").trim());
  };

  const exec = (command: string, value?: string) => {
    editorRef.current?.focus();
    // eslint-disable-next-line deprecation/deprecation
    document.execCommand(command, false, value);
    emit();
  };

  const ToolbarButton = ({
    onClick,
    label,
    children,
  }: {
    onClick: () => void;
    label: string;
    children: React.ReactNode;
  }) => (
    <button
      type="button"
      title={label}
      aria-label={label}
      // onMouseDown + preventDefault keeps the editor's text selection intact
      // so the command applies to the selected words, not a lost selection.
      onMouseDown={(e) => {
        e.preventDefault();
        onClick();
      }}
      className="inline-flex h-7 w-7 items-center justify-center rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
    >
      {children}
    </button>
  );

  return (
    <div
      className={`rounded-md border border-input bg-background focus-within:ring-1 focus-within:ring-ring ${className}`}
    >
      <div className="flex items-center gap-0.5 border-b border-border px-1.5 py-1">
        <ToolbarButton onClick={() => exec("bold")} label="Bold">
          <Bold className="h-3.5 w-3.5" />
        </ToolbarButton>
        <ToolbarButton onClick={() => exec("italic")} label="Italic">
          <Italic className="h-3.5 w-3.5" />
        </ToolbarButton>
        <ToolbarButton
          onClick={() => exec("formatBlock", "<h3>")}
          label="Heading"
        >
          <Heading2 className="h-3.5 w-3.5" />
        </ToolbarButton>
        <ToolbarButton
          onClick={() => exec("insertUnorderedList")}
          label="Bullet list"
        >
          <List className="h-3.5 w-3.5" />
        </ToolbarButton>
        <ToolbarButton
          onClick={() => exec("insertOrderedList")}
          label="Numbered list"
        >
          <ListOrdered className="h-3.5 w-3.5" />
        </ToolbarButton>
      </div>
      <div
        ref={editorRef}
        contentEditable
        suppressContentEditableWarning
        onInput={emit}
        data-placeholder={placeholder}
        role="textbox"
        aria-multiline="true"
        className="rich-text-area-input px-3 py-2 text-sm leading-relaxed focus:outline-none overflow-y-auto"
        style={{ minHeight }}
      />
      <style>{`
        .rich-text-area-input:empty:before {
          content: attr(data-placeholder);
          color: hsl(var(--muted-foreground));
          pointer-events: none;
        }
        .rich-text-area-input h3 { font-size: 0.95rem; font-weight: 600; margin: 0.25rem 0; }
        .rich-text-area-input ul { list-style: disc; padding-left: 1.25rem; margin: 0.25rem 0; }
        .rich-text-area-input ol { list-style: decimal; padding-left: 1.25rem; margin: 0.25rem 0; }
      `}</style>
    </div>
  );
}
