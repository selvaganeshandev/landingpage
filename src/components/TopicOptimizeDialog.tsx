import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import { 
  Target, 
  Sparkles, 
  TrendingUp, 
  AlertCircle, 
  CheckCircle2, 
  Lightbulb,
  Plus,
  Loader2
} from "lucide-react";
import { supabase } from "@/integrations/supabase/client";

interface TopicOptimizeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  topic: {
    id: number;
    name: string;
    keywords: string[];
    mentions: number;
    visibility: number;
    sentiment: number;
  } | null;
}

export const TopicOptimizeDialog = ({ open, onOpenChange, topic }: TopicOptimizeDialogProps) => {
  const { toast } = useToast();
  const [isGenerating, setIsGenerating] = useState(false);
  const [recommendations, setRecommendations] = useState<any>(null);

  const handleGenerateRecommendations = async () => {
    if (!topic) return;

    setIsGenerating(true);

    try {
      // Simulate AI analysis
      await new Promise(resolve => setTimeout(resolve, 2000));

      // Generate recommendations based on topic data
      setRecommendations({
        keywords: [
          { keyword: "vegan athlete protein", impact: "high", difficulty: "low" },
          { keyword: "plant protein for bodybuilding", impact: "high", difficulty: "medium" },
          { keyword: "complete plant-based protein", impact: "medium", difficulty: "low" },
          { keyword: "clean vegan protein supplement", impact: "medium", difficulty: "medium" },
        ],
        contentGaps: [
          { gap: "Comparison with whey protein", priority: "high", potential: "+15% visibility" },
          { gap: "Scientific backing and studies", priority: "high", potential: "+12% sentiment" },
          { gap: "Recipe integration ideas", priority: "medium", potential: "+8% engagement" },
        ],
        prompts: [
          "best complete protein vegan powder for athletes",
          "plant-based protein vs whey for muscle building",
          "scientifically proven vegan protein supplements",
          "high protein vegan powder for strength training",
        ],
        competitive: [
          { insight: "Emphasize complete amino acid profile", impact: "high" },
          { insight: "Highlight third-party testing certifications", impact: "high" },
          { insight: "Focus on clean ingredient list", impact: "medium" },
        ],
        actions: [
          { action: "Add 'complete protein' to main positioning", priority: 1 },
          { action: "Create comparison content vs traditional proteins", priority: 2 },
          { action: "Showcase scientific research and certifications", priority: 3 },
          { action: "Expand into recovery and performance keywords", priority: 4 },
        ],
      });

      toast({
        title: "Recommendations Generated",
        description: "AI has analyzed your topic and created optimization strategies.",
      });

    } catch (error: any) {
      console.error("Error generating recommendations:", error);
      toast({
        title: "Generation Failed",
        description: error.message || "Failed to generate recommendations. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsGenerating(false);
    }
  };

  if (!topic) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-outfit text-2xl flex items-center gap-2">
            <Target className="h-6 w-6 text-primary" />
            Optimize "{topic.name}"
          </DialogTitle>
          <DialogDescription>
            AI-powered recommendations to improve visibility and sentiment
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Current Status */}
          <Card className="p-4 bg-gradient-to-br from-primary/5 to-secondary/5 border-primary/20">
            <div className="grid grid-cols-3 gap-4">
              <div>
                <p className="text-xs text-muted-foreground mb-1">Current Visibility</p>
                <p className="text-2xl font-bold">{topic.visibility}%</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">Current Sentiment</p>
                <p className="text-2xl font-bold">{topic.sentiment}%</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">Active Keywords</p>
                <p className="text-2xl font-bold">{topic.keywords.length}</p>
              </div>
            </div>
          </Card>

          {/* Generate Button */}
          {!recommendations && (
            <Button
              onClick={handleGenerateRecommendations}
              disabled={isGenerating}
              className="w-full gradient-primary shadow-md"
              size="lg"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                  Generating AI Recommendations...
                </>
              ) : (
                <>
                  <Sparkles className="h-5 w-5 mr-2" />
                  Generate Optimization Recommendations
                </>
              )}
            </Button>
          )}

          {/* Recommendations */}
          {recommendations && (
            <Tabs defaultValue="keywords" className="space-y-4">
              <TabsList className="grid w-full grid-cols-5">
                <TabsTrigger value="keywords">Keywords</TabsTrigger>
                <TabsTrigger value="gaps">Content Gaps</TabsTrigger>
                <TabsTrigger value="prompts">Prompts</TabsTrigger>
                <TabsTrigger value="competitive">Positioning</TabsTrigger>
                <TabsTrigger value="actions">Action Plan</TabsTrigger>
              </TabsList>

              {/* Keyword Suggestions */}
              <TabsContent value="keywords" className="space-y-3">
                <Card className="p-6">
                  <h4 className="font-semibold mb-4 flex items-center gap-2">
                    <Plus className="h-4 w-4 text-primary" />
                    Recommended Keywords to Add
                  </h4>
                  <div className="space-y-3">
                    {recommendations.keywords.map((item: any, idx: number) => (
                      <div key={idx} className="p-4 rounded-lg border border-border hover:bg-accent/50 transition-colors">
                        <div className="flex items-center justify-between mb-2">
                          <Badge variant="secondary" className="font-mono">{item.keyword}</Badge>
                          <div className="flex items-center gap-3">
                            <Badge variant={item.impact === "high" ? "default" : "outline"}>
                              {item.impact} impact
                            </Badge>
                            <Badge variant={item.difficulty === "low" ? "outline" : "secondary"}>
                              {item.difficulty} difficulty
                            </Badge>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              </TabsContent>

              {/* Content Gaps */}
              <TabsContent value="gaps" className="space-y-3">
                <Card className="p-6">
                  <h4 className="font-semibold mb-4 flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 text-warning" />
                    Content Opportunities
                  </h4>
                  <div className="space-y-3">
                    {recommendations.contentGaps.map((item: any, idx: number) => (
                      <div key={idx} className="p-4 rounded-lg border border-border">
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex-1">
                            <p className="font-medium mb-1">{item.gap}</p>
                            <p className="text-sm text-success font-medium">{item.potential}</p>
                          </div>
                          <Badge variant={item.priority === "high" ? "destructive" : "secondary"}>
                            {item.priority} priority
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              </TabsContent>

              {/* Prompt Suggestions */}
              <TabsContent value="prompts" className="space-y-3">
                <Card className="p-6">
                  <h4 className="font-semibold mb-4 flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-primary" />
                    Recommended Prompt Variations
                  </h4>
                  <div className="space-y-2">
                    {recommendations.prompts.map((prompt: string, idx: number) => (
                      <div key={idx} className="p-3 rounded-lg border border-border hover:bg-accent/50 transition-colors">
                        <p className="font-mono text-sm">{prompt}</p>
                      </div>
                    ))}
                  </div>
                </Card>
              </TabsContent>

              {/* Competitive Positioning */}
              <TabsContent value="competitive" className="space-y-3">
                <Card className="p-6">
                  <h4 className="font-semibold mb-4 flex items-center gap-2">
                    <Target className="h-4 w-4 text-primary" />
                    Competitive Positioning Advice
                  </h4>
                  <div className="space-y-3">
                    {recommendations.competitive.map((item: any, idx: number) => (
                      <div key={idx} className="p-4 rounded-lg border border-border">
                        <div className="flex items-start gap-3">
                          <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                            <Lightbulb className="h-5 w-5 text-primary" />
                          </div>
                          <div className="flex-1">
                            <p className="font-medium mb-1">{item.insight}</p>
                            <Badge variant={item.impact === "high" ? "default" : "outline"}>
                              {item.impact} impact
                            </Badge>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              </TabsContent>

              {/* Action Plan */}
              <TabsContent value="actions" className="space-y-3">
                <Card className="p-6">
                  <h4 className="font-semibold mb-4 flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-success" />
                    Recommended Action Plan
                  </h4>
                  <div className="space-y-3">
                    {recommendations.actions.map((item: any, idx: number) => (
                      <div key={idx} className="p-4 rounded-lg border border-border hover:bg-accent/50 transition-colors">
                        <div className="flex items-start gap-4">
                          <div className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold flex-shrink-0">
                            {item.priority}
                          </div>
                          <div className="flex-1">
                            <p className="font-medium">{item.action}</p>
                          </div>
                          <TrendingUp className="h-5 w-5 text-success" />
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              </TabsContent>
            </Tabs>
          )}

          {recommendations && (
            <div className="flex gap-3">
              <Button variant="outline" onClick={() => setRecommendations(null)} className="flex-1">
                Regenerate
              </Button>
              <Button className="gradient-primary flex-1" onClick={() => {
                toast({
                  title: "Recommendations Saved",
                  description: "Optimization plan has been saved to your workspace.",
                });
                onOpenChange(false);
              }}>
                Save & Apply
              </Button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};
