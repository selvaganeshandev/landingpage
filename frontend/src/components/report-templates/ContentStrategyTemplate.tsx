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

export const ContentStrategyTemplate = () => {
  return (
    <div className="w-full bg-background space-y-8">
      {/* Header Section */}
      <div className="border-b pb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">Content Strategy Report</h1>
            <p className="text-muted-foreground">Gap Analysis, Opportunities & Recommendations</p>
          </div>
          <div className="text-right">
            <p className="text-sm text-muted-foreground">Report Period</p>
            <p className="font-semibold">{new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}</p>
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
                A+
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mb-1">Content Quality Score</p>
            <p className="text-3xl font-bold">92/100</p>
            <p className="text-xs text-muted-foreground mt-2">Excellent performance</p>
          </Card>

          <Card className="p-5 border border-border">
            <div className="flex items-center justify-between mb-3">
              <Target className="h-6 w-6 text-green-600 dark:text-green-400" />
              <Badge variant="outline" className="bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400">
                <TrendingUp className="h-3 w-3 mr-1" />
                +24%
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mb-1">Topics Covered</p>
            <p className="text-3xl font-bold">247</p>
            <p className="text-xs text-muted-foreground mt-2">vs. 199 last period</p>
          </Card>

          <Card className="p-5 border border-border">
            <div className="flex items-center justify-between mb-3">
              <Sparkles className="h-6 w-6 text-purple-600 dark:text-purple-400" />
              <Badge variant="outline">
                <Flame className="h-3 w-3 mr-1" />
                Hot
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mb-1">Content Gaps Found</p>
            <p className="text-3xl font-bold">18</p>
            <p className="text-xs text-muted-foreground mt-2">High opportunity areas</p>
          </Card>

          <Card className="p-5 border border-border">
            <div className="flex items-center justify-between mb-3">
              <Award className="h-6 w-6 text-amber-600 dark:text-amber-400" />
              <Badge variant="outline" className="bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400">
                <TrendingUp className="h-3 w-3 mr-1" />
                +18%
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mb-1">Engagement Rate</p>
            <p className="text-3xl font-bold">87%</p>
            <p className="text-xs text-muted-foreground mt-2">Above industry avg</p>
          </Card>
        </div>
      </div>

      {/* Content Gap Analysis */}
      <div>
        <h2 className="text-2xl font-bold mb-6">Content Gap Analysis</h2>
        <Card className="p-6 border border-border">
          <div className="space-y-4">
            {/* High Priority Gap */}
            <div className="p-5 rounded-lg bg-red-50 dark:bg-red-900/10 border-2 border-red-500">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-red-600 flex items-center justify-center">
                    <AlertTriangle className="h-5 w-5 text-white" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-lg font-bold">Climate-Conscious Nutrition</h3>
                      <Badge variant="destructive">Critical Gap</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">High search volume, zero current coverage</p>
                  </div>
                </div>
                <Badge className="bg-red-600 text-white">Priority 1</Badge>
              </div>
              <div className="grid grid-cols-4 gap-4 mt-4 pt-4 border-t border-red-200 dark:border-red-900/30">
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Search Volume</p>
                  <p className="text-lg font-bold">12,400/mo</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Competitor Coverage</p>
                  <p className="text-lg font-bold">3/5</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Opportunity Score</p>
                  <p className="text-lg font-bold text-red-600">95/100</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Est. Traffic Gain</p>
                  <p className="text-lg font-bold">+1,240/mo</p>
                </div>
              </div>
              <div className="mt-4 p-3 bg-white dark:bg-background rounded border border-red-200 dark:border-red-900/30">
                <p className="text-sm font-semibold mb-2">Recommended Topics:</p>
                <div className="flex gap-2 flex-wrap">
                  <Badge variant="outline" className="text-xs">carbon footprint tracking</Badge>
                  <Badge variant="outline" className="text-xs">sustainable protein sources</Badge>
                  <Badge variant="outline" className="text-xs">eco-friendly packaging</Badge>
                  <Badge variant="outline" className="text-xs">climate impact comparison</Badge>
                </div>
              </div>
            </div>

            {/* Medium Priority Gap */}
            <div className="p-5 rounded-lg bg-amber-50 dark:bg-amber-900/10 border border-amber-500">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-amber-600 flex items-center justify-center">
                    <Lightbulb className="h-5 w-5 text-white" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-lg font-bold">AI-Powered Meal Planning</h3>
                      <Badge variant="secondary" className="bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400">High Opportunity</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">Growing trend, limited current content</p>
                  </div>
                </div>
                <Badge className="bg-amber-600 text-white">Priority 2</Badge>
              </div>
              <div className="grid grid-cols-4 gap-4 mt-4 pt-4 border-t border-amber-200 dark:border-amber-900/30">
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Search Volume</p>
                  <p className="text-lg font-bold">8,900/mo</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Competitor Coverage</p>
                  <p className="text-lg font-bold">2/5</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Opportunity Score</p>
                  <p className="text-lg font-bold text-amber-600">88/100</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Est. Traffic Gain</p>
                  <p className="text-lg font-bold">+890/mo</p>
                </div>
              </div>
              <div className="mt-4 p-3 bg-white dark:bg-background rounded border border-amber-200 dark:border-amber-900/30">
                <p className="text-sm font-semibold mb-2">Recommended Topics:</p>
                <div className="flex gap-2 flex-wrap">
                  <Badge variant="outline" className="text-xs">personalized nutrition AI</Badge>
                  <Badge variant="outline" className="text-xs">smart meal recommendations</Badge>
                  <Badge variant="outline" className="text-xs">AI fitness coaching</Badge>
                </div>
              </div>
            </div>

            {/* Good Coverage Gap */}
            <div className="p-5 rounded-lg bg-blue-50 dark:bg-blue-900/10 border border-blue-500">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center">
                    <Telescope className="h-5 w-5 text-white" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-lg font-bold">Gut Health Optimization</h3>
                      <Badge variant="secondary" className="bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400">Moderate Opportunity</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">Some coverage, room for expansion</p>
                  </div>
                </div>
                <Badge className="bg-blue-600 text-white">Priority 3</Badge>
              </div>
              <div className="grid grid-cols-4 gap-4 mt-4 pt-4 border-t border-blue-200 dark:border-blue-900/30">
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Search Volume</p>
                  <p className="text-lg font-bold">6,200/mo</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Competitor Coverage</p>
                  <p className="text-lg font-bold">4/5</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Opportunity Score</p>
                  <p className="text-lg font-bold text-blue-600">72/100</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Est. Traffic Gain</p>
                  <p className="text-lg font-bold">+620/mo</p>
                </div>
              </div>
              <div className="mt-4 p-3 bg-white dark:bg-background rounded border border-blue-200 dark:border-blue-900/30">
                <p className="text-sm font-semibold mb-2">Recommended Topics:</p>
                <div className="flex gap-2 flex-wrap">
                  <Badge variant="outline" className="text-xs">microbiome health</Badge>
                  <Badge variant="outline" className="text-xs">probiotic supplements</Badge>
                  <Badge variant="outline" className="text-xs">digestive wellness</Badge>
                </div>
              </div>
            </div>
          </div>
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
              <div className="flex items-center justify-between p-3 rounded bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-900/30">
                <div>
                  <p className="text-sm font-semibold">carbon neutral protein</p>
                  <p className="text-xs text-muted-foreground">Zero current mentions</p>
                </div>
                <div className="text-right">
                  <Badge className="bg-green-600 text-white mb-1">High</Badge>
                  <p className="text-xs text-muted-foreground">8,400/mo</p>
                </div>
              </div>
              <div className="flex items-center justify-between p-3 rounded bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-900/30">
                <div>
                  <p className="text-sm font-semibold">AI nutrition coach</p>
                  <p className="text-xs text-muted-foreground">Zero current mentions</p>
                </div>
                <div className="text-right">
                  <Badge className="bg-green-600 text-white mb-1">High</Badge>
                  <p className="text-xs text-muted-foreground">6,700/mo</p>
                </div>
              </div>
              <div className="flex items-center justify-between p-3 rounded bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-900/30">
                <div>
                  <p className="text-sm font-semibold">sustainable supplements</p>
                  <p className="text-xs text-muted-foreground">Low current mentions</p>
                </div>
                <div className="text-right">
                  <Badge className="bg-amber-600 text-white mb-1">Med</Badge>
                  <p className="text-xs text-muted-foreground">5,200/mo</p>
                </div>
              </div>
              <div className="flex items-center justify-between p-3 rounded bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-900/30">
                <div>
                  <p className="text-sm font-semibold">eco protein powder</p>
                  <p className="text-xs text-muted-foreground">Low current mentions</p>
                </div>
                <div className="text-right">
                  <Badge className="bg-amber-600 text-white mb-1">Med</Badge>
                  <p className="text-xs text-muted-foreground">4,800/mo</p>
                </div>
              </div>
            </div>
          </Card>

          <Card className="p-6 border border-border">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-primary" />
              Trending Topics to Amplify
            </h3>
            <div className="space-y-3">
              <div className="p-3 rounded bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-900/30">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold">Vegan protein powder</span>
                  <Badge className="bg-blue-600 text-white">
                    <TrendingUp className="h-3 w-3 mr-1" />
                    +127%
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground mb-2">Already strong, amplify further</p>
                <div className="flex gap-2">
                  <Badge variant="outline" className="text-xs">847 mentions</Badge>
                  <Badge variant="outline" className="text-xs">12.4K searches/mo</Badge>
                </div>
              </div>
              <div className="p-3 rounded bg-purple-50 dark:bg-purple-900/10 border border-purple-200 dark:border-purple-900/30">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold">Plant-based fitness</span>
                  <Badge className="bg-purple-600 text-white">
                    <TrendingUp className="h-3 w-3 mr-1" />
                    +94%
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground mb-2">Growing fast, maintain momentum</p>
                <div className="flex gap-2">
                  <Badge variant="outline" className="text-xs">623 mentions</Badge>
                  <Badge variant="outline" className="text-xs">9.8K searches/mo</Badge>
                </div>
              </div>
              <div className="p-3 rounded bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-900/30">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold">Sustainable nutrition</span>
                  <Badge className="bg-green-600 text-white">
                    <TrendingUp className="h-3 w-3 mr-1" />
                    +82%
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground mb-2">Hot topic, increase coverage</p>
                <div className="flex gap-2">
                  <Badge variant="outline" className="text-xs">541 mentions</Badge>
                  <Badge variant="outline" className="text-xs">8.2K searches/mo</Badge>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Content Performance by Topic */}
      <div>
        <h2 className="text-2xl font-bold mb-6">Content Performance by Topic Category</h2>
        <Card className="p-6 border border-border">
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 rounded bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-900/30">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                  <h4 className="font-semibold">Plant-Based Nutrition</h4>
                  <Badge className="bg-green-600 text-white">Excellent</Badge>
                </div>
                <div className="grid grid-cols-4 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground text-xs">Coverage</p>
                    <p className="font-bold">94/100</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs">Mentions</p>
                    <p className="font-bold">1,247</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs">Engagement</p>
                    <p className="font-bold">92%</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs">Growth</p>
                    <p className="font-bold text-green-600">+35%</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between p-4 rounded bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-900/30">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <CheckCircle2 className="h-5 w-5 text-blue-600" />
                  <h4 className="font-semibold">Fitness & Performance</h4>
                  <Badge className="bg-blue-600 text-white">Good</Badge>
                </div>
                <div className="grid grid-cols-4 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground text-xs">Coverage</p>
                    <p className="font-bold">87/100</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs">Mentions</p>
                    <p className="font-bold">1,089</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs">Engagement</p>
                    <p className="font-bold">88%</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs">Growth</p>
                    <p className="font-bold text-blue-600">+28%</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between p-4 rounded bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-900/30">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <AlertTriangle className="h-5 w-5 text-amber-600" />
                  <h4 className="font-semibold">Sustainability & Environment</h4>
                  <Badge className="bg-amber-600 text-white">Needs Work</Badge>
                </div>
                <div className="grid grid-cols-4 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground text-xs">Coverage</p>
                    <p className="font-bold">62/100</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs">Mentions</p>
                    <p className="font-bold">412</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs">Engagement</p>
                    <p className="font-bold">79%</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs">Growth</p>
                    <p className="font-bold text-amber-600">+12%</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between p-4 rounded bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-900/30">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <AlertTriangle className="h-5 w-5 text-red-600" />
                  <h4 className="font-semibold">Technology & Innovation</h4>
                  <Badge variant="destructive">Critical Gap</Badge>
                </div>
                <div className="grid grid-cols-4 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground text-xs">Coverage</p>
                    <p className="font-bold">38/100</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs">Mentions</p>
                    <p className="font-bold">187</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs">Engagement</p>
                    <p className="font-bold">71%</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs">Growth</p>
                    <p className="font-bold text-red-600">+5%</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Competitor Content Comparison */}
      <div>
        <h2 className="text-2xl font-bold mb-6">Competitor Content Comparison</h2>
        <Card className="p-6 border border-border">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3 px-4 font-semibold">Topic Category</th>
                  <th className="text-center py-3 px-4 font-semibold">Your Brand</th>
                  <th className="text-center py-3 px-4 font-semibold">PlantPower</th>
                  <th className="text-center py-3 px-4 font-semibold">GreenFuel</th>
                  <th className="text-center py-3 px-4 font-semibold">Status</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b hover:bg-muted/30">
                  <td className="py-3 px-4 font-medium">Plant-Based Nutrition</td>
                  <td className="text-center py-3 px-4">
                    <Badge className="bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400">94%</Badge>
                  </td>
                  <td className="text-center py-3 px-4">
                    <Badge variant="outline">82%</Badge>
                  </td>
                  <td className="text-center py-3 px-4">
                    <Badge variant="outline">78%</Badge>
                  </td>
                  <td className="text-center py-3 px-4">
                    <Badge className="bg-green-600 text-white">Leading</Badge>
                  </td>
                </tr>
                <tr className="border-b hover:bg-muted/30">
                  <td className="py-3 px-4 font-medium">Fitness & Performance</td>
                  <td className="text-center py-3 px-4">
                    <Badge className="bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400">87%</Badge>
                  </td>
                  <td className="text-center py-3 px-4">
                    <Badge variant="outline">79%</Badge>
                  </td>
                  <td className="text-center py-3 px-4">
                    <Badge variant="outline">85%</Badge>
                  </td>
                  <td className="text-center py-3 px-4">
                    <Badge className="bg-green-600 text-white">Leading</Badge>
                  </td>
                </tr>
                <tr className="border-b hover:bg-muted/30">
                  <td className="py-3 px-4 font-medium">Sustainability</td>
                  <td className="text-center py-3 px-4">
                    <Badge variant="outline">62%</Badge>
                  </td>
                  <td className="text-center py-3 px-4">
                    <Badge className="bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400">71%</Badge>
                  </td>
                  <td className="text-center py-3 px-4">
                    <Badge className="bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400">68%</Badge>
                  </td>
                  <td className="text-center py-3 px-4">
                    <Badge variant="secondary" className="bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400">Behind</Badge>
                  </td>
                </tr>
                <tr className="border-b hover:bg-muted/30">
                  <td className="py-3 px-4 font-medium">Technology & AI</td>
                  <td className="text-center py-3 px-4">
                    <Badge variant="outline">38%</Badge>
                  </td>
                  <td className="text-center py-3 px-4">
                    <Badge className="bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400">52%</Badge>
                  </td>
                  <td className="text-center py-3 px-4">
                    <Badge variant="outline">41%</Badge>
                  </td>
                  <td className="text-center py-3 px-4">
                    <Badge variant="destructive">Critical Gap</Badge>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      {/* Content Calendar Recommendations */}
      <div>
        <h2 className="text-2xl font-bold mb-6">30-Day Content Calendar</h2>
        <Card className="p-6 border border-border">
          <div className="space-y-3">
            <div className="p-4 rounded bg-gradient-to-r from-red-50 to-red-100 dark:from-red-900/20 dark:to-red-900/10 border-l-4 border-l-red-500">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3">
                  <Calendar className="h-5 w-5 text-red-600" />
                  <div>
                    <h4 className="font-semibold">Week 1: Climate-Conscious Nutrition Launch</h4>
                    <p className="text-xs text-muted-foreground">Critical gap - immediate priority</p>
                  </div>
                </div>
                <Badge variant="destructive">Priority 1</Badge>
              </div>
              <div className="mt-3 space-y-1 text-sm">
                <p className="flex items-center gap-2">
                  <Plus className="h-3 w-3" />
                  Create: "Ultimate Guide to Carbon Neutral Protein"
                </p>
                <p className="flex items-center gap-2">
                  <Plus className="h-3 w-3" />
                  Create: "Comparing Carbon Footprints of Protein Sources"
                </p>
                <p className="flex items-center gap-2">
                  <Plus className="h-3 w-3" />
                  Create: "Sustainable Packaging in Nutrition Industry"
                </p>
              </div>
            </div>

            <div className="p-4 rounded bg-gradient-to-r from-amber-50 to-amber-100 dark:from-amber-900/20 dark:to-amber-900/10 border-l-4 border-l-amber-500">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3">
                  <Calendar className="h-5 w-5 text-amber-600" />
                  <div>
                    <h4 className="font-semibold">Week 2: AI-Powered Nutrition Series</h4>
                    <p className="text-xs text-muted-foreground">High opportunity - emerging trend</p>
                  </div>
                </div>
                <Badge className="bg-amber-600 text-white">Priority 2</Badge>
              </div>
              <div className="mt-3 space-y-1 text-sm">
                <p className="flex items-center gap-2">
                  <Plus className="h-3 w-3" />
                  Create: "How AI Personalizes Your Nutrition Plan"
                </p>
                <p className="flex items-center gap-2">
                  <Plus className="h-3 w-3" />
                  Create: "Smart Meal Planning with AI Technology"
                </p>
              </div>
            </div>

            <div className="p-4 rounded bg-gradient-to-r from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-900/10 border-l-4 border-l-blue-500">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3">
                  <Calendar className="h-5 w-5 text-blue-600" />
                  <div>
                    <h4 className="font-semibold">Week 3: Gut Health Deep Dive</h4>
                    <p className="text-xs text-muted-foreground">Moderate opportunity - expand existing content</p>
                  </div>
                </div>
                <Badge className="bg-blue-600 text-white">Priority 3</Badge>
              </div>
              <div className="mt-3 space-y-1 text-sm">
                <p className="flex items-center gap-2">
                  <Plus className="h-3 w-3" />
                  Update: Expand existing microbiome content
                </p>
                <p className="flex items-center gap-2">
                  <Plus className="h-3 w-3" />
                  Create: "Probiotics for Athletes Guide"
                </p>
              </div>
            </div>

            <div className="p-4 rounded bg-gradient-to-r from-green-50 to-green-100 dark:from-green-900/20 dark:to-green-900/10 border-l-4 border-l-green-500">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3">
                  <Calendar className="h-5 w-5 text-green-600" />
                  <div>
                    <h4 className="font-semibold">Week 4: Amplify Top Performers</h4>
                    <p className="text-xs text-muted-foreground">Maintain momentum on strong topics</p>
                  </div>
                </div>
                <Badge className="bg-green-600 text-white">Maintenance</Badge>
              </div>
              <div className="mt-3 space-y-1 text-sm">
                <p className="flex items-center gap-2">
                  <Plus className="h-3 w-3" />
                  Refresh: Top vegan protein powder content
                </p>
                <p className="flex items-center gap-2">
                  <Plus className="h-3 w-3" />
                  Update: Plant-based fitness guides with new data
                </p>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Strategic Recommendations */}
      <div>
        <h2 className="text-2xl font-bold mb-6">Strategic Content Recommendations</h2>
        <div className="space-y-3">
          <div className="p-5 border-l-4 border-l-red-500 bg-red-50/50 dark:bg-red-900/10 rounded-lg">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-red-600 flex items-center justify-center text-sm font-bold text-white flex-shrink-0">
                1
              </div>
              <div className="flex-1">
                <h4 className="font-semibold mb-2">Immediately Address Climate-Conscious Nutrition Gap</h4>
                <p className="text-sm text-muted-foreground mb-3">
                  This is your largest content gap with the highest opportunity score (95/100). Competitors are gaining ground. Launch comprehensive content series within 7 days to capture 12,400 monthly searches.
                </p>
                <div className="flex gap-2">
                  <Badge variant="outline" className="text-xs">Timeline: 7 days</Badge>
                  <Badge variant="outline" className="text-xs">Content Pieces: 5-7 articles</Badge>
                  <Badge variant="outline" className="text-xs">Expected Traffic: +1,240/mo</Badge>
                </div>
              </div>
            </div>
          </div>

          <div className="p-5 border-l-4 border-l-amber-500 bg-amber-50/50 dark:bg-amber-900/10 rounded-lg">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-amber-600 flex items-center justify-center text-sm font-bold text-white flex-shrink-0">
                2
              </div>
              <div className="flex-1">
                <h4 className="font-semibold mb-2">Establish AI & Technology Content Leadership</h4>
                <p className="text-sm text-muted-foreground mb-3">
                  PlantPower leads this category (52% vs your 38%). AI-powered meal planning is trending +94%. Create authoritative content to reclaim leadership and capture emerging audience.
                </p>
                <div className="flex gap-2">
                  <Badge variant="outline" className="text-xs">Timeline: 14 days</Badge>
                  <Badge variant="outline" className="text-xs">Content Pieces: 4-6 articles</Badge>
                  <Badge variant="outline" className="text-xs">Expected Traffic: +890/mo</Badge>
                </div>
              </div>
            </div>
          </div>

          <div className="p-5 border-l-4 border-l-green-500 bg-green-50/50 dark:bg-green-900/10 rounded-lg">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-green-600 flex items-center justify-center text-sm font-bold text-white flex-shrink-0">
                3
              </div>
              <div className="flex-1">
                <h4 className="font-semibold mb-2">Double Down on Plant-Based Nutrition Excellence</h4>
                <p className="text-sm text-muted-foreground mb-3">
                  Your strongest category (94% coverage, 1,247 mentions, +35% growth). Maintain dominance by refreshing top content quarterly and expanding into adjacent topics before competitors can catch up.
                </p>
                <div className="flex gap-2">
                  <Badge variant="outline" className="text-xs">Timeline: Ongoing</Badge>
                  <Badge variant="outline" className="text-xs">Refresh Cycle: Quarterly</Badge>
                  <Badge variant="outline" className="text-xs">Status: Market Leader</Badge>
                </div>
              </div>
            </div>
          </div>
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
  );
};
