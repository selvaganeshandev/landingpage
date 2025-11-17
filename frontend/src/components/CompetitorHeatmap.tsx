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
  // Handle empty data
  if (!data || data.length === 0 || !platforms || platforms.length === 0) {
    return (
      <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
        <div className="space-y-6">
          <div className="pb-4 border-b border-border/50">
            <h3 className="text-lg font-semibold font-inter">
              Competitor Analysis Heatmap
            </h3>
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
          <h3 className="text-lg font-semibold font-inter">
            Competitor Analysis Heatmap
          </h3>
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
                    <div className="w-8 h-8 rounded-xl gradient-primary shadow-md flex items-center justify-center">
                      <Building2 className="h-4 w-4 text-white" />
                    </div>
                    <span className="truncate font-inter font-semibold">{row.competitor}</span>
                  </div>
                  {platforms.map((platform) => (
                    <div
                      key={platform}
                      className={`p-3 rounded-xl text-center font-semibold text-sm transition-all duration-300 hover:scale-105 hover:shadow-md ${getHeatmapColor(
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
