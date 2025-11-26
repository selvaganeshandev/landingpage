# Engine Processor Analysis: Domain, Prompt, and Topic Processing

## Overview

The engine folder contains three main processors that work together in a pipeline to process domains, generate and analyze prompts, and organize keywords into topics. This document provides a comprehensive analysis of how each processor works and how they interact.

---

## 1. Domain Processor (`domain_processor.py`)

### Purpose
The Domain Processor is the entry point of the processing pipeline. It handles:
- Keyword validation and selection
- Prompt generation from keywords using ChatGPT
- Semantic grouping of prompts using NLP (SentenceTransformers + KMeans)
- Creating prompt groups and linking prompts to keywords

### Key Components

#### Class: `DomainProcessor`
- **Initialization**: Sets up ChatGPT client, manages concurrent domain processing (max 10 by default)
- **Threading**: Uses threading for concurrent domain processing with lock-based synchronization

#### Main Processing Flow (`_process_single_domain`)

1. **Status Management**
   - Uses `select_for_update()` to prevent race conditions
   - Status transitions: `SCHD` → `PROC` → `COMP` (or `FAIL`)
   - Tracks progress with `track_message` and `tracked_at`

2. **Keyword Selection**
   - Filters keywords where `last_used_for_generation` is NULL (unused keywords)
   - Only processes keywords with `auto_generate_prompts=True`
   - Orders by priority and creation date
   - Handles edge cases:
     - No keywords → marks domain as `FAIL`
     - All keywords used → marks domain as `COMP`

3. **Prompt Generation**
   - Uses `ChatGPTClient.generate_prompts_from_keywords()`
   - Generates prompts with country-specific context
   - Ensures minimum prompts per keyword (default: 2)
   - Deduplicates and sanitizes prompts
   - Builds prompt-to-keyword mapping before grouping

4. **Prompt Grouping (NLP-based)**
   - Uses SentenceTransformers (`paraphrase-MiniLM-L6-v2`) for embeddings
   - Applies KMeans clustering (1 cluster per ~5 prompts)
   - Extracts smart titles from clusters using NLP analysis
   - Normalizes titles to 1-2 words with "&" separator
   - Removes numbers and generic boilerplate

5. **Database Storage**
   - Creates `PromptGroup` records with themes
   - Creates `Prompt` records (primary/secondary types)
   - Links prompts to keywords via `PromptKeyword` records
   - Creates default `PromptAnalytics` records for all enabled platforms
   - Marks keywords as used (`last_used_for_generation` timestamp)

6. **Status Updates**
   - Keeps domain in `PROC` status (analytics processor will set to `COMP`)
   - Does NOT mark as `COMP` here - waits for LLM queries

### Key Methods

- `_group_prompts_with_sentence_transformers()`: NLP-based clustering
- `_extract_smart_title_from_prompts()`: Extracts meaningful titles from prompt clusters
- `_normalize_to_term()`: Converts prompt text to concise terms (max 2 words)
- `_link_prompt_to_keyword_direct()`: Creates PromptKeyword links
- `_store_prompt_groups()`: Persists groups and prompts to database

### Integration Points
- **Input**: Domains with `processing_status='SCHD'`
- **Output**: PromptGroups and Prompts ready for analytics processing
- **Triggered by**: Celery task `process_domain_task` or API endpoint

---

## 2. Prompt Analytics Processor (`prompt_analytics_processor.py`)

### Purpose
The Prompt Analytics Processor handles:
- Processing prompts across multiple LLM platforms (ChatGPT, Gemini, Perplexity)
- Extracting analytics (mentions, citations, sentiment, position)
- Aggregating results at group and domain levels
- Creating metric snapshots for time-series analysis
- Managing competitor mentions

### Key Components

#### Class: `PromptAnalyticsProcessor`
- **Initialization**: Loads platform clients (OpenAI, Gemini, Perplexity)
- **Concurrency**: Manages max concurrent prompts per group (default: 10)

#### Main Processing Flow

1. **Scheduling (`schedule_tick`)**
   - Group-wise scheduling (one group at a time)
   - Picks one `INIT` group when domain is `PROC` or `COMP`
   - Marks group as `SCHD`
   - Processes all `INIT` prompts in that group
   - Enforces per-group concurrent limit

2. **Single Prompt Processing (`process_single_prompt`)**
   - Status: `INIT` → `SCHD` → `PROC` → `COMP`
   - For each enabled platform:
     - Calls platform-specific processing function
     - Extracts: mentions, citations, sentiment, position, competitor mentions
   - Creates `PromptAnalytics` records per platform
   - Creates prompt metric snapshots immediately
   - Updates sentiment analytics for theme
   - Checks if group is ready for aggregation

3. **Analytics Creation (`_create_analytics_record`)**
   - Creates one `PromptAnalytics` per platform
   - Extracts position from context using regex
   - Stores competitor mentions from LLM responses
   - Marks as `COMP` and `is_published=True`

4. **Group Aggregation (`_check_and_aggregate_group`)**
   - Triggers when all prompts in group are `COMP` or `FAIL`
   - Calculates group totals (mentions, citations, avg position, sentiment)
   - Calculates visibility score (weighted formula)
   - Updates `PromptGroup` record
   - Creates group metric snapshots
   - Updates `SentimentAnalytics` for theme (per platform)
   - Updates domain-level aggregations
   - Creates domain metric snapshots
   - Checks if domain should be marked as `COMP`

5. **Domain Completion (`_check_and_complete_domain`)**
   - Checks if all groups are `COMP`
   - If complete:
     - Checks for unused keywords
     - If unused keywords exist → resets domain to `INIT` for next cycle
     - If no unused keywords → marks domain as `COMP`
     - Triggers topic processing via Celery task

### Key Methods

- `_calculate_visibility_score()`: Weighted formula (40% mentions, 30% citations, 20% sentiment, 10% position)
- `_update_sentiment_analytics_for_theme()`: Creates platform-specific SentimentAnalytics records
- `_create_prompt_metric_snapshots()`: Time-series snapshots per platform
- `_create_group_metric_snapshots()`: Group-level snapshots per platform
- `_create_domain_metric_snapshots()`: Domain-level snapshots per platform

### Platform Processing
- **ChatGPT**: Uses OpenAI API with system prompts
- **Gemini**: Uses Google Generative AI library
- **Perplexity**: Uses Perplexity API
- **Fallback**: Returns neutral analytics if platform unavailable

### Integration Points
- **Input**: PromptGroups with `track_status='INIT'`
- **Output**: Completed `PromptAnalytics` records, metric snapshots
- **Triggered by**: Celery task `process_prompt_analytics_scheduler` or API endpoint

---

## 3. Topic Processor (`topic_processor.py`)

### Purpose
The Topic Processor groups keywords into semantic topics using NLP when a domain completes processing.

### Key Components

#### Class: `TopicProcessor`
- **Initialization**: Sets up ChatGPT client for keyword grouping

#### Main Processing Flow (`process_topics_for_domain`)

1. **Keyword Selection**
   - Fetches keywords where `last_used_for_topic_generation` is NULL
   - Only processes unused keywords

2. **Topic Grouping (`_group_keywords_into_topics`)**
   - Uses ChatGPT to group keywords semantically
   - System prompt instructs ChatGPT to group related keywords
   - Returns JSON array with topic names and keyword lists
   - Fallback: Groups all keywords into "General" topic if ChatGPT fails

3. **Topic Creation (`_create_topic`)**
   - Creates `Topic` records with:
     - Domain reference
     - Topic name
     - Keyword list (JSON array)
     - Status: `INIT`

4. **Keyword Linking (`_link_keywords_to_topic`)**
   - Creates `TopicKeyword` records linking keywords to topics
   - Marks keywords as used (`last_used_for_topic_generation` timestamp)
   - Can be used multiple times (timestamp updated)

### Key Methods

- `_parse_topic_groups()`: Parses ChatGPT JSON response
- `_fallback_group_keywords()`: Fallback when ChatGPT unavailable
- `match_keyword_to_existing_topics()`: Matches new keywords to existing topics

### Integration Points
- **Input**: Domains with `processing_status='COMP'`
- **Output**: `Topic` and `TopicKeyword` records
- **Triggered by**: Celery task `process_topics_for_domain_task` (called when domain completes)

---

## 4. Topic Analytics Processor (`topic_analytics_processor.py`)

### Purpose
The Topic Analytics Processor calculates analytics for keywords and topics based on prompt analytics data.

### Key Components

#### Class: `TopicAnalyticsProcessor`
- Processes keyword and topic analytics from prompt data

#### Main Processing Flow (`process_analytics_for_domain`)

1. **Topic Processing**
   - Gets all topics for domain (status: `INIT`, `PROC`, or `COMP`)
   - For each topic:
     - Updates status: `INIT` → `PROC`
     - Processes keyword analytics
     - Aggregates to topic level
     - Updates status: `PROC` → `COMP`

2. **Keyword Analytics (`_process_keyword_analytics_for_topic`)**
   - Gets `TopicKeyword` records with status `INIT`
   - For each keyword:
     - Finds prompts linked via `PromptKeyword`
     - Gets `PromptAnalytics` for those prompts (status `COMP`)
     - Groups by platform
     - Calculates metrics per platform:
       - Mentions (count in context_summary)
       - Average position
       - Visibility score
       - Sentiment score
     - Creates `KeywordAnalytics` records per platform
     - Marks `TopicKeyword` as `COMP`

3. **Topic Aggregation (`_aggregate_topic_analytics`)**
   - Aggregates keyword analytics to topic level
   - Calculates per-platform metrics:
     - Total mentions
     - Average visibility score
     - Average sentiment score
   - Updates `Topic` record with aggregated metrics
   - Creates `TopicAnalytics` time-series records per platform

4. **Scheduling (`schedule_tick`)**
   - Finds topics needing updates:
     - Topics with `INIT` or `PROC` status
     - Topics with new prompts processed
   - Processes one topic at a time

### Key Methods

- `_calculate_keyword_metrics()`: Calculates metrics from PromptAnalytics
- `_create_keyword_analytics()`: Creates/updates KeywordAnalytics records
- `_aggregate_topic_analytics()`: Aggregates keyword data to topic level

### Integration Points
- **Input**: Topics with `track_status='INIT'`
- **Output**: `KeywordAnalytics` and `TopicAnalytics` records
- **Triggered by**: Celery task `process_topic_analytics_scheduler` or as part of topic processing

---

## Processing Pipeline Flow

```
1. Domain Creation
   └─> Domain status: INIT

2. Domain Processor (domain_processor.py)
   └─> Domain status: SCHD → PROC
   └─> Generates prompts from keywords
   └─> Groups prompts using NLP
   └─> Creates PromptGroups and Prompts
   └─> Domain status: PROC (waiting for analytics)

3. Prompt Analytics Processor (prompt_analytics_processor.py)
   └─> Processes prompts across platforms
   └─> Creates PromptAnalytics records
   └─> Aggregates to group level
   └─> Aggregates to domain level
   └─> Domain status: COMP (when all groups done)

4. Topic Processor (topic_processor.py)
   └─> Triggered when domain status = COMP
   └─> Groups keywords into topics using ChatGPT
   └─> Creates Topic and TopicKeyword records

5. Topic Analytics Processor (topic_analytics_processor.py)
   └─> Calculates keyword analytics from prompts
   └─> Aggregates to topic level
   └─> Creates KeywordAnalytics and TopicAnalytics records
```

---

## Status Management

### Domain Status Flow
- `INIT` → `SCHD` → `PROC` → `COMP` (or `FAIL`)
- Can reset to `INIT` if unused keywords exist after completion

### Prompt Status Flow
- `INIT` → `SCHD` → `PROC` → `COMP` (or `FAIL`)

### PromptGroup Status Flow
- `INIT` → `SCHD` → `PROC` → `COMP` (or `FAIL`)

### Topic Status Flow
- `INIT` → `PROC` → `COMP` (or `FAIL`)

---

## Key Design Patterns

1. **Idempotency**: Uses `select_for_update()` to prevent race conditions
2. **Status Tracking**: Comprehensive status management with `track_status`, `track_message`, `tracked_at`
3. **Platform Abstraction**: Supports multiple LLM platforms with fallback handling
4. **Incremental Processing**: Only processes unused keywords/prompts
5. **Aggregation Hierarchy**: Prompt → Group → Domain → Topic
6. **Time-Series Snapshots**: Creates metric snapshots for historical analysis
7. **Concurrency Control**: Threading for domains, per-group limits for prompts

---

## Celery Task Integration

### Tasks (`processing_tasks.py`)

1. `process_domain_task`: Processes a single domain
2. `scheduler_tick`: Schedules domains for processing
3. `process_prompt_analytics_task`: Processes a single prompt
4. `process_prompt_analytics_scheduler`: Schedules prompt groups for processing
5. `process_topics_for_domain_task`: Processes topics for a domain
6. `process_topic_analytics_scheduler`: Periodic topic analytics updates

### Scheduling
- Domain scheduler: Picks `INIT` domains, marks as `SCHD`, enqueues task
- Prompt scheduler: Picks `INIT` groups, processes all prompts in group
- Topic scheduler: Processes incomplete topics or topics with new data

---

## Error Handling

- **Graceful Degradation**: Fallback analytics when platforms unavailable
- **Status Tracking**: Failed items marked as `FAIL` with error messages
- **Transaction Safety**: Uses `transaction.atomic()` for critical operations
- **Logging**: Comprehensive logging at all levels

---

## Performance Considerations

1. **Concurrency Limits**: 
   - Max concurrent domains: 10 (configurable)
   - Max concurrent prompts per group: 10 (configurable)

2. **Database Optimization**:
   - Uses `select_for_update()` for locking
   - Bulk operations where possible
   - Indexed queries on status fields

3. **NLP Processing**:
   - SentenceTransformers model loaded once
   - KMeans clustering optimized for prompt count

4. **Incremental Processing**:
   - Only processes unused keywords/prompts
   - Tracks usage with timestamps

---

## Summary

The engine implements a sophisticated multi-stage processing pipeline:

1. **Domain Processor**: Generates and groups prompts from keywords
2. **Prompt Analytics Processor**: Analyzes prompts across LLM platforms and aggregates results
3. **Topic Processor**: Organizes keywords into semantic topics
4. **Topic Analytics Processor**: Calculates analytics for keywords and topics

Each processor is designed to be:
- **Idempotent**: Safe to retry
- **Incremental**: Only processes new/unused data
- **Resilient**: Handles errors gracefully
- **Scalable**: Supports concurrent processing with limits
- **Observable**: Comprehensive status tracking and logging

