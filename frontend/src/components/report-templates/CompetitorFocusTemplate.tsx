import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import {
  TrendingUp,
  TrendingDown,
  Target,
  Users,
  Award,
  AlertCircle,
  Shield,
  Zap,
  BarChart3,
  PieChart,
  Activity,
  Eye,
  MessageSquare,
  ThumbsUp,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  Star,
  Crown,
  Flame,
  CheckCircle2,
  XCircle
} from "lucide-react";

interface CompetitorData {
  name: string;
  url?: string;
  mentions: number;
  visibility_score: number;
  sentiment_score: number;
  share_of_voice: number;
  average_position?: number;
  trend: number;
  status?: string;
}

interface OurMetrics {
  mentions: number;
  visibility_score: number;
  sentiment_score: number;
  share_of_voice: number;
  total_prompts: number;
}

interface PlatformData {
  platform: string;
  total: number;
  mentions: number;
  mention_rate: number;
}

interface CompetitorFocusData {
  period?: {
    start: string;
    end: string;
  };
  domain_name?: string;
  domain_url?: string;
  our_metrics?: OurMetrics;
  competitors?: CompetitorData[];
  total_competitors?: number;
  total_market_mentions?: number;
  platform_breakdown?: PlatformData[];
}

interface CompetitorFocusTemplateProps {
  data: CompetitorFocusData | null;
}

export const CompetitorFocusTemplate = ({ data }: CompetitorFocusTemplateProps) => {
  // Use data from props or fallback to empty/default values
  const domainName = data?.domain_name || 'Your Brand';
  const ourMetrics = data?.our_metrics || {
    mentions: 0,
    visibility_score: 0,
    sentiment_score: 0,
    share_of_voice: 0,
    total_prompts: 0,
  };
  const competitors = data?.competitors || [];
  const totalCompetitors = data?.total_competitors || competitors.length;
  const totalMarketMentions = data?.total_market_mentions || 0;
  const platformBreakdown = data?.platform_breakdown || [];
  const period = data?.period;

  // Calculate our rank based on share of voice
  const allEntities = [
    { name: domainName, share_of_voice: ourMetrics.share_of_voice, isOurs: true },
    ...competitors.map(c => ({ ...c, isOurs: false }))
  ].sort((a, b) => b.share_of_voice - a.share_of_voice);

  const ourRank = allEntities.findIndex(e => e.isOurs) + 1;
  const topCompetitor = competitors[0];
  const visibilityGap = topCompetitor ? (ourMetrics.visibility_score - topCompetitor.visibility_score).toFixed(1) : '0';

  // Count threats (competitors with positive trend > 5%)
  const risingThreats = competitors.filter(c => c.trend > 5).length;

  // Format period for display
  const periodDisplay = period
    ? `${new Date(period.start).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${new Date(period.end).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`
    : new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

  const getTrendIcon = (trend: number) => {
    if (trend > 0) return <TrendingUp className="h-3 w-3 mr-1" />;
    if (trend < 0) return <TrendingDown className="h-3 w-3 mr-1" />;
    return <Minus className="h-3 w-3 mr-1" />;
  };

  const getTrendColor = (trend: number) => {
    if (trend > 5) return 'text-green-600';
    if (trend < -5) return 'text-red-600';
    return 'text-muted-foreground';
  };

  const getStatusBadge = (competitor: CompetitorData, index: number) => {
    if (competitor.trend > 10) {
      return (
        <Badge variant="secondary" className="bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400">
          <AlertCircle className="h-3 w-3 mr-1" />
          Rising Threat
        </Badge>
      );
    }
    if (competitor.trend < -5) {
      return <Badge variant="secondary">Declining</Badge>;
    }
    return <Badge variant="secondary">Stable</Badge>;
  };

  return (
    <div className="w-full min-h-screen bg-white dark:bg-gray-950 space-y-8">
      <div className="max-w-[1200px] mx-auto px-8 py-8">
      {/* Header Section */}
      <div className="border-b pb-6 break-inside-avoid">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">Competitor Focus Report</h1>
            <p className="text-muted-foreground">Competitive Intelligence & Market Benchmarking</p>
          </div>
          <div className="text-right">
            <p className="text-sm text-muted-foreground">Report Period</p>
            <p className="font-semibold">{periodDisplay}</p>
          </div>
        </div>
      </div>

      {/* Market Position Overview */}
      <div>
        <h2 className="text-2xl font-bold mb-6">Market Position Overview</h2>
        <div className="grid grid-cols-4 gap-4">
          <Card className="p-5 border border-border bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/20 dark:to-green-900/10">
            <div className="flex items-center justify-between mb-3">
              <Crown className="h-6 w-6 text-green-600 dark:text-green-400" />
              <Badge className="bg-green-600 text-white">
                {getTrendIcon(parseFloat(visibilityGap))}
                #{ourRank}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mb-1">Your Rank</p>
            <p className="text-3xl font-bold">{ourRank === 1 ? 'Leader' : `#${ourRank}`}</p>
            <p className="text-xs text-muted-foreground mt-2">
              {ourRank === 1 ? 'Market Leader' : `${Math.abs(parseFloat(visibilityGap))} pts from #1`}
            </p>
          </Card>

          <Card className="p-5 border border-border">
            <div className="flex items-center justify-between mb-3">
              <Target className="h-6 w-6 text-blue-600 dark:text-blue-400" />
              <Badge variant="outline">
                {parseFloat(visibilityGap) >= 0 ? <TrendingUp className="h-3 w-3 mr-1" /> : <TrendingDown className="h-3 w-3 mr-1" />}
                {visibilityGap}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mb-1">Visibility Gap</p>
            <p className="text-3xl font-bold">{parseFloat(visibilityGap) >= 0 ? '+' : ''}{visibilityGap}</p>
            <p className="text-xs text-muted-foreground mt-2">
              {parseFloat(visibilityGap) >= 0 ? 'Points ahead of #2' : 'Points behind leader'}
            </p>
          </Card>

          <Card className="p-5 border border-border">
            <div className="flex items-center justify-between mb-3">
              <Users className="h-6 w-6 text-purple-600 dark:text-purple-400" />
              <Badge variant="outline">
                <Eye className="h-3 w-3 mr-1" />
                {totalCompetitors}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mb-1">Tracked Competitors</p>
            <p className="text-3xl font-bold">{totalCompetitors}</p>
            <p className="text-xs text-muted-foreground mt-2">Active monitoring</p>
          </Card>

          <Card className="p-5 border border-border">
            <div className="flex items-center justify-between mb-3">
              <Shield className="h-6 w-6 text-amber-600 dark:text-amber-400" />
              <Badge variant="outline">
                <Flame className="h-3 w-3 mr-1" />
                {risingThreats}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mb-1">Rising Threats</p>
            <p className="text-3xl font-bold">{risingThreats}</p>
            <p className="text-xs text-muted-foreground mt-2">
              {risingThreats > 0 ? 'Require attention' : 'None detected'}
            </p>
          </Card>
        </div>
      </div>

      {/* Competitive Ranking */}
      <div>
        <h2 className="text-2xl font-bold mb-6">Competitive Ranking</h2>
        <Card className="p-6 border border-border">
          <div className="space-y-4">
            {/* Your Brand */}
            <div className="p-5 rounded-lg bg-gradient-to-r from-green-50 to-green-100 dark:from-green-900/20 dark:to-green-900/10 border-2 border-green-500">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-green-600 flex items-center justify-center">
                    <Crown className="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <div className="flex items-center gap-3 mb-1">
                      <h3 className="text-lg font-bold">Your Brand ({domainName})</h3>
                      {ourRank === 1 && <Badge className="bg-green-600 text-white">Market Leader</Badge>}
                    </div>
                    <p className="text-sm text-muted-foreground">{data?.domain_url || 'Your domain'}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-3xl font-bold text-green-600">{ourMetrics.visibility_score.toFixed(1)}</p>
                  <p className="text-xs text-muted-foreground">Visibility Score</p>
                </div>
              </div>
              <div className="grid grid-cols-4 gap-4 mt-4 pt-4 border-t border-green-200 dark:border-green-900/30">
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Mentions</p>
                  <p className="text-lg font-bold">{ourMetrics.mentions.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Sentiment</p>
                  <p className="text-lg font-bold">{(ourMetrics.sentiment_score * 100).toFixed(0)}%</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Share of Voice</p>
                  <p className="text-lg font-bold">{ourMetrics.share_of_voice.toFixed(1)}%</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Prompts</p>
                  <p className="text-lg font-bold">{ourMetrics.total_prompts}</p>
                </div>
              </div>
            </div>

            {/* Competitors */}
            {competitors.map((competitor, index) => (
              <div key={competitor.name} className="p-5 rounded-lg bg-muted/30 border border-border">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center">
                      <span className="text-xl font-bold">{index + 2}</span>
                    </div>
                    <div>
                      <div className="flex items-center gap-3 mb-1">
                        <h3 className="text-lg font-bold">{competitor.name}</h3>
                        {getStatusBadge(competitor, index)}
                      </div>
                      <p className="text-sm text-muted-foreground">{competitor.url || 'Competitor'}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-3xl font-bold text-muted-foreground">{competitor.visibility_score.toFixed(1)}</p>
                    <p className="text-xs text-muted-foreground">Visibility Score</p>
                    <Badge variant="outline" className={`mt-2 ${competitor.trend > 0 ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400' : competitor.trend < 0 ? 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400' : ''}`}>
                      {getTrendIcon(competitor.trend)}
                      {competitor.trend > 0 ? '+' : ''}{competitor.trend.toFixed(1)}%
                    </Badge>
                  </div>
                </div>
                <div className="grid grid-cols-4 gap-4 mt-4 pt-4 border-t border-border">
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Mentions</p>
                    <p className="text-lg font-bold">{competitor.mentions.toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Sentiment</p>
                    <p className="text-lg font-bold">{(competitor.sentiment_score * 100).toFixed(0)}%</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Share of Voice</p>
                    <p className="text-lg font-bold">{competitor.share_of_voice.toFixed(1)}%</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Growth</p>
                    <p className={`text-lg font-bold ${getTrendColor(competitor.trend)}`}>
                      {competitor.trend > 0 ? '+' : ''}{competitor.trend.toFixed(1)}%
                    </p>
                  </div>
                </div>
              </div>
            ))}

            {competitors.length === 0 && (
              <div className="p-8 text-center text-muted-foreground">
                <Users className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No competitors tracked yet.</p>
                <p className="text-sm mt-2">Add competitors in your dashboard to enable competitive analysis.</p>
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Share of Voice Comparison */}
      {competitors.length > 0 && (
        <div>
          <h2 className="text-2xl font-bold mb-6">Competitive Analysis</h2>
          <div className="grid grid-cols-2 gap-6">
            <Card className="p-6 border border-border">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-primary" />
                Share of Voice Comparison
              </h3>
              <div className="space-y-3">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium">Your Brand</span>
                    <span className="text-sm font-bold">{ourMetrics.share_of_voice.toFixed(1)}%</span>
                  </div>
                  <div className="h-3 bg-muted rounded-full overflow-hidden">
                    <div className="h-full bg-green-500" style={{ width: `${Math.min(ourMetrics.share_of_voice, 100)}%` }}></div>
                  </div>
                </div>
                {competitors.slice(0, 5).map((competitor, index) => {
                  const colors = ['bg-amber-500', 'bg-blue-500', 'bg-purple-500', 'bg-gray-500', 'bg-pink-500'];
                  return (
                    <div key={competitor.name}>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium">{competitor.name}</span>
                        <span className="text-sm font-bold">{competitor.share_of_voice.toFixed(1)}%</span>
                      </div>
                      <div className="h-3 bg-muted rounded-full overflow-hidden">
                        <div className={`h-full ${colors[index]}`} style={{ width: `${Math.min(competitor.share_of_voice, 100)}%` }}></div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </Card>

            <Card className="p-6 border border-border">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Activity className="h-5 w-5 text-primary" />
                Growth Rate Comparison
              </h3>
              <div className="space-y-3">
                {[{ name: 'Your Brand', trend: 0, isOurs: true }, ...competitors]
                  .sort((a, b) => b.trend - a.trend)
                  .slice(0, 6)
                  .map((entity, index) => {
                    const bgColor = entity.trend > 5 ? 'bg-green-50 dark:bg-green-900/10' :
                                   entity.trend < -5 ? 'bg-red-50 dark:bg-red-900/10' :
                                   'bg-muted/30';
                    const badgeClass = entity.trend > 5 ? 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400' :
                                       entity.trend < -5 ? 'bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400' :
                                       '';
                    return (
                      <div key={entity.name} className={`flex items-center justify-between p-3 rounded ${bgColor}`}>
                        <span className="text-sm font-medium">{entity.name}</span>
                        <Badge className={badgeClass} variant={entity.trend > 5 || entity.trend < -5 ? 'default' : 'outline'}>
                          {getTrendIcon(entity.trend)}
                          {entity.trend > 0 ? '+' : ''}{entity.trend.toFixed(1)}%
                        </Badge>
                      </div>
                    );
                  })}
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* Platform Performance */}
      {platformBreakdown.length > 0 && (
        <div>
          <h2 className="text-2xl font-bold mb-6">Platform Performance</h2>
          <Card className="p-6 border border-border">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3 px-4 font-semibold">Platform</th>
                    <th className="text-center py-3 px-4 font-semibold">Total Queries</th>
                    <th className="text-center py-3 px-4 font-semibold">Mentions</th>
                    <th className="text-center py-3 px-4 font-semibold">Mention Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {platformBreakdown.map((platform) => (
                    <tr key={platform.platform} className="border-b hover:bg-muted/30">
                      <td className="py-3 px-4 font-medium capitalize">{platform.platform}</td>
                      <td className="text-center py-3 px-4">{platform.total.toLocaleString()}</td>
                      <td className="text-center py-3 px-4">{platform.mentions.toLocaleString()}</td>
                      <td className="text-center py-3 px-4">
                        <Badge variant="outline">{platform.mention_rate.toFixed(1)}%</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}

      {/* Key Insights */}
      <div>
        <h2 className="text-2xl font-bold mb-6">Key Competitive Insights</h2>
        <div className="grid grid-cols-2 gap-6">
          <Card className="p-6 border border-border">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-green-600" />
              Your Competitive Advantages
            </h3>
            <div className="space-y-3">
              {ourRank === 1 && (
                <div className="p-3 rounded bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-900/30">
                  <div className="flex items-center gap-2 mb-2">
                    <Star className="h-4 w-4 text-green-600" />
                    <span className="text-sm font-semibold">Market Leader</span>
                  </div>
                  <p className="text-xs text-muted-foreground">You hold the #1 position with {ourMetrics.share_of_voice.toFixed(1)}% share of voice</p>
                </div>
              )}
              {ourMetrics.sentiment_score > 0.7 && (
                <div className="p-3 rounded bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-900/30">
                  <div className="flex items-center gap-2 mb-2">
                    <Star className="h-4 w-4 text-green-600" />
                    <span className="text-sm font-semibold">Strong Sentiment</span>
                  </div>
                  <p className="text-xs text-muted-foreground">{(ourMetrics.sentiment_score * 100).toFixed(0)}% positive sentiment score</p>
                </div>
              )}
              {parseFloat(visibilityGap) > 5 && (
                <div className="p-3 rounded bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-900/30">
                  <div className="flex items-center gap-2 mb-2">
                    <Star className="h-4 w-4 text-green-600" />
                    <span className="text-sm font-semibold">Visibility Lead</span>
                  </div>
                  <p className="text-xs text-muted-foreground">{visibilityGap} points ahead of nearest competitor</p>
                </div>
              )}
              {competitors.length === 0 && (
                <p className="text-sm text-muted-foreground">Add competitors to see comparative advantages</p>
              )}
            </div>
          </Card>

          <Card className="p-6 border border-border">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <XCircle className="h-5 w-5 text-amber-600" />
              Areas to Monitor
            </h3>
            <div className="space-y-3">
              {risingThreats > 0 && (
                <div className="p-3 rounded bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-900/30">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertCircle className="h-4 w-4 text-amber-600" />
                    <span className="text-sm font-semibold">{risingThreats} Rising Competitor{risingThreats > 1 ? 's' : ''}</span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {competitors.filter(c => c.trend > 5).map(c => c.name).join(', ')} showing strong growth
                  </p>
                </div>
              )}
              {ourRank > 1 && (
                <div className="p-3 rounded bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-900/30">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertCircle className="h-4 w-4 text-amber-600" />
                    <span className="text-sm font-semibold">Not Market Leader</span>
                  </div>
                  <p className="text-xs text-muted-foreground">You are #{ourRank} - focus on closing the gap with the leader</p>
                </div>
              )}
              {competitors.length === 0 && (
                <p className="text-sm text-muted-foreground">Add competitors to identify potential threats</p>
              )}
            </div>
          </Card>
        </div>
      </div>

      {/* Footer */}
      <div className="pt-6 border-t">
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <p>Competitor Focus Report - AI Visibility Monitor</p>
          <p>Confidential - Strategic Planning Use Only</p>
        </div>
      </div>
      </div>
    </div>
  );
};
