import React, { createContext, useContext, useReducer, useEffect, ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
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
import { useDomainStore } from '@/stores/domainStore';

// Auth Actions
type AuthAction =
  | { type: 'LOGIN_START' }
  | { type: 'LOGIN_SUCCESS'; payload: { user: User; permissions: Permission[]; accessToken: string; refreshToken: string } }
  | { type: 'LOGIN_FAILURE'; payload: string }
  | { type: 'LOGOUT' }
  | { type: 'UPDATE_USER'; payload: User }
  | { type: 'UPDATE_PERMISSIONS'; payload: Permission[] }
  | { type: 'SET_LOADING'; payload: boolean }
  // This browser had a session and no longer does, so the guard can say
  // "expired" instead of greeting a first-time visitor with it.
  | { type: 'SESSION_ENDED' };

// Action rights that sit under a parent module rather than granting page
// access of their own. Kept in sync with UserPermission.MODULE_CHOICES.
const ACTION_MODULES = [
  'prompts_add',
  'prompts_edit',
  'prompts_delete',
  'keywords_add',
  'keywords_edit',
  'keywords_delete',
];

// Initial state
const initialState: AuthState = {
  user: null,
  permissions: [],
  accessToken: null,
  refreshToken: null,
  isAuthenticated: false,
  isLoading: true,
  sessionEnded: false,
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
        // From here on, losing auth means it expired rather than never existed.
        sessionEnded: true,
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
        // Signing out on purpose is not an expiry. Without this reset, logging
        // out and then opening any app link showed "your session has timed out
        // for security reasons" to someone who simply clicked Log out.
        sessionEnded: false,
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
    case 'SESSION_ENDED':
      return {
        ...state,
        sessionEnded: true,
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

          // Clear cached domains if they belong to a different organization
          // This prevents stale domains showing after account switch
          const domainStore = useDomainStore.getState();
          const cachedDomains = domainStore.domains;
          if (cachedDomains.length > 0 && profile.user?.organisation) {
            const hasMismatch = cachedDomains.some(
              (d: any) => d.organisation !== profile.user.organisation
            );
            if (hasMismatch) {
              domainStore.clearDomainStore();
              localStorage.removeItem('domain-store');
            }
          }

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
            try {
              const response = await apiClient.getDomains();
              const domains = response?.domains || [];

              if (Array.isArray(domains) && domains.length > 0) {
                const firstDomain = domains[0];
                const domainId = firstDomain?.id;

                if (domainId && typeof domainId === 'number') {
                  // Update both server and localStorage
                  await updateActiveDomain(profile.user.id, domainId, firstDomain);
                }
              }
            } catch (error) {
              // Silently ignore errors
            }
          }
        } catch (error) {
          // Token is invalid, clear it and require re-login. This browser DID
          // hold a session, so this is a genuine expiry and the guard should
          // say so.
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          dispatch({ type: 'SESSION_ENDED' });
          dispatch({ type: 'SET_LOADING', payload: false });
        }
      } else {
        // No tokens at all: nobody has signed in on this browser. A first-time
        // visitor lands here, and must be sent to sign-in — not told that a
        // session they never had has timed out.
        dispatch({ type: 'SET_LOADING', payload: false });
      }
    };

    initializeAuth();
  }, []);

  // Login function
  const login = async (credentials: LoginRequest): Promise<void> => {
    try {
      dispatch({ type: 'LOGIN_START' });

      // Clear stale domain data from previous account/session immediately
      // This prevents showing another account's domains after switching accounts
      useDomainStore.getState().clearDomainStore();
      localStorage.removeItem('domain-store');

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
        try {
          const domainsResponse = await apiClient.getDomains();
          const domains = domainsResponse?.domains || [];

          if (Array.isArray(domains) && domains.length > 0) {
            const firstDomain = domains[0];
            const domainId = firstDomain?.id;

            if (domainId && typeof domainId === 'number') {
              // Update both server and localStorage
              await updateActiveDomain(response.user.id, domainId, firstDomain);
            }
          }
        } catch (error) {
          // Silently ignore errors
        }
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
      } catch (error) {
        // Silently ignore errors
      }

      // Clear auth tokens
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    } catch (error) {
      // Silently ignore logout errors
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

    // Fine-grained action rights (add/edit/delete prompts and keywords).
    // Mirrors core/permissions.user_has_module_permission on the backend:
    // admins hold these by role and never carry an explicit grant, clients
    // never hold them at all. Everyone else needs the row.
    if (ACTION_MODULES.includes(module)) {
      if (state.user?.role === 'admin') return true;
      if (state.user?.role === 'client') return false;
      return !!permission;
    }

    // Client: read-only access to data modules, never admin modules.
    // Backend domain-scoping is the real boundary; this only shapes the UI.
    if (state.user?.role === 'client') {
      const CLIENT_ADMIN_MODULES = ['organization_settings', 'team_management'];
      if (CLIENT_ADMIN_MODULES.includes(module)) return false;
      return requiredLevel === 'read';
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
  /** Restrict to specific roles, e.g. ['super_admin']. Checked in addition to
   *  any permission gate, so a page can be role-only without inventing a
   *  permission module for it. */
  requiredRoles?: string[];
  fallback?: ReactNode;
}

export function ProtectedRoute({ 
  children, 
  requiredPermission, 
  requiredLevel = 'read',
  requiredRoles,
  fallback = <div>Access denied</div>
}: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, checkPermission, user, sessionEnded } = useAuth();

  if (isLoading) {
    return <PageLoader />;
  }

  if (!isAuthenticated) {
    // "Not signed in" has two causes and they need different answers. Someone
    // whose session ran out gets told that; a first-time visitor — who reaches
    // this guard just by opening the app link before signing in — gets the
    // sign-in page, not "your session has timed out for security reasons"
    // about a session they never had.
    return <Navigate to={sessionEnded ? '/session-expired' : '/signin'} replace />;
  }

  if (requiredRoles && !requiredRoles.includes(user?.role ?? '')) {
    return <>{fallback}</>;
  }

  if (requiredPermission && !checkPermission(requiredPermission, requiredLevel)) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}

