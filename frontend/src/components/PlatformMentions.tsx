import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface Mention {
  platform: string;
  count: number;
  avgPosition: number;
  color: string;
}

const defaultPlatforms: Mention[] = [
  { platform: "ChatGPT", count: 0, avgPosition: 0, color: "bg-chart-1" },
  { platform: "Claude", count: 0, avgPosition: 0, color: "bg-chart-2" },
  { platform: "Perplexity", count: 0, avgPosition: 0, color: "bg-chart-3" },
  { platform: "Gemini", count: 0, avgPosition: 0, color: "bg-chart-4" },
];

export interface PlatformMentionsProps {
  data?: Array<{ platform: string; count: number; avg_position?: number }>;
}

export const PlatformMentions = ({ data }: PlatformMentionsProps) => {
  const map: Record<string, Mention> = {
    ChatGPT: { platform: "ChatGPT", count: 0, avgPosition: 0, color: "bg-chart-1" },
    Claude: { platform: "Claude", count: 0, avgPosition: 0, color: "bg-chart-2" },
    Perplexity: { platform: "Perplexity", count: 0, avgPosition: 0, color: "bg-chart-3" },
    Gemini: { platform: "Gemini", count: 0, avgPosition: 0, color: "bg-chart-4" },
  };
  const platforms: Mention[] = (data && data.length)
    ? data.map((p, idx) => ({
        platform: p.platform,
        count: p.count,
        avgPosition: typeof p.avg_position === 'number' ? p.avg_position : 0,
        color: Object.values(map)[idx % 4].color,
      }))
    : defaultPlatforms;
  const maxCount = Math.max(1, ...platforms.map(p => p.count));
  return (
    <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80 h-full flex flex-col">
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
                    style={{ width: `${(platform.count / maxCount) * 100}%` }}
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
