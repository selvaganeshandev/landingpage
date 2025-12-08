import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useDomainStore } from "@/stores/domainStore";
import apiClient from "@/services/api";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Card } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import {
  FileText,
  Book,
  GitCompare,
  List,
  Wrench,
  Sparkles,
  Calendar,
  Target,
  CheckCircle2,
  ArrowRight
} from "lucide-react";

interface GenerateContentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  existingContent?: any;
}

export const GenerateContentDialog = ({
  open,
  onOpenChange,
  existingContent
}: GenerateContentDialogProps) => {
  const { toast } = useToast();
  const navigate = useNavigate();
  const { selectedDomain } = useDomainStore();
  const [step, setStep] = useState(1);
  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [generatedContent, setGeneratedContent] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [showSuccess, setShowSuccess] = useState(false);
  
  const [formData, setFormData] = useState({
    articleType: existingContent?.type || "blog",
    title: existingContent?.title || "",
    keywords: existingContent?.targetKeywords?.join(", ") || "",
    tone: "professional",
    style: "informative",
    goal: "educate",
    audience: "general",
    depth: "comprehensive",
    wordCount: existingContent?.wordCount || 1500,
    scheduledDate: existingContent?.scheduledDate || new Date(),
  });

  // Reset state when dialog closes, initialize when it opens
  useEffect(() => {
    if (!open) {
      // Dialog closed - reset everything for next time
      setStep(1);
      setProgress(0);
      setIsGenerating(false);
      setError(null);
      setShowSuccess(false);
      setGeneratedContent(null);
    }
  }, [open]);

  // Update form data when existingContent changes (on dialog open)
  useEffect(() => {
    if (existingContent && open && !showSuccess) {
      setFormData({
        articleType: existingContent?.type || "blog",
        title: existingContent?.title || "",
        keywords: Array.isArray(existingContent?.targetKeywords)
          ? existingContent.targetKeywords.join(", ")
          : (existingContent?.targetKeywords || ""),
        tone: "professional",
        style: "informative",
        goal: "educate",
        audience: "general",
        depth: "comprehensive",
        wordCount: existingContent?.wordCount || 1500,
        scheduledDate: existingContent?.scheduledDate || new Date(),
      });
    }
  }, [existingContent, open, showSuccess]);

  const articleTypes = [
    {
      id: "blog",
      icon: FileText,
      title: "Blog Post",
      description: "General informational content for your blog",
      examples: ["Industry insights", "Company updates", "Educational content"]
    },
    {
      id: "guide",
      icon: Book,
      title: "How-to Guide",
      description: "Step-by-step instructional content",
      examples: ["Tutorials", "DIY guides", "Process explanations"]
    },
    {
      id: "comparison",
      icon: GitCompare,
      title: "Comparison Article",
      description: "Side-by-side analysis of multiple options",
      examples: ["A vs B articles", "Best alternatives", "Feature comparisons"]
    },
    {
      id: "listicle",
      icon: List,
      title: "Listicle",
      description: "List-based content with numbered or bulleted items",
      examples: ["Top 10 lists", "Best practices", "Resource roundups"]
    },
    {
      id: "technical",
      icon: Wrench,
      title: "Technical Article",
      description: "In-depth technical documentation or analysis",
      examples: ["API documentation", "Technical deep-dives", "Implementation guides"]
    }
  ];

  const handleGenerate = async () => {
    if (!selectedDomain) {
      toast({
        title: "Error",
        description: "Please select a domain first",
        variant: "destructive",
      });
      return;
    }

    setIsGenerating(true);
    setProgress(0);
    setError(null);
    setGeneratedContent(null);

    // Simulate progress for UX
    const progressInterval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 90) {
          clearInterval(progressInterval);
          return 90;
        }
        return prev + 5;
      });
    }, 1000);

    try {
      // Use enriched source reference if already built, otherwise use default
      const sourceReference = existingContent?.sourceReference || formData.title;

      // Prepare generation request
      const generationData = {
        domain_id: selectedDomain.id,
        title: formData.title,
        keywords: formData.keywords,
        article_type: formData.articleType,
        tone: formData.tone,
        style: formData.style,
        goal: formData.goal,
        audience: formData.audience,
        depth: formData.depth,
        word_count: formData.wordCount,
        source_type: existingContent?.sourceType || 'manual',
        source_id: existingContent?.sourceId,
        source_reference: sourceReference,
        priority: existingContent?.priority || 'medium',
        scheduled_date: formData.scheduledDate instanceof Date
          ? formData.scheduledDate.toISOString().split('T')[0]  // Convert to YYYY-MM-DD format
          : formData.scheduledDate
      };

      // Log the data being sent for debugging
      console.log('Content generation request:', generationData);

      // Call the API to generate content
      const response = await apiClient.generateContent(generationData);

      clearInterval(progressInterval);
      setProgress(100);

      if (response.status === 'success') {
        setGeneratedContent(response.data);
        setIsGenerating(false);
        setShowSuccess(true);

        toast({
          title: "Content Generated Successfully!",
          description: `Generated ${response.data.actual_word_count} words in ${response.data.generation_time_seconds}s`,
        });
      } else {
        throw new Error(response.message || 'Generation failed');
      }

    } catch (err: any) {
      clearInterval(progressInterval);
      setIsGenerating(false);
      setProgress(0);

      console.error('Content generation error:', err);
      const errorMessage = err.message || 'Failed to generate content. Please try again.';
      setError(errorMessage);

      toast({
        title: "Generation Failed",
        description: errorMessage,
        variant: "destructive",
      });
    }
  };

  const renderStepContent = () => {
    switch (step) {
      case 1:
        return (
          <div className="space-y-4">
            <div className="pb-4 border-b border-border">
              <h3 className="text-lg font-semibold mb-1">Choose an Article Type</h3>
              <p className="text-sm text-muted-foreground">
                Choose the type of article you want to create
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {articleTypes.map((type) => {
                const Icon = type.icon;
                const isSelected = formData.articleType === type.id;
                
                return (
                  <Card
                    key={type.id}
                    className={`p-3 cursor-pointer transition-all hover:shadow-md ${
                      isSelected ? 'ring-2 ring-primary' : ''
                    }`}
                    onClick={() => setFormData({ ...formData, articleType: type.id })}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg gradient-primary flex items-center justify-center flex-shrink-0">
                        <Icon className="h-5 w-5 text-white" />
                      </div>
                      <div className="flex-1">
                        <h4 className="font-semibold text-sm mb-0.5">{type.title}</h4>
                        <p className="text-xs text-muted-foreground">
                          {type.description}
                        </p>
                      </div>
                    </div>
                  </Card>
                );
              })}
            </div>
          </div>
        );

      case 2:
        return (
          <div className="space-y-6">
            <div className="pb-4 border-b border-border">
              <h3 className="text-lg font-semibold mb-1">Article Details</h3>
              <p className="text-sm text-muted-foreground">
                Provide title and target keywords
              </p>
            </div>

            <div className="space-y-4">
              <div>
                <Label>Article Title</Label>
                <Input
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="Best Plant-Based Protein Powders for Athletes"
                />
              </div>

              <div>
                <Label>Target Keywords (comma-separated)</Label>
                <Textarea
                  value={formData.keywords}
                  onChange={(e) => setFormData({ ...formData, keywords: e.target.value })}
                  placeholder="plant protein, vegan protein powder, athlete supplements"
                  rows={3}
                />
                <p className="text-xs text-muted-foreground mt-1">
                  These keywords will be naturally integrated into your content
                </p>
              </div>
            </div>
          </div>
        );

      case 3:
        return (
          <div className="space-y-6">
            <div className="pb-4 border-b border-border">
              <h3 className="text-lg font-semibold mb-1">Content Settings</h3>
              <p className="text-sm text-muted-foreground">
                Configure your article generation preferences
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Tone</Label>
                <Select value={formData.tone} onValueChange={(v) => setFormData({ ...formData, tone: v })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="professional">Professional</SelectItem>
                    <SelectItem value="casual">Casual</SelectItem>
                    <SelectItem value="friendly">Friendly</SelectItem>
                    <SelectItem value="authoritative">Authoritative</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label>Style</Label>
                <Select value={formData.style} onValueChange={(v) => setFormData({ ...formData, style: v })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="informative">Informative</SelectItem>
                    <SelectItem value="persuasive">Persuasive</SelectItem>
                    <SelectItem value="storytelling">Storytelling</SelectItem>
                    <SelectItem value="analytical">Analytical</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label>Goal</Label>
                <Select value={formData.goal} onValueChange={(v) => setFormData({ ...formData, goal: v })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="educate">Educate</SelectItem>
                    <SelectItem value="convert">Convert</SelectItem>
                    <SelectItem value="engage">Engage</SelectItem>
                    <SelectItem value="inform">Inform</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label>Target Audience</Label>
                <Select value={formData.audience} onValueChange={(v) => setFormData({ ...formData, audience: v })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="general">General</SelectItem>
                    <SelectItem value="beginners">Beginners</SelectItem>
                    <SelectItem value="professionals">Professionals</SelectItem>
                    <SelectItem value="experts">Experts</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label>Content Depth</Label>
                <Select value={formData.depth} onValueChange={(v) => setFormData({ ...formData, depth: v })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="overview">Overview</SelectItem>
                    <SelectItem value="detailed">Detailed</SelectItem>
                    <SelectItem value="comprehensive">Comprehensive</SelectItem>
                    <SelectItem value="extensive">Extensive</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label>Word Count</Label>
                <Select 
                  value={formData.wordCount.toString()} 
                  onValueChange={(v) => setFormData({ ...formData, wordCount: parseInt(v) })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="800">800-1,000 words</SelectItem>
                    <SelectItem value="1500">1,000-2,000 words</SelectItem>
                    <SelectItem value="2500">2,000-3,000 words</SelectItem>
                    <SelectItem value="3500">3,000+ words</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        );

      case 4:
        return (
          <div className="space-y-6">
            <div className="pb-4 border-b border-border">
              <h3 className="text-lg font-semibold mb-1">
                {showSuccess ? "Content Generated!" : "Review & Generate"}
              </h3>
              <p className="text-sm text-muted-foreground">
                {showSuccess
                  ? "Your content has been successfully generated"
                  : "Review your settings and generate content"}
              </p>
            </div>

            {showSuccess ? (
              <div className="py-8 space-y-6">
                <div className="flex items-center justify-center">
                  <div className="w-20 h-20 rounded-full bg-green-500/10 flex items-center justify-center">
                    <CheckCircle2 className="h-10 w-10 text-green-500" />
                  </div>
                </div>

                <div className="text-center space-y-3">
                  <h4 className="text-xl font-semibold">Content Successfully Generated!</h4>
                  <p className="text-muted-foreground max-w-md mx-auto">
                    Your content has been created and saved to your content library which can be found in{' '}
                    <strong>
                      {existingContent?.sourceType === 'content_gap' ? 'Content Gaps' :
                       existingContent?.sourceType === 'answer_gap' ? 'Competitor Analysis' :
                       existingContent?.sourceType === 'topic' ? 'Topics' :
                       'Content Calendar'}
                    </strong>
                  </p>
                </div>

                <div className="flex justify-center gap-3 pt-4">
                  <Button
                    onClick={() => {
                      onOpenChange(false);
                      // Navigate to content editor with the generated content ID
                      if (generatedContent?.id) {
                        navigate(`/content-editor/${generatedContent.id}`);
                      } else {
                        // Fallback: Navigate to the appropriate section based on source type
                        const sourceType = existingContent?.sourceType;
                        if (sourceType === 'content_gap') {
                          navigate('/content-gaps');
                        } else if (sourceType === 'answer_gap') {
                          navigate('/competitors');
                        } else if (sourceType === 'topic') {
                          navigate('/topics');
                        } else {
                          navigate('/content-calendar');
                        }
                      }
                    }}
                    className="gradient-primary"
                  >
                    <ArrowRight className="h-4 w-4 mr-2" />
                    View Content
                  </Button>
                  <Button
                    onClick={() => onOpenChange(false)}
                    variant="outline"
                  >
                    Close
                  </Button>
                </div>
              </div>
            ) : isGenerating ? (
              <div className="py-12 space-y-6">
                <div className="flex items-center justify-center">
                  <div className="w-20 h-20 rounded-full gradient-primary flex items-center justify-center animate-pulse">
                    <Sparkles className="h-10 w-10 text-white" />
                  </div>
                </div>
                <div className="space-y-3">
                  <p className="text-center font-medium">Generating your content...</p>
                  <Progress value={progress} className="h-2" />
                  <p className="text-center text-sm text-muted-foreground">{progress}% complete</p>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <Card className="p-5 border border-border bg-muted/30">
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <FileText className="h-5 w-5 text-primary" />
                      <h4 className="font-semibold">{formData.title || "Untitled Article"}</h4>
                    </div>
                    
                    <div className="flex flex-wrap gap-2">
                      <Badge variant="secondary">{formData.articleType}</Badge>
                      <Badge variant="outline">{formData.wordCount} words</Badge>
                      <Badge variant="outline">{formData.tone} tone</Badge>
                    </div>

                    <div className="grid grid-cols-2 gap-3 text-sm pt-3 border-t border border-border">
                      <div>
                        <p className="text-muted-foreground mb-1">Style & Goal</p>
                        <p className="font-medium capitalize">{formData.style} / {formData.goal}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground mb-1">Audience & Depth</p>
                        <p className="font-medium capitalize">{formData.audience} / {formData.depth}</p>
                      </div>
                      {formData.keywords && (
                        <div className="col-span-2">
                          <p className="text-muted-foreground mb-1">Keywords</p>
                          <p className="font-medium">{formData.keywords}</p>
                        </div>
                      )}
                    </div>
                  </div>
                </Card>

                <div className="bg-primary/5 border border-primary/20 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <Sparkles className="h-5 w-5 text-primary mt-0.5" />
                    <div className="text-sm">
                      <p className="font-medium mb-1">AI-Powered Generation</p>
                      <p className="text-muted-foreground">
                        Content will be optimized for AI visibility and designed to appear in relevant AI model responses.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-2xl">Content Generation Wizard</DialogTitle>
        </DialogHeader>

        {/* Wizard Step Indicator - Only show when not in success state */}
        {!showSuccess && (
          <div className="mb-6">
            <div className="flex items-center justify-center gap-3">
              {[1, 2, 3, 4].map((stepNumber) => (
                <div key={stepNumber} className="flex items-center">
                  <div className={`flex items-center justify-center w-10 h-10 rounded-full transition-all ${
                    stepNumber === step
                      ? 'bg-primary text-white shadow-md shadow-primary/30'
                      : stepNumber < step
                        ? 'bg-primary/20 text-primary'
                        : 'bg-muted text-muted-foreground'
                  }`}>
                    <span className="text-sm font-semibold">{stepNumber}</span>
                  </div>
                  {stepNumber < 4 && (
                    <div className={`w-16 h-0.5 mx-1 transition-all ${
                      stepNumber < step ? 'bg-primary' : 'bg-muted'
                    }`} />
                  )}
                </div>
              ))}
            </div>
            <div className="text-center mt-3">
              <p className="text-sm font-medium">
                {step === 1 && "Choose Article Type"}
                {step === 2 && "Article Details"}
                {step === 3 && "Content Settings"}
                {step === 4 && "Review & Generate"}
              </p>
            </div>
          </div>
        )}

        {renderStepContent()}

        {/* Navigation - Hide when showing success */}
        {!showSuccess && (
          <div className="flex items-center justify-between pt-6 border-t border-border">
            <Button
              variant="outline"
              onClick={() => step > 1 ? setStep(step - 1) : onOpenChange(false)}
              disabled={isGenerating}
            >
              {step === 1 ? "Cancel" : "Previous"}
            </Button>

            {step < 4 ? (
              <Button onClick={() => setStep(step + 1)} disabled={!formData.title && step === 2}>
                Next Step
              </Button>
            ) : (
              <Button
                onClick={handleGenerate}
                disabled={isGenerating}
                className="gradient-primary"
              >
                <Sparkles className="h-4 w-4 mr-2" />
                {isGenerating ? "Generating..." : "Generate Content"}
              </Button>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};
