# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**AI Visibility Pro** (prompt-reach-insight) - A multi-tenant SaaS application for monitoring brand mentions across AI platforms (ChatGPT, Claude, Gemini, Perplexity, Grok), detecting misinformation, tracking traffic attribution via Google Analytics/Search Console, and generating comprehensive reports.

**Tech Stack:**
- Frontend: React 18 + TypeScript + Vite
- UI: shadcn/ui components + Tailwind CSS + Radix UI primitives
- State: TanStack Query (React Query) for server state
- Routing: React Router v6
- Backend: Supabase (PostgreSQL + Auth + Edge Functions + Storage)
- Hosting: Lovable Cloud

## Development Commands

### Start Development Server
```bash
npm run dev
```
Runs on port 8080 (configured in vite.config.ts)

### Build for Production
```bash
npm run build
```
Creates optimized production build in `dist/`

### Build for Development
```bash
npm run build:dev
```
Builds with development mode flags

### Lint Code
```bash
npm run lint
```
Runs ESLint on the codebase

### Preview Production Build
```bash
npm run preview
```
Serves the production build locally for testing

### Supabase Edge Functions
Edge functions are located in `supabase/functions/`. To work with them locally, you'll need Supabase CLI:
```bash
# Example: Test edge function locally
supabase functions serve generate-prompt-suggestions --env-file .env
```

## Architecture Overview

### Multi-Tenant Data Model
The application uses a hierarchical multi-tenant architecture:

```
Organizations (tenants)
  └─> Domains (websites to track)
       ├─> Integrations (GA/GSC per domain)
       ├─> Mentions (AI platform responses)
       │    └─> Citations (source references)
       └─> Traffic Attribution (analytics data)
```

**Key Architectural Principle:** Row-Level Security (RLS) policies enforce data isolation. Users can only access data from domains belonging to their organization. Admins have additional privileges for managing integrations and team members.

### Authentication & Authorization
- **Supabase Auth** handles authentication (email/password + optional Google OAuth)
- **Team Members:** Users belong to organizations with roles: `admin` or `user`
- **Admins can:** Manage organization settings, configure integrations, add/remove team members, create monitoring rules
- **Users can:** View mentions, analytics, alerts, and reports (read-only on org settings)

### Core Data Flow

**1. AI Mention Tracking:**
- Edge functions call AI platform APIs (OpenAI, Anthropic, Google, Perplexity, X.AI) with test queries
- Parse responses for brand mentions and extract citations
- Store in `mentions` and `citations` tables
- Run misinformation detection by comparing AI responses with original website content (via Firecrawl)

**2. Misinformation Detection:**
- Firecrawl API scrapes original website content cited by AI
- Lovable AI (Gemini 2.5 Flash) performs semantic comparison
- Alerts created if discrepancies found (stored in `misinformation_alerts` table)
- Notifications sent via Resend (email) or Slack webhooks

**3. Traffic Attribution:**
- Daily sync job fetches Google Analytics data (sessions, conversions, revenue)
- Tracks referrers from AI platforms (chat.openai.com, claude.ai, etc.)
- Google Search Console data for search queries
- Data stored in `traffic_attribution` table
- Attribution models: first touch, last touch, linear, time decay

**4. Reports:**
- Edge functions generate PDF reports using HTML templates + Puppeteer
- Types: Executive Summary, Detailed Analytics, Misinformation Report, Traffic Attribution
- Stored in Supabase Storage with expiring download links
- Can be scheduled (weekly/monthly) or generated on-demand

### Frontend Structure

**Routing:** All routes defined in `src/App.tsx` using React Router v6

**Key Pages:**
- `/` - Dashboard (overview metrics)
- `/mentions` - AI mention tracking
- `/misinformation` - Misinformation alerts management
- `/traffic` - Traffic attribution dashboard
- `/competitors` - Competitor comparison
- `/content-calendar` - Content planning calendar
- `/organization-settings` - Org settings, domains, integrations, team management

**Component Organization:**
- `src/components/` - Reusable UI components (dialogs, charts, forms)
- `src/components/ui/` - shadcn/ui base components
- `src/pages/` - Page-level components (one per route)
- `src/integrations/supabase/` - Supabase client and TypeScript types
- `src/hooks/` - Custom React hooks
- `src/lib/` - Utility functions

### Supabase Integration

**Client Setup:** `src/integrations/supabase/client.ts`
```typescript
import { supabase } from '@/integrations/supabase/client';
```

**Type Definitions:** `src/integrations/supabase/types.ts` (auto-generated from DB schema)

**Edge Functions:** Located in `supabase/functions/`
- Example: `generate-prompt-suggestions` - Uses Lovable AI Gateway for content generation

**Environment Variables:**
- `VITE_SUPABASE_URL` - Auto-configured by Lovable
- `VITE_SUPABASE_PUBLISHABLE_KEY` - Auto-configured by Lovable
- Edge Function secrets stored in Supabase (API keys for AI platforms, Google OAuth, Firecrawl, Resend)

## External API Integrations

### AI Platform APIs
- **OpenAI API:** ChatGPT responses (`OPENAI_API_KEY`)
- **Anthropic API:** Claude responses (`ANTHROPIC_API_KEY`)
- **Google Gemini API:** Gemini responses (`GOOGLE_GEMINI_API_KEY`)
- **Perplexity API:** Perplexity responses (`PERPLEXITY_API_KEY`)
- **X.AI API:** Grok responses (`XAI_API_KEY`)

### Analytics & Content
- **Google Analytics API:** OAuth 2.0 per domain (traffic data)
- **Google Search Console API:** OAuth 2.0 per domain (search queries)
- **Firecrawl API:** Web scraping for content verification (`FIRECRAWL_API_KEY`)
- **Lovable AI Gateway:** Semantic analysis for misinformation detection (`LOVABLE_API_KEY`)

### Notifications
- **Resend:** Email notifications (`RESEND_API_KEY`)
- **Slack Webhooks:** Optional, user-provided per organization

**Important:** API keys are stored as Supabase Edge Function secrets, never in frontend code or environment variables.

## Common Development Patterns

### Data Fetching with TanStack Query
```typescript
import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';

const { data, isLoading } = useQuery({
  queryKey: ['mentions', domainId],
  queryFn: async () => {
    const { data, error } = await supabase
      .from('mentions')
      .select('*')
      .eq('domain_id', domainId);
    if (error) throw error;
    return data;
  }
});
```

### Calling Edge Functions
```typescript
const { data, error } = await supabase.functions.invoke('generate-prompt-suggestions', {
  body: { mainPrompt: 'your prompt here' }
});
```

### shadcn/ui Components
Components are installed via CLI and live in `src/components/ui/`. They use:
- Radix UI primitives for accessibility
- Tailwind CSS for styling
- `class-variance-authority` (cva) for variants
- `tailwind-merge` (cn) for class merging

Example usage:
```typescript
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader } from '@/components/ui/dialog';
```

### Path Aliases
Uses `@/` alias for `src/` directory (configured in tsconfig.json and vite.config.ts):
```typescript
import { supabase } from '@/integrations/supabase/client';
import { Button } from '@/components/ui/button';
```

## Database Schema Notes

**Note:** Database tables are not yet created (types.ts shows empty schema). The schema is defined in `docs/API_REQUIREMENTS.md` and `docs/ARCHITECTURE_FLOWS.md`.

**Key Tables (to be created):**
- `organizations` - Tenant entities
- `domains` - Websites tracked per organization
- `integrations` - Google Analytics/Search Console OAuth tokens
- `mentions` - AI platform responses with brand mentions
- `citations` - Source references extracted from AI responses
- `misinformation_alerts` - Flagged inaccuracies
- `monitoring_rules` - User-defined detection rules
- `team_members` - Organization membership with roles
- `traffic_attribution` - Daily aggregated analytics data

**RLS Policies:** Must be implemented to ensure users only access their organization's data.

## File Organization Principles

- **Pages** are route-level components in `src/pages/`
- **Shared components** go in `src/components/`
- **UI primitives** (shadcn/ui) live in `src/components/ui/`
- **Business logic** and data fetching stay close to the components that use them
- **Edge Functions** are separate services in `supabase/functions/`

## Testing Edge Functions

When creating or modifying edge functions:
1. Test locally using Supabase CLI
2. Ensure CORS headers are properly configured
3. Handle errors gracefully with appropriate status codes
4. Use environment variables for API keys (never hardcode)
5. Return JSON responses with proper Content-Type headers

## Documentation References

See additional architecture documentation in `docs/`:
- `docs/ARCHITECTURE_FLOWS.md` - Detailed system architecture, data flows, ERD diagrams
- `docs/API_REQUIREMENTS.md` - Complete API integration requirements, OAuth setup, costs

## Deployment

This project is deployed via **Lovable Cloud**. Changes pushed to the main branch are automatically deployed. Build output goes to `dist/` directory.

## Key Considerations

1. **Multi-tenancy:** Always filter data by organization/domain. Never expose data across tenants.
2. **OAuth Token Management:** Tokens stored encrypted per domain. Implement refresh logic before API calls.
3. **Rate Limiting:** AI platform APIs have strict rate limits. Implement retry logic with exponential backoff.
4. **Cost Optimization:** Use cheaper models (GPT-5-mini, Gemini Flash) where possible. Cache AI responses.
5. **Security:** RLS policies must be enabled on all tables. Edge function secrets for API keys.
