import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface Mention {
  platform: string;
  count: number;
  avgPosition: number;
  color: string;
}

const platforms: Mention[] = [
  { platform: "ChatGPT", count: 89, avgPosition: 1.4, color: "bg-chart-1" },
  { platform: "Claude", count: 64, avgPosition: 1.8, color: "bg-chart-2" },
  { platform: "Perplexity", count: 42, avgPosition: 1.5, color: "bg-chart-3" },
  { platform: "Gemini", count: 26, avgPosition: 2.1, color: "bg-chart-4" },
];

export const PlatformMentions = () => {
  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-4">Platform Distribution</h3>
      <div className="space-y-4">
        {platforms.map((platform) => (
          <div key={platform.platform} className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full ${platform.color}`} />
                <span className="font-medium">{platform.platform}</span>
              </div>
              <Badge variant="secondary">{platform.count} mentions</Badge>
            </div>
            <div className="pl-6">
              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <span>Avg Position: {platform.avgPosition}</span>
                <div className="h-2 w-32 bg-muted rounded-full overflow-hidden">
                  <div 
                    className={`h-full ${platform.color}`}
                    style={{ width: `${(platform.count / 89) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
};
