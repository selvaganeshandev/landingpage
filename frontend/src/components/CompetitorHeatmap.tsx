import { Card } from "@/components/ui/card";
import { Building2, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { getFaviconUrl, handleFaviconError } from "@/utils/faviconHelper";

interface HeatmapData {
  competitor: string;
  platforms: {
    [key: string]: number;
  };
  isYou?: boolean;
  url?: string;
}

interface CompetitorHeatmapProps {
  data: HeatmapData[];
  platforms: string[];
}

const getHeatmapColor = (value: number) => {
  if (value >= 30) return "bg-emerald-600 text-white";
  if (value >= 20) return "bg-emerald-500 text-white";
  if (value >= 10) return "bg-emerald-400 text-white";
  if (value >= 5) return "bg-emerald-200 text-emerald-900";
  return "bg-emerald-100 text-emerald-900";
};

export const CompetitorHeatmap = ({ data, platforms }: CompetitorHeatmapProps) => {
  // Handle empty data
  if (!data || data.length === 0 || !platforms || platforms.length === 0) {
    return (
      <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
        <div className="space-y-6">
        <div className="pb-4 border-b border-border/50">
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-semibold font-inter">
              Competitor Analysis Heatmap
            </h3>
            <TooltipProvider delayDuration={150}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    aria-label="How we calculate this heatmap"
                    className="w-5 h-5 rounded-full border border-border flex items-center justify-center text-muted-foreground hover:text-primary hover:border-primary transition-colors"
                  >
                    <Info className="h-3.5 w-3.5" />
                  </button>
                </TooltipTrigger>
                <TooltipContent className="max-w-xs text-xs leading-relaxed">
                  Percentages come from the latest competitor metric snapshots. We total mention counts per AI provider for each brand, compare them to the platform’s overall mentions, then express share as a percentage so every column adds up to 100%.
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Percentage of mentions per AI provider for each brand
          </p>
        </div>
          <div className="flex items-center justify-center py-12">
            <p className="text-sm text-muted-foreground">No heatmap data available yet.</p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
      <div className="space-y-6">
        <div className="pb-4 border-b border-border/50">
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-semibold font-inter">
              Competitor Analysis Heatmap
            </h3>
            <TooltipProvider delayDuration={150}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    aria-label="How we calculate this heatmap"
                    className="w-5 h-5 rounded-full border border-border flex items-center justify-center text-muted-foreground hover:text-primary hover:border-primary transition-colors"
                  >
                    <Info className="h-3.5 w-3.5" />
                  </button>
                </TooltipTrigger>
                <TooltipContent className="max-w-xs text-xs leading-relaxed">
                  Percentages come from the latest competitor metric snapshots. We total mention counts per AI provider for each brand, compare them to the platform’s overall mentions, then express share as a percentage so every column adds up to 100%.
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Percentage of mentions per AI provider for each brand
          </p>
        </div>

        <div className="overflow-x-auto px-2">
          <div className="min-w-[800px]">
            {/* Header */}
            <div className="grid gap-3 mb-3 px-2" style={{ gridTemplateColumns: `220px repeat(${platforms.length}, 1fr)` }}>
              <div className="font-semibold text-sm text-muted-foreground uppercase tracking-wider">Competitor</div>
              {platforms.map((platform) => (
                <div key={platform} className="font-semibold text-sm text-center text-muted-foreground uppercase tracking-wider">
                  {platform}
                </div>
              ))}
            </div>

            {/* Rows */}
            <div className="space-y-3">
              {data.map((row) => (
                <div
                  key={row.competitor}
                  className={`grid gap-3 transition-all duration-300 ${
                    row.isYou
                      ? "ring-2 ring-primary/30 rounded-xl p-3 bg-gradient-to-br from-primary/5 to-secondary/5"
                      : "p-3"
                  }`}
                  style={{ gridTemplateColumns: `220px repeat(${platforms.length}, 1fr)` }}
                >
                  <div className="flex items-center gap-3 font-medium text-sm">
                    <div className="w-9 h-9 rounded-xl bg-white border border-border shadow-sm flex items-center justify-center overflow-hidden">
                      {row.url ? (
                        <img
                          src={getFaviconUrl(row.url, 64)}
                          alt={`${row.competitor} favicon`}
                          className="h-full w-full object-contain p-1"
                          loading="lazy"
                          onError={(e) => handleFaviconError(e, row.url || '', row.competitor, 64)}
                        />
                      ) : null}
                      <Building2 className={cn("heatmap-fallback-icon h-4 w-4 text-primary", row.url && "hidden")} />
                    </div>
                    <span className="truncate font-inter font-semibold">{row.competitor}</span>
                  </div>
                  {platforms.map((platform) => (
                    <div
                      key={platform}
                      className={`p-3 rounded-xl text-center font-semibold text-sm ${getHeatmapColor(
                        row.platforms[platform] || 0
                      )}`}
                    >
                      {row.platforms[platform]?.toFixed(1) || "0.0"}%
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
};
