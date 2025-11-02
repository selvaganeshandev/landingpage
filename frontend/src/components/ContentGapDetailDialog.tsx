import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card } from "@/components/ui/card";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { 
  Target, 
  TrendingUp, 
  Lightbulb, 
  CheckCircle2,
  AlertCircle,
  FileText,
  Users,
  Search
} from "lucide-react";

interface ContentGapDetailDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  gap: {
    id: number;
    question: string;
    frequency: number;
    currentCoverage: number;
    priority: string;
    platforms: string[];
    competitorMentions: Array<{ brand: string; share: number }>;
    recommendation: string;
  } | null;
}

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

const trendData = [
  { month: "Jun", mentions: 98, coverage: 28 },
  { month: "Jul", mentions: 105, coverage: 30 },
  { month: "Aug", mentions: 115, coverage: 32 },
  { month: "Sep", mentions: 120, coverage: 33 },
  { month: "Oct", mentions: 122, coverage: 34 },
  { month: "Nov", mentions: 127, coverage: 35 },
];

const relatedQuestions = [
  { question: "What vegan protein has the most complete amino acids?", frequency: 45 },
  { question: "How much protein do I need for muscle building?", frequency: 38 },
  { question: "Best time to take vegan protein powder?", frequency: 34 },
  { question: "Can vegan protein replace whey for bodybuilding?", frequency: 29 },
  { question: "What are BCAAs in vegan protein?", frequency: 22 },
];

const contentRecommendations = [
  {
    type: "Comprehensive Guide",
    title: "Complete Guide to Muscle Building with Plant Protein",
    sections: [
      "Science of muscle protein synthesis",
      "Amino acid profile comparison",
      "Optimal timing and dosage",
      "Sample meal plans and recipes",
      "Workout nutrition strategies",
      "Success stories and case studies"
    ],
    estimatedWords: "2500-3000",
    impact: "high"
  },
  {
    type: "Video Content",
    title: "Plant Protein vs Whey: What Science Says",
    sections: [
      "Side-by-side nutritional comparison",
      "Absorption rate analysis",
      "Expert interviews (nutritionists)",
      "Real athlete testimonials",
      "Q&A segment"
    ],
    estimatedWords: "Script: 1200-1500",
    impact: "high"
  },
  {
    type: "Interactive Tool",
    title: "Vegan Protein Calculator",
    sections: [
      "Personal protein requirement calculator",
      "Meal planning tool",
      "Supplement timing optimizer",
      "Progress tracker"
    ],
    estimatedWords: "Support content: 800-1000",
    impact: "medium"
  }
];

const seoSuggestions = [
  { suggestion: "Target long-tail keyword: 'best vegan protein powder for muscle building beginners'", priority: "high" },
  { suggestion: "Add FAQ schema markup for 'How much protein for muscle building'", priority: "high" },
  { suggestion: "Create pillar page linking to related muscle building content", priority: "medium" },
  { suggestion: "Optimize images with alt text including 'vegan muscle building'", priority: "medium" },
  { suggestion: "Build internal links from product pages to educational content", priority: "low" },
];

const actionPlan = [
  { step: "Research and outline comprehensive guide", timeline: "Week 1", owner: "Content Team" },
  { step: "Interview nutritionists and athletes", timeline: "Week 2", owner: "Video Team" },
  { step: "Write and design main guide", timeline: "Week 3-4", owner: "Content Team" },
  { step: "Develop interactive calculator", timeline: "Week 4-5", owner: "Dev Team" },
  { step: "Produce and edit video content", timeline: "Week 5-6", owner: "Video Team" },
  { step: "SEO optimization and internal linking", timeline: "Week 6", owner: "SEO Team" },
  { step: "Launch and promote content", timeline: "Week 7", owner: "Marketing Team" },
];

export const ContentGapDetailDialog = ({ open, onOpenChange, gap }: ContentGapDetailDialogProps) => {
  if (!gap) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-outfit text-2xl flex items-center gap-2">
            <Target className="h-6 w-6 text-primary" />
            Content Gap Analysis
          </DialogTitle>
          <DialogDescription className="text-base">
            {gap.question}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-4 gap-4">
            <Card className="p-4 border border-border">
              <div className="flex items-center justify-between mb-2">
                <Search className="h-5 w-5 text-muted-foreground" />
                <Badge className={getPriorityColor(gap.priority)}>
                  {gap.priority}
                </Badge>
              </div>
              <p className="text-2xl font-bold">{gap.frequency}</p>
              <p className="text-xs text-muted-foreground">Mentions/Month</p>
            </Card>

            <Card className="p-4 border border-border">
              <div className="flex items-center justify-between mb-2">
                <AlertCircle className="h-5 w-5 text-warning" />
              </div>
              <p className="text-2xl font-bold text-warning">{gap.currentCoverage}%</p>
              <p className="text-xs text-muted-foreground">Current Coverage</p>
            </Card>

            <Card className="p-4 border border-border">
              <div className="flex items-center justify-between mb-2">
                <TrendingUp className="h-5 w-5 text-success" />
              </div>
              <p className="text-2xl font-bold text-success">+23%</p>
              <p className="text-xs text-muted-foreground">Growth (6 mo)</p>
            </Card>

            <Card className="p-4 border border-border">
              <div className="flex items-center justify-between mb-2">
                <Users className="h-5 w-5 text-muted-foreground" />
              </div>
              <p className="text-2xl font-bold">{gap.platforms.length}</p>
              <p className="text-xs text-muted-foreground">AI Platforms</p>
            </Card>
          </div>

          <Tabs defaultValue="overview" className="space-y-6">
            <TabsList className="grid w-full grid-cols-6">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="competitors">Competitors</TabsTrigger>
              <TabsTrigger value="related">Related</TabsTrigger>
              <TabsTrigger value="content">Content Ideas</TabsTrigger>
              <TabsTrigger value="seo">SEO</TabsTrigger>
              <TabsTrigger value="action">Action Plan</TabsTrigger>
            </TabsList>

            {/* Overview */}
            <TabsContent value="overview" className="space-y-4">
              <div className="grid grid-cols-2 gap-6">
                <Card className="p-6 border border-border">
                  <h4 className="font-semibold mb-4">Mention Trend</h4>
                  <ResponsiveContainer width="100%" height={250}>
                    <LineChart data={trendData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="month" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                      <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "hsl(var(--card))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "var(--radius)",
                        }}
                      />
                      <Line 
                        type="monotone" 
                        dataKey="mentions" 
                        stroke="hsl(var(--primary))" 
                        strokeWidth={3}
                        name="Monthly Mentions"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </Card>

                <Card className="p-6 border border-border">
                  <h4 className="font-semibold mb-4">Coverage Trend</h4>
                  <ResponsiveContainer width="100%" height={250}>
                    <LineChart data={trendData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="month" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                      <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "hsl(var(--card))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "var(--radius)",
                        }}
                      />
                      <Line 
                        type="monotone" 
                        dataKey="coverage" 
                        stroke="hsl(var(--warning))" 
                        strokeWidth={3}
                        name="Coverage %"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </Card>
              </div>

              <Card className="p-6 border border-border">
                <h4 className="font-semibold mb-4">Platform Distribution</h4>
                <div className="space-y-3">
                  {gap.platforms.map((platform) => (
                    <div key={platform} className="flex items-center justify-between">
                      <Badge variant="outline">{platform}</Badge>
                      <span className="text-sm text-muted-foreground">Active</span>
                    </div>
                  ))}
                </div>
              </Card>

              <Card className="p-6 bg-gradient-to-br from-primary/5 to-secondary/5 border-primary/20">
                <div className="flex items-start gap-3">
                  <Lightbulb className="h-6 w-6 text-primary flex-shrink-0 mt-1" />
                  <div>
                    <h4 className="font-semibold mb-2">AI Recommendation</h4>
                    <p className="text-sm text-muted-foreground">{gap.recommendation}</p>
                  </div>
                </div>
              </Card>
            </TabsContent>

            {/* Competitors */}
            <TabsContent value="competitors" className="space-y-4">
              <Card className="p-6 border border-border">
                <h4 className="font-semibold mb-4">Competitor Share of Voice</h4>
                <div className="space-y-4">
                  {gap.competitorMentions.map((comp) => (
                    <div key={comp.brand}>
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium">{comp.brand}</span>
                        <span className="text-2xl font-bold" style={{ 
                          color: comp.brand === "VegFit Pro" ? "hsl(var(--primary))" : "inherit" 
                        }}>
                          {comp.share}%
                        </span>
                      </div>
                      <Progress value={comp.share} className="h-3" />
                    </div>
                  ))}
                </div>
              </Card>

              <Card className="p-6 border border-border">
                <h4 className="font-semibold mb-4">Opportunity Analysis</h4>
                <div className="space-y-4">
                  <div className="p-4 rounded-lg bg-warning/10 border border-warning/20">
                    <p className="font-medium text-warning mb-2">Gap Opportunity</p>
                    <p className="text-sm text-muted-foreground">
                      With {100 - gap.currentCoverage}% uncovered mentions, there's significant opportunity 
                      to capture market share from competitors by creating authoritative content.
                    </p>
                  </div>
                  <div className="p-4 rounded-lg bg-success/10 border border-success/20">
                    <p className="font-medium text-success mb-2">Estimated Impact</p>
                    <p className="text-sm text-muted-foreground">
                      Addressing this gap could increase your monthly mentions by 35-45 and improve 
                      visibility score by 15-20 percentage points.
                    </p>
                  </div>
                </div>
              </Card>
            </TabsContent>

            {/* Related Questions */}
            <TabsContent value="related" className="space-y-4">
              <Card className="p-6 border border-border">
                <h4 className="font-semibold mb-4">Related Questions ({relatedQuestions.length})</h4>
                <div className="space-y-3">
                  {relatedQuestions.map((q, idx) => (
                    <div key={idx} className="p-4 rounded-lg border border-border hover:bg-accent/50 transition-colors">
                      <div className="flex items-start justify-between mb-2">
                        <p className="font-medium flex-1">{q.question}</p>
                        <Badge variant="secondary">{q.frequency} mentions</Badge>
                      </div>
                      <Progress value={(q.frequency / relatedQuestions[0].frequency) * 100} className="h-1.5" />
                    </div>
                  ))}
                </div>
              </Card>

              <Card className="p-6 bg-muted/30">
                <p className="text-sm">
                  <strong>💡 Pro Tip:</strong> Creating content that addresses the main question plus 
                  these related queries will maximize your content's impact and improve overall topic authority.
                </p>
              </Card>
            </TabsContent>

            {/* Content Recommendations */}
            <TabsContent value="content" className="space-y-4">
              {contentRecommendations.map((rec, idx) => (
                <Card key={idx} className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <Badge variant="outline" className="mb-2">{rec.type}</Badge>
                      <h4 className="font-semibold text-lg">{rec.title}</h4>
                    </div>
                    <Badge className={rec.impact === "high" ? "bg-success" : ""}>{rec.impact} impact</Badge>
                  </div>
                  
                  <div className="space-y-3">
                    <div>
                      <p className="text-sm font-medium text-muted-foreground mb-2">Recommended Sections:</p>
                      <ul className="space-y-1">
                        {rec.sections.map((section, i) => (
                          <li key={i} className="text-sm flex items-start gap-2">
                            <CheckCircle2 className="h-4 w-4 text-success mt-0.5 flex-shrink-0" />
                            <span>{section}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div className="pt-3 border-t border-border">
                      <p className="text-xs text-muted-foreground">
                        <strong>Estimated Length:</strong> {rec.estimatedWords} words
                      </p>
                    </div>
                  </div>
                </Card>
              ))}
            </TabsContent>

            {/* SEO Suggestions */}
            <TabsContent value="seo" className="space-y-4">
              <Card className="p-6 border border-border">
                <h4 className="font-semibold mb-4">SEO Optimization Checklist</h4>
                <div className="space-y-3">
                  {seoSuggestions.map((sug, idx) => (
                    <div key={idx} className="p-4 rounded-lg border border-border">
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-3 flex-1">
                          <CheckCircle2 className="h-5 w-5 text-muted-foreground mt-0.5" />
                          <p className="text-sm">{sug.suggestion}</p>
                        </div>
                        <Badge 
                          variant={sug.priority === "high" ? "destructive" : "secondary"}
                          className="ml-4"
                        >
                          {sug.priority}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </TabsContent>

            {/* Action Plan */}
            <TabsContent value="action" className="space-y-4">
              <Card className="p-6 border border-border">
                <h4 className="font-semibold mb-4">7-Week Implementation Plan</h4>
                <div className="space-y-3">
                  {actionPlan.map((action, idx) => (
                    <div key={idx} className="p-4 rounded-lg border border-border hover:bg-accent/50 transition-colors">
                      <div className="flex items-start gap-4">
                        <div className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold flex-shrink-0">
                          {idx + 1}
                        </div>
                        <div className="flex-1">
                          <p className="font-medium mb-1">{action.step}</p>
                          <div className="flex items-center gap-4 text-sm text-muted-foreground">
                            <span>{action.timeline}</span>
                            <span>•</span>
                            <span>{action.owner}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>

              <Card className="p-6 bg-gradient-to-br from-success/5 to-success/10 border-success/20">
                <div className="flex items-start gap-3">
                  <Target className="h-6 w-6 text-success flex-shrink-0" />
                  <div>
                    <h4 className="font-semibold mb-2 text-success">Expected Outcomes</h4>
                    <ul className="space-y-2 text-sm">
                      <li className="flex items-start gap-2">
                        <span className="text-success">•</span>
                        <span>Increase coverage from {gap.currentCoverage}% to 75%+ within 3 months</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-success">•</span>
                        <span>Capture additional 40-50 monthly mentions</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-success">•</span>
                        <span>Establish authority on muscle building + plant protein topic</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-success">•</span>
                        <span>Improve overall brand visibility score by 12-15%</span>
                      </li>
                    </ul>
                  </div>
                </div>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </DialogContent>
    </Dialog>
  );
};
