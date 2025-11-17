/**
 * API Client - Complete implementation
 * Centralized API client with all backend endpoints
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface RequestOptions extends RequestInit {
  skipAuth?: boolean;
}

/**
 * Get auth token from localStorage
 */
function getAuthToken(): string | null {
  return localStorage.getItem('access_token');
}

/**
 * Generic API request handler with auth and error handling
 */
async function apiRequest<T>(
  endpoint: string, 
  options: RequestOptions = {}
): Promise<T> {
  const { skipAuth, ...fetchOptions } = options;
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...fetchOptions.headers,
  };

  // Add auth token if not skipped
  if (!skipAuth) {
    const token = getAuthToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...fetchOptions,
    headers,
  });

  // Handle unauthorized (token expired) - but don't redirect for login endpoint
  if (response.status === 401) {
    // Only redirect if not on login endpoint (to avoid redirecting during login attempts)
    if (!endpoint.includes('/auth/login/')) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.location.href = '/signin';
      throw new Error('Unauthorized');
    }
    // For login endpoint, let it fall through to error handling below
  }

  // Handle other errors
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'An error occurred' }));
    const errorMessage = error.detail || error.error || error.message || `HTTP ${response.status}: ${response.statusText}`;
    throw new Error(errorMessage);
  }

  // Handle empty responses
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

/**
 * Download file handler (for binary responses like PDFs)
 */
async function downloadFile(endpoint: string, filename: string): Promise<void> {
  const token = getAuthToken();
  const headers: HeadersInit = {};

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers,
  });

  if (!response.ok) {
    throw new Error(`Download failed: ${response.statusText}`);
  }

  // Get the blob from response
  const blob = await response.blob();

  // Create download link
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();

  // Cleanup
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

// ==================== API Client with All Methods ====================

export const apiClient = {
  // ===== Low-level HTTP methods =====
  get: <T>(endpoint: string, options?: RequestOptions) => 
    apiRequest<T>(endpoint, { ...options, method: 'GET' }),

  post: <T>(endpoint: string, data?: any, options?: RequestOptions) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    }),

  put: <T>(endpoint: string, data?: any, options?: RequestOptions) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    }),

  patch: <T>(endpoint: string, data?: any, options?: RequestOptions) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    }),

  delete: <T>(endpoint: string, options?: RequestOptions) =>
    apiRequest<T>(endpoint, { ...options, method: 'DELETE' }),

  // ===== Authentication =====
  login: async (credentials: { email: string; password: string }) => {
    const response: any = await apiRequest('/auth/login/', {
      method: 'POST',
      body: JSON.stringify(credentials),
      skipAuth: true,
    });
    
    // Store tokens in localStorage
    if (response.access) {
      localStorage.setItem('access_token', response.access);
    }
    if (response.refresh) {
      localStorage.setItem('refresh_token', response.refresh);
    }
    
    return response;
  },

  logout: async () => {
    const refreshToken = localStorage.getItem('refresh_token');
    await apiRequest('/auth/logout/', { 
      method: 'POST',
      body: JSON.stringify({ refresh: refreshToken }),
    });
    // Clear tokens from localStorage
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
  },

  getProfile: () => apiRequest('/auth/profile/'),

  updateProfile: (data: any) => apiRequest('/auth/profile/update/', {
    method: 'PUT',
    body: JSON.stringify(data),
  }),

  updateActiveDomain: (domainId: number | null) => apiRequest('/auth/active-domain/', {
    method: 'PUT',
    body: JSON.stringify({ domain_id: domainId }),
  }),

  // ===== Organization =====
  getOrganization: () => apiRequest('/auth/organization/'),

  updateOrganization: (data: any) => apiRequest('/auth/organization/', {
    method: 'PUT',
    body: JSON.stringify(data),
  }),

  // ===== Team Management =====
  getTeamMembers: () => apiRequest('/auth/team-members/'),

  removeTeamMember: (id: number) => apiRequest(`/auth/team-members/${id}/`, {
    method: 'DELETE',
  }),

  updateTeamMemberRole: (id: number, role: string) => apiRequest(`/auth/team-members/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify({ role }),
  }),

  sendInvitation: (data: any) => apiRequest('/auth/invite/', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  getInvitationDetails: (invitationId: string) => 
    apiRequest(`/auth/invitation/${invitationId}/`, { skipAuth: true }),

  acceptInvitation: (invitationId: string, data: any) => 
    apiRequest(`/auth/accept-invitation/${invitationId}/`, {
      method: 'POST',
      body: JSON.stringify(data),
      skipAuth: true,
    }),

  // ===== Permissions =====
  listUserPermissions: (userId: number) => 
    apiRequest(`/auth/permissions/user/${userId}/`),

  assignPermission: (data: any) => apiRequest('/auth/permissions/assign/', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  bulkAssignPermissions: (permissions: any[]) => 
    apiRequest('/auth/permissions/bulk-assign/', {
      method: 'POST',
      body: JSON.stringify({ permissions }),
    }),

  deletePermission: (id: number) => 
    apiRequest(`/auth/permissions/${id}/delete/`, { method: 'DELETE' }),

  grantAllPermissions: (userId: number) => 
    apiRequest(`/auth/permissions/user/${userId}/grant-all/`, { method: 'POST' }),

  revokeAllPermissions: (userId: number) => 
    apiRequest(`/auth/permissions/user/${userId}/revoke-all/`, { method: 'POST' }),

  // ===== Password Reset =====
  forgotPassword: (email: string) => apiRequest('/auth/forgot-password/', {
    method: 'POST',
    body: JSON.stringify({ email }),
    skipAuth: true,
  }),

  verifyResetToken: (tokenId: string) => 
    apiRequest(`/auth/verify-reset-token/${tokenId}/`, { skipAuth: true }),

  resetPassword: (token: string, newPassword: string, confirmPassword: string) => 
    apiRequest('/auth/reset-password/', {
      method: 'POST',
      body: JSON.stringify({ token, new_password: newPassword, confirm_password: confirmPassword }),
      skipAuth: true,
    }),

  // ===== Domains =====
  getDomains: (params?: any) => {
    const queryParams = params ? `?${new URLSearchParams(params).toString()}` : '';
    return apiRequest(`/domains/${queryParams}`);
  },

  createDomain: (data: any) => apiRequest('/domains/', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  updateDomain: (id: number, data: any) => apiRequest(`/domains/${id}/`, {
    method: 'PUT',
    body: JSON.stringify(data),
  }),

  deleteDomain: (id: number) => apiRequest(`/domains/${id}/`, {
    method: 'DELETE',
  }),

  // ===== Domain Access =====
  getDomainAccess: (domainId: number) => 
    apiRequest(`/domains/${domainId}/access/`),

  grantDomainAccess: (domainId: number, data: any) => 
    apiRequest(`/domains/${domainId}/access/`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  revokeDomainAccess: (domainId: number, userId: number) => 
    apiRequest(`/domains/${domainId}/access/${userId}/`, {
      method: 'DELETE',
    }),

  getAvailableUsersForDomain: (domainId: number) => 
    apiRequest(`/domains/${domainId}/access/available-users/`),

  // ===== Mentions =====
  getMentions: (params?: any) => {
    const cleaned: Record<string, string> = {};
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') cleaned[k] = String(v);
      });
    }
    const queryParams = Object.keys(cleaned).length ? `?${new URLSearchParams(cleaned).toString()}` : '';
    return apiRequest(`/prompts/mentions/${queryParams}`);
  },

  getMentionFilters: () => apiRequest('/prompts/mentions/filters/'),

  getMentionDetail: (id: number) => apiRequest(`/prompts/mentions/${id}/`),

  getRelatedMentions: (id: number) => apiRequest(`/prompts/mentions/${id}/related/`),

  getMentionTrends: () => apiRequest('/prompts/mentions/trends/'),

  getHistoricalTrends: (params: { domain_id: string; months?: number }) => {
    const queryParams = `?${new URLSearchParams({
      domain_id: params.domain_id,
      ...(params.months ? { months: String(params.months) } : {}),
    }).toString()}`;
    return apiRequest(`/prompts/historical-trends${queryParams}`);
  },

  exportMentions: (data: any) => apiRequest('/prompts/mentions/export/', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  // ===== Prompt Groups =====
  getPromptGroups: (params?: any) => {
    const cleaned: Record<string, string> = {};
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') cleaned[k] = String(v);
      });
    }
    const queryParams = Object.keys(cleaned).length ? `?${new URLSearchParams(cleaned).toString()}` : '';
    return apiRequest(`/prompts/groups/${queryParams}`);
  },

  createPromptGroup: (data: any) => apiRequest('/prompts/groups/', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  getPromptGroupDetail: (id: number) => apiRequest(`/prompts/groups/${id}/`),

  updatePromptGroup: (id: number, data: any) => apiRequest(`/prompts/groups/${id}/`, {
    method: 'PUT',
    body: JSON.stringify(data),
  }),

  deletePromptGroup: (id: number) => apiRequest(`/prompts/groups/${id}/`, {
    method: 'DELETE',
  }),

  generatePromptVariants: (data: { main_prompt?: string; prompt?: string; group_id?: number }) => 
    apiRequest('/prompts/groups/generate-variants/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // ===== Prompts =====
  getPrompts: (params?: any) => {
    const queryParams = params ? `?${new URLSearchParams(params).toString()}` : '';
    return apiRequest(`/prompts/prompts/${queryParams}`);
  },

  createPrompt: (data: any) => apiRequest('/prompts/prompts/', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  getPromptDetail: (id: number) => apiRequest(`/prompts/prompts/${id}/`),

  updatePrompt: (id: number, data: any) => apiRequest(`/prompts/prompts/${id}/`, {
    method: 'PUT',
    body: JSON.stringify(data),
  }),

  deletePrompt: (id: number) => apiRequest(`/prompts/prompts/${id}/`, {
    method: 'DELETE',
  }),

  bulkUpdatePrompts: (data: any) => apiRequest('/prompts/prompts/bulk-update/', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  getPromptAnalytics: (id: number) => apiRequest(`/prompts/prompts/${id}/analytics/`),

  // ===== Alerts =====
  getAlerts: (params?: any) => {
    const queryParams = params ? `?${new URLSearchParams(params).toString()}` : '';
    return apiRequest(`/alerts/alerts/${queryParams}`);
  },

  getActiveAlerts: (params?: any) => {
    const queryParams = params ? `?${new URLSearchParams(params).toString()}` : '';
    return apiRequest(`/alerts/alerts/active/${queryParams}`);
  },

  getAlertSummary: (params?: any) => {
    const queryParams = params ? `?${new URLSearchParams(params).toString()}` : '';
    return apiRequest(`/alerts/alerts/summary/${queryParams}`);
  },

  createAlert: (data: any) => apiRequest('/alerts/alerts/', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  updateAlert: (id: number, data: any) => apiRequest(`/alerts/alerts/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),

  deleteAlert: (id: number) => apiRequest(`/alerts/alerts/${id}/`, {
    method: 'DELETE',
  }),

  resolveAlert: (id: number) => apiRequest(`/alerts/alerts/${id}/resolve/`, {
    method: 'POST',
  }),

  investigateAlert: (id: number) => apiRequest(`/alerts/alerts/${id}/investigate/`, {
    method: 'POST',
  }),

  // ===== Alert Rules =====
  getAlertRules: (params?: any) => {
    const queryParams = params ? `?${new URLSearchParams(params).toString()}` : '';
    return apiRequest(`/alerts/alert-rules/${queryParams}`);
  },

  createAlertRule: (data: any) => apiRequest('/alerts/alert-rules/', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  updateAlertRule: (id: number, data: any) => apiRequest(`/alerts/alert-rules/${id}/`, {
    method: 'PUT',
    body: JSON.stringify(data),
  }),

  toggleAlertRule: (id: number) => apiRequest(`/alerts/alert-rules/${id}/toggle/`, { method: 'POST' }),

  deleteAlertRule: (id: number) => apiRequest(`/alerts/alert-rules/${id}/`, {
    method: 'DELETE',
  }),

  // ===== Alert Configuration =====
  getAlertConfiguration: (domainId?: number) => {
    const queryParams = domainId ? `?domain_id=${domainId}` : '';
    return apiRequest(`/alerts/alert-configuration${queryParams}`);
  },

  updateAlertConfiguration: (data: any) => {
    return apiRequest('/alerts/alert-configuration/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  updateEmailConfig: (data: { domain_id: number; email_address: string }) => {
    return apiRequest('/alerts/alert-configuration/email/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // ===== Competitors =====
  getCompetitors: (params?: any) => {
    const queryParams = params ? `?${new URLSearchParams(params).toString()}` : '';
    return apiRequest(`/competitors/competitors/${queryParams}`);
  },

  createCompetitor: (data: any) => apiRequest('/competitors/competitors/', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  getCompetitorDetail: (id: number) => apiRequest(`/competitors/competitors/${id}/`),

  updateCompetitor: (id: number, data: any) => apiRequest(`/competitors/competitors/${id}/`, {
    method: 'PUT',
    body: JSON.stringify(data),
  }),

  deleteCompetitor: (id: number) => apiRequest(`/competitors/competitors/${id}/`, {
    method: 'DELETE',
  }),

  getCompetitorAnalytics: (params?: any) => {
    const queryParams = params ? `?${new URLSearchParams(params).toString()}` : '';
    return apiRequest(`/competitors/competitor-analytics/${queryParams}`);
  },

  getCompetitorPrompts: (params?: any) => {
    const queryParams = params ? `?${new URLSearchParams(params).toString()}` : '';
    return apiRequest(`/competitors/competitor-prompts/${queryParams}`);
  },

  // ===== Topics =====
  getTopics: (params?: any) => {
    const queryParams = params ? `?${new URLSearchParams(params).toString()}` : '';
    return apiRequest(`/topics/topics/${queryParams}`);
  },

  createTopic: (data: any) => apiRequest('/topics/topics/', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  updateTopic: (id: number, data: any) => apiRequest(`/topics/topics/${id}/`, {
    method: 'PUT',
    body: JSON.stringify(data),
  }),

  deleteTopic: (id: number) => apiRequest(`/topics/topics/${id}/`, {
    method: 'DELETE',
  }),

  getTopicAnalytics: (params?: any) => {
    const queryParams = params ? `?${new URLSearchParams(params).toString()}` : '';
    return apiRequest(`/topics/topic-analytics/${queryParams}`);
  },

  getTopicPrompts: (params?: any) => {
    const queryParams = params ? `?${new URLSearchParams(params).toString()}` : '';
    return apiRequest(`/topics/topic-prompts/${queryParams}`);
  },

  // ===== Analytics =====
  getSentimentAnalytics: (params?: any) => {
    const queryParams = params ? `?${new URLSearchParams(params).toString()}` : '';
    return apiRequest(`/analytics/sentiment-analytics/${queryParams}`);
  },

  getSentimentSummary: (params: { domain_id: string; days?: number }) => {
    const queryParams = `?${new URLSearchParams({
      domain_id: params.domain_id,
      ...(params.days ? { days: String(params.days) } : {}),
    }).toString()}`;
    return apiRequest(`/analytics/sentiment-analytics/summary/${queryParams}`);
  },

  getSentimentByDomain: (params: { domain_id: string; days?: number }) => {
    const queryParams = `?${new URLSearchParams({
      domain_id: params.domain_id,
      ...(params.days ? { days: String(params.days) } : {}),
    }).toString()}`;
    return apiRequest(`/analytics/sentiment-analytics/by_domain/${queryParams}`);
  },

  getShareOfVoice: (params?: any) => {
    const queryParams = params ? `?${new URLSearchParams(params).toString()}` : '';
    return apiRequest(`/analytics/share-of-voice/${queryParams}`);
  },

  // Share of Voice helpers for ShareOfVoice page
  

  getShareOfVoiceByDomain: (params: { domain_id: string; days?: number; platform?: string }) => {
    const queryParams = `?${new URLSearchParams({
      domain_id: params.domain_id,
      ...(params.days ? { days: String(params.days) } : {}),
      ...(params.platform ? { platform: params.platform } : {}),
    }).toString()}`;
    return apiRequest(`/analytics/share-of-voice/by_domain/${queryParams}`);
  },

  getShareOfVoiceComparison: (params: { domain_id: string; date?: string; platform?: string }) => {
    const queryParams = `?${new URLSearchParams({
      domain_id: params.domain_id,
      ...(params.date ? { date: params.date } : {}),
      ...(params.platform ? { platform: params.platform } : {}),
    }).toString()}`;
    return apiRequest(`/analytics/share-of-voice/comparison/${queryParams}`);
  },

  getShareOfVoiceLatestEngine: (params: { domain_id: string }) => {
    const queryParams = `?${new URLSearchParams({ domain_id: params.domain_id }).toString()}`;
    return apiRequest(`/analytics/share-of-voice/${queryParams}`);
  },

  // ===== Engine (port 8001) helpers for competitor sentiment (optional for Sentiment page)
  getEngine: <T>(endpoint: string) => {
    const engineBaseUrl = import.meta.env.VITE_ENGINE_API_URL || 'http://localhost:8001';
    const apiUrl = `${engineBaseUrl}${endpoint}`;
    return fetch(apiUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...(localStorage.getItem('access_token') ? {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        } : {}),
      },
    }).then(async (response) => {
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'An error occurred' }));
        throw new Error(error.detail || error.error || `HTTP ${response.status}`);
      }
      return response.json();
    });
  },

  getCompetitorPromptAnalyticsEngine: (params: { domain_id: string }) => {
    const queryParams = `?${new URLSearchParams({ domain_id: params.domain_id }).toString()}`;
    return apiRequest(`/competitors/competitor-prompt-analytics/${queryParams}`);
  },

  getCompetitorGapsEngine: (params: { domain_id: string; competitor_id?: string }) => {
    const queryParams = `?${new URLSearchParams({
      domain_id: params.domain_id,
      ...(params.competitor_id ? { competitor_id: params.competitor_id } : {}),
    }).toString()}`;
    return apiClient.getEngine(`/api/competitor-prompt-analytics/gaps/${queryParams}`);
  },

  getCompetitorHeatmap: (params: { domain_id: string; days?: number }) => {
    const queryParams = `?${new URLSearchParams({
      domain_id: params.domain_id,
      ...(params.days ? { days: String(params.days) } : {}),
    }).toString()}`;
    return apiRequest(`/competitors/heatmap/${queryParams}`);
  },

  getCompetitorMetricSnapshots: (params: { domain_id: string; days?: number; competitor_id?: string }) => {
    const queryParams = `?${new URLSearchParams({
      domain_id: params.domain_id,
      ...(params.days ? { days: String(params.days) } : {}),
      ...(params.competitor_id ? { competitor_id: params.competitor_id } : {}),
    }).toString()}`;
    return apiRequest(`/competitors/competitor-metric-snapshots/${queryParams}`);
  },

  getEngineCompetitors: (params: { domain_id: string }) => {
    const queryParams = `?${new URLSearchParams({ domain_id: params.domain_id }).toString()}`;
    return apiRequest(`/competitors/competitors/${queryParams}`);
  },

  getEngineCompetitorDetail: (id: number) => apiRequest(`/competitors/competitors/${id}/`),
  getEngineCompetitorAnalytics: (id: number) => apiRequest(`/competitors/competitor-analytics/?competitor_id=${id}`),

  // Competitor Analysis APIs
  getCompetitiveStrengthAnalysis: (params: { domain_id: string }) => {
    const queryParams = `?${new URLSearchParams({ domain_id: params.domain_id }).toString()}`;
    return apiRequest(`/competitors/competitive-strength-analysis${queryParams}`);
  },

  getCompetitiveInsights: (params: { domain_id: string }) => {
    const queryParams = `?${new URLSearchParams({ domain_id: params.domain_id }).toString()}`;
    return apiRequest(`/competitors/competitive-insights${queryParams}`);
  },

  getAnswerGapAnalysis: (params: { domain_id: string; competitor_id?: string }) => {
    const queryParams = `?${new URLSearchParams({
      domain_id: params.domain_id,
      ...(params.competitor_id ? { competitor_id: params.competitor_id } : {}),
    }).toString()}`;
    return apiRequest(`/competitors/answer-gap-analysis${queryParams}`);
  },

  // ===== Dashboard =====
  getDashboardSummary: (params: { domain_id: string; days?: number }) => {
    const queryParams = `?${new URLSearchParams({
      domain_id: params.domain_id,
      ...(params.days ? { days: String(params.days) } : {}),
    }).toString()}`;
    // Use backend API endpoint
    return apiClient.get(`/analytics/dashboard/summary/${queryParams}`);
  },

  // ===== Integrations =====
  getIntegrations: () => apiRequest('/integrations/integrations/'),

  createIntegration: (data: any) => apiRequest('/integrations/integrations/', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  updateIntegration: (id: number, data: any) => apiRequest(`/integrations/integrations/${id}/`, {
    method: 'PUT',
    body: JSON.stringify(data),
  }),

  deleteIntegration: (id: number) => apiRequest(`/integrations/integrations/${id}/`, {
    method: 'DELETE',
  }),

  // ===== Reports =====
  // Report Templates
  getReportTemplates: () => apiRequest('/reports/templates/'),

  getReportTemplate: (id: number) => apiRequest(`/reports/templates/${id}/`),

  // Scheduled Reports
  getScheduledReports: (params?: any) => {
    const queryParams = params ? `?${new URLSearchParams(params).toString()}` : '';
    return apiRequest(`/reports/scheduled/${queryParams}`);
  },

  createScheduledReport: (data: any) => apiRequest('/reports/scheduled/', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  getScheduledReport: (id: number) => apiRequest(`/reports/scheduled/${id}/`),

  updateScheduledReport: (id: number, data: any) => apiRequest(`/reports/scheduled/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),

  deleteScheduledReport: (id: number) => apiRequest(`/reports/scheduled/${id}/`, {
    method: 'DELETE',
  }),

  pauseScheduledReport: (id: number) => apiRequest(`/reports/scheduled/${id}/pause/`, {
    method: 'POST',
  }),

  resumeScheduledReport: (id: number) => apiRequest(`/reports/scheduled/${id}/resume/`, {
    method: 'POST',
  }),

  // Generated Reports
  getGeneratedReports: (params?: any) => {
    const queryParams = params ? `?${new URLSearchParams(params).toString()}` : '';
    return apiRequest(`/reports/generated/${queryParams}`);
  },

  getGeneratedReport: (id: number) => apiRequest(`/reports/generated/${id}/`),

  downloadReport: async (id: number, filename?: string) => {
    // Get report details first to get the correct filename
    const report: any = await apiRequest(`/reports/generated/${id}/`);
    const downloadFilename = filename || `${report.name}.${report.format.toLowerCase()}`;
    return downloadFile(`/reports/generated/${id}/download/`, downloadFilename);
  },

  // Report Generation
  generateReport: (data: any) => apiRequest('/reports/generation/generate_now/', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  checkGenerationTask: (taskId: string) => {
    const queryParams = `?task_id=${taskId}`;
    return apiRequest(`/reports/generation/task_status/${queryParams}`);
  },
};

// Also export as 'api' for flexibility
export const api = apiClient;

export default apiClient;
