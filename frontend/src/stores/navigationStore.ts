import { create } from 'zustand';
import { MODULES } from '@/types/auth';
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
  Activity,
  Lightbulb,
  MessageSquarePlus,
  Clock,
  Calendar,
} from 'lucide-react';

export interface NavItem {
  name: string;
  path: string;
  icon: any;
  module: string;
  requiredLevel?: 'read' | 'write' | 'admin';
}

export interface NavGroup {
  name: string;
  icon?: any;
  items: NavItem[];
  separator?: boolean;
  scrollable?: boolean;
}

interface NavigationState {
  navGroups: NavGroup[];
  filteredNavGroups: NavGroup[];
  
  // Actions
  filterByPermissions: (checkPermission: (module: string, level?: 'read' | 'write' | 'admin') => boolean) => void;
  getFilteredNavGroups: () => NavGroup[];
}

const allNavGroups: NavGroup[] = [
  {
    name: "Chat",
    items: [
      { name: "New Chat", path: "/chat", icon: MessageSquarePlus, module: MODULES.DASHBOARD },
    ],
  },
  {
    name: "Overview",
    items: [
      { name: "Insights", path: "/insights", icon: LayoutDashboard, module: MODULES.DASHBOARD },
    ],
  },
  {
    name: "Tracking",
    icon: Activity,
    items: [
      { name: "Prompts", path: "/prompts", icon: Search, module: MODULES.PROMPTS },
      { name: "Mentions", path: "/mentions", icon: MessageSquare, module: MODULES.MENTIONS },
      { name: "Alerts", path: "/alerts", icon: Bell, module: MODULES.ALERTS },
    ],
  },
  {
    name: "Analytics",
    icon: BarChart3,
    items: [
      { name: "Sentiment", path: "/sentiment", icon: TrendingUp, module: MODULES.SENTIMENT_ANALYSIS },
      { name: "Topics", path: "/topics", icon: Brain, module: MODULES.TOPICS },
      { name: "Share of Voice", path: "/share-of-voice", icon: BarChart3, module: MODULES.SHARE_OF_VOICE },
      { name: "Historical Trends", path: "/trends", icon: LineChart, module: MODULES.HISTORICAL_TRENDS },
    ],
  },
  {
    name: "Strategy",
    icon: Lightbulb,
    items: [
      { name: "Competitors", path: "/competitors", icon: Users, module: MODULES.COMPETITORS },
      { name: "Content Gaps", path: "/content-gaps", icon: Target, module: MODULES.CONTENT_GAPS },
      { name: "Content Planner", path: "/content-calendar", icon: Calendar, module: MODULES.CONTENT_GAPS },
    ],
  },
  {
    name: "Advanced",
    icon: Sparkles,
    items: [
      // { name: "Multilingual", path: "/multilingual", icon: Globe, module: MODULES.MULTILINGUAL },
      { name: "Traffic Attribution", path: "/traffic", icon: Link2, module: MODULES.TRAFFIC_ATTRIBUTION },
      { name: "Misinformation", path: "/misinformation", icon: AlertTriangle, module: MODULES.MISINFORMATION_ALERTS },
    ],
  },
  {
    name: "Reporting",
    items: [
      { name: "Reports", path: "/reports", icon: FileText, module: MODULES.REPORTS },
    ],
  },
  {
    name: "Recents",
    icon: Clock,
    separator: true,
    scrollable: true,
    items: [],
  },
];

export const useNavigationStore = create<NavigationState>((set, get) => ({
  navGroups: allNavGroups,
  filteredNavGroups: allNavGroups,

  filterByPermissions: (checkPermission) => {
    const { navGroups } = get();

    const filteredGroups = navGroups
      .map(group => ({
        ...group,
        items: group.items.filter(item => checkPermission(item.module, item.requiredLevel))
      }))
      .filter(group => group.items.length > 0 || group.name === "Recents"); // Keep Recents visible even when empty

    set({ filteredNavGroups: filteredGroups });
  },

  getFilteredNavGroups: () => {
    return get().filteredNavGroups;
  },
}));
