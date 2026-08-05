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
import { X, Loader2, Sparkles } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/services/api";
import { useDomainStore } from "@/stores/domainStore";
import { useAuth } from "@/contexts/AuthContext";
import { getActiveDomainIdNumber } from "@/utils/activeDomain";

interface AddPromptGroupDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAdd?: (group: any) => void;
}

export const AddPromptGroupDialog = ({ open, onOpenChange, onAdd }: AddPromptGroupDialogProps) => {
  const { toast } = useToast();
  const { selectedDomain } = useDomainStore();
  const { user } = useAuth();
  const [groupId, setGroupId] = useState("");
  const [mainPrompt, setMainPrompt] = useState("");
  const [description, setDescription] = useState("");
  const [variants, setVariants] = useState<string[]>([]);
  const [variantInput, setVariantInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  // Reset form when dialog opens/closes
  useEffect(() => {
    if (!open) {
      setGroupId("");
      setMainPrompt("");
      setDescription("");
      setVariants([]);
      setVariantInput("");
    }
  }, [open]);

  const handleAddVariant = () => {
    if (variantInput.trim() && !variants.includes(variantInput.trim())) {
      setVariants([...variants, variantInput.trim()]);
      setVariantInput("");
    }
  };

  const handleRemoveVariant = (index: number) => {
    setVariants(variants.filter((_, i) => i !== index));
  };

  const handleGenerateSuggestions = async () => {
    if (!mainPrompt.trim()) {
      toast({
        title: "Missing Main Prompt",
        description: "Please enter a main prompt first.",
        variant: "destructive",
      });
      return;
    }

    setIsGenerating(true);
    try {
      // Call backend API to generate variants
      const response = await apiClient.generatePromptVariants({
        main_prompt: mainPrompt.trim(),
      });

      if (response.variants && Array.isArray(response.variants)) {
        // Generate a group name from the main prompt if not set
        if (!groupId.trim()) {
          const words = mainPrompt.trim().split(' ');
          const capitalized = words.map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
          setGroupId(capitalized);
        }

        // Add generated variants (avoid duplicates)
        const newVariants = response.variants.filter(v => !variants.includes(v));
        setVariants([...variants, ...newVariants]);

        toast({
          title: "Suggestions Generated",
          description: `Generated ${response.variants.length} prompt variants.`,
        });
      } else {
        throw new Error("Invalid response format");
      }
    } catch (error: any) {
      console.error("Error generating suggestions:", error);
      toast({
        title: "Generation Failed",
        description: error.message || "Failed to generate suggestions. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSubmit = async () => {
    const activeDomainId = selectedDomain?.id ?? getActiveDomainIdNumber(user);
    
    if (!activeDomainId) {
      toast({
        title: "No Domain Selected",
        description: "Please select a domain first.",
        variant: "destructive",
      });
      return;
    }

    if (!groupId.trim()) {
      toast({
        title: "Missing Information",
        description: "Please provide a group name.",
        variant: "destructive",
      });
      return;
    }

    // Main prompt is optional, but a group needs at least one prompt — the main
    // prompt OR a variant — to be trackable (matches the backend's rule).
    if (!mainPrompt.trim() && variants.length === 0) {
      toast({
        title: "Add a prompt",
        description: "Enter a main prompt or add at least one variant.",
        variant: "destructive",
      });
      return;
    }

    try {
      setIsLoading(true);
      const response = await apiClient.createPromptGroup({
        group_id: groupId.trim(),
        domain_id: activeDomainId,
        // Omit the primary prompt entirely when left blank (don't send [""]).
        primary_prompts: mainPrompt.trim() ? [mainPrompt.trim()] : [],
        secondary_prompts: variants,
      });

      // Close first, then notify. Refreshing the list is the caller's job and
      // can take a moment; holding the dialog open for it made a successful
      // create look like it was still working.
      onOpenChange(false);

      toast({
        title: "Prompt group created",
        description: `"${groupId}" is queued — analysis starts automatically.`,
      });

      // Call onAdd callback to refresh the list
      if (onAdd) {
        onAdd(response.group);
      }
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to create prompt group",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
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
          <DialogTitle className="font-inter text-2xl">Add Prompt Group</DialogTitle>
          <DialogDescription>
            Create a new prompt group to track related search queries
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Group Name */}
          <div className="space-y-2">
            <Label htmlFor="name">Group Name*</Label>
            <Input
              id="name"
              placeholder="e.g., Vegan Protein - Athletes"
              value={groupId}
              onChange={(e) => setGroupId(e.target.value)}
              className="border-border/50"
            />
          </div>

          {/* Main Prompt */}
          <div className="space-y-2">
            <Label htmlFor="mainPrompt">Main Prompt (Optional)</Label>
            <div className="flex gap-2">
              <Input
                id="mainPrompt"
                placeholder="e.g., best vegan protein powder for athletes"
                value={mainPrompt}
                onChange={(e) => setMainPrompt(e.target.value)}
                className="border-border/50 font-mono flex-1"
              />
              <Button 
                type="button" 
                onClick={handleGenerateSuggestions}
                disabled={isGenerating || !mainPrompt.trim()}
                className="gradient-primary"
              >
                {isGenerating ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Sparkles className="h-4 w-4" />
                )}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Optional — add a main prompt and click the ✨ button to auto-generate the group name and variants. You can also skip it and just add variants below.
            </p>
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Description (Optional)</Label>
            <Textarea
              id="description"
              placeholder="Brief description of what this prompt group tracks..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="border-border/50 min-h-[80px]"
            />
          </div>

          {/* Prompt Variants */}
          <div className="space-y-2">
            <Label htmlFor="variant">Prompt Variants</Label>
            <div className="flex gap-2">
              <Input
                id="variant"
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
          <Button onClick={handleSubmit} disabled={isLoading} className="gradient-primary">
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Creating...
              </>
            ) : (
              "Create Group"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};