import { useNavigate } from "react-router-dom";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ExternalLink } from "lucide-react";
import { InfoHint, MetricHint } from "@/components/InfoHint";

interface Mention {
  id: number;
  platform: string;
  prompt: string;
  position: number;
  sentiment: "positive" | "neutral" | "negative";
  timestamp?: string;
  relative_time?: string;
  url?: string;
}

interface MentionTableProps {
  mentions?: Mention[];
}

/** Card title + its explanation, shared by the empty and populated states so the
 *  header cannot explain itself in one and stay silent in the other. */
const TableHeading = () => (
  <div className="flex items-center gap-1.5 mb-6">
    <h3 className="text-lg font-semibold font-inter">Recent Mentions</h3>
    <InfoHint side="right">
      <MetricHint
        title="The latest AI answers that named your brand"
        plain="A sample of the individual answers behind the totals above — which platform gave it, which of your prompts triggered it, and how your brand came across."
        formula={
          <>
            The most recent answers in the date range where your brand was detected, newest first.
            Answers that did not mention you are not listed here, and this is a preview rather than
            the full set — open the Mentions page for everything in the window.
          </>
        }
      />
    </InfoHint>
  </div>
);

const getSentimentColor = (sentiment: string) => {
  switch (sentiment) {
    case "positive":
      return "bg-success text-success-foreground";
    case "neutral":
      return "bg-warning text-warning-foreground";
    case "negative":
      return "bg-destructive text-destructive-foreground";
    default:
      return "bg-muted";
  }
};

export const MentionTable = ({ mentions = [] }: MentionTableProps) => {
  const navigate = useNavigate();
  
  const handleViewDetails = (mentionId: number) => {
    navigate(`/mentions/${mentionId}`);
  };

  if (mentions.length === 0) {
    return (
      <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
        <TableHeading />
        <p className="text-muted-foreground text-center py-8">No mentions found</p>
      </Card>
    );
  }

  return (
    <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
      <TableHeading />
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Platform</TableHead>
            <TableHead>Prompt</TableHead>
            <TableHead className="text-center">
              <span className="inline-flex items-center gap-1.5">
                Position
                <InfoHint label="What Position means">
                  Where your brand was named inside that answer. #1 means it was the first brand
                  mentioned; a higher number means other brands came first. Lower is better.
                </InfoHint>
              </span>
            </TableHead>
            <TableHead className="text-center">
              <span className="inline-flex items-center gap-1.5">
                Sentiment
                <InfoHint label="What Sentiment means">
                  How the answer described your brand — positive, neutral or negative — judged from
                  the wording around the mention. This is the per-answer verdict that feeds the
                  sentiment split on the AI Visibility card.
                </InfoHint>
              </span>
            </TableHead>
            <TableHead>Time</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {mentions.map((mention) => (
            <TableRow key={mention.id}>
              <TableCell className="font-medium">{mention.platform}</TableCell>
              <TableCell className="max-w-xs truncate">{mention.prompt}</TableCell>
              <TableCell className="text-center">
                <Badge variant="outline" className="font-bold">#{mention.position}</Badge>
              </TableCell>
              <TableCell className="text-center">
                <Badge className={getSentimentColor(mention.sentiment)}>
                  {mention.sentiment}
                </Badge>
              </TableCell>
              <TableCell className="text-muted-foreground">{mention.relative_time || mention.timestamp || 'N/A'}</TableCell>
              <TableCell className="text-right">
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => handleViewDetails(mention.id)}
                  className="border-border/50 hover:gradient-primary hover:text-white transition-all"
                >
                  <ExternalLink className="h-3 w-3 mr-1" />
                  View Details
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  );
};
