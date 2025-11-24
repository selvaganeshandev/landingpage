import { useState, useEffect } from "react";
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
  Search,
  Loader2
} from "lucide-react";
import apiClient from "@/services/api";
import { useToast } from "@/hooks/use-toast";

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
  domainId: string | undefined;
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

export const ContentGapDetailDialog = ({ open, onOpenChange, gap, domainId }: ContentGapDetailDialogProps) => {
  const { toast } = useToast();
  const [detailData, setDetailData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!gap || !domainId || !open) {
      return;
    }

    const loadDetailData = async () => {
      setIsLoading(true);
      try {
        const data = await apiClient.getContentGapDetail(gap.id, { domain_id: domainId });
        setDetailData(data);
      } catch (error: any) {
        console.error('Failed to load content gap details:', error);
        toast({
          title: "Error",
          description: "Failed to load detailed analysis. Showing basic information.",
          variant: "destructive",
        });
        // Keep basic gap data even if detail fetch fails
      } finally {
        setIsLoading(false);
      }
    };

    loadDetailData();
  }, [gap, domainId, open, toast]);

  if (!gap) return null;

  // Use API data if available, otherwise fall back to gap data
  const relatedQuestions = detailData?.relatedQuestions || [];
  const competitorBreakdown = detailData?.competitorBreakdown || gap.competitorMentions;
  const estimatedImpact = detailData?.estimatedImpact || `+${Math.round((100 - gap.currentCoverage) * 0.3)}%`;
  const trendData = detailData?.trendData || [];
  const hasTrendData = trendData.length > 0;

  // Dynamic data from API
  const contentRecommendations = detailData?.contentRecommendations || [];
  const seoSuggestions = detailData?.seoSuggestions || [];
  const actionPlan = detailData?.actionPlan || [];
  const estimatedTimeline = detailData?.estimatedTimeline || '';
  const opportunityAnalysis = detailData?.opportunityAnalysis || null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-inter text-2xl flex items-center gap-2">
            <Target className="h-6 w-6 text-primary" />
            Content Gap Analysis
          </DialogTitle>
          <DialogDescription className="text-base">
            {gap.question}
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-16 space-y-4">
            <Loader2 className="h-12 w-12 text-primary animate-spin" />
            <p className="text-muted-foreground">Loading detailed analysis...</p>
          </div>
        ) : (
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
              <p className="text-2xl font-bold text-success">{estimatedImpact}</p>
              <p className="text-xs text-muted-foreground">Est. Impact</p>
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
              {hasTrendData ? (
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
              ) : (
                <Card className="p-6 border border-border">
                  <div className="flex flex-col items-center justify-center py-12 space-y-3">
                    <TrendingUp className="h-12 w-12 text-muted-foreground opacity-50" />
                    <p className="text-sm text-muted-foreground text-center">
                      No historical trend data available yet.
                      <br />
                      Trends will appear as more data is collected over time.
                    </p>
                  </div>
                </Card>
              )}

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
                  {competitorBreakdown && competitorBreakdown.length > 0 ? (
                    competitorBreakdown.map((comp: any) => (
                      <div key={comp.brand}>
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-medium">{comp.brand}</span>
                          <span className="text-2xl font-bold">
                            {comp.share}%
                          </span>
                        </div>
                        <Progress value={comp.share} className="h-3" />
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-muted-foreground">No competitor data available</p>
                  )}
                </div>
              </Card>

              <Card className="p-6 border border-border">
                <h4 className="font-semibold mb-4">Opportunity Analysis</h4>
                <div className="space-y-4">
                  <div className="p-4 rounded-lg bg-warning/10 border border-warning/20">
                    <p className="font-medium text-warning mb-2">Gap Opportunity</p>
                    <p className="text-sm text-muted-foreground">
                      {opportunityAnalysis?.gapOpportunity || `With ${100 - gap.currentCoverage}% uncovered mentions, there's significant opportunity to capture market share from competitors by creating authoritative content.`}
                    </p>
                  </div>
                  <div className="p-4 rounded-lg bg-success/10 border border-success/20">
                    <p className="font-medium text-success mb-2">Estimated Impact</p>
                    <p className="text-sm text-muted-foreground">
                      {opportunityAnalysis?.estimatedImpact || "Addressing this gap could increase your monthly mentions and improve visibility score."}
                    </p>
                  </div>
                  {opportunityAnalysis?.urgency && (
                    <div className="p-4 rounded-lg bg-primary/10 border border-primary/20">
                      <p className="font-medium text-primary mb-2">Priority Assessment</p>
                      <p className="text-sm text-muted-foreground">
                        {opportunityAnalysis.urgency}
                      </p>
                    </div>
                  )}
                </div>
              </Card>
            </TabsContent>

            {/* Related Questions */}
            <TabsContent value="related" className="space-y-4">
              <Card className="p-6 border border-border">
                <h4 className="font-semibold mb-4">Related Questions ({relatedQuestions.length})</h4>
                <div className="space-y-3">
                  {relatedQuestions.length > 0 ? (
                    relatedQuestions.map((q: any, idx: number) => (
                      <div key={idx} className="p-4 rounded-lg border border-border hover:bg-accent/50 transition-colors">
                        <div className="flex items-start justify-between mb-2">
                          <p className="font-medium flex-1">{q.question}</p>
                          <Badge variant="secondary">{q.frequency} mentions</Badge>
                        </div>
                        <Progress value={(q.frequency / (relatedQuestions[0]?.frequency || 1)) * 100} className="h-1.5" />
                      </div>
                    ))
                  ) : (
                    <div className="flex flex-col items-center justify-center py-8 space-y-2">
                      <Search className="h-12 w-12 text-muted-foreground opacity-50" />
                      <p className="text-sm text-muted-foreground">No related questions found</p>
                    </div>
                  )}
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
              {contentRecommendations.length > 0 ? (
                contentRecommendations.map((rec: any, idx: number) => (
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
                          {rec.sections.map((section: string, i: number) => (
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
                ))
              ) : (
                <Card className="p-6 border border-border">
                  <div className="flex flex-col items-center justify-center py-12 space-y-3">
                    <Lightbulb className="h-12 w-12 text-muted-foreground opacity-50" />
                    <p className="text-sm text-muted-foreground text-center">
                      No content recommendations available
                    </p>
                  </div>
                </Card>
              )}
            </TabsContent>

            {/* SEO Suggestions */}
            <TabsContent value="seo" className="space-y-4">
              {seoSuggestions.length > 0 ? (
                <Card className="p-6 border border-border">
                  <h4 className="font-semibold mb-4">SEO Optimization Checklist</h4>
                  <div className="space-y-3">
                    {seoSuggestions.map((sug: any, idx: number) => (
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
              ) : (
                <Card className="p-6 border border-border">
                  <div className="flex flex-col items-center justify-center py-12 space-y-3">
                    <Search className="h-12 w-12 text-muted-foreground opacity-50" />
                    <p className="text-sm text-muted-foreground text-center">
                      No SEO suggestions available
                    </p>
                  </div>
                </Card>
              )}
            </TabsContent>

            {/* Action Plan */}
            <TabsContent value="action" className="space-y-4">
              {actionPlan.length > 0 ? (
                <>
                  <Card className="p-6 border border-border">
                    <h4 className="font-semibold mb-4">
                      {estimatedTimeline ? `${estimatedTimeline} Implementation Plan` : 'Implementation Plan'}
                    </h4>
                    <div className="space-y-3">
                      {actionPlan.map((action: any, idx: number) => (
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
                            <span>Increase coverage from {gap.currentCoverage}% to 75%+</span>
                          </li>
                          <li className="flex items-start gap-2">
                            <span className="text-success">•</span>
                            <span>Capture significant share of {100 - gap.currentCoverage}% uncovered mentions</span>
                          </li>
                          <li className="flex items-start gap-2">
                            <span className="text-success">•</span>
                            <span>Establish authority on '{gap.question}' topic</span>
                          </li>
                          <li className="flex items-start gap-2">
                            <span className="text-success">•</span>
                            <span>Improve overall brand visibility and search rankings</span>
                          </li>
                        </ul>
                      </div>
                    </div>
                  </Card>
                </>
              ) : (
                <Card className="p-6 border border-border">
                  <div className="flex flex-col items-center justify-center py-12 space-y-3">
                    <Target className="h-12 w-12 text-muted-foreground opacity-50" />
                    <p className="text-sm text-muted-foreground text-center">
                      No action plan available
                    </p>
                  </div>
                </Card>
              )}
            </TabsContent>
          </Tabs>
        </div>
        )}
      </DialogContent>
    </Dialog>
  );
};
