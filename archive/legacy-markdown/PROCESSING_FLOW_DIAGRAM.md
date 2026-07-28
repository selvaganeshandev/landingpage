# LLM Monitor - Processing Flow Diagrams

## 🔄 Complete System Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERACTION                         │
│  Create Domain → Add Keywords → Configure Settings              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                         BACKEND API                              │
│  Port: 8000                                                      │
│  - Domain Management                                             │
│  - Keyword Management                                            │
│  - User Authentication                                           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      POSTGRESQL DATABASE                         │
│  - Domain (status: INIT)                                         │
│  - Keywords                                                      │
│  - Prompts                                                       │
│  - PromptAnalytics                                               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ENGINE PROCESSING                           │
│  Port: 8001                                                      │
│  Celery Workers + Beat                                           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LLM PLATFORMS                                 │
│  - ChatGPT (OpenAI)                                              │
│  - Google Gemini                                                 │
│  - Perplexity                                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Domain Processing Flow (Detailed)

```
┌──────────────────────────────────────────────────────────────┐
│ Step 1: Domain Creation (Backend)                            │
│                                                              │
│  User creates domain with keywords                           │
│  Domain.status = INIT                                        │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 2: Auto-Scheduling                                      │
│                                                              │
│  Domain.status = INIT → SCHD                                 │
│  (Automatic or via API)                                      │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 3: Celery Scheduler (Every 15s)                         │
│                                                              │
│  scheduler_tick()                                            │
│  - Finds domains with status = SCHD                          │
│  - Limits to MAX_CONCURRENT_DOMAINS (10)                    │
│  - Calls process_domain_task.delay()                         │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 4: Domain Processing (DomainProcessor)                │
│                                                              │
│  Domain.status = SCHD → PROC                                 │
│                                                              │
│  4.1: Retrieve unused keywords                               │
│  4.2: Generate prompts using ChatGPT                        │
│       - Calls ChatGPT API                                    │
│       - Creates natural language prompts                     │
│       - 2 prompts per keyword (default)                      │
│                                                              │
│  4.3: Group prompts using NLP                                │
│       - SentenceTransformer embeddings                       │
│       - K-means clustering                                   │
│       - Creates PromptGroup records                          │
│                                                              │
│  4.4: Create Prompt records                                  │
│       - Link to PromptGroup                                  │
│       - Mark keywords as used                                │
│                                                              │
│  Domain.status = PROC (waiting for analytics)                │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 5: Prompt Analytics Processing                          │
│  (See detailed flow below)                                    │
└──────────────────────────────────────────────────────────────┘
```

---

## 🔍 Prompt Analytics Processing Flow (Detailed)

```
┌──────────────────────────────────────────────────────────────┐
│ Step 1: Scheduler (Every 15s)                               │
│                                                              │
│  process_prompt_analytics_scheduler()                       │
│  - Finds PromptGroups with status = INIT                    │
│  - Domain must be PROC or COMP                               │
│  - Processes one group at a time                            │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 2: Schedule Group                                       │
│                                                              │
│  PromptGroup.status = INIT → SCHD                           │
│  Get all prompts in group with status = INIT                │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 3: Process Prompts (Concurrently, max 10)               │
│                                                              │
│  For each prompt:                                            │
│    Prompt.status = INIT → SCHD → PROC                        │
│                                                              │
│    3.1: Query ChatGPT                                        │
│         - OpenAI API call                                     │
│         - Extract: mentions, citations, position            │
│                                                              │
│    3.2: Query Google Gemini                                 │
│         - Google API call                                    │
│         - Extract: mentions, citations, position             │
│                                                              │
│    3.3: Query Perplexity                                    │
│         - Perplexity API call                                │
│         - Extract: mentions, citations, position             │
│                                                              │
│    3.4: Create PromptAnalytics records                      │
│         - One per platform                                  │
│         - Store: mentions, citations, sentiment, position   │
│         - Status = COMP                                      │
│                                                              │
│    Prompt.status = PROC → COMP                               │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 4: Aggregate Group Metrics                             │
│                                                              │
│  When all prompts in group are COMP:                         │
│                                                              │
│  - Calculate group totals                                    │
│    * Total mentions                                          │
│    * Total citations                                         │
│    * Average position                                        │
│    * Average sentiment                                       │
│                                                              │
│  - Calculate visibility_score                               │
│    (40% mentions + 30% citations + 20% sentiment + 10% pos) │
│                                                              │
│  - Update PromptGroup                                       │
│  - Create metric snapshots                                  │
│  - Update domain-level aggregations                         │
│                                                              │
│  PromptGroup.status = COMP                                   │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 5: Check Domain Completion                             │
│                                                              │
│  When all groups are COMP:                                    │
│                                                              │
│  - Check for unused keywords                                 │
│                                                              │
│  IF unused keywords exist:                                    │
│    → Domain.status = INIT (ready for next cycle)            │
│                                                              │
│  IF no unused keywords:                                       │
│    → Domain.status = COMP                                    │
│    → Trigger topic processing                                │
└──────────────────────────────────────────────────────────────┘
```

---

## 🏢 Competitor Processing Flow

```
┌──────────────────────────────────────────────────────────────┐
│ Step 1: Create Competitor (Backend)                          │
│                                                              │
│  POST /competitors/                                          │
│  - Creates Competitor record                                 │
│  - Status = INIT                                             │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 2: Trigger Processing (Engine API)                      │
│                                                              │
│  POST /api/competitors/process-single/                       │
│  { "competitor_id": 1 }                                      │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 3: Link Prompts to Competitor                           │
│                                                              │
│  _link_prompts_to_competitor()                               │
│                                                              │
│  - Find all prompts with completed analytics                 │
│    (PromptAnalytics.track_status = COMP)                    │
│                                                              │
│  - Create CompetitorPromptAnalytics records                  │
│    - One per prompt                                          │
│    - Status = INIT                                           │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 4: Process Competitor Mentions                          │
│                                                              │
│  For each CompetitorPromptAnalytics:                         │
│                                                              │
│    - Get PromptAnalytics.context_summary                     │
│      (No new API calls - reuses existing data)               │
│                                                              │
│    - Analyze competitor mentions:                            │
│      * is_mentioned (boolean)                                │
│      * position (integer)                                    │
│      * mention_count (integer)                               │
│      * sentiment_category                                    │
│      * sentiment_score                                       │
│                                                              │
│    - Update CompetitorPromptAnalytics                        │
│      Status = COMP                                           │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 5: Aggregate Competitor Analytics                       │
│                                                              │
│  _aggregate_competitor_analytics()                           │
│                                                              │
│  - Calculate totals from CompetitorPromptAnalytics:          │
│    * total_mentions                                          │
│    * total_citations                                         │
│    * average_position                                        │
│    * sentiment_score                                         │
│                                                              │
│  - Calculate visibility_score                               │
│  - Calculate share_of_voice_percentage                      │
│                                                              │
│  - Update Competitor record                                  │
│  - Create CompetitorAnalytics (time-series)                 │
│  - Create ShareOfVoiceAnalytics                             │
│                                                              │
│  Competitor.status = COMP                                    │
└──────────────────────────────────────────────────────────────┘
```

---

## 📚 Topic Processing Flow

```
┌──────────────────────────────────────────────────────────────┐
│ Trigger: Domain status = COMP                                 │
│                                                              │
│  process_topics_for_domain_task.delay(domain_id)            │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 1: Group Keywords into Topics                           │
│                                                              │
│  TopicProcessor.process_topics_for_domain()                 │
│                                                              │
│  - Use NLP clustering (SentenceTransformer + K-means)       │
│  - Group similar keywords                                    │
│  - Create Topic records                                      │
│  - Link keywords to topics (TopicKeyword)                   │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ Step 2: Process Topic Analytics                              │
│                                                              │
│  TopicAnalyticsProcessor.process_analytics_for_domain()      │
│                                                              │
│  - For each topic:                                           │
│    * Get all keywords in topic                               │
│    * Get all prompts linked to keywords                      │
│    * Aggregate from PromptAnalytics:                         │
│      - Total mentions                                        │
│      - Total citations                                       │
│      - Average position                                      │
│      - Sentiment score                                       │
│                                                              │
│  - Create TopicAnalytics records                             │
│  - Create KeywordAnalytics records                          │
└──────────────────────────────────────────────────────────────┘
```

---

## 🔄 Status Transition Diagram

### Domain Status Flow

```
     ┌─────┐
     │ INIT│  ← New domain created
     └──┬──┘
        │
        │ Auto-schedule or API call
        │
        ▼
     ┌─────┐
     │ SCHD│  ← Scheduled for processing
     └──┬──┘
        │
        │ Celery picks up
        │
        ▼
     ┌─────┐
     │ PROC│  ← Processing (keywords → prompts → analytics)
     └──┬──┘
        │
        │ All analytics complete
        │
        ▼
     ┌─────┐
     │ COMP│  ← Completed
     └──┬──┘
        │
        │ (If unused keywords exist)
        │
        └──────┐
               │
               ▼
            ┌─────┐
            │ INIT│  ← Reset for next cycle
            └─────┘
```

### Prompt Status Flow

```
     ┌─────┐
     │ INIT│  ← Prompt created
     └──┬──┘
        │
        │ Scheduler picks up
        │
        ▼
     ┌─────┐
     │ SCHD│  ← Scheduled for LLM query
     └──┬──┘
        │
        │ Processing starts
        │
        ▼
     ┌─────┐
     │ PROC│  ← Querying LLM platforms
     └──┬──┘
        │
        │ Analytics extracted
        │
        ▼
     ┌─────┐
     │ COMP│  ← Analytics complete
     └─────┘
```

---

## 🎯 Celery Task Scheduling

```
┌──────────────────────────────────────────────────────────────┐
│                    CELERY BEAT (Scheduler)                     │
│                    Runs every 15 seconds                       │
└──────────────────────────┬─────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Domain       │  │ Prompt       │  │ Competitor    │
│ Scheduler    │  │ Analytics    │  │ Scheduler    │
│              │  │ Scheduler     │  │              │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Find SCHD    │  │ Find INIT     │  │ Find INIT    │
│ domains      │  │ prompt groups │  │ competitors  │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Dispatch to  │  │ Dispatch to  │  │ Dispatch to  │
│ Celery       │  │ Celery       │  │ Celery       │
│ Workers      │  │ Workers      │  │ Workers      │
└──────────────┘  └──────────────┘  └──────────────┘
```

---

## 📊 Data Flow: Keywords to Analytics

```
Keywords
   │
   │ Domain Processing
   ▼
Prompts (via ChatGPT generation)
   │
   │ NLP Clustering
   ▼
PromptGroups
   │
   │ Prompt Analytics Processing
   ▼
PromptAnalytics (per platform)
   │
   │ Aggregation
   ▼
Group Metrics
   │
   │ Domain Aggregation
   ▼
Domain Metrics
   │
   │ Topic Processing
   ▼
Topics & TopicAnalytics
   │
   │ Competitor Processing
   ▼
CompetitorAnalytics
```

---

## 🔐 Authentication Flow

```
User Login
   │
   │ POST /auth/login/
   ▼
Backend validates credentials
   │
   │ Returns JWT tokens
   ▼
Frontend stores tokens
   │
   │ All API requests
   ▼
Include Authorization header
   │
   │ Token expires (401)
   ▼
Auto-refresh token
   │
   │ POST /auth/token/refresh/
   ▼
New tokens stored
   │
   │ Retry original request
   ▼
Success
```

---

This document provides visual representations of all major processing flows in the LLM Monitor system.

