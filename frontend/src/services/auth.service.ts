/**
 * Authentication Service
 * Handles login, logout, profile management, and team management
 */

import { apiClient } from './api';

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user: User;
}

export interface User {
  id: number;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  role: 'super_admin' | 'admin' | 'user';
  organisation: number;
  is_active: boolean;
}

export interface ProfileUpdateData {
  first_name?: string;
  last_name?: string;
  username?: string;
}

export interface InvitationData {
  email: string;
  role: 'admin' | 'user' | 'client';
  organisation?: number;
  /** Required when role is 'client': the single domain the client is scoped to. */
  domain?: number;
  message?: string;
}

export interface Permission {
  id: number;
  user: number;
  module: string;
  granted_by: number;
  created_at: string;
}

export const authService = {
  /**
   * Login user
   */
  login: async (credentials: LoginCredentials): Promise<LoginResponse> => {
    const response = await apiClient.post<LoginResponse>(
      '/auth/login/',
      credentials,
      { skipAuth: true }
    );
    
    // Store tokens
    localStorage.setItem('access_token', response.access);
    localStorage.setItem('refresh_token', response.refresh);
    localStorage.setItem('user', JSON.stringify(response.user));
    
    return response;
  },

  /**
   * Logout user
   */
  logout: async (): Promise<void> => {
    await apiClient.post('/auth/logout/');
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
  },

  /**
   * Get current user profile
   */
  getProfile: (): Promise<User> => {
    return apiClient.get<User>('/auth/profile/');
  },

  /**
   * Update user profile
   */
  updateProfile: (data: ProfileUpdateData): Promise<User> => {
    return apiClient.put<User>('/auth/profile/update/', data);
  },

  /**
   * Send team invitation
   */
  sendInvitation: (data: InvitationData): Promise<any> => {
    return apiClient.post('/auth/invite/', data);
  },

  /**
   * Get invitation details
   */
  getInvitation: (invitationId: string): Promise<any> => {
    return apiClient.get(`/auth/invitation/${invitationId}/`);
  },

  /**
   * Accept invitation
   */
  acceptInvitation: (invitationId: string, data: {
    username: string;
    password: string;
    first_name: string;
    last_name: string;
  }): Promise<any> => {
    return apiClient.post(`/auth/accept-invitation/${invitationId}/`, data);
  },

  /**
   * Get team members
   */
  getTeamMembers: (): Promise<User[]> => {
    return apiClient.get<User[]>('/auth/team-members/');
  },

  /**
   * Get user permissions
   */
  getUserPermissions: (userId: number): Promise<Permission[]> => {
    return apiClient.get<Permission[]>(`/auth/permissions/user/${userId}/`);
  },

  /**
   * Assign permission to user
   */
  assignPermission: (userId: number, module: string): Promise<Permission> => {
    return apiClient.post<Permission>('/auth/permissions/assign/', {
      user_id: userId,
      module
    });
  },

  /**
   * Remove permission
   */
  removePermission: (permissionId: number): Promise<void> => {
    return apiClient.delete(`/auth/permissions/${permissionId}/delete/`);
  },

  /**
   * Grant all permissions to user
   */
  grantAllPermissions: (userId: number): Promise<any> => {
    return apiClient.post(`/auth/permissions/user/${userId}/grant-all/`);
  },

  /**
   * Revoke all permissions from user
   */
  revokeAllPermissions: (userId: number): Promise<any> => {
    return apiClient.post(`/auth/permissions/user/${userId}/revoke-all/`);
  },

  /**
   * Get available modules
   */
  getAvailableModules: (): Promise<string[]> => {
    return apiClient.get<string[]>('/auth/permissions/modules/');
  },

  /**
   * Forgot password
   */
  forgotPassword: (email: string): Promise<any> => {
    return apiClient.post('/auth/forgot-password/', { email }, { skipAuth: true });
  },

  /**
   * Reset password
   */
  resetPassword: (token: string, password: string): Promise<any> => {
    return apiClient.post('/auth/reset-password/', { token, password }, { skipAuth: true });
  },
};

export default authService;

