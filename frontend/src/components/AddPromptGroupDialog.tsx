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
import { Badge } from "@/components/ui/badge";
import { X, Loader2, Plus } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/services/api";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface AddPromptGroupDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAdd?: (group: any) => void;
}

export const AddPromptGroupDialog = ({ open, onOpenChange, onAdd }: AddPromptGroupDialogProps) => {
  const { toast } = useToast();
  const [groupId, setGroupId] = useState("");
  const [domainId, setDomainId] = useState<number | null>(null);
  const [primaryPrompts, setPrimaryPrompts] = useState<string[]>([]);
  const [secondaryPrompts, setSecondaryPrompts] = useState<string[]>([]);
  const [primaryInput, setPrimaryInput] = useState("");
  const [secondaryInput, setSecondaryInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [domains, setDomains] = useState<any[]>([]);

  // Load domains when dialog opens
  useEffect(() => {
    if (open) {
      loadDomains();
    }
  }, [open]);

  const loadDomains = async () => {
    try {
      const response = await apiClient.getDomains();
      setDomains(response.domains);
    } catch (error) {
      console.error("Failed to load domains:", error);
    }
  };

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

  const handleSubmit = async () => {
    if (!groupId.trim() || !domainId) {
      toast({
        title: "Missing Information",
        description: "Please provide a group ID and select a domain.",
        variant: "destructive",
      });
      return;
    }

    // Treat the "Main Prompt" input as required primary prompt
    if (primaryPrompts.length === 0) {
      toast({
        title: "Main Prompt required",
        description: "Please add a main prompt.",
        variant: "destructive",
      });
      return;
    }

    try {
      setIsLoading(true);
      const response = await apiClient.createPromptGroup({
        group_id: groupId.trim(),
        domain_id: domainId,
        primary_prompts: primaryPrompts,
        secondary_prompts: secondaryPrompts,
      });

      toast({
        title: "Success",
        description: `Created prompt group with ${response.prompts_created} prompts and ${response.analytics_created} analytics records.`,
      });

      if (onAdd) {
        onAdd(response.group);
      }

      // Reset form
      setGroupId("");
      setDomainId(null);
      setPrimaryPrompts([]);
      setSecondaryPrompts([]);
      setPrimaryInput("");
      setSecondaryInput("");
      onOpenChange(false);
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

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-outfit text-2xl">Add Prompt Group</DialogTitle>
          <DialogDescription>
            Create a prompt group and variants like in the reference design
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Group Name */}
          <div className="space-y-2">
            <Label htmlFor="groupId">Group Name*</Label>
            <Input
              id="groupId"
              placeholder="e.g., Vegan Protein - Athletes"
              value={groupId}
              onChange={(e) => setGroupId(e.target.value)}
              className="border border-border"
            />
          </div>

          {/* Domain Selection */}
          <div className="space-y-2">
            <Label htmlFor="domain">Domain*</Label>
            <Select value={domainId?.toString() || ""} onValueChange={(value) => setDomainId(parseInt(value))}>
              <SelectTrigger className="border border-border">
                <SelectValue placeholder="Select a domain" />
              </SelectTrigger>
              <SelectContent>
                {domains.map((domain) => (
                  <SelectItem key={domain.id} value={domain.id.toString()}>
                    {domain.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Main Prompt */}
          <div className="space-y-2">
            <Label>Main Prompt*</Label>
            <div className="flex gap-2">
              <Input
                placeholder="e.g., best vegan protein powder for athletes"
                value={primaryInput}
                onChange={(e) => setPrimaryInput(e.target.value)}
                className="border border-border font-mono flex-1"
                onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddPrimaryPrompt())}
              />
              <Button type="button" onClick={handleAddPrimaryPrompt} size="sm">
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            {primaryPrompts.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {primaryPrompts.map((prompt, index) => (
                  <Badge key={index} variant="default" className="px-3 py-1">
                    {prompt}
                    <button
                      onClick={() => handleRemovePrimaryPrompt(index)}
                      className="ml-2 hover:bg-white/20 rounded-full p-0.5"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            )}
          </div>

          {/* Prompt Variants */}
          <div className="space-y-2">
            <Label>Prompt Variants (Optional)</Label>
            <div className="flex gap-2">
              <Input
                placeholder="Add a variant prompt..."
                value={secondaryInput}
                onChange={(e) => setSecondaryInput(e.target.value)}
                className="border border-border font-mono flex-1"
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
          <Button variant="outline" onClick={() => onOpenChange(false)} className="border border-border">
            Cancel
          </Button>
          <Button 
            onClick={handleSubmit} 
            disabled={isLoading}
            className="gradient-primary"
          >
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