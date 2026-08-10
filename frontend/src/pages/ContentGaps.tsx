import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { useToast } from "@/hooks/use-toast";
import {
  Target,
  Sparkles,
  Search,
  TrendingUp,
  Calendar,
  Lightbulb,
  AlertCircle,
  CheckCircle2
} from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { ContentGapDetailDialog } from "@/components/ContentGapDetailDialog";
import { GenerateContentDialog } from "@/components/GenerateContentDialog";
import { useDomainStore } from "@/stores/domainStore";
import { PageLoader } from "@/components/PageLoader";
import apiClient from "@/services/api";

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
  const { selectedDomain } = useDomainStore();

  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [generateDialogOpen, setGenerateDialogOpen] = useState(false);
  const [selectedGap, setSelectedGap] = useState<any | null>(null);
  const [selectedContentForGeneration, setSelectedContentForGeneration] = useState<any | null>(null);
  const [contentGaps, setContentGaps] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [totalCount, setTotalCount] = useState(0);

  const domainId = selectedDomain?.id?.toString();

  // Reset page when domain changes
  useEffect(() => {
    setCurrentPage(1);
  }, [domainId]);

  // Load summary data separately (only once)
  useEffect(() => {
    if (!domainId) {
      return;
    }

    const loadSummary = async () => {
      try {
        const summaryData = await apiClient.getContentGapSummary({ domain_id: domainId });
        setSummary(summaryData);
      } catch (error: any) {
        console.error('Failed to load content gap summary:', error);
      }
    };

    loadSummary();
  }, [domainId]);

  // Load paginated content gaps
  useEffect(() => {
    if (!domainId) {
      setIsLoading(false);
      return;
    }

    const loadGaps = async () => {
      setIsLoading(true);
      try {
        const gapsData = await apiClient.getContentGaps({
          domain_id: domainId,
          page: currentPage,
          page_size: '20'
        });

        // Handle paginated response
        const gaps = Array.isArray(gapsData) ? gapsData : gapsData?.results || [];
        const paginationInfo = !Array.isArray(gapsData) ? gapsData : null;

        setContentGaps(gaps);

        if (paginationInfo) {
          setTotalPages(paginationInfo.total_pages || 0);
          setTotalCount(paginationInfo.count || 0);
        }
      } catch (error: any) {
        console.error('Failed to load content gaps:', error);
        toast({
          title: "Error",
          description: "Failed to load content gap analysis. Please try again.",
          variant: "destructive",
        });
      } finally {
        setIsLoading(false);
      }
    };

    loadGaps();
  }, [domainId, currentPage, toast]);

  const handleGenerateContentPlan = () => {
    navigate('/content-calendar');
  };

  const handleGenerateContentBrief = async (gap: any) => {
    // First, fetch detailed gap data including Content Ideas, SEO, and Action Plan
    try {
      if (!domainId) {
        toast({
          title: "Error",
          description: "Please select a domain first",
          variant: "destructive",
        });
        return;
      }

      const detailData = await apiClient.getContentGapDetail(gap.id, {
        domain_id: domainId
      });

      // Use the question/title as the keyword
      let keywords = gap.question.replace(/[?]/g, '').trim();

      // Determine article type based on question or content recommendations
      let articleType = "guide";
      const questionLower = gap.question.toLowerCase();

      // Check content recommendations for article type
      if (detailData?.contentRecommendations && detailData.contentRecommendations.length > 0) {
        const firstRec = detailData.contentRecommendations[0];
        const typeMap: any = {
          'comprehensive guide': 'guide',
          'comparison article': 'comparison',
          'listicle': 'listicle',
          'blog post': 'blog',
          'technical article': 'technical'
        };
        articleType = typeMap[firstRec.type?.toLowerCase()] || articleType;
      } else {
        // Fallback to question-based detection
        if (questionLower.includes('vs') || questionLower.includes('versus') || questionLower.includes('or')) {
          articleType = "comparison";
        } else if (questionLower.includes('how to') || questionLower.includes('how do')) {
          articleType = "guide";
        } else if (questionLower.match(/best|top \d+|list of/)) {
          articleType = "listicle";
        } else if (questionLower.includes('what is') || questionLower.includes('definition')) {
          articleType = "blog";
        }
      }

      // Determine word count from content recommendations or priority
      let wordCount = 1500;
      if (detailData?.contentRecommendations && detailData.contentRecommendations.length > 0) {
        const firstRec = detailData.contentRecommendations[0];
        wordCount = parseInt(firstRec.estimatedWords) || wordCount;
      } else {
        if (gap.priority === 'high') {
          wordCount = gap.frequency > 50 ? 2500 : 2000;
        } else if (gap.priority === 'medium') {
          wordCount = 1500;
        } else {
          wordCount = 1200;
        }
      }

      // Build enriched source reference with all detailed information
      let enrichedReference = `Question: ${gap.question}\n\nAI Recommendation: ${gap.recommendation}`;

      // Add content recommendations
      if (detailData?.contentRecommendations && detailData.contentRecommendations.length > 0) {
        enrichedReference += '\n\n=== Content Structure Recommendations ===\n';
        detailData.contentRecommendations.forEach((rec: any, idx: number) => {
          enrichedReference += `\n${idx + 1}. ${rec.title} (${rec.type})\n`;
          enrichedReference += `   Sections to include:\n`;
          rec.sections.forEach((section: string) => {
            enrichedReference += `   - ${section}\n`;
          });
        });
      }

      // Add SEO suggestions
      if (detailData?.seoSuggestions && detailData.seoSuggestions.length > 0) {
        enrichedReference += '\n\n=== SEO Optimization Points ===\n';
        detailData.seoSuggestions.forEach((sug: any) => {
          enrichedReference += `- ${sug.suggestion}\n`;
        });
      }

      // Add competitor context
      enrichedReference += `\n\n=== Market Context ===\n`;
      enrichedReference += `Mention Frequency: ${gap.frequency} times across platforms\n`;
      if (gap.competitorMentions && gap.competitorMentions.length > 0) {
        enrichedReference += `Top Competitors:\n`;
        gap.competitorMentions.slice(0, 3).forEach((comp: any) => {
          enrichedReference += `- ${comp.brand}: ${comp.share}%\n`;
        });
      }

      // Set the content data for the dialog
      setSelectedContentForGeneration({
        title: gap.question,
        type: articleType,
        targetKeywords: [keywords],
        priority: gap.priority,
        wordCount: wordCount,
        sourceType: "content_gap",
        sourceId: gap.id,
        sourceReference: enrichedReference,
        // Additional context for better generation
        competitorMentions: gap.competitorMentions,
        recommendation: gap.recommendation,
        frequency: gap.frequency,
        platforms: gap.platforms,
        // Include detailed data
        contentRecommendations: detailData?.contentRecommendations,
        seoSuggestions: detailData?.seoSuggestions,
        actionPlan: detailData?.actionPlan
      });

      // Open the dialog
      setGenerateDialogOpen(true);

    } catch (error) {
      console.error('Error fetching gap details:', error);
      toast({
        title: "Warning",
        description: "Could not load detailed gap analysis. Using basic information.",
        variant: "default",
      });

      // Fallback to basic mode if API fails
      const keywords = gap.question.replace(/[?]/g, '').trim();

      setSelectedContentForGeneration({
        title: gap.question,
        type: "guide",
        targetKeywords: [keywords],
        priority: gap.priority,
        wordCount: 1500,
        sourceType: "content_gap",
        sourceId: gap.id,
        sourceReference: gap.question,
        competitorMentions: gap.competitorMentions,
        recommendation: gap.recommendation,
        frequency: gap.frequency,
        platforms: gap.platforms
      });

      setGenerateDialogOpen(true);
    }
  };

  const handleViewDetails = (gap: any) => {
    setSelectedGap(gap);
    setDetailDialogOpen(true);
  };

  const filteredGaps = contentGaps.filter(gap =>
    gap.question.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (!domainId) {
    return (
      <div className="p-8 space-y-8 bg-background animate-fade-in">
        <div className="flex flex-col items-center justify-center py-32 space-y-4">
          <Target className="h-16 w-16 text-muted-foreground" />
          <h3 className="text-2xl font-semibold">No Domain Selected</h3>
          <p className="text-muted-foreground text-center max-w-md">
            Please select a domain from the header to view content gap analysis.
          </p>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return <PageLoader />;
  }

  return (
    <div className="p-8 space-y-8 bg-background animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">GEO Content Gaps</h1>
          <p className="text-muted-foreground mt-2">
            Discover untapped opportunities and AI-powered recommendations
          </p>
        </div>
        <Button onClick={handleGenerateContentPlan} className="gradient-primary shadow-md shadow-primary/20">
          <Calendar className="h-4 w-4 mr-2" />
          Content Planner
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-muted-foreground font-medium">Total Gaps</p>
            <Target className="h-5 w-5 text-muted-foreground" />
          </div>
          <h3 className="text-3xl font-bold">{summary?.totalGaps || 0}</h3>
          <p className="text-xs text-muted-foreground mt-1">Identified opportunities</p>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-muted-foreground font-medium">High Priority</p>
            <AlertCircle className="h-5 w-5 text-destructive" />
          </div>
          <h3 className="text-3xl font-bold text-destructive">{summary?.highPriority || 0}</h3>
          <p className="text-xs text-muted-foreground mt-1">Require immediate action</p>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-muted-foreground font-medium">Avg Coverage</p>
            <TrendingUp className="h-5 w-5 text-muted-foreground" />
          </div>
          <h3 className="text-3xl font-bold">{summary?.avgCoverage || 0}%</h3>
          <p className="text-xs text-muted-foreground mt-1">Across all gaps</p>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-muted-foreground font-medium">Est. Impact</p>
            <Sparkles className="h-5 w-5 text-primary" />
          </div>
          <h3 className="text-3xl font-bold text-primary">{summary?.estimatedImpact || "+0%"}</h3>
          <p className="text-xs text-muted-foreground mt-1">Potential visibility gain</p>
        </Card>
      </div>

      {/* Content Gaps List */}
      <Card className="p-6 border border-border">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold">Identified Content Gaps</h3>
          <div className="relative w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search gaps..."
              className="pl-10"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        {filteredGaps.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 space-y-4">
            <Search className="h-16 w-16 text-muted-foreground opacity-50" />
            <h3 className="text-xl font-semibold">No Content Gaps Found</h3>
            <p className="text-muted-foreground text-center max-w-md">
              {searchQuery ? "No gaps match your search. Try a different query." : "Great news! Your content coverage is comprehensive. Keep monitoring for new opportunities."}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredGaps.map((gap) => (
              <div key={gap.id} className="p-4 rounded-lg transition-all duration-300 border border-border hover:border-primary">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <Badge className={getPriorityColor(gap.priority)}>
                        {gap.priority} priority
                      </Badge>
                      <span className="text-sm text-muted-foreground">
                        {gap.frequency} mentions
                      </span>
                    </div>
                    <h4 className="font-semibold text-lg mb-2">{gap.question}</h4>
                    <div className="flex flex-wrap gap-2 mb-3">
                      {gap.platforms && gap.platforms.map((platform: string) => (
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
                      {gap.competitorMentions && gap.competitorMentions.map((comp: any) => (
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
        )}

        {/* Pagination Controls */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between pt-6 border-t border-border">
            <div className="text-sm text-muted-foreground">
              Showing page {currentPage} of {totalPages} ({totalCount} total gaps)
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage(1)}
                disabled={currentPage === 1}
              >
                First
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                disabled={currentPage === 1}
              >
                Previous
              </Button>
              <div className="flex items-center gap-1">
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  let pageNum;
                  if (totalPages <= 5) {
                    pageNum = i + 1;
                  } else if (currentPage <= 3) {
                    pageNum = i + 1;
                  } else if (currentPage >= totalPages - 2) {
                    pageNum = totalPages - 4 + i;
                  } else {
                    pageNum = currentPage - 2 + i;
                  }
                  return (
                    <Button
                      key={pageNum}
                      variant={currentPage === pageNum ? "default" : "outline"}
                      size="sm"
                      onClick={() => setCurrentPage(pageNum)}
                      className="w-10"
                    >
                      {pageNum}
                    </Button>
                  );
                })}
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                disabled={currentPage === totalPages}
              >
                Next
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage(totalPages)}
                disabled={currentPage === totalPages}
              >
                Last
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Detail Dialog */}
      <ContentGapDetailDialog
        open={detailDialogOpen}
        onOpenChange={setDetailDialogOpen}
        gap={selectedGap}
        domainId={domainId}
      />

      {/* Generate Content Dialog */}
      <GenerateContentDialog
        open={generateDialogOpen}
        onOpenChange={setGenerateDialogOpen}
        existingContent={selectedContentForGeneration}
      />
    </div>
  );
};

export default ContentGaps;
