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

interface MisinformationCase {
  id: number;
  title: string;
  platform: string;
  severity: string;
  correctInfo: string;
}

interface MisinformationActionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  misinformationCase: MisinformationCase | null;
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
          <DialogTitle>Take Action on Misinformation</DialogTitle>
          <DialogDescription>
            Choose how to address: {misinformationCase.title}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Case Summary */}
          <div className="p-4 bg-muted rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-medium">Case #{misinformationCase.id}</p>
              <Badge variant="secondary">{misinformationCase.platform}</Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              {misinformationCase.title}
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

          {/* Correct Information Reference */}
          <div className="p-4 bg-success/10 border border-success/20 rounded-lg">
            <div className="flex items-start gap-2 mb-2">
              <CheckCircle className="h-4 w-4 text-success mt-0.5" />
              <p className="text-sm font-medium text-success">Correct Information to Submit</p>
            </div>
            <p className="text-sm pl-6">{misinformationCase.correctInfo}</p>
          </div>

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
                    A correction request will be automatically submitted to {misinformationCase.platform} with the accurate information and supporting documentation.
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
                    This case will remain in monitoring status. You'll receive updates if the situation changes or spreads to more platforms.
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
