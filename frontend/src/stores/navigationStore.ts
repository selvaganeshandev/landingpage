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
  Bell,
  Users,
  FileText,
  Brain,
  Sparkles,
  AlertTriangle,
  Activity,
  Lightbulb,
  Calendar,
  ExternalLink,
  SearchCheck,
} from 'lucide-react';

export interface NavItem {
  name: string;
  path: string;
  icon: any;
  module: string;
  requiredLevel?: 'read' | 'write' | 'admin';
  conversationId?: number; // For recent chats
}

export interface NavGroup {
  name: string;
  icon?: any;
  items: NavItem[];
  separator?: boolean;
  scrollable?: boolean;
  sectionLabel?: boolean; // If true, renders as a text label header only
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
    name: "Overview",
    items: [
      { name: "Insights", path: "/insights", icon: LayoutDashboard, module: MODULES.DASHBOARD },
    ],
  },
  // GEO Monitoring Section
  {
    name: "GEO Monitoring",
    sectionLabel: true,
    separator: true,
    items: [],
  },
  {
    name: "Tracking",
    icon: Activity,
    items: [
      { name: "Prompts", path: "/prompts", icon: Search, module: MODULES.PROMPTS },
      { name: "Mentions", path: "/mentions", icon: MessageSquare, module: MODULES.MENTIONS },
      { name: "Citations", path: "/citations", icon: ExternalLink, module: MODULES.CITATIONS },
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
    name: "Advanced",
    icon: Sparkles,
    items: [
      { name: "Traffic Attribution", path: "/traffic", icon: Link2, module: MODULES.TRAFFIC_ATTRIBUTION },
      { name: "Misinformation", path: "/misinformation", icon: AlertTriangle, module: MODULES.MISINFORMATION_ALERTS },
    ],
  },
  {
    name: "GEO Reports",
    items: [
      { name: "Reports", path: "/reports", icon: FileText, module: MODULES.REPORTS },
    ],
  },
  // SEO Monitoring Section
  {
    name: "SEO Monitoring",
    sectionLabel: true,
    separator: true,
    items: [],
  },
  {
    name: "Rankings",
    icon: SearchCheck,
    items: [
      { name: "Keyword Rankings", path: "/seo-rankings", icon: TrendingUp, module: MODULES.SEO_RANKINGS },
      { name: "Competitors", path: "/seo-competitors", icon: Users, module: MODULES.SEO_COMPETITORS },
    ],
  },
  {
    name: "Organic Reports",
    items: [
      { name: "Organic Reports", path: "/seo-reports", icon: FileText, module: MODULES.SEO_RANKINGS },
    ],
  },
  // Strategy Section
  {
    name: "Strategy",
    sectionLabel: true,
    separator: true,
    items: [],
  },
  {
    name: "Strategy",
    icon: Lightbulb,
    items: [
      { name: "Content Gaps", path: "/content-gaps", icon: Target, module: MODULES.CONTENT_GAPS },
      { name: "Competitors", path: "/competitors", icon: Users, module: MODULES.COMPETITORS },
      { name: "Content Planner", path: "/content-calendar", icon: Calendar, module: MODULES.CONTENT_PLANNER },
    ],
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
      .filter(group => group.items.length > 0 || group.sectionLabel); // Keep section labels visible

    set({ filteredNavGroups: filteredGroups });
  },

  getFilteredNavGroups: () => {
    return get().filteredNavGroups;
  },
}));
