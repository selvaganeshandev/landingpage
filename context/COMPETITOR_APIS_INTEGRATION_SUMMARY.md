# Competitor APIs Integration Summary

## ✅ All APIs Created and Integrated

### Backend APIs (`backend/competitors/views.py`)

#### 1. **Competitive Strength Analysis**
- **Endpoint**: `GET /competitors/competitive-strength-analysis/?domain_id={id}`
- **Purpose**: Returns radar chart data comparing your brand with top 3 competitors
- **Metrics**: Visibility, Sentiment, Position, Coverage, Growth
- **Data Sources**: 
  - `PromptAnalytics` (your brand)
  - `Competitor` model (competitor metrics)
  - `CompetitorAnalytics` (time-series data)
  - `CompetitorPromptAnalytics` (coverage calculation)

#### 2. **Competitive Insights**
- **Endpoint**: `GET /competitors/competitive-insights/?domain_id={id}`
- **Purpose**: Generates automated competitive intelligence insights
- **Insights Generated**:
  - Market leadership status
  - Sentiment advantages
  - Competitor momentum tracking
  - Opportunity gaps identification
- **Returns**: Up to 4 insights with type (success/warning/opportunity) and impact (high/medium)

#### 3. **Answer Gap Analysis**
- **Endpoint**: `GET /competitors/answer-gap-analysis/?domain_id={id}&competitor_id={id}`
- **Purpose**: Finds queries where competitors appear but you don't
- **Returns**: Top 20 gaps with:
  - Query text
  - Competitor name
  - Mention counts (competitor vs yours)
  - Opportunity level (high/medium/low)
  - Platforms where gaps exist

---

### Frontend Integration (`frontend/src/pages/Competitors.tsx`)

#### API Client Methods (`frontend/src/services/api.ts`)
```typescript
// All three APIs are integrated:
getCompetitiveStrengthAnalysis({ domain_id: string })
getCompetitiveInsights({ domain_id: string })
getAnswerGapAnalysis({ domain_id: string, competitor_id?: string })
```

#### Data Loading
- All APIs are called in parallel using `Promise.all()`
- Error handling with `.catch()` to prevent page crashes
- Fallback to static data if APIs fail or return empty
- Console logging for debugging

#### UI Components Updated
1. **Competitive Strength Analysis (Radar Chart)**
   - Dynamically renders based on API data
   - Handles any number of competitors
   - Shows empty state if no data

2. **Competitive Intelligence (Insights Cards)**
   - Displays insights from API
   - Shows type badges (success/warning/opportunity)
   - Impact indicators (high/medium)
   - Empty state handling

3. **Answer Gap Analysis**
   - Lists gaps from API
   - Shows opportunity levels
   - Platform badges
   - "Generate Content" button for each gap

---

## 🔍 How to Verify APIs Are Working

### 1. Check Backend URLs
```bash
# Verify URLs are registered
cd backend
python manage.py show_urls | grep competitive
```

Expected output:
```
/competitors/competitive-strength-analysis/
/competitors/competitive-insights/
/competitors/answer-gap-analysis/
```

### 2. Test APIs Directly

#### Test Competitive Strength Analysis:
```bash
curl -X GET "http://localhost:8000/competitors/competitive-strength-analysis/?domain_id=1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Expected response:
```json
[
  {
    "metric": "Visibility",
    "yourbrand": 85,
    "competitor1": 78,
    "competitor2": 72
  },
  {
    "metric": "Sentiment",
    "yourbrand": 75,
    "competitor1": 68,
    "competitor2": 71
  },
  ...
]
```

#### Test Competitive Insights:
```bash
curl -X GET "http://localhost:8000/competitors/competitive-insights/?domain_id=1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Expected response:
```json
[
  {
    "title": "Market Leadership Maintained",
    "description": "Your Brand maintains #1 position with 42% market share...",
    "type": "success",
    "impact": "high"
  },
  ...
]
```

#### Test Answer Gap Analysis:
```bash
curl -X GET "http://localhost:8000/competitors/answer-gap-analysis/?domain_id=1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Expected response:
```json
[
  {
    "id": 1,
    "query": "Best vegan protein powder",
    "competitor": "Competitor Name",
    "mentions": 45,
    "yourMentions": 0,
    "opportunity": "high",
    "platforms": ["ChatGPT", "Perplexity"]
  },
  ...
]
```

### 3. Check Frontend Console

1. Open browser DevTools (F12)
2. Navigate to `/competitors` page
3. Check Console tab for:
   - `"Competitive strength analysis loaded: X metrics"`
   - `"Competitive insights loaded: X insights"`
   - `"Answer gap analysis loaded: X gaps"`
   - Or warnings if APIs fail (with fallback messages)

### 4. Verify UI Updates

1. **Radar Chart**: Should show data from API (or fallback if empty)
2. **Insights Cards**: Should display insights from API
3. **Answer Gap Tab**: Should list gaps from API

---

## 🐛 Troubleshooting

### Issue: APIs return empty arrays
**Solution**: 
- Check if domain has competitors and analytics data
- Verify `domain_id` is correct
- Check database has:
  - `Competitor` records
  - `CompetitorAnalytics` records
  - `PromptAnalytics` records
  - `ShareOfVoiceAnalytics` records

### Issue: 404 Not Found
**Solution**:
- Verify URLs are registered in `backend/competitors/urls.py`
- Check Django server is running on port 8000
- Verify URL pattern matches: `/competitors/competitive-strength-analysis/`

### Issue: 401 Unauthorized
**Solution**:
- Check authentication token is valid
- Verify token is in localStorage: `localStorage.getItem('access_token')`
- Re-login if token expired

### Issue: Frontend shows fallback data
**Solution**:
- Check browser console for API errors
- Verify API endpoints are accessible
- Check network tab for failed requests
- APIs gracefully fallback to static data if they fail

---

## 📊 Data Flow

```
Frontend (Competitors.tsx)
  ↓
API Client (api.ts)
  ↓
Backend API Endpoints
  ↓
Database Models:
  - Competitor
  - CompetitorAnalytics
  - CompetitorPromptAnalytics
  - PromptAnalytics
  - ShareOfVoiceAnalytics
  ↓
Response JSON
  ↓
Frontend State Updates
  ↓
UI Components Render
```

---

## ✅ Integration Checklist

- [x] Backend APIs created
- [x] URLs registered
- [x] Frontend API client methods added
- [x] Data fetching integrated in Competitors page
- [x] Error handling implemented
- [x] Fallback data configured
- [x] UI components updated
- [x] Console logging added
- [x] Empty state handling
- [x] Type safety (TypeScript)

---

## 🎯 Next Steps

1. **Test with Real Data**: Ensure database has competitor and analytics data
2. **Monitor Console**: Check browser console for any warnings/errors
3. **Verify Calculations**: Ensure metrics are calculated correctly
4. **Performance**: Monitor API response times
5. **Error Handling**: Test error scenarios (no data, API failures)

---

## 📝 Notes

- All APIs use `AllowAny` permission for now (can be changed to `IsAuthenticated` if needed)
- APIs gracefully handle missing data (return empty arrays)
- Frontend has fallback static data for development/testing
- Console logging helps with debugging
- All date calculations use timezone-aware datetime objects

