import { LoginRequest, LoginResponse, User, Permission, ApiError } from '@/types/auth';
import { config } from '@/config/environment';

// API Configuration
const API_BASE_URL = config.API_BASE_URL;
const API_TIMEOUT = config.API_TIMEOUT;

class ApiClient {
  private baseURL: string;
  private timeout: number;

  constructor(baseURL: string, timeout: number = API_TIMEOUT) {
    this.baseURL = baseURL;
    this.timeout = timeout;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    const token = this.getAccessToken();

    const config: RequestInit = {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
        ...options.headers,
      },
      signal: AbortSignal.timeout(this.timeout),
    };

    try {
      const response = await fetch(url, config);

      if (!response.ok) {
        const errorData: ApiError = await response.json().catch(() => ({
          error: `HTTP ${response.status}: ${response.statusText}`,
        }));
        throw new Error(errorData.error || (errorData as any).detail || 'Request failed');
      }

      return await response.json();
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error('Network error occurred');
    }
  }

  private getAccessToken(): string | null {
    return localStorage.getItem('access_token');
  }

  private setTokens(accessToken: string, refreshToken: string): void {
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
  }

  private clearTokens(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }

  // Authentication methods
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await this.request<LoginResponse>('/auth/login/', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });

    // Store tokens
    this.setTokens(response.access, response.refresh);

    return response;
  }

  async logout(): Promise<void> {
    const refreshToken = localStorage.getItem('refresh_token');
    
    if (refreshToken) {
      try {
        await this.request('/auth/logout/', {
          method: 'POST',
          body: JSON.stringify({ refresh: refreshToken }),
        });
      } catch (error) {
        console.warn('Logout request failed:', error);
      }
    }

    this.clearTokens();
  }

  async refreshToken(): Promise<{ access: string }> {
    const refreshToken = localStorage.getItem('refresh_token');
    
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await this.request<{ access: string }>('/auth/token/refresh/', {
      method: 'POST',
      body: JSON.stringify({ refresh: refreshToken }),
    });

    // Update access token
    localStorage.setItem('access_token', response.access);

    return response;
  }

  async getProfile(): Promise<{ user: User; permissions: Permission[] }> {
    return await this.request<{ user: User; permissions: Permission[] }>('/auth/profile/');
  }

  async updateProfile(data: Partial<User>): Promise<{ message: string; user: User }> {
    return await this.request<{ message: string; user: User }>('/auth/profile/update/', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  // Forgot Password API methods
  async forgotPassword(email: string): Promise<{ message: string; email: string }> {
    const response = await fetch(`${this.baseURL}/auth/forgot-password/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to send password reset email');
    }

    return response.json();
  }

  async verifyResetToken(tokenId: string): Promise<{ valid: boolean; email?: string; expires_at?: string; error?: string }> {
    const response = await fetch(`${this.baseURL}/auth/verify-reset-token/${tokenId}/`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to verify reset token');
    }

    return response.json();
  }

  async resetPassword(token: string, newPassword: string, confirmPassword: string): Promise<{ message: string; email: string }> {
    const response = await fetch(`${this.baseURL}/auth/reset-password/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        token,
        new_password: newPassword,
        confirm_password: confirmPassword,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to reset password');
    }

    return response.json();
  }

  // Team Invitation API methods
  async getInvitationDetails(invitationId: string): Promise<{
    id: string;
    email: string;
    organisation: number;
    organisation_name: string;
    invited_by: number;
    invited_by_name: string;
    role: string;
    status: string;
    message: string;
    expires_at: string;
    is_expired: boolean;
    can_be_accepted: boolean;
  }> {
    const response = await fetch(`${this.baseURL}/auth/invitation/${invitationId}/`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get invitation details');
    }

    return response.json();
  }

  

  // Permission management methods
  async checkPermissions(module?: string): Promise<any> {
    const endpoint = module ? `/auth/permissions/check/?module=${module}` : '/auth/permissions/check/';
    return await this.request(endpoint);
  }

  async getAvailableModules(): Promise<{
    modules: Array<{ value: string; label: string }>;
    permission_levels: Array<{ value: string; label: string }>;
  }> {
    return await this.request('/auth/permissions/modules/');
  }

  async listPermissions(filters?: { user_id?: number; module?: string }): Promise<{
    permissions: Permission[];
    total_count: number;
    filters_applied: any;
  }> {
    const params = new URLSearchParams();
    if (filters?.user_id) params.append('user_id', filters.user_id.toString());
    if (filters?.module) params.append('module', filters.module);
    
    const queryString = params.toString();
    const endpoint = queryString ? `/auth/permissions/?${queryString}` : '/auth/permissions/';
    
    return await this.request(endpoint);
  }

  async listUserPermissions(userId: number): Promise<{
    user: User;
    permissions: Permission[];
    total_count: number;
  }> {
    return await this.request(`/auth/permissions/user/${userId}/`);
  }

  async updatePermission(permissionId: number, permissionLevel: string): Promise<{
    message: string;
    permission: Permission;
  }> {
    return await this.request(`/auth/permissions/${permissionId}/`, {
      method: 'PUT',
      body: JSON.stringify({ permission_level: permissionLevel }),
    });
  }

  async deletePermission(permissionId: number): Promise<{ message: string }> {
    return await this.request(`/auth/permissions/${permissionId}/delete/`, {
      method: 'DELETE',
    });
  }

  async bulkAssignPermissions(permissions: Array<{
    user: number;
    module: string;
    permission_level: string;
  }>): Promise<{
    message: string;
    created_permissions: Permission[];
    errors: any[];
    success_count: number;
    error_count: number;
  }> {
    return await this.request('/auth/permissions/bulk-assign/', {
      method: 'POST',
      body: JSON.stringify({ permissions }),
    });
  }

  async revokeAllPermissions(userId: number): Promise<{
    message: string;
    deleted_count: number;
  }> {
    return await this.request(`/auth/permissions/user/${userId}/revoke-all/`, {
      method: 'POST',
    });
  }

  async grantAllPermissions(userId: number, permissionLevel: string = 'read'): Promise<{
    message: string;
    created_permissions: Permission[];
    created_count: number;
  }> {
    return await this.request(`/auth/permissions/user/${userId}/grant-all/`, {
      method: 'POST',
      body: JSON.stringify({ permission_level: permissionLevel }),
    });
  }

  async getPermissionSummary(): Promise<{
    module_counts: Record<string, any>;
    user_permission_counts: Array<{
      user_id: number;
      user_email: string;
      user_name: string;
      permission_count: number;
      total_modules: number;
      percentage: number;
    }>;
    total_users: number;
    total_modules: number;
  }> {
    return await this.request('/auth/permissions/summary/');
  }

  // Team management methods
  async sendInvitation(data: {
    email: string;
    role: 'admin' | 'user';
    message?: string;
  }): Promise<{ message: string; invitation: any }> {
    return await this.request('/auth/invite/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async acceptInvitation(invitationId: string, userData: {
    first_name: string;
    last_name: string;
    password: string;
  }): Promise<{ message: string; user: User }> {
    return await this.request(`/auth/accept-invitation/${invitationId}/`, {
      method: 'POST',
      body: JSON.stringify(userData),
    });
  }

  // Organization Management methods
  async getOrganization(): Promise<{
    id: number;
    name: string;
    industry: string;
    team_count: number;
    created_at: string;
    modified_at: string;
  }> {
    return await this.request('/auth/organization/');
  }

  async updateOrganization(data: {
    name?: string;
    industry?: string;
  }): Promise<{
    message: string;
    organization: any;
  }> {
    return await this.request('/auth/organization/', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  // Domain Management methods
  async getDomains(options?: { manage?: boolean }): Promise<{
    domains: Array<{
      id: number;
      name: string;
      url: string;
      organisation: number;
      total_mentions: number;
      total_citations: number;
      visibility_score: string;
      average_position: string;
      active_alerts: number;
      sentiment: string;
      sentiment_score: string;
      created_at: string;
      modified_at: string;
    }>;
  }> {
    const query = options?.manage ? '?manage=1' : '';
    return await this.request(`/domains/${query}`);
  }

  async createDomain(data: {
    name: string;
    url: string;
  }): Promise<{
    message: string;
    domain: any;
  }> {
    return await this.request('/domains/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateDomain(domainId: number, data: {
    name?: string;
    url?: string;
  }): Promise<{
    message: string;
    domain: any;
  }> {
    return await this.request(`/domains/${domainId}/`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteDomain(domainId: number): Promise<{ message: string }> {
    return await this.request(`/domains/${domainId}/`, {
      method: 'DELETE',
    });
  }

  // Domain Access Management methods
  async getDomainAccess(domainId: number): Promise<{
    access_list: Array<{
      id: number;
      user: {
        id: number;
        email: string;
        first_name: string;
        last_name: string;
      };
      // no access level
      granted_by: {
        id: number;
        email: string;
      };
      created_at: string;
    }>;
  }> {
    return await this.request(`/domains/${domainId}/access/`);
  }

  async grantDomainAccess(domainId: number, data: {
    user_id: number;
  }): Promise<{
    message: string;
    access: any;
  }> {
    return await this.request(`/domains/${domainId}/access/`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateDomainAccess(domainId: number, userId: number, data: {}): Promise<{
    message: string;
    access: any;
  }> {
    return await this.request(`/domains/${domainId}/access/${userId}/`, {
      method: 'PUT',
      body: JSON.stringify(data || {}),
    });
  }

  async revokeDomainAccess(domainId: number, userId: number): Promise<{
    message: string;
  }> {
    return await this.request(`/domains/${domainId}/access/${userId}/`, {
      method: 'DELETE',
    });
  }

  async getAvailableUsersForDomain(domainId: number): Promise<{
    available_users: Array<{
      id: number;
      email: string;
      first_name: string;
      last_name: string;
      role: 'admin' | 'user';
    }>;
  }> {
    return await this.request(`/domains/${domainId}/access/available-users/`);
  }

  // Detected Models methods
  async getDetectedModels(): Promise<{
    detected_models: Array<{
      id: number;
      name: string;
      domain: number;
      domain_name: string;
      organisation: number;
      detection_count: number;
      first_detected: string;
      last_detected: string;
      is_active: boolean;
    }>;
  }> {
    return await this.request('/domains/detected-models/');
  }

  async updateDetectedModel(modelId: number, data: {
    is_active?: boolean;
  }): Promise<{
    message: string;
    detected_model: any;
  }> {
    return await this.request(`/domains/detected-models/${modelId}/`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  // Team Management methods
  async getTeamMembers(): Promise<{
    members: Array<{
      id: number;
      email: string;
      first_name: string;
      last_name: string;
      role: 'admin' | 'user';
      organisation: number;
      organisation_name: string;
      is_active: boolean;
      created_at: string;
      modified_at: string;
    }>;
    invitations: Array<{
      id: string;
      email: string;
      role: 'admin' | 'user';
      status: 'pending' | 'accepted' | 'declined' | 'expired';
      invited_by: number;
      invited_by_email: string;
      expires_at: string;
      accepted_at?: string | null;
      created_at: string;
    }>;
  }> {
    return await this.request('/auth/team-members/');
  }

  async updateTeamMemberRole(memberId: number, role: 'admin' | 'user'): Promise<{
    message: string;
    member: any;
  }> {
    return await this.request(`/auth/team-members/${memberId}/`, {
      method: 'PUT',
      body: JSON.stringify({ role }),
    });
  }

  async removeTeamMember(memberId: number): Promise<{ message: string }> {
    return await this.request(`/auth/team-members/${memberId}/`, {
      method: 'DELETE',
    });
  }

  // Mentions API methods
  async getMentions(params?: {
    search?: string;
    platform?: string;
    sentiment?: string;
    limit?: number;
    offset?: number;
    domain_id?: number;
  }): Promise<{
    mentions: any[];
    total_count: number;
    filters_applied: any;
    pagination?: { limit: number; offset: number; returned: number };
    available_platforms: string[];
    available_sentiments: string[];
  }> {
    const queryParams = new URLSearchParams();
    if (params?.search) queryParams.append('search', params.search);
    if (params?.platform) queryParams.append('platform', params.platform);
    if (params?.sentiment) queryParams.append('sentiment', params.sentiment);
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.offset) queryParams.append('offset', params.offset.toString());
    if (params?.domain_id) queryParams.append('domain_id', params.domain_id.toString());
    
    const queryString = queryParams.toString();
    const response: any = await this.request(`/prompts/mentions/${queryString ? `?${queryString}` : ''}`);
    
    // Transform the response to match expected structure
    return {
      mentions: response.mentions || [],
      total_count: response.total_count || 0,
      filters_applied: response.filters_applied || {},
      pagination: response.pagination || undefined,
      available_platforms: response.available_platforms || [],
      available_sentiments: response.available_sentiments || []
    };
  }

  async getMentionDetail(id: number): Promise<any> {
    return await this.request(`/prompts/mentions/${id}/`);
  }

  async getMentionFilters(): Promise<{
    platforms: Array<{ name: string; count: number }>;
    sentiments: Array<{ name: string; count: number }>;
    total_mentions: number;
  }> {
    return await this.request('/prompts/mentions/filters/');
  }

  async getMentionTrends(days: number = 30): Promise<{
    trends: any[];
    period: string;
    total_mentions: number;
  }> {
    return await this.request(`/prompts/mentions/trends/?days=${days}`);
  }

  async getMentionAnalytics(): Promise<{
    platform_stats: any[];
    sentiment_stats: any[];
    top_mentions: any[];
    competitor_analysis: any;
    total_mentions: number;
    avg_position: number;
    avg_sentiment: number;
  }> {
    return await this.request('/prompts/mentions/analytics/');
  }

  async getRelatedMentions(id: number): Promise<{
    related_mentions: any[];
    original_mention: any;
  }> {
    return await this.request(`/prompts/mentions/${id}/related/`);
  }

  async exportMentions(data: {
    platform?: string;
    sentiment?: string;
    date_from?: string;
    date_to?: string;
    format?: string;
  }): Promise<{
    message: string;
    format: string;
    count: number;
    data: any[];
    download_url: string;
  }> {
    return await this.request('/prompts/mentions/export/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // ==================== PROMPTS APIs ====================

  // Prompt Groups APIs
  async getPromptGroups(params?: {
    domain_id?: number;
    search?: string;
    limit?: number;
    offset?: number;
  }): Promise<{
    groups: any[];
    total_count: number;
    filters_applied: any;
    pagination?: { limit: number; offset: number; returned: number };
  }> {
    const queryParams = new URLSearchParams();
    if (params?.domain_id) queryParams.append('domain_id', params.domain_id.toString());
    if (params?.search) queryParams.append('search', params.search);
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.offset) queryParams.append('offset', params.offset.toString());
    
    const queryString = queryParams.toString();
    return await this.request(`/prompts/groups/${queryString ? `?${queryString}` : ''}`);
  }

  async createPromptGroup(data: {
    group_id: string;
    domain_id: number;
    primary_prompts: string[];
    secondary_prompts: string[];
  }): Promise<{
    message: string;
    group: any;
    prompts_created: number;
    analytics_created: number;
    platforms: string[];
  }> {
    return await this.request('/prompts/groups/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getPromptGroupDetail(groupId: number): Promise<{
    group: any;
  }> {
    return await this.request(`/prompts/groups/${groupId}/`);
  }

  async updatePromptGroup(groupId: number, data: {
    group_id?: string;
    domain_id?: number;
  }): Promise<{
    message: string;
    group: any;
  }> {
    return await this.request(`/prompts/groups/${groupId}/`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deletePromptGroup(groupId: number): Promise<{
    message: string;
  }> {
    return await this.request(`/prompts/groups/${groupId}/`, {
      method: 'DELETE',
    });
  }

  // Prompts APIs
  async getPrompts(params?: {
    group_id?: number;
    domain_id?: number;
    track_status?: string;
    type?: string;
    search?: string;
  }): Promise<{
    prompts: any[];
    total_count: number;
    filters_applied: any;
  }> {
    const queryParams = new URLSearchParams();
    if (params?.group_id) queryParams.append('group_id', params.group_id.toString());
    if (params?.domain_id) queryParams.append('domain_id', params.domain_id.toString());
    if (params?.track_status) queryParams.append('track_status', params.track_status);
    if (params?.type) queryParams.append('type', params.type);
    if (params?.search) queryParams.append('search', params.search);
    
    const queryString = queryParams.toString();
    return await this.request(`/prompts/prompts/${queryString ? `?${queryString}` : ''}`);
  }

  async createPrompt(data: {
    prompt: string;
    domain_id: number;
    group_id?: number;
    track_status?: string;
    type?: string;
    track_message?: string;
  }): Promise<{
    message: string;
    prompt: any;
  }> {
    return await this.request('/prompts/prompts/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getPromptDetail(promptId: number): Promise<{
    prompt: any;
  }> {
    return await this.request(`/prompts/prompts/${promptId}/`);
  }

  async updatePrompt(promptId: number, data: {
    prompt?: string;
    group_id?: number;
    track_status?: string;
    type?: string;
    track_message?: string;
  }): Promise<{
    message: string;
    prompt: any;
  }> {
    return await this.request(`/prompts/prompts/${promptId}/`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deletePrompt(promptId: number): Promise<{
    message: string;
  }> {
    return await this.request(`/prompts/prompts/${promptId}/`, {
      method: 'DELETE',
    });
  }

  async bulkUpdatePrompts(data: {
    prompt_ids: number[];
    updates: {
      track_status?: string;
      type?: string;
      track_message?: string;
      group_id?: number;
    };
  }): Promise<{
    message: string;
    updated_count: number;
    total_requested: number;
  }> {
    return await this.request('/prompts/prompts/bulk-update/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getPromptAnalytics(promptId: number, params?: {
    platform?: string;
    is_mention?: boolean;
  }): Promise<{
    prompt: any;
    analytics: any[];
    total_count: number;
    filters_applied: any;
    summary: any;
  }> {
    const queryParams = new URLSearchParams();
    if (params?.platform) queryParams.append('platform', params.platform);
    if (params?.is_mention !== undefined) queryParams.append('is_mention', params.is_mention.toString());
    
    const queryString = queryParams.toString();
    return await this.request(`/prompts/prompts/${promptId}/analytics/${queryString ? `?${queryString}` : ''}`);
  }

  // ==================== ALERTS API ====================
  
  async getAlerts(params?: {
    domain_id?: number;
    status?: 'active' | 'investigating' | 'resolved';
    type?: string;
    severity?: 'high' | 'medium' | 'low';
  }): Promise<any[]> {
    const queryParams = new URLSearchParams();
    if (params?.domain_id) queryParams.append('domain_id', params.domain_id.toString());
    if (params?.status) queryParams.append('status', params.status);
    if (params?.type) queryParams.append('type', params.type);
    if (params?.severity) queryParams.append('severity', params.severity);
    
    const queryString = queryParams.toString();
    return await this.request(`/alerts/alerts/${queryString ? `?${queryString}` : ''}`);
  }

  async getAlert(id: number): Promise<any> {
    return await this.request(`/alerts/alerts/${id}/`);
  }

  async createAlert(data: {
    domain: number;
    type: string;
    severity: string;
    title: string;
    message: string;
    platform?: string;
    metric?: number;
  }): Promise<any> {
    return await this.request('/alerts/alerts/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateAlert(id: number, data: any): Promise<any> {
    return await this.request(`/alerts/alerts/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async resolveAlert(id: number): Promise<{ status: string }> {
    return await this.request(`/alerts/alerts/${id}/resolve/`, {
      method: 'POST',
    });
  }

  async investigateAlert(id: number): Promise<{ status: string }> {
    return await this.request(`/alerts/alerts/${id}/investigate/`, {
      method: 'POST',
    });
  }

  async getActiveAlerts(): Promise<any[]> {
    return await this.request('/alerts/alerts/active/');
  }

  async getAlertSummary(domainId?: number): Promise<{
    total: number;
    active: number;
    high_priority: number;
    investigating: number;
    resolved_today: number;
  }> {
    const queryParams = new URLSearchParams();
    if (domainId) queryParams.append('domain_id', domainId.toString());
    
    const queryString = queryParams.toString();
    return await this.request(`/alerts/alerts/summary/${queryString ? `?${queryString}` : ''}`);
  }

  // Alert Rules
  async getAlertRules(params?: { domain_id?: number }): Promise<any[]> {
    const queryParams = new URLSearchParams();
    if (params?.domain_id) queryParams.append('domain_id', params.domain_id.toString());
    
    const queryString = queryParams.toString();
    return await this.request(`/alerts/alert-rules/${queryString ? `?${queryString}` : ''}`);
  }

  async createAlertRule(data: {
    domain: number;
    name: string;
    description: string;
    enabled: boolean;
    conditions: any;
    notification_channels: string[];
  }): Promise<any> {
    return await this.request('/alerts/alert-rules/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateAlertRule(id: number, data: any): Promise<any> {
    return await this.request(`/alerts/alert-rules/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async toggleAlertRule(id: number): Promise<{ enabled: boolean }> {
    return await this.request(`/alerts/alert-rules/${id}/toggle/`, {
      method: 'POST',
    });
  }

  // ==================== COMPETITORS API ====================
  
  async getCompetitors(params?: { domain_id?: number }): Promise<any[]> {
    const queryParams = new URLSearchParams();
    if (params?.domain_id) queryParams.append('domain_id', params.domain_id.toString());
    
    const queryString = queryParams.toString();
    return await this.request(`/competitors/competitors/${queryString ? `?${queryString}` : ''}`);
  }

  async getCompetitorsByDomain(domainId: number): Promise<any[]> {
    return await this.request(`/competitors/competitors/by_domain/?domain_id=${domainId}`);
  }

  async getCompetitor(id: number): Promise<any> {
    return await this.request(`/competitors/competitors/${id}/`);
  }

  async createCompetitor(data: {
    domain: number;
    name: string;
    url: string;
    mentions?: number;
    visibility_score?: number;
    sentiment?: number;
  }): Promise<any> {
    return await this.request('/competitors/competitors/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateCompetitor(id: number, data: any): Promise<any> {
    return await this.request(`/competitors/competitors/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteCompetitor(id: number): Promise<void> {
    return await this.request(`/competitors/competitors/${id}/`, {
      method: 'DELETE',
    });
  }

  async getCompetitorComparison(domainId: number): Promise<{
    competitors: any[];
    summary: {
      total_competitors: number;
      avg_mentions: number;
      total_market_mentions: number;
    };
  }> {
    return await this.request(`/competitors/competitors/comparison/?domain_id=${domainId}`);
  }

  // Competitor Analytics
  async getCompetitorAnalytics(params?: {
    competitor_id?: number;
    days?: number;
  }): Promise<any[]> {
    const queryParams = new URLSearchParams();
    if (params?.competitor_id) queryParams.append('competitor_id', params.competitor_id.toString());
    if (params?.days) queryParams.append('days', params.days.toString());
    
    const queryString = queryParams.toString();
    return await this.request(`/competitors/competitor-analytics/${queryString ? `?${queryString}` : ''}`);
  }

  async getCompetitorTrends(competitorId: number, days: number = 30): Promise<any[]> {
    return await this.request(`/competitors/competitor-analytics/trends/?competitor_id=${competitorId}&days=${days}`);
  }

  // Competitor Prompts
  async getCompetitorPrompts(competitorId?: number): Promise<any[]> {
    const queryParams = new URLSearchParams();
    if (competitorId) queryParams.append('competitor_id', competitorId.toString());
    
    const queryString = queryParams.toString();
    return await this.request(`/competitors/competitor-prompts/${queryString ? `?${queryString}` : ''}`);
  }

  async getAnswerGaps(domainId: number): Promise<any[]> {
    return await this.request(`/competitors/competitor-prompts/answer_gaps/?domain_id=${domainId}`);
  }

  // ==================== TOPICS API ====================
  
  async getTopics(params?: { domain_id?: number }): Promise<any[]> {
    const queryParams = new URLSearchParams();
    if (params?.domain_id) queryParams.append('domain_id', params.domain_id.toString());
    
    const queryString = queryParams.toString();
    return await this.request(`/topics/topics/${queryString ? `?${queryString}` : ''}`);
  }

  async getTopicsByDomain(domainId: number): Promise<any[]> {
    return await this.request(`/topics/topics/by_domain/?domain_id=${domainId}`);
  }

  async getTopic(id: number): Promise<any> {
    return await this.request(`/topics/topics/${id}/`);
  }

  async createTopic(data: {
    domain: number;
    name: string;
    keywords: string[];
    platforms?: string[];
  }): Promise<any> {
    return await this.request('/topics/topics/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateTopic(id: number, data: any): Promise<any> {
    return await this.request(`/topics/topics/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteTopic(id: number): Promise<void> {
    return await this.request(`/topics/topics/${id}/`, {
      method: 'DELETE',
    });
  }

  async getTrendingTopics(domainId?: number): Promise<any[]> {
    const queryParams = new URLSearchParams();
    if (domainId) queryParams.append('domain_id', domainId.toString());
    
    const queryString = queryParams.toString();
    return await this.request(`/topics/topics/trending/${queryString ? `?${queryString}` : ''}`);
  }

  // Topic Analytics
  async getTopicAnalytics(params?: {
    topic_id?: number;
    days?: number;
  }): Promise<any[]> {
    const queryParams = new URLSearchParams();
    if (params?.topic_id) queryParams.append('topic_id', params.topic_id.toString());
    if (params?.days) queryParams.append('days', params.days.toString());
    
    const queryString = queryParams.toString();
    return await this.request(`/topics/topic-analytics/${queryString ? `?${queryString}` : ''}`);
  }

  async getTopicTrends(topicId: number, days: number = 30): Promise<any[]> {
    return await this.request(`/topics/topic-analytics/trends/?topic_id=${topicId}&days=${days}`);
  }

  // Topic Prompts
  async getTopicPrompts(topicId?: number): Promise<any[]> {
    const queryParams = new URLSearchParams();
    if (topicId) queryParams.append('topic_id', topicId.toString());
    
    const queryString = queryParams.toString();
    return await this.request(`/topics/topic-prompts/${queryString ? `?${queryString}` : ''}`);
  }

  async getHighRelevancePrompts(params?: {
    topic_id?: number;
    min_score?: number;
  }): Promise<any[]> {
    const queryParams = new URLSearchParams();
    if (params?.topic_id) queryParams.append('topic_id', params.topic_id.toString());
    if (params?.min_score) queryParams.append('min_score', params.min_score.toString());
    
    const queryString = queryParams.toString();
    return await this.request(`/topics/topic-prompts/high_relevance/${queryString ? `?${queryString}` : ''}`);
  }

  // ==================== ANALYTICS API ====================
  
  // Sentiment Analytics
  async getSentimentAnalytics(params?: {
    domain_id?: number;
    days?: number;
  }): Promise<any[]> {
    const queryParams = new URLSearchParams();
    if (params?.domain_id) queryParams.append('domain_id', params.domain_id.toString());
    if (params?.days) queryParams.append('days', params.days.toString());
    
    const queryString = queryParams.toString();
    return await this.request(`/analytics/sentiment-analytics/${queryString ? `?${queryString}` : ''}`);
  }

  async getSentimentByDomain(domainId: number, days: number = 30): Promise<any[]> {
    return await this.request(`/analytics/sentiment-analytics/by_domain/?domain_id=${domainId}&days=${days}`);
  }

  async getSentimentSummary(domainId: number, days: number = 7): Promise<{
    positive_percentage: number;
    neutral_percentage: number;
    negative_percentage: number;
    total_mentions: number;
    themes: any[];
  }> {
    return await this.request(`/analytics/sentiment-analytics/summary/?domain_id=${domainId}&days=${days}`);
  }

  // Share of Voice Analytics
  async getShareOfVoice(params?: {
    domain_id?: number;
    days?: number;
    platform?: string;
  }): Promise<any[]> {
    const queryParams = new URLSearchParams();
    if (params?.domain_id) queryParams.append('domain_id', params.domain_id.toString());
    if (params?.days) queryParams.append('days', params.days.toString());
    if (params?.platform) queryParams.append('platform', params.platform);
    
    const queryString = queryParams.toString();
    return await this.request(`/analytics/share-of-voice/${queryString ? `?${queryString}` : ''}`);
  }

  async getShareOfVoiceByDomain(domainId: number, params?: {
    days?: number;
    platform?: string;
  }): Promise<any[]> {
    const queryParams = new URLSearchParams();
    queryParams.append('domain_id', domainId.toString());
    if (params?.days) queryParams.append('days', params.days.toString());
    if (params?.platform) queryParams.append('platform', params.platform);
    
    const queryString = queryParams.toString();
    return await this.request(`/analytics/share-of-voice/by_domain/?${queryString}`);
  }

  async getShareOfVoiceComparison(domainId: number, params?: {
    date?: string;
    platform?: string;
  }): Promise<{
    your_brand: any;
    competitors: any[];
    total_market_mentions: number;
  }> {
    const queryParams = new URLSearchParams();
    queryParams.append('domain_id', domainId.toString());
    if (params?.date) queryParams.append('date', params.date);
    if (params?.platform) queryParams.append('platform', params.platform);
    
    const queryString = queryParams.toString();
    return await this.request(`/analytics/share-of-voice/comparison/?${queryString}`);
  }

  // ==================== INTEGRATIONS API ====================
  
  async getIntegrations(params?: { domain_id?: number }): Promise<any[]> {
    const queryParams = new URLSearchParams();
    if (params?.domain_id) queryParams.append('domain_id', params.domain_id.toString());
    
    const queryString = queryParams.toString();
    return await this.request(`/integrations/integrations/${queryString ? `?${queryString}` : ''}`);
  }

  async getIntegrationsByDomain(domainId: number): Promise<any[]> {
    return await this.request(`/integrations/integrations/by_domain/?domain_id=${domainId}`);
  }

  async getIntegration(id: number): Promise<any> {
    return await this.request(`/integrations/integrations/${id}/`);
  }

  async createIntegration(data: {
    domain: number;
    type: 'google_analytics' | 'search_console' | 'slack' | 'sms' | 'cms';
    provider_id: string;
    credentials: any;
  }): Promise<any> {
    return await this.request('/integrations/integrations/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateIntegration(id: number, data: any): Promise<any> {
    return await this.request(`/integrations/integrations/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteIntegration(id: number): Promise<void> {
    return await this.request(`/integrations/integrations/${id}/`, {
      method: 'DELETE',
    });
  }

  async testIntegration(id: number): Promise<{ status: string; message: string }> {
    return await this.request(`/integrations/integrations/${id}/test_connection/`, {
      method: 'POST',
    });
  }

  async disconnectIntegration(id: number): Promise<{ status: string; message: string }> {
    return await this.request(`/integrations/integrations/${id}/disconnect/`, {
      method: 'POST',
    });
  }

  async syncIntegration(id: number): Promise<{ status: string; last_sync_at: string }> {
    return await this.request(`/integrations/integrations/${id}/sync/`, {
      method: 'POST',
    });
  }

  async getIntegrationStatusSummary(domainId?: number): Promise<{
    total: number;
    active: number;
    error: number;
    disconnected: number;
  }> {
    const queryParams = new URLSearchParams();
    if (domainId) queryParams.append('domain_id', domainId.toString());
    
    const queryString = queryParams.toString();
    return await this.request(`/integrations/integrations/status_summary/${queryString ? `?${queryString}` : ''}`);
  }
}

// Create and export the API client instance
export const apiClient = new ApiClient(API_BASE_URL);

// Export the class for testing purposes
export { ApiClient };
