/**
 * API Client - Complete implementation
 * Centralized API client with all backend endpoints
 */

export const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const ENGINE_URL = import.meta.env.VITE_ENGINE_URL || 'http://localhost:8001';

interface RequestOptions extends RequestInit {
  skipAuth?: boolean;
  useEngine?: boolean;
  timeout?: number;
}

/**
 * Get auth token from localStorage
 */
function getAuthToken(): string | null {
  return localStorage.getItem('access_token');
}

// Flag to prevent multiple simultaneous refresh attempts
let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

/**
 * Subscribe to token refresh completion
 */
function subscribeTokenRefresh(callback: (token: string) => void) {
  refreshSubscribers.push(callback);
}

/**
 * Notify all subscribers when token is refreshed
 */
function onTokenRefreshed(token: string) {
  refreshSubscribers.forEach(callback => callback(token));
  refreshSubscribers = [];
}

/**
 * Refresh the access token using the refresh token
 */
async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = localStorage.getItem('refresh_token');

  if (!refreshToken) {
    return null;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/auth/token/refresh/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh: refreshToken }),
    });

    if (!response.ok) {
      throw new Error('Token refresh failed');
    }

    const data = await response.json();
    const newAccessToken = data.access;
    const newRefreshToken = data.refresh;  // Backend rotates refresh tokens

    // Store new tokens
    localStorage.setItem('access_token', newAccessToken);
    if (newRefreshToken) {
      localStorage.setItem('refresh_token', newRefreshToken);
    }

    return newAccessToken;
  } catch (error) {
    // Refresh failed, clear tokens and redirect to login
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    return null;
  }
}

/**
 * Generic API request handler with auth and error handling
 */
async function apiRequest<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { skipAuth, useEngine, timeout, ...fetchOptions } = options;

  const headers: HeadersInit = {
    // Don't set Content-Type for FormData - let browser set it with boundary
    ...(fetchOptions.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
    ...fetchOptions.headers,
  };

  // Add auth token if not skipped
  if (!skipAuth) {
    const token = getAuthToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }

  // Use engine URL if specified, otherwise use backend URL
  const baseURL = useEngine ? ENGINE_URL : API_BASE_URL;

  // Set up abort controller for timeout
  const controller = new AbortController();
  const timeoutMs = timeout || 120000; // Default 2 minutes
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  let response: Response;
  try {
    response = await fetch(`${baseURL}${endpoint}`, {
      ...fetchOptions,
      headers,
      signal: controller.signal,
    });
  } catch (err: any) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') {
      throw new Error('Request timed out. Please try again.');
    }
    throw err;
  }
  clearTimeout(timeoutId);

  // Handle unauthorized (token expired) - try to refresh token first
  if (response.status === 401 && !skipAuth) {
    // Don't try to refresh for login, logout, or refresh endpoints
    const skipRefreshEndpoints = ['/auth/login/', '/auth/logout/', '/auth/token/refresh/'];
    const shouldSkipRefresh = skipRefreshEndpoints.some(ep => endpoint.includes(ep));

    if (!shouldSkipRefresh) {
      // If already refreshing, wait for it to complete
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          subscribeTokenRefresh(async (newToken: string) => {
            // Retry the original request with new token
            const newHeaders = {
              ...headers,
              'Authorization': `Bearer ${newToken}`,
            };

            try {
              const retryResponse = await fetch(`${baseURL}${endpoint}`, {
                ...fetchOptions,
                headers: newHeaders,
              });

              if (!retryResponse.ok) {
                const error = await retryResponse.json().catch(() => ({ detail: 'An error occurred' }));
                const errorMessage = error.detail || error.error || error.message || `HTTP ${retryResponse.status}: ${retryResponse.statusText}`;
                reject(new Error(errorMessage));
                return;
              }

              if (retryResponse.status === 204) {
                resolve({} as T);
                return;
              }

              const data = await retryResponse.json();
              resolve(data);
            } catch (error) {
              reject(error);
            }
          });
        });
      }

      // Try to refresh the token
      isRefreshing = true;
      const newToken = await refreshAccessToken();
      isRefreshing = false;

      if (newToken) {
        // Notify all waiting requests
        onTokenRefreshed(newToken);

        // Retry the original request with new token
        const newHeaders = {
          ...headers,
          'Authorization': `Bearer ${newToken}`,
        };

        response = await fetch(`${baseURL}${endpoint}`, {
          ...fetchOptions,
          headers: newHeaders,
        });
      } else {
        // Refresh failed, redirect to session expired page
        window.location.href = '/session-expired';
        throw new Error('Session expired. Please login again.');
      }
    } else {
      // For login/logout endpoints, don't try to refresh
      if (!endpoint.includes('/auth/login/')) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/session-expired';
      }
      throw new Error('Unauthorized');
    }
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

  deleteInvitation: (invitationId: string) => apiRequest(`/auth/invitation/${invitationId}/delete/`, {
    method: 'DELETE',
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

  getDomain: (id: number) => apiRequest(`/domains/${id}/`),

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

  fetchBrandInfo: (domainName: string, domainUrl?: string) => apiRequest('/domains/fetch-brand-info/', {
    method: 'POST',
    body: JSON.stringify({ domain_name: domainName, domain_url: domainUrl }),
  }),

  fetchBrandNiches: (domainName: string, brandName?: string) => apiRequest('/domains/fetch-brand-niches/', {
    method: 'POST',
    body: JSON.stringify({ domain_name: domainName, brand_name: brandName }),
  }),

  generateSemanticKeywords: (data: { domain_name: string; brand_name: string; country: string; niches: string[]; approx_keywords?: number }) =>
    apiRequest('/domains/generate-semantic-keywords/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  automatedDomainOnboard: (data: { domain_name: string; brand_name: string; country: string; niches?: string[] }) =>
    apiRequest('/domains/automated-onboard/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getDomainHealthCheck: (domainId: number) =>
    apiRequest(`/domains/${domainId}/health-check/`, { timeout: 300000 }),  // 5 minutes - health check calls multiple external APIs

  getDomainHealthCheckHistory: (domainId: number, limit?: number) => {
    const queryParams = limit ? `?limit=${limit}` : '';
    return apiRequest(`/domains/${domainId}/health-check/history/${queryParams}`);
  },

  bulkCreateKeywords: (domainId: number, keywords: any[]) =>
    apiRequest('/keywords/bulk-create/', {
      method: 'POST',
      body: JSON.stringify({ domain_id: domainId, keywords }),
    }),

  bulkCreateSecondaryKeywords: (domainId: number, keywords: any[]) =>
    apiRequest('/keywords/secondary/bulk-create/', {
      method: 'POST',
      body: JSON.stringify({ domain_id: domainId, keywords }),
    }),

  // ===== Domain Access =====
  getUserDomainAccess: (userId: number) =>
    apiRequest(`/domains/user-access/${userId}/`),

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

  // ===== Internal Link Map =====
  getInternalLinkMaps: (domainId: number) =>
    apiRequest(`/domains/${domainId}/internal-links/`),

  createInternalLinkMap: (domainId: number, data: { topic: string; keywords: string; url: string }) =>
    apiRequest(`/domains/${domainId}/internal-links/`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateInternalLinkMap: (domainId: number, linkId: number, data: Partial<{ topic: string; keywords: string; url: string }>) =>
    apiRequest(`/domains/${domainId}/internal-links/${linkId}/`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  deleteInternalLinkMap: (domainId: number, linkId: number) =>
    apiRequest(`/domains/${domainId}/internal-links/${linkId}/`, {
      method: 'DELETE',
    }),

  importInternalLinkMaps: (domainId: number, csvData: Array<{ topic: string; keywords: string; url: string }>) =>
    apiRequest(`/domains/${domainId}/internal-links/import/`, {
      method: 'POST',
      body: JSON.stringify({ csv_data: csvData }),
    }),

  // ===== Reference Repository =====
  getReferenceDocuments: (domainId: number) =>
    apiRequest(`/domains/${domainId}/reference-repository/`),

  uploadReferenceDocument: (domainId: number, formData: FormData) =>
    apiRequest(`/domains/${domainId}/reference-repository/`, {
      method: 'POST',
      body: formData,
    }),

  addReferenceTextNote: (domainId: number, data: { title: string; text_content: string; description?: string; file_type: string }) =>
    apiRequest(`/domains/${domainId}/reference-repository/`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  deleteReferenceDocument: (domainId: number, docId: number) =>
    apiRequest(`/domains/${domainId}/reference-repository/${docId}/`, {
      method: 'DELETE',
    }),

  updateReferenceDocument: (domainId: number, docId: number, data: any) =>
    apiRequest(`/domains/${domainId}/reference-repository/${docId}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  getReferenceDocumentDetail: (domainId: number, docId: number) =>
    apiRequest(`/domains/${domainId}/reference-repository/${docId}/`),

  // ===== Brand Links =====
  getBrandLinks: (domainId: number) =>
    apiRequest(`/domains/${domainId}/brand-links/`),

  addBrandLink: (domainId: number, data: { platform: string; url: string; label?: string }) =>
    apiRequest(`/domains/${domainId}/brand-links/`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getBrandLinkDetail: (domainId: number, linkId: number) =>
    apiRequest(`/domains/${domainId}/brand-links/${linkId}/`),

  updateBrandLink: (domainId: number, linkId: number, data: any) =>
    apiRequest(`/domains/${domainId}/brand-links/${linkId}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  deleteBrandLink: (domainId: number, linkId: number) =>
    apiRequest(`/domains/${domainId}/brand-links/${linkId}/`, {
      method: 'DELETE',
    }),

  recrawlBrandLink: (domainId: number, linkId: number) =>
    apiRequest(`/domains/${domainId}/brand-links/${linkId}/recrawl/`, {
      method: 'POST',
    }),

  // ===== Keywords =====
  getKeywords: (params?: any) => {
    const queryParams = params ? `?${new URLSearchParams(params).toString()}` : '';
    return apiRequest(`/keywords/${queryParams}`);
  },

  getDomainKeywords: (domainId: number) => 
    apiRequest(`/domains/${domainId}/keywords/`),

  createKeyword: (data: any) => apiRequest('/keywords/', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  updateKeyword: (id: number, data: any) => apiRequest(`/keywords/${id}/`, {
    method: 'PUT',
    body: JSON.stringify(data),
  }),

  deleteKeyword: (id: number) => apiRequest(`/keywords/${id}/`, {
    method: 'DELETE',
  }),

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

  // Export mentions list to Excel
  exportMentionsListExcel: async (params: {
    domain_id?: number;
    search?: string;
    platform?: string;
    sentiment?: string;
    show_all?: boolean;
  }) => {
    const queryParams = new URLSearchParams();
    if (params.domain_id) queryParams.set('domain_id', String(params.domain_id));
    if (params.search) queryParams.set('search', params.search);
    if (params.platform && params.platform !== 'all') queryParams.set('platform', params.platform);
    if (params.sentiment && params.sentiment !== 'all') queryParams.set('sentiment', params.sentiment);
    if (params.show_all) queryParams.set('show_all', 'true');
    
    const queryString = queryParams.toString() ? `?${queryParams.toString()}` : '';
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    return downloadFile(`/prompts/mentions/export/${queryString}`, `mentions_export_${timestamp}.xlsx`);
  },

  // Export single mention to Excel
  exportMentionDetailExcel: async (mentionId: number) => {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    return downloadFile(`/prompts/mentions/${mentionId}/export/`, `mention_${mentionId}_export_${timestamp}.xlsx`);
  },

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

  getPromptGroupDetail: (id: number, params?: Record<string, string>) => {
    const queryString = params ? '?' + new URLSearchParams(params).toString() : '';
    return apiRequest(`/prompts/groups/${id}/${queryString}`);
  },

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

  getPromptAnalyticsByDomain: (domainId: number) => {
    return apiRequest(`/prompts/mentions/analytics/?domain_id=${domainId}`);
  },

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

  getCompetitorsByDomain: (domainId: number) => {
    return apiRequest(`/competitors/competitors/?domain_id=${domainId}`);
  },

  updateCompetitor: (id: number, data: any) => apiRequest(`/competitors/competitors/${id}/`, {
    method: 'PUT',
    body: JSON.stringify(data),
  }),

  deleteCompetitor: (id: number) => apiRequest(`/competitors/competitors/${id}/`, {
    method: 'DELETE',
  }),

  startCompetitorAnalysis: (domainId: number) => apiRequest('/competitors/start-analysis/', {
    method: 'POST',
    body: JSON.stringify({ domain_id: domainId }),
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

  getTopicsByDomain: (domainId: number) => {
    return apiRequest(`/topics/topics/by_domain/?domain_id=${domainId}`);
  },

  getTrendingTopics: (domainId?: number) => {
    const params = domainId ? `?domain_id=${domainId}` : '';
    return apiRequest(`/topics/topics/trending/${params}`);
  },

  getTopicKeywordAnalytics: (topicId: number) => {
    return apiRequest(`/topics/topics/${topicId}/keyword_analytics/`);
  },

  getTopicRelatedPrompts: (topicId: number) => {
    return apiRequest(`/topics/topics/${topicId}/related_prompts/`);
  },

  getTopicOptimization: (topicId: number) => {
    return apiRequest(`/topics/topics/${topicId}/optimize/`);
  },

  getTopicTrends: (params: { domainId?: number; topicId?: number; days?: number } = {}) => {
    const { domainId, topicId, days = 30 } = params;
    const urlParams = new URLSearchParams({ days: String(days) });
    if (domainId) urlParams.append('domain_id', String(domainId));
    if (topicId) urlParams.append('topic_id', String(topicId));
    return apiRequest(`/topics/topic-analytics/trends/?${urlParams.toString()}`);
  },

  // New dedicated analytics endpoints for Topics page
  getTopicDistribution: (domainId: number) => {
    return apiRequest(`/topics/topic-analytics/distribution/?domain_id=${domainId}`);
  },

  getTopicKeywordPerformance: (domainId: number, limit: number = 10) => {
    return apiRequest(`/topics/topic-analytics/keyword-performance/?domain_id=${domainId}&limit=${limit}`);
  },

  getTopicPromptSuggestions: (domainId: number, limit: number = 6, generateNew: boolean = false) => {
    const generateParam = generateNew ? '&generate_new=true' : '';
    return apiRequest(`/topics/topic-analytics/prompt-suggestions/?domain_id=${domainId}&limit=${limit}${generateParam}`);
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
  

  getShareOfVoiceByDomain: (params: { domain_id: string; days?: number; platform?: string }, options?: RequestOptions) => {
    const queryParams = `?${new URLSearchParams({
      domain_id: params.domain_id,
      ...(params.days ? { days: String(params.days) } : {}),
      ...(params.platform ? { platform: params.platform } : {}),
    }).toString()}`;
    return apiRequest(`/analytics/share-of-voice/by_domain/${queryParams}`, options);
  },

  getShareOfVoiceComparison: (params: { domain_id: string; date?: string; platform?: string }) => {
    const queryParams = `?${new URLSearchParams({
      domain_id: params.domain_id,
      ...(params.date ? { date: params.date } : {}),
      ...(params.platform ? { platform: params.platform } : {}),
    }).toString()}`;
    return apiRequest(`/analytics/share-of-voice/comparison/${queryParams}`);
  },

  getShareOfVoiceLatestEngine: (params: { domain_id: string }, options?: RequestOptions) => {
    const queryParams = `?${new URLSearchParams({ domain_id: params.domain_id }).toString()}`;
    return apiRequest(`/analytics/share-of-voice/by_domain/${queryParams}`, options);
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

  getCompetitorPromptAnalyticsEngine: (params: { domain_id: string; competitor_id?: string; page_size?: string; is_mentioned?: string; platform?: string; page?: number }, options?: RequestOptions) => {
    const queryParams = `?${new URLSearchParams({
      domain_id: params.domain_id,
      ...(params.competitor_id ? { competitor_id: params.competitor_id } : {}),
      ...(params.page_size ? { page_size: params.page_size } : {}),
      ...(params.is_mentioned ? { is_mentioned: params.is_mentioned } : {}),
      ...(params.platform ? { platform: params.platform } : {}),
      ...(params.page ? { page: params.page.toString() } : {}),
    }).toString()}`;
    return apiRequest(`/competitors/competitor-prompt-analytics/${queryParams}`, options);
  },

  getCompetitorGapsEngine: (params: { domain_id: string; competitor_id?: string }) => {
    const queryParams = `?${new URLSearchParams({
      domain_id: params.domain_id,
      ...(params.competitor_id ? { competitor_id: params.competitor_id } : {}),
    }).toString()}`;
    return apiClient.get(`/competitors/competitor-prompt-analytics/gaps/${queryParams}`);
  },

  getCompetitorHeatmap: (params: { domain_id: string; days?: number; platform?: string }, options?: RequestOptions) => {
    const queryParams = `?${new URLSearchParams({
      domain_id: params.domain_id,
      ...(params.days ? { days: String(params.days) } : {}),
      ...(params.platform ? { platform: params.platform } : {}),
    }).toString()}`;
    return apiRequest(`/competitors/heatmap/${queryParams}`, options);
  },

  getCompetitorMetricSnapshots: (params: { domain_id: string; days?: number; competitor_id?: string; platform?: string }, options?: RequestOptions) => {
    const queryParams = `?${new URLSearchParams({
      domain_id: params.domain_id,
      ...(params.days ? { days: String(params.days) } : {}),
      ...(params.competitor_id ? { competitor_id: params.competitor_id } : {}),
      ...(params.platform ? { platform: params.platform } : {}),
    }).toString()}`;
    return apiRequest(`/competitors/competitor-metric-snapshots/${queryParams}`, options);
  },

  getEngineCompetitors: (params: { domain_id: string; platform?: string }, options?: RequestOptions) => {
    const queryParams = `?${new URLSearchParams({
      domain_id: params.domain_id,
      ...(params.platform ? { platform: params.platform } : {}),
    }).toString()}`;
    return apiRequest(`/competitors/competitors/by_domain/${queryParams}`, options);
  },

  getEngineCompetitorDetail: (id: number) => apiRequest(`/competitors/competitors/${id}/`),
  getEngineCompetitorAnalytics: (id: number) => apiRequest(`/competitors/competitor-analytics/?competitor_id=${id}`),
  processCompetitor: async (id: number) => {
    const engineBaseUrl = import.meta.env.VITE_ENGINE_API_URL || 'http://localhost:8001';
    const token = getAuthToken();
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const response = await fetch(`${engineBaseUrl}/api/competitors/competitors/${id}/process/`, {
      method: 'POST',
      headers,
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'An error occurred' }));
      throw new Error(error.detail || error.error || `HTTP ${response.status}`);
    }
    return response.json();
  },

  // Competitor Analysis APIs
  getCompetitiveStrengthAnalysis: (params: { domain_id: string; platform?: string }, options?: RequestOptions) => {
    const queryParams = `?${new URLSearchParams({
      domain_id: params.domain_id,
      ...(params.platform ? { platform: params.platform } : {}),
    }).toString()}`;
    return apiRequest(`/competitors/competitive-strength-analysis${queryParams}`, options);
  },

  getCompetitiveInsights: (params: { domain_id: string; platform?: string }, options?: RequestOptions) => {
    const queryParams = `?${new URLSearchParams({
      domain_id: params.domain_id,
      ...(params.platform ? { platform: params.platform } : {}),
    }).toString()}`;
    return apiRequest(`/competitors/competitive-insights${queryParams}`, options);
  },

  getAnswerGapAnalysis: (params: { domain_id: string; competitor_id?: string; platform?: string }, options?: RequestOptions) => {
    const queryParams = `?${new URLSearchParams({
      domain_id: params.domain_id,
      ...(params.competitor_id ? { competitor_id: params.competitor_id } : {}),
      ...(params.platform ? { platform: params.platform } : {}),
    }).toString()}`;
    return apiRequest(`/competitors/answer-gap-analysis${queryParams}`, options);
  },

  // ===== Content Gaps =====
  getContentGaps: (params: { domain_id: string; platform?: string; priority?: string; page?: number; page_size?: string }, options?: RequestOptions) => {
    const queryParams = `?${new URLSearchParams({
      domain_id: params.domain_id,
      ...(params.platform ? { platform: params.platform } : {}),
      ...(params.priority ? { priority: params.priority } : {}),
      ...(params.page ? { page: String(params.page) } : {}),
      ...(params.page_size ? { page_size: params.page_size } : {}),
    }).toString()}`;
    return apiRequest(`/competitors/content-gaps/${queryParams}`, options);
  },

  getContentGapSummary: (params: { domain_id: string; platform?: string }, options?: RequestOptions) => {
    const queryParams = `?${new URLSearchParams({
      domain_id: params.domain_id,
      ...(params.platform ? { platform: params.platform } : {}),
    }).toString()}`;
    return apiRequest(`/competitors/content-gaps/summary/${queryParams}`, options);
  },

  getContentGapDetail: (gapId: number, params: { domain_id: string; platform?: string }, options?: RequestOptions) => {
    const queryParams = `?${new URLSearchParams({
      domain_id: params.domain_id,
      ...(params.platform ? { platform: params.platform } : {}),
    }).toString()}`;
    return apiRequest(`/competitors/content-gaps/${gapId}/${queryParams}`, options);
  },

  // ===== Dashboard =====
  getDashboardSummary: (params: { domain_id: string; days?: number; llm_model?: string }) => {
    const queryParams = new URLSearchParams({
      domain_id: params.domain_id,
      ...(params.days ? { days: String(params.days) } : {}),
      ...(params.llm_model ? { llm_model: params.llm_model } : {}),
    });
    // Use backend API endpoint
    return apiClient.get(`/analytics/dashboard/summary/?${queryParams.toString()}`);
  },

  // ===== Integrations =====
  getIntegrations: () => apiRequest('/integrations/integrations/'),

  getIntegrationsByDomain: (domainId: number) =>
    apiRequest(`/integrations/integrations/by_domain/?domain_id=${domainId}`),

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

  disconnectIntegration: (id: number) => apiRequest(`/integrations/integrations/${id}/disconnect/`, {
    method: 'POST',
  }),

  // Google OAuth
  // `popup` marks an OAuth started from a popup window (e.g. connecting a
  // secondary subdomain on the Configure Report page) — the callback then
  // closes the popup and notifies the opener instead of doing a redirect.
  getGoogleAuthUrl: (domainId: number, integrationType: string = 'google_analytics', popup: boolean = false) =>
    apiRequest(`/integrations/google/auth-url/?domain_id=${domainId}&integration_type=${integrationType}${popup ? '&popup=1' : ''}`),

  // OAuth for a report-only secondary subdomain — anchored on secondary_id, not
  // a Domain. Always a popup (preserves the half-filled report form in the opener).
  getGoogleAuthUrlSecondary: (secondaryId: number, integrationType: string = 'google_analytics') =>
    apiRequest(`/integrations/google/auth-url/?secondary_id=${secondaryId}&integration_type=${integrationType}&popup=1`),

  // Integrations belonging to a report-only secondary subdomain (domain IS NULL).
  getSecondaryIntegrations: (secondaryId: number) =>
    apiRequest(`/integrations/integrations/by_secondary/?secondary_id=${secondaryId}`),

  getGAProperties: (params: { integrationId?: number; domainId?: number }) => {
    const queryParams = new URLSearchParams();
    if (params.integrationId) queryParams.set('integration_id', String(params.integrationId));
    if (params.domainId) queryParams.set('domain_id', String(params.domainId));
    return apiRequest(`/integrations/google/properties/?${queryParams.toString()}`);
  },

  selectGAProperty: (integrationId: number, propertyId: string, propertyName: string) =>
    apiRequest('/integrations/google/select-property/', {
      method: 'POST',
      body: JSON.stringify({ integration_id: integrationId, property_id: propertyId, property_name: propertyName }),
    }),

  getGSCSites: (params: { integrationId?: number; domainId?: number }) => {
    const queryParams = new URLSearchParams();
    if (params.integrationId) queryParams.set('integration_id', String(params.integrationId));
    if (params.domainId) queryParams.set('domain_id', String(params.domainId));
    return apiRequest(`/integrations/google/search-console/sites/?${queryParams.toString()}`);
  },

  selectGSCSite: (integrationId: number, siteId: string, siteName: string) =>
    apiRequest('/integrations/google/search-console/select-site/', {
      method: 'POST',
      body: JSON.stringify({ integration_id: integrationId, site_id: siteId, site_name: siteName }),
    }),

  startTrafficProcessing: (integrationId?: number, daysBack: number = 30) =>
    apiRequest('/integrations/start/', {
      method: 'POST',
      body: JSON.stringify({ integration_id: integrationId, days_back: daysBack }),
    }),

  getTrafficInsights: (domainId: number) =>
    apiRequest(`/integrations/traffic-insights/?domain_id=${domainId}`),

  getGSCKeywords: (domainId: number, articleTitle?: string) =>
    apiRequest<{
      connected: boolean;
      keywords?: Array<{
        keyword: string;
        clicks: number;
        impressions: number;
        ctr: number;
        position: number;
      }>;
      message?: string;
      main_keyword?: string;
      total_keywords?: number;
    }>(`/integrations/gsc-keywords/?domain_id=${domainId}${articleTitle ? `&article_title=${encodeURIComponent(articleTitle)}` : ''}`),

  getGAData: (domainId: number, startDate?: string, endDate?: string) => {
    const queryParams = new URLSearchParams({ domain_id: String(domainId) });
    if (startDate) queryParams.set('start_date', startDate);
    if (endDate) queryParams.set('end_date', endDate);
    return apiRequest(`/integrations/google/analytics-data/?${queryParams.toString()}`);
  },

  getAIReferralData: (domainId: number, startDate?: string, endDate?: string) => {
    const queryParams = new URLSearchParams({ domain_id: String(domainId) });
    if (startDate) queryParams.set('start_date', startDate);
    if (endDate) queryParams.set('end_date', endDate);
    return apiRequest(`/integrations/google/ai-referrals/?${queryParams.toString()}`);
  },

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

  downloadAllReports: async (reportIds?: number[], domainId?: number) => {
    // Build query params
    const params = new URLSearchParams();
    if (reportIds && reportIds.length > 0) {
      params.set('ids', reportIds.join(','));
    }
    if (domainId) {
      params.set('domain_id', String(domainId));
    }
    const queryString = params.toString() ? `?${params.toString()}` : '';

    // Download the ZIP file
    const today = new Date().toISOString().split('T')[0];
    return downloadFile(`/reports/generated/download_all/${queryString}`, `reports_${today}.zip`);
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

  // Content Generation (Backend API)
  generateContent: (data: any) => apiRequest('/content/generate/', {
    method: 'POST',
    body: JSON.stringify(data),
    timeout: 300000, // 5 minutes - content generation takes longer
  }),

  generateOutline: (data: any) => apiRequest('/content/generate-outline/', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  generateContentFromOutline: (data: any) => apiRequest('/content/generate-from-outline/', {
    method: 'POST',
    body: JSON.stringify(data),
    timeout: 300000, // 5 minutes - content generation takes longer
  }),

  rewriteContent: (data: { original_text: string; prompt: string; domain_id?: number }) => apiRequest('/content/rewrite/', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  getGeneratedContents: (params?: { domain_id?: string; status?: string; source_type?: string; page?: number; page_size?: string }, options?: RequestOptions) => {
    const queryParams = params ? `?${new URLSearchParams({
      ...(params.domain_id ? { domain_id: params.domain_id } : {}),
      ...(params.status ? { status: params.status } : {}),
      ...(params.source_type ? { source_type: params.source_type } : {}),
      ...(params.page ? { page: String(params.page) } : {}),
      ...(params.page_size ? { page_size: params.page_size } : {}),
    }).toString()}` : '';
    return apiRequest(`/content/${queryParams}`, options);
  },

  getGeneratedContent: (contentId: number) => apiRequest(`/content/${contentId}/`),

  updateGeneratedContent: (contentId: number, data: any) => apiRequest(`/content/${contentId}/update/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),

  deleteGeneratedContent: (contentId: number) => apiRequest(`/content/${contentId}/delete/`, {
    method: 'DELETE',
  }),

  // AI Content Detection
  detectAiContent: (text: string, contentId?: number) => apiRequest('/content/detect-ai/', {
    method: 'POST',
    body: JSON.stringify({ text, content_id: contentId }),
  }),

  // Humanise content
  humaniseContent: (contentId: number) => apiRequest(`/content/${contentId}/humanise/`, {
    method: 'POST',
  }),

  getHumaniseStatus: (contentId: number) => apiRequest(`/content/${contentId}/humanise-status/`),

  humaniseUndo: (contentId: number) => apiRequest(`/content/${contentId}/humanise-undo/`, {
    method: 'POST',
  }),

  // ===== CMS Provider Management =====
  getCMSProviders: (params?: { domain_id?: number }) => {
    const queryParams = params?.domain_id ? `?domain_id=${params.domain_id}` : '';
    return apiRequest(`/content/cms-providers/${queryParams}`);
  },

  createCMSProvider: (data: {
    domain: number;
    provider_type: string;
    name: string;
    settings: Record<string, any>;
    is_active?: boolean;
    is_default?: boolean;
  }) =>
    apiRequest('/content/cms-providers/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateCMSProvider: (providerId: number, data: Partial<{
    domain: number;
    provider_type: string;
    name: string;
    settings: Record<string, any>;
    is_active: boolean;
    is_default: boolean;
  }>) =>
    apiRequest(`/content/cms-providers/${providerId}/`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  deleteCMSProvider: (providerId: number) =>
    apiRequest(`/content/cms-providers/${providerId}/`, {
      method: 'DELETE',
    }),

  testCMSProviderConnection: (providerId: number) =>
    apiRequest(`/content/cms-providers/${providerId}/test/`, {
      method: 'POST',
    }),

  // ===== Publishing =====
  publishContent: (data: {
    content_id: number;
    cms_provider_id: number;
    publish_now: boolean;
    scheduled_at?: string;
  }) =>
    apiRequest('/content/publish/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // ===== Misinformation Alerts =====
  getMisinformationDashboard: (params: { domain_id: string; days?: number }) => {
    const queryParams = `?${new URLSearchParams({
      domain_id: params.domain_id,
      ...(params.days ? { days: String(params.days) } : {}),
    }).toString()}`;
    return apiRequest(`/misinformation/dashboard/${queryParams}`);
  },

  getMisinformationAlerts: (params: {
    domain_id: string;
    alert_type?: string;
    severity?: string;
    status?: string;
    page?: number;
    page_size?: number;
  }) => {
    const queryParams = `?${new URLSearchParams({
      domain_id: params.domain_id,
      ...(params.alert_type ? { alert_type: params.alert_type } : {}),
      ...(params.severity ? { severity: params.severity } : {}),
      ...(params.status ? { status: params.status } : {}),
      ...(params.page ? { page: String(params.page) } : {}),
      ...(params.page_size ? { page_size: String(params.page_size) } : {}),
    }).toString()}`;
    return apiRequest(`/misinformation/alerts/${queryParams}`);
  },

  getMisinformationAlert: (alertId: number) =>
    apiRequest(`/misinformation/alerts/${alertId}/`),

  getMisinformationAlertComparison: (alertId: number) =>
    apiRequest(`/misinformation/alerts/${alertId}/comparison/`),

  updateMisinformationAlert: (alertId: number, data: { status: string }) =>
    apiRequest(`/misinformation/alerts/${alertId}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  triggerMisinformationScan: (data: { domain_id: number; prompt_analytics_ids?: number[] }) =>
    apiRequest('/misinformation/scan/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getMisinformationScanStatus: (scanId: number) =>
    apiRequest(`/misinformation/scan/${scanId}/`),

  getMisinformationScans: (params: { domain_id: string; page?: number; page_size?: number }) => {
    const queryParams = `?${new URLSearchParams({
      domain_id: params.domain_id,
      ...(params.page ? { page: String(params.page) } : {}),
      ...(params.page_size ? { page_size: String(params.page_size) } : {}),
    }).toString()}`;
    return apiRequest(`/misinformation/scans/${queryParams}`);
  },

  getMisinformationAnalytics: (params: { domain_id: string; start_date?: string; end_date?: string }) => {
    const queryParams = `?${new URLSearchParams({
      domain_id: params.domain_id,
      ...(params.start_date ? { start_date: params.start_date } : {}),
      ...(params.end_date ? { end_date: params.end_date } : {}),
    }).toString()}`;
    return apiRequest(`/misinformation/analytics/${queryParams}`);
  },

  // ===== Citations =====
  getCitationsDashboard: (params: { domain_id: string; days?: number }) => {
    const queryParams = `?${new URLSearchParams({
      domain_id: params.domain_id,
      ...(params.days ? { days: String(params.days) } : {}),
    }).toString()}`;
    return apiRequest(`/misinformation/citations/dashboard/${queryParams}`);
  },

  getCitations: (params: {
    domain_id: string;
    status?: string;
    source_type?: string;
    platform?: string;
    search?: string;
    page?: number;
    page_size?: number;
  }) => {
    const queryParams = `?${new URLSearchParams({
      domain_id: params.domain_id,
      ...(params.status ? { status: params.status } : {}),
      ...(params.source_type ? { source_type: params.source_type } : {}),
      ...(params.platform ? { platform: params.platform } : {}),
      ...(params.search ? { search: params.search } : {}),
      ...(params.page ? { page: String(params.page) } : {}),
      ...(params.page_size ? { page_size: String(params.page_size) } : {}),
    }).toString()}`;
    return apiRequest(`/misinformation/citations/${queryParams}`);
  },

  getCitationDetail: (citationId: number) =>
    apiRequest(`/misinformation/citations/${citationId}/`),

  getCitationsBySource: (params: { domain_id: string; limit?: number }) => {
    const queryParams = `?${new URLSearchParams({
      domain_id: params.domain_id,
      ...(params.limit ? { limit: String(params.limit) } : {}),
    }).toString()}`;
    return apiRequest(`/misinformation/citations/by-source/${queryParams}`);
  },

  // ===== Agentic ChatBot =====
  sendChatMessage: (data: {
    message: string;
    domain_id: number;
    conversation_id?: number;
  }) => apiRequest('/chat/send_message/', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  getChatConversations: (params?: { domain_id?: number }) => {
    const queryParams = params ? `?${new URLSearchParams(
      Object.entries(params).reduce((acc, [k, v]) => {
        if (v !== undefined) acc[k] = String(v);
        return acc;
      }, {} as Record<string, string>)
    ).toString()}` : '';
    return apiRequest(`/chat/conversations/${queryParams}`);
  },

  getChatConversationDetail: (conversationId: number) =>
    apiRequest(`/chat/${conversationId}/conversation_detail/`),

  deleteChatConversation: (conversationId: number) =>
    apiRequest(`/chat/${conversationId}/delete_conversation/`, {
      method: 'DELETE',
    }),

  // ===== Content Comments (Google Docs-style) =====
  getContentComments: (contentId: number) =>
    apiRequest(`/content/${contentId}/comments/`),

  addContentComment: (contentId: number, data: {
    selected_text: string;
    comment: string;
    suggestion?: string;
  }) =>
    apiRequest(`/content/${contentId}/comments/`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateContentComment: (contentId: number, commentId: number, data: {
    comment?: string;
    suggestion?: string;
    status?: 'pending' | 'accepted' | 'rejected';
  }) =>
    apiRequest(`/content/${contentId}/comments/${commentId}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  deleteContentComment: (contentId: number, commentId: number) =>
    apiRequest(`/content/${contentId}/comments/${commentId}/`, {
      method: 'DELETE',
    }),

  // ===== Bulk Content Upload =====
  downloadBulkUploadTemplate: async (domainId?: number) => {
    const token = getAuthToken();
    const url = domainId
      ? `${API_BASE_URL}/content/bulk-upload/template/?domain_id=${domainId}`
      : `${API_BASE_URL}/content/bulk-upload/template/`;
    const response = await fetch(url, {
      headers: {
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      },
    });
    if (!response.ok) throw new Error('Failed to download template');
    const blob = await response.blob();
    const blobUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = 'bulk_content_upload_template.xlsx';
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(blobUrl);
    document.body.removeChild(a);
  },

  uploadBulkContent: async (domainId: number, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('domain_id', String(domainId));

    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/content/bulk-upload/`, {
      method: 'POST',
      headers: {
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      },
      body: formData,
    });

    const data = await response.json();
    if (!response.ok) {
      throw { response: data, status: response.status };
    }
    return data;
  },

  getBulkUploadBatches: (params?: { domain_id?: string }) => {
    const queryParams = params?.domain_id ? `?domain_id=${params.domain_id}` : '';
    return apiRequest(`/content/bulk-upload/batches/${queryParams}`);
  },

  getBulkUploadBatchDetail: (batchId: number) =>
    apiRequest(`/content/bulk-upload/batches/${batchId}/`),

  retryBulkUploadItem: (itemId: number) =>
    apiRequest(`/content/bulk-upload/items/${itemId}/retry/`, {
      method: 'POST',
    }),

  updateBulkUploadItemStatus: (itemId: number, newStatus: string) =>
    apiRequest(`/content/bulk-upload/items/${itemId}/status/`, {
      method: 'PATCH',
      body: JSON.stringify({ status: newStatus }),
    }),

  // ===== URL Reading (Issue 8A) =====
  readUrl: (url: string) => apiRequest('/content/read-url/', {
    method: 'POST',
    body: JSON.stringify({ url }),
  }),

  // ===== Keyword Suggestions (Issue 8B) =====
  suggestKeywords: (data: { title: string; article_type?: string; domain_url?: string; existing_keywords?: string }) =>
    apiRequest('/content/suggest-keywords/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // ===== Content Planning (Issue 8C) =====
  planContent: (data: {
    domain_id: number;
    title: string;
    keywords?: string;
    article_type?: string;
    scheduled_date?: string;
    priority?: string;
    word_count?: number;
  }) => apiRequest('/content/plan/', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  rescheduleContent: (contentId: number, scheduledDate: string | null) =>
    apiRequest(`/content/${contentId}/reschedule/`, {
      method: 'PATCH',
      body: JSON.stringify({ scheduled_date: scheduledDate }),
    }),

  // ===== Content Refurbishing (Issue 8D) =====
  refurbishContent: (data: {
    content_id: number;
    refurbish_type: 'refresh_stats' | 'improve_seo' | 'expand' | 'repurpose';
    new_article_type?: string;
    new_keywords?: string;
    additional_instructions?: string;
  }) => apiRequest('/content/refurbish/', {
    method: 'POST',
    body: JSON.stringify(data),
    timeout: 300000, // 5 minutes
  }),

  // ===== File Text Extraction (Issue 12) =====
  extractFileText: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);

    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/content/extract-file-text/`, {
      method: 'POST',
      headers: {
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      },
      body: formData,
    });

    const data = await response.json();
    if (!response.ok) {
      throw { response: data, status: response.status };
    }
    return data;
  },

  // ===== SEO Rankings =====
  getSeoKeywords: (params: { domain_id: string; platform?: string; search?: string; status?: string }) => {
    const searchParams = new URLSearchParams({ domain_id: params.domain_id });
    if (params.platform) searchParams.append('platform', params.platform);
    if (params.search) searchParams.append('search', params.search);
    if (params.status) searchParams.append('status', params.status);
    return apiRequest(`/seo/keywords/?${searchParams.toString()}`);
  },

  addSeoKeyword: (data: {
    keyword: number;
    domain: number;
    platform?: string;
    target_url?: string;
    region?: string;
    isocode?: string;
    language_code?: string;
    geo_target?: string;
    geo_target_uule?: string;
  }) =>
    apiRequest('/seo/keywords/add/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  bulkAddSeoKeywords: (data: {
    domain_id: number;
    keywords: Array<{
      keyword_id: number;
      platform?: string;
      target_url?: string;
      region?: string;
      isocode?: string;
      language_code?: string;
    }>;
  }) =>
    apiRequest('/seo/keywords/bulk-add/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getSeoKeywordRemaining: () =>
    apiRequest('/seo/keywords/remaining/'),

  importSeoKeywords: (data: FormData | {
    domain_id: number;
    keywords: string[];
    platform?: string;
    region?: string;
    isocode?: string;
    language_code?: string;
    geo_target?: string;
    geo_target_uule?: string;
    target_url?: string;
    tags?: string[];
  }) =>
    apiRequest('/seo/keywords/import/', {
      method: 'POST',
      body: data instanceof FormData ? data : JSON.stringify(data),
    }),

  getSeoKeywordDetail: (id: number) =>
    apiRequest(`/seo/keywords/${id}/`),

  deleteSeoKeyword: (id: number) =>
    apiRequest(`/seo/keywords/${id}/`, { method: 'DELETE' }),

  getSeoRankHistory: (seoKwId: number, days?: number) => {
    const params = days ? `?days=${days}` : '';
    return apiRequest(`/seo/keywords/${seoKwId}/history/${params}`);
  },

  getSeoSerpFeatures: (seoKwId: number) =>
    apiRequest(`/seo/keywords/${seoKwId}/serp-features/`),

  getSeoDomainMetrics: (params: { domain_id: string; days?: number }) => {
    const searchParams = new URLSearchParams({ domain_id: params.domain_id });
    if (params.days) searchParams.append('days', String(params.days));
    return apiRequest(`/seo/metrics/?${searchParams.toString()}`);
  },

  getSeoDomainOverview: (domainId: string) =>
    apiRequest(`/seo/overview/?domain_id=${domainId}`),

  triggerSeoRanking: (data: { domain_id?: number; seo_keyword_rank_id?: number }) =>
    apiRequest('/seo/trigger/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getSeoRefreshStatus: (domainId: string) =>
    apiRequest(`/seo/refresh-status/?domain_id=${domainId}`),

  bulkDeleteSeoKeywords: (ids: number[]) =>
    apiRequest('/seo/keywords/bulk-delete/', {
      method: 'POST',
      body: JSON.stringify({ ids }),
    }),

  updateSeoKeywordTags: (data: { ids: number[]; tags: string[]; mode?: 'merge' | 'replace' }) =>
    apiRequest('/seo/keywords/update-tags/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  removeSeoKeywordTag: (data: { domain_id: number; tag: string }) =>
    apiRequest('/seo/keywords/remove-tag/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getSeoKeywordTags: (domainId: string, ids?: number[]) => {
    const params = new URLSearchParams({ domain_id: domainId });
    if (ids && ids.length) params.append('ids', ids.join(','));
    return apiRequest(`/seo/keywords/get-tags/?${params.toString()}`);
  },

  toggleSeoKeywordFavourite: (data: { id?: number; domain_id?: number; value: number }) =>
    apiRequest('/seo/keywords/favourite/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // ===== SEO Keyword Detail — Notes =====
  getSeoKeywordNotes: (seoKwId: number) =>
    apiRequest(`/seo/keywords/${seoKwId}/notes/`),

  createSeoKeywordNote: (seoKwId: number, data: { title: string; notes: string; note_date: string }) =>
    apiRequest(`/seo/keywords/${seoKwId}/notes/create/`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateSeoKeywordNote: (seoKwId: number, noteId: number, data: { title: string; notes: string; note_date: string }) =>
    apiRequest(`/seo/keywords/${seoKwId}/notes/${noteId}/`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  deleteSeoKeywordNote: (seoKwId: number, noteId: number) =>
    apiRequest(`/seo/keywords/${seoKwId}/notes/${noteId}/`, {
      method: 'DELETE',
    }),

  // ===== SEO Keyword Detail — Volume History =====
  getSeoKeywordVolume: (seoKwId: number) =>
    apiRequest(`/seo/keywords/${seoKwId}/volume/`),

  // ===== SEO Keyword Detail — Competitors =====
  getSeoKeywordCompetitors: (seoKwId: number, type?: string) => {
    const params = type ? `?type=${type}` : '';
    return apiRequest(`/seo/keywords/${seoKwId}/competitors/${params}`);
  },

  exportSeoKeywordsPdf: async (domainId: number): Promise<Blob> => {
    const token = getAuthToken();
    const headers: HeadersInit = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const response = await fetch(`${API_BASE_URL}/seo/keywords/pdf-export/`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ domain_id: domainId }),
    });
    if (!response.ok) throw new Error('PDF export failed');
    return response.blob();
  },

  // ===== SEO Competitor Analysis =====
  startSeoCompetitorAnalysis: (domainId: number) =>
    apiRequest('/seo/competitors/start/', {
      method: 'POST',
      body: JSON.stringify({ domain_id: domainId }),
    }),

  getSeoCompetitorStatus: (domainId: number) =>
    apiRequest(`/seo/competitors/status/?domain_id=${domainId}`),

  addSeoCompetitor: (domainId: number, competitorDomain: string) =>
    apiRequest('/seo/competitors/add/', {
      method: 'POST',
      body: JSON.stringify({ domain_id: domainId, competitor_domain: competitorDomain }),
    }),

  deleteSeoCompetitor: (projectId: number) =>
    apiRequest(`/seo/competitors/${projectId}/delete/`, { method: 'DELETE' }),

  getSeoCompetitorProjects: (domainId: number) =>
    apiRequest(`/seo/competitors/projects/?domain_id=${domainId}`),

  getSeoCompetitorKeywords: (projectId: number) =>
    apiRequest(`/seo/competitors/${projectId}/keywords/`),

  // SEO Report Sheets
  getSeoReportSheets: (domainId: number) =>
    apiRequest(`/seo/report-sheets/?domain_id=${domainId}`),

  // Create-or-get a report-only secondary subdomain (NOT a Domain), so its own
  // GA4/GSC connection can be pooled into the report. Returns { secondary_id }.
  resolveSecondarySubdomain: (primaryDomainId: number, subdomain: string) =>
    apiRequest<{ secondary_id: number; name: string; url: string; created: boolean }>(
      '/seo/report-sheets/secondary-domain/resolve/',
      {
        method: 'POST',
        body: JSON.stringify({ primary_domain_id: primaryDomainId, subdomain }),
      },
    ),

  addSeoReportSheet: (data: {
    domain_id: number;
    sheet_name: string;
    category: string;
    sheet_type: string;
    metrics?: string[];
    change_units?: string[];
    schedule?: string;
    duration?: number;
    order_by?: string;
    secondary_domain_id?: number | null;
  }) =>
    apiRequest('/seo/report-sheets/add/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  deleteSeoReportSheet: (id: number) =>
    apiRequest(`/seo/report-sheets/${id}/delete/`, { method: 'DELETE' }),

  updateSeoReportSheet: (id: number, data: Record<string, any>) =>
    apiRequest(`/seo/report-sheets/${id}/update/`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  getSeoReportSheetData: (domainId: number, sheetIds?: number[]) =>
    apiRequest(
      `/seo/report-sheets/data/?domain_id=${domainId}` +
      (sheetIds && sheetIds.length ? `&sheet_ids=${sheetIds.join(',')}` : '')
    ),

  exportSeoReportXlsx: async (domainId: number): Promise<Blob> => {
    const token = getAuthToken();
    const headers: HeadersInit = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const response = await fetch(`${API_BASE_URL}/seo/report-sheets/export/?domain_id=${domainId}`, {
      method: 'GET',
      headers,
    });
    if (!response.ok) throw new Error('Excel export failed');
    return response.blob();
  },
};

// Also export as 'api' for flexibility
export const api = apiClient;

export default apiClient;
