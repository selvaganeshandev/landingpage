// Authentication types for Django backend integration

export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: 'super_admin' | 'admin' | 'user' | 'client';
  organisation: number;
  organisation_name: string;
  is_active: boolean;
  created_at: string;
  modified_at: string;
}

export interface Permission {
  id: number;
  user: number;
  user_email: string;
  module: string;
  module_display: string;
  permission_level: 'read' | 'write' | 'admin';
  permission_display: string;
  granted_by: number;
  granted_by_email: string;
  created_at: string;
  modified_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user: User;
  permissions: Permission[];
  message: string;
}

export interface AuthState {
  user: User | null;
  permissions: Permission[];
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  /** This browser held a session that has since gone away — an expiry.
   *
   *  Distinguishes the two reasons `isAuthenticated` can be false. Without it
   *  a first-time visitor opening the app was told "Session Expired — your
   *  session has timed out", about a session they never had. Set when stored
   *  tokens are found at startup, and on a successful login; stays false for
   *  someone who has never signed in on this browser. */
  sessionEnded: boolean;
}

export interface ApiError {
  error: string;
  detail?: string;
}

// Available modules for permissions
export const MODULES = {
  DASHBOARD: 'dashboard',
  MENTIONS: 'mentions',
  PROMPTS: 'prompts',
  ALERTS: 'alerts',
  CITATIONS: 'citations',
  SENTIMENT_ANALYSIS: 'sentiment_analysis',
  TOPICS: 'topics',
  SHARE_OF_VOICE: 'share_of_voice',
  HISTORICAL_TRENDS: 'historical_trends',
  CONTENT_GAPS: 'content_gaps',
  COMPETITORS: 'competitors',
  CONTENT_PLANNER: 'content_planner',
  MULTILINGUAL: 'multilingual',
  AI_COPILOT: 'ai_copilot',
  TRAFFIC_ATTRIBUTION: 'traffic_attribution',
  MISINFORMATION_ALERTS: 'misinformation_alerts',
  REPORTS: 'reports',
  ORGANIZATION_SETTINGS: 'organization_settings',
  TEAM_MANAGEMENT: 'team_management',
  AUDIT_ENGINE: 'audit_engine',
  // SEO Monitoring modules
  KEYWORD_RANKINGS: 'keyword_rankings',
  SEO_COMPETITORS: 'seo_competitors',
  ORGANIC_REPORTS: 'organic_reports',
  BACKLINKS: 'backlinks',
} as const;

export type ModuleKey = typeof MODULES[keyof typeof MODULES];

export const PERMISSION_LEVELS = {
  READ: 'read',
  WRITE: 'write',
  ADMIN: 'admin',
} as const;

export type PermissionLevel = typeof PERMISSION_LEVELS[keyof typeof PERMISSION_LEVELS];

