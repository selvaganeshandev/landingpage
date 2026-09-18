import { create } from 'zustand';
import { MODULES } from '@/types/auth';
import {
  LayoutDashboard,
  PieChart,
  Search,
  MessageSquare,
  TrendingUp,
  BarChart3,
  Target,
  Link2,
  LineChart,
  FileSearch,
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
  Link as LinkIcon,
  SearchCheck,
  MessageSquareText,
  ScanSearch,
  CalendarClock,
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

export interface RecentChat {
  id: number;
  title?: string;
  updated_at: string;
}

interface NavigationState {
  navGroups: NavGroup[];
  filteredNavGroups: NavGroup[];
  recentChats: RecentChat[];

  // Actions
  filterByPermissions: (checkPermission: (module: string, level?: 'read' | 'write' | 'admin') => boolean) => void;
  getFilteredNavGroups: () => NavGroup[];
  updateRecentChats: (chats: RecentChat[]) => void;
}

const allNavGroups: NavGroup[] = [
  // Overview Section
  {
    name: "Overview",
    sectionLabel: true,
    items: [],
  },
  {
    name: "Dashboard",
    items: [
      // Label only — the route stays /insights so existing links and bookmarks
      // keep working. The underlying module is already MODULES.DASHBOARD.
      { name: "Dashboard", path: "/insights", icon: LayoutDashboard, module: MODULES.DASHBOARD },
    ],
  },
  {
    name: "Schedules",
    items: [
    ],
  },
  {
    name: "Ask Agent",
    items: [
      { name: "Ask Agent", path: "/chat", icon: MessageSquareText, module: MODULES.AI_COPILOT },
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
      { name: "Sources", path: "/sources", icon: LinkIcon, module: MODULES.CITATIONS },
      { name: "Alerts", path: "/alerts", icon: Bell, module: MODULES.ALERTS },
      // The run ledger is the evidence every other GEO screen is computed
      // from, so it led this group as a flat entry until the sidebar stopped
      // fitting on one screen. Inside Tracking it costs a hover and saves a row.
      { name: "Runs", path: "/runs", icon: Activity, module: MODULES.PROMPTS },
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
  // GEO competitors. Moved out of Strategy so each discipline owns its own
  // competitor view — this one alongside Share of Voice and Mentions, and the
  // SEO one under SEO Monitoring. Flat entry, matching its SEO counterpart.
  {
    name: "Competitors",
    items: [
      { name: "Competitors", path: "/competitors", icon: Users, module: MODULES.COMPETITORS },
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
  // Keywords and Competitors are siblings rather than a "Rankings" flyout with
  // two children. A group of one renders as a flat link (see Sidebar), so both
  // are reachable in a single click instead of hover-then-click.
  {
    name: "Keywords",
    items: [
      { name: "Keywords", path: "/seo-rankings", icon: SearchCheck, module: MODULES.KEYWORD_RANKINGS },
    ],
  },
  {
    name: "Opportunities",
    items: [
      { name: "Opportunities", path: "/seo-opportunities", icon: Target, module: MODULES.KEYWORD_RANKINGS },
    ],
  },
  {
    name: "Share of Voice",
    items: [
      { name: "Share of Voice", path: "/seo-share-of-voice", icon: PieChart, module: MODULES.SEO_COMPETITORS },
    ],
  },
  {
    name: "Competitors",
    items: [
      { name: "Competitors", path: "/seo-competitors", icon: Users, module: MODULES.SEO_COMPETITORS },
    ],
  },
  {
    name: "Backlinks",
    items: [
      { name: "Backlinks", path: "/seo-backlinks", icon: Link2, module: MODULES.BACKLINKS },
    ],
  },
  {
    name: "Organic Reports",
    items: [
      { name: "Organic Reports", path: "/seo-reports", icon: FileText, module: MODULES.ORGANIC_REPORTS },
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
      { name: "GEO Content Gaps", path: "/content-gaps", icon: Target, module: MODULES.CONTENT_GAPS },
      { name: "SEO Content Gaps", path: "/seo-content-gaps", icon: FileSearch, module: MODULES.KEYWORD_RANKINGS },
      { name: "Content Planner", path: "/content-calendar", icon: Calendar, module: MODULES.CONTENT_PLANNER },
    ],
  },
  // Audit Engine sits under Strategy as its own row, not inside the fly-out:
  // it is where new business comes from rather than a view of an existing
  // project, so it is worth a click of its own. Still an admin tool — the
  // backend scopes the leads table to admin / super_admin, so it rides on the
  // organization_settings module rather than a new one: super_admin always
  // passes, admins pass unless explicitly restricted, clients never do.
  {
    name: "Audit Engine",
    items: [
      { name: "Audit Engine", path: "/audits", icon: ScanSearch, module: MODULES.ORGANIZATION_SETTINGS },
    ],
  },
];

export const useNavigationStore = create<NavigationState>((set, get) => ({
  navGroups: allNavGroups,
  filteredNavGroups: allNavGroups,
  recentChats: [],

  filterByPermissions: (checkPermission) => {
    const { navGroups } = get();

    // First pass: filter items by permissions
    const withFilteredItems = navGroups.map(group => ({
      ...group,
      items: group.items.filter(item => checkPermission(item.module, item.requiredLevel))
    }));

    // Second pass: keep groups with items, and section labels only if at least one following group (before the next section label) has items
    const filteredGroups = withFilteredItems.filter((group, index) => {
      if (!group.sectionLabel) return group.items.length > 0;
      // Check if any group after this section label (up to the next section label) has items
      for (let i = index + 1; i < withFilteredItems.length; i++) {
        if (withFilteredItems[i].sectionLabel) break;
        if (withFilteredItems[i].items.length > 0) return true;
      }
      return false;
    });

    set({ filteredNavGroups: filteredGroups });
  },

  getFilteredNavGroups: () => {
    return get().filteredNavGroups;
  },

  updateRecentChats: (chats) => {
    set({ recentChats: chats });
  },
}));
