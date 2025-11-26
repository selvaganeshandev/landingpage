import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import {
  TrendingUp,
  TrendingDown,
  Lightbulb,
  Target,
  Zap,
  AlertTriangle,
  CheckCircle2,
  FileText,
  Sparkles,
  BookOpen,
  MessageSquare,
  Search,
  Users,
  Calendar,
  Star,
  Award,
  ArrowUpRight,
  ArrowDownRight,
  Plus,
  Minus,
  Brain,
  Telescope,
  Flame,
  Trophy
} from "lucide-react";

interface TopicPerformance {
  name: string;
  keywords?: string[];
  coverage_score: number;
  mentions: number;
  engagement?: number;
  growth: number;
  sentiment: number;
}

interface ContentGap {
  keyword: string;
  search_volume: number;
  competitor_coverage: number;
  opportunity_score: number;
  estimated_traffic: number;
  priority: string;
}

interface KeywordData {
  keyword: string;
  mentions: number;
  growth?: number;
  priority?: string;
  search_volume: number;
}

interface Recommendation {
  priority: number;
  title: string;
  description: string;
  timeline: string;
  content_pieces: string;
  expected_traffic: string;
}

interface ContentStrategyData {
  period?: {
    start: string;
    end: string;
  };
  domain_name?: string;
  domain_url?: string;
  overview?: {
    content_quality_score: number;
    topics_covered: number;
    topics_growth: number;
    content_gaps_found: number;
    engagement_rate: number;
    engagement_growth: number;
  };
  content_gaps?: ContentGap[];
  topic_performance?: TopicPerformance[];
  untapped_keywords?: KeywordData[];
  trending_keywords?: KeywordData[];
  competitor_comparison?: any[];
  recommendations?: Recommendation[];
}

interface ContentStrategyTemplateProps {
  data: ContentStrategyData | null;
}

export const ContentStrategyTemplate = ({ data }: ContentStrategyTemplateProps) => {
  // Extract data from API response with defaults
  const overview = data?.overview || {
    content_quality_score: 0,
    topics_covered: 0,
    topics_growth: 0,
    content_gaps_found: 0,
    engagement_rate: 0,
    engagement_growth: 0,
  };
  const contentGaps = data?.content_gaps || [];
  const topicPerformance = data?.topic_performance || [];
  const untappedKeywords = data?.untapped_keywords || [];
  const trendingKeywords = data?.trending_keywords || [];
  const competitors = data?.competitor_comparison || [];
  const recommendations = data?.recommendations || [];
  const domainName = data?.domain_name || 'Your Brand';
  const period = data?.period;

  // Format period for display
  const periodDisplay = period
    ? `${new Date(period.start).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${new Date(period.end).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`
    : new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

  const getGradeFromScore = (score: number) => {
    if (score >= 90) return 'A+';
    if (score >= 80) return 'A';
    if (score >= 70) return 'B';
    if (score >= 60) return 'C';
    return 'D';
  };

  const getTopicBadgeColor = (coverage: number) => {
    if (coverage >= 80) return { bg: 'bg-green-600', text: 'Excellent' };
    if (coverage >= 60) return { bg: 'bg-blue-600', text: 'Good' };
    if (coverage >= 40) return { bg: 'bg-amber-600', text: 'Needs Work' };
    return { bg: 'bg-red-600', text: 'Critical Gap' };
  };

  const getTopicRowColor = (coverage: number) => {
    if (coverage >= 80) return 'bg-green-50 dark:bg-green-900/10 border-green-200 dark:border-green-900/30';
    if (coverage >= 60) return 'bg-blue-50 dark:bg-blue-900/10 border-blue-200 dark:border-blue-900/30';
    if (coverage >= 40) return 'bg-amber-50 dark:bg-amber-900/10 border-amber-200 dark:border-amber-900/30';
    return 'bg-red-50 dark:bg-red-900/10 border-red-200 dark:border-red-900/30';
  };

  const getTopicIcon = (coverage: number) => {
    if (coverage >= 60) return <CheckCircle2 className={`h-5 w-5 ${coverage >= 80 ? 'text-green-600' : 'text-blue-600'}`} />;
    return <AlertTriangle className={`h-5 w-5 ${coverage >= 40 ? 'text-amber-600' : 'text-red-600'}`} />;
  };

  const getTrendColor = (growth: number) => {
    if (growth > 10) return 'text-green-600';
    if (growth > 0) return 'text-blue-600';
    if (growth < 0) return 'text-red-600';
    return 'text-muted-foreground';
  };

  return (
    <div className="w-full min-h-screen bg-white dark:bg-gray-950 space-y-8">
      <div className="max-w-[1200px] mx-auto px-8 py-8">
      {/* Header Section */}
      <div className="border-b pb-6 break-inside-avoid">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">Content Strategy Report</h1>
            <p className="text-muted-foreground">Gap Analysis, Opportunities & Recommendations for {domainName}</p>
          </div>
          <div className="text-right">
            <p className="text-sm text-muted-foreground">Report Period</p>
            <p className="font-semibold">{periodDisplay}</p>
          </div>
        </div>
      </div>

      {/* Content Performance Overview */}
      <div>
        <h2 className="text-2xl font-bold mb-6">Content Performance Overview</h2>
        <div className="grid grid-cols-4 gap-4">
          <Card className="p-5 border border-border">
            <div className="flex items-center justify-between mb-3">
              <FileText className="h-6 w-6 text-blue-600 dark:text-blue-400" />
              <Badge variant="outline">
                <Trophy className="h-3 w-3 mr-1" />
                {getGradeFromScore(overview.content_quality_score)}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mb-1">Content Quality Score</p>
            <p className="text-3xl font-bold">{Math.round(overview.content_quality_score)}/100</p>
            <p className="text-xs text-muted-foreground mt-2">
              {overview.content_quality_score >= 90 ? 'Excellent performance' : overview.content_quality_score >= 70 ? 'Good performance' : 'Needs improvement'}
            </p>
          </Card>

          <Card className="p-5 border border-border">
            <div className="flex items-center justify-between mb-3">
              <Target className="h-6 w-6 text-green-600 dark:text-green-400" />
              <Badge variant="outline" className={overview.topics_growth > 0 ? "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400" : overview.topics_growth < 0 ? "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400" : ""}>
                {overview.topics_growth > 0 ? <TrendingUp className="h-3 w-3 mr-1" /> : overview.topics_growth < 0 ? <TrendingDown className="h-3 w-3 mr-1" /> : <Minus className="h-3 w-3 mr-1" />}
                {overview.topics_growth > 0 ? '+' : ''}{Math.round(overview.topics_growth)}%
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mb-1">Topics Covered</p>
            <p className="text-3xl font-bold">{overview.topics_covered}</p>
            <p className="text-xs text-muted-foreground mt-2">
              {overview.topics_growth > 0 ? `Growing steadily` : 'Monitor performance'}
            </p>
          </Card>

          <Card className="p-5 border border-border">
            <div className="flex items-center justify-between mb-3">
              <Sparkles className="h-6 w-6 text-purple-600 dark:text-purple-400" />
              <Badge variant="outline">
                <Flame className="h-3 w-3 mr-1" />
                {overview.content_gaps_found > 10 ? 'Hot' : overview.content_gaps_found > 0 ? 'Warm' : 'Cold'}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mb-1">Content Gaps Found</p>
            <p className="text-3xl font-bold">{overview.content_gaps_found}</p>
            <p className="text-xs text-muted-foreground mt-2">
              {overview.content_gaps_found > 10 ? 'High opportunity areas' : overview.content_gaps_found > 0 ? 'Moderate opportunities' : 'Good coverage'}
            </p>
          </Card>

          <Card className="p-5 border border-border">
            <div className="flex items-center justify-between mb-3">
              <Award className="h-6 w-6 text-amber-600 dark:text-amber-400" />
              <Badge variant="outline" className={overview.engagement_growth > 0 ? "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400" : overview.engagement_growth < 0 ? "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400" : ""}>
                {overview.engagement_growth > 0 ? <TrendingUp className="h-3 w-3 mr-1" /> : overview.engagement_growth < 0 ? <TrendingDown className="h-3 w-3 mr-1" /> : <Minus className="h-3 w-3 mr-1" />}
                {overview.engagement_growth > 0 ? '+' : ''}{Math.round(overview.engagement_growth)}%
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mb-1">Engagement Rate</p>
            <p className="text-3xl font-bold">{Math.round(overview.engagement_rate)}%</p>
            <p className="text-xs text-muted-foreground mt-2">
              {overview.engagement_rate >= 80 ? 'Above industry avg' : 'Room for growth'}
            </p>
          </Card>
        </div>
      </div>

      {/* Content Gap Analysis */}
      <div>
        <h2 className="text-2xl font-bold mb-6">Content Gap Analysis</h2>
        <Card className="p-6 border border-border">
          {contentGaps.length > 0 ? (
          <div className="space-y-4">
            {contentGaps.slice(0, 5).map((gap, index) => {
              const priority = gap.priority || 'Medium';
              const borderColor = priority === 'Critical' ? 'border-red-500' : priority === 'High' ? 'border-amber-500' : 'border-blue-500';
              const bgColor = priority === 'Critical' ? 'bg-red-50 dark:bg-red-900/10' : priority === 'High' ? 'bg-amber-50 dark:bg-amber-900/10' : 'bg-blue-50 dark:bg-blue-900/10';
              const iconBg = priority === 'Critical' ? 'bg-red-600' : priority === 'High' ? 'bg-amber-600' : 'bg-blue-600';
              const IconComponent = priority === 'Critical' ? AlertTriangle : priority === 'High' ? Lightbulb : Telescope;

              return (
                <div key={index} className={`p-5 rounded-lg ${bgColor} ${index === 0 ? 'border-2' : 'border'} ${borderColor}`}>
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-full ${iconBg} flex items-center justify-center`}>
                        <IconComponent className="h-5 w-5 text-white" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="text-lg font-bold">{gap.keyword}</h3>
                          <Badge variant={priority === 'Critical' ? 'destructive' : 'secondary'} className={priority === 'High' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400' : ''}>
                            {priority === 'Critical' ? 'Critical Gap' : priority === 'High' ? 'High Opportunity' : 'Moderate Opportunity'}
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {gap.competitor_coverage === 0 ? 'High search volume, zero current coverage' : 'Growing trend, limited current content'}
                        </p>
                      </div>
                    </div>
                    <Badge className={iconBg + ' text-white'}>Priority {index + 1}</Badge>
                  </div>
                  <div className={`grid grid-cols-4 gap-4 mt-4 pt-4 border-t ${priority === 'Critical' ? 'border-red-200 dark:border-red-900/30' : priority === 'High' ? 'border-amber-200 dark:border-amber-900/30' : 'border-blue-200 dark:border-blue-900/30'}`}>
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Search Volume</p>
                      <p className="text-lg font-bold">{gap.search_volume?.toLocaleString() || 0}/mo</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Competitor Coverage</p>
                      <p className="text-lg font-bold">{gap.competitor_coverage || 0}/5</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Opportunity Score</p>
                      <p className={`text-lg font-bold ${priority === 'Critical' ? 'text-red-600' : priority === 'High' ? 'text-amber-600' : 'text-blue-600'}`}>
                        {gap.opportunity_score || 0}/100
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Est. Traffic Gain</p>
                      <p className="text-lg font-bold">+{gap.estimated_traffic?.toLocaleString() || 0}/mo</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
          ) : (
            <div className="text-center py-12">
              <CheckCircle2 className="h-12 w-12 text-green-600 mx-auto mb-3" />
              <h3 className="text-lg font-semibold mb-2">Excellent Content Coverage!</h3>
              <p className="text-muted-foreground">No critical content gaps detected. Your content strategy is performing well.</p>
            </div>
          )}
        </Card>
      </div>

      {/* Keyword Opportunities */}
      <div>
        <h2 className="text-2xl font-bold mb-6">High-Value Keyword Opportunities</h2>
        <div className="grid grid-cols-2 gap-6">
          <Card className="p-6 border border-border">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Search className="h-5 w-5 text-primary" />
              Untapped Keywords
            </h3>
            <div className="space-y-3">
              {untappedKeywords.length > 0 ? (
                untappedKeywords.slice(0, 5).map((kw, index) => {
                  const priorityColor = kw.priority === 'High' ? 'bg-green-50 dark:bg-green-900/10 border-green-200 dark:border-green-900/30' : 'bg-amber-50 dark:bg-amber-900/10 border-amber-200 dark:border-amber-900/30';
                  const badgeColor = kw.priority === 'High' ? 'bg-green-600' : 'bg-amber-600';
                  return (
                    <div key={index} className={`flex items-center justify-between p-3 rounded border ${priorityColor}`}>
                      <div>
                        <p className="text-sm font-semibold">{kw.keyword}</p>
                        <p className="text-xs text-muted-foreground">Zero current mentions</p>
                      </div>
                      <div className="text-right">
                        <Badge className={`${badgeColor} text-white mb-1`}>{kw.priority || 'Med'}</Badge>
                        <p className="text-xs text-muted-foreground">{kw.search_volume?.toLocaleString() || 0}/mo</p>
                      </div>
                    </div>
                  );
                })
              ) : (
                <p className="text-sm text-muted-foreground text-center py-4">No untapped keywords identified. Add keywords to your domain to track opportunities.</p>
              )}
            </div>
          </Card>

          <Card className="p-6 border border-border">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-primary" />
              Trending Topics to Amplify
            </h3>
            <div className="space-y-3">
              {trendingKeywords.length > 0 ? (
                trendingKeywords.slice(0, 4).map((kw, index) => {
                  const colors = [
                    'bg-blue-50 dark:bg-blue-900/10 border-blue-200 dark:border-blue-900/30',
                    'bg-purple-50 dark:bg-purple-900/10 border-purple-200 dark:border-purple-900/30',
                    'bg-green-50 dark:bg-green-900/10 border-green-200 dark:border-green-900/30',
                    'bg-amber-50 dark:bg-amber-900/10 border-amber-200 dark:border-amber-900/30',
                  ];
                  const badgeColors = ['bg-blue-600', 'bg-purple-600', 'bg-green-600', 'bg-amber-600'];
                  return (
                    <div key={index} className={`p-3 rounded border ${colors[index % colors.length]}`}>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-semibold">{kw.keyword}</span>
                        <Badge className={`${badgeColors[index % badgeColors.length]} text-white`}>
                          <TrendingUp className="h-3 w-3 mr-1" />
                          +{Math.round(kw.growth || 0)}%
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground mb-2">
                        {(kw.growth || 0) > 50 ? 'Growing fast, maintain momentum' : 'Steady growth, amplify further'}
                      </p>
                      <div className="flex gap-2">
                        <Badge variant="outline" className="text-xs">{kw.mentions} mentions</Badge>
                        <Badge variant="outline" className="text-xs">{kw.search_volume?.toLocaleString() || 0}/mo</Badge>
                      </div>
                    </div>
                  );
                })
              ) : (
                <p className="text-sm text-muted-foreground text-center py-4">No trending keywords detected in this period.</p>
              )}
            </div>
          </Card>
        </div>
      </div>

      {/* Content Performance by Topic */}
      {topicPerformance.length > 0 && (
        <div>
          <h2 className="text-2xl font-bold mb-6">Content Performance by Topic Category</h2>
          <Card className="p-6 border border-border">
            <div className="space-y-4">
              {topicPerformance.slice(0, 6).map((topic, index) => {
                const badgeInfo = getTopicBadgeColor(topic.coverage_score);
                const rowColor = getTopicRowColor(topic.coverage_score);
                const icon = getTopicIcon(topic.coverage_score);

                return (
                  <div key={index} className={`flex items-center justify-between p-4 rounded border ${rowColor}`}>
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        {icon}
                        <h4 className="font-semibold">{topic.name}</h4>
                        <Badge className={`${badgeInfo.bg} text-white`}>{badgeInfo.text}</Badge>
                      </div>
                      <div className="grid grid-cols-4 gap-4 text-sm">
                        <div>
                          <p className="text-muted-foreground text-xs">Coverage</p>
                          <p className="font-bold">{Math.round(topic.coverage_score)}/100</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground text-xs">Mentions</p>
                          <p className="font-bold">{topic.mentions?.toLocaleString() || 0}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground text-xs">Sentiment</p>
                          <p className="font-bold">{((topic.sentiment || 0) * 100).toFixed(0)}%</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground text-xs">Growth</p>
                          <p className={`font-bold ${getTrendColor(topic.growth)}`}>
                            {topic.growth > 0 ? '+' : ''}{Math.round(topic.growth)}%
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>
      )}

      {/* No Topics Message */}
      {topicPerformance.length === 0 && (
        <div>
          <h2 className="text-2xl font-bold mb-6">Content Performance by Topic Category</h2>
          <Card className="p-6 border border-border">
            <div className="text-center py-12">
              <Target className="h-12 w-12 text-muted-foreground mx-auto mb-3 opacity-50" />
              <h3 className="text-lg font-semibold mb-2">No Topics Configured</h3>
              <p className="text-muted-foreground">Add topics to your domain to track content performance by category.</p>
            </div>
          </Card>
        </div>
      )}

      {/* Strategic Recommendations */}
      <div>
        <h2 className="text-2xl font-bold mb-6">Strategic Content Recommendations</h2>
        <div className="space-y-3">
          {recommendations.length > 0 ? (
            recommendations.slice(0, 5).map((rec, index) => {
              const colors = [
                { border: 'border-l-red-500', bg: 'bg-red-50/50 dark:bg-red-900/10', badge: 'bg-red-600' },
                { border: 'border-l-amber-500', bg: 'bg-amber-50/50 dark:bg-amber-900/10', badge: 'bg-amber-600' },
                { border: 'border-l-green-500', bg: 'bg-green-50/50 dark:bg-green-900/10', badge: 'bg-green-600' },
                { border: 'border-l-blue-500', bg: 'bg-blue-50/50 dark:bg-blue-900/10', badge: 'bg-blue-600' },
                { border: 'border-l-purple-500', bg: 'bg-purple-50/50 dark:bg-purple-900/10', badge: 'bg-purple-600' },
              ];
              const color = colors[index % colors.length];

              return (
                <div key={index} className={`p-5 border-l-4 ${color.border} ${color.bg} rounded-lg`}>
                  <div className="flex items-start gap-3">
                    <div className={`w-8 h-8 rounded-full ${color.badge} flex items-center justify-center text-sm font-bold text-white flex-shrink-0`}>
                      {rec.priority}
                    </div>
                    <div className="flex-1">
                      <h4 className="font-semibold mb-2">{rec.title}</h4>
                      <p className="text-sm text-muted-foreground mb-3">{rec.description}</p>
                      <div className="flex gap-2 flex-wrap">
                        <Badge variant="outline" className="text-xs">Timeline: {rec.timeline}</Badge>
                        <Badge variant="outline" className="text-xs">Content: {rec.content_pieces}</Badge>
                        <Badge variant="outline" className="text-xs">Expected: {rec.expected_traffic}</Badge>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })
          ) : (
            // Generate default recommendations based on data
            <div className="space-y-3">
              {contentGaps.length > 0 && (
                <div className="p-5 border-l-4 border-l-red-500 bg-red-50/50 dark:bg-red-900/10 rounded-lg">
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-full bg-red-600 flex items-center justify-center text-sm font-bold text-white flex-shrink-0">1</div>
                    <div className="flex-1">
                      <h4 className="font-semibold mb-2">Address Top Content Gaps</h4>
                      <p className="text-sm text-muted-foreground mb-3">
                        You have {contentGaps.length} content gap{contentGaps.length > 1 ? 's' : ''} identified.
                        Focus on "{contentGaps[0]?.keyword}" first with an opportunity score of {contentGaps[0]?.opportunity_score}/100.
                      </p>
                      <div className="flex gap-2">
                        <Badge variant="outline" className="text-xs">Priority: High</Badge>
                        <Badge variant="outline" className="text-xs">Est. Traffic: +{contentGaps[0]?.estimated_traffic?.toLocaleString() || 0}/mo</Badge>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {topicPerformance.filter(t => t.coverage_score < 60).length > 0 && (
                <div className="p-5 border-l-4 border-l-amber-500 bg-amber-50/50 dark:bg-amber-900/10 rounded-lg">
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-full bg-amber-600 flex items-center justify-center text-sm font-bold text-white flex-shrink-0">2</div>
                    <div className="flex-1">
                      <h4 className="font-semibold mb-2">Improve Low-Performing Topics</h4>
                      <p className="text-sm text-muted-foreground mb-3">
                        {topicPerformance.filter(t => t.coverage_score < 60).length} topic{topicPerformance.filter(t => t.coverage_score < 60).length > 1 ? 's need' : ' needs'} attention.
                        Focus on improving coverage to increase visibility.
                      </p>
                      <div className="flex gap-2">
                        <Badge variant="outline" className="text-xs">Priority: Medium</Badge>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {trendingKeywords.length > 0 && (
                <div className="p-5 border-l-4 border-l-green-500 bg-green-50/50 dark:bg-green-900/10 rounded-lg">
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-full bg-green-600 flex items-center justify-center text-sm font-bold text-white flex-shrink-0">3</div>
                    <div className="flex-1">
                      <h4 className="font-semibold mb-2">Capitalize on Trending Keywords</h4>
                      <p className="text-sm text-muted-foreground mb-3">
                        {trendingKeywords.length} keyword{trendingKeywords.length > 1 ? 's are' : ' is'} showing growth momentum.
                        Amplify content around these topics to maintain momentum.
                      </p>
                      <div className="flex gap-2">
                        <Badge variant="outline" className="text-xs">Priority: High</Badge>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {contentGaps.length === 0 && topicPerformance.length === 0 && trendingKeywords.length === 0 && (
                <div className="text-center py-8">
                  <Lightbulb className="h-12 w-12 text-muted-foreground mx-auto mb-3 opacity-50" />
                  <h3 className="text-lg font-semibold mb-2">Add More Data for Recommendations</h3>
                  <p className="text-muted-foreground">Configure topics, keywords, and prompts to receive strategic content recommendations.</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="pt-6 border-t">
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <p>Content Strategy Report - AI Visibility Monitor</p>
          <p>Confidential - Content Planning Use Only</p>
        </div>
      </div>
      </div>
    </div>
  );
};
