import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TrendingUp } from "lucide-react";

interface Competitor {
  name: string;
  url: string;
  mentions: number;
  shareOfVoice: number;
  trend: number;
}

const competitors: Competitor[] = [
  { name: "VegFit Pro", url: "vegfitpro.com", mentions: 221, shareOfVoice: 42, trend: 15 },
  { name: "MyProtein", url: "myprotein.com", mentions: 187, shareOfVoice: 35, trend: 8 },
  { name: "Naked Nutrition", url: "nakednutrition.com", mentions: 123, shareOfVoice: 23, trend: -3 },
];

export const CompetitorComparison = () => {
  return (
    <Card className="p-6 h-full flex flex-col border border-border">
      <h3 className="text-lg font-semibold mb-4">Share of Voice</h3>
      <div className="space-y-4 flex-1">
        {competitors.map((competitor, index) => (
          <div key={competitor.name} className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-secondary text-primary-foreground flex items-center justify-center font-bold text-sm">
                  {index + 1}
                </div>
                <div>
                  <p className="font-medium">{competitor.name}</p>
                  <p className="text-xs text-muted-foreground">{competitor.url}</p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm font-medium">{competitor.mentions} mentions</p>
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <TrendingUp className="h-3 w-3" />
                  {competitor.trend > 0 ? "+" : ""}{competitor.trend}%
                </div>
              </div>
            </div>
            <div className="space-y-1">
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-primary to-secondary transition-all"
                  style={{ width: `${competitor.shareOfVoice}%` }}
                />
              </div>
              <p className="text-xs text-muted-foreground text-right">{competitor.shareOfVoice}% share of voice</p>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
};
