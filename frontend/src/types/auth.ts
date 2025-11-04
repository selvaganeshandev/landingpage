// Authentication types for Django backend integration

export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: 'super_admin' | 'admin' | 'user';
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
  SENTIMENT_ANALYSIS: 'sentiment_analysis',
  TOPICS: 'topics',
  SHARE_OF_VOICE: 'share_of_voice',
  HISTORICAL_TRENDS: 'historical_trends',
  CONTENT_GAPS: 'content_gaps',
  COMPETITORS: 'competitors',
  MULTILINGUAL: 'multilingual',
  AI_COPILOT: 'ai_copilot',
  PROMPT_INSIGHTS: 'prompt_insights',
  AGENT_ANALYTICS: 'agent_analytics',
  AI_CRAWLER: 'ai_crawler',
  TRAFFIC_ATTRIBUTION: 'traffic_attribution',
  MISINFORMATION_ALERTS: 'misinformation_alerts',
  REPORTS: 'reports',
  ORGANIZATION_SETTINGS: 'organization_settings',
  TEAM_MANAGEMENT: 'team_management',
} as const;

export type ModuleKey = typeof MODULES[keyof typeof MODULES];

export const PERMISSION_LEVELS = {
  READ: 'read',
  WRITE: 'write',
  ADMIN: 'admin',
} as const;

export type PermissionLevel = typeof PERMISSION_LEVELS[keyof typeof PERMISSION_LEVELS];

