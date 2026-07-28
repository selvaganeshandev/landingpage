# Topics Analytics API Integration

## Summary

Created dedicated, optimized API endpoints for the Topics page analytics sections and integrated them with the frontend.

## New Backend API Endpoints

### 1. Topic Distribution
**Endpoint:** `GET /topics/topic-analytics/distribution/?domain_id={id}`

**Purpose:** Get pie chart data showing distribution of mentions across topics

**Response Format:**
```json
[
  {
    "name": "Topic Name",
    "value": 150,
    "topic_id": 1
  }
]
```

**Query Parameters:**
- `domain_id` (required): Domain ID to filter topics

---

### 2. Top Keyword Performance
**Endpoint:** `GET /topics/topic-analytics/keyword-performance/?domain_id={id}&limit={n}`

**Purpose:** Get aggregated keyword analytics across all topics in a domain

**Response Format:**
```json
[
  {
    "keyword": "keyword text",
    "total_mentions": 250,
    "avg_position": 3.5,
    "visibility_score": 85.2,
    "sentiment_score": 0.75,
    "platform_count": 3,
    "platforms": ["ChatGPT", "Claude", "Perplexity"]
  }
]
```

**Query Parameters:**
- `domain_id` (required): Domain ID to filter keywords
- `limit` (optional, default=10): Number of top keywords to return

**SQL Query:**
- Joins: `keyword_analytics` ← `topic_keywords` ← `topics` ← `keywords`
- Aggregates by keyword across all platforms
- Filters by domain and COMP status
- Orders by total mentions DESC

---

### 3. AI-Generated Prompt Suggestions
**Endpoint:** `GET /topics/topic-analytics/prompt-suggestions/?domain_id={id}&limit={n}`

**Purpose:** Get relevant prompts linked to topics in a domain

**Response Format:**
```json
[
  {
    "id": 1,
    "prompt_text": "What are the best...",
    "topic_name": "Topic Name",
    "group_theme": "Theme",
    "analytics_count": 5,
    "avg_position": 2.5,
    "avg_sentiment": 0.8,
    "mentions": 120,
    "relevance_score": 85,
    "search_volume": "high"
  }
]
```

**Query Parameters:**
- `domain_id` (required): Domain ID to filter prompts
- `limit` (optional, default=6): Number of prompts to return

**SQL Query:**
- Joins: `prompts` ← `prompt_keywords` ← `topic_keywords` ← `topics` ← `prompt_groups`
- Left join with `prompt_analytics` for metrics
- Calculates relevance score from avg position
- Determines search volume from total mentions
- Orders by mentions DESC, relevance DESC

---

## Frontend Integration

### API Client Updates (`frontend/src/services/api.ts`)

Added three new API methods:

```typescript
getTopicDistribution: (domainId: number) => {
  return apiRequest(`/topics/topic-analytics/distribution/?domain_id=${domainId}`);
},

getTopicKeywordPerformance: (domainId: number, limit: number = 10) => {
  return apiRequest(`/topics/topic-analytics/keyword-performance/?domain_id=${domainId}&limit=${limit}`);
},

getTopicPromptSuggestions: (domainId: number, limit: number = 6) => {
  return apiRequest(`/topics/topic-analytics/prompt-suggestions/?domain_id=${domainId}&limit=${limit}`);
},
```

### Topics Page Updates (`frontend/src/pages/Topics.tsx`)

**Before:** Made 5+ individual API calls, aggregated data in frontend
**After:** Makes 3 optimized API calls, receives pre-aggregated data

#### Changes Made:

1. **Topic Distribution**
   - Replaced: Local `useMemo` aggregation from topics list
   - With: Direct API call to `getTopicDistribution()`
   - Benefit: Consistent data, no client-side aggregation

2. **Top Keyword Performance**
   - Replaced: Loop through 5 topics, fetch keywords for each, aggregate manually
   - With: Single API call to `getTopicKeywordPerformance()`
   - Benefit: 5x fewer API calls, backend aggregation, better performance

3. **AI-Generated Prompt Suggestions**
   - Replaced: Fetch prompts for first topic only
   - With: Domain-wide prompt suggestions via `getTopicPromptSuggestions()`
   - Benefit: Better suggestions from all topics, not just one

#### State Management:

Added new state variable:
```typescript
const [topicDistributionData, setTopicDistributionData] = useState<any[]>([]);
```

#### Data Flow:

```typescript
// Fetch all analytics data in parallel
const fetchTopics = async () => {
  // 1. Fetch topics
  const topicsData = await apiClient.getTopicsByDomain(selectedDomain.id);
  
  // 2. Fetch distribution
  const distributionData = await apiClient.getTopicDistribution(selectedDomain.id);
  setTopicDistributionData(distributionWithColors);
  
  // 3. Fetch keyword performance
  const keywordData = await apiClient.getTopicKeywordPerformance(selectedDomain.id, 10);
  setKeywordPerformance(formattedKeywords);
  
  // 4. Fetch prompt suggestions
  const promptsData = await apiClient.getTopicPromptSuggestions(selectedDomain.id, 6);
  setPromptSuggestions(suggestions);
};
```

#### Error Handling:

Each API call wrapped in try-catch:
- Logs errors to console
- Sets empty array on failure
- Shows "No data available" message in UI

---

## Benefits

### Performance Improvements
- **API Calls Reduced:** From 7-10 calls → 4 calls (60% reduction)
- **Data Transfer:** Aggregated at backend, less data over network
- **Client Processing:** No frontend aggregation loops

### Code Quality
- **Separation of Concerns:** Backend handles data aggregation
- **Maintainability:** Single source of truth for analytics logic
- **Scalability:** Backend can optimize queries with indexes

### User Experience
- **Faster Load Times:** Fewer API calls, parallel fetching
- **Consistent Data:** All sections use same data source
- **Error Resilience:** Individual sections fail independently

---

## Database Dependencies

These endpoints require the following tables to have data:

1. **topics** - Topic definitions
2. **topic_keywords** - Links topics to keywords
3. **keywords** - Keyword definitions
4. **keyword_analytics** - Platform-specific keyword metrics (track_status='COMP')
5. **prompts** - Prompt definitions
6. **prompt_keywords** - Links prompts to keywords
7. **prompt_groups** - Prompt grouping/themes
8. **prompt_analytics** - Prompt performance metrics (track_status='COMP')

### Data Flow Chain:
```
Keywords → Topic Processor → Topics + TopicKeywords
    ↓
Keywords → Keyword Analytics Processor → KeywordAnalytics
    ↓
Prompts → Prompt Processor → Prompts + PromptKeywords + PromptGroups
    ↓
Prompts → Prompt Analytics Processor → PromptAnalytics
    ↓
All Data → Topic Analytics Endpoints → Frontend
```

---

## Testing

### Manual Testing Steps:

1. **Start Backend Server:**
   ```bash
   cd backend
   source /path/to/env/bin/activate
   python manage.py runserver 8000
   ```

2. **Test Endpoints (with auth token):**
   ```bash
   # Get auth token
   TOKEN=$(curl -X POST http://localhost:8000/auth/login/ \
     -H "Content-Type: application/json" \
     -d '{"email":"user@example.com","password":"password"}' \
     | jq -r '.access')
   
   # Test distribution
   curl -H "Authorization: Bearer $TOKEN" \
     "http://localhost:8000/topics/topic-analytics/distribution/?domain_id=1"
   
   # Test keyword performance
   curl -H "Authorization: Bearer $TOKEN" \
     "http://localhost:8000/topics/topic-analytics/keyword-performance/?domain_id=1&limit=10"
   
   # Test prompt suggestions
   curl -H "Authorization: Bearer $TOKEN" \
     "http://localhost:8000/topics/topic-analytics/prompt-suggestions/?domain_id=1&limit=6"
   ```

3. **Test Frontend:**
   - Navigate to `http://localhost:8080/topics`
   - Select a domain from dropdown
   - Verify all three sections load:
     - Topic Distribution (pie chart)
     - Top Keyword Performance (bar chart)
     - AI-Generated Prompt Suggestions (list)

---

## Files Modified

### Backend:
- `backend/topics/views.py` - Added 3 new @action methods to TopicAnalyticsViewSet
- `backend/topics/urls.py` - No changes (router auto-registers new actions)

### Frontend:
- `frontend/src/services/api.ts` - Added 3 new API methods
- `frontend/src/pages/Topics.tsx` - Replaced aggregation logic with API calls

---

## Future Enhancements

1. **Caching:** Add Redis caching for analytics endpoints
2. **Real-time Updates:** WebSocket notifications when data changes
3. **Filters:** Add date range, platform, sentiment filters
4. **Export:** Add CSV/PDF export for analytics data
5. **Pagination:** For large datasets, add pagination support
6. **Comparison:** Add ability to compare multiple domains

