# Dashboard API Integration Guide

## ✅ Integration Complete

The dashboard API has been successfully integrated into the frontend Dashboard component.

## Backend Setup

### API Endpoint
- **URL**: `GET /analytics/dashboard/summary/`
- **Query Parameters**:
  - `domain_id` (required): The domain ID to fetch data for
  - `days` (optional, default=7): Number of days to look back

### Authentication
- Requires Bearer token authentication
- Token obtained from login endpoint: `POST /auth/login/`

### Response Structure
```json
{
  "period_days": 30,
  "mentions": {
    "total": 0,
    "avg_position": 0.0,
    "avg_sentiment": 0.0,
    "by_platform": [
      {
        "platform": "ChatGPT",
        "count": 10
      }
    ],
    "top_mentions": []
  },
  "alerts": {
    "active": 1,
    "summary": [
      {
        "type": "visibility_drop",
        "severity": "high",
        "status": "active",
        "count": 1
      }
    ]
  },
  "sentiment": {
    "positive_percentage": 53.23,
    "neutral_percentage": 32.05,
    "negative_percentage": 14.72,
    "total_mentions": 1501
  },
  "share_of_voice_latest": {
    "date": "2025-11-03",
    "your_brand": {
      "share_percentage": 43.77,
      "mention_count": 169
    },
    "competitors": [
      {
        "competitor_id": 11,
        "share_percentage": 12.52,
        "mention_count": 281,
        "market_position": 2,
        "platform": null
      }
    ]
  }
}
```

## Frontend Setup

### Files Modified
1. **`backend/analytics/views_dashboard.py`** - New dashboard summary view
2. **`backend/analytics/urls.py`** - Added dashboard/summary/ route
3. **`frontend/src/services/api.ts`** - Added getDashboardSummary() method
4. **`frontend/src/pages/Dashboard.tsx`** - Integrated API call and data rendering
5. **`frontend/src/components/PlatformMentions.tsx`** - Updated to accept API data
6. **`frontend/src/components/CompetitorComparison.tsx`** - Updated to accept API data

### Configuration

#### Backend Server
Backend is running on `http://localhost:8000`

To restart:
```bash
cd /home/hts-005/Documents/python/v3.12/llm-monitor/backend
/home/hts-005/Documents/python/v3.12/env/bin/python manage.py runserver 0.0.0.0:8000
```

#### Frontend Configuration
The frontend automatically points to `http://localhost:8000` by default.

To change the API URL, create a `.env` file in the frontend directory:
```bash
echo "VITE_API_URL=http://localhost:8000" > frontend/.env
```

Then restart the frontend dev server.

## Usage Instructions

### Step 1: Login
1. Navigate to the login page
2. Login with:
   - **Email**: `admin@llmmonitor.com`
   - **Password**: `Admin123`

### Step 2: Set Active Domain
After login, set the active domain ID in browser console:
```javascript
localStorage.setItem('active_domain_id', '52');  // Use your domain ID
```

To find your domain IDs, check:
```bash
curl -X GET "http://localhost:8000/domains/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" | python3 -m json.tool
```

### Step 3: View Dashboard
Navigate to `/dashboard` and the data should load automatically.

The dashboard will:
- Fetch data based on the selected time period (defaults to 30 days)
- Show total mentions, citations, visibility score, average position, and active alerts
- Display platform distribution
- Show share of voice and competitors
- Auto-refresh when time period changes

## Testing the API

### Test Login
```bash
curl -X POST http://localhost:8000/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@llmmonitor.com","password":"Admin123"}'
```

### Test Dashboard API
```bash
# Get access token from login response
TOKEN="YOUR_ACCESS_TOKEN_HERE"

# Test dashboard summary
curl -X GET "http://localhost:8000/analytics/dashboard/summary/?domain_id=52&days=30" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

### Test Domains List
```bash
curl -X GET "http://localhost:8000/domains/" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

## Dashboard Features

### Metrics Displayed
1. **Total Mentions** - Count of all mentions in the time period
2. **Total Citations** - Sum of citations from top mentions
3. **Visibility Score** - Calculated from average sentiment (0-100)
4. **Average Position** - Average position across all platforms
5. **Active Alerts** - Count of active alerts

### Charts & Visualizations
1. **Visibility Score Card** - Shows brand score, mentions, and sentiment breakdown
2. **Platform Mentions** - Distribution of mentions by platform (ChatGPT, Claude, Perplexity, Gemini)
3. **Competitor Comparison** - Share of voice comparison with competitors
4. **Trend Chart** - Historical trends (placeholder, needs data integration)
5. **Mentions Table** - Recent mentions (placeholder, needs data integration)

### Time Period Filters
- 7 days
- 30 days
- 90 days
- 12 months

### Actions
- **Refresh Data** - Manually refresh dashboard data
- **Export Report** - Export dashboard data (implementation pending)

## Troubleshooting

### Dashboard shows no data
1. Ensure you're logged in (check for `access_token` in localStorage)
2. Set a valid domain ID: `localStorage.setItem('active_domain_id', '52')`
3. Check browser console for errors
4. Verify backend is running on port 8000

### CORS errors
- Backend CORS is configured to allow `http://localhost:5173` and `http://localhost:3000`
- In DEBUG mode, all origins are allowed
- If using a different port, update `backend/llm_monitor/settings.py`

### Authentication errors (401)
- Token may have expired
- Login again to get a fresh token
- Access token expires after 1 hour

### Port conflicts
If port 8000 is in use:
```bash
# Kill existing process
lsof -i :8000
kill -9 PID

# Or run on different port
python manage.py runserver 0.0.0.0:8001
```

Then update frontend API URL to match.

## Next Steps

To populate the dashboard with data, you need to:
1. Create prompt groups and prompts for your domain
2. Run the engine to process prompts and generate analytics
3. Set up competitors for share of voice tracking
4. Configure alerts and monitoring rules

Refer to the main project documentation for these workflows.

## API Integration Summary

✅ Backend endpoint created and working  
✅ Frontend API client updated  
✅ Dashboard component fetches live data  
✅ Components updated to render API data  
✅ Authentication flow working  
✅ CORS configured  
✅ Time period filtering working  

The integration is **complete and functional**!

