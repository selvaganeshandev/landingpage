# LLM Monitor - Project Knowledge Summary

## 🎯 Project Purpose

**LLM Monitor** is a comprehensive platform for monitoring how brands, domains, and keywords are mentioned across Large Language Models (LLMs) like ChatGPT, Google Gemini, and Perplexity. It tracks mentions, citations, sentiment, visibility scores, and competitive positioning.

---

## 🏗️ System Architecture

### Three-Tier Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │     Engine      │
│   (React/Vite)  │───▶│   (Django API)  │───▶│  (Django +      │
│   Port: 8080    │    │   Port: 8000    │    │   Celery)       │
│                 │    │                 │    │   Port: 8001    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                        │
                              └──────────┬─────────────┘
                                         │
                              ┌──────────▼──────────┐
                              │   PostgreSQL DB     │
                              │   (Shared)          │
                              └─────────────────────┘
```

### Component Responsibilities

1. **Frontend (React + TypeScript + Vite)**
   - User interface and dashboards
   - Authentication and authorization
   - Data visualization and analytics
   - Real-time status monitoring
   - Port: 8080

2. **Backend (Django REST API)**
   - User authentication (JWT)
   - Domain, keyword, prompt management
   - Competitor tracking
   - Analytics and reporting APIs
   - Organization and team management
   - Port: 8000

3. **Engine (Django + Celery)**
   - Domain processing (keywords → prompts)
   - Prompt analytics processing (querying LLMs)
   - Competitor analysis
   - Topic generation and analytics
   - Background task scheduling
   - Port: 8001

---

## 📊 Core Data Flow

### Complete Processing Pipeline

```
User Input (Keywords)
    ↓
Domain Created (status: INIT)
    ↓
Auto-Schedule (status: INIT → SCHD)
    ↓
Engine: Domain Processing
    ├─ Keywords → Prompts (via ChatGPT API)
    ├─ NLP Clustering (SentenceTransformer + K-means)
    └─ Create PromptGroups & Prompts
    ↓
Domain Status: PROC (waiting for analytics)
    ↓
Engine: Prompt Analytics Processing
    ├─ Query ChatGPT
    ├─ Query Google Gemini
    ├─ Query Perplexity
    └─ Extract: mentions, citations, sentiment, position
    ↓
Store PromptAnalytics (one per platform per prompt)
    ↓
Aggregate Metrics (Group → Domain level)
    ↓
Domain Status: COMP
    ↓
Topic Processing (NLP clustering of keywords)
    ↓
Competitor Processing (if configured)
    ↓
Backend: Serve via API
    ↓
Frontend: Display Dashboards
```

---

## 🗄️ Database Models (Key Entities)

### Core Models

1. **Organisation**
   - Companies/organizations using the system
   - Has many accounts and domains
   - Fields: name, industry, team_count

2. **Account** (Custom User Model)
   - Users with roles: super_admin, admin, user
   - Belongs to an organisation
   - JWT authentication
   - Uses email as USERNAME_FIELD

3. **Domain**
   - Websites/domains being monitored
   - Processing status: INIT → SCHD → PROC → COMP
   - Contains keywords and prompts
   - Aggregated metrics: mentions, citations, visibility_score

4. **Keyword**
   - Keywords to track
   - Linked to domains
   - Used to generate prompts
   - Can be marked as "used" after prompt generation

5. **PromptGroup**
   - Groups of similar prompts (NLP clustering)
   - Contains aggregated metrics
   - Status: INIT → SCHD → PROC → COMP

6. **Prompt**
   - Individual prompts generated from keywords
   - Belongs to a PromptGroup
   - Track status: INIT → SCHD → PROC → COMP
   - Type: primary or secondary

7. **PromptAnalytics**
   - Analytics results from LLM queries
   - One per platform per prompt (ChatGPT, Gemini, Perplexity)
   - Contains: mentions, citations, position, sentiment, context_summary
   - Track status: INIT → PROC → COMP

8. **Competitor**
   - Competitor brands being tracked
   - Aggregated metrics
   - Status: INIT → SCHD → PROC → COMP

9. **CompetitorPromptAnalytics**
   - Links competitors to prompts
   - Stores competitor-specific analytics
   - Extracted from PromptAnalytics.context_summary

10. **Topic**
    - Groups of related keywords
    - Created via NLP clustering

11. **TopicAnalytics**
    - Aggregated analytics per topic
    - Calculated from PromptAnalytics

---

## 🔄 Status Flow System

### Domain Status Flow
```
INIT → SCHD → PROC → COMP
  ↓      ↓      ↓      ↓
Initial Scheduled Processing Completed
  ↓      ↓      ↓      ↓
Reset   Auto   Manual  Done
```

- **INIT**: Newly created, ready for processing
- **SCHD**: Scheduled for processing
- **PROC**: Currently processing
- **COMP**: Processing complete
- **FAIL**: Processing failed

### Prompt Status Flow
```
INIT → SCHD → PROC → COMP
```

- **INIT**: Created, waiting for analytics
- **SCHD**: Scheduled for LLM query
- **PROC**: Querying LLM platforms
- **COMP**: Analytics complete
- **FAIL**: Processing failed

---

## ⚙️ Background Processing (Celery)

### Celery Configuration
- **Broker**: Redis
- **Result Backend**: Redis
- **Workers**: Process background tasks
- **Beat**: Schedules periodic tasks (every 15 seconds)

### Scheduled Tasks

1. **Domain Scheduler** (`scheduler_tick`)
   - Picks up domains with status SCHD
   - Processes up to MAX_CONCURRENT_DOMAINS (default: 10)
   - Calls `process_domain_task` for each domain

2. **Prompt Analytics Scheduler** (`process_prompt_analytics_scheduler`)
   - Picks up prompt groups with status INIT
   - Processes prompts group by group
   - Queries LLM platforms (ChatGPT, Gemini, Perplexity)
   - Max 10 concurrent prompts

3. **Topic Analytics Scheduler** (`process_topic_analytics_scheduler`)
   - Processes topic analytics for completed domains

4. **Competitor Scheduler** (`process_competitor_scheduler`)
   - Processes competitors with status INIT

5. **Integration Insights Scheduler**
   - Processes Google Analytics and Search Console data

---

## 🔐 Authentication & Authorization

### Authentication Flow
1. User logs in via `POST /auth/login/`
2. Backend returns JWT tokens:
   - `access_token` (short-lived, ~15 min)
   - `refresh_token` (long-lived, ~7 days)
3. Frontend stores tokens in localStorage
4. All API requests include: `Authorization: Bearer <access_token>`
5. On 401, frontend automatically refreshes token
6. On refresh failure, redirects to login

### Authorization
- **Role-based**: super_admin, admin, user
- **Module-based**: Permissions per module (DASHBOARD, PROMPTS, etc.)
- **Level-based**: read, write, admin levels

---

## 🎨 Frontend Architecture

### Tech Stack
- **React 18** with TypeScript
- **Vite** for build tooling
- **React Router** for routing
- **TanStack Query** for data fetching
- **Zustand** for state management
- **shadcn/ui** for UI components
- **Tailwind CSS** for styling

### Key Features
1. **Protected Routes**: Route-level permission checks
2. **Domain Context**: Active domain selection
3. **Real-time Updates**: Polling for processing status
4. **Responsive Design**: Mobile-friendly UI
5. **Dark Mode**: Theme support

### Main Pages
- `/` or `/chat` - Chat interface (landing)
- `/insights` - Dashboard
- `/prompts` - Prompt management
- `/mentions` - Mentions tracking
- `/competitors` - Competitor analysis
- `/topics` - Topic analytics
- `/sentiment` - Sentiment analysis
- `/reports` - Report generation
- `/alerts` - Alert management

---

## 🔌 Key API Endpoints

### Backend API (Port 8000)

**Authentication:**
- `POST /auth/login/` - User login
- `POST /auth/token/refresh/` - Refresh JWT token
- `POST /auth/logout/` - Logout

**Domains:**
- `GET /domains/` - List domains
- `POST /domains/` - Create domain
- `GET /domains/{id}/` - Get domain details
- `PUT /domains/{id}/` - Update domain

**Keywords:**
- `GET /keywords/` - List keywords
- `POST /keywords/` - Create keyword
- `DELETE /keywords/{id}/` - Delete keyword

**Prompts:**
- `GET /prompts/` - List prompts
- `GET /prompts/{id}/` - Get prompt details
- `GET /prompts/{id}/analytics/` - Get prompt analytics

**Competitors:**
- `GET /competitors/` - List competitors
- `POST /competitors/` - Create competitor
- `GET /competitors/{id}/` - Get competitor details

**Analytics:**
- `GET /analytics/dashboard/` - Dashboard data
- `GET /analytics/sentiment/` - Sentiment analytics

### Engine API (Port 8001)

**Domain Processing:**
- `POST /api/start/` - Start domain processing
- `GET /api/domains/` - List domains with status
- `POST /api/domains/schedule/` - Schedule domain
- `POST /api/domains/reset/` - Reset domain to INIT

**Prompt Analytics:**
- `POST /api/prompts/process/` - Start prompt analytics processing
- `POST /api/prompts/start/` - Process single prompt
- `GET /api/prompts/status/{domain_id}/` - Get processing status

**Competitors:**
- `POST /api/competitors/process-single/` - Process competitor

**Status:**
- `GET /api/status/` - Overall processing status

---

## 🔍 Key Processing Components

### DomainProcessor
- Converts keywords to prompts using ChatGPT
- Groups prompts using NLP clustering (SentenceTransformer + K-means)
- Manages domain processing lifecycle
- Location: `engine/core/domain_processor.py`

### PromptAnalyticsProcessor
- Queries LLM platforms (ChatGPT, Gemini, Perplexity)
- Extracts mentions, citations, sentiment
- Aggregates group and domain metrics
- Location: `engine/core/prompt_analytics_processor.py`

### CompetitorProcessor
- Links competitors to prompts
- Analyzes competitor mentions from context_summary
- Calculates share of voice
- Location: `engine/core/competitor_processor.py`

### TopicProcessor
- Groups keywords into topics using NLP
- Creates topic hierarchies
- Location: `engine/core/topic_processor.py`

### TopicAnalyticsProcessor
- Aggregates analytics per topic
- Calculates topic-level metrics
- Location: `engine/core/topic_analytics_processor.py`

---

## 📦 Technology Stack

### Backend Dependencies
- Django 5.2
- Django REST Framework 3.15.2
- PostgreSQL (psycopg[binary])
- JWT Authentication (djangorestframework-simplejwt)
- CORS headers
- xhtml2pdf (for reports)
- Google API libraries (Analytics, Gemini)
- pandas, openpyxl (Excel export)

### Engine Dependencies
- Django 5.2
- OpenAI (ChatGPT API)
- sentence-transformers (NLP clustering)
- scikit-learn (K-means clustering)
- google-generativeai (Gemini API)
- perplexity-ai
- Celery 5.3.4 (task queue)
- Redis 5.0.1 (broker)
- TextBlob, NLTK (text processing)

### Frontend Dependencies
- React 18
- TypeScript
- Vite
- React Router
- TanStack Query
- Zustand
- shadcn/ui
- Tailwind CSS

---

## 🚀 Starting the System

### Quick Start (All Services)
```bash
./start-all.sh
```

This starts:
1. Backend (Django) on port 8000
2. Engine (Django) on port 8001
3. Celery Worker
4. Celery Beat
5. Frontend (Vite) on port 8080

### Manual Start

**Backend:**
```bash
cd backend
source .venv/bin/activate
python manage.py runserver
```

**Engine:**
```bash
cd engine
source .venv/bin/activate
python manage.py runserver 8001
```

**Celery:**
```bash
cd engine
source .venv/bin/activate
celery -A llm_monitor_engine worker --loglevel=info
celery -A llm_monitor_engine beat --loglevel=info
```

**Frontend:**
```bash
cd frontend
npm run dev
```

---

## 📝 Key Configuration

### Environment Variables

**Backend (.env):**
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- `SECRET_KEY`
- `DEBUG`

**Engine (.env):**
- Same database config as backend
- `OPENAI_API_KEY`
- `GOOGLE_API_KEY`
- `PERPLEXITY_API_KEY`
- `CELERY_BROKER_URL` (Redis)

**Frontend (.env):**
- `VITE_API_URL` (Backend URL)
- `VITE_ENGINE_URL` (Engine URL)

### Settings

**Backend:**
- `MAX_CONCURRENT_DOMAINS`: 10
- `PROMPT_MIN_COUNT`: 2 prompts per keyword

**Engine:**
- `MAX_CONCURRENT_DOMAINS`: 10
- `MAX_CONCURRENT_PROMPT_ANALYTICS`: 10
- Celery beat schedule: 15 seconds

---

## 🎯 Key Features

1. **Multi-LLM Monitoring**: Tracks mentions across ChatGPT, Gemini, Perplexity
2. **Automated Processing**: Celery-based background processing
3. **Competitive Intelligence**: Competitor tracking and share of voice
4. **Topic Analytics**: NLP-based topic grouping and analysis
5. **Real-time Dashboards**: Live status and metrics
6. **Alert System**: Configurable alerts for mentions, sentiment, etc.
7. **Report Generation**: PDF reports with analytics
8. **Multi-domain Support**: Track multiple domains per organization
9. **Team Management**: Role-based access control
10. **Integration Support**: Google Analytics, Search Console
11. **Misinformation Detection**: Flag inaccurate mentions
12. **Content Generation**: AI-powered content suggestions
13. **Multilingual Support**: Track mentions in multiple languages

---

## 📁 Project Structure

```
llm-monitor/
├── backend/                 # Django REST API
│   ├── authentication/      # User auth, JWT tokens
│   ├── domains/             # Domain management
│   ├── keywords/            # Keyword tracking
│   ├── prompts/             # Prompt management
│   ├── competitors/         # Competitor tracking
│   ├── topics/              # Topic management
│   ├── analytics/           # Analytics APIs
│   ├── alerts/              # Alert system
│   ├── reports/             # Report generation
│   ├── integrations/        # Google Analytics, GSC
│   ├── misinformation/     # Misinformation detection
│   ├── content/             # Content management
│   ├── chat/                # Chat interface
│   └── shared_models/       # Shared database models
│
├── engine/                  # Processing engine
│   ├── core/                # Core processing logic
│   │   ├── domain_processor.py
│   │   ├── prompt_analytics_processor.py
│   │   ├── competitor_processor.py
│   │   ├── topic_processor.py
│   │   └── processing_tasks.py  # Celery tasks
│   ├── shared_models/       # Shared database models
│   └── llm_monitor_engine/  # Engine Django settings
│
├── frontend/                # React frontend
│   ├── src/
│   │   ├── pages/           # Page components
│   │   ├── components/      # Reusable components
│   │   ├── services/        # API clients
│   │   ├── contexts/        # React contexts
│   │   └── stores/          # State management
│   └── public/
│
└── context/                 # Documentation
```

---

## 🔄 Processing Details

### Domain Processing (Keywords → Prompts)
1. Retrieve unused keywords for domain
2. Generate prompts from keywords using ChatGPT API
   - Creates natural language prompts
   - Generates multiple prompts per keyword (default: 2)
3. Group prompts using NLP clustering
   - Uses SentenceTransformer embeddings
   - K-means clustering to group similar prompts
   - Creates PromptGroup records
4. Create Prompt records
   - Links prompts to groups
   - Marks keywords as used
5. Domain status: PROC (waiting for analytics)

### Prompt Analytics Processing
1. For each PromptGroup:
   - Schedule group (status: INIT → SCHD)
   - Process prompts in group (concurrently, max 10)
2. For each prompt, query LLM platforms:
   - ChatGPT (OpenAI API)
   - Google Gemini
   - Perplexity
3. Extract analytics from responses:
   - Mentions count
   - Citations (URLs)
   - Position in response
   - Sentiment score
   - Context summary
4. Create PromptAnalytics records
   - One record per platform per prompt
   - Status: COMP when done
5. Aggregate group metrics
   - Calculate group totals
   - Update PromptGroup visibility_score
   - Create metric snapshots
6. Check domain completion
   - If all groups COMP:
     - Check for unused keywords
     - If unused keywords → reset to INIT
     - If no unused keywords → status: COMP
     - Trigger topic processing

### Topic Processing
1. Group keywords into topics (TopicProcessor)
   - Uses NLP clustering
   - Creates Topic records
   - Links keywords to topics
2. Process topic analytics (TopicAnalyticsProcessor)
   - Aggregates from PromptAnalytics
   - Calculates topic-level metrics
   - Creates TopicAnalytics records

### Competitor Processing
1. Create Competitor record (status: INIT)
2. Link prompts to competitor
   - Find all prompts with completed analytics
   - Create CompetitorPromptAnalytics records
3. Process competitor mentions
   - Extract from PromptAnalytics.context_summary
   - Analyze mentions, position, sentiment
   - Update CompetitorPromptAnalytics
4. Aggregate competitor analytics
   - Calculate totals (mentions, citations, etc.)
   - Update Competitor record
   - Create CompetitorAnalytics (time-series)
   - Create ShareOfVoiceAnalytics

---

## 📚 Additional Documentation Files

- `PROJECT_OVERVIEW.md` - Comprehensive project overview
- `PROCESSING_FLOW_DIAGRAM.md` - Visual flow diagrams
- `backend/API_DOCUMENTATION.md` - Backend API details
- `backend/API_STRUCTURE.md` - Backend API structure
- `ENGINE_API_ENDPOINTS.md` - Engine API reference
- `context/` - Additional context documentation

---

## 🛠️ Development Notes

- Always use `python3` instead of `python` for Django commands
- Backend and Engine share the same PostgreSQL database
- Engine uses `managed = False` models (read-only) to avoid migration conflicts
- Celery tasks run every 15 seconds by default
- Maximum 10 concurrent domains processed at once
- Maximum 10 concurrent prompt analytics processed at once
- Processing loop runs every 30 seconds if Celery unavailable

---

This summary provides a comprehensive understanding of the LLM Monitor project structure, architecture, data flow, and key components.

