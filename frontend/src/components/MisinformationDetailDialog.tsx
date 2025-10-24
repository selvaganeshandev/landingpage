import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { 
  CheckCircle, 
  XCircle, 
  MessageSquare, 
  Clock,
  ExternalLink,
  AlertTriangle,
  Eye
} from "lucide-react";

interface MisinformationCase {
  id: number;
  title: string;
  description: string;
  severity: string;
  platform: string;
  detectedAt: string;
  mentions: number;
  status: string;
  impact: string;
  correctInfo: string;
  incorrectInfo: string;
}

interface MisinformationDetailDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  misinformationCase: MisinformationCase | null;
}

const getSeverityColor = (severity: string) => {
  switch (severity) {
    case "high":
      return "bg-destructive text-destructive-foreground";
    case "medium":
      return "bg-warning text-warning-foreground";
    case "low":
      return "bg-success text-success-foreground";
    default:
      return "bg-muted";
  }
};

export function MisinformationDetailDialog({
  open,
  onOpenChange,
  misinformationCase,
}: MisinformationDetailDialogProps) {
  if (!misinformationCase) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-start gap-3">
            <div className="flex-1">
              <DialogTitle className="text-xl mb-2">
                {misinformationCase.title}
              </DialogTitle>
              <DialogDescription>
                Case #{misinformationCase.id} • Detected {misinformationCase.detectedAt}
              </DialogDescription>
            </div>
            <Badge className={getSeverityColor(misinformationCase.severity)}>
              {misinformationCase.severity} severity
            </Badge>
          </div>
        </DialogHeader>

        <div className="space-y-6">
          {/* Description */}
          <div>
            <h3 className="text-sm font-semibold mb-2">Description</h3>
            <p className="text-sm text-muted-foreground">
              {misinformationCase.description}
            </p>
          </div>

          <Separator />

          {/* Key Information */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-3">
              <div>
                <p className="text-xs text-muted-foreground mb-1">Platform</p>
                <Badge variant="secondary">{misinformationCase.platform}</Badge>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">Status</p>
                <Badge variant="outline">{misinformationCase.status}</Badge>
              </div>
            </div>
            <div className="space-y-3">
              <div>
                <p className="text-xs text-muted-foreground mb-1">Impact Area</p>
                <p className="text-sm font-medium">{misinformationCase.impact}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">Affected Mentions</p>
                <div className="flex items-center gap-2">
                  <MessageSquare className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm font-medium">{misinformationCase.mentions} mentions</span>
                </div>
              </div>
            </div>
          </div>

          <Separator />

          {/* Incorrect vs Correct Information */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold">Information Comparison</h3>
            
            <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
              <div className="flex items-start gap-2 mb-2">
                <XCircle className="h-4 w-4 text-destructive mt-0.5" />
                <p className="text-sm font-medium text-destructive">Incorrect Information Being Cited</p>
              </div>
              <p className="text-sm pl-6">{misinformationCase.incorrectInfo}</p>
            </div>

            <div className="p-4 bg-success/10 border border-success/20 rounded-lg">
              <div className="flex items-start gap-2 mb-2">
                <CheckCircle className="h-4 w-4 text-success mt-0.5" />
                <p className="text-sm font-medium text-success">Correct Information</p>
              </div>
              <p className="text-sm pl-6">{misinformationCase.correctInfo}</p>
            </div>
          </div>

          <Separator />

          {/* Timeline */}
          <div>
            <h3 className="text-sm font-semibold mb-3">Detection Timeline</h3>
            <div className="space-y-3">
              <div className="flex items-start gap-3">
                <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                  <Eye className="h-4 w-4 text-primary" />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Issue Detected</p>
                  <p className="text-xs text-muted-foreground">
                    {misinformationCase.detectedAt}
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="h-8 w-8 rounded-full bg-warning/10 flex items-center justify-center">
                  <AlertTriangle className="h-4 w-4 text-warning" />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Status: {misinformationCase.status}</p>
                  <p className="text-xs text-muted-foreground">
                    Currently being monitored and investigated
                  </p>
                </div>
              </div>
            </div>
          </div>

          <Separator />

          {/* Sample Affected Mentions */}
          <div>
            <h3 className="text-sm font-semibold mb-3">Sample Affected Responses</h3>
            <div className="space-y-2">
              <div className="p-3 bg-muted rounded-lg text-xs">
                <p className="font-medium mb-1">ChatGPT Response Sample:</p>
                <p className="text-muted-foreground">
                  "According to the latest information, {misinformationCase.incorrectInfo.toLowerCase()}..."
                </p>
              </div>
              <div className="p-3 bg-muted rounded-lg text-xs">
                <p className="font-medium mb-1">Perplexity Response Sample:</p>
                <p className="text-muted-foreground">
                  "Based on available sources, the product {misinformationCase.incorrectInfo.toLowerCase()}..."
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="flex justify-between items-center pt-4 border-t">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          <div className="flex gap-2">
            <Button variant="outline">
              <ExternalLink className="h-4 w-4 mr-2" />
              View All Mentions
            </Button>
            <Button>Take Action</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
