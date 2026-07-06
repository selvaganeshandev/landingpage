import { useState } from "react";
import { Card } from "@/components/ui/card";

interface Mention {
  platform: string;
  count: number;
  citations: number;
  color: string;
  hexColor: string;
}

type MetricTab = "mentions" | "citations";

const PLATFORM_META: Record<string, { color: string; hex: string; initials: string }> = {
  ChatGPT:        { color: "bg-[#10a37f]", hex: "#10a37f", initials: "C" },
  "AI Overview":  { color: "bg-[#4285F4]", hex: "#4285F4", initials: "G" },
  "AI Mode":      { color: "bg-[#4285F4]", hex: "#4285F4", initials: "G" },
  Perplexity:     { color: "bg-[#20B2AA]", hex: "#20B2AA", initials: "P" },
  "Google Gemini":{ color: "bg-[#8E44AD]", hex: "#8E44AD", initials: "G" },
  Gemini:         { color: "bg-[#8E44AD]", hex: "#8E44AD", initials: "G" },
  Claude:         { color: "bg-[#D97706]", hex: "#D97706", initials: "C" },
  Grok:           { color: "bg-[#1DA1F2]", hex: "#1DA1F2", initials: "X" },
  DeepSeek:       { color: "bg-[#2563EB]", hex: "#2563EB", initials: "D" },
  Copilot:        { color: "bg-[#00A4EF]", hex: "#00A4EF", initials: "M" },
};

const FALLBACK_COLORS = [
  { color: "bg-chart-1", hex: "hsl(var(--chart-1))" },
  { color: "bg-chart-2", hex: "hsl(var(--chart-2))" },
  { color: "bg-chart-3", hex: "hsl(var(--chart-3))" },
  { color: "bg-chart-4", hex: "hsl(var(--chart-4))" },
  { color: "bg-chart-5", hex: "hsl(var(--chart-5))" },
];

const fmt = (n: number): string => {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1).replace(/\.0$/, "")}M`;
  if (n >= 1_000)     return `${(n / 1_000).toFixed(1).replace(/\.0$/, "")}K`;
  return String(n);
};

const defaultPlatforms: Mention[] = [
  { platform: "ChatGPT",    count: 0, citations: 0, color: "bg-[#10a37f]", hexColor: "#10a37f" },
  { platform: "Claude",     count: 0, citations: 0, color: "bg-[#D97706]", hexColor: "#D97706" },
  { platform: "Perplexity", count: 0, citations: 0, color: "bg-[#20B2AA]", hexColor: "#20B2AA" },
  { platform: "Gemini",     count: 0, citations: 0, color: "bg-[#8E44AD]", hexColor: "#8E44AD" },
  { platform: "Grok",       count: 0, citations: 0, color: "bg-[#1DA1F2]", hexColor: "#1DA1F2" },
];

export interface PlatformMentionsProps {
  data?: Array<{ platform: string; count: number; avg_position?: number; citations?: number }>;
}

export const PlatformMentions = ({ data }: PlatformMentionsProps) => {
  const [activeTab, setActiveTab] = useState<MetricTab>("mentions");

  const platforms: Mention[] = (data && data.length)
    ? data.map((p, idx) => {
        const meta = PLATFORM_META[p.platform] ?? FALLBACK_COLORS[idx % FALLBACK_COLORS.length];
        return {
          platform: p.platform,
          count:    p.count,
          citations: typeof p.citations === "number" ? p.citations : 0,
          color:    "color" in meta ? meta.color : FALLBACK_COLORS[idx % FALLBACK_COLORS.length].color,
          hexColor: "hex" in meta ? meta.hex : FALLBACK_COLORS[idx % FALLBACK_COLORS.length].hex,
        };
      })
    : defaultPlatforms;

  const valueOf = (p: Mention) => (activeTab === "citations" ? p.citations : p.count);
  const totalValue = platforms.reduce((s, p) => s + valueOf(p), 0) || 1;
  const maxValue   = Math.max(1, ...platforms.map(valueOf));

  const PlatformIcon = ({ platform, hexColor }: { platform: string; hexColor: string }) => {
    const initials = PLATFORM_META[platform]?.initials ?? platform.charAt(0).toUpperCase();
    return (
      <span
        className="flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold text-white shadow-sm"
        style={{ backgroundColor: hexColor }}
      >
        {initials}
      </span>
    );
  };

  const tabButton = (tab: MetricTab, label: string) => (
    <button
      type="button"
      onClick={() => setActiveTab(tab)}
      className={`px-3 py-1 text-sm font-medium rounded-md transition-all border ${
        activeTab === tab
          ? "bg-background text-foreground border-border shadow-sm"
          : "text-muted-foreground hover:text-foreground border-transparent"
      }`}
    >
      {label}
    </button>
  );

  return (
    <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80 h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-6 gap-3 flex-wrap">
        <h3 className="text-base font-semibold font-inter">Distribution by LLM</h3>
        <div className="flex items-center gap-0.5 rounded-lg bg-muted/60 p-0.5 border border-border/50">
          {tabButton("mentions", "Mentions")}
          {tabButton("citations", "Cited Pages")}
        </div>
      </div>

      {/* Platform rows - Horizontal Bar Chart Layout */}
      <div className="flex flex-col gap-5 flex-1 justify-center">
        {platforms.map((platform) => {
          const val = valueOf(platform);
          const pct = totalValue > 0 ? ((val / totalValue) * 100).toFixed(1) : "0.0";
          const barWidth = (val / maxValue) * 100;

          return (
            <div key={platform.platform} className="flex items-center gap-4">
              {/* Logo + Name */}
              <div className="flex items-center gap-2.5 w-32 flex-shrink-0">
                <PlatformIcon platform={platform.platform} hexColor={platform.hexColor} />
                <span className="text-sm font-medium truncate text-foreground/90">{platform.platform}</span>
              </div>

              {/* Horizontal Bar */}
              <div className="flex-1 h-2 bg-muted/60 rounded-sm overflow-hidden">
                <div
                  className="h-full rounded-sm transition-all duration-500 bg-[#5C59E8]"
                  style={{ width: `${barWidth}%` }}
                />
              </div>

              {/* Percentage */}
              <span className="text-sm text-muted-foreground w-12 text-right font-medium tabular-nums">{pct}%</span>

              {/* Count */}
              <span className="text-sm font-semibold w-14 text-right tabular-nums text-[#5C59E8]">
                {fmt(val)}
              </span>
            </div>
          );
        })}
      </div>
    </Card>
  );
};
