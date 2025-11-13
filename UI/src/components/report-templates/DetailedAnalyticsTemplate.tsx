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
  Minus
} from "lucide-react";

export const DetailedAnalyticsTemplate = () => {
  return (
    <div className="p-8 bg-background space-y-8">
      {/* Header Section */}
      <div className="border-b pb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">Detailed Analytics Report</h1>
            <p className="text-muted-foreground">Complete Performance Analysis & Metrics</p>
          </div>
          <div className="text-right">
            <p className="text-sm text-muted-foreground">Report Period</p>
            <p className="font-semibold">Nov 1 - Nov 30, 2024</p>
            <p className="text-xs text-muted-foreground mt-1">Generated: {new Date().toLocaleString()}</p>
          </div>
        </div>
      </div>

      {/* Overview Metrics Grid */}
      <div>
        <h2 className="text-2xl font-bold mb-6">Performance Overview</h2>
        <div className="grid grid-cols-4 gap-4">
          <Card className="p-5 border border-border">
            <div className="flex items-center justify-between mb-2">
              <Eye className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              <Badge variant="default" className="bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400">
                <TrendingUp className="h-3 w-3 mr-1" />
                +8.3%
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mb-1">Visibility Score</p>
            <p className="text-2xl font-bold">87.5</p>
            <p className="text-xs text-muted-foreground mt-1">Previous: 80.8</p>
          </Card>

          <Card className="p-5 border border-border">
            <div className="flex items-center justify-between mb-2">
              <MessageSquare className="h-5 w-5 text-purple-600 dark:text-purple-400" />
              <Badge variant="default" className="bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400">
                <TrendingUp className="h-3 w-3 mr-1" />
                +15.2%
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mb-1">Total Mentions</p>
            <p className="text-2xl font-bold">3,847</p>
            <p className="text-xs text-muted-foreground mt-1">Previous: 3,340</p>
          </Card>

          <Card className="p-5 border border-border">
            <div className="flex items-center justify-between mb-2">
              <Activity className="h-5 w-5 text-green-600 dark:text-green-400" />
              <Badge variant="default" className="bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400">
                <TrendingUp className="h-3 w-3 mr-1" />
                +12.7%
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mb-1">Daily Avg Mentions</p>
            <p className="text-2xl font-bold">128</p>
            <p className="text-xs text-muted-foreground mt-1">Previous: 113</p>
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
            <p className="text-2xl font-bold">5</p>
            <p className="text-xs text-muted-foreground mt-1">ChatGPT, Claude, Gemini, Perplexity, Grok</p>
          </Card>
        </div>
      </div>

      {/* Sentiment Analysis Deep Dive */}
      <div>
        <h2 className="text-2xl font-bold mb-6">Sentiment Analysis</h2>
        <div className="grid grid-cols-3 gap-6">
          <Card className="p-6 border border-border">
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
                  <span className="text-sm font-bold">92%</span>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div className="h-full bg-green-500" style={{ width: '92%' }}></div>
                </div>
                <p className="text-xs text-muted-foreground mt-1">3,539 mentions</p>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-gray-500"></div>
                    Neutral
                  </span>
                  <span className="text-sm font-bold">6%</span>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div className="h-full bg-gray-500" style={{ width: '6%' }}></div>
                </div>
                <p className="text-xs text-muted-foreground mt-1">231 mentions</p>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-500"></div>
                    Negative
                  </span>
                  <span className="text-sm font-bold">2%</span>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div className="h-full bg-red-500" style={{ width: '2%' }}></div>
                </div>
                <p className="text-xs text-muted-foreground mt-1">77 mentions</p>
              </div>
            </div>
          </Card>

          <Card className="p-6 border border-border">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Sentiment by Platform</h3>
              <BarChart3 className="h-5 w-5 text-primary" />
            </div>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-2 rounded bg-muted/30">
                <span className="text-sm font-medium">ChatGPT</span>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400 text-xs">94%</Badge>
                  <TrendingUp className="h-3 w-3 text-green-600" />
                </div>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-muted/30">
                <span className="text-sm font-medium">Perplexity</span>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400 text-xs">91%</Badge>
                  <TrendingUp className="h-3 w-3 text-green-600" />
                </div>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-muted/30">
                <span className="text-sm font-medium">Claude</span>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400 text-xs">93%</Badge>
                  <TrendingUp className="h-3 w-3 text-green-600" />
                </div>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-muted/30">
                <span className="text-sm font-medium">Gemini</span>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400 text-xs">89%</Badge>
                  <Minus className="h-3 w-3 text-gray-600" />
                </div>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-muted/30">
                <span className="text-sm font-medium">Grok</span>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400 text-xs">88%</Badge>
                  <TrendingDown className="h-3 w-3 text-amber-600" />
                </div>
              </div>
            </div>
          </Card>

          <Card className="p-6 border border-border">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Sentiment Trends</h3>
              <TrendingUp className="h-5 w-5 text-green-600" />
            </div>
            <div className="space-y-3">
              <div className="p-3 rounded bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-900/30">
                <div className="flex items-center gap-2 mb-1">
                  <ArrowUpRight className="h-4 w-4 text-green-600" />
                  <span className="text-sm font-semibold">Positive Growth</span>
                </div>
                <p className="text-xs text-muted-foreground">+3.8% from last period</p>
                <p className="text-xs text-muted-foreground">Highest in 6 months</p>
              </div>
              <div className="p-3 rounded bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-900/30">
                <div className="flex items-center gap-2 mb-1">
                  <Award className="h-4 w-4 text-blue-600" />
                  <span className="text-sm font-semibold">Quality Score</span>
                </div>
                <p className="text-xs text-muted-foreground">4.6/5.0 average rating</p>
                <p className="text-xs text-muted-foreground">Based on 847 reviews</p>
              </div>
              <div className="p-3 rounded bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-900/30">
                <div className="flex items-center gap-2 mb-1">
                  <AlertTriangle className="h-4 w-4 text-amber-600" />
                  <span className="text-sm font-semibold">Watch Area</span>
                </div>
                <p className="text-xs text-muted-foreground">77 negative mentions</p>
                <p className="text-xs text-muted-foreground">-15 from last period</p>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Platform Distribution & Performance */}
      <div>
        <h2 className="text-2xl font-bold mb-6">Platform Distribution & Performance</h2>
        <div className="grid grid-cols-2 gap-6">
          <Card className="p-6 border border-border">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <PieChart className="h-5 w-5 text-primary" />
              Mention Distribution
            </h3>
            <div className="space-y-3">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                    <span className="text-sm font-medium">ChatGPT</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold">1,616</span>
                    <span className="text-xs text-muted-foreground">(42%)</span>
                  </div>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div className="h-full bg-blue-500" style={{ width: '42%' }}></div>
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-purple-500"></div>
                    <span className="text-sm font-medium">Perplexity</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold">1,077</span>
                    <span className="text-xs text-muted-foreground">(28%)</span>
                  </div>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div className="h-full bg-purple-500" style={{ width: '28%' }}></div>
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-amber-500"></div>
                    <span className="text-sm font-medium">Claude</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold">692</span>
                    <span className="text-xs text-muted-foreground">(18%)</span>
                  </div>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div className="h-full bg-amber-500" style={{ width: '18%' }}></div>
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-green-500"></div>
                    <span className="text-sm font-medium">Gemini</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold">462</span>
                    <span className="text-xs text-muted-foreground">(12%)</span>
                  </div>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div className="h-full bg-green-500" style={{ width: '12%' }}></div>
                </div>
              </div>
            </div>
          </Card>

          <Card className="p-6 border border-border">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-primary" />
              Platform Growth Rates
            </h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 rounded bg-muted/30">
                <div>
                  <p className="text-sm font-medium">ChatGPT</p>
                  <p className="text-xs text-muted-foreground">1,616 mentions</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400">
                    <TrendingUp className="h-3 w-3 mr-1" />
                    +8.2%
                  </Badge>
                </div>
              </div>
              <div className="flex items-center justify-between p-3 rounded bg-muted/30">
                <div>
                  <p className="text-sm font-medium">Perplexity</p>
                  <p className="text-xs text-muted-foreground">1,077 mentions</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400">
                    <TrendingUp className="h-3 w-3 mr-1" />
                    +22.5%
                  </Badge>
                </div>
              </div>
              <div className="flex items-center justify-between p-3 rounded bg-muted/30">
                <div>
                  <p className="text-sm font-medium">Claude</p>
                  <p className="text-xs text-muted-foreground">692 mentions</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400">
                    <TrendingUp className="h-3 w-3 mr-1" />
                    +15.3%
                  </Badge>
                </div>
              </div>
              <div className="flex items-center justify-between p-3 rounded bg-muted/30">
                <div>
                  <p className="text-sm font-medium">Gemini</p>
                  <p className="text-xs text-muted-foreground">462 mentions</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400">
                    <TrendingUp className="h-3 w-3 mr-1" />
                    +45.1%
                  </Badge>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Topic & Keyword Analysis */}
      <div>
        <h2 className="text-2xl font-bold mb-6">Topic & Keyword Analysis</h2>
        <div className="grid grid-cols-2 gap-6">
          <Card className="p-6 border border-border">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Target className="h-5 w-5 text-primary" />
              Top Performing Keywords
            </h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 rounded bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-900/30">
                <div>
                  <p className="text-sm font-semibold">vegan protein powder</p>
                  <p className="text-xs text-muted-foreground">847 mentions across platforms</p>
                </div>
                <Badge className="bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400">
                  <TrendingUp className="h-3 w-3 mr-1" />
                  +28%
                </Badge>
              </div>
              <div className="flex items-center justify-between p-3 rounded bg-muted/30">
                <div>
                  <p className="text-sm font-semibold">plant-based fitness</p>
                  <p className="text-xs text-muted-foreground">623 mentions across platforms</p>
                </div>
                <Badge variant="outline">
                  <TrendingUp className="h-3 w-3 mr-1" />
                  +18%
                </Badge>
              </div>
              <div className="flex items-center justify-between p-3 rounded bg-muted/30">
                <div>
                  <p className="text-sm font-semibold">sustainable nutrition</p>
                  <p className="text-xs text-muted-foreground">541 mentions across platforms</p>
                </div>
                <Badge variant="outline">
                  <TrendingUp className="h-3 w-3 mr-1" />
                  +35%
                </Badge>
              </div>
              <div className="flex items-center justify-between p-3 rounded bg-muted/30">
                <div>
                  <p className="text-sm font-semibold">eco-friendly supplements</p>
                  <p className="text-xs text-muted-foreground">412 mentions across platforms</p>
                </div>
                <Badge variant="outline">
                  <TrendingUp className="h-3 w-3 mr-1" />
                  +12%
                </Badge>
              </div>
              <div className="flex items-center justify-between p-3 rounded bg-muted/30">
                <div>
                  <p className="text-sm font-semibold">organic wellness</p>
                  <p className="text-xs text-muted-foreground">387 mentions across platforms</p>
                </div>
                <Badge variant="outline">
                  <Minus className="h-3 w-3 mr-1" />
                  +5%
                </Badge>
              </div>
            </div>
          </Card>

          <Card className="p-6 border border-border">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Search className="h-5 w-5 text-primary" />
              Emerging Topics
            </h3>
            <div className="space-y-3">
              <div className="p-3 rounded bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-900/30">
                <div className="flex items-center gap-2 mb-2">
                  <Zap className="h-4 w-4 text-blue-600" />
                  <span className="text-sm font-semibold">Climate-Conscious Nutrition</span>
                </div>
                <p className="text-xs text-muted-foreground mb-2">215 mentions | +127% growth</p>
                <div className="flex gap-2 flex-wrap">
                  <Badge variant="secondary" className="text-xs">carbon footprint</Badge>
                  <Badge variant="secondary" className="text-xs">sustainable sourcing</Badge>
                  <Badge variant="secondary" className="text-xs">eco packaging</Badge>
                </div>
              </div>
              <div className="p-3 rounded bg-purple-50 dark:bg-purple-900/10 border border-purple-200 dark:border-purple-900/30">
                <div className="flex items-center gap-2 mb-2">
                  <Zap className="h-4 w-4 text-purple-600" />
                  <span className="text-sm font-semibold">AI-Powered Meal Planning</span>
                </div>
                <p className="text-xs text-muted-foreground mb-2">178 mentions | +94% growth</p>
                <div className="flex gap-2 flex-wrap">
                  <Badge variant="secondary" className="text-xs">personalized nutrition</Badge>
                  <Badge variant="secondary" className="text-xs">AI coaching</Badge>
                </div>
              </div>
              <div className="p-3 rounded bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-900/30">
                <div className="flex items-center gap-2 mb-2">
                  <Zap className="h-4 w-4 text-green-600" />
                  <span className="text-sm font-semibold">Gut Health Optimization</span>
                </div>
                <p className="text-xs text-muted-foreground mb-2">156 mentions | +82% growth</p>
                <div className="flex gap-2 flex-wrap">
                  <Badge variant="secondary" className="text-xs">microbiome</Badge>
                  <Badge variant="secondary" className="text-xs">probiotics</Badge>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Traffic & Attribution Metrics */}
      <div>
        <h2 className="text-2xl font-bold mb-6">Traffic Attribution & ROI</h2>
        <div className="grid grid-cols-4 gap-4 mb-6">
          <Card className="p-5 border border-border">
            <div className="flex items-center gap-2 mb-2">
              <Users className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              <span className="text-sm text-muted-foreground">Sessions</span>
            </div>
            <p className="text-2xl font-bold">12,847</p>
            <Badge variant="outline" className="mt-2 text-xs">
              <TrendingUp className="h-3 w-3 mr-1" />
              +18.5%
            </Badge>
          </Card>

          <Card className="p-5 border border-border">
            <div className="flex items-center gap-2 mb-2">
              <Target className="h-5 w-5 text-green-600 dark:text-green-400" />
              <span className="text-sm text-muted-foreground">Conversions</span>
            </div>
            <p className="text-2xl font-bold">1,847</p>
            <Badge variant="outline" className="mt-2 text-xs">
              <TrendingUp className="h-3 w-3 mr-1" />
              +24.2%
            </Badge>
          </Card>

          <Card className="p-5 border border-border">
            <div className="flex items-center gap-2 mb-2">
              <Activity className="h-5 w-5 text-purple-600 dark:text-purple-400" />
              <span className="text-sm text-muted-foreground">Conversion Rate</span>
            </div>
            <p className="text-2xl font-bold">14.4%</p>
            <Badge variant="outline" className="mt-2 text-xs">
              <TrendingUp className="h-3 w-3 mr-1" />
              +4.8%
            </Badge>
          </Card>

          <Card className="p-5 border border-border">
            <div className="flex items-center gap-2 mb-2">
              <Award className="h-5 w-5 text-amber-600 dark:text-amber-400" />
              <span className="text-sm text-muted-foreground">Revenue</span>
            </div>
            <p className="text-2xl font-bold">$124K</p>
            <Badge variant="outline" className="mt-2 text-xs">
              <TrendingUp className="h-3 w-3 mr-1" />
              +22.5%
            </Badge>
          </Card>
        </div>

        <Card className="p-6 border border-border">
          <h3 className="text-lg font-semibold mb-4">Revenue by Platform</h3>
          <div className="grid grid-cols-5 gap-4">
            <div className="p-4 rounded bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-900/30">
              <p className="text-xs text-muted-foreground mb-1">ChatGPT</p>
              <p className="text-xl font-bold mb-1">$52.1K</p>
              <Badge variant="outline" className="text-xs">42%</Badge>
            </div>
            <div className="p-4 rounded bg-purple-50 dark:bg-purple-900/10 border border-purple-200 dark:border-purple-900/30">
              <p className="text-xs text-muted-foreground mb-1">Perplexity</p>
              <p className="text-xl font-bold mb-1">$34.7K</p>
              <Badge variant="outline" className="text-xs">28%</Badge>
            </div>
            <div className="p-4 rounded bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-900/30">
              <p className="text-xs text-muted-foreground mb-1">Claude</p>
              <p className="text-xl font-bold mb-1">$22.3K</p>
              <Badge variant="outline" className="text-xs">18%</Badge>
            </div>
            <div className="p-4 rounded bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-900/30">
              <p className="text-xs text-muted-foreground mb-1">Gemini</p>
              <p className="text-xl font-bold mb-1">$14.9K</p>
              <Badge variant="outline" className="text-xs">12%</Badge>
            </div>
            <div className="p-4 rounded bg-muted/30">
              <p className="text-xs text-muted-foreground mb-1">Other</p>
              <p className="text-xl font-bold mb-1">$0.0K</p>
              <Badge variant="outline" className="text-xs">0%</Badge>
            </div>
          </div>
        </Card>
      </div>

      {/* Time-based Analysis */}
      <div>
        <h2 className="text-2xl font-bold mb-6">Temporal Patterns</h2>
        <div className="grid grid-cols-2 gap-6">
          <Card className="p-6 border border-border">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Clock className="h-5 w-5 text-primary" />
              Peak Activity Hours (UTC)
            </h3>
            <div className="space-y-2">
              <div className="flex items-center justify-between p-2 rounded bg-green-50 dark:bg-green-900/10">
                <span className="text-sm">14:00 - 16:00</span>
                <Badge className="bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400 text-xs">
                  487 mentions/hour
                </Badge>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-blue-50 dark:bg-blue-900/10">
                <span className="text-sm">18:00 - 20:00</span>
                <Badge className="bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400 text-xs">
                  412 mentions/hour
                </Badge>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-muted/30">
                <span className="text-sm">09:00 - 11:00</span>
                <Badge variant="outline" className="text-xs">358 mentions/hour</Badge>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-muted/30">
                <span className="text-sm">21:00 - 23:00</span>
                <Badge variant="outline" className="text-xs">287 mentions/hour</Badge>
              </div>
            </div>
          </Card>

          <Card className="p-6 border border-border">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Calendar className="h-5 w-5 text-primary" />
              Weekly Patterns
            </h3>
            <div className="space-y-2">
              <div className="flex items-center justify-between p-2 rounded bg-green-50 dark:bg-green-900/10">
                <span className="text-sm">Tuesday</span>
                <Badge className="bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400 text-xs">
                  623 avg mentions
                </Badge>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-blue-50 dark:bg-blue-900/10">
                <span className="text-sm">Wednesday</span>
                <Badge className="bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400 text-xs">
                  598 avg mentions
                </Badge>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-muted/30">
                <span className="text-sm">Thursday</span>
                <Badge variant="outline" className="text-xs">547 avg mentions</Badge>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-muted/30">
                <span className="text-sm">Monday</span>
                <Badge variant="outline" className="text-xs">512 avg mentions</Badge>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Alerts & Issues */}
      <div>
        <h2 className="text-2xl font-bold mb-6">Alerts & Quality Monitoring</h2>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <Card className="p-5 border border-border">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
              <span className="text-sm text-muted-foreground">Critical Alerts</span>
            </div>
            <p className="text-3xl font-bold">3</p>
            <p className="text-xs text-muted-foreground mt-1">Requires immediate action</p>
          </Card>

          <Card className="p-5 border border-border">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400" />
              <span className="text-sm text-muted-foreground">Warnings</span>
            </div>
            <p className="text-3xl font-bold">8</p>
            <p className="text-xs text-muted-foreground mt-1">Monitor closely</p>
          </Card>

          <Card className="p-5 border border-border">
            <div className="flex items-center gap-2 mb-2">
              <Activity className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              <span className="text-sm text-muted-foreground">Info</span>
            </div>
            <p className="text-3xl font-bold">15</p>
            <p className="text-xs text-muted-foreground mt-1">For awareness</p>
          </Card>
        </div>

        <Card className="p-6 border border-border">
          <h3 className="text-lg font-semibold mb-4">Recent Alerts</h3>
          <div className="space-y-3">
            <div className="p-4 rounded bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-900/30">
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-red-600 flex-shrink-0 mt-0.5" />
                  <span className="text-sm font-semibold">Misinformation: Pricing on Perplexity</span>
                </div>
                <Badge variant="destructive" className="text-xs">Critical</Badge>
              </div>
              <p className="text-xs text-muted-foreground ml-6">3 instances detected - Incorrect product pricing displayed</p>
              <p className="text-xs text-muted-foreground ml-6 mt-1">Last updated: 2 hours ago</p>
            </div>

            <div className="p-4 rounded bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-900/30">
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
                  <span className="text-sm font-semibold">Competitor gaining visibility</span>
                </div>
                <Badge variant="secondary" className="bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400 text-xs">Warning</Badge>
              </div>
              <p className="text-xs text-muted-foreground ml-6">Competitor A increased 12% in last 7 days</p>
              <p className="text-xs text-muted-foreground ml-6 mt-1">Last updated: 5 hours ago</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Footer */}
      <div className="pt-6 border-t">
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <p>Detailed Analytics Report - AI Visibility Monitor</p>
          <p>Page 1 of 1 | Confidential</p>
        </div>
      </div>
    </div>
  );
};
