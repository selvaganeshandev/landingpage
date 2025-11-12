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
        <h3 className="text-lg font-semibold mb-6 font-inter">Recent Mentions</h3>
        <p className="text-muted-foreground text-center py-8">No mentions found</p>
      </Card>
    );
  }

  return (
    <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
      <h3 className="text-lg font-semibold mb-6 font-inter">Recent Mentions</h3>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Platform</TableHead>
            <TableHead>Prompt</TableHead>
            <TableHead className="text-center">Position</TableHead>
            <TableHead className="text-center">Sentiment</TableHead>
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
