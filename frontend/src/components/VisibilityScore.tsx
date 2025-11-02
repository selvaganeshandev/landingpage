import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

interface VisibilityScoreProps {
  brand: string;
  score: number;
  mentions: number;
  sentiment: {
    positive: number;
    neutral: number;
    negative: number;
  };
}

export const VisibilityScore = ({ brand, score, mentions, sentiment }: VisibilityScoreProps) => {
  return (
    <Card className="p-6 h-full border border-border">
      <div className="space-y-4 h-full flex flex-col">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">{brand}</h3>
          <div className="text-3xl font-bold text-primary">{score}</div>
        </div>
        
        <Progress value={score} className="h-2" />
        
        <div className="grid grid-cols-2 gap-4 pt-2">
          <div>
            <p className="text-sm text-muted-foreground">Total Mentions</p>
            <p className="text-2xl font-bold">{mentions}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Avg Position</p>
            <p className="text-2xl font-bold">1.6</p>
          </div>
        </div>
        
        <div className="space-y-2 pt-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Sentiment</span>
          </div>
          <div className="flex gap-1 h-2 rounded-full overflow-hidden">
            <div 
              className="bg-success" 
              style={{ width: `${sentiment.positive}%` }}
            />
            <div 
              className="bg-warning" 
              style={{ width: `${sentiment.neutral}%` }}
            />
            <div 
              className="bg-destructive" 
              style={{ width: `${sentiment.negative}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>{sentiment.positive}% Positive</span>
            <span>{sentiment.neutral}% Neutral</span>
            <span>{sentiment.negative}% Negative</span>
          </div>
        </div>
      </div>
    </Card>
  );
};
