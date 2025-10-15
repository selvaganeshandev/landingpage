import { Link, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
import { useState } from "react";
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
  ChevronDown,
  ChevronRight,
  Activity,
  Lightbulb,
  Zap,
  LogOut,
  Calendar,
} from "lucide-react";
import { DomainSelector } from "./DomainSelector";
import { Separator } from "@/components/ui/separator";

const navGroups = [
  {
    name: "Overview",
    items: [
      { name: "Dashboard", path: "/", icon: LayoutDashboard },
    ],
  },
  {
    name: "Tracking",
    icon: Activity,
    items: [
      { name: "Mentions", path: "/mentions", icon: MessageSquare },
      { name: "Prompts", path: "/prompts", icon: Search },
      { name: "Alerts", path: "/alerts", icon: Bell },
    ],
  },
  {
    name: "Analytics",
    icon: BarChart3,
    items: [
      { name: "Sentiment", path: "/sentiment", icon: TrendingUp },
      { name: "Topics", path: "/topics", icon: Brain },
      { name: "Share of Voice", path: "/share-of-voice", icon: BarChart3 },
      { name: "Historical Trends", path: "/trends", icon: LineChart },
    ],
  },
  {
    name: "Strategy",
    icon: Lightbulb,
    items: [
      { name: "Content Gaps", path: "/content-gaps", icon: Target },
      { name: "Content Calendar", path: "/content-calendar", icon: Calendar },
      { name: "Automation", path: "/automation", icon: Zap },
      { name: "Competitors", path: "/competitors", icon: Users },
    ],
  },
  {
    name: "Advanced",
    icon: Zap,
    items: [
      { name: "Multilingual", path: "/multilingual", icon: Globe },
      { name: "AI Copilot", path: "/copilot", icon: Sparkles },
      { name: "Prompt Insights", path: "/prompt-insights", icon: TrendingUp },
      { name: "Agent Analytics", path: "/agent-analytics", icon: Network },
      { name: "AI Crawler", path: "/crawler", icon: Network },
      { name: "Traffic Attribution", path: "/traffic", icon: Link2 },
      { name: "Misinformation", path: "/misinformation", icon: AlertTriangle },
    ],
  },
  {
    name: "Reporting",
    items: [
      { name: "Reports", path: "/reports", icon: FileText },
    ],
  },
];

const NavGroup = ({ group, location }: { group: typeof navGroups[0]; location: any }) => {
  const [isOpen, setIsOpen] = useState(true);
  
  // Check if any item in group is active
  const hasActiveItem = group.items.some(item => location.pathname === item.path);
  
  // If group has only one item, render it directly
  if (group.items.length === 1) {
    const item = group.items[0];
    const Icon = item.icon;
    const isActive = location.pathname === item.path;
    
    return (
      <Link
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
  }
  
  const GroupIcon = group.icon;
  
  return (
    <div className="space-y-1">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "w-full flex items-center justify-between gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
          hasActiveItem
            ? "text-primary"
            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
        )}
      >
        <div className="flex items-center gap-3">
          {GroupIcon && <GroupIcon className="h-4 w-4" />}
          <span>{group.name}</span>
        </div>
        {isOpen ? (
          <ChevronDown className="h-4 w-4" />
        ) : (
          <ChevronRight className="h-4 w-4" />
        )}
      </button>
      
      {isOpen && (
        <div className="ml-4 space-y-1">
          {group.items.map((item) => {
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
                <Icon className="h-3 w-3" />
                {item.name}
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
};

export const Sidebar = () => {
  const location = useLocation();

  return (
    <aside className="w-64 bg-card border-r border-border h-screen sticky top-0 overflow-y-auto flex flex-col">
      <div className="p-6 border-b border-border">
        <h2 className="text-xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
          PromptMaxx
        </h2>
        <p className="text-xs text-muted-foreground mt-1">AI Visibility & Content Strategy</p>
        <div className="mt-4">
          <DomainSelector />
        </div>
      </div>
      
      <nav className="p-4 space-y-2 flex-1">
        {navGroups.map((group, index) => (
          <NavGroup key={index} group={group} location={location} />
        ))}
      </nav>
      
      <div className="p-4 border-t border-border mt-auto space-y-2">
        <Link
          to="/organization-settings"
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
        >
          <Settings className="h-4 w-4" />
          Organization
        </Link>
        <button
          onClick={() => {/* TODO: Add logout */}}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
        >
          <LogOut className="h-4 w-4" />
          Sign Out
        </button>
      </div>
    </aside>
  );
};
