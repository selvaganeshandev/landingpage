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
    <Card className="p-6 shadow-elegant border-border/50 backdrop-blur-sm bg-card/80 h-full flex flex-col">
      <h3 className="text-lg font-semibold mb-6 font-outfit">Platform Distribution</h3>
      <div className="space-y-5 flex-1">
        {platforms.map((platform) => (
          <div key={platform.platform} className="space-y-3 group">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full ${platform.color} transition-all group-hover:scale-125 group-hover:shadow-lg`} />
                <span className="font-semibold font-outfit">{platform.platform}</span>
              </div>
              <Badge variant="secondary" className="font-medium">{platform.count} mentions</Badge>
            </div>
            <div className="pl-6">
              <div className="flex items-center justify-between text-sm text-muted-foreground mb-2">
                <span>Avg Position: <span className="font-semibold text-foreground">{platform.avgPosition}</span></span>
                <div className="h-2 w-32 bg-muted rounded-full overflow-hidden border border-border/50">
                  <div 
                    className={`h-full ${platform.color} transition-all duration-500`}
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
