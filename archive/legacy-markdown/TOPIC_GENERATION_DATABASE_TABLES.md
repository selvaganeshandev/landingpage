# Database Tables Used by Topic Generation

This document lists all database tables/models used by the topic generation and analytics processing system.

## Core Tables (Directly Used)

### 1. **`domains`** (Domain)
- **Purpose**: Represents the domain/website being monitored
- **Usage in Topic Generation**:
  - Used to filter keywords by domain
  - Used to associate topics with domains
  - Used to check domain processing status (triggers topic generation when status = 'COMP')
- **Key Fields Used**:
  - `id`: Domain identifier
  - `name`: Domain name
  - `processing_status`: Status tracking (INIT/SCHD/PROC/COMP/FAIL)

### 2. **`keywords`** (Keyword)
- **Purpose**: Stores keywords being tracked for domains
- **Usage in Topic Generation**:
  - Source data for topic creation (keywords are grouped into topics)
  - Filtered by `last_used_for_topic_generation__isnull=True` to get only unused keywords
  - Updated with `last_used_for_topic_generation` timestamp when used
- **Key Fields Used**:
  - `id`: Keyword identifier
  - `keyword`: Keyword text
  - `domain_id`: Foreign key to domains
  - `last_used_for_topic_generation`: Timestamp tracking when keyword was last used for topic generation

### 3. **`topics`** (Topic)
- **Purpose**: Stores topics created from keyword grouping
- **Usage in Topic Generation**:
  - Created by Topic Processor when grouping keywords
  - Stores topic name, keyword list, and aggregated analytics
- **Key Fields Used**:
  - `id`: Topic identifier
  - `domain_id`: Foreign key to domains
  - `name`: Topic name
  - `keyword_list`: JSON array of keyword strings
  - `track_status`: Processing status (INIT/SCHD/PROC/COMP/FAIL)
  - `track_message`: Status message
  - `tracked_at`: Timestamp of last status update
  - `total_mentions`: Aggregated mentions count
  - `visibility_score`: Aggregated visibility score
  - `sentiment_score`: Aggregated sentiment score
  - `trend_percentage`: Trend percentage
  - `platform_list`: JSON array of platform names

### 4. **`topic_keywords`** (TopicKeyword)
- **Purpose**: Linking table between Topics and Keywords (many-to-many relationship)
- **Usage in Topic Generation**:
  - Created when keywords are linked to topics
  - Tracks which keywords belong to which topics
  - Used to track processing status of keyword analytics
- **Key Fields Used**:
  - `id`: Record identifier
  - `topic_id`: Foreign key to topics
  - `keyword_id`: Foreign key to keywords
  - `relevance_score`: Relevance score (0-100)
  - `track_status`: Processing status (INIT/COMP)

## Analytics Tables (Used by Topic Analytics Processor)

### 5. **`prompt_keywords`** (PromptKeyword)
- **Purpose**: Linking table between Prompts and Keywords
- **Usage in Topic Generation**:
  - Used to find which prompts are associated with keywords in topics
  - Links prompts to keywords for analytics calculation
- **Key Fields Used**:
  - `id`: Record identifier
  - `prompt_id`: Foreign key to prompts
  - `keyword_id`: Foreign key to keywords
  - `relevance_score`: Relevance score (0-100)

### 6. **`prompts`** (Prompt)
- **Purpose**: Stores prompts generated from keywords
- **Usage in Topic Generation**:
  - Referenced via PromptKeyword to find prompts linked to keywords
  - Used indirectly through PromptAnalytics for analytics calculation
- **Key Fields Used**:
  - `id`: Prompt identifier
  - (Accessed via PromptKeyword relationships)

### 7. **`prompt_analytics`** (PromptAnalytics)
- **Purpose**: Stores analytics data for prompts (platform-wise)
- **Usage in Topic Generation**:
  - Source data for calculating keyword analytics
  - Aggregated to create KeywordAnalytics records
  - Used to calculate topic-level analytics
- **Key Fields Used**:
  - `id`: Analytics record identifier
  - `prompt_id`: Foreign key to prompts
  - `platform`: Platform name (e.g., ChatGPT, Claude, Perplexity)
  - `track_status`: Processing status (must be 'COMP' for analytics)
  - `mentions`: Number of mentions
  - `avg_position`: Average position in search results
  - `visibility_score`: Visibility score
  - `sentiment_score`: Sentiment score

### 8. **`keyword_analytics`** (KeywordAnalytics)
- **Purpose**: Platform-wise analytics for keywords
- **Usage in Topic Generation**:
  - Created/updated by Topic Analytics Processor
  - Aggregated from PromptAnalytics for each keyword-platform combination
  - Used to calculate topic-level aggregated analytics
- **Key Fields Used**:
  - `id`: Analytics record identifier
  - `keyword_id`: Foreign key to keywords
  - `platform`: Platform name
  - `timestamp`: Date of analytics snapshot
  - `mentions`: Number of mentions
  - `avg_position`: Average position
  - `visibility_score`: Visibility score
  - `sentiment_score`: Sentiment score
  - `track_status`: Processing status

### 9. **`topic_analytics`** (TopicAnalytics)
- **Purpose**: Time-series analytics for topics
- **Usage in Topic Generation**:
  - Created/updated by Topic Analytics Processor
  - Stores aggregated analytics for topics over time
  - Aggregated from KeywordAnalytics for all keywords in a topic
- **Key Fields Used**:
  - `id`: Analytics record identifier
  - `topic_id`: Foreign key to topics
  - `timestamp`: Date of analytics snapshot
  - `total_mentions`: Aggregated mentions
  - `visibility_score`: Aggregated visibility score
  - `sentiment_score`: Aggregated sentiment score

## Optional/Supporting Tables

### 10. **`topic_prompts`** (TopicPrompt)
- **Purpose**: Stores prompts related to topics (for suggestions/recommendations)
- **Usage in Topic Generation**:
  - Not directly used in the core topic generation flow
  - May be used for storing topic-related prompt suggestions
- **Key Fields**:
  - `id`: Record identifier
  - `topic_id`: Foreign key to topics
  - `prompt_text`: Prompt text
  - `relevance_score`: Relevance score (0-100)
  - `search_volume`: Search volume category
  - `platform_list`: JSON array of platform names

## Data Flow Summary

1. **Topic Generation (Topic Processor)**:
   - Reads: `domains`, `keywords` (unused only)
   - Creates: `topics`, `topic_keywords`
   - Updates: `keywords` (sets `last_used_for_topic_generation`)

2. **Topic Analytics (Topic Analytics Processor)**:
   - Reads: `topics`, `topic_keywords`, `prompt_keywords`, `prompts`, `prompt_analytics`
   - Creates/Updates: `keyword_analytics`, `topic_analytics`
   - Updates: `topics` (aggregated metrics), `topic_keywords` (track_status)

## Relationships

```
domains (1) ──< (many) keywords
domains (1) ──< (many) topics
topics (1) ──< (many) topic_keywords ──> (many) keywords
topics (1) ──< (many) topic_analytics
topics (1) ──< (many) topic_prompts
keywords (1) ──< (many) topic_keywords
keywords (1) ──< (many) prompt_keywords ──> (many) prompts
keywords (1) ──< (many) keyword_analytics
prompts (1) ──< (many) prompt_analytics
prompts (1) ──< (many) prompt_keywords
```

## Indexes Used for Performance

- `keywords.domain_id + last_used_for_topic_generation` (for filtering unused keywords)
- `topics.domain_id + track_status` (for finding topics to process)
- `topic_keywords.topic_id + track_status` (for finding unprocessed keywords)
- `topic_keywords.keyword_id` (for finding prompts via prompt_keywords)
- `prompt_keywords.keyword_id` (for linking prompts to keywords)
- `prompt_analytics.prompt_id + track_status` (for finding completed analytics)
- `keyword_analytics.keyword_id + platform + timestamp` (for aggregating topic analytics)

