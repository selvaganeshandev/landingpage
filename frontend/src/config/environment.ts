// Environment configuration for the LLM Monitor frontend
// This file should be copied to .env.local for local development

export const config = {
  // API Configuration
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  
  // App Configuration
  APP_NAME: 'PromptMaxx',
  APP_DESCRIPTION: 'AI Visibility & Content Strategy Platform',
  
  // Feature Flags
  ENABLE_DEBUG: import.meta.env.VITE_ENABLE_DEBUG === 'true',
  ENABLE_ANALYTICS: import.meta.env.VITE_ENABLE_ANALYTICS === 'true',
  
  // Timeouts
  API_TIMEOUT: 10000, // 10 seconds
  REFRESH_TOKEN_THRESHOLD: 300000, // 5 minutes before expiry
};

// Environment variables that should be set:
// VITE_API_BASE_URL=http://localhost:8000
// VITE_ENABLE_DEBUG=true
// VITE_ENABLE_ANALYTICS=false

