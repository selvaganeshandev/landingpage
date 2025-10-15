import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { useToast } from "@/hooks/use-toast";
import { Sparkles, Loader2, Brain, Plus } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";

interface GenerateTopicsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAdd?: (topics: any[]) => void;
}

export const GenerateTopicsDialog = ({ open, onOpenChange, onAdd }: GenerateTopicsDialogProps) => {
  const { toast } = useToast();
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedTopics, setGeneratedTopics] = useState<any[]>([]);
  const [selectedTopics, setSelectedTopics] = useState<Set<number>>(new Set());

  const handleGenerate = async () => {
    setIsGenerating(true);
    setGeneratedTopics([]);
    setSelectedTopics(new Set());

    try {
      // Simulate AI generation with mock data
      await new Promise(resolve => setTimeout(resolve, 2000));

      const mockTopics = [
        {
          name: "Recovery & Post-Workout",
          keywords: ["recovery", "post-workout nutrition", "muscle repair", "BCAA"],
          description: "Focus on recovery benefits and post-workout usage",
          estimatedMentions: 45,
          potentialVisibility: 85,
        },
        {
          name: "Allergen-Free & Sensitivities",
          keywords: ["allergen-free", "soy-free", "gluten-free", "digestive health"],
          description: "Targeting users with dietary restrictions",
          estimatedMentions: 38,
          potentialVisibility: 78,
        },
        {
          name: "Energy & Pre-Workout",
          keywords: ["energy boost", "pre-workout", "stamina", "performance fuel"],
          description: "Pre-workout and energy-focused positioning",
          estimatedMentions: 52,
          potentialVisibility: 82,
        },
        {
          name: "Women's Health & Wellness",
          keywords: ["women's protein", "hormonal balance", "prenatal nutrition", "wellness"],
          description: "Specifically targeting women's health needs",
          estimatedMentions: 41,
          potentialVisibility: 80,
        },
        {
          name: "Environmental Impact",
          keywords: ["carbon footprint", "sustainable farming", "eco-packaging", "climate-friendly"],
          description: "Focus on environmental and sustainability benefits",
          estimatedMentions: 29,
          potentialVisibility: 88,
        },
      ];

      setGeneratedTopics(mockTopics);
      setSelectedTopics(new Set(mockTopics.map((_, idx) => idx)));

      toast({
        title: "Topics Generated",
        description: `${mockTopics.length} potential topics identified from your data.`,
      });

    } catch (error: any) {
      console.error("Error generating topics:", error);
      toast({
        title: "Generation Failed",
        description: error.message || "Failed to generate topics. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const toggleTopic = (index: number) => {
    const newSelected = new Set(selectedTopics);
    if (newSelected.has(index)) {
      newSelected.delete(index);
    } else {
      newSelected.add(index);
    }
    setSelectedTopics(newSelected);
  };

  const handleAddSelected = () => {
    const selected = generatedTopics.filter((_, idx) => selectedTopics.has(idx));
    if (selected.length === 0) {
      toast({
        title: "No Topics Selected",
        description: "Please select at least one topic to add.",
        variant: "destructive",
      });
      return;
    }

    if (onAdd) {
      onAdd(selected);
    }

    toast({
      title: "Topics Added",
      description: `${selected.length} topic(s) added to your tracking.`,
    });

    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[800px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-outfit text-2xl flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-primary" />
            AI Topic Generation
          </DialogTitle>
          <DialogDescription>
            Discover new topics and categories to track based on your mention data
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Generate Button */}
          {generatedTopics.length === 0 && (
            <Card className="p-8 text-center">
              <Brain className="h-16 w-16 mx-auto mb-4 text-primary opacity-50" />
              <h3 className="text-lg font-semibold mb-2">AI-Powered Topic Discovery</h3>
              <p className="text-sm text-muted-foreground mb-6">
                Our AI will analyze your existing mentions, keywords, and performance data to suggest relevant topics and categories you should be tracking.
              </p>
              <Button
                onClick={handleGenerate}
                disabled={isGenerating}
                className="gradient-primary shadow-md"
                size="lg"
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                    Analyzing Your Data...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-5 w-5 mr-2" />
                    Generate Topic Suggestions
                  </>
                )}
              </Button>
            </Card>
          )}

          {/* Generated Topics */}
          {generatedTopics.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm font-medium">
                  Suggested Topics ({selectedTopics.size} selected)
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

              <div className="space-y-3">
                {generatedTopics.map((topic, idx) => (
                  <Card
                    key={idx}
                    className={`p-5 cursor-pointer transition-all ${
                      selectedTopics.has(idx)
                        ? "border-primary shadow-md"
                        : "hover:border-primary/50"
                    }`}
                    onClick={() => toggleTopic(idx)}
                  >
                    <div className="flex items-start gap-4">
                      <Checkbox
                        checked={selectedTopics.has(idx)}
                        onCheckedChange={() => toggleTopic(idx)}
                        className="mt-1"
                      />
                      <div className="flex-1">
                        <h4 className="font-semibold text-lg mb-2">{topic.name}</h4>
                        <p className="text-sm text-muted-foreground mb-3">{topic.description}</p>
                        
                        <div className="flex flex-wrap gap-2 mb-3">
                          {topic.keywords.map((keyword: string) => (
                            <Badge key={keyword} variant="secondary" className="text-xs">
                              {keyword}
                            </Badge>
                          ))}
                        </div>

                        <div className="grid grid-cols-2 gap-4 pt-3 border-t border-border">
                          <div>
                            <p className="text-xs text-muted-foreground">Estimated Mentions</p>
                            <p className="text-lg font-bold text-primary">{topic.estimatedMentions}</p>
                          </div>
                          <div>
                            <p className="text-xs text-muted-foreground">Potential Visibility</p>
                            <p className="text-lg font-bold text-success">{topic.potentialVisibility}%</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </div>

        {generatedTopics.length > 0 && (
          <div className="flex gap-3 pt-4 border-t">
            <Button variant="outline" onClick={() => onOpenChange(false)} className="flex-1">
              Cancel
            </Button>
            <Button onClick={handleAddSelected} className="gradient-primary flex-1">
              <Plus className="h-4 w-4 mr-2" />
              Add Selected Topics ({selectedTopics.size})
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};
