import React, { createContext, useContext, useReducer, useEffect, ReactNode } from 'react';
import { AuthState, User, Permission, LoginRequest } from '@/types/auth';
import { apiClient } from '@/services/api';

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
        } catch (error) {
          // Token is invalid, try to refresh
          try {
            const refreshResponse = await apiClient.refreshToken();
            const profile = await apiClient.getProfile();
            dispatch({
              type: 'LOGIN_SUCCESS',
              payload: {
                user: profile.user,
                permissions: profile.permissions,
                accessToken: refreshResponse.access,
                refreshToken,
              },
            });
          } catch (refreshError) {
            // Both tokens are invalid, clear them
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            dispatch({ type: 'LOGIN_FAILURE', payload: 'Session expired' });
          }
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
    } catch (error) {
      dispatch({ type: 'LOGIN_FAILURE', payload: error instanceof Error ? error.message : 'Login failed' });
      throw error;
    }
  };

  // Logout function
  const logout = async (): Promise<void> => {
    try {
      await apiClient.logout();
    } catch (error) {
      console.warn('Logout error:', error);
    } finally {
      dispatch({ type: 'LOGOUT' });
    }
  };

  // Refresh auth function
  const refreshAuth = async (): Promise<void> => {
    try {
      const refreshResponse = await apiClient.refreshToken();
      const profile = await apiClient.getProfile();
      dispatch({
        type: 'LOGIN_SUCCESS',
        payload: {
          user: profile.user,
          permissions: profile.permissions,
          accessToken: refreshResponse.access,
          refreshToken: localStorage.getItem('refresh_token') || '',
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
      dispatch({ type: 'UPDATE_USER', payload: response.user });
    } catch (error) {
      throw error;
    }
  };

  // Permission checking functions
  const checkPermission = (module: string, requiredLevel: 'read' | 'write' | 'admin' = 'read'): boolean => {
    const permission = state.permissions.find(p => p.module === module);
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
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    return <div>Please log in to access this page</div>;
  }

  if (requiredPermission && !checkPermission(requiredPermission, requiredLevel)) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}

