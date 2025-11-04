# Authentication Integration - LLM Monitor Frontend

This document describes the authentication integration between the React frontend and Django backend for the LLM Monitor application.

## 🏗️ Architecture Overview

The authentication system uses JWT tokens for secure communication between the frontend and backend:

- **Frontend**: React with TypeScript, using Context API for state management
- **Backend**: Django with JWT authentication
- **Token Storage**: localStorage for persistence across browser sessions
- **Permission System**: Role-based access control with module-specific permissions

## 📁 File Structure

```
src/
├── types/
│   └── auth.ts                 # TypeScript interfaces for auth
├── services/
│   └── api.ts                  # API client for backend communication
├── contexts/
│   └── AuthContext.tsx         # React context for auth state
├── pages/
│   └── Auth.tsx                # Login page component
├── config/
│   └── environment.ts          # Environment configuration
└── App.tsx                     # Main app with protected routes
```

## 🔧 Configuration

### Environment Variables

Create a `.env.local` file in the frontend root directory:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_ENABLE_DEBUG=true
VITE_ENABLE_ANALYTICS=false
```

### Backend API Endpoints

The frontend expects these Django endpoints:

- `POST /auth/login/` - User login
- `POST /auth/logout/` - User logout
- `POST /auth/token/refresh/` - Refresh JWT token
- `GET /auth/profile/` - Get user profile and permissions
- `PUT /auth/profile/update/` - Update user profile
- `GET /auth/permissions/check/` - Check user permissions

## 🚀 Usage

### 1. Authentication Context

Wrap your app with the `AuthProvider`:

```tsx
import { AuthProvider } from '@/contexts/AuthContext';

function App() {
  return (
    <AuthProvider>
      {/* Your app components */}
    </AuthProvider>
  );
}
```

### 2. Using Authentication

```tsx
import { useAuth } from '@/contexts/AuthContext';

function MyComponent() {
  const { user, isAuthenticated, login, logout, checkPermission } = useAuth();

  // Check if user has permission for a module
  const canAccessReports = checkPermission('reports', 'read');
  
  // Check if user has admin access
  const isAdmin = user?.role === 'admin';
}
```

### 3. Protected Routes

```tsx
import { ProtectedRoute } from '@/contexts/AuthContext';

function App() {
  return (
    <Routes>
      <Route path="/signin" element={<SignIn />} />
      <Route element={<Layout />}>
        <Route path="/reports" element={
          <ProtectedRoute requiredPermission="reports" requiredLevel="read">
            <Reports />
          </ProtectedRoute>
        } />
        <Route path="/admin" element={
          <ProtectedRoute requiredPermission="organization_settings" requiredLevel="admin">
            <AdminPanel />
          </ProtectedRoute>
        } />
      </Route>
    </Routes>
  );
}
```

## 🔐 Permission System

### Available Modules

The system supports these modules (matching the backend):

- `dashboard` - Dashboard
- `mentions` - Mentions tracking
- `prompts` - Prompts management
- `alerts` - Alert system
- `sentiment_analysis` - Sentiment analysis
- `topics` - Topics management
- `share_of_voice` - Share of voice analytics
- `historical_trends` - Historical trends
- `content_gaps` - Content gap analysis
- `competitors` - Competitor tracking
- `multilingual` - Multilingual support
- `ai_copilot` - AI Copilot features
- `prompt_insights` - Prompt insights
- `agent_analytics` - Agent analytics
- `ai_crawler` - AI Crawler
- `traffic_attribution` - Traffic attribution
- `misinformation_alerts` - Misinformation alerts
- `reports` - Reports generation
- `organization_settings` - Organization settings
- `team_management` - Team management

### Permission Levels

- `read` - View-only access
- `write` - Create and edit access
- `admin` - Full administrative access

## 🔄 Token Management

### Automatic Token Refresh

The system automatically handles token refresh:

1. **Token Validation**: On app load, validates stored tokens
2. **Automatic Refresh**: Refreshes tokens before expiry
3. **Fallback Logout**: Logs out user if refresh fails

### Token Storage

- **Access Token**: Stored in localStorage, used for API requests
- **Refresh Token**: Stored in localStorage, used for token renewal
- **Automatic Cleanup**: Tokens are cleared on logout or expiry

## 🛡️ Security Features

### Request Interceptors

- **Authorization Headers**: Automatically adds Bearer tokens to requests
- **Error Handling**: Handles 401/403 responses gracefully
- **Timeout Protection**: Prevents hanging requests

### Permission Checking

- **Route Protection**: Prevents unauthorized access to pages
- **Component-Level**: Fine-grained permission checking in components
- **Real-time Updates**: Permissions update when user profile changes

## 🧪 Testing

### Mock Authentication

For testing, you can mock the authentication context:

```tsx
// In your test file
import { AuthProvider } from '@/contexts/AuthContext';

const mockAuthValue = {
  user: { id: 1, email: 'test@example.com', role: 'admin' },
  isAuthenticated: true,
  checkPermission: () => true,
  // ... other auth methods
};

function TestWrapper({ children }) {
  return (
    <AuthContext.Provider value={mockAuthValue}>
      {children}
    </AuthContext.Provider>
  );
}
```

## 🚨 Error Handling

### Common Error Scenarios

1. **Network Errors**: Handled with user-friendly messages
2. **Token Expiry**: Automatic refresh or redirect to login
3. **Permission Denied**: Clear access denied messages
4. **Server Errors**: Graceful degradation with retry options

### Error Messages

The system provides clear error messages for:
- Invalid credentials
- Network connectivity issues
- Permission denied access
- Session expiry

## 🔧 Development

### Running the Development Server

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Make sure backend is running on http://localhost:8000
```

### Debugging

Enable debug mode by setting `VITE_ENABLE_DEBUG=true` in your environment file.

## 📝 API Integration

The `apiClient` provides methods for all authentication operations:

```tsx
import { apiClient } from '@/services/api';

// Login
const response = await apiClient.login({ email, password });

// Get profile
const profile = await apiClient.getProfile();

// Check permissions
const permissions = await apiClient.checkPermissions('reports');

// Update profile
await apiClient.updateProfile({ first_name: 'John' });
```

## 🎯 Next Steps

1. **Environment Setup**: Configure your `.env.local` file
2. **Backend Integration**: Ensure Django backend is running
3. **User Testing**: Test login/logout flows
4. **Permission Testing**: Verify permission-based access control
5. **Error Handling**: Test error scenarios

## 📞 Support

For issues with the authentication integration:

1. Check browser console for errors
2. Verify backend API endpoints are accessible
3. Check environment configuration
4. Review network requests in browser dev tools

