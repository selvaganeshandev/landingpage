# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**LLM Monitor** - A comprehensive multi-component system for monitoring domain visibility across AI platforms. The system tracks keywords, generates prompts, analyzes LLM responses, and provides analytics through a multi-tenant SaaS interface.

**Architecture**: Monorepo with 4 main components:
1. **backend/** - Django 5.2 REST API (primary backend)
2. **engine/** - Django-based processing engine (keyword scraping, prompt generation, NLP grouping)
3. **frontend/** - React + TypeScript application (primary UI)
4. **UI/** - React + TypeScript application (Lovable-generated UI)

**Tech Stack**:
- Backend: Django 5.2 + Django REST Framework + PostgreSQL
- Engine: Django 5.2 + Celery + Redis + OpenAI + DataForSEO APIs
- Frontend: React 18 + TypeScript + Vite + shadcn/ui + Tailwind CSS + TanStack Query
- Database: PostgreSQL (shared between backend and engine)

## Development Commands

### Backend (Django API)

```bash
# Navigate to backend
cd backend

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Run development server (default: http://localhost:8000)
python manage.py runserver

# Create test data
python create_test_data.py
```

### Engine (Processing Engine)

```bash
# Navigate to engine
cd engine

# Activate virtual environment (if separate)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start the processing engine
python start_engine.py
# OR
python manage.py start_processor

# Start as daemon
python manage.py start_processor --daemon

# Check published status
python check_published_status.py
```

### Frontend (Primary React UI)

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server (http://localhost:5173)
npm run dev

# Build for production
npm run build

# Build for development
npm run build:dev

# Lint code
npm run lint

# Preview production build
npm run preview
```

### UI (Lovable-Generated React UI)

```bash
# Navigate to UI
cd UI

# Install dependencies
npm install

# Start development server
npm run dev

# Build and other commands (same as frontend)
npm run build
npm run lint
npm run preview
```

## Architecture Overview

### Database Architecture

**Shared PostgreSQL Database** (`llm_monitor`):
- Host: 64.227.190.42:5432
- Used by both `backend/` and `engine/`
- Multi-tenant data model with organization-level isolation

**Core Tables**:
- `organisations` - Tenant entities
- `accounts` - Custom user model (email-based auth, roles: super_admin/admin/user)
- `domains` - Websites tracked per organization (with processing_status: INIT/SCHD/PROC/COMP/FAIL)
- `keywords` - Keywords extracted for each domain
- `prompt_clusters` - Grouped prompts with NLP clustering
- `prompts` - Individual prompts (primary/secondary) tracked per domain
- `prompt_analytics` - Analytics data per prompt per LLM model
- `team_invitations` - Team member invitation system
- `user_permissions` - Module-level access control
- `password_reset_tokens` - Password reset workflow

**Additional Apps**:
- `alerts/` - Alert management models
- `analytics/` - Analytics tracking models
- `competitors/` - Competitor tracking models
- `topics/` - Topic analysis models
- `integrations/` - Third-party integration configs

### Backend (Django REST API)

**Base URL**: http://localhost:8000

**Key API Endpoints**:
- `/auth/*` - Authentication (JWT-based with djangorestframework-simplejwt)
  - Registration, login, logout, password reset, team invitations
- `/domains/*` - Domain management
- `/keywords/*` - Keyword management
- `/prompts/*` - Prompt and prompt cluster management
- `/alerts/*` - Alert management
- `/competitors/*` - Competitor tracking
- `/topics/*` - Topic analysis
- `/analytics/*` - Analytics data
- `/integrations/*` - Integration management
- `/admin/` - Django admin interface

**Authentication**:
- JWT tokens (access token: 60 min, refresh token: 7 days)
- Custom user model: `authentication.Account`
- Email-based authentication (email is USERNAME_FIELD)
- Role-based access control (super_admin/admin/user)
- Module-level permissions via `UserPermission` model

**CORS Configuration**:
- Configured for localhost:3000, 5173, 8080, 8081
- Credentials allowed
- All origins allowed in DEBUG mode

### Engine (Processing Engine)

**Base URL**: http://localhost:8001 (configured separately)

**Purpose**: Automated domain processing pipeline
1. Monitors domains with status "SCHD" (scheduled)
2. Scrapes keywords using DataForSEO API (50 keywords per domain)
3. Generates prompts from keywords using ChatGPT API
4. Groups prompts using NLP/ChatGPT
5. Updates domain status to "COMP" (completed) or "FAIL"

**Key Components**:
- `core/domain_processor.py` - Main processing logic
- `core/rest_client.py` - DataForSEO API client
- `core/chatgpt_client.py` - OpenAI API client
- `core/processing_tasks.py` - Celery tasks
- `core/prompt_analytics_processor.py` - Analytics processing
- `core/analytics_helpers.py` - Analytics utilities

**Multithreading**: Max 10 concurrent domains (configurable via MAX_CONCURRENT_DOMAINS)

**Celery Configuration**:
- Broker: Redis (redis://localhost:6379/0)
- Result backend: Redis
- Beat scheduler for periodic tasks

**API Endpoints**:
- `GET /api/status/` - Processing status
- `POST /api/start/` - Start processing a domain
- `GET /api/domains/` - List domains
- `POST /api/domains/schedule/` - Schedule domain for processing
- `POST /api/domains/reset/` - Reset domain to INIT status

**Required Environment Variables**:
- `DATAFORSEO_USERNAME` - DataForSEO API username
- `DATAFORSEO_PASSWORD` - DataForSEO API password
- `OPENAI_API_KEY` - OpenAI API key

### Frontend Architecture

**Routing**: React Router v6 (defined in `src/App.tsx`)

**State Management**:
- TanStack Query (React Query) for server state
- Zustand for client state (in `frontend/`)
- Context API for auth and global state

**Component Structure**:
- `src/pages/` - Page-level components (one per route)
- `src/components/` - Reusable UI components
- `src/components/ui/` - shadcn/ui base components (Radix UI + Tailwind)
- `src/services/` - API service functions
- `src/hooks/` - Custom React hooks
- `src/lib/` - Utility functions
- `src/contexts/` - Context providers
- `src/config/` - Configuration files

**Path Aliases**: Uses `@/` alias for `src/` directory (configured in tsconfig.json and vite.config.ts)

**Key Dependencies**:
- UI Components: shadcn/ui (Radix UI primitives) + Tailwind CSS
- Forms: react-hook-form + zod validation
- Charts: recharts
- HTTP Client: fetch API with TanStack Query
- Icons: lucide-react
- Date handling: date-fns

**API Integration Pattern**:
```typescript
// Example: Fetching data with TanStack Query
import { useQuery } from '@tanstack/react-query';

const { data, isLoading } = useQuery({
  queryKey: ['domains', organisationId],
  queryFn: async () => {
    const response = await fetch(`http://localhost:8000/domains/?organisation=${organisationId}`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    });
    return response.json();
  }
});
```

## Domain Status Flow (Engine Processing)

```
INIT (Initial)
  ↓
SCHD (Scheduled) ← Triggered by API or admin
  ↓
PROC (Processing) ← Engine picks up and processes
  ↓
COMP (Completed) or FAIL (Failed) ← Final status
```

**To reset a domain**: Change status back to INIT or use `/api/domains/reset/` endpoint

## Multi-Tenant Data Isolation

**Critical Principle**: All queries must filter by `organisation` to ensure data isolation between tenants.

**Implementation**:
- All major models have `organisation` foreign key
- ViewSets should filter querysets by user's organisation
- RLS policies recommended for production (currently enforced at application level)
- `DomainAccess` model provides additional per-domain access control

**User Roles**:
- `super_admin` - Platform-wide access (across all organisations)
- `admin` - Organisation admin (can manage team, domains, settings)
- `user` - Regular user (read access, limited write)

**Permission System**:
- Module-based permissions via `UserPermission` model
- Modules include: dashboard, mentions, prompts, alerts, sentiment_analysis, topics, competitors, etc.
- Permission levels: read, write, admin

## Common Development Patterns

### Creating New Django Models

```python
# Always include organisation foreign key for multi-tenancy
from django.db import models

class MyModel(models.Model):
    organisation = models.ForeignKey(
        'authentication.Organisation',
        on_delete=models.CASCADE,
        related_name='my_models'
    )
    # ... other fields
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'my_models'
        indexes = [
            models.Index(fields=['organisation', 'created_at']),
        ]
```

### Creating ViewSets

```python
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

class MyModelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # CRITICAL: Filter by user's organisation
        return MyModel.objects.filter(
            organisation=self.request.user.organisation
        )
```

### Frontend API Calls

```typescript
// src/services/api.ts pattern
const API_URL = 'http://localhost:8000';

export const getDomains = async (token: string, orgId: number) => {
  const response = await fetch(`${API_URL}/domains/?organisation=${orgId}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) throw new Error('Failed to fetch domains');
  return response.json();
};
```

## Testing

### Backend Testing

```bash
cd backend
python manage.py test

# Test specific app
python manage.py test authentication
python manage.py test domains
```

### Engine Testing

```bash
cd engine
python test_engine.py
```

### Frontend Testing

Currently no test suite configured. Tests can be added using:
- Vitest (recommended for Vite projects)
- React Testing Library
- Playwright/Cypress for E2E tests

## Database Migrations

**Important**: Since backend and engine share the same database, coordinate migrations carefully.

```bash
# Backend migrations
cd backend
python manage.py makemigrations
python manage.py migrate

# Engine migrations
cd engine
python manage.py makemigrations shared_models
python manage.py migrate
```

**Note**: Engine uses `shared_models/` app which should mirror core models from backend.

## API Documentation Files

Additional API documentation available in `backend/`:
- `API_DOCUMENTATION.md` - Complete API endpoint documentation
- `API_STRUCTURE.md` - API structure and conventions
- `AUTH_CURL_REQUESTS.md` - cURL examples for authentication endpoints
- `SIMPLIFIED_AUTH_API.md` - Simplified auth flow documentation
- `DATABASE_NAMING_CONVENTION_CHANGES.md` - Database naming standards
- `DATABASE_OPTIMIZATIONS.md` - Performance optimization notes
- `INDEXING_SUMMARY.md` - Database indexing strategy
- `ADMIN_SETUP.md` - Admin panel setup
- `POSTGRES_SETUP.md` - PostgreSQL setup guide

## Environment Configuration

### Backend `.env`

```env
SECRET_KEY=<django-secret-key>
DEBUG=True
DB_NAME=llm_monitor
DB_USER=root
DB_PASSWORD=Monit@2025$
DB_HOST=64.227.190.42
DB_PORT=5432
SITE_URL=http://localhost:8080
```

### Engine Environment

Engine uses same database config as backend, plus:
- `DATAFORSEO_USERNAME` - DataForSEO API credentials
- `DATAFORSEO_PASSWORD` - DataForSEO API credentials
- `OPENAI_API_KEY` - OpenAI API key
- Celery/Redis configuration in settings

### Frontend Environment

Frontend expects backend at `http://localhost:8000`. Configure via:
- `src/config/` directory
- Or environment variables (e.g., `VITE_API_URL`)

## Key Considerations

1. **Multi-tenancy**: Always filter by organisation. Never expose data across tenants.
2. **Authentication**: JWT tokens expire (60 min). Implement refresh token logic.
3. **Processing Engine**: Monitor domain status. Engine processes domains with status="SCHD".
4. **API Rate Limits**: DataForSEO and OpenAI have rate limits. Implement retry logic.
5. **Database Indexing**: Critical indexes on organisation, processing_status, created_at fields.
6. **Email Configuration**: SMTP configured for Gmail (appkodes@gmail.com).
7. **CORS**: Ensure frontend origin is in CORS_ALLOWED_ORIGINS.

## Lovable Integration

The `UI/` and `frontend/` directories have existing CLAUDE.md files focused on Lovable Cloud deployment and Supabase integration. Those are separate from this monorepo's Django backend architecture.

**Note**: The UI/ and frontend/ directories may have been generated via Lovable and could be legacy/alternative implementations. The primary backend is Django-based.

## Production Deployment Checklist

- [ ] Set `DEBUG=False` in Django settings
- [ ] Configure production SECRET_KEY
- [ ] Set up production database with proper credentials
- [ ] Configure proper ALLOWED_HOSTS
- [ ] Set up production CORS origins
- [ ] Use environment variables for all secrets
- [ ] Set up process manager for engine (systemd/supervisor)
- [ ] Configure Redis for Celery in production
- [ ] Set up monitoring for engine processing
- [ ] Configure static file serving (collectstatic)
- [ ] Set up database backups
- [ ] Configure email backend for production (not Gmail SMTP)
- [ ] Review and apply RLS policies on database tables

## Common Issues

**Database Connection Errors**: Ensure PostgreSQL is running at 64.227.190.42:5432 and credentials are correct.

**CORS Errors**: Add frontend origin to `CORS_ALLOWED_ORIGINS` in backend/llm_monitor/settings.py.

**Engine Not Processing**: Check domain status is "SCHD", verify API keys (DATAFORSEO, OPENAI_API_KEY), ensure Redis is running.

**JWT Token Expired**: Implement refresh token logic in frontend using `/auth/token/refresh/` endpoint.

**Migration Conflicts**: Backend and engine share DB - coordinate migrations or use separate migration apps.
