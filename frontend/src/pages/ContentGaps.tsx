import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { useToast } from "@/hooks/use-toast";
import { useContentGeneration } from "@/hooks/useContentGeneration";
import { 
  Target,
  Sparkles,
  Search,
  TrendingUp,
  FileText,
  Lightbulb,
  AlertCircle,
  CheckCircle2
} from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { ContentGapDetailDialog } from "@/components/ContentGapDetailDialog";

const contentGaps = [
  {
    id: 1,
    question: "What's the best vegan protein powder for building muscle?",
    frequency: 127,
    currentCoverage: 35,
    priority: "high",
    platforms: ["ChatGPT", "Claude", "Perplexity"],
    competitorMentions: [
      { brand: "MyProtein", share: 42 },
      { brand: "Naked Nutrition", share: 38 },
      { brand: "VegFit Pro", share: 20 },
    ],
    recommendation: "Create detailed guide on muscle building with plant protein, including amino acid profiles and workout nutrition timing"
  },
  {
    id: 2,
    question: "Is vegan protein powder good for weight loss?",
    frequency: 98,
    currentCoverage: 28,
    priority: "high",
    platforms: ["ChatGPT", "Gemini"],
    competitorMentions: [
      { brand: "Naked Nutrition", share: 45 },
      { brand: "MyProtein", share: 32 },
      { brand: "VegFit Pro", share: 23 },
    ],
    recommendation: "Publish weight loss guide featuring calorie content, satiety benefits, and success stories"
  },
  {
    id: 3,
    question: "How does vegan protein compare to whey protein?",
    frequency: 156,
    currentCoverage: 52,
    priority: "medium",
    platforms: ["ChatGPT", "Claude", "Perplexity", "Gemini"],
    competitorMentions: [
      { brand: "VegFit Pro", share: 52 },
      { brand: "MyProtein", share: 30 },
      { brand: "Naked Nutrition", share: 18 },
    ],
    recommendation: "Expand existing content with more scientific studies and side-by-side nutritional comparisons"
  },
  {
    id: 4,
    question: "What are the best vegan protein sources besides powder?",
    frequency: 84,
    currentCoverage: 15,
    priority: "high",
    platforms: ["Claude", "Perplexity"],
    competitorMentions: [
      { brand: "Naked Nutrition", share: 38 },
      { brand: "MyProtein", share: 35 },
      { brand: "VegFit Pro", share: 27 },
    ],
    recommendation: "Create comprehensive guide on whole food protein sources to complement powder usage"
  },
  {
    id: 5,
    question: "Can you build muscle on a vegan diet?",
    frequency: 112,
    currentCoverage: 42,
    priority: "medium",
    platforms: ["ChatGPT", "Claude"],
    competitorMentions: [
      { brand: "VegFit Pro", share: 42 },
      { brand: "MyProtein", share: 35 },
      { brand: "Naked Nutrition", share: 23 },
    ],
    recommendation: "Update content with recent athlete success stories and new research"
  },
];

const optimizationSuggestions = [
  {
    page: "Product Page - VegFit Pro Original",
    currentScore: 72,
    improvements: [
      "Add FAQ section addressing 'muscle building' queries",
      "Include customer testimonials for weight loss",
      "Add comparison table vs whey protein",
      "Optimize meta description with 'best vegan protein' keyword"
    ],
    estimatedImpact: "+15% visibility"
  },
  {
    page: "Blog - Benefits of Plant Protein",
    currentScore: 68,
    improvements: [
      "Update with 2024 scientific studies",
      "Add structured data markup for FAQ",
      "Include athlete success stories",
      "Expand section on amino acid profiles"
    ],
    estimatedImpact: "+12% visibility"
  },
  {
    page: "Guide - Vegan Nutrition for Athletes",
    currentScore: 58,
    improvements: [
      "Add more specific workout nutrition timing",
      "Include meal planning templates",
      "Add video content transcripts",
      "Optimize for voice search queries"
    ],
    estimatedImpact: "+18% visibility"
  },
];

const topicClusters = [
  {
    topic: "Muscle Building",
    keywords: 12,
    coverage: 45,
    opportunity: "high",
    suggestedContent: ["Beginner muscle building guide", "Advanced athlete protocols", "Recovery nutrition"]
  },
  {
    topic: "Weight Loss",
    keywords: 8,
    coverage: 32,
    opportunity: "high",
    suggestedContent: ["Calorie-focused meal plans", "Appetite control guide", "Success case studies"]
  },
  {
    topic: "Comparison Content",
    keywords: 15,
    coverage: 68,
    opportunity: "medium",
    suggestedContent: ["Plant vs animal protein science", "Brand comparison matrix", "Cost analysis"]
  },
  {
    topic: "Ingredient Quality",
    keywords: 10,
    coverage: 78,
    opportunity: "low",
    suggestedContent: ["Sourcing transparency page", "Third-party testing results"]
  },
];

const getPriorityColor = (priority: string) => {
  switch (priority) {
    case "high":
      return "bg-destructive text-destructive-foreground";
    case "medium":
      return "bg-warning text-warning-foreground";
    case "low":
      return "bg-success text-success-foreground";
    default:
      return "bg-muted";
  }
};

const ContentGaps = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { navigateToContentGeneration } = useContentGeneration();
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [selectedGap, setSelectedGap] = useState<typeof contentGaps[0] | null>(null);

  const handleGenerateContentPlan = () => {
    navigateToContentGeneration({
      source: "Content Gap Analysis",
      priority: "high"
    });
  };

  const handleGenerateContentBrief = (gap: typeof contentGaps[0]) => {
    navigateToContentGeneration({
      topic: gap.question,
      keywords: gap.question.toLowerCase().split(' '),
      source: "Content Gap - " + gap.question,
      priority: gap.priority as any,
      articleType: "guide"
    });
  };

  const handleViewDetails = (gap: typeof contentGaps[0]) => {
    setSelectedGap(gap);
    setDetailDialogOpen(true);
  };

  return (
    <div className="p-8 space-y-8 bg-background">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Content Gap Analysis</h1>
          <p className="text-muted-foreground mt-2">
            Discover untapped opportunities and AI-powered recommendations
          </p>
        </div>
        <Button onClick={handleGenerateContentPlan} className="gradient-primary shadow-md shadow-primary/20">
          <FileText className="h-4 w-4 mr-2" />
          Generate Content Plan
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-muted-foreground font-medium">Total Gaps</p>
            <Target className="h-5 w-5 text-muted-foreground" />
          </div>
          <h3 className="text-3xl font-bold">24</h3>
          <p className="text-xs text-muted-foreground mt-1">Identified opportunities</p>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-muted-foreground font-medium">High Priority</p>
            <AlertCircle className="h-5 w-5 text-destructive" />
          </div>
          <h3 className="text-3xl font-bold text-destructive">9</h3>
          <p className="text-xs text-muted-foreground mt-1">Require immediate action</p>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-muted-foreground font-medium">Avg Coverage</p>
            <TrendingUp className="h-5 w-5 text-muted-foreground" />
          </div>
          <h3 className="text-3xl font-bold">34%</h3>
          <p className="text-xs text-muted-foreground mt-1">Across all gaps</p>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-muted-foreground font-medium">Est. Impact</p>
            <Sparkles className="h-5 w-5 text-primary" />
          </div>
          <h3 className="text-3xl font-bold text-primary">+28%</h3>
          <p className="text-xs text-muted-foreground mt-1">Potential visibility gain</p>
        </Card>
      </div>

      {/* Content Gaps List */}
      <Card className="p-6 border border-border">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold">Identified Content Gaps</h3>
          <div className="relative w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input placeholder="Search gaps..." className="pl-10" />
          </div>
        </div>

        <div className="space-y-4">
          {contentGaps.map((gap) => (
            <div key={gap.id} className="p-4 rounded-lg transition-all duration-300 border border-border hover:border-primary">
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <Badge className={getPriorityColor(gap.priority)}>
                      {gap.priority} priority
                    </Badge>
                    <span className="text-sm text-muted-foreground">
                      {gap.frequency} mentions/month
                    </span>
                  </div>
                  <h4 className="font-semibold text-lg mb-2">{gap.question}</h4>
                  <div className="flex flex-wrap gap-2 mb-3">
                    {gap.platforms.map((platform) => (
                      <Badge key={platform} variant="outline" className="text-xs">
                        {platform}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div className="text-right min-w-[100px]">
                  <p className="text-2xl font-bold text-primary">{gap.currentCoverage}%</p>
                  <p className="text-xs text-muted-foreground">current coverage</p>
                </div>
              </div>

              <div className="space-y-3">
                <div>
                  <p className="text-sm font-medium mb-2">Competitor Mentions:</p>
                  <div className="space-y-2">
                    {gap.competitorMentions.map((comp) => (
                      <div key={comp.brand} className="flex items-center justify-between">
                        <span className="text-sm">{comp.brand}</span>
                        <div className="flex items-center gap-2 flex-1 max-w-xs">
                          <Progress value={comp.share} className="h-2" />
                          <span className="text-xs font-medium min-w-[40px] text-right">
                            {comp.share}%
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="pt-2 border-t border-border">
                  <div className="flex items-start gap-2">
                    <Lightbulb className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-sm font-medium mb-1">AI Recommendation:</p>
                      <p className="text-sm text-muted-foreground">{gap.recommendation}</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex gap-2 mt-4 pt-3 border-t border-border">
                <Button size="sm" variant="default" onClick={() => handleGenerateContentBrief(gap)}>
                  <Sparkles className="h-3 w-3 mr-1" />
                  Generate Content
                </Button>
                <Button size="sm" variant="outline" onClick={() => handleViewDetails(gap)}>View Details</Button>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Page Optimization Suggestions */}
      <Card className="p-6 border border-border">
        <h3 className="text-lg font-semibold mb-6">Page Optimization Suggestions</h3>
        <div className="space-y-4">
          {optimizationSuggestions.map((suggestion, idx) => (
            <div key={idx} className="p-4 rounded-lg transition-all duration-300 border border-border hover:border-primary">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h4 className="font-semibold mb-1">{suggestion.page}</h4>
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-muted-foreground">Current Score: {suggestion.currentScore}/100</span>
                    <Badge variant="secondary" className="text-xs">
                      {suggestion.estimatedImpact}
                    </Badge>
                  </div>
                </div>
                <Progress value={suggestion.currentScore} className="w-24 h-2" />
              </div>
              
              <ul className="space-y-2">
                {suggestion.improvements.map((improvement, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    <CheckCircle2 className="h-4 w-4 text-success mt-0.5 flex-shrink-0" />
                    <span>{improvement}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </Card>

      {/* Topic Clusters */}
      <Card className="p-6 border border-border">
        <h3 className="text-lg font-semibold mb-6">Topic Cluster Analysis</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {topicClusters.map((cluster) => (
            <div key={cluster.topic} className="p-4 rounded-lg transition-all duration-300 border border-border hover:border-primary">
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-semibold">{cluster.topic}</h4>
                <Badge 
                  variant={cluster.opportunity === "high" ? "default" : "secondary"}
                  className={cluster.opportunity === "high" ? "bg-warning text-warning-foreground" : ""}
                >
                  {cluster.opportunity} opportunity
                </Badge>
              </div>
              
              <div className="space-y-2 mb-4">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">{cluster.keywords} keywords</span>
                  <span className="font-medium">{cluster.coverage}% coverage</span>
                </div>
                <Progress value={cluster.coverage} className="h-2" />
              </div>

              <div>
                <p className="text-xs font-medium text-muted-foreground mb-2">Suggested Content:</p>
                <div className="space-y-1">
                  {cluster.suggestedContent.map((content, idx) => (
                    <p key={idx} className="text-sm flex items-start gap-2">
                      <span className="text-primary">•</span>
                      <span>{content}</span>
                    </p>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Detail Dialog */}
      <ContentGapDetailDialog
        open={detailDialogOpen}
        onOpenChange={setDetailDialogOpen}
        gap={selectedGap}
      />
    </div>
  );
};

export default ContentGaps;
