import { Card } from "@/components/ui/card";
import { Building2 } from "lucide-react";

interface HeatmapData {
  competitor: string;
  platforms: {
    [key: string]: number;
  };
  isYou?: boolean;
}

interface CompetitorHeatmapProps {
  data: HeatmapData[];
  platforms: string[];
}

const getHeatmapColor = (value: number) => {
  if (value >= 25) return "bg-success/80 text-white";
  if (value >= 20) return "bg-success/60 text-white";
  if (value >= 15) return "bg-success/40";
  if (value >= 10) return "bg-success/20";
  return "bg-muted";
};

export const CompetitorHeatmap = ({ data, platforms }: CompetitorHeatmapProps) => {
  return (
    <Card className="p-6">
      <div className="space-y-4">
        <div>
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Building2 className="h-5 w-5" />
            Competitor Analysis Heatmap
          </h3>
          <p className="text-sm text-muted-foreground mt-1">
            Percentage of mentions per AI provider for each brand
          </p>
        </div>

        <div className="overflow-x-auto">
          <div className="min-w-[800px]">
            {/* Header */}
            <div className="grid gap-2 mb-2" style={{ gridTemplateColumns: `200px repeat(${platforms.length}, 1fr)` }}>
              <div className="font-semibold text-sm">Competitor</div>
              {platforms.map((platform) => (
                <div key={platform} className="font-semibold text-sm text-center">
                  {platform}
                </div>
              ))}
            </div>

            {/* Rows */}
            <div className="space-y-2">
              {data.map((row) => (
                <div
                  key={row.competitor}
                  className={`grid gap-2 ${row.isYou ? "ring-2 ring-primary rounded-lg p-2" : ""}`}
                  style={{ gridTemplateColumns: `200px repeat(${platforms.length}, 1fr)` }}
                >
                  <div className="flex items-center gap-2 font-medium text-sm">
                    <div className="w-6 h-6 rounded bg-gradient-to-br from-primary to-secondary text-primary-foreground flex items-center justify-center text-xs">
                      <Building2 className="h-3 w-3" />
                    </div>
                    <span className="truncate">{row.competitor}</span>
                  </div>
                  {platforms.map((platform) => (
                    <div
                      key={platform}
                      className={`p-3 rounded-lg text-center font-semibold text-sm transition-all hover:scale-105 ${getHeatmapColor(
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
