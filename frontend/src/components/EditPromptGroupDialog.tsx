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
  const [mainPrompt, setMainPrompt] = useState("");
  const [description, setDescription] = useState("");
  const [variants, setVariants] = useState<string[]>([]);
  const [variantInput, setVariantInput] = useState("");

  useEffect(() => {
    if (promptGroup) {
      setGroupId(promptGroup.group_id);
      setDomainId(promptGroup.domain_id);
      // Load group details to populate primary/secondary
      (async () => {
        try {
          const detail = await apiClient.getPromptGroupDetail(promptGroup.id);
          setMainPrompt(detail.group.primary_prompt || "");
          setVariants(detail.group.prompts?.filter((p: any) => p.type === 'secondary').map((p: any) => p.prompt_text) || detail.group.secondary_prompts || []);
          setDescription(detail.group.description || "");
        } catch (e) {
          // Fallback to list data if detail missing
          setMainPrompt((promptGroup as any).primary_prompt || "");
          setVariants(((promptGroup as any).secondary_prompts as string[]) || []);
          setDescription("");
        }
      })();
    }
  }, [promptGroup]);

  const handleAddVariant = () => {
    if (variantInput.trim() && !variants.includes(variantInput.trim())) {
      setVariants([...variants, variantInput.trim()]);
      setVariantInput("");
    }
  };

  const handleRemoveVariant = (index: number) => {
    setVariants(variants.filter((_, i) => i !== index));
  };

  const handleSubmit = async () => {
    if (!groupId.trim() || !mainPrompt.trim() || !promptGroup) {
      toast({
        title: "Missing Information",
        description: "Please provide a name and main prompt.",
        variant: "destructive",
      });
      return;
    }

    try {
      const response = await apiClient.updatePromptGroup(promptGroup.id, {
        group_id: groupId.trim(),
        domain_id: domainId,
        primary_prompt: mainPrompt.trim(),
        secondary_prompts: variants,
      });

      toast({
        title: "Prompt Group Updated",
        description: `"${groupId}" has been updated successfully.`,
      });

      // Call onEdit callback to refresh the list
      if (onEdit) {
        onEdit(response.group as any);
      }

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
      handleAddVariant();
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
          {/* Group Name */}
          <div className="space-y-2">
            <Label htmlFor="edit-name">Group Name*</Label>
            <Input
              id="edit-name"
              placeholder="e.g., Vegan Protein - Athletes"
              value={groupId}
              onChange={(e) => setGroupId(e.target.value)}
              className="border-border/50"
            />
          </div>

          {/* Main Prompt */}
          <div className="space-y-2">
            <Label htmlFor="edit-mainPrompt">Main Prompt*</Label>
            <Input
              id="edit-mainPrompt"
              placeholder="e.g., best vegan protein powder for athletes"
              value={mainPrompt}
              onChange={(e) => setMainPrompt(e.target.value)}
              className="border-border/50 font-mono"
            />
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="edit-description">Description (Optional)</Label>
            <Textarea
              id="edit-description"
              placeholder="Brief description of what this prompt group tracks..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="border-border/50 min-h-[80px]"
            />
          </div>

          {/* Prompt Variants */}
          <div className="space-y-2">
            <Label htmlFor="edit-variant">Prompt Variants</Label>
            <div className="flex gap-2">
              <Input
                id="edit-variant"
                placeholder="Add a variant prompt..."
                value={variantInput}
                onChange={(e) => setVariantInput(e.target.value)}
                onKeyPress={handleKeyPress}
                className="border-border/50 font-mono"
              />
              <Button type="button" onClick={handleAddVariant} variant="outline">
                Add
              </Button>
            </div>
            
            {variants.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-3">
                {variants.map((variant, idx) => (
                  <Badge
                    key={idx}
                    variant="secondary"
                    className="pl-3 pr-2 py-1.5 text-sm font-mono"
                  >
                    {variant}
                    <button
                      onClick={() => handleRemoveVariant(idx)}
                      className="ml-2 hover:text-destructive transition-colors"
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
