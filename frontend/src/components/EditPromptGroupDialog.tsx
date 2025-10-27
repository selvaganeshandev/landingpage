import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { X } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface PromptGroup {
  id: number;
  group_id: string;
  domain_id: number;
  domain_name: string;
  total_mentions: number;
  total_citations: number;
  average_position: number;
  created_at: string;
  modified_at: string;
  prompts_count: number;
  analytics_summary?: any;
}

interface EditPromptGroupDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  promptGroup: PromptGroup | null;
  onEdit?: (group: PromptGroup) => void;
}

export const EditPromptGroupDialog = ({ open, onOpenChange, promptGroup, onEdit }: EditPromptGroupDialogProps) => {
  const { toast } = useToast();
  const [groupId, setGroupId] = useState("");
  const [domainId, setDomainId] = useState<number>(0);
  const [primaryPrompts, setPrimaryPrompts] = useState<string[]>([]);
  const [secondaryPrompts, setSecondaryPrompts] = useState<string[]>([]);
  const [primaryInput, setPrimaryInput] = useState("");
  const [secondaryInput, setSecondaryInput] = useState("");

  useEffect(() => {
    console.log("EditPromptGroupDialog - promptGroup received:", promptGroup);
    if (promptGroup) {
      setGroupId(promptGroup.group_id);
      setDomainId(promptGroup.domain_id);
      // For now, we'll start with empty prompts arrays
      // In a real implementation, you'd fetch the actual prompts for this group
      setPrimaryPrompts([]);
      setSecondaryPrompts([]);
    }
  }, [promptGroup]);

  const handleAddPrimaryPrompt = () => {
    if (primaryInput.trim() && !primaryPrompts.includes(primaryInput.trim())) {
      setPrimaryPrompts([...primaryPrompts, primaryInput.trim()]);
      setPrimaryInput("");
    }
  };

  const handleAddSecondaryPrompt = () => {
    if (secondaryInput.trim() && !secondaryPrompts.includes(secondaryInput.trim())) {
      setSecondaryPrompts([...secondaryPrompts, secondaryInput.trim()]);
      setSecondaryInput("");
    }
  };

  const handleRemovePrimaryPrompt = (index: number) => {
    setPrimaryPrompts(primaryPrompts.filter((_, i) => i !== index));
  };

  const handleRemoveSecondaryPrompt = (index: number) => {
    setSecondaryPrompts(secondaryPrompts.filter((_, i) => i !== index));
  };

  const handleSubmit = () => {
    if (!groupId.trim() || !promptGroup) {
      toast({
        title: "Missing Information",
        description: "Please provide a group ID.",
        variant: "destructive",
      });
      return;
    }

    const updatedGroup: PromptGroup = {
      ...promptGroup,
      group_id: groupId.trim(),
      domain_id: domainId,
    };

    if (onEdit) {
      onEdit(updatedGroup);
    }

    toast({
      title: "Prompt Group Updated",
      description: `"${groupId}" has been updated successfully.`,
    });

    onOpenChange(false);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAddPrimaryPrompt();
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-outfit text-2xl">Edit Prompt Group</DialogTitle>
          <DialogDescription>
            Update your prompt group settings and variants
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Group ID */}
          <div className="space-y-2">
            <Label htmlFor="edit-groupId">Group ID*</Label>
            <Input
              id="edit-groupId"
              placeholder="e.g., Test"
              value={groupId}
              onChange={(e) => setGroupId(e.target.value)}
              className="border-border/50"
            />
          </div>

          {/* Domain Info */}
          <div className="space-y-2">
            <Label>Domain</Label>
            <div className="p-3 bg-muted/30 rounded-lg border border-border/50">
              <p className="text-sm font-medium">{promptGroup?.domain_name}</p>
              <p className="text-xs text-muted-foreground">Domain ID: {promptGroup?.domain_id}</p>
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 gap-4">
            <div className="p-3 bg-muted/30 rounded-lg border border-border/50">
              <p className="text-sm font-medium">Total Mentions</p>
              <p className="text-lg font-bold">{promptGroup?.total_mentions || 0}</p>
            </div>
            <div className="p-3 bg-muted/30 rounded-lg border border-border/50">
              <p className="text-sm font-medium">Prompts Count</p>
              <p className="text-lg font-bold">{promptGroup?.prompts_count || 0}</p>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} className="gradient-primary">
            Save Changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
