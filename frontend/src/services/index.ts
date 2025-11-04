/**
 * Service Index - All API Services
 * Export all service modules for easy import
 */

export { apiClient, api } from './api';
export { default } from './api';
export { authService } from './auth.service';

// Re-export types
export type {
  LoginCredentials,
  LoginResponse,
  User,
  ProfileUpdateData,
  InvitationData,
  Permission,
} from './auth.service';

