import type { CSSProperties } from "react";
import { getPlatformMark } from "@/lib/platform-marks";

interface PlatformLogoProps {
  /** Platform label exactly as the API sends it — matching is case-insensitive. */
  platform: string;
  /** Chip colour for platforms we have no brand mark for. */
  fallbackHex: string;
  /** Letter shown on the fallback chip. Defaults to the platform's first letter. */
  fallbackInitials?: string;
  /** Tailwind size classes for the chip. Defaults to a 24px circle. */
  className?: string;
}

/**
 * The brand mark for an AI platform, as a coloured chip.
 *
 * Platforms without a mark (Microsoft Copilot today) fall back to the coloured
 * initial this component replaced, so an unrecognised label degrades to
 * something readable instead of an empty circle.
 *
 * The chip is aria-hidden: every current caller renders the platform name as
 * text beside it, so announcing the logo too would just repeat it.
 */
export const PlatformLogo = ({
  platform,
  fallbackHex,
  fallbackInitials,
  className = "w-6 h-6",
}: PlatformLogoProps) => {
  const mark = getPlatformMark(platform);

  if (!mark) {
    return (
      <span
        aria-hidden="true"
        className={`${className} flex-shrink-0 rounded-full flex items-center justify-center text-[9px] font-bold text-white shadow-sm`}
        style={{ backgroundColor: fallbackHex }}
      >
        {fallbackInitials ?? platform.charAt(0).toUpperCase()}
      </span>
    );
  }

  // Near-black marks (X/Grok) would vanish on a dark card, so each mark can
  // declare an inverted pair. Passed as custom properties because inline styles
  // cannot respond to the `dark` class on their own.
  const chipColors = {
    "--pl-bg": mark.hex,
    "--pl-fg": "#FFFFFF",
    "--pl-bg-dark": mark.darkHex ?? mark.hex,
    "--pl-fg-dark": mark.darkFg ?? "#FFFFFF",
  } as CSSProperties;

  return (
    <span
      aria-hidden="true"
      className={`${className} flex-shrink-0 rounded-full flex items-center justify-center shadow-sm bg-[var(--pl-bg)] text-[var(--pl-fg)] dark:bg-[var(--pl-bg-dark)] dark:text-[var(--pl-fg-dark)]`}
      style={chipColors}
    >
      <svg viewBox="0 0 24 24" fill="currentColor" className="h-3.5 w-3.5">
        <path d={mark.path} />
      </svg>
    </span>
  );
};
