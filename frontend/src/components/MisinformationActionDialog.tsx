import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import { 
  Send,
  FileText,
  Users,
  CheckCircle,
  AlertCircle
} from "lucide-react";

interface MisinformationAlert {
  id: number;
  alert_type: 'misinformation' | 'broken_link' | 'outdated';
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'new' | 'reviewed' | 'resolved' | 'dismissed';
  llm_claim: string;
  source_content?: string;
  explanation?: string;
  created_at: string;
  reviewed_at?: string;
  citation_url?: {
    url: string;
    crawl_status: string;
  };
  prompt?: {
    id: number;
    prompt_text: string;
  };
}

const alertTypeLabels: Record<string, string> = {
  misinformation: 'Misinformation',
  broken_link: 'Broken Link',
  outdated: 'Outdated Information'
};

interface MisinformationActionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  misinformationCase: MisinformationAlert | null;
}

export function MisinformationActionDialog({
  open,
  onOpenChange,
  misinformationCase,
}: MisinformationActionDialogProps) {
  const { toast } = useToast();
  const [actionType, setActionType] = useState("submit-correction");
  const [notes, setNotes] = useState("");

  if (!misinformationCase) return null;

  const handleSubmitAction = () => {
    toast({
      title: "Action submitted successfully",
      description: `Your ${actionType} request has been initiated for case #${misinformationCase.id}`,
    });
    onOpenChange(false);
    setNotes("");
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Take Action on {alertTypeLabels[misinformationCase.alert_type] || 'Issue'}</DialogTitle>
          <DialogDescription>
            Choose how to address this {misinformationCase.alert_type.replace('_', ' ')} issue
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Case Summary */}
          <div className="p-4 bg-muted rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-medium">Case #{misinformationCase.id}</p>
              <Badge variant="secondary">{alertTypeLabels[misinformationCase.alert_type]}</Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              {misinformationCase.explanation || misinformationCase.llm_claim}
            </p>
          </div>

          <Separator />

          {/* Action Type Selection */}
          <div className="space-y-4">
            <Label className="text-base font-semibold">Select Action Type</Label>
            <RadioGroup value={actionType} onValueChange={setActionType}>
              <div className="space-y-3">
                <div className="flex items-start space-x-3 p-4 rounded-lg border hover:bg-accent cursor-pointer">
                  <RadioGroupItem value="submit-correction" id="submit-correction" className="mt-1" />
                  <div className="flex-1">
                    <Label htmlFor="submit-correction" className="cursor-pointer font-medium flex items-center gap-2">
                      <Send className="h-4 w-4" />
                      Submit Correction Request
                    </Label>
                    <p className="text-xs text-muted-foreground mt-1">
                      Submit official correction request to the AI platform with accurate information
                    </p>
                  </div>
                </div>

                <div className="flex items-start space-x-3 p-4 rounded-lg border hover:bg-accent cursor-pointer">
                  <RadioGroupItem value="update-sources" id="update-sources" className="mt-1" />
                  <div className="flex-1">
                    <Label htmlFor="update-sources" className="cursor-pointer font-medium flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      Update Source Documentation
                    </Label>
                    <p className="text-xs text-muted-foreground mt-1">
                      Update public documentation and authoritative sources with correct information
                    </p>
                  </div>
                </div>

                <div className="flex items-start space-x-3 p-4 rounded-lg border hover:bg-accent cursor-pointer">
                  <RadioGroupItem value="escalate-team" id="escalate-team" className="mt-1" />
                  <div className="flex-1">
                    <Label htmlFor="escalate-team" className="cursor-pointer font-medium flex items-center gap-2">
                      <Users className="h-4 w-4" />
                      Escalate to Team
                    </Label>
                    <p className="text-xs text-muted-foreground mt-1">
                      Assign to PR or legal team for review and coordinated response
                    </p>
                  </div>
                </div>

                <div className="flex items-start space-x-3 p-4 rounded-lg border hover:bg-accent cursor-pointer">
                  <RadioGroupItem value="monitor-only" id="monitor-only" className="mt-1" />
                  <div className="flex-1">
                    <Label htmlFor="monitor-only" className="cursor-pointer font-medium flex items-center gap-2">
                      <CheckCircle className="h-4 w-4" />
                      Continue Monitoring
                    </Label>
                    <p className="text-xs text-muted-foreground mt-1">
                      Mark as acknowledged and continue monitoring without immediate action
                    </p>
                  </div>
                </div>
              </div>
            </RadioGroup>
          </div>

          <Separator />

          {/* Source Content Reference */}
          {misinformationCase.source_content && (
            <div className="p-4 bg-success/10 border border-success/20 rounded-lg">
              <div className="flex items-start gap-2 mb-2">
                <CheckCircle className="h-4 w-4 text-success mt-0.5" />
                <p className="text-sm font-medium text-success">What the Source Actually Says</p>
              </div>
              <p className="text-sm pl-6">{misinformationCase.source_content}</p>
            </div>
          )}

          {/* LLM Claim Reference */}
          {misinformationCase.llm_claim && (
            <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
              <div className="flex items-start gap-2 mb-2">
                <AlertCircle className="h-4 w-4 text-destructive mt-0.5" />
                <p className="text-sm font-medium text-destructive">What the LLM Claimed</p>
              </div>
              <p className="text-sm pl-6">{misinformationCase.llm_claim}</p>
            </div>
          )}

          {/* Additional Notes */}
          <div className="space-y-2">
            <Label htmlFor="notes">Additional Notes or Context</Label>
            <Textarea
              id="notes"
              placeholder="Add any additional context, supporting documentation, or instructions for this action..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={4}
            />
          </div>

          {/* Action Preview */}
          <div className="p-4 bg-primary/5 border border-primary/20 rounded-lg">
            <div className="flex items-start gap-2">
              <AlertCircle className="h-4 w-4 text-primary mt-0.5" />
              <div className="text-xs space-y-1">
                <p className="font-medium">What happens next:</p>
                {actionType === "submit-correction" && (
                  <p className="text-muted-foreground">
                    A correction request will be documented with the accurate information and supporting documentation for follow-up with AI platforms.
                  </p>
                )}
                {actionType === "update-sources" && (
                  <p className="text-muted-foreground">
                    Your content team will be notified to update official documentation, press releases, and authoritative sources with correct information.
                  </p>
                )}
                {actionType === "escalate-team" && (
                  <p className="text-muted-foreground">
                    This case will be assigned to the appropriate team members with high priority notification for immediate review.
                  </p>
                )}
                {actionType === "monitor-only" && (
                  <p className="text-muted-foreground">
                    This case will remain in monitoring status. You'll receive updates if the situation changes.
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmitAction}>
            Submit Action
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
