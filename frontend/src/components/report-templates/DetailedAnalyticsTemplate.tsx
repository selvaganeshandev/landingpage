import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import {
  TrendingUp,
  TrendingDown,
  Activity,
  Eye,
  MessageSquare,
  ThumbsUp,
  ThumbsDown,
  AlertTriangle,
  BarChart3,
  PieChart,
  Calendar,
  Clock,
  Globe,
  Search,
  Users,
  Target,
  Zap,
  Award,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  FileText,
  CheckCircle2
} from "lucide-react";

interface DetailedAnalyticsTemplateProps {
  data: any;
}

export const DetailedAnalyticsTemplate = ({ data }: DetailedAnalyticsTemplateProps) => {
  // Extract metrics from the API response structure
  const metrics = data?.metrics || {};
  const brand = data?.brand || {};
  const platforms = data?.platforms || [];
  const shareOfVoice = data?.share_of_voice;

  // Extract domain information
  const domainName = data?.domain_name || 'Your Brand';
  const domainUrl = data?.domain_url || '';

  // Helper function to get favicon URL
  const getFaviconUrl = (url: string) => {
    try {
      const domain = new URL(url.startsWith('http') ? url : `https://${url}`).hostname;
      return `https://www.google.com/s2/favicons?domain=${domain}&sz=128`;
    } catch {
      return `https://ui-avatars.com/api/?name=${encodeURIComponent(url)}&background=random`;
    }
  };

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

  // Calculate daily average
  const dailyAvgMentions = totalMentions > 0 ? Math.round(totalMentions / 30) : 0;

  // Platform distribution
  const platformStats = platforms.map((platform: any) => ({
    model_name: platform.platform,
    percentage: totalMentions > 0 ? ((platform.mention_count / totalMentions) * 100).toFixed(1) : '0.0',
    mention_count: platform.mention_count
  }));

  // Calculate sentiment counts
  const positiveMentions = Math.round((totalMentions * sentimentScore) / 100);
  const negativeMentions = Math.round((totalMentions * negativeSentiment) / 100);
  const neutralMentions = Math.round((totalMentions * neutralSentiment) / 100);

  // Helper function to render trend badge
  const renderTrendBadge = (trend: number) => {
    if (trend > 0) {
      return (
        <Badge variant="default" className="bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400">
          <TrendingUp className="h-3 w-3 mr-1" />
          +{trend.toFixed(1)}%
        </Badge>
      );
    } else if (trend < 0) {
      return (
        <Badge variant="default" className="bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400">
          <TrendingDown className="h-3 w-3 mr-1" />
          {trend.toFixed(1)}%
        </Badge>
      );
    } else {
      return (
        <Badge variant="default" className="bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400">
          <Minus className="h-3 w-3 mr-1" />
          0%
        </Badge>
      );
    }
  };

  return (
    <div className="w-full min-h-screen bg-white dark:bg-gray-950 space-y-8">
      <div className="max-w-[1200px] mx-auto px-8 py-8">
        {/* Header Section */}
        <div className="border-b pb-6 break-inside-avoid">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold mb-2">Detailed Analytics Report</h1>
              <p className="text-muted-foreground">Complete Performance Analysis & Metrics</p>
            </div>
            <div className="text-right">
              <p className="text-sm text-muted-foreground">Report Period</p>
              <p className="font-semibold">{new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}</p>
              <p className="text-xs text-muted-foreground mt-1">Generated: {new Date().toLocaleString()}</p>
            </div>
          </div>
        </div>

        {/* Overview Metrics Grid */}
        <div className="mt-8">
          <h2 className="text-2xl font-bold mb-6 break-after-avoid">Performance Overview</h2>
          <div className="grid grid-cols-4 gap-4 break-inside-avoid">
            <Card className="p-5 border border-border">
              <div className="flex items-center justify-between mb-2">
                <Eye className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                {renderTrendBadge(visibilityTrend)}
              </div>
              <p className="text-sm text-muted-foreground mb-1">Visibility Score</p>
              <p className="text-2xl font-bold">{visibilityScore.toFixed(1)}</p>
              <p className="text-xs text-muted-foreground mt-1">
                Previous: {(visibilityScore - visibilityTrend).toFixed(1)}
              </p>
            </Card>

            <Card className="p-5 border border-border">
              <div className="flex items-center justify-between mb-2">
                <MessageSquare className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                {renderTrendBadge(mentionsTrend)}
              </div>
              <p className="text-sm text-muted-foreground mb-1">Total Mentions</p>
              <p className="text-2xl font-bold">{totalMentions.toLocaleString()}</p>
              <p className="text-xs text-muted-foreground mt-1">
                Previous: {Math.round(totalMentions / (1 + mentionsTrend / 100)).toLocaleString()}
              </p>
            </Card>

            <Card className="p-5 border border-border">
              <div className="flex items-center justify-between mb-2">
                <Activity className="h-5 w-5 text-green-600 dark:text-green-400" />
                {renderTrendBadge(mentionsTrend)}
              </div>
              <p className="text-sm text-muted-foreground mb-1">Daily Avg Mentions</p>
              <p className="text-2xl font-bold">{dailyAvgMentions}</p>
              <p className="text-xs text-muted-foreground mt-1">
                Previous: {Math.round(dailyAvgMentions / (1 + mentionsTrend / 100))}
              </p>
            </Card>

            <Card className="p-5 border border-border">
              <div className="flex items-center justify-between mb-2">
                <Globe className="h-5 w-5 text-amber-600 dark:text-amber-400" />
                <Badge variant="default" className="bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400">
                  <Minus className="h-3 w-3 mr-1" />
                  0%
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground mb-1">Platforms Tracked</p>
              <p className="text-2xl font-bold">{platforms.length}</p>
              <p className="text-xs text-muted-foreground mt-1">
                {platforms.map((p: any) => p.platform).join(', ') || 'No platforms'}
              </p>
            </Card>
          </div>
        </div>

        {/* Sentiment Analysis Deep Dive */}
        <div className="mt-8 break-inside-avoid">
          <h2 className="text-2xl font-bold mb-6 break-after-avoid">Sentiment Analysis</h2>
          <div className="grid grid-cols-3 gap-6">
            <Card className="p-6 border border-border break-inside-avoid">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">Overall Sentiment</h3>
                <ThumbsUp className="h-5 w-5 text-green-600 dark:text-green-400" />
              </div>
              <div className="space-y-4">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-green-500"></div>
                      Positive
                    </span>
                    <span className="text-sm font-bold">{sentimentScore.toFixed(0)}%</span>
                  </div>
                  <div className="h-2 bg-muted rounded-full overflow-hidden">
                    <div className="h-full bg-green-500" style={{ width: `${sentimentScore}%` }}></div>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">{positiveMentions.toLocaleString()} mentions</p>
                </div>
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-gray-500"></div>
                      Neutral
                    </span>
                    <span className="text-sm font-bold">{neutralSentiment.toFixed(0)}%</span>
                  </div>
                  <div className="h-2 bg-muted rounded-full overflow-hidden">
                    <div className="h-full bg-gray-500" style={{ width: `${neutralSentiment}%` }}></div>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">{neutralMentions.toLocaleString()} mentions</p>
                </div>
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-red-500"></div>
                      Negative
                    </span>
                    <span className="text-sm font-bold">{negativeSentiment.toFixed(0)}%</span>
                  </div>
                  <div className="h-2 bg-muted rounded-full overflow-hidden">
                    <div className="h-full bg-red-500" style={{ width: `${negativeSentiment}%` }}></div>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">{negativeMentions.toLocaleString()} mentions</p>
                </div>
              </div>
            </Card>

            <Card className="p-6 border border-border break-inside-avoid">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">Sentiment by Platform</h3>
                <BarChart3 className="h-5 w-5 text-primary" />
              </div>
              <div className="space-y-3">
                {platformStats.length > 0 ? (
                  platformStats.slice(0, 5).map((platform: any, index: number) => (
                    <div key={index} className="flex items-center justify-between p-2 rounded bg-muted/30">
                      <span className="text-sm font-medium">{platform.model_name}</span>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400 text-xs">
                          {sentimentScore.toFixed(0)}%
                        </Badge>
                        <TrendingUp className="h-3 w-3 text-green-600" />
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-4 text-muted-foreground text-sm">
                    No platform data available
                  </div>
                )}
              </div>
            </Card>

            <Card className="p-6 border border-border break-inside-avoid bg-gradient-to-br from-white to-gray-50/50 dark:from-gray-900 dark:to-gray-900/50">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold">Key Insights & Performance</h3>
                <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/20">
                  <Activity className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                </div>
              </div>
              <div className="space-y-4">
                {sentimentScore > 0 && (
                  <div className="relative overflow-hidden rounded-lg bg-gradient-to-r from-green-50 to-green-100/50 dark:from-green-900/20 dark:to-green-900/10 border border-green-200 dark:border-green-900/30 p-4 transition-all hover:shadow-md">
                    <div className="absolute top-0 right-0 w-24 h-24 bg-green-500/5 rounded-full -mr-12 -mt-12"></div>
                    <div className="relative">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <div className="p-1.5 rounded-md bg-green-500/10">
                            <ArrowUpRight className="h-4 w-4 text-green-600 dark:text-green-500" />
                          </div>
                          <span className="text-sm font-semibold text-green-900 dark:text-green-100">Positive Sentiment</span>
                        </div>
                        <Badge className="bg-green-600 text-white hover:bg-green-700 dark:bg-green-500 dark:hover:bg-green-600">
                          {sentimentScore.toFixed(0)}%
                        </Badge>
                      </div>
                      <div className="ml-8 space-y-1">
                        <p className="text-sm font-medium text-green-800 dark:text-green-200">
                          {positiveMentions.toLocaleString()} positive mentions
                        </p>
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-1.5 bg-green-200 dark:bg-green-900/30 rounded-full overflow-hidden">
                            <div className="h-full bg-green-500 rounded-full" style={{ width: `${sentimentScore}%` }}></div>
                          </div>
                          <span className="text-xs text-green-700 dark:text-green-300 font-medium">Strong</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                {totalCitations > 0 && (
                  <div className="relative overflow-hidden rounded-lg bg-gradient-to-r from-blue-50 to-blue-100/50 dark:from-blue-900/20 dark:to-blue-900/10 border border-blue-200 dark:border-blue-900/30 p-4 transition-all hover:shadow-md">
                    <div className="absolute top-0 right-0 w-24 h-24 bg-blue-500/5 rounded-full -mr-12 -mt-12"></div>
                    <div className="relative">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <div className="p-1.5 rounded-md bg-blue-500/10">
                            <Award className="h-4 w-4 text-blue-600 dark:text-blue-500" />
                          </div>
                          <span className="text-sm font-semibold text-blue-900 dark:text-blue-100">Citation Authority</span>
                        </div>
                        <Badge className="bg-blue-600 text-white hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600">
                          {((totalCitations / totalMentions) * 100).toFixed(1)}%
                        </Badge>
                      </div>
                      <div className="ml-8 space-y-1">
                        <p className="text-sm font-medium text-blue-800 dark:text-blue-200">
                          {totalCitations} total citations
                        </p>
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-1.5 bg-blue-200 dark:bg-blue-900/30 rounded-full overflow-hidden">
                            <div className="h-full bg-blue-500 rounded-full" style={{ width: `${((totalCitations / totalMentions) * 100)}%` }}></div>
                          </div>
                          <span className="text-xs text-blue-700 dark:text-blue-300 font-medium">
                            {totalCitations}/{totalMentions}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                {negativeMentions > 0 && (
                  <div className="relative overflow-hidden rounded-lg bg-gradient-to-r from-amber-50 to-amber-100/50 dark:from-amber-900/20 dark:to-amber-900/10 border border-amber-200 dark:border-amber-900/30 p-4 transition-all hover:shadow-md">
                    <div className="absolute top-0 right-0 w-24 h-24 bg-amber-500/5 rounded-full -mr-12 -mt-12"></div>
                    <div className="relative">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <div className="p-1.5 rounded-md bg-amber-500/10">
                            <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-500" />
                          </div>
                          <span className="text-sm font-semibold text-amber-900 dark:text-amber-100">Watch Area</span>
                        </div>
                        <Badge className="bg-amber-600 text-white hover:bg-amber-700 dark:bg-amber-500 dark:hover:bg-amber-600">
                          {negativeSentiment.toFixed(1)}%
                        </Badge>
                      </div>
                      <div className="ml-8 space-y-1">
                        <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
                          {negativeMentions} negative mentions
                        </p>
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-1.5 bg-amber-200 dark:bg-amber-900/30 rounded-full overflow-hidden">
                            <div className="h-full bg-amber-500 rounded-full" style={{ width: `${negativeSentiment}%` }}></div>
                          </div>
                          <span className="text-xs text-amber-700 dark:text-amber-300 font-medium">Monitor</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </Card>
          </div>
        </div>

        {/* Platform Distribution & Performance */}
        <div className="mt-8 break-inside-avoid">
          <h2 className="text-2xl font-bold mb-6 break-after-avoid">Platform Distribution & Performance</h2>
          <div className="grid grid-cols-2 gap-6">
            <Card className="p-6 border border-border break-inside-avoid">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <PieChart className="h-5 w-5 text-primary" />
                Mention Distribution
              </h3>
              <div className="space-y-3">
                {platformStats.length > 0 ? (
                  platformStats.map((platform: any, index: number) => {
                    const colors = ['bg-blue-500', 'bg-purple-500', 'bg-amber-500', 'bg-green-500', 'bg-pink-500'];
                    const dotColors = ['bg-blue-500', 'bg-purple-500', 'bg-amber-500', 'bg-green-500', 'bg-pink-500'];
                    return (
                      <div key={index}>
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <div className={`w-3 h-3 rounded-full ${dotColors[index % dotColors.length]}`}></div>
                            <span className="text-sm font-medium">{platform.model_name}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-bold">{platform.mention_count}</span>
                            <span className="text-xs text-muted-foreground">({platform.percentage}%)</span>
                          </div>
                        </div>
                        <div className="h-2 bg-muted rounded-full overflow-hidden">
                          <div className={`h-full ${colors[index % colors.length]}`} style={{ width: `${platform.percentage}%` }}></div>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="text-center py-4 text-muted-foreground text-sm">
                    No platform data available
                  </div>
                )}
              </div>
            </Card>

            <Card className="p-6 border border-border break-inside-avoid">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-primary" />
                Platform Performance
              </h3>
              <div className="space-y-3">
                {platformStats.length > 0 ? (
                  platformStats.map((platform: any, index: number) => (
                    <div key={index} className="flex items-center justify-between p-3 rounded bg-muted/30">
                      <div>
                        <p className="text-sm font-medium">{platform.model_name}</p>
                        <p className="text-xs text-muted-foreground">{platform.mention_count} mentions</p>
                      </div>
                      <div className="flex items-center gap-2">
                        {renderTrendBadge(mentionsTrend)}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-4 text-muted-foreground text-sm">
                    No platform data available
                  </div>
                )}
              </div>
            </Card>
          </div>
        </div>

        {/* Citation Analysis */}
        <div className="mt-8 break-inside-avoid">
          <h2 className="text-2xl font-bold mb-6 break-after-avoid">Citation & Authority Metrics</h2>
          <div className="grid grid-cols-4 gap-4">
            <Card className="p-5 border border-border">
              <div className="flex items-center gap-2 mb-2">
                <FileText className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                <span className="text-sm text-muted-foreground">Total Citations</span>
              </div>
              <p className="text-2xl font-bold">{totalCitations}</p>
              {renderTrendBadge(citationsTrend)}
            </Card>

            <Card className="p-5 border border-border">
              <div className="flex items-center gap-2 mb-2">
                <Target className="h-5 w-5 text-green-600 dark:text-green-400" />
                <span className="text-sm text-muted-foreground">Citation Rate</span>
              </div>
              <p className="text-2xl font-bold">
                {totalMentions > 0 ? ((totalCitations / totalMentions) * 100).toFixed(1) : 0}%
              </p>
              <Badge variant="outline" className="mt-2 text-xs">
                {totalCitations} of {totalMentions}
              </Badge>
            </Card>

            <Card className="p-5 border border-border">
              <div className="flex items-center gap-2 mb-2">
                <Activity className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                <span className="text-sm text-muted-foreground">Avg Position</span>
              </div>
              <p className="text-2xl font-bold">{avgPosition > 0 ? avgPosition.toFixed(1) : 'N/A'}</p>
              <Badge variant="outline" className="mt-2 text-xs">
                In responses
              </Badge>
            </Card>

            <Card className="p-5 border border-border">
              <div className="flex items-center gap-2 mb-2">
                <Award className="h-5 w-5 text-amber-600 dark:text-amber-400" />
                <span className="text-sm text-muted-foreground">Visibility Score</span>
              </div>
              <p className="text-2xl font-bold">{visibilityScore.toFixed(1)}</p>
              {renderTrendBadge(visibilityTrend)}
            </Card>
          </div>
        </div>

        {/* Competitive Analysis */}
        {shareOfVoice && shareOfVoice.competitors && shareOfVoice.competitors.length > 0 && (
          <div className="mt-8 break-inside-avoid">
            <h2 className="text-2xl font-bold mb-6 break-after-avoid">Competitive Landscape</h2>
            <Card className="p-6 border border-border">
              <h3 className="text-lg font-semibold mb-4">Market Share Distribution</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 bg-green-50 dark:bg-green-900/10 rounded-lg border border-green-200 dark:border-green-900/30">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-white dark:bg-gray-800 flex items-center justify-center border-2 border-primary shadow-sm overflow-hidden">
                      <img
                        src={getFaviconUrl(domainUrl || domainName)}
                        alt={domainName}
                        className="w-6 h-6 object-contain"
                        onError={(e) => {
                          e.currentTarget.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(domainName)}&background=0EA5E9&color=fff`;
                        }}
                      />
                    </div>
                    <div>
                      <span className="font-semibold">{domainName}</span>
                      <p className="text-xs text-muted-foreground">Your Brand</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-bold">{shareOfVoice.your_brand?.share_percentage?.toFixed(1)}%</p>
                    <p className="text-xs text-muted-foreground">Share of Voice</p>
                  </div>
                </div>
                {shareOfVoice.competitors.slice(0, 5).map((competitor: any, index: number) => (
                  <div key={index} className="flex items-center justify-between p-3 bg-muted/30 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-white dark:bg-gray-800 flex items-center justify-center border border-muted-foreground/20 shadow-sm overflow-hidden">
                        <img
                          src={getFaviconUrl(competitor.url || competitor.name)}
                          alt={competitor.name}
                          className="w-6 h-6 object-contain"
                          onError={(e) => {
                            e.currentTarget.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(competitor.name)}&background=random`;
                          }}
                        />
                      </div>
                      <div>
                        <span className="font-medium">{competitor.name}</span>
                        <p className="text-xs text-muted-foreground">Competitor</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-bold text-muted-foreground">{competitor.share_percentage?.toFixed(1)}%</p>
                      <p className="text-xs text-muted-foreground">Share of Voice</p>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        )}

        {/* Alerts & Issues */}
        {data?.alerts && data.alerts.length > 0 && (
          <div className="mt-8 break-inside-avoid">
            <h2 className="text-2xl font-bold mb-6 break-after-avoid">Alerts & Quality Monitoring</h2>
            <Card className="p-6 border border-border">
              <h3 className="text-lg font-semibold mb-4">Active Alerts</h3>
              <div className="space-y-3">
                {data.alerts.map((alert: any, index: number) => (
                  <div
                    key={index}
                    className={`p-4 rounded border ${
                      alert.severity === 'high'
                        ? 'bg-red-50 dark:bg-red-900/10 border-red-200 dark:border-red-900/30'
                        : 'bg-amber-50 dark:bg-amber-900/10 border-amber-200 dark:border-amber-900/30'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <AlertTriangle
                          className={`h-4 w-4 flex-shrink-0 mt-0.5 ${
                            alert.severity === 'high' ? 'text-red-600' : 'text-amber-600'
                          }`}
                        />
                        <span className="text-sm font-semibold">{alert.title}</span>
                      </div>
                      <Badge
                        variant={alert.severity === 'high' ? 'destructive' : 'secondary'}
                        className={
                          alert.severity === 'high'
                            ? 'text-xs'
                            : 'bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400 text-xs'
                        }
                      >
                        {alert.severity === 'high' ? 'Critical' : 'Warning'}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground ml-6">{alert.description}</p>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        )}

        {/* No Alerts State */}
        {(!data?.alerts || data.alerts.length === 0) && (
          <div className="mt-8 break-inside-avoid">
            <h2 className="text-2xl font-bold mb-6 break-after-avoid">Alerts & Quality Monitoring</h2>
            <Card className="p-6 border border-border bg-green-50/50 dark:bg-green-900/10 border-l-4 border-l-green-500">
              <div className="flex items-start gap-3">
                <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-semibold mb-2">All Systems Operational</h4>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    No critical alerts or quality issues detected. All metrics are performing within normal parameters.
                  </p>
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* Footer */}
        <div className="pt-6 border-t">
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <p>Detailed Analytics Report - AI Visibility Monitor</p>
            <p>Page 1 of 1 | Confidential</p>
          </div>
        </div>
      </div>
    </div>
  );
};
