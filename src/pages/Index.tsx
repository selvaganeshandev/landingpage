import { MetricCard } from "@/components/MetricCard";
import { VisibilityScore } from "@/components/VisibilityScore";
import { PlatformMentions } from "@/components/PlatformMentions";
import { CompetitorComparison } from "@/components/CompetitorComparison";
import { MentionTable } from "@/components/MentionTable";
import { TrendChart } from "@/components/TrendChart";
import { Eye, TrendingUp, Target, Bell } from "lucide-react";
import { Button } from "@/components/ui/button";
import heroBg from "@/assets/hero-bg.jpg";

const Index = () => {
  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-accent/20">
      {/* Hero Section */}
      <section 
        className="relative h-[400px] flex items-center justify-center overflow-hidden"
        style={{
          backgroundImage: `url(${heroBg})`,
          backgroundSize: "cover",
          backgroundPosition: "center",
        }}
      >
        <div className="absolute inset-0 bg-gradient-to-r from-primary/90 to-secondary/90" />
        <div className="relative z-10 text-center space-y-6 px-4">
          <h1 className="text-5xl md:text-6xl font-bold text-white tracking-tight">
            AI Search Visibility Tracker
          </h1>
          <p className="text-xl text-white/90 max-w-2xl mx-auto">
            Monitor your brand's performance across ChatGPT, Claude, Perplexity, and Gemini
          </p>
          <div className="flex items-center justify-center gap-4">
            <Button size="lg" variant="secondary">
              View Full Report
            </Button>
            <Button size="lg" variant="outline" className="bg-white/10 text-white border-white/20 hover:bg-white/20">
              Export Data
            </Button>
          </div>
        </div>
      </section>

      {/* Main Content */}
      <div className="container mx-auto px-4 -mt-16 relative z-20">
        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
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
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
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
        <div className="mb-8">
          <MentionTable />
        </div>
      </div>
    </div>
  );
};

export default Index;
