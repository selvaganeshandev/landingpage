import { Link, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Search,
  MessageSquare,
  TrendingUp,
  BarChart3,
  Target,
  Link2,
  LineChart,
  Globe,
  Bell,
  Users,
  FileText,
  Brain,
  Sparkles,
  AlertTriangle,
  Network,
  Settings,
} from "lucide-react";

const navItems = [
  { name: "Dashboard", path: "/", icon: LayoutDashboard },
  { name: "Prompt Monitoring", path: "/prompts", icon: Search },
  { name: "Mention Tracking", path: "/mentions", icon: MessageSquare },
  { name: "Sentiment Analysis", path: "/sentiment", icon: TrendingUp },
  { name: "Share of Voice", path: "/share-of-voice", icon: BarChart3 },
  { name: "Content Gaps", path: "/content-gaps", icon: Target },
  { name: "Traffic Attribution", path: "/traffic", icon: Link2 },
  { name: "Historical Trends", path: "/trends", icon: LineChart },
  { name: "AI Crawler Analysis", path: "/crawler", icon: Network },
  { name: "Topic Tracking", path: "/topics", icon: Brain },
  { name: "Multilingual", path: "/multilingual", icon: Globe },
  { name: "Alerts", path: "/alerts", icon: Bell },
  { name: "Competitors", path: "/competitors", icon: Users },
  { name: "Reports", path: "/reports", icon: FileText },
  { name: "AI Copilot", path: "/copilot", icon: Sparkles },
  { name: "Prompt Insights", path: "/prompt-insights", icon: TrendingUp },
  { name: "Misinformation", path: "/misinformation", icon: AlertTriangle },
  { name: "Agent Analytics", path: "/agent-analytics", icon: Network },
];

export const Sidebar = () => {
  const location = useLocation();

  return (
    <aside className="w-64 bg-card border-r border-border h-screen sticky top-0 overflow-y-auto">
      <div className="p-6 border-b border-border">
        <h2 className="text-xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
          AI Visibility Pro
        </h2>
        <p className="text-xs text-muted-foreground mt-1">Brand Intelligence Platform</p>
      </div>
      
      <nav className="p-4 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;
          
          return (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              {item.name}
            </Link>
          );
        })}
      </nav>
      
      <div className="p-4 border-t border-border mt-auto">
        <Link
          to="/settings"
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
        >
          <Settings className="h-4 w-4" />
          Settings
        </Link>
      </div>
    </aside>
  );
};
