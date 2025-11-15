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

export const CompetitorFocusTemplate = () => {
  return (
    <div className="w-full bg-background space-y-8">
      {/* Header Section */}
      <div className="border-b pb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">Competitor Focus Report</h1>
            <p className="text-muted-foreground">Competitive Intelligence & Market Benchmarking</p>
          </div>
          <div className="text-right">
            <p className="text-sm text-muted-foreground">Report Period</p>
            <p className="font-semibold">{new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}</p>
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
                <TrendingUp className="h-3 w-3 mr-1" />
                #1
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mb-1">Your Rank</p>
            <p className="text-3xl font-bold">Leader</p>
            <p className="text-xs text-muted-foreground mt-2">Up from #2 last quarter</p>
          </Card>

          <Card className="p-5 border border-border">
            <div className="flex items-center justify-between mb-3">
              <Target className="h-6 w-6 text-blue-600 dark:text-blue-400" />
              <Badge variant="outline">
                <TrendingUp className="h-3 w-3 mr-1" />
                +9.3
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mb-1">Visibility Gap</p>
            <p className="text-3xl font-bold">+9.3</p>
            <p className="text-xs text-muted-foreground mt-2">Points ahead of #2</p>
          </Card>

          <Card className="p-5 border border-border">
            <div className="flex items-center justify-between mb-3">
              <Users className="h-6 w-6 text-purple-600 dark:text-purple-400" />
              <Badge variant="outline">
                <Eye className="h-3 w-3 mr-1" />
                5
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mb-1">Tracked Competitors</p>
            <p className="text-3xl font-bold">5</p>
            <p className="text-xs text-muted-foreground mt-2">Active monitoring</p>
          </Card>

          <Card className="p-5 border border-border">
            <div className="flex items-center justify-between mb-3">
              <Shield className="h-6 w-6 text-amber-600 dark:text-amber-400" />
              <Badge variant="outline">
                <Flame className="h-3 w-3 mr-1" />
                2
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mb-1">Threats Detected</p>
            <p className="text-3xl font-bold">2</p>
            <p className="text-xs text-muted-foreground mt-2">Require attention</p>
          </Card>
        </div>
      </div>

      {/* Competitive Ranking */}
      <div>
        <h2 className="text-2xl font-bold mb-6">Competitive Ranking</h2>
        <Card className="p-6 border border-border">
          <div className="space-y-4">
            {/* Your Brand - Rank 1 */}
            <div className="p-5 rounded-lg bg-gradient-to-r from-green-50 to-green-100 dark:from-green-900/20 dark:to-green-900/10 border-2 border-green-500">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-green-600 flex items-center justify-center">
                    <Crown className="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <div className="flex items-center gap-3 mb-1">
                      <h3 className="text-lg font-bold">Your Brand (VegFitPro)</h3>
                      <Badge className="bg-green-600 text-white">Market Leader</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">Plant-based fitness nutrition</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-3xl font-bold text-green-600">87.5</p>
                  <p className="text-xs text-muted-foreground">Visibility Score</p>
                  <Badge variant="outline" className="mt-2 bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400">
                    <TrendingUp className="h-3 w-3 mr-1" />
                    +8.3%
                  </Badge>
                </div>
              </div>
              <div className="grid grid-cols-4 gap-4 mt-4 pt-4 border-t border-green-200 dark:border-green-900/30">
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Mentions</p>
                  <p className="text-lg font-bold">3,847</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Sentiment</p>
                  <p className="text-lg font-bold">92%</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Share of Voice</p>
                  <p className="text-lg font-bold">34%</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Growth</p>
                  <p className="text-lg font-bold text-green-600">+15.2%</p>
                </div>
              </div>
            </div>

            {/* Competitor A - Rank 2 */}
            <div className="p-5 rounded-lg bg-muted/30 border border-border">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center">
                    <span className="text-xl font-bold">2</span>
                  </div>
                  <div>
                    <div className="flex items-center gap-3 mb-1">
                      <h3 className="text-lg font-bold">PlantPower Nutrition</h3>
                      <Badge variant="secondary" className="bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400">
                        <AlertCircle className="h-3 w-3 mr-1" />
                        Rising Threat
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">Vegan supplements and protein</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-3xl font-bold text-muted-foreground">78.2</p>
                  <p className="text-xs text-muted-foreground">Visibility Score</p>
                  <Badge variant="outline" className="mt-2">
                    <TrendingUp className="h-3 w-3 mr-1" />
                    +12.1%
                  </Badge>
                </div>
              </div>
              <div className="grid grid-cols-4 gap-4 mt-4 pt-4 border-t border-border">
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Mentions</p>
                  <p className="text-lg font-bold">2,847</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Sentiment</p>
                  <p className="text-lg font-bold">88%</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Share of Voice</p>
                  <p className="text-lg font-bold">25%</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Growth</p>
                  <p className="text-lg font-bold text-amber-600">+12.1%</p>
                </div>
              </div>
            </div>

            {/* Competitor B - Rank 3 */}
            <div className="p-5 rounded-lg bg-muted/20 border border-border">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center">
                    <span className="text-xl font-bold">3</span>
                  </div>
                  <div>
                    <div className="flex items-center gap-3 mb-1">
                      <h3 className="text-lg font-bold">GreenFuel Athletics</h3>
                      <Badge variant="secondary">Stable</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">Sustainable sports nutrition</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-3xl font-bold text-muted-foreground">72.8</p>
                  <p className="text-xs text-muted-foreground">Visibility Score</p>
                  <Badge variant="outline" className="mt-2">
                    <TrendingUp className="h-3 w-3 mr-1" />
                    +5.4%
                  </Badge>
                </div>
              </div>
              <div className="grid grid-cols-4 gap-4 mt-4 pt-4 border-t border-border">
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Mentions</p>
                  <p className="text-lg font-bold">2,312</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Sentiment</p>
                  <p className="text-lg font-bold">85%</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Share of Voice</p>
                  <p className="text-lg font-bold">20%</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Growth</p>
                  <p className="text-lg font-bold">+5.4%</p>
                </div>
              </div>
            </div>

            {/* Competitor C - Rank 4 */}
            <div className="p-5 rounded-lg bg-muted/20 border border-border">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center">
                    <span className="text-xl font-bold">4</span>
                  </div>
                  <div>
                    <div className="flex items-center gap-3 mb-1">
                      <h3 className="text-lg font-bold">EcoWarrior Wellness</h3>
                      <Badge variant="secondary">Declining</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">Organic health products</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-3xl font-bold text-muted-foreground">68.5</p>
                  <p className="text-xs text-muted-foreground">Visibility Score</p>
                  <Badge variant="outline" className="mt-2 bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400">
                    <TrendingDown className="h-3 w-3 mr-1" />
                    -3.2%
                  </Badge>
                </div>
              </div>
              <div className="grid grid-cols-4 gap-4 mt-4 pt-4 border-t border-border">
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Mentions</p>
                  <p className="text-lg font-bold">1,987</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Sentiment</p>
                  <p className="text-lg font-bold">82%</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Share of Voice</p>
                  <p className="text-lg font-bold">17%</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Growth</p>
                  <p className="text-lg font-bold text-red-600">-3.2%</p>
                </div>
              </div>
            </div>

            {/* Competitor D - Rank 5 */}
            <div className="p-5 rounded-lg bg-muted/20 border border-border">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center">
                    <span className="text-xl font-bold">5</span>
                  </div>
                  <div>
                    <div className="flex items-center gap-3 mb-1">
                      <h3 className="text-lg font-bold">PureNature Supplements</h3>
                      <Badge variant="secondary">Stable</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">Natural nutrition supplements</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-3xl font-bold text-muted-foreground">65.3</p>
                  <p className="text-xs text-muted-foreground">Visibility Score</p>
                  <Badge variant="outline" className="mt-2">
                    <Minus className="h-3 w-3 mr-1" />
                    +1.8%
                  </Badge>
                </div>
              </div>
              <div className="grid grid-cols-4 gap-4 mt-4 pt-4 border-t border-border">
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Mentions</p>
                  <p className="text-lg font-bold">1,654</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Sentiment</p>
                  <p className="text-lg font-bold">80%</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Share of Voice</p>
                  <p className="text-lg font-bold">14%</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Growth</p>
                  <p className="text-lg font-bold">+1.8%</p>
                </div>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Competitive Analysis */}
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
                  <span className="text-sm font-bold">34%</span>
                </div>
                <div className="h-3 bg-muted rounded-full overflow-hidden">
                  <div className="h-full bg-green-500" style={{ width: '34%' }}></div>
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">PlantPower</span>
                  <span className="text-sm font-bold">25%</span>
                </div>
                <div className="h-3 bg-muted rounded-full overflow-hidden">
                  <div className="h-full bg-amber-500" style={{ width: '25%' }}></div>
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">GreenFuel</span>
                  <span className="text-sm font-bold">20%</span>
                </div>
                <div className="h-3 bg-muted rounded-full overflow-hidden">
                  <div className="h-full bg-blue-500" style={{ width: '20%' }}></div>
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">EcoWarrior</span>
                  <span className="text-sm font-bold">17%</span>
                </div>
                <div className="h-3 bg-muted rounded-full overflow-hidden">
                  <div className="h-full bg-purple-500" style={{ width: '17%' }}></div>
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">PureNature</span>
                  <span className="text-sm font-bold">14%</span>
                </div>
                <div className="h-3 bg-muted rounded-full overflow-hidden">
                  <div className="h-full bg-gray-500" style={{ width: '14%' }}></div>
                </div>
              </div>
            </div>
          </Card>

          <Card className="p-6 border border-border">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary" />
              Growth Rate Comparison
            </h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 rounded bg-green-50 dark:bg-green-900/10">
                <span className="text-sm font-medium">Your Brand</span>
                <Badge className="bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400">
                  <TrendingUp className="h-3 w-3 mr-1" />
                  +15.2%
                </Badge>
              </div>
              <div className="flex items-center justify-between p-3 rounded bg-amber-50 dark:bg-amber-900/10">
                <span className="text-sm font-medium">PlantPower</span>
                <Badge className="bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400">
                  <TrendingUp className="h-3 w-3 mr-1" />
                  +12.1%
                </Badge>
              </div>
              <div className="flex items-center justify-between p-3 rounded bg-muted/30">
                <span className="text-sm font-medium">GreenFuel</span>
                <Badge variant="outline">
                  <TrendingUp className="h-3 w-3 mr-1" />
                  +5.4%
                </Badge>
              </div>
              <div className="flex items-center justify-between p-3 rounded bg-muted/30">
                <span className="text-sm font-medium">PureNature</span>
                <Badge variant="outline">
                  <TrendingUp className="h-3 w-3 mr-1" />
                  +1.8%
                </Badge>
              </div>
              <div className="flex items-center justify-between p-3 rounded bg-red-50 dark:bg-red-900/10">
                <span className="text-sm font-medium">EcoWarrior</span>
                <Badge className="bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400">
                  <TrendingDown className="h-3 w-3 mr-1" />
                  -3.2%
                </Badge>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Platform-wise Competitive Analysis */}
      <div>
        <h2 className="text-2xl font-bold mb-6">Platform-wise Competitive Analysis</h2>
        <Card className="p-6 border border-border">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3 px-4 font-semibold">Platform</th>
                  <th className="text-center py-3 px-4 font-semibold">Your Brand</th>
                  <th className="text-center py-3 px-4 font-semibold">PlantPower</th>
                  <th className="text-center py-3 px-4 font-semibold">GreenFuel</th>
                  <th className="text-center py-3 px-4 font-semibold">EcoWarrior</th>
                  <th className="text-center py-3 px-4 font-semibold">PureNature</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b hover:bg-muted/30">
                  <td className="py-3 px-4 font-medium">ChatGPT</td>
                  <td className="text-center py-3 px-4">
                    <div className="flex flex-col items-center">
                      <Badge className="bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400 mb-1">
                        <Crown className="h-3 w-3 mr-1" />
                        #1
                      </Badge>
                      <span className="text-sm font-bold">1,616</span>
                    </div>
                  </td>
                  <td className="text-center py-3 px-4">
                    <div className="flex flex-col items-center">
                      <Badge variant="outline" className="mb-1">#2</Badge>
                      <span className="text-sm">1,198</span>
                    </div>
                  </td>
                  <td className="text-center py-3 px-4">
                    <div className="flex flex-col items-center">
                      <Badge variant="outline" className="mb-1">#3</Badge>
                      <span className="text-sm">971</span>
                    </div>
                  </td>
                  <td className="text-center py-3 px-4">
                    <div className="flex flex-col items-center">
                      <Badge variant="outline" className="mb-1">#4</Badge>
                      <span className="text-sm">835</span>
                    </div>
                  </td>
                  <td className="text-center py-3 px-4">
                    <div className="flex flex-col items-center">
                      <Badge variant="outline" className="mb-1">#5</Badge>
                      <span className="text-sm">696</span>
                    </div>
                  </td>
                </tr>
                <tr className="border-b hover:bg-muted/30">
                  <td className="py-3 px-4 font-medium">Perplexity</td>
                  <td className="text-center py-3 px-4">
                    <div className="flex flex-col items-center">
                      <Badge className="bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400 mb-1">
                        <Crown className="h-3 w-3 mr-1" />
                        #1
                      </Badge>
                      <span className="text-sm font-bold">1,077</span>
                    </div>
                  </td>
                  <td className="text-center py-3 px-4">
                    <div className="flex flex-col items-center">
                      <Badge variant="outline" className="mb-1">#2</Badge>
                      <span className="text-sm">712</span>
                    </div>
                  </td>
                  <td className="text-center py-3 px-4">
                    <div className="flex flex-col items-center">
                      <Badge variant="outline" className="mb-1">#3</Badge>
                      <span className="text-sm">578</span>
                    </div>
                  </td>
                  <td className="text-center py-3 px-4">
                    <div className="flex flex-col items-center">
                      <Badge variant="outline" className="mb-1">#4</Badge>
                      <span className="text-sm">497</span>
                    </div>
                  </td>
                  <td className="text-center py-3 px-4">
                    <div className="flex flex-col items-center">
                      <Badge variant="outline" className="mb-1">#5</Badge>
                      <span className="text-sm">414</span>
                    </div>
                  </td>
                </tr>
                <tr className="border-b hover:bg-muted/30">
                  <td className="py-3 px-4 font-medium">Claude</td>
                  <td className="text-center py-3 px-4">
                    <div className="flex flex-col items-center">
                      <Badge className="bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400 mb-1">
                        <Crown className="h-3 w-3 mr-1" />
                        #1
                      </Badge>
                      <span className="text-sm font-bold">692</span>
                    </div>
                  </td>
                  <td className="text-center py-3 px-4">
                    <div className="flex flex-col items-center">
                      <Badge variant="outline" className="mb-1">#2</Badge>
                      <span className="text-sm">513</span>
                    </div>
                  </td>
                  <td className="text-center py-3 px-4">
                    <div className="flex flex-col items-center">
                      <Badge variant="outline" className="mb-1">#3</Badge>
                      <span className="text-sm">416</span>
                    </div>
                  </td>
                  <td className="text-center py-3 px-4">
                    <div className="flex flex-col items-center">
                      <Badge variant="outline" className="mb-1">#4</Badge>
                      <span className="text-sm">357</span>
                    </div>
                  </td>
                  <td className="text-center py-3 px-4">
                    <div className="flex flex-col items-center">
                      <Badge variant="outline" className="mb-1">#5</Badge>
                      <span className="text-sm">298</span>
                    </div>
                  </td>
                </tr>
                <tr className="border-b hover:bg-muted/30">
                  <td className="py-3 px-4 font-medium">Gemini</td>
                  <td className="text-center py-3 px-4">
                    <div className="flex flex-col items-center">
                      <Badge className="bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400 mb-1">
                        <Crown className="h-3 w-3 mr-1" />
                        #1
                      </Badge>
                      <span className="text-sm font-bold">462</span>
                    </div>
                  </td>
                  <td className="text-center py-3 px-4">
                    <div className="flex flex-col items-center">
                      <Badge variant="outline" className="mb-1">#2</Badge>
                      <span className="text-sm">342</span>
                    </div>
                  </td>
                  <td className="text-center py-3 px-4">
                    <div className="flex flex-col items-center">
                      <Badge variant="outline" className="mb-1">#3</Badge>
                      <span className="text-sm">278</span>
                    </div>
                  </td>
                  <td className="text-center py-3 px-4">
                    <div className="flex flex-col items-center">
                      <Badge variant="outline" className="mb-1">#4</Badge>
                      <span className="text-sm">239</span>
                    </div>
                  </td>
                  <td className="text-center py-3 px-4">
                    <div className="flex flex-col items-center">
                      <Badge variant="outline" className="mb-1">#5</Badge>
                      <span className="text-sm">199</span>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      {/* Competitive Strengths & Weaknesses */}
      <div>
        <h2 className="text-2xl font-bold mb-6">Competitive Strengths & Weaknesses</h2>
        <div className="grid grid-cols-2 gap-6">
          <Card className="p-6 border border-border">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-green-600" />
              Your Competitive Advantages
            </h3>
            <div className="space-y-3">
              <div className="p-3 rounded bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-900/30">
                <div className="flex items-center gap-2 mb-2">
                  <Star className="h-4 w-4 text-green-600" />
                  <span className="text-sm font-semibold">Platform Leadership</span>
                </div>
                <p className="text-xs text-muted-foreground">#1 position across all 4 major AI platforms - strongest market presence</p>
              </div>
              <div className="p-3 rounded bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-900/30">
                <div className="flex items-center gap-2 mb-2">
                  <Star className="h-4 w-4 text-green-600" />
                  <span className="text-sm font-semibold">Sentiment Excellence</span>
                </div>
                <p className="text-xs text-muted-foreground">92% positive sentiment - highest among all competitors</p>
              </div>
              <div className="p-3 rounded bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-900/30">
                <div className="flex items-center gap-2 mb-2">
                  <Star className="h-4 w-4 text-green-600" />
                  <span className="text-sm font-semibold">Growth Momentum</span>
                </div>
                <p className="text-xs text-muted-foreground">+15.2% growth rate - outpacing all competitors significantly</p>
              </div>
              <div className="p-3 rounded bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-900/30">
                <div className="flex items-center gap-2 mb-2">
                  <Star className="h-4 w-4 text-green-600" />
                  <span className="text-sm font-semibold">Share of Voice Dominance</span>
                </div>
                <p className="text-xs text-muted-foreground">34% share - 9% higher than nearest competitor</p>
              </div>
            </div>
          </Card>

          <Card className="p-6 border border-border">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <XCircle className="h-5 w-5 text-amber-600" />
              Areas to Monitor
            </h3>
            <div className="space-y-3">
              <div className="p-3 rounded bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-900/30">
                <div className="flex items-center gap-2 mb-2">
                  <AlertCircle className="h-4 w-4 text-amber-600" />
                  <span className="text-sm font-semibold">PlantPower Rising Fast</span>
                </div>
                <p className="text-xs text-muted-foreground">+12.1% growth rate - closing gap faster than expected</p>
              </div>
              <div className="p-3 rounded bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-900/30">
                <div className="flex items-center gap-2 mb-2">
                  <AlertCircle className="h-4 w-4 text-amber-600" />
                  <span className="text-sm font-semibold">Premium Positioning Gap</span>
                </div>
                <p className="text-xs text-muted-foreground">PlantPower gaining traction in premium segment - traditionally your strong area</p>
              </div>
              <div className="p-3 rounded bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-900/30">
                <div className="flex items-center gap-2 mb-2">
                  <Eye className="h-4 w-4 text-blue-600" />
                  <span className="text-sm font-semibold">Gemini Platform Opportunity</span>
                </div>
                <p className="text-xs text-muted-foreground">High growth potential but competitors also increasing presence</p>
              </div>
              <div className="p-3 rounded bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-900/30">
                <div className="flex items-center gap-2 mb-2">
                  <Eye className="h-4 w-4 text-blue-600" />
                  <span className="text-sm font-semibold">Content Freshness</span>
                </div>
                <p className="text-xs text-muted-foreground">PlantPower updating content 2x more frequently - maintain vigilance</p>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Threat Analysis */}
      <div>
        <h2 className="text-2xl font-bold mb-6">Competitive Threats & Opportunities</h2>
        <div className="grid grid-cols-2 gap-6">
          <Card className="p-6 border border-border bg-red-50/50 dark:bg-red-900/10">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-red-600" />
              Active Threats
            </h3>
            <div className="space-y-3">
              <div className="p-4 rounded bg-white dark:bg-background border border-red-200 dark:border-red-900/30">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h4 className="font-semibold text-sm mb-1">PlantPower Aggressive Expansion</h4>
                    <p className="text-xs text-muted-foreground">Launched on 3 new platforms in Q4</p>
                  </div>
                  <Badge variant="destructive" className="text-xs">High</Badge>
                </div>
                <p className="text-xs text-muted-foreground">Growing 12.1% - potential to reach #1 in 6-9 months</p>
              </div>
              <div className="p-4 rounded bg-white dark:bg-background border border-amber-200 dark:border-amber-900/30">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h4 className="font-semibold text-sm mb-1">Pricing Pressure</h4>
                    <p className="text-xs text-muted-foreground">2 competitors reduced prices by 15%</p>
                  </div>
                  <Badge variant="secondary" className="bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400 text-xs">Medium</Badge>
                </div>
                <p className="text-xs text-muted-foreground">May impact premium positioning strategy</p>
              </div>
            </div>
          </Card>

          <Card className="p-6 border border-border bg-green-50/50 dark:bg-green-900/10">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Zap className="h-5 w-5 text-green-600" />
              Strategic Opportunities
            </h3>
            <div className="space-y-3">
              <div className="p-4 rounded bg-white dark:bg-background border border-green-200 dark:border-green-900/30">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h4 className="font-semibold text-sm mb-1">EcoWarrior Weakness</h4>
                    <p className="text-xs text-muted-foreground">Declining -3.2% with quality issues</p>
                  </div>
                  <Badge className="bg-green-600 text-white text-xs">High</Badge>
                </div>
                <p className="text-xs text-muted-foreground">Capture their market share in organic wellness segment</p>
              </div>
              <div className="p-4 rounded bg-white dark:bg-background border border-blue-200 dark:border-blue-900/30">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h4 className="font-semibold text-sm mb-1">Gemini Expansion Window</h4>
                    <p className="text-xs text-muted-foreground">45% growth potential on platform</p>
                  </div>
                  <Badge variant="outline" className="bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400 text-xs">Medium</Badge>
                </div>
                <p className="text-xs text-muted-foreground">Low competition - establish dominance early</p>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Strategic Recommendations */}
      <div>
        <h2 className="text-2xl font-bold mb-6">Competitive Strategy Recommendations</h2>
        <div className="space-y-3">
          <div className="p-5 border-l-4 border-l-green-500 bg-green-50/50 dark:bg-green-900/10 rounded-lg">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-green-600 flex items-center justify-center text-sm font-bold text-white flex-shrink-0">
                1
              </div>
              <div className="flex-1">
                <h4 className="font-semibold mb-2">Defend Market Leadership Against PlantPower</h4>
                <p className="text-sm text-muted-foreground mb-3">
                  PlantPower's 12.1% growth rate poses the most significant threat to your #1 position. Accelerate content updates and increase presence on platforms where they're gaining traction.
                </p>
                <div className="flex gap-2">
                  <Badge variant="outline" className="text-xs">Priority: Critical</Badge>
                  <Badge variant="outline" className="text-xs">Timeline: Immediate</Badge>
                  <Badge variant="outline" className="text-xs">Expected Impact: Maintain +9pt gap</Badge>
                </div>
              </div>
            </div>
          </div>

          <div className="p-5 border-l-4 border-l-blue-500 bg-blue-50/50 dark:bg-blue-900/10 rounded-lg">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-sm font-bold text-white flex-shrink-0">
                2
              </div>
              <div className="flex-1">
                <h4 className="font-semibold mb-2">Capture EcoWarrior's Declining Market Share</h4>
                <p className="text-sm text-muted-foreground mb-3">
                  EcoWarrior's -3.2% decline creates an opportunity to capture their organic wellness audience. Target their keywords and highlight quality advantages.
                </p>
                <div className="flex gap-2">
                  <Badge variant="outline" className="text-xs">Priority: High</Badge>
                  <Badge variant="outline" className="text-xs">Timeline: 30 days</Badge>
                  <Badge variant="outline" className="text-xs">Expected Impact: +3-5% share gain</Badge>
                </div>
              </div>
            </div>
          </div>

          <div className="p-5 border-l-4 border-l-purple-500 bg-purple-50/50 dark:bg-purple-900/10 rounded-lg">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center text-sm font-bold text-white flex-shrink-0">
                3
              </div>
              <div className="flex-1">
                <h4 className="font-semibold mb-2">Dominate Gemini Before Competition Intensifies</h4>
                <p className="text-sm text-muted-foreground mb-3">
                  With 45% growth potential and current #1 position, establish unassailable dominance on Gemini before competitors increase investment.
                </p>
                <div className="flex gap-2">
                  <Badge variant="outline" className="text-xs">Priority: High</Badge>
                  <Badge variant="outline" className="text-xs">Timeline: 60 days</Badge>
                  <Badge variant="outline" className="text-xs">Expected Impact: 50%+ platform share</Badge>
                </div>
              </div>
            </div>
          </div>
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
  );
};
