import React, { createContext, useContext, useReducer, useEffect, ReactNode } from 'react';
import { AuthState, User, Permission, LoginRequest } from '@/types/auth';
import { apiClient } from '@/services/api';
import { PageLoader } from '@/components/PageLoader';
import {
  loadActiveDomain,
  saveActiveDomain,
  loadActiveDomainFromServer,
  updateActiveDomain,
  clearAllActiveDomainStorage
} from '@/utils/activeDomain';

// Auth Actions
type AuthAction =
  | { type: 'LOGIN_START' }
  | { type: 'LOGIN_SUCCESS'; payload: { user: User; permissions: Permission[]; accessToken: string; refreshToken: string } }
  | { type: 'LOGIN_FAILURE'; payload: string }
  | { type: 'LOGOUT' }
  | { type: 'UPDATE_USER'; payload: User }
  | { type: 'UPDATE_PERMISSIONS'; payload: Permission[] }
  | { type: 'SET_LOADING'; payload: boolean };

// Initial state
const initialState: AuthState = {
  user: null,
  permissions: [],
  accessToken: null,
  refreshToken: null,
  isAuthenticated: false,
  isLoading: true,
};

// Auth reducer
function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case 'LOGIN_START':
      return {
        ...state,
        isLoading: true,
      };
    case 'LOGIN_SUCCESS':
      return {
        ...state,
        user: action.payload.user,
        permissions: action.payload.permissions,
        accessToken: action.payload.accessToken,
        refreshToken: action.payload.refreshToken,
        isAuthenticated: true,
        isLoading: false,
      };
    case 'LOGIN_FAILURE':
      return {
        ...state,
        user: null,
        permissions: [],
        accessToken: null,
        refreshToken: null,
        isAuthenticated: false,
        isLoading: false,
      };
    case 'LOGOUT':
      return {
        ...state,
        user: null,
        permissions: [],
        accessToken: null,
        refreshToken: null,
        isAuthenticated: false,
        isLoading: false,
      };
    case 'UPDATE_USER':
      return {
        ...state,
        user: action.payload,
      };
    case 'UPDATE_PERMISSIONS':
      return {
        ...state,
        permissions: action.payload,
      };
    case 'SET_LOADING':
      return {
        ...state,
        isLoading: action.payload,
      };
    default:
      return state;
  }
}

// Auth Context
interface AuthContextType extends AuthState {
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  refreshAuth: () => Promise<void>;
  updateProfile: (data: Partial<User>) => Promise<void>;
  checkPermission: (module: string, requiredLevel?: 'read' | 'write' | 'admin') => boolean;
  hasAnyPermission: (modules: string[]) => boolean;
  hasAllPermissions: (modules: string[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Auth Provider
interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // Initialize auth state from localStorage
  useEffect(() => {
    const initializeAuth = async () => {
      const accessToken = localStorage.getItem('access_token');
      const refreshToken = localStorage.getItem('refresh_token');

      if (accessToken && refreshToken) {
        try {
          // Try to get user profile to validate token
          const profile = await apiClient.getProfile();
          dispatch({
            type: 'LOGIN_SUCCESS',
            payload: {
              user: profile.user,
              permissions: profile.permissions,
              accessToken,
              refreshToken,
            },
          });

          // Sync active domain from server (primary source of truth)
          const serverActiveDomain = await loadActiveDomainFromServer(profile.user.id);
          
          // If server has no active domain (null or undefined), set first available domain
          if (!serverActiveDomain || serverActiveDomain === null || serverActiveDomain === '') {
            console.log(`[AuthContext] No active domain found for user ${profile.user.id}, setting first available domain`);
            try {
              const response = await apiClient.getDomains();
              const domains = response?.domains || [];
              console.log(`[AuthContext] Fetched ${domains?.length || 0} domains for user ${profile.user.id}`);
              
              if (Array.isArray(domains) && domains.length > 0) {
                const firstDomain = domains[0];
                const domainId = firstDomain?.id;
                
                if (domainId && typeof domainId === 'number') {
                  console.log(`[AuthContext] Setting first domain ${domainId} as active for user ${profile.user.id}`);
                  // Update both server and localStorage
                  const success = await updateActiveDomain(profile.user.id, domainId, firstDomain);
                  if (success) {
                    console.log(`[AuthContext] Successfully set active domain ${domainId} for user ${profile.user.id}`);
                  } else {
                    console.warn(`[AuthContext] Failed to set active domain ${domainId} for user ${profile.user.id}`);
                  }
                } else {
                  console.warn(`[AuthContext] No valid domain ID found in first domain:`, firstDomain);
                }
              } else {
                console.warn(`[AuthContext] No domains available for user ${profile.user.id}`);
              }
            } catch (error) {
              console.error(`[AuthContext] Error setting first domain for user ${profile.user.id}:`, error);
            }
          } else {
            console.log(`[AuthContext] Active domain ${serverActiveDomain} already set for user ${profile.user.id}`);
          }
        } catch (error) {
          // Token is invalid, clear it and require re-login
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          dispatch({ type: 'SET_LOADING', payload: false });
        }
      } else {
        dispatch({ type: 'SET_LOADING', payload: false });
      }
    };

    initializeAuth();
  }, []);

  // Login function
  const login = async (credentials: LoginRequest): Promise<void> => {
    try {
      dispatch({ type: 'LOGIN_START' });
      const response = await apiClient.login(credentials);
      dispatch({
        type: 'LOGIN_SUCCESS',
        payload: {
          user: response.user,
          permissions: response.permissions,
          accessToken: response.access,
          refreshToken: response.refresh,
        },
      });

      // Sync active domain from server (primary source of truth)
      const serverActiveDomain = await loadActiveDomainFromServer(response.user.id);
      
      // If server has no active domain (null or undefined), set first available domain
      if (!serverActiveDomain || serverActiveDomain === null || serverActiveDomain === '') {
        console.log(`[AuthContext] No active domain found for user ${response.user.id} after login, setting first available domain`);
        try {
          const domainsResponse = await apiClient.getDomains();
          const domains = domainsResponse?.domains || [];
          console.log(`[AuthContext] Fetched ${domains?.length || 0} domains for user ${response.user.id}`);
          
          if (Array.isArray(domains) && domains.length > 0) {
            const firstDomain = domains[0];
            const domainId = firstDomain?.id;
            
            if (domainId && typeof domainId === 'number') {
              console.log(`[AuthContext] Setting first domain ${domainId} as active for user ${response.user.id}`);
              // Update both server and localStorage
              const success = await updateActiveDomain(response.user.id, domainId, firstDomain);
              if (success) {
                console.log(`[AuthContext] Successfully set active domain ${domainId} for user ${response.user.id}`);
              } else {
                console.warn(`[AuthContext] Failed to set active domain ${domainId} for user ${response.user.id}`);
              }
            } else {
              console.warn(`[AuthContext] No valid domain ID found in first domain:`, firstDomain);
            }
          } else {
            console.warn(`[AuthContext] No domains available for user ${response.user.id}`);
          }
        } catch (error) {
          console.error(`[AuthContext] Error setting first domain for user ${response.user.id}:`, error);
        }
      } else {
        console.log(`[AuthContext] Active domain ${serverActiveDomain} already set for user ${response.user.id}`);
      }
    } catch (error) {
      dispatch({ type: 'LOGIN_FAILURE', payload: error instanceof Error ? error.message : 'Login failed' });
      throw error;
    }
  };

  // Logout function
  const logout = async (): Promise<void> => {
    try {
      // Get user ID before clearing state
      const userId = state.user?.id;
      
      await apiClient.logout();
      
      // Clear all active domain related localStorage values
      if (userId) {
        clearAllActiveDomainStorage(userId);
      }
      
      // Clear domain store from localStorage
      try {
        localStorage.removeItem('domain-store');
        console.log('[AuthContext] Cleared domain-store from localStorage');
      } catch (error) {
        console.warn('[AuthContext] Error clearing domain-store:', error);
      }
      
      // Clear auth tokens
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      
      console.log('[AuthContext] Cleared all localStorage values on logout');
    } catch (error) {
      console.warn('Logout error:', error);
    } finally {
      dispatch({ type: 'LOGOUT' });
    }
  };

  // Refresh auth function (simplified - just re-fetch profile)
  const refreshAuth = async (): Promise<void> => {
    try {
      const profile = await apiClient.getProfile();
      const accessToken = localStorage.getItem('access_token') || '';
      const refreshToken = localStorage.getItem('refresh_token') || '';
      dispatch({
        type: 'LOGIN_SUCCESS',
        payload: {
          user: profile.user,
          permissions: profile.permissions,
          accessToken,
          refreshToken,
        },
      });
    } catch (error) {
      dispatch({ type: 'LOGOUT' });
      throw error;
    }
  };

  // Update profile function
  const updateProfile = async (data: Partial<User>): Promise<void> => {
    try {
      const response = await apiClient.updateProfile(data);
      // Backend returns the user object directly or wrapped in { user: ... }
      const updatedUser = response.user || response;
      dispatch({ type: 'UPDATE_USER', payload: updatedUser });
    } catch (error) {
      throw error;
    }
  };

  // Permission checking functions
  const checkPermission = (module: string, requiredLevel: 'read' | 'write' | 'admin' = 'read'): boolean => {
    const permission = state.permissions.find(p => p.module === module);

    // Super admin shortcut: full access
    if (state.user?.role === 'super_admin') {
      return true;
    }

    // Organization settings default for admin: allow unless explicitly restricted
    if (module === 'organization_settings' && state.user?.role === 'admin') {
      if (!permission) {
        return true;
      }
      // fall through to normal level check when explicit permission exists
    }

    if (!permission) return false;

    const levelHierarchy = { read: 1, write: 2, admin: 3 };
    const userLevel = levelHierarchy[permission.permission_level as keyof typeof levelHierarchy];
    const requiredLevelValue = levelHierarchy[requiredLevel];

    return userLevel >= requiredLevelValue;
  };

  const hasAnyPermission = (modules: string[]): boolean => {
    return modules.some(module => checkPermission(module));
  };

  const hasAllPermissions = (modules: string[]): boolean => {
    return modules.every(module => checkPermission(module));
  };

  const contextValue: AuthContextType = {
    ...state,
    login,
    logout,
    refreshAuth,
    updateProfile,
    checkPermission,
    hasAnyPermission,
    hasAllPermissions,
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
}

// Custom hook to use auth context
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

// Higher-order component for protected routes
interface ProtectedRouteProps {
  children: ReactNode;
  requiredPermission?: string;
  requiredLevel?: 'read' | 'write' | 'admin';
  fallback?: ReactNode;
}

export function ProtectedRoute({ 
  children, 
  requiredPermission, 
  requiredLevel = 'read',
  fallback = <div>Access denied</div>
}: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, checkPermission } = useAuth();

  if (isLoading) {
    return <PageLoader />;
  }

  if (!isAuthenticated) {
    return <div>Please log in to access this page</div>;
  }

  if (requiredPermission && !checkPermission(requiredPermission, requiredLevel)) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}

