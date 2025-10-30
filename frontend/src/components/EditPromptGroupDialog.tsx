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
import { X, Plus } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/services/api";

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
  const [primaryPrompt, setPrimaryPrompt] = useState("");
  const [secondaryPrompts, setSecondaryPrompts] = useState<string[]>([]);
  const [secondaryInput, setSecondaryInput] = useState("");

  useEffect(() => {
    if (promptGroup) {
      setGroupId(promptGroup.group_id);
      setDomainId(promptGroup.domain_id);
      // Load group details to populate primary/secondary
      (async () => {
        try {
          const detail = await apiClient.getPromptGroupDetail(promptGroup.id);
          setPrimaryPrompt(detail.group.primary_prompt || "");
          setSecondaryPrompts(detail.group.prompts?.filter((p: any) => p.type === 'secondary').map((p: any) => p.prompt_text) || detail.group.secondary_prompts || []);
        } catch (e) {
          // Fallback to list data if detail missing
          setPrimaryPrompt((promptGroup as any).primary_prompt || "");
          setSecondaryPrompts(((promptGroup as any).secondary_prompts as string[]) || []);
        }
      })();
    }
  }, [promptGroup]);

  const handleAddSecondaryPrompt = () => {
    if (secondaryInput.trim() && !secondaryPrompts.includes(secondaryInput.trim())) {
      setSecondaryPrompts([...secondaryPrompts, secondaryInput.trim()]);
      setSecondaryInput("");
    }
  };

  const handleRemoveSecondaryPrompt = (index: number) => {
    setSecondaryPrompts(secondaryPrompts.filter((_, i) => i !== index));
  };

  const handleSubmit = async () => {
    if (!groupId.trim() || !promptGroup) {
      toast({
        title: "Missing Information",
        description: "Please provide a group name.",
        variant: "destructive",
      });
      return;
    }
    if (!primaryPrompt.trim()) {
      toast({
        title: "Main Prompt required",
        description: "Please enter the main prompt.",
        variant: "destructive",
      });
      return;
    }

    try {
      const response = await apiClient.updatePromptGroup(promptGroup.id, {
        group_id: groupId.trim(),
        domain_id: domainId,
        primary_prompt: primaryPrompt.trim(),
        secondary_prompts: secondaryPrompts,
      });

      if (onEdit) {
        onEdit(response.group as any);
      }

      toast({
        title: "Prompt Group Updated",
        description: `"${groupId}" has been updated successfully.`,
      });

      onOpenChange(false);
    } catch (error: any) {
      toast({
        title: "Update failed",
        description: error.message || "Failed to update prompt group",
        variant: "destructive",
      });
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      setPrimaryPrompt(primaryPrompt);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-outfit text-2xl">Edit Prompt Group</DialogTitle>
          <DialogDescription>
            Update your prompt group settings and variants
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Group Name */}
          <div className="space-y-2">
            <Label htmlFor="edit-groupId">Group ID*</Label>
            <Input
              id="edit-groupId"
              placeholder="e.g., Vegan Protein - Athletes"
              value={groupId}
              onChange={(e) => setGroupId(e.target.value)}
              className="border-border/50"
            />
          </div>

          {/* Main Prompt */}
          <div className="space-y-2">
            <Label htmlFor="main-prompt">Main Prompt*</Label>
            <Input
              id="main-prompt"
              placeholder="e.g., best vegan protein powder for athletes"
              value={primaryPrompt}
              onChange={(e) => setPrimaryPrompt(e.target.value)}
              className="border-border/50 font-mono"
            />
          </div>

          {/* Prompt Variants */}
          <div className="space-y-2">
            <Label>Prompt Variants</Label>
            <div className="flex gap-2">
              <Input
                placeholder="Add a variant prompt..."
                value={secondaryInput}
                onChange={(e) => setSecondaryInput(e.target.value)}
                className="border-border/50 font-mono flex-1"
                onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddSecondaryPrompt())}
              />
              <Button type="button" onClick={handleAddSecondaryPrompt} size="sm">
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            {secondaryPrompts.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {secondaryPrompts.map((prompt, index) => (
                  <Badge key={index} variant="secondary" className="px-3 py-1">
                    {prompt}
                    <button
                      onClick={() => handleRemoveSecondaryPrompt(index)}
                      className="ml-2 hover:bg-white/20 rounded-full p-0.5"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            )}
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
