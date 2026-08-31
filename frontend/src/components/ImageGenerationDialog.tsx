/**
 * Image generation for the content editor — two stages over OpenRouter.
 *
 * Stage 1 turns the selected passage into a vivid image prompt using a text
 * model. Stage 2 renders that prompt to pixels. The user edits the prompt in
 * between, which is where most of the perceived quality comes from — so the
 * textarea is always visible and the render button never depends on Stage 1
 * having succeeded.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Loader2, Download, Sparkles, RefreshCw, ImagePlus } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiClient, API_BASE_URL } from "@/services/api";

/** Mirrors STYLES in backend/content/image_generation.py. */
const STYLES = [
  { value: "realistic", label: "Realistic", hint: "Photorealistic, high detail" },
  { value: "real-world", label: "Real world", hint: "Candid photograph" },
  { value: "cartoon", label: "Cartoonic", hint: "Bold, flat cartoon" },
  { value: "animation", label: "3D animation", hint: "Pixar-style render" },
  { value: "watercolor", label: "Watercolor", hint: "Hand-drawn, painterly" },
  { value: "flat-design", label: "Flat design", hint: "Minimal vector illustration" },
] as const;

const PHOTOGRAPHIC = new Set(["realistic", "real-world"]);

/**
 * The API returns a RELATIVE url (/media/...), which is correct: it survives a
 * domain change and works behind a proxy that serves the app and /media from
 * one origin. In local development they are two origins — the app on :8080, the
 * files on :8000 — so a relative path resolves to the dev server, which answers
 * every unknown path with index.html. The <img> then receives HTML and fails
 * silently. Resolving against the API origin fixes dev and is a no-op wherever
 * the two already share an origin.
 */
const resolveMediaUrl = (url: string): string =>
  url.startsWith("/") ? `${API_BASE_URL.replace(/\/$/, "")}${url}` : url;

/** Shape both image endpoints return. `apiRequest` is untyped, so narrow here. */
interface ImageApiResponse {
  status?: string;
  message?: string;
  data?: { prompt?: string; url?: string; mime_type?: string; bytes?: number };
}

/** Pull a usable message off an unknown thrown value. */
const errorMessage = (err: unknown, fallback: string): string =>
  err instanceof Error && err.message ? err.message : fallback;
const MAX_INSTRUCTIONS = 500;

interface ImageGenerationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** The passage the image should illustrate. */
  selectedText: string;
  articleTitle?: string;
  /** Heading immediately above the selection — the spec's preferred alt text. */
  nearestHeading?: string;
  keyword?: string;
  domainId?: number;
  /** Optional hex palette. The brand-colors control hides when empty. */
  brandColors?: string[];
  /** Called with the saved image URL when the user inserts it. */
  onInsert: (url: string, alt: string) => void;
}

export function ImageGenerationDialog({
  open,
  onOpenChange,
  selectedText,
  articleTitle = "",
  nearestHeading = "",
  keyword = "",
  domainId,
  brandColors = [],
  onInsert,
}: ImageGenerationDialogProps) {
  const { toast } = useToast();

  const [style, setStyle] = useState<string>(STYLES[0].value);
  const [instructions, setInstructions] = useState("");
  const [useBrandColors, setUseBrandColors] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [imageUrl, setImageUrl] = useState<string | null>(null);

  const [writingPrompt, setWritingPrompt] = useState(false);
  const [rendering, setRendering] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // The checkbox follows the chosen style until the user touches it, after
  // which their choice sticks. A brand palette fights a photograph, so
  // photographic styles default it off.
  const brandColorsTouched = useRef(false);
  const hasPalette = brandColors.length > 0;

  useEffect(() => {
    if (!open) return;
    // Fresh state each time the dialog opens — a stale prompt from a previous
    // selection is worse than no prompt.
    setStyle(STYLES[0].value);
    setInstructions("");
    setPrompt("");
    setImageUrl(null);
    setError(null);
    brandColorsTouched.current = false;
    setUseBrandColors(hasPalette && !PHOTOGRAPHIC.has(STYLES[0].value));
  }, [open, hasPalette]);

  const handleStyleChange = (next: string) => {
    setStyle(next);
    if (!brandColorsTouched.current) {
      setUseBrandColors(hasPalette && !PHOTOGRAPHIC.has(next));
    }
  };

  const handleWritePrompt = async () => {
    setWritingPrompt(true);
    setError(null);
    try {
      const res = (await apiClient.generateImagePrompt({
        domain_id: domainId,
        title: articleTitle,
        keyword,
        selected_text: selectedText,
        style,
        additional_instructions: instructions.trim() || undefined,
      })) as ImageApiResponse;
      if (res?.status === "success" && res?.data?.prompt) {
        setPrompt(res.data.prompt);
      } else {
        throw new Error(res?.message || "The model returned no prompt.");
      }
    } catch (err: unknown) {
      setError(errorMessage(err, "Could not write a prompt."));
    } finally {
      setWritingPrompt(false);
    }
  };

  const handleRender = async () => {
    if (!prompt.trim()) {
      setError("Write or generate a prompt first.");
      return;
    }
    setRendering(true);
    setError(null);
    try {
      const res = (await apiClient.generateImage({
        domain_id: domainId,
        prompt: prompt.trim(),
        brand_colors: useBrandColors && hasPalette ? brandColors : undefined,
      })) as ImageApiResponse;
      if (res?.status === "success" && res?.data?.url) {
        setImageUrl(resolveMediaUrl(res.data.url));
      } else {
        throw new Error(res?.message || "The model returned no image.");
      }
    } catch (err: unknown) {
      setError(errorMessage(err, "Could not render the image."));
    } finally {
      setRendering(false);
    }
  };

  /** Article slug + timestamp keeps saved files sorted and self-describing. */
  const downloadName = useMemo(() => {
    const slug = (articleTitle || "image")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "")
      .slice(0, 60);
    return `${slug || "image"}-${Date.now()}`;
  }, [articleTitle]);

  /**
   * Save to the user's computer.
   *
   * A plain <a download> is ignored cross-origin — the browser navigates to the
   * image instead of saving it. Fetching the bytes and handing over a blob is
   * the only reliable route.
   */
  const handleSaveToComputer = async () => {
    if (!imageUrl) return;
    try {
      const res = await fetch(imageUrl);
      if (!res.ok) throw new Error("Couldn't fetch the image to save it.");
      const blob = await res.blob();

      // Trust the blob's own mime type — the renderer decides the format.
      const extension = blob.type.split("/")[1] ?? "png";
      const blobUrl = URL.createObjectURL(blob);

      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = `${downloadName}.${extension}`;
      // Some browsers ignore a click on a detached anchor.
      document.body.appendChild(link);
      link.click();
      link.remove();
      // Without this the full image leaks for the page's lifetime.
      URL.revokeObjectURL(blobUrl);

      toast({ title: "Image saved", description: `${downloadName}.${extension}` });
    } catch (err: unknown) {
      toast({
        title: "Couldn't save the image",
        description: errorMessage(err, "The download failed."),
        variant: "destructive",
      });
    }
  };

  const handleInsert = () => {
    if (!imageUrl) return;
    // Never leave alt empty — these are blog images and an empty alt is an
    // accessibility and SEO regression. Nearest heading first, then the title.
    const alt =
      nearestHeading?.trim() ||
      (articleTitle ? `Illustration for ${articleTitle}` : "Generated illustration");
    onInsert(imageUrl, alt);
    onOpenChange(false);
  };

  const busy = writingPrompt || rendering;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[680px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Generate an image</DialogTitle>
          <DialogDescription>
            A text model writes the prompt, then an image model renders it. Edit the
            prompt before rendering — that is where most of the quality comes from.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-2">
          {/* What the image is about */}
          <div className="grid gap-2">
            <Label>Selected passage</Label>
            <div className="rounded-md border bg-muted/40 p-3 text-sm max-h-28 overflow-y-auto whitespace-pre-wrap">
              {selectedText || (
                <span className="text-muted-foreground">
                  No text selected — select a passage in the article first.
                </span>
              )}
            </div>
          </div>

          {/* Style */}
          <div className="grid gap-2">
            <Label>Illustration style</Label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {STYLES.map((s) => (
                <button
                  key={s.value}
                  type="button"
                  onClick={() => handleStyleChange(s.value)}
                  disabled={busy}
                  className={`rounded-md border p-2 text-left transition-colors disabled:opacity-50 ${
                    style === s.value
                      ? "border-primary bg-primary/5 ring-1 ring-primary"
                      : "hover:bg-muted/60"
                  }`}
                >
                  <div className="text-sm font-medium">{s.label}</div>
                  <div className="text-xs text-muted-foreground">{s.hint}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Additional details */}
          <div className="grid gap-2">
            <Label htmlFor="imgInstructions">
              Additional details{" "}
              <span className="text-muted-foreground font-normal">(optional)</span>
            </Label>
            <Input
              id="imgInstructions"
              placeholder="e.g. include our logo, set it at night, focus on the laptop screen"
              value={instructions}
              maxLength={MAX_INSTRUCTIONS}
              disabled={busy}
              onChange={(e) => setInstructions(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Treated as required instructions, not hints. {instructions.length}/
              {MAX_INSTRUCTIONS}
            </p>
          </div>

          {/* Brand colors — hidden entirely when the project has no palette */}
          {hasPalette && (
            <div className="flex items-center gap-2">
              <Checkbox
                id="useBrandColors"
                checked={useBrandColors}
                disabled={busy}
                onCheckedChange={(v) => {
                  brandColorsTouched.current = true;
                  setUseBrandColors(Boolean(v));
                }}
              />
              <Label htmlFor="useBrandColors" className="font-normal">
                Use brand colors
              </Label>
              <div className="flex gap-1 ml-1">
                {brandColors.slice(0, 5).map((c) => (
                  <span
                    key={c}
                    className="h-4 w-4 rounded-sm border"
                    style={{ backgroundColor: c }}
                    title={c}
                  />
                ))}
              </div>
            </div>
          )}

          {/* The prompt. Always visible so the renderer stays reachable even if
              the text model is unavailable. */}
          <div className="grid gap-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="imgPrompt">Image prompt</Label>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleWritePrompt}
                disabled={busy || !selectedText}
              >
                {writingPrompt ? (
                  <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                ) : prompt ? (
                  <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
                ) : (
                  <Sparkles className="h-3.5 w-3.5 mr-1.5" />
                )}
                {writingPrompt
                  ? "Writing…"
                  : prompt
                  ? "Regenerate prompt"
                  : "Generate prompt"}
              </Button>
            </div>
            <Textarea
              id="imgPrompt"
              rows={5}
              placeholder="Generate a prompt from the passage, or write your own here."
              value={prompt}
              disabled={busy}
              onChange={(e) => setPrompt(e.target.value)}
            />
          </div>

          {error && (
            <div className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
              {error}
            </div>
          )}

          {/* Preview */}
          {imageUrl && (
            <div className="grid gap-2">
              <Label>Preview</Label>
              <img
                src={imageUrl}
                alt="Generated preview"
                className="w-full rounded-md border"
              />
              <p className="text-xs text-muted-foreground break-all">{imageUrl}</p>
            </div>
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-2">
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={busy}>
            Cancel
          </Button>

          <Button onClick={handleRender} disabled={busy || !prompt.trim()}>
            {rendering ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <ImagePlus className="h-4 w-4 mr-2" />
            )}
            {rendering ? "Rendering…" : imageUrl ? "Render again" : "Generate image"}
          </Button>

          {/* Saving and inserting are independent — downloading must not close
              the dialog or count as "using" the image. */}
          {imageUrl && (
            <>
              <Button variant="outline" onClick={handleSaveToComputer} disabled={busy}>
                <Download className="h-4 w-4 mr-2" />
                Save image
              </Button>
              <Button onClick={handleInsert} disabled={busy}>
                Insert into article
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default ImageGenerationDialog;
