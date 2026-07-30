import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Info } from "lucide-react";
import { cn } from "@/lib/utils";

interface InfoHintProps {
  /** Explanation shown on hover/focus. */
  children: React.ReactNode;
  side?: "top" | "right" | "bottom" | "left";
  /** Size override for the glyph — chart pills use a smaller icon than card headers. */
  iconClassName?: string;
  className?: string;
  /** Accessible name; default suits metric explanations. */
  label?: string;
}

/**
 * The shared "what does this number mean?" affordance.
 *
 * Every metric surface on Insights had its own copy of this Radix scaffolding,
 * which is why some cards explained themselves and others (the five headline
 * MetricCards) silently did not. One component keeps the icon, placement and
 * keyboard behaviour identical everywhere a figure needs explaining.
 *
 * `stopPropagation` matters: several of these sit inside clickable cards that
 * navigate on click, and reading a tooltip must never take the user off-page.
 */
export const InfoHint = ({ children, side = "top", iconClassName, className, label = "What this metric means" }: InfoHintProps) => (
  <TooltipProvider>
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          aria-label={label}
          onClick={(event) => {
            event.stopPropagation();
            event.preventDefault();
          }}
          className={cn(
            "inline-flex cursor-pointer text-muted-foreground opacity-50 hover:opacity-100 focus-visible:opacity-100 transition-opacity",
            className,
          )}
        >
          <Info className={cn("h-3.5 w-3.5 flex-shrink-0", iconClassName)} />
        </button>
      </TooltipTrigger>
      <TooltipContent side={side} className="max-w-xs text-xs">
        {children}
      </TooltipContent>
    </Tooltip>
  </TooltipProvider>
);

/**
 * Standard body for a metric tooltip: what the number is in plain language,
 * then how it is actually computed. Both halves are required — "Visibility
 * Score" means nothing without its weights, and the weights mean nothing to a
 * reader who does not first know what the score is for.
 */
export const MetricHint = ({ title, plain, formula }: { title: string; plain: React.ReactNode; formula: React.ReactNode }) => (
  <>
    <p className="font-medium mb-1">{title}</p>
    <p className="mb-1.5">{plain}</p>
    <div className="text-muted-foreground">
      <span className="font-medium text-foreground">How it's calculated: </span>
      {formula}
    </div>
  </>
);
