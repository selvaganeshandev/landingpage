import { useState } from "react";
import { MetricCard } from "@/components/MetricCard";
import { VisibilityScore } from "@/components/VisibilityScore";
import { PlatformMentions } from "@/components/PlatformMentions";
import { CompetitorComparison } from "@/components/CompetitorComparison";
import { MentionTable } from "@/components/MentionTable";
import { TrendChart } from "@/components/TrendChart";
import { TimeFilter } from "@/components/TimeFilter";
import { Eye, TrendingUp, Target, Bell, Link2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";

const Dashboard = () => {
  const [timePeriod, setTimePeriod] = useState("30");
  const { toast } = useToast();

  const handleExportReport = () => {
    toast({
      title: "Exporting Report",
      description: "Your dashboard report is being generated...",
    });
  };

  const handleRefreshData = () => {
    toast({
      title: "Data Refreshed",
      description: "Dashboard data has been updated successfully.",
    });
  };

  return (
    <div className="p-8 space-y-8">
      <div className="space-y-4">
        <div className="flex items-center justify-between pb-4 border-b border-border/50">
          <div>
            <h1 className="text-4xl font-bold tracking-tight font-outfit bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">Dashboard</h1>
            <p className="text-muted-foreground mt-2">
              Overview of your brand's AI search visibility performance
            </p>
          </div>
          <div className="flex gap-3">
            <Button variant="outline" onClick={handleExportReport} className="border-border/50">Export Report</Button>
            <Button onClick={handleRefreshData} className="gradient-primary shadow-md shadow-primary/20">Refresh Data</Button>
          </div>
        </div>
        <TimeFilter selected={timePeriod} onSelect={setTimePeriod} />
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        <MetricCard
          title="Total Mentions"
          value="221"
          change={15.2}
          trend="up"
          icon={<Eye className="h-6 w-6" />}
        />
        <MetricCard
          title="Total Citations"
          value="487"
          change={23.4}
          trend="up"
          icon={<Link2 className="h-6 w-6" />}
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
