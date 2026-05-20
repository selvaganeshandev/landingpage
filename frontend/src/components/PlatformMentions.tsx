import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface Mention {
  platform: string;
  count: number;
  avgPosition: number;
  color: string;
}

const PLATFORM_COLORS = [
  "bg-chart-1",
  "bg-chart-3",
  "bg-chart-4",
  "bg-chart-2",
  "bg-chart-5",
  "bg-primary",
];

const defaultPlatforms: Mention[] = [
  { platform: "ChatGPT", count: 0, avgPosition: 0, color: "bg-chart-1" },
  { platform: "Perplexity", count: 0, avgPosition: 0, color: "bg-chart-3" },
  { platform: "Google Gemini", count: 0, avgPosition: 0, color: "bg-chart-4" },
  { platform: "Claude", count: 0, avgPosition: 0, color: "bg-chart-2" },
  { platform: "Grok", count: 0, avgPosition: 0, color: "bg-chart-5" },
  { platform: "DeepSeek", count: 0, avgPosition: 0, color: "bg-primary" },
];

export interface PlatformMentionsProps {
  data?: Array<{ platform: string; count: number; avg_position?: number }>;
}

export const PlatformMentions = ({ data }: PlatformMentionsProps) => {
  const map: Record<string, Mention> = {
    ChatGPT: { platform: "ChatGPT", count: 0, avgPosition: 0, color: "bg-chart-1" },
    Perplexity: { platform: "Perplexity", count: 0, avgPosition: 0, color: "bg-chart-3" },
    "Google Gemini": { platform: "Google Gemini", count: 0, avgPosition: 0, color: "bg-chart-4" },
    Claude: { platform: "Claude", count: 0, avgPosition: 0, color: "bg-chart-2" },
    Grok: { platform: "Grok", count: 0, avgPosition: 0, color: "bg-chart-5" },
    DeepSeek: { platform: "DeepSeek", count: 0, avgPosition: 0, color: "bg-primary" },
  };
  const platforms: Mention[] = (data && data.length)
    ? data.map((p, idx) => ({
        platform: p.platform,
        count: p.count,
        avgPosition: typeof p.avg_position === 'number' ? p.avg_position : 0,
        color: map[p.platform]?.color ?? PLATFORM_COLORS[idx % PLATFORM_COLORS.length],
      }))
    : defaultPlatforms;
  const maxCount = Math.max(1, ...platforms.map(p => p.count));
  return (
    <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80 h-full flex flex-col">
      <h3 className="text-lg font-semibold mb-6 font-inter">Platform Distribution</h3>
      <div className="space-y-5 flex-1">
        {platforms.map((platform) => (
          <div key={platform.platform} className="space-y-3 group">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full ${platform.color} transition-all group-hover:scale-125 group-hover:shadow-lg`} />
                <span className="font-semibold font-inter">{platform.platform}</span>
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
