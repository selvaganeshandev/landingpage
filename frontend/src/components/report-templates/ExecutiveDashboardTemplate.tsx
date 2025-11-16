import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import {
  TrendingUp,
  TrendingDown,
  Target,
  DollarSign,
  Users,
  Activity,
  AlertCircle,
  CheckCircle2,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight,
  FileText,
  PieChart
} from "lucide-react";

interface ExecutiveDashboardTemplateProps {
  data: any;
}

export const ExecutiveDashboardTemplate = ({ data }: ExecutiveDashboardTemplateProps) => {
  // Extract metrics from the API response structure
  const metrics = data?.metrics || {};
  const brand = data?.brand || {};
  const platforms = data?.platforms || [];
  const shareOfVoice = data?.share_of_voice;

  // Calculate metrics from data
  const totalMentions = metrics.total_mentions || 0;
  const visibilityScore = metrics.visibility_score || 0;
  const sentimentScore = brand.sentiment?.positive_percentage || 0;
  const negativeSentiment = brand.sentiment?.negative_percentage || 0;
  const neutralSentiment = brand.sentiment?.neutral_percentage || 0;
  const totalCitations = metrics.total_citations || 0;
  const avgPosition = metrics.avg_position || 0;

  // Calculate trends (use API change values or defaults)
  const visibilityTrend = metrics.visibility_change !== null && metrics.visibility_change !== undefined ? metrics.visibility_change : 0;
  const mentionsTrend = metrics.mentions_change !== null && metrics.mentions_change !== undefined ? metrics.mentions_change : 0;
  const citationsTrend = metrics.citations_change !== null && metrics.citations_change !== undefined ? metrics.citations_change : 0;
  const sentimentTrend = 0; // TODO: Calculate sentiment trend from historical data

  // Calculate mention rate (percentage of citations that mention)
  const mentionRate = totalCitations > 0 ? (totalMentions / totalCitations) * 100 : 0;

  // Share of voice and competitors
  const yourSharePercentage = shareOfVoice?.your_brand?.share_percentage || 0;
  const topCompetitor = shareOfVoice?.competitors?.[0];
  const competitorCount = shareOfVoice?.competitors?.length || 0;

  // Platform distribution - map to expected format
  const platformStats = platforms.map((platform: any) => ({
    model_name: platform.platform,
    percentage: totalMentions > 0 ? ((platform.mention_count / totalMentions) * 100).toFixed(1) : 0,
    mention_count: platform.mention_count
  }));

  return (
    <div className="w-full bg-background space-y-8">
      {/* Header Section */}
      <div className="border-b pb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">Executive Dashboard</h1>
            <p className="text-muted-foreground">AI Visibility Performance Overview</p>
          </div>
          <div className="text-right">
            <p className="text-sm text-muted-foreground">Report Period</p>
            <p className="font-semibold">{new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}</p>
          </div>
        </div>
      </div>

      {/* Executive Summary - Key Metrics */}
      <div>
        <h2 className="text-2xl font-bold mb-6">Summary</h2>
        <div className="grid grid-cols-4 gap-4">
          {/* Box 1: Overall Visibility Score */}
          <Card className="p-6 border border-border">
            <div className="flex items-start justify-between mb-3">
              <div className="w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-900/20 flex items-center justify-center">
                <Target className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              </div>
            </div>
            <p className="text-sm text-muted-foreground mb-1">Overall Visibility Score</p>
            <p className="text-3xl font-bold">{visibilityScore.toFixed(1)}</p>
          </Card>

          {/* Box 2: Platform Coverage */}
          <Card className="p-6 border border-border">
            <div className="flex items-start justify-between mb-3">
              <div className="w-10 h-10 rounded-lg bg-purple-100 dark:bg-purple-900/20 flex items-center justify-center">
                <BarChart3 className="h-5 w-5 text-purple-600 dark:text-purple-400" />
              </div>
            </div>
            <p className="text-sm text-muted-foreground mb-1">Platform Coverage</p>
            <p className="text-3xl font-bold">{platforms.length}</p>
          </Card>

          {/* Box 3: Total AI Mentions */}
          <Card className="p-6 border border-border">
            <div className="flex items-start justify-between mb-3">
              <div className="w-10 h-10 rounded-lg bg-green-100 dark:bg-green-900/20 flex items-center justify-center">
                <Activity className="h-5 w-5 text-green-600 dark:text-green-400" />
              </div>
            </div>
            <p className="text-sm text-muted-foreground mb-1">Total AI Mentions</p>
            <p className="text-3xl font-bold">{totalMentions.toLocaleString()}</p>
          </Card>

          {/* Box 4: Total Citations */}
          <Card className="p-6 border border-border">
            <div className="flex items-start justify-between mb-3">
              <div className="w-10 h-10 rounded-lg bg-indigo-100 dark:bg-indigo-900/20 flex items-center justify-center">
                <FileText className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
              </div>
            </div>
            <p className="text-sm text-muted-foreground mb-1">Total Citations</p>
            <p className="text-3xl font-bold">{totalCitations.toLocaleString()}</p>
          </Card>

          {/* Box 5: Positive Sentiment */}
          <Card className="p-6 border border-border">
            <div className="flex items-start justify-between mb-3">
              <div className="w-10 h-10 rounded-lg bg-green-100 dark:bg-green-900/20 flex items-center justify-center">
                <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
              </div>
            </div>
            <p className="text-sm text-muted-foreground mb-1">Positive Sentiment</p>
            <p className="text-3xl font-bold">{sentimentScore.toFixed(0)}%</p>
          </Card>

          {/* Box 6: Negative Sentiment */}
          <Card className="p-6 border border-border">
            <div className="flex items-start justify-between mb-3">
              <div className="w-10 h-10 rounded-lg bg-red-100 dark:bg-red-900/20 flex items-center justify-center">
                <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400" />
              </div>
            </div>
            <p className="text-sm text-muted-foreground mb-1">Negative Sentiment</p>
            <p className="text-3xl font-bold">{negativeSentiment.toFixed(0)}%</p>
          </Card>

          {/* Box 7: Neutral Sentiment */}
          <Card className="p-6 border border-border">
            <div className="flex items-start justify-between mb-3">
              <div className="w-10 h-10 rounded-lg bg-gray-100 dark:bg-gray-900/20 flex items-center justify-center">
                <DollarSign className="h-5 w-5 text-gray-600 dark:text-gray-400" />
              </div>
            </div>
            <p className="text-sm text-muted-foreground mb-1">Neutral Sentiment</p>
            <p className="text-3xl font-bold">{neutralSentiment.toFixed(0)}%</p>
          </Card>

          {/* Box 8: Share of Voice */}
          <Card className="p-6 border border-border">
            <div className="flex items-start justify-between mb-3">
              <div className="w-10 h-10 rounded-lg bg-teal-100 dark:bg-teal-900/20 flex items-center justify-center">
                <PieChart className="h-5 w-5 text-teal-600 dark:text-teal-400" />
              </div>
            </div>
            <p className="text-sm text-muted-foreground mb-1">Share of Voice</p>
            <p className="text-3xl font-bold">{yourSharePercentage > 0 ? `${yourSharePercentage.toFixed(1)}%` : 'N/A'}</p>
          </Card>
        </div>
      </div>

      {/* Strategic Performance Indicators */}
      <div>
        <h2 className="text-2xl font-bold mb-6">Strategic Performance Indicators</h2>
        <div className="grid grid-cols-2 gap-6">
          <Card className="p-6 border border-border">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-primary" />
              AI Platform Distribution
            </h3>
            <div className="space-y-3">
              {platformStats.length > 0 ? (
                platformStats.map((platform: any, index: number) => {
                  const colors = ['bg-blue-500', 'bg-purple-500', 'bg-amber-500', 'bg-green-500', 'bg-pink-500'];
                  return (
                    <div key={index}>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium">{platform.model_name}</span>
                        <span className="text-sm font-bold">{platform.percentage}%</span>
                      </div>
                      <div className="h-2 bg-muted rounded-full overflow-hidden">
                        <div className={`h-full ${colors[index % colors.length]}`} style={{ width: `${platform.percentage}%` }}></div>
                      </div>
                    </div>
                  );
                })
              ) : (
                <>
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">ChatGPT</span>
                      <span className="text-sm font-bold">42%</span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div className="h-full bg-blue-500" style={{ width: '42%' }}></div>
                    </div>
                  </div>
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">Perplexity</span>
                      <span className="text-sm font-bold">28%</span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div className="h-full bg-purple-500" style={{ width: '28%' }}></div>
                    </div>
                  </div>
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">Claude</span>
                      <span className="text-sm font-bold">18%</span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div className="h-full bg-amber-500" style={{ width: '18%' }}></div>
                    </div>
                  </div>
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">Gemini</span>
                      <span className="text-sm font-bold">12%</span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div className="h-full bg-green-500" style={{ width: '12%' }}></div>
                    </div>
                  </div>
                </>
              )}
            </div>
          </Card>

          <Card className="p-6 border border-border">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Users className="h-5 w-5 text-primary" />
              Market Position vs Competitors
            </h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-green-50 dark:bg-green-900/10 rounded-lg border border-green-200 dark:border-green-900/30">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center">
                    <span className="text-sm font-bold text-primary-foreground">1</span>
                  </div>
                  <span className="font-semibold">Your Brand</span>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold">{visibilityScore.toFixed(1)}</p>
                  <p className="text-xs text-muted-foreground">Visibility Score</p>
                </div>
              </div>
              {data?.competitors?.slice(0, 2).map((competitor: any, index: number) => (
                <div key={index} className="flex items-center justify-between p-3 bg-muted/30 rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center">
                      <span className="text-sm font-bold">{index + 2}</span>
                    </div>
                    <span className="font-medium">{competitor.name}</span>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-bold text-muted-foreground">{competitor.score.toFixed(1)}</p>
                    <p className="text-xs text-muted-foreground">Visibility Score</p>
                  </div>
                </div>
              )) || (
                <>
                  <div className="flex items-center justify-between p-3 bg-muted/30 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center">
                        <span className="text-sm font-bold">2</span>
                      </div>
                      <span className="font-medium">Competitor A</span>
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-bold text-muted-foreground">78.2</p>
                      <p className="text-xs text-muted-foreground">Visibility Score</p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-muted/30 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center">
                        <span className="text-sm font-bold">3</span>
                      </div>
                      <span className="font-medium">Competitor B</span>
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-bold text-muted-foreground">72.8</p>
                      <p className="text-xs text-muted-foreground">Visibility Score</p>
                    </div>
                  </div>
                </>
              )}
            </div>
          </Card>
        </div>
      </div>

      {/* Key Insights & Opportunities */}
      <div>
        <h2 className="text-2xl font-bold mb-6">Key Strategic Insights</h2>
        <div className="grid grid-cols-2 gap-4">
          <Card className="p-5 border border-border border-l-4 border-l-green-500">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-lg bg-green-100 dark:bg-green-900/20 flex items-center justify-center flex-shrink-0">
                <ArrowUpRight className="h-5 w-5 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <h4 className="font-semibold mb-1">Market Leadership Achieved</h4>
                <p className="text-sm text-muted-foreground">Your brand now ranks #1 in AI visibility, surpassing all competitors by 9.3 points</p>
              </div>
            </div>
          </Card>

          <Card className="p-5 border border-border border-l-4 border-l-blue-500">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-900/20 flex items-center justify-center flex-shrink-0">
                <DollarSign className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <h4 className="font-semibold mb-1">Revenue Impact Growing</h4>
                <p className="text-sm text-muted-foreground">AI-attributed revenue up 22.5%, contributing $124K this period with strong ROI</p>
              </div>
            </div>
          </Card>

          <Card className="p-5 border border-border border-l-4 border-l-purple-500">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-lg bg-purple-100 dark:bg-purple-900/20 flex items-center justify-center flex-shrink-0">
                <TrendingUp className="h-5 w-5 text-purple-600 dark:text-purple-400" />
              </div>
              <div>
                <h4 className="font-semibold mb-1">Strong Momentum Continues</h4>
                <p className="text-sm text-muted-foreground">15.2% growth in mentions with 92% positive sentiment across all platforms</p>
              </div>
            </div>
          </Card>

          <Card className="p-5 border border-border border-l-4 border-l-amber-500">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-lg bg-amber-100 dark:bg-amber-900/20 flex items-center justify-center flex-shrink-0">
                <Target className="h-5 w-5 text-amber-600 dark:text-amber-400" />
              </div>
              <div>
                <h4 className="font-semibold mb-1">Expansion Opportunity</h4>
                <p className="text-sm text-muted-foreground">Gemini platform shows 45% month-over-month growth potential for market share</p>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Critical Alerts */}
      <div>
        <h2 className="text-2xl font-bold mb-6">Items Requiring Attention</h2>
        <div className="space-y-3">
          <Card className="p-4 border border-border bg-red-50/50 dark:bg-red-900/10 border-l-4 border-l-red-500">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="font-semibold mb-1">Misinformation Alert Detected</h4>
                    <p className="text-sm text-muted-foreground">3 instances of inaccurate pricing information found on Perplexity - Immediate correction recommended</p>
                  </div>
                  <Badge variant="destructive">High Priority</Badge>
                </div>
              </div>
            </div>
          </Card>

          <Card className="p-4 border border-border bg-amber-50/50 dark:bg-amber-900/10 border-l-4 border-l-amber-500">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="font-semibold mb-1">Competitor Gaining Traction</h4>
                    <p className="text-sm text-muted-foreground">Competitor A increased visibility by 12% - Monitor their content strategy closely</p>
                  </div>
                  <Badge variant="secondary" className="bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400">Medium Priority</Badge>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Executive Recommendations */}
      <div>
        <h2 className="text-2xl font-bold mb-6">Strategic Recommendations</h2>
        <div className="space-y-3">
          <div className="p-4 border-l-4 border-l-primary bg-primary/5 rounded-lg">
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-primary flex items-center justify-center text-xs font-bold text-primary-foreground flex-shrink-0 mt-0.5">
                1
              </div>
              <div>
                <h4 className="font-semibold mb-1">Accelerate Gemini Platform Investment</h4>
                <p className="text-sm text-muted-foreground mb-2">
                  With 45% growth potential and currently only 12% market share, prioritize content optimization for Gemini to capture this emerging opportunity.
                </p>
                <Badge variant="outline" className="text-xs">Expected ROI: +$35K/quarter</Badge>
              </div>
            </div>
          </div>

          <div className="p-4 border-l-4 border-l-primary bg-primary/5 rounded-lg">
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-primary flex items-center justify-center text-xs font-bold text-primary-foreground flex-shrink-0 mt-0.5">
                2
              </div>
              <div>
                <h4 className="font-semibold mb-1">Address Perplexity Misinformation Immediately</h4>
                <p className="text-sm text-muted-foreground mb-2">
                  Coordinate with marketing to correct pricing inaccuracies. Submit content corrections to Perplexity and update website FAQs.
                </p>
                <Badge variant="outline" className="text-xs">Timeline: 72 hours</Badge>
              </div>
            </div>
          </div>

          <div className="p-4 border-l-4 border-l-primary bg-primary/5 rounded-lg">
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-primary flex items-center justify-center text-xs font-bold text-primary-foreground flex-shrink-0 mt-0.5">
                3
              </div>
              <div>
                <h4 className="font-semibold mb-1">Maintain ChatGPT Market Dominance</h4>
                <p className="text-sm text-muted-foreground mb-2">
                  With 42% share, continue current content strategy while monitoring competitor movements. Consider exclusive partnerships or thought leadership initiatives.
                </p>
                <Badge variant="outline" className="text-xs">Status: On Track</Badge>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="pt-6 border-t">
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <p>Generated by AI Visibility Monitor</p>
          <p>Confidential - Executive Use Only</p>
        </div>
      </div>
    </div>
  );
};
