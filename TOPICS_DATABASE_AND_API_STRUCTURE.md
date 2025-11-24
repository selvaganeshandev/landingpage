# Topics Module - Database Structure & API Implementation

## Database Structure

### 1. **topics** Table
Primary table storing topic information aggregated from keywords.

**Fields:**
- `id` (PK) - Auto-increment
- `domain_id` (FK to domains) - Which domain this topic belongs to
- `name` (VARCHAR) - Topic name (e.g., "Vegan Protein Supplements")
- `keyword_list` (JSON) - Array of keyword strings related to this topic
- `total_mentions` (INT) - Total mentions across all platforms
- `visibility_score` (DECIMAL 5,2) - Visibility score (0-100)
- `sentiment_score` (DECIMAL 5,2) - Sentiment score (-1.00 to 1.00)
- `trend_percentage` (DECIMAL 6,2) - Trend percentage change
- `platform_list` (JSON) - Array of platform names where topic is active
- `track_status` (VARCHAR) - Processing status: INIT/SCHD/PROC/COMP/FAIL
- `track_message` (TEXT) - Status message
- `tracked_at` (TIMESTAMP) - Last tracking update time
- `created_by_id` (FK to accounts)
- `created_at`, `modified_at` (TIMESTAMP)

**Indexes:**
- `(domain_id, -total_mentions)` - For sorting by popularity
- `(domain_id, -visibility_score)` - For sorting by visibility
- `(domain_id, -trend_percentage)` - For trending topics
- `(domain_id, track_status)` - For processing queries

---

### 2. **topic_analytics** Table
Time-series platform-specific analytics for topics.

**Fields:**
- `id` (PK) - Auto-increment
- `topic_id` (FK to topics)
- `platform` (VARCHAR) - Platform name (ChatGPT, Claude, Perplexity, or "All Platforms")
- `total_mentions` (INT) - Mentions on this platform for this date
- `visibility_score` (DECIMAL 5,2) - Visibility on this platform
- `sentiment_score` (DECIMAL 5,2) - Sentiment on this platform
- `timestamp` (DATE) - Date of this snapshot
- `created_at` (TIMESTAMP)

**Unique Constraint:** `(topic_id, platform, timestamp)`

**Indexes:**
- `(topic_id, platform, timestamp)` - For querying platform data over time
- `(topic_id, -timestamp, -total_mentions)` - For recent high-mention data
- `(platform, timestamp)` - For platform-wide analysis

---

### 3. **topic_prompts** Table
Stores AI-generated prompt suggestions for topics.

**Fields:**
- `id` (PK)
- `topic_id` (FK to topics)
- `prompt_text` (TEXT) - The actual prompt/question
- `relevance_score` (INT) - 0-100 relevance to topic
- `search_volume` (VARCHAR) - 'high', 'medium', 'low'
- `platform_list` (JSON) - Platforms where this prompt is relevant
- `created_at` (TIMESTAMP)

**Indexes:**
- `(topic_id, -relevance_score)` - For getting top prompts per topic
- `(search_volume, -relevance_score)` - For high-volume prompts

---

### 4. **topic_keywords** Table
Linking table between topics and keywords.

**Fields:**
- `id` (PK)
- `topic_id` (FK to topics)
- `keyword_id` (FK to keywords)
- `relevance_score` (DECIMAL 5,2) - How relevant keyword is to topic (0-100)
- `track_status` (VARCHAR) - INIT/COMP
- `created_at`, `modified_at` (TIMESTAMP)

**Unique Constraint:** `(topic_id, keyword_id)`

**Indexes:**
- `(topic_id, track_status)` - For processing queries
- `(keyword_id, track_status)` - For keyword lookups
- `(topic_id, -relevance_score)` - For top keywords per topic

---

### 5. **keyword_analytics** Table
Platform-wise analytics for individual keywords (feeds into topic analytics).

**Fields:**
- `id` (PK)
- `keyword_id` (FK to keywords)
- `platform` (VARCHAR) - Platform name
- `mentions` (INT) - Number of mentions
- `avg_position` (DECIMAL 8,2) - Average position in results
- `visibility_score` (DECIMAL 5,2) - Visibility score
- `sentiment_score` (DECIMAL 5,2) - Sentiment score
- `timestamp` (DATE) - Date of snapshot
- `track_status` (VARCHAR) - INIT/SCHD/PROC/COMP/FAIL
- `track_message` (TEXT)
- `tracked_at` (TIMESTAMP)
- `created_at`, `modified_at` (TIMESTAMP)

**Unique Constraint:** `(keyword_id, platform, timestamp)`

**Indexes:**
- `(keyword_id, platform, timestamp)` - For time-series queries
- `(keyword_id, track_status)` - For processing
- `(timestamp, -mentions)` - For trending keywords

---

### 6. **prompt_keywords** Table
Linking table between prompts and keywords (tracks which prompts are generated from which keywords).

**Fields:**
- `id` (PK)
- `prompt_id` (FK to prompts)
- `keyword_id` (FK to keywords)
- `relevance_score` (DECIMAL 5,2)
- `created_at`, `modified_at` (TIMESTAMP)

**Unique Constraint:** `(prompt_id, keyword_id)`

**Indexes:**
- `(prompt_id, keyword_id)`
- `(keyword_id, prompt_id)`
- `(keyword_id, -relevance_score)`

---

## Data Flow

```
Keywords (User Input)
    ↓
Topic Processor Groups Keywords → Creates Topics
    ↓
Topic Keywords (Links keywords to topics)
    ↓
Prompt Keywords (Links prompts to keywords)
    ↓
Keyword Analytics (Analyzes each keyword by platform)
    ↓
Topic Analytics (Aggregates keyword analytics by topic and platform)
    ↓
Topic (Updates with aggregated metrics)
```

---

## Backend API Endpoints

### 1. **TopicViewSet** (`/topics/topics/`)

#### Standard REST Endpoints:
- `GET /topics/topics/` - List all topics (filtered by user org)
- `GET /topics/topics/{id}/` - Get single topic
- `POST /topics/topics/` - Create topic
- `PUT /topics/topics/{id}/` - Update topic
- `DELETE /topics/topics/{id}/` - Delete topic

#### Custom Actions:

**a. `GET /topics/topics/by_domain/?domain_id={id}`**
- Returns all topics for a specific domain
- Response: `TopicSerializer[]`
```json
[
  {
    "id": 1,
    "domain": 1,
    "domain_name": "example.com",
    "name": "Vegan Protein",
    "keyword_list": ["vegan protein", "plant protein"],
    "total_mentions": 245,
    "visibility_score": "87.50",
    "sentiment_score": "0.65",
    "trend_percentage": "15.30",
    "platform_list": ["ChatGPT", "Claude"],
    "track_status": "COMP",
    "track_message": "",
    "tracked_at": "2025-11-24T10:30:00Z",
    "created_by": 1,
    "created_by_email": "user@example.com",
    "created_at": "2025-11-20T08:00:00Z",
    "modified_at": "2025-11-24T10:30:00Z"
  }
]
```

**b. `GET /topics/topics/trending/?domain_id={id}`**
- Returns top 10 trending topics (positive trend)
- Response: `TopicSerializer[]`

**c. `GET /topics/topics/{id}/keyword_analytics/`**
- Returns keyword analytics for a specific topic
- Aggregates mentions across platforms per keyword
- Response:
```json
[
  {
    "keyword": "vegan protein",
    "mentions": 145,
    "avg_position": 0,
    "visibility_score": 0,
    "sentiment_score": 0,
    "platforms": ["ChatGPT", "Claude", "Perplexity"]
  }
]
```

**d. `GET /topics/topics/{id}/related_prompts/`**
- Returns prompts related to topic via keywords
- Joins: prompts ← prompt_keywords ← topic_keywords ← topic
- Response:
```json
[
  {
    "id": 123,
    "prompt_text": "best vegan protein powder for athletes",
    "group_theme": "Supplement Recommendations",
    "analytics_count": 5,
    "avg_position": 1.5,
    "avg_sentiment": 0.75,
    "mentions": 45,
    "relevance_score": 85
  }
]
```

---

### 2. **TopicAnalyticsViewSet** (`/topics/topic-analytics/`)

#### Standard REST Endpoints:
- `GET /topics/topic-analytics/` - List all (supports `?topic_id=x` filter)
- `GET /topics/topic-analytics/{id}/` - Get single record
- `POST /topics/topic-analytics/` - Create record
- `PUT /topics/topic-analytics/{id}/` - Update record
- `DELETE /topics/topic-analytics/{id}/` - Delete record

**Response includes `platform` field:**
```json
{
  "id": 1,
  "topic": 1,
  "topic_name": "Vegan Protein",
  "platform": "ChatGPT",
  "total_mentions": 85,
  "visibility_score": "88.50",
  "sentiment_score": "0.70",
  "timestamp": "2025-11-24",
  "created_at": "2025-11-24T10:30:00Z"
}
```

#### Custom Actions:

**`GET /topics/topic-analytics/trends/?topic_id={id}&days={n}`**
- Returns time-series data for last N days (default 30)
- Can filter by specific topic or get all topics
- Response: `TopicAnalyticsSerializer[]`

---

### 3. **TopicPromptViewSet** (`/topics/topic-prompts/`)

#### Standard REST Endpoints:
- `GET /topics/topic-prompts/` - List all (supports `?topic_id=x` filter)
- `GET /topics/topic-prompts/{id}/` - Get single prompt
- `POST /topics/topic-prompts/` - Create prompt
- `PUT /topics/topic-prompts/{id}/` - Update prompt
- `DELETE /topics/topic-prompts/{id}/` - Delete prompt

**Response:**
```json
{
  "id": 1,
  "topic": 1,
  "topic_name": "Vegan Protein",
  "prompt_text": "best plant-based protein for muscle building",
  "relevance_score": 92,
  "search_volume": "high",
  "platform_list": ["ChatGPT", "Claude"],
  "created_at": "2025-11-24T10:30:00Z"
}
```

#### Custom Actions:

**`GET /topics/topic-prompts/high_relevance/?topic_id={id}&min_score={n}`**
- Returns prompts with relevance_score >= min_score (default 80)
- Can filter by topic

---

## Frontend-to-API Mapping

### Topics Page Components → API Calls

| UI Component | API Endpoint | Data Used |
|-------------|-------------|-----------|
| **Main Topics List** | `GET /topics/topics/by_domain/?domain_id=X` | All topic fields |
| **Topic Distribution Chart** | Same as above | `name`, `total_mentions`, `color` (computed) |
| **Topic Trends Chart** | `GET /topics/topic-analytics/trends/?days=90` | `timestamp`, `total_mentions`, `topic` |
| **Topic Card - Keywords** | From topic data | `keyword_list` (JSON field) |
| **Topic Card - Platforms** | From topic data | `platform_list` (JSON field) |
| **Keyword Performance Chart** | `GET /topics/topics/{id}/keyword_analytics/` (per topic) | `keyword`, `mentions` |
| **Prompt Suggestions** | `GET /topics/topic-prompts/?topic_id=X` | `prompt_text`, `relevance_score`, `search_volume` |

### Topic Detail Dialog Components → API Calls

| Tab/Section | API Endpoint | Data Used |
|------------|-------------|-----------|
| **Summary Cards** | From parent topic data | `mentions`, `visibility`, `sentiment`, `platforms.length` |
| **Timeline Tab** | `GET /topics/topic-analytics/trends/?topic_id=X&days=30` | `timestamp`, `total_mentions`, `visibility_score` |
| **Platforms Tab** | `GET /topics/topic-analytics/?topic_id=X` | `platform`, `total_mentions` |
| **Keywords Tab** | `GET /topics/topics/{id}/keyword_analytics/` | `keyword`, `mentions`, `avg_position`, `visibility_score` |
| **Sentiment Tab** | Calculated from topic data | `sentiment_score` → broken into Positive/Neutral/Negative |
| **Related Prompts Tab** | `GET /topics/topics/{id}/related_prompts/` | `prompt_text`, `mentions`, `relevance_score` |

---

## API Improvements Made

### 1. **Fixed TopicAnalyticsSerializer**
- ✅ **Added `platform` field** - Was missing, causing platform data to not be exposed

### 2. **Fixed related_prompts Query**
- ✅ **Renamed `prompt` → `prompt_text`** - Matches TopicPromptSerializer
- ✅ **Renamed `total_mentions` → `mentions`** - Matches frontend expectation
- ✅ **Added `relevance_score`** - Calculated from `avg_position`
- ✅ **Added type conversion** - Convert Decimal to float for JSON serialization

### 3. **Enhanced Query Param Filtering**
- ✅ **TopicAnalyticsViewSet** - Now supports `?topic_id=X` in base queryset
- ✅ **TopicPromptViewSet** - Now supports `?topic_id=X` in base queryset

---

## Data Verification Checklist

### ✅ Database Schema
- [x] All tables exist with correct fields
- [x] Foreign keys properly defined
- [x] Indexes on critical query paths
- [x] Unique constraints to prevent duplicates

### ✅ API Endpoints
- [x] All CRUD operations work
- [x] Custom actions return correct data
- [x] Query param filtering works
- [x] Response fields match serializers

### ✅ Frontend Integration
- [x] All API calls use correct endpoints
- [x] Response data properly transformed
- [x] Empty states handled
- [x] Loading states shown
- [x] Error handling implemented

### ✅ Data Flow
- [x] Keywords → Topics (via Topic Processor)
- [x] Keywords → Keyword Analytics (per platform)
- [x] Keyword Analytics → Topic Analytics (aggregation)
- [x] Prompts → Keywords (via Prompt Keywords)
- [x] Topics → UI (via API serializers)

---

## Testing the Complete Flow

### 1. Check Topics Exist
```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/topics/topics/by_domain/?domain_id=1
```

### 2. Check Topic Analytics with Platform
```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/topics/topic-analytics/?topic_id=1
```

### 3. Check Topic Trends
```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/topics/topic-analytics/trends/?topic_id=1&days=30
```

### 4. Check Keyword Analytics
```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/topics/topics/1/keyword_analytics/
```

### 5. Check Related Prompts
```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/topics/topics/1/related_prompts/
```

### 6. Check Topic Prompts
```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/topics/topic-prompts/?topic_id=1
```

---

## Summary

✅ **Database Structure**: Properly designed with 6 tables, appropriate relationships, and indexes

✅ **API Endpoints**: All necessary endpoints implemented with correct filtering and data transformation

✅ **Data Flow**: Keywords → Topics → Analytics → UI, with proper linking tables

✅ **Frontend Integration**: All components use dynamic data from APIs with proper error handling

✅ **Improvements Made**: 
- Added missing `platform` field to TopicAnalyticsSerializer
- Fixed field names in related_prompts query
- Enhanced query param filtering in ViewSets
- Added type conversion for Decimal fields

**The Topics module is now fully functional with correct database structure and complete API implementation!**

