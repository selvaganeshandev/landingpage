import { MetricCard } from "@/components/MetricCard";
import { VisibilityScore } from "@/components/VisibilityScore";
import { PlatformMentions } from "@/components/PlatformMentions";
import { CompetitorComparison } from "@/components/CompetitorComparison";
import { MentionTable } from "@/components/MentionTable";
import { TrendChart } from "@/components/TrendChart";
import { Eye, TrendingUp, Target, Bell } from "lucide-react";
import { Button } from "@/components/ui/button";

const Dashboard = () => {
  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground mt-2">
            Overview of your brand's AI search visibility performance
          </p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline">Export Report</Button>
          <Button>Refresh Data</Button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Total Mentions"
          value="221"
          change={15.2}
          trend="up"
          icon={<Eye className="h-6 w-6" />}
        />
        <MetricCard
          title="Visibility Score"
          value="94"
          change={8.5}
          trend="up"
          icon={<Target className="h-6 w-6" />}
        />
        <MetricCard
          title="Avg Position"
          value="1.6"
          change={-12.3}
          trend="up"
          icon={<TrendingUp className="h-6 w-6" />}
        />
        <MetricCard
          title="Active Alerts"
          value="12"
          icon={<Bell className="h-6 w-6" />}
        />
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <VisibilityScore
            brand="VegFit Pro"
            score={94}
            mentions={221}
            sentiment={{ positive: 74, neutral: 21, negative: 5 }}
          />
          <TrendChart />
        </div>
        <div className="space-y-6">
          <PlatformMentions />
          <CompetitorComparison />
        </div>
      </div>

      {/* Mentions Table */}
      <MentionTable />
    </div>
  );
};

export default Dashboard;
