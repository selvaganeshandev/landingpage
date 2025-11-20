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

  // Extract domain information
  const domainName = data?.domain_name || 'Your Brand';
  const domainUrl = data?.domain_url || '';

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

  // Calculate citation rate (percentage of mentions that have citations)
  const citationRate = totalMentions > 0 ? (totalCitations / totalMentions) * 100 : 0;

  // Share of voice and competitors
  const yourSharePercentage = shareOfVoice?.your_brand?.share_percentage || 0;
  const topCompetitor = shareOfVoice?.competitors?.[0];
  const competitorCount = shareOfVoice?.competitors?.length || 0;

  // Platform distribution - map to expected format
  const platformStats = platforms.map((platform: any) => ({
    model_name: platform.platform,
    percentage: totalMentions > 0 ? ((platform.mention_count / totalMentions) * 100).toFixed(1) : '0.0',
    mention_count: platform.mention_count
  }));

  return (
    <div className="w-full min-h-screen bg-white dark:bg-gray-950 space-y-8">
      <div className="max-w-[1200px] mx-auto px-8 py-8">
      {/* Header Section */}
      <div className="border-b pb-6 break-inside-avoid">
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
      <div className="mt-8">
        <h2 className="text-2xl font-bold mb-6 break-after-avoid">Summary</h2>
        <div className="grid grid-cols-4 gap-4 break-inside-avoid">
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
      <div className="mt-8">
        <h2 className="text-2xl font-bold mb-6 break-after-avoid">Strategic Performance Indicators</h2>
        <div className="grid grid-cols-2 gap-6 break-inside-avoid">
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
                  <div className="w-8 h-8 rounded-full bg-white dark:bg-gray-800 flex items-center justify-center border-2 border-primary overflow-hidden">
                    <img
                      src={`https://www.google.com/s2/favicons?domain=${domainUrl}&sz=64`}
                      alt={domainName}
                      className="w-5 h-5"
                      onError={(e) => {
                        e.currentTarget.style.display = 'none';
                        const parent = e.currentTarget.parentElement;
                        if (parent) {
                          parent.innerHTML = '<span class="text-sm font-bold text-primary">1</span>';
                        }
                      }}
                    />
                  </div>
                  <span className="font-semibold">{domainName}</span>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold">{shareOfVoice?.your_brand?.share_percentage?.toFixed(1) || yourSharePercentage.toFixed(1)}%</p>
                  <p className="text-xs text-muted-foreground">Share of Voice</p>
                </div>
              </div>
              {shareOfVoice?.competitors && shareOfVoice.competitors.length > 0 ? (
                shareOfVoice.competitors.slice(0, 3).map((competitor: any, index: number) => (
                  <div key={index} className="flex items-center justify-between p-3 bg-muted/30 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-white dark:bg-gray-800 flex items-center justify-center border border-muted-foreground/20 overflow-hidden">
                        <img
                          src={`https://www.google.com/s2/favicons?domain=${competitor.url}&sz=64`}
                          alt={competitor.name}
                          className="w-5 h-5"
                          onError={(e) => {
                            e.currentTarget.style.display = 'none';
                            const parent = e.currentTarget.parentElement;
                            if (parent) {
                              parent.innerHTML = `<span class="text-sm font-bold">${competitor.market_position || (index + 2)}</span>`;
                            }
                          }}
                        />
                      </div>
                      <span className="font-medium">{competitor.name}</span>
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-bold text-muted-foreground">{competitor.share_percentage?.toFixed(1)}%</p>
                      <p className="text-xs text-muted-foreground">Share of Voice</p>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-4 text-muted-foreground text-sm">
                  No competitor data available
                </div>
              )}
            </div>
          </Card>
        </div>
      </div>

      {/* Items Requiring Attention */}
      <div className="mt-8">
        <h2 className="text-2xl font-bold mb-6 break-after-avoid">Items Requiring Attention</h2>
        {data?.alerts && data.alerts.length > 0 ? (
          <div className="space-y-3 break-inside-avoid">
            {data.alerts.map((alert: any, index: number) => (
              <Card key={index} className={`p-4 border border-border ${
                alert.severity === 'high'
                  ? 'bg-red-50/50 dark:bg-red-900/10 border-l-4 border-l-red-500'
                  : 'bg-amber-50/50 dark:bg-amber-900/10 border-l-4 border-l-amber-500'
              }`}>
                <div className="flex items-start gap-3">
                  <AlertCircle className={`h-5 w-5 ${
                    alert.severity === 'high'
                      ? 'text-red-600 dark:text-red-400'
                      : 'text-amber-600 dark:text-amber-400'
                  } flex-shrink-0 mt-0.5`} />
                  <div className="flex-1">
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="font-semibold mb-1">{alert.title}</h4>
                        <p className="text-sm text-muted-foreground">{alert.description}</p>
                      </div>
                      <Badge variant={alert.severity === 'high' ? 'destructive' : 'secondary'} className={
                        alert.severity === 'high'
                          ? ''
                          : 'bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400'
                      }>
                        {alert.severity === 'high' ? 'High Priority' : 'Medium Priority'}
                      </Badge>
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        ) : (
          <Card className="p-6 border border-border bg-green-50/50 dark:bg-green-900/10 border-l-4 border-l-green-500 break-inside-avoid">
            <div className="flex items-start gap-3">
              <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="font-semibold mb-2">All Clear!</h4>
                <p className="text-sm text-muted-foreground leading-relaxed">Good news! There are no misinformation alerts or critical issues at the moment. Your brand presence is performing well across all platforms.</p>
              </div>
            </div>
          </Card>
        )}
      </div>

      {/* Key Insights & Opportunities */}
      <div className="mt-8 break-inside-avoid">
        <h2 className="text-2xl font-bold mb-6 break-after-avoid">Key Strategic Insights</h2>
        {(() => {
          const hasMarketLeadership = shareOfVoice?.your_brand?.market_position === 1;
          const hasVisibilityGrowth = metrics.visibility_change && metrics.visibility_change > 0;
          const hasMentionsMomentum = mentionsTrend > 0;
          const hasPlatformData = platforms.length > 0;
          const hasCitations = totalCitations > 0;
          const hasCompetitors = competitorCount > 0;

          const hasAnyInsights = hasMarketLeadership || hasVisibilityGrowth || hasMentionsMomentum ||
                                 hasPlatformData || hasCitations || hasCompetitors;

          if (!hasAnyInsights) {
            return (
              <Card className="p-6 border border-border bg-muted/30 break-inside-avoid">
                <div className="text-center py-4">
                  <p className="text-muted-foreground">
                    No strategic insights available yet. Start tracking prompts and competitors to generate insights.
                  </p>
                </div>
              </Card>
            );
          }

          return null;
        })()}
        <div className="grid grid-cols-2 gap-4">
          {/* Market Leadership - Show if #1 in share of voice */}
          {shareOfVoice?.your_brand?.market_position === 1 && (
            <Card className="p-5 border border-border border-l-4 border-l-green-500 break-inside-avoid">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-green-100 dark:bg-green-900/20 flex items-center justify-center flex-shrink-0">
                  <ArrowUpRight className="h-5 w-5 text-green-600 dark:text-green-400" />
                </div>
                <div>
                  <h4 className="font-semibold mb-2">Market Leadership Achieved</h4>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {domainName} ranks #1 in AI visibility with {yourSharePercentage.toFixed(1)}% share of voice
                    {shareOfVoice?.competitors?.[0] && ` - leading by ${(yourSharePercentage - shareOfVoice.competitors[0].share_percentage).toFixed(1)} percentage points`}
                  </p>
                </div>
              </div>
            </Card>
          )}

          {/* Visibility Growth - Show if positive change */}
          {metrics.visibility_change && metrics.visibility_change > 0 && (
            <Card className="p-5 border border-border border-l-4 border-l-blue-500 break-inside-avoid">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-900/20 flex items-center justify-center flex-shrink-0">
                  <TrendingUp className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <h4 className="font-semibold mb-2">Visibility Score Growing</h4>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    AI visibility increased by {metrics.visibility_change.toFixed(1)}% with current score of {visibilityScore.toFixed(1)}
                  </p>
                </div>
              </div>
            </Card>
          )}

          {/* Positive Mentions Momentum */}
          {mentionsTrend > 0 && (
            <Card className="p-5 border border-border border-l-4 border-l-purple-500 break-inside-avoid">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-purple-100 dark:bg-purple-900/20 flex items-center justify-center flex-shrink-0">
                  <Activity className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <h4 className="font-semibold mb-1">Strong Mentions Momentum</h4>
                  <p className="text-sm text-muted-foreground">
                    {mentionsTrend > 0 ? '+' : ''}{mentionsTrend.toFixed(1)}% growth in mentions with {sentimentScore.toFixed(0)}% positive sentiment across all platforms
                  </p>
                </div>
              </div>
            </Card>
          )}

          {/* Platform Opportunity - Show best performing or fastest growing platform */}
          {platforms.length > 0 && (
            <Card className="p-5 border border-border border-l-4 border-l-amber-500 break-inside-avoid">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-amber-100 dark:bg-amber-900/20 flex items-center justify-center flex-shrink-0">
                  <Target className="h-5 w-5 text-amber-600 dark:text-amber-400" />
                </div>
                <div>
                  <h4 className="font-semibold mb-1">Platform Performance Insight</h4>
                  <p className="text-sm text-muted-foreground">
                    {platforms[0].platform} leads with {platforms[0].mention_count} mentions
                    {platforms.length > 1 && ` - ${((platforms[0].mention_count / totalMentions) * 100).toFixed(0)}% of total visibility`}
                  </p>
                </div>
              </div>
            </Card>
          )}

          {/* Citations Impact */}
          {totalCitations > 0 && (
            <Card className="p-5 border border-border border-l-4 border-l-teal-500 break-inside-avoid">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-teal-100 dark:bg-teal-900/20 flex items-center justify-center flex-shrink-0">
                  <FileText className="h-5 w-5 text-teal-600 dark:text-teal-400" />
                </div>
                <div>
                  <h4 className="font-semibold mb-1">Strong Citation Authority</h4>
                  <p className="text-sm text-muted-foreground">
                    {totalCitations} citation{totalCitations > 1 ? 's' : ''} from {totalMentions} mention{totalMentions > 1 ? 's' : ''} ({citationRate.toFixed(1)}% citation rate)
                  </p>
                </div>
              </div>
            </Card>
          )}

          {/* Competitive Position */}
          {competitorCount > 0 && (
            <Card className="p-5 border border-border border-l-4 border-l-indigo-500 break-inside-avoid">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-indigo-100 dark:bg-indigo-900/20 flex items-center justify-center flex-shrink-0">
                  <Users className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
                </div>
                <div>
                  <h4 className="font-semibold mb-1">Competitive Landscape</h4>
                  <p className="text-sm text-muted-foreground">
                    Tracking {competitorCount} competitor{competitorCount > 1 ? 's' : ''} with market position #{shareOfVoice?.your_brand?.market_position || 1}
                  </p>
                </div>
              </div>
            </Card>
          )}
        </div>
      </div>

      {/* Executive Recommendations */}
      <div className="mt-8 break-inside-avoid">
        <h2 className="text-2xl font-bold mb-6 break-after-avoid">Strategic Recommendations</h2>
        {(() => {
          const recommendations: Array<{
            title: string;
            description: string;
            badge: string;
            priority: number;
          }> = [];

          // Recommendation 1: Address alerts if they exist
          if (data?.alerts && data.alerts.length > 0) {
            const highPriorityAlerts = data.alerts.filter((a: any) => a.severity === 'high');
            if (highPriorityAlerts.length > 0) {
              recommendations.push({
                title: 'Address Critical Alerts Immediately',
                description: `${highPriorityAlerts.length} high-priority alert${highPriorityAlerts.length > 1 ? 's' : ''} require immediate attention. Review and resolve misinformation or accuracy issues to maintain brand credibility.`,
                badge: 'Timeline: 24-48 hours',
                priority: 1
              });
            }
          }

          // Recommendation 2: Improve low-performing platforms
          if (platforms.length > 1) {
            const lowestPlatform = platforms[platforms.length - 1];
            const topPlatform = platforms[0];
            const percentageGap = ((topPlatform.mention_count / totalMentions) * 100) - ((lowestPlatform.mention_count / totalMentions) * 100);

            if (percentageGap > 30 && lowestPlatform.mention_count < 5) {
              recommendations.push({
                title: `Expand Presence on ${lowestPlatform.platform}`,
                description: `${lowestPlatform.platform} represents an untapped opportunity with only ${lowestPlatform.mention_count} mention${lowestPlatform.mention_count > 1 ? 's' : ''}. Optimize content for this platform to diversify AI visibility.`,
                badge: 'Opportunity: High Growth Potential',
                priority: 2
              });
            }
          }

          // Recommendation 3: Maintain leadership position
          if (shareOfVoice?.your_brand?.market_position === 1) {
            const yourShare = yourSharePercentage;
            const secondPlace = shareOfVoice?.competitors?.[0];
            const gap = secondPlace ? (yourShare - secondPlace.share_percentage).toFixed(1) : yourShare.toFixed(1);

            recommendations.push({
              title: 'Maintain Market Leadership',
              description: `Currently leading with ${yourShare.toFixed(1)}% share of voice${secondPlace ? `, ahead by ${gap} percentage points` : ''}. Continue current content strategy and monitor competitor activities to defend position.`,
              badge: 'Status: On Track',
              priority: 3
            });
          }

          // Recommendation 4: Improve visibility if low
          if (visibilityScore < 50 && visibilityScore > 0) {
            recommendations.push({
              title: 'Boost AI Visibility Score',
              description: `Current visibility score of ${visibilityScore.toFixed(1)} is below optimal. Increase prompt coverage, improve content quality, and enhance citation opportunities to improve rankings.`,
              badge: `Target: 75+ Score`,
              priority: 2
              });
          }

          // Recommendation 5: Leverage top platform
          if (platforms.length > 0) {
            const topPlatform = platforms[0];
            const topPlatformShare = ((topPlatform.mention_count / totalMentions) * 100).toFixed(0);

            if (topPlatform.mention_count > 5) {
              recommendations.push({
                title: `Maximize ${topPlatform.platform} Dominance`,
                description: `${topPlatform.platform} is your strongest platform with ${topPlatformShare}% of mentions (${topPlatform.mention_count} total). Double down on this channel through targeted content optimization and prompt engineering.`,
                badge: 'Priority: Leverage Strength',
                priority: 3
              });
            }
          }

          // Recommendation 6: Improve sentiment if low
          if (sentimentScore < 70 && totalMentions > 0) {
            recommendations.push({
              title: 'Enhance Sentiment Quality',
              description: `${sentimentScore.toFixed(0)}% positive sentiment indicates room for improvement. Review negative mentions, update content accuracy, and strengthen value propositions in source materials.`,
              badge: 'Target: 80%+ Positive',
              priority: 2
            });
          }

          // Recommendation 7: Track competitors if none
          if (competitorCount === 0) {
            recommendations.push({
              title: 'Start Competitor Tracking',
              description: 'Add competitor tracking to benchmark your performance and identify market opportunities. Understanding competitor strategies helps refine your AI visibility approach.',
              badge: 'Action: Add Competitors',
              priority: 3
            });
          }

          // Recommendation 8: Compete with leaders if behind
          if (shareOfVoice?.your_brand?.market_position && shareOfVoice.your_brand.market_position > 1) {
            const leader = shareOfVoice.competitors.find((c: any) => c.market_position === 1);
            const gap = leader ? (leader.share_percentage - yourSharePercentage).toFixed(1) : 'significant';

            recommendations.push({
              title: 'Close Competitive Gap',
              description: `Currently in position #${shareOfVoice.your_brand.market_position} with ${gap !== 'significant' ? `${gap} percentage points` : 'distance'} to close. Analyze top competitor strategies and increase content optimization efforts.`,
              badge: `Target: Position #${Math.max(1, shareOfVoice.your_brand.market_position - 1)}`,
              priority: 1
            });
          }

          // Sort by priority and limit to top 3
          const topRecommendations = recommendations
            .sort((a, b) => a.priority - b.priority)
            .slice(0, 3);

          if (topRecommendations.length === 0) {
            return (
              <Card className="p-6 border border-border bg-muted/30 break-inside-avoid">
                <div className="text-center py-4">
                  <p className="text-muted-foreground">
                    Excellent performance! Continue monitoring metrics and maintain current strategies.
                  </p>
                </div>
              </Card>
            );
          }

          return (
            <div className="space-y-3">
              {topRecommendations.map((rec, index) => (
                <div key={index} className="p-4 border-l-4 border-l-primary bg-primary/5 rounded-lg break-inside-avoid">
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-primary flex items-center justify-center text-xs font-bold text-primary-foreground flex-shrink-0 mt-0.5">
                      {index + 1}
                    </div>
                    <div>
                      <h4 className="font-semibold mb-1">{rec.title}</h4>
                      <p className="text-sm text-muted-foreground mb-2">{rec.description}</p>
                      <Badge variant="outline" className="text-xs">{rec.badge}</Badge>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          );
        })()}
      </div>

      {/* Footer */}
      <div className="pt-6 border-t">
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <p>Generated by AI Visibility Monitor</p>
          <p>Confidential - Executive Use Only</p>
        </div>
      </div>
      </div>
    </div>
  );
};
