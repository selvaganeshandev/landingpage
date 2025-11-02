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
import { Badge } from "@/components/ui/badge";
import { Sparkles, Loader2, Plus } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface GenerateVariantsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  promptGroup: {
    id: number;
    group_id: string;
    domain_name: string;
    prompts_count: number;
  } | null;
  onAdd?: (variants: string[]) => void;
}

export const GenerateVariantsDialog = ({ open, onOpenChange, promptGroup, onAdd }: GenerateVariantsDialogProps) => {
  const { toast } = useToast();
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedVariants, setGeneratedVariants] = useState<string[]>([]);
  const [selectedVariants, setSelectedVariants] = useState<Set<number>>(new Set());

  useEffect(() => {
    console.log("GenerateVariantsDialog - promptGroup received:", promptGroup);
  }, [promptGroup]);

  const handleGenerate = async () => {
    setIsGenerating(true);
    setGeneratedVariants([]);
    setSelectedVariants(new Set());

    try {
      // Simulate AI generation - in real app, call your AI backend
      await new Promise(resolve => setTimeout(resolve, 2000));

      // Generate variants based on the group ID and domain
      const basePrompt = promptGroup?.group_id || "prompt";
      const mockVariants = [
        `best ${basePrompt}`,
        `top ${basePrompt}`,
        `affordable ${basePrompt}`,
        `premium ${basePrompt}`,
        `${basePrompt} reviews`,
        `${basePrompt} comparison`,
        `${basePrompt} guide`,
        `${basePrompt} tips`,
      ];

      setGeneratedVariants(mockVariants);
      // Auto-select all generated variants
      setSelectedVariants(new Set(mockVariants.map((_, idx) => idx)));

      toast({
        title: "Variants Generated",
        description: `${mockVariants.length} prompt variants have been created.`,
      });
    } catch (error) {
      toast({
        title: "Generation Failed",
        description: "Failed to generate variants. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const toggleVariant = (index: number) => {
    const newSelected = new Set(selectedVariants);
    if (newSelected.has(index)) {
      newSelected.delete(index);
    } else {
      newSelected.add(index);
    }
    setSelectedVariants(newSelected);
  };

  const handleAddSelected = () => {
    const selected = generatedVariants.filter((_, idx) => selectedVariants.has(idx));
    if (selected.length === 0) {
      toast({
        title: "No Variants Selected",
        description: "Please select at least one variant to add.",
        variant: "destructive",
      });
      return;
    }

    if (onAdd) {
      onAdd(selected);
    }

    toast({
      title: "Variants Added",
      description: `${selected.length} variant(s) added to your prompt group.`,
    });

    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-outfit text-2xl flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            Generate Prompt Variants
          </DialogTitle>
          <DialogDescription>
            AI will create variations of your main prompt to expand tracking coverage
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Group Information */}
          <div className="space-y-2">
            <p className="text-sm font-medium">Prompt Group</p>
            <div className="p-4 rounded-xl bg-gradient-to-br from-primary/5 to-secondary/5 border border border-border">
              <p className="font-mono text-sm">Group ID: {promptGroup?.group_id}</p>
              <p className="text-xs text-muted-foreground mt-1">Domain: {promptGroup?.domain_name}</p>
              <p className="text-xs text-muted-foreground">Current Prompts: {promptGroup?.prompts_count}</p>
            </div>
          </div>

          {/* Generate Button */}
          {generatedVariants.length === 0 && (
            <Button
              onClick={handleGenerate}
              disabled={isGenerating}
              className="w-full gradient-primary shadow-md"
              size="lg"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Generating Variants...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 mr-2" />
                  Generate Variants with AI
                </>
              )}
            </Button>
          )}

          {/* Generated Variants */}
          {generatedVariants.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium">
                  Generated Variants ({selectedVariants.size} selected)
                </p>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleGenerate}
                  disabled={isGenerating}
                >
                  {isGenerating ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    "Regenerate"
                  )}
                </Button>
              </div>

              <div className="space-y-2 max-h-[300px] overflow-y-auto">
                {generatedVariants.map((variant, idx) => (
                  <div
                    key={idx}
                    onClick={() => toggleVariant(idx)}
                    className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${
                      selectedVariants.has(idx)
                        ? "border-primary bg-primary/5 shadow-sm"
                        : "border border-border hover:border-primary/50 bg-card/50"
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`w-5 h-5 rounded border-2 flex-shrink-0 mt-0.5 flex items-center justify-center transition-all ${
                        selectedVariants.has(idx)
                          ? "border-primary bg-primary"
                          : "border-muted-foreground"
                      }`}>
                        {selectedVariants.has(idx) && (
                          <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                          </svg>
                        )}
                      </div>
                      <p className="font-mono text-sm flex-1">{variant}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {generatedVariants.length > 0 && (
          <DialogFooter>
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button onClick={handleAddSelected} className="gradient-primary">
              <Plus className="h-4 w-4 mr-2" />
              Add Selected ({selectedVariants.size})
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
};
